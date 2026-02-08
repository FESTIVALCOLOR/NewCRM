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
from config import PROJECT_TYPES, AGENTS, CITIES, YANDEX_DISK_TOKEN
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar  # ← ДОБАВЛЕНО
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox  # ← ДОБАВЛЕНО
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
from utils.yandex_disk import YandexDiskManager
from utils.table_settings import TableSettings, ProportionalResizeTable
import json
import os
import threading

# Классы FormattedMoneyInput, FormattedAreaInput, FormattedPeriodInput остаются БЕЗ ИЗМЕНЕНИЙ
class FormattedMoneyInput(QLineEdit):
    """Поле ввода суммы с форматированием 1 000 000 ₽"""
    def __init__(self, placeholder='Введите сумму', parent=None):
        super().__init__(parent)
        self.setPlaceholderText(placeholder)
        self.setAlignment(Qt.AlignRight)
        self._value = 0
        
        self.setStyleSheet('''
            QLineEdit {
                padding: 2px 8px;
                min-height: 24px;
                max-height: 24px;
            }
        ''')
    
    def focusInEvent(self, event):
        if self._value > 0:
            self.setText(str(self._value))
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        text = self.text().replace(' ', '').replace('₽', '').replace(',', '')
        
        try:
            if text:
                self._value = int(text)
                formatted = f"{self._value:,} ₽".replace(',', ' ')
                self.setText(formatted)
            else:
                self._value = 0
                self.setText('')
        except ValueError:
            self._value = 0
            self.setText('')
        
        super().focusOutEvent(event)
    
    def value(self):
        return self._value
    
    def setValue(self, value):
        self._value = int(value) if value else 0
        if self._value > 0:
            formatted = f"{self._value:,} ₽".replace(',', ' ')
            self.setText(formatted)
        else:
            self.setText('')


