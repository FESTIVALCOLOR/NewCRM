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

import io
import json
import logging
import os
import threading
import time
from typing import Optional

from PyQt5.QtCore import Qt, QTimer, pyqtSignal
from PyQt5.QtGui import QKeySequence
from PyQt5.QtWidgets import (
    QAction,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QScrollArea,
    QShortcut,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ui.chat_message_bubble import ChatMessageBubble

logger = logging.getLogger(__name__)

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

    def __init__(self, chat_id: int, chat_type: str, employee: dict, api_client, parent=None):
        super().__init__(parent)
        self._chat_id = chat_id
        self._chat_type = chat_type
        self._employee = employee
        self._api = api_client
        self._ws_worker: Optional[ChatWebSocketWorker] = None
        self._messages = []
        self._typing_timer = None
        self._is_typing = False

        # Подключаем сигналы ДО setup_ui, чтобы они были готовы когда придут данные
        self._sig_messages_ready.connect(self._on_messages_loaded)
        self._sig_new_msg.connect(self._append_message)
        self._sig_ws_data.connect(self._handle_ws_event)

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

        self._title_lbl = QLabel("Чат")
        self._title_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        h_layout.addWidget(self._title_lbl)

        h_layout.addStretch()

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

        # ---------- TYPING INDICATOR ----------
        self._typing_lbl = QLabel("")
        self._typing_lbl.setFixedHeight(20)
        self._typing_lbl.setStyleSheet("font-size: 10px; color: #888; padding-left: 12px;")
        main_layout.addWidget(self._typing_lbl)

        # ---------- MESSAGES AREA ----------
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #FFFFFF; }")

        self._messages_widget = QWidget()
        self._messages_widget.setStyleSheet("background: #FFFFFF;")
        self._messages_layout = QVBoxLayout(self._messages_widget)
        self._messages_layout.setContentsMargins(8, 8, 8, 8)
        self._messages_layout.setSpacing(2)
        self._messages_layout.addStretch()  # index 0 — прижимает сообщения к низу

        self._scroll.setWidget(self._messages_widget)
        main_layout.addWidget(self._scroll, stretch=1)

        # ---------- INPUT PANEL ----------
        input_frame = QFrame()
        input_frame.setStyleSheet("""
            QFrame {
                background: #FAFAFA;
                border-top: 1px solid #E0E0E0;
            }
        """)
        input_frame.setFixedHeight(90)
        i_layout = QVBoxLayout(input_frame)
        i_layout.setContentsMargins(8, 6, 8, 6)
        i_layout.setSpacing(4)

        row = QHBoxLayout()
        row.setSpacing(6)

        attach_btn = QPushButton("📎")
        attach_btn.setFixedSize(32, 32)
        attach_btn.setToolTip("Прикрепить файл")
        attach_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d9d9d9; border-radius: 4px;
                font-size: 16px; background: #fff;
            }
            QPushButton:hover { background: #f5f5f5; }
        """)
        attach_btn.clicked.connect(self._attach_file)
        row.addWidget(attach_btn)

        voice_btn = QPushButton("🎤")
        voice_btn.setFixedSize(32, 32)
        voice_btn.setCheckable(True)
        voice_btn.setToolTip("Голосовое сообщение")
        voice_btn.setStyleSheet("""
            QPushButton {
                border: 1px solid #d9d9d9; border-radius: 4px;
                font-size: 16px; background: #fff;
            }
            QPushButton:hover { background: #f5f5f5; }
            QPushButton:checked { background: #ffd93c; border-color: #e6c535; }
        """)
        voice_btn.clicked.connect(self._toggle_voice)
        self._voice_btn = voice_btn
        row.addWidget(voice_btn)

        self._input = QTextEdit()
        self._input.setFixedHeight(44)
        self._input.setPlaceholderText("Введите сообщение... (Enter — отправить, Shift+Enter — перенос)")
        self._input.setStyleSheet("""
            QTextEdit {
                border: 1px solid #d9d9d9;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                background: #fff;
            }
        """)
        self._input.textChanged.connect(self._on_input_changed)
        row.addWidget(self._input, stretch=1)

        send_btn = QPushButton("Отправить")
        send_btn.setFixedHeight(44)
        send_btn.setStyleSheet("""
            QPushButton {
                background: #ffd93c;
                border: none;
                border-radius: 6px;
                padding: 0 18px;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover { background: #f5c800; }
            QPushButton:pressed { background: #e6b800; }
        """)
        send_btn.clicked.connect(self._send_text)
        row.addWidget(send_btn)

        i_layout.addLayout(row)
        main_layout.addWidget(input_frame)

        send_shortcut = QShortcut(QKeySequence(Qt.Key_Return), self._input)
        send_shortcut.activated.connect(self._send_text)

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
        self._messages = list(msgs) if msgs else []
        self._render_all_messages()

    def _render_all_messages(self):
        layout = self._messages_layout
        # Оставляем stretch на позиции 0, удаляем все пузыри (позиции 1+)
        while layout.count() > 1:
            item = layout.takeAt(1)
            if item.widget():
                item.widget().deleteLater()

        my_id = self._employee.get("id")
        for msg in self._messages:
            is_own = msg.get("sender_employee_id") == my_id
            bubble = ChatMessageBubble(msg, is_own)
            layout.addWidget(bubble)

        self._messages_widget.update()
        self._scroll_to_bottom()

    def _append_message(self, msg):
        """Добавить одно сообщение. Вызывается из GUI-потока через сигнал."""
        if not isinstance(msg, dict):
            return
        msg_id = msg.get("id")
        if msg_id and any(m.get("id") == msg_id for m in self._messages):
            return
        my_id = self._employee.get("id")
        is_own = msg.get("sender_employee_id") == my_id
        bubble = ChatMessageBubble(msg, is_own)
        self._messages_layout.addWidget(bubble)
        self._messages.append(msg)
        self._messages_widget.update()
        self._scroll_to_bottom()

    def _scroll_to_bottom(self):
        # Вызывается из GUI-потока — QTimer здесь работает корректно
        QTimer.singleShot(50, lambda: self._scroll.verticalScrollBar().setValue(self._scroll.verticalScrollBar().maximum()))

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
            self._sig_ws_data.emit(data)  # thread-safe через сигнал

        def on_error(err):
            logger.warning(f"Chat WS error: {err}")

        def on_close():
            logger.debug(f"Chat WS closed: chat_id={self._chat_id}")

        def on_open():
            logger.debug(f"Chat WS opened: chat_id={self._chat_id}")

        self._ws_worker = ChatWebSocketWorker(ws_url, on_message, on_error, on_close, on_open)
        self._ws_worker.start()

    def _handle_ws_event(self, data):
        if not isinstance(data, dict):
            return
        event = data.get("type")
        if event == "new_message":
            msg = data.get("message", {})
            self._append_message(msg)
        elif event == "typing":
            if data.get("is_typing"):
                self._typing_lbl.setText(f"{data.get('name', '')} печатает…")
            else:
                self._typing_lbl.setText("")
        elif event == "message_deleted":
            msg_id = data.get("message_id")
            for i, m in enumerate(self._messages):
                if m.get("id") == msg_id:
                    self._messages[i]["is_deleted"] = True
                    self._messages[i]["content"] = "[Сообщение удалено]"
            self._render_all_messages()

    def _poll_new_messages(self):
        """Fallback polling при отсутствии websocket-client."""

        def _worker():
            msgs = self._api.get_chat_messages(self._chat_id, limit=50)
            if msgs and len(msgs) > len(self._messages):
                for m in msgs[len(self._messages) :]:
                    self._sig_new_msg.emit(m)  # thread-safe через сигнал

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
        text = self._input.toPlainText().strip()
        if not text:
            return
        self._input.clear()
        self._stop_typing()

        def _worker():
            msg = self._api.send_chat_message(self._chat_id, text)
            if msg:
                self._sig_new_msg.emit(msg)  # thread-safe через сигнал

        threading.Thread(target=_worker, daemon=True).start()

    def _attach_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Все файлы (*);;Изображения (*.jpg *.jpeg *.png *.gif *.webp);;PDF (*.pdf)")
        if not path:
            return
        fname = os.path.basename(path)
        ext = os.path.splitext(fname)[1].lower()
        msg_type = "image" if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"} else "file"

        def _worker():
            with open(path, "rb") as f:
                data = f.read()
            result = self._api.upload_chat_file(self._chat_id, data, fname, message_type=msg_type)
            if result:
                self._sig_new_msg.emit(result)  # thread-safe через сигнал

        threading.Thread(target=_worker, daemon=True).start()

    def _toggle_voice(self):
        from PyQt5.QtWidgets import QMessageBox

        self._voice_btn.setChecked(False)
        QMessageBox.information(self, "Голосовое", "Запись голосовых доступна в мобильной версии.\nНа десктопе используйте прикрепление файла (.webm, .mp3).")

    # ===========================================================
    # Диалог участников
    # ===========================================================

    def _show_members_dialog(self):
        from ui.chat_members_dialog import ChatMembersDialog

        dlg = ChatMembersDialog(self._chat_id, self._chat_type, self._employee, self._api, self)
        dlg.exec_()

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
