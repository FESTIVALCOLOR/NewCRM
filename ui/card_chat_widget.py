"""
CardChatWidget — вкладка чата внутри CRM-карточки.

Для chat_type='employee': загружает или предлагает создать чат сотрудников по заказу.
Для chat_type='client': загружает или предлагает создать клиентский чат.
"""

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from utils.permissions import _has_perm


class CardChatWidget(QWidget):
    """Вкладка чата в карточке CRM. Ленивая загрузка — подключается только при первом показе."""

    def __init__(self, contract_id, chat_type, employee, api_client, parent=None):
        super().__init__(parent)
        self._contract_id = contract_id
        self._chat_type = chat_type  # 'employee' | 'client'
        self._employee = employee
        self._api_client = api_client
        self._chat_room = None
        self._initialized = False

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)

        # Placeholder — загружается при первом показе вкладки
        self._placeholder = self._build_loading_placeholder()
        self._layout.addWidget(self._placeholder)

    def _build_loading_placeholder(self):
        w = QFrame()
        vl = QVBoxLayout(w)
        vl.setAlignment(Qt.AlignCenter)
        lbl = QLabel("Загрузка чата...")
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #999; font-size: 13px;")
        vl.addWidget(lbl)
        return w

    def _build_empty_placeholder(self, can_create):
        """Нет активного чата — предлагаем создать или показываем сообщение."""
        w = QFrame()
        vl = QVBoxLayout(w)
        vl.setAlignment(Qt.AlignCenter)
        vl.setSpacing(12)

        icon_lbl = QLabel("💬")
        icon_lbl.setAlignment(Qt.AlignCenter)
        icon_lbl.setFont(QFont("", 32))
        vl.addWidget(icon_lbl)

        if self._chat_type == "employee":
            text = "Чат сотрудников по этому заказу ещё не создан"
        else:
            text = "Клиентский чат по этому заказу ещё не создан"
        lbl = QLabel(text)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: #666; font-size: 13px;")
        vl.addWidget(lbl)

        if can_create:
            btn_text = "Создать чат сотрудников" if self._chat_type == "employee" else "Создать чат с клиентом"
            btn = QPushButton(btn_text)
            btn.setFixedHeight(34)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2980B9;
                    color: white;
                    border-radius: 4px;
                    border: none;
                    font-size: 13px;
                    padding: 0 20px;
                }
                QPushButton:hover { background-color: #2471A3; }
                QPushButton:pressed { background-color: #1F618D; }
            """)
            btn.clicked.connect(self._create_chat)
            vl.addWidget(btn, alignment=Qt.AlignCenter)

        return w

    def showEvent(self, event):
        super().showEvent(event)
        if not self._initialized:
            self._initialized = True
            QTimer.singleShot(50, self._load_chat)

    def _load_chat(self):
        """Ищем активный чат для данного crm_card_id.

        Передаём crm_card_id явно — сервер использует get_card_chat_for_employee,
        которая автоматически добавляет сотрудника в участники при первом доступе.
        """
        try:
            # ВАЖНО: crm_card_id (не contract_id!) — сервер применяет auto-membership
            chats = self._api_client.get_internal_chats(
                chat_type=self._chat_type,
                crm_card_id=self._contract_id,
            )
        except Exception as e:
            print(f"[CardChatWidget] Ошибка загрузки чатов: {e}")
            chats = []

        active = None
        if chats:
            for c in chats:
                if c.get("is_active", True):
                    active = c
                    break

        if active:
            self._open_room(active)
        else:
            perm = "chat.employee.manage" if self._chat_type == "employee" else "chat.client.manage"
            can_create = _has_perm(self._employee, self._api_client, perm)
            self._replace_content(self._build_empty_placeholder(can_create))

    def _open_room(self, chat_info):
        """Показываем ChatRoomWidget для найденного чата."""
        try:
            from ui.chat_room_widget import ChatRoomWidget
        except ImportError as e:
            print(f"[CardChatWidget] Не удалось импортировать ChatRoomWidget: {e}")
            return

        room = ChatRoomWidget(
            chat_id=chat_info["id"],
            chat_type=self._chat_type,
            employee=self._employee,
            api_client=self._api_client,
            parent=self,
        )
        room.set_title(chat_info.get("title", "Чат"))
        self._chat_room = room
        self._replace_content(room)

    def _replace_content(self, new_widget):
        """Заменяем содержимое на новый виджет."""
        old = self._layout.itemAt(0)
        if old and old.widget():
            old.widget().deleteLater()
        self._layout.addWidget(new_widget)

    def _create_chat(self):
        """Создаём новый чат для карточки."""
        try:
            if self._chat_type == "employee":
                result = self._api_client.create_internal_chat(
                    chat_type="employee",
                    crm_card_id=self._contract_id,
                )
            else:
                result = self._api_client.create_internal_chat(
                    chat_type="client",
                    crm_card_id=self._contract_id,
                )
            if result:
                self._open_room(result)
        except Exception as e:
            print(f"[CardChatWidget] Ошибка создания чата: {e}")
