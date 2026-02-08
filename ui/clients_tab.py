# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QLabel, QMessageBox, QGroupBox,
                             QHeaderView, QDateEdit, QFrame, QTextEdit, QSpinBox, QMenu, QApplication)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate, QSize, QTimer
from database.db_manager import DatabaseManager
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
from utils.table_settings import TableSettings, ProportionalResizeTable
from utils.data_access import DataAccess

class ClientsTab(QWidget):
    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.api_client = api_client
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db  # обратная совместимость для raw SQL
        self.table_settings = TableSettings()
        self.init_ui()
        # ОПТИМИЗАЦИЯ: Первая загрузка из локальной БД (мгновенно)
        self.data.prefer_local = True
        QTimer.singleShot(0, self._initial_load)
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(0, 5, 0, 5)

        # Заголовок и кнопки
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        title = QLabel('Управление клиентами')
        title.setStyleSheet('font-size: 13px; font-weight: bold; color: #333333;')
        header_layout.addWidget(title)
        header_layout.addStretch()

        # ========== КНОПКА ПОИСКА (SVG) ==========
        search_btn = IconLoader.create_icon_button('search', 'Поиск', 'Поиск клиентов', icon_size=12)
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
                background-color: #f5f5f5;
                border-color: #ffd93c;
            }
        ''')
        header_layout.addWidget(search_btn)
        # =========================================

        # ========== КНОПКА СБРОСА ФИЛЬТРОВ (SVG) ==========
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить фильтры и показать всех клиентов', icon_size=12)
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
                background-color: #FFF3E0;
                border-color: #FF9800;
            }
        ''')
        header_layout.addWidget(reset_btn)
        # ================================================

        # ========== КНОПКА ОБНОВЛЕНИЯ ДАННЫХ ==========
        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить БД', 'Обновить данные с сервера', icon_size=12)
        refresh_btn.clicked.connect(self.load_clients)
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
        add_btn = IconLoader.create_icon_button('add', 'Добавить клиента', 'Добавить нового клиента', icon_size=12)
        add_btn.clicked.connect(self.add_client)
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
        
        # Таблица клиентов - используем ProportionalResizeTable для растягивания + ручного изменения
        self.clients_table = ProportionalResizeTable()
        self.clients_table.setStyleSheet("""
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
        self.clients_table.setColumnCount(7)
        self.clients_table.setHorizontalHeaderLabels([
            ' ID ', ' Тип ', ' ФИО/Название ', ' Телефон ', ' Email ', ' ИНН ', ' Действия '
        ])

        # Настройка пропорционального изменения размера:
        # - Колонки 0-5 растягиваются пропорционально И можно менять вручную
        # - Колонка 6 (Действия) фиксирована 110px
        self.clients_table.setup_proportional_resize(
            column_ratios=[0.08, 0.12, 0.25, 0.18, 0.20, 0.17],  # Пропорции для колонок 0-5
            fixed_columns={6: 110},  # Действия = 110px фиксированно
            min_width=50
        )

        # Запрещаем изменение высоты строк
        self.clients_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.clients_table.verticalHeader().setDefaultSectionSize(34)

        self.clients_table.setSortingEnabled(True)
        # Разрешаем выделение отдельных ячеек для копирования
        self.clients_table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.clients_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.clients_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.clients_table.setAlternatingRowColors(True)

        # Добавляем контекстное меню для копирования
        self.clients_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.clients_table.customContextMenuRequested.connect(self.show_context_menu)

        # Подключаем обработчик сортировки для сохранения настроек
        self.clients_table.horizontalHeader().sectionClicked.connect(self.on_sort_changed)
        
        layout.addWidget(self.clients_table)
        
        self.setLayout(layout)

    def create_action_buttons(self, client):
        """Создание кнопок действий для строки таблицы"""
        actions_widget = QWidget()
        actions_layout = QHBoxLayout()
        actions_layout.setContentsMargins(2, 0, 2, 0)
        actions_layout.setSpacing(1)

        # Кнопка Просмотр
        view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=12)
        view_btn.setFixedSize(20, 20)
        view_btn.setStyleSheet('''
            QPushButton {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
            }
        ''')
        view_btn.clicked.connect(lambda: self.view_client(client))
        actions_layout.addWidget(view_btn)

        # Кнопка Редактировать
        edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=12)
        edit_btn.setFixedSize(20, 20)
        edit_btn.setStyleSheet('''
            QPushButton {
                background-color: #FFF3E0;
                border: 1px solid #FFE0B2;
                border-radius: 4px;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #FF9800;
            }
        ''')
        edit_btn.clicked.connect(lambda: self.edit_client(client))
        actions_layout.addWidget(edit_btn)

        # Кнопка Удалить
        delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить', icon_size=12)
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
        delete_btn.clicked.connect(lambda: self.delete_client(client['id']))
        actions_layout.addWidget(delete_btn)

        actions_widget.setLayout(actions_layout)

        return actions_widget

    def populate_table_row(self, row, client):
        """Заполнение строки таблицы данными клиента"""
        self.clients_table.setRowHeight(row, 34)
        self.clients_table.setItem(row, 0, QTableWidgetItem(str(client['id'])))
        self.clients_table.setItem(row, 1, QTableWidgetItem(client['client_type']))
        
        name = (client['full_name'] if client['client_type'] == 'Физическое лицо' 
                else client['organization_name'])
        self.clients_table.setItem(row, 2, QTableWidgetItem(name or ''))
        
        self.clients_table.setItem(row, 3, QTableWidgetItem(client['phone']))
        self.clients_table.setItem(row, 4, QTableWidgetItem(client.get('email', '')))
        self.clients_table.setItem(row, 5, QTableWidgetItem(client.get('inn', '')))
        
        self.clients_table.setCellWidget(row, 6, self.create_action_buttons(client))
            
    def _initial_load(self):
        """Первая загрузка из локальной БД (мгновенно)"""
        self.load_clients()
        self.data.prefer_local = False

    def load_clients(self):
        """Загрузка списка клиентов"""
        print("[DB REFRESH] Начало обновления данных клиентов...")
        try:
            self.clients_table.setSortingEnabled(False)

            clients = self.data.get_all_clients()
            print(f"[DB REFRESH] Загружено {len(clients)} клиентов")

            self.clients_table.setRowCount(len(clients))

            for row, client in enumerate(clients):
                self.populate_table_row(row, client)

            self.clients_table.setSortingEnabled(True)

            # Восстанавливаем сохраненную сортировку
            column, order = self.table_settings.get_sort_order('clients')
            if column is not None and order is not None:
                from PyQt5.QtCore import Qt as QtCore
                sort_order = QtCore.AscendingOrder if order == 0 else QtCore.DescendingOrder
                self.clients_table.sortItems(column, sort_order)
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось загрузить клиентов: {e}', 'error').exec_()
        
    def add_client(self):
        """Открытие диалога добавления клиента"""
        dialog = ClientDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_clients()

    def view_client(self, client_data):
        """Просмотр информации о клиенте"""
        dialog = ClientDialog(self, client_data, view_only=True)
        dialog.exec_()

    def edit_client(self, client_data):
        """Редактирование клиента"""
        dialog = ClientDialog(self, client_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_clients()
    
    def delete_client(self, client_id):
        """Удаление клиента"""
        from ui.custom_message_box import CustomQuestionBox

        # Проверяем наличие связанных договоров
        try:
            contracts_count = self.data.get_contracts_count_by_client(client_id)
            if contracts_count > 0:
                CustomMessageBox(
                    self,
                    'Невозможно удалить',
                    f'У клиента есть {contracts_count} связанных договоров.\n'
                    f'Сначала удалите или переназначьте договоры.',
                    'error'
                ).exec_()
                return
        except Exception as e:
            print(f"[WARN] Ошибка проверки связанных договоров: {e}")

        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить этого клиента?'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                self.data.delete_client(client_id)
                self.load_clients()
                CustomMessageBox(self, 'Успех', 'Клиент удален', 'success').exec_()
            except Exception as e:
                print(f"[ERROR] Ошибка удаления клиента: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить клиента: {e}', 'error').exec_()

    def show_context_menu(self, position):
        """Контекстное меню для копирования текста из ячеек"""
        menu = QMenu()

        copy_action = menu.addAction("Копировать")
        copy_action.triggered.connect(self.copy_selected_cells)

        menu.exec_(self.clients_table.viewport().mapToGlobal(position))

    def copy_selected_cells(self):
        """Копирование выделенных ячеек в буфер обмена"""
        selection = self.clients_table.selectedItems()
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
        order = self.clients_table.horizontalHeader().sortIndicatorOrder()
        # Сохраняем настройки (0 = по возрастанию, 1 = по убыванию)
        self.table_settings.save_sort_order('clients', column, order)
            
    def open_search(self):
        """Открытие диалога поиска клиентов"""
        dialog = ClientSearchDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            search_params = dialog.get_search_params()
            self.apply_search(search_params)

    def reset_filters(self):
        """Сброс всех фильтров и перезагрузка всех клиентов"""
        self.load_clients()

    def apply_search(self, params):
        """Применение фильтров поиска"""
        self.clients_table.setSortingEnabled(False)

        clients = self.data.get_all_clients()

        filtered_clients = []
        for client in clients:
            if params.get('name'):
                name = client.get('full_name') or client.get('organization_name') or ''
                if params['name'].lower() not in name.lower():
                    continue
            
            if params.get('phone'):
                if params['phone'] not in client.get('phone', ''):
                    continue
            
            if params.get('email'):
                if params['email'].lower() not in client.get('email', '').lower():
                    continue
            
            if params.get('inn'):
                if params['inn'] not in client.get('inn', ''):
                    continue
            
            filtered_clients.append(client)
        
        self.clients_table.setRowCount(len(filtered_clients))
        
        for row, client in enumerate(filtered_clients):
            self.populate_table_row(row, client)
        
        # ========== ЗАМЕНИЛИ QMessageBox на CustomMessageBox ==========
        CustomMessageBox(
            self, 
            'Результаты поиска', 
            f'Найдено клиентов: {len(filtered_clients)}', 
            'info'
        ).exec_()

    def on_sync_update(self, updated_clients):
        """
        Обработчик обновления данных от SyncManager.
        Вызывается при изменении клиентов другими пользователями.
        """
        try:
            print(f"[SYNC] Получено обновление клиентов: {len(updated_clients)} записей")
            # Перезагружаем таблицу клиентов
            self.load_clients()
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации клиентов: {e}")
            import traceback
            traceback.print_exc()

class ClientDialog(QDialog):
    def __init__(self, parent, client_data=None, view_only=False):
        super().__init__(parent)
        self.client_data = client_data
        self.view_only = view_only
        self.data = getattr(parent, 'data', DataAccess())
        self.db = self.data.db
        self.api_client = self.data.api_client

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

        if client_data:
            self.fill_data()
    
    def init_ui(self):
        if self.view_only:
            title = 'Просмотр клиента'
        else:
            title = 'Добавление клиента' if not self.client_data else 'Редактирование клиента'
        
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
        
        # Тип клиента
        type_group = QGroupBox('Тип клиента')
        type_layout = QFormLayout()
        
        self.client_type = CustomComboBox()
        self.client_type.addItems(['Физическое лицо', 'Юридическое лицо'])
        self.client_type.currentTextChanged.connect(self.on_type_changed)
        type_layout.addRow('Тип:', self.client_type)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # Группа для физического лица
        self.individual_group = QGroupBox('Данные физического лица')
        individual_layout = QFormLayout()
        
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText('Иванов Иван Иванович')

        individual_layout.addRow('ФИО*:', self.full_name)

        self.phone = QLineEdit()
        self.phone.setPlaceholderText('+7 (999) 123-45-67')
        # ИСПРАВЛЕНИЕ: Убираем InputMask, используем кастомное форматирование
        # ИСПРАВЛЕНИЕ: Тонкий курсор через CSS
        self.phone.setStyleSheet("""
            QLineEdit {
                caret-width: 1px;
            }
        """)
        # Не устанавливаем начальное значение, чтобы сохранить placeholder
        self.phone.textChanged.connect(lambda: self.format_phone_input(self.phone))
        self.phone.focusInEvent = lambda e: self.on_phone_focus_in(self.phone, e)
        individual_layout.addRow('Телефон*:', self.phone)
        
        self.email = QLineEdit()
        self.email.setPlaceholderText('example@mail.com')

        individual_layout.addRow('Email:', self.email)
        
        passport_layout = QHBoxLayout()
        
        self.passport_series = QLineEdit()
        self.passport_series.setPlaceholderText('0000')
        self.passport_series.setMaxLength(4)
        self.passport_series.textChanged.connect(lambda: self.format_digits_only(self.passport_series))

        self.passport_number = QLineEdit()
        self.passport_number.setPlaceholderText('000 000')
        self.passport_number.setMaxLength(7)
        self.passport_number.textChanged.connect(self.format_passport_number)
        
        passport_layout.addWidget(QLabel('Серия:'))
        passport_layout.addWidget(self.passport_series)
        passport_layout.addWidget(QLabel('Номер:'))
        passport_layout.addWidget(self.passport_number)
        individual_layout.addRow('Паспорт:', passport_layout)
        
        self.passport_issued_by = QTextEdit()
        self.passport_issued_by.setPlaceholderText('МВД России по г. Москва')
        self.passport_issued_by.setStyleSheet('''
            QTextEdit {
                padding: 2px 8px;
                min-height: 50px;
                max-height: 50px;
            }
        ''')        
        individual_layout.addRow('Кем выдан:', self.passport_issued_by)
        
        self.passport_issued_date = CustomDateEdit()
        self.passport_issued_date.setCalendarPopup(True)
        add_today_button_to_dateedit(self.passport_issued_date)
        self.passport_issued_date.setDate(QDate.currentDate())
        self.passport_issued_date.setDisplayFormat('dd.MM.yyyy')

        individual_layout.addRow('Дата выдачи:', self.passport_issued_date)
        
        self.registration_address = QTextEdit()
        self.registration_address.setPlaceholderText('г. Москва, ул. Ленина, д.10, кв.5')
        self.registration_address.setStyleSheet('''
            QTextEdit {
                padding: 2px 8px;
                min-height: 50px;
                max-height: 50px;
            }
        ''') 
        individual_layout.addRow('Адрес прописки:', self.registration_address)
        
        self.individual_group.setLayout(individual_layout)
        layout.addWidget(self.individual_group)
        
        # Группа для юридического лица
        self.legal_group = QGroupBox('Данные юридического лица')
        legal_layout = QFormLayout()
        
        self.org_type = CustomComboBox()
        self.org_type.addItems(['ИП', 'ООО', 'ОАО'])
        legal_layout.addRow('Тип организации:', self.org_type)
        
        self.org_name = QLineEdit()
        self.org_name.setPlaceholderText('ООО "Название"')

        legal_layout.addRow('Название*:', self.org_name)

        self.inn = QLineEdit()
        self.inn.setPlaceholderText('1234567890')

        legal_layout.addRow('ИНН:', self.inn)

        self.ogrn = QLineEdit()

        legal_layout.addRow('ОГРН:', self.ogrn)
        
        self.account_details = QTextEdit()
        self.account_details.setPlaceholderText('Р/С: 40702810..., БИК: 044525225, Банк: ПАО Сбербанк')
        self.account_details.setStyleSheet('''
            QTextEdit {
                padding: 2px 8px;
                min-height: 100px;
                max-height: 100px;
            }
        ''')
        legal_layout.addRow('Реквизиты счета:', self.account_details)
        
        self.responsible_person = QLineEdit()

        legal_layout.addRow('Ответственное лицо:', self.responsible_person)

        self.org_phone = QLineEdit()
        self.org_phone.setPlaceholderText('+7 (999) 123-45-67')
        # ИСПРАВЛЕНИЕ: Убираем InputMask, используем кастомное форматирование
        # ИСПРАВЛЕНИЕ: Было self.phone.setInputMask (ошибка!), исправлено на self.org_phone
        # ИСПРАВЛЕНИЕ: Тонкий курсор через CSS
        self.org_phone.setStyleSheet("""
            QLineEdit {
                caret-width: 1px;
            }
        """)
        # Не устанавливаем начальное значение, чтобы сохранить placeholder
        self.org_phone.textChanged.connect(lambda: self.format_phone_input(self.org_phone))
        self.org_phone.focusInEvent = lambda e: self.on_phone_focus_in(self.org_phone, e)
        legal_layout.addRow('Телефон*:', self.org_phone)
        
        self.org_email = QLineEdit()

        legal_layout.addRow('Email:', self.org_email)
        
        self.legal_group.setLayout(legal_layout)
        layout.addWidget(self.legal_group)

        # Кнопки
        if not self.view_only:
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()

            save_btn = QPushButton('Сохранить')
            save_btn.setFixedHeight(36)
            save_btn.clicked.connect(self.save_client)
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

            cancel_btn = QPushButton('Отмена')
            cancel_btn.setFixedHeight(36)
            cancel_btn.clicked.connect(self.reject)
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

            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)

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
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
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
                child.setStyleSheet('QDateEdit:disabled { background-color: #F0F0F0; }')  # Серый фон
        # ==========================================================

        self.on_type_changed('Физическое лицо')

        # ========== ИСПРАВЛЕНИЕ: ФИКСИРОВАННАЯ ШИРИНА БЕЗ adjustSize() ==========
        self.setFixedWidth(650)
        # ========================================================================

    def showEvent(self, event):
        """Центрируем диалог при показе (когда размеры уже правильно установлены)"""
        super().showEvent(event)
        # Центрируем только при первом показе
        if not hasattr(self, '_centered'):
            from utils.dialog_helpers import center_dialog_on_parent
            center_dialog_on_parent(self)
            self._centered = True

    def format_phone_number(self, line_edit):
        """Универсальное форматирование телефона"""
        line_edit.blockSignals(True)
        
        digits = ''.join(filter(str.isdigit, line_edit.text()))
        
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        
        if len(digits) == 0:
            formatted = ''
        elif len(digits) <= 1:
            formatted = '+' + digits
        elif len(digits) <= 4:
            formatted = f'+{digits[0]} ({digits[1:]}'
        elif len(digits) <= 7:
            formatted = f'+{digits[0]} ({digits[1:4]}) {digits[4:]}'
        elif len(digits) <= 9:
            formatted = f'+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}'
        else:
            formatted = f'+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}'
        
        cursor_pos = line_edit.cursorPosition()
        line_edit.setText(formatted)
        line_edit.setCursorPosition(min(cursor_pos, len(formatted)))
        
        line_edit.blockSignals(False)
    
    def format_passport_number(self, text):
        """Форматирование номера паспорта: 000 000"""
        self.passport_number.blockSignals(True)
        
        digits = ''.join(filter(str.isdigit, text))
        
        if len(digits) <= 3:
            formatted = digits
        else:
            formatted = f'{digits[:3]} {digits[3:6]}'
        
        self.passport_number.setText(formatted)
        
        self.passport_number.blockSignals(False)
    
    def format_digits_only(self, line_edit):
        """Оставляем только цифры"""
        line_edit.blockSignals(True)
        text = line_edit.text()
        digits = ''.join(filter(str.isdigit, text))
        line_edit.setText(digits)
        line_edit.blockSignals(False)

    def format_phone_input(self, line_edit):
        """
        Форматирование телефона с фиксированным префиксом +7 (
        Автоматическое добавление пробелов, скобок и тире
        """
        line_edit.blockSignals(True)

        text = line_edit.text()
        cursor_pos = line_edit.cursorPosition()

        # Если поле пустое, оставляем пустым (для placeholder)
        if not text:
            line_edit.blockSignals(False)
            return

        # Извлекаем только цифры
        digits = ''.join(filter(str.isdigit, text))

        # Если нет цифр, очищаем поле
        if not digits:
            line_edit.setText('')
            line_edit.blockSignals(False)
            return

        # Подсчитываем сколько цифр было до курсора (для правильного позиционирования)
        digits_before_cursor = len(''.join(filter(str.isdigit, text[:cursor_pos])))

        # Убираем первую 7 или 8, если пользователь её ввёл
        if digits.startswith('7') or digits.startswith('8'):
            digits = digits[1:]

        # Ограничиваем 10 цифрами (код города + номер)
        digits = digits[:10]

        # Форматируем номер: +7 (XXX) XXX-XX-XX
        if len(digits) == 0:
            formatted = '+7 ('
            new_cursor_pos = 4
        elif len(digits) <= 3:
            formatted = f'+7 ({digits}'
            new_cursor_pos = 4 + len(digits)
        elif len(digits) <= 6:
            formatted = f'+7 ({digits[:3]}) {digits[3:]}'
            # Пересчитываем позицию курсора
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            else:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
        elif len(digits) <= 8:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}'
            # Пересчитываем позицию курсора
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            else:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
        else:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}'
            # Пересчитываем позицию курсора
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            elif digits_before_cursor <= 8:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
            else:
                new_cursor_pos = 16 + (digits_before_cursor - 8)

        line_edit.setText(formatted)
        line_edit.setCursorPosition(min(new_cursor_pos, len(formatted)))

        line_edit.blockSignals(False)

    def on_phone_focus_in(self, line_edit, event):
        """
        При фокусе на поле телефона начинаем с префикса +7 (
        """
        from PyQt5.QtWidgets import QLineEdit
        QLineEdit.focusInEvent(line_edit, event)

        # Если поле пустое, добавляем префикс
        if not line_edit.text():
            line_edit.blockSignals(True)
            line_edit.setText('+7 (')
            line_edit.setCursorPosition(4)
            line_edit.blockSignals(False)
    
    def on_type_changed(self, client_type):
        """Переключение между типами клиентов"""
        if client_type == 'Физическое лицо':
            self.individual_group.setVisible(True)
            self.legal_group.setVisible(False)
        else:
            self.individual_group.setVisible(False)
            self.legal_group.setVisible(True)

        # ИСПРАВЛЕНИЕ: Разрешаем окну менять размер
        self.setMinimumHeight(0)  # Убираем минимальную высоту
        self.setMaximumHeight(16777215)  # Убираем максимальную высоту (стандартное значение Qt)

        # Пересчитываем размер окна после переключения
        self.adjustSize()

        # Фиксируем только ширину, высота подстраивается автоматически
        self.setFixedWidth(650)
            
    def fill_data(self):
        """Заполнение формы данными клиента"""
        self.client_type.setCurrentText(self.client_data['client_type'])

        if self.client_data['client_type'] == 'Физическое лицо':
            self.full_name.setText(self.client_data.get('full_name', ''))
            # ИСПРАВЛЕНИЕ: Блокируем сигналы при загрузке данных
            self.phone.blockSignals(True)
            phone_number = self.client_data.get('phone', '')
            # Если номер есть - показываем, если нет - оставляем пустым (будет placeholder)
            self.phone.setText(phone_number if phone_number else '')
            self.phone.blockSignals(False)
            self.email.setText(self.client_data.get('email', ''))
            self.passport_series.setText(self.client_data.get('passport_series', ''))
            self.passport_number.setText(self.client_data.get('passport_number', ''))
            self.passport_issued_by.setPlainText(self.client_data.get('passport_issued_by', ''))
            self.registration_address.setPlainText(self.client_data.get('registration_address', ''))
        else:
            self.org_type.setCurrentText(self.client_data.get('organization_type', 'ООО'))
            self.org_name.setText(self.client_data.get('organization_name', ''))
            self.inn.setText(self.client_data.get('inn', ''))
            self.ogrn.setText(self.client_data.get('ogrn', ''))
            self.account_details.setPlainText(self.client_data.get('account_details', ''))
            self.responsible_person.setText(self.client_data.get('responsible_person', ''))
            # ИСПРАВЛЕНИЕ: Блокируем сигналы при загрузке данных
            self.org_phone.blockSignals(True)
            phone_number = self.client_data.get('phone', '')
            # Если номер есть - показываем, если нет - оставляем пустым (будет placeholder)
            self.org_phone.setText(phone_number if phone_number else '')
            self.org_phone.blockSignals(False)
            self.org_email.setText(self.client_data.get('email', ''))

    def save_client(self):
        """Сохранение данных клиента"""
        client_type = self.client_type.currentText()

        if client_type == 'Физическое лицо':
            if not self.full_name.text().strip() or not self.phone.text().strip():
                # ========== ЗАМЕНИЛИ QMessageBox ==========
                CustomMessageBox(
                    self,
                    'Ошибка',
                    'Заполните все обязательные поля (ФИО, Телефон)',
                    'warning'
                ).exec_()
                return

            client_data = {
                'client_type': client_type,
                'full_name': self.full_name.text().strip(),
                'phone': self.phone.text().strip(),
                'email': self.email.text().strip(),
                'passport_series': self.passport_series.text().strip(),
                'passport_number': self.passport_number.text().strip(),
                'passport_issued_by': self.passport_issued_by.toPlainText().strip(),
                'passport_issued_date': self.passport_issued_date.date().toString('yyyy-MM-dd'),
                'registration_address': self.registration_address.toPlainText().strip()
            }
        else:
            if not self.org_name.text().strip() or not self.org_phone.text().strip():
                # ========== ЗАМЕНИЛИ QMessageBox ==========
                CustomMessageBox(
                    self,
                    'Ошибка',
                    'Заполните все обязательные поля (Название, Телефон)',
                    'warning'
                ).exec_()
                return

            client_data = {
                'client_type': client_type,
                'organization_type': self.org_type.currentText(),
                'organization_name': self.org_name.text().strip(),
                'inn': self.inn.text().strip(),
                'ogrn': self.ogrn.text().strip(),
                'account_details': self.account_details.toPlainText().strip(),
                'responsible_person': self.responsible_person.text().strip(),
                'phone': self.org_phone.text().strip(),
                'email': self.org_email.text().strip()
            }

        try:
            if self.client_data:
                self.data.update_client(self.client_data['id'], client_data)
            else:
                self.data.create_client(client_data)
            self.accept()
        except Exception as e:
            CustomMessageBox(
                self,
                'Ошибка',
                f'Не удалось сохранить клиента: {e}',
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
        
class ClientSearchDialog(QDialog):
    """Диалог поиска клиентов"""
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
        title_bar = CustomTitleBar(self, 'Поиск клиентов', simple_mode=True)
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
            QWidget#dialogContent {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()

        # Стили для полей ввода (уменьшаем высоту на 30%)
        input_style = """
            QLineEdit {
            }
        """

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Введите имя или название организации')
        self.name_input.setStyleSheet(input_style)
        form_layout.addRow('Имя/Название:', self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText('+7 (999) 123-45-67')
        # Тонкий курсор через CSS
        self.phone_input.setStyleSheet(input_style + """
            QLineEdit {
                caret-width: 1px;
            }
        """)
        # Подключаем форматирование телефона
        self.phone_input.textChanged.connect(lambda: self.format_phone_input(self.phone_input))
        self.phone_input.focusInEvent = lambda e: self.on_phone_focus_in(self.phone_input, e)
        form_layout.addRow('Телефон:', self.phone_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('example@mail.com')
        self.email_input.setStyleSheet(input_style)
        form_layout.addRow('Email:', self.email_input)

        self.inn_input = QLineEdit()
        self.inn_input.setPlaceholderText('1234567890')
        self.inn_input.setStyleSheet(input_style)
        form_layout.addRow('ИНН:', self.inn_input)
        
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
        """Сброс всех фильтров и перезагрузка"""
        self.name_input.clear()
        self.phone_input.clear()
        self.email_input.clear()
        self.inn_input.clear()

        self.parent().load_clients()

        # Закрываем диалог после сброса (без отдельного сообщения)
        self.reject()
    
    def get_search_params(self):
        """Получение параметров поиска"""
        return {
            'name': self.name_input.text().strip(),
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'inn': self.inn_input.text().strip()
        }

    def format_phone_input(self, line_edit):
        """
        Форматирование телефона с фиксированным префиксом +7 (
        Автоматическое добавление пробелов, скобок и тире
        """
        line_edit.blockSignals(True)

        text = line_edit.text()
        cursor_pos = line_edit.cursorPosition()

        # Если поле пустое, оставляем пустым (для placeholder)
        if not text:
            line_edit.blockSignals(False)
            return

        # Извлекаем только цифры
        digits = ''.join(filter(str.isdigit, text))

        # Если нет цифр, очищаем поле
        if not digits:
            line_edit.setText('')
            line_edit.blockSignals(False)
            return

        # Подсчитываем сколько цифр было до курсора (для правильного позиционирования)
        digits_before_cursor = len(''.join(filter(str.isdigit, text[:cursor_pos])))

        # Убираем первую 7 или 8, если пользователь её ввёл
        if digits.startswith('7') or digits.startswith('8'):
            digits = digits[1:]

        # Ограничиваем 10 цифрами (код города + номер)
        digits = digits[:10]

        # Форматируем номер: +7 (XXX) XXX-XX-XX
        if len(digits) == 0:
            formatted = '+7 ('
            new_cursor_pos = 4
        elif len(digits) <= 3:
            formatted = f'+7 ({digits}'
            new_cursor_pos = 4 + len(digits)
        elif len(digits) <= 6:
            formatted = f'+7 ({digits[:3]}) {digits[3:]}'
            # Пересчитываем позицию курсора
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            else:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
        elif len(digits) <= 8:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}'
            # Пересчитываем позицию курсора
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            else:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
        else:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}'
            # Пересчитываем позицию курсора
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            elif digits_before_cursor <= 8:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
            else:
                new_cursor_pos = 16 + (digits_before_cursor - 8)

        line_edit.setText(formatted)
        line_edit.setCursorPosition(min(new_cursor_pos, len(formatted)))

        line_edit.blockSignals(False)

    def on_phone_focus_in(self, line_edit, event):
        """
        При фокусе на поле телефона начинаем с префикса +7 (
        """
        from PyQt5.QtWidgets import QLineEdit
        QLineEdit.focusInEvent(line_edit, event)

        # Если поле пустое, добавляем префикс
        if not line_edit.text():
            line_edit.blockSignals(True)
            line_edit.setText('+7 (')
            line_edit.setCursorPosition(4)
            line_edit.blockSignals(False)

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

