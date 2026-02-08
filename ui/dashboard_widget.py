# -*- coding: utf-8 -*-
"""
Базовый класс для дашбордов с метриками
Поддерживает создание карточек статистики с фильтрами
"""

from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QGroupBox, QLabel, QPushButton, QMenu, QSizePolicy,
                             QToolTip)
from PyQt5.QtCore import Qt, pyqtSignal, QSize, QRectF
from PyQt5.QtGui import QFont, QIcon, QPixmap, QPainter, QColor
from PyQt5.QtSvg import QSvgWidget, QSvgRenderer
import os
from utils.resource_path import resource_path


def create_colored_icon(icon_path, color):
    """Создать цветную иконку из SVG"""
    full_path = resource_path(icon_path)
    if not os.path.exists(full_path):
        print(f"[WARN] Icon not found: {full_path}")
        return None

    # Читаем SVG и заменяем цвет
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()

        # Заменяем currentColor на нужный цвет
        svg_content = svg_content.replace('currentColor', color)

        # Заменяем stroke на нужный цвет
        svg_content = svg_content.replace('stroke="black"', f'stroke="{color}"')
        svg_content = svg_content.replace("stroke='black'", f"stroke='{color}'")
        svg_content = svg_content.replace('stroke="#000"', f'stroke="{color}"')
        svg_content = svg_content.replace('stroke="#000000"', f'stroke="{color}"')

        # Заменяем fill на нужный цвет
        svg_content = svg_content.replace('fill="black"', f'fill="{color}"')
        svg_content = svg_content.replace("fill='black'", f"fill='{color}'")
        svg_content = svg_content.replace('fill="#000"', f'fill="{color}"')
        svg_content = svg_content.replace('fill="#000000"', f'fill="{color}"')

        # Если нет явного указания stroke или fill, добавляем в svg тег
        if 'stroke=' not in svg_content.lower() and 'fill=' not in svg_content.lower():
            svg_content = svg_content.replace('<svg', f'<svg fill="{color}" stroke="{color}"')

        return svg_content.encode('utf-8')
    except Exception as e:
        print(f"[WARN] Error creating colored icon: {e}")
        import traceback
        traceback.print_exc()
        return None


class ColoredSvgWidget(QWidget):
    """SVG виджет с поддержкой цвета"""

    def __init__(self, icon_path, color, size=60, parent=None):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.color = color
        self.icon_path = icon_path
        self.svg_data = create_colored_icon(icon_path, color)

    def paintEvent(self, event):
        if self.svg_data:
            painter = QPainter(self)
            renderer = QSvgRenderer(self.svg_data)
            # Преобразуем QRect в QRectF для совместимости с PyQt5
            renderer.render(painter, QRectF(self.rect()))


class FilterButton(QPushButton):
    """Кнопка фильтра с выпадающим меню"""

    filter_changed = pyqtSignal(str)  # Сигнал при изменении фильтра

    def __init__(self, filter_type, options, border_color='#F57C00', parent=None):
        """
        Args:
            filter_type: Тип фильтра ('agent', 'year', 'month')
            options: Список опций для выбора
            border_color: Цвет рамки
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.filter_type = filter_type
        self.options = options
        self.current_value = None
        self.border_color = border_color

        # Настройка внешнего вида - размер кнопок фильтров
        self.setFixedSize(24, 24)  # Размер кнопок 24px
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.setCursor(Qt.PointingHandCursor)

        # Стиль белой кнопки с цветной рамкой
        # ВАЖНО: min/max-height/width переопределяют глобальный стиль из unified_styles.py
        # где QPushButton имеет min-height: 32px
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: #FFFFFF;
                color: {border_color};
                border: 2px solid {border_color};
                border-radius: 6px;
                padding: 1px;
                min-height: 24px;
                max-height: 24px;
                min-width: 24px;
                max-width: 24px;
            }}
            QPushButton:hover {{
                background-color: #F5F5F5;
            }}
            QPushButton:pressed {{
                background-color: #EEEEEE;
            }}
        """)

        # Устанавливаем иконку вместо текста
        self._set_icon()

        # Создаем меню
        self.menu = QMenu(self)
        self.menu.setStyleSheet("""
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 1px;
            }
            QMenu::item {
                padding: 8px 10px;
                border-radius: 0px;
            }
            QMenu::item:selected {
                background-color: #E3F2FD;
            }
        """)
        self.update_menu()

        # Подключаем клик
        self.clicked.connect(self.show_menu)

    def _set_icon(self):
        """Установить иконку в зависимости от типа фильтра"""
        icon_map = {
            'agent': 'resources/icons/user.svg',
            'year': 'resources/icons/calendar.svg',
            'month': 'resources/icons/clock.svg'
        }

        icon_path = icon_map.get(self.filter_type, 'resources/icons/settings.svg')
        full_path = resource_path(icon_path)

        if os.path.exists(full_path):
            # Создаем цветную иконку
            svg_data = create_colored_icon(icon_path, self.border_color)
            if svg_data:
                pixmap = QPixmap(18, 18)
                pixmap.fill(Qt.transparent)
                painter = QPainter(pixmap)
                renderer = QSvgRenderer(svg_data)
                renderer.render(painter)
                painter.end()
                self.setIcon(QIcon(pixmap))
                self.setIconSize(QSize(16, 16))  # Размер иконки внутри кнопки

    def update_menu(self):
        """Обновление меню с опциями"""
        self.menu.clear()

        for option in self.options:
            action = self.menu.addAction(str(option))
            action.triggered.connect(lambda checked, opt=option: self.select_option(opt))

    def show_menu(self):
        """Показать меню под кнопкой"""
        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.menu.exec_(pos)

    def select_option(self, option):
        """Выбор опции из меню"""
        self.current_value = option
        # Показываем tooltip с выбранным значением
        self.setToolTip(f"{self._get_filter_name()}: {option}")
        self.filter_changed.emit(str(option))

    def _get_filter_name(self):
        """Получить название фильтра"""
        names = {'agent': 'Агент', 'year': 'Год', 'month': 'Месяц'}
        return names.get(self.filter_type, 'Фильтр')

    def get_value(self):
        """Получить текущее значение фильтра"""
        return self.current_value

    def set_options(self, options):
        """Обновить список опций"""
        self.options = options
        self.update_menu()


