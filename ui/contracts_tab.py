# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QLabel, QMessageBox, QGroupBox,
                             QHeaderView, QDateEdit, QTextEdit, QDoubleSpinBox,
                             QSpinBox, QFrame, QFileDialog, QMenu, QApplication)  # ← ИСПРАВЛЕНО: QSpinBox + QFrame + QFileDialog + QMenu + QApplication
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QValidator, QDesktopServices, QCursor
from PyQt5.QtCore import QUrl
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from config import PROJECT_TYPES, PROJECT_SUBTYPES, TEMPLATE_SUBTYPES, AGENTS, CITIES, YANDEX_DISK_TOKEN
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar  # ← ДОБАВЛЕНО
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox  # ← ДОБАВЛЕНО
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
from utils.dialog_helpers import create_progress_dialog
from utils.yandex_disk import YandexDiskManager
from utils.table_settings import TableSettings, ProportionalResizeTable
import json
import os
import threading
from utils.button_debounce import debounce_click
from utils.permissions import _has_perm

# ========== ИМПОРТ ДИАЛОГОВ (вынесены в contract_dialogs.py) ==========
from ui.contract_dialogs import (
    FormattedMoneyInput,
    FormattedAreaInput,
    FormattedPeriodInput,
    ContractDialog,
    ContractSearchDialog,
    AgentDialog,
)
# Re-export для обратной совместимости тестов и внешних модулей
# (тесты импортируют: from ui.contracts_tab import ContractDialog)
__all__ = [
    'ContractsTab',
    'ContractDialog',
    'ContractSearchDialog',
    'AgentDialog',
    'FormattedMoneyInput',
    'FormattedAreaInput',
    'FormattedPeriodInput',
]


# ========== ОСНОВНАЯ ВКЛАДКА ДОГОВОРОВ ==========

