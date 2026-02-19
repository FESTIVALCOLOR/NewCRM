# -*- coding: utf-8 -*-
"""
Диалог администрирования мессенджер-чатов (только для Директора).
Вкладки:
  1. Telegram — настройки подключения
  2. Email (SMTP) — настройки почты для invite-ссылок
  3. Скрипты — шаблоны сообщений с плейсхолдерами, вкл/выкл
"""
import logging
from typing import Optional, Dict, Any, List

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QWidget, QFormLayout, QLineEdit,
    QCheckBox, QTextEdit, QComboBox, QListWidget, QListWidgetItem,
    QGroupBox, QGridLayout, QScrollArea, QSizePolicy, QSpinBox,
    QStackedWidget, QSplitter,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QColor

from utils.resource_path import resource_path
from utils.icon_loader import IconLoader

logger = logging.getLogger(__name__)

# Стиль кнопки toggle-пароля (глаз)
_EYE_BTN_STYLE = """
    QPushButton {
        background-color: transparent;
        border: none;
        padding: 4px;
    }
    QPushButton:hover { background-color: #f0f0f0; border-radius: 4px; }
"""

# Стили
_INPUT_STYLE = """
    QLineEdit {
        border: 1px solid #d9d9d9;
        border-radius: 6px;
        padding: 7px 10px;
        font-size: 13px;
        background-color: #ffffff;
    }
    QLineEdit:focus { border-color: #ffd93c; }
    QLineEdit:disabled { background-color: #f5f5f5; color: #999; }
"""

_TEXTEDIT_STYLE = """
    QTextEdit {
        border: 1px solid #d9d9d9;
        border-radius: 6px;
        padding: 6px 8px;
        font-size: 13px;
        background-color: #ffffff;
    }
    QTextEdit:focus { border-color: #ffd93c; }
"""

_COMBO_STYLE = """
    QComboBox {
        border: 1px solid #d9d9d9;
        border-radius: 6px;
        padding: 6px 10px;
        font-size: 13px;
        background-color: #ffffff;
    }
    QComboBox:focus { border-color: #ffd93c; }
    QComboBox::drop-down {
        border-left: 1px solid #d9d9d9;
        width: 28px;
    }
"""

_TAB_STYLE = """
    QTabWidget::pane {
        border: 1px solid #e0e0e0;
        border-radius: 6px;
        background-color: #ffffff;
        top: -1px;
    }
    QTabBar::tab {
        background-color: #f5f5f5;
        border: 1px solid #e0e0e0;
        border-bottom: none;
        padding: 8px 16px;
        font-size: 13px;
        margin-right: 2px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
    }
    QTabBar::tab:selected {
        background-color: #ffffff;
        font-weight: 600;
        border-bottom: 2px solid #ffd93c;
    }
    QTabBar::tab:hover:!selected { background-color: #fafafa; }
"""

# Плейсхолдеры для скриптов
SCRIPT_PLACEHOLDERS = {
    "{client_name}": "Имя клиента",
    "{project_name}": "Название проекта (номер договора)",
    "{stage_name}": "Название стадии",
    "{substage_name}": "Название подэтапа",
    "{deadline}": "Дата дедлайна (ДД.ММ.ГГГГ)",
    "{manager_name}": "Имя менеджера",
    "{senior_manager}": "Старший менеджер (СДП)",
    "{director}": "Директор",
    "{address}": "Адрес объекта",
    "{city}": "Город",
}

SCRIPT_TYPES = {
    "project_start": "Начало проекта",
    "stage_complete": "Завершение стадии",
    "project_end": "Завершение проекта",
    "project_paused": "Приостановка проекта",
    "custom": "Пользовательский",
}

# Стадии CRM для уведомлений, сгруппированные по типу проекта
CRM_STAGE_GROUPS = {
    "Индивидуальный проект": [
        ("Стадия 1: планировочные решения", [
            "Подэтап 1.1: Разработка планировок",
            "Подэтап 1.2: Фин. план. решение (1 круг)",
            "Подэтап 1.3: Фин. план. решение (2 круг)",
        ]),
        ("Стадия 2: концепция дизайна", [
            "Подэтап 2.1: Мудборды",
            "Подэтап 2.2: Визуализация 1 помещения",
            "Подэтап 2.3: Виз. 1 пом. (1 круг правок)",
            "Подэтап 2.4: Виз. 1 пом. (2 круг правок)",
            "Подэтап 2.5: Визуализация остальных помещений",
            "Подэтап 2.6: Виз. все (1 круг правок)",
            "Подэтап 2.7: Виз. все (2 круг правок)",
        ]),
        ("Стадия 3: рабочие чертежи", []),
        ("Стадия 3: 3д визуализация (Доп.)", []),
        ("Выполненный проект", []),
    ],
    "Шаблонный проект": [
        ("Стадия 1: планировочные решения", [
            "Подэтап 1.1: Разработка планировок",
            "Подэтап 1.2: Финальное план. решение",
        ]),
        ("Стадия 2: рабочие чертежи", []),
        ("Стадия 3: 3д визуализация (Доп.)", []),
        ("Выполненный проект", []),
    ],
    "Надзор": [
        ("Стадия 1: Закупка керамогранита", []),
        ("Стадия 2: Закупка сантехники", []),
        ("Стадия 3: Закупка оборудования", []),
        ("Стадия 4: Закупка дверей и окон", []),
        ("Стадия 5: Закупка настенных материалов", []),
        ("Стадия 6: Закупка напольных материалов", []),
        ("Стадия 7: Лепной декор", []),
        ("Стадия 8: Освещение", []),
        ("Стадия 9: Бытовая техника", []),
        ("Стадия 10: Закупка заказной мебели", []),
        ("Стадия 11: Закупка фабричной мебели", []),
        ("Стадия 12: Закупка декора", []),
        ("Выполненный проект", []),
    ],
}


