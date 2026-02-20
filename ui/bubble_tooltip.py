# -*- coding: utf-8 -*-
"""
Кастомный tooltip в виде облачка с хвостиком (стрелкой) и тенью.
Заменяет стандартный QToolTip во всём приложении.
"""
from PyQt5.QtWidgets import QWidget, QApplication
from PyQt5.QtCore import Qt, QTimer, QRectF, QObject, QEvent
from PyQt5.QtGui import QPainter, QPen, QColor, QPainterPath, QFontMetrics


class BubbleToolTip(QWidget):
    """Tooltip-облачко с хвостиком и тенью"""
    _instance = None
    SHADOW = 6  # дополнительное пространство под тень

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = BubbleToolTip()
        return cls._instance

    def __init__(self):
        super().__init__(None, Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.NoFocus)

        self._text = ""
        self._arrow_size = 6
        self._pad_h = 8
        self._pad_v = 4
        self._radius = 6
        self._arrow_x = 0
        self._arrow_top = True
        self._body_w = 0
        self._body_h = 0

        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.setInterval(4000)
        self._hide_timer.timeout.connect(self.hide)

    def show_bubble(self, text, widget):
        if not text or not widget:
            self.hide()
            return

        self._text = text
        self._hide_timer.stop()

        # Гарантировать, что stylesheet применён (иначе при первом показе
        # font() вернёт системный шрифт, а не Manrope 13px из stylesheet,
        # и размер пузырька будет рассчитан неправильно)
        self.ensurePolished()
        fm = QFontMetrics(self.font())
        tw = fm.horizontalAdvance(text) + 2
        th = fm.height()

        s = self.SHADOW
        self._body_w = tw + self._pad_h * 2
        self._body_h = th + self._pad_v * 2 + self._arrow_size

        # Размер виджета = тело + тень со всех сторон
        w = self._body_w + s * 2
        h = self._body_h + s * 2
        self.setFixedSize(w, h)

        gcenter = widget.mapToGlobal(widget.rect().center())
        gbottom_y = widget.mapToGlobal(widget.rect().bottomLeft()).y()
        gtop_y = widget.mapToGlobal(widget.rect().topLeft()).y()

        x = gcenter.x() - w // 2
        y = gbottom_y + 2

        screen = QApplication.primaryScreen().availableGeometry()
        if x < screen.left():
            x = screen.left()
        if x + w > screen.right():
            x = screen.right() - w

        # Позиция стрелки относительно тела (без учёта тени)
        self._arrow_x = max(
            self._radius + self._arrow_size,
            min(gcenter.x() - x - s, self._body_w - self._radius - self._arrow_size))

        if y + h > screen.bottom():
            y = gtop_y - h - 2
            self._arrow_top = False
        else:
            self._arrow_top = True

        self.move(x, y)
        self.show()
        self.update()
        self._hide_timer.start()

    def _build_path(self):
        """Построить path облачка с хвостиком"""
        bw = self._body_w
        bh = self._body_h
        a = self._arrow_size
        r = self._radius
        ax = self._arrow_x

        path = QPainterPath()

        if self._arrow_top:
            bt = float(a)
            path.moveTo(r, bt)
            path.lineTo(ax - a, bt)
            path.lineTo(ax, 0)
            path.lineTo(ax + a, bt)
            path.lineTo(bw - r, bt)
            path.arcTo(bw - 2 * r, bt, 2 * r, 2 * r, 90, -90)
            path.lineTo(bw, bh - r)
            path.arcTo(bw - 2 * r, bh - 2 * r, 2 * r, 2 * r, 0, -90)
            path.lineTo(r, bh)
            path.arcTo(0, bh - 2 * r, 2 * r, 2 * r, -90, -90)
            path.lineTo(0, bt + r)
            path.arcTo(0, bt, 2 * r, 2 * r, 180, -90)
        else:
            bb = float(bh - a)
            path.moveTo(r, 0)
            path.lineTo(bw - r, 0)
            path.arcTo(bw - 2 * r, 0, 2 * r, 2 * r, 90, -90)
            path.lineTo(bw, bb - r)
            path.arcTo(bw - 2 * r, bb - 2 * r, 2 * r, 2 * r, 0, -90)
            path.lineTo(ax + a, bb)
            path.lineTo(ax, bh)
            path.lineTo(ax - a, bb)
            path.lineTo(r, bb)
            path.arcTo(0, bb - 2 * r, 2 * r, 2 * r, -90, -90)
            path.lineTo(0, r)
            path.arcTo(0, 0, 2 * r, 2 * r, 180, -90)

        path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        s = self.SHADOW
        path = self._build_path()

        # Сдвигаем всё на SHADOW px от краёв (место для тени)
        painter.translate(s, s)

        # Тень — несколько слоёв со смещением вниз
        for dy, alpha in [(4, 8), (3, 12), (2, 16), (1, 20)]:
            painter.save()
            painter.translate(0, dy)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(0, 0, 0, alpha))
            painter.drawPath(path)
            painter.restore()

        # Основное облачко
        painter.setPen(QPen(QColor('#d9d9d9'), 1))
        painter.setBrush(QColor('#ffffff'))
        painter.drawPath(path)

        # Текст
        a = self._arrow_size
        bw = self._body_w
        bh = self._body_h
        if self._arrow_top:
            text_rect = QRectF(0, a, bw, bh - a)
        else:
            text_rect = QRectF(0, 0, bw, bh - a)

        painter.setPen(QColor('#333333'))
        painter.drawText(text_rect, Qt.AlignCenter, self._text)

        painter.end()


class ToolTipFilter(QObject):
    """Глобальный фильтр — заменяет стандартные tooltip на облачко с хвостиком"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._target = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.ToolTip:
            if isinstance(obj, QWidget) and obj.toolTip():
                self._target = obj
                BubbleToolTip.instance().show_bubble(obj.toolTip(), obj)
                event.accept()
                return True
        elif event.type() == QEvent.Leave and obj is self._target:
            self._target = None
            BubbleToolTip.instance().hide()
        elif event.type() == QEvent.MouseButtonPress:
            if self._target is not None:
                self._target = None
                BubbleToolTip.instance().hide()
        return False
