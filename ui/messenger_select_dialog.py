# -*- coding: utf-8 -*-
"""
Диалог создания / привязки мессенджер-чата для CRM-карточки.
Двухшаговый процесс:
  1. Выбор мессенджера (Telegram / Max / WhatsApp)
  2. Настройка чата: название, способ создания, участники
"""
import logging
from typing import Optional, Dict, Any, List

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QStackedWidget, QRadioButton, QButtonGroup,
    QLineEdit, QCheckBox, QGroupBox, QGridLayout, QWidget,
    QSizePolicy, QScrollArea,
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QPixmap, QFont

from utils.resource_path import resource_path
from utils.icon_loader import IconLoader

logger = logging.getLogger(__name__)

# Стиль кнопок мессенджера
_MESSENGER_BTN_STYLE = """
    QPushButton {{
        background-color: {bg};
        color: {fg};
        border: 1px solid {border};
        border-radius: 8px;
        padding: 12px 20px;
        font-size: 14px;
        font-weight: 600;
        text-align: left;
    }}
    QPushButton:hover {{ background-color: {hover}; }}
    QPushButton:pressed {{ background-color: {pressed}; }}
    QPushButton:disabled {{ background-color: #f5f5f5; color: #b0b0b0; border-color: #e6e6e6; }}
"""

# Общие стили
_INPUT_STYLE = """
    QLineEdit {
        border: 1px solid #d9d9d9;
        border-radius: 6px;
        padding: 8px 12px;
        font-size: 13px;
        background-color: #ffffff;
    }
    QLineEdit:focus { border-color: #ffd93c; }
    QLineEdit:disabled { background-color: #f5f5f5; color: #999999; }
"""

_RADIO_STYLE = """
    QRadioButton {
        font-size: 13px;
        spacing: 8px;
        padding: 4px 0;
    }
    QRadioButton::indicator { width: 16px; height: 16px; }
    QRadioButton::indicator:checked {
        background-color: #ffd93c;
        border: 2px solid #e6c236;
        border-radius: 8px;
    }
    QRadioButton::indicator:unchecked {
        background-color: #ffffff;
        border: 2px solid #d9d9d9;
        border-radius: 8px;
    }
"""

_CHECKBOX_STYLE = """
    QCheckBox {
        font-size: 13px;
        spacing: 8px;
        padding: 3px 0;
    }
    QCheckBox::indicator { width: 16px; height: 16px; border-radius: 3px; }
    QCheckBox::indicator:checked {
        background-color: #ffd93c;
        border: 1px solid #e6c236;
    }
    QCheckBox::indicator:unchecked {
        background-color: #ffffff;
        border: 1px solid #d9d9d9;
    }
    QCheckBox::indicator:checked:disabled {
        background-color: #e6e6e6;
        border: 1px solid #cccccc;
    }
    QCheckBox:disabled { color: #999999; }
"""


