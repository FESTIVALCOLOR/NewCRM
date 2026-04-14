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

from PyQt5.QtCore import Qt, QTimer, QUrl
from PyQt5.QtGui import QDesktopServices, QFont, QPixmap
from PyQt5.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

_STYLE_OWN = """
    QFrame#bubble {
        background-color: #FFF8DC;
        border-radius: 12px;
        border-bottom-right-radius: 4px;
    }
"""
_STYLE_OTHER = """
    QFrame#bubble {
        background-color: #F5F5F5;
        border-radius: 12px;
        border-bottom-left-radius: 4px;
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

    def __init__(self, message: dict, is_own: bool, parent=None):
        super().__init__(parent)
        self._msg = message
        self._is_own = is_own
        self._setup_ui()

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
        bubble.setMaximumWidth(420)

        v = QVBoxLayout(bubble)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(4)

        # Имя отправителя (только для чужих)
        if not self._is_own:
            name_lbl = QLabel(self._msg.get("sender_display_name", ""))
            name_lbl.setStyleSheet("font-weight: bold; font-size: 11px; color: #555;")
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

        # Время
        ts = self._msg.get("created_at", "")
        if ts and len(ts) >= 16:
            time_str = ts[11:16]  # HH:MM из ISO строки
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
    def _build_system(self, outer: QHBoxLayout):
        lbl = QLabel(self._msg.get("content", ""))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 10px; color: #aaa; font-style: italic; padding: 2px 8px;")
        lbl.setWordWrap(True)
        outer.addStretch()
        outer.addWidget(lbl)
        outer.addStretch()

    def _build_text(self, layout: QVBoxLayout):
        content = self._msg.get("content") or ""
        if self._msg.get("is_deleted"):
            content = "🗑 Сообщение удалено"
        lbl = QLabel(content)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        lbl.setOpenExternalLinks(True)
        lbl.setStyleSheet("font-size: 13px; color: #222;")
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

        img_lbl = QLabel()
        img_lbl.setFixedSize(200, 150)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("border: 1px solid #ddd; border-radius: 6px; background: #f9f9f9;")
        img_lbl.setText("🖼 " + name[:20])
        img_lbl.setToolTip(url)
        img_lbl.setCursor(Qt.PointingHandCursor)

        # Попытка загрузить миниатюру если есть локальный путь
        # (для упрощения — открываем по клику)
        img_lbl.mousePressEvent = lambda _e: QDesktopServices.openUrl(QUrl(url))
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
