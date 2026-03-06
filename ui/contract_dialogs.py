# -*- coding: utf-8 -*-
"""
Диалоги для работы с договорами.

Вынесено из contracts_tab.py (Phase 5 аудита, задача #47).
Содержит:
  - FormattedMoneyInput   — поле ввода суммы с форматированием
  - FormattedAreaInput    — поле ввода площади с форматированием
  - FormattedPeriodInput  — поле ввода срока (раб. дней)
  - ContractDialog        — диалог создания/редактирования договора
  - ContractSearchDialog  — диалог поиска договоров
  - AgentDialog           — диалог управления агентами
"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QLabel, QMessageBox, QGroupBox,
                             QHeaderView, QDateEdit, QTextEdit, QDoubleSpinBox,
                             QSpinBox, QFrame, QFileDialog, QMenu, QApplication)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate, QSize, pyqtSignal, QTimer
from PyQt5.QtGui import QValidator, QDesktopServices, QCursor
from PyQt5.QtCore import QUrl
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from config import PROJECT_TYPES, PROJECT_SUBTYPES, TEMPLATE_SUBTYPES, AGENTS, YANDEX_DISK_TOKEN
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
from utils.dialog_helpers import create_progress_dialog
from utils.button_debounce import debounce_click
from utils.yandex_disk import YandexDiskManager
from utils.table_settings import TableSettings, ProportionalResizeTable
import json
import os
import threading


# ========== ВСПОМОГАТЕЛЬНЫЕ ВИДЖЕТЫ ВВОДА ==========

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




# ========== ДИАЛОГИ ДОГОВОРОВ ==========

class ContractDialog(QDialog):
    # Сигналы для межпоточного взаимодействия при загрузке файлов
    contract_file_upload_completed = pyqtSignal(str, str, str, str)  # public_link, yandex_path, file_name, project_type
    contract_file_upload_error = pyqtSignal(str)  # error_msg
    tech_task_upload_completed = pyqtSignal(str, str, str)  # public_link, yandex_path, file_name
    tech_task_upload_error = pyqtSignal(str)  # error_msg
    doc_file_upload_completed = pyqtSignal(str, str, str, str)  # field_prefix, public_link, yandex_path, file_name
    doc_file_upload_error = pyqtSignal(str, str)  # field_prefix, error_msg
    files_verification_completed = pyqtSignal()  # Сигнал завершения проверки файлов
    _sync_ended = pyqtSignal()  # Сигнал завершения фоновой синхронизации

    def __init__(self, parent, contract_data=None, view_only=False):
        super().__init__(parent)
        self.contract_data = contract_data
        self.view_only = view_only
        self.data = getattr(parent, 'data', DataAccess())
        self.db = self.data.db
        self.api_client = self.data.api_client
        self._uploading_files = 0  # Счётчик загружаемых файлов
        self.offline_manager = getattr(parent, 'offline_manager', None)

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
        self.doc_file_upload_completed.connect(self._on_doc_file_uploaded)
        self.doc_file_upload_error.connect(self._on_doc_file_upload_error)

        # Синхронизация
        self._active_sync_count = 0
        self._sync_ended.connect(self._on_sync_ended)

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
                border: 1px solid #E0E0E0;
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
        
        # Выбор клиента (без рамки — единственное поле, рамка QComboBox достаточна)
        client_group = QGroupBox('Клиент')
        client_group.setStyleSheet("""
            QGroupBox {
                border: none;
                margin-top: 12px;
                padding-top: 12px;
                background-color: transparent;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 3px 10px;
                color: #000000;
                font-weight: 700;
            }
        """)
        client_layout = QFormLayout()
        client_layout.setSpacing(8)

        self.client_combo = CustomComboBox()
        self.client_combo.setEditable(True)
        self.client_combo.setInsertPolicy(QComboBox.NoInsert)
        # ИСПРАВЛЕНИЕ 07.02.2026: Отступы для текста в dropdown (#7)
        self.client_combo.lineEdit().setStyleSheet("padding-left: 8px; padding-right: 8px;")

        # Загрузка клиентов через DataAccess (API с fallback на локальную БД)
        self.all_clients = self.data.get_all_clients() or []
        for client in self.all_clients:
            name = client['full_name'] if client['client_type'] == 'Физическое лицо' else client['organization_name']
            self.client_combo.addItem(f"{name} ({client['phone']})", client['id'])

        from PyQt5.QtWidgets import QCompleter

        completer = QCompleter([self.client_combo.itemText(i) for i in range(self.client_combo.count())])
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.client_combo.setCompleter(completer)

        # Белый фон для dropdown списка автодополнения
        # border-top: none — убирает двойную рамку при стыке с QComboBox
        completer.popup().setStyleSheet("""
            QAbstractItemView {
                background-color: #ffffff;
                border: 1px solid #E0E0E0;
                border-top: none;
                border-top-left-radius: 0px;
                border-top-right-radius: 0px;
                border-bottom-left-radius: 6px;
                border-bottom-right-radius: 6px;
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

        self.project_subtype = CustomComboBox()
        self.project_subtype.addItems(PROJECT_SUBTYPES)
        self.project_subtype.currentTextChanged.connect(self._on_subtype_or_area_changed)
        main_layout_form.addRow('Подтип проекта*:', self.project_subtype)

        # Кол-во этажей (для шаблонных проектов)
        self.floors_label = QLabel('Кол-во этажей:')
        self.floors_spin = QSpinBox()
        self.floors_spin.setRange(1, 10)
        self.floors_spin.setValue(1)
        self.floors_spin.valueChanged.connect(self._on_subtype_or_area_changed)
        main_layout_form.addRow(self.floors_label, self.floors_spin)
        self.floors_label.hide()
        self.floors_spin.hide()

        self.agent_combo = CustomComboBox()
        self.reload_agents()
        main_layout_form.addRow('Агент:', self.agent_combo)

        self.city_combo = CustomComboBox()
        cities = self.data.get_all_cities() or []
        for city in cities:
            self.city_combo.addItem(city.get('name', ''))
        main_layout_form.addRow('Город:', self.city_combo)

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
        self.area.editingFinished.connect(self._on_subtype_or_area_changed)
        main_layout_form.addRow('Площадь:', self.area)

        self.total_amount = FormattedMoneyInput('Введите сумму')
        main_layout_form.addRow('Сумма договора:', self.total_amount)
        
        main_group.setLayout(main_layout_form)
        layout.addWidget(main_group)
        
        # Дополнительные поля (Индивидуальный)
        self.individual_group = QGroupBox('Дополнительные данные (Индивидуальный проект)')
        individual_layout = QFormLayout()
        individual_layout.setSpacing(8)

        # === Платежи с кнопками Оплачено и Загрузить чек ===
        _payment_fields = [
            ('advance_payment', '1 платёж (Аванс)', '1 платеж (Аванс):'),
            ('additional_payment', '2 платёж (Доплата)', '2 платеж (Доплата):'),
            ('third_payment', '3 платёж (Доплата)', '3 платеж (Доплата):'),
        ]
        _paid_btn_style = '''
            QPushButton { background-color: #ffffff; border: 1px solid #E0E0E0; border-radius: 6px; padding: 0px 4px; }
            QPushButton:hover { background-color: #f5f5f5; }
            QPushButton:disabled { background-color: #f0f0f0; border: 1px solid #e0e0e0; }
        '''
        _receipt_upload_btn_style = '''
            QPushButton { background-color: #ffd93c; color: #333333; border: none; border-radius: 6px; font-size: 11px; padding: 0px 4px; }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:disabled { background-color: #BDC3C7; color: #7F8C8D; }
        '''
        _receipt_delete_btn_style = '''
            QPushButton { background-color: #E74C3C; color: white; border: none; border-radius: 6px; padding: 0px 4px; }
            QPushButton:hover { background-color: #C0392B; }
        '''
        _paid_date_style = '''
            QLabel {
                background-color: #F8F9FA;
                padding: 2px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 11px;
                min-width: 120px;
                min-height: 16px;
            }
        '''
        _paid_date_active_style = '''
            QLabel {
                background-color: #F8F9FA;
                padding: 2px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 11px;
                color: #27AE60;
                font-weight: 600;
                min-width: 120px;
                min-height: 16px;
            }
        '''
        for prefix, placeholder, row_label in _payment_fields:
            payment_row = QHBoxLayout()
            payment_row.setSpacing(6)
            payment_row.setContentsMargins(0, 0, 0, 0)

            # Поле суммы
            money_input = FormattedMoneyInput(placeholder)
            setattr(self, prefix, money_input)
            payment_row.addWidget(money_input, 1)

            # Кнопка «Оплачено»
            paid_btn = QPushButton()
            paid_btn.setIcon(IconLoader.load('money'))
            paid_btn.setIconSize(QSize(14, 14))
            paid_btn.setFixedSize(28, 28)
            paid_btn.setToolTip('Отметить как оплачено')
            paid_btn.setStyleSheet(_paid_btn_style)
            paid_btn.clicked.connect(lambda checked, p=prefix: self._mark_payment_paid(p))
            setattr(self, f'{prefix}_paid_btn', paid_btn)
            payment_row.addWidget(paid_btn, 0)

            # Кнопка «Загрузить чек»
            receipt_btn = IconLoader.create_icon_button('download', '', 'Загрузить чек', icon_size=14)
            receipt_btn.setFixedSize(28, 28)
            receipt_btn.setStyleSheet(_receipt_upload_btn_style)
            receipt_btn.clicked.connect(lambda checked, p=prefix: self._upload_receipt_file(p))
            setattr(self, f'{prefix}_receipt_btn', receipt_btn)
            payment_row.addWidget(receipt_btn, 0)

            # Кнопка просмотра чека
            receipt_view_btn = IconLoader.create_icon_button('eye', '', 'Просмотр чека', icon_size=14)
            receipt_view_btn.setFixedSize(28, 28)
            receipt_view_btn.setStyleSheet(_paid_btn_style)
            receipt_view_btn.setVisible(False)
            receipt_view_btn.clicked.connect(lambda checked, p=prefix: self._view_receipt_file(p))
            setattr(self, f'{prefix}_receipt_view_btn', receipt_view_btn)
            payment_row.addWidget(receipt_view_btn, 0)

            # Кнопка удаления чека
            receipt_del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить чек', icon_size=14)
            receipt_del_btn.setFixedSize(28, 28)
            receipt_del_btn.setStyleSheet(_receipt_delete_btn_style)
            receipt_del_btn.setVisible(False)
            receipt_del_btn.clicked.connect(lambda checked, p=prefix: self._delete_receipt_file(p))
            setattr(self, f'{prefix}_receipt_delete_btn', receipt_del_btn)
            payment_row.addWidget(receipt_del_btn, 0)

            # Лейбл даты оплаты (с рамкой)
            paid_label = QLabel('Платеж не проведен')
            paid_label.setStyleSheet(_paid_date_style)
            paid_label.setFixedHeight(28)
            paid_label.setAlignment(Qt.AlignCenter)
            setattr(self, f'{prefix}_paid_label', paid_label)
            payment_row.addWidget(paid_label, 0)

            individual_layout.addRow(row_label, payment_row)

        period_layout = QHBoxLayout()
        period_layout.setSpacing(8)
        period_layout.setContentsMargins(0, 0, 0, 0)
        self.contract_period = FormattedPeriodInput()
        self.contract_period.setEnabled(False)
        period_layout.addWidget(self.contract_period)

        self.btn_show_term_table = QPushButton('Таблица сроков')
        self.btn_show_term_table.setFixedHeight(28)
        self.btn_show_term_table.setStyleSheet('''
            QPushButton { background-color: #E8F4F8; border: 1px solid #B0D4E8;
                          border-radius: 6px; padding: 2px 10px; font-size: 11px;
                          min-height: 22px; max-height: 22px; }
            QPushButton:hover { background-color: #D0E8F2; }
        ''')
        self.btn_show_term_table.clicked.connect(self._show_term_table_dialog)
        period_layout.addWidget(self.btn_show_term_table)

        self.btn_manual_period = QPushButton('Вручную')
        self.btn_manual_period.setFixedHeight(28)
        self.btn_manual_period.setStyleSheet('''
            QPushButton { background-color: #FFF3CD; border: 1px solid #E0C97A;
                          border-radius: 6px; padding: 2px 10px; font-size: 11px;
                          min-height: 22px; max-height: 22px; }
            QPushButton:hover { background-color: #FFE9A0; }
        ''')
        self.btn_manual_period.clicked.connect(self._enable_manual_period)
        period_layout.addWidget(self.btn_manual_period)

        individual_layout.addRow('Срок договора:', period_layout)

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

        # === Акты: 2 столбца (без подписи | с подписью) ===
        _file_label_style = '''
            QLabel {
                background-color: #F8F9FA;
                padding: 5px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                font-size: 11px;
                min-height: 16px;
            }
            QLabel a { color: #ffd93c; text-decoration: none; }
            QLabel a:hover { color: #2980B9; text-decoration: underline; }
        '''
        _upload_btn_style = '''
            QPushButton { background-color: #ffd93c; color: #333333; border: none; border-radius: 6px; font-size: 11px; padding: 0px 4px; }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:disabled { background-color: #BDC3C7; color: #7F8C8D; }
        '''
        _delete_btn_style = '''
            QPushButton { background-color: #E74C3C; color: white; border: none; border-radius: 6px; padding: 0px 4px; }
            QPushButton:hover { background-color: #C0392B; }
        '''

        # Контейнер для 2 столбцов актов
        acts_container = QHBoxLayout()
        acts_container.setSpacing(10)
        acts_container.setContentsMargins(0, 0, 0, 0)

        # --- Столбец 1: Акты без подписи ---
        unsigned_group = QGroupBox('Акты без подписи')
        unsigned_layout = QFormLayout()
        unsigned_layout.setSpacing(6)

        _act_rows = [
            ('act_planning', 'act_planning_signed', 'Акт ПР:'),
            ('act_concept', 'act_concept_signed', 'Акт КД:'),
            ('info_letter', 'info_letter_signed', 'Инф. письмо:'),
            ('act_final', 'act_final_signed', 'Акт финальный:'),
        ]

        for unsigned_prefix, _, row_label in _act_rows:
            layout_h = QHBoxLayout()
            layout_h.setSpacing(6)

            lbl = QLabel('Не загружен')
            lbl.setStyleSheet(_file_label_style)
            lbl.setWordWrap(False)
            lbl.setFixedHeight(28)
            lbl.setMaximumWidth(200)
            lbl.setOpenExternalLinks(True)
            lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
            lbl.setTextFormat(Qt.RichText)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lbl.setCursor(QCursor(Qt.PointingHandCursor))
            lbl.mousePressEvent = lambda e, p=unsigned_prefix: self._open_doc_file(p)
            setattr(self, f'{unsigned_prefix}_file_label', lbl)
            setattr(self, f'{unsigned_prefix}_file_path', None)

            up_btn = IconLoader.create_icon_button('download', '', 'Загрузить файл', icon_size=14)
            up_btn.setFixedSize(28, 28)
            up_btn.clicked.connect(lambda checked, p=unsigned_prefix, l=row_label: self._upload_doc_file(p, l))
            up_btn.setStyleSheet(_upload_btn_style)
            setattr(self, f'{unsigned_prefix}_upload_btn', up_btn)

            del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
            del_btn.setFixedSize(28, 28)
            del_btn.clicked.connect(lambda checked, p=unsigned_prefix, l=row_label: self._delete_doc_file(p, l))
            del_btn.setStyleSheet(_delete_btn_style)
            del_btn.setVisible(False)
            setattr(self, f'{unsigned_prefix}_file_delete_btn', del_btn)

            layout_h.addWidget(lbl, 1)
            layout_h.addWidget(up_btn, 0)
            layout_h.addWidget(del_btn, 0)
            unsigned_layout.addRow(row_label, layout_h)

        unsigned_group.setLayout(unsigned_layout)
        acts_container.addWidget(unsigned_group, 1)

        # --- Столбец 2: Акты с подписью ---
        signed_group = QGroupBox('Акты с подписью')
        signed_layout = QFormLayout()
        signed_layout.setSpacing(6)

        for _, signed_prefix, row_label in _act_rows:
            layout_h = QHBoxLayout()
            layout_h.setSpacing(6)

            lbl = QLabel('Не загружен')
            lbl.setStyleSheet(_file_label_style)
            lbl.setWordWrap(False)
            lbl.setFixedHeight(28)
            lbl.setMaximumWidth(200)
            lbl.setOpenExternalLinks(True)
            lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
            lbl.setTextFormat(Qt.RichText)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lbl.setCursor(QCursor(Qt.PointingHandCursor))
            lbl.mousePressEvent = lambda e, p=signed_prefix: self._open_doc_file(p)
            setattr(self, f'{signed_prefix}_file_label', lbl)
            setattr(self, f'{signed_prefix}_file_path', None)

            up_btn = IconLoader.create_icon_button('download', '', 'Загрузить файл', icon_size=14)
            up_btn.setFixedSize(28, 28)
            up_btn.clicked.connect(lambda checked, p=signed_prefix, l=row_label: self._upload_doc_file(p, l))
            up_btn.setStyleSheet(_upload_btn_style)
            setattr(self, f'{signed_prefix}_upload_btn', up_btn)

            del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
            del_btn.setFixedSize(28, 28)
            del_btn.clicked.connect(lambda checked, p=signed_prefix, l=row_label: self._delete_doc_file(p, l))
            del_btn.setStyleSheet(_delete_btn_style)
            del_btn.setVisible(False)
            setattr(self, f'{signed_prefix}_file_delete_btn', del_btn)

            layout_h.addWidget(lbl, 1)
            layout_h.addWidget(up_btn, 0)
            layout_h.addWidget(del_btn, 0)
            signed_layout.addRow(row_label, layout_h)

        signed_group.setLayout(signed_layout)
        acts_container.addWidget(signed_group, 1)

        individual_layout.addRow(acts_container)

        self.individual_group.setLayout(individual_layout)
        layout.addWidget(self.individual_group)

        # Дополнительные поля (Шаблонный)
        self.template_group = QGroupBox('Дополнительные данные (Шаблонный проект)')
        template_layout = QFormLayout()
        template_layout.setSpacing(8)

        # Строка оплаты шаблонного проекта (с кнопками Оплачено/Чек)
        tpl_payment_row = QHBoxLayout()
        tpl_payment_row.setSpacing(6)
        tpl_payment_row.setContentsMargins(0, 0, 0, 0)

        self.template_paid_amount = FormattedMoneyInput('Сумма оплаты')
        tpl_payment_row.addWidget(self.template_paid_amount, 1)

        # Кнопка «Оплачено» (шаблон)
        tpl_paid_btn = QPushButton()
        tpl_paid_btn.setIcon(IconLoader.load('money'))
        tpl_paid_btn.setIconSize(QSize(14, 14))
        tpl_paid_btn.setFixedSize(28, 28)
        tpl_paid_btn.setToolTip('Отметить как оплачено')
        tpl_paid_btn.setStyleSheet(_paid_btn_style)
        tpl_paid_btn.clicked.connect(lambda checked: self._mark_payment_paid('advance_payment'))
        self.tpl_advance_payment_paid_btn = tpl_paid_btn
        tpl_payment_row.addWidget(tpl_paid_btn, 0)

        # Кнопка «Загрузить чек» (шаблон)
        tpl_receipt_btn = IconLoader.create_icon_button('download', '', 'Загрузить чек', icon_size=14)
        tpl_receipt_btn.setFixedSize(28, 28)
        tpl_receipt_btn.setStyleSheet(_receipt_upload_btn_style)
        tpl_receipt_btn.clicked.connect(lambda checked: self._upload_receipt_file('advance_payment'))
        self.tpl_advance_payment_receipt_btn = tpl_receipt_btn
        tpl_payment_row.addWidget(tpl_receipt_btn, 0)

        # Кнопка просмотра чека (шаблон)
        tpl_receipt_view_btn = IconLoader.create_icon_button('eye', '', 'Просмотр чека', icon_size=14)
        tpl_receipt_view_btn.setFixedSize(28, 28)
        tpl_receipt_view_btn.setStyleSheet(_paid_btn_style)
        tpl_receipt_view_btn.setVisible(False)
        tpl_receipt_view_btn.clicked.connect(lambda checked: self._view_receipt_file('advance_payment'))
        self.tpl_advance_payment_receipt_view_btn = tpl_receipt_view_btn
        tpl_payment_row.addWidget(tpl_receipt_view_btn, 0)

        # Кнопка удаления чека (шаблон)
        tpl_receipt_del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить чек', icon_size=14)
        tpl_receipt_del_btn.setFixedSize(28, 28)
        tpl_receipt_del_btn.setStyleSheet(_receipt_delete_btn_style)
        tpl_receipt_del_btn.setVisible(False)
        tpl_receipt_del_btn.clicked.connect(lambda checked: self._delete_receipt_file('advance_payment'))
        self.tpl_advance_payment_receipt_delete_btn = tpl_receipt_del_btn
        tpl_payment_row.addWidget(tpl_receipt_del_btn, 0)

        # Лейбл даты оплаты (шаблон)
        tpl_paid_label = QLabel('Платеж не проведен')
        tpl_paid_label.setStyleSheet(_paid_date_style)
        tpl_paid_label.setFixedHeight(28)
        tpl_paid_label.setAlignment(Qt.AlignCenter)
        self.tpl_advance_payment_paid_label = tpl_paid_label
        tpl_payment_row.addWidget(tpl_paid_label, 0)

        template_layout.addRow('Оплачено:', tpl_payment_row)

        tpl_period_layout = QHBoxLayout()
        tpl_period_layout.setSpacing(8)
        tpl_period_layout.setContentsMargins(0, 0, 0, 0)
        self.template_contract_period = FormattedPeriodInput()
        self.template_contract_period.setEnabled(False)
        tpl_period_layout.addWidget(self.template_contract_period)

        self.tpl_btn_show_term_table = QPushButton('Таблица сроков')
        self.tpl_btn_show_term_table.setFixedHeight(28)
        self.tpl_btn_show_term_table.setStyleSheet('''
            QPushButton { background-color: #E8F4F8; border: 1px solid #B0D4E8;
                          border-radius: 6px; padding: 2px 10px; font-size: 11px;
                          min-height: 22px; max-height: 22px; }
            QPushButton:hover { background-color: #D0E8F2; }
        ''')
        self.tpl_btn_show_term_table.clicked.connect(self._show_template_term_table_dialog)
        tpl_period_layout.addWidget(self.tpl_btn_show_term_table)

        self.tpl_btn_manual_period = QPushButton('Вручную')
        self.tpl_btn_manual_period.setFixedHeight(28)
        self.tpl_btn_manual_period.setStyleSheet('''
            QPushButton { background-color: #FFF3CD; border: 1px solid #E0C97A;
                          border-radius: 6px; padding: 2px 10px; font-size: 11px;
                          min-height: 22px; max-height: 22px; }
            QPushButton:hover { background-color: #FFE9A0; }
        ''')
        self.tpl_btn_manual_period.clicked.connect(self._enable_manual_period_template)
        tpl_period_layout.addWidget(self.tpl_btn_manual_period)

        template_layout.addRow('Срок договора:', tpl_period_layout)

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

        # === Акты (шаблонный) — 2 столбца: без подписи / с подписью ===
        _tpl_act_rows = [
            ('act_planning', 'act_planning_signed', 'Акт ПР:'),
            ('act_concept', 'act_concept_signed', 'Акт КД:'),
            ('info_letter', 'info_letter_signed', 'Инф. письмо:'),
            ('act_final', 'act_final_signed', 'Акт финальный:'),
        ]

        tpl_acts_container = QHBoxLayout()
        tpl_acts_container.setSpacing(10)
        tpl_acts_container.setContentsMargins(0, 0, 0, 0)

        # --- Столбец 1: Акты без подписи (шаблон) ---
        tpl_unsigned_group = QGroupBox('Акты без подписи')
        tpl_unsigned_layout = QFormLayout()
        tpl_unsigned_layout.setSpacing(6)

        for data_prefix, _, row_label in _tpl_act_rows:
            widget_prefix = f'tpl_{data_prefix}'
            layout_h = QHBoxLayout()
            layout_h.setSpacing(6)

            lbl = QLabel('Не загружен')
            lbl.setStyleSheet(_file_label_style)
            lbl.setWordWrap(False)
            lbl.setFixedHeight(28)
            lbl.setMaximumWidth(200)
            lbl.setOpenExternalLinks(True)
            lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
            lbl.setTextFormat(Qt.RichText)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lbl.setCursor(QCursor(Qt.PointingHandCursor))
            lbl.mousePressEvent = lambda e, p=data_prefix: self._open_doc_file(p)
            setattr(self, f'{widget_prefix}_file_label', lbl)
            setattr(self, f'{widget_prefix}_file_path', None)

            up_btn = IconLoader.create_icon_button('download', '', 'Загрузить файл', icon_size=14)
            up_btn.setFixedSize(28, 28)
            up_btn.clicked.connect(lambda checked, p=data_prefix, l=row_label: self._upload_doc_file(p, l))
            up_btn.setStyleSheet(_upload_btn_style)
            setattr(self, f'{widget_prefix}_upload_btn', up_btn)

            del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
            del_btn.setFixedSize(28, 28)
            del_btn.clicked.connect(lambda checked, p=data_prefix, l=row_label: self._delete_doc_file(p, l))
            del_btn.setStyleSheet(_delete_btn_style)
            del_btn.setVisible(False)
            setattr(self, f'{widget_prefix}_file_delete_btn', del_btn)

            layout_h.addWidget(lbl, 1)
            layout_h.addWidget(up_btn, 0)
            layout_h.addWidget(del_btn, 0)
            tpl_unsigned_layout.addRow(row_label, layout_h)

        tpl_unsigned_group.setLayout(tpl_unsigned_layout)
        tpl_acts_container.addWidget(tpl_unsigned_group, 1)

        # --- Столбец 2: Акты с подписью (шаблон) ---
        tpl_signed_group = QGroupBox('Акты с подписью')
        tpl_signed_layout = QFormLayout()
        tpl_signed_layout.setSpacing(6)

        for _, data_prefix, row_label in _tpl_act_rows:
            widget_prefix = f'tpl_{data_prefix}'
            layout_h = QHBoxLayout()
            layout_h.setSpacing(6)

            lbl = QLabel('Не загружен')
            lbl.setStyleSheet(_file_label_style)
            lbl.setWordWrap(False)
            lbl.setFixedHeight(28)
            lbl.setMaximumWidth(200)
            lbl.setOpenExternalLinks(True)
            lbl.setTextInteractionFlags(Qt.TextBrowserInteraction)
            lbl.setTextFormat(Qt.RichText)
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            lbl.setCursor(QCursor(Qt.PointingHandCursor))
            lbl.mousePressEvent = lambda e, p=data_prefix: self._open_doc_file(p)
            setattr(self, f'{widget_prefix}_file_label', lbl)
            setattr(self, f'{widget_prefix}_file_path', None)

            up_btn = IconLoader.create_icon_button('download', '', 'Загрузить файл', icon_size=14)
            up_btn.setFixedSize(28, 28)
            up_btn.clicked.connect(lambda checked, p=data_prefix, l=row_label: self._upload_doc_file(p, l))
            up_btn.setStyleSheet(_upload_btn_style)
            setattr(self, f'{widget_prefix}_upload_btn', up_btn)

            del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=14)
            del_btn.setFixedSize(28, 28)
            del_btn.clicked.connect(lambda checked, p=data_prefix, l=row_label: self._delete_doc_file(p, l))
            del_btn.setStyleSheet(_delete_btn_style)
            del_btn.setVisible(False)
            setattr(self, f'{widget_prefix}_file_delete_btn', del_btn)

            layout_h.addWidget(lbl, 1)
            layout_h.addWidget(up_btn, 0)
            layout_h.addWidget(del_btn, 0)
            tpl_signed_layout.addRow(row_label, layout_h)

        tpl_signed_group.setLayout(tpl_signed_layout)
        tpl_acts_container.addWidget(tpl_signed_group, 1)

        template_layout.addRow(tpl_acts_container)

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
        
        # Надпись синхронизации
        self.sync_label = QLabel('Синхронизация...')
        self.sync_label.setStyleSheet('color: #999999; font-size: 11px;')
        self.sync_label.setVisible(False)

        # Кнопки
        if not self.view_only:
            buttons_layout = QHBoxLayout()
            buttons_layout.addWidget(self.sync_label)
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
            view_buttons_layout = QHBoxLayout()
            view_buttons_layout.addWidget(self.sync_label)
            view_buttons_layout.addStretch()
            view_buttons_layout.addWidget(close_btn)
            layout.addLayout(view_buttons_layout)
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
                child.setStyleSheet('QDateEdit:disabled { background-color: #F0F0F0; color: #666666; }')  # Серый фон

            # БЛОКИРУЕМ QSpinBox (кол-во этажей и т.д.)
            for child in self.findChildren(QSpinBox):
                child.setEnabled(False)
                child.setStyleSheet('QSpinBox:disabled { background-color: #F0F0F0; }')

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

                # Кнопка «Просмотр чека» — оставляем видимой в режиме просмотра
                if 'просмотр чека' in tooltip_lower:
                    continue

                # Остальные кнопки — по общим правилам
                if ('загрузить pdf' in tooltip_lower or
                    'загрузить файл' in tooltip_lower or
                    'загрузить чек' in tooltip_lower or
                    'отметить как оплачено' in tooltip_lower or
                    'удалить файл' in tooltip_lower or
                    'удалить чек' in tooltip_lower or
                    button_text == 'Добавить' or
                    button_text == 'Таблица сроков' or
                    button_text == 'Вручную' or
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

        # Переключаем подтипы в ComboBox
        self.project_subtype.blockSignals(True)
        self.project_subtype.clear()
        if project_type == 'Шаблонный':
            self.project_subtype.addItems(TEMPLATE_SUBTYPES)
            if hasattr(self, 'floors_label'):
                self.floors_label.show()
                self.floors_spin.show()
        else:
            self.project_subtype.addItems(PROJECT_SUBTYPES)
            if hasattr(self, 'floors_label'):
                self.floors_label.hide()
                self.floors_spin.hide()
        self.project_subtype.blockSignals(False)

        # Авторасчёт срока при смене типа
        self._on_subtype_or_area_changed()

    def _get_pt_code(self):
        """Код подтипа проекта: 1=Полный, 2=Эскизный, 3=Планировочный"""
        subtype = self.project_subtype.currentText()
        if 'Полный' in subtype:
            return 1
        elif 'Планировочный' in subtype:
            return 3
        return 2

    @staticmethod
    def _calc_contract_term(pt_code, area):
        """Расчёт срока договора (рабочие дни) по подтипу и площади"""
        if pt_code == 1:
            thresholds = [(70,50),(100,60),(130,70),(160,80),(190,90),(220,100),
                          (250,110),(300,120),(350,130),(400,140),(450,150),(500,160)]
        elif pt_code == 3:
            thresholds = [(70,10),(100,15),(130,20),(160,25),(190,30),(220,35),
                          (250,40),(300,45),(350,50),(400,55),(450,60),(500,65)]
        else:
            thresholds = [(70,30),(100,35),(130,40),(160,45),(190,50),(220,55),
                          (250,60),(300,65),(350,70),(400,75),(450,80),(500,85)]
        for max_area, days in thresholds:
            if area <= max_area:
                return days
        # Площадь > 500 м² — возвращаем максимальный срок из таблицы
        return thresholds[-1][1]

    @staticmethod
    def _calc_template_contract_term(template_subtype, area, floors=1):
        """Расчёт срока для шаблонных проектов (рабочие дни)"""
        sub = template_subtype.lower()
        if 'ванной' in sub:
            if 'визуализац' in sub:
                return 20
            return 10

        # Стандарт / Стандарт с визуализацией
        if area <= 90:
            base_days = 20
        else:
            extra = int((area - 90 - 1) // 50) + 1
            base_days = 20 + extra * 10

        if floors > 1:
            for _ in range(1, floors):
                if area <= 90:
                    base_days += 10
                else:
                    extra = int((area - 90 - 1) // 50) + 1
                    base_days += 10 + extra * 10

        if 'визуализац' in sub:
            if area <= 90:
                base_days += 25
            else:
                extra = int((area - 90 - 1) // 50) + 1
                base_days += 25 + extra * 15

        return int(base_days)

    def _on_subtype_or_area_changed(self, *_args):
        """Авторасчёт срока при изменении подтипа или площади"""
        area = self.area.value()
        if area <= 0:
            return

        project_type = self.project_type.currentText()
        if project_type == 'Шаблонный':
            subtype = self.project_subtype.currentText()
            floors = self.floors_spin.value() if hasattr(self, 'floors_spin') else 1
            term = self._calc_template_contract_term(subtype, area, floors)
        else:
            pt_code = self._get_pt_code()
            term = self._calc_contract_term(pt_code, area)

        if term > 0:
            self.contract_period.setEnabled(False)
            self.contract_period.setValue(term)
            self.template_contract_period.setEnabled(False)
            self.template_contract_period.setValue(term)

    def _enable_manual_period(self):
        """Переключить ручной/авто ввод срока для индивидуального проекта"""
        if self.contract_period.isEnabled():
            # Вернуть авторасчёт
            self._on_subtype_or_area_changed()
            self.btn_manual_period.setText('Вручную')
            self.btn_manual_period.setStyleSheet('''
                QPushButton { background-color: #FFF3CD; border: 1px solid #E0C97A;
                              border-radius: 6px; padding: 2px 10px; font-size: 11px;
                              min-height: 22px; max-height: 22px; }
                QPushButton:hover { background-color: #FFE9A0; }
            ''')
        else:
            # Включить ручной ввод
            self.contract_period.setEnabled(True)
            self.contract_period.setFocus()
            self.btn_manual_period.setText('Авто')
            self.btn_manual_period.setStyleSheet('''
                QPushButton { background-color: #D4EDDA; border: 1px solid #A3D9B1;
                              border-radius: 6px; padding: 2px 10px; font-size: 11px;
                              min-height: 22px; max-height: 22px; }
                QPushButton:hover { background-color: #C3E6CB; }
            ''')

    def _enable_manual_period_template(self):
        """Переключить ручной/авто ввод срока для шаблонного проекта"""
        if self.template_contract_period.isEnabled():
            self._on_subtype_or_area_changed()
            self.tpl_btn_manual_period.setText('Вручную')
            self.tpl_btn_manual_period.setStyleSheet('''
                QPushButton { background-color: #FFF3CD; border: 1px solid #E0C97A;
                              border-radius: 6px; padding: 2px 10px; font-size: 11px;
                              min-height: 22px; max-height: 22px; }
                QPushButton:hover { background-color: #FFE9A0; }
            ''')
        else:
            self.template_contract_period.setEnabled(True)
            self.template_contract_period.setFocus()
            self.tpl_btn_manual_period.setText('Авто')
            self.tpl_btn_manual_period.setStyleSheet('''
                QPushButton { background-color: #D4EDDA; border: 1px solid #A3D9B1;
                              border-radius: 6px; padding: 2px 10px; font-size: 11px;
                              min-height: 22px; max-height: 22px; }
                QPushButton:hover { background-color: #C3E6CB; }
            ''')

    def _show_term_table_dialog(self):
        """Показать диалог с таблицей площадь - срок для всех подтипов"""
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground, False)
        dlg.setFixedSize(480, 480)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Рамка
        frame = QFrame()
        frame.setStyleSheet('''
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        ''')
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Заголовок
        title_bar = CustomTitleBar(dlg, 'Таблица сроков договора', simple_mode=True)
        frame_layout.addWidget(title_bar)

        # Содержимое
        content = QWidget()
        content.setStyleSheet('background-color: #FFFFFF;')
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 8, 12, 12)
        cl.setSpacing(8)

        # Описание
        desc = QLabel('Срок договора (рабочих дней) в зависимости от площади и подтипа проекта:')
        desc.setStyleSheet('font-size: 11px; color: #666; background: transparent;')
        desc.setWordWrap(True)
        cl.addWidget(desc)

        # Таблица
        tbl = QTableWidget()
        tbl.setColumnCount(4)
        tbl.setHorizontalHeaderLabels(['Площадь до (м\u00b2)', 'Полный', 'Эскизный', 'Планировочный'])
        areas = [70, 100, 130, 160, 190, 220, 250, 300, 350, 400, 450, 500]
        tbl.setRowCount(len(areas))
        tbl.verticalHeader().setVisible(False)
        for r, a in enumerate(areas):
            for col, val in enumerate([
                str(a),
                str(self._calc_contract_term(1, a)),
                str(self._calc_contract_term(2, a)),
                str(self._calc_contract_term(3, a)),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, col, item)
            tbl.setRowHeight(r, 28)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setFocusPolicy(Qt.NoFocus)
        tbl.setStyleSheet('''
            QTableWidget {
                border: 1px solid #E0E0E0;
                gridline-color: #E8E8E8;
                font-size: 12px;
                background-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                padding: 4px;
                font-weight: bold;
                font-size: 11px;
            }
        ''')
        cl.addWidget(tbl)

        # Кнопка закрыть
        close_btn = QPushButton('Закрыть')
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet('''
            QPushButton {
                background-color: #F5F5F5; border: 1px solid #E0E0E0;
                border-radius: 4px; padding: 4px 20px; font-size: 12px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        ''')
        close_btn.clicked.connect(dlg.accept)
        cl.addWidget(close_btn, alignment=Qt.AlignRight)

        frame_layout.addWidget(content)
        outer.addWidget(frame)

        # Центрируем относительно родителя
        from utils.dialog_helpers import center_dialog_on_parent
        dlg.show()
        center_dialog_on_parent(dlg)
        dlg.exec_()

    def _show_template_term_table_dialog(self):
        """Показать диалог с таблицей сроков для шаблонных проектов"""
        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground, False)
        dlg.setFixedSize(560, 400)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        frame = QFrame()
        frame.setStyleSheet('''
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
        ''')
        frame_layout = QVBoxLayout(frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        title_bar = CustomTitleBar(dlg, 'Таблица сроков (шаблонные проекты)', simple_mode=True)
        frame_layout.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet('background-color: #FFFFFF;')
        cl = QVBoxLayout(content)
        cl.setContentsMargins(12, 8, 12, 12)
        cl.setSpacing(8)

        desc = QLabel('Срок договора (рабочих дней) для шаблонных проектов.\n'
                       'Стандарт и Стандарт с визуализацией зависят от площади и этажей.\n'
                       'Ванная комната \u2014 фиксированный срок.')
        desc.setStyleSheet('font-size: 11px; color: #666; background: transparent;')
        desc.setWordWrap(True)
        cl.addWidget(desc)

        tbl = QTableWidget()
        tbl.setColumnCount(5)
        tbl.setHorizontalHeaderLabels([
            'Площадь до (м\u00b2)', 'Стандарт', 'Стандарт+Визуал.',
            'Ванная', 'Ванная+Визуал.'
        ])
        areas = [90, 140, 190, 240, 290, 340]
        tbl.setRowCount(len(areas))
        tbl.verticalHeader().setVisible(False)
        for r, a in enumerate(areas):
            for col, val in enumerate([
                str(a),
                str(self._calc_template_contract_term('Стандарт', a, 1)),
                str(self._calc_template_contract_term('Стандарт с визуализацией', a, 1)),
                str(self._calc_template_contract_term('Проект ванной комнаты', a, 1)),
                str(self._calc_template_contract_term('Проект ванной комнаты с визуализацией', a, 1)),
            ]):
                item = QTableWidgetItem(val)
                item.setTextAlignment(Qt.AlignCenter)
                item.setFlags(Qt.ItemIsEnabled)
                tbl.setItem(r, col, item)
            tbl.setRowHeight(r, 28)
        tbl.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        tbl.setEditTriggers(QTableWidget.NoEditTriggers)
        tbl.setSelectionMode(QTableWidget.NoSelection)
        tbl.setFocusPolicy(Qt.NoFocus)
        tbl.setStyleSheet('''
            QTableWidget {
                border: 1px solid #E0E0E0;
                gridline-color: #E8E8E8;
                font-size: 12px;
                background-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                padding: 4px;
                font-weight: bold;
                font-size: 11px;
            }
        ''')
        cl.addWidget(tbl)

        close_btn = QPushButton('Закрыть')
        close_btn.setFixedHeight(30)
        close_btn.setStyleSheet('''
            QPushButton {
                background-color: #F5F5F5; border: 1px solid #E0E0E0;
                border-radius: 4px; padding: 4px 20px; font-size: 12px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        ''')
        close_btn.clicked.connect(dlg.accept)
        cl.addWidget(close_btn, alignment=Qt.AlignRight)

        frame_layout.addWidget(content)
        outer.addWidget(frame)

        from utils.dialog_helpers import center_dialog_on_parent
        dlg.show()
        center_dialog_on_parent(dlg)
        dlg.exec_()

    def truncate_filename(self, filename, max_length=30):
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

        agents = self.data.get_all_agents()
        for agent in agents:
            self.agent_combo.addItem(agent['name'])

        # Восстанавливаем выбор если был
        if current_text:
            index = self.agent_combo.findText(current_text)
            if index >= 0:
                self.agent_combo.setCurrentIndex(index)

    def fill_data(self):
        """Заполнение формы данными"""
        # Загружаем свежие данные через DataAccess (API с fallback на локальную БД)
        if self.contract_data and self.contract_data.get('id'):
            fresh_data = self.data.get_contract(self.contract_data['id'])
            if fresh_data:
                self.contract_data = fresh_data
                print(f"[fill_data] Загружены свежие данные для контракта {self.contract_data['id']}")

            # Дополняем данные из локальной БД для новых полей
            # (пока сервер не задеплоен с новыми колонками, API их не возвращает)
            if self.data.db:
                try:
                    local_contract = self.data.db.get_contract_by_id(self.contract_data['id'])
                    if local_contract:
                        _new_fields = [
                            'advance_payment_paid_date', 'additional_payment_paid_date', 'third_payment_paid_date',
                            'advance_receipt_link', 'advance_receipt_yandex_path', 'advance_receipt_file_name',
                            'additional_receipt_link', 'additional_receipt_yandex_path', 'additional_receipt_file_name',
                            'third_receipt_link', 'third_receipt_yandex_path', 'third_receipt_file_name',
                            'act_planning_signed_link', 'act_planning_signed_yandex_path', 'act_planning_signed_file_name',
                            'act_concept_signed_link', 'act_concept_signed_yandex_path', 'act_concept_signed_file_name',
                            'info_letter_signed_link', 'info_letter_signed_yandex_path', 'info_letter_signed_file_name',
                            'act_final_signed_link', 'act_final_signed_yandex_path', 'act_final_signed_file_name',
                        ]
                        for field in _new_fields:
                            if not self.contract_data.get(field) and local_contract.get(field):
                                self.contract_data[field] = local_contract[field]
                except Exception as e:
                    print(f"[fill_data] Ошибка дополнения из локальной БД: {e}")

        # R-10 FIX: .get() вместо ['key'] для защиты от KeyError при неполных данных
        client_id = self.contract_data.get('client_id')
        for i in range(self.client_combo.count()):
            if self.client_combo.itemData(i) == client_id:
                self.client_combo.setCurrentIndex(i)
                break

        self.project_type.setCurrentText(self.contract_data.get('project_type', ''))
        # Подтип: сначала переключаем набор элементов, потом выбираем значение
        pt = self.contract_data.get('project_type', '')
        self.project_subtype.blockSignals(True)
        self.project_subtype.clear()
        if pt == 'Шаблонный':
            self.project_subtype.addItems(TEMPLATE_SUBTYPES)
            if hasattr(self, 'floors_label'):
                self.floors_label.show()
                self.floors_spin.show()
        else:
            self.project_subtype.addItems(PROJECT_SUBTYPES)
            if hasattr(self, 'floors_label'):
                self.floors_label.hide()
                self.floors_spin.hide()
        if self.contract_data.get('project_subtype'):
            self.project_subtype.setCurrentText(self.contract_data['project_subtype'])
        self.project_subtype.blockSignals(False)
        # Этажи
        if hasattr(self, 'floors_spin'):
            self.floors_spin.setValue(self.contract_data.get('floors', 1) or 1)
        self.agent_combo.setCurrentText(self.contract_data.get('agent_type', ''))
        self.city_combo.setCurrentText(self.contract_data.get('city', ''))
        self.contract_number.setText(self.contract_data.get('contract_number', ''))
        
        if self.contract_data.get('contract_date'):
            self.contract_date.setDate(QDate.fromString(self.contract_data['contract_date'], 'yyyy-MM-dd'))
        
        self.address.setText(self.contract_data.get('address', ''))
        self.area.setValue(self.contract_data.get('area', 0))
        self.total_amount.setValue(self.contract_data.get('total_amount', 0))
        self.advance_payment.setValue(self.contract_data.get('advance_payment', 0))
        self.additional_payment.setValue(self.contract_data.get('additional_payment', 0))
        self.third_payment.setValue(self.contract_data.get('third_payment', 0))
        self.template_paid_amount.setValue(self.contract_data.get('advance_payment', 0))
        self.contract_period.setValue(self.contract_data.get('contract_period', 0))
        self.template_contract_period.setValue(self.contract_data.get('contract_period', 0))

        # Загружаем данные о файле договора (индивидуальный проект)
        contract_file_link = self.contract_data.get('contract_file_link', '')
        contract_file_yp = self.contract_data.get('contract_file_yandex_path', '')
        if contract_file_link or contract_file_yp:
            self.contract_file_path = contract_file_link or contract_file_yp
            file_name = self.contract_data.get('contract_file_name', '') or 'Договор.pdf'
            truncated_name = self.truncate_filename(file_name)
            if contract_file_link:
                html_link = f'<a href="{contract_file_link}" title="{file_name}">{truncated_name}</a>'
            else:
                html_link = truncated_name
            self.contract_file_label.setText(html_link)
            self.contract_file_delete_btn.setVisible(not self.view_only)
            self.contract_upload_btn.setEnabled(False)
        else:
            self.contract_file_label.setText('Не загружен')
            self.contract_file_delete_btn.setVisible(False)
            self.contract_upload_btn.setEnabled(True)

        # Загружаем данные о файле договора (шаблонный проект)
        template_file_link = self.contract_data.get('template_contract_file_link', '')
        template_file_yp = self.contract_data.get('template_contract_file_yandex_path', '')
        if template_file_link or template_file_yp:
            self.template_contract_file_path = template_file_link or template_file_yp
            file_name = self.contract_data.get('template_contract_file_name', '') or 'Договор.pdf'
            truncated_name = self.truncate_filename(file_name)
            if template_file_link:
                html_link = f'<a href="{template_file_link}" title="{file_name}">{truncated_name}</a>'
            else:
                html_link = truncated_name
            self.template_contract_file_label.setText(html_link)
            self.template_contract_file_delete_btn.setVisible(not self.view_only)
            self.template_contract_upload_btn.setEnabled(False)
        else:
            self.template_contract_file_label.setText('Не загружен')
            self.template_contract_file_delete_btn.setVisible(False)
            self.template_contract_upload_btn.setEnabled(True)

        # Загружаем данные о файле тех.задания
        tech_task_link = self.contract_data.get('tech_task_link', '')
        tech_task_yp = self.contract_data.get('tech_task_yandex_path', '')
        if tech_task_link or tech_task_yp:
            self.tech_task_file_path = tech_task_link or tech_task_yp
            self.tech_task_yandex_path = tech_task_yp
            self.tech_task_file_name = self.contract_data.get('tech_task_file_name', '')
            file_name = self.tech_task_file_name if self.tech_task_file_name else 'ТехЗадание.pdf'
            truncated_name = self.truncate_filename(file_name)
            if tech_task_link:
                html_link = f'<a href="{tech_task_link}" title="{file_name}">{truncated_name}</a>'
            else:
                html_link = truncated_name
            self.tech_task_file_label.setText(html_link)
            self.tech_task_file_delete_btn.setVisible(not self.view_only)
            self.tech_task_upload_btn.setEnabled(False)
        else:
            self.tech_task_file_label.setText('Не загружен')
            self.tech_task_file_delete_btn.setVisible(False)
            self.tech_task_upload_btn.setEnabled(True)

        # Загружаем данные об актах (без подписи + с подписью)
        _doc_defaults = {
            'act_planning': 'Акт ПР.pdf',
            'act_concept': 'Акт КД.pdf',
            'info_letter': 'Инф. письмо.pdf',
            'act_final': 'Акт финальный.pdf',
            'act_planning_signed': 'Акт ПР (подписан).pdf',
            'act_concept_signed': 'Акт КД (подписан).pdf',
            'info_letter_signed': 'Инф. письмо (подписано).pdf',
            'act_final_signed': 'Акт финальный (подписан).pdf',
        }
        for prefix, default_name in _doc_defaults.items():
            link = self.contract_data.get(f'{prefix}_link', '')
            yp = self.contract_data.get(f'{prefix}_yandex_path', '')
            if link or yp:
                setattr(self, f'{prefix}_file_path', link or yp)
                setattr(self, f'{prefix}_yandex_path', yp)
                setattr(self, f'{prefix}_file_name', self.contract_data.get(f'{prefix}_file_name', ''))
                file_name = getattr(self, f'{prefix}_file_name') or default_name
                truncated_name = self.truncate_filename(file_name)
                if link:
                    html_link = f'<a href="{link}" title="{file_name}">{truncated_name}</a>'
                else:
                    html_link = truncated_name
                getattr(self, f'{prefix}_file_label').setText(html_link)
                getattr(self, f'{prefix}_file_delete_btn').setVisible(not self.view_only)
                getattr(self, f'{prefix}_upload_btn').setEnabled(False)
            else:
                getattr(self, f'{prefix}_file_label').setText('Не загружен')
                getattr(self, f'{prefix}_file_delete_btn').setVisible(False)
                getattr(self, f'{prefix}_upload_btn').setEnabled(True)

            # Зеркалим в шаблонные виджеты (tpl_ prefix)
            tpl_label = getattr(self, f'tpl_{prefix}_file_label', None)
            tpl_del_btn = getattr(self, f'tpl_{prefix}_file_delete_btn', None)
            tpl_up_btn = getattr(self, f'tpl_{prefix}_upload_btn', None)
            if tpl_label:
                if link or yp:
                    tpl_label.setText(html_link if (link or yp) else 'Не загружен')
                    if tpl_del_btn:
                        tpl_del_btn.setVisible(not self.view_only)
                    if tpl_up_btn:
                        tpl_up_btn.setEnabled(False)
                else:
                    tpl_label.setText('Не загружен')
                    if tpl_del_btn:
                        tpl_del_btn.setVisible(False)
                    if tpl_up_btn:
                        tpl_up_btn.setEnabled(True)

        # Загружаем данные о платежах (даты оплат и чеки)
        _payment_prefixes = ['advance_payment', 'additional_payment', 'third_payment']
        _receipt_prefix_map = {
            'advance_payment': 'advance_receipt',
            'additional_payment': 'additional_receipt',
            'third_payment': 'third_receipt',
        }
        _paid_date_active_style = '''
            QLabel {
                background-color: #F8F9FA; padding: 2px 8px; border: 1px solid #E0E0E0;
                border-radius: 6px; font-size: 11px; color: #27AE60; font-weight: 600;
                min-width: 120px; min-height: 16px;
            }
        '''
        _paid_date_default_style = '''
            QLabel {
                background-color: #F8F9FA; padding: 2px 8px; border: 1px solid #E0E0E0;
                border-radius: 6px; font-size: 11px;
                min-width: 120px; min-height: 16px;
            }
        '''
        for pp in _payment_prefixes:
            # Дата оплаты — обновляем оба набора виджетов (индивидуальный + шаблонный)
            paid_date = self.contract_data.get(f'{pp}_paid_date', '')
            for w_prefix in (pp, f'tpl_{pp}'):
                paid_label = getattr(self, f'{w_prefix}_paid_label', None)
                paid_btn = getattr(self, f'{w_prefix}_paid_btn', None)
                if paid_date and paid_label:
                    display_date = QDate.fromString(paid_date, 'yyyy-MM-dd').toString('dd.MM.yyyy')
                    paid_label.setText(display_date)
                    paid_label.setStyleSheet(_paid_date_active_style)
                    if paid_btn:
                        paid_btn.setEnabled(False)
                        paid_btn.setToolTip(f'Оплачено {display_date}')
                else:
                    if paid_label:
                        paid_label.setText('Платеж не проведен')
                        paid_label.setStyleSheet(_paid_date_default_style)
                    if paid_btn:
                        paid_btn.setEnabled(not self.view_only)

            # Блокируем поле суммы если платеж уже проведен
            if paid_date:
                _locked_money_style = 'QLineEdit { background-color: #F0F0F0; padding: 2px 8px; min-height: 24px; max-height: 24px; }'
                money_input = getattr(self, pp, None)
                if money_input:
                    money_input.setReadOnly(True)
                    money_input.setStyleSheet(_locked_money_style)
                tpl_money_input = getattr(self, f'tpl_{pp}', None)
                if tpl_money_input:
                    tpl_money_input.setReadOnly(True)
                    tpl_money_input.setStyleSheet(_locked_money_style)
                # Для шаблона advance_payment — отдельный виджет template_paid_amount
                if pp == 'advance_payment':
                    tpl_paid_amt = getattr(self, 'template_paid_amount', None)
                    if tpl_paid_amt:
                        tpl_paid_amt.setReadOnly(True)
                        tpl_paid_amt.setStyleSheet(_locked_money_style)

            # Чек — обновляем оба набора виджетов
            rp = _receipt_prefix_map[pp]
            receipt_link = self.contract_data.get(f'{rp}_link', '')
            receipt_yp = self.contract_data.get(f'{rp}_yandex_path', '')
            if receipt_link or receipt_yp:
                setattr(self, f'{rp}_file_path', receipt_link or receipt_yp)
                setattr(self, f'{rp}_yandex_path', receipt_yp)
                setattr(self, f'{rp}_file_name', self.contract_data.get(f'{rp}_file_name', ''))
            for w_prefix in (pp, f'tpl_{pp}'):
                receipt_btn = getattr(self, f'{w_prefix}_receipt_btn', None)
                receipt_del_btn = getattr(self, f'{w_prefix}_receipt_delete_btn', None)
                receipt_view_btn = getattr(self, f'{w_prefix}_receipt_view_btn', None)
                if receipt_link or receipt_yp:
                    if receipt_btn:
                        receipt_btn.setEnabled(False)
                    if receipt_del_btn:
                        receipt_del_btn.setVisible(not self.view_only)
                    if receipt_view_btn:
                        receipt_view_btn.setVisible(bool(receipt_link))  # Показываем если есть ссылка
                else:
                    if receipt_btn:
                        receipt_btn.setEnabled(not self.view_only)
                    if receipt_del_btn:
                        receipt_del_btn.setVisible(False)
                    if receipt_view_btn:
                        receipt_view_btn.setVisible(False)

        self.comments.setPlainText(self.contract_data.get('comments', ''))

        # Проверяем файлы на Яндекс.Диске в фоновом режиме
        self.verify_files_on_yandex_disk()

        # Синхронизируем файлы с Яндекс.Диска (добавляем новые файлы в БД)
        self.sync_files_from_yandex_disk()

        # Восстанавливаем недостающие публичные ссылки в фоне
        self.repair_missing_public_links()

    def repair_missing_public_links(self):
        """Восстановление недостающих публичных ссылок для файлов с yandex_path"""
        if not self.contract_data or not self.data.is_multi_user:
            return

        contract_id = self.contract_data.get('id')
        if not contract_id:
            return

        # Собираем файлы, у которых yandex_path есть, но link пустой
        files_to_repair = []
        # Договор (индивидуальный)
        if self.contract_data.get('contract_file_yandex_path') and not self.contract_data.get('contract_file_link'):
            files_to_repair.append(('contract_file', self.contract_data['contract_file_yandex_path']))
        # Договор (шаблонный)
        if self.contract_data.get('template_contract_file_yandex_path') and not self.contract_data.get('template_contract_file_link'):
            files_to_repair.append(('template_contract_file', self.contract_data['template_contract_file_yandex_path']))
        # ТЗ
        if self.contract_data.get('tech_task_yandex_path') and not self.contract_data.get('tech_task_link'):
            files_to_repair.append(('tech_task', self.contract_data['tech_task_yandex_path']))
        # Акты (без подписи + с подписью) и чеки
        for prefix in ('act_planning', 'act_concept', 'info_letter', 'act_final',
                        'act_planning_signed', 'act_concept_signed', 'info_letter_signed', 'act_final_signed',
                        'advance_receipt', 'additional_receipt', 'third_receipt'):
            if self.contract_data.get(f'{prefix}_yandex_path') and not self.contract_data.get(f'{prefix}_link'):
                files_to_repair.append((prefix, self.contract_data[f'{prefix}_yandex_path']))

        if not files_to_repair:
            return

        self._show_sync_label()

        def repair():
            try:
                update_data = {}
                for prefix, yandex_path in files_to_repair:
                    try:
                        result = self.data.get_yandex_public_link(yandex_path)
                        public_link = None
                        if isinstance(result, dict):
                            public_link = result.get('public_url') or result.get('public_link')
                        elif isinstance(result, str):
                            public_link = result

                        if public_link:
                            link_field = f'{prefix}_link'
                            update_data[link_field] = public_link
                            print(f"[REPAIR] Восстановлена ссылка для {prefix}: {public_link}")
                        else:
                            print(f"[REPAIR] Не удалось получить ссылку для {prefix}")
                    except Exception as e:
                        print(f"[REPAIR] Ошибка получения ссылки для {prefix}: {e}")

                if update_data:
                    try:
                        self.data.update_contract(contract_id, update_data)
                        print(f"[REPAIR] Обновлена БД: {list(update_data.keys())}")
                    except Exception as e:
                        print(f"[REPAIR] Ошибка обновления: {e}")

                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self.refresh_file_labels)
            except Exception as e:
                print(f"[REPAIR] Ошибка: {e}")
            finally:
                self._sync_ended.emit()

        thread = threading.Thread(target=repair, daemon=True)
        thread.start()

    def _show_sync_label(self):
        """Показать надпись синхронизации"""
        self._active_sync_count += 1
        if hasattr(self, 'sync_label'):
            self.sync_label.setVisible(True)

    def _on_sync_ended(self):
        """Скрыть надпись синхронизации когда все операции завершены"""
        self._active_sync_count = max(0, self._active_sync_count - 1)
        if self._active_sync_count == 0 and hasattr(self, 'sync_label'):
            self.sync_label.setVisible(False)

    def verify_files_on_yandex_disk(self):
        """Проверка существования файлов на Яндекс.Диске в фоновом режиме"""
        if not self.contract_data:
            return

        self._show_sync_label()
        contract_id = self.contract_data['id']

        def check_files():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                if not yd.token:
                    print("[VERIFY-CT] Токен Яндекс.Диска не установлен, пропуск проверки")
                    return

                # Получаем данные через DataAccess (API с fallback на локальную БД)
                contract = self.data.get_contract(contract_id)
                if not contract:
                    print(f"[VERIFY-CT] Контракт {contract_id} не найден")
                    return

                needs_update = False
                update_data = {}

                # Проверяем файл договора (индивидуальный)
                cf_path = contract.get('contract_file_yandex_path', '')
                if cf_path:
                    print(f"[VERIFY-CT] Проверяем договор: {cf_path}")
                    if not yd.file_exists(cf_path):
                        print(f"[VERIFY-CT] Файл договора НЕ найден на ЯД")
                        update_data['contract_file_link'] = ''
                        update_data['contract_file_yandex_path'] = ''
                        update_data['contract_file_name'] = ''
                        needs_update = True

                # Проверяем файл договора (шаблонный)
                tcf_path = contract.get('template_contract_file_yandex_path', '')
                if tcf_path:
                    print(f"[VERIFY-CT] Проверяем шаблон: {tcf_path}")
                    if not yd.file_exists(tcf_path):
                        print(f"[VERIFY-CT] Файл шаблона НЕ найден на ЯД")
                        update_data['template_contract_file_link'] = ''
                        update_data['template_contract_file_yandex_path'] = ''
                        update_data['template_contract_file_name'] = ''
                        needs_update = True

                # Проверяем тех.задание
                tz_path = contract.get('tech_task_yandex_path', '')
                if tz_path:
                    print(f"[VERIFY-CT] Проверяем ТЗ: {tz_path}")
                    if not yd.file_exists(tz_path):
                        print(f"[VERIFY-CT] Файл ТЗ НЕ найден на ЯД")
                        update_data['tech_task_link'] = ''
                        update_data['tech_task_yandex_path'] = ''
                        update_data['tech_task_file_name'] = ''
                        needs_update = True

                # Проверяем замер
                meas_path = contract.get('measurement_yandex_path', '')
                if meas_path:
                    print(f"[VERIFY-CT] Проверяем замер: {meas_path}")
                    if not yd.file_exists(meas_path):
                        print(f"[VERIFY-CT] Файл замера НЕ найден на ЯД")
                        update_data['measurement_image_link'] = ''
                        update_data['measurement_yandex_path'] = ''
                        update_data['measurement_file_name'] = ''
                        needs_update = True

                # Проверяем акты (без подписи + с подписью) и чеки
                for _pref in ('act_planning', 'act_concept', 'info_letter', 'act_final',
                              'act_planning_signed', 'act_concept_signed', 'info_letter_signed', 'act_final_signed',
                              'advance_receipt', 'additional_receipt', 'third_receipt'):
                    _path = contract.get(f'{_pref}_yandex_path', '')
                    if _path:
                        if not yd.file_exists(_path):
                            print(f"[VERIFY-CT] Файл {_pref} НЕ найден на ЯД")
                            update_data[f'{_pref}_link'] = ''
                            update_data[f'{_pref}_yandex_path'] = ''
                            update_data[f'{_pref}_file_name'] = ''
                            needs_update = True

                if needs_update:
                    print(f"[VERIFY-CT] Обновляем БД: {list(update_data.keys())}")
                    try:
                        self.data.update_contract(contract_id, update_data)
                        print(f"[VERIFY-CT] Обновлена БД")
                    except Exception as e:
                        print(f"[VERIFY-CT] Ошибка обновления: {e}")

                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self.refresh_file_labels)
                else:
                    print(f"[VERIFY-CT] Все файлы договора на месте")

            except Exception as e:
                import traceback
                print(f"[ERROR] Ошибка при проверке файлов на Яндекс.Диске: {e}")
                traceback.print_exc()
            finally:
                self._sync_ended.emit()

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

        self._show_sync_label()

        def sync_files():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                # Получаем данные через DataAccess (API с fallback на локальную БД)
                contract = self.data.get_contract(contract_id)
                if not contract:
                    print(f"[SYNC] Контракт {contract_id} не найден")
                    return

                needs_update = False
                update_data = {}
                project_type = contract.get('project_type') or 'Индивидуальный'

                # Определяем какие файлы искать в зависимости от типа проекта
                file_mappings = []

                if project_type == 'Индивидуальный':
                    # Для индивидуального проекта ищем обычный договор
                    if not contract.get('contract_file_yandex_path'):
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
                    if not contract.get('template_contract_file_yandex_path'):
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
                if not contract.get('tech_task_yandex_path'):
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
                if not contract.get('measurement_yandex_path'):
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

                # Акт планировочные решения
                if not contract.get('act_planning_yandex_path'):
                    file_mappings.append({
                        'subfolder': 'Документы',
                        'keywords': ['акт планировочн', 'акт пр'],
                        'extensions': ['.pdf', '.docx', '.doc'],
                        'db_fields': {
                            'act_planning_link': 'public_link',
                            'act_planning_yandex_path': 'yandex_path',
                            'act_planning_file_name': 'file_name'
                        }
                    })

                # Акт концепция дизайна
                if not contract.get('act_concept_yandex_path'):
                    file_mappings.append({
                        'subfolder': 'Документы',
                        'keywords': ['акт концепц', 'акт кд'],
                        'extensions': ['.pdf', '.docx', '.doc'],
                        'db_fields': {
                            'act_concept_link': 'public_link',
                            'act_concept_yandex_path': 'yandex_path',
                            'act_concept_file_name': 'file_name'
                        }
                    })

                # Информационное письмо
                if not contract.get('info_letter_yandex_path'):
                    file_mappings.append({
                        'subfolder': 'Документы',
                        'keywords': ['информационн', 'инф. письм', 'информ письм'],
                        'extensions': ['.pdf', '.docx', '.doc'],
                        'db_fields': {
                            'info_letter_link': 'public_link',
                            'info_letter_yandex_path': 'yandex_path',
                            'info_letter_file_name': 'file_name'
                        }
                    })

                # Акт финальный
                if not contract.get('act_final_yandex_path'):
                    file_mappings.append({
                        'subfolder': 'Документы',
                        'keywords': ['акт финальн', 'акт фин'],
                        'extensions': ['.pdf', '.docx', '.doc'],
                        'db_fields': {
                            'act_final_link': 'public_link',
                            'act_final_yandex_path': 'yandex_path',
                            'act_final_file_name': 'file_name'
                        }
                    })

                # === Подписанные акты (ищем файлы с "подпис" в имени) ===
                _signed_acts = [
                    ('act_planning_signed', ['акт планировочн', 'акт пр']),
                    ('act_concept_signed', ['акт концепц', 'акт кд']),
                    ('info_letter_signed', ['информационн', 'инф. письм', 'информ письм']),
                    ('act_final_signed', ['акт финальн', 'акт фин']),
                ]
                for signed_prefix, base_keywords in _signed_acts:
                    if not contract.get(f'{signed_prefix}_yandex_path'):
                        # Добавляем "подпис" к каждому ключевому слову
                        signed_keywords = [f'{kw}' for kw in base_keywords]
                        file_mappings.append({
                            'subfolder': 'Документы',
                            'keywords': signed_keywords,
                            'extensions': ['.pdf', '.docx', '.doc'],
                            'extra_keyword': 'подпис',  # Файл должен содержать И ключевое слово И "подпис"
                            'db_fields': {
                                f'{signed_prefix}_link': 'public_link',
                                f'{signed_prefix}_yandex_path': 'yandex_path',
                                f'{signed_prefix}_file_name': 'file_name'
                            }
                        })

                # === Чеки платежей (ищем файлы с "чек" в имени) ===
                _receipt_mappings = [
                    ('advance_receipt', ['чек']),
                    ('additional_receipt', ['чек']),
                    ('third_receipt', ['чек']),
                ]
                # Находим первый свободный слот для чеков
                for receipt_prefix, keywords in _receipt_mappings:
                    if not contract.get(f'{receipt_prefix}_yandex_path'):
                        file_mappings.append({
                            'subfolder': 'Документы',
                            'keywords': keywords,
                            'extensions': ['.pdf', '.jpg', '.jpeg', '.png'],
                            'db_fields': {
                                f'{receipt_prefix}_link': 'public_link',
                                f'{receipt_prefix}_yandex_path': 'yandex_path',
                                f'{receipt_prefix}_file_name': 'file_name'
                            }
                        })
                        break  # Только один чек за раз (чтобы не привязать все к одному файлу)

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

                        # Проверяем extra_keyword (для подписанных актов)
                        extra_kw = mapping.get('extra_keyword')
                        if keyword_found and extra_kw:
                            if extra_kw not in file_name_lower:
                                keyword_found = False  # Основное слово есть, но "подпис" нет — пропускаем
                        elif not keyword_found and extra_kw:
                            pass  # Основного слова нет — уже False

                        if keyword_found:
                            print(f"[INFO SYNC] Найден файл '{file_name}' на Яндекс.Диске! (ключевое слово: '{matched_keyword}')")

                            # Формируем полный путь к файлу
                            file_path = f"{subfolder_path}/{file_name}"

                            # Получаем публичную ссылку (через сервер или локально)
                            public_link = None
                            try:
                                result = self.data.get_yandex_public_link(file_path)
                                if isinstance(result, dict):
                                    public_link = result.get('public_url') or result.get('public_link')
                                elif isinstance(result, str):
                                    public_link = result
                            except Exception as e:
                                print(f"[SYNC] Ошибка получения ссылки через DataAccess: {e}")
                            if not public_link:
                                try:
                                    public_link = yd.get_public_link(file_path)
                                except Exception:
                                    pass

                            # Сохраняем данные для обновления БД (даже без public_link)
                            for db_field, value_type in mapping['db_fields'].items():
                                if value_type == 'public_link':
                                    update_data[db_field] = public_link or ''
                                elif value_type == 'yandex_path':
                                    update_data[db_field] = file_path
                                elif value_type == 'file_name':
                                    update_data[db_field] = file_name

                            needs_update = True
                            if public_link:
                                print(f"[OK SYNC] Файл '{file_name}' добавлен с ссылкой")
                            else:
                                print(f"[OK SYNC] Файл '{file_name}' добавлен (ссылка будет восстановлена позже)")
                            break  # Нашли файл, переходим к следующей подпапке

                # Обновляем БД если нашли новые файлы
                if needs_update:
                    print(f"[INFO SYNC] Обновляем БД: {update_data}")
                    # Обновляем локальную БД
                    try:
                        self.data.update_contract(contract_id, update_data)
                        print(f"[OK SYNC] Обновлена БД: {list(update_data.keys())}")
                    except Exception as e:
                        print(f"[ERROR] Не удалось обновить через DataAccess: {e}")
                    print(f"[OK SYNC] Синхронизация завершена! Добавлено полей: {len(update_data)}")

                    # Обновляем UI через QTimer (thread-safe)
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self.refresh_file_labels)
                else:
                    print(f"[INFO SYNC] Новых файлов для синхронизации не найдено")

            except Exception as e:
                print(f"[ERROR] Ошибка при синхронизации файлов с Яндекс.Диска: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self._sync_ended.emit()

        # Запускаем синхронизацию в фоновом потоке
        thread = threading.Thread(target=sync_files, daemon=True)
        thread.start()

    def refresh_file_labels(self):
        """Обновление меток файлов после проверки"""
        if not self.contract_data:
            return

        contract_id = self.contract_data['id']

        # Перезагружаем данные через DataAccess (API с fallback на локальную БД)
        contract_data = self.data.get_contract(contract_id)
        if contract_data:
            # Дополняем из локальной БД для новых полей
            if self.data.db:
                try:
                    local = self.data.db.get_contract_by_id(contract_id)
                    if local:
                        _nf = [
                            'advance_payment_paid_date', 'additional_payment_paid_date', 'third_payment_paid_date',
                            'advance_receipt_link', 'advance_receipt_yandex_path', 'advance_receipt_file_name',
                            'additional_receipt_link', 'additional_receipt_yandex_path', 'additional_receipt_file_name',
                            'third_receipt_link', 'third_receipt_yandex_path', 'third_receipt_file_name',
                            'act_planning_signed_link', 'act_planning_signed_yandex_path', 'act_planning_signed_file_name',
                            'act_concept_signed_link', 'act_concept_signed_yandex_path', 'act_concept_signed_file_name',
                            'info_letter_signed_link', 'info_letter_signed_yandex_path', 'info_letter_signed_file_name',
                            'act_final_signed_link', 'act_final_signed_yandex_path', 'act_final_signed_file_name',
                        ]
                        for f in _nf:
                            if not contract_data.get(f) and local.get(f):
                                contract_data[f] = local[f]
                except Exception:
                    pass

            self.contract_data = contract_data

            # Обновляем файл договора (индивидуальный)
            cf_link = contract_data.get('contract_file_link', '')
            cf_yp = contract_data.get('contract_file_yandex_path', '')
            if cf_link or cf_yp:
                file_name = contract_data.get('contract_file_name', '') or 'Договор.pdf'
                truncated_name = self.truncate_filename(file_name)
                if cf_link:
                    html_link = f'<a href="{cf_link}" title="{file_name}">{truncated_name}</a>'
                else:
                    html_link = truncated_name
                self.contract_file_label.setText(html_link)
                self.contract_file_delete_btn.setVisible(not self.view_only)
                self.contract_upload_btn.setEnabled(False)
            else:
                self.contract_file_label.setText('Не загружен')
                self.contract_file_delete_btn.setVisible(False)
                self.contract_upload_btn.setEnabled(not self.view_only)

            # Обновляем файл договора (шаблонный)
            tcf_link = contract_data.get('template_contract_file_link', '')
            tcf_yp = contract_data.get('template_contract_file_yandex_path', '')
            if tcf_link or tcf_yp:
                file_name = contract_data.get('template_contract_file_name', '') or 'Договор.pdf'
                truncated_name = self.truncate_filename(file_name)
                if tcf_link:
                    html_link = f'<a href="{tcf_link}" title="{file_name}">{truncated_name}</a>'
                else:
                    html_link = truncated_name
                self.template_contract_file_label.setText(html_link)
                self.template_contract_file_delete_btn.setVisible(not self.view_only)
                self.template_contract_upload_btn.setEnabled(False)
            else:
                self.template_contract_file_label.setText('Не загружен')
                self.template_contract_file_delete_btn.setVisible(False)
                self.template_contract_upload_btn.setEnabled(not self.view_only)

            # Обновляем тех.задание
            tt_link = contract_data.get('tech_task_link', '')
            tt_yp = contract_data.get('tech_task_yandex_path', '')
            if tt_link or tt_yp:
                file_name = contract_data.get('tech_task_file_name', '') or 'ТехЗадание.pdf'
                truncated_name = self.truncate_filename(file_name)
                if tt_link:
                    html_link = f'<a href="{tt_link}" title="{file_name}">{truncated_name}</a>'
                else:
                    html_link = truncated_name
                self.tech_task_file_label.setText(html_link)
                self.tech_task_file_delete_btn.setVisible(not self.view_only)
                self.tech_task_upload_btn.setEnabled(False)
            else:
                self.tech_task_file_label.setText('Не загружен')
                self.tech_task_file_delete_btn.setVisible(False)
                self.tech_task_upload_btn.setEnabled(not self.view_only)

            # Обновляем акты и информационное письмо (без подписи + с подписью)
            _doc_defaults = {
                'act_planning': 'Акт ПР.pdf',
                'act_concept': 'Акт КД.pdf',
                'info_letter': 'Инф. письмо.pdf',
                'act_final': 'Акт финальный.pdf',
                'act_planning_signed': 'Акт ПР (подписан).pdf',
                'act_concept_signed': 'Акт КД (подписан).pdf',
                'info_letter_signed': 'Инф. письмо (подписано).pdf',
                'act_final_signed': 'Акт финальный (подписан).pdf',
            }
            for prefix, default_name in _doc_defaults.items():
                link = contract_data.get(f'{prefix}_link', '')
                yp = contract_data.get(f'{prefix}_yandex_path', '')
                if link or yp:
                    file_name = contract_data.get(f'{prefix}_file_name', '') or default_name
                    truncated_name = self.truncate_filename(file_name)
                    if link:
                        html_link = f'<a href="{link}" title="{file_name}">{truncated_name}</a>'
                    else:
                        html_link = truncated_name
                    getattr(self, f'{prefix}_file_label').setText(html_link)
                    getattr(self, f'{prefix}_file_delete_btn').setVisible(not self.view_only)
                    getattr(self, f'{prefix}_upload_btn').setEnabled(False)
                else:
                    getattr(self, f'{prefix}_file_label').setText('Не загружен')
                    getattr(self, f'{prefix}_file_delete_btn').setVisible(False)
                    getattr(self, f'{prefix}_upload_btn').setEnabled(not self.view_only)

                # Зеркалим в шаблонные виджеты
                tpl_lbl = getattr(self, f'tpl_{prefix}_file_label', None)
                if tpl_lbl:
                    if link or yp:
                        tpl_lbl.setText(html_link)
                        tpl_del = getattr(self, f'tpl_{prefix}_file_delete_btn', None)
                        tpl_up = getattr(self, f'tpl_{prefix}_upload_btn', None)
                        if tpl_del:
                            tpl_del.setVisible(not self.view_only)
                        if tpl_up:
                            tpl_up.setEnabled(False)
                    else:
                        tpl_lbl.setText('Не загружен')
                        tpl_del = getattr(self, f'tpl_{prefix}_file_delete_btn', None)
                        tpl_up = getattr(self, f'tpl_{prefix}_upload_btn', None)
                        if tpl_del:
                            tpl_del.setVisible(False)
                        if tpl_up:
                            tpl_up.setEnabled(not self.view_only)

    def upload_contract_file(self, project_type):
        """Загрузка файла договора на Яндекс.Диск"""
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
        progress = create_progress_dialog("Загрузка файла", "Подготовка к загрузке...", "Отмена", 3, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if cancel_event.is_set():
                        return
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    label_text = f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Документы",
                    file_name,
                    progress_callback=update_progress
                )

                if result:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 3))
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.contract_file_upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name'],
                        project_type
                    )
                else:
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.contract_file_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
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
                self.contract_file_yandex_path_attr = yandex_path
                self.contract_file_name_attr = file_name
            else:
                self.template_contract_file_path = public_link
                self.template_contract_file_yandex_path_attr = yandex_path
                self.template_contract_file_name_attr = file_name

            # Сохраняем в базу данных, если договор уже существует
            if self.contract_data and self.contract_data.get('id'):
                contract_id = self.contract_data['id']

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
                    self.data.update_contract(contract_id, update_data)
                    self.contract_data = self.data.get_contract(contract_id)
                except Exception as e:
                    print(f"[WARNING] Ошибка обновления contract через DataAccess: {e}")

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
        progress = create_progress_dialog("Загрузка файла", "Подготовка к загрузке...", "Отмена", 3, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if cancel_event.is_set():
                        return
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    label_text = f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Анкета",
                    file_name,
                    progress_callback=update_progress
                )

                if result:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 3))
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.tech_task_upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name']
                    )
                else:
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.tech_task_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
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

                try:
                    update_data = {
                        'tech_task_link': public_link,
                        'tech_task_yandex_path': yandex_path,
                        'tech_task_file_name': file_name
                    }
                    self.data.update_contract(contract_id, update_data)
                    self.contract_data = self.data.get_contract(contract_id)
                except Exception as e:
                    print(f"[WARNING] Ошибка обновления contract через DataAccess: {e}")

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

    # === Обобщённые методы для новых файловых полей (акты/инф.письмо) ===

    def _open_doc_file(self, prefix):
        """Открытие файла по префиксу поля"""
        path = getattr(self, f'{prefix}_file_path', None)
        if path:
            QDesktopServices.openUrl(QUrl(path))

    def _upload_doc_file(self, prefix, display_name):
        """Загрузка файла акта/письма в папку Документы на ЯД"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Выберите файл: {display_name}", "",
            "PDF Files (*.pdf);;Документы (*.pdf *.docx *.doc)"
        )
        if not file_path:
            return

        contract_folder = self.get_contract_yandex_folder()
        if not contract_folder:
            CustomMessageBox(self, 'Ошибка',
                'Сначала сохраните договор, чтобы создать папку на Яндекс.Диске', 'warning').exec_()
            return

        file_name = os.path.basename(file_path)

        progress = create_progress_dialog("Загрузка файла", "Подготовка к загрузке...", "Отмена", 3, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if cancel_event.is_set():
                        return
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    phase_names = {'preparing': 'Подготовка...', 'uploading': 'Загрузка на Яндекс.Диск...', 'finalizing': 'Завершение...'}
                    percent = int((step / 3) * 100)
                    label_text = f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                result = yd.upload_file_to_contract_folder(
                    file_path, contract_folder, "Документы", file_name,
                    progress_callback=update_progress
                )

                if result:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 3))
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.doc_file_upload_completed.emit(
                        prefix, result['public_link'], result['yandex_path'], result['file_name']
                    )
                else:
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.doc_file_upload_error.emit(prefix, "Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                import traceback
                traceback.print_exc()
                self.doc_file_upload_error.emit(prefix, str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_doc_file_uploaded(self, prefix, public_link, yandex_path, file_name):
        """Обработчик успешной загрузки файла акта/письма/чека"""
        is_receipt = prefix.endswith('_receipt')

        if public_link:
            setattr(self, f'{prefix}_file_path', public_link)
            setattr(self, f'{prefix}_yandex_path', yandex_path)
            setattr(self, f'{prefix}_file_name', file_name)

            if self.contract_data and self.contract_data.get('id'):
                contract_id = self.contract_data['id']
                update_data = {
                    f'{prefix}_link': public_link,
                    f'{prefix}_yandex_path': yandex_path,
                    f'{prefix}_file_name': file_name
                }
                try:
                    self.data.update_contract(contract_id, update_data)
                    # Обновляем локальные данные
                    for k, v in update_data.items():
                        self.contract_data[k] = v
                except Exception as e:
                    print(f"[WARNING] Ошибка обновления {prefix}: {e}")

            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>'

            if is_receipt:
                # Чек: дизейблим receipt_btn, показываем view + delete
                # prefix = 'advance_receipt' → payment_prefix = 'advance_payment'
                payment_prefix = prefix.replace('_receipt', '_payment')
                for wp in (payment_prefix, f'tpl_{payment_prefix}'):
                    btn = getattr(self, f'{wp}_receipt_btn', None)
                    del_btn = getattr(self, f'{wp}_receipt_delete_btn', None)
                    view_btn = getattr(self, f'{wp}_receipt_view_btn', None)
                    if btn:
                        btn.setEnabled(False)
                    if del_btn:
                        del_btn.setVisible(True)
                    if view_btn:
                        view_btn.setVisible(True)
            else:
                # Акт/документ: стандартная логика
                getattr(self, f'{prefix}_file_label').setText(html_link)
                getattr(self, f'{prefix}_file_delete_btn').setVisible(True)
                getattr(self, f'{prefix}_upload_btn').setEnabled(False)
                # Зеркалим в шаблонный виджет
                tpl_lbl = getattr(self, f'tpl_{prefix}_file_label', None)
                if tpl_lbl:
                    tpl_lbl.setText(html_link)
                    tpl_del = getattr(self, f'tpl_{prefix}_file_delete_btn', None)
                    tpl_up = getattr(self, f'tpl_{prefix}_upload_btn', None)
                    if tpl_del:
                        tpl_del.setVisible(True)
                    if tpl_up:
                        tpl_up.setEnabled(False)
        else:
            if is_receipt:
                CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить чек на Яндекс.Диск', 'error').exec_()
            else:
                getattr(self, f'{prefix}_file_label').setText('Не загружен')
                CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл на Яндекс.Диск', 'error').exec_()

    def _on_doc_file_upload_error(self, prefix, error_msg):
        """Обработчик ошибки загрузки файла акта/письма"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файла: {error_msg}', 'error').exec_()

    def _mark_payment_paid(self, prefix):
        """Отметка платежа как оплаченного (сохраняет дату в БД)"""
        if not self.contract_data or not self.contract_data.get('id'):
            CustomMessageBox(self, 'Ошибка', 'Сначала сохраните договор', 'warning').exec_()
            return

        # Проверяем сумму платежа
        money_input = getattr(self, prefix, None)
        if money_input and money_input.value() <= 0:
            CustomMessageBox(self, 'Ошибка', 'Укажите сумму платежа перед отметкой оплаты', 'warning').exec_()
            return

        today = QDate.currentDate().toString('yyyy-MM-dd')
        date_field = f'{prefix}_paid_date'
        update_data = {date_field: today}

        try:
            contract_id = self.contract_data['id']
            self.data.update_contract(contract_id, update_data)

            # Обновить локальные данные
            self.contract_data[date_field] = today

            # Обновить UI (оба набора виджетов — индивидуальный и шаблонный)
            display_date = QDate.fromString(today, 'yyyy-MM-dd').toString('dd.MM.yyyy')
            _paid_date_active = '''
                QLabel {
                    background-color: #F8F9FA; padding: 2px 8px; border: 1px solid #E0E0E0;
                    border-radius: 6px; font-size: 11px; color: #27AE60; font-weight: 600;
                    min-width: 120px; min-height: 16px;
                }
            '''
            for widget_prefix in (prefix, f'tpl_{prefix}'):
                paid_label = getattr(self, f'{widget_prefix}_paid_label', None)
                paid_btn = getattr(self, f'{widget_prefix}_paid_btn', None)
                if paid_label:
                    paid_label.setText(display_date)
                    paid_label.setStyleSheet(_paid_date_active)
                if paid_btn:
                    paid_btn.setEnabled(False)
                    paid_btn.setToolTip(f'Оплачено {display_date}')

            # Блокируем поле суммы после оплаты
            money_input = getattr(self, prefix, None)
            if money_input:
                money_input.setReadOnly(True)
                money_input.setStyleSheet('QLineEdit { background-color: #F0F0F0; padding: 2px 8px; min-height: 24px; max-height: 24px; }')
            # Шаблонный аналог
            _locked_style = 'QLineEdit { background-color: #F0F0F0; padding: 2px 8px; min-height: 24px; max-height: 24px; }'
            tpl_money = getattr(self, f'tpl_{prefix}', None)
            if tpl_money:
                tpl_money.setReadOnly(True)
                tpl_money.setStyleSheet(_locked_style)
            if prefix == 'advance_payment':
                tpl_paid_amt = getattr(self, 'template_paid_amount', None)
                if tpl_paid_amt:
                    tpl_paid_amt.setReadOnly(True)
                    tpl_paid_amt.setStyleSheet(_locked_style)

        except Exception as e:
            print(f"[ERROR] Ошибка отметки оплаты {prefix}: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить дату оплаты: {e}', 'error').exec_()

    def _upload_receipt_file(self, prefix):
        """Загрузка чека платежа в папку Документы на ЯД"""
        if not self.contract_data or not self.contract_data.get('id'):
            CustomMessageBox(self, 'Ошибка', 'Сначала сохраните договор', 'warning').exec_()
            return

        # Маппинг prefix → отображаемое имя для диалога
        display_names = {
            'advance_payment': 'Чек аванса',
            'additional_payment': 'Чек 2-го платежа',
            'third_payment': 'Чек 3-го платежа',
        }
        display_name = display_names.get(prefix, 'Чек')

        # Маппинг prefix → prefix для receipt полей в БД
        receipt_prefix_map = {
            'advance_payment': 'advance_receipt',
            'additional_payment': 'additional_receipt',
            'third_payment': 'third_receipt',
        }
        receipt_prefix = receipt_prefix_map.get(prefix, prefix)

        file_path, _ = QFileDialog.getOpenFileName(
            self, f"Выберите файл: {display_name}", "",
            "Изображения и PDF (*.pdf *.jpg *.jpeg *.png);;Все файлы (*.*)"
        )
        if not file_path:
            return

        contract_folder = self.get_contract_yandex_folder()
        if not contract_folder:
            CustomMessageBox(self, 'Ошибка',
                'Сначала сохраните договор, чтобы создать папку на Яндекс.Диске', 'warning').exec_()
            return

        file_name = os.path.basename(file_path)

        progress = create_progress_dialog("Загрузка чека", "Подготовка к загрузке...", "Отмена", 3, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if cancel_event.is_set():
                        return
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    phase_names = {'preparing': 'Подготовка...', 'uploading': 'Загрузка на Яндекс.Диск...', 'finalizing': 'Завершение...'}
                    percent = int((step / 3) * 100)
                    label_text = f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                result = yd.upload_file_to_contract_folder(
                    file_path, contract_folder, "Документы", file_name,
                    progress_callback=update_progress
                )

                if result:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 3))
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.doc_file_upload_completed.emit(
                        receipt_prefix, result['public_link'], result['yandex_path'], result['file_name']
                    )
                else:
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.doc_file_upload_error.emit(receipt_prefix, "Не удалось загрузить чек на Яндекс.Диск")

            except Exception as e:
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                import traceback
                traceback.print_exc()
                self.doc_file_upload_error.emit(receipt_prefix, str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _view_receipt_file(self, payment_prefix):
        """Открытие чека в браузере"""
        receipt_prefix_map = {
            'advance_payment': 'advance_receipt',
            'additional_payment': 'additional_receipt',
            'third_payment': 'third_receipt',
        }
        receipt_prefix = receipt_prefix_map.get(payment_prefix, payment_prefix)
        link = getattr(self, f'{receipt_prefix}_file_path', None)
        if link and link.startswith('http'):
            QDesktopServices.openUrl(QUrl(link))
        else:
            CustomMessageBox(self, 'Ошибка', 'Ссылка на чек недоступна', 'warning').exec_()

    def _delete_receipt_file(self, payment_prefix):
        """Удаление чека платежа"""
        if not self.contract_data or not self.contract_data.get('id'):
            CustomMessageBox(self, 'Ошибка', 'Сначала сохраните договор', 'warning').exec_()
            return

        receipt_prefix_map = {
            'advance_payment': 'advance_receipt',
            'additional_payment': 'additional_receipt',
            'third_payment': 'third_receipt',
        }
        receipt_prefix = receipt_prefix_map.get(payment_prefix, payment_prefix)

        reply = CustomQuestionBox(
            self, 'Подтверждение',
            'Удалить загруженный чек?',
            'Удалить', 'Отмена'
        ).exec_()
        if reply != QDialog.Accepted:
            return

        try:
            contract_id = self.contract_data['id']
            # Удаляем файл с Яндекс.Диска
            yandex_path = getattr(self, f'{receipt_prefix}_yandex_path', None)
            if yandex_path:
                try:
                    self.data.delete_yandex_file(yandex_path)
                except Exception as e:
                    print(f"[WARN] Не удалось удалить чек с Яндекс.Диска: {e}")

            # Очищаем поля в БД через DataAccess
            update_data = {
                f'{receipt_prefix}_link': '',
                f'{receipt_prefix}_yandex_path': '',
                f'{receipt_prefix}_file_name': '',
            }
            self.data.update_contract(contract_id, update_data)

            # Очищаем UI
            setattr(self, f'{receipt_prefix}_file_path', None)
            setattr(self, f'{receipt_prefix}_yandex_path', None)
            setattr(self, f'{receipt_prefix}_file_name', None)
            for wp in (payment_prefix, f'tpl_{payment_prefix}'):
                receipt_btn = getattr(self, f'{wp}_receipt_btn', None)
                if receipt_btn:
                    receipt_btn.setEnabled(True)
                receipt_del_btn = getattr(self, f'{wp}_receipt_delete_btn', None)
                if receipt_del_btn:
                    receipt_del_btn.setVisible(False)
                receipt_view_btn = getattr(self, f'{wp}_receipt_view_btn', None)
                if receipt_view_btn:
                    receipt_view_btn.setVisible(False)

            CustomMessageBox(self, 'Успех', 'Чек удалён', 'success').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка при удалении чека: {str(e)}', 'error').exec_()

    def _delete_doc_file(self, prefix, display_name):
        """Удаление файла акта/письма"""
        if not self.contract_data:
            CustomMessageBox(self, 'Ошибка', 'Сначала сохраните договор', 'warning').exec_()
            return

        reply = CustomQuestionBox(
            self, 'Подтверждение',
            f'Вы уверены, что хотите удалить файл "{display_name}"?'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        contract_id = self.contract_data['id']
        yandex_path = getattr(self, f'{prefix}_yandex_path', None)

        # Сначала удаляем файл с Яндекс.Диска (до очистки БД!)
        if yandex_path:
            try:
                self.data.delete_yandex_file(yandex_path)
                print(f"[INFO] Файл {display_name} удален с Яндекс.Диска: {yandex_path}")
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл с ЯД: {e}")
                CustomMessageBox(self, 'Ошибка', 'Не удалось удалить файл с Яндекс.Диска. Попробуйте позже.', 'error').exec_()
                return

        # Обновляем БД/API только после успешного удаления с ЯД
        update_data = {
            f'{prefix}_link': '',
            f'{prefix}_yandex_path': '',
            f'{prefix}_file_name': ''
        }
        try:
            self.data.update_contract(contract_id, update_data)

            getattr(self, f'{prefix}_file_label').setText('Не загружен')
            setattr(self, f'{prefix}_file_path', None)
            setattr(self, f'{prefix}_yandex_path', None)
            setattr(self, f'{prefix}_file_name', None)
            getattr(self, f'{prefix}_file_delete_btn').setVisible(False)
            getattr(self, f'{prefix}_upload_btn').setEnabled(True)
            # Зеркалим в шаблонный виджет
            tpl_lbl = getattr(self, f'tpl_{prefix}_file_label', None)
            if tpl_lbl:
                tpl_lbl.setText('Не загружен')
                tpl_del = getattr(self, f'tpl_{prefix}_file_delete_btn', None)
                tpl_up = getattr(self, f'tpl_{prefix}_upload_btn', None)
                if tpl_del:
                    tpl_del.setVisible(False)
                if tpl_up:
                    tpl_up.setEnabled(True)

            CustomMessageBox(self, 'Успех', f'Файл "{display_name}" успешно удален', 'success').exec_()
            self.files_verification_completed.emit()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка при удалении файла: {str(e)}', 'error').exec_()

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
            contract = self.data.get_contract(contract_id)
            if contract:
                contract_yandex_path = contract.get('contract_file_yandex_path')
                template_yandex_path = contract.get('template_contract_file_yandex_path')
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к файлам: {e}")

        # Сначала удаляем файлы с Яндекс.Диска (до очистки БД!)
        yd_delete_ok = True
        if contract_yandex_path:
            try:
                self.data.delete_yandex_file(contract_yandex_path)
                print(f"[INFO] Файл договора удален с Яндекс.Диска: {contract_yandex_path}")
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл договора с Яндекс.Диска: {e}")
                yd_delete_ok = False

        if template_yandex_path:
            try:
                self.data.delete_yandex_file(template_yandex_path)
                print(f"[INFO] Файл шаблонного договора удален с Яндекс.Диска: {template_yandex_path}")
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл шаблонного договора с Яндекс.Диска: {e}")
                yd_delete_ok = False

        if not yd_delete_ok:
            CustomMessageBox(self, 'Ошибка', 'Не удалось удалить файл с Яндекс.Диска. Попробуйте позже.', 'error').exec_()
            return

        # Обновляем БД через DataAccess после успешного удаления с ЯД
        update_data = {
            'contract_file_link': '',
            'contract_file_yandex_path': '',
            'contract_file_name': '',
            'template_contract_file_link': '',
            'template_contract_file_yandex_path': '',
            'template_contract_file_name': ''
        }
        try:
            self.data.update_contract(contract_id, update_data)

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

        # Сначала удаляем файл с Яндекс.Диска (до очистки БД!)
        if yandex_path:
            try:
                self.data.delete_yandex_file(yandex_path)
                print(f"[INFO] Файл ТЗ удален с Яндекс.Диска: {yandex_path}")
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")
                CustomMessageBox(self, 'Ошибка', 'Не удалось удалить файл с Яндекс.Диска. Попробуйте позже.', 'error').exec_()
                return

        # Обновляем БД через DataAccess после успешного удаления с ЯД
        update_data = {
            'tech_task_link': '',
            'tech_task_yandex_path': '',
            'tech_task_file_name': ''
        }
        try:
            self.data.update_contract(contract_id, update_data)

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

    @debounce_click(delay_ms=2000)
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
        existing = self.data.check_contract_number_exists(contract_number, exclude_id=current_contract_id)
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
            'project_subtype': self.project_subtype.currentText(),
            'floors': self.floors_spin.value() if hasattr(self, 'floors_spin') else 1,
            'agent_type': self.agent_combo.currentText(),
            'city': self.city_combo.currentText(),
            'contract_number': contract_number,
            'contract_date': self.contract_date.date().toString('yyyy-MM-dd'),
            'address': self.address.text().strip(),
            'area': self.area.value(),
            'total_amount': self.total_amount.value(),
            'advance_payment': self.template_paid_amount.value() if project_type == 'Шаблонный' else self.advance_payment.value(),
            'additional_payment': 0 if project_type == 'Шаблонный' else self.additional_payment.value(),
            'third_payment': 0 if project_type == 'Шаблонный' else self.third_payment.value(),
            'contract_period': contract_period,
            'contract_file_link': contract_file_link,
            'contract_file_yandex_path': getattr(self, 'contract_file_yandex_path_attr', '') or (self.contract_data or {}).get('contract_file_yandex_path', '') or '',
            'contract_file_name': getattr(self, 'contract_file_name_attr', '') or (self.contract_data or {}).get('contract_file_name', '') or '',
            'template_contract_file_link': getattr(self, 'template_contract_file_path', '') or '',
            'template_contract_file_yandex_path': getattr(self, 'template_contract_file_yandex_path_attr', '') or (self.contract_data or {}).get('template_contract_file_yandex_path', '') or '',
            'template_contract_file_name': getattr(self, 'template_contract_file_name_attr', '') or (self.contract_data or {}).get('template_contract_file_name', '') or '',
            'tech_task_link': tech_task_link,
            'tech_task_yandex_path': tech_task_yandex_path,
            'tech_task_file_name': tech_task_file_name,
            'act_planning_link': getattr(self, 'act_planning_file_path', '') or '',
            'act_planning_yandex_path': getattr(self, 'act_planning_yandex_path', '') or '',
            'act_planning_file_name': getattr(self, 'act_planning_file_name', '') or '',
            'act_concept_link': getattr(self, 'act_concept_file_path', '') or '',
            'act_concept_yandex_path': getattr(self, 'act_concept_yandex_path', '') or '',
            'act_concept_file_name': getattr(self, 'act_concept_file_name', '') or '',
            'info_letter_link': getattr(self, 'info_letter_file_path', '') or '',
            'info_letter_yandex_path': getattr(self, 'info_letter_yandex_path', '') or '',
            'info_letter_file_name': getattr(self, 'info_letter_file_name', '') or '',
            'act_final_link': getattr(self, 'act_final_file_path', '') or '',
            'act_final_yandex_path': getattr(self, 'act_final_yandex_path', '') or '',
            'act_final_file_name': getattr(self, 'act_final_file_name', '') or '',
            # Подписанные акты
            'act_planning_signed_link': getattr(self, 'act_planning_signed_file_path', '') or '',
            'act_planning_signed_yandex_path': getattr(self, 'act_planning_signed_yandex_path', '') or '',
            'act_planning_signed_file_name': getattr(self, 'act_planning_signed_file_name', '') or '',
            'act_concept_signed_link': getattr(self, 'act_concept_signed_file_path', '') or '',
            'act_concept_signed_yandex_path': getattr(self, 'act_concept_signed_yandex_path', '') or '',
            'act_concept_signed_file_name': getattr(self, 'act_concept_signed_file_name', '') or '',
            'info_letter_signed_link': getattr(self, 'info_letter_signed_file_path', '') or '',
            'info_letter_signed_yandex_path': getattr(self, 'info_letter_signed_yandex_path', '') or '',
            'info_letter_signed_file_name': getattr(self, 'info_letter_signed_file_name', '') or '',
            'act_final_signed_link': getattr(self, 'act_final_signed_file_path', '') or '',
            'act_final_signed_yandex_path': getattr(self, 'act_final_signed_yandex_path', '') or '',
            'act_final_signed_file_name': getattr(self, 'act_final_signed_file_name', '') or '',
            # Даты оплат (сохраняются мгновенно через _mark_payment_paid, но включаем для полноты)
            'advance_payment_paid_date': (self.contract_data or {}).get('advance_payment_paid_date', '') or '',
            'additional_payment_paid_date': (self.contract_data or {}).get('additional_payment_paid_date', '') or '',
            'third_payment_paid_date': (self.contract_data or {}).get('third_payment_paid_date', '') or '',
            # Чеки платежей
            'advance_receipt_link': getattr(self, 'advance_receipt_file_path', '') or '',
            'advance_receipt_yandex_path': getattr(self, 'advance_receipt_yandex_path', '') or '',
            'advance_receipt_file_name': getattr(self, 'advance_receipt_file_name', '') or '',
            'additional_receipt_link': getattr(self, 'additional_receipt_file_path', '') or '',
            'additional_receipt_yandex_path': getattr(self, 'additional_receipt_yandex_path', '') or '',
            'additional_receipt_file_name': getattr(self, 'additional_receipt_file_name', '') or '',
            'third_receipt_link': getattr(self, 'third_receipt_file_path', '') or '',
            'third_receipt_yandex_path': getattr(self, 'third_receipt_yandex_path', '') or '',
            'third_receipt_file_name': getattr(self, 'third_receipt_file_name', '') or '',
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

                # Обновляем договор через DataAccess (API + локальная БД)
                self.data.update_contract(self.contract_data['id'], contract_data)

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
                            # Обновляем путь в БД через DataAccess
                            self.data.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
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
                                # Сохраняем новый путь через DataAccess (будет актуален после синхронизации)
                                self.data.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
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
                                self.data.update_contract(self.contract_data['id'], {'yandex_folder_path': new_folder_path})
                                print(f"[QUEUE] Переименование папки добавлено в очередь: {old_folder_path} -> {new_folder_path}")
                            except Exception as queue_error:
                                print(f"[ERROR] Не удалось добавить в очередь: {queue_error}")
            else:
                # Создание нового договора через DataAccess
                new_contract_id = None
                result = self.data.create_contract(contract_data)
                if result:
                    new_contract_id = result.get('id')

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

                        # Обновить путь к папке в договоре через DataAccess
                        if folder_path:
                            self.data.update_contract(new_contract_id, {'yandex_folder_path': folder_path})
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
                border: 1px solid #E0E0E0;
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
        # Получаем DataAccess из parent (ContractDialog), иначе создаём новый
        self.data = getattr(parent, 'data', None) or DataAccess()
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
                border: 1px solid #E0E0E0;
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

        agents = self.data.get_all_agents()
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
        self.color_preview.setStyleSheet('background-color: #ffd93c; border: 1px solid #E0E0E0; border-radius: 6px;')
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

        if self.data.add_agent(name, self.selected_color):
            CustomMessageBox(self, 'Успех', f'Агент "{name}" добавлен', 'success').exec_()
            self.accept()
        else:
            CustomMessageBox(self, 'Ошибка', 'Не удалось добавить агента', 'error').exec_()

    def edit_agent_color(self, agent_name):
        """Редактирование цвета агента"""
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor()
        if color.isValid():
            if self.data.update_agent_color(agent_name, color.name()):
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
