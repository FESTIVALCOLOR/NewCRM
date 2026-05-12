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

from datetime import datetime, timedelta
import json
import logging
import os
import threading
import time
from typing import Optional
import uuid

from PyQt5.QtCore import Qt, QTimer, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
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
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from ui.custom_title_bar import CustomTitleBar
from utils.icon_loader import IconLoader
from utils.permissions import _has_perm

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
        delay = 1
        while self._running:
            _connected = [False]

            def _on_open_cb(_c=_connected):
                _c[0] = True
                self._on_open()

            try:
                self._ws = _ws_lib.WebSocketApp(
                    self._url,
                    on_message=lambda ws, msg: self._on_message(msg),
                    on_error=lambda ws, err: self._on_error(err),
                    on_close=lambda ws, *a: self._on_close(),
                    on_open=lambda ws: _on_open_cb(),
                )
                self._ws.run_forever(ping_interval=30)
            except Exception as e:
                logger.warning(f"WS error: {e}")
            if self._running:
                time.sleep(delay)
                delay = 3 if _connected[0] else min(delay * 2, 30)

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
        # Право просмотра телефона клиента (только для client-чатов)
        self._show_phone = _has_perm(employee, api_client, "chat.client.show_phone") if chat_type == "client" else False

        # Режим ответа / редактирования
        self._reply_to_msg: Optional[dict] = None
        self._edit_msg_id: Optional[int] = None
        self._first_unread_id: Optional[int] = None

        # Закреплённые сообщения
        self._pinned_messages: list = []
        self._pinned_index: int = 0

        # Файлы, ожидающие отправки
        self._pending_files: list = []

        # Поиск по сообщениям: хранение результатов и текущей позиции
        self._search_results: list = []
        self._search_idx: int = 0

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

        # Кнопка папки Яндекс.Диска (скрыта, показывается если у чата есть yandex_folder_path)
        self._yd_folder_btn = QPushButton("Файлы чата")
        self._yd_folder_btn.setFixedHeight(28)
        self._yd_folder_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #FFCA28;
                border-radius: 4px;
                padding: 0 10px;
                font-size: 11px;
                background: #FFFDE7;
                color: #795548;
                max-height: 26px;
            }
            QPushButton:hover { background: #FFF9C4; }
        """)
        self._yd_folder_btn.setVisible(False)
        self._yd_folder_btn.clicked.connect(self._open_yd_folder)
        h_layout.addWidget(self._yd_folder_btn)

        members_btn = QPushButton("Участники")
        members_btn.setFixedHeight(28)
        members_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 0 14px;
                font-size: 12px;
                background: #fff;
                max-height: 26px;
            }
            QPushButton:hover { background: #f5f5f5; }
        """)
        members_btn.clicked.connect(self._show_members_dialog)
        h_layout.addWidget(members_btn)

        search_btn = IconLoader.create_icon_button("search", "", "Поиск в чате")
        search_btn.setFixedSize(28, 28)
        search_btn.clicked.connect(self._toggle_search)
        h_layout.addWidget(search_btn)

        main_layout.addWidget(header)

        # ---------- SEARCH PANEL (скрыта по умолчанию) ----------
        self._search_panel = QFrame()
        self._search_panel.setStyleSheet("QFrame { background: #FAFAFA; }")
        self._search_panel.setVisible(False)
        sp_layout = QVBoxLayout(self._search_panel)
        sp_layout.setContentsMargins(12, 6, 12, 6)
        sp_layout.setSpacing(4)
        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Поиск в чате…")
        self._search_input.setStyleSheet("QLineEdit { border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; font-size: 12px; background: #fff; }")
        self._search_input.returnPressed.connect(self._do_search)
        sp_layout.addWidget(self._search_input)
        self._search_result_lbl = QLabel("")
        self._search_result_lbl.setStyleSheet("font-size: 10px; color: #888;")
        self._search_result_lbl.setVisible(False)
        sp_layout.addWidget(self._search_result_lbl)

        # Навигация по результатам поиска (скрыта пока нет результатов)
        self._search_nav_row = QWidget()
        nav_h = QHBoxLayout(self._search_nav_row)
        nav_h.setContentsMargins(0, 0, 0, 0)
        nav_h.setSpacing(4)
        _nav_btn_style = (
            "QPushButton { border: 1px solid #d9d9d9; border-radius: 4px; background: #fff; "
            "font-size: 12px; padding: 0 8px; min-width: 26px; max-width: 26px; min-height: 22px; max-height: 22px; }"
            "QPushButton:hover { background: #f5f5f5; }"
            "QPushButton:disabled { color: #ccc; }"
        )
        self._search_prev_btn = QPushButton("▲")
        self._search_prev_btn.setToolTip("Предыдущее найденное")
        self._search_prev_btn.setStyleSheet(_nav_btn_style)
        self._search_prev_btn.clicked.connect(lambda: self._search_navigate(-1))
        nav_h.addWidget(self._search_prev_btn)
        self._search_nav_lbl = QLabel("0 / 0")
        self._search_nav_lbl.setStyleSheet("font-size: 10px; color: #555; min-width: 40px; text-align: center;")
        self._search_nav_lbl.setAlignment(Qt.AlignCenter)
        nav_h.addWidget(self._search_nav_lbl)
        self._search_next_btn = QPushButton("▼")
        self._search_next_btn.setToolTip("Следующее найденное")
        self._search_next_btn.setStyleSheet(_nav_btn_style)
        self._search_next_btn.clicked.connect(lambda: self._search_navigate(1))
        nav_h.addWidget(self._search_next_btn)
        nav_h.addStretch()
        self._search_nav_row.setVisible(False)
        sp_layout.addWidget(self._search_nav_row)

        main_layout.addWidget(self._search_panel)

        self._build_pinned_bar(main_layout)

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

        # ---------- FLOATING SCROLL-TO-BOTTOM BUTTON ----------
        self._scroll_btn = QPushButton("▼", self._scroll)
        self._scroll_btn.setFixedSize(36, 36)
        self._scroll_btn.setToolTip("Прокрутить вниз")
        self._scroll_btn.setStyleSheet("""
            QPushButton {
                background: #ffd93c;
                border: none;
                border-radius: 18px;
                font-size: 13px;
                font-weight: bold;
                color: #555;
                letter-spacing: 0px;
            }
            QPushButton:hover {
                background: #f5c800;
                color: #222;
            }
            QPushButton:pressed {
                background: #e6b800;
            }
        """)
        self._scroll_btn.clicked.connect(self._scroll_to_bottom)
        self._scroll_btn.hide()
        self._scroll.verticalScrollBar().valueChanged.connect(self._on_scroll_value_changed)

        self._build_action_area(main_layout)
        self._build_input_panel(main_layout)

    def _build_pinned_bar(self, main_layout):
        self._pinned_bar = QFrame()
        self._pinned_bar.setStyleSheet("QFrame { background: #fff; }")
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
        self._pin_text_lbl.mousePressEvent = lambda e: self._scroll_to_pinned()
        pin_text_col.addWidget(self._pin_text_lbl)
        pin_text_widget = QWidget()
        pin_text_widget.setLayout(pin_text_col)
        pin_text_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        pin_text_widget.setCursor(Qt.PointingHandCursor)
        pin_text_widget.mousePressEvent = lambda e: self._scroll_to_pinned()
        pb_layout.addWidget(pin_text_widget)

        self._pin_nav_lbl = QLabel("")
        self._pin_nav_lbl.setStyleSheet("color: #E65100; font-size: 10px; font-weight: bold;")
        pb_layout.addWidget(self._pin_nav_lbl)

        unpin_btn = QPushButton("×")
        unpin_btn.setFixedSize(24, 24)
        unpin_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 14px; line-height: 1; color: #aaa; }QPushButton:hover { color: #555; }")
        unpin_btn.setToolTip("Открепить сообщение")
        unpin_btn.clicked.connect(self._unpin_current)
        pb_layout.addWidget(unpin_btn)

        self._pinned_bar.setVisible(False)
        self._pinned_bar.mousePressEvent = lambda e: self._scroll_to_pinned()
        self._pinned_messages = []
        self._pinned_index = 0
        main_layout.addWidget(self._pinned_bar)

    def _build_action_area(self, main_layout):
        # ACTION BAR (ответ / редактирование)
        self._action_bar = QFrame()
        self._action_bar.setStyleSheet("QFrame { background: #F3F6FF; }")
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
        cancel_btn.setFixedSize(28, 28)
        cancel_btn.setStyleSheet("QPushButton { border: none; background: transparent; font-size: 16px; line-height: 1; color: #888; }QPushButton:hover { color: #333; }")
        cancel_btn.clicked.connect(self._cancel_action)
        ab_layout.addWidget(cancel_btn)
        self._action_bar.setVisible(False)
        main_layout.addWidget(self._action_bar)

        # UPLOAD PROGRESS
        self._upload_progress = QProgressBar()
        self._upload_progress.setFixedHeight(4)
        self._upload_progress.setRange(0, 0)
        self._upload_progress.setStyleSheet("QProgressBar { border: none; background: #f0f0f0; }QProgressBar::chunk { background: #ffd93c; }")
        self._upload_progress.setVisible(False)
        main_layout.addWidget(self._upload_progress)

        # PENDING FILES PREVIEW
        self._pending_panel = QFrame()
        self._pending_panel.setStyleSheet("QFrame { background: #E3F2FD; }")
        self._pending_panel.setFixedHeight(104)
        pp_vbox = QVBoxLayout(self._pending_panel)
        pp_vbox.setContentsMargins(8, 4, 8, 6)
        pp_vbox.setSpacing(4)
        self._caption_input = QLineEdit()
        self._caption_input.setPlaceholderText("Подпись к файлу…")
        self._caption_input.setFixedHeight(28)
        self._caption_input.setStyleSheet("QLineEdit { border: 1px solid #BBDEFB; border-radius: 14px; padding: 0 10px; font-size: 11px; background: #fff; }")
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

    def _build_input_panel(self, main_layout):
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
            }
        """)
        input_frame.setMinimumHeight(56)
        input_frame.setMaximumHeight(180)
        self._input_frame = input_frame
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

        self._card_files_btn = IconLoader.create_action_button("folder", tooltip="Файлы из карточки CRM", button_size=36, icon_size=18, icon_color="#666")
        self._card_files_btn.setStyleSheet(self._card_files_btn.styleSheet() + "QPushButton { border-radius: 18px; }")
        self._card_files_btn.clicked.connect(self._attach_card_file)
        self._card_files_btn.setVisible(False)
        row.addWidget(self._card_files_btn)

        voice_btn = IconLoader.create_action_button("message-circle", tooltip="Голосовое (только мобиль)", button_size=36, icon_size=18, icon_color="#888")
        voice_btn.setCheckable(True)
        voice_btn.setStyleSheet(voice_btn.styleSheet() + "QPushButton { border-radius: 18px; } QPushButton:checked { background: #ffd93c; border-color: #e6c535; }")
        voice_btn.clicked.connect(self._toggle_voice)
        self._voice_btn = voice_btn
        row.addWidget(voice_btn)

        self._input = ChatInputEdit()
        self._input.setMinimumHeight(36)
        self._input.setMaximumHeight(120)
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
        _sig = self._sig_messages_ready

        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            msgs = self._api.get_chat_messages(self._chat_id, limit=50)
            try:
                _sig.emit(chat, msgs or [])
            except Exception:
                pass

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
            yd_path = chat.get("yandex_folder_path") or ""
            self._yd_folder_path = yd_path
            self._yd_folder_btn.setVisible(bool(yd_path))
            self._card_files_btn.setVisible(bool(self._crm_card_id))
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
        is_forwarded = "(переслано)" in (msg.get("sender_display_name") or "")
        token = getattr(self._api, "token", "") or ""
        base_url = getattr(self._api, "base_url", "") or ""
        bubble = ChatMessageBubble(msg, is_own, token=token, base_url=base_url, show_phone=self._show_phone, is_forwarded=is_forwarded)
        bubble.edit_requested.connect(self._on_edit_requested)
        bubble.delete_requested.connect(self._on_delete_requested)
        bubble.reply_requested.connect(self._on_reply_requested)
        bubble.pin_requested.connect(self._on_pin_requested)
        bubble.scroll_to_requested.connect(self._scroll_to_message)
        bubble.forward_requested.connect(self._on_forward_requested)
        bubble.height_changed.connect(self._on_bubble_height_changed)
        if self._crm_card_id:
            bubble.copy_to_card_requested.connect(self._on_copy_to_card_requested)
        return bubble

    def _on_bubble_height_changed(self, delta: int):
        """Компенсировать сдвиг скролла при async-загрузке изображений/превью."""
        sb = self._scroll.verticalScrollBar()
        near_bottom = sb.maximum() == 0 or sb.value() >= sb.maximum() - 120
        if not near_bottom:
            sb.setValue(sb.value() + delta)

    def _render_all_messages(self):
        layout = self._messages_layout
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        unread_divider_shown = False
        last_date = None
        i = 0
        while i < len(self._messages):
            msg = self._messages[i]

            # Дата-разделитель при смене дня
            msg_date = self._msg_local_date(msg)
            if msg_date and msg_date != last_date:
                layout.addWidget(self._make_date_divider(self._date_label(msg_date)))
                last_date = msg_date

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
        gallery = ChatGalleryWidget(msgs, is_own, token=token, base_url=base_url, chat_id=self._chat_id, crm_card_id=self._crm_card_id or 0, parent=self)
        gallery.edit_requested.connect(self._on_edit_requested)
        gallery.delete_requested.connect(self._on_delete_requested)
        gallery.reply_requested.connect(self._on_reply_requested)
        gallery.pin_requested.connect(self._on_pin_requested)
        gallery.scroll_to_requested.connect(self._scroll_to_message)
        gallery.forward_requested.connect(self._on_forward_requested)
        if self._crm_card_id:
            gallery.copy_to_card_requested.connect(self._on_copy_to_card_requested)
        return gallery

    @staticmethod
    def _msg_local_date(msg: dict):
        """Вернуть локальную дату сообщения или None при ошибке."""
        ts = msg.get("created_at", "")
        if not ts:
            return None
        try:
            clean = ts.rstrip("Z").replace("+00:00", "")
            dt_utc = datetime.fromisoformat(clean).replace(tzinfo=None)
            epoch = (dt_utc - datetime(1970, 1, 1)).total_seconds()
            return datetime.fromtimestamp(epoch).date()
        except Exception:
            return None

    @staticmethod
    def _date_label(d) -> str:
        """Человекочитаемая метка для дня: Сегодня / Вчера / «12 мая»."""
        today = datetime.now().date()
        if d == today:
            return "Сегодня"
        if d == today - timedelta(days=1):
            return "Вчера"
        months = ["янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
        return f"{d.day} {months[d.month - 1]}"

    def _make_date_divider(self, label: str) -> QWidget:
        w = QWidget()
        row = QHBoxLayout(w)
        row.setContentsMargins(8, 8, 8, 4)
        row.setAlignment(Qt.AlignCenter)

        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 10px; color: #bbb; white-space: nowrap; background: transparent;")
        row.addWidget(lbl)

        return w

    def _make_unread_divider(self) -> QWidget:
        w = QWidget()
        w.setObjectName("unreadDivider")
        row = QHBoxLayout(w)
        row.setContentsMargins(8, 4, 8, 4)
        row.setAlignment(Qt.AlignCenter)

        lbl = QLabel("Новые сообщения")
        lbl.setStyleSheet("font-size: 10px; color: #E53935; white-space: nowrap;")
        row.addWidget(lbl)

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
        sb = self._scroll.verticalScrollBar()
        near_bottom = sb.maximum() == 0 or sb.value() >= sb.maximum() - 120
        if near_bottom:
            self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        # Вызывается из GUI-потока — QTimer здесь работает корректно
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum()))

    def _on_scroll_value_changed(self, value: int):
        sb = self._scroll.verticalScrollBar()
        near_bottom = sb.maximum() == 0 or value >= sb.maximum() - 120
        self._scroll_btn.setVisible(not near_bottom)
        if not near_bottom:
            self._reposition_scroll_btn()

    def _reposition_scroll_btn(self):
        btn = self._scroll_btn
        x = self._scroll.width() - btn.width() - 14
        y = self._scroll.height() - btn.height() - 14
        btn.move(x, y)
        btn.raise_()

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
        dlg = CustomQuestionBox(self, "Удалить сообщение", "Удалить это сообщение?")
        if dlg.exec_() != dlg.Accepted:
            return

        def _worker():
            ok = self._api.delete_chat_message(self._chat_id, msg_id)
            if ok:
                for i, m in enumerate(self._messages):
                    if m.get("id") == msg_id:
                        self._messages[i] = dict(m, is_deleted=True, content="Сообщение удалено", message_type="text")
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
        # Захватываем сигналы локально — при удалении виджета обращение к self вызовет RuntimeError
        _sig_data = self._sig_ws_data
        _sig_status = self._sig_ws_status

        def on_message(raw: str):
            try:
                data = json.loads(raw)
            except Exception:
                return
            try:
                _sig_data.emit(data)
            except RuntimeError:
                pass

        def on_error(err):
            logger.warning(f"Chat WS error: {err}")

        def on_close():
            logger.debug(f"Chat WS closed: chat_id={self._chat_id}")
            try:
                _sig_status.emit(False)
            except Exception:
                pass

        def on_open():
            logger.debug(f"Chat WS opened: chat_id={self._chat_id}")
            try:
                _sig_status.emit(True)
            except Exception:
                pass

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
        _internal = {
            "_hide_progress",
            "_forward_pick",
            "_update_pinned",
            "_rerender",
            "_update_member_count",
            "_copy_to_card_pick",
            "_copy_success",
            "_copy_error",
            "_card_files_ready",
            "_search_results",
            "_upload_error",
        }
        if event in _internal:
            self._ws_internal(event, data)
        elif event in ("new_message", "new_message_group"):
            self._ws_on_message(event, data)
        elif event in ("member_added", "member_removed"):
            self._ws_reload_member_count()
        elif event == "message_pinned":
            self._ws_reload_pinned()
        elif event == "typing":
            self._ws_on_typing(data)
        elif event in ("message_deleted", "message_edited"):
            self._ws_on_message_mutated(event, data)

    def _ws_internal(self, event: str, data: dict):
        if event == "_hide_progress":
            self._upload_progress.setVisible(False)
            self._remove_upload_placeholders()
        elif event == "_forward_pick":
            self._show_forward_dialog(data.get("msg_ids", []), data.get("chats", []))
        elif event == "_update_pinned":
            self._update_pinned_bar()
        elif event == "_rerender":
            self._render_all_messages()
        elif event == "_update_member_count":
            count = data.get("count", 0)
            self._members_count_str = f"{count} уч." if count else ""
            self._on_ws_status(bool(self._ws_worker and self._ws_worker._running))
        elif event == "_copy_to_card_pick":
            self._show_copy_to_card_dialog(
                data.get("msg_id"),
                data.get("msg_type"),
                data.get("variations"),
                data.get("next_variation", 1),
            )
        elif event == "_copy_success":
            CustomMessageBox(self, "Готово", "Файл скопирован в карточку CRM.", icon_type="success").exec_()
        elif event == "_copy_error":
            CustomMessageBox(self, "Ошибка", "Не удалось скопировать файл в карточку.", icon_type="error").exec_()
        elif event == "_card_files_ready":
            err = data.get("error")
            if err:
                CustomMessageBox(self, "Ошибка", f"Не удалось загрузить файлы карточки:\n{err}", icon_type="error").exec_()
                return
            files = data.get("files", [])
            if not files:
                CustomMessageBox(self, "Файлы карточки", "У этой карточки нет загруженных файлов.", icon_type="info").exec_()
                return
            dlg = CardFilesPickerDialog(files, parent=self)
            if dlg.exec_() and dlg.selected_file:
                self._upload_card_file(dlg.selected_file)
        elif event == "_search_results":
            results = data.get("results", [])
            if not results:
                self._search_result_lbl.setText("Ничего не найдено")
                self._search_result_lbl.setVisible(True)
                self._search_nav_row.setVisible(False)
                return
            self._search_results = results
            # Начинаем с самого последнего (самого нового) результата
            self._search_idx = len(results) - 1
            self._search_result_lbl.setText(f"Найдено: {len(results)}")
            self._search_result_lbl.setVisible(True)
            self._search_nav_row.setVisible(True)
            self._search_update_nav()
            self._scroll_to_msg_id(results[self._search_idx].get("id"))
        elif event == "_upload_error":
            CustomMessageBox(self, "Ошибка загрузки", f"Не удалось загрузить файл:\n{data.get('msg', '')}", icon_type="error").exec_()

    def _ws_on_message(self, event: str, data: dict):
        if event == "new_message":
            msg = data.get("message", {})
            self._append_message(msg)
            msg_id = msg.get("id") if isinstance(msg, dict) else None
            if msg_id and self.isVisible():
                threading.Thread(
                    target=lambda: self._api.mark_chat_read(self._chat_id, msg_id),
                    daemon=True,
                ).start()
                self.unread_changed.emit(self._chat_id, 0)
        else:
            messages = data.get("messages", [])
            for msg in messages:
                self._messages.append(msg)
            self._render_all_messages()
            self._scroll_to_bottom()
            last_id = messages[-1].get("id") if messages else None
            if last_id and self.isVisible():
                threading.Thread(
                    target=lambda: self._api.mark_chat_read(self._chat_id, last_id),
                    daemon=True,
                ).start()
                self.unread_changed.emit(self._chat_id, 0)

    def _ws_reload_member_count(self):
        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            if chat:
                self._sig_ws_data.emit({"type": "_update_member_count", "count": chat.get("member_count", 0)})

        threading.Thread(target=_worker, daemon=True).start()

    def _ws_reload_pinned(self):
        def _worker():
            chat = self._api.get_internal_chat(self._chat_id)
            if chat:
                self._pinned_messages = chat.get("pinned_messages") or []
                self._pinned_index = 0
                self._sig_ws_data.emit({"type": "_update_pinned"})

        threading.Thread(target=_worker, daemon=True).start()

    def _ws_on_typing(self, data: dict):
        if data.get("is_typing"):
            self._typing_lbl.setText(f"{data.get('name', '')} печатает…")
            self._typing_lbl.setVisible(True)
        else:
            self._typing_lbl.setText("")
            self._typing_lbl.setVisible(False)

    def _ws_on_message_mutated(self, event: str, data: dict):
        msg_id = data.get("message_id")
        if event == "message_deleted":
            for i, m in enumerate(self._messages):
                if m.get("id") == msg_id:
                    self._messages[i] = dict(m, is_deleted=True, content="Сообщение удалено", message_type="text")
        else:
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
        # Динамическая высота поля ввода (до 4 строк)
        doc_h = int(self._input.document().size().height())
        new_h = max(36, min(doc_h + 14, 120))
        if self._input.height() != new_h:
            self._input.setFixedHeight(new_h)
            frame_h = max(56, new_h + 20)
            self._input_frame.setFixedHeight(frame_h)

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
        reply_msg_snapshot = None
        if self._reply_to_msg is not None:
            reply_to_id = self._reply_to_msg.get("id")
            reply_msg_snapshot = dict(self._reply_to_msg)
            self._cancel_action()

        def _worker():
            msg = self._api.send_chat_message(self._chat_id, text, reply_to_id=reply_to_id)
            if msg:
                # Сервер может не возвращать reply_preview в POST-ответе — добавляем локально
                if reply_msg_snapshot and not msg.get("reply_preview"):
                    reply_type = reply_msg_snapshot.get("message_type", "text")
                    reply_content = reply_msg_snapshot.get("content") or ("[Изображение]" if reply_type == "image" else "[Файл]")
                    msg["reply_preview"] = {
                        "id": reply_msg_snapshot.get("id"),
                        "sender_display_name": reply_msg_snapshot.get("sender_display_name"),
                        "content": reply_content,
                        "message_type": reply_type,
                        "yandex_path": reply_msg_snapshot.get("yandex_path"),
                        "file_name": reply_msg_snapshot.get("file_name"),
                    }
                    msg["reply_to_id"] = reply_to_id
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
            if len(self._pending_files) >= 20:
                CustomMessageBox(self, "Лимит файлов", "Можно прикрепить не более 20 файлов за раз.", icon_type="info").exec_()
                break
            fname = os.path.basename(path)
            ext = os.path.splitext(fname)[1].lower()
            msg_type = "image" if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else "file"
            self._pending_files.append({"path": path, "name": fname, "type": msg_type})
        self._refresh_pending_panel()

    def _attach_card_file(self):
        if not self._crm_card_id:
            return

        def _load():
            try:
                card = self._api.get_crm_card(self._crm_card_id)
                contract_id = card.get("contract_id") if card else None
                files = self._api.get_project_files(contract_id) if contract_id else []
                self._sig_ws_data.emit({"type": "_card_files_ready", "files": files or []})
            except Exception as e:
                self._sig_ws_data.emit({"type": "_card_files_ready", "files": [], "error": str(e)})

        threading.Thread(target=_load, daemon=True).start()

    def _upload_card_file(self, file_info: dict):
        """Прикрепить существующий файл проекта в чат (через сервер, без скачивания байт)."""
        fname = file_info.get("name") or "файл"
        public_link = file_info.get("link") or ""
        yandex_path = file_info.get("yandex_path") or ""
        if not yandex_path:
            CustomMessageBox(self, "Ошибка", "Нет пути к файлу на Яндекс.Диске.", icon_type="error").exec_()
            return

        self._upload_progress.setVisible(True)
        _sig_new = self._sig_new_msg
        _sig_ws = self._sig_ws_data
        _api = self._api
        _chat_id = self._chat_id

        def _worker():
            try:
                ext = os.path.splitext(fname)[1].lower()
                msg_type = "image" if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else "file"
                result = _api.link_project_file_to_chat(
                    _chat_id,
                    yandex_path,
                    fname,
                    public_link=public_link,
                    message_type=msg_type,
                )
                if result:
                    try:
                        _sig_new.emit(result)
                    except Exception:
                        pass
                else:
                    try:
                        _sig_ws.emit({"type": "_upload_error", "msg": "Сервер не вернул результат — проверьте права доступа"})
                    except Exception:
                        pass
            except Exception as e:
                try:
                    _sig_ws.emit({"type": "_upload_error", "msg": str(e)})
                except Exception:
                    pass
            finally:
                try:
                    _sig_ws.emit({"type": "_hide_progress"})
                except Exception:
                    pass

        threading.Thread(target=_worker, daemon=True).start()

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
            rm_btn.setFixedSize(22, 22)
            rm_btn.setStyleSheet("""
                QPushButton {
                    background: #E53935; color: #fff;
                    border: none; border-radius: 11px;
                    font-size: 11px; padding: 0;
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

    def _add_upload_placeholders(self, files: list):
        """Добавляет временные пузыри-плейсхолдеры в ленту пока файлы загружаются."""
        from PyQt5.QtGui import QPixmap as _QPixmap

        self._upload_placeholders = []
        layout = self._messages_layout
        for f in files:
            ph = QFrame()
            ph.setObjectName("bubble")
            ph.setStyleSheet("QFrame#bubble { background: #E8F5E9; border-radius: 12px; border-bottom-right-radius: 2px; }")
            ph.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
            ph.setMaximumWidth(300)
            ph_l = QVBoxLayout(ph)
            ph_l.setContentsMargins(10, 6, 10, 6)
            ph_l.setSpacing(4)
            if f["type"] == "image":
                pix = _QPixmap(f["path"])
                if not pix.isNull():
                    img_lbl = QLabel()
                    img_lbl.setPixmap(pix.scaled(180, 120, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                    img_lbl.setFixedSize(180, 120)
                    img_lbl.setStyleSheet("border-radius: 6px;")
                    ph_l.addWidget(img_lbl)
            else:
                name_lbl = QLabel(f["name"][:30] + ("…" if len(f["name"]) > 30 else ""))
                name_lbl.setStyleSheet("font-size: 12px; color: #555;")
                ph_l.addWidget(name_lbl)
            status_lbl = QLabel("Загрузка...")
            status_lbl.setStyleSheet("font-size: 10px; color: #888; font-style: italic;")
            ph_l.addWidget(status_lbl)

            row = QWidget()
            row.setAutoFillBackground(False)
            row_l = QHBoxLayout(row)
            row_l.setContentsMargins(4, 2, 4, 2)
            row_l.setSpacing(0)
            spacer = QWidget()
            spacer.setMinimumWidth(80)
            spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            row_l.addWidget(spacer)
            row_l.addWidget(ph)
            layout.addWidget(row)
            self._upload_placeholders.append(row)

        self._scroll_to_bottom()

    def _remove_upload_placeholders(self):
        """Удаляет временные пузыри после завершения загрузки."""
        for ph in getattr(self, "_upload_placeholders", []):
            self._messages_layout.removeWidget(ph)
            ph.deleteLater()
        self._upload_placeholders = []

    def _send_pending_files(self):
        if not self._pending_files:
            return
        files = list(self._pending_files)
        caption = self._caption_input.text().strip()
        self._caption_input.clear()
        self._pending_files.clear()
        self._refresh_pending_panel()
        self._add_upload_placeholders(files)
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
        CustomMessageBox(
            self,
            "Голосовое",
            "Запись голосовых доступна в мобильной версии.\nНа десктопе используйте прикрепление файла (.webm, .mp3).",
            icon_type="info",
        ).exec_()

    def _open_yd_folder(self):
        from urllib.parse import quote as _quote

        path = getattr(self, "_yd_folder_path", "") or ""
        if not path:
            return
        clean = path[len("disk:") :] if path.startswith("disk:") else path
        url = f"https://disk.yandex.ru/client/disk{_quote(clean, safe='/')}"
        QDesktopServices.openUrl(QUrl(url))

    # ===========================================================
    # Поиск по сообщениям
    # ===========================================================

    def _toggle_search(self):
        visible = not self._search_panel.isVisible()
        self._search_panel.setVisible(visible)
        if visible:
            self._search_input.setFocus()
            self._search_input.selectAll()
        else:
            self._search_input.clear()
            self._search_results = []
            self._search_idx = 0
            self._search_result_lbl.setVisible(False)
            self._search_nav_row.setVisible(False)

    def _do_search(self):
        q = self._search_input.text().strip()
        if not q or len(q) < 2:
            return
        if not self._chat_id or not self._api:
            return
        self._search_result_lbl.setText("Поиск…")
        self._search_result_lbl.setVisible(True)

        def _worker():
            try:
                results = self._api.search_chat_messages(self._chat_id, q) or []
            except Exception:
                results = []
            try:
                self._sig_ws_data.emit({"type": "_search_results", "results": results})
            except Exception:
                pass

        threading.Thread(target=_worker, daemon=True).start()

    def _scroll_to_msg_id(self, msg_id: int):
        """Найти пузырь с данным msg_id и прокрутить к нему."""
        layout = self._messages_layout
        for i in range(layout.count()):
            item = layout.itemAt(i)
            if not item:
                continue
            w = item.widget()
            if isinstance(w, ChatMessageBubble) and w.msg_id == msg_id:
                from PyQt5.QtCore import QTimer

                QTimer.singleShot(0, lambda _w=w: self._scroll.ensureWidgetVisible(_w))
                return
        # Если не нашли (может быть вне загруженных) — показываем подсказку
        self._search_result_lbl.setText(f"Сообщение #{msg_id} вне загруженной истории")

    def _search_update_nav(self):
        """Обновить счётчик навигации поиска и состояние кнопок."""
        total = len(self._search_results)
        idx = self._search_idx
        self._search_nav_lbl.setText(f"{idx + 1} / {total}")
        self._search_prev_btn.setEnabled(idx > 0)
        self._search_next_btn.setEnabled(idx < total - 1)

    def _search_navigate(self, direction: int):
        """Перейти к следующему (direction=1) или предыдущему (direction=-1) результату поиска."""
        if not self._search_results:
            return
        self._search_idx = max(0, min(self._search_idx + direction, len(self._search_results) - 1))
        self._search_update_nav()
        msg_id = self._search_results[self._search_idx].get("id")
        if msg_id:
            self._scroll_to_msg_id(msg_id)

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
        """Переслать сообщение (или группу) в другой чат."""
        msg_id = msg.get("id")
        if not msg_id:
            return
        # Для галереи собираем все msg_ids группы
        group_id = msg.get("group_id")
        if group_id:
            msg_ids = [m.get("id") for m in self._messages if m.get("group_id") == group_id and m.get("id") and not m.get("is_deleted")]
        else:
            msg_ids = [msg_id]

        def _worker():
            chats = self._api.get_internal_chats() or []
            chats = [c for c in chats if c.get("id") != self._chat_id]
            self._sig_ws_data.emit({"type": "_forward_pick", "msg_ids": msg_ids, "chats": chats})

        threading.Thread(target=_worker, daemon=True).start()

    def _show_forward_dialog(self, msg_ids: list, chats: list):
        from PyQt5.QtWidgets import QDialog, QListWidget, QListWidgetItem, QVBoxLayout

        if not msg_ids:
            return
        is_group = len(msg_ids) > 1
        title_text = "Переслать галерею" if is_group else "Переслать сообщение"

        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground, True)
        dlg.setMinimumWidth(340)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("borderFrame")
        frame.setStyleSheet("QFrame#borderFrame { background:#fff; border:1px solid #E0E0E0; border-radius:10px; }")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        title_bar = CustomTitleBar(dlg, title_text, simple_mode=True)
        title_bar.setStyleSheet("CustomTitleBar { background:#fff; border-bottom:1px solid #E0E0E0; border-top-left-radius:10px; border-top-right-radius:10px; }")
        fl.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet("background:#F9FAFB; border-bottom-left-radius:10px; border-bottom-right-radius:10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 14, 16, 16)
        cl.setSpacing(8)

        hint_text = f"Переслать {len(msg_ids)} файлов. Выберите чат:" if is_group else "Выберите чат:"
        lbl = QLabel(hint_text)
        lbl.setStyleSheet("font-size: 12px; color: #333;")
        cl.addWidget(lbl)

        search = QLineEdit()
        search.setPlaceholderText("Поиск по чатам…")
        search.setStyleSheet("QLineEdit { border: 1px solid #E0E0E0; border-radius: 4px; padding: 4px 8px; font-size: 12px; background: #fff; }")
        cl.addWidget(search)

        lst = QListWidget()
        lst.setStyleSheet("border:1px solid #E0E0E0; border-radius:4px; font-size:12px; background:#fff;")
        lst.setFixedHeight(160)
        for chat in chats:
            chat_title = chat.get("title") or f"Чат #{chat['id']}"
            item = QListWidgetItem(chat_title)
            item.setData(Qt.UserRole, chat.get("id"))
            lst.addItem(item)
        cl.addWidget(lst)

        def _filter_chats(text):
            lo = text.lower()
            for i in range(lst.count()):
                it = lst.item(i)
                it.setHidden(lo not in it.text().lower())

        search.textChanged.connect(_filter_chats)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            "QPushButton { border:1px solid #d9d9d9; border-radius:4px; font-size:12px; padding:0 14px; background:#fff; max-height:26px; } QPushButton:hover { background:#f5f5f5; }"
        )
        cancel_btn.clicked.connect(dlg.reject)
        ok_btn = QPushButton("Переслать")
        ok_btn.setFixedHeight(28)
        ok_btn.setStyleSheet(
            "QPushButton { background:#ffd93c; border:none; border-radius:4px; font-size:12px; font-weight:bold; padding:0 14px; max-height:26px; } QPushButton:hover { background:#f5c800; }"
        )
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        cl.addLayout(btn_row)

        fl.addWidget(content)
        outer.addWidget(frame)

        if dlg.exec_() == QDialog.Accepted and lst.currentItem():
            target_chat_id = lst.currentItem().data(Qt.UserRole)
            if is_group:
                threading.Thread(
                    target=lambda: self._api.forward_chat_message_group(self._chat_id, target_chat_id, msg_ids),
                    daemon=True,
                ).start()
            else:
                threading.Thread(
                    target=lambda: self._api.forward_chat_message(self._chat_id, msg_ids[0], target_chat_id),
                    daemon=True,
                ).start()

    # ===========================================================
    # Копирование файла в карточку CRM
    # ===========================================================

    # Читаемые названия назначений (ключи = значения destination для API)
    _DESTINATION_LABELS = {
        # Стадии
        "stage_1": "1 стадия — Планировочное решение",
        "stage_2": "2 стадия — Концепция дизайна",
        "stage_3": "3 стадия — Чертежный проект",
        "stage_1_revisions": "1 стадия — Правки",
        "stage_2_revisions": "2 стадия — Правки концепции",
        "stage_3_revisions": "3 стадия — Правки чертежей",
        # Документы договора
        "contract_file_yandex_path": "Договор",
        "additional_agreement_yandex_path": "Дополнительное соглашение",
        "act_planning_yandex_path": "Акт — Планировочное решение",
        "act_concept_yandex_path": "Акт — Концепция",
        "act_final_yandex_path": "Акт — Финал",
        "info_letter_yandex_path": "Информационное письмо",
        "act_planning_signed_yandex_path": "Акт подписанный — Планировочное",
        "act_concept_signed_yandex_path": "Акт подписанный — Концепция",
        "act_final_signed_yandex_path": "Акт подписанный — Финал",
        "info_letter_signed_yandex_path": "Информационное письмо (подписанное)",
        "advance_receipt_yandex_path": "Чек — Аванс",
        "additional_receipt_yandex_path": "Чек — Доп. оплата",
        "third_receipt_yandex_path": "Чек — 3-я оплата",
        "tech_task_yandex_path": "Техническое задание",
        "photo_documentation_yandex_path": "Фотофиксация",
        "references_yandex_path": "Референсы",
        "measurement_yandex_path": "Замер",
    }

    def _on_copy_to_card_requested(self, msg: dict):
        """Загружаем вариации стадии (для stage_2) и открываем диалог выбора назначения."""
        msg_id = msg.get("id")
        msg_type = msg.get("message_type", "file")
        if not msg_id or not self._crm_card_id:
            return

        def _worker():
            variations_data = self._api.get_card_stage_variations(self._chat_id, self._crm_card_id, "stage_2")
            self._sig_ws_data.emit(
                {
                    "type": "_copy_to_card_pick",
                    "msg_id": msg_id,
                    "msg_type": msg_type,
                    "variations": variations_data.get("variations", []),
                    "next_variation": variations_data.get("next_variation", 1),
                }
            )

        threading.Thread(target=_worker, daemon=True).start()

    def _show_copy_to_card_dialog(self, msg_id: int, msg_type: str, variations: list, next_variation: int):
        from PyQt5.QtWidgets import (
            QDialog,
            QGroupBox,
            QListWidget,
            QListWidgetItem,
            QRadioButton,
            QVBoxLayout,
            QWidget,
        )

        dlg = QDialog(self)
        dlg.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dlg.setAttribute(Qt.WA_TranslucentBackground, True)
        dlg.setMinimumWidth(400)

        outer = QVBoxLayout(dlg)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("borderFrame")
        frame.setStyleSheet("QFrame#borderFrame { background:#fff; border:1px solid #E0E0E0; border-radius:10px; }")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        title_bar = CustomTitleBar(dlg, "Скопировать в карточку", simple_mode=True)
        title_bar.setStyleSheet("CustomTitleBar { background:#fff; border-bottom:1px solid #E0E0E0; border-top-left-radius:10px; border-top-right-radius:10px; }")
        fl.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet("background:#F9FAFB; border-bottom-left-radius:10px; border-bottom-right-radius:10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(16, 14, 16, 16)
        cl.setSpacing(8)

        lbl = QLabel("Выберите назначение файла:")
        lbl.setStyleSheet("font-size: 12px; color: #333; font-weight: bold;")
        cl.addWidget(lbl)

        lst = QListWidget()
        lst.setStyleSheet("border:1px solid #E0E0E0; border-radius:4px; font-size:12px; background:#fff;")
        lst.setFixedHeight(240)

        for key in ("stage_1", "stage_2", "stage_3", "stage_1_revisions", "stage_2_revisions", "stage_3_revisions"):
            item = QListWidgetItem(self._DESTINATION_LABELS[key])
            item.setData(Qt.UserRole, key)
            lst.addItem(item)

        doc_keys = [k for k in self._DESTINATION_LABELS if k not in ("stage_1", "stage_2", "stage_3", "stage_1_revisions", "stage_2_revisions", "stage_3_revisions")]
        for key in doc_keys:
            item = QListWidgetItem(self._DESTINATION_LABELS[key])
            item.setData(Qt.UserRole, key)
            lst.addItem(item)

        cl.addWidget(lst)

        var_group = QGroupBox("Вариация (для 2 стадии):")
        var_group.setStyleSheet("font-size: 11px; color: #555;")
        var_vb = QVBoxLayout(var_group)
        var_vb.setSpacing(4)

        _var_radios = []
        for v in variations:
            files_hint = ", ".join(v.get("files", [])[:2])
            label = f"Вариация {v['variation']}" + (f" ({files_hint})" if files_hint else "")
            rb = QRadioButton(label)
            rb.setProperty("variation", v["variation"])
            rb.setStyleSheet("font-size: 11px;")
            var_vb.addWidget(rb)
            _var_radios.append(rb)

        rb_new = QRadioButton(f"Новая вариация {next_variation}")
        rb_new.setProperty("variation", next_variation)
        rb_new.setChecked(True)
        rb_new.setStyleSheet("font-size: 11px;")
        var_vb.addWidget(rb_new)
        _var_radios.append(rb_new)

        var_group.setVisible(False)
        cl.addWidget(var_group)

        def _on_dest_changed():
            item = lst.currentItem()
            dest = item.data(Qt.UserRole) if item else ""
            var_group.setVisible(dest == "stage_2")
            dlg.adjustSize()

        lst.currentItemChanged.connect(lambda *_: _on_dest_changed())

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            "QPushButton { border:1px solid #d9d9d9; border-radius:4px; font-size:12px; padding:0 14px; background:#fff; max-height:26px; } QPushButton:hover { background:#f5f5f5; }"
        )
        cancel_btn.clicked.connect(dlg.reject)
        ok_btn = QPushButton("Скопировать")
        ok_btn.setFixedHeight(28)
        ok_btn.setStyleSheet(
            "QPushButton { background:#ffd93c; border:none; border-radius:4px; font-size:12px; font-weight:bold; padding:0 14px; max-height:26px; } QPushButton:hover { background:#f5c800; }"
        )
        ok_btn.clicked.connect(dlg.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(ok_btn)
        cl.addLayout(btn_row)

        fl.addWidget(content)
        outer.addWidget(frame)

        if dlg.exec_() != QDialog.Accepted:
            return

        item = lst.currentItem()
        if not item:
            return
        destination = item.data(Qt.UserRole)
        variation = None
        if destination == "stage_2":
            for rb in _var_radios:
                if rb.isChecked():
                    variation = rb.property("variation")
                    break

        card_id = self._crm_card_id

        def _do_copy():
            result = self._api.copy_message_to_card(self._chat_id, msg_id, card_id, destination, variation)
            if result:
                self._sig_ws_data.emit({"type": "_copy_success"})
            else:
                self._sig_ws_data.emit({"type": "_copy_error"})

        threading.Thread(target=_do_copy, daemon=True).start()

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

    def cleanup(self):
        """Остановить WS и отключить сигналы перед удалением виджета."""
        if self._ws_worker:
            self._ws_worker.stop()
            self._ws_worker = None
        try:
            self._sig_messages_ready.disconnect()
            self._sig_new_msg.disconnect()
            self._sig_ws_data.disconnect()
            self._sig_ws_status.disconnect()
        except (RuntimeError, TypeError):
            pass

    def closeEvent(self, event):
        self.cleanup()
        super().closeEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "_scroll_btn") and self._scroll_btn.isVisible():
            self._reposition_scroll_btn()

    def hideEvent(self, event):
        super().hideEvent(event)

    def showEvent(self, event):
        super().showEvent(event)


class CardFilesPickerDialog:
    """Диалог выбора файла из данных CRM-карточки (Яндекс.Диск).

    После exec_() атрибут selected_file содержит dict {name, link, yandex_path}
    или None если пользователь отменил.

    Файлы группируются по стадиям и сортируются по вариациям.
    """

    # Метки стадий для отображения (код → читаемое название)
    _STAGE_LABELS = {
        "measurement": "Замер",
        "stage1": "Стадия 1 — Планировочное решение",
        "stage2_concept": "Стадия 2 — Концепция / коллажи",
        "stage2_3d": "Стадия 2 — 3D визуализация",
        "stage3": "Стадия 3 — Чертежный проект",
        "supervision": "Авторский надзор",
        "references": "Референсы",
        "photo_documentation": "Фотофиксация",
        "tech_task": "Техническое задание",
        "documents": "Документы",
        "acts": "Акты",
        "info_letters": "Информационные письма",
        "questionnaire": "Анкета",
    }

    # Порядок отображения стадий
    _STAGE_ORDER = [
        "measurement",
        "stage1",
        "stage2_concept",
        "stage2_3d",
        "stage3",
        "supervision",
        "tech_task",
        "documents",
        "acts",
        "info_letters",
        "references",
        "photo_documentation",
        "questionnaire",
    ]

    def __init__(self, files: list, parent=None):
        from PyQt5.QtCore import QSize, Qt
        from PyQt5.QtGui import QColor, QFont, QIcon, QPainter, QPixmap
        from PyQt5.QtWidgets import (
            QDialog,
            QFrame,
            QHBoxLayout,
            QLabel,
            QListWidget,
            QListWidgetItem,
            QPushButton,
            QVBoxLayout,
            QWidget,
        )

        self._dialog = QDialog(parent)
        self._dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self._dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        self._dialog.setMinimumWidth(520)
        self.selected_file = None  # dict {name, link, yandex_path} или None

        outer = QVBoxLayout(self._dialog)
        outer.setContentsMargins(0, 0, 0, 0)

        frame = QFrame()
        frame.setObjectName("borderFrame")
        frame.setStyleSheet("QFrame#borderFrame { background:#fff; border:1px solid #E0E0E0; border-radius:10px; }")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(0)

        from ui.custom_title_bar import CustomTitleBar

        tb = CustomTitleBar(self._dialog, "Файлы из карточки CRM", simple_mode=True)
        tb.setStyleSheet("CustomTitleBar { background:#fff; border-bottom:1px solid #E0E0E0; border-top-left-radius:10px; border-top-right-radius:10px; }")
        fl.addWidget(tb)

        content = QFrame()
        content.setStyleSheet("background:#F9FAFB; border-bottom-left-radius:10px; border-bottom-right-radius:10px;")
        cl = QVBoxLayout(content)
        cl.setContentsMargins(14, 12, 14, 14)
        cl.setSpacing(8)

        hint = QLabel("Выберите файл — он будет прикреплён к сообщению:")
        hint.setStyleSheet("font-size: 11px; color: #555;")
        cl.addWidget(hint)

        lw = QListWidget()
        lw.setFixedHeight(340)
        lw.setIconSize(QSize(56, 42))
        lw.setStyleSheet(
            "QListWidget { border:1px solid #E0E0E0; border-radius:4px; background:#fff; }"
            "QListWidget::item { padding:2px 4px; }"
            "QListWidget::item:selected { background:#FFF8DC; }"
            "QListWidget::item:hover:!disabled { background:#f5f5f5; }"
        )
        cl.addWidget(lw)

        def _file_icon_text(fname: str) -> str:
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            if ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff"):
                return "IMG"
            if ext == "pdf":
                return "PDF"
            if ext in ("xls", "xlsx", "csv", "ods"):
                return "XLS"
            if ext in ("doc", "docx", "odt", "rtf", "txt"):
                return "DOC"
            if ext in ("zip", "rar", "7z", "tar", "gz"):
                return "ZIP"
            return "FILE"

        def _is_image_ext(fname: str) -> bool:
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            return ext in ("jpg", "jpeg", "png", "gif", "webp", "bmp", "tiff")

        _ICON_COLORS = {
            "IMG": ("#C8E6C9", "#2E7D32"),
            "PDF": ("#FFCDD2", "#B71C1C"),
            "XLS": ("#C8E6C9", "#1B5E20"),
            "DOC": ("#BBDEFB", "#0D47A1"),
            "ZIP": ("#E1BEE7", "#4A148C"),
            "FILE": ("#E0E0E0", "#424242"),
        }

        def _make_file_icon(fname: str) -> QIcon:
            """Цветной плейсхолдер с аббревиатурой типа файла."""
            text = _file_icon_text(fname)
            bg_hex, fg_hex = _ICON_COLORS.get(text, _ICON_COLORS["FILE"])
            pix = QPixmap(56, 42)
            pix.fill(QColor(bg_hex))
            painter = QPainter(pix)
            painter.setPen(QColor(fg_hex))
            fnt = QFont()
            fnt.setBold(True)
            fnt.setPointSize(9)
            painter.setFont(fnt)
            painter.drawText(pix.rect(), Qt.AlignCenter, text)
            painter.end()
            return QIcon(pix)

        # Собираем файлы по стадиям
        by_stage: dict[str, list] = {}
        for f in files:
            s = f.get("stage") or "documents"
            by_stage.setdefault(s, []).append(f)

        ordered_stages = [s for s in self._STAGE_ORDER if s in by_stage]
        extra_stages = [s for s in by_stage if s not in self._STAGE_ORDER]
        all_stages = ordered_stages + extra_stages

        for stage in all_stages:
            stage_label = self._STAGE_LABELS.get(stage, stage)

            # Заголовок стадии
            hdr = QListWidgetItem(f"  {stage_label}")
            hdr.setFlags(Qt.ItemIsEnabled)
            hdr.setBackground(QColor("#E8EEF6"))
            hf = QFont()
            hf.setBold(True)
            hf.setPointSize(9)
            hdr.setFont(hf)
            hdr.setForeground(QColor("#1a3a6b"))
            hdr.setData(Qt.UserRole, None)
            hdr.setSizeHint(QSize(0, 26))
            lw.addItem(hdr)

            # Группируем по вариации
            by_var: dict[int, list] = {}
            for f in by_stage[stage]:
                v = f.get("variation") or 1
                by_var.setdefault(v, []).append(f)
            show_var_headers = len(by_var) > 1 or (len(by_var) == 1 and list(by_var.keys())[0] != 1)

            for var_num in sorted(by_var.keys()):
                if show_var_headers:
                    vhdr = QListWidgetItem(f"      Вариант {var_num}")
                    vhdr.setFlags(Qt.ItemIsEnabled)
                    vhdr.setBackground(QColor("#F3F3F3"))
                    vf = QFont()
                    vf.setItalic(True)
                    vf.setPointSize(8)
                    vhdr.setFont(vf)
                    vhdr.setForeground(QColor("#666"))
                    vhdr.setData(Qt.UserRole, None)
                    vhdr.setSizeHint(QSize(0, 22))
                    lw.addItem(vhdr)

                for f in sorted(by_var[var_num], key=lambda x: x.get("file_order", 0)):
                    fname = f.get("file_name") or f.get("filename") or f.get("original_name") or "файл"
                    link = f.get("public_link") or ""
                    yandex_path = f.get("yandex_path") or ""
                    preview_path = f.get("preview_cache_path") or ""

                    item = QListWidgetItem(fname)
                    item.setData(Qt.UserRole, {"name": fname, "link": link, "yandex_path": yandex_path})
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    item.setSizeHint(QSize(0, 54))

                    # Иконка: реальная миниатюра или цветной плейсхолдер
                    icon_set = False
                    if _is_image_ext(fname) and preview_path and os.path.exists(preview_path):
                        pix = QPixmap(preview_path).scaled(56, 42, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        if not pix.isNull():
                            item.setIcon(QIcon(pix))
                            icon_set = True
                    if not icon_set:
                        item.setIcon(_make_file_icon(fname))

                    lw.addItem(item)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        cancel_btn = QPushButton("Отмена")
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet(
            "QPushButton { border:1px solid #d9d9d9; border-radius:4px; padding:0 14px; font-size:12px; background:#fff; max-height:26px; }QPushButton:hover { background:#f5f5f5; }"
        )
        cancel_btn.clicked.connect(self._dialog.reject)
        btn_row.addWidget(cancel_btn)

        select_btn = QPushButton("Прикрепить файл")
        select_btn.setFixedHeight(28)
        select_btn.setStyleSheet(
            "QPushButton { background:#ffd93c; border:none; border-radius:4px; padding:0 14px; font-size:12px; font-weight:bold; max-height:26px; }QPushButton:hover { background:#f5c800; }"
        )
        select_btn.clicked.connect(lambda: self._on_select(lw))
        btn_row.addWidget(select_btn)

        lw.itemDoubleClicked.connect(lambda _: self._on_select(lw))

        cl.addLayout(btn_row)
        fl.addWidget(content)
        outer.addWidget(frame)

    def _on_select(self, lw):
        from PyQt5.QtCore import Qt

        item = lw.currentItem()
        if not item:
            return
        d = item.data(Qt.UserRole)
        if not d:  # заголовок секции — не выбираем
            return
        self.selected_file = d  # {name, link, yandex_path}
        self._dialog.accept()

    def exec_(self):
        return self._dialog.exec_()
