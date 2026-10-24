"""
ChatGalleryWidget — группа изображений в пузыре (аналог медиа-галереи мобильной версии).

Принимает список dict-сообщений с message_type='image' из одной group_id.
Рендерит их в сетку (1, 2, 3, 4+ фото) с async-загрузкой через QNetworkAccessManager.
"""

from datetime import datetime
from urllib.parse import quote

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QColor, QPixmap
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkRequest
from PyQt5.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QGridLayout,
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


class ChatGalleryWidget(QWidget):
    """
    Пузырь-галерея: группа изображений с одинаковым group_id.

    Параметры
    ---------
    messages : list[dict]
        Список сообщений с message_type='image' из одной group_id.
        Предполагается непустой список.
    is_own : bool
        True → правая сторона (собственные сообщения).
    token : str
        JWT токен для streaming endpoint.
    base_url : str
        Базовый URL API.
    """

    edit_requested = pyqtSignal(dict)
    delete_requested = pyqtSignal(dict)
    reply_requested = pyqtSignal(dict)
    pin_requested = pyqtSignal(dict)
    scroll_to_requested = pyqtSignal(int)
    forward_requested = pyqtSignal(dict)
    copy_to_card_requested = pyqtSignal(dict)

    def __init__(
        self,
        messages: list,
        is_own: bool,
        token: str = "",
        base_url: str = "",
        chat_id: int = 0,
        crm_card_id: int = 0,
        parent=None,
    ):
        super().__init__(parent)
        self._messages = messages
        self._is_own = is_own
        self._token = token
        self._base_url = base_url.rstrip("/")
        self._chat_id = chat_id
        self._crm_card_id = crm_card_id
        # Первое сообщение группы — источник заголовка и контекстного меню
        self._primary_msg = messages[0] if messages else {}
        # _msg — алиас для совместимости со _scroll_to_message / _scroll_to_pinned
        self._msg = self._primary_msg
        # NAM-объекты храним в списке, чтобы не собирались GC раньше времени
        self._nam_list = []
        self.setAutoFillBackground(False)
        self._setup_ui()

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event):
        self._show_action_menu(event.globalPos())

    def _show_action_menu(self, global_pos):
        msg = self._primary_msg
        if not msg:
            return
        menu = QMenu(self)

        reply_act = menu.addAction("Ответить")
        reply_act.triggered.connect(lambda: self.reply_requested.emit(msg))

        # Переслать
        if not msg.get("is_deleted"):
            fwd_act = menu.addAction("Переслать")
            fwd_act.triggered.connect(lambda: self.forward_requested.emit(msg))

        # Открыть галерею в браузере (только для групп с yandex_path)
        if self._primary_msg.get("yandex_path") and self._base_url and self._token:
            gallery_act = menu.addAction("Открыть галерею")
            gallery_act.triggered.connect(self._open_gallery_link)

        # Скопировать в карточку (только если есть yandex_path и crm_card_id)
        if self._primary_msg.get("yandex_path") and self._crm_card_id:
            copy_card_act = menu.addAction("Скопировать в карточку")
            copy_card_act.triggered.connect(lambda: self.copy_to_card_requested.emit(msg))

        menu.addSeparator()

        pin_label = "Открепить" if msg.get("is_pinned") else "Закрепить"
        pin_act = menu.addAction(pin_label)
        pin_act.triggered.connect(lambda: self.pin_requested.emit(msg))

        if self._is_own and not msg.get("is_deleted"):
            menu.addSeparator()
            del_act = menu.addAction("Удалить")
            del_act.triggered.connect(lambda: self.delete_requested.emit(msg))

        menu.exec_(global_pos)

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _setup_ui(self):
        outer = QHBoxLayout(self)
        outer.setContentsMargins(4, 2, 4, 2)
        outer.setSpacing(0)

        spacer = QWidget()
        spacer.setMinimumWidth(80)
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        spacer.setAutoFillBackground(False)

        bubble = QFrame()
        bubble.setObjectName("bubble")
        bubble.setStyleSheet(_STYLE_OWN if self._is_own else _STYLE_OTHER)
        bubble.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        bubble.setMinimumWidth(120)
        bubble.setMaximumWidth(400)

        if not self._is_own:
            shadow = QGraphicsDropShadowEffect(bubble)
            shadow.setBlurRadius(6)
            shadow.setOffset(0, 1)
            shadow.setColor(QColor(0, 0, 0, 25))
            bubble.setGraphicsEffect(shadow)

        v = QVBoxLayout(bubble)
        v.setContentsMargins(6, 6, 6, 6)
        v.setSpacing(3)

        # Заголовок: имя отправителя + кнопка "..."
        self._build_header(v)

        # Сетка фото
        n = len(self._messages)
        if n == 1:
            self._build_single(v, self._messages[0])
        elif n == 2:
            self._build_two(v, self._messages)
        elif n == 3:
            self._build_three(v, self._messages)
        else:
            self._build_multi(v, self._messages)

        # Подпись (caption) и время
        self._build_footer(v)

        if self._is_own:
            outer.addWidget(spacer)
            outer.addWidget(bubble)
        else:
            outer.addWidget(bubble)
            outer.addWidget(spacer)

    def _build_header(self, layout: QVBoxLayout):
        """Имя отправителя слева + кнопка ... справа."""
        msg = self._primary_msg
        if msg.get("is_deleted"):
            return

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)

        name = msg.get("sender_display_name") or ""
        name_color = "#999" if self._is_own else "#1565C0"
        name_lbl = QLabel(name)
        name_lbl.setStyleSheet(f"font-weight: bold; font-size: 11px; color: {name_color}; background: transparent;")
        name_lbl.setMinimumWidth(0)
        name_lbl.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        row.addWidget(name_lbl, stretch=1)

        more_btn = QPushButton("⋮")
        more_btn.setFixedSize(28, 28)
        more_btn.setStyleSheet(
            """
            QPushButton {
                border: none; background: transparent;
                font-size: 16px; color: #aaa; padding: 0; line-height: 1;
            }
            QPushButton:hover { color: #555; }
        """
        )
        more_btn.clicked.connect(lambda: self._show_action_menu(more_btn.mapToGlobal(more_btn.rect().bottomLeft())))
        row.addWidget(more_btn)

        layout.addLayout(row)

    def _build_footer(self, layout: QVBoxLayout):
        """Caption последнего сообщения (если есть) + время первого."""
        # Caption: content последнего сообщения в группе (если не пустой)
        last_msg = self._messages[-1] if self._messages else {}
        caption = last_msg.get("content") or ""
        if caption:
            cap_lbl = QLabel(caption)
            cap_lbl.setWordWrap(True)
            cap_lbl.setStyleSheet("font-size: 12px; color: #212121; background: transparent;")
            layout.addWidget(cap_lbl)

        # Время
        ts = self._primary_msg.get("created_at", "")
        if not ts:
            return
        time_str = self._format_ts(ts)

        row = QHBoxLayout()
        row.setContentsMargins(0, 2, 0, 0)
        row.setSpacing(4)
        row.addStretch()

        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet("font-size: 9px; color: #999; background: transparent;")
        row.addWidget(time_lbl)

        layout.addLayout(row)

    # ------------------------------------------------------------------
    # Фото-сетки
    # ------------------------------------------------------------------

    def _build_single(self, layout: QVBoxLayout, msg: dict):
        """Одно крупное фото (max 380x260)."""
        img_lbl = self._make_photo_label(msg, fixed_height=200, max_width=380)
        layout.addWidget(img_lbl)

    def _build_two(self, layout: QVBoxLayout, msgs: list):
        """Два фото 50/50 по горизонтали, высота 160px каждое, зазор 2px."""
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        for col, msg in enumerate(msgs):
            img_lbl = self._make_photo_label(msg, fixed_height=160, max_width=190)
            img_lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(img_lbl, 0, col)

        layout.addWidget(grid_widget)

    def _build_three(self, layout: QVBoxLayout, msgs: list):
        """
        Первое фото крупное (2 строки) слева + два маленьких справа.

        [  фото 0   ] [ фото 1 ]
        [ (rowspan) ] [ фото 2 ]
        """
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        # Крупное фото слева, занимает 2 строки
        big = self._make_photo_label(msgs[0], fixed_height=184, max_width=200)
        big.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        grid.addWidget(big, 0, 0, 2, 1)

        # Два маленьких справа
        for row_idx, msg in enumerate(msgs[1:3]):
            small = self._make_photo_label(msg, fixed_height=91, max_width=190)
            small.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(small, row_idx, 1)

        layout.addWidget(grid_widget)

    def _build_multi(self, layout: QVBoxLayout, msgs: list):
        """
        4+ фото:
          - первые 2 широких (180px высота) по одному в строке
          - остальные мелкой сеткой по 3 колонки (100px каждое)
        """
        grid_widget = QWidget()
        grid_widget.setStyleSheet("background: transparent;")
        grid = QGridLayout(grid_widget)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(4)

        # Первые 2 широких
        for i in range(min(2, len(msgs))):
            wide = self._make_photo_label(msgs[i], fixed_height=180, max_width=380)
            wide.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(wide, i, 0, 1, 3)

        # Остальные мелкой сеткой по 3 колонки
        rest = msgs[2:]
        for idx, msg in enumerate(rest):
            row_off = 2 + idx // 3
            col_off = idx % 3
            small = self._make_photo_label(msg, fixed_height=100, max_width=120)
            small.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            grid.addWidget(small, row_off, col_off)

        layout.addWidget(grid_widget)

    # ------------------------------------------------------------------
    # Вспомогательные методы
    # ------------------------------------------------------------------

    def _open_gallery_link(self):
        """Получить публичную ссылку галереи и открыть в браузере."""
        msg_id = self._primary_msg.get("id")
        chat_id = getattr(self, "_chat_id", None)
        if not msg_id:
            return
        # Открываем в фоне через NAM POST запрос
        from urllib.parse import quote as _q

        from PyQt5.QtNetwork import QNetworkRequest

        url = f"{self._base_url}/api/v1/chats/{chat_id}/messages/{msg_id}/gallery-link"
        if not chat_id:
            # Если chat_id нет — открыть файл напрямую
            from PyQt5.QtGui import QDesktopServices

            QDesktopServices.openUrl(QUrl(self._primary_msg.get("file_url", "")))
            return
        nam = QNetworkAccessManager(self)
        self._nam_list.append(nam)
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"Authorization", f"Bearer {self._token}".encode())
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        reply = nam.post(req, b"")

        def _on_done():
            if reply.error() == 0:
                import json as _json

                data = _json.loads(reply.readAll().data().decode("utf-8", errors="ignore"))
                pub_url = data.get("public_url", "")
                if pub_url:
                    from PyQt5.QtGui import QDesktopServices

                    QDesktopServices.openUrl(QUrl(pub_url))
            reply.deleteLater()

        reply.finished.connect(_on_done)

    def _make_photo_label(self, msg: dict, fixed_height: int, max_width: int) -> QLabel:
        """Создать QLabel-заглушку и запустить async-загрузку изображения."""
        name = msg.get("file_name", "изображение")
        display_name = name[:20] + ("…" if len(name) > 20 else "")

        img_lbl = QLabel(display_name)
        img_lbl.setFixedHeight(fixed_height)
        img_lbl.setMaximumWidth(max_width)
        img_lbl.setAlignment(Qt.AlignCenter)
        img_lbl.setStyleSheet(
            """
            border: 1px solid #ddd;
            border-radius: 4px;
            background: #f0f0f0;
            color: #888;
            font-size: 10px;
        """
        )
        img_lbl.setCursor(Qt.PointingHandCursor)

        url = msg.get("file_url", "")
        if url:
            img_lbl.mousePressEvent = lambda _e, u=url: self._open_url(u)
        img_lbl.setToolTip(name)

        self._load_image(img_lbl, msg, fixed_height, max_width)
        return img_lbl

    def _load_image(self, img_lbl: QLabel, msg: dict, fixed_height: int, max_width: int):
        """Async-загрузка через QNetworkAccessManager (GUI-поток, через сигнал finished)."""
        yandex_path = msg.get("yandex_path", "")
        url_direct = msg.get("file_url", "")

        load_url = ""
        if yandex_path and self._token and self._base_url:
            path = yandex_path.replace("disk:", "", 1)
            encoded = quote(path, safe="/")
            load_url = f"{self._base_url}/api/v1/files/stream?yandex_path={encoded}&token={quote(self._token, safe='')}"
        elif url_direct:
            load_url = url_direct

        if not load_url:
            return

        nam = QNetworkAccessManager(self)
        self._nam_list.append(nam)

        req = QNetworkRequest(QUrl(load_url))
        if self._token and not yandex_path:
            req.setRawHeader(b"Authorization", f"Bearer {self._token}".encode())

        reply = nam.get(req)

        def _on_finished():
            if not img_lbl.isVisible():
                reply.deleteLater()
                return
            if reply.error() == 0:
                data = reply.readAll()
                pix = QPixmap()
                if pix.loadFromData(data):
                    scaled = pix.scaled(
                        max_width,
                        fixed_height,
                        Qt.KeepAspectRatioByExpanding,
                        Qt.SmoothTransformation,
                    )
                    # Кропируем до нужного размера (центр)
                    if scaled.width() > max_width or scaled.height() > fixed_height:
                        x = max(0, (scaled.width() - max_width) // 2)
                        y = max(0, (scaled.height() - fixed_height) // 2)
                        scaled = scaled.copy(x, y, min(max_width, scaled.width()), min(fixed_height, scaled.height()))
                    img_lbl.setPixmap(scaled)
                    img_lbl.setStyleSheet("border-radius: 4px; background: transparent;")
                    img_lbl.setToolTip(msg.get("file_name", "изображение"))
            reply.deleteLater()

        reply.finished.connect(_on_finished)

    @staticmethod
    def _open_url(url: str):
        from PyQt5.QtCore import QUrl as _QUrl
        from PyQt5.QtGui import QDesktopServices

        QDesktopServices.openUrl(_QUrl(url))

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
