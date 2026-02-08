# -*- coding: utf-8 -*-
"""
Вспомогательные функции и классы для работы с календарем
"""
from PyQt5.QtWidgets import QDateEdit, QPushButton, QVBoxLayout, QWidget, QCalendarWidget
from PyQt5.QtCore import QDate, Qt
from utils.resource_path import resource_path

# ========== ОПРЕДЕЛЯЕМ ПУТЬ К ИКОНКАМ ==========
ICONS_PATH = resource_path('resources/icons').replace('\\', '/')

# ========== CALENDAR_STYLE (для обратной совместимости) ==========
# Все стили календаря теперь в unified_styles.py
# Эта переменная оставлена пустой для совместимости со старым кодом
CALENDAR_STYLE = ""


class CustomCalendarWidget(QCalendarWidget):
    """Кастомный календарь с кнопкой 'Сегодня' внизу"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.today_button = None
        self.button_container = None
        # Увеличиваем минимальную высоту для размещения всех чисел + кнопки
        self.setMinimumHeight(340)

    def showEvent(self, event):
        """Добавляем кнопку при первом показе календаря"""
        super().showEvent(event)

        if self.today_button is None:
            self.setup_today_button()

    def setup_today_button(self):
        """Добавление кнопки 'Сегодня' внизу календаря"""
        # Создаем контейнер для кнопки
        self.button_container = QWidget(self)
        self.button_container.setStyleSheet("""
            QWidget {
                background-color: #F8F9FA;
                border-top: 1px solid #E0E0E0;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
            }
        """)

        button_layout = QVBoxLayout(self.button_container)
        button_layout.setContentsMargins(8, 6, 8, 6)
        button_layout.setSpacing(0)

        # Создаем кнопку "Сегодня"
        self.today_button = QPushButton('Сегодня', self.button_container)
        self.today_button.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #000000;
                border: none;
                border-radius: 6px;
                padding: 4px 16px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #ffdb4d;
            }
            QPushButton:pressed {
                background-color: #e6c236;
            }
        """)
        self.today_button.clicked.connect(self.go_to_today)
        button_layout.addWidget(self.today_button)

        # Позиционируем контейнер внизу календаря
        self.position_button_container()

    def position_button_container(self):
        """Позиционируем контейнер с кнопкой внизу календаря"""
        if self.button_container:
            # Получаем размеры календаря
            calendar_height = self.height()
            calendar_width = self.width()
            button_height = 50

            # Размещаем контейнер внизу
            self.button_container.setGeometry(0, calendar_height - button_height, calendar_width, button_height)
            self.button_container.raise_()
            self.button_container.show()

    def resizeEvent(self, event):
        """Обновляем позицию кнопки при изменении размера"""
        super().resizeEvent(event)
        self.position_button_container()

    def go_to_today(self):
        """Переход на сегодняшнюю дату"""
        today = QDate.currentDate()
        self.setSelectedDate(today)
        self.setCurrentPage(today.year(), today.month())


def add_today_button_to_dateedit(date_edit):
    """
    Добавляет кастомный календарь с кнопкой 'Сегодня' внизу к QDateEdit

    Использование:
        date_edit = QDateEdit()
        date_edit.setCalendarPopup(True)
        add_today_button_to_dateedit(date_edit)
    """
    custom_calendar = CustomCalendarWidget(date_edit)
    date_edit.setCalendarWidget(custom_calendar)
    return custom_calendar
