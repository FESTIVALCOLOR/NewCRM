# -*- coding: utf-8 -*-
import os
import sys
from PyQt5.QtWidgets import QDateEdit, QPushButton, QVBoxLayout, QWidget, QCalendarWidget
from PyQt5.QtCore import QDate, Qt
from utils.resource_path import resource_path

# ========== ОПРЕДЕЛЯЕМ ПУТЬ К ИКОНКАМ ==========
ICONS_PATH = resource_path('resources/icons').replace('\\', '/')

print(f"[CALENDAR_STYLES] Путь к иконкам: {ICONS_PATH}")
# ================================================

CALENDAR_STYLE = f"""
/* ========== QDateEdit (ЗАКРЫТ) ========== */
QDateEdit {{
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px 8px;
    font-size: 12px;
    color: #333333;
    min-height: 28px;
}}

QDateEdit:hover {{
    border-color: #3498DB;
    background-color: #F8FBFF;
}}

QDateEdit:focus {{
    border-color: #3498DB;
    background-color: #FFFFFF;
}}

QDateEdit:disabled {{
    background-color: #F5F5F5;
    color: #999999;
}}

/* ========== QDateEdit (ОТКРЫТ) - убираем нижние радиусы ========== */
QDateEdit:on {{
    border-color: #3498DB; 
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    border-bottom: 1px solid #3498DB;  /* ← ИЗМЕНЕНО: оставляем границу */
}}
/* ================================================================== */

/* Кнопка календаря */
QDateEdit::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: right center;
    width: 25px;
    border: none;
    background-color: transparent;
    border-top-right-radius: 4px;
    border-bottom-right-radius: 4px;
}}

/* ========== ИСПРАВЛЕНИЕ: При открытом календаре ========== */
QDateEdit:on::drop-down {{
    border-bottom-right-radius: 4px;
    border-top-right-radius: 4px;
    
}}

QDateEdit:on::drop-down:hover {{
    border-bottom-right-radius: 3px;
    border-top-right-radius: 3px;
    margin: 1px;
    margin-bottom: 0px;
}}
/* ========================================================== */

QDateEdit::drop-down:hover {{
    background-color: #E8F4F8;
    border-top-right-radius: 3px;     /* ← УМЕНЬШЕНО */
    border-bottom-right-radius: 3px;  /* ← УМЕНЬШЕНО */
    margin: 1px;                      /* ← ДОБАВЛЕНО */
}}

QDateEdit::drop-down:pressed {{
    background-color: #D4E9F7;
    border-top-right-radius: 3px;
    border-bottom-right-radius: 3px;
    margin: 1px;
}}

QDateEdit::down-arrow {{
    image: url({ICONS_PATH}/arrow-down-circle.svg);
    width: 16px;
    height: 16px;
}}

/* ========== КАЛЕНДАРЬ ========== */
QCalendarWidget {{
    background-color: #FFFFFF;
    border: 1px solid #3498DB;  /* ← ИЗМЕНЕНО: синяя рамка для связи с полем */
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    border-bottom-left-radius: 4px;
    border-bottom-right-radius: 4px;
    margin-top: 1px;  /* ← ДОБАВЛЕНО: подтягиваем вплотную */  
}}

/* Навигационная панель */
QCalendarWidget QWidget#qt_calendar_navigationbar {{
    background-color: #F8F9FA;
    border-bottom: 1px solid #E0E0E0;
    border-top-left-radius: 4px;  
    border-top-right-radius: 4px; 
    min-height: 40px;
}}

/* Кнопки навигации */
QCalendarWidget QToolButton {{
    background-color: transparent;
    color: #333333;
    border: none;
    border-radius: 4px;
    padding: 5px;
    margin: 0px;
    min-width: 30px;
    min-height: 30px;
}}

QCalendarWidget QToolButton:hover {{
    background-color: #E8F4F8;
}}

QCalendarWidget QToolButton:pressed {{
    background-color: #D4E9F7;
}}

QCalendarWidget QToolButton#qt_calendar_prevmonth {{
    qproperty-icon: url({ICONS_PATH}/arrow-left-circle.svg);
    qproperty-iconSize: 20px;
}}

QCalendarWidget QToolButton#qt_calendar_nextmonth {{
    qproperty-icon: url({ICONS_PATH}/arrow-right-circle.svg);
    qproperty-iconSize: 20px;
}}

QCalendarWidget QToolButton::menu-indicator {{
    image: none;
}}

/* Меню выбора месяца/года */
QCalendarWidget QMenu {{
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 0px;
    padding: 2px;
}}

QCalendarWidget QMenu::item {{
    padding: 5px 20px;
    color: #333333;
}}

QCalendarWidget QMenu::item:selected {{
    background-color: #E8F4F8;
    color: #3498DB;
}}

QCalendarWidget QSpinBox {{
    background-color: #FFFFFF;
    border: 1px solid #CCCCCC;
    border-radius: 0px;
    padding: 2px;
    color: #333333;
    font-size: 12px;
    font-weight: bold;
}}

QCalendarWidget QSpinBox:hover {{
    border-color: #3498DB;
}}

QCalendarWidget QSpinBox::up-button,
QCalendarWidget QSpinBox::down-button {{
    background-color: #F8F9FA;
    border: none;
    width: 16px;
}}

QCalendarWidget QSpinBox::up-button:hover,
QCalendarWidget QSpinBox::down-button:hover {{
    background-color: #E8F4F8;
}}

QCalendarWidget QSpinBox::up-arrow {{
    image: url({ICONS_PATH}/arrow-up-circle.svg);
    width: 12px;
    height: 12px;
}}

QCalendarWidget QSpinBox::down-arrow {{
    image: url({ICONS_PATH}/arrow-down-circle.svg);
    width: 12px;
    height: 12px;
}}

/* Таблица календаря */
QCalendarWidget QTableView {{
    background-color: #FFFFFF;
    gridline-color: #F0F0F0;
    outline: none;
}}

/* Заголовок (дни недели) */
QCalendarWidget QHeaderView::section {{
    background-color: #F8F9FA;
    color: #666666;
    font-weight: bold;
    font-size: 10px;
    padding: 5px;
    border: none;
}}

/* Ячейки календаря */
QCalendarWidget QTableView::item {{
    padding: 8px;
    color: #333333;
}}

QCalendarWidget QTableView::item:hover {{
    background-color: #E8F4F8;
    color: #333333;
    border-radius: 4px;
}}

QCalendarWidget QTableView::item:selected {{
    background-color: #3498DB;
    color: #FFFFFF;
    font-weight: bold;
    border-radius: 4px;
}}

QCalendarWidget QTableView::item:focus {{
    background-color: #3498DB;
    color: #FFFFFF;
    border: 2px solid #2980B9;
    border-radius: 4px;
}}

QCalendarWidget QTableView::item:disabled {{
    color: #CCCCCC;
    background-color: transparent;
}}
"""


class CustomCalendarWidget(QCalendarWidget):
    """Кастомный календарь с кнопкой 'Сегодня' внизу"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.today_button = None
        self.button_container = None
        # ИСПРАВЛЕНИЕ: Увеличиваем минимальную высоту для размещения всех чисел + кнопки
        self.setMinimumHeight(300)

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
            }
        """)

        button_layout = QVBoxLayout(self.button_container)
        button_layout.setContentsMargins(8, 6, 8, 6)
        button_layout.setSpacing(0)

        # Создаем кнопку "Сегодня"
        self.today_button = QPushButton('Сегодня', self.button_container)
        self.today_button.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #21618C;
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
            button_height = 40

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