class MetricCard(QGroupBox):
    """Карточка метрики с опциональными фильтрами"""

    def __init__(self, object_name, title, value, icon_path, bg_color, border_color,
                 filters=None, parent=None):
        """
        Args:
            object_name: Уникальное имя карточки
            title: Заголовок метрики
            value: Значение метрики
            icon_path: Путь к иконке
            bg_color: Цвет фона
            border_color: Цвет рамки
            filters: Список фильтров [{'type': 'agent', 'options': [...]}]
            parent: Родительский виджет
        """
        super().__init__(parent)
        self.setObjectName(object_name)
        self.border_color = border_color
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(95)  # Высота карточки для размещения 2 кнопок фильтров

        # Стиль карточки
        self.setStyleSheet(f"""
            QGroupBox {{
                background-color: {bg_color};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 0px;
            }}
            QGroupBox:hover {{
                border: 3px solid {border_color};
            }}
        """)

        # Основной горизонтальный layout - напрямую, без лишнего центрирования
        main_layout = QHBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(10, 6, 8, 6)

        # Иконка слева - ЦВЕТНАЯ (размер 36px как на скриншоте)
        icon_widget = ColoredSvgWidget(icon_path, border_color, size=36, parent=self)
        main_layout.addWidget(icon_widget, 0, Qt.AlignVCenter)

        # Текстовая часть
        data_layout = QVBoxLayout()
        data_layout.setSpacing(2)
        data_layout.setContentsMargins(0, 0, 0, 0)

        # Заголовок
        title_label = QLabel(title, self)
        title_label.setStyleSheet(f'''
            font-size: 10px;
            color: {border_color};
            font-weight: 600;
            background-color: transparent;
        ''')
        title_label.setWordWrap(True)
        data_layout.addWidget(title_label)

        # Значение - уменьшен шрифт с 30 до 22
        self.value_label = QLabel(value, self)
        self.value_label.setObjectName('value')
        self.value_label.setStyleSheet(f'''
            font-size: 22px;
            font-weight: bold;
            color: {border_color};
            background-color: transparent;
        ''')
        self.value_label.setWordWrap(False)
        data_layout.addWidget(self.value_label)

        # Метка выбранного фильтра - скрыта по умолчанию
        self.filter_label = QLabel('', self)
        self.filter_label.setStyleSheet(f'''
            font-size: 9px;
            color: #666666;
            background-color: transparent;
            font-style: italic;
        ''')
        self.filter_label.setVisible(False)  # Скрыта по умолчанию, показываем при выборе фильтра
        data_layout.addWidget(self.filter_label)

        # Добавляем текстовую часть с вертикальным центрированием
        data_widget = QWidget(self)
        data_widget.setStyleSheet("background: transparent;")
        data_widget.setLayout(data_layout)
        main_layout.addWidget(data_widget, 1, Qt.AlignVCenter)

        # Фильтры справа (если есть) - ВЕРТИКАЛЬНО
        if filters:
            # Создаём контейнер-виджет для фильтров
            filters_container = QWidget(self)
            filters_container.setStyleSheet("background: transparent;")
            filters_layout = QVBoxLayout(filters_container)
            filters_layout.setSpacing(4)  # Расстояние между кнопками фильтров
            filters_layout.setContentsMargins(4, 2, 4, 2)

            self.filter_buttons = {}
            for filter_config in filters:
                filter_btn = FilterButton(
                    filter_config['type'],
                    filter_config['options'],
                    border_color=border_color,
                    parent=self
                )
                # Подключаем обновление метки при выборе
                filter_btn.filter_changed.connect(
                    lambda val, ft=filter_config['type']: self._update_filter_label(ft, val)
                )
                filters_layout.addWidget(filter_btn, 0, Qt.AlignHCenter)
                self.filter_buttons[filter_config['type']] = filter_btn

            # Добавляем контейнер с фильтрами
            main_layout.addWidget(filters_container, 0, Qt.AlignVCenter)
        else:
            self.filter_buttons = {}

        self.setLayout(main_layout)

    def _update_filter_label(self, filter_type, value):
        """Обновить метку с выбранным фильтром"""
        # Собираем все выбранные фильтры
        labels = []
        for ft, btn in self.filter_buttons.items():
            val = btn.get_value()
            if val:
                if ft == 'year':
                    labels.append(f"Год: {val}")
                elif ft == 'month':
                    labels.append(f"Месяц: {val}")
                elif ft == 'agent':
                    labels.append(f"Агент: {val}")

        if labels:
            self.filter_label.setText(' | '.join(labels))
            self.filter_label.setVisible(True)  # Показываем только если выбран фильтр
        else:
            self.filter_label.setText('')
            self.filter_label.setVisible(False)  # Скрываем если фильтр сброшен

    def update_value(self, value):
        """Обновить значение метрики"""
        self.value_label.setText(str(value))

    def get_filter_value(self, filter_type):
        """Получить значение фильтра"""
        if filter_type in self.filter_buttons:
            return self.filter_buttons[filter_type].get_value()
        return None

    def connect_filter(self, filter_type, callback):
        """Подключить callback к изменению фильтра"""
        if filter_type in self.filter_buttons:
            self.filter_buttons[filter_type].filter_changed.connect(callback)