class MessengerAdminDialog(QDialog):
    """Диалог администрирования мессенджер-системы"""

    def __init__(self, parent, api_client, data_access, employee: Dict):
        super().__init__(parent)
        self.api_client = api_client
        self.data_access = data_access
        self.employee = employee or {}

        self._settings: Dict[str, str] = {}
        self._scripts: List[Dict] = []
        self._current_script_id: Optional[int] = None

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumSize(680, 560)
        self.setMaximumSize(780, 700)

        self._init_ui()
        self._load_data()

    # ================================================================
    # UI
    # ================================================================

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        frame_layout = QVBoxLayout(border_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        from ui.custom_title_bar import CustomTitleBar
        title_bar = CustomTitleBar(self, "Администрирование чатов", simple_mode=True)
        frame_layout.addWidget(title_bar)

        # Табы
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(16, 8, 16, 16)
        content_layout.setSpacing(10)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(_TAB_STYLE)

        self._tab_telegram = self._create_telegram_tab()
        self._tab_email = self._create_email_tab()
        self._tab_scripts = self._create_scripts_tab()

        self._tabs.addTab(self._tab_telegram, "Telegram")
        self._tabs.addTab(self._tab_email, "Email (SMTP)")
        self._tabs.addTab(self._tab_scripts, "Скрипты")

        content_layout.addWidget(self._tabs)

        # Нижняя панель
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)

        # Статус подключения
        self._status_label = QLabel("")
        self._status_label.setStyleSheet("font-size: 12px; color: #999;")
        bottom_row.addWidget(self._status_label)

        bottom_row.addStretch()

        save_btn = QPushButton("Сохранить")
        save_btn.setFixedHeight(38)
        save_btn.setCursor(Qt.PointingHandCursor)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                border: none;
                border-radius: 6px;
                padding: 0 30px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        save_btn.clicked.connect(self._on_save)
        bottom_row.addWidget(save_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(38)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 0 24px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #f5f5f5; }
        """)
        close_btn.clicked.connect(self.close)
        bottom_row.addWidget(close_btn)

        content_layout.addLayout(bottom_row)
        frame_layout.addWidget(content)
        root.addWidget(border_frame)

    # ----------------------------------------------------------------
    # Поле пароля с кнопкой-глазом
    # ----------------------------------------------------------------

    def _make_password_field(self, placeholder: str = "") -> tuple:
        """Создать QLineEdit с кнопкой toggle-видимости (глаз).
        Возвращает (container_widget, line_edit)."""
        container = QWidget()
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(4)

        edit = QLineEdit()
        edit.setPlaceholderText(placeholder)
        edit.setStyleSheet(_INPUT_STYLE)
        edit.setEchoMode(QLineEdit.Password)
        h.addWidget(edit)

        eye_btn = QPushButton()
        eye_btn.setFixedSize(30, 30)
        eye_btn.setCursor(Qt.PointingHandCursor)
        eye_btn.setStyleSheet(_EYE_BTN_STYLE)
        eye_btn.setToolTip("Показать / скрыть")
        eye_icon = IconLoader.load("eye")
        if eye_icon and not eye_icon.isNull():
            eye_btn.setIcon(eye_icon)
            eye_btn.setIconSize(QSize(16, 16))

        def _toggle():
            if edit.echoMode() == QLineEdit.Password:
                edit.setEchoMode(QLineEdit.Normal)
                off_icon = IconLoader.load("eye-off")
                if off_icon and not off_icon.isNull():
                    eye_btn.setIcon(off_icon)
                eye_btn.setToolTip("Скрыть")
            else:
                edit.setEchoMode(QLineEdit.Password)
                on_icon = IconLoader.load("eye")
                if on_icon and not on_icon.isNull():
                    eye_btn.setIcon(on_icon)
                eye_btn.setToolTip("Показать")

        eye_btn.clicked.connect(_toggle)
        h.addWidget(eye_btn)
        return container, edit

    # ----------------------------------------------------------------
    # Вкладка Telegram
    # ----------------------------------------------------------------

    def _create_telegram_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        desc = QLabel(
            "Настройки подключения к Telegram.\n"
            "Bot Token — для отправки сообщений.\n"
            "API ID/Hash + телефон — для автосоздания групп (MTProto)."
        )
        desc.setStyleSheet("color: #666; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        token_row, self._tg_bot_token = self._make_password_field("123456:ABC-DEF1234ghIkl-zyx57W2v...")
        form.addRow("Bot Token:", token_row)

        self._tg_api_id = QLineEdit()
        self._tg_api_id.setPlaceholderText("12345678")
        self._tg_api_id.setStyleSheet(_INPUT_STYLE)
        form.addRow("API ID:", self._tg_api_id)

        hash_row, self._tg_api_hash = self._make_password_field("abcdef0123456789abcdef0123456789")
        form.addRow("API Hash:", hash_row)

        self._tg_phone = QLineEdit()
        self._tg_phone.setPlaceholderText("+79062003365")
        self._tg_phone.setStyleSheet(_INPUT_STYLE)
        form.addRow("Телефон:", self._tg_phone)

        layout.addLayout(form)

        # Статус Telegram
        status_frame = QFrame()
        status_frame.setStyleSheet(
            "QFrame { background-color: #fafafa; border: 1px solid #e6e6e6; border-radius: 6px; }"
        )
        sf_layout = QHBoxLayout(status_frame)
        sf_layout.setContentsMargins(10, 8, 10, 8)
        self._tg_status = QLabel("Статус: загрузка...")
        self._tg_status.setStyleSheet("font-size: 12px; color: #666; border: none;")
        sf_layout.addWidget(self._tg_status)
        layout.addWidget(status_frame)

        # Секция активации MTProto
        mtproto_frame = QFrame()
        mtproto_frame.setStyleSheet(
            "QFrame { background-color: #fff8e1; border: 1px solid #ffe082; border-radius: 6px; }"
        )
        mf_layout = QVBoxLayout(mtproto_frame)
        mf_layout.setContentsMargins(10, 8, 10, 8)
        mf_layout.setSpacing(6)

        mf_title = QLabel("Активация MTProto (автосоздание групп)")
        mf_title.setStyleSheet("font-weight: bold; font-size: 12px; color: #333; border: none;")
        mf_layout.addWidget(mf_title)

        mf_desc = QLabel(
            "Для автоматического создания Telegram-групп нужна авторизация.\n"
            "Нажмите «Запросить код» — на телефон придёт код из Telegram."
        )
        mf_desc.setStyleSheet("font-size: 11px; color: #666; border: none;")
        mf_desc.setWordWrap(True)
        mf_layout.addWidget(mf_desc)

        # Кнопка "Запросить код"
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._mtproto_send_btn = QPushButton("Запросить код")
        self._mtproto_send_btn.setFixedHeight(34)
        self._mtproto_send_btn.setStyleSheet(
            "QPushButton { background-color: #ffd93c; border: 1px solid #e6c200; border-radius: 6px; "
            "font-size: 12px; font-weight: bold; padding: 0 16px; }"
            "QPushButton:hover { background-color: #ffe566; }"
            "QPushButton:disabled { background-color: #e0e0e0; color: #999; border-color: #ccc; }"
        )
        self._mtproto_send_btn.clicked.connect(self._on_mtproto_send_code)
        btn_row.addWidget(self._mtproto_send_btn)

        # Поле ввода кода + кнопка подтвердить (скрыты)
        self._mtproto_code_input = QLineEdit()
        self._mtproto_code_input.setPlaceholderText("Код из Telegram")
        self._mtproto_code_input.setFixedWidth(140)
        self._mtproto_code_input.setStyleSheet(_INPUT_STYLE)
        self._mtproto_code_input.setVisible(False)
        btn_row.addWidget(self._mtproto_code_input)

        self._mtproto_verify_btn = QPushButton("Подтвердить")
        self._mtproto_verify_btn.setFixedHeight(34)
        self._mtproto_verify_btn.setStyleSheet(
            "QPushButton { background-color: #4CAF50; border: 1px solid #388E3C; border-radius: 6px; "
            "font-size: 12px; font-weight: bold; color: white; padding: 0 16px; }"
            "QPushButton:hover { background-color: #66BB6A; }"
            "QPushButton:disabled { background-color: #e0e0e0; color: #999; border-color: #ccc; }"
        )
        self._mtproto_verify_btn.setVisible(False)
        self._mtproto_verify_btn.clicked.connect(self._on_mtproto_verify_code)
        btn_row.addWidget(self._mtproto_verify_btn)

        # Кнопка "Отправить по SMS" (скрыта, появляется после send-code)
        self._mtproto_sms_btn = QPushButton("Отправить по SMS")
        self._mtproto_sms_btn.setFixedHeight(34)
        self._mtproto_sms_btn.setStyleSheet(
            "QPushButton { background-color: #2196F3; border: 1px solid #1976D2; border-radius: 6px; "
            "font-size: 12px; font-weight: bold; color: white; padding: 0 16px; }"
            "QPushButton:hover { background-color: #42A5F5; }"
            "QPushButton:disabled { background-color: #e0e0e0; color: #999; border-color: #ccc; }"
        )
        self._mtproto_sms_btn.clicked.connect(self._on_mtproto_resend_sms)
        btn_row.addWidget(self._mtproto_sms_btn)

        btn_row.addStretch()
        mf_layout.addLayout(btn_row)

        # Статус MTProto сессии
        self._mtproto_session_label = QLabel("")
        self._mtproto_session_label.setStyleSheet("font-size: 11px; color: #666; border: none;")
        self._mtproto_session_label.setWordWrap(True)
        mf_layout.addWidget(self._mtproto_session_label)

        layout.addWidget(mtproto_frame)

        layout.addStretch()
        return tab

    # ----------------------------------------------------------------
    # Вкладка Email (SMTP)
    # ----------------------------------------------------------------

    def _create_email_tab(self) -> QWidget:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        desc = QLabel(
            "Настройки SMTP для отправки invite-ссылок по email.\n"
            "Поддерживаются Mail.ru, Yandex, Gmail и другие сервисы."
        )
        desc.setStyleSheet("color: #666; font-size: 12px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        self._smtp_host = QLineEdit()
        self._smtp_host.setPlaceholderText("smtp.mail.ru")
        self._smtp_host.setStyleSheet(_INPUT_STYLE)
        form.addRow("SMTP Host:", self._smtp_host)

        self._smtp_port = QLineEdit()
        self._smtp_port.setPlaceholderText("465")
        self._smtp_port.setStyleSheet(_INPUT_STYLE)
        form.addRow("SMTP Port:", self._smtp_port)

        self._smtp_username = QLineEdit()
        self._smtp_username.setPlaceholderText("user@mail.ru")
        self._smtp_username.setStyleSheet(_INPUT_STYLE)
        form.addRow("Логин:", self._smtp_username)

        pwd_row, self._smtp_password = self._make_password_field("пароль приложения")
        form.addRow("Пароль:", pwd_row)

        self._smtp_tls = QCheckBox("Использовать SSL/TLS")
        self._smtp_tls.setChecked(True)
        form.addRow("", self._smtp_tls)

        self._smtp_from_name = QLineEdit()
        self._smtp_from_name.setPlaceholderText("Festival Color CRM")
        self._smtp_from_name.setStyleSheet(_INPUT_STYLE)
        form.addRow("Имя отправителя:", self._smtp_from_name)

        layout.addLayout(form)

        # Статус Email
        status_frame = QFrame()
        status_frame.setStyleSheet(
            "QFrame { background-color: #fafafa; border: 1px solid #e6e6e6; border-radius: 6px; }"
        )
        sf_layout = QHBoxLayout(status_frame)
        sf_layout.setContentsMargins(10, 8, 10, 8)
        self._email_status = QLabel("Статус: загрузка...")
        self._email_status.setStyleSheet("font-size: 12px; color: #666; border: none;")
        sf_layout.addWidget(self._email_status)
        layout.addWidget(status_frame)

        layout.addStretch()
        return tab

    # ----------------------------------------------------------------
    # Вкладка Скрипты
    # ----------------------------------------------------------------

    def _create_scripts_tab(self) -> QWidget:
        tab = QWidget()
        layout = QHBoxLayout(tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        # Левая панель: список скриптов
        left = QVBoxLayout()
        left.setSpacing(6)

        list_label = QLabel("Скрипты")
        list_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        left.addWidget(list_label)

        self._script_list = QListWidget()
        self._script_list.setStyleSheet("""
            QListWidget {
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                font-size: 13px;
                background-color: #ffffff;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-bottom: 1px solid #f0f0f0;
            }
            QListWidget::item:selected {
                background-color: #fff8e1;
                color: #333;
            }
        """)
        self._script_list.currentRowChanged.connect(self._on_script_selected)
        left.addWidget(self._script_list)

        add_btn = QPushButton("Добавить скрипт")
        add_btn.setFixedHeight(32)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #f0c929; }
        """)
        add_btn.clicked.connect(self._on_add_script)
        left.addWidget(add_btn)

        left_w = QWidget()
        left_w.setLayout(left)
        left_w.setFixedWidth(200)
        layout.addWidget(left_w)

        # Правая панель: редактор скрипта
        right = QVBoxLayout()
        right.setSpacing(8)

        self._script_editor_stack = QStackedWidget()

        # Пустое состояние
        empty_page = QWidget()
        ep_layout = QVBoxLayout(empty_page)
        ep_layout.addStretch()
        ep_label = QLabel("Выберите скрипт для редактирования")
        ep_label.setStyleSheet("color: #999; font-size: 13px;")
        ep_label.setAlignment(Qt.AlignCenter)
        ep_layout.addWidget(ep_label)
        ep_layout.addStretch()
        self._script_editor_stack.addWidget(empty_page)

        # Редактор
        editor_page = QWidget()
        ed_layout = QVBoxLayout(editor_page)
        ed_layout.setContentsMargins(0, 0, 0, 0)
        ed_layout.setSpacing(8)

        # Тип скрипта
        type_row = QHBoxLayout()
        type_row.setSpacing(8)
        type_row.addWidget(QLabel("Тип:"))
        self._script_type_combo = QComboBox()
        self._script_type_combo.setStyleSheet(_COMBO_STYLE)
        for key, label in SCRIPT_TYPES.items():
            self._script_type_combo.addItem(label, key)
        type_row.addWidget(self._script_type_combo)
        ed_layout.addLayout(type_row)

        # Стадия (для stage_complete и других типов с привязкой к стадии)
        stage_row = QHBoxLayout()
        stage_row.setSpacing(8)
        stage_row.addWidget(QLabel("Стадия:"))
        self._script_stage_combo = QComboBox()
        self._script_stage_combo.setStyleSheet(_COMBO_STYLE)
        self._populate_stage_combo()
        stage_row.addWidget(self._script_stage_combo)
        ed_layout.addLayout(stage_row)

        self._script_type_combo.currentIndexChanged.connect(self._on_script_type_changed)

        # Текст шаблона
        ed_layout.addWidget(QLabel("Текст сообщения (HTML):"))
        self._script_text = QTextEdit()
        self._script_text.setStyleSheet(_TEXTEDIT_STYLE)
        self._script_text.setMinimumHeight(120)
        ed_layout.addWidget(self._script_text)

        # Плейсхолдеры
        ph_label = QLabel("Доступные переменные (кликните для вставки):")
        ph_label.setStyleSheet("font-size: 12px; color: #666;")
        ed_layout.addWidget(ph_label)

        ph_frame = QFrame()
        ph_frame.setStyleSheet(
            "QFrame { background-color: #fafafa; border: 1px solid #e6e6e6; border-radius: 4px; }"
        )
        ph_layout = QGridLayout(ph_frame)
        ph_layout.setContentsMargins(8, 6, 8, 6)
        ph_layout.setSpacing(4)

        col = 0
        row = 0
        for placeholder, desc in SCRIPT_PLACEHOLDERS.items():
            btn = QPushButton(placeholder)
            btn.setFixedHeight(26)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setToolTip(desc)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    border: 1px solid #d9d9d9;
                    border-radius: 3px;
                    font-size: 11px;
                    padding: 0 8px;
                    color: #0066cc;
                    font-family: monospace;
                }
                QPushButton:hover { background-color: #e8f0fe; border-color: #0066cc; }
            """)
            btn.clicked.connect(lambda _, p=placeholder: self._insert_placeholder(p))
            ph_layout.addWidget(btn, row, col)
            col += 1
            if col >= 4:
                col = 0
                row += 1

        ed_layout.addWidget(ph_frame)

        # Опции
        opts_row = QHBoxLayout()
        self._script_enabled_cb = QCheckBox("Включен")
        self._script_enabled_cb.setChecked(True)
        opts_row.addWidget(self._script_enabled_cb)

        self._script_auto_deadline_cb = QCheckBox("Подставлять дедлайн автоматически")
        self._script_auto_deadline_cb.setChecked(True)
        opts_row.addWidget(self._script_auto_deadline_cb)
        opts_row.addStretch()
        ed_layout.addLayout(opts_row)

        # Кнопки скрипта
        script_btns = QHBoxLayout()
        script_btns.setSpacing(8)

        self._save_script_btn = QPushButton("Сохранить скрипт")
        self._save_script_btn.setFixedHeight(32)
        self._save_script_btn.setCursor(Qt.PointingHandCursor)
        self._save_script_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333;
                border: none;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #f0c929; }
        """)
        self._save_script_btn.clicked.connect(self._on_save_script)
        script_btns.addWidget(self._save_script_btn)

        self._delete_script_btn = QPushButton("Удалить")
        self._delete_script_btn.setFixedHeight(32)
        self._delete_script_btn.setCursor(Qt.PointingHandCursor)
        self._delete_script_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #F44336;
                border: 1px solid #F44336;
                border-radius: 4px;
                font-size: 12px;
                padding: 0 16px;
            }
            QPushButton:hover { background-color: #fff5f5; }
        """)
        self._delete_script_btn.clicked.connect(self._on_delete_script)
        script_btns.addWidget(self._delete_script_btn)

        script_btns.addStretch()
        ed_layout.addLayout(script_btns)

        self._script_editor_stack.addWidget(editor_page)

        right.addWidget(self._script_editor_stack)
        layout.addLayout(right)

        return tab

    # ================================================================
    # Загрузка данных
    # ================================================================

    def _load_data(self):
        """Загрузить настройки и скрипты с сервера"""
        self._load_settings()
        self._load_scripts()
        self._load_status()

    def _load_settings(self):
        """Загрузить настройки мессенджера"""
        try:
            settings_list = []
            if self.data_access:
                settings_list = self.data_access.get_messenger_settings()
            elif self.api_client:
                settings_list = self.api_client.get_messenger_settings()

            self._settings = {}
            for s in (settings_list or []):
                key = s.get("setting_key", "")
                val = s.get("setting_value", "")
                if key:
                    self._settings[key] = val or ""

            # Заполнить поля Telegram
            self._tg_bot_token.setText(self._settings.get("telegram_bot_token", ""))
            self._tg_api_id.setText(self._settings.get("telegram_api_id", ""))
            self._tg_api_hash.setText(self._settings.get("telegram_api_hash", ""))
            self._tg_phone.setText(self._settings.get("telegram_phone", ""))

            # Заполнить поля SMTP
            self._smtp_host.setText(self._settings.get("smtp_host", ""))
            self._smtp_port.setText(self._settings.get("smtp_port", "465"))
            self._smtp_username.setText(self._settings.get("smtp_username", ""))
            self._smtp_password.setText(self._settings.get("smtp_password", ""))
            self._smtp_tls.setChecked(
                self._settings.get("smtp_use_tls", "true").lower() == "true"
            )
            self._smtp_from_name.setText(
                self._settings.get("smtp_from_name", "Festival Color CRM")
            )
        except Exception as e:
            logger.error(f"Ошибка загрузки настроек: {e}")

    def _load_scripts(self):
        """Загрузить скрипты"""
        try:
            if self.data_access:
                self._scripts = self.data_access.get_messenger_scripts() or []
            elif self.api_client:
                self._scripts = self.api_client.get_messenger_scripts() or []
            else:
                self._scripts = []

            self._refresh_script_list()
        except Exception as e:
            logger.error(f"Ошибка загрузки скриптов: {e}")
            self._scripts = []

    def _load_status(self):
        """Загрузить статус сервисов"""
        try:
            status = {}
            if self.data_access:
                status = self.data_access.get_messenger_status()
            elif self.api_client:
                status = self.api_client.get_messenger_status()

            # Telegram
            bot_ok = status.get("telegram_bot_available", False)
            mtproto_ok = status.get("telegram_mtproto_available", False)
            tg_parts = []
            tg_parts.append(f"Bot API: {'подключен' if bot_ok else 'не настроен'}")
            tg_parts.append(f"MTProto: {'подключен' if mtproto_ok else 'не настроен'}")
            self._tg_status.setText("Статус: " + " | ".join(tg_parts))
            self._tg_status.setStyleSheet(
                f"font-size: 12px; color: {'#4CAF50' if bot_ok else '#F44336'}; border: none;"
            )

            # Email
            email_ok = status.get("email_available", False)
            self._email_status.setText(
                f"Статус: {'подключен' if email_ok else 'не настроен'}"
            )
            self._email_status.setStyleSheet(
                f"font-size: 12px; color: {'#4CAF50' if email_ok else '#F44336'}; border: none;"
            )

            # Проверка MTProto-сессии
            try:
                session_info = {}
                if self.data_access:
                    session_info = self.data_access.mtproto_session_status()
                elif self.api_client:
                    session_info = self.api_client.mtproto_session_status()

                if session_info.get("valid"):
                    name = session_info.get("first_name", "")
                    username = session_info.get("username", "")
                    self._mtproto_session_label.setText(
                        f"Сессия активна: {name}"
                        + (f" (@{username})" if username else "")
                    )
                    self._mtproto_session_label.setStyleSheet(
                        "font-size: 11px; color: #4CAF50; font-weight: bold; border: none;"
                    )
                else:
                    if mtproto_ok:
                        self._mtproto_session_label.setText(
                            "Настройки заполнены, но сессия не активирована"
                        )
                        self._mtproto_session_label.setStyleSheet(
                            "font-size: 11px; color: #FF9800; border: none;"
                        )
                    else:
                        self._mtproto_session_label.setText("")
            except Exception:
                pass

            # Общий статус
            parts = []
            if bot_ok:
                parts.append("TG Bot")
            if mtproto_ok:
                parts.append("MTProto")
            if email_ok:
                parts.append("Email")
            self._status_label.setText(
                "Подключено: " + ", ".join(parts) if parts else "Сервисы не настроены"
            )
        except Exception as e:
            logger.warning(f"Ошибка загрузки статуса: {e}")
            self._tg_status.setText("Статус: ошибка загрузки")
            self._email_status.setText("Статус: ошибка загрузки")

    # ================================================================
    # MTProto авторизация
    # ================================================================

    def _on_mtproto_send_code(self):
        """Шаг 1: Запросить код подтверждения"""
        self._mtproto_send_btn.setEnabled(False)
        self._mtproto_send_btn.setText("Отправка...")
        self._mtproto_session_label.setText("")

        try:
            result = {}
            if self.data_access:
                result = self.data_access.mtproto_send_code()
            elif self.api_client:
                result = self.api_client.mtproto_send_code()

            if result.get("status") == "code_sent":
                phone = result.get("phone", "")
                self._mtproto_session_label.setText(
                    f"Код отправлен на {phone}. Проверьте Telegram.\n"
                    "Если код не пришёл — нажмите «Отправить по SMS»."
                )
                self._mtproto_session_label.setStyleSheet(
                    "font-size: 11px; color: #4CAF50; border: none;"
                )
                # Показать поле ввода кода + кнопки
                self._mtproto_code_input.setVisible(True)
                self._mtproto_code_input.setFocus()
                self._mtproto_verify_btn.setVisible(True)
                self._mtproto_sms_btn.setVisible(True)
                self._mtproto_send_btn.setText("Отправить повторно")
                self._mtproto_send_btn.setEnabled(True)
            else:
                error = result.get("detail", result.get("error", "Неизвестная ошибка"))
                self._mtproto_session_label.setText(f"Ошибка: {error}")
                self._mtproto_session_label.setStyleSheet(
                    "font-size: 11px; color: #F44336; border: none;"
                )
                self._mtproto_send_btn.setText("Запросить код")
                self._mtproto_send_btn.setEnabled(True)
        except Exception as e:
            error_msg = str(e)
            # Извлечь detail из ответа API если есть
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get("detail", error_msg)
                except Exception:
                    pass
            self._mtproto_session_label.setText(f"Ошибка: {error_msg}")
            self._mtproto_session_label.setStyleSheet(
                "font-size: 11px; color: #F44336; border: none;"
            )
            self._mtproto_send_btn.setText("Запросить код")
            self._mtproto_send_btn.setEnabled(True)

    def _on_mtproto_resend_sms(self):
        """Переотправить код по SMS"""
        self._mtproto_sms_btn.setEnabled(False)
        self._mtproto_sms_btn.setText("Отправка SMS...")

        try:
            result = {}
            if self.data_access:
                result = self.data_access.mtproto_resend_sms()
            elif self.api_client:
                result = self.api_client.mtproto_resend_sms()

            if result.get("status") == "sms_sent":
                phone = result.get("phone", "")
                self._mtproto_session_label.setText(
                    f"SMS отправлена на {phone}. Введите код из SMS."
                )
                self._mtproto_session_label.setStyleSheet(
                    "font-size: 11px; color: #4CAF50; font-weight: bold; border: none;"
                )
                # Показать поле ввода кода
                self._mtproto_code_input.setVisible(True)
                self._mtproto_code_input.setFocus()
                self._mtproto_verify_btn.setVisible(True)
            else:
                error = result.get("detail", result.get("error", "Ошибка"))
                self._mtproto_session_label.setText(f"Ошибка SMS: {error}")
                self._mtproto_session_label.setStyleSheet(
                    "font-size: 11px; color: #F44336; border: none;"
                )
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get("detail", error_msg)
                except Exception:
                    pass
            self._mtproto_session_label.setText(f"Ошибка SMS: {error_msg}")
            self._mtproto_session_label.setStyleSheet(
                "font-size: 11px; color: #F44336; border: none;"
            )
        finally:
            self._mtproto_sms_btn.setText("Отправить по SMS")
            self._mtproto_sms_btn.setEnabled(True)

    def _on_mtproto_verify_code(self):
        """Шаг 2: Подтвердить код"""
        code = self._mtproto_code_input.text().strip()
        if not code:
            self._mtproto_session_label.setText("Введите код подтверждения")
            self._mtproto_session_label.setStyleSheet(
                "font-size: 11px; color: #F44336; border: none;"
            )
            return

        self._mtproto_verify_btn.setEnabled(False)
        self._mtproto_verify_btn.setText("Проверка...")
        self._mtproto_session_label.setText("")

        try:
            result = {}
            if self.data_access:
                result = self.data_access.mtproto_verify_code(code)
            elif self.api_client:
                result = self.api_client.mtproto_verify_code(code)

            if result.get("status") == "success":
                user_info = result.get("user", {})
                name = user_info.get("first_name", "")
                username = user_info.get("username", "")
                self._mtproto_session_label.setText(
                    f"MTProto активирован! Авторизован как: {name}"
                    + (f" (@{username})" if username else "")
                )
                self._mtproto_session_label.setStyleSheet(
                    "font-size: 11px; color: #4CAF50; font-weight: bold; border: none;"
                )
                # Скрыть поле ввода
                self._mtproto_code_input.setVisible(False)
                self._mtproto_verify_btn.setVisible(False)
                self._mtproto_sms_btn.setVisible(False)
                self._mtproto_send_btn.setText("Запросить код")
                self._mtproto_send_btn.setEnabled(True)
                # Обновить статусы
                self._load_status()
            else:
                error = result.get("detail", result.get("error", "Неверный код"))
                self._mtproto_session_label.setText(f"Ошибка: {error}")
                self._mtproto_session_label.setStyleSheet(
                    "font-size: 11px; color: #F44336; border: none;"
                )
                self._mtproto_verify_btn.setText("Подтвердить")
                self._mtproto_verify_btn.setEnabled(True)
        except Exception as e:
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get("detail", error_msg)
                except Exception:
                    pass
            self._mtproto_session_label.setText(f"Ошибка: {error_msg}")
            self._mtproto_session_label.setStyleSheet(
                "font-size: 11px; color: #F44336; border: none;"
            )
            self._mtproto_verify_btn.setText("Подтвердить")
            self._mtproto_verify_btn.setEnabled(True)

    # ================================================================
    # Скрипты — UI
    # ================================================================

    def _refresh_script_list(self):
        """Обновить список скриптов"""
        self._script_list.clear()
        for script in self._scripts:
            script_type = script.get("script_type", "")
            stage = script.get("stage_name", "")
            is_enabled = script.get("is_enabled", True)

            type_label = SCRIPT_TYPES.get(script_type, script_type)
            display = type_label
            if stage:
                display += f" ({stage})"
            if not is_enabled:
                display += " [ВЫКЛ]"

            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, script.get("id"))
            if not is_enabled:
                item.setForeground(QColor("#999999"))
            self._script_list.addItem(item)

        self._script_editor_stack.setCurrentIndex(0)
        self._current_script_id = None

    def _on_script_selected(self, row: int):
        """Выбран скрипт из списка"""
        if row < 0 or row >= len(self._scripts):
            self._script_editor_stack.setCurrentIndex(0)
            self._current_script_id = None
            return

        script = self._scripts[row]
        self._current_script_id = script.get("id")
        self._script_editor_stack.setCurrentIndex(1)

        # Тип
        script_type = script.get("script_type", "project_start")
        idx = self._script_type_combo.findData(script_type)
        if idx >= 0:
            self._script_type_combo.setCurrentIndex(idx)

        # Стадия — ищем по data, а если не нашли — по тексту (подэтапы имеют отступ)
        stage = script.get("stage_name", "") or ""
        s_idx = self._script_stage_combo.findData(stage)
        if s_idx < 0 and stage:
            # Попробуем найти по тексту (возможно подэтап)
            for i in range(self._script_stage_combo.count()):
                if self._script_stage_combo.itemData(i) == stage:
                    s_idx = i
                    break
        if s_idx >= 0:
            self._script_stage_combo.setCurrentIndex(s_idx)
        else:
            self._script_stage_combo.setCurrentIndex(0)  # (все стадии)

        # Текст
        self._script_text.setPlainText(script.get("message_template", ""))

        # Опции
        self._script_enabled_cb.setChecked(script.get("is_enabled", True))
        self._script_auto_deadline_cb.setChecked(script.get("use_auto_deadline", True))

        self._on_script_type_changed()

    def _populate_stage_combo(self):
        """Заполнить комбобокс стадий с группировкой по типам проектов"""
        self._script_stage_combo.clear()
        self._script_stage_combo.addItem("(все стадии)", "")

        from PyQt5.QtGui import QStandardItemModel
        model = self._script_stage_combo.model()

        for group_name, stages in CRM_STAGE_GROUPS.items():
            # Разделитель-заголовок группы
            sep_idx = self._script_stage_combo.count()
            self._script_stage_combo.addItem(f"── {group_name} ──", f"__group__{group_name}")
            sep_item = model.item(sep_idx)
            if sep_item:
                sep_item.setEnabled(False)
                sep_item.setForeground(QColor("#999999"))
                f = sep_item.font()
                f.setBold(True)
                f.setPointSize(f.pointSize() - 1)
                sep_item.setFont(f)

            for stage_name, substages in stages:
                self._script_stage_combo.addItem(f"  {stage_name}", stage_name)
                # Подэтапы
                for sub in substages:
                    self._script_stage_combo.addItem(f"    {sub}", sub)

    def _on_script_type_changed(self):
        """Показать/скрыть выбор стадии в зависимости от типа"""
        current_type = self._script_type_combo.currentData()
        # Стадию показываем для всех типов кроме project_start и project_end
        show_stage = current_type not in ("project_start", "project_end")
        self._script_stage_combo.setVisible(show_stage)
        # Найти label "Стадия:" — он в parent layout
        for i in range(self._script_stage_combo.parent().layout().count()):
            item = self._script_stage_combo.parent().layout().itemAt(i)
            if item and item.layout():
                for j in range(item.layout().count()):
                    w = item.layout().itemAt(j).widget()
                    if isinstance(w, QLabel) and w.text() == "Стадия:":
                        w.setVisible(show_stage)

    def _insert_placeholder(self, placeholder: str):
        """Вставить плейсхолдер в редактор скрипта"""
        cursor = self._script_text.textCursor()
        cursor.insertText(placeholder)
        self._script_text.setFocus()

    def _on_add_script(self):
        """Добавить новый скрипт — сначала спросить тип"""
        from ui.custom_message_box import CustomMessageBox

        # Мини-диалог выбора типа
        type_dialog = QDialog(self)
        type_dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        type_dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        type_dialog.setFixedWidth(340)

        d_root = QVBoxLayout(type_dialog)
        d_root.setContentsMargins(0, 0, 0, 0)

        d_frame = QFrame()
        d_frame.setObjectName("addScriptFrame")
        d_frame.setStyleSheet("""
            QFrame#addScriptFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        d_layout = QVBoxLayout(d_frame)
        d_layout.setContentsMargins(20, 16, 20, 16)
        d_layout.setSpacing(12)

        d_title = QLabel("Выберите тип скрипта")
        d_title.setStyleSheet("font-size: 14px; font-weight: 600; color: #333;")
        d_layout.addWidget(d_title)

        type_combo = QComboBox()
        type_combo.setStyleSheet(_COMBO_STYLE)
        for key, label in SCRIPT_TYPES.items():
            type_combo.addItem(label, key)
        d_layout.addWidget(type_combo)

        d_btns = QHBoxLayout()
        d_btns.setSpacing(8)
        d_btns.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(32)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #333;
                border: 1px solid #d9d9d9; border-radius: 4px;
                padding: 0 16px; font-size: 12px;
            }
            QPushButton:hover { background-color: #f5f5f5; }
        """)
        cancel_btn.clicked.connect(type_dialog.reject)
        d_btns.addWidget(cancel_btn)

        ok_btn = QPushButton("Создать")
        ok_btn.setFixedHeight(32)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c; color: #333;
                border: none; border-radius: 4px;
                padding: 0 20px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #f0c929; }
        """)
        ok_btn.clicked.connect(type_dialog.accept)
        d_btns.addWidget(ok_btn)

        d_layout.addLayout(d_btns)
        d_root.addWidget(d_frame)

        if type_dialog.exec_() != QDialog.Accepted:
            return

        chosen_type = type_combo.currentData()

        # Шаблоны по умолчанию для разных типов
        default_templates = {
            "project_start": "Здравствуйте, {client_name}!\n\nДобро пожаловать в проект. Ваш менеджер — {manager_name}.\nАдрес объекта: {address}, {city}.",
            "stage_complete": "Здравствуйте, {client_name}!\n\nЭтап «{stage_name}» готов к согласованию.\nПросим ознакомиться с материалами.",
            "project_end": "Здравствуйте, {client_name}!\n\nПроект завершён. Благодарим за сотрудничество!",
            "project_paused": "Здравствуйте, {client_name}!\n\nПроект временно приостановлен.\nМенеджер {manager_name} свяжется с вами для уточнения деталей.",
            "custom": "Здравствуйте, {client_name}!\n\n",
        }

        try:
            data = {
                "script_type": chosen_type,
                "message_template": default_templates.get(chosen_type, ""),
                "is_enabled": True,
                "use_auto_deadline": chosen_type == "stage_complete",
                "sort_order": len(self._scripts),
            }
            if self.api_client:
                result = self.api_client.create_messenger_script(data)
                if result:
                    self._load_scripts()
                    if self._script_list.count() > 0:
                        self._script_list.setCurrentRow(self._script_list.count() - 1)
            else:
                CustomMessageBox(self, "Ошибка", "Нет подключения к серверу", "error").exec_()
        except Exception as e:
            CustomMessageBox(self, "Ошибка", f"Не удалось создать скрипт:\n{str(e)}", "error").exec_()

    def _on_save_script(self):
        """Сохранить текущий скрипт"""
        from ui.custom_message_box import CustomMessageBox

        if not self._current_script_id:
            return

        text = self._script_text.toPlainText().strip()
        if not text:
            CustomMessageBox(self, "Ошибка", "Текст скрипта не может быть пустым", "warning").exec_()
            return

        data = {
            "script_type": self._script_type_combo.currentData(),
            "stage_name": self._script_stage_combo.currentData() or None,
            "message_template": text,
            "is_enabled": self._script_enabled_cb.isChecked(),
            "use_auto_deadline": self._script_auto_deadline_cb.isChecked(),
        }

        try:
            if self.api_client:
                self.api_client.update_messenger_script(self._current_script_id, data)
                self._load_scripts()
                CustomMessageBox(self, "Готово", "Скрипт сохранён", "success").exec_()
            else:
                CustomMessageBox(self, "Ошибка", "Нет подключения к серверу", "error").exec_()
        except Exception as e:
            CustomMessageBox(self, "Ошибка", f"Не удалось сохранить:\n{str(e)}", "error").exec_()

    def _on_delete_script(self):
        """Удалить текущий скрипт"""
        from ui.custom_message_box import CustomQuestionBox, CustomMessageBox

        if not self._current_script_id:
            return

        reply = CustomQuestionBox(
            self, "Удаление скрипта",
            "Вы уверены, что хотите удалить этот скрипт?"
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                if self.api_client:
                    self.api_client.delete_messenger_script(self._current_script_id)
                    self._current_script_id = None
                    self._load_scripts()
            except Exception as e:
                CustomMessageBox(
                    self, "Ошибка", f"Не удалось удалить:\n{str(e)}", "error"
                ).exec_()

    # ================================================================
    # Сохранение настроек
    # ================================================================

    def _on_save(self):
        """Сохранить все настройки"""
        from ui.custom_message_box import CustomMessageBox

        settings = [
            {"setting_key": "telegram_bot_token", "setting_value": self._tg_bot_token.text().strip()},
            {"setting_key": "telegram_api_id", "setting_value": self._tg_api_id.text().strip()},
            {"setting_key": "telegram_api_hash", "setting_value": self._tg_api_hash.text().strip()},
            {"setting_key": "telegram_phone", "setting_value": self._tg_phone.text().strip()},
            {"setting_key": "smtp_host", "setting_value": self._smtp_host.text().strip()},
            {"setting_key": "smtp_port", "setting_value": self._smtp_port.text().strip() or "465"},
            {"setting_key": "smtp_username", "setting_value": self._smtp_username.text().strip()},
            {"setting_key": "smtp_password", "setting_value": self._smtp_password.text().strip()},
            {"setting_key": "smtp_use_tls", "setting_value": "true" if self._smtp_tls.isChecked() else "false"},
            {"setting_key": "smtp_from_name", "setting_value": self._smtp_from_name.text().strip() or "Festival Color CRM"},
        ]

        try:
            result = None
            if self.data_access:
                result = self.data_access.update_messenger_settings(settings)
            elif self.api_client:
                result = self.api_client.update_messenger_settings(settings)

            if result is not None:
                CustomMessageBox(
                    self, "Готово",
                    "Настройки сохранены.\nИзменения вступят в силу после перезапуска сервера.",
                    "success",
                ).exec_()
                self._load_status()
            else:
                CustomMessageBox(self, "Ошибка", "Нет подключения к серверу", "error").exec_()
        except Exception as e:
            CustomMessageBox(
                self, "Ошибка", f"Не удалось сохранить настройки:\n{str(e)}", "error"
            ).exec_()
