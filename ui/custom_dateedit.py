# -*- coding: utf-8 -*-
"""
Кастомный QDateEdit с блокировкой колеса мыши
"""
from PyQt5.QtWidgets import QDateEdit

from PyQt5.QtCore import Qt


class CustomDateEdit(QDateEdit):
    """
    QDateEdit с блокировкой прокрутки колесом мыши если календарь не открыт.
    Аналогично CustomComboBox - предотвращает случайное изменение даты.
    """

    def wheelEvent(self, event):
        """Обработка события колеса мыши"""
        # Разрешаем прокрутку только если календарь открыт
        if self.calendarWidget() and self.calendarWidget().isVisible():
            # Если календарь открыт - разрешаем прокрутку
            super().wheelEvent(event)
        else:
            # Если календарь закрыт - игнорируем событие
            event.ignore()
