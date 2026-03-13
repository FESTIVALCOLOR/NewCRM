from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QDateEdit,
                             QListWidget, QListWidgetItem, QTabWidget, QTextEdit,
                             QTableWidget, QHeaderView, QTableWidgetItem, QGroupBox,
                             QSpinBox, QFileDialog)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QMimeData, QDate, pyqtSignal, QSize, QUrl, QTimer
from PyQt5.QtGui import QDrag, QColor
from database.db_manager import DatabaseManager
from utils.icon_loader import IconLoader  # ← НОВОЕ
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit, ICONS_PATH
from utils.resource_path import resource_path
from utils.table_settings import ProportionalResizeTable, apply_no_focus_delegate, TableSettings
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
from utils.dialog_helpers import create_progress_dialog
from utils.data_access import DataAccess
from utils.button_debounce import debounce_click
from ui.base_kanban_tab import BaseDraggableList, BaseKanbanColumn
from utils.permissions import _has_perm
import os
import threading

# Маппинг названия стадии надзора -> stage_code (для связи файлов с timeline)
SUPERVISION_STAGE_MAPPING = {
    'Стадия 1: Закупка керамогранита': 'STAGE_1_CERAMIC',
    'Стадия 2: Закупка сантехники': 'STAGE_2_PLUMBING',
    'Стадия 3: Закупка оборудования': 'STAGE_3_EQUIPMENT',
    'Стадия 4: Закупка дверей и окон': 'STAGE_4_DOORS',
    'Стадия 5: Закупка настенных материалов': 'STAGE_5_WALL',
    'Стадия 6: Закупка напольных материалов': 'STAGE_6_FLOOR',
    'Стадия 7: Лепной декор': 'STAGE_7_STUCCO',
    'Стадия 8: Освещение': 'STAGE_8_LIGHTING',
    'Стадия 9: Бытовая техника': 'STAGE_9_APPLIANCES',
    'Стадия 10: Закупка заказной мебели': 'STAGE_10_CUSTOM_FURNITURE',
    'Стадия 11: Закупка фабричной мебели': 'STAGE_11_FACTORY_FURNITURE',
    'Стадия 12: Закупка декора': 'STAGE_12_DECOR',
}

class SupervisionDraggableList(BaseDraggableList):
    """Draggable список для надзора.
    __init__ и startDrag наследуются из BaseDraggableList."""

    def dropEvent(self, event):
        if not self.can_drag:
            event.ignore()
            return
        
        source = event.source()
        
        if not isinstance(source, SupervisionDraggableList):
            event.ignore()
            return
        
        item = source.currentItem()
        if not item:
            event.ignore()
            return
        
        card_id = item.data(Qt.UserRole)
        source_column = source.parent_column
        target_column = self.parent_column
        
        if source_column == target_column:
            super().dropEvent(event)
            event.accept()
            return
        
        source_column.card_moved.emit(card_id, source_column.column_name, target_column.column_name)
        event.accept()

