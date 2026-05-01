"""
Вкладка "Чаты сотрудников" — главное меню CRM.

Структура:
  QSplitter
    LEFT:  ChatListWidget — список чатов с поиском
    RIGHT: ChatRoomWidget или заглушка
"""

import threading

from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ui.chat_room_widget import ChatRoomWidget


class EmployeeChatsTab(QWidget):
    """
    Параметры
    ---------
    employee   : dict  — {'id': ..., 'full_name': ..., ...}
    api_client : APIClient
    """

    _sig_chats = pyqtSignal(object)  # list[dict] — thread-safe обновление списка чатов

    def __init__(self, employee: dict, api_client, parent=None):
        super().__init__(parent)
        self._employee = employee
        self._api = api_client
        self._chats = []
        self._current_room: ChatRoomWidget | None = None
        self._sig_chats.connect(self._fill_list)
        self._setup_ui()
        self._load_chats()

    # ===========================================================
    # UI
    # ===========================================================

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet("QSplitter::handle { background: #E0E0E0; }")

        # ------- LEFT: список чатов -------
        left = QWidget()
        left.setMinimumWidth(260)
        left.setMaximumWidth(360)
        left.setStyleSheet("background: #FAFAFA; border-right: 1px solid #E0E0E0;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        # Заголовок
        hdr = QFrame()
        hdr.setFixedHeight(48)
        hdr.setStyleSheet("background: #fff; border-bottom: 1px solid #E0E0E0;")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(12, 0, 8, 0)
        title = QLabel("Чаты сотрудников")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        hh.addWidget(title, stretch=1)
        from PyQt5.QtWidgets import QPushButton

        refresh_btn = QPushButton("↻")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Обновить список чатов")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid transparent;
                border-radius: 4px; font-size: 14px; color: #666;
            }
            QPushButton:hover { background: #f0f0f0; border-color: #d9d9d9; }
        """)
        refresh_btn.clicked.connect(self._load_chats)
        hh.addWidget(refresh_btn)
        lv.addWidget(hdr)

        # Поиск
        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по адресу объекта…")
        self._search.setFixedHeight(32)
        self._search.setStyleSheet("""
            QLineEdit {
                border: none;
                border-bottom: 1px solid #E0E0E0;
                padding: 0 12px;
                font-size: 12px;
                background: #fff;
            }
        """)
        self._search.textChanged.connect(self._filter_list)
        lv.addWidget(self._search)

        # Список
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget { border: none; background: #FAFAFA; }
            QListWidget::item { border-bottom: 1px solid #EFEFEF; padding: 0; }
            QListWidget::item:selected { background: #FFF8DC; }
            QListWidget::item:hover { background: #F0F0F0; }
        """)
        self._list.itemClicked.connect(self._on_chat_selected)
        lv.addWidget(self._list, stretch=1)

        splitter.addWidget(left)

        # ------- RIGHT: комната чата -------
        self._right = QWidget()
        rv = QVBoxLayout(self._right)
        rv.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Выберите чат слева")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #aaa; font-size: 16px;")
        rv.addWidget(self._placeholder)

        splitter.addWidget(self._right)
        splitter.setSizes([280, 700])

        layout.addWidget(splitter)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_chats()

    # ===========================================================
    # Загрузка и фильтрация
    # ===========================================================

    def _load_chats(self):
        def _worker():
            chats = self._api.get_internal_chats(chat_type="employee")
            self._sig_chats.emit(chats or [])  # thread-safe через сигнал

        threading.Thread(target=_worker, daemon=True).start()

    def _fill_list(self, chats: list):
        self._chats = chats or []
        self._filter_list(self._search.text())

    def _filter_list(self, text: str):
        self._list.clear()
        q = text.lower()
        for chat in self._chats:
            title = chat.get("title") or f"Чат #{chat['id']}"
            if q and q not in title.lower():
                continue
            item = QListWidgetItem()
            item.setData(Qt.UserRole, chat)
            widget = self._make_chat_item(chat, title)
            item.setSizeHint(widget.sizeHint())
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _make_chat_item(self, chat: dict, title: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(10)

        # Аватар — круглый с иконкой чата
        avatar = QLabel("С")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                background: #FFF8DC;
                color: #a0880c;
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }
        """)
        h.addWidget(avatar)

        v = QVBoxLayout()
        v.setSpacing(2)
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 12px; color: #212121;")
        title_lbl.setMinimumWidth(0)
        title_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        v.addWidget(title_lbl)

        last = chat.get("last_message", "")
        if last:
            last_lbl = QLabel(last[:50] + ("…" if len(last) > 50 else ""))
            last_lbl.setStyleSheet("font-size: 10px; color: #888;")
            last_lbl.setMinimumWidth(0)
            last_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
            v.addWidget(last_lbl)

        h.addLayout(v, stretch=1)

        unread = chat.get("unread_count", 0)
        if unread:
            badge = QLabel(str(unread) if unread < 100 else "99+")
            badge.setFixedSize(20, 20)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("""
                background: #E53935; color: #fff;
                border-radius: 10px; font-size: 9px; font-weight: bold;
            """)
            h.addWidget(badge)

        return w

    def _on_chat_selected(self, item: QListWidgetItem):
        chat = item.data(Qt.UserRole)
        if not chat:
            return
        self._open_room(chat["id"], chat.get("title", "Чат"))

    def _open_room(self, chat_id: int, title: str):
        # Останавливаем предыдущий виджет
        if self._current_room:
            self._current_room.hide()
            self._right.layout().removeWidget(self._current_room)
            self._current_room.deleteLater()
            self._current_room = None

        self._placeholder.hide()

        room = ChatRoomWidget(
            chat_id=chat_id,
            chat_type="employee",
            employee=self._employee,
            api_client=self._api,
            parent=self._right,
        )
        room.set_title(title)
        self._right.layout().addWidget(room)
        self._current_room = room

    # ===========================================================
    # Публичные
    # ===========================================================

    def refresh(self):
        self._load_chats()
        if self._current_room:
            self._current_room.refresh()
