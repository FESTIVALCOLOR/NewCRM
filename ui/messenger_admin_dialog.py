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
    "{deadline}": "Дата дедлайна (ДД.ММ.ГГГГ)",
    "{manager_name}": "Имя менеджера проекта",
    "{address}": "Адрес объекта",
    "{city}": "Город",
}

SCRIPT_TYPES = {
    "project_start": "Начало проекта",
    "stage_complete": "Завершение стадии",
    "project_end": "Завершение проекта",
}

# Стадии CRM для уведомлений
CRM_STAGES = [
    "Стадия 1: планировочные решения",
    "Стадия 2: концепция дизайна",
    "Стадия 2: рабочие чертежи",
    "Стадия 3: рабочие чертежи",
    "Стадия 3: 3д визуализация (Дополнительная)",
    "Выполненный проект",
]


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

        self._tg_bot_token = QLineEdit()
        self._tg_bot_token.setPlaceholderText("123456:ABC-DEF1234ghIkl-zyx57W2v...")
        self._tg_bot_token.setStyleSheet(_INPUT_STYLE)
        self._tg_bot_token.setEchoMode(QLineEdit.Password)
        form.addRow("Bot Token:", self._tg_bot_token)

        self._tg_api_id = QLineEdit()
        self._tg_api_id.setPlaceholderText("12345678")
        self._tg_api_id.setStyleSheet(_INPUT_STYLE)
        form.addRow("API ID:", self._tg_api_id)

        self._tg_api_hash = QLineEdit()
        self._tg_api_hash.setPlaceholderText("abcdef0123456789abcdef0123456789")
        self._tg_api_hash.setStyleSheet(_INPUT_STYLE)
        self._tg_api_hash.setEchoMode(QLineEdit.Password)
        form.addRow("API Hash:", self._tg_api_hash)

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

        self._smtp_password = QLineEdit()
        self._smtp_password.setPlaceholderText("пароль приложения")
        self._smtp_password.setStyleSheet(_INPUT_STYLE)
        self._smtp_password.setEchoMode(QLineEdit.Password)
        form.addRow("Пароль:", self._smtp_password)

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

        # Стадия (для stage_complete)
        stage_row = QHBoxLayout()
        stage_row.setSpacing(8)
        stage_row.addWidget(QLabel("Стадия:"))
        self._script_stage_combo = QComboBox()
        self._script_stage_combo.setStyleSheet(_COMBO_STYLE)
        self._script_stage_combo.addItem("(все стадии)", "")
        for stage in CRM_STAGES:
            self._script_stage_combo.addItem(stage, stage)
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
            if col >= 3:
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

        # Стадия
        stage = script.get("stage_name", "") or ""
        s_idx = self._script_stage_combo.findData(stage)
        if s_idx >= 0:
            self._script_stage_combo.setCurrentIndex(s_idx)

        # Текст
        self._script_text.setPlainText(script.get("message_template", ""))

        # Опции
        self._script_enabled_cb.setChecked(script.get("is_enabled", True))
        self._script_auto_deadline_cb.setChecked(script.get("use_auto_deadline", True))

        self._on_script_type_changed()

    def _on_script_type_changed(self):
        """Показать/скрыть выбор стадии в зависимости от типа"""
        current_type = self._script_type_combo.currentData()
        show_stage = (current_type == "stage_complete")
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
        """Добавить новый скрипт"""
        from ui.custom_message_box import CustomMessageBox

        try:
            data = {
                "script_type": "stage_complete",
                "message_template": "Здравствуйте, {client_name}!\n\nНовое уведомление по проекту.",
                "is_enabled": True,
                "use_auto_deadline": True,
                "sort_order": len(self._scripts),
            }
            if self.api_client:
                result = self.api_client.create_messenger_script(data)
                if result:
                    self._load_scripts()
                    # Выбрать последний
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