class CRMSupervisionTab(QWidget):
    """Вкладка CRM Авторского надзора"""

    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db

        # Инициализация Yandex Disk
        try:
            self.yandex_disk = YandexDiskManager(YANDEX_DISK_TOKEN)
        except Exception as e:
            print(f"[WARNING] Не удалось инициализировать Yandex Disk: {e}")
            self.yandex_disk = None

        # Определяем права через permissions вместо хардкода роли
        self.is_dan_role = not _has_perm(employee, api_client, 'supervision.move')

        self._data_loaded = False
        self._loading_guard = False
        self.init_ui()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(0, 5, 0, 5)
        
        # Заголовок и кнопка статистики
        header_layout = QHBoxLayout()
        header = QLabel('CRM - Авторский надзор')
        header.setStyleSheet('font-size: 13px; font-weight: bold; color: #333333;')
        header_layout.addWidget(header)
        header_layout.addStretch(1)

        refresh_btn = IconLoader.create_action_button('refresh', 'Обновить данные с сервера')
        refresh_btn.clicked.connect(self.refresh_current_tab)
        header_layout.addWidget(refresh_btn)

        if not self.is_dan_role:
            stats_btn = IconLoader.create_action_button('stats', 'Показать статистику надзора')
            stats_btn.clicked.connect(self.show_statistics)
            header_layout.addWidget(stats_btn)
        
        main_layout.addLayout(header_layout)
        
        # Вкладки: Активные / Архив
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabBar::tab {
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #d9d9d9;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background-color: #E8E8E8;                
                min-width: 180px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid #d9d9d9;
            }
            QTabBar::tab:hover {
                background-color: #F0F0F0;
            }
        """)
        
        # Активные проекты
        self.active_widget = self.create_supervision_board()
        self.tabs.addTab(self.active_widget, 'Активные проекты (0)')
        
        # Архив (только для менеджеров)
        if not self.is_dan_role:
            self.archive_widget = self.create_archive_board()
            self.tabs.addTab(self.archive_widget, 'Архив (0)')
        
        self.tabs.currentChanged.connect(self.on_tab_changed)
        
        main_layout.addWidget(self.tabs, 1)
        self.setLayout(main_layout)
    
    def create_supervision_board(self):
        """Создание доски надзора"""
        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        columns_widget = QWidget()
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(10)
        columns_layout.setContentsMargins(0, 5, 0, 0)
        
        # Колонки
        columns = [
            'Новый заказ',
            'В ожидании',
            'Стадия 1: Закупка керамогранита',
            'Стадия 2: Закупка сантехники',
            'Стадия 3: Закупка оборудования',
            'Стадия 4: Закупка дверей и окон',
            'Стадия 5: Закупка настенных материалов',
            'Стадия 6: Закупка напольных материалов',
            'Стадия 7: Лепной декор',
            'Стадия 8: Освещение',
            'Стадия 9: Бытовая техника',
            'Стадия 10: Закупка заказной мебели',
            'Стадия 11: Закупка фабричной мебели',
            'Стадия 12: Закупка декора',
            'Выполненный проект'
        ]
        
        columns_dict = {}
        
        for column_name in columns:
            column = SupervisionColumn(column_name, self.employee, self.db, self.api_client)
            column.card_moved.connect(self.on_card_moved)
            columns_dict[column_name] = column
            columns_layout.addWidget(column)

        # ИСПРАВЛЕНИЕ 07.02.2026: Выравнивание по левому краю при сворачивании (#19)
        columns_layout.addStretch()

        widget.columns = columns_dict

        columns_widget.setLayout(columns_layout)
        scroll.setWidget(columns_widget)
        
        main_layout.addWidget(scroll, 1)
        widget.setLayout(main_layout)
        
        return widget
    
    def create_archive_board(self):
        """Создание архивной доски"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 5, 0, 10)
        layout.setSpacing(10)

        archive_header = QLabel('Архив проектов авторского надзора')
        archive_header.setStyleSheet("""
            font-size: 13px;
            font-weight: bold;
            padding: 8px;
            background-color: #F0F0F0;
            border-radius: 4px;
        """)
        layout.addWidget(archive_header)

        # ========== ФИЛЬТРЫ ==========
        filters_group = QGroupBox('Фильтры')
        filters_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
        """)
        filters_layout = QVBoxLayout()

        # Кнопка свернуть/развернуть
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 5)

        toggle_btn = IconLoader.create_icon_button('arrow-down-circle', '', 'Развернуть фильтры', icon_size=12)
        toggle_btn.setFixedSize(20, 20)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #f5f5f5;
                border-radius: 12px;
            }
        """)
        header_row.addWidget(toggle_btn)
        header_row.addStretch()
        filters_layout.addLayout(header_row)

        # Контейнер для фильтров (который можно сворачивать)
        filters_content = QWidget()
        filters_content_layout = QVBoxLayout(filters_content)
        filters_content_layout.setContentsMargins(0, 0, 0, 0)
        filters_content_layout.setSpacing(8)
        filters_content.hide()  # По умолчанию свернуто

        # Одна строка: Период, Адрес, Город, Агент
        main_row = QHBoxLayout()
        main_row.setSpacing(8)

        # Период
        main_row.addWidget(QLabel('Период:'))
        period_combo = CustomComboBox()
        period_combo.addItems(['Все время', 'Год', 'Квартал', 'Месяц'])
        period_combo.setMinimumWidth(100)
        main_row.addWidget(period_combo)

        year_spin = QSpinBox()
        year_spin.setRange(2020, 2100)
        year_spin.setValue(QDate.currentDate().year())
        year_spin.setPrefix('Год: ')
        year_spin.setMinimumWidth(80)
        year_spin.setFixedHeight(42)
        year_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding-left: 8px;
                padding-right: 8px;
                color: #333333;
                font-size: 12px;
            }}
            QSpinBox:hover {{
                border-color: #ffd93c;
            }}
            QSpinBox::up-button,
            QSpinBox::down-button {{
                background-color: #F8F9FA;
                border: none;
                width: 20px;
                border-radius: 4px;
            }}
            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover {{
                background-color: #f5f5f5;
            }}
            QSpinBox::up-arrow {{
                image: url({ICONS_PATH}/arrow-up-circle.svg);
                width: 14px;
                height: 14px;
            }}
            QSpinBox::down-arrow {{
                image: url({ICONS_PATH}/arrow-down-circle.svg);
                width: 14px;
                height: 14px;
            }}
        """)
        main_row.addWidget(year_spin)
        year_spin.hide()

        quarter_combo = CustomComboBox()
        quarter_combo.addItems(['Q1', 'Q2', 'Q3', 'Q4'])
        quarter_combo.setCurrentIndex((QDate.currentDate().month() - 1) // 3)
        quarter_combo.setMinimumWidth(60)
        main_row.addWidget(quarter_combo)
        quarter_combo.hide()

        month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_combo.addItems(months)
        month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        month_combo.setMinimumWidth(100)
        main_row.addWidget(month_combo)
        month_combo.hide()

        # Критерий даты
        main_row.addWidget(QLabel('Критерий:'))
        date_criterion_combo = CustomComboBox()
        date_criterion_combo.addItems(['Дата создания', 'Дата закрытия'])
        date_criterion_combo.setMinimumWidth(120)
        date_criterion_combo.setVisible(False)  # Показываем только когда выбран период
        main_row.addWidget(date_criterion_combo)

        # Адрес
        main_row.addWidget(QLabel('Адрес:'))
        address_input = QLineEdit()
        address_input.setPlaceholderText('Адрес...')
        address_input.setMinimumWidth(150)
        main_row.addWidget(address_input)

        # Город
        main_row.addWidget(QLabel('Город:'))
        city_combo = CustomComboBox()
        city_combo.addItem('Все', None)
        city_combo.setMinimumWidth(100)
        main_row.addWidget(city_combo)

        # Агент
        main_row.addWidget(QLabel('Агент:'))
        agent_combo = CustomComboBox()
        agent_combo.addItem('Все', None)
        agent_combo.setMinimumWidth(120)
        main_row.addWidget(agent_combo)

        main_row.addStretch()
        filters_content_layout.addLayout(main_row)

        # Кнопки: Применить и Сбросить
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        apply_btn = IconLoader.create_icon_button('check-square', 'Применить фильтры', icon_size=12)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        buttons_layout.addWidget(apply_btn)

        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить фильтры', icon_size=12)
        reset_btn.setStyleSheet("""
            QPushButton {
                padding: 8px 16px;
                font-weight: 500;
                color: #333;
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FFF3E0;
                border-color: #FF9800;
            }
        """)
        buttons_layout.addWidget(reset_btn)

        filters_content_layout.addLayout(buttons_layout)

        # Добавляем контейнер фильтров в основной layout
        filters_layout.addWidget(filters_content)

        filters_group.setLayout(filters_layout)
        layout.addWidget(filters_group)

        # Обработчик изменения периода
        def on_period_changed(period):
            year_spin.setVisible(period in ['Год', 'Квартал', 'Месяц'])
            quarter_combo.setVisible(period == 'Квартал')
            month_combo.setVisible(period == 'Месяц')
            date_criterion_combo.setVisible(period != 'Все время')

        period_combo.currentTextChanged.connect(on_period_changed)

        # Обработчик применения фильтров
        def apply_filters():
            self.apply_archive_filters()

        apply_btn.clicked.connect(apply_filters)

        # ИСПРАВЛЕНИЕ 07.02.2026: Автоприменение фильтров при изменении (НОВОЕ 3)
        # Все фильтры автоматически применяются при изменении значения
        period_combo.currentTextChanged.connect(apply_filters)
        year_spin.valueChanged.connect(apply_filters)
        quarter_combo.currentIndexChanged.connect(apply_filters)
        month_combo.currentIndexChanged.connect(apply_filters)
        date_criterion_combo.currentIndexChanged.connect(apply_filters)
        city_combo.currentIndexChanged.connect(apply_filters)
        agent_combo.currentIndexChanged.connect(apply_filters)
        address_input.textChanged.connect(apply_filters)

        # Обработчик сброса фильтров
        def reset_filters():
            period_combo.setCurrentText('Все время')
            address_input.clear()
            city_combo.setCurrentIndex(0)
            agent_combo.setCurrentIndex(0)
            self.apply_archive_filters()

        reset_btn.clicked.connect(reset_filters)

        # Обработчик сворачивания/разворачивания фильтров
        def toggle_filters():
            is_visible = filters_content.isVisible()
            filters_content.setVisible(not is_visible)
            if is_visible:
                toggle_btn.setIcon(IconLoader.load('arrow-down-circle'))
                toggle_btn.setToolTip('Развернуть фильтры')
            else:
                toggle_btn.setIcon(IconLoader.load('arrow-up-circle'))
                toggle_btn.setToolTip('Свернуть фильтры')

        toggle_btn.clicked.connect(toggle_filters)

        # Сохраняем ссылки на фильтры в виджете
        widget.period_combo = period_combo
        widget.year_spin = year_spin
        widget.quarter_combo = quarter_combo
        widget.month_combo = month_combo
        widget.date_criterion_combo = date_criterion_combo
        widget.address_input = address_input
        widget.city_combo = city_combo
        widget.agent_combo = agent_combo

        # Загружаем данные для комбобоксов
        self.load_archive_filter_data(city_combo, agent_combo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        cards_container = QWidget()
        self.archive_layout = QVBoxLayout()
        self.archive_layout.setSpacing(10)
        self.archive_layout.setContentsMargins(10, 10, 10, 10)

        cards_container.setLayout(self.archive_layout)
        scroll.setWidget(cards_container)

        layout.addWidget(scroll)
        widget.setLayout(layout)
        widget.archive_layout = self.archive_layout

        return widget

    def load_archive_filter_data(self, city_combo, agent_combo):
        """Загрузка данных для фильтров архива"""
        try:
            # Получаем все архивные карточки для заполнения фильтров
            cards = self.data.get_supervision_cards_archived() or []

            # Собираем уникальные города
            cities = set()
            for card in cards:
                city = card.get('city')
                if city:
                    cities.add(city)

            # Добавляем города в комбобокс
            for city in sorted(cities):
                city_combo.addItem(city, city)

            # Получаем всех агентов из базы данных (локальные данные)
            agents = self.data.get_all_agents() or []
            for agent in agents:
                agent_name = agent['name']
                agent_combo.addItem(agent_name, agent_name)

        except Exception as e:
            print(f" ОШИБКА загрузки данных фильтров: {e}")

    def apply_archive_filters(self):
        """Применение фильтров к архивным карточкам надзора"""
        print("\n=== ПРИМЕНЕНИЕ ФИЛЬТРОВ К АРХИВУ НАДЗОРА ===")

        try:
            # Получаем виджет архива
            archive_widget = self.archive_widget

            # Получаем значения фильтров
            period = archive_widget.period_combo.currentText()
            year = archive_widget.year_spin.value()
            quarter = archive_widget.quarter_combo.currentIndex() + 1
            month = archive_widget.month_combo.currentIndex() + 1
            date_criterion = archive_widget.date_criterion_combo.currentText()
            address_filter = archive_widget.address_input.text().strip().lower()
            city_filter = archive_widget.city_combo.currentData()
            agent_filter = archive_widget.agent_combo.currentData()

            # Получаем все архивные карточки
            cards = self.data.get_supervision_cards_archived() or []

            # Применяем фильтры
            filtered_cards = []
            for card in cards:
                # Фильтр по адресу
                if address_filter:
                    card_address = card.get('address', '').lower()
                    if address_filter not in card_address:
                        continue

                # Фильтр по городу
                if city_filter:
                    if card.get('city') != city_filter:
                        continue

                # Фильтр по агенту
                if agent_filter:
                    if card.get('agent_type') != agent_filter:
                        continue

                # Фильтр по периоду (используем выбранный критерий даты)
                if period != 'Все время':
                    # Выбираем поле даты в зависимости от критерия
                    if date_criterion == 'Дата создания':
                        date_field = card.get('contract_date')  # Дата заключения договора
                    else:  # Дата закрытия
                        date_field = card.get('status_changed_date')  # Дата установки статуса Сдан/Расторгнут/Авторский надзор

                    if date_field:
                        try:
                            # Пытаемся разобрать дату в разных форматах
                            if ' ' in date_field:  # Формат с временем: '2024-11-25 10:30:00'
                                date_part = date_field.split()[0]
                                card_date = QDate.fromString(date_part, 'yyyy-MM-dd')
                            else:  # Формат без времени: '2024-11-25'
                                card_date = QDate.fromString(date_field, 'yyyy-MM-dd')

                            if not card_date.isValid():
                                # Если не удалось распарсить дату, пропускаем
                                continue

                            card_year = card_date.year()
                            card_month = card_date.month()
                            card_quarter = (card_month - 1) // 3 + 1

                            if period == 'Год' and card_year != year:
                                continue
                            elif period == 'Квартал' and (card_year != year or card_quarter != quarter):
                                continue
                            elif period == 'Месяц' and (card_year != year or card_month != month):
                                continue
                        except Exception:
                            # Если произошла ошибка при парсинге, пропускаем
                            continue
                    else:
                        # Если поле даты отсутствует, пропускаем карточку
                        continue

                filtered_cards.append(card)

            # Очищаем текущие карточки
            archive_layout = archive_widget.archive_layout
            while archive_layout.count():
                child = archive_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            # Отображаем отфильтрованные карточки
            if filtered_cards:
                for card_data in filtered_cards:
                    from ui.crm_tab import ArchiveCard
                    archive_card = ArchiveCard(card_data, self.db, card_type='supervision', employee=self.employee, api_client=self.api_client)
                    archive_layout.addWidget(archive_card)
            else:
                empty_label = QLabel('Нет карточек, соответствующих фильтрам')
                empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
                empty_label.setAlignment(Qt.AlignCenter)
                archive_layout.addWidget(empty_label)

            archive_layout.addStretch(1)

            print(f"Фильтрация завершена: {len(filtered_cards)} из {len(cards)} карточек\n")

        except Exception as e:
            print(f" ОШИБКА применения фильтров: {e}")
            import traceback
            traceback.print_exc()

    def ensure_data_loaded(self):
        """Ленивая загрузка: данные загружаются при первом показе таба.
        При повторном переключении — пропускаем если кэш свежий (<30с)."""
        import time as _time
        now = _time.monotonic()
        first_time = not self._data_loaded

        if first_time:
            self._data_loaded = True
            self._last_load_time = now
            self._loading_guard = True
            self.data.prefer_local = True
            try:
                self.load_cards_for_current_tab()
            finally:
                self.data.prefer_local = False
                self._loading_guard = False
        elif now - getattr(self, '_last_load_time', 0) < 30:
            return
        else:
            self._last_load_time = now
            self.load_active_cards()

    def load_cards_for_current_tab(self):
        """Загрузка карточек для текущей вкладки"""
        self.load_active_cards()
        if not self.is_dan_role:
            # Отложенная загрузка архива — не блокирует UI
            QTimer.singleShot(200, self.load_archive_cards)
            
    def load_active_cards(self):
        """Загрузка активных карточек с fallback на локальную БД"""
        try:
            cards = self.data.get_supervision_cards_active() or []
        except Exception as e:
            print(f"[ERROR] Загрузка карточек надзора: {e}")
            self._show_critical_error(e, None)
            return

        if not hasattr(self.active_widget, 'columns'):
            return

        columns_dict = self.active_widget.columns

        # Отключаем отрисовку на время массовой загрузки
        for column in columns_dict.values():
            column.cards_list.setUpdatesEnabled(False)
            column.clear_cards()

        # Добавляем карточки с учетом прав
        is_dan = self.is_dan_role
        dan_id = self.employee['id']
        for card_data in cards:
            if is_dan and card_data.get('dan_id') != dan_id:
                continue

            column_name = card_data.get('column_name', 'Новый заказ')
            if column_name in columns_dict:
                columns_dict[column_name].add_card(card_data, bulk=True)

        # Пакетное обновление после загрузки
        for column in columns_dict.values():
            column.update_header_count()
            column.cards_list.setUpdatesEnabled(True)

        self.update_tab_counters()

    def load_archive_cards(self):
        """Загрузка архивных карточек с fallback на локальную БД"""
        try:
            cards = self.data.get_supervision_cards_archived()
        except Exception as e:
            print(f"[ERROR] Загрузка архива надзора: {e}")
            cards = []

        archive_layout = self.archive_widget.archive_layout

        # Очищаем архив
        while archive_layout.count():
            child = archive_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Добавляем карточки
        if cards:
            from ui.crm_tab import ArchiveCard
            for card_data in cards:
                # Для ДАН показываем только свои
                if self.is_dan_role:
                    if card_data.get('dan_id') != self.employee['id']:
                        continue

                archive_card = ArchiveCard(card_data, self.db, card_type='supervision', employee=self.employee, api_client=self.api_client)
                archive_layout.addWidget(archive_card)
        else:
            empty_label = QLabel('Архив пуст')
            empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            archive_layout.addWidget(empty_label)
        
        archive_layout.addStretch(1)

        self.update_tab_counters()

    def _show_offline_notification(self, error=None):
        """Показать уведомление об offline режиме"""
        try:
            from ui.custom_message_box import CustomMessageBox
            msg = 'Сервер недоступен. Данные загружены из локальной базы.\n'
            msg += 'Изменения будут синхронизированы при восстановлении связи.'
            if error:
                msg += f'\n\nОшибка: {str(error)[:100]}'
            CustomMessageBox(self, 'Offline режим', msg, 'warning').exec_()
        except Exception:
            pass

    def _show_critical_error(self, api_error, db_error):
        """Показать критическую ошибку когда и API, и БД недоступны"""
        try:
            from ui.custom_message_box import CustomMessageBox
            msg = 'Не удалось загрузить данные:\n\n'
            if api_error:
                msg += f'Сервер: {str(api_error)[:100]}\n'
            if db_error:
                msg += f'Локальная БД: {str(db_error)[:100]}'
            CustomMessageBox(self, 'Критическая ошибка', msg, 'error').exec_()
        except Exception:
            pass

    def _api_update_card_with_fallback(self, card_id: int, updates: dict):
        """Обновить карточку надзора с fallback на локальную БД и очередью offline"""
        self.data.update_supervision_card(card_id, updates)

    def update_tab_counters(self):
        """Обновление счетчиков вкладок"""
        # Подсчет активных
        active_count = 0
        if hasattr(self.active_widget, 'columns'):
            for column in self.active_widget.columns.values():
                active_count += column.cards_list.count()
        
        self.tabs.setTabText(0, f'Активные проекты ({active_count})')
        
        # Подсчет архива
        if not self.is_dan_role:
            archive_count = 0
            if hasattr(self.archive_widget, 'archive_layout'):
                layout = self.archive_widget.archive_layout
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item.widget() and item.widget().__class__.__name__ == 'ArchiveCard':
                        archive_count += 1
            
            self.tabs.setTabText(1, f'Архив ({archive_count})')
    
    def on_tab_changed(self, index):
        """Переключение вкладок"""
        if getattr(self, '_loading_guard', False):
            return
        if index == 0:
            self.load_active_cards()
        elif index == 1:
            self.load_archive_cards()
    
    def _get_sync_manager(self):
        """Получить SyncManager из главного окна"""
        mw = self.window()
        return getattr(mw, 'sync_manager', None)

    def on_card_moved(self, card_id, from_column, to_column):
        """Обработка перемещения карточки"""
        # === ПРОВЕРКА ПРАВА НА ПЕРЕМЕЩЕНИЕ ===
        if not _has_perm(self.employee, self.api_client, 'supervision.move'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на перемещение карточек надзора.', 'error').exec_()
            self.load_cards_for_current_tab()
            return
        # === ПРАВИЛО: Нельзя вернуться в "Новый заказ" ===
        if to_column == 'Новый заказ' and from_column != 'Новый заказ':
            CustomMessageBox(
                self, 'Перемещение запрещено',
                'Нельзя вернуть карточку в "Новый заказ".\n'
                'Используйте столбец "В ожидании" для приостановки.',
                'warning'
            ).exec_()
            self.load_cards_for_current_tab()
            return

        # === ПРАВИЛО: Из "В ожидании" — только в прежний столбец или "Выполненный проект" ===
        if from_column == 'В ожидании' and to_column not in ['В ожидании', 'Выполненный проект']:
            card_info = self.data.get_supervision_card(card_id)
            prev_col = card_info.get('previous_column') if card_info else None
            # Если prev_col известен и это не "Новый заказ" — разрешаем только в prev_col
            if prev_col and prev_col != 'Новый заказ' and to_column != prev_col:
                CustomMessageBox(
                    self, 'Перемещение запрещено',
                    f'Из "В ожидании" можно вернуть только в "{prev_col}" или "Выполненный проект".',
                    'warning'
                ).exec_()
                self.load_cards_for_current_tab()
                return
            # Если prev_col = None/пусто — разрешаем (сервер дополнительно проверит)

        # Приостанавливаем синхронизацию на время перемещения
        sync = self._get_sync_manager()
        if sync:
            sync.pause_sync()

        print(f"\n[RELOAD] ПЕРЕМЕЩЕНИЕ КАРТОЧКИ НАДЗОРА:")
        print(f"   ID: {card_id}")
        print(f"   Из: '{from_column}' → В: '{to_column}'")

        try:
            # ========== ПРОВЕРКА НАЗНАЧЕНИЯ ИСПОЛНИТЕЛЕЙ ==========
            # При перемещении на рабочую стадию проверяем, назначены ли исполнители
            non_work_columns = ['Новый заказ', 'В ожидании', 'Выполненный проект']

            if to_column not in non_work_columns and not self.is_dan_role:
                # Получаем данные об исполнителях
                card_data = self.data.get_supervision_card(card_id)
                executors_data = None
                if card_data:
                    executors_data = {
                        'dan_id': card_data.get('dan_id'),
                        'senior_manager_id': card_data.get('senior_manager_id')
                    }

                # Если хотя бы один исполнитель не назначен - показываем диалог
                if executors_data and (not executors_data.get('dan_id') or not executors_data.get('senior_manager_id')):
                    print(f"   ! Исполнитель не назначен (ДАН={executors_data.get('dan_id')}, СМП={executors_data.get('senior_manager_id')}), показываем диалог назначения")
                    dialog = AssignExecutorsDialog(self, card_id, to_column, api_client=self.api_client)
                    if dialog.exec_() != QDialog.Accepted:
                        # Пользователь отменил - отменяем перемещение и перезагружаем карточки
                        print(f"   ! Назначение отменено, отмена перемещения. Карточка остается в '{from_column}'")
                        self.load_cards_for_current_tab()
                        return
                    # Перепроверяем: были ли исполнители реально назначены после диалога
                    updated_card = self.data.get_supervision_card(card_id)
                    if updated_card and (not updated_card.get('dan_id') or not updated_card.get('senior_manager_id')):
                        print(f"   ! После диалога исполнители всё ещё не назначены, отмена перемещения")
                        self.load_cards_for_current_tab()
                        return
                    print(f"   + Исполнители назначены: ДАН={dialog.assigned_dan_id}, СМП={dialog.assigned_smp_id}")

            # ========== КОНЕЦ ПРОВЕРКИ НАЗНАЧЕНИЯ ==========

            # ИСПРАВЛЕНИЕ: Проверка и автоматическое принятие работы при перемещении
            # "В ожидании" также исключаем - это стартовая колонка без рабочей стадии
            if not self.is_dan_role and from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                # Получаем данные карточки через DataAccess
                card_data = self.data.get_supervision_card(card_id)
                card_info = None
                if card_data:
                    card_info = {
                        'dan_completed': card_data.get('dan_completed', 0),
                        'dan_name': card_data.get('dan_name', 'ДАН')
                    }

                if card_info:
                    dan_completed = card_info['dan_completed']
                    dan_name = card_info['dan_name'] or 'ДАН'

                    # Если ДАН сдал работу, но её не приняли - предупреждение
                    if dan_completed == 1:
                        CustomMessageBox(
                            self,
                            'Работа не принята',
                            f'ДАН сдал работу, но вы еще не приняли её!\n\n'
                            f'Сначала нажмите кнопку "Принять работу" на карточке,\n'
                            f'затем переместите её на следующую стадию.',
                            'warning'
                        ).exec_()
                        self.load_cards_for_current_tab()
                        return

                    # Если ДАН НЕ сдал работу, но пользователь с правом complete_stage перемещает - автоматически принимаем
                    if dan_completed == 0 and _has_perm(self.employee, self.api_client, 'supervision.complete_stage'):
                        print(f"\n[AUTO ACCEPT] Автоматическое принятие стадии надзора '{from_column}'")

                        # Добавляем запись в историю о принятии
                        self.data.add_supervision_history(
                            card_id,
                            self.employee['id'],
                            'accepted',
                            f"Стадия '{from_column}' автоматически принята при перемещении руководством. Исполнитель: {dan_name}"
                        )

                        print(f"    Запись о принятии добавлена в историю")

                        # ИСПРАВЛЕНИЕ: Обновляем отчетный месяц для оплат этой стадии
                        from datetime import datetime
                        current_month = datetime.now().strftime('%Y-%m')

                        # Получаем contract_id через DataAccess (не прямой SQL)
                        card_api_data_for_contract = self.data.get_supervision_card(card_id)
                        contract_id = (card_api_data_for_contract or {}).get('contract_id')

                        if contract_id:
                            # Проверяем, есть ли уже оплаты для этой стадии через DataAccess
                            all_card_payments = self.data.get_payments_by_supervision_card(card_id) or []
                            existing_payments = [p for p in all_card_payments if p.get('stage_name') == from_column]

                            # Если оплат для этой стадии нет, создаем их
                            if not existing_payments:
                                # Получаем назначенных исполнителей через DataAccess
                                card_api_data = self.data.get_supervision_card(card_id)
                                executors_row = None
                                if card_api_data:
                                    executors_row = {
                                        'dan_id': card_api_data.get('dan_id'),
                                        'senior_manager_id': card_api_data.get('senior_manager_id')
                                    }
                                    print(f"    Получены исполнители: ДАН={executors_row['dan_id']}, СМП={executors_row['senior_manager_id']}")

                                if executors_row:
                                    # Создаем оплату для ДАН
                                    if executors_row['dan_id']:
                                        # ИСПРАВЛЕНО 06.02.2026: Рассчитываем сумму перед созданием платежа
                                        dan_amount = 0
                                        try:
                                            dan_amount = self.data.calculate_payment_amount(
                                                contract_id, executors_row['dan_id'], 'ДАН',
                                                stage_name=from_column, supervision_card_id=card_id
                                            )
                                        except Exception as e:
                                            print(f"    [WARN] Ошибка расчёта суммы ДАН: {e}")

                                        payment_data = {
                                            'contract_id': contract_id,
                                            'employee_id': executors_row['dan_id'],
                                            'role': 'ДАН',
                                            'stage_name': from_column,
                                            'calculated_amount': dan_amount,
                                            'final_amount': dan_amount,
                                            'payment_type': 'Полная оплата',
                                            'report_month': current_month,
                                            'supervision_card_id': card_id
                                        }
                                        self.data.create_payment(payment_data)
                                        print(f"    Создана оплата для ДАН по стадии '{from_column}': {dan_amount} руб")

                                    # Создаем оплату для Старшего менеджера
                                    if executors_row['senior_manager_id']:
                                        # ИСПРАВЛЕНО 06.02.2026: Рассчитываем сумму перед созданием платежа
                                        smp_amount = 0
                                        try:
                                            smp_amount = self.data.calculate_payment_amount(
                                                contract_id, executors_row['senior_manager_id'], 'Старший менеджер проектов',
                                                stage_name=from_column, supervision_card_id=card_id
                                            )
                                        except Exception as e:
                                            print(f"    [WARN] Ошибка расчёта суммы СМП: {e}")

                                        payment_data = {
                                            'contract_id': contract_id,
                                            'employee_id': executors_row['senior_manager_id'],
                                            'role': 'Старший менеджер проектов',
                                            'stage_name': from_column,
                                            'calculated_amount': smp_amount,
                                            'final_amount': smp_amount,
                                            'payment_type': 'Полная оплата',
                                            'report_month': current_month,
                                            'supervision_card_id': card_id
                                        }
                                        self.data.create_payment(payment_data)
                                        print(f"    Создана оплата для СМП по стадии '{from_column}': {smp_amount} руб")

                                # Верификация: проверяем дубли оплат для этой стадии
                                if self.data.is_multi_user:
                                    try:
                                        all_stage_payments = self.data.get_payments_by_supervision_card(card_id)
                                        stage_payments = [p for p in (all_stage_payments or []) if p.get('stage_name') == from_column]
                                        for check_role in ['ДАН', 'Старший менеджер проектов']:
                                            rp = [p for p in stage_payments if p.get('role') == check_role]
                                            if len(rp) > 1:
                                                print(f"[WARN] Обнаружено {len(rp)} оплат для {check_role} на стадии '{from_column}', ожидается 1")
                                                sorted_rp = sorted(rp, key=lambda x: x.get('id', 0), reverse=True)
                                                for dup in sorted_rp[1:]:
                                                    self.data.delete_payment(dup['id'])
                                                    print(f"[DEDUP] Удалена лишняя оплата ID={dup['id']} для {check_role}")
                                    except Exception as e:
                                        print(f"[WARN] Ошибка верификации дублей оплат: {e}")
                            else:
                                # Если оплаты уже есть, обновляем отчетный месяц через DataAccess
                                updated_count = 0
                                for ep in existing_payments:
                                    if not ep.get('report_month'):
                                        self.data.update_payment(ep['id'], {'report_month': current_month})
                                        updated_count += 1

                                if updated_count > 0:
                                    print(f"    + Обновлен отчетный месяц ({current_month}) для {updated_count} оплат стадии '{from_column}'"
                                    )

            # Обновляем колонку в БД с fallback логикой
            # Перемещаем карточку через DataAccess (API + fallback на локальную БД)
            from utils.api_client.exceptions import APIResponseError
            try:
                self.data.move_supervision_card(card_id, to_column)
            except APIResponseError as move_err:
                # Бизнес-ошибка (сервер запретил перемещение)
                error_msg = str(move_err)
                # Извлекаем понятный текст из "Ошибка сервера (HTTP 422): ..."
                if ': ' in error_msg:
                    error_msg = error_msg.split(': ', 1)[1]
                print(f"   ! Перемещение запрещено сервером: {error_msg}")
                CustomMessageBox(self, 'Перемещение запрещено', error_msg, 'warning').exec_()
                self.load_cards_for_current_tab()
                return
            print(f"   + Карточка перемещена")

            # Сбрасываем отметку о сдаче при перемещении
            # Примечание: resume при выходе из "В ожидании" выполняется автоматически
            # на сервере в move_supervision_card_to_column, повторный вызов не нужен
            if to_column != from_column:
                self.data.reset_supervision_stage_completion(card_id)
                print(f"   + Отметка о сдаче сброшена")

            # Запрос дедлайна при перемещении (только для менеджеров)
            if not self.is_dan_role:
                skip_deadline_columns = ['Новый заказ', 'В ожидании', 'Выполненный проект']

                if to_column not in skip_deadline_columns and from_column != to_column:
                    dialog = SupervisionStageDeadlineDialog(self, card_id, to_column, api_client=self.api_client)
                    dialog.exec_()

            # Обновляем статус договора только при перемещении в "Выполненный проект"
            if to_column == 'Выполненный проект':
                dialog = SupervisionCompletionDialog(self, card_id, api_client=self.api_client)
                if dialog.exec_() == QDialog.Accepted:
                    self.load_cards_for_current_tab()
                else:
                    self.load_cards_for_current_tab()
                return

            self.load_cards_for_current_tab()

        except Exception as e:
            print(f" Ошибка перемещения: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось переместить карточку: {e}', 'error').exec_()
        finally:
            # Возобновляем синхронизацию после перемещения
            if sync:
                sync.resume_sync()

    def request_termination_reason(self, contract_id):
        """Запрос причины расторжения"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Причина расторжения')
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        label = QLabel('Укажите причину расторжения договора:')
        layout.addWidget(label)
        
        reason_text = QTextEdit()
        reason_text.setMaximumHeight(100)
        layout.addWidget(reason_text)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(lambda: self.save_termination_reason(contract_id, reason_text.toPlainText(), dialog))
        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(dialog.reject)
        
        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        dialog.setLayout(layout)
        dialog.exec_()
    
    def save_termination_reason(self, contract_id, reason, dialog):
        """Сохранение причины расторжения"""
        if not reason.strip():
            CustomMessageBox(self, 'Ошибка', 'Укажите причину расторжения', 'warning').exec_()
            return

        self.data.update_contract(contract_id, {'termination_reason': reason.strip()})
        dialog.accept()
    
    def show_statistics(self):
        """Показ статистики"""
        dialog = SupervisionStatisticsDialog(self, api_client=self.api_client)
        dialog.exec_()

    def refresh_current_tab(self):
        """Обновление текущей вкладки"""
        current_index = self.tabs.currentIndex()
        if current_index == 0:
            self.load_active_cards()
        elif current_index == 1:
            self.load_archive_cards()

        # Обновляем дашборд
        mw = self.window()
        if hasattr(mw, 'refresh_current_dashboard'):
            mw.refresh_current_dashboard()

    def on_sync_update(self, updated_cards):
        """
        Обработчик обновления данных от SyncManager.
        Вызывается при изменении карточек надзора другими пользователями.
        Данные уже обновлены в локальной БД — используем prefer_local для мгновенного обновления UI.
        """
        try:
            print(f"[SYNC] Получено обновление карточек надзора: {len(updated_cards)} записей")
            # Обновляем из локальной БД (данные уже синхронизированы), не блокируя UI
            self.data.prefer_local = True
            try:
                self.refresh_current_tab()
            finally:
                self.data.prefer_local = False
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации карточек надзора: {e}")
            import traceback
            traceback.print_exc()


