# -*- coding: utf-8 -*-
"""
Кастомный стиль для переопределения цветов tooltip
"""
from PyQt5.QtWidgets import QProxyStyle, QToolTip
from PyQt5.QtGui import QPalette, QColor
from PyQt5.QtCore import Qt, QObject, QEvent


class CustomProxyStyle(QProxyStyle):
    """Прокси-стиль для принудительного переопределения цветов tooltip"""

    def __init__(self, base_style):
        super().__init__(base_style)

    def standardPalette(self):
        """Переопределяем стандартную палитру"""
        palette = super().standardPalette()
        # Устанавливаем светло-серый фон для tooltip
        palette.setColor(QPalette.ToolTipBase, QColor(245, 245, 245))
        palette.setColor(QPalette.ToolTipText, QColor(51, 51, 51))
        return palette


class TooltipProxyStyle(QProxyStyle):
    """Прокси-стиль ТОЛЬКО для tooltip виджетов"""

    def drawPrimitive(self, element, option, painter, widget=None):
        """Переопределяем отрисовку примитивов для tooltip"""
        if widget and hasattr(widget, 'windowFlags') and widget.windowFlags() & Qt.ToolTip:
            # Для tooltip используем светлый фон
            if element == QProxyStyle.PE_PanelTipLabel:
                painter.fillRect(option.rect, QColor(245, 245, 245))
                return
        super().drawPrimitive(element, option, painter, widget)


class TooltipEventFilter(QObject):
    """Фильтр событий для принудительного применения стилей к tooltip"""

    def __init__(self):
        super().__init__()
        self.tooltip_count = 0
        self.tooltip_style = None

    def eventFilter(self, obj, event):
        """Перехватываем события показа tooltip"""
        if event.type() == QEvent.ToolTip:
            # Когда событие ToolTip происходит, применяем стили
            from PyQt5.QtWidgets import QApplication
            from PyQt5.QtCore import QTimer

            def apply_styles_to_tooltip():
                """Применяем стили к tooltip виджету"""
                app = QApplication.instance()
                if not app:
                    return

                for widget in app.topLevelWidgets():
                    if hasattr(widget, 'windowFlags') and widget.windowFlags() & Qt.ToolTip:
                        # Применяем stylesheet ТОЛЬКО к tooltip виджету
                        # Используем очень специфичный селектор чтобы не влиять на остальное
                        widget.setStyleSheet("""
                            QWidget {
                                background-color: rgb(245, 245, 245);
                                color: rgb(51, 51, 51);
                                border: 1px solid rgb(204, 204, 204);
                                border-radius: 4px;
                                padding: 5px;
                                font-size: 12px;
                            }
                        """)
                        break

            # Применяем стили с небольшой задержкой
            QTimer.singleShot(0, apply_styles_to_tooltip)

        return super().eventFilter(obj, event)


# Сохраняем оригинальную функцию showText
_original_showText = QToolTip.showText


def apply_tooltip_styles():
    """Функция для применения стилей к tooltip с небольшой задержкой"""
    from PyQt5.QtWidgets import QApplication
    for top_widget in QApplication.topLevelWidgets():
        if top_widget.windowFlags() & Qt.ToolTip and top_widget.isVisible():
            # Применяем стили напрямую к виджету
            top_widget.setStyleSheet("""
                background-color: rgb(245, 245, 245);
                color: rgb(51, 51, 51);
                border: 1px solid rgb(204, 204, 204);
                border-radius: 4px;
                padding: 5px;
                font-size: 12px;
            """)
            break


def custom_showText(pos, text, widget=None, rect=None):
    """Переопределенная функция showText с принудительной установкой стилей"""
    # Вызываем оригинальную функцию
    if rect is not None:
        _original_showText(pos, text, widget, rect)
    elif widget is not None:
        _original_showText(pos, text, widget)
    else:
        _original_showText(pos, text)

    # Применяем стили с небольшой задержкой
    from PyQt5.QtCore import QTimer
    QTimer.singleShot(0, apply_tooltip_styles)
    QTimer.singleShot(10, apply_tooltip_styles)


def install_tooltip_patch():
    """Устанавливаем патч для QToolTip.showText"""
    QToolTip.showText = custom_showText