class FormattedAreaInput(QLineEdit):
    """Поле ввода площади с форматированием (м²)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText('Введите площадь')
        self.setAlignment(Qt.AlignRight)
        self._value = 0.0
        
        self.setStyleSheet('''
            QLineEdit {
                padding: 2px 8px;
                min-height: 24px;
                max-height: 24px;
            }
        ''')
    
    def focusInEvent(self, event):
        if self._value > 0:
            self.setText(str(self._value))
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        text = self.text().replace(' м²', '').replace(',', '.')
        
        try:
            if text:
                self._value = float(text)
                if self._value > 10000:
                    self._value = 10000
                formatted = f"{self._value:.1f} м²"
                self.setText(formatted)
            else:
                self._value = 0.0
                self.setText('')
        except ValueError:
            self._value = 0.0
            self.setText('')
        
        super().focusOutEvent(event)
    
    def value(self):
        return self._value
    
    def setValue(self, value):
        self._value = float(value) if value else 0.0
        if self._value > 0:
            formatted = f"{self._value:.1f} м²"
            self.setText(formatted)
        else:
            self.setText('')


class FormattedPeriodInput(QLineEdit):
    """Поле ввода срока (раб. дней)"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText('Введите срок')
        self.setAlignment(Qt.AlignRight)
        self._value = 0
        
        self.setStyleSheet('''
            QLineEdit {
                padding: 2px 8px;
                min-height: 24px;
                max-height: 24px;
            }
        ''')
    
    def focusInEvent(self, event):
        if self._value > 0:
            self.setText(str(self._value))
        super().focusInEvent(event)
    
    def focusOutEvent(self, event):
        text = self.text().replace(' раб. дней', '')
        
        try:
            if text:
                self._value = int(text)
                if self._value > 365:
                    self._value = 365
                formatted = f"{self._value} раб. дней"
                self.setText(formatted)
            else:
                self._value = 0
                self.setText('')
        except ValueError:
            self._value = 0
            self.setText('')
        
        super().focusOutEvent(event)
    
    def value(self):
        return self._value
    
    def setValue(self, value):
        self._value = int(value) if value else 0
        if self._value > 0:
            formatted = f"{self._value} раб. дней"
            self.setText(formatted)
        else:
            self.setText('')


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

        # ========== КНОПКА ПОИСКА (SVG) ==========
        search_btn = IconLoader.create_icon_button('search', 'Поиск', 'Поиск договоров', icon_size=12)
        search_btn.clicked.connect(self.open_search)
        search_btn.setStyleSheet('''
            QPushButton {
                padding: 2px 8px;
                font-weight: 500;
                font-size: 11px;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #fafafa;
                border-color: #c0c0c0;
            }
        ''')
        header_layout.addWidget(search_btn)
        # =========================================

        # ========== КНОПКА СБРОСА ФИЛЬТРОВ (SVG) ==========
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить фильтры', icon_size=12)
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setStyleSheet('''
            QPushButton {
                padding: 2px 8px;
                font-weight: 500;
                font-size: 11px;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #fafafa;
                border-color: #c0c0c0;
            }
        ''')
        header_layout.addWidget(reset_btn)
        # ================================================

        # ========== КНОПКА ОБНОВЛЕНИЯ ДАННЫХ ==========
        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить БД', 'Обновить данные с сервера', icon_size=12)
        refresh_btn.clicked.connect(self.load_contracts)
        refresh_btn.setStyleSheet('''
            QPushButton {
                padding: 2px 8px;
                font-weight: 500;
                font-size: 11px;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #2196F3;
            }
        ''')
        header_layout.addWidget(refresh_btn)
        # ================================================

        # ========== КНОПКА ДОБАВЛЕНИЯ (SVG) ==========
        add_btn = IconLoader.create_icon_button('add', 'Добавить', 'Создать новый договор', icon_size=12)
        add_btn.clicked.connect(self.add_contract)
        add_btn.setStyleSheet('''
            QPushButton {
                padding: 2px 8px;
                font-weight: 600;
                font-size: 11px;
                color: #000000;
                background-color: #ffd93c;
                border: 1px solid #e6c236;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #ffdb4d;
                border-color: #d9b530;
            }
        ''')
        header_layout.addWidget(add_btn)
        # =============================================

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
        """Ленивая загрузка: данные загружаются при первом показе таба"""
        if not self._data_loaded:
            self._data_loaded = True
            self.data.prefer_local = True
            self.load_contracts()
            self.data.prefer_local = False

    def load_contracts(self):
        """Загрузка списка договоров"""
        print("[DB REFRESH] Начало обновления данных договоров...")
        self.contracts_table.setSortingEnabled(False)

        # Загружаем договоры через DataAccess (API с fallback на локальную БД)
        contracts = self.data.get_all_contracts()
        print(f"[DB REFRESH] Загружено {len(contracts)} договоров")
        # Загружаем клиентов для отображения имен
        clients_dict = {}
        try:
            clients = self.data.get_all_clients()
            clients_dict = {c['id']: c for c in clients}
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
                agent_color = self.db.get_agent_color(agent_type)
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

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(edit_btn)

            if self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов']:
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

    def add_contract(self):
        """Добавление договора"""
        dialog = ContractDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contracts()
    
    def view_contract(self, contract_data):
        """Просмотр договора"""
        dialog = ContractDialog(self, contract_data, view_only=True)
        dialog.exec_()
    
    def edit_contract(self, contract_data):
        """Редактирование договора"""
        dialog = ContractDialog(self, contract_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_contracts()

    def delete_contract(self, contract_data):
        """Удаление договора - ИСПРАВЛЕНО 01.02.2026: добавлен fallback и offline поддержка"""
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
        self.load_contracts()

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
                agent_color = self.db.get_agent_color(agent_type)
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

            actions_layout.addWidget(view_btn)
            actions_layout.addWidget(edit_btn)

            if self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов']:
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
        """
        try:
            print(f"[SYNC] Получено обновление договоров: {len(updated_contracts)} записей")
            # Перезагружаем таблицу договоров
            self.load_contracts()
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации договоров: {e}")
            import traceback
            traceback.print_exc()


class ContractDialog(QDialog):
    # Сигналы для межпоточного взаимодействия при загрузке файлов
    contract_file_upload_completed = pyqtSignal(str, str, str, str)  # public_link, yandex_path, file_name, project_type
    contract_file_upload_error = pyqtSignal(str)  # error_msg
    tech_task_upload_completed = pyqtSignal(str, str, str)  # public_link, yandex_path, file_name
    tech_task_upload_error = pyqtSignal(str)  # error_msg
    files_verification_completed = pyqtSignal()  # Сигнал завершения проверки файлов

    def __init__(self, parent, contract_data=None, view_only=False):
        super().__init__(parent)
        self.contract_data = contract_data
        self.view_only = view_only
        self.data = getattr(parent, 'data', DataAccess())
        self.db = self.data.db
        self.api_client = self.data.api_client
        self._uploading_files = 0  # Счётчик загружаемых файлов

        # Инициализация YandexDiskManager
        try:
            self.yandex_disk = YandexDiskManager(YANDEX_DISK_TOKEN)
        except Exception as e:
            print(f"[WARNING] Не удалось инициализировать YandexDiskManager: {e}")
            self.yandex_disk = None

        # Подключаем сигналы к обработчикам
        self.contract_file_upload_completed.connect(self._on_contract_file_uploaded)
        self.contract_file_upload_error.connect(self._on_contract_file_upload_error)
        self.tech_task_upload_completed.connect(self._on_tech_task_file_uploaded)
        self.files_verification_completed.connect(self.refresh_file_labels)
        self.tech_task_upload_error.connect(self._on_tech_task_file_upload_error)

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

        if contract_data:
            self.fill_data()
    
    def init_ui(self):
        title = 'Просмотр договора' if self.view_only else ('Добавление договора' if not self.contract_data else 'Редактирование договора')

        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, title, simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== ДОБАВЛЯЕМ QScrollArea ==========
        from PyQt5.QtWidgets import QScrollArea
        
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget#dialogContent {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Выбор клиента
        client_group = QGroupBox('Клиент')
        client_layout = QFormLayout()
        client_layout.setSpacing(8)

        self.client_combo = CustomComboBox()
        self.client_combo.setEditable(True)
        self.client_combo.setInsertPolicy(QComboBox.NoInsert)
        # ИСПРАВЛЕНИЕ 07.02.2026: Отступы для текста в dropdown (#7)
        self.client_combo.lineEdit().setStyleSheet("padding-left: 8px; padding-right: 8px;")

        # Загрузка клиентов через DataAccess (API с fallback на локальную БД)
        self.all_clients = self.data.get_all_clients()
        for client in self.all_clients:
            name = client['full_name'] if client['client_type'] == 'Физическое лицо' else client['organization_name']
            self.client_combo.addItem(f"{name} ({client['phone']})", client['id'])

        from PyQt5.QtWidgets import QCompleter

        completer = QCompleter([self.client_combo.itemText(i) for i in range(self.client_combo.count())])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.client_combo.setCompleter(completer)

        # ИСПРАВЛЕНИЕ 06.02.2026: Белый фон для dropdown списка автодополнения
        completer.popup().setStyleSheet("""
            QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                padding: 4px;
                selection-background-color: #fff4d9;
            }
            QAbstractItemView::item {
                padding: 6px 8px;
                min-height: 28px;
            }
            QAbstractItemView::item:hover {
                background-color: #fafafa;
            }
        """)

        self.client_combo.lineEdit().setPlaceholderText('Начните вводить имя клиента...')

        client_layout.addRow('Выберите клиента*:', self.client_combo)

        client_group.setLayout(client_layout)
        layout.addWidget(client_group)
        
        # Основные данные
        main_group = QGroupBox('Основные данные')
        main_layout_form = QFormLayout()
        main_layout_form.setSpacing(8)

        self.project_type = CustomComboBox()
        self.project_type.addItems(PROJECT_TYPES)
        self.project_type.currentTextChanged.connect(self.on_project_type_changed)
        main_layout_form.addRow('Тип проекта*:', self.project_type)

        # ИСПРАВЛЕНИЕ: Загрузка агентов из БД с цветами
        agent_layout = QHBoxLayout()
        self.agent_combo = CustomComboBox()
        self.reload_agents()
        agent_layout.addWidget(self.agent_combo)
        add_agent_btn = IconLoader.create_icon_button('settings2', '', 'Добавить', icon_size=14)
        add_agent_btn.setMaximumWidth(28)
        add_agent_btn.setFixedHeight(28)
        add_agent_btn.setStyleSheet('padding: 0px 0px; font-size: 14px;')
        add_agent_btn.setToolTip('Управление агентами')
        add_agent_btn.clicked.connect(self.add_agent)
        agent_layout.addWidget(add_agent_btn)
        main_layout_form.addRow('Агент:', agent_layout)

        city_layout = QHBoxLayout()
        self.city_combo = CustomComboBox()
        self.city_combo.addItems(CITIES)
        city_layout.addWidget(self.city_combo)
        add_city_btn = IconLoader.create_icon_button('settings2', '', 'Добавить', icon_size=14)
        add_city_btn.setMaximumWidth(28)
        add_city_btn.setFixedHeight(28)
        add_city_btn.setStyleSheet('padding: 0px 0px; font-size: 14px;')
        add_city_btn.setToolTip('Управление городами')
        add_city_btn.clicked.connect(self.add_city)
        city_layout.addWidget(add_city_btn)
        main_layout_form.addRow('Город:', city_layout)

        self.contract_number = QLineEdit()
        self.contract_number.setPlaceholderText('№001-2024')
        main_layout_form.addRow('Номер договора*:', self.contract_number)

        self.contract_date = CustomDateEdit()
        self.contract_date.setCalendarPopup(True)
        add_today_button_to_dateedit(self.contract_date)
        self.contract_date.setDate(QDate.currentDate())
        self.contract_date.setDisplayFormat('dd.MM.yyyy')

        main_layout_form.addRow('Дата заключения:', self.contract_date)

        self.address = QLineEdit()
        self.address.setPlaceholderText('г. Москва, ул. Ленина, д.1')

        main_layout_form.addRow('Адрес объекта:', self.address)

        self.area = FormattedAreaInput()
        main_layout_form.addRow('Площадь:', self.area)

        self.total_amount = FormattedMoneyInput('Введите сумму')
        main_layout_form.addRow('Сумма договора:', self.total_amount)
        
        main_group.setLayout(main_layout_form)
        layout.addWidget(main_group)
        
        # Дополнительные поля (Индивидуальный)
        self.individual_group = QGroupBox('Дополнительные данные (Индивидуальный проект)')
        individual_layout = QFormLayout()
        individual_layout.setSpacing(8)

        self.advance_payment = FormattedMoneyInput('1 платёж (Аванс)')
        individual_layout.addRow('1 платеж (Аванс):', self.advance_payment)

        self.additional_payment = FormattedMoneyInput('2 платёж (Доплата)')
        individual_layout.addRow('2 платеж (Доплата):', self.additional_payment)

        self.third_payment = FormattedMoneyInput('3 платёж (Доплата)')
        individual_layout.addRow('3 платеж (Доплата):', self.third_payment)

        self.contract_period = FormattedPeriodInput()
        individual_layout.addRow('Срок договора:', self.contract_period)

        # Виджет загрузки файла договора
        contract_file_layout = QHBoxLayout()
        contract_file_layout.setSpacing(10)

        self.contract_file_label = QLabel('Не загружен')
        self.contract_file_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 5px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 11px;
                min-height: 16px;
            }
            QLabel a {
                color: #ffd93c;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.contract_file_label.setWordWrap(False)
        self.contract_file_label.setFixedHeight(28)
        self.contract_file_label.setOpenExternalLinks(True)
        self.contract_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        # Обрезаем длинный текст с многоточием
        self.contract_file_label.setTextFormat(Qt.RichText)
        from PyQt5.QtWidgets import QSizePolicy
        self.contract_file_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.contract_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.contract_file_label.mousePressEvent = lambda e: self.open_contract_file()
        self.contract_file_path = None  # Хранение пути к файлу

        self.contract_upload_btn = IconLoader.create_icon_button('download', '', 'Загрузить PDF', icon_size=14)
        self.contract_upload_btn.setFixedSize(28, 28)
        self.contract_upload_btn.clicked.connect(lambda: self.upload_contract_file('individual'))
        self.contract_upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                padding: 0px 4px; 
            }
            QPushButton:hover {
                background-color: #f0c929;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        ''')

        # Кнопка удаления файла договора
        self.contract_file_delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
        self.contract_file_delete_btn.setFixedSize(28, 28)
        self.contract_file_delete_btn.setToolTip('Удалить файл')
        self.contract_file_delete_btn.clicked.connect(self.delete_contract_file)
        self.contract_file_delete_btn.setStyleSheet('''
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0px 4px; 
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        ''')
        self.contract_file_delete_btn.setVisible(False)  # Скрыта по умолчанию

        contract_file_layout.addWidget(self.contract_file_label, 1)
        contract_file_layout.addWidget(self.contract_upload_btn, 0)
        contract_file_layout.addWidget(self.contract_file_delete_btn, 0)
        individual_layout.addRow('Файл договора:', contract_file_layout)

        self.individual_group.setLayout(individual_layout)
        layout.addWidget(self.individual_group)

        # Дополнительные поля (Шаблонный)
        self.template_group = QGroupBox('Дополнительные данные (Шаблонный проект)')
        template_layout = QFormLayout()
        template_layout.setSpacing(8)

        self.template_contract_period = FormattedPeriodInput()
        template_layout.addRow('Срок договора:', self.template_contract_period)

        # Виджет загрузки файла договора для шаблонных
        template_contract_file_layout = QHBoxLayout()
        template_contract_file_layout.setSpacing(10)

        self.template_contract_file_label = QLabel('Не загружен')
        self.template_contract_file_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 5px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 11px;
                min-height: 16px;
            }
            QLabel a {
                color: #ffd93c;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.template_contract_file_label.setWordWrap(False)
        self.template_contract_file_label.setFixedHeight(28)
        self.template_contract_file_label.setOpenExternalLinks(True)
        self.template_contract_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.template_contract_file_label.setTextFormat(Qt.RichText)
        self.template_contract_file_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.template_contract_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.template_contract_file_label.mousePressEvent = lambda e: self.open_contract_file()
        self.template_contract_file_path = None

        self.template_contract_upload_btn = IconLoader.create_icon_button('download', '', 'Загрузить PDF', icon_size=14)
        self.template_contract_upload_btn.setFixedSize(28, 28)
        self.template_contract_upload_btn.clicked.connect(lambda: self.upload_contract_file('template'))
        self.template_contract_upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                padding: 0px 4px; 
            }
            QPushButton:hover {
                background-color: #f0c929;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        ''')

        # Кнопка удаления файла договора (шаблонный)
        self.template_contract_file_delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
        self.template_contract_file_delete_btn.setFixedSize(28, 28)
        self.template_contract_file_delete_btn.setToolTip('Удалить файл')
        self.template_contract_file_delete_btn.clicked.connect(self.delete_contract_file)
        self.template_contract_file_delete_btn.setStyleSheet('''
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0px 4px; 
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        ''')
        self.template_contract_file_delete_btn.setVisible(False)  # Скрыта по умолчанию

        template_contract_file_layout.addWidget(self.template_contract_file_label, 1)
        template_contract_file_layout.addWidget(self.template_contract_upload_btn, 0)
        template_contract_file_layout.addWidget(self.template_contract_file_delete_btn, 0)
        template_layout.addRow('Файл договора:', template_contract_file_layout)

        self.template_group.setLayout(template_layout)
        layout.addWidget(self.template_group)

        # Дополнительно
        common_group = QGroupBox('ТЗ и Комментарий')
        common_layout = QFormLayout()
        common_layout.setSpacing(8)

        # Виджет загрузки файла тех.задания
        tech_task_file_layout = QHBoxLayout()
        tech_task_file_layout.setSpacing(10)

        self.tech_task_file_label = QLabel('Не загружен')
        self.tech_task_file_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 5px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 11px;
                min-height: 16px;
            }
            QLabel a {
                color: #ffd93c;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.tech_task_file_label.setWordWrap(False)
        self.tech_task_file_label.setFixedHeight(28)
        self.tech_task_file_label.setOpenExternalLinks(True)
        self.tech_task_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.tech_task_file_label.setTextFormat(Qt.RichText)
        self.tech_task_file_label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        self.tech_task_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        self.tech_task_file_label.mousePressEvent = lambda e: self.open_tech_task_file()
        self.tech_task_file_path = None

        self.tech_task_upload_btn = IconLoader.create_icon_button('download', '', 'Загрузить PDF', icon_size=14)
        self.tech_task_upload_btn.setFixedSize(28, 28)
        self.tech_task_upload_btn.clicked.connect(self.upload_tech_task_file)
        self.tech_task_upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                border: none;
                border-radius: 6px;
                font-size: 11px;
                padding: 0px 4px; 
            }
            QPushButton:hover {
                background-color: #f0c929;
            }
            QPushButton:disabled {
                background-color: #BDC3C7;
                color: #7F8C8D;
            }
        ''')

        # Кнопка удаления файла тех.задания
        self.tech_task_file_delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
        self.tech_task_file_delete_btn.setFixedSize(28, 28)
        self.tech_task_file_delete_btn.setToolTip('Удалить файл')
        self.tech_task_file_delete_btn.clicked.connect(self.delete_tech_task_file_contracts)
        self.tech_task_file_delete_btn.setStyleSheet('''
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 0px 4px; 
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
        ''')
        self.tech_task_file_delete_btn.setVisible(False)  # Скрыта по умолчанию

        tech_task_file_layout.addWidget(self.tech_task_file_label, 1)
        tech_task_file_layout.addWidget(self.tech_task_upload_btn, 0)
        tech_task_file_layout.addWidget(self.tech_task_file_delete_btn, 0)
        common_layout.addRow('Файл тех.задания:', tech_task_file_layout)

        self.comments = QTextEdit()
        self.comments.setPlaceholderText('Введите комментарий...')
        self.comments.setStyleSheet('''
            QTextEdit {
                padding: 2px 8px;
                min-height: 50px;
                max-height: 50px;
            }
        ''')
        common_layout.addRow('Комментарий:', self.comments)

        common_group.setLayout(common_layout)
        layout.addWidget(common_group)
        
        # Кнопки
        if not self.view_only:
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()

            self.save_btn = QPushButton('Сохранить')
            self.save_btn.setFixedHeight(36)
            self.save_btn.clicked.connect(self.save_contract)
            self.save_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd93c;
                    color: #333333;
                    padding: 0px 30px;
                    font-weight: bold;
                    border-radius: 4px;
                    border: none;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #f0c929; }
                QPushButton:pressed { background-color: #e0b919; }
                QPushButton:disabled {
                    background-color: #d9d9d9;
                    color: #666666;
                }
            """)

            self.cancel_btn = QPushButton('Отмена')
            self.cancel_btn.setFixedHeight(36)
            self.cancel_btn.clicked.connect(self.reject)
            self.cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    color: #333333;
                    padding: 0px 30px;
                    border-radius: 4px;
                    border: none;
                    font-weight: bold;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #D0D0D0; }
                QPushButton:pressed { background-color: #C0C0C0; }
                QPushButton:disabled {
                    background-color: #d9d9d9;
                    color: #666666;
                }
            """)

            buttons_layout.addWidget(self.save_btn)
            buttons_layout.addWidget(self.cancel_btn)

            layout.addLayout(buttons_layout)
        else:
            # ========== РЕЖИМ ПРОСМОТРА ==========
            close_btn = QPushButton('Закрыть')
            close_btn.setFixedHeight(36)
            close_btn.clicked.connect(self.reject)
            close_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    color: #333333;
                    padding: 0px 30px;
                    border-radius: 4px;
                    border: none;
                    font-weight: bold;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #D0D0D0; }
                QPushButton:pressed { background-color: #C0C0C0; }
            """)
            layout.addWidget(close_btn)
            # =====================================
        
        # ========== ПОМЕЩАЕМ КОНТЕНТ В SCROLL AREA ==========
        content_widget.setLayout(layout)
        scroll_area.setWidget(content_widget)
        
        border_layout.addWidget(scroll_area)
        # ====================================================
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # ========== БЛОКИРОВКА ПОЛЕЙ (ПОСЛЕ setLayout!) ==========
        if self.view_only:
            # Отключаем текстовые поля
            for child in self.findChildren(QLineEdit):
                child.setReadOnly(True)
                child.setStyleSheet('QLineEdit { background-color: #F0F0F0; }')  # Серый фон

            # Отключаем QTextEdit
            for child in self.findChildren(QTextEdit):
                child.setReadOnly(True)
                child.setStyleSheet('QTextEdit { background-color: #F0F0F0; padding: 2px 8px; min-height: 50px; max-height: 50px; }')  # Серый фон

            # БЛОКИРУЕМ QComboBox (запрещаем открытие списка)
            for child in self.findChildren((QComboBox, CustomComboBox)):
                child.setEnabled(False)
                child.setStyleSheet('QComboBox:disabled { background-color: #F0F0F0; }')  # Серый фон

            # БЛОКИРУЕМ QDateEdit (запрещаем открытие календаря)
            for child in self.findChildren((QDateEdit, CustomDateEdit)):
                child.setEnabled(False)
                child.setStyleSheet('QDateEdit:disabled { background-color: #F0F0F0; color: }')  # Серый фон

            # СКРЫВАЕМ кнопки загрузки, удаления файлов и настроек (агент/город)
            # Список кнопок, которые должны быть скрыты в режиме просмотра
            managed_delete_buttons = [
                self.contract_file_delete_btn,
                self.template_contract_file_delete_btn,
                self.tech_task_file_delete_btn
            ]

            for button in self.findChildren(QPushButton):
                button_text = button.text()
                button_tooltip = button.toolTip()
                tooltip_lower = button_tooltip.strip().lower()

                # Если это одна из кнопок удаления — скрываем БЕЗ УСЛОВИЙ
                if button in managed_delete_buttons and 'удалить файл' in tooltip_lower:
                    button.setVisible(False)  # Принудительно скрываем
                    continue  # Не даём другим правилам её трогать

                # Остальные кнопки — по общим правилам
                if ('загрузить pdf' in tooltip_lower or
                    'удалить файл' in tooltip_lower or
                    button_text == 'Добавить' or
                    'управление' in button_tooltip.lower()):
                    button.setVisible(False)
        # ==========================================================

        self.on_project_type_changed('Индивидуальный')
        
        # ========== АДАПТИВНЫЕ РАЗМЕРЫ С СКРОЛЛОМ ==========
        from PyQt5.QtWidgets import QDesktopWidget
        available_screen = QDesktopWidget().availableGeometry()
        
        # 85-90% от высоты экрана
        min_height = max(int(available_screen.height() * 0.85), 820)
        max_height = min(int(available_screen.height() * 0.90), 950)
        max_width = min(int(available_screen.width() * 0.65), 800)
        
        self.setMinimumWidth(720)
        self.setMaximumWidth(max_width)
        self.setMinimumHeight(min_height)
        self.setMaximumHeight(max_height)

        # Устанавливаем начальный размер
        self.resize(720, min_height)
        # ===================================================

    def showEvent(self, event):
        """Центрируем диалог при показе (когда размеры уже правильно установлены)"""
        super().showEvent(event)
        # Центрируем только при первом показе
        if not hasattr(self, '_centered'):
            from utils.dialog_helpers import center_dialog_on_parent
            center_dialog_on_parent(self)
            self._centered = True

    def on_project_type_changed(self, project_type):
        """Переключение полей в зависимости от типа проекта"""
        if project_type == 'Индивидуальный':
            self.individual_group.show()
            self.template_group.hide()
        elif project_type == 'Шаблонный':
            self.individual_group.hide()
            self.template_group.show()
        else:
            self.individual_group.hide()
            self.template_group.hide()

        # ========== НЕ ИСПОЛЬЗУЕМ adjustSize() ==========

    def truncate_filename(self, filename, max_length=50):
        """Обрезает длинное имя файла с многоточием в середине"""
        if len(filename) <= max_length:
            return filename

        # Разделяем имя и расширение
        import os
        name, ext = os.path.splitext(filename)

        # Рассчитываем сколько символов оставить в начале и конце
        ext_len = len(ext)
        available = max_length - ext_len - 3  # 3 для "..."

        if available <= 0:
            return filename[:max_length - 3] + "..."

        # Половину символов в начало, половину в конец (перед расширением)
        start_len = available // 2
        end_len = available - start_len

        return name[:start_len] + "..." + name[-end_len:] + ext

    def add_agent(self):
        """ИСПРАВЛЕНИЕ: Добавление/редактирования агента с выбором цвета"""
        dialog = AgentDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # Перезагружаем список агентов
            self.reload_agents()

    def reload_agents(self):
        """ИСПРАВЛЕНИЕ: Перезагрузка списка агентов из БД"""
        current_text = self.agent_combo.currentText()
        self.agent_combo.clear()

        agents = self.db.get_all_agents()
        for agent in agents:
            self.agent_combo.addItem(agent['name'])

        # Восстанавливаем выбор если был
        if current_text:
            index = self.agent_combo.findText(current_text)
            if index >= 0:
                self.agent_combo.setCurrentIndex(index)

    def add_city(self):
        """Добавление нового города"""
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setFixedWidth(400)

        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        # Кастомный title bar
        title_bar = CustomTitleBar(dialog, 'Добавить город', simple_mode=True)
        border_layout.addWidget(title_bar)

        # Контент
        content = QWidget()
        content.setStyleSheet("background-color: #FFFFFF;")
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 10)
        content_layout.setSpacing(15)

        # Поле ввода
        label = QLabel('Название города:')
        label.setStyleSheet('font-size: 12px; color: #333;')
        content_layout.addWidget(label)

        city_input = QLineEdit()
        city_input.setPlaceholderText('Введите название города...')
        city_input.setStyleSheet("""
            QLineEdit {
                padding: 6px 8px;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                font-size: 12px;
                max-height: 28px;
                min-height: 28px;
            }
            QLineEdit:focus {
                border: 1px solid #ffd93c;
            }
        """)
        content_layout.addWidget(city_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Добавить')
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        save_btn.clicked.connect(dialog.accept)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        content.setLayout(content_layout)
        border_layout.addWidget(content)
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        dialog.setLayout(main_layout)

        if dialog.exec_() == QDialog.Accepted:
            text = city_input.text().strip()
            if text:
                self.city_combo.addItem(text)
                self.city_combo.setCurrentText(text)

    def fill_data(self):
        """Заполнение формы данными"""
        # Загружаем свежие данные через DataAccess (API с fallback на локальную БД)
        if self.contract_data and self.contract_data.get('id'):
            fresh_data = self.data.get_contract(self.contract_data['id'])
            if fresh_data:
                self.contract_data = fresh_data
                print(f"[fill_data] Загружены свежие данные для контракта {self.contract_data['id']}")

        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == self.contract_data['client_id']:
                self.client_combo.setCurrentIndex(i)
                break
        
        self.project_type.setCurrentText(self.contract_data['project_type'])
        self.agent_combo.setCurrentText(self.contract_data.get('agent_type', ''))
        self.city_combo.setCurrentText(self.contract_data.get('city', ''))
        self.contract_number.setText(self.contract_data['contract_number'])
        
        if self.contract_data.get('contract_date'):
            self.contract_date.setDate(QDate.fromString(self.contract_data['contract_date'], 'yyyy-MM-dd'))
        
        self.address.setText(self.contract_data.get('address', ''))
        self.area.setValue(self.contract_data.get('area', 0))
        self.total_amount.setValue(self.contract_data.get('total_amount', 0))
        self.advance_payment.setValue(self.contract_data.get('advance_payment', 0))
        self.additional_payment.setValue(self.contract_data.get('additional_payment', 0))
        self.third_payment.setValue(self.contract_data.get('third_payment', 0))
        self.contract_period.setValue(self.contract_data.get('contract_period', 0))
        self.template_contract_period.setValue(self.contract_data.get('contract_period', 0))

        # Загружаем данные о файле договора (индивидуальный проект)
        contract_file_link = self.contract_data.get('contract_file_link', '')
        if contract_file_link:
            self.contract_file_path = contract_file_link
            # Используем сохраненное имя файла, если оно есть
            file_name = self.contract_data.get('contract_file_name', '')
            if not file_name:
                file_name = 'Договор.pdf'
            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{contract_file_link}" title="{file_name}">{truncated_name}</a>'
            self.contract_file_label.setText(html_link)
            # Показываем кнопку удаления
            self.contract_file_delete_btn.setVisible(not self.view_only)
            self.contract_upload_btn.setEnabled(False)  # Деактивируем кнопку загрузки
        else:
            self.contract_file_label.setText('Не загружен')
            self.contract_file_delete_btn.setVisible(False)
            self.contract_upload_btn.setEnabled(True)  # Активируем кнопку загрузки

        # Загружаем данные о файле договора (шаблонный проект)
        template_file_link = self.contract_data.get('template_contract_file_link', '')
        if template_file_link:
            self.template_contract_file_path = template_file_link
            # Используем сохраненное имя файла, если оно есть
            file_name = self.contract_data.get('template_contract_file_name', '')
            if not file_name:
                file_name = 'Договор.pdf'
            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{template_file_link}" title="{file_name}">{truncated_name}</a>'
            self.template_contract_file_label.setText(html_link)
            # Показываем кнопку удаления
            self.template_contract_file_delete_btn.setVisible(not self.view_only)
            self.template_contract_upload_btn.setEnabled(False)  # Деактивируем кнопку загрузки
        else:
            self.template_contract_file_label.setText('Не загружен')
            self.template_contract_file_delete_btn.setVisible(False)
            self.template_contract_upload_btn.setEnabled(True)  # Активируем кнопку загрузки

        # Загружаем данные о файле тех.задания
        tech_task_link = self.contract_data.get('tech_task_link', '')
        if tech_task_link:
            self.tech_task_file_path = tech_task_link
            self.tech_task_yandex_path = self.contract_data.get('tech_task_yandex_path', '')
            self.tech_task_file_name = self.contract_data.get('tech_task_file_name', '')
            # Используем сохраненное имя файла, если оно есть
            file_name = self.tech_task_file_name if self.tech_task_file_name else 'ТехЗадание.pdf'
            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{tech_task_link}" title="{file_name}">{truncated_name}</a>'
            self.tech_task_file_label.setText(html_link)
            # Показываем кнопку удаления
            self.tech_task_file_delete_btn.setVisible(not self.view_only)
            self.tech_task_upload_btn.setEnabled(False)  # Деактивируем кнопку загрузки
        else:
            self.tech_task_file_label.setText('Не загружен')
            self.tech_task_file_delete_btn.setVisible(False)
            self.tech_task_upload_btn.setEnabled(True)  # Активируем кнопку загрузки

        self.comments.setPlainText(self.contract_data.get('comments', ''))

        # Проверяем файлы на Яндекс.Диске в фоновом режиме
        self.verify_files_on_yandex_disk()

        # Синхронизируем файлы с Яндекс.Диска (добавляем новые файлы в БД)
        self.sync_files_from_yandex_disk()

    def verify_files_on_yandex_disk(self):
        """Проверка существования файлов на Яндекс.Диске в фоновом режиме"""
        if not self.contract_data:
            return

        contract_id = self.contract_data['id']

        def check_files():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                conn = self.db.connect()
                cursor = conn.cursor()

                # Получаем данные о файлах
                cursor.execute('''
                    SELECT tech_task_yandex_path, measurement_yandex_path,
                           contract_file_yandex_path, template_contract_file_yandex_path
                    FROM contracts WHERE id = ?
                ''', (contract_id,))
                result = cursor.fetchone()

                if not result:
                    conn.close()
                    return

                needs_update = False
                update_data = {}

                # Проверяем файл договора (индивидуальный)
                if result['contract_file_yandex_path']:
                    if not yd.file_exists(result['contract_file_yandex_path']):
                        print(f"[INFO] Файл договора не найден на Яндекс.Диске, удаляем из БД")
                        update_data['contract_file_link'] = ''
                        update_data['contract_file_yandex_path'] = ''
                        update_data['contract_file_name'] = ''
                        needs_update = True

                # Проверяем файл договора (шаблонный)
                if result['template_contract_file_yandex_path']:
                    if not yd.file_exists(result['template_contract_file_yandex_path']):
                        print(f"[INFO] Файл шаблонного договора не найден на Яндекс.Диске, удаляем из БД")
                        update_data['template_contract_file_link'] = ''
                        update_data['template_contract_file_yandex_path'] = ''
                        update_data['template_contract_file_name'] = ''
                        needs_update = True

                # Проверяем тех.задание
                if result['tech_task_yandex_path']:
                    if not yd.file_exists(result['tech_task_yandex_path']):
                        print(f"[INFO] Файл ТЗ не найден на Яндекс.Диске, удаляем из БД")
                        update_data['tech_task_link'] = ''
                        update_data['tech_task_yandex_path'] = ''
                        update_data['tech_task_file_name'] = ''
                        needs_update = True

                # Проверяем замер
                if result['measurement_yandex_path']:
                    if not yd.file_exists(result['measurement_yandex_path']):
                        print(f"[INFO] Файл замера не найден на Яндекс.Диске, удаляем из БД")
                        update_data['measurement_image_link'] = ''
                        update_data['measurement_yandex_path'] = ''
                        update_data['measurement_file_name'] = ''
                        needs_update = True

                # Обновляем БД если нужно
                if needs_update:
                    if self.api_client:
                        # Используем API для обновления
                        try:
                            self.api_client.update_contract(contract_id, update_data)
                        except Exception as e:
                            print(f"[ERROR] Не удалось обновить через API: {e}")
                    else:
                        # Локальный режим - используем прямой SQL
                        for key, value in update_data.items():
                            cursor.execute(f'UPDATE contracts SET {key} = ? WHERE id = ?', (value, contract_id))
                        conn.commit()

                    # Отправляем сигнал для обновления UI в главном потоке
                    self.files_verification_completed.emit()

                conn.close()

            except Exception as e:
                print(f"[ERROR] Ошибка при проверке файлов на Яндекс.Диске: {e}")

        # Запускаем проверку в фоновом потоке
        thread = threading.Thread(target=check_files, daemon=True)
        thread.start()

    def sync_files_from_yandex_disk(self):
        """Синхронизация файлов с Яндекс.Диска в БД

        Сканирует папку договора на Яндекс.Диске и автоматически добавляет
        файлы с именами Договор, ТЗ, Анкета, Замер в базу данных
        """
        if not self.contract_data:
            return

        contract_id = self.contract_data.get('id')
        yandex_folder_path = self.contract_data.get('yandex_folder_path')

        if not contract_id or not yandex_folder_path:
            return

        def sync_files():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                conn = self.db.connect()
                cursor = conn.cursor()

                # Получаем текущие данные о файлах из БД
                cursor.execute('''
                    SELECT contract_file_yandex_path, template_contract_file_yandex_path,
                           tech_task_yandex_path, measurement_yandex_path,
                           project_type
                    FROM contracts WHERE id = ?
                ''', (contract_id,))
                result = cursor.fetchone()

                if not result:
                    conn.close()
                    return

                needs_update = False
                update_data = {}
                project_type = result['project_type'] if result['project_type'] else 'Индивидуальный'

                # Определяем какие файлы искать в зависимости от типа проекта
                file_mappings = []

                if project_type == 'Индивидуальный':
                    # Для индивидуального проекта ищем обычный договор
                    if not result['contract_file_yandex_path']:
                        file_mappings.append({
                            'subfolder': 'Документы',
                            'keywords': ['договор', 'contract'],
                            'extensions': ['.pdf', '.docx', '.doc'],
                            'db_fields': {
                                'contract_file_link': 'public_link',
                                'contract_file_yandex_path': 'yandex_path',
                                'contract_file_name': 'file_name'
                            }
                        })
                else:
                    # Для шаблонного проекта ищем шаблонный договор
                    if not result['template_contract_file_yandex_path']:
                        file_mappings.append({
                            'subfolder': 'Документы',
                            'keywords': ['договор', 'contract'],
                            'extensions': ['.pdf', '.docx', '.doc'],
                            'db_fields': {
                                'template_contract_file_link': 'public_link',
                                'template_contract_file_yandex_path': 'yandex_path',
                                'template_contract_file_name': 'file_name'
                            }
                        })

                # ТЗ (Техническое задание)
                if not result['tech_task_yandex_path']:
                    file_mappings.append({
                        'subfolder': 'Анкета',
                        'keywords': ['тз', 'анкета', 'техническое задание'],
                        'extensions': ['.pdf', '.docx', '.doc'],
                        'db_fields': {
                            'tech_task_link': 'public_link',
                            'tech_task_yandex_path': 'yandex_path',
                            'tech_task_file_name': 'file_name'
                        }
                    })

                # Замер
                if not result['measurement_yandex_path']:
                    file_mappings.append({
                        'subfolder': 'Замер',
                        'keywords': ['замер', 'measurement'],
                        'extensions': ['.pdf', '.jpg', '.jpeg', '.png', '.gif', '.bmp'],
                        'db_fields': {
                            'measurement_image_link': 'public_link',
                            'measurement_yandex_path': 'yandex_path',
                            'measurement_file_name': 'file_name'
                        }
                    })

                # Сканируем каждую подпапку
                for mapping in file_mappings:
                    subfolder_path = f"{yandex_folder_path}/{mapping['subfolder']}"

                    # Проверяем существование подпапки
                    if not yd.folder_exists(subfolder_path):
                        continue

                    # Получаем список файлов в подпапке
                    items = yd.get_folder_contents(subfolder_path)

                    # Ищем файлы с нужными ключевыми словами
                    for item in items:
                        if item.get('type') != 'file':
                            continue

                        file_name = item.get('name')
                        if not file_name:
                            continue

                        # Получаем расширение файла
                        file_name_lower = file_name.lower()
                        file_extension = None
                        for ext in mapping['extensions']:
                            if file_name_lower.endswith(ext):
                                file_extension = ext
                                break

                        # Проверяем расширение
                        if not file_extension:
                            continue

                        # Проверяем, содержит ли имя файла одно из ключевых слов
                        keyword_found = False
                        matched_keyword = None
                        for keyword in mapping['keywords']:
                            if keyword in file_name_lower:
                                keyword_found = True
                                matched_keyword = keyword
                                break

                        if keyword_found:
                            print(f"[INFO SYNC] Найден файл '{file_name}' на Яндекс.Диске! (ключевое слово: '{matched_keyword}')")

                            # Формируем полный путь к файлу
                            file_path = f"{subfolder_path}/{file_name}"

                            # Получаем публичную ссылку
                            public_link = yd.get_public_link(file_path)

                            if public_link:
                                # Сохраняем данные для обновления БД
                                for db_field, value_type in mapping['db_fields'].items():
                                    if value_type == 'public_link':
                                        update_data[db_field] = public_link
                                    elif value_type == 'yandex_path':
                                        update_data[db_field] = file_path
                                    elif value_type == 'file_name':
                                        update_data[db_field] = file_name

                                needs_update = True
                                print(f"[OK SYNC] Файл '{file_name}' добавлен в очередь для синхронизации")
                                break  # Нашли файл, переходим к следующей подпапке

                # Обновляем БД если нашли новые файлы
                if needs_update:
                    print(f"[INFO SYNC] Обновляем БД: {update_data}")
                    if self.api_client:
                        # Используем API для обновления
                        try:
                            self.api_client.update_contract(contract_id, update_data)
                        except Exception as e:
                            print(f"[ERROR] Не удалось обновить через API: {e}")
                    else:
                        # Локальный режим - используем прямой SQL
                        for key, value in update_data.items():
                            cursor.execute(f'UPDATE contracts SET {key} = ? WHERE id = ?', (value, contract_id))
                        conn.commit()
                    print(f"[OK SYNC] Синхронизация завершена! Добавлено полей: {len(update_data)}")

                    # Отправляем сигнал для обновления UI в главном потоке
                    self.files_verification_completed.emit()
                else:
                    print(f"[INFO SYNC] Новых файлов для синхронизации не найдено")

                conn.close()

            except Exception as e:
                print(f"[ERROR] Ошибка при синхронизации файлов с Яндекс.Диска: {e}")
                import traceback
                traceback.print_exc()

        # Запускаем синхронизацию в фоновом потоке
        thread = threading.Thread(target=sync_files, daemon=True)
        thread.start()

    def refresh_file_labels(self):
        """Обновление меток файлов после проверки"""
        if not self.contract_data:
            return

        contract_id = self.contract_data['id']

        # Перезагружаем данные из БД или API
        if self.api_client:
            try:
                contract_data = self.api_client.get_contract(contract_id)
            except Exception as e:
                print(f"[WARN] Ошибка загрузки контракта из API: {e}")
                contract_data = self.db.get_contract_by_id(contract_id)
        else:
            contract_data = self.db.get_contract_by_id(contract_id)
        if contract_data:

            self.contract_data = contract_data

            # Обновляем файл договора (индивидуальный)
            if not contract_data.get('contract_file_link'):
                self.contract_file_label.setText('Не загружен')
                self.contract_file_delete_btn.setVisible(False)
                self.contract_upload_btn.setEnabled(True)  # Активируем кнопку загрузки
            else:
                file_name = contract_data.get('contract_file_name', 'Договор.pdf')
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{contract_data["contract_file_link"]}" title="{file_name}">{truncated_name}</a>'
                self.contract_file_label.setText(html_link)
                self.contract_file_delete_btn.setVisible(True)
                self.contract_upload_btn.setEnabled(False)  # Деактивируем кнопку загрузки

            # Обновляем файл договора (шаблонный)
            if not contract_data.get('template_contract_file_link'):
                self.template_contract_file_label.setText('Не загружен')
                self.template_contract_file_delete_btn.setVisible(False)
                self.template_contract_upload_btn.setEnabled(True)  # Активируем кнопку загрузки
            else:
                file_name = contract_data.get('template_contract_file_name', 'Договор.pdf')
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{contract_data["template_contract_file_link"]}" title="{file_name}">{truncated_name}</a>'
                self.template_contract_file_label.setText(html_link)
                self.template_contract_file_delete_btn.setVisible(True)
                self.template_contract_upload_btn.setEnabled(False)  # Деактивируем кнопку загрузки

            # Обновляем тех.задание
            if not contract_data.get('tech_task_link'):
                self.tech_task_file_label.setText('Не загружен')
                self.tech_task_file_delete_btn.setVisible(False)
                self.tech_task_upload_btn.setEnabled(True)  # Активируем кнопку загрузки
            else:
                file_name = contract_data.get('tech_task_file_name', 'ТехЗадание.pdf')
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{contract_data["tech_task_link"]}" title="{file_name}">{truncated_name}</a>'
                self.tech_task_file_label.setText(html_link)
                self.tech_task_file_delete_btn.setVisible(True)
                self.tech_task_upload_btn.setEnabled(False)  # Деактивируем кнопку загрузки

    def upload_contract_file(self, project_type):
        """Загрузка файла договора на Яндекс.Диск"""
        from PyQt5.QtWidgets import QProgressDialog
        from PyQt5.QtCore import Qt
        from PyQt5.QtGui import QPixmap

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF файл договора",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Проверяем наличие yandex_folder_path
        contract_folder = self.get_contract_yandex_folder()
        if not contract_folder:
            CustomMessageBox(
                self,
                'Ошибка',
                'Сначала сохраните договор, чтобы создать папку на Яндекс.Диске',
                'warning'
            ).exec_()
            return

        file_name = os.path.basename(file_path)

        # Создаем прогресс-диалог
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, 3, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файла")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)

        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if progress.wasCanceled():
                        return
                    progress.setValue(step)
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    progress.setLabelText(f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)")

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Документы",
                    file_name,
                    progress_callback=update_progress
                )

                if result:
                    progress.setValue(3)
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # Отправляем сигнал в главный поток с полными данными
                    self.contract_file_upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name'],
                        project_type
                    )
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.contract_file_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                import traceback
                traceback.print_exc()
                self.contract_file_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_contract_file_uploaded(self, public_link, yandex_path, file_name, project_type):
        """Обработчик успешной загрузки файла договора"""

        if public_link:
            # Сохраняем в атрибуты
            if project_type == 'individual':
                self.contract_file_path = public_link
            else:
                self.template_contract_file_path = public_link

            # Сохраняем в базу данных, если договор уже существует
            if self.contract_data and self.contract_data.get('id'):
                contract_id = self.contract_data['id']

                if self.api_client:
                    # Многопользовательский режим - обновляем через API
                    try:
                        if project_type == 'individual':
                            update_data = {
                                'contract_file_link': public_link,
                                'contract_file_yandex_path': yandex_path,
                                'contract_file_name': file_name
                            }
                        else:
                            update_data = {
                                'template_contract_file_link': public_link,
                                'template_contract_file_yandex_path': yandex_path,
                                'template_contract_file_name': file_name
                            }
                        self.api_client.update_contract(contract_id, update_data)
                        self.contract_data = self.api_client.get_contract(contract_id)
                    except Exception as e:
                        print(f"[WARNING] Ошибка обновления contract через API: {e}")
                else:
                    # Локальный режим - обновляем локальную БД
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    if project_type == 'individual':
                        cursor.execute('''
                            UPDATE contracts
                            SET contract_file_link = ?,
                                contract_file_yandex_path = ?,
                                contract_file_name = ?
                            WHERE id = ?
                        ''', (public_link, yandex_path, file_name, contract_id))
                    else:
                        cursor.execute('''
                            UPDATE contracts
                            SET template_contract_file_link = ?,
                                template_contract_file_yandex_path = ?,
                                template_contract_file_name = ?
                            WHERE id = ?
                        ''', (public_link, yandex_path, file_name, contract_id))

                    conn.commit()
                    conn.close()
                    self.contract_data = self.db.get_contract_by_id(contract_id)

            # Обновляем лейблы с HTML ссылкой (обрезаем длинное имя)
            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>'
            if project_type == 'individual':
                self.contract_file_label.setText(html_link)
                self.contract_file_delete_btn.setVisible(True)
                # ИСПРАВЛЕНИЕ: Блокируем кнопку загрузки сразу после загрузки
                if hasattr(self, 'contract_upload_btn'):
                    self.contract_upload_btn.setEnabled(False)
            else:
                self.template_contract_file_label.setText(html_link)
                self.template_contract_file_delete_btn.setVisible(True)
                # ИСПРАВЛЕНИЕ: Блокируем кнопку загрузки сразу после загрузки
                if hasattr(self, 'template_contract_upload_btn'):
                    self.template_contract_upload_btn.setEnabled(False)
        else:
            if project_type == 'individual':
                self.contract_file_label.setText('Не загружен')
            else:
                self.template_contract_file_label.setText('Не загружен')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл на Яндекс.Диск', 'error').exec_()

    def _on_contract_file_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файла договора"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файла: {error_msg}', 'error').exec_()
        print(f"[ERROR] Ошибка загрузки файла договора: {error_msg}")

    def upload_tech_task_file(self):
        """Загрузка файла тех.задания на Яндекс.Диск"""
        from PyQt5.QtWidgets import QProgressDialog
        from PyQt5.QtCore import Qt

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF файл тех.задания",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Проверяем наличие yandex_folder_path
        contract_folder = self.get_contract_yandex_folder()
        if not contract_folder:
            CustomMessageBox(
                self,
                'Ошибка',
                'Сначала сохраните договор, чтобы создать папку на Яндекс.Диске',
                'warning'
            ).exec_()
            return

        file_name = os.path.basename(file_path)

        # Создаем прогресс-диалог
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, 3, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файла")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)

        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if progress.wasCanceled():
                        return
                    progress.setValue(step)
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    progress.setLabelText(f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)")

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Анкета",
                    file_name,
                    progress_callback=update_progress
                )

                if result:
                    progress.setValue(3)
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # Отправляем сигнал в главный поток с полными данными
                    self.tech_task_upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name']
                    )
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.tech_task_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                import traceback
                traceback.print_exc()
                self.tech_task_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_tech_task_file_uploaded(self, public_link, yandex_path, file_name):
        """Обработчик успешной загрузки файла тех.задания"""

        if public_link:
            # Сохраняем в атрибуты
            self.tech_task_file_path = public_link
            self.tech_task_yandex_path = yandex_path
            self.tech_task_file_name = file_name

            # Сохраняем в базу данных, если договор уже существует
            if self.contract_data and self.contract_data.get('id'):
                contract_id = self.contract_data['id']

                if self.api_client:
                    # Многопользовательский режим - обновляем через API
                    try:
                        update_data = {
                            'tech_task_link': public_link,
                            'tech_task_yandex_path': yandex_path,
                            'tech_task_file_name': file_name
                        }
                        self.api_client.update_contract(contract_id, update_data)
                        self.contract_data = self.api_client.get_contract(contract_id)
                    except Exception as e:
                        print(f"[WARNING] Ошибка обновления contract через API: {e}")
                else:
                    # Локальный режим - обновляем локальную БД
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE contracts
                        SET tech_task_link = ?,
                            tech_task_yandex_path = ?,
                            tech_task_file_name = ?
                        WHERE id = ?
                    ''', (public_link, yandex_path, file_name, contract_id))
                    conn.commit()
                    conn.close()
                    self.contract_data = self.db.get_contract_by_id(contract_id)

            # Обновляем лейбл с HTML ссылкой (обрезаем длинное имя)
            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>'
            self.tech_task_file_label.setText(html_link)

            # Показываем кнопку удаления
            self.tech_task_file_delete_btn.setVisible(True)

            # ИСПРАВЛЕНИЕ: Блокируем кнопку загрузки сразу после загрузки
            if hasattr(self, 'tech_task_upload_btn'):
                self.tech_task_upload_btn.setEnabled(False)
        else:
            self.tech_task_file_label.setText('Не загружен')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл на Яндекс.Диск', 'error').exec_()

    def _on_tech_task_file_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файла тех.задания"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файла: {error_msg}', 'error').exec_()

    def get_contract_yandex_folder(self):
        """Получение пути к папке договора на Яндекс.Диске"""
        if self.contract_data:
            # Редактирование существующего договора
            return self.contract_data.get('yandex_folder_path')
        else:
            # Новый договор - нужно сначала сохранить
            return None

    def open_contract_file(self):
        """Открытие файла договора"""
        file_path = None
        if hasattr(self, 'contract_file_path') and self.contract_file_path:
            file_path = self.contract_file_path
        elif hasattr(self, 'template_contract_file_path') and self.template_contract_file_path:
            file_path = self.template_contract_file_path

        if file_path:
            QDesktopServices.openUrl(QUrl(file_path))

    def open_tech_task_file(self):
        """Открытие файла тех.задания"""
        if hasattr(self, 'tech_task_file_path') and self.tech_task_file_path:
            QDesktopServices.openUrl(QUrl(self.tech_task_file_path))

    def delete_contract_file(self):
        """Удаление файла договора"""
        if not self.contract_data:
            CustomMessageBox(self, 'Ошибка', 'Сначала сохраните договор', 'warning').exec_()
            return

        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить файл договора?'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        contract_id = self.contract_data['id']

        # Получаем путь к файлу на Яндекс.Диске перед удалением из БД
        contract_yandex_path = None
        template_yandex_path = None
        try:
            if self.api_client:
                contract = self.api_client.get_contract(contract_id)
                if contract:
                    contract_yandex_path = contract.get('contract_file_yandex_path')
                    template_yandex_path = contract.get('template_contract_file_yandex_path')
            else:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT contract_file_yandex_path, template_contract_file_yandex_path FROM contracts WHERE id = ?', (contract_id,))
                result = cursor.fetchone()
                conn.close()
                contract_yandex_path = result['contract_file_yandex_path'] if result else None
                template_yandex_path = result['template_contract_file_yandex_path'] if result else None
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к файлам: {e}")

        # Обновляем БД/API
        update_data = {
            'contract_file_link': '',
            'contract_file_yandex_path': '',
            'contract_file_name': '',
            'template_contract_file_link': '',
            'template_contract_file_yandex_path': '',
            'template_contract_file_name': ''
        }
        try:
            if self.api_client:
                self.api_client.update_contract(contract_id, update_data)
            else:
                self.db.update_contract(contract_id, update_data)

            # Удаляем файлы с Яндекс.Диска
            if contract_yandex_path:
                try:
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    yd.delete_file(contract_yandex_path)
                    print(f"[INFO] Файл договора удален с Яндекс.Диска: {contract_yandex_path}")
                except Exception as e:
                    print(f"[WARN] Не удалось удалить файл договора с Яндекс.Диска: {e}")

            if template_yandex_path:
                try:
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    yd.delete_file(template_yandex_path)
                    print(f"[INFO] Файл шаблонного договора удален с Яндекс.Диска: {template_yandex_path}")
                except Exception as e:
                    print(f"[WARN] Не удалось удалить файл шаблонного договора с Яндекс.Диска: {e}")

            # Обновляем UI
            self.contract_file_label.setText('Не загружен')
            self.template_contract_file_label.setText('Не загружен')
            self.contract_file_path = None
            self.template_contract_file_path = None

            # Скрываем кнопки удаления и активируем кнопки загрузки
            self.contract_file_delete_btn.setVisible(False)
            self.template_contract_file_delete_btn.setVisible(False)
            self.contract_upload_btn.setEnabled(True)
            self.template_contract_upload_btn.setEnabled(True)

            CustomMessageBox(self, 'Успех', 'Файл договора успешно удален', 'success').exec_()

            # Отправляем сигнал для обновления UI (чтобы другие открытые окна тоже обновились)
            # Делаем это после закрытия MessageBox чтобы избежать конфликтов
            self.files_verification_completed.emit()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка при удалении файла: {str(e)}', 'error').exec_()

    def delete_tech_task_file_contracts(self):
        """Удаление файла тех.задания из contracts tab"""
        if not self.contract_data:
            CustomMessageBox(self, 'Ошибка', 'Сначала сохраните договор', 'warning').exec_()
            return

        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить файл ТЗ?'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        contract_id = self.contract_data['id']

        # Получаем путь к файлу на Яндекс.Диске перед удалением из БД
        yandex_path = self.tech_task_yandex_path if hasattr(self, 'tech_task_yandex_path') else None

        # Обновляем БД/API
        update_data = {
            'tech_task_link': '',
            'tech_task_yandex_path': '',
            'tech_task_file_name': ''
        }
        try:
            if self.api_client:
                self.api_client.update_contract(contract_id, update_data)
            else:
                self.db.update_contract(contract_id, update_data)

            # Удаляем файл с Яндекс.Диска
            if yandex_path:
                try:
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    yd.delete_file(yandex_path)
                except Exception as e:
                    print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")

            # Обновляем UI
            self.tech_task_file_label.setText('Не загружен')
            self.tech_task_file_path = None
            self.tech_task_yandex_path = None
            self.tech_task_file_name = None

            # Скрываем кнопку удаления и активируем кнопку загрузки
            self.tech_task_file_delete_btn.setVisible(False)
            self.tech_task_upload_btn.setEnabled(True)

            CustomMessageBox(self, 'Успех', 'Файл ТЗ успешно удален', 'success').exec_()

            # Отправляем сигнал для обновления UI (чтобы другие открытые окна тоже обновились)
            # Делаем это после закрытия MessageBox чтобы избежать конфликтов
            self.files_verification_completed.emit()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка при удалении файла: {str(e)}', 'error').exec_()

    def _lock_dialog(self):
        """Блокировка кнопок диалога во время загрузки файлов"""
        self._uploading_files += 1
        if hasattr(self, 'save_btn'):
            self.save_btn.setEnabled(False)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setEnabled(False)

    def _unlock_dialog(self):
        """Разблокировка кнопок диалога после загрузки файлов"""
        self._uploading_files = max(0, self._uploading_files - 1)
        if self._uploading_files == 0:
            if hasattr(self, 'save_btn'):
                self.save_btn.setEnabled(True)
            if hasattr(self, 'cancel_btn'):
                self.cancel_btn.setEnabled(True)

    def closeEvent(self, event):
        """Блокировка закрытия окна во время загрузки файлов"""
        if self._uploading_files > 0:
            CustomMessageBox(self, 'Внимание', 'Дождитесь завершения загрузки файлов', 'warning').exec_()
            event.ignore()
        else:
            event.accept()

    def save_contract(self):
        """Сохранение договора"""
        if not self.contract_number.text().strip():
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Ошибка', 'Укажите номер договора', 'warning').exec_()
            return

        contract_number = self.contract_number.text().strip()

        # Получаем ID текущего договора для исключения из проверки
        current_contract_id = self.contract_data.get('id') if self.contract_data else None

        # Проверяем существование договора с таким номером
        # Для нового договора - просто проверяем наличие номера
        # Для редактирования - проверяем с исключением текущего договора
        if self.api_client:
            existing = self.api_client.check_contract_number_exists(contract_number, exclude_id=current_contract_id)
        else:
            existing = self.db.check_contract_number_exists(contract_number, exclude_id=current_contract_id)
        if existing:
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(
                self,
                'Ошибка',
                f'Договор с номером "{contract_number}" уже существует!\n\n'
                f'Пожалуйста, укажите другой номер.',
                'error'
            ).exec_()
            return

        project_type = self.project_type.currentText()

        # Определяем откуда брать contract_period и contract_file_link
        if project_type == 'Шаблонный':
            contract_period = self.template_contract_period.value()
            contract_file_link = self.template_contract_file_path if hasattr(self, 'template_contract_file_path') and self.template_contract_file_path else ''
        else:
            contract_period = self.contract_period.value()
            contract_file_link = self.contract_file_path if hasattr(self, 'contract_file_path') and self.contract_file_path else ''

        # Получаем данные тех.задания
        tech_task_link = self.tech_task_file_path if hasattr(self, 'tech_task_file_path') and self.tech_task_file_path else ''
        tech_task_yandex_path = self.tech_task_yandex_path if hasattr(self, 'tech_task_yandex_path') and self.tech_task_yandex_path else ''
        tech_task_file_name = self.tech_task_file_name if hasattr(self, 'tech_task_file_name') and self.tech_task_file_name else ''

        contract_data = {
            'client_id': self.client_combo.currentData(),
            'project_type': project_type,
            'agent_type': self.agent_combo.currentText(),
            'city': self.city_combo.currentText(),
            'contract_number': contract_number,
            'contract_date': self.contract_date.date().toString('yyyy-MM-dd'),
            'address': self.address.text().strip(),
            'area': self.area.value(),
            'total_amount': self.total_amount.value(),
            'advance_payment': self.advance_payment.value(),
            'additional_payment': self.additional_payment.value(),
            'third_payment': self.third_payment.value(),
            'contract_period': contract_period,
            'contract_file_link': contract_file_link,
            'tech_task_link': tech_task_link,
            'tech_task_yandex_path': tech_task_yandex_path,
            'tech_task_file_name': tech_task_file_name,
            'comments': self.comments.toPlainText().strip()
        }

        try:
            if self.contract_data:
                # Обновление существующего договора
                old_contract = self.contract_data

                # Проверяем, изменились ли данные, влияющие на путь к папке
                old_city = old_contract.get('city', '')
                old_address = old_contract.get('address', '')
                old_area = old_contract.get('area', 0)
                old_agent_type = old_contract.get('agent_type', '')
                old_project_type = old_contract.get('project_type', '')

                new_city = self.city_combo.currentText()
                new_address = self.address.text().strip()
                new_area = self.area.value()
                new_agent_type = self.agent_combo.currentText()
                new_project_type = self.project_type.currentText()

                folder_changed = (
                    old_city != new_city or
                    old_address != new_address or
                    old_area != new_area or
                    old_agent_type != new_agent_type or
                    old_project_type != new_project_type
                )

                # Обновляем договор в БД
                if self.api_client and self.api_client.is_online:
                    # API режим
                    self.api_client.update_contract(self.contract_data['id'], contract_data)
                elif self.api_client:
                    # Offline режим - сохраняем локально и добавляем в очередь
                    self.db.update_contract(self.contract_data['id'], contract_data)
                    if self.offline_manager:
                        from utils.offline_manager import OperationType
                        self.offline_manager.queue_operation(
                            OperationType.UPDATE, 'contract', self.contract_data['id'], contract_data
                        )
                        CustomMessageBox(self, 'Offline режим',
                            'Изменения сохранены локально.\nДанные будут синхронизированы при восстановлении подключения.', 'info').exec_()
                else:
                    # Локальный режим
                    self.db.update_contract(self.contract_data['id'], contract_data)

                # Переименование папки на Яндекс.Диске при изменении данных
                old_folder_path = old_contract.get('yandex_folder_path', '')
                if folder_changed and old_folder_path and self.yandex_disk:
                    try:
                        # Строим новый путь к папке
                        new_folder_path = self.yandex_disk.build_contract_folder_path(
                            agent_type=new_agent_type,
                            project_type=new_project_type,
                            city=new_city,
                            address=new_address,
                            area=new_area
                        )

                        # Перемещаем папку (переименовываем)
                        if self.yandex_disk.move_folder(old_folder_path, new_folder_path):
                            # Обновляем путь в БД
                            if self.api_client:
                                self.api_client.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
                            else:
                                self.db.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
                            print(f"[OK] Папка переименована: {old_folder_path} -> {new_folder_path}")
                        else:
                            # Яндекс.Диск недоступен - добавляем в offline очередь
                            print(f"[WARNING] Не удалось переименовать папку на Яндекс.Диске, добавляем в очередь")
                            if self.offline_manager:
                                from utils.offline_manager import OperationType
                                self.offline_manager.queue_operation(
                                    OperationType.UPDATE,
                                    'yandex_folder',
                                    self.contract_data['id'],
                                    {'old_path': old_folder_path, 'new_path': new_folder_path}
                                )
                                # Сохраняем новый путь локально (будет актуален после синхронизации)
                                self.db.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
                    except Exception as e:
                        print(f"[WARNING] Ошибка переименования папки: {e}")
                        # При ошибке тоже добавляем в очередь
                        if self.offline_manager and old_folder_path:
                            try:
                                new_folder_path = self.yandex_disk.build_contract_folder_path(
                                    agent_type=new_agent_type,
                                    project_type=new_project_type,
                                    city=new_city,
                                    address=new_address,
                                    area=new_area
                                )
                                from utils.offline_manager import OperationType
                                self.offline_manager.queue_operation(
                                    OperationType.UPDATE,
                                    'yandex_folder',
                                    self.contract_data['id'],
                                    {'old_path': old_folder_path, 'new_path': new_folder_path}
                                )
                                self.db.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
                                print(f"[QUEUE] Переименование папки добавлено в очередь: {old_folder_path} -> {new_folder_path}")
                            except Exception as queue_error:
                                print(f"[ERROR] Не удалось добавить в очередь: {queue_error}")
            else:
                # Создание нового договора
                new_contract_id = None
                if self.api_client and self.api_client.is_online:
                    # API режим
                    result = self.api_client.create_contract(contract_data)
                    new_contract_id = result.get('id')
                elif self.api_client:
                    # Offline режим - сохраняем локально и добавляем в очередь
                    self.db.add_contract(contract_data)
                    new_contract_id = self.db.conn.execute("SELECT last_insert_rowid()").fetchone()[0]
                    if self.offline_manager:
                        from utils.offline_manager import OperationType
                        self.offline_manager.queue_operation(
                            OperationType.CREATE, 'contract', new_contract_id, contract_data
                        )
                        CustomMessageBox(self, 'Offline режим',
                            'Договор создан локально.\nДанные будут синхронизированы при восстановлении подключения.', 'info').exec_()
                else:
                    # Локальный режим
                    self.db.add_contract(contract_data)
                    # Получить ID последнего добавленного договора
                    new_contract_id = self.db.conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                # ПРИМЕЧАНИЕ: CRM карточка создается автоматически:
                # - В локальном режиме: db_manager.add_contract() вызывает _create_crm_card()
                # - В API режиме: сервер создает карточку при создании договора

                # Создание папки на Яндекс.Диске для нового договора
                if new_contract_id and self.yandex_disk:
                    try:
                        # Получаем данные для создания папки
                        agent_type = self.agent_combo.currentText()
                        project_type = self.project_type.currentText()
                        city = self.city_combo.currentText()
                        address = self.address.text().strip()
                        area = self.area.value()

                        # Создаем структуру папок
                        folder_path = self.yandex_disk.create_contract_folder_structure(
                            agent_type=agent_type,
                            project_type=project_type,
                            city=city,
                            address=address,
                            area=area
                        )

                        # Обновить путь к папке в договоре
                        if folder_path:
                            if self.api_client:
                                self.api_client.update_contract(new_contract_id, {'yandex_folder_path': folder_path})
                            else:
                                self.db.update_contract(new_contract_id, {'yandex_folder_path': folder_path})

                            print(f"[OK] Папка на Яндекс.Диске создана: {folder_path}")
                        else:
                            print(f"[WARNING] Папка на Яндекс.Диске не была создана")
                    except Exception as e:
                        print(f"[WARNING] Не удалось создать папку на Яндекс.Диске: {e}")

            # ИСПРАВЛЕНИЕ: Закрываем диалог без показа сообщения
            self.accept()

        except Exception as e:
            error_msg = str(e)
            if 'UNIQUE constraint failed' in error_msg or 'уже существует' in error_msg:
                # ========== ЗАМЕНИЛИ QMessageBox ==========
                CustomMessageBox(
                    self,
                    'Ошибка сохранения',
                    f'Договор с таким номером уже существует!\n\n'
                    f'Измените номер договора и попробуйте снова.',
                    'error'
                ).exec_()
            else:
                # ========== ЗАМЕНИЛИ QMessageBox ==========
                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось сохранить договор:\n{error_msg}',
                    'error'
                ).exec_()
                
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

class ContractSearchDialog(QDialog):
    """Диалог поиска договоров"""
    def __init__(self, parent):
        super().__init__(parent)
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Поиск договоров', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()

        input_style = """
            QLineEdit {
            }
        """

        self.contract_number_input = QLineEdit()
        self.contract_number_input.setPlaceholderText('№001-2024')
        self.contract_number_input.setStyleSheet(input_style)
        form_layout.addRow('Номер договора:', self.contract_number_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText('Адрес объекта')
        self.address_input.setStyleSheet(input_style)
        form_layout.addRow('Адрес объекта:', self.address_input)

        self.client_name_input = QLineEdit()
        self.client_name_input.setPlaceholderText('ФИО или название организации')
        self.client_name_input.setStyleSheet(input_style)
        form_layout.addRow('Клиент:', self.client_name_input)

        # Чекбокс для включения поиска по дате
        from PyQt5.QtWidgets import QCheckBox
        self.use_date_filter = QCheckBox('Искать по дате заключения')
        form_layout.addRow(self.use_date_filter)

        date_group = QGroupBox('Период дат')
        date_layout = QHBoxLayout()

        date_style = CALENDAR_STYLE + """
            QDateEdit {
            }
        """

        self.date_from = CustomDateEdit()
        self.date_from.setCalendarPopup(True)
        add_today_button_to_dateedit(self.date_from)
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_from.setDisplayFormat('dd.MM.yyyy')
        self.date_from.setStyleSheet(date_style)
        self.date_from.setEnabled(False)  # По умолчанию отключено

        self.date_to = CustomDateEdit()
        self.date_to.setCalendarPopup(True)
        add_today_button_to_dateedit(self.date_to)
        self.date_to.setDate(QDate.currentDate())
        self.date_to.setDisplayFormat('dd.MM.yyyy')
        self.date_to.setStyleSheet(date_style)
        self.date_to.setEnabled(False)  # По умолчанию отключено

        # Подключаем чекбокс к включению/выключению полей дат
        self.use_date_filter.toggled.connect(lambda checked: self.date_from.setEnabled(checked))
        self.use_date_filter.toggled.connect(lambda checked: self.date_to.setEnabled(checked))

        date_layout.addWidget(QLabel('С:'))
        date_layout.addWidget(self.date_from)
        date_layout.addWidget(QLabel('По:'))
        date_layout.addWidget(self.date_to)

        date_group.setLayout(date_layout)
        form_layout.addRow(date_group)
        
        layout.addLayout(form_layout)
        
        # ========== КНОПКИ (SVG) ==========
        buttons_layout = QHBoxLayout()
        
        search_btn = IconLoader.create_icon_button('search2', 'Найти', 'Выполнить поиск', icon_size=16)
        search_btn.setFixedHeight(36)
        search_btn.clicked.connect(self.accept)
        search_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        ''')

        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить фильтры', icon_size=16)
        reset_btn.setFixedHeight(36)
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setStyleSheet('''
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        ''')

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet('''
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        ''')
        
        buttons_layout.addWidget(search_btn)
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setFixedWidth(500)
    
    def reset_filters(self):
        """Сброс всех фильтров"""
        self.contract_number_input.clear()
        self.address_input.clear()
        self.client_name_input.clear()
        self.date_from.setDate(QDate.currentDate().addYears(-1))
        self.date_to.setDate(QDate.currentDate())

        self.parent().load_contracts()

        # Закрываем диалог после сброса (без отдельного сообщения)
        self.reject()
    
    def get_search_params(self):
        """Получение параметров поиска"""
        params = {
            'contract_number': self.contract_number_input.text().strip(),
            'address': self.address_input.text().strip(),
            'client_name': self.client_name_input.text().strip()
        }

        # Добавляем даты только если чекбокс включен
        if self.use_date_filter.isChecked():
            params['date_from'] = self.date_from.date()
            params['date_to'] = self.date_to.date()

        return params
    
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)


