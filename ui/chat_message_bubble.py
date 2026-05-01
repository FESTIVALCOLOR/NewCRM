"""
Пузырь сообщения чата — стиль WhatsApp/Telegram.

Чужие сообщения — слева (bg #F5F5F5)
Свои сообщения  — справа (bg #FFF8DC — жёлтые под фирстиль)

message_type:
    text   — QLabel с текстом
    voice  — аудиоплеер (QPushButton воспроизведения)
    image  — миниатюра 200px + клик для открытия
    file   — иконка + имя файла + кнопка открыть
    system — серый курсив по центру
"""

from datetime import datetime

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_STYLE_OWN = """
    QFrame#bubble {
        background-color: #E8F5E9;
        border-radius: 12px;
        border-bottom-right-radius: 2px;
    }
"""
_STYLE_OTHER = """
    QFrame#bubble {
        background-color: #FFFFFF;
        border-radius: 12px;
        border-bottom-left-radius: 2px;
    }
"""
_STYLE_SYSTEM = """
    QFrame#bubble {
        background-color: transparent;
    }
"""


class ChatMessageBubble(QWidget):
    """
    Один пузырь сообщения.

    Параметры
    ---------
    message : dict
        Поля: id, sender_display_name, message_type,
              content, file_url, file_name, created_at, is_deleted
    is_own : bool
        True  → правая сторона (собственное)
        False → левая (чужое)
    """

    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    reply_requested = pyqtSignal(dict)

    def __init__(self, message: dict, is_own: bool, parent=None):
        super().__init__(parent)
        self._msg = message
        self._is_own = is_own
        self._setup_ui()

    def contextMenuEvent(self, event):
        if self._msg.get("message_type") == "system":
            return
        menu = QMenu(self)
        reply_act = menu.addAction("Ответить")
        reply_act.triggered.connect(lambda: self.reply_requested.emit(self._msg))
        if self._is_own and not self._msg.get("is_deleted"):
            if self._msg.get("message_type", "text") == "text":
                edit_act = menu.addAction("Редактировать")
                edit_act.triggered.connect(lambda: self.edit_requested.emit(self._msg))
            menu.addSeparator()
            del_act = menu.addAction("Удалить")
            del_act.triggered.connect(lambda: self.delete_requested.emit(self._msg))
        menu.exec_(event.globalPos())

    # ----------------------------------------------------------
    def _setup_ui(self):
        msg_type = self._msg.get("message_type", "text")
        is_system = msg_type == "system"

        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(0)

        if is_system:
            self._build_system(outer)
            return

        # Отступ-спейсер с противоположной стороны
        spacer = QWidget()
        spacer.setMinimumWidth(60)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble.setStyleSheet(_STYLE_OWN if self._is_own else _STYLE_OTHER)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble.setMinimumWidth(120)
        bubble.setMaximumWidth(460)

        if not self._is_own:
            from PyQt5.QtGui import QColor
            from PyQt5.QtWidgets import QGraphicsDropShadowEffect

            shadow = QGraphicsDropShadowEffect(bubble)
            shadow.setBlurRadius(6)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 25))
            bubble.setGraphicsEffect(shadow)

        v = QVBoxLayout(bubble)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(4)

        # Имя отправителя (только для чужих)
        if not self._is_own:
            name_lbl = QLabel(self._msg.get("sender_display_name", ""))
            name_lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #1565C0;")
            v.addWidget(name_lbl)

        # Содержимое
        if msg_type == "text":
            self._build_text(v)
        elif msg_type == "voice":
            self._build_voice(v)
        elif msg_type == "image":
            self._build_image(v)
        elif msg_type == "file":
            self._build_file(v)
        else:
            self._build_text(v)

        # Время + "изм."
        ts = self._msg.get("created_at", "")
        if ts:
            time_str = self._format_ts(ts)
            if self._msg.get("is_edited"):
                time_str = "изм. " + time_str
            time_lbl = QLabel(time_str)
            time_lbl.setStyleSheet("font-size: 9px; color: #999;")
            time_lbl.setAlignment(Qt.AlignRight)
            v.addWidget(time_lbl)

        if self._is_own:
            outer.addWidget(spacer)
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addWidget(spacer)

    # ----------------------------------------------------------
    @staticmethod
    def _format_ts(ts: str) -> str:
        """UTC ISO → локальное время. Если не сегодня — добавляет дд.мм."""
        try:
            clean = ts.rstrip("Z").replace("+00:00", "")
            dt_utc = datetime.fromisoformat(clean).replace(tzinfo=None)
            # fromisoformat без tzinfo → считаем UTC, конвертируем в local
            import time as _time

            epoch = (dt_utc - datetime(1970, 1, 1)).total_seconds()
            local_dt = datetime.fromtimestamp(epoch)
            today = datetime.now().date()
            if local_dt.date() == today:
                return local_dt.strftime("%H:%M")
            return local_dt.strftime("%d.%m %H:%M")
        except Exception:
            return ts[11:16] if len(ts) >= 16 else ts

    def _build_system(self, outer: QHBoxLayout):
        lbl = QLabel(self._msg.get("content", ""))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 10px; color: #aaa; font-style: italic; padding: 2px 8px;")
        lbl.setWordWrap(True)
        outer.addStretch()
        outer.addWidget(lbl)
        outer.addStretch()

    def _build_text(self, layout: QVBoxLayout):
        # Reply preview
        reply = self._msg.get("reply_preview")
        if reply and not self._msg.get("is_deleted"):
            rb = QFrame()
            rb.setStyleSheet("""
                QFrame {
                    background: rgba(0,0,0,0.06);
                    border-left: 3px solid #aaa;
                    border-radius: 4px;
                }
            """)
            rbl = QVBoxLayout(rb)
            rbl.setContentsMargins(6, 3, 6, 3)
            rbl.setSpacing(1)
            sender_lbl = QLabel(reply.get("sender_display_name", ""))
            sender_lbl.setStyleSheet("font-weight: bold; font-size: 10px; color: #555;")
            rbl.addWidget(sender_lbl)
            rtext = reply.get("content") or ""
            if reply.get("message_type") in ("image", "file", "voice"):
                rtext = f"[{reply.get('message_type', 'файл')}]"
            rtext_lbl = QLabel((rtext[:60] + "…") if len(rtext) > 60 else rtext)
            rtext_lbl.setStyleSheet("font-size: 10px; color: #666;")
            rbl.addWidget(rtext_lbl)
            layout.addWidget(rb)

        content = self._msg.get("content") or ""
        if self._msg.get("is_deleted"):
            content = "Сообщение удалено"
        lbl = QLabel(content)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        lbl.setOpenExternalLinks(True)
        style = "font-size: 13px; color: #999; font-style: italic;" if self._msg.get("is_deleted") else "font-size: 13px; color: #222;"
        lbl.setStyleSheet(style)
        layout.addWidget(lbl)

    def _build_voice(self, layout: QVBoxLayout):
        row = QHBoxLayout()
        row.setSpacing(6)

        play_btn = QPushButton("▶  Голосовое")
        play_btn.setFixedHeight(28)
        play_btn.setStyleSheet("""
            QPushButton {
                background: #e8e8e8;
                border: 1px solid #ccc;
                border-radius: 14px;
                padding: 0 12px;
                font-size: 12px;
            }
            QPushButton:hover { background: #d8d8d8; }
        """)
        url = self._msg.get("file_url", "")
        play_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))

        row.addWidget(play_btn)
        row.addStretch()
        layout.addLayout(row)

    def _build_image(self, layout: QVBoxLayout):
        url = self._msg.get("file_url", "")
        name = self._msg.get("file_name", "изображение")
        display_name = name[:28] + ("…" if len(name) > 28 else "")

        img_lbl = QLabel(display_name)
        img_lbl.setFixedSize(240, 180)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("""
            border: 1px solid #ddd;
            border-radius: 6px;
            background: #f5f5f5;
            color: #666;
            font-size: 11px;
        """)
        img_lbl.setToolTip(f"{name}\n(кликните для открытия)")
        img_lbl.setCursor(Qt.PointingHandCursor)
        img_lbl.mousePressEvent = lambda _e: QDesktopServices.openUrl(QUrl(url))

        if url:
            self._img_nam = QNetworkAccessManager(self)
            reply = self._img_nam.get(QNetworkRequest(QUrl(url)))

            def _on_reply():
                if reply.error() == 0:
                    data = reply.readAll()
                    pix = QPixmap()
                    if pix.loadFromData(data):
                        img_lbl.setPixmap(pix.scaled(240, 180, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                        img_lbl.setToolTip(name)
                reply.deleteLater()

            reply.finished.connect(_on_reply)

        layout.addWidget(img_lbl)

    def _build_file(self, layout: QVBoxLayout):
        name = self._msg.get("file_name") or "файл"
        url = self._msg.get("file_url", "")

        row = QHBoxLayout()
        row.setSpacing(6)

        icon_lbl = QLabel("📎")
        icon_lbl.setStyleSheet("font-size: 18px;")
        row.addWidget(icon_lbl)

        name_lbl = QLabel(name[:30] + ("…" if len(name) > 30 else ""))
        name_lbl.setStyleSheet("font-size: 12px; color: #333;")
        row.addWidget(name_lbl)
        row.addStretch()

        open_btn = QPushButton("Открыть")
        open_btn.setFixedHeight(24)
        open_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #aaa;
                border-radius: 4px;
                padding: 0 8px;
                font-size: 11px;
                color: #555;
            }
            QPushButton:hover { background: #eee; }
        """)
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)))
        row.addWidget(open_btn)

        layout.addLayout(row)
