"""
Пузырь сообщения чата — стиль мобильной версии (Telegram/WhatsApp).

Свои сообщения  — справа (bg #E8F5E9 — зелёный)
Чужие сообщения — слева (bg #FFFFFF + тень)

message_type:
    text   — QLabel с текстом
    voice  — аудиоплеер (кнопка воспроизведения)
    image  — миниатюра с async-загрузкой + клик для открытия
    file   — иконка + имя файла (ссылка-кнопка)
    system — серый курсив по центру
"""

from collections import OrderedDict
from datetime import datetime
from urllib.parse import quote

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QDesktopServices, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)
import sip

from utils.icon_loader import IconLoader

_IMAGE_CACHE: "OrderedDict[str, QPixmap]" = OrderedDict()
_IMAGE_CACHE_MAX = 60

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


class ChatMessageBubble(QWidget):
    """
    Один пузырь сообщения.

    Параметры
    ---------
    message : dict
        Поля: id, sender_display_name, message_type,
              content, file_url, yandex_path, file_name, created_at,
              is_deleted, is_edited, reply_preview
    is_own : bool
        True  → правая сторона (собственное)
        False → левая (чужое)
    token : str
        JWT токен для авторизации при загрузке изображений
    """

    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    reply_requested = pyqtSignal(dict)
    pin_requested = pyqtSignal(dict)
    scroll_to_requested = pyqtSignal(int)
    forward_requested = pyqtSignal(dict)
    copy_to_card_requested = pyqtSignal(dict)
    height_changed = pyqtSignal(int)  # delta px когда async-загрузка меняет высоту пузыря

    def __init__(self, message: dict, is_own: bool, parent=None, token: str = "", base_url: str = "", show_phone: bool = True):
        super().__init__(parent)
        self._msg = message
        self._is_own = is_own
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._show_phone = show_phone
        self.setAutoFillBackground(False)
        self._setup_ui()

    @property
    def msg_id(self) -> int:
        return self._msg.get("id", 0)

    def contextMenuEvent(self, event):
        self._show_action_menu(event.globalPos())

    def _show_action_menu(self, global_pos):
        if self._msg.get("message_type") == "system":
            return
        menu = QMenu(self)
        reply_act = menu.addAction("Ответить")
        reply_act.triggered.connect(lambda: self.reply_requested.emit(self._msg))

        # Скопировать текст (только для text-сообщений с контентом)
        content = self._msg.get("content") or ""
        if content and not self._msg.get("is_deleted"):
            copy_act = menu.addAction("Скопировать текст")
            copy_act.triggered.connect(lambda: self._copy_text(content))

        # Переслать
        if not self._msg.get("is_deleted"):
            fwd_act = menu.addAction("Переслать")
            fwd_act.triggered.connect(lambda: self.forward_requested.emit(self._msg))

        # Скопировать в карточку (для файлов/изображений)
        msg_type = self._msg.get("message_type", "text")
        has_file = bool(self._msg.get("yandex_path") or self._msg.get("file_url"))
        if msg_type in ("image", "file") and has_file and not self._msg.get("is_deleted"):
            copy_card_act = menu.addAction("Скопировать в карточку")
            copy_card_act.triggered.connect(lambda: self.copy_to_card_requested.emit(self._msg))

        menu.addSeparator()

        pin_label = "Открепить" if self._msg.get("is_pinned") else "Закрепить"
        pin_act = menu.addAction(pin_label)
        pin_act.triggered.connect(lambda: self.pin_requested.emit(self._msg))

        if self._is_own and not self._msg.get("is_deleted"):
            if self._msg.get("message_type", "text") == "text":
                edit_act = menu.addAction("Редактировать")
                edit_act.triggered.connect(lambda: self.edit_requested.emit(self._msg))
            menu.addSeparator()
            del_act = menu.addAction("Удалить")
            del_act.triggered.connect(lambda: self.delete_requested.emit(self._msg))
        menu.exec_(global_pos)

    @staticmethod
    def _copy_text(text: str):
        from PyQt5.QtWidgets import QApplication

        QApplication.clipboard().setText(text)

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

        # Спейсер с противоположной стороны (80px — максимум 80% ширины для пузыря)
        spacer = QWidget()
        spacer.setMinimumWidth(80)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setAutoFillBackground(False)

        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble.setStyleSheet(_STYLE_OWN if self._is_own else _STYLE_OTHER)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble.setMinimumWidth(120)
        bubble.setMaximumWidth(420)

        if not self._is_own:
            shadow = QGraphicsDropShadowEffect(bubble)
            shadow.setBlurRadius(6)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 25))
            bubble.setGraphicsEffect(shadow)

        v = QVBoxLayout(bubble)
        v.setContentsMargins(10, 6, 10, 6)
        v.setSpacing(3)

        # Строка заголовка: имя отправителя + кнопка "⋮"
        self._build_header(v)

        # Маркер пересланного сообщения
        if "(переслано)" in (self._msg.get("sender_display_name") or ""):
            self._build_forwarded_marker(v)

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

        # Нижняя строка: "изм." + время
        self._build_footer(v)

        # Реакции
        self._build_reactions(v)

        if self._is_own:
            outer.addWidget(spacer)
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addWidget(spacer)

    # ----------------------------------------------------------
    def _build_forwarded_marker(self, layout: QVBoxLayout):
        """Серая метка «→ Переслано» между именем отправителя и контентом."""
        fwd = QLabel("→ Переслано")
        fwd.setStyleSheet("font-size: 10px; color: #888; font-style: italic; background: transparent; padding: 0 0 2px 0;")
        layout.addWidget(fwd)

    # ----------------------------------------------------------
    def _build_header(self, layout: QVBoxLayout):
        """Имя отправителя слева + кнопка ⋮ справа."""
        if self._msg.get("is_deleted"):
            return

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        name = self._msg.get("sender_display_name") or ""
        name_color = "#999" if self._is_own else "#1565C0"
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {name_color}; background: transparent;")
        name_lbl.setMinimumWidth(0)
        name_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.addWidget(name_lbl, stretch=1)

        # Чип «клиент» для сообщений от гостей (клиентов по ссылке-приглашению)
        if self._msg.get("sender_guest_token"):
            guest_chip = QLabel("клиент")
            guest_chip.setStyleSheet("font-size: 9px; font-weight: bold; color: #fff; background: #43A047; border-radius: 3px; padding: 1px 5px;")
            row.addWidget(guest_chip)
            phone = self._msg.get("sender_phone") or ""
            if phone and self._show_phone:
                phone_lbl = QLabel(phone)
                phone_lbl.setStyleSheet("font-size: 9px; color: #777; background: transparent;")
                phone_lbl.setToolTip(f"Телефон клиента: {phone}")
                row.addWidget(phone_lbl)

        more_btn = QPushButton("⋮")
        more_btn.setFixedSize(28, 28)
        more_btn.setStyleSheet("""
            QPushButton {
                border: none; background: transparent;
                font-size: 16px; color: #aaa; padding: 0; line-height: 1;
            }
            QPushButton:hover { color: #555; }
        """)
        more_btn.clicked.connect(lambda: self._show_action_menu(more_btn.mapToGlobal(more_btn.rect().bottomLeft())))
        row.addWidget(more_btn)

        layout.addLayout(row)

    def _build_reactions(self, layout: QVBoxLayout):
        """Строка emoji-реакций под временем сообщения."""
        reactions: dict = self._msg.get("reactions") or {}
        if not reactions:
            return
        row = QHBoxLayout()
        row.setContentsMargins(6, 2, 6, 0)
        row.setSpacing(4)
        if self._is_own:
            row.addStretch()
        for emoji, reactors in reactions.items():
            count = len(reactors)
            btn = QPushButton(f"{emoji} {count}")
            btn.setFixedHeight(22)
            btn.setStyleSheet(
                "QPushButton { border: 1px solid #E0E0E0; border-radius: 11px; "
                "background: #F5F5F5; font-size: 12px; padding: 0 8px; color: #333; }"
                "QPushButton:hover { background: #E3F2FD; border-color: #90CAF9; }"
            )
            row.addWidget(btn)
        if not self._is_own:
            row.addStretch()
        layout.addLayout(row)

    def _build_footer(self, layout: QVBoxLayout):
        """Нижняя строка: «изм.» + время."""
        ts = self._msg.get("created_at", "")
        if not ts:
            return
        time_str = self._format_ts(ts)

        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 0)
        row.setSpacing(4)
        row.addStretch()

        if self._msg.get("is_edited"):
            edited_lbl = QLabel("изм.")
            edited_lbl.setStyleSheet("font-size: 9px; color: #bbb; background: transparent;")
            row.addWidget(edited_lbl)

        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("font-size: 9px; color: #999; background: transparent;")
        row.addWidget(time_lbl)

        layout.addLayout(row)

    # ----------------------------------------------------------
    @staticmethod
    def _format_ts(ts: str) -> str:
        """UTC ISO → локальное время. Если не сегодня — добавляет дд.мм."""
        try:
            clean = ts.rstrip("Z").replace("+00:00", "")
            dt_utc = datetime.fromisoformat(clean).replace(tzinfo=None)
            import time as _time  # noqa: PLC0415

            epoch = (dt_utc - datetime(1970, 1, 1)).total_seconds()
            local_dt = datetime.fromtimestamp(epoch)
            today = datetime.now().date()
            if local_dt.date() == today:
                return local_dt.strftime("%H:%M")
            return local_dt.strftime("%d.%m %H:%M")
        except Exception:
            return ts[11:16] if len(ts) >= 16 else ts

    def _build_system(self, outer: QHBoxLayout):
        chip = QFrame()
        chip.setStyleSheet("""
            QFrame {
                background: #E0E0E0;
                border-radius: 10px;
            }
        """)
        chip_layout = QHBoxLayout(chip)
        chip_layout.setContentsMargins(10, 3, 10, 3)
        lbl = QLabel(self._msg.get("content", ""))
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("font-size: 10px; color: #757575; background: transparent;")
        lbl.setWordWrap(True)
        chip_layout.addWidget(lbl)
        outer.addStretch()
        outer.addWidget(chip)
        outer.addStretch()

    def _build_text(self, layout: QVBoxLayout):
        # Превью цитируемого сообщения
        reply = self._msg.get("reply_preview")
        if reply and not self._msg.get("is_deleted"):
            rb = QFrame()
            rb.setStyleSheet("""
                QFrame {
                    background: rgba(21,101,192,0.07);
                    border-left: 3px solid #1565C0;
                    border-radius: 4px;
                }
            """)
            rbl = QHBoxLayout(rb)
            rbl.setContentsMargins(6, 3, 6, 3)
            rbl.setSpacing(6)

            # Текстовая часть цитаты
            rtext_col = QVBoxLayout()
            rtext_col.setSpacing(1)
            sender_lbl = QLabel(reply.get("sender_display_name", ""))
            sender_lbl.setStyleSheet("font-weight: bold; font-size: 10px; color: #1565C0; background: transparent;")
            rtext_col.addWidget(sender_lbl)
            rtext = reply.get("content") or ""
            if reply.get("message_type") in ("image", "file", "voice"):
                rtext = f"[{reply.get('message_type', 'файл')}]"
            rtext_lbl = QLabel((rtext[:60] + "…") if len(rtext) > 60 else rtext)
            rtext_lbl.setStyleSheet("font-size: 10px; color: #555; background: transparent;")
            rtext_col.addWidget(rtext_lbl)
            rbl.addLayout(rtext_col, stretch=1)

            # Миниатюра изображения (если цитируется image с yandex_path)
            yp = reply.get("yandex_path")
            if yp and reply.get("message_type") == "image" and self._base_url and self._token:
                thumb_lbl = QLabel()
                thumb_lbl.setFixedSize(40, 40)
                thumb_lbl.setStyleSheet("border-radius: 4px; background: #e8e8e8;")
                rbl.addWidget(thumb_lbl)
                path = yp[len("disk:") :] if yp.startswith("disk:") else yp
                from urllib.parse import quote as _quote

                stream_url = f"{self._base_url}/api/v1/yadisk/stream?path={_quote(path, safe='/')}&token={self._token}"
                if stream_url in _IMAGE_CACHE:
                    _IMAGE_CACHE.move_to_end(stream_url)
                    pix = _IMAGE_CACHE[stream_url]
                    thumb_lbl.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
                else:
                    nam = QNetworkAccessManager(self)
                    self._nam_list = getattr(self, "_nam_list", [])
                    self._nam_list.append(nam)
                    req = QNetworkRequest(QUrl(stream_url))
                    reply_obj = nam.get(req)

                    def _on_thumb(r=reply_obj, lbl=thumb_lbl, url=stream_url):
                        data = r.readAll().data()
                        pix = QPixmap()
                        pix.loadFromData(data)
                        if not pix.isNull() and not sip.isdeleted(lbl):
                            _IMAGE_CACHE[url] = pix
                            _IMAGE_CACHE.move_to_end(url)
                            while len(_IMAGE_CACHE) > _IMAGE_CACHE_MAX:
                                _IMAGE_CACHE.popitem(last=False)
                            lbl.setPixmap(pix.scaled(40, 40, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))

                    reply_obj.finished.connect(_on_thumb)

            rb.setCursor(Qt.PointingHandCursor)
            rb.mousePressEvent = lambda e: self.scroll_to_requested.emit(self._msg.get("reply_to_id", 0))
            layout.addWidget(rb)

        content = self._msg.get("content") or ""
        if self._msg.get("is_deleted"):
            content = "Сообщение удалено"

        lbl = QLabel(content)
        lbl.setWordWrap(True)
        lbl.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.LinksAccessibleByMouse)
        lbl.setOpenExternalLinks(True)
        if self._msg.get("is_deleted"):
            lbl.setStyleSheet("font-size: 13px; color: #999; font-style: italic; background: transparent;")
        else:
            lbl.setStyleSheet("font-size: 13px; color: #212121; background: transparent;")
        layout.addWidget(lbl)

    def _build_voice(self, layout: QVBoxLayout):
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setAlignment(Qt.AlignVCenter)

        from PyQt5.QtCore import QSize

        play_btn = QPushButton()
        play_icon = IconLoader.load_colored("play", color="#555", size=16)
        play_btn.setIcon(play_icon)
        play_btn.setIconSize(QSize(16, 16))
        play_btn.setFixedSize(32, 32)
        play_btn.setStyleSheet("""
            QPushButton {
                background: #e8e8e8;
                border: 1px solid #d9d9d9;
                border-radius: 16px;
                padding: 0;
            }
            QPushButton:hover { background: #d8d8d8; }
        """)
        open_url = self._build_open_url()
        play_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(open_url)) if open_url else None)

        voice_lbl = QLabel("Голосовое сообщение")
        voice_lbl.setStyleSheet("font-size: 12px; color: #333; background: transparent;")

        row.addWidget(play_btn)
        row.addWidget(voice_lbl)
        row.addStretch()
        layout.addLayout(row)

    def _build_image(self, layout: QVBoxLayout):
        url = self._msg.get("file_url", "")
        yandex_path = self._msg.get("yandex_path", "")
        name = self._msg.get("file_name", "изображение")
        display_name = name[:28] + ("…" if len(name) > 28 else "")

        img_lbl = QLabel(display_name)
        img_lbl.setMinimumSize(120, 80)
        img_lbl.setMaximumWidth(380)
        img_lbl.setFixedHeight(160)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet("""
            border: 1px solid #ddd;
            border-radius: 6px;
            background: #f5f5f5;
            color: #666;
            font-size: 11px;
        """)
        img_lbl.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        img_lbl.setToolTip(f"{name}\n(кликните для открытия)")
        img_lbl.setCursor(Qt.PointingHandCursor)
        _open_url = self._build_open_url()
        img_lbl.mousePressEvent = lambda _e: QDesktopServices.openUrl(QUrl(_open_url)) if _open_url else None

        # Если есть yandex_path и api base_url — используем streaming endpoint (как мобильная версия)
        load_url = ""
        if yandex_path and self._token and self._base_url:
            path = yandex_path.replace("disk:", "", 1)
            encoded = quote(path, safe="/")
            load_url = f"{self._base_url}/api/v1/files/stream?yandex_path={encoded}&token={quote(self._token, safe='')}"
        elif url:
            load_url = url

        if load_url:

            def _apply_pixmap(pix: QPixmap):
                if sip.isdeleted(img_lbl):
                    return
                w = min(pix.width(), 380)
                h = min(int(pix.height() * w / max(pix.width(), 1)), 320)
                h = max(h, 80)
                old_h = img_lbl.height()
                img_lbl.setFixedWidth(w)
                img_lbl.setFixedHeight(h)
                img_lbl.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
                img_lbl.setPixmap(pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                img_lbl.setStyleSheet("border-radius: 6px; background: transparent;")
                img_lbl.setToolTip(name)
                if not sip.isdeleted(layout):
                    bubble_frame = layout.parentWidget()
                    if bubble_frame and not sip.isdeleted(bubble_frame):
                        bubble_frame.setMaximumWidth(w + 20)
                        bubble_frame.setMinimumWidth(min(w + 20, 120))
                        bubble_frame.updateGeometry()
                if not sip.isdeleted(self):
                    self.updateGeometry()
                    delta = h - old_h
                    if delta != 0:
                        self.height_changed.emit(delta)

            if load_url in _IMAGE_CACHE:
                _IMAGE_CACHE.move_to_end(load_url)
                _apply_pixmap(_IMAGE_CACHE[load_url])
            else:
                self._img_nam = QNetworkAccessManager(self)
                req = QNetworkRequest(QUrl(load_url))
                if self._token and not yandex_path:
                    req.setRawHeader(b"Authorization", f"Bearer {self._token}".encode())
                reply = self._img_nam.get(req)

                def _on_reply():
                    if reply.error() == 0:
                        data = reply.readAll()
                        pix = QPixmap()
                        if pix.loadFromData(data):
                            _IMAGE_CACHE[load_url] = pix
                            _IMAGE_CACHE.move_to_end(load_url)
                            while len(_IMAGE_CACHE) > _IMAGE_CACHE_MAX:
                                _IMAGE_CACHE.popitem(last=False)
                            _apply_pixmap(pix)
                    reply.deleteLater()

                reply.finished.connect(_on_reply)

        layout.addWidget(img_lbl)

    def _build_file(self, layout: QVBoxLayout):
        name = self._msg.get("file_name") or "файл"
        url = self._build_open_url()
        is_pdf = name.lower().endswith(".pdf")

        if is_pdf:
            self._build_pdf_preview(layout, name, url)
        else:
            self._build_file_row(layout, name, url)

    def _build_file_row(self, layout: QVBoxLayout, name: str, url: str):
        """Обычный файл: иконка + имя + кнопка Открыть."""
        row = QHBoxLayout()
        row.setSpacing(8)
        row.setAlignment(Qt.AlignVCenter)

        icon_lbl = QLabel()
        file_icon = IconLoader.load_colored("file-text", color="#555", size=20)
        icon_lbl.setPixmap(file_icon.pixmap(20, 20))
        icon_lbl.setStyleSheet("background: transparent;")
        row.addWidget(icon_lbl)

        file_col = QVBoxLayout()
        file_col.setSpacing(1)
        name_lbl = QLabel(name[:30] + ("…" if len(name) > 30 else ""))
        name_lbl.setStyleSheet("font-size: 12px; color: #333; background: transparent;")
        file_col.addWidget(name_lbl)
        size_bytes = self._msg.get("file_size")
        if size_bytes:
            if size_bytes >= 1_048_576:
                size_str = f"{size_bytes / 1_048_576:.1f} МБ"
            elif size_bytes >= 1024:
                size_str = f"{size_bytes / 1024:.0f} КБ"
            else:
                size_str = f"{size_bytes} Б"
            size_lbl = QLabel(size_str)
            size_lbl.setStyleSheet("font-size: 10px; color: #999; background: transparent;")
            file_col.addWidget(size_lbl)
        row.addLayout(file_col, stretch=1)

        open_btn = QPushButton("Открыть")
        open_btn.setFixedHeight(28)
        open_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
                padding: 0px 14px;
                font-size: 12px;
                color: #555;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)) if url else None)
        row.addWidget(open_btn)

        layout.addLayout(row)

    def _build_pdf_preview(self, layout: QVBoxLayout, name: str, url: str):
        """PDF: превью первой страницы (через fitz) + кнопка Открыть."""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                border: 1px solid #E0E0E0;
                border-radius: 6px;
                background: #fafafa;
            }
        """)
        c_layout = QVBoxLayout(container)
        c_layout.setContentsMargins(6, 6, 6, 6)
        c_layout.setSpacing(4)

        # Превью (сначала placeholder)
        preview_lbl = QLabel("PDF")
        preview_lbl.setAlignment(Qt.AlignCenter)
        preview_lbl.setFixedHeight(120)
        preview_lbl.setMaximumWidth(240)
        preview_lbl.setStyleSheet("""
            background: #E53935;
            color: #fff;
            border-radius: 4px;
            font-size: 22px;
            font-weight: bold;
        """)
        c_layout.addWidget(preview_lbl, alignment=Qt.AlignHCenter)

        # Имя файла + кнопка — одинаковая высота 26px
        row = QHBoxLayout()
        row.setSpacing(6)
        row.setAlignment(Qt.AlignVCenter)
        name_lbl = QLabel(name[:28] + ("…" if len(name) > 28 else ""))
        name_lbl.setFixedHeight(26)
        name_lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        name_lbl.setStyleSheet("font-size: 11px; color: #555; background: transparent;")
        row.addWidget(name_lbl, stretch=1)

        open_btn = QPushButton("Открыть")
        open_btn.setFixedHeight(26)
        open_btn.setStyleSheet("""
            QPushButton {
                background: transparent; border: 1px solid #d9d9d9;
                border-radius: 4px; font-size: 11px; color: #555;
                padding: 0 10px; max-height: 26px; min-height: 26px;
            }
            QPushButton:hover { background: #f0f0f0; }
        """)
        open_btn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl(url)) if url else None)
        row.addWidget(open_btn, 0, Qt.AlignVCenter)
        c_layout.addLayout(row)

        layout.addWidget(container)

        # Асинхронная загрузка и рендер превью
        if url:
            self._pdf_nam = QNetworkAccessManager(self)
            req = QNetworkRequest(QUrl(url))
            reply = self._pdf_nam.get(req)

            def _on_pdf_done():
                try:
                    if sip.isdeleted(preview_lbl):
                        return
                    if reply.error() == 0:
                        try:
                            import fitz  # noqa: PLC0415

                            pdf_bytes = reply.readAll().data()
                            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
                            page = doc[0]
                            mat = fitz.Matrix(1.0, 1.0)
                            pix = page.get_pixmap(matrix=mat)
                            img_data = pix.tobytes("png")
                            doc.close()

                            if sip.isdeleted(preview_lbl):
                                return
                            qt_pix = QPixmap()
                            if qt_pix.loadFromData(img_data):
                                w = min(qt_pix.width(), 240)
                                h = min(int(qt_pix.height() * w / max(qt_pix.width(), 1)), 200)
                                h = max(h, 60)
                                old_h = preview_lbl.height()
                                preview_lbl.setFixedWidth(w)
                                preview_lbl.setFixedHeight(h)
                                scaled = qt_pix.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                                preview_lbl.setPixmap(scaled)
                                preview_lbl.setStyleSheet("border-radius: 4px; background: transparent;")
                                preview_lbl.setCursor(Qt.PointingHandCursor)
                                preview_lbl.mousePressEvent = lambda _e: QDesktopServices.openUrl(QUrl(url)) if url else None
                                # Сжать контейнер и пузырь до ширины превью
                                if not sip.isdeleted(container):
                                    container.setMaximumWidth(w + 12)
                                if not sip.isdeleted(layout):
                                    bubble_frame = layout.parentWidget()
                                    if bubble_frame and not sip.isdeleted(bubble_frame):
                                        bubble_frame.setMaximumWidth(w + 12 + 20)
                                        bubble_frame.setMinimumWidth(min(w + 12 + 20, 120))
                                        bubble_frame.updateGeometry()
                                if not sip.isdeleted(self):
                                    delta = h - old_h
                                    if delta != 0:
                                        self.height_changed.emit(delta)
                        except Exception:
                            pass
                except RuntimeError:
                    pass
                finally:
                    try:
                        reply.deleteLater()
                    except RuntimeError:
                        pass

            reply.finished.connect(_on_pdf_done)

    def _build_open_url(self) -> str:
        """Вернуть URL для открытия файла: streaming endpoint (ЯД) или прямой file_url."""
        from urllib.parse import quote as _quote

        yandex_path = self._msg.get("yandex_path", "")
        if yandex_path and self._token and self._base_url:
            path = yandex_path.replace("disk:", "", 1)
            encoded = _quote(path, safe="/")
            return f"{self._base_url}/api/v1/files/stream?yandex_path={encoded}&token={_quote(self._token, safe='')}"
        return self._msg.get("file_url", "")
