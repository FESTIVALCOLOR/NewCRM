"""
Вкладка "Чат с клиентами" — главное меню CRM.

Структура:
  QSplitter
    LEFT:  ChatListWidget — список клиентских чатов с поиском
    RIGHT: ChatRoomWidget + панель управления (ссылки, скрипт)
"""

import threading

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QClipboard
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.chat_room_widget import ChatRoomWidget
from utils.permissions import _has_perm


class ClientChatsTab(QWidget):
    """
    Параметры
    ---------
    employee   : dict  — {'id': ..., 'full_name': ..., ...}
    api_client : APIClient
    """

    def __init__(self, employee: dict, api_client, parent=None):
        super().__init__(parent)
        self._employee = employee
        self._api = api_client
        self._chats = []
        self._current_room: ChatRoomWidget | None = None
        self._current_chat: dict | None = None
        self._can_manage = _has_perm(employee, api_client, "chat.client.manage")
        self._can_script = _has_perm(employee, api_client, "chat.client.send_script")
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
        title = QLabel("Чаты с клиентами")
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
            QListWidget::item { padding: 10px 12px; border-bottom: 1px solid #EFEFEF; }
            QListWidget::item:selected { background: #E8F5E9; }
            QListWidget::item:hover { background: #F5F5F5; }
        """)
        self._list.itemClicked.connect(self._on_chat_selected)
        lv.addWidget(self._list, stretch=1)

        splitter.addWidget(left)

        # ------- RIGHT: чат + панель управления -------
        right_outer = QWidget()
        rv = QVBoxLayout(right_outer)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        # Панель управления чатом (сверху)
        self._ctrl_panel = self._build_ctrl_panel()
        rv.addWidget(self._ctrl_panel)

        # Область чата
        self._right = QWidget()
        inner_v = QVBoxLayout(self._right)
        inner_v.setContentsMargins(0, 0, 0, 0)

        self._placeholder = QLabel("Выберите чат слева")
        self._placeholder.setAlignment(Qt.AlignCenter)
        self._placeholder.setStyleSheet("color: #aaa; font-size: 16px;")
        inner_v.addWidget(self._placeholder)
        rv.addWidget(self._right, stretch=1)

        splitter.addWidget(right_outer)
        splitter.setSizes([280, 700])

        layout.addWidget(splitter)

    def _build_ctrl_panel(self) -> QFrame:
        """Верхняя панель: ссылка-приглашение + кнопки управления."""
        panel = QFrame()
        panel.setFixedHeight(40)
        panel.setStyleSheet("background: #f0f7f0; border-bottom: 1px solid #C8E6C9;")
        panel.setVisible(False)  # показывается при выборе чата

        h = QHBoxLayout(panel)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(8)

        self._link_label = QLabel("Ссылка клиента:")
        self._link_label.setStyleSheet("font-size: 11px; color: #555;")
        h.addWidget(self._link_label)

        self._link_value = QLabel("")
        self._link_value.setStyleSheet("""
            font-size: 11px; color: #1565C0;
            text-decoration: underline;
        """)
        self._link_value.setCursor(Qt.PointingHandCursor)
        self._link_value.setOpenExternalLinks(False)
        self._link_value.mousePressEvent = self._copy_link
        h.addWidget(self._link_value)

        copy_btn = QPushButton("Копировать")
        copy_btn.setFixedHeight(26)
        copy_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px; padding: 0 10px;
                border: 1px solid #81C784; border-radius: 4px;
                background: #fff;
            }
            QPushButton:hover { background: #E8F5E9; }
        """)
        copy_btn.clicked.connect(self._on_copy_link)
        h.addWidget(copy_btn)

        h.addStretch()

        if self._can_script:
            script_btn = QPushButton("Отправить скрипт")
            script_btn.setFixedHeight(26)
            script_btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px; padding: 0 12px;
                    border: 1px solid #2196F3; border-radius: 4px;
                    background: #fff; color: #1565C0;
                }
                QPushButton:hover { background: #E3F2FD; }
            """)
            script_btn.clicked.connect(self._send_script)
            h.addWidget(script_btn)

        if self._can_manage:
            invite_btn = QPushButton("Добавить участника")
            invite_btn.setFixedHeight(26)
            invite_btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px; padding: 0 12px;
                    border: 1px solid #4CAF50; border-radius: 4px;
                    background: #fff; color: #2E7D32;
                }
                QPushButton:hover { background: #E8F5E9; }
            """)
            invite_btn.clicked.connect(self._add_client_member)
            h.addWidget(invite_btn)

        return panel

    def showEvent(self, event):
        super().showEvent(event)
        self._load_chats()

    # ===========================================================
    # Загрузка и фильтрация
    # ===========================================================

    def _load_chats(self):
        def _worker():
            chats = self._api.get_internal_chats(chat_type="client")
            QTimer.singleShot(0, lambda c=chats: self._fill_list(c))

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
        h.setContentsMargins(0, 4, 8, 4)
        h.setSpacing(6)

        v = QVBoxLayout()
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet("font-weight: bold; font-size: 12px;")
        v.addWidget(title_lbl)

        # Показываем количество участников-клиентов
        members = chat.get("member_count", 0)
        guests = chat.get("guest_count", 0)
        sub = f"{members} уч."
        if guests:
            sub += f", {guests} клиент(ов)"
        sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet("font-size: 10px; color: #888;")
        v.addWidget(sub_lbl)

        h.addLayout(v, stretch=1)

        unread = chat.get("unread_count", 0)
        if unread:
            badge = QLabel(str(unread))
            badge.setFixedSize(20, 20)
            badge.setAlignment(Qt.AlignCenter)
            badge.setStyleSheet("""
                background: #ff4444; color: #fff;
                border-radius: 10px; font-size: 9px; font-weight: bold;
            """)
            h.addWidget(badge)

        return w

    def _on_chat_selected(self, item: QListWidgetItem):
        chat = item.data(Qt.UserRole)
        if not chat:
            return
        self._current_chat = chat
        self._open_room(chat["id"], chat.get("title", "Чат"))
        self._update_ctrl_panel(chat)

    def _open_room(self, chat_id: int, title: str):
        if self._current_room:
            self._current_room.hide()
            self._right.layout().removeWidget(self._current_room)
            self._current_room.deleteLater()
            self._current_room = None

        self._placeholder.hide()

        room = ChatRoomWidget(
            chat_id=chat_id,
            chat_type="client",
            employee=self._employee,
            api_client=self._api,
            parent=self._right,
        )
        room.set_title(title)
        self._right.layout().addWidget(room)
        self._current_room = room

    def _update_ctrl_panel(self, chat: dict):
        """Обновить панель управления для выбранного чата."""
        token = chat.get("client_access_token", "")
        if token:
            # Формируем URL клиентского чата
            from config import SERVER_URL

            base = SERVER_URL.rstrip("/")
            # Для PWA используем mobile-порт или тот же домен
            link = f"{base}/c/{token}"
            short = link[:50] + "…" if len(link) > 50 else link
            self._link_value.setText(short)
            self._link_value.setToolTip(link)
            self._link_value._full_link = link
            self._ctrl_panel.setVisible(True)
        else:
            self._ctrl_panel.setVisible(False)

    def _copy_link(self, _event=None):
        """Клик по ссылке — копировать."""
        self._on_copy_link()

    def _on_copy_link(self):
        link = getattr(self._link_value, "_full_link", "")
        if link:
            QApplication.clipboard().setText(link)
            old = self._link_value.text()
            self._link_value.setText("Скопировано!")
            QTimer.singleShot(1500, lambda: self._link_value.setText(old))

    def _send_script(self):
        """Отправить скрипт в клиентский чат."""
        if not self._current_chat:
            return
        dlg = ScriptSendDialog(
            chat_id=self._current_chat["id"],
            api_client=self._api,
            parent=self,
        )
        dlg.exec_()

    def _add_client_member(self):
        """Создать дополнительную ссылку-приглашение для клиентской стороны."""
        if not self._current_chat:
            return
        try:
            result = self._api.create_client_invite_link(self._current_chat["id"])
            if result:
                token = result.get("access_token", "")
                from config import SERVER_URL

                link = f"{SERVER_URL.rstrip('/')}/c/{token}"
                InviteLinkDialog(link=link, parent=self).exec_()
        except Exception as e:
            print(f"[ClientChatsTab] Ошибка создания ссылки-приглашения: {e}")

    # ===========================================================
    # Публичные
    # ===========================================================

    def refresh(self):
        self._load_chats()
        if self._current_room:
            self._current_room.refresh()


# ===========================================================
# Вспомогательные диалоги
# ===========================================================


class ScriptSendDialog(QDialog):
    """Диалог отправки скрипта в клиентский чат."""

    def __init__(self, chat_id: int, api_client, parent=None):
        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self._chat_id = chat_id
        self._api = api_client
        self.setWindowTitle("Отправить скрипт клиенту")
        self.setMinimumWidth(480)
        self.setMinimumHeight(320)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Текст скрипта:"))
        self._text = QTextEdit()
        self._text.setPlaceholderText("Введите текст скрипта…")
        layout.addWidget(self._text, stretch=1)

        btns = QHBoxLayout()
        btns.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(30)
        cancel_btn.clicked.connect(self.reject)
        btns.addWidget(cancel_btn)

        send_btn = QPushButton("Отправить")
        send_btn.setFixedHeight(30)
        send_btn.setStyleSheet("""
            QPushButton {
                background: #2196F3; color: #fff;
                border-radius: 4px; border: none; padding: 0 20px;
            }
            QPushButton:hover { background: #1565C0; }
        """)
        send_btn.clicked.connect(self._send)
        btns.addWidget(send_btn)
        layout.addLayout(btns)

    def _send(self):
        text = self._text.toPlainText().strip()
        if not text:
            return
        try:
            self._api.send_chat_message(
                chat_id=self._chat_id,
                content=text,
                message_type="system",
            )
            self.accept()
        except Exception as e:
            print(f"[ScriptSendDialog] Ошибка отправки: {e}")


class InviteLinkDialog(QDialog):
    """Показывает ссылку-приглашение для клиента."""

    def __init__(self, link: str, parent=None):
        super().__init__(parent, Qt.WindowTitleHint | Qt.WindowCloseButtonHint)
        self.setWindowTitle("Ссылка для клиента")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        layout.addWidget(QLabel("Отправьте клиенту эту ссылку для входа в чат:"))

        link_edit = QLineEdit(link)
        link_edit.setReadOnly(True)
        link_edit.setStyleSheet("font-size: 12px; padding: 4px;")
        layout.addWidget(link_edit)

        btns = QHBoxLayout()
        btns.addStretch()

        copy_btn = QPushButton("Копировать")
        copy_btn.setFixedHeight(30)
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(link))
        btns.addWidget(copy_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(30)
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)

        layout.addLayout(btns)
