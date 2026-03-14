# -*- coding: utf-8 -*-
"""
Вспомогательные функции и классы для работы с календарем
"""
from datetime import datetime, timedelta
from PyQt5.QtWidgets import QDateEdit, QPushButton, QVBoxLayout, QWidget, QCalendarWidget
from PyQt5.QtCore import QDate, Qt, QRectF
from PyQt5.QtGui import QPalette, QColor, QPainter, QFont
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
        # Принудительно белый фон для popup календаря
        self.setAutoFillBackground(True)
        pal = self.palette()
        pal.setColor(QPalette.Window, QColor('#ffffff'))
        pal.setColor(QPalette.Base, QColor('#ffffff'))
        self.setPalette(pal)

    def showEvent(self, event):
        """Добавляем кнопку при первом показе календаря"""
        super().showEvent(event)

        # Пропускаем инициализацию если окно ещё не видимо пользователю
        # (setCalendarWidget вызывает showEvent во время конструирования диалога)
        if not self.window().isVisible():
            return

        # Всегда открываем на текущем месяце/годе
        today = QDate.currentDate()
        self.setCurrentPage(today.year(), today.month())

        if self.today_button is None:
            self.setup_today_button()
        elif self.button_container:
            self.position_button_container()

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

    def paintCell(self, painter, rect, date):
        """Кастомная отрисовка ячеек — красный круг для выбранной даты"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing, True)

        is_selected = (date == self.selectedDate())
        is_current_month = (date.month() == self.monthShown()
                            and date.year() == self.yearShown())
        is_weekend = date.dayOfWeek() in (6, 7)

        # Белый фон ячейки
        painter.fillRect(rect, QColor('#ffffff'))

        if is_selected:
            # Красный круг
            size = min(rect.width(), rect.height()) - 6
            cx = rect.center().x()
            cy = rect.center().y()
            circle = QRectF(cx - size / 2, cy - size / 2, size, size)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor('#E74C3C'))
            painter.drawEllipse(circle)
            # Белый жирный текст
            painter.setPen(QColor('#FFFFFF'))
            font = painter.font()
            font.setBold(True)
            painter.setFont(font)
        else:
            font = painter.font()
            font.setBold(False)
            painter.setFont(font)
            if is_current_month:
                if is_weekend:
                    painter.setPen(QColor('#E74C3C'))
                else:
                    painter.setPen(QColor('#333333'))
            else:
                painter.setPen(QColor('#c0c0c0'))

        painter.drawText(rect, Qt.AlignCenter, str(date.day()))
        painter.restore()

    def go_to_today(self):
        """Переход на сегодняшнюю дату"""
        today = QDate.currentDate()
        self.setSelectedDate(today)
        self.setCurrentPage(today.year(), today.month())


def add_working_days(start_date_str, working_days):
    """Добавляет рабочие дни (с учётом праздников РФ) к дате.
    start_date_str: 'YYYY-MM-DD'
    working_days: int
    Возвращает: 'YYYY-MM-DD'
    """
    if not start_date_str or working_days <= 0:
        return start_date_str or ''
    try:
        current = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return start_date_str or ''
    from utils.date_utils import is_working_day
    added = 0
    while added < working_days:
        current += timedelta(days=1)
        if is_working_day(current):
            added += 1
    return current.strftime('%Y-%m-%d')


def working_days_between(start_date_str, end_date_str):
    """Подсчитывает количество рабочих дней (Пн-Пт) между двумя датами.
    start_date_str, end_date_str: 'YYYY-MM-DD'
    Возвращает: int (количество рабочих дней, не считая start, считая end)
    """
    if not start_date_str or not end_date_str:
        return 0
    try:
        start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return 0
    if end <= start:
        return 0
    from utils.date_utils import is_working_day
    count = 0
    current = start
    while current < end:
        current += timedelta(days=1)
        if is_working_day(current):
            count += 1
    return count


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
