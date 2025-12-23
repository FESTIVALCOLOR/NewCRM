# -*- coding: utf-8 -*-
"""
Custom ComboBox - QComboBox с отключенным изменением значения при прокрутке колесиком мыши
"""
from PyQt5.QtWidgets import QComboBox
from PyQt5.QtCore import Qt
from utils.resource_path import resource_path
import os


class CustomComboBox(QComboBox):
    """
    Кастомный ComboBox, который не меняет значение при прокрутке колесиком мыши,
    если не находится в фокусе
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFocusPolicy(Qt.StrongFocus)

        # Формируем путь к иконке arrow-down-circle.svg (как в calendar_styles.py)
        icons_path = resource_path('resources/icons').replace('\\', '/')
        arrow_icon_path = f"{icons_path}/arrow-down-circle.svg"

        # Устанавливаем стиль с иконкой через url() (работает в dev и exe с resource_path)
        self.setStyleSheet(f"""
            QComboBox::drop-down {{
                border: none;
                width: 24px;
            }}
            QComboBox::down-arrow {{
                image: url({arrow_icon_path});
                width: 14px;
                height: 14px;
            }}
        """)

    def wheelEvent(self, event):
        """
        Переопределяем обработку события колесика мыши.
        Изменение значения происходит только если ComboBox в фокусе.
        """
        if self.hasFocus():
            # Если ComboBox в фокусе, работает как обычно
            super().wheelEvent(event)
        else:
            # Если не в фокусе, игнорируем событие и передаем его родителю (для прокрутки страницы)
            event.ignore()

    def focusInEvent(self, event):
        """Визуальная обратная связь при получении фокуса"""
        super().focusInEvent(event)

    def focusOutEvent(self, event):
        """Визуальная обратная связь при потере фокуса"""
        super().focusOutEvent(event)