class MessengerSelectDialog(QDialog):
    """Двухшаговый диалог: выбор мессенджера -> настройка чата"""

    def __init__(
        self,
        parent,
        card_data: Dict[str, Any],
        api_client,
        db,
        data_access,
        employee: Dict[str, Any],
    ):
        super().__init__(parent)
        self.card_data = card_data or {}
        self.api_client = api_client
        self.db = db
        self.data_access = data_access
        self.employee = employee or {}
        self.result_chat_data: Optional[Dict] = None

        self._selected_messenger = "telegram"
        self._participant_checkboxes: List[Dict] = []

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(500)
        self.setMaximumWidth(560)

        self._init_ui()

    # ================================================================
    # UI
    # ================================================================

    def _init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Рамка
        self._border_frame = QFrame()
        self._border_frame.setObjectName("borderFrame")
        self._border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        frame_layout = QVBoxLayout(self._border_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # TitleBar
        from ui.custom_title_bar import CustomTitleBar
        self._title_bar = CustomTitleBar(self, "Создать чат", simple_mode=True)
        frame_layout.addWidget(self._title_bar)

        # Стек страниц
        self._stack = QStackedWidget()
        frame_layout.addWidget(self._stack)

        self._page_messenger = self._create_messenger_page()
        self._page_config = self._create_config_page()
        self._stack.addWidget(self._page_messenger)
        self._stack.addWidget(self._page_config)

        root.addWidget(self._border_frame)

    # ----------------------------------------------------------------
    # Страница 1: Выбор мессенджера
    # ----------------------------------------------------------------

    def _create_messenger_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 16, 24, 24)
        layout.setSpacing(12)

        hint = QLabel("Выберите мессенджер для проектного чата:")
        hint.setStyleSheet("font-size: 14px; color: #333333;")
        layout.addWidget(hint)

        # Telegram
        tg_btn = self._make_messenger_btn(
            "telegram", "Telegram",
            "Групповые чаты, файлы, боты",
            bg="#0088cc", fg="#ffffff", border="#0077b3",
            hover="#0099e0", pressed="#006699",
        )
        tg_btn.clicked.connect(lambda: self._on_messenger_chosen("telegram"))
        layout.addWidget(tg_btn)

        # Max (VK Teams)
        max_btn = self._make_messenger_btn(
            "max", "Max (VK Teams)",
            "Скоро",
            bg="#ffffff", fg="#333333", border="#d9d9d9",
            hover="#f5f5f5", pressed="#eeeeee",
        )
        max_btn.setEnabled(False)
        layout.addWidget(max_btn)

        # WhatsApp
        wa_btn = self._make_messenger_btn(
            "whatsapp", "WhatsApp",
            "Скоро",
            bg="#ffffff", fg="#333333", border="#d9d9d9",
            hover="#f5f5f5", pressed="#eeeeee",
        )
        wa_btn.setEnabled(False)
        layout.addWidget(wa_btn)

        layout.addStretch()
        return page

    def _make_messenger_btn(
        self, icon_name: str, title: str, subtitle: str,
        bg: str, fg: str, border: str, hover: str, pressed: str,
    ) -> QPushButton:
        btn = QPushButton()
        btn.setFixedHeight(56)
        btn.setCursor(Qt.PointingHandCursor)

        icon = IconLoader.load(icon_name)
        if icon and not icon.isNull():
            btn.setIcon(icon)
            btn.setIconSize(QSize(24, 24))

        btn.setText(f"  {title}     {subtitle}")
        btn.setStyleSheet(_MESSENGER_BTN_STYLE.format(
            bg=bg, fg=fg, border=border, hover=hover, pressed=pressed,
        ))
        return btn

    # ----------------------------------------------------------------
    # Страница 2: Настройка чата
    # ----------------------------------------------------------------

    def _create_config_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 12, 24, 20)
        layout.setSpacing(14)

        # --- Название чата ---
        title_label = QLabel("Название чата")
        title_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        layout.addWidget(title_label)

        self._chat_title_edit = QLineEdit()
        self._chat_title_edit.setPlaceholderText("ИН-Город-Адрес")
        self._chat_title_edit.setStyleSheet(_INPUT_STYLE)
        self._chat_title_edit.setText(self._build_default_title())
        layout.addWidget(self._chat_title_edit)

        # --- Способ создания ---
        method_label = QLabel("Способ создания")
        method_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        layout.addWidget(method_label)

        self._method_group = QButtonGroup(self)
        self._radio_auto = QRadioButton("Автоматическое создание группы")
        self._radio_manual = QRadioButton("Привязать существующий чат (вставить ссылку)")
        self._radio_auto.setStyleSheet(_RADIO_STYLE)
        self._radio_manual.setStyleSheet(_RADIO_STYLE)
        self._method_group.addButton(self._radio_auto, 0)
        self._method_group.addButton(self._radio_manual, 1)
        self._radio_manual.setChecked(True)  # По умолчанию — ручная привязка (безопаснее)

        layout.addWidget(self._radio_auto)
        layout.addWidget(self._radio_manual)

        # Поле для invite-ссылки (показываем при ручном режиме)
        self._invite_link_edit = QLineEdit()
        self._invite_link_edit.setPlaceholderText("https://t.me/+ABC123... или числовой chat_id")
        self._invite_link_edit.setStyleSheet(_INPUT_STYLE)
        layout.addWidget(self._invite_link_edit)

        self._radio_auto.toggled.connect(self._on_method_toggled)
        self._radio_manual.toggled.connect(self._on_method_toggled)
        self._on_method_toggled()

        # --- Участники ---
        members_label = QLabel("Участники чата")
        members_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #333;")
        layout.addWidget(members_label)

        members_frame = QFrame()
        members_frame.setStyleSheet("""
            QFrame {
                border: 1px solid #e6e6e6;
                border-radius: 6px;
                background-color: #fafafa;
            }
        """)
        members_layout = QVBoxLayout(members_frame)
        members_layout.setContentsMargins(12, 10, 12, 10)
        members_layout.setSpacing(4)

        self._build_participant_checkboxes(members_layout)
        layout.addWidget(members_frame)

        # --- Аватар ---
        avatar_row = QHBoxLayout()
        avatar_row.setSpacing(10)
        av_label = QLabel("Аватар группы:")
        av_label.setStyleSheet("font-size: 13px; color: #666;")
        avatar_row.addWidget(av_label)

        self._avatar_preview = QLabel()
        self._avatar_preview.setFixedSize(36, 36)
        self._avatar_preview.setStyleSheet("border-radius: 18px; border: 1px solid #e0e0e0;")
        avatar_row.addWidget(self._avatar_preview)

        agent_type = (self.card_data.get("agent_type") or "").lower()
        logo_file = "petrovich_logo.png" if "петрович" in agent_type or "petrovich" in agent_type else "festival_logo.png"
        pixmap = QPixmap(resource_path(f"resources/{logo_file}"))
        if not pixmap.isNull():
            self._avatar_preview.setPixmap(
                pixmap.scaled(36, 36, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        av_name = QLabel(logo_file.replace("_logo.png", "").replace("_", " ").title())
        av_name.setStyleSheet("font-size: 13px; color: #333;")
        avatar_row.addWidget(av_name)
        avatar_row.addStretch()
        layout.addLayout(avatar_row)

        layout.addStretch()

        # --- Кнопки ---
        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        self._back_btn = QPushButton("Назад")
        self._back_btn.setFixedHeight(38)
        self._back_btn.setCursor(Qt.PointingHandCursor)
        self._back_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff;
                color: #333333;
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 0 24px;
                font-size: 13px;
            }
            QPushButton:hover { background-color: #f5f5f5; border-color: #bfbfbf; }
        """)
        self._back_btn.clicked.connect(self._go_back)
        btn_row.addWidget(self._back_btn)

        btn_row.addStretch()

        self._create_btn = QPushButton("Создать чат")
        self._create_btn.setFixedHeight(38)
        self._create_btn.setCursor(Qt.PointingHandCursor)
        self._create_btn.setStyleSheet("""
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
            QPushButton:disabled { background-color: #f0f0f0; color: #b0b0b0; }
        """)
        self._create_btn.clicked.connect(self._on_create)
        btn_row.addWidget(self._create_btn)

        layout.addLayout(btn_row)
        return page

    # ----------------------------------------------------------------
    # Участники
    # ----------------------------------------------------------------

    def _build_participant_checkboxes(self, layout: QVBoxLayout):
        """Построить чекбоксы участников из card_data"""
        self._participant_checkboxes = []

        # Директор: ищем среди сотрудников
        director_info = self._find_director()
        if director_info:
            self._add_participant_cb(
                layout, "Директор", director_info["name"],
                director_info["id"], mandatory=True,
            )

        # Старший менеджер (обязательный)
        sm_id = self.card_data.get("senior_manager_id")
        sm_name = self.card_data.get("senior_manager_name")
        if sm_id and sm_name:
            self._add_participant_cb(layout, "Старший менеджер", sm_name, sm_id, mandatory=True)

        # СДП (опциональный)
        sdp_id = self.card_data.get("sdp_id")
        sdp_name = self.card_data.get("sdp_name")
        if sdp_id and sdp_name:
            self._add_participant_cb(layout, "СДП", sdp_name, sdp_id, mandatory=False, checked=True)

        # ГАП (опциональный)
        gap_id = self.card_data.get("gap_id")
        gap_name = self.card_data.get("gap_name")
        if gap_id and gap_name:
            self._add_participant_cb(layout, "ГАП", gap_name, gap_id, mandatory=False, checked=True)

        # Менеджер (опциональный)
        mgr_id = self.card_data.get("manager_id")
        mgr_name = self.card_data.get("manager_name")
        if mgr_id and mgr_name:
            self._add_participant_cb(layout, "Менеджер", mgr_name, mgr_id, mandatory=False, checked=True)

        # Дизайнер / Чертёжник из stage_executors
        stage_executors = self.card_data.get("stage_executors") or []
        seen_ids = set()
        for se in stage_executors:
            se_id = se.get("executor_id")
            se_name = se.get("executor_name", "")
            stage = (se.get("stage_name") or "").lower()
            if not se_id or se_id in seen_ids:
                continue
            seen_ids.add(se_id)

            if "дизайн" in stage:
                self._add_participant_cb(
                    layout, "Дизайнер", se_name, se_id,
                    mandatory=False, checked=False,
                )
            elif "черт" in stage:
                self._add_participant_cb(
                    layout, "Чертёжник", se_name, se_id,
                    mandatory=False, checked=False,
                )

        if not self._participant_checkboxes:
            no_data = QLabel("Исполнители не назначены")
            no_data.setStyleSheet("color: #999; font-size: 12px; padding: 4px;")
            layout.addWidget(no_data)

    def _add_participant_cb(
        self, layout: QVBoxLayout, role: str, name: str,
        employee_id: int, mandatory: bool = False, checked: bool = True,
    ):
        cb = QCheckBox(f"{role}: {name}")
        cb.setStyleSheet(_CHECKBOX_STYLE)
        cb.setChecked(checked or mandatory)
        if mandatory:
            cb.setEnabled(False)
        layout.addWidget(cb)

        self._participant_checkboxes.append({
            "checkbox": cb,
            "role": role,
            "name": name,
            "employee_id": employee_id,
            "mandatory": mandatory,
        })

    def _find_director(self) -> Optional[Dict]:
        """Найти директора среди сотрудников"""
        try:
            employees = []
            if self.data_access:
                employees = self.data_access.get_all_employees()
            elif self.api_client:
                employees = self.api_client.get_employees(skip=0, limit=1000)

            for emp in (employees or []):
                pos = (emp.get("position") or emp.get("role") or "").lower()
                if "директор" in pos:
                    return {
                        "id": emp.get("id"),
                        "name": emp.get("full_name") or emp.get("name", "Директор"),
                    }
        except Exception as e:
            logger.warning(f"Не удалось найти директора: {e}")
        return None

    # ----------------------------------------------------------------
    # Навигация
    # ----------------------------------------------------------------

    def _on_messenger_chosen(self, messenger: str):
        self._selected_messenger = messenger
        self._title_bar.set_title(f"Настройка чата — {messenger.title()}")
        self._update_create_btn_text()
        self._stack.setCurrentIndex(1)

    def _go_back(self):
        self._title_bar.set_title("Создать чат")
        self._stack.setCurrentIndex(0)

    def _on_method_toggled(self):
        is_manual = self._radio_manual.isChecked()
        self._invite_link_edit.setVisible(is_manual)
        self._update_create_btn_text()

    def _update_create_btn_text(self):
        if not hasattr(self, '_create_btn') or self._create_btn is None:
            return
        if self._radio_manual.isChecked():
            self._create_btn.setText("Привязать чат")
        else:
            self._create_btn.setText("Создать чат")

    # ----------------------------------------------------------------
    # Вспомогательные
    # ----------------------------------------------------------------

    def _build_default_title(self) -> str:
        """Сформировать название чата из данных карточки"""
        city = self.card_data.get("city", "")
        address = self.card_data.get("address", "")
        # Убираем дублирование города из адреса (если адрес начинается с города)
        if address and city:
            # Адрес может содержать "Санкт_петербург. ..." — убираем город-префикс
            addr_lower = address.lower().replace("_", "-").replace(".", "").strip()
            city_lower = city.lower().replace("_", "-")
            # Убираем варианты: "Санкт-Петербург", "Санкт_петербург", "СПБ"
            for prefix in [city_lower, city_lower.replace("-", "_")]:
                if addr_lower.startswith(prefix):
                    address = address[len(prefix):].lstrip(".,;: ")
                    break
            # Также убираем полное название города если оно в начале адреса
            city_full_map = {
                "спб": "Санкт-Петербург",
                "мск": "Москва",
                "нск": "Новосибирск",
                "екб": "Екатеринбург",
            }
            full_city = city_full_map.get(city_lower, "")
            if full_city:
                full_lower = full_city.lower()
                addr_check = address.lower().replace("_", "-")
                if addr_check.startswith(full_lower):
                    address = address[len(full_city):].lstrip(".,;:_ ")
        # Заменяем подчёркивания на дефисы
        if city:
            city = city.replace("_", "-")
        if address:
            address = address.replace("_", "-")
        parts = ["ИН"]
        if city:
            parts.append(city)
        if address:
            parts.append(address)
        return "-".join(parts) if len(parts) > 1 else ""

    def _collect_members(self) -> List[Dict]:
        """Собрать список выбранных участников"""
        members = []
        for item in self._participant_checkboxes:
            cb: QCheckBox = item["checkbox"]
            if cb.isChecked():
                members.append({
                    "member_type": "employee",
                    "member_id": item["employee_id"],
                    "role_in_project": item["role"],
                    "is_mandatory": item["mandatory"],
                })
        return members

    # ----------------------------------------------------------------
    # Создание / привязка
    # ----------------------------------------------------------------

    def _on_create(self):
        """Обработчик кнопки Создать/Привязать"""
        from ui.custom_message_box import CustomMessageBox

        chat_title = self._chat_title_edit.text().strip()
        if not chat_title:
            CustomMessageBox(self, "Ошибка", "Укажите название чата", "warning").exec_()
            return

        is_manual = self._radio_manual.isChecked()
        if is_manual:
            invite_link = self._invite_link_edit.text().strip()
            if not invite_link:
                CustomMessageBox(
                    self, "Ошибка",
                    "Вставьте invite-ссылку на чат", "warning",
                ).exec_()
                return

        crm_card_id = self.card_data.get("id")
        if not crm_card_id:
            CustomMessageBox(self, "Ошибка", "Не определён ID карточки", "error").exec_()
            return

        members = self._collect_members()

        self._create_btn.setEnabled(False)
        self._create_btn.setText("Подождите...")

        try:
            if is_manual:
                # Привязка
                invite_link = self._invite_link_edit.text().strip()
                result = self._do_bind(crm_card_id, invite_link, members)
            else:
                # Автоматическое создание
                result = self._do_create(crm_card_id, members)

            if result:
                self.result_chat_data = result
                CustomMessageBox(
                    self, "Готово",
                    "Чат успешно " + ("привязан" if is_manual else "создан"),
                    "success",
                ).exec_()
                self.accept()
            else:
                CustomMessageBox(
                    self, "Ошибка",
                    "Не удалось " + ("привязать" if is_manual else "создать") + " чат.\n"
                    "Проверьте подключение к серверу.",
                    "error",
                ).exec_()
        except Exception as e:
            logger.error(f"Ошибка создания чата: {e}")
            CustomMessageBox(
                self, "Ошибка", f"Произошла ошибка:\n{str(e)}", "error",
            ).exec_()
        finally:
            self._create_btn.setEnabled(True)
            self._update_create_btn_text()

    def _do_create(self, crm_card_id: int, members: List[Dict]) -> Optional[Dict]:
        """Автоматическое создание чата через MTProto"""
        if self.data_access:
            return self.data_access.create_messenger_chat(
                crm_card_id, self._selected_messenger, members,
            )
        elif self.api_client:
            return self.api_client.create_messenger_chat(
                crm_card_id, self._selected_messenger, members,
            )
        return None

    def _do_bind(self, crm_card_id: int, invite_link: str, members: List[Dict]) -> Optional[Dict]:
        """Привязка существующего чата"""
        if self.data_access:
            return self.data_access.bind_messenger_chat(
                crm_card_id, invite_link, self._selected_messenger, members,
            )
        elif self.api_client:
            return self.api_client.bind_messenger_chat(
                crm_card_id, invite_link, self._selected_messenger, members,
            )
        return None
