"""
ChatRoomWidget — основной виджет чат-комнаты.

Используется в:
  - EmployeeChatsTab (правая панель)
  - ClientChatsTab  (правая панель)
  - CrmCardEditDialog (вкладка "Чат сотрудников" / "Чат с клиентом")

Поведение:
  - Загружает историю (REST) при открытии
  - Поддерживает отправку текста, файлов, голосовых
  - Подключается к WebSocket для real-time сообщений
  - PyQt Signal Safety: все UI-обновления из фоновых потоков — через pyqtSignal,
    НЕ через QTimer.singleShot (он не срабатывает из threading.Thread в PyQt5 5.15)
"""

import json
import logging
import os
import threading
import time
from typing import Optional
import uuid

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.chat_gallery_widget import ChatGalleryWidget
from ui.chat_message_bubble import ChatMessageBubble
from utils.icon_loader import IconLoader

logger = logging.getLogger(__name__)


class ChatInputEdit(QTextEdit):
    """QTextEdit с перехватом Enter: Enter — отправить, Shift+Enter — перенос строки."""

    send_requested = pyqtSignal()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
                event.accept()
        else:
            super().keyPressEvent(event)


try:
    import websocket as _ws_lib

    _WS_AVAILABLE = True
except ImportError:
    _WS_AVAILABLE = False
    logger.warning("websocket-client не установлен — real-time отключён. pip install websocket-client")


class ChatWebSocketWorker(threading.Thread):
    """Фоновый поток WebSocket."""

    def __init__(self, url: str, on_message, on_error, on_close, on_open):
        super().__init__(daemon=True)
        self._url = url
        self._on_message = on_message
        self._on_error = on_error
        self._on_close = on_close
        self._on_open = on_open
        self._ws = None
        self._running = True

    def run(self):
        if not _WS_AVAILABLE:
            return
        while self._running:
            try:
                self._ws = _ws_lib.WebSocketApp(
                    self._url,
                    on_message=lambda ws, msg: self._on_message(msg),
                    on_error=lambda ws, err: self._on_error(err),
                    on_close=lambda ws, *a: self._on_close(),
                    on_open=lambda ws: self._on_open(),
                )
                self._ws.run_forever(ping_interval=30)
            except Exception as e:
                logger.warning(f"WS error: {e}")
            if self._running:
                time.sleep(5)

    def send(self, data: dict):
        if self._ws:
            try:
                self._ws.send(json.dumps(data))
            except Exception as e:
                logger.warning(f"WS send error: {e}")

    def stop(self):
        self._running = False
        if self._ws:
            try:
                self._ws.close()
            except Exception:
                pass