class ContractsTab(QWidget):
    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.data = DataAccess(api_client=api_client)
        self.api_client = self.data.api_client  # Сохраняем для совместимости (проверки UI)
        self.db = self.data.db  # Сохраняем для совместимости
        self.table_settings = TableSettings()  # ← ДОБАВЛЕНО
        self._data_loaded = False
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 5, 0, 5)

        # Заголовок и кнопки
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)  # Убираем внутренние отступы
        title = QLabel('Управление договорами')
        title.setStyleSheet('font-size: 13px; font-weight: bold; color: #333333;')
        header_layout.addWidget(title)
        header_layout.addStretch()

        search_btn = IconLoader.create_action_button('search', 'Поиск договоров')
        search_btn.clicked.connect(self.open_search)
        header_layout.addWidget(search_btn)

        reset_btn = IconLoader.create_action_button('x-circle', 'Сбросить фильтры')
        reset_btn.clicked.connect(self.reset_filters)
        header_layout.addWidget(reset_btn)

        refresh_btn = IconLoader.create_action_button('refresh', 'Обновить данные с сервера')
        refresh_btn.clicked.connect(self.load_contracts)
        header_layout.addWidget(refresh_btn)

        if _has_perm(self.employee, self.api_client, 'contracts.create'):
            add_btn = IconLoader.create_action_button(
                'add', 'Создать новый договор',
                bg_color='#ffd93c', hover_color='#ffdb4d', icon_color='#000000')
            add_btn.clicked.connect(lambda checked: self.add_contract())
            header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # Таблица договоров - используем ProportionalResizeTable для растягивания + ручного изменения
        self.contracts_table = ProportionalResizeTable()
        self.contracts_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
            }
            QTableCornerButton::section {
                background-color: #fafafa;
                border: none;
                border-bottom: 1px solid #e6e6e6;
                border-right: 1px solid #f0f0f0;
                border-top-left-radius: 8px;
            }
            QHeaderView::section:first {
                border-top-left-radius: 8px;
            }
            QHeaderView::section:last {
                border-top-right-radius: 8px;
            }
        """)
        self.contracts_table.setColumnCount(11)
        self.contracts_table.setHorizontalHeaderLabels([
            ' № ', ' Дата ', ' Адрес объекта ', ' S, м2 ', ' Город ',
            'Тип агента', 'Тип проекта', 'Сумма', 'Клиент', 'Статус', 'Действия'
        ])

        # Настройка пропорционального изменения размера:
        # - Колонки 0-9 растягиваются пропорционально И можно менять вручную
        # - Колонка 10 (Действия) фиксирована 110px
        self.contracts_table.setup_proportional_resize(
            column_ratios=[0.06, 0.08, 0.18, 0.06, 0.10, 0.10, 0.10, 0.10, 0.12, 0.10],  # Пропорции для колонок 0-9
            fixed_columns={10: 110},  # Действия = 110px фиксированно
            min_width=50
        )

        # Запрещаем изменение высоты строк
        self.contracts_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.contracts_table.verticalHeader().setDefaultSectionSize(34)

        self.contracts_table.setSortingEnabled(True)
        # Разрешаем выделение отдельных ячеек для копирования
        self.contracts_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.contracts_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.contracts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.contracts_table.setAlternatingRowColors(True)

        # Добавляем контекстное меню для копирования
        self.contracts_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.contracts_table.customContextMenuRequested.connect(self.show_context_menu)

        # Подключаем обработчик сортировки для сохранения настроек
        self.contracts_table.horizontalHeader().sectionClicked.connect(self.on_sort_changed)
        
        layout.addWidget(self.contracts_table)
        
        self.setLayout(layout)

    def ensure_data_loaded(self):
        """Ленивая загрузка: данные загружаются при первом показе таба.
        При повторном переключении — пропускаем если кэш свежий (<30с)."""
        import time as _time
        now = _time.monotonic()
        first_time = not self._data_loaded

        if first_time:
            self._data_loaded = True
            self._last_load_time = now
            self.data.prefer_local = True
            self.load_contracts()
            self.data.prefer_local = False
        elif now - getattr(self, '_last_load_time', 0) < 30:
            return
        else:
            self._last_load_time = now
            self.load_contracts()

    def load_contracts(self):
        """Загрузка списка договоров"""
        print("[DB REFRESH] Начало обновления данных договоров...")
        self.contracts_table.setSortingEnabled(False)

        # Загружаем договоры через DataAccess (API с fallback на локальную БД)
        try:
            contracts = self.data.get_all_contracts()
        except Exception as e:
            CustomMessageBox(self, "Ошибка загрузки", f"Не удалось загрузить договоры: {e}", "warning").exec_()
            contracts = None

        if not contracts:
            self.contracts_table.setRowCount(0)
            self.contracts_table.setSortingEnabled(True)
            print("[DB REFRESH] Нет данных о договорах")
            return

        print(f"[DB REFRESH] Загружено {len(contracts)} договоров")
        # Загружаем клиентов для отображения имен
        clients_dict = {}
        try:
            clients = self.data.get_all_clients()
            clients_dict = {c['id']: c for c in (clients or [])}
        except Exception:
            pass

        self.contracts_table.setRowCount(len(contracts))

        for row, contract in enumerate(contracts):
            self.contracts_table.setRowHeight(row, 34)

            # Получаем имя клиента
            client_id = contract.get('client_id')
            if client_id in clients_dict:
                client = clients_dict[client_id]
                client_name = client['full_name'] if client.get('client_type') == 'Физическое лицо' else client.get('organization_name', 'Неизвестно')
            else:
                client = self.data.get_client(client_id)
                client_name = client['full_name'] if client and client.get('client_type') == 'Физическое лицо' else (client.get('organization_name', 'Неизвестно') if client else 'Неизвестно')

            self.contracts_table.setItem(row, 0, QTableWidgetItem(contract['contract_number']))

            date_str = contract.get('contract_date', '')
            if date_str:
                try:
                    date_obj = QDate.fromString(date_str, 'yyyy-MM-dd')
                    formatted_date = date_obj.toString('dd.MM.yyyy')
                except Exception:
                    formatted_date = date_str
            else:
                formatted_date = ''
            
            self.contracts_table.setItem(row, 1, QTableWidgetItem(formatted_date))
            self.contracts_table.setItem(row, 2, QTableWidgetItem(contract.get('address', '')))
            self.contracts_table.setItem(row, 3, QTableWidgetItem(str(contract.get('area', 0))))
            self.contracts_table.setItem(row, 4, QTableWidgetItem(contract.get('city', '')))

            # ИСПРАВЛЕНИЕ: Применяем цвет агента с автоматическим выбором контрастного текста
            agent_type = contract.get('agent_type', '')
            agent_item = QTableWidgetItem(agent_type if agent_type else '')

            from PyQt5.QtGui import QColor, QBrush

            if agent_type:
                agent_color = self.data.get_agent_color(agent_type)
                if agent_color:
                    # Устанавливаем цветной фон
                    bg_color = QColor(agent_color)
                    agent_item.setBackground(QBrush(bg_color))

                    # Определяем контрастный цвет текста на основе яркости фона
                    # Формула относительной яркости: (0.299*R + 0.587*G + 0.114*B)
                    brightness = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                    text_color = '#000000' if brightness > 128 else '#FFFFFF'
                    agent_item.setForeground(QBrush(QColor(text_color)))
                else:
                    # Если цвет агента не установлен, используем черный текст на белом фоне
                    agent_item.setBackground(QBrush(QColor('#FFFFFF')))
                    agent_item.setForeground(QBrush(QColor('#000000')))
            else:
                # Если тип агента пуст, используем черный текст на белом фоне
                agent_item.setBackground(QBrush(QColor('#FFFFFF')))
                agent_item.setForeground(QBrush(QColor('#000000')))

            self.contracts_table.setItem(row, 5, agent_item)

            self.contracts_table.setItem(row, 6, QTableWidgetItem(contract['project_type']))
            self.contracts_table.setItem(row, 7, QTableWidgetItem(f"{contract.get('total_amount', 0):,.0f} ₽"))
            self.contracts_table.setItem(row, 8, QTableWidgetItem(client_name))

            status_item = QTableWidgetItem(contract.get('status', 'Новый заказ'))
            if contract['status'] == 'СДАН':
                status_item.setBackground(Qt.green)
            elif contract['status'] == 'РАСТОРГНУТ':
                status_item.setBackground(Qt.red)
                if contract.get('termination_reason'):
                    status_item.setToolTip(f"Причина: {contract['termination_reason']}")
            
            self.contracts_table.setItem(row, 9, status_item)
            
            # ========== КНОПКИ ДЕЙСТВИЙ (SVG) ==========
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(1)

            # Иконка комментария (желтый восклицательный знак)
            if contract.get('comments') and contract['comments'].strip():
                comment_btn = IconLoader.create_icon_button('warning', '', f"Комментарий: {contract['comments']}", icon_size=12)
                comment_btn.setFixedSize(20, 20)
                comment_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFF9C4;
                        border: 1px solid #FFD54F;
                        border-radius: 4px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #FFE082;
                    }
                ''')
                comment_btn.setEnabled(False)  # Только для отображения
                actions_layout.addWidget(comment_btn)

            view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=12)
            view_btn.setFixedSize(20, 20)
            view_btn.setStyleSheet('''
                QPushButton {
                    background-color: #f5f5f5;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #d9d9d9;
                }
            ''')
            view_btn.clicked.connect(lambda checked, c=contract: self.view_contract(c))

            edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=12)
            edit_btn.setFixedSize(20, 20)
            edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #d4e4bc;
                    border: 1px solid #c0d4a8;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #c0d4a8;
                }
            ''')
            edit_btn.clicked.connect(lambda checked, c=contract: self.edit_contract(c))

            # Проверка прав на редактирование договоров
            can_edit = _has_perm(self.employee, self.api_client, 'contracts.update')
            if not can_edit:
                edit_btn.setEnabled(False)
                edit_btn.setToolTip('Нет прав на редактирование')

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(edit_btn)

            if _has_perm(self.employee, self.api_client, 'contracts.delete'):
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить заказ', icon_size=12)
                delete_btn.setFixedSize(20, 20)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 4px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, c=contract: self.delete_contract(c))
                actions_layout.addWidget(delete_btn)

            actions_widget.setLayout(actions_layout)
            self.contracts_table.setCellWidget(row, 10, actions_widget)

        self.contracts_table.setSortingEnabled(True)

        # Восстанавливаем сохраненную сортировку
        column, order = self.table_settings.get_sort_order('contracts')
        if column is not None and order is not None:
            from PyQt5.QtCore import Qt as QtCore
            sort_order = QtCore.AscendingOrder if order == 0 else QtCore.DescendingOrder
            self.contracts_table.sortItems(column, sort_order)

    def _refresh_dashboard(self):
        """Обновить дашборд после изменения данных"""
        mw = self.window()
        if hasattr(mw, 'refresh_current_dashboard'):
            mw.refresh_current_dashboard()

    def _invalidate_crm_cache(self):
        """Сбросить кэш CRM-вкладки, чтобы новые карточки отобразились при переключении"""
        mw = self.window()
        crm_tab = getattr(mw, 'crm_tab', None)
        if crm_tab and hasattr(crm_tab, '_data_loaded'):
            crm_tab._data_loaded = False

    @debounce_click
    def add_contract(self):
        """Добавление договора"""
        if not _has_perm(self.employee, self.api_client, 'contracts.create'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на создание договоров.', 'error').exec_()
            return
        dialog = ContractDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contracts()
            self._refresh_dashboard()
            self._invalidate_crm_cache()

    def view_contract(self, contract_data):
        """Просмотр договора"""
        dialog = ContractDialog(self, contract_data, view_only=True)
        dialog.exec_()

    def edit_contract(self, contract_data):
        """Редактирование договора"""
        if not _has_perm(self.employee, self.api_client, 'contracts.update'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на редактирование договоров.', 'error').exec_()
            return
        dialog = ContractDialog(self, contract_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contracts()
            self._refresh_dashboard()
            self._invalidate_crm_cache()

    @debounce_click(delay_ms=2000)
    def delete_contract(self, contract_data):
        """Удаление договора"""
        if not _has_perm(self.employee, self.api_client, 'contracts.delete'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на удаление договоров.', 'error').exec_()
            return
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            f"Вы точно хотите удалить договор?\n\n"
            f"Договор: {contract_data.get('contract_number', 'N/A')}\n"
            f"Адрес: {contract_data.get('address', 'N/A')}\n\n"
            f"ВНИМАНИЕ: Это действие нельзя отменить!\n"
            f"Будут удалены все связанные данные."
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                contract_id = contract_data['id']

                # Удаляем папку на Яндекс.Диске (если есть)
                yandex_folder_path = contract_data.get('yandex_folder_path')
                if yandex_folder_path:
                    try:
                        from utils.yandex_disk import YandexDiskManager
                        from config import YANDEX_DISK_TOKEN
                        yandex_disk = YandexDiskManager(YANDEX_DISK_TOKEN)
                        if yandex_disk.delete_folder(yandex_folder_path):
                            print(f"[OK] Папка на Яндекс.Диске удалена: {yandex_folder_path}")
                        else:
                            print(f"[WARNING] Не удалось удалить папку на Яндекс.Диске: {yandex_folder_path}")
                    except Exception as e:
                        print(f"[WARNING] Ошибка удаления папки на Яндекс.Диске: {e}")

                # Удаляем договор через DataAccess (API с fallback на локальную БД)
                self.data.delete_contract(contract_id)

                CustomMessageBox(
                    self,
                    'Успех',
                    'Договор успешно удален из системы',
                    'success'
                ).exec_()

                self.load_contracts()
                self._refresh_dashboard()

            except Exception as e:
                print(f"[ERROR] Ошибка удаления договора: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить договор:\n{str(e)}',
                    'error'
                ).exec_()

    def show_context_menu(self, position):
        """Контекстное меню для копирования текста из ячеек"""
        menu = QMenu()

        copy_action = menu.addAction("Копировать")
        copy_action.triggered.connect(self.copy_selected_cells)

        menu.exec_(self.contracts_table.viewport().mapToGlobal(position))

    def copy_selected_cells(self):
        """Копирование выделенных ячеек в буфер обмена"""
        selection = self.contracts_table.selectedItems()
        if not selection:
            return

        # Получаем выделенные ячейки и сортируем по строкам и колонкам
        cells = {}
        for item in selection:
            row = item.row()
            col = item.column()
            if row not in cells:
                cells[row] = {}
            cells[row][col] = item.text()

        # Формируем текст для копирования
        rows = sorted(cells.keys())
        text = ""
        for row in rows:
            cols = sorted(cells[row].keys())
            row_text = "\t".join([cells[row][col] for col in cols])
            text += row_text + "\n"

        # Копируем в буфер обмена
        clipboard = QApplication.clipboard()
        clipboard.setText(text.strip())

    def on_sort_changed(self, column):
        """Сохранение настроек сортировки при клике на заголовок"""
        # Получаем текущий порядок сортировки
        order = self.contracts_table.horizontalHeader().sortIndicatorOrder()
        # Сохраняем настройки (0 = по возрастанию, 1 = по убыванию)
        self.table_settings.save_sort_order('contracts', column, order)
                
    def open_search(self):
        """Открытие диалога поиска договоров"""
        dialog = ContractSearchDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            search_params = dialog.get_search_params()
            self.apply_search(search_params)

    def reset_filters(self):
        """Сброс всех фильтров и перезагрузка всех договоров"""
        # S9.4: QTimer.singleShot предотвращает UI freeze при сбросе
        QTimer.singleShot(0, self.load_contracts)

    def apply_search(self, params):
        """Применение фильтров поиска"""
        from PyQt5.QtCore import QDate

        self.contracts_table.setSortingEnabled(False)

        # Загружаем данные через DataAccess (API с fallback на локальную БД)
        contracts = self.data.get_all_contracts()
        clients = self.data.get_all_clients()
        clients_dict = {c['id']: c for c in clients}

        def get_client(client_id):
            if client_id in clients_dict:
                return clients_dict.get(client_id)
            return self.data.get_client(client_id)

        filtered_contracts = []
        for contract in contracts:
            if params.get('contract_number'):
                if params['contract_number'].lower() not in contract.get('contract_number', '').lower():
                    continue

            if params.get('address'):
                if params['address'].lower() not in contract.get('address', '').lower():
                    continue

            if params.get('client_name'):
                client = get_client(contract['client_id'])
                if client:
                    client_name = client['full_name'] if client['client_type'] == 'Физическое лицо' else client['organization_name']
                    if params['client_name'].lower() not in client_name.lower():
                        continue
                else:
                    continue

            if params.get('date_from'):
                contract_date = QDate.fromString(contract.get('contract_date', ''), 'yyyy-MM-dd')
                if contract_date < params['date_from']:
                    continue

            if params.get('date_to'):
                contract_date = QDate.fromString(contract.get('contract_date', ''), 'yyyy-MM-dd')
                if contract_date > params['date_to']:
                    continue

            filtered_contracts.append(contract)

        self.contracts_table.setRowCount(len(filtered_contracts))

        for row, contract in enumerate(filtered_contracts):
            self.contracts_table.setRowHeight(row, 32)

            client = get_client(contract['client_id'])
            client_name = client['full_name'] if client and client['client_type'] == 'Физическое лицо' else (client['organization_name'] if client else '')

            self.contracts_table.setItem(row, 0, QTableWidgetItem(contract['contract_number']))

            date_str = contract.get('contract_date', '')
            if date_str:
                try:
                    date_obj = QDate.fromString(date_str, 'yyyy-MM-dd')
                    formatted_date = date_obj.toString('dd.MM.yyyy')
                except Exception:
                    formatted_date = date_str
            else:
                formatted_date = ''

            self.contracts_table.setItem(row, 1, QTableWidgetItem(formatted_date))
            self.contracts_table.setItem(row, 2, QTableWidgetItem(contract.get('address', '')))
            self.contracts_table.setItem(row, 3, QTableWidgetItem(str(contract.get('area', 0))))
            self.contracts_table.setItem(row, 4, QTableWidgetItem(contract.get('city', '')))

            # ИСПРАВЛЕНИЕ: Применяем цвет агента с автоматическим выбором контрастного текста
            agent_type = contract.get('agent_type', '')
            agent_item = QTableWidgetItem(agent_type if agent_type else '')

            from PyQt5.QtGui import QColor, QBrush

            if agent_type:
                # Цвета агентов хранятся только локально
                agent_color = self.data.get_agent_color(agent_type)
                if agent_color:
                    # Устанавливаем цветной фон
                    bg_color = QColor(agent_color)
                    agent_item.setBackground(QBrush(bg_color))

                    # Определяем контрастный цвет текста на основе яркости фона
                    # Формула относительной яркости: (0.299*R + 0.587*G + 0.114*B)
                    brightness = (0.299 * bg_color.red() + 0.587 * bg_color.green() + 0.114 * bg_color.blue())
                    text_color = '#000000' if brightness > 128 else '#FFFFFF'
                    agent_item.setForeground(QBrush(QColor(text_color)))
                else:
                    # Если цвет агента не установлен, используем черный текст на белом фоне
                    agent_item.setBackground(QBrush(QColor('#FFFFFF')))
                    agent_item.setForeground(QBrush(QColor('#000000')))
            else:
                # Если тип агента пуст, используем черный текст на белом фоне
                agent_item.setBackground(QBrush(QColor('#FFFFFF')))
                agent_item.setForeground(QBrush(QColor('#000000')))

            self.contracts_table.setItem(row, 5, agent_item)

            self.contracts_table.setItem(row, 6, QTableWidgetItem(contract['project_type']))
            self.contracts_table.setItem(row, 7, QTableWidgetItem(f"{contract.get('total_amount', 0):,.0f} ₽"))
            self.contracts_table.setItem(row, 8, QTableWidgetItem(client_name))
            
            status_item = QTableWidgetItem(contract.get('status', 'Новый заказ'))
            if contract['status'] == 'СДАН':
                status_item.setBackground(Qt.green)
            elif contract['status'] == 'РАСТОРГНУТ':
                status_item.setBackground(Qt.red)
                if contract.get('termination_reason'):
                    status_item.setToolTip(f"Причина: {contract['termination_reason']}")
            
            self.contracts_table.setItem(row, 9, status_item)

            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(2, 0, 2, 0)
            actions_layout.setSpacing(2)

            # Иконка комментария (желтый восклицательный знак)
            if contract.get('comments') and contract['comments'].strip():
                comment_btn = IconLoader.create_icon_button('warning', '', f"Комментарий: {contract['comments']}", icon_size=12)
                comment_btn.setFixedSize(20, 20)
                comment_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFF9C4;
                        border: 1px solid #FFD54F;
                        border-radius: 4px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #FFE082;
                    }
                ''')
                comment_btn.setEnabled(False)  # Только для отображения
                actions_layout.addWidget(comment_btn)

            view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=12)
            view_btn.setFixedSize(20, 20)
            view_btn.setStyleSheet('''
                QPushButton {
                    background-color: #f5f5f5;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #d9d9d9;
                }
            ''')
            view_btn.clicked.connect(lambda checked, c=contract: self.view_contract(c))

            edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=12)
            edit_btn.setFixedSize(20, 20)
            edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: #d4e4bc;
                    border: 1px solid #c0d4a8;
                    border-radius: 4px;
                    padding: 0px;
                }
                QPushButton:hover {
                    background-color: #c0d4a8;
                }
            ''')
            edit_btn.clicked.connect(lambda checked, c=contract: self.edit_contract(c))

            # Проверка прав на редактирование договоров
            can_edit = _has_perm(self.employee, self.api_client, 'contracts.update')
            if not can_edit:
                edit_btn.setEnabled(False)
                edit_btn.setToolTip('Нет прав на редактирование')

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(edit_btn)

            if _has_perm(self.employee, self.api_client, 'contracts.delete'):
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить заказ', icon_size=12)
                delete_btn.setFixedSize(20, 20)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 4px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, c=contract: self.delete_contract(c))
                actions_layout.addWidget(delete_btn)

            actions_widget.setLayout(actions_layout)
            self.contracts_table.setCellWidget(row, 10, actions_widget)

        self.contracts_table.setSortingEnabled(True)

    def on_sync_update(self, updated_contracts):
        """
        Обработчик обновления данных от SyncManager.
        Вызывается при изменении договоров другими пользователями.
        Данные уже обновлены в локальной БД — используем prefer_local для мгновенного обновления UI.
        """
        try:
            print(f"[SYNC] Получено обновление договоров: {len(updated_contracts)} записей")
            # Обновляем из локальной БД (данные уже синхронизированы), не блокируя UI
            self.data.prefer_local = True
            try:
                self.load_contracts()
            finally:
                self.data.prefer_local = False
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации договоров: {e}")
            import traceback
            traceback.print_exc()