# ========== ДИАЛОГ УПРАВЛЕНИЯ АГЕНТАМИ ==========
class AgentDialog(QDialog):
    """Диалог добавления/редактирования агентов с выбором цвета"""

    def __init__(self, parent):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        title_bar = CustomTitleBar(self, 'Управление агентами', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Список существующих агентов
        agents_label = QLabel('Существующие агенты:')
        agents_label.setStyleSheet('font-weight: bold; font-size: 12px;')
        layout.addWidget(agents_label)

        agents = self.db.get_all_agents()
        for agent in agents:
            agent_frame = QFrame()
            agent_frame.setStyleSheet(f'''
                QFrame {{
                    background-color: {agent['color']};
                    border: 2px solid {agent['color']};
                    border-radius: 6px;
                    padding: 8px;
                    margin: 4px 0;
                }}
            ''')

            agent_layout = QHBoxLayout()
            agent_layout.setContentsMargins(4, 4, 4, 4)

            agent_name = QLabel(agent['name'])
            agent_name.setStyleSheet('font-weight: bold; font-size: 12px; color: white;')
            agent_layout.addWidget(agent_name)

            agent_layout.addStretch()

            edit_btn = QPushButton('Изменить цвет')
            edit_btn.setStyleSheet('''
                QPushButton {
                    background-color: white;
                    color: #333;
                    padding: 4px 12px;
                    border-radius: 6px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #F0F0F0; }
            ''')
            edit_btn.clicked.connect(lambda checked, n=agent['name']: self.edit_agent_color(n))
            agent_layout.addWidget(edit_btn)

            agent_frame.setLayout(agent_layout)
            layout.addWidget(agent_frame)

        # Форма добавления нового агента
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet('background-color: #E0E0E0; margin: 10px 0;')
        layout.addWidget(separator)

        new_agent_label = QLabel('Добавить нового агента:')
        new_agent_label.setStyleSheet('font-weight: bold; font-size: 12px;')
        layout.addWidget(new_agent_label)

        form_layout = QFormLayout()

        self.agent_name_input = QLineEdit()
        self.agent_name_input.setPlaceholderText('Название агента')
        form_layout.addRow('Название:', self.agent_name_input)

        color_layout = QHBoxLayout()
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(40, 25)
        self.color_preview.setStyleSheet('background-color: #ffd93c; border: 1px solid #d9d9d9; border-radius: 6px;')
        self.selected_color = '#ffd93c'
        color_layout.addWidget(self.color_preview)

        choose_color_btn = QPushButton('Выбрать цвет')
        choose_color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(choose_color_btn)
        color_layout.addStretch()

        form_layout.addRow('Цвет:', color_layout)

        layout.addLayout(form_layout)

        add_btn = QPushButton('Добавить агента')
        add_btn.setFixedHeight(36)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        add_btn.clicked.connect(self.add_new_agent)
        layout.addWidget(add_btn)

        close_btn = QPushButton('Закрыть')
        close_btn.setFixedHeight(36)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setMinimumWidth(450)

    def choose_color(self):
        """Выбор цвета"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            self.selected_color = color.name()
            self.color_preview.setStyleSheet(f'background-color: {self.selected_color}; border: 1px solid #CCC; border-radius: 6px;')

    def add_new_agent(self):
        """Добавление нового агента"""
        name = self.agent_name_input.text().strip()
        if not name:
            CustomMessageBox(self, 'Ошибка', 'Введите название агента', 'warning').exec_()
            return

        if self.db.add_agent(name, self.selected_color):
            CustomMessageBox(self, 'Успех', f'Агент "{name}" добавлен', 'success').exec_()
            self.accept()
        else:
            CustomMessageBox(self, 'Ошибка', 'Не удалось добавить агента', 'error').exec_()

    def edit_agent_color(self, agent_name):
        """Редактирование цвета агента"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            if self.db.update_agent_color(agent_name, color.name()):
                CustomMessageBox(self, 'Успех', f'Цвет агента "{agent_name}" обновлен', 'success').exec_()
                # Обновляем диалог
                self.close()
                new_dialog = AgentDialog(self.parent())
                new_dialog.exec_()
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось обновить цвет', 'error').exec_()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 3 + screen.top()
        self.move(x, y)