class DashboardWidget(QWidget):
    """Базовый класс для дашбордов"""

    def __init__(self, db_manager, api_client=None, parent=None):
        super().__init__(parent)
        self.db = db_manager
        self.api_client = api_client
        self.metric_cards = {}

        # Фиксированная высота дашборда - компактный вид
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setFixedHeight(105)  # Высота дашборда = высота карточки (95) + отступы (10)

        # Основной layout
        self.main_layout = QVBoxLayout()
        self.main_layout.setContentsMargins(10, 5, 10, 5)
        self.main_layout.setSpacing(5)

        # Grid для карточек
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(8)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)

        self.main_layout.addLayout(self.grid_layout)
        self.setLayout(self.main_layout)

        # Стиль контейнера
        self.setStyleSheet('background-color: #FAFAFA; padding: 2px;')

    def add_metric_card(self, row, col, object_name, title, value, icon_path,
                       bg_color='#ffffff', border_color='#F57C00', filters=None):
        """
        Добавить карточку метрики в grid

        Args:
            row: Строка в grid
            col: Колонка в grid
            object_name: Уникальное имя карточки
            title: Заголовок
            value: Значение
            icon_path: Путь к иконке
            bg_color: Цвет фона
            border_color: Цвет рамки
            filters: Список фильтров
        """
        card = MetricCard(
            object_name=object_name,
            title=title,
            value=value,
            icon_path=icon_path,
            bg_color=bg_color,
            border_color=border_color,
            filters=filters,
            parent=self
        )

        self.grid_layout.addWidget(card, row, col)
        self.metric_cards[object_name] = card

        return card

    def update_metric(self, object_name, value):
        """Обновить значение метрики"""
        if object_name in self.metric_cards:
            self.metric_cards[object_name].update_value(value)

    def get_metric_card(self, object_name):
        """Получить карточку метрики по имени"""
        return self.metric_cards.get(object_name)

    def set_column_stretch(self, columns=6):
        """Установить растяжение колонок"""
        for col in range(columns):
            self.grid_layout.setColumnStretch(col, 1)

    def load_data(self):
        """Загрузить данные (переопределяется в наследниках)"""
        pass  # Пустая реализация, переопределяется в наследниках

    def get_years(self):
        """Получить динамический список годов из договоров для фильтров

        Пытается получить список годов из API или локальной БД.
        Включает текущий год и следующий год.

        Returns:
            list: Список годов в обратном порядке (от нового к старому)
        """
        from datetime import datetime

        try:
            # Сначала пробуем API
            if self.api_client:
                try:
                    years = self.api_client.get_contract_years()
                    if years:
                        return years
                except Exception as e:
                    print(f"[WARN] Ошибка получения годов через API: {e}")

            # Затем локальная БД
            if self.db:
                try:
                    years = self.db.get_contract_years()
                    if years:
                        return years
                except Exception as e:
                    print(f"[WARN] Ошибка получения годов из БД: {e}")

        except Exception as e:
            print(f"[ERROR] Ошибка получения годов: {e}")

        # Fallback: 10 лет назад до следующего года
        current_year = datetime.now().year
        return list(range(current_year + 1, current_year - 10, -1))

    def refresh(self):
        """Обновить данные дашборда"""
        try:
            self.load_data()
        except Exception as e:
            print(f"[ERROR] Ошибка обновления дашборда: {e}")
            import traceback
            traceback.print_exc()
