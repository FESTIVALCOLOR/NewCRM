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
    QSizePolicy,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.chat_room_widget import ChatRoomWidget
from ui.custom_title_bar import CustomTitleBar
from utils.permissions import _has_perm


class ClientChatsTab(QWidget):
    """
    Параметры
    ---------
    employee   : dict  — {'id': ..., 'full_name': ..., ...}
    api_client : APIClient
    """

    _sig_chats = pyqtSignal(object)  # list[dict] — thread-safe обновление списка

    def __init__(self, employee: dict, api_client, parent=None):
        super().__init__(parent)
        self._employee = employee
        self._api = api_client
        self._chats = []
        self._current_room: ChatRoomWidget | None = None
        self._current_chat: dict | None = None
        self._can_manage = _has_perm(employee, api_client, "chat.client.manage")
        self._can_script = _has_perm(employee, api_client, "chat.client.send_script")
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
        self._search.setFixedHeight(28)
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
            QListWidget::item:selected { background: #E8F5E9; }
            QListWidget::item:hover { background: #F0F0F0; }
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
        splitter.setSizes([360, 900])

        layout.addWidget(splitter)

    def _build_ctrl_panel(self) -> QFrame:
        """Верхняя панель: ссылка-приглашение + кнопки управления."""
        panel = QFrame()
        panel.setFixedHeight(44)
        panel.setStyleSheet("background: #FAFAFA; border-bottom: 1px solid #E0E0E0;")
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
        self._link_value.setMaximumWidth(240)
        self._link_value.setMinimumWidth(0)
        self._link_value.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        h.addWidget(self._link_value, stretch=1)

        copy_btn = QPushButton("Копировать")
        copy_btn.setFixedHeight(28)
        copy_btn.setStyleSheet("""
            QPushButton {
                font-size: 11px; padding: 0 10px; max-height: 26px;
                border: 1px solid #d9d9d9; border-radius: 4px;
                background: #fff;
            }
            QPushButton:hover { background: #f5f5f5; }
        """)
        copy_btn.clicked.connect(self._on_copy_link)
        h.addWidget(copy_btn)

        h.addStretch()

        if self._can_script:
            script_btn = QPushButton("Отправить скрипт")
            script_btn.setFixedHeight(28)
            script_btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px; padding: 0 12px; max-height: 26px;
                    border: 1px solid #d9d9d9; border-radius: 4px;
                    background: #fff; color: #333;
                }
                QPushButton:hover { background: #f5f5f5; }
            """)
            script_btn.clicked.connect(self._send_script)
            h.addWidget(script_btn)

        if self._can_manage:
            invite_btn = QPushButton("Добавить участника")
            invite_btn.setFixedHeight(28)
            invite_btn.setStyleSheet("""
                QPushButton {
                    font-size: 11px; padding: 0 12px; max-height: 26px;
                    border: 1px solid #d9d9d9; border-radius: 4px;
                    background: #fff; color: #333;
                }
                QPushButton:hover { background: #f5f5f5; }
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
            # Динамическая высота: минимум 56px, увеличивается при переносе названия
            from PyQt5.QtCore import QSize

            lines = max(1, (len(title) + 39) // 40)  # приблизительный подсчёт строк
            row_h = max(56, 32 + lines * 18)
            item.setSizeHint(QSize(0, row_h))
            self._list.addItem(item)
            self._list.setItemWidget(item, widget)

    def _make_chat_item(self, chat: dict, title: str) -> QWidget:
        w = QWidget()
        h = QHBoxLayout(w)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(10)

        # Аватар — круглый зелёный для клиентских чатов
        avatar = QLabel("К")
        avatar.setFixedSize(40, 40)
        avatar.setAlignment(Qt.AlignCenter)
        avatar.setStyleSheet("""
            QLabel {
                background: #E8F5E9;
                color: #2E7D32;
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
        title_lbl.setWordWrap(True)
        title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v.addWidget(title_lbl)

        # Показываем последнее сообщение или количество участников
        last = chat.get("last_message", "")
        if last:
            sub_lbl = QLabel(last[:50] + ("…" if len(last) > 50 else ""))
        else:
            members = chat.get("member_count", 0)
            guests = chat.get("guest_count", 0)
            sub = f"{members} уч."
            if guests:
                sub += f", {guests} клиент(ов)"
            sub_lbl = QLabel(sub)
        sub_lbl.setStyleSheet("font-size: 10px; color: #888;")
        sub_lbl.setWordWrap(True)
        sub_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v.addWidget(sub_lbl)

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
        room.unread_changed.connect(self._on_unread_changed)
        self._right.layout().addWidget(room)
        self._current_room = room

    def _on_unread_changed(self, chat_id: int, unread_count: int):
        for i, chat in enumerate(self._chats):
            if chat.get("id") == chat_id:
                self._chats[i] = dict(chat, unread_count=unread_count)
                break
        self._filter_list(self._search.text())

    def _update_ctrl_panel(self, chat: dict):
        """Обновить панель управления для выбранного чата."""
        token = chat.get("client_access_token", "")
        if token:
            base = self._api.base_url.rstrip("/")
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
            employee=self._employee,
            crm_card_id=self._current_chat.get("crm_card_id"),
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
                link = result.get("invite_link", "")
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
    """Двухэтапный диалог отправки скрипта: выбор из списка → редактирование → отправка."""

    _sig_data = pyqtSignal(object, object)  # (scripts_list, card_dict)

    def __init__(self, chat_id: int, api_client, employee: dict = None, crm_card_id: int = None, parent=None):
        super().__init__(parent)
        self._chat_id = chat_id
        self._api = api_client
        self._employee = employee or {}
        self._crm_card_id = crm_card_id
        self._card_data: dict = {}

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(500)

        self._sig_data.connect(self._fill_data)
        self._setup_ui()
        self._load_data()

    def _setup_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("borderFrame")
        frame.setStyleSheet("QFrame#borderFrame { background:#fff; border:1px solid #E0E0E0; border-radius:10px; }")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        title_bar = CustomTitleBar(self, "Отправить скрипт клиенту", simple_mode=True)
        title_bar.setStyleSheet("CustomTitleBar { background:#fff; border-bottom:1px solid #E0E0E0; border-top-left-radius:10px; border-top-right-radius:10px; }")
        fl.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet("background:#F9FAFB; border-bottom-left-radius:10px; border-bottom-right-radius:10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 14, 16, 16)
        cl.setSpacing(8)

        # ── Этап 1: список скриптов ──────────────────────────────
        self._stage1 = QWidget()
        s1 = QVBoxLayout(self._stage1)
        s1.setContentsMargins(0, 0, 0, 0)
        s1.setSpacing(6)

        s1_lbl = QLabel("Выберите скрипт:")
        s1_lbl.setStyleSheet("font-size: 12px; color: #555; font-weight: bold;")
        s1.addWidget(s1_lbl)

        self._loading_lbl = QLabel("Загрузка скриптов…")
        self._loading_lbl.setAlignment(Qt.AlignCenter)
        self._loading_lbl.setStyleSheet("font-size: 12px; color: #888; padding: 20px 0;")
        s1.addWidget(self._loading_lbl)

        self._scripts_list = QListWidget()
        self._scripts_list.setVisible(False)
        self._scripts_list.setFixedHeight(200)
        self._scripts_list.setStyleSheet("""
            QListWidget { border:1px solid #E0E0E0; border-radius:4px; background:#fff; }
            QListWidget::item { border-bottom:1px solid #f0f0f0; padding:6px 8px; }
            QListWidget::item:selected { background:#FFF8DC; }
            QListWidget::item:hover { background:#f5f5f5; }
        """)
        self._scripts_list.currentRowChanged.connect(lambda i: self._select_btn.setEnabled(i >= 0))
        self._scripts_list.itemDoubleClicked.connect(lambda _: self._on_select())
        s1.addWidget(self._scripts_list)
        cl.addWidget(self._stage1)

        # ── Этап 2: редактор текста ──────────────────────────────
        self._stage2 = QWidget()
        self._stage2.setVisible(False)
        s2 = QVBoxLayout(self._stage2)
        s2.setContentsMargins(0, 0, 0, 0)
        s2.setSpacing(6)

        self._script_name_lbl = QLabel("")
        self._script_name_lbl.setStyleSheet("font-size: 11px; color: #888; font-style: italic;")
        s2.addWidget(self._script_name_lbl)

        edit_lbl = QLabel("Текст (можно отредактировать перед отправкой):")
        edit_lbl.setStyleSheet("font-size: 12px; color: #555; font-weight: bold;")
        s2.addWidget(edit_lbl)

        self._text_edit = QTextEdit()
        self._text_edit.setStyleSheet("QTextEdit { border:1px solid #E0E0E0; border-radius:4px; font-size:12px; background:#fff; padding:4px; }")
        self._text_edit.setMinimumHeight(150)
        s2.addWidget(self._text_edit)
        cl.addWidget(self._stage2)

        # ── Кнопки ───────────────────────────────────────────────
        btn_row = QHBoxLayout()

        self._back_btn = QPushButton("← Назад")
        self._back_btn.setFixedHeight(28)
        self._back_btn.setStyleSheet(
            "QPushButton { border:1px solid #d9d9d9; border-radius:4px; font-size:12px; padding:0 14px; background:#fff; max-height:26px; } QPushButton:hover { background:#f5f5f5; }"
        )
        self._back_btn.setVisible(False)
        self._back_btn.clicked.connect(self._show_stage1)
        btn_row.addWidget(self._back_btn)
        btn_row.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            "QPushButton { border:1px solid #d9d9d9; border-radius:4px; font-size:12px; padding:0 14px; background:#fff; max-height:26px; } QPushButton:hover { background:#f5f5f5; }"
        )
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self._select_btn = QPushButton("Выбрать →")
        self._select_btn.setFixedHeight(28)
        self._select_btn.setStyleSheet(
            "QPushButton { background:#ffd93c; border:none; border-radius:4px; font-size:12px; font-weight:bold; padding:0 14px; max-height:26px; } QPushButton:hover { background:#f5c800; } QPushButton:disabled { background:#f0f0f0; color:#aaa; }"
        )
        self._select_btn.setEnabled(False)
        self._select_btn.clicked.connect(self._on_select)
        btn_row.addWidget(self._select_btn)

        self._send_btn = QPushButton("Отправить")
        self._send_btn.setFixedHeight(28)
        self._send_btn.setStyleSheet(
            "QPushButton { background:#2196F3; color:#fff; border-radius:4px; border:none; padding:0 16px; max-height:26px; font-size:12px; } QPushButton:hover { background:#1565C0; } QPushButton:disabled { background:#ccc; color:#fff; }"
        )
        self._send_btn.setVisible(False)
        self._send_btn.clicked.connect(self._send)
        btn_row.addWidget(self._send_btn)

        cl.addLayout(btn_row)
        fl.addWidget(content)
        outer.addWidget(frame)

    # ── Загрузка данных ─────────────────────────────────────────

    def _load_data(self):
        def _worker():
            scripts = []
            card = {}
            try:
                scripts = self._api.get_messenger_scripts() or []
            except Exception:
                pass
            if self._crm_card_id:
                try:
                    card = self._api.get_crm_card(self._crm_card_id) or {}
                except Exception:
                    pass
            self._sig_data.emit(scripts, card)

        import threading as _t

        _t.Thread(target=_worker, daemon=True).start()

    def _fill_data(self, scripts, card):
        self._card_data = card or {}
        self._loading_lbl.setVisible(False)

        if not scripts:
            self._loading_lbl.setText("Скрипты не найдены")
            self._loading_lbl.setVisible(True)
            return

        self._scripts_list.setVisible(True)
        for s in scripts:
            name = s.get("name") or s.get("script_type") or "Скрипт"
            from PyQt5.QtWidgets import QListWidgetItem

            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, s)
            self._scripts_list.addItem(item)

    # ── Навигация ────────────────────────────────────────────────

    def _on_select(self):
        item = self._scripts_list.currentItem()
        if not item:
            return
        s = item.data(Qt.UserRole)
        name = s.get("name") or s.get("script_type") or "Скрипт"
        template = s.get("message_template") or ""
        filled = self._fill_vars(template)
        self._script_name_lbl.setText(f"Скрипт: {name}")
        self._text_edit.setPlainText(filled)
        self._show_stage2()

    def _show_stage1(self):
        self._stage1.setVisible(True)
        self._stage2.setVisible(False)
        self._back_btn.setVisible(False)
        self._select_btn.setVisible(True)
        self._send_btn.setVisible(False)
        self.adjustSize()

    def _show_stage2(self):
        self._stage1.setVisible(False)
        self._stage2.setVisible(True)
        self._back_btn.setVisible(True)
        self._select_btn.setVisible(False)
        self._send_btn.setVisible(True)
        self.adjustSize()

    # ── Подстановка переменных ───────────────────────────────────

    def _fill_vars(self, template: str) -> str:
        """Заменить {переменные} данными карточки. Строки с пустыми переменными удаляются."""
        import re

        if not template:
            return ""
        d = self._card_data
        client = d.get("client") or {}
        client_name = (client.get("full_name") if isinstance(client, dict) else "") or d.get("client_name", "")
        parts = client_name.split()
        client_first = parts[1] if len(parts) > 1 else (parts[0] if parts else "")

        area = d.get("area")
        vars_map = {
            "client_name": client_name,
            "client_first_name": client_first,
            "address": d.get("address", ""),
            "area": f"{area} м²" if area else "",
            "contract_number": d.get("contract_number", ""),
            "deadline": d.get("deadline", ""),
            "deadline_date": d.get("deadline", ""),
            "senior_manager": d.get("senior_manager_name", ""),
            "senior_manager_username": d.get("senior_manager_name", ""),
            "manager_name": d.get("manager_name", ""),
            "manager_username": d.get("manager_name", ""),
            "sdp": d.get("sdp_name", ""),
            "sdp_username": d.get("sdp_name", ""),
            "gap": d.get("gap_name", ""),
            "surveyor": d.get("surveyor_name", ""),
            "sender_name": self._employee.get("full_name", ""),
            "role_name": self._employee.get("position", ""),
        }

        result = []
        for line in template.split("\n"):
            keys = re.findall(r"\{(\w+)\}", line)
            if not keys:
                result.append(line)
                continue
            has_empty = [False]

            def _rep(m, _map=vars_map, _flag=has_empty):
                key = m.group(1)
                val = _map.get(key, m.group(0))
                if key in _map and not val:
                    _flag[0] = True
                return val

            substituted = re.sub(r"\{(\w+)\}", _rep, line)
            if not has_empty[0]:
                result.append(substituted)

        return "\n".join(result).strip()

    # ── Отправка ─────────────────────────────────────────────────

    def _send(self):
        text = self._text_edit.toPlainText().strip()
        if not text:
            return
        try:
            self._api.send_chat_message(chat_id=self._chat_id, content=text)
            self.accept()
        except Exception as e:
            print(f"[ScriptSendDialog] Ошибка отправки: {e}")


class InviteLinkDialog(QDialog):
    """Показывает ссылку-приглашение для клиента."""

    def __init__(self, link: str, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(480)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("borderFrame")
        frame.setStyleSheet("QFrame#borderFrame { background:#fff; border:1px solid #E0E0E0; border-radius:10px; }")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        title_bar = CustomTitleBar(self, "Ссылка для клиента", simple_mode=True)
        title_bar.setStyleSheet("CustomTitleBar { background:#fff; border-bottom:1px solid #E0E0E0; border-top-left-radius:10px; border-top-right-radius:10px; }")
        fl.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet("background:#F9FAFB; border-bottom-left-radius:10px; border-bottom-right-radius:10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 14, 16, 16)
        cl.setSpacing(8)

        lbl = QLabel("Отправьте клиенту эту ссылку для входа в чат:")
        lbl.setStyleSheet("font-size: 12px; color: #555;")
        cl.addWidget(lbl)

        link_edit = QLineEdit(link)
        link_edit.setReadOnly(True)
        link_edit.setFixedHeight(28)
        link_edit.setStyleSheet("QLineEdit { font-size:12px; padding:0 8px; border:1px solid #E0E0E0; border-radius:4px; background:#fff; }")
        cl.addWidget(link_edit)

        btns = QHBoxLayout()
        btns.addStretch()

        copy_btn = QPushButton("Копировать")
        copy_btn.setFixedHeight(28)
        copy_btn.setStyleSheet(
            "QPushButton { border:1px solid #d9d9d9; border-radius:4px; font-size:12px; padding:0 14px; background:#fff; max-height:26px; } QPushButton:hover { background:#f5f5f5; }"
        )
        copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(link))
        btns.addWidget(copy_btn)

        close_btn = QPushButton("Закрыть")
        close_btn.setFixedHeight(28)
        close_btn.setStyleSheet(
            "QPushButton { background:#ffd93c; border:none; border-radius:4px; font-size:12px; font-weight:bold; padding:0 14px; max-height:26px; } QPushButton:hover { background:#f5c800; }"
        )
        close_btn.clicked.connect(self.accept)
        btns.addWidget(close_btn)
        cl.addLayout(btns)

        fl.addWidget(content)
        outer.addWidget(frame)
