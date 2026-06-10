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
        left.setMinimumWidth(320)
        left.setMaximumWidth(460)
        left.setStyleSheet("background: #FAFAFA;")
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(0)

        # Заголовок
        hdr = QFrame()
        hdr.setFixedHeight(48)
        hdr.setStyleSheet("background: #fff;")
        hh = QHBoxLayout(hdr)
        hh.setContentsMargins(12, 0, 8, 0)
        title = QLabel("Чаты сотрудников")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        hh.addWidget(title, stretch=1)
        lv.addWidget(hdr)

        # Поиск + кнопка обновления в одном ряду
        search_row = QFrame()
        search_row.setFixedHeight(34)
        search_row.setStyleSheet("background: #fff;")
        sr = QHBoxLayout(search_row)
        sr.setContentsMargins(0, 3, 4, 3)
        sr.setSpacing(0)

        self._search = QLineEdit()
        self._search.setPlaceholderText("Поиск по названию чата…")
        self._search.setFixedHeight(28)
        self._search.setStyleSheet("""
            QLineEdit {
                border: none;
                padding: 0 12px;
                font-size: 12px;
                background: #fff;
            }
        """)
        self._search.textChanged.connect(self._filter_list)
        sr.addWidget(self._search, stretch=1)

        from PyQt5.QtWidgets import QPushButton

        refresh_btn = QPushButton("⟳")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setToolTip("Обновить список чатов")
        refresh_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid transparent;
                border-radius: 4px; font-size: 16px; color: #666;
                padding: 0;
            }
            QPushButton:hover { background: #f0f0f0; border-color: #d9d9d9; color: #333; }
        """)
        refresh_btn.clicked.connect(self._load_chats)
        sr.addWidget(refresh_btn)
        lv.addWidget(search_row)

        # Список
        self._list = QListWidget()
        self._list.setStyleSheet("""
            QListWidget { border: none; background: #FAFAFA; }
            QListWidget::item { padding: 0; }
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
        splitter.setSizes([360, 900])

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
        from PyQt5.QtCore import QSize
        from PyQt5.QtGui import QColor

        self._list.clear()
        q = text.lower()

        visible = []
        for chat in self._chats:
            title = chat.get("title") or f"Чат #{chat['id']}"
            if q and q not in title.lower():
                continue
            visible.append((chat, title))

        admin = [(c, t) for c, t in visible if c.get("is_admin_chat")]
        pinned = [(c, t) for c, t in visible if not c.get("is_admin_chat") and c.get("is_pinned_by_user")]
        regular = [(c, t) for c, t in visible if not c.get("is_admin_chat") and not c.get("is_pinned_by_user")]

        def add_section_header(label: str):
            sep = QListWidgetItem(label)
            sep.setFlags(Qt.NoItemFlags)
            sep.setBackground(QColor("#F0F0F0"))
            sep.setForeground(QColor("#888888"))
            sep.setSizeHint(QSize(0, 22))
            font = sep.font()
            font.setPointSize(8)
            font.setBold(True)
            sep.setFont(font)
            self._list.addItem(sep)

        def add_chat_row(chat, title):
            item = QListWidgetItem()
            item.setData(Qt.UserRole, chat)
            widget = self._make_chat_item(chat, title)
            lines = max(1, (len(title) + 39) // 40)
            row_h = max(56, 32 + lines * 18)
            item.setSizeHint(QSize(0, row_h))
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

        if admin:
            add_section_header("  АДМИНИСТРАТИВНЫЕ")
            for chat, title in admin:
                add_chat_row(chat, title)

        if pinned:
            add_section_header("  ЗАКРЕПЛЁННЫЕ")
            for chat, title in pinned:
                add_chat_row(chat, title)

        if regular:
            if admin or pinned:
                add_section_header("  ВСЕ ЧАТЫ")
            for chat, title in regular:
                add_chat_row(chat, title)

    def _make_chat_item(self, chat: dict, title: str) -> QWidget:
        is_admin = bool(chat.get("is_admin_chat"))
        is_pinned = bool(chat.get("is_pinned_by_user"))

        if is_admin:
            bg = "#E3F2FD"
            border = "border-left: 3px solid #1565C0;"
            avatar_bg = "#BBDEFB"
            avatar_color = "#0D47A1"
            avatar_char = "А"
            title_color = "#0D47A1"
        elif is_pinned:
            bg = "#FFFDE7"
            border = "border-left: 3px solid #F9A825;"
            avatar_bg = "#FFF9C4"
            avatar_color = "#F57F17"
            avatar_char = "С"
            title_color = "#212121"
        else:
            bg = "transparent"
            border = ""
            avatar_bg = "#FFF8DC"
            avatar_color = "#a0880c"
            avatar_char = "С"
            title_color = "#212121"

        w = QWidget()
        w.setStyleSheet(f"QWidget {{ background: {bg}; {border} }}")
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(10)

        # Аватар
        avatar = QLabel(avatar_char)
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet(f"""
            QLabel {{
                background: {avatar_bg};
                color: {avatar_color};
                border-radius: 20px;
                font-size: 16px;
                font-weight: bold;
            }}
        """)
        h.addWidget(avatar)

        v = QVBoxLayout()
        v.setSpacing(2)

        title_prefix = "📌 " if is_pinned else ""
        title_lbl = QLabel(title_prefix + title)
        title_lbl.setStyleSheet(f"font-weight: bold; font-size: 12px; color: {title_color};")
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v.addWidget(title_lbl)

        last = chat.get("last_message", "")
        if last:
            last_lbl = QLabel(last[:50] + ("…" if len(last) > 50 else ""))
            last_lbl.setStyleSheet("font-size: 10px; color: #888;")
            last_lbl.setWordWrap(True)
            last_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            v.addWidget(last_lbl)

        h.addLayout(v, stretch=1)

        unread = chat.get("unread_count", 0)
        if unread:
            badge = QLabel(str(unread) if unread < 100 else "99+")
            badge.setFixedSize(24, 24)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("""
                background: #E53935; color: #fff;
                border-radius: 12px; font-size: 9px; font-weight: bold;
            """)
            h.addWidget(badge)

        # Кнопка закрепить / открепить (только для не-административных чатов)
        if not is_admin:
            pin_btn = QPushButton("📌")
            pin_btn.setFixedSize(26, 26)
            pin_btn.setToolTip("Открепить" if is_pinned else "Закрепить сверху")
            pin_btn.setStyleSheet("""
                QPushButton {
                    background: transparent; border: none;
                    font-size: 14px; padding: 0;
                    opacity: 0.6;
                }
                QPushButton:hover { background: rgba(0,0,0,0.06); border-radius: 4px; }
            """)
            chat_id = chat["id"]
            if is_pinned:
                pin_btn.clicked.connect(lambda _, cid=chat_id: self._unpin_chat(cid))
            else:
                pin_btn.clicked.connect(lambda _, cid=chat_id: self._pin_chat(cid))
            h.addWidget(pin_btn)

        return w

    def _on_chat_selected(self, item: QListWidgetItem):
        chat = item.data(Qt.UserRole)
        if not chat:
            return
        self._open_room(chat["id"], chat.get("title", "Чат"))

    def _open_room(self, chat_id: int, title: str):
        # Останавливаем предыдущий виджет
        if self._current_room:
            self._current_room.cleanup()
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
        room.unread_changed.connect(self._on_unread_changed)
        self._right.layout().addWidget(room)
        self._current_room = room

    def _on_unread_changed(self, chat_id: int, unread_count: int):
        """Обновить бейдж непрочитанных в списке чатов без перезагрузки."""
        for i, chat in enumerate(self._chats):
            if chat.get("id") == chat_id:
                self._chats[i] = dict(chat, unread_count=unread_count)
                break
        self._filter_list(self._search.text())

    # ===========================================================
    # Pin / Unpin
    # ===========================================================

    def _pin_chat(self, chat_id: int):
        def _worker():
            ok = self._api.pin_chat(chat_id)
            if ok:
                for i, c in enumerate(self._chats):
                    if c.get("id") == chat_id:
                        self._chats[i] = dict(c, is_pinned_by_user=True)
                        break
                self._sig_chats.emit(self._chats)

        threading.Thread(target=_worker, daemon=True).start()

    def _unpin_chat(self, chat_id: int):
        def _worker():
            ok = self._api.unpin_chat(chat_id)
            if ok:
                for i, c in enumerate(self._chats):
                    if c.get("id") == chat_id:
                        self._chats[i] = dict(c, is_pinned_by_user=False)
                        break
                self._sig_chats.emit(self._chats)

        threading.Thread(target=_worker, daemon=True).start()

    # ===========================================================
    # Публичные
    # ===========================================================

    def refresh(self):
        self._load_chats()
        if self._current_room:
            self._current_room.refresh()