# ИСПРАВЛЕНИЕ 07.02.2026: Класс для вертикального текста в свёрнутых колонках (#19)
class VerticalLabelSupervision(QWidget):
    """Виджет с вертикальным текстом для свёрнутых колонок надзора"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self.setMinimumWidth(40)
        self.setMaximumWidth(40)

    def setText(self, text):
        self._text = text
        self.update()

    def text(self):
        return self._text

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QFont
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Фон (оранжевый как у заголовка надзора)
        painter.fillRect(self.rect(), QColor('#FFE5CC'))

        # Настройка шрифта
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor('#333333'))

        # Поворот на 90 градусов (текст снизу вверх)
        painter.translate(self.width() / 2 + 5, self.height() - 10)
        painter.rotate(-90)

        # Рисуем текст
        painter.drawText(0, 0, self._text)

        painter.end()

    def sizeHint(self):
        return QSize(40, 200)


class SupervisionColumn(BaseKanbanColumn):
    """Колонка для карточек надзора"""
    card_moved = pyqtSignal(int, str, str)

    def __init__(self, column_name, employee, db, api_client=None):
        super().__init__()
        self.column_name = column_name
        self.employee = employee
        self.db = db
        self.api_client = api_client
        self.is_dan_role = not _has_perm(employee, api_client, 'supervision.move')
        self._original_min_width = 340
        self._original_max_width = 360
        self._board_name = "crm_supervision"
        self.init_ui()
        self._apply_initial_collapse_state()

    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(self._original_min_width)
        self.setMaximumWidth(self._original_max_width)
        self.setStyleSheet("""
            SupervisionColumn {
                background-color: #F5F5F5;
                border: 1px solid #d9d9d9;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # ИСПРАВЛЕНИЕ 07.02.2026: Заголовок с кнопкой сворачивания (#19)
        header_container = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        self.header_label = QLabel()
        self.header_label.setStyleSheet("""
            font-weight: bold;
            font-size: 13px;
            padding: 10px;
            background-color: #FFE5CC;
            border-radius: 4px;
        """)
        self.header_label.setWordWrap(True)
        self.update_header_count()
        header_layout.addWidget(self.header_label, 1)

        # Кнопка сворачивания - используем иконку стрелки как у фильтров
        self.collapse_btn = IconLoader.create_icon_button('arrow-left-circle', '', 'Свернуть колонку', icon_size=14)
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #FFD4A8; }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.collapse_btn)

        header_container.setLayout(header_layout)
        layout.addWidget(header_container)
        
        # Список карточек
        can_drag = not self.is_dan_role
        self.cards_list = SupervisionDraggableList(self, can_drag)
        self.cards_list.setStyleSheet("""
            QListWidget {
                background-color: #E8E8E8;
                border: none;
                padding: 5px;
            }
            QListWidget::item {
                background-color: transparent;
                border: none;
                padding: 2px;
            }
        """)
        self.cards_list.setFocusPolicy(Qt.ClickFocus)
        self.cards_list.setSpacing(5)
        self.cards_list.itemDoubleClicked.connect(self._on_card_double_clicked)

        layout.addWidget(self.cards_list, 1)
        self.setLayout(layout)

    def _on_card_double_clicked(self, item):
        """Двойной клик по карточке надзора → редактирование."""
        card_widget = self.cards_list.itemWidget(item)
        if card_widget and hasattr(card_widget, 'edit_card'):
            card_widget.edit_card()

    # _apply_initial_collapse_state, _collapse_column, _expand_column,
    # toggle_collapse, update_header_count, add_card, clear_cards
    # наследуются из BaseKanbanColumn

    def _make_vertical_label(self):
        """Создать вертикальный лейбл для свёрнутой колонки надзора."""
        return VerticalLabelSupervision()

    def _create_card_widget(self, card_data):
        """Создать виджет карточки надзора."""
        return SupervisionCard(card_data, self.employee, self.db, self.api_client)

class SupervisionCard(QFrame):
    """Карточка авторского надзора"""

    def __init__(self, card_data, employee, db, api_client=None):
        super().__init__()
        self.card_data = card_data
        self.employee = employee
        self.db = db
        self.api_client = api_client
        self.data = DataAccess(api_client=api_client)
        self.is_dan_role = not _has_perm(employee, api_client, 'supervision.move')
        self.init_ui()

    def init_ui(self):
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)

        # Если приостановлена - подсветка
        if self.card_data.get('is_paused'):
            self.setStyleSheet("""
                SupervisionCard {
                    background-color: #FFF3CD;
                    border: 2px solid #F39C12;
                    border-radius: 8px;
                }
            """)
        else:
            # ИСПРАВЛЕНИЕ 06.02.2026: Стили как в основном CRM (#21)
            self.setStyleSheet("""
                SupervisionCard {
                    background-color: white;
                    border: 2px solid #CCCCCC;
                    border-radius: 8px;
                }
                SupervisionCard:hover {
                    border: 2px solid #909090;
                    background-color: #f5f5f5;
                }
            """)
        
        self.setMinimumWidth(200)
        self.setMaximumWidth(300)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        # Номер договора
        contract_label = QLabel(f"Договор: {self.card_data.get('contract_number', 'N/A')}")
        contract_label.setStyleSheet('font-size: 10px; color: #888; background-color: transparent;')
        contract_label.setFixedHeight(16)
        layout.addWidget(contract_label, 0)
        
        # Адрес
        address = self.card_data.get('address', 'Адрес не указан')
        address_label = QLabel(f"<b>{address}</b>")
        address_label.setWordWrap(True)
        address_label.setStyleSheet('font-size: 14px; color: #222; font-weight: bold; background-color: transparent;')
        address_label.setMaximumHeight(50)
        layout.addWidget(address_label, 0)
        
        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet('background-color: #DDDDDD;')
        separator.setFixedHeight(1)
        layout.addWidget(separator, 0)
        
        # Информация с иконками
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        info_row.setContentsMargins(0, 0, 0, 0)

        # Площадь и город с иконками
        info_container = QWidget()
        info_layout = QHBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)

        if self.card_data.get('area'):
            # Иконка площади
            area_icon = IconLoader.create_icon_button('box', '', '', icon_size=12)
            area_icon.setFixedSize(12, 12)
            area_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
            area_icon.setEnabled(False)
            info_layout.addWidget(area_icon)

            # Текст площади
            area_label = QLabel(f"{self.card_data['area']} м²")
            area_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            info_layout.addWidget(area_label)

            if self.card_data.get('city') or self.card_data.get('agent_type'):
                # Разделитель
                sep_label = QLabel("|")
                sep_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                info_layout.addWidget(sep_label)

        if self.card_data.get('city'):
            # Иконка города
            city_icon = IconLoader.create_icon_button('map-pin', '', '', icon_size=12)
            city_icon.setFixedSize(12, 12)
            city_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
            city_icon.setEnabled(False)
            info_layout.addWidget(city_icon)

            # Текст города
            city_label = QLabel(self.card_data['city'])
            city_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            info_layout.addWidget(city_label)

            if self.card_data.get('agent_type'):
                # Разделитель
                sep_label = QLabel("|")
                sep_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                info_layout.addWidget(sep_label)

        if self.card_data.get('agent_type'):
            # Тип агента с цветом
            agent_type = self.card_data['agent_type']
            agent_color = self.data.get_agent_color(agent_type)
            agent_label = QLabel(agent_type)
            agent_label.setFixedHeight(24)
            if agent_color:
                agent_label.setStyleSheet(f'''
                    background-color: {agent_color};
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    border: 2px solid {agent_color};
                ''')
            else:
                agent_label.setStyleSheet('''
                    background-color: #95A5A6;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                ''')
            info_layout.addWidget(agent_label)

        info_layout.addStretch()
        info_container.setLayout(info_layout)
        layout.addWidget(info_container, 0)
        
        # Команда (сворачиваемая)
        team_widget = self.create_team_section()
        if team_widget:
            layout.addWidget(team_widget, 0)
        
        # Индикатор приостановки
        if self.card_data.get('is_paused'):
            pause_label = QLabel('⏸ ПРИОСТАНОВЛЕНО')
            pause_label.setStyleSheet('''
                color: white;
                background-color: #F39C12;
                padding: 5px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            ''')
            pause_label.setFixedHeight(28)
            layout.addWidget(pause_label, 0)
        
        # Дедлайн
        if self.card_data.get('deadline'):
            deadline_raw = self.card_data['deadline']
            try:
                dl_date = QDate.fromString(deadline_raw, 'yyyy-MM-dd')
                deadline_display = dl_date.toString('dd.MM.yyyy') if dl_date.isValid() else deadline_raw
            except Exception:
                deadline_display = deadline_raw
            deadline_label = QLabel(f"Дедлайн: {deadline_display}")
            deadline_label.setStyleSheet('''
                color: white;
                background-color: #95A5A6;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            ''')
            deadline_label.setFixedHeight(28)
            layout.addWidget(deadline_label, 0)
        
        # Теги
        if self.card_data.get('tags'):
            tags_label = QLabel(f"{self.card_data['tags']}")
            tags_label.setStyleSheet('''
                color: white;
                background-color: #FF6B6B;
                padding: 3px 8px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
            ''')
            tags_label.setFixedHeight(28)
            layout.addWidget(tags_label, 0)
        
        # Индикатор "РАБОТА СДАНА" (для менеджеров)
        if not self.is_dan_role and self.card_data.get('dan_completed'):
            work_done_label = QLabel(
                f"Работа сдана: {self.card_data.get('dan_name', 'ДАН')}\n"
                f"Требуется согласование и перемещение на следующую стадию"
            )
            work_done_label.setWordWrap(True)
            work_done_label.setStyleSheet('''
                color: white;
                background-color: #27AE60;
                padding: 6px 10px;
                border-radius: 4px;
                font-size: 10px;
                font-weight: bold;
                border: 2px solid #1E8449;
            ''')
            work_done_label.setFixedHeight(55)
            layout.addWidget(work_done_label, 0)
            
            # ========== КНОПКА "ПРИНЯТЬ РАБОТУ" (SVG) ==========
            accept_work_btn = IconLoader.create_icon_button('accept', 'Принять работу', 'Принять выполненную работу', icon_size=12)
            accept_work_btn.setStyleSheet("""
                QPushButton {
                    background-color: #1E8449;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #17703C; }
            """)
            accept_work_btn.setFixedHeight(32)
            accept_work_btn.clicked.connect(self.accept_work)
            layout.addWidget(accept_work_btn, 0)
            
        # КНОПКИ
        buttons_added = False
        
        # ДЛЯ МЕНЕДЖЕРОВ
        if not self.is_dan_role:
            # ========== 1. ДОБАВИТЬ ЗАПИСЬ (SVG) ==========
            add_note_btn = IconLoader.create_icon_button('note', 'Добавить запись', 'Добавить запись в историю', icon_size=12)
            add_note_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95A5A6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover { background-color: #7F8C8D; }
            """)
            add_note_btn.setFixedHeight(28)
            add_note_btn.clicked.connect(self.add_project_note)
            layout.addWidget(add_note_btn, 0)
            
            # ========== 2. ПРИОСТАНОВИТЬ/ВОЗОБНОВИТЬ (SVG) ==========
            if self.card_data.get('is_paused'):
                pause_btn = IconLoader.create_icon_button('play', 'Возобновить', 'Возобновить работу над проектом', icon_size=12)
                pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        padding: 0px 10px;
                        border-radius: 6px;
                        font-size: 10px;
                        font-weight: bold;
                        min-height: 28px;
                        max-height: 28px;
                    }
                    QPushButton:hover { background-color: #229954; }
                """)
                pause_btn.clicked.connect(self.resume_card)
            else:
                pause_btn = IconLoader.create_icon_button('pause', 'Приостановить', 'Приостановить проект', icon_size=12)
                pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F39C12;
                        color: white;
                        padding: 0px 10px;
                        border-radius: 6px;
                        font-size: 10px;
                        font-weight: bold;
                        min-height: 28px;
                        max-height: 28px;
                    }
                    QPushButton:hover { background-color: #E67E22; }
                """)
                pause_btn.clicked.connect(self.pause_card)
            
            pause_btn.setFixedHeight(28)
            layout.addWidget(pause_btn, 0)

            # ========== 3. РЕДАКТИРОВАНИЕ (SVG) ==========
            edit_btn = IconLoader.create_icon_button('edit', 'Редактирование', 'Редактировать карточку', icon_size=12)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90E2;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover { background-color: #357ABD; }
            """)
            edit_btn.setFixedHeight(28)
            edit_btn.setAccessibleName("Редактирование карточки надзора")
            edit_btn.clicked.connect(self.edit_card)
            layout.addWidget(edit_btn, 0)

            buttons_added = True
        
        # ДЛЯ ДАН
        else:
            # ========== 1. ДОБАВИТЬ ЗАПИСЬ (SVG) ==========
            add_note_btn = IconLoader.create_icon_button('note', 'Добавить запись', 'Добавить запись в историю', icon_size=12)
            add_note_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95A5A6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    font-size: 10px;
                    font-weight: bold;
                    min-height: 28px;
                    max-height: 28px;
                }
                QPushButton:hover { background-color: #7F8C8D; }
            """)
            add_note_btn.setFixedHeight(28)
            add_note_btn.clicked.connect(self.add_project_note)
            layout.addWidget(add_note_btn, 0)
            
            # ========== 2. СДАТЬ РАБОТУ ИЛИ ОЖИДАНИЕ ==========
            if not self.card_data.get('dan_completed'):
                submit_btn = IconLoader.create_icon_button('submit', 'Сдать работу', 'Отметить работу как выполненную', icon_size=12)
                submit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        padding: 0px 10px;
                        border-radius: 6px;
                        font-size: 10px;
                        font-weight: bold;
                        min-height: 28px;
                        max-height: 28px;
                    }
                    QPushButton:hover { background-color: #229954; }
                """)
                submit_btn.setFixedHeight(28)
                submit_btn.clicked.connect(self.submit_work)
                layout.addWidget(submit_btn, 0)
            else:
                waiting_label = QLabel('⏳ Ожидает согласования менеджера')
                waiting_label.setStyleSheet('''
                    color: white;
                    background-color: #ffd93c;
                    padding: 8px 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    text-align: center;
                ''')
                waiting_label.setFixedHeight(38)
                layout.addWidget(waiting_label, 0)
            
            # ========== 3. ИСТОРИЯ ПРОЕКТА (SVG) ==========
            history_btn = IconLoader.create_icon_button('history', 'История проекта', 'Просмотр истории проекта', icon_size=12)
            history_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90E2;
                    color: white;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #357ABD; }
            """)
            history_btn.setFixedHeight(38)
            history_btn.clicked.connect(self.edit_card)
            layout.addWidget(history_btn, 0)
            
            buttons_added = True

        self.setLayout(layout)

        initial_height = self.calculate_height()
        self.setFixedHeight(initial_height)
    
    def create_team_section(self):
        """Создание секции команды"""
        team_members = []
        
        if self.card_data.get('senior_manager_name'):
            team_members.append(('Ст.менеджер', self.card_data['senior_manager_name']))
        if self.card_data.get('dan_name'):
            team_members.append(('ДАН', self.card_data['dan_name']))
        
        if not team_members:
            return None
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Кнопка-заголовок - ИСПРАВЛЕНИЕ 07.02.2026: Стили как в основном CRM (#21)
        self.team_toggle_btn = IconLoader.create_icon_button('chevron-right', f"Команда ({len(team_members)})", '', icon_size=10)
        self.team_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 3px 5px;
                text-align: left;
                font-size: 10px;
                font-weight: bold;
                color: #555;
                max-height: 20px;
                min-height: 20px;
            }
            QPushButton:hover { background-color: #E8E9EA; }
        """)
        self.team_toggle_btn.setFixedHeight(20)
        self.team_toggle_btn.clicked.connect(self.toggle_team)
        main_layout.addWidget(self.team_toggle_btn)
        
        # Контейнер сотрудников
        self.team_container = QFrame()
        self.team_container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-top: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                padding: 4px;
            }
        """)
        
        team_layout = QVBoxLayout()
        team_layout.setSpacing(4)
        team_layout.setContentsMargins(8, 6, 8, 6)

        for role, name in team_members:
            label = QLabel(f"{role}: {name}")
            label.setStyleSheet('font-size: 10px; color: #444; padding: 2px 4px;')
            label.setWordWrap(True)
            label.setMinimumHeight(26)
            team_layout.addWidget(label)
        
        self.team_container.setLayout(team_layout)
        main_layout.addWidget(self.team_container)
        
        self.team_container.hide()
        
        main_widget.setLayout(main_layout)
        return main_widget
    
    def toggle_team(self):
        """Сворачивание/разворачивание команды"""
        is_visible = self.team_container.isVisible()
        
        if is_visible:
            self.team_container.hide()
            self.team_toggle_btn.setIcon(IconLoader.load('chevron-right'))
            self.team_toggle_btn.setIconSize(QSize(10, 10))
            print("  Команда свернута")
        else:
            self.team_container.show()
            self.team_toggle_btn.setIcon(IconLoader.load('chevron-down'))
            self.team_toggle_btn.setIconSize(QSize(10, 10))
            print("  Команда развернута")
        
        self.update_card_height_immediately()
    
    def update_card_height_immediately(self):
        """Немедленное обновление высоты карточки"""
        new_height = self.calculate_height()
        
        print(f"  Новая высота карточки: {new_height}px")
        
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215)
        self.setFixedHeight(new_height)
        
        parent_widget = self.parent()
        while parent_widget:
            if isinstance(parent_widget, QListWidget):
                for i in range(parent_widget.count()):
                    item = parent_widget.item(i)
                    if parent_widget.itemWidget(item) == self:
                        item.setSizeHint(QSize(200, new_height + 10))
                        parent_widget.scheduleDelayedItemsLayout()
                        print(f"  Item обновлен: {new_height + 10}px")
                        return
                break
            parent_widget = parent_widget.parent()
    
    def calculate_height(self):
        """Расчет высоты карточки"""
        height = 150
        
        team_visible = False
        if hasattr(self, 'team_container'):
            team_visible = self.team_container.isVisible()
        
        if team_visible:
            team_count = 0
            if self.card_data.get('senior_manager_name'):
                team_count += 1
            if self.card_data.get('dan_name'):
                team_count += 1
            
            if team_count > 0:
                height += 35 + (team_count * 38)
        else:
            height += 35
        
        if not self.is_dan_role and self.card_data.get('dan_completed'):
            height += 55
            height += 38
        
        if self.card_data.get('is_paused'):
            height += 28
        
        if self.card_data.get('deadline'):
            height += 28
        
        if self.card_data.get('tags'):
            height += 28
        
        buttons_count = 1
        
        if not self.is_dan_role:
            buttons_count += 1
            buttons_count += 1
        else:
            if not self.card_data.get('dan_completed'):
                buttons_count += 1
            else:
                buttons_count += 1
            buttons_count += 1
        
        height += 38 * buttons_count
        
        return min(height, 1000)
    
    def pause_card(self):
        """Приостановка карточки"""
        if not _has_perm(self.employee, self.api_client, 'supervision.pause_resume'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на приостановку карточки', 'error').exec_()
            return
        dialog = PauseDialog(self, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            reason = dialog.reason_text.toPlainText().strip()
            if reason:
                self.data.pause_supervision_card(
                            self.card_data['id'],
                            reason
                        )
                self.refresh_parent_tab()
            else:
                CustomMessageBox(self, 'Ошибка', 'Укажите причину приостановки', 'warning').exec_()
                
    def resume_card(self):
        """Возобновление карточки"""
        if not _has_perm(self.employee, self.api_client, 'supervision.pause_resume'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на возобновление карточки', 'error').exec_()
            return
        dialog = QDialog(self)
        dialog.setWindowTitle('Подтверждение')
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        question = QLabel('Возобновить работу над проектом?')
        question.setStyleSheet('font-size: 13px; font-weight: bold; color: #333;')
        question.setAlignment(Qt.AlignCenter)
        layout.addWidget(question)
        
        info = QLabel('Статус "Приостановлено" будет снят.')
        info.setStyleSheet('font-size: 11px; color: #666;')
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        yes_btn = IconLoader.create_icon_button('play', 'Возобновить', '', icon_size=14)
        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        yes_btn.clicked.connect(dialog.accept)
        layout.addWidget(yes_btn)
        
        no_btn = QPushButton('Отмена')
        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        no_btn.clicked.connect(dialog.reject)
        layout.addWidget(no_btn)
        
        dialog.setLayout(layout)

        if dialog.exec_() == QDialog.Accepted:
            self.data.resume_supervision_card(
                self.card_data['id'],
                self.employee['id']
            )
            self.refresh_parent_tab()
            
    @debounce_click(delay_ms=2000)
    def submit_work(self):
        """Сдача работы (для ДАН)"""
        column_name = self.card_data.get('column_name', 'N/A')
        
        dialog = QDialog(self)
        dialog.setWindowTitle('Подтверждение')
        dialog.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        question = QLabel('Подтвердить сдачу работы?')
        question.setStyleSheet('font-size: 13px; font-weight: bold; color: #333;')
        question.setAlignment(Qt.AlignCenter)
        layout.addWidget(question)
        
        info = QLabel('Стадия будет отмечена как выполненная и\nпередана на согласование менеджеру.')
        info.setStyleSheet('font-size: 11px; color: #666;')
        info.setWordWrap(True)
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        yes_btn = QPushButton('Подтвердить')
        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        yes_btn.clicked.connect(dialog.accept)
        layout.addWidget(yes_btn)
        
        no_btn = QPushButton('Отмена')
        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        no_btn.clicked.connect(dialog.reject)
        layout.addWidget(no_btn)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.data.complete_supervision_stage(self.card_data['id'])
                self.data.add_supervision_history(
                    self.card_data['id'],
                    self.employee['id'],
                    'submitted',
                    f"Стадия '{column_name}' сдана на проверку"
                )
                
                success_dialog = QDialog(self)
                success_dialog.setWindowTitle('Успех')
                success_dialog.setMinimumWidth(450)
                
                success_layout = QVBoxLayout()
                success_layout.setSpacing(15)
                success_layout.setContentsMargins(20, 20, 20, 20)
                
                success_title = QLabel('Работа сдана!')
                success_title.setStyleSheet('font-size: 13px; font-weight: bold; color: #27AE60;')
                success_title.setAlignment(Qt.AlignCenter)
                success_layout.addWidget(success_title)
                
                success_text = QLabel('Ожидайте согласования менеджера для\nперемещения на следующую стадию.')
                success_text.setStyleSheet('font-size: 11px; color: #555;')
                success_text.setWordWrap(True)
                success_text.setAlignment(Qt.AlignCenter)
                success_layout.addWidget(success_text)
                
                ok_btn = QPushButton('OK')
                ok_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffd93c;
                        color: white;
                        padding: 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #2980B9; }
                """)
                ok_btn.clicked.connect(success_dialog.accept)
                success_layout.addWidget(ok_btn)
                
                success_dialog.setLayout(success_layout)
                success_dialog.exec_()
                
                self.refresh_parent_tab()
                
            except Exception as e:
                print(f" Ошибка сдачи работы: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось сдать работу: {e}', 'error').exec_()
                
    def mouseDoubleClickEvent(self, event):
        """Двойной клик по карточке → редактирование."""
        self.edit_card()

    def edit_card(self):
        """Редактирование карточки"""
        dialog = SupervisionCardEditDialog(self, self.card_data, self.employee, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_parent_tab()
            
    def refresh_parent_tab(self):
        """Обновление родительской вкладки"""
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMSupervisionTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()
    
    @debounce_click(delay_ms=2000)
    def accept_work(self):
        """Принятие работы менеджером"""
        column_name = self.card_data.get('column_name', 'N/A')
        dan_name = self.card_data.get('dan_name', 'ДАН')
        
        dialog = QDialog(self)
        dialog.setWindowTitle('Подтверждение')
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(15, 15, 15, 15)
        
        title = QLabel('Принять работу по стадии:')
        title.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        stage_frame = QFrame()
        stage_frame.setStyleSheet('''
            QFrame {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        ''')
        stage_layout = QVBoxLayout()
        stage_layout.setContentsMargins(0, 0, 0, 0)
        
        stage_label = QLabel(f'"{column_name}"')
        stage_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #2C3E50;')
        stage_label.setWordWrap(True)
        stage_label.setAlignment(Qt.AlignCenter)
        stage_layout.addWidget(stage_label)
        
        stage_frame.setLayout(stage_layout)
        layout.addWidget(stage_frame)
        
        executor_label = QLabel(f'Исполнитель: {dan_name}')
        executor_label.setStyleSheet('font-size: 11px; color: #555;')
        executor_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(executor_label)
        
        yes_btn = QPushButton('Принять')
        yes_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        yes_btn.clicked.connect(dialog.accept)
        layout.addWidget(yes_btn)
        
        no_btn = QPushButton('Отмена')
        no_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        no_btn.clicked.connect(dialog.reject)
        layout.addWidget(no_btn)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.data.add_supervision_history(
                    self.card_data['id'],
                    self.employee['id'],
                    'accepted',
                    f"Стадия '{column_name}' принята менеджером. Исполнитель: {dan_name}"
                )
                self.data.reset_supervision_stage_completion(self.card_data['id'])
                
                success_dialog = QDialog(self)
                success_dialog.setWindowTitle('Успех')
                success_dialog.setMinimumWidth(450)
                
                success_layout = QVBoxLayout()
                success_layout.setSpacing(15)
                success_layout.setContentsMargins(20, 20, 20, 20)
                
                success_title = QLabel(f'Работа по стадии "{column_name}" принята!')
                success_title.setStyleSheet('font-size: 13px; font-weight: bold; color: #27AE60;')
                success_title.setWordWrap(True)
                success_title.setAlignment(Qt.AlignCenter)
                success_layout.addWidget(success_title)
                
                success_text = QLabel('Теперь переместите карточку на следующую стадию.')
                success_text.setStyleSheet('font-size: 11px; color: #555;')
                success_text.setWordWrap(True)
                success_text.setAlignment(Qt.AlignCenter)
                success_layout.addWidget(success_text)
                
                ok_btn = QPushButton('OK')
                ok_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #ffd93c;
                        color: white;
                        padding: 12px;
                        border-radius: 4px;
                        font-size: 12px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #2980B9; }
                """)
                ok_btn.clicked.connect(success_dialog.accept)
                success_layout.addWidget(ok_btn)
                
                success_dialog.setLayout(success_layout)
                success_dialog.exec_()
                
                self.refresh_parent_tab()
                
            except Exception as e:
                print(f" Ошибка принятия работы: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось принять работу: {e}', 'error').exec_()
             
    def add_project_note(self):
        """Добавление записи в историю проекта"""
        dialog = AddProjectNoteDialog(self, self.card_data['id'], self.employee, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_parent_tab()




# Импорты диалогов (в конце файла для избежания циклических импортов)
from ui.supervision_card_edit_dialog import SupervisionCardEditDialog
from ui.supervision_dialogs import (PauseDialog, SupervisionStatisticsDialog,
    SupervisionCompletionDialog, AddProjectNoteDialog,
    SupervisionStageDeadlineDialog, SupervisionReassignDANDialog,
    AssignExecutorsDialog, SupervisionFileUploadDialog)