class ChatRoomWidget(QWidget):
    """
    Виджет чат-комнаты.

    Параметры
    ---------
    chat_id    : int  — ID чата в internal_chats
    chat_type  : str  — 'employee' / 'client'
    employee   : dict — текущий пользователь {'id': ..., 'full_name': ...}
    api_client : APIClient
    """

    # Публичный сигнал: новое непрочитанное сообщение
    unread_changed = pyqtSignal(int, int)  # (chat_id, unread_count)

    # Приватные сигналы для thread-safe передачи данных из фоновых потоков.
    # QTimer.singleShot НЕ работает из threading.Thread в PyQt5 5.15 —
    # только pyqtSignal гарантированно доставляется в GUI-поток.
    _sig_messages_ready = pyqtSignal(object, object)  # (chat_dict|None, msgs_list)
    _sig_new_msg = pyqtSignal(object)  # msg dict
    _sig_ws_data = pyqtSignal(object)  # ws event dict
    _sig_ws_status = pyqtSignal(bool)  # True=connected, False=disconnected

    def __init__(self, chat_id: int, chat_type: str, employee: dict, api_client, parent=None):
        super().__init__(parent)
        self._chat_id = chat_id
        self._chat_type = chat_type
        self._employee = employee
        self._api = api_client
        self._ws_worker: Optional[ChatWebSocketWorker] = None
        self._messages = []
        self._crm_card_id: Optional[int] = None
        self._typing_timer = None
        self._is_typing = False

        # Режим ответа / редактирования
        self._reply_to_msg: Optional[dict] = None
        self._edit_msg_id: Optional[int] = None
        self._first_unread_id: Optional[int] = None

        # Закреплённые сообщения
        self._pinned_messages: list = []
        self._pinned_index: int = 0

        # Файлы, ожидающие отправки
        self._pending_files: list = []

        # Строка с количеством участников для subtitle
        self._members_count_str: str = ""

        # Подключаем сигналы ДО setup_ui, чтобы они были готовы когда придут данные
        self._sig_messages_ready.connect(self._on_messages_loaded)
        self._sig_new_msg.connect(self._append_message)
        self._sig_ws_data.connect(self._handle_ws_event)
        self._sig_ws_status.connect(self._on_ws_status)

        self._setup_ui()
        self._load_messages()
        self._connect_websocket()

    # ===========================================================
    # UI
    # ===========================================================

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ---------- HEADER ----------
        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(12, 0, 12, 0)
        h_layout.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setSpacing(0)
        title_col.setContentsMargins(0, 0, 0, 0)

        self._title_lbl = QLabel("Чат")
        self._title_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        self._title_lbl.setMinimumWidth(0)
        self._title_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        title_col.addWidget(self._title_lbl)

        self._member_count_lbl = QLabel("")
        self._member_count_lbl.setStyleSheet("font-size: 10px; color: #888;")
        self._member_count_lbl.setVisible(False)
        title_col.addWidget(self._member_count_lbl)

        h_layout.addLayout(title_col)
        h_layout.setStretch(0, 1)

        members_btn = QPushButton("Участники")
        members_btn.setFixedHeight(28)
        members_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 0 14px;
                font-size: 12px;
                background: #fff;
            }
            QPushButton:hover { background: #f5f5f5; }
        """)
        members_btn.clicked.connect(self._show_members_dialog)
        h_layout.addWidget(members_btn)

        main_layout.addWidget(header)

        # ---------- PINNED MESSAGE BAR ----------
        self._pinned_bar = QFrame()
        self._pinned_bar.setStyleSheet("""
            QFrame {
                background: #fff;
                border-bottom: 1px solid #E0E0E0;
            }
        """)
        self._pinned_bar.setFixedHeight(44)
        pb_layout = QHBoxLayout(self._pinned_bar)
        pb_layout.setContentsMargins(10, 4, 6, 4)
        pb_layout.setSpacing(6)

        self._pin_icon_lbl = QLabel("|")
        self._pin_icon_lbl.setFixedWidth(12)
        self._pin_icon_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #E65100;")
        pb_layout.addWidget(self._pin_icon_lbl)

        pin_text_col = QVBoxLayout()
        pin_text_col.setSpacing(0)
        pin_text_col.setContentsMargins(0, 0, 0, 0)

        self._pin_title_lbl = QLabel("Закреплено")
        self._pin_title_lbl.setStyleSheet("font-size: 10px; font-weight: bold; color: #E65100;")
        pin_text_col.addWidget(self._pin_title_lbl)

        self._pin_text_lbl = QLabel("")
        self._pin_text_lbl.setStyleSheet("font-size: 11px; color: #333;")
        self._pin_text_lbl.setMinimumWidth(0)
        self._pin_text_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self._pin_text_lbl.setCursor(Qt.PointingHandCursor)
        pin_text_col.addWidget(self._pin_text_lbl)

        pin_text_widget = QWidget()
        pin_text_widget.setLayout(pin_text_col)
        pin_text_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        pb_layout.addWidget(pin_text_widget)

        self._pin_nav_lbl = QLabel("")
        self._pin_nav_lbl.setStyleSheet("color: #E65100; font-size: 10px; font-weight: bold;")
        pb_layout.addWidget(self._pin_nav_lbl)

        unpin_btn = QPushButton("×")
        unpin_btn.setFixedSize(20, 20)
        unpin_btn.setStyleSheet("""
            QPushButton {
                border: none; background: transparent;
                font-size: 12px; line-height: 1; color: #aaa;
            }
            QPushButton:hover { color: #555; }
        """)
        unpin_btn.setToolTip("Открепить сообщение")
        unpin_btn.clicked.connect(self._unpin_current)
        pb_layout.addWidget(unpin_btn)

        self._pinned_bar.setVisible(False)
        self._pinned_bar.mousePressEvent = lambda e: self._scroll_to_pinned()
        self._pinned_messages = []
        self._pinned_index = 0
        main_layout.addWidget(self._pinned_bar)

        # ---------- TYPING INDICATOR ----------
        self._typing_lbl = QLabel("")
        self._typing_lbl.setStyleSheet("font-size: 10px; color: #888; padding-left: 12px;")
        self._typing_lbl.setVisible(False)
        main_layout.addWidget(self._typing_lbl)

        # ---------- MESSAGES AREA ----------
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #F5F5F5; }")
        self._scroll.viewport().setStyleSheet("background: #F5F5F5;")

        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet("background: #F5F5F5;")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(4)
        self._messages_layout.addStretch()  # index 0 — прижимает сообщения к низу

        self._scroll.setWidget(self._messages_widget)
        main_layout.addWidget(self._scroll, stretch=1)

        # ---------- ACTION BAR (ответ / редактирование) ----------
        self._action_bar = QFrame()
        self._action_bar.setStyleSheet("""
            QFrame {
                background: #F3F6FF;
                border-top: 1px solid #D0D9F0;
            }
        """)
        self._action_bar.setFixedHeight(36)
        ab_layout = QHBoxLayout(self._action_bar)
        ab_layout.setContentsMargins(12, 0, 8, 0)
        ab_layout.setSpacing(8)

        self._action_icon_lbl = QLabel("↩")
        self._action_icon_lbl.setStyleSheet("font-size: 16px; color: #1565C0;")
        ab_layout.addWidget(self._action_icon_lbl)

        self._action_text_lbl = QLabel("")
        self._action_text_lbl.setStyleSheet("font-size: 11px; color: #1565C0;")
        self._action_text_lbl.setMinimumWidth(0)
        self._action_text_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        ab_layout.addWidget(self._action_text_lbl)

        cancel_btn = QPushButton("×")
        cancel_btn.setFixedSize(24, 24)
        cancel_btn.setStyleSheet("""
            QPushButton {
                border: none; background: transparent;
                font-size: 12px; line-height: 1; color: #888;
            }
            QPushButton:hover { color: #333; }
        """)
        cancel_btn.clicked.connect(self._cancel_action)
        ab_layout.addWidget(cancel_btn)

        self._action_bar.setVisible(False)
        main_layout.addWidget(self._action_bar)

        # ---------- UPLOAD PROGRESS ----------
        self._upload_progress = QProgressBar()
        self._upload_progress.setFixedHeight(4)
        self._upload_progress.setRange(0, 0)  # indeterminate
        self._upload_progress.setStyleSheet("""
            QProgressBar {
                border: none;
                background: #f0f0f0;
            }
            QProgressBar::chunk {
                background: #ffd93c;
            }
        """)
        self._upload_progress.setVisible(False)
        main_layout.addWidget(self._upload_progress)

        # ---------- PENDING FILES PREVIEW ----------
        self._pending_panel = QFrame()
        self._pending_panel.setStyleSheet("""
            QFrame {
                background: #E3F2FD;
                border-top: 1px solid #BBDEFB;
            }
        """)
        self._pending_panel.setFixedHeight(104)
        pp_vbox = QVBoxLayout(self._pending_panel)
        pp_vbox.setContentsMargins(8, 4, 8, 6)
        pp_vbox.setSpacing(4)

        self._caption_input = QLineEdit()
        self._caption_input.setPlaceholderText("Подпись к файлу…")
        self._caption_input.setFixedHeight(24)
        self._caption_input.setStyleSheet("""
            QLineEdit {
                border: 1px solid #BBDEFB;
                border-radius: 12px;
                padding: 0 10px;
                font-size: 11px;
                background: #fff;
            }
        """)
        pp_vbox.addWidget(self._caption_input)

        pp_thumb_widget = QWidget()
        pp_thumb_widget.setStyleSheet("background: transparent;")
        pp_layout = QHBoxLayout(pp_thumb_widget)
        pp_layout.setContentsMargins(0, 0, 0, 0)
        pp_layout.setSpacing(6)
        pp_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        pp_vbox.addWidget(pp_thumb_widget)
        self._pending_thumbnails_layout = pp_layout
        self._pending_panel.setVisible(False)
        main_layout.addWidget(self._pending_panel)

        self._build_input_panel(main_layout)

    def _build_input_panel(self, main_layout):
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border-top: 1px solid #E0E0E0;
            }
        """)
        input_frame.setFixedHeight(56)
        i_layout = QVBoxLayout(input_frame)
        i_layout.setContentsMargins(8, 8, 8, 8)
        i_layout.setSpacing(0)

        row = QHBoxLayout()
        row.setSpacing(6)
        row.setAlignment(Qt.AlignVCenter)

        attach_btn = IconLoader.create_action_button("upload", tooltip="Прикрепить файл", button_size=36, icon_size=18, icon_color="#666")
        attach_btn.setStyleSheet(attach_btn.styleSheet() + "QPushButton { border-radius: 18px; }")
        attach_btn.clicked.connect(self._attach_file)
        row.addWidget(attach_btn)

        voice_btn = IconLoader.create_action_button("message-circle", tooltip="Голосовое (только мобиль)", button_size=36, icon_size=18, icon_color="#888")
        voice_btn.setCheckable(True)
        voice_btn.setStyleSheet(voice_btn.styleSheet() + "QPushButton { border-radius: 18px; } QPushButton:checked { background: #ffd93c; border-color: #e6c535; }")
        voice_btn.clicked.connect(self._toggle_voice)
        self._voice_btn = voice_btn
        row.addWidget(voice_btn)

        self._input = ChatInputEdit()
        self._input.setFixedHeight(36)
        self._input.setPlaceholderText("Сообщение… (Enter — отправить, Shift+Enter — перенос)")
        self._input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 18px;
                padding: 6px 12px;
                font-size: 13px;
                background: #fff;
            }
        """)
        self._input.textChanged.connect(self._on_input_changed)
        self._input.send_requested.connect(self._send_text)
        row.addWidget(self._input, stretch=1)

        self._send_btn = IconLoader.create_action_button(
            "arrow-right-circle",
            tooltip="Отправить",
            button_size=36,
            icon_size=20,
            bg_color="#ffd93c",
            hover_color="#f5c800",
            icon_color="#555",
        )
        self._send_btn.setStyleSheet(self._send_btn.styleSheet() + "QPushButton { border-radius: 18px; border: none; } QPushButton:pressed { background: #e6b800; }")
        self._send_btn.clicked.connect(self._send_text)
        row.addWidget(self._send_btn)

        i_layout.addLayout(row)
        main_layout.addWidget(input_frame)

    # ===========================================================
    # Загрузка данных
    # ===========================================================

    def _load_messages(self):
        """Загрузить историю через REST. Результат передаётся через сигнал."""

        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            msgs = self._api.get_chat_messages(self._chat_id, limit=50)
            self._sig_messages_ready.emit(chat, msgs or [])

        threading.Thread(target=_worker, daemon=True).start()

    def _on_messages_loaded(self, chat, msgs):
        if chat:
            self._title_lbl.setText(chat.get("title") or "Чат")
            self._crm_card_id = chat.get("crm_card_id")
            self._first_unread_id = chat.get("first_unread_message_id")
            member_count = chat.get("member_count")
            self._members_count_str = f"{member_count} уч." if member_count else ""
            self._pinned_messages = chat.get("pinned_messages") or []
            self._update_pinned_bar()
        self._on_ws_status(bool(self._ws_worker and self._ws_worker._running))
        self._messages = list(msgs) if msgs else []
        self._render_all_messages()
        if self._messages:
            last_id = self._messages[-1].get("id")
            if last_id:
                threading.Thread(
                    target=lambda: self._api.mark_chat_read(self._chat_id, last_id),
                    daemon=True,
                ).start()

    def _make_bubble(self, msg: dict) -> ChatMessageBubble:
        my_id = self._employee.get("id")
        is_own = msg.get("sender_employee_id") == my_id
        token = getattr(self._api, "token", "") or ""
        base_url = getattr(self._api, "base_url", "") or ""
        bubble = ChatMessageBubble(msg, is_own, token=token, base_url=base_url)
        bubble.edit_requested.connect(self._on_edit_requested)
        bubble.delete_requested.connect(self._on_delete_requested)
        bubble.reply_requested.connect(self._on_reply_requested)
        bubble.pin_requested.connect(self._on_pin_requested)
        bubble.scroll_to_requested.connect(self._scroll_to_message)
        bubble.forward_requested.connect(self._on_forward_requested)
        return bubble

    def _render_all_messages(self):
        layout = self._messages_layout
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        unread_divider_shown = False
        i = 0
        while i < len(self._messages):
            msg = self._messages[i]

            if self._first_unread_id and msg.get("id") == self._first_unread_id and not unread_divider_shown:
                divider = self._make_unread_divider()
                layout.addWidget(divider)
                unread_divider_shown = True

            gid = msg.get("group_id")
            if gid and msg.get("message_type") == "image" and not msg.get("is_deleted"):
                group = [msg]
                j = i + 1
                while j < len(self._messages) and self._messages[j].get("group_id") == gid and not self._messages[j].get("is_deleted"):
                    group.append(self._messages[j])
                    j += 1
                if len(group) > 1:
                    layout.addWidget(self._make_gallery(group))
                    i = j
                    continue

            layout.addWidget(self._make_bubble(msg))
            i += 1

        self._messages_widget.update()

        if self._first_unread_id and unread_divider_shown:
            QTimer.singleShot(80, self._scroll_to_first_unread)
        else:
            self._scroll_to_bottom()

    def _make_gallery(self, msgs: list) -> ChatGalleryWidget:
        my_id = self._employee.get("id")
        is_own = msgs[0].get("sender_employee_id") == my_id
        token = getattr(self._api, "token", "") or ""
        base_url = getattr(self._api, "base_url", "") or ""
        gallery = ChatGalleryWidget(msgs, is_own, token=token, base_url=base_url, parent=self)
        gallery.edit_requested.connect(self._on_edit_requested)
        gallery.delete_requested.connect(self._on_delete_requested)
        gallery.reply_requested.connect(self._on_reply_requested)
        gallery.pin_requested.connect(self._on_pin_requested)
        gallery.scroll_to_requested.connect(self._scroll_to_message)
        return gallery

    def _make_unread_divider(self) -> QWidget:
        w = QWidget()
        w.setObjectName("unreadDivider")
        row = QHBoxLayout(w)
        row.setContentsMargins(8, 4, 8, 4)
        row.setSpacing(8)

        line_l = QFrame()
        line_l.setFrameShape(QFrame.HLine)
        line_l.setStyleSheet("color: #E53935;")
        row.addWidget(line_l, stretch=1)

        lbl = QLabel("Новые сообщения")
        lbl.setStyleSheet("font-size: 10px; color: #E53935; white-space: nowrap;")
        row.addWidget(lbl)

        line_r = QFrame()
        line_r.setFrameShape(QFrame.HLine)
        line_r.setStyleSheet("color: #E53935;")
        row.addWidget(line_r, stretch=1)

        return w

    def _scroll_to_first_unread(self):
        layout = self._messages_layout
        for i in range(1, layout.count()):
            item = layout.itemAt(i)
            w = item.widget() if item else None
            if w and w.objectName() == "unreadDivider":
                pos_y = w.mapTo(self._messages_widget, w.rect().topLeft()).y()
                self._scroll.verticalScrollBar().setValue(max(0, pos_y - 20))
                return
        self._scroll_to_bottom()

    def _scroll_to_message(self, msg_id: int):
        if not msg_id:
            return
        layout = self._messages_layout
        for i in range(1, layout.count()):
            item = layout.itemAt(i)
            w = item.widget() if item else None
            if w and hasattr(w, "_msg") and w._msg.get("id") == msg_id:
                pos_y = w.mapTo(self._messages_widget, w.rect().topLeft()).y()
                self._scroll.verticalScrollBar().setValue(max(0, pos_y - 20))
                QTimer.singleShot(100, lambda w=w: self._highlight_widget(w))
                return

    def _highlight_widget(self, w: QWidget):
        """Кратковременная жёлтая подсветка виджета после перехода к цитате."""
        if not w or not w.isVisible():
            return
        from PyQt5.QtGui import QColor

        w.setAutoFillBackground(True)
        pal = w.palette()
        pal.setColor(w.backgroundRole(), QColor(255, 245, 157, 160))
        w.setPalette(pal)
        QTimer.singleShot(1500, lambda: self._unhighlight_widget(w))

    def _unhighlight_widget(self, w: QWidget):
        if w and w.isVisible():
            w.setAutoFillBackground(False)
            w.setPalette(w.style().standardPalette())

    def _append_message(self, msg):
        """Добавить одно сообщение. Вызывается из GUI-потока через сигнал."""
        if not isinstance(msg, dict):
            return
        msg_id = msg.get("id")
        if msg_id and any(m.get("id") == msg_id for m in self._messages):
            return
        # Изображения с group_id группируются в галерею — перерисовываем всё
        if msg.get("group_id") and msg.get("message_type") == "image" and not msg.get("is_deleted"):
            self._messages.append(msg)
            self._render_all_messages()
            return
        bubble = self._make_bubble(msg)
        self._messages_layout.addWidget(bubble)
        self._messages.append(msg)
        self._messages_widget.update()
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        # Вызывается из GUI-потока — QTimer здесь работает корректно
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum()))

    # ===========================================================
    # Действия над сообщениями
    # ===========================================================

    def _on_reply_requested(self, msg: dict):
        self._reply_to_msg = msg
        self._edit_msg_id = None
        sender = msg.get("sender_display_name") or "Сообщение"
        content = msg.get("content") or ""
        preview = (content[:50] + "…") if len(content) > 50 else content
        self._action_icon_lbl.setText("↩")
        self._action_text_lbl.setText(f"Ответить {sender}: {preview}")
        self._action_bar.setVisible(True)
        self._input.setFocus()

    def _on_edit_requested(self, msg: dict):
        self._edit_msg_id = msg.get("id")
        self._reply_to_msg = None
        content = msg.get("content") or ""
        self._action_icon_lbl.setText("✎")
        self._action_text_lbl.setText(f"Редактировать: {(content[:60] + '…') if len(content) > 60 else content}")
        self._action_bar.setVisible(True)
        self._input.setPlainText(content)
        self._input.setFocus()
        # Курсор в конец
        cursor = self._input.textCursor()
        cursor.movePosition(cursor.End)
        self._input.setTextCursor(cursor)

    def _on_delete_requested(self, msg: dict):
        msg_id = msg.get("id")
        if not msg_id:
            return
        if (
            QMessageBox.question(
                self,
                "Удалить сообщение",
                "Удалить это сообщение?",
                QMessageBox.Yes | QMessageBox.No,
            )
            != QMessageBox.Yes
        ):
            return

        def _worker():
            ok = self._api.delete_chat_message(self._chat_id, msg_id)
            if ok:
                for i, m in enumerate(self._messages):
                    if m.get("id") == msg_id:
                        self._messages[i] = dict(m, is_deleted=True, content="Сообщение удалено")
                        break
                # Перерисовываем через сигнал (уже в рабочем потоке)
                self._sig_ws_data.emit({"type": "_rerender"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_pin_requested(self, msg: dict):
        msg_id = msg.get("id")
        if not msg_id:
            return

        def _worker():
            self._api.pin_chat_message(self._chat_id, msg_id)
            chat = self._api.get_internal_chat(self._chat_id)
            if chat:
                self._pinned_messages = chat.get("pinned_messages") or []
                self._pinned_index = 0
                # Обновить is_pinned в self._messages
                pinned_ids = {m.get("id") for m in self._pinned_messages}
                for i, m in enumerate(self._messages):
                    if m.get("id") == msg_id:
                        self._messages[i] = dict(m, is_pinned=(msg_id in pinned_ids))
                        break
                self._sig_ws_data.emit({"type": "_update_pinned"})

        threading.Thread(target=_worker, daemon=True).start()

    def _cancel_action(self):
        self._reply_to_msg = None
        self._edit_msg_id = None
        self._action_bar.setVisible(False)
        self._input.clear()

    # ===========================================================
    # WebSocket
    # ===========================================================

    def _connect_websocket(self):
        if not _WS_AVAILABLE:
            self._poll_timer = QTimer(self)
            self._poll_timer.timeout.connect(self._poll_new_messages)
            self._poll_timer.start(10000)
            return

        ws_url = self._api.get_chat_ws_url(self._chat_id)

        def on_message(raw: str):
            try:
                data = json.loads(raw)
            except Exception:
                return
            self._sig_ws_data.emit(data)

        def on_error(err):
            logger.warning(f"Chat WS error: {err}")

        def on_close():
            logger.debug(f"Chat WS closed: chat_id={self._chat_id}")
            self._sig_ws_status.emit(False)

        def on_open():
            logger.debug(f"Chat WS opened: chat_id={self._chat_id}")
            self._sig_ws_status.emit(True)

        self._ws_worker = ChatWebSocketWorker(ws_url, on_message, on_error, on_close, on_open)
        self._ws_worker.start()

    def _on_ws_status(self, connected: bool):
        if connected:
            suffix = (f" • {self._members_count_str}") if self._members_count_str else ""
            self._member_count_lbl.setText(f"● онлайн{suffix}")
            self._member_count_lbl.setStyleSheet("font-size: 10px; color: #4caf50;")
        else:
            self._member_count_lbl.setText("○ оффлайн")
            self._member_count_lbl.setStyleSheet("font-size: 10px; color: #999;")
        self._member_count_lbl.setVisible(True)

    def _handle_ws_event(self, data):
        if not isinstance(data, dict):
            return
        event = data.get("type")

        if event == "_hide_progress":
            self._upload_progress.setVisible(False)

        elif event == "_forward_pick":
            self._show_forward_dialog(data.get("msg_id"), data.get("chats", []))

        elif event == "_update_pinned":
            self._update_pinned_bar()

        elif event == "message_pinned":
            # WS-событие: msg_id закреплён/откреплён — перезагрузить из API
            def _reload_pinned():
                chat = self._api.get_internal_chat(self._chat_id)
                if chat:
                    self._pinned_messages = chat.get("pinned_messages") or []
                    self._pinned_index = 0
                    self._sig_ws_data.emit({"type": "_update_pinned"})

            threading.Thread(target=_reload_pinned, daemon=True).start()

        elif event == "_rerender":
            self._render_all_messages()

        elif event == "new_message":
            msg = data.get("message", {})
            self._append_message(msg)
            msg_id = msg.get("id") if isinstance(msg, dict) else None
            if msg_id and self.isVisible():
                threading.Thread(
                    target=lambda: self._api.mark_chat_read(self._chat_id, msg_id),
                    daemon=True,
                ).start()
                self.unread_changed.emit(self._chat_id, 0)

        elif event == "typing":
            if data.get("is_typing"):
                self._typing_lbl.setText(f"{data.get('name', '')} печатает…")
                self._typing_lbl.setVisible(True)
            else:
                self._typing_lbl.setText("")
                self._typing_lbl.setVisible(False)

        elif event == "message_deleted":
            msg_id = data.get("message_id")
            for i, m in enumerate(self._messages):
                if m.get("id") == msg_id:
                    self._messages[i] = dict(m, is_deleted=True, content="Сообщение удалено")
            self._render_all_messages()

        elif event == "message_edited":
            msg_id = data.get("message_id")
            new_content = data.get("content", "")
            for i, m in enumerate(self._messages):
                if m.get("id") == msg_id:
                    self._messages[i] = dict(m, content=new_content, is_edited=True)
            self._render_all_messages()

    def _poll_new_messages(self):
        """Fallback polling при отсутствии websocket-client."""

        def _worker():
            msgs = self._api.get_chat_messages(self._chat_id, limit=50)
            if msgs and len(msgs) > len(self._messages):
                for m in msgs[len(self._messages) :]:
                    self._sig_new_msg.emit(m)

        threading.Thread(target=_worker, daemon=True).start()

    # ===========================================================
    # Отправка
    # ===========================================================

    def _on_input_changed(self):
        text = self._input.toPlainText()
        if text and not self._is_typing:
            self._is_typing = True
            if self._ws_worker:
                self._ws_worker.send({"type": "typing_start"})
        if self._typing_timer:
            self._typing_timer.stop()
            self._typing_timer.deleteLater()
        self._typing_timer = QTimer(self)
        self._typing_timer.setSingleShot(True)
        self._typing_timer.timeout.connect(self._stop_typing)
        self._typing_timer.start(2000)

    def _stop_typing(self):
        if self._is_typing:
            self._is_typing = False
            if self._ws_worker:
                self._ws_worker.send({"type": "typing_stop"})

    def _send_text(self):
        if self._pending_files:
            self._send_pending_files()
            self._input.clear()
            self._stop_typing()
            return

        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self._stop_typing()

        # Режим редактирования
        if self._edit_msg_id is not None:
            msg_id = self._edit_msg_id
            self._cancel_action()

            def _edit_worker():
                result = self._api.edit_chat_message(self._chat_id, msg_id, text)
                if result:
                    for i, m in enumerate(self._messages):
                        if m.get("id") == msg_id:
                            self._messages[i] = dict(m, content=text, is_edited=True)
                            break
                    self._sig_ws_data.emit({"type": "_rerender"})

            threading.Thread(target=_edit_worker, daemon=True).start()
            return

        # Режим ответа
        reply_to_id = None
        if self._reply_to_msg is not None:
            reply_to_id = self._reply_to_msg.get("id")
            self._cancel_action()

        def _worker():
            msg = self._api.send_chat_message(self._chat_id, text, reply_to_id=reply_to_id)
            if msg:
                self._sig_new_msg.emit(msg)

        threading.Thread(target=_worker, daemon=True).start()

    def _attach_file(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы",
            "",
            "Все файлы (*);;Изображения (*.jpg *.jpeg *.png *.gif *.webp);;PDF (*.pdf)",
        )
        if not paths:
            return
        for path in paths:
            fname = os.path.basename(path)
            ext = os.path.splitext(fname)[1].lower()
            msg_type = "image" if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else "file"
            self._pending_files.append({"path": path, "name": fname, "type": msg_type})
        self._refresh_pending_panel()

    def _refresh_pending_panel(self):
        from PyQt5.QtGui import QPixmap as _QPixmap

        while self._pending_thumbnails_layout.count():
            item = self._pending_thumbnails_layout.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
            del item

        if not self._pending_files:
            self._pending_panel.setVisible(False)
            return

        for idx, f in enumerate(self._pending_files):
            cell = QWidget()
            cell.setFixedSize(72, 58)
            cl = QHBoxLayout(cell)
            cl.setContentsMargins(0, 0, 0, 0)
            cl.setSpacing(3)

            thumb = QLabel()
            thumb.setFixedSize(52, 52)
            thumb.setAlignment(Qt.AlignCenter)
            if f["type"] == "image":
                pix = _QPixmap(f["path"])
                if not pix.isNull():
                    thumb.setPixmap(pix.scaled(52, 52, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                    thumb.setStyleSheet("border-radius: 4px;")
                else:
                    thumb.setStyleSheet("background: #cce5ff; border-radius: 4px;")
            else:
                nm = f["name"]
                thumb.setText((nm[:7] + "…") if len(nm) > 7 else nm)
                thumb.setStyleSheet("background: #e0e0e0; border-radius: 4px; font-size: 9px; color: #555;")
                thumb.setWordWrap(True)
            cl.addWidget(thumb)

            rm_btn = QPushButton("×")
            rm_btn.setFixedSize(20, 20)
            rm_btn.setStyleSheet("""
                QPushButton {
                    background: #E53935; color: #fff;
                    border: none; border-radius: 10px;
                    font-size: 10px; padding: 0;
                }
                QPushButton:hover { background: #c62828; }
            """)
            rm_btn.clicked.connect(lambda checked, i=idx: self._remove_pending_file(i))
            cl.addWidget(rm_btn)

            self._pending_thumbnails_layout.addWidget(cell)

        self._pending_thumbnails_layout.addStretch()
        self._pending_panel.setVisible(True)

    def _remove_pending_file(self, index: int):
        if 0 <= index < len(self._pending_files):
            self._pending_files.pop(index)
        self._refresh_pending_panel()

    def _send_pending_files(self):
        if not self._pending_files:
            return
        files = list(self._pending_files)
        caption = self._caption_input.text().strip()
        self._caption_input.clear()
        self._pending_files.clear()
        self._refresh_pending_panel()
        self._upload_progress.setVisible(True)

        # Все изображения группируются одним group_id для галереи
        images = [f for f in files if f["type"] == "image"]
        group_id = str(uuid.uuid4()) if len(images) > 1 else None

        def _worker():
            try:
                for f in files:
                    with open(f["path"], "rb") as fh:
                        data = fh.read()
                    gid = group_id if f["type"] == "image" and group_id else None
                    result = self._api.upload_chat_file(
                        self._chat_id,
                        data,
                        f["name"],
                        message_type=f["type"],
                        group_id=gid,
                    )
                    if result:
                        self._sig_new_msg.emit(result)
                if caption:
                    msg = self._api.send_chat_message(self._chat_id, caption)
                    if msg:
                        self._sig_new_msg.emit(msg)
            finally:
                self._sig_ws_data.emit({"type": "_hide_progress"})

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_voice(self):
        self._voice_btn.setChecked(False)
        QMessageBox.information(
            self,
            "Голосовое",
            "Запись голосовых доступна в мобильной версии.\nНа десктопе используйте прикрепление файла (.webm, .mp3).",
        )

    # ===========================================================
    # Диалог участников
    # ===========================================================

    def _show_members_dialog(self):
        from ui.chat_members_dialog import ChatMembersDialog

        dlg = ChatMembersDialog(
            self._chat_id,
            self._chat_type,
            self._employee,
            self._api,
            self,
            crm_card_id=self._crm_card_id,
        )
        dlg.exec_()

    # ===========================================================
    # Закреплённые сообщения
    # ===========================================================

    def _update_pinned_bar(self):
        if not self._pinned_messages:
            self._pinned_bar.setVisible(False)
            return
        total = len(self._pinned_messages)
        idx = max(0, min(self._pinned_index, total - 1))
        msg = self._pinned_messages[idx]
        content = msg.get("content") or ""
        if msg.get("message_type") in ("image", "file", "voice"):
            content = f"[{msg.get('message_type', 'файл')}]"
        preview = (content[:55] + "…") if len(content) > 55 else content
        self._pin_text_lbl.setText(preview)
        if total > 1:
            self._pin_nav_lbl.setText(f"{idx + 1}/{total}")
            self._pin_nav_lbl.setVisible(True)
        else:
            self._pin_nav_lbl.setVisible(False)
        self._pinned_bar.setVisible(True)

    def _scroll_to_pinned(self):
        if not self._pinned_messages:
            return
        total = len(self._pinned_messages)
        self._pinned_index = (self._pinned_index + 1) % total
        self._update_pinned_bar()
        # Прокрутка к сообщению
        idx = self._pinned_index
        msg_id = self._pinned_messages[idx].get("id")
        if not msg_id:
            return
        layout = self._messages_layout
        for i in range(1, layout.count()):
            item = layout.itemAt(i)
            w = item.widget() if item else None
            if w and hasattr(w, "_msg") and w._msg.get("id") == msg_id:
                pos_y = w.mapTo(self._messages_widget, w.rect().topLeft()).y()
                self._scroll.verticalScrollBar().setValue(max(0, pos_y - 20))
                return

    def _unpin_current(self):
        if not self._pinned_messages:
            return
        idx = max(0, min(self._pinned_index, len(self._pinned_messages) - 1))
        msg = self._pinned_messages[idx]
        msg_id = msg.get("id")
        if not msg_id:
            return

        def _worker():
            self._api.pin_chat_message(self._chat_id, msg_id)
            # Обновить список закреплённых
            chat = self._api.get_internal_chat(self._chat_id)
            if chat:
                self._pinned_messages = chat.get("pinned_messages") or []
                self._pinned_index = 0
                self._sig_ws_data.emit({"type": "_update_pinned"})

        threading.Thread(target=_worker, daemon=True).start()

    def _on_forward_requested(self, msg: dict):
        """Переслать сообщение в другой чат (выбор из списка)."""
        msg_id = msg.get("id")
        if not msg_id:
            return

        def _worker():
            chats = self._api.get_internal_chats() or []
            chats = [c for c in chats if c.get("id") != self._chat_id]
            self._sig_ws_data.emit({"type": "_forward_pick", "msg_id": msg_id, "chats": chats})

        threading.Thread(target=_worker, daemon=True).start()

    def _show_forward_dialog(self, msg_id: int, chats: list):
        from PyQt5.QtWidgets import QDialog, QDialogButtonBox, QListWidget, QListWidgetItem, QVBoxLayout

        dlg = QDialog(self)
        dlg.setWindowTitle("Переслать сообщение")
        dlg.setMinimumWidth(320)
        vb = QVBoxLayout(dlg)
        lbl = QLabel("Выберите чат:")
        lbl.setStyleSheet("font-size: 12px; color: #333;")
        vb.addWidget(lbl)

        lst = QListWidget()
        lst.setStyleSheet("border: 1px solid #E0E0E0; border-radius: 4px;")
        for chat in chats:
            title = chat.get("title") or f"Чат #{chat['id']}"
            item = QListWidgetItem(title)
            item.setData(Qt.UserRole, chat.get("id"))
            lst.addItem(item)
        vb.addWidget(lst)

        bb = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        vb.addWidget(bb)

        if dlg.exec_() == QDialog.Accepted and lst.currentItem():
            target_chat_id = lst.currentItem().data(Qt.UserRole)
            threading.Thread(
                target=lambda: self._api.forward_chat_message(self._chat_id, msg_id, target_chat_id),
                daemon=True,
            ).start()

    # ===========================================================
    # Публичные методы
    # ===========================================================

    def refresh(self):
        self._load_messages()

    def set_title(self, title: str):
        self._title_lbl.setText(title)

    # ===========================================================
    # Cleanup
    # ===========================================================

    def closeEvent(self, event):
        if self._ws_worker:
            self._ws_worker.stop()
        super().closeEvent(event)

    def hideEvent(self, event):
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)
