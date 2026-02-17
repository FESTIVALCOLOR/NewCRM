from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QDateEdit,
                             QListWidget, QListWidgetItem, QTabWidget, QTextEdit,
                             QTableWidget, QHeaderView, QTableWidgetItem, QGroupBox,
                             QSpinBox, QFileDialog, QProgressDialog)
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
from utils.data_access import DataAccess
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

class SupervisionDraggableList(QListWidget):
    """Draggable список для надзора"""
    item_dropped = pyqtSignal(int, object)
    
    def __init__(self, parent_column, can_drag=True):
        super().__init__()
        self.parent_column = parent_column
        self.can_drag = can_drag
        
        if self.can_drag:
            self.setDragDropMode(QListWidget.DragDrop)
            self.setDefaultDropAction(Qt.MoveAction)
            self.setAcceptDrops(True)
            self.setDragEnabled(True)
        else:
            self.setDragDropMode(QListWidget.NoDragDrop)
        
        self.setSelectionMode(QListWidget.SingleSelection)
    
    def startDrag(self, supportedActions):
        if not self.can_drag:
            return
        super().startDrag(supportedActions)
    
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

        # Учитываем secondary_position для роли ДАН
        _pos = employee.get('position', '') if employee else ''
        _sec = employee.get('secondary_position', '') if employee else ''
        self.is_dan_role = (_pos == 'ДАН' or _sec == 'ДАН')

        self._data_loaded = False
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
            'Стадия 7: Лепного декора',
            'Стадия 8: Освещения',
            'Стадия 9: бытовой техники',
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
            cards = self.data.get_supervision_cards_archived()

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
            agents = self.db.get_all_agents()
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
            cards = self.data.get_supervision_cards_archived()

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
        """Ленивая загрузка: данные загружаются при первом показе таба"""
        if not self._data_loaded:
            self._data_loaded = True
            self.data.prefer_local = True
            self.load_cards_for_current_tab()
            self.data.prefer_local = False

    def load_cards_for_current_tab(self):
        """Загрузка карточек для текущей вкладки"""
        self.load_active_cards()
        if not self.is_dan_role:
            self.load_archive_cards()
            
    def load_active_cards(self):
        """Загрузка активных карточек с fallback на локальную БД"""
        try:
            cards = self.data.get_supervision_cards_active()
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
        if index == 0:
            self.load_active_cards()
        elif index == 1:
            self.load_archive_cards()
    
    def on_card_moved(self, card_id, from_column, to_column):
        """Обработка перемещения карточки"""
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
                        QMessageBox.warning(
                            self,
                            'Работа не принята',
                            f'ДАН сдал работу, но вы еще не приняли её!\n\n'
                            f'Сначала нажмите кнопку "Принять работу" на карточке,\n'
                            f'затем переместите её на следующую стадию.'
                        )
                        self.load_cards_for_current_tab()
                        return

                    # Если ДАН НЕ сдал работу, но руководство перемещает - автоматически принимаем
                    if dan_completed == 0 and (self.employee.get('position', '') in ['Руководитель студии', 'Старший менеджер проектов'] or self.employee.get('secondary_position', '') in ['Руководитель студии', 'Старший менеджер проектов']):
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

                        conn = self.db.connect()
                        cursor = conn.cursor()

                        # Получаем contract_id
                        cursor.execute('SELECT contract_id FROM supervision_cards WHERE id = ?', (card_id,))
                        card_row = cursor.fetchone()

                        if card_row:
                            contract_id = card_row['contract_id']

                            # Проверяем, есть ли уже оплаты для этой стадии
                            cursor.execute('''
                            SELECT id FROM payments
                            WHERE supervision_card_id = ?
                              AND stage_name = ?
                            ''', (card_id, from_column))

                            existing_payments = cursor.fetchall()

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
                                        if self.api_client:
                                            try:
                                                dan_amount = self.api_client.calculate_payment_amount(
                                                    contract_id, executors_row['dan_id'], 'ДАН',
                                                    stage_name=from_column, supervision_card_id=card_id
                                                )
                                            except Exception as e:
                                                print(f"    [WARN] Ошибка расчёта суммы ДАН: {e}")
                                                dan_amount = self.db.calculate_payment_amount(
                                                    contract_id, executors_row['dan_id'], 'ДАН',
                                                    stage_name=from_column, supervision_card_id=card_id
                                                )
                                        else:
                                            dan_amount = self.db.calculate_payment_amount(
                                                contract_id, executors_row['dan_id'], 'ДАН',
                                                stage_name=from_column, supervision_card_id=card_id
                                            )

                                        if self.api_client:
                                            try:
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
                                                result = self.api_client.create_payment(payment_data)
                                                print(f"    Создана оплата для ДАН через API по стадии '{from_column}': {dan_amount} руб")
                                            except Exception as e:
                                                print(f"    [WARNING] Ошибка создания оплаты ДАН через API: {e}")
                                                self.db.close()
                                                payment_id = self.db.create_payment_record(
                                                    contract_id,
                                                    executors_row['dan_id'],
                                                    'ДАН',
                                                    stage_name=from_column,
                                                    payment_type='Полная оплата',
                                                    report_month=current_month,
                                                    supervision_card_id=card_id
                                                )
                                                conn = self.db.connect()
                                                cursor = conn.cursor()
                                        else:
                                            self.db.close()
                                            payment_id = self.db.create_payment_record(
                                                contract_id,
                                                executors_row['dan_id'],
                                                'ДАН',
                                                stage_name=from_column,
                                                payment_type='Полная оплата',
                                                report_month=current_month,
                                                supervision_card_id=card_id
                                            )
                                            if payment_id:
                                                print(f"    Создана оплата для ДАН по стадии '{from_column}' (ID={payment_id})")
                                            conn = self.db.connect()
                                            cursor = conn.cursor()

                                    # Создаем оплату для Старшего менеджера
                                    if executors_row['senior_manager_id']:
                                        # ИСПРАВЛЕНО 06.02.2026: Рассчитываем сумму перед созданием платежа
                                        smp_amount = 0
                                        if self.api_client:
                                            try:
                                                smp_amount = self.api_client.calculate_payment_amount(
                                                    contract_id, executors_row['senior_manager_id'], 'Старший менеджер проектов',
                                                    stage_name=from_column, supervision_card_id=card_id
                                                )
                                            except Exception as e:
                                                print(f"    [WARN] Ошибка расчёта суммы СМП: {e}")
                                                smp_amount = self.db.calculate_payment_amount(
                                                    contract_id, executors_row['senior_manager_id'], 'Старший менеджер проектов',
                                                    stage_name=from_column, supervision_card_id=card_id
                                                )
                                        else:
                                            smp_amount = self.db.calculate_payment_amount(
                                                contract_id, executors_row['senior_manager_id'], 'Старший менеджер проектов',
                                                stage_name=from_column, supervision_card_id=card_id
                                            )

                                        if self.api_client:
                                            try:
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
                                                result = self.api_client.create_payment(payment_data)
                                                print(f"    Создана оплата для СМП через API по стадии '{from_column}': {smp_amount} руб")
                                            except Exception as e:
                                                print(f"    [WARNING] Ошибка создания оплаты СМП через API: {e}")
                                                self.db.close()
                                                payment_id = self.db.create_payment_record(
                                                    contract_id,
                                                    executors_row['senior_manager_id'],
                                                    'Старший менеджер проектов',
                                                    stage_name=from_column,
                                                    payment_type='Полная оплата',
                                                    report_month=current_month,
                                                    supervision_card_id=card_id
                                                )
                                                conn = self.db.connect()
                                                cursor = conn.cursor()
                                        else:
                                            self.db.close()
                                            payment_id = self.db.create_payment_record(
                                                contract_id,
                                                executors_row['senior_manager_id'],
                                                'Старший менеджер проектов',
                                                stage_name=from_column,
                                                payment_type='Полная оплата',
                                                report_month=current_month,
                                                supervision_card_id=card_id
                                            )
                                            if payment_id:
                                                print(f"    Создана оплата для СМП по стадии '{from_column}' (ID={payment_id})")
                                            conn = self.db.connect()
                                            cursor = conn.cursor()
                            else:
                                # Если оплаты уже есть, обновляем отчетный месяц
                                cursor.execute('''
                                UPDATE payments
                                SET report_month = ?
                                WHERE supervision_card_id = ?
                                  AND stage_name = ?
                                  AND (report_month IS NULL OR report_month = '')
                                ''', (current_month, card_id, from_column))

                                updated_count = cursor.rowcount
                                conn.commit()

                                if updated_count > 0:
                                    print(f"    + Обновлен отчетный месяц ({current_month}) для {updated_count} оплат стадии '{from_column}'")

                        self.db.close()

            # Обновляем колонку в БД с fallback логикой
            api_success = False
            if self.api_client:
                try:
                    self.api_client.move_supervision_card(card_id, to_column)
                    api_success = True
                    print(f"   + [API] Карточка перемещена")
                except Exception as api_error:
                    print(f"   ! [API ERROR] {api_error}")
                    print(f"     [FALLBACK] Сохранение в локальную БД...")

            # Fallback на локальную БД
            if not api_success:
                self.db.update_supervision_card_column(card_id, to_column)
                print(f"   + [DB] Карточка перемещена")

            # Сбрасываем приостановку при перемещении
            if to_column != from_column:
                if self.api_client:
                    try:
                        self.api_client.resume_supervision_card(card_id, self.employee['id'])
                        self.api_client.reset_supervision_stage_completion(card_id)
                    except Exception as e:
                        print(f"[WARN] API ошибка сброса: {e}")
                        self.db.resume_supervision_card(card_id, self.employee['id'])
                        self.db.reset_supervision_stage_completion(card_id)
                else:
                    self.db.resume_supervision_card(card_id, self.employee['id'])
                    self.db.reset_supervision_stage_completion(card_id)
                print(f"   + Отметка о сдаче сброшена")
                
            # Запрос дедлайна при перемещении (только для менеджеров)
            if not self.is_dan_role:
                skip_deadline_columns = ['Новый заказ', 'Выполненный проект']
                
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
            QMessageBox.critical(self, 'Ошибка', f'Не удалось переместить карточку: {e}')
    
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
            QMessageBox.warning(self, 'Ошибка', 'Укажите причину расторжения')
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
        """
        try:
            print(f"[SYNC] Получено обновление карточек надзора: {len(updated_cards)} записей")
            # Обновляем текущую вкладку
            self.refresh_current_tab()
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


class SupervisionColumn(QFrame):
    """Колонка для карточек надзора"""
    card_moved = pyqtSignal(int, str, str)

    def __init__(self, column_name, employee, db, api_client=None):
        super().__init__()
        self.column_name = column_name
        self.employee = employee
        self.db = db
        self.api_client = api_client
        _pos = employee.get('position', '') if employee else ''
        _sec = employee.get('secondary_position', '') if employee else ''
        self.is_dan_role = (_pos == 'ДАН' or _sec == 'ДАН')
        self.header_label = None
        # ИСПРАВЛЕНИЕ 07.02.2026: Добавлено сворачивание колонок с сохранением состояния (#19)
        self._is_collapsed = False
        self._original_min_width = 340
        self._original_max_width = 360
        self._collapsed_width = 50
        self.vertical_label = None
        # Настройки для сохранения состояния
        self._settings = TableSettings()
        self._board_name = "crm_supervision"
        self.init_ui()
        # Загружаем сохранённое состояние
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
        self.cards_list.setFocusPolicy(Qt.NoFocus)
        self.cards_list.setSpacing(5)
        
        layout.addWidget(self.cards_list, 1)
        self.setLayout(layout)
    
    # ИСПРАВЛЕНИЕ 07.02.2026: Применение начального состояния сворачивания (#19)
    def _apply_initial_collapse_state(self):
        """Применить начальное состояние сворачивания (из настроек)"""
        saved_state = self._settings.get_column_collapsed_state(
            self._board_name, self.column_name, default=None
        )
        if saved_state:
            self._collapse_column()

    def _collapse_column(self):
        """Свернуть колонку (без сохранения состояния)"""
        self._is_collapsed = True
        self.cards_list.hide()
        self.header_label.hide()
        self.collapse_btn.setIcon(IconLoader.load('arrow-right-circle'))
        self.collapse_btn.setToolTip('Развернуть колонку')
        self.setMinimumWidth(self._collapsed_width)
        self.setMaximumWidth(self._collapsed_width)

        if self.vertical_label is None:
            self.vertical_label = VerticalLabelSupervision()
            self.layout().insertWidget(1, self.vertical_label, 1)

        count = self.cards_list.count() if hasattr(self, 'cards_list') else 0
        short_name = self.column_name
        self.vertical_label.setText(f"{short_name} ({count})")
        self.vertical_label.show()

    def _expand_column(self):
        """Развернуть колонку (без сохранения состояния)"""
        self._is_collapsed = False
        self.cards_list.show()
        self.header_label.show()
        self.collapse_btn.setIcon(IconLoader.load('arrow-left-circle'))
        self.collapse_btn.setToolTip('Свернуть колонку')
        self.setMinimumWidth(self._original_min_width)
        self.setMaximumWidth(self._original_max_width)

        if self.vertical_label:
            self.vertical_label.hide()

    # ИСПРАВЛЕНИЕ 07.02.2026: Метод сворачивания колонки с сохранением (#19)
    def toggle_collapse(self):
        """Переключение состояния сворачивания колонки"""
        if self._is_collapsed:
            self._expand_column()
        else:
            self._collapse_column()

        # Сохраняем новое состояние
        self._settings.save_column_collapsed_state(
            self._board_name, self.column_name, self._is_collapsed
        )

    def update_header_count(self):
        """Обновление счетчика"""
        count = self.cards_list.count() if hasattr(self, 'cards_list') else 0

        if count == 0:
            self.header_label.setText(self.column_name)
        else:
            self.header_label.setText(f"{self.column_name} ({count})")

        # Также обновляем вертикальный лейбл если колонка свёрнута
        if self._is_collapsed and self.vertical_label:
            self.vertical_label.setText(f"{self.column_name} ({count})")
    
    def add_card(self, card_data, bulk=False):
        """Добавление карточки. bulk=True пропускает update_header_count."""
        card_widget = SupervisionCard(card_data, self.employee, self.db, self.api_client)

        recommended_size = card_widget.sizeHint()
        exact_height = recommended_size.height()
        card_widget.setMinimumHeight(exact_height)

        item = QListWidgetItem()
        item.setData(Qt.UserRole, card_data.get('id'))
        item.setSizeHint(QSize(200, exact_height + 10))

        self.cards_list.addItem(item)
        self.cards_list.setItemWidget(item, card_widget)

        if not bulk:
            self.update_header_count()
    
    def clear_cards(self):
        """Очистка карточек"""
        self.cards_list.clear()
        self.update_header_count()

class SupervisionCard(QFrame):
    """Карточка авторского надзора"""

    def __init__(self, card_data, employee, db, api_client=None):
        super().__init__()
        self.card_data = card_data
        self.employee = employee
        self.db = db
        self.api_client = api_client
        _pos = employee.get('position', '') if employee else ''
        _sec = employee.get('secondary_position', '') if employee else ''
        self.is_dan_role = (_pos == 'ДАН' or _sec == 'ДАН')
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
            # Тип агента
            agent_label = QLabel(self.card_data['agent_type'])
            agent_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
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
            deadline_label = QLabel(f"Дедлайн: {self.card_data['deadline']}")
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
        self.team_toggle_btn = QPushButton(f"Команда ({len(team_members)})  ▶")
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
            self.team_toggle_btn.setText(self.team_toggle_btn.text().replace('▼', '▶'))
            print("  Команда свернута")
        else:
            self.team_container.show()
            self.team_toggle_btn.setText(self.team_toggle_btn.text().replace('▶', '▼'))
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
        dialog = PauseDialog(self, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            reason = dialog.reason_text.toPlainText().strip()
            if reason:
                if self.api_client and self.api_client.is_online:
                    try:
                        self.api_client.pause_supervision_card(
                            self.card_data['id'],
                            reason
                        )
                    except Exception as e:
                        print(f"[WARN] API ошибка pause_card: {e}")
                        self.db.pause_supervision_card(
                            self.card_data['id'],
                            reason,
                            self.employee['id']
                        )
                else:
                    self.db.pause_supervision_card(
                        self.card_data['id'],
                        reason,
                        self.employee['id']
                    )
                self.refresh_parent_tab()
                
    def resume_card(self):
        """Возобновление карточки"""
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
        
        yes_btn = QPushButton('▶ Возобновить')
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
            if self.api_client:
                try:
                    self.api_client.resume_supervision_card(
                        self.card_data['id'],
                        self.employee['id']
                    )
                except Exception as e:
                    print(f"[WARN] API ошибка resume_card: {e}")
                    self.db.resume_supervision_card(
                        self.card_data['id'],
                        self.employee['id']
                    )
            else:
                self.db.resume_supervision_card(
                    self.card_data['id'],
                    self.employee['id']
                )
            self.refresh_parent_tab()
            
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
                if self.api_client:
                    try:
                        self.api_client.complete_supervision_stage(self.card_data['id'])
                        self.api_client.add_supervision_history(
                            self.card_data['id'],
                            'submitted',
                            f"Стадия '{column_name}' сдана на проверку",
                            self.employee['id']
                        )
                    except Exception as e:
                        print(f"[WARN] API ошибка submit_work: {e}")
                        self.db.complete_supervision_stage(self.card_data['id'])
                        self.db.add_supervision_history(
                            self.card_data['id'],
                            'submitted',
                            f"Стадия '{column_name}' сдана на проверку",
                            self.employee['id']
                        )
                else:
                    self.db.complete_supervision_stage(self.card_data['id'])
                    self.db.add_supervision_history(
                        self.card_data['id'],
                        'submitted',
                        f"Стадия '{column_name}' сдана на проверку",
                        self.employee['id']
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
                QMessageBox.critical(self, 'Ошибка', f'Не удалось сдать работу: {e}')
                
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
                if self.api_client:
                    try:
                        self.api_client.add_supervision_history(
                            self.card_data['id'],
                            'accepted',
                            f"Стадия '{column_name}' принята менеджером. Исполнитель: {dan_name}",
                            self.employee['id']
                        )
                        self.api_client.reset_supervision_stage_completion(self.card_data['id'])
                    except Exception as e:
                        print(f"[WARN] API ошибка accept_work: {e}")
                        self.db.add_supervision_history(
                            self.card_data['id'],
                            'accepted',
                            f"Стадия '{column_name}' принята менеджером. Исполнитель: {dan_name}",
                            self.employee['id']
                        )
                        self.db.reset_supervision_stage_completion(self.card_data['id'])
                else:
                    self.db.add_supervision_history(
                        self.card_data['id'],
                        'accepted',
                        f"Стадия '{column_name}' принята менеджером. Исполнитель: {dan_name}",
                        self.employee['id']
                    )
                    self.db.reset_supervision_stage_completion(self.card_data['id'])
                
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
                QMessageBox.critical(self, 'Ошибка', f'Не удалось принять работу: {e}')
             
    def add_project_note(self):
        """Добавление записи в историю проекта"""
        dialog = AddProjectNoteDialog(self, self.card_data['id'], self.employee, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_parent_tab()

class PauseDialog(QDialog):
    """Диалог приостановки"""

    def __init__(self, parent, api_client=None):
        super().__init__(parent)
        self.api_client = api_client
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: none;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Приостановка проекта', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel('⏸ Приостановка проекта')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #F39C12;')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        label = QLabel('Укажите причину приостановки:')
        label.setStyleSheet('font-size: 11px; color: #555;')
        layout.addWidget(label)
        
        self.reason_text = QTextEdit()
        self.reason_text.setPlaceholderText('Например: Ожидание решения клиента...')
        self.reason_text.setMinimumHeight(120)
        self.reason_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #DDD;
                border-radius: 4px;
                padding: 8px;
                font-size: 11px;
            }
        """)
        layout.addWidget(self.reason_text)
        
        hint = QLabel('Эта информация будет сохранена в истории проекта')
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic;')
        layout.addWidget(hint)
        
        ok_btn = QPushButton('Приостановить')
        ok_btn.setFixedHeight(36)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(500)
    
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)
        
class SupervisionCardEditDialog(QDialog):
    """Диалог редактирования/просмотра карточки надзора"""

    # Сигналы для потокобезопасной загрузки файлов
    supervision_upload_completed = pyqtSignal(str, str, str, str, str, int)  # file_name, stage, date, public_link, yandex_path, contract_id
    supervision_upload_error = pyqtSignal(str)  # error_msg
    _reload_files_signal = pyqtSignal()  # потокобезопасный сигнал для перезагрузки списка файлов
    _sync_ended = pyqtSignal()  # Сигнал завершения фоновой синхронизации

    def __init__(self, parent, card_data, employee, api_client=None):
        super().__init__(parent)
        self.card_data = card_data
        self.employee = employee
        self.data = getattr(parent, 'data', DataAccess(api_client=api_client))
        self.db = self.data.db
        self.api_client = self.data.api_client
        _pos = employee.get('position', '') if employee else ''
        _sec = employee.get('secondary_position', '') if employee else ''
        self.is_dan_role = (_pos == 'ДАН' or _sec == 'ДАН')

        # Инициализация Yandex Disk
        try:
            self.yandex_disk = YandexDiskManager(YANDEX_DISK_TOKEN)
        except Exception as e:
            print(f"[WARNING] Не удалось инициализировать Yandex Disk: {e}")
            self.yandex_disk = None

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        # Переменные для изменения размера окна
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
        self.resize_margin = 8

        self._loading_data = False

        # Синхронизация (до init_ui, т.к. init_ui вызывает load_supervision_files -> validate)
        self._active_sync_count = 0
        self._sync_ended.connect(self._on_sync_ended)

        self.init_ui()
        self.load_data()

        # ИСПРАВЛЕНИЕ: Подключаем автосохранение после загрузки данных
        if not self.is_dan_role:
            self.connect_autosave_signals()

        # Подключаем сигналы загрузки файлов
        self.supervision_upload_completed.connect(self._on_supervision_upload_completed)
        self.supervision_upload_error.connect(self._on_supervision_upload_error)
        self._reload_files_signal.connect(lambda: self.load_supervision_files(validate=False))

    def _get_contract_yandex_folder(self, contract_id):
        """Получение пути к папке договора на Яндекс.Диске"""
        if not contract_id:
            return None

        try:
            if self.api_client:
                contract = self.api_client.get_contract(contract_id)
                return contract.get('yandex_folder_path') if contract else None
            else:
                contract = self.db.get_contract_by_id(contract_id)
                return contract.get('yandex_folder_path') if contract else None
        except Exception as e:
            print(f"[ERROR SupervisionCardEditDialog] Ошибка получения пути к папке договора: {e}")
            return None

    def init_ui(self):
        title = 'История проекта' if self.is_dan_role else 'Редактирование карточки надзора'

        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, title, simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Вкладки
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::tab-bar {
                left: 20px;
            }
        """)

        # ВКЛАДКА 1: РЕДАКТИРОВАНИЕ (только для менеджеров)
        if not self.is_dan_role:
            edit_widget = QWidget()
            edit_layout = QVBoxLayout()
            edit_layout.setContentsMargins(20, 15, 20, 20)

            form_layout = QFormLayout()

            # Старший менеджер
            self.senior_manager = CustomComboBox()
            if self.api_client:
                try:
                    managers = self.api_client.get_employees_by_position('Старший менеджер проектов')
                except Exception as e:
                    print(f"[WARN] API ошибка загрузки менеджеров: {e}")
                    managers = self.db.get_employees_by_position('Старший менеджер проектов')
            else:
                managers = self.db.get_employees_by_position('Старший менеджер проектов')
            self.senior_manager.addItem('Не назначен', None)
            for manager in managers:
                self.senior_manager.addItem(manager['full_name'], manager['id'])
            form_layout.addRow('Старший менеджер:', self.senior_manager)

            # ДАН
            self.dan = CustomComboBox()
            if self.api_client:
                try:
                    dans = self.api_client.get_employees_by_position('ДАН')
                except Exception as e:
                    print(f"[WARN] API ошибка загрузки ДАН: {e}")
                    dans = self.db.get_employees_by_position('ДАН')
            else:
                dans = self.db.get_employees_by_position('ДАН')
            self.dan.addItem('Не назначен', None)
            for dan in dans:
                self.dan.addItem(dan['full_name'], dan['id'])

            # ИСПРАВЛЕНИЕ 28.01.2026: Добавляем кнопку переназначения ДАН
            dan_row = QHBoxLayout()
            dan_row.addWidget(self.dan)

            reassign_dan_btn = IconLoader.create_icon_button(
                'refresh-black',
                'Переназначить',
                'Выбрать другого ДАН',
                icon_size=12
            )
            reassign_dan_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    color: #333;
                    padding: 4px 8px;
                    border: none;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #BDBDBD; }
            """)
            reassign_dan_btn.clicked.connect(self.reassign_dan)
            dan_row.addWidget(reassign_dan_btn)
            dan_row.addStretch()

            form_layout.addRow('ДАН:', dan_row)

            # ========== НОВОЕ: ПОДКЛЮЧЕНИЕ АВТОМАТИЧЕСКОГО СОЗДАНИЯ ВЫПЛАТ ==========
            # Подключаем обработчики изменения сотрудников для автоматического
            # создания/обновления записей о выплатах
            self.senior_manager.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.senior_manager, 'Старший менеджер проектов')
            )
            self.dan.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.dan, 'ДАН')
            )
            # =========================================================================

            # Дата начала надзора
            start_date_row = QHBoxLayout()
            start_date_row.setSpacing(8)

            self.start_date_edit = CustomDateEdit()
            self.start_date_edit.setCalendarPopup(True)
            self.start_date_edit.setDisplayFormat('dd.MM.yyyy')
            self.start_date_edit.setDate(QDate.currentDate())
            add_today_button_to_dateedit(self.start_date_edit)
            start_date_row.addWidget(self.start_date_edit)

            edit_start_btn = QPushButton('Изменить дату')
            edit_start_btn.setFixedHeight(28)
            edit_start_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0; color: #333333;
                    padding: 0px 10px; border-radius: 4px; border: none;
                    font-size: 10px; font-weight: bold;
                }
                QPushButton:hover { background-color: #D0D0D0; }
            """)
            edit_start_btn.clicked.connect(self._on_start_date_manual_change)
            start_date_row.addWidget(edit_start_btn)

            # Кнопка приостановить / возобновить
            if self.card_data.get('is_paused'):
                self.pause_btn = QPushButton('Возобновить')
                self.pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60; color: white;
                        padding: 0px 10px; border-radius: 4px; border: none;
                        font-size: 10px; font-weight: bold; min-height: 28px;
                    }
                    QPushButton:hover { background-color: #229954; }
                """)
                self.pause_btn.clicked.connect(self._resume_from_edit_tab)
            else:
                self.pause_btn = QPushButton('Приостановить')
                self.pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F39C12; color: white;
                        padding: 0px 10px; border-radius: 4px; border: none;
                        font-size: 10px; font-weight: bold; min-height: 28px;
                    }
                    QPushButton:hover { background-color: #E67E22; }
                """)
                self.pause_btn.clicked.connect(self._pause_from_edit_tab)
            self.pause_btn.setFixedHeight(28)
            start_date_row.addWidget(self.pause_btn)

            form_layout.addRow('Дата начала:', start_date_row)

            # Дедлайн
            self.deadline = CustomDateEdit()
            self.deadline.setCalendarPopup(True)
            self.deadline.setDate(QDate.currentDate())
            add_today_button_to_dateedit(self.deadline)
            form_layout.addRow('Дедлайн:', self.deadline)

            # Теги
            self.tags = QLineEdit()
            self.tags.setPlaceholderText('Срочный, VIP...')
            form_layout.addRow('Теги:', self.tags)

            edit_layout.addLayout(form_layout)
            edit_layout.addStretch()
            edit_widget.setLayout(edit_layout)

            self.tabs.addTab(edit_widget, 'Редактирование')

        # ВКЛАДКИ: Отложенное создание тяжёлых вкладок (после showEvent)
        # Лёгкие placeholder'ы — реальные виджеты создаются в _init_deferred_tabs()
        self.sv_timeline_widget = None
        self._timeline_placeholder = QWidget()
        self._timeline_tab_index = self.tabs.addTab(self._timeline_placeholder, 'Таблица сроков')

        self._payments_placeholder = QWidget()
        self.payments_tab_index = self.tabs.addTab(self._payments_placeholder, 'Оплаты надзора')

        self._info_placeholder = QWidget()
        self.project_info_tab_index = self.tabs.addTab(self._info_placeholder, 'Информация о проекте')

        # Надпись синхронизации
        self.sync_label = QLabel('Синхронизация...')
        self.sync_label.setStyleSheet('color: #999999; font-size: 11px;')
        self.sync_label.setVisible(False)

        self._files_placeholder = QWidget()
        self.files_tab_index = self.tabs.addTab(self._files_placeholder, 'Файлы надзора')

        self._deferred_tabs_ready = False

        layout.addWidget(self.tabs, 1)

        # Кнопки
        buttons_layout = QHBoxLayout()

        # Кнопка удаления заказа (только для Руководителя студии)
        if self.employee.get('position', '') == 'Руководитель студии' or self.employee.get('secondary_position', '') == 'Руководитель студии':
            delete_btn = IconLoader.create_icon_button('delete', 'Удалить заказ', 'Полностью удалить заказ', icon_size=12)
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    padding: 10px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #C0392B; }
            """)
            delete_btn.clicked.connect(self.delete_order)
            buttons_layout.addWidget(delete_btn)

        buttons_layout.addWidget(self.sync_label)
        buttons_layout.addStretch()

        if not self.is_dan_role:
            save_btn = QPushButton('Сохранить')
            save_btn.setStyleSheet('padding: 10px 20px; font-weight: bold;')
            save_btn.clicked.connect(self.save_changes)
            buttons_layout.addWidget(save_btn)

        close_btn = QPushButton('Закрыть')
        close_btn.setStyleSheet('padding: 10px 20px;')
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # ========== ИСПРАВЛЕНИЕ: ДИНАМИЧЕСКИЕ РАЗМЕРЫ ==========
        from PyQt5.QtWidgets import QDesktopWidget
        available_screen = QDesktopWidget().availableGeometry()

        # 90% от высоты экрана
        target_height = int(available_screen.height() * 0.90)

        # Ширина: фиксированная 1200px
        target_width = 1200

        self.setMinimumWidth(1100)
        self.setFixedHeight(target_height)
        self.resize(target_width, target_height)
        # =======================================================
    
    def create_history_widget(self):
        """Создание виджета истории"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        header = QLabel('История ведения проекта')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)
        
        # Кнопка добавления записи
        add_btn = IconLoader.create_icon_button('note', 'Добавить запись', 'Добавить запись в историю', icon_size=12)
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        add_btn.clicked.connect(self.add_history_entry)
        layout.addWidget(add_btn)
        
        # Скролл с историей
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #DDD; border-radius: 4px; background: white; }")

        history_container = QWidget()
        self.history_layout = QVBoxLayout()
        self.history_layout.setSpacing(10)
        self.history_layout.setContentsMargins(10, 10, 10, 10)

        # Загружаем историю
        if self.api_client:
            try:
                history = self.api_client.get_supervision_history(self.card_data['id'])
            except Exception as e:
                print(f"[WARN] API ошибка загрузки истории: {e}")
                history = self.db.get_supervision_history(self.card_data['id'])
        else:
            history = self.db.get_supervision_history(self.card_data['id'])
        
        if history:
            for entry in history:
                entry_widget = self.create_history_entry_widget(entry)
                self.history_layout.addWidget(entry_widget)
        else:
            empty_label = QLabel('История пуста')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            self.history_layout.addWidget(empty_label)
        
        self.history_layout.addStretch()
        
        history_container.setLayout(self.history_layout)
        scroll.setWidget(history_container)
        
        layout.addWidget(scroll, 1)
        
        widget.setLayout(layout)
        return widget
    
    def create_history_entry_widget(self, entry):
        """Создание виджета записи истории"""
        entry_frame = QFrame()
        
        # Цвет в зависимости от типа
        entry_type = entry.get('entry_type', 'note')
        
        if entry_type == 'pause':
            bg_color = '#FFF3CD'
            icon = '⏸'
        elif entry_type == 'resume':
            bg_color = '#ffffff'
            icon = '▶'
        elif entry_type == 'submitted':
            bg_color = '#D6EAF8'
            icon = ''
        elif entry_type == 'accepted':
            bg_color = '#D5F4E6'
            icon = ''
        else:
            bg_color = '#F8F9FA'
            icon = ''
        
        entry_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
        """)
        
        entry_layout = QVBoxLayout()
        entry_layout.setSpacing(2)
        entry_layout.setContentsMargins(6, 4, 6, 4)
        
        # Заголовок с датой
        created_at = entry.get('created_at', '')
        created_by = entry.get('created_by_name', 'Система')
        
        header_label = QLabel(f"{icon} {created_at} | {created_by}")
        header_label.setStyleSheet('font-size: 9px; font-weight: bold; color: #555;')
        entry_layout.addWidget(header_label)
        
        # Сообщение
        message_label = QLabel(entry.get('message', ''))
        message_label.setWordWrap(True)
        message_label.setStyleSheet('font-size: 10px; color: #333;')
        entry_layout.addWidget(message_label)
        
        entry_frame.setLayout(entry_layout)
        return entry_frame
    
    def add_history_entry(self):
        """Добавление новой записи в историю"""
        dialog = AddProjectNoteDialog(self, self.card_data['id'], self.employee, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.reload_history()
    
    def reload_history(self):
        """Перезагрузка истории"""
        # Очищаем
        while self.history_layout.count():
            child = self.history_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Загружаем заново
        if self.api_client:
            try:
                history = self.api_client.get_supervision_history(self.card_data['id'])
            except Exception as e:
                print(f"[WARN] API ошибка refresh_history: {e}")
                history = self.db.get_supervision_history(self.card_data['id'])
        else:
            history = self.db.get_supervision_history(self.card_data['id'])
        
        if history:
            for entry in history:
                entry_widget = self.create_history_entry_widget(entry)
                self.history_layout.addWidget(entry_widget)
        else:
            empty_label = QLabel('История пуста')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            self.history_layout.addWidget(empty_label)
        
        self.history_layout.addStretch()

    def delete_order(self):
        """Удаление заказа надзора"""
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            f"Вы точно хотите удалить заказ?\n\n"
            f"Договор: {self.card_data.get('contract_number', 'N/A')}\n"
            f"Адрес: {self.card_data.get('address', 'N/A')}\n\n"
            f"ВНИМАНИЕ: Это действие нельзя отменить!\n"
            f"Будут удалены:\n"
            f"• Карточка надзора в CRM\n"
            f"• Договор\n"
            f"• Все связанные данные (история, оплаты)"
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                contract_id = self.card_data.get('contract_id')
                supervision_card_id = self.card_data.get('id')

                if self.api_client:
                    try:
                        self.api_client.delete_supervision_order(contract_id, supervision_card_id)
                    except Exception as e:
                        print(f"[WARN] API ошибка delete_supervision_order: {e}")
                        self.db.delete_supervision_order(contract_id, supervision_card_id)
                else:
                    self.db.delete_supervision_order(contract_id, supervision_card_id)

                CustomMessageBox(
                    self,
                    'Успех',
                    'Заказ успешно удален из системы',
                    'success'
                ).exec_()
                self.accept()

                # Обновляем родительскую вкладку
                parent = self.parent()
                while parent:
                    if hasattr(parent, 'load_cards_for_current_tab'):
                        parent.load_cards_for_current_tab()
                        break
                    parent = parent.parent()

            except Exception as e:
                print(f" Ошибка удаления заказа надзора: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить заказ:\n{str(e)}', 'error').exec_()

    def create_payments_widget(self):
        """ИСПРАВЛЕНИЕ: Создание виджета оплат НАДЗОРА"""
        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлены стили как в основном CRM (#25)
        GROUP_BOX_STYLE = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2C3E50;
            }
        """

        TABLE_STYLE = """
            QTableWidget {
                background-color: #FFFFFF;
                border: none;
                gridline-color: #e0e0e0;
            }
            QTableWidget::item {
                padding: 4px;
            }
            QTableWidget::item:selected {
                background-color: #FFFFFF;
                color: #333333;
            }
            QHeaderView::section {
                background-color: #f5f5f5;
                padding: 6px;
                border: none;
                border-bottom: 1px solid #d9d9d9;
                font-weight: bold;
                font-size: 10px;
            }
        """

        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 20)

        contract_id = self.card_data.get('contract_id')

        # ИСПРАВЛЕНИЕ 06.02.2026: Используем GroupBox как в основном CRM
        payments_group = QGroupBox("Оплаты надзора")
        payments_group.setStyleSheet(GROUP_BOX_STYLE)
        payments_layout = QVBoxLayout()

        # Таблица оплат - используем ProportionalResizeTable
        from PyQt5.QtWidgets import QTableWidget, QHeaderView, QTableWidgetItem, QHBoxLayout
        table = ProportionalResizeTable()
        # ИСПРАВЛЕНИЕ 06.02.2026: Применяем TABLE_STYLE
        table.setStyleSheet(TABLE_STYLE + """
            QTableCornerButton::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
        """)
        table.setColumnCount(9)
        table.setHorizontalHeaderLabels([
            'Должность', 'ФИО', 'Стадия', 'Тип выплаты',
            'Выплата', 'Аванс', 'Доплата', 'Отчетный месяц', 'Действия'
        ])

        # ИСПРАВЛЕНИЕ: Получаем ТОЛЬКО оплаты надзора
        if contract_id:
            if self.api_client:
                try:
                    payments = self.api_client.get_payments_for_supervision(contract_id)
                except Exception as e:
                    print(f"[WARN] API ошибка get_payments_for_supervision: {e}")
                    payments = self.db.get_payments_for_supervision(contract_id)
            else:
                payments = self.db.get_payments_for_supervision(contract_id)

            # ИСПРАВЛЕНИЕ 30.01.2026: Сортировка платежей надзора
            # Приоритет по ролям: СМП -> ДАН -> остальные
            role_priority = {
                'Старший менеджер проектов': 1,
                'СМП': 1,
                'ДАН': 2,
            }
            payment_type_priority = {
                'Аванс': 1,
                'Доплата': 2,
                'Полная оплата': 3,
            }

            def payment_sort_key(p):
                role = p.get('role', '')
                ptype = p.get('payment_type', '')
                payment_id = p.get('id', 0)
                return (
                    role_priority.get(role, 99),
                    payment_type_priority.get(ptype, 99),
                    payment_id  # Стабильная сортировка по ID
                )

            payments = sorted(payments, key=payment_sort_key)
            table.setRowCount(len(payments))

            for row, payment in enumerate(payments):
                # Определяем цвет строки в зависимости от статуса оплаты
                from PyQt5.QtGui import QColor
                is_reassigned = payment.get('reassigned', False)
                payment_status = payment.get('payment_status')
                if is_reassigned:
                    row_color = QColor('#FFF9C4')  # Светло-желтый для переназначения
                elif payment_status == 'to_pay':
                    row_color = QColor('#FFF3CD')  # Светло-желтый
                elif payment_status == 'paid':
                    row_color = QColor('#D4EDDA')  # Светло-зеленый
                else:
                    row_color = QColor('#FFFFFF')  # Белый

                # Должность
                role_label = QLabel(payment.get('role', ''))
                role_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                role_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 0, role_label)

                # ФИО
                employee_name = payment.get('employee_name', '')
                if is_reassigned:
                    employee_name = f"* {employee_name} *"
                name_label = QLabel(employee_name)
                if is_reassigned:
                    name_label.setStyleSheet(f"background-color: {row_color.name()}; font-weight: bold; border-radius: 2px;")
                    old_emp_id = payment.get('old_employee_id')
                    if old_emp_id:
                        try:
                            old_emp = self.db.get_employee_by_id(old_emp_id)
                            old_emp_name = old_emp.get('full_name', 'Неизвестный') if old_emp else 'Неизвестный'
                        except Exception:
                            old_emp_name = 'Неизвестный'
                        name_label.setToolTip(f'Переназначено от: {old_emp_name}')
                    else:
                        name_label.setToolTip('Переназначенная выплата')
                else:
                    name_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 1, name_label)

                # Стадия
                stage_label = QLabel(payment.get('stage_name', '') or '-')
                stage_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                stage_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 2, stage_label)

                # Тип выплаты
                type_label = QLabel(payment.get('payment_type', ''))
                type_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                type_label.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 3, type_label)

                # Выплата
                final_amount = payment.get('final_amount', 0)
                amount_label = QLabel(f"{final_amount:,.2f} ₽")
                amount_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                amount_label.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 4, amount_label)

                # Аванс/Доплата
                payment_type = payment.get('payment_type', '')
                if payment_type == 'Аванс':
                    advance_label = QLabel(f"{final_amount:,.2f} ₽")
                    advance_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    advance_label.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 5, advance_label)

                    balance_empty = QLabel('-')
                    balance_empty.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    balance_empty.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 6, balance_empty)
                elif payment_type == 'Доплата':
                    advance_empty = QLabel('-')
                    advance_empty.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    advance_empty.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 5, advance_empty)

                    balance_label = QLabel(f"{final_amount:,.2f} ₽")
                    balance_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    balance_label.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 6, balance_label)
                else:
                    advance_empty2 = QLabel('-')
                    advance_empty2.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    advance_empty2.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 5, advance_empty2)

                    balance_empty2 = QLabel('-')
                    balance_empty2.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    balance_empty2.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 6, balance_empty2)

                # Отчетный месяц
                from utils.date_utils import format_month_year
                formatted_month = format_month_year(payment.get('report_month', ''))
                month_label = QLabel(formatted_month)
                month_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                month_label.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 7, month_label)

                # Кнопки действий (столбец 8, только для руководителей)
                if self.employee.get('position', '') in ['Руководитель студии', 'Старший менеджер проектов'] or self.employee.get('secondary_position', '') in ['Руководитель студии', 'Старший менеджер проектов']:
                    actions_widget = QWidget()
                    actions_widget.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                    actions_layout = QHBoxLayout()
                    actions_layout.setContentsMargins(2, 2, 2, 2)
                    actions_layout.setSpacing(4)

                    # Кнопка корректировки (иконка edit2)
                    adj_btn = IconLoader.create_icon_button('edit2', '', 'Изменить сумму', icon_size=12)
                    adj_btn.setFixedSize(20, 20)
                    adj_btn.setStyleSheet('''
                        QPushButton {
                            background-color: #d4e4bc;
                            border: 1px solid #c0d4a8;
                            border-radius: 4px;
                            padding: 0px;
                        }
                        QPushButton:hover {
                            background-color: #c0d4a8;
                        }
                    ''')
                    adj_btn.clicked.connect(
                        lambda checked, p_id=payment['id']: self.adjust_payment_amount(p_id)
                    )
                    actions_layout.addWidget(adj_btn)

                    # Кнопка удаления (иконка delete2)
                    del_btn = IconLoader.create_icon_button('delete2', '', 'Удалить выплату', icon_size=12)
                    del_btn.setFixedSize(20, 20)
                    del_btn.setStyleSheet('''
                        QPushButton {
                            background-color: #FFE6E6;
                            border: 1px solid #FFCCCC;
                            border-radius: 4px;
                            padding: 0px;
                        }
                        QPushButton:hover {
                            background-color: #FFCCCC;
                        }
                    ''')
                    del_btn.clicked.connect(
                        lambda checked, p_id=payment['id'], p_role=payment['role'], p_name=payment['employee_name']:
                        self.delete_payment(p_id, p_role, p_name)
                    )
                    actions_layout.addWidget(del_btn)

                    actions_layout.setAlignment(Qt.AlignCenter)
                    actions_widget.setLayout(actions_layout)
                    table.setCellWidget(row, 8, actions_widget)

        # Настройка пропорционального изменения размера колонок
        # Колонки: Должность, ФИО, Стадия, Тип выплаты, Выплата, Аванс, Доплата, Отчетный месяц, фикс: Действия
        table.setup_proportional_resize(
            column_ratios=[0.11, 0.18, 0.13, 0.11, 0.10, 0.09, 0.09, 0.13],
            fixed_columns={8: 80},
            min_width=50
        )

        # НЕ используем setAlternatingRowColors, чтобы можно было окрашивать строки вручную
        table.setAlternatingRowColors(False)
        # ВАЖНО: НЕ устанавливаем background-color для QTableWidget,
        # чтобы цвета ячеек работали корректно
        table.setStyleSheet("""
            QTableWidget {
                border: 1px solid #d9d9d9;
                border-radius: 8px;
                gridline-color: #E0E0E0;
            }
            QTableWidget::item {
                padding: 1px;
            }
            QHeaderView::section {
                background-color: #F5F5F5;
                padding: 4px;
                border: none;
                border-bottom: 2px solid #E0E0E0;
                font-weight: bold;
            }
        """)

        # Запрещаем изменение высоты строк
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setDefaultSectionSize(32)

        payments_layout.addWidget(table)

        # Блок-запись о переназначении и итого (используем уже загруженные payments)
        if contract_id and payments:
            has_reassigned = any(p.get('reassigned') for p in payments)
            if has_reassigned:
                warning_label = QLabel(
                    '<b>ВНИМАНИЕ!</b> Обнаружено переназначение сотрудников (строки выделены жёлтым).'
                )
                warning_label.setStyleSheet('''
                    background-color: #FFF3CD; color: #856404; border: 2px solid #FFC107;
                    border-radius: 4px; padding: 10px; font-size: 11px; margin: 10px 0;
                ''')
                warning_label.setWordWrap(True)
                payments_layout.addWidget(warning_label)

            # Итого: исключаем переназначенные (старые) записи, чтобы не было двойного подсчёта
            total = sum(p.get('final_amount', 0) for p in payments if not p.get('reassigned', False))
            total_label = QLabel(f'<b>Итого:</b> {total:,.2f} ₽')
            total_label.setStyleSheet('''
                font-size: 14px;
                padding: 10px;
                background-color: #f5f5f5;
                border-radius: 5px;
                margin-top: 10px;
            ''')
            payments_layout.addWidget(total_label)

        # ИСПРАВЛЕНИЕ 06.02.2026: Закрываем GroupBox
        payments_group.setLayout(payments_layout)
        layout.addWidget(payments_group)
        layout.addStretch()

        widget.setLayout(layout)
        return widget

    def delete_payment(self, payment_id, role, employee_name):
        """ИСПРАВЛЕНИЕ 30.01.2026: Удаление записи об оплате с API синхронизацией"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            f'Вы уверены, что хотите удалить оплату?\n\n'
            f'Должность: {role}\n'
            f'ФИО: {employee_name}\n\n'
            f'Это действие нельзя отменить!'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                # ИСПРАВЛЕНИЕ: Сначала пробуем API, потом локальную БД
                if self.api_client and self.api_client.is_online:
                    try:
                        self.api_client.delete_payment(payment_id)
                        print(f"[API] Оплата удалена: {role} - {employee_name} (ID: {payment_id})")
                    except Exception as api_error:
                        print(f"[WARN] Ошибка API удаления: {api_error}, fallback на локальную БД")
                        self._delete_payment_locally(payment_id)
                else:
                    self._delete_payment_locally(payment_id)
                    print(f"[LOCAL] Оплата удалена: {role} - {employee_name} (ID: {payment_id})")

                # Показываем сообщение об успехе
                CustomMessageBox(
                    self,
                    'Успех',
                    f'Оплата успешно удалена:\n{role} - {employee_name}',
                    'success'
                ).exec_()

                # Обновляем вкладку оплат
                self.refresh_payment_tab()

            except Exception as e:
                print(f"Ошибка удаления оплаты: {e}")
                import traceback
                traceback.print_exc()

                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить оплату:\n{str(e)}',
                    'error'
                ).exec_()

    def _delete_payment_locally(self, payment_id):
        """Вспомогательный метод для удаления платежа локально"""
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM payments WHERE id = ?', (payment_id,))
        conn.commit()
        self.db.close()

    def adjust_payment_amount(self, payment_id):
        """ИСПРАВЛЕНИЕ 30.01.2026: Диалог корректировки с API синхронизацией"""
        from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QComboBox, QFrame
        from PyQt5.QtCore import Qt, QDate
        from ui.custom_title_bar import CustomTitleBar

        # ИСПРАВЛЕНИЕ: Сначала пробуем API, потом локальную БД
        payment = None
        if self.api_client and self.api_client.is_online:
            try:
                payment = self.api_client.get_payment(payment_id)
                print(f"[API] Загружены данные платежа {payment_id}")
            except Exception as api_error:
                print(f"[WARN] Ошибка API загрузки платежа: {api_error}, fallback на локальную БД")

        if not payment:
            # Fallback на локальную БД
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT p.*, e.full_name as employee_name
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            WHERE p.id = ?
            ''', (payment_id,))
            payment_row = cursor.fetchone()
            self.db.close()
            if not payment_row:
                return
            payment = dict(payment_row)
            print(f"[LOCAL] Загружены данные платежа {payment_id}")

        if not payment:
            return

        current_report_month = payment.get('report_month', '')
        current_amount = payment.get('manual_amount') if payment.get('is_manual') else payment.get('final_amount', 0)

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)

        title_bar = CustomTitleBar(dialog, 'Корректировка оплаты', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # ИСПРАВЛЕНИЕ: Уменьшены размеры на 30% (как в основной CRM)
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(14, 14, 14, 14)

        # Подсказка
        hint_label = QLabel('Введите новую сумму выплаты:')
        hint_label.setStyleSheet('font-size: 10px; color: #666666;')
        layout.addWidget(hint_label)

        # Поле ввода суммы с кастомными стрелками (как в основной CRM)
        amount_container = QWidget()
        amount_layout = QHBoxLayout()
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(4)

        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, 10000000)
        amount_spin.setSuffix(' ₽')
        amount_spin.setDecimals(2)
        amount_spin.setValue(current_amount)
        amount_spin.setSpecialValueText('Введите сумму...')
        amount_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)
        amount_spin.setStyleSheet("""
            QDoubleSpinBox {
                padding: 6px;
                font-size: 11px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #ffd93c;
            }
        """)
        amount_layout.addWidget(amount_spin, 1)

        # Кастомные кнопки вверх/вниз с иконками
        buttons_container = QWidget()
        buttons_vert_layout = QVBoxLayout()
        buttons_vert_layout.setContentsMargins(0, 0, 0, 0)
        buttons_vert_layout.setSpacing(0)

        up_btn = QPushButton()
        up_btn.setIcon(IconLoader.load('arrow-up-circle'))
        up_btn.setIconSize(QSize(12, 12))
        up_btn.setFixedSize(16, 16)
        up_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                min-height: 0px; max-height: 16px;
                min-width: 0px; max-width: 16px;
            }
            QPushButton:hover { background-color: #E8F8F5; border-radius: 3px; }
        """)
        up_btn.clicked.connect(lambda: amount_spin.stepUp())

        down_btn = QPushButton()
        down_btn.setIcon(IconLoader.load('arrow-down-circle'))
        down_btn.setIconSize(QSize(12, 12))
        down_btn.setFixedSize(16, 16)
        down_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
                min-height: 0px; max-height: 16px;
                min-width: 0px; max-width: 16px;
            }
            QPushButton:hover { background-color: #E8F8F5; border-radius: 3px; }
        """)
        down_btn.clicked.connect(lambda: amount_spin.stepDown())

        buttons_vert_layout.addWidget(up_btn)
        buttons_vert_layout.addWidget(down_btn)
        buttons_container.setLayout(buttons_vert_layout)

        amount_layout.addWidget(buttons_container)
        amount_container.setLayout(amount_layout)
        layout.addWidget(amount_container)

        # Отчетный месяц
        month_label = QLabel('Отчетный месяц:')
        month_label.setStyleSheet('font-size: 10px; color: #666666; margin-top: 10px;')
        layout.addWidget(month_label)

        month_layout = QHBoxLayout()
        month_layout.setSpacing(5)

        # Выбор месяца
        month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_combo.addItems(months)

        from datetime import datetime
        try:
            if current_report_month:
                date_obj = datetime.strptime(current_report_month, '%Y-%m')
                month_combo.setCurrentIndex(date_obj.month - 1)
            else:
                month_combo.setCurrentIndex(datetime.now().month - 1)
        except Exception:
            month_combo.setCurrentIndex(datetime.now().month - 1)
        month_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                font-size: 11px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #ffd93c;
            }
        """)
        month_layout.addWidget(month_combo, 1)

        # Выбор года
        year_combo = CustomComboBox()
        current_year = QDate.currentDate().year()
        for year in range(current_year - 2, current_year + 3):
            year_combo.addItem(str(year))

        try:
            if current_report_month:
                date_obj = datetime.strptime(current_report_month, '%Y-%m')
                year_combo.setCurrentText(str(date_obj.year))
            else:
                year_combo.setCurrentText(str(current_year))
        except Exception:
            year_combo.setCurrentText(str(current_year))
        year_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                font-size: 11px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #ffd93c;
            }
        """)
        month_layout.addWidget(year_combo)

        layout.addLayout(month_layout)

        # Кнопки
        buttons_layout = QHBoxLayout()

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 7px 14px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #ffce00; }
        """)
        save_btn.clicked.connect(
            lambda: self.save_manual_amount(payment_id, amount_spin.value(), month_combo.currentIndex() + 1, int(year_combo.currentText()), dialog)
        )

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 7px 14px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #CCCCCC; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        dialog.setLayout(main_layout)

        dialog.setFixedWidth(336)

        # Центрирование относительно родительского окна
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(dialog)

        # Автофокус на поле ввода + выделение текста
        amount_spin.setFocus()
        amount_spin.selectAll()

        dialog.exec_()

    def save_manual_amount(self, payment_id, amount, month, year, dialog):
        """ИСПРАВЛЕНИЕ 30.01.2026: Сохранение ручной суммы с API синхронизацией"""
        # Формируем отчетный месяц в формате YYYY-MM
        report_month = f"{year}-{month:02d}"

        # ИСПРАВЛЕНИЕ: Проверяем is_online для корректной работы offline режима
        if self.api_client and self.api_client.is_online:
            try:
                # Сбрасываем reassigned при редактировании
                self.api_client.update_payment(payment_id, {
                    'manual_amount': amount,
                    'final_amount': amount,
                    'is_manual': True,
                    'report_month': report_month,
                    'reassigned': False  # Сбрасываем флаг переназначения
                })
                print(f"[API] Платёж {payment_id} обновлён через API")
            except Exception as e:
                print(f"[WARN] API ошибка update_payment_manual: {e}, fallback на локальную БД")
                self._save_payment_locally(payment_id, amount, report_month)
        else:
            self._save_payment_locally(payment_id, amount, report_month)
            print(f"[LOCAL] Платёж {payment_id} обновлён локально")

        # Завершаем сохранение - обновляем UI
        self._finish_save_manual_amount(payment_id, amount, report_month, dialog)

    def _save_payment_locally(self, payment_id, amount, report_month):
        """Вспомогательный метод для сохранения платежа локально"""
        self.db.update_payment_manual(payment_id, amount)
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE payments
            SET report_month = ?,
                reassigned = 0
            WHERE id = ?
        ''', (report_month, payment_id))
        conn.commit()
        self.db.close()

    def _finish_save_manual_amount(self, payment_id, amount, report_month, dialog):
        """Завершение сохранения ручной суммы - обновление UI"""
        print(f"Оплата обновлена: ID={payment_id}, сумма={amount}, месяц={report_month}")

        # Закрываем диалог
        dialog.accept()

        # Обновляем вкладку оплат в карточке
        self.refresh_payment_tab()

        # Обновляем вкладку "Зарплаты" в главном окне
        try:
            # Ищем главное окно
            main_window = None
            widget = self.parent()
            while widget is not None:
                if widget.__class__.__name__ == 'MainWindow':
                    main_window = widget
                    break
                widget = widget.parent()

            if main_window and hasattr(main_window, 'tabs'):
                # Ищем вкладку SalariesTab
                from ui.salaries_tab import SalariesTab
                for i in range(main_window.tabs.count()):
                    tab_widget = main_window.tabs.widget(i)
                    if isinstance(tab_widget, SalariesTab):
                        # Обновляем данные в вкладке Зарплаты
                        if hasattr(tab_widget, 'load_all_payments'):
                            tab_widget.load_all_payments()
                        break
        except Exception as e:
            print(f"Предупреждение: не удалось обновить вкладку Зарплаты: {e}")

    def refresh_payment_tab(self):
        """Обновление вкладки оплат надзора"""
        try:
            # Находим индекс вкладки оплат надзора
            for i in range(self.tabs.count()):
                if self.tabs.tabText(i) == 'Оплаты надзора':
                    # Удаляем старую вкладку
                    self.tabs.removeTab(i)
                    # Создаем новую вкладку
                    payments_widget = self.create_payments_widget()
                    self.tabs.insertTab(i, payments_widget, 'Оплаты надзора')
                    self.tabs.setCurrentIndex(i)
                    print(f"Вкладка оплат обновлена")
                    break
        except Exception as e:
            print(f" Ошибка обновления вкладки оплат: {e}")

    def create_project_info_widget(self):
        """ИСПРАВЛЕНИЕ: Создание виджета информации о проекте с согласованиями"""
        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлены стили как в основном CRM (#22, #24)
        GROUP_BOX_STYLE = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2C3E50;
            }
        """

        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 20)

        # ИСПРАВЛЕНИЕ 06.02.2026: Используем GroupBox как в основном CRM
        info_group = QGroupBox("Информация о проекте")
        info_group.setStyleSheet(GROUP_BOX_STYLE)
        layout = QVBoxLayout()

        # ========== НОВОЕ: ПРИНЯТЫЕ СТАДИИ НАДЗОРА ==========
        # Показываем стадии надзора, которые были приняты менеджером
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            # Получаем принятые стадии из истории проекта надзора
            cursor.execute('''
            SELECT created_at, message
            FROM supervision_project_history
            WHERE supervision_card_id = ? AND entry_type = 'accepted'
            ORDER BY created_at ASC
            ''', (self.card_data['id'],))

            accepted_history = cursor.fetchall()
            self.db.close()

            if accepted_history:
                # Заголовок
                completed_header = QLabel('Принятые стадии:')
                completed_header.setStyleSheet('font-size: 11px; font-weight: bold; color: #27AE60; margin-bottom: 4px; margin-top: 4px;')
                layout.addWidget(completed_header)

                # Контейнер для стадий
                for history in accepted_history:
                    from utils.date_utils import format_date
                    date_str = format_date(history['created_at'])

                    # Извлекаем информацию из сообщения
                    # Формат: "Стадия 'название' принята менеджером. Исполнитель: ФИО"
                    message = history['message']

                    stage_label = QLabel(f"{message} | Дата: {date_str}")
                    stage_label.setStyleSheet('''
                        color: #27AE60;
                        font-size: 10px;
                        font-weight: bold;
                        background-color: #E8F8F5;
                        padding: 5px;
                        border-radius: 4px;
                        margin-bottom: 4px;
                    ''')
                    stage_label.setWordWrap(True)
                    layout.addWidget(stage_label)

        except Exception as e:
            print(f" Ошибка загрузки принятых стадий надзора: {e}")
            import traceback
            traceback.print_exc()
        # ===============================================

        # Сданные стадии (еще не согласованные)
        if self.api_client:
            try:
                submitted_stages = self.api_client.get_submitted_stages(self.card_data['id'])
            except Exception as e:
                print(f"[WARN] API ошибка get_submitted_stages: {e}")
                submitted_stages = self.db.get_submitted_stages(self.card_data['id'])
        else:
            submitted_stages = self.db.get_submitted_stages(self.card_data['id'])

        if submitted_stages:
            submitted_header = QLabel('Сданные стадии (ожидают согласования):')
            submitted_header.setStyleSheet('font-size: 11px; font-weight: bold; color: #ffd93c; margin-bottom: 4px;')
            layout.addWidget(submitted_header)

            submitted_container = QFrame()
            submitted_container.setStyleSheet('''
                QFrame {
                    background-color: #f5f5f5;
                    border: 2px solid #ffd93c;
                    border-radius: 4px;
                    padding: 8px;
                }
            ''')

            submitted_layout = QHBoxLayout()
            submitted_layout.setSpacing(6)
            submitted_layout.setContentsMargins(4, 4, 4, 4)

            for submitted in submitted_stages:
                stage_block = QFrame()
                stage_block.setStyleSheet('''
                    QFrame {
                        background-color: #ffd93c;
                        border: none;
                        border-radius: 4px;
                        min-width: 80px;
                        max-width: 150px;
                    }
                ''')

                block_layout = QVBoxLayout()
                block_layout.setSpacing(2)
                block_layout.setContentsMargins(8, 6, 8, 6)

                stage_name = QLabel(f"{submitted['stage_name']}")
                stage_name.setWordWrap(True)
                stage_name.setAlignment(Qt.AlignCenter)
                stage_name.setStyleSheet('font-size: 9px; color: white; font-weight: bold;')
                block_layout.addWidget(stage_name)

                executor = QLabel(submitted['executor_name'])
                executor.setWordWrap(True)
                executor.setAlignment(Qt.AlignCenter)
                executor.setStyleSheet('font-size: 8px; color: #D4E9F7;')
                block_layout.addWidget(executor)

                from utils.date_utils import format_date
                date_label = QLabel(f"Сдано: {format_date(submitted['submitted_date'])}")
                date_label.setAlignment(Qt.AlignCenter)
                date_label.setStyleSheet('font-size: 7px; color: #BBDEFB;')
                block_layout.addWidget(date_label)

                stage_block.setLayout(block_layout)
                submitted_layout.addWidget(stage_block)

            submitted_layout.addStretch()
            submitted_container.setLayout(submitted_layout)
            layout.addWidget(submitted_container)

        # СКРЫТО: Согласованные стадии (это стадии основного CRM, они уже отображены выше в "Принятых стадиях")
        # accepted_stages = self.db.get_accepted_stages(self.card_data['id'])
        #
        # if accepted_stages:
        #     acceptance_header = QLabel('Согласованные стадии:')
        #     acceptance_header.setStyleSheet('font-size: 11px; font-weight: bold; color: #27AE60; margin-bottom: 4px;')
        #     layout.addWidget(acceptance_header)
        #
        #     acceptance_container = QFrame()
        #     acceptance_container.setStyleSheet('''
        #         QFrame {
        #             background-color: #E8F8F5;
        #             border: 2px solid #27AE60;
        #             border-radius: 4px;
        #             padding: 8px;
        #         }
        #     ''')
        #
        #     acceptance_layout = QHBoxLayout()
        #     acceptance_layout.setSpacing(6)
        #     acceptance_layout.setContentsMargins(4, 4, 4, 4)
        #
        #     for accepted in accepted_stages:
        #         stage_block = QFrame()
        #         stage_block.setStyleSheet('''
        #             QFrame {
        #                 background-color: #27AE60;
        #                 border: none;
        #                 border-radius: 4px;
        #                 min-width: 80px;
        #                 max-width: 150px;
        #             }
        #         ''')
        #
        #         block_layout = QVBoxLayout()
        #         block_layout.setSpacing(2)
        #         block_layout.setContentsMargins(8, 6, 8, 6)
        #
        #         stage_name = QLabel(f"{accepted['stage_name']}")
        #         stage_name.setWordWrap(True)
        #         stage_name.setAlignment(Qt.AlignCenter)
        #         stage_name.setStyleSheet('font-size: 9px; color: white; font-weight: bold;')
        #         block_layout.addWidget(stage_name)
        #
        #         executor = QLabel(accepted['executor_name'])
        #         executor.setWordWrap(True)
        #         executor.setAlignment(Qt.AlignCenter)
        #         executor.setStyleSheet('font-size: 8px; color: #E8F8F5;')
        #         block_layout.addWidget(executor)
        #
        #         # Дата сдачи
        #         if accepted.get('submitted_date'):
        #             from utils.date_utils import format_date
        #             submitted_label = QLabel(f"{format_date(accepted['submitted_date'])}")
        #             submitted_label.setAlignment(Qt.AlignCenter)
        #             submitted_label.setStyleSheet('font-size: 7px; color: #BBDEFB;')
        #             block_layout.addWidget(submitted_label)
        #
        #         # Дата согласования
        #         from utils.date_utils import format_date
        #         date_label = QLabel(f"{format_date(accepted['accepted_date'])}")
        #         date_label.setAlignment(Qt.AlignCenter)
        #         date_label.setStyleSheet('font-size: 7px; color: #D5F4E6;')
        #         block_layout.addWidget(date_label)
        #
        #         stage_block.setLayout(block_layout)
        #         acceptance_layout.addWidget(stage_block)
        #
        #     acceptance_layout.addStretch()
        #     acceptance_container.setLayout(acceptance_layout)
        #     layout.addWidget(acceptance_container)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet('background-color: #E0E0E0; margin: 8px 0px;')
        separator.setFixedHeight(2)
        layout.addWidget(separator)

        # ИСПРАВЛЕНИЕ: История стадий с датами сдачи и принятия
        history_header = QLabel('История ведения проекта')
        history_header.setStyleSheet('font-size: 12px; font-weight: bold; margin-bottom: 8px;')
        layout.addWidget(history_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #DDD; border-radius: 4px; background: white; }")

        info_container = QWidget()
        info_layout = QVBoxLayout()
        info_layout.setSpacing(10)
        info_layout.setContentsMargins(10, 10, 10, 10)

        if self.api_client:
            try:
                stages = self.api_client.get_stage_history(self.card_data['id'])
            except Exception as e:
                print(f"[WARN] API ошибка get_stage_history: {e}")
                stages = self.db.get_stage_history(self.card_data['id'])
        else:
            stages = self.db.get_stage_history(self.card_data['id'])

        if stages:
            for stage in stages:
                stage_widget = self.create_stage_info_widget(stage)
                info_layout.addWidget(stage_widget)
        else:
            empty_label = QLabel('История проекта пуста')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            info_layout.addWidget(empty_label)

        info_layout.addStretch()

        info_container.setLayout(info_layout)
        scroll.setWidget(info_container)

        layout.addWidget(scroll, 1)

        # ИСПРАВЛЕНИЕ 06.02.2026: Закрываем GroupBox
        info_group.setLayout(layout)
        main_layout.addWidget(info_group)

        widget.setLayout(main_layout)
        return widget

    def create_stage_info_widget(self, stage):
        """ИСПРАВЛЕНИЕ: Создание виджета для записи о стадии с датами сдачи и принятия"""
        stage_frame = QFrame()

        if stage.get('completed'):
            bg_color = '#D5F4E6'
            icon = ''
        else:
            bg_color = '#FFF3CD'
            icon = '⏳'

        stage_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
                padding: 6px;
            }}
        """)

        stage_layout = QVBoxLayout()
        stage_layout.setSpacing(2)
        stage_layout.setContentsMargins(6, 4, 6, 4)

        header = QLabel(f"{icon} {stage.get('assigned_date', '')} | {stage.get('stage_name', 'N/A')}")
        header.setStyleSheet('font-size: 9px; font-weight: bold; color: #555;')
        stage_layout.addWidget(header)

        executor = QLabel(f"Исполнитель: {stage.get('executor_name', 'Не назначен')}")
        executor.setStyleSheet('font-size: 10px; color: #333;')
        stage_layout.addWidget(executor)

        deadline = QLabel(f"Дедлайн: {stage.get('deadline', 'N/A')}")
        deadline.setStyleSheet('font-size: 10px; color: #333;')
        stage_layout.addWidget(deadline)

        # Дата сдачи работы
        if stage.get('submitted_date'):
            submitted_label = QLabel(f"<b>Сдано:</b> {stage.get('submitted_date', 'N/A')}")
            submitted_label.setStyleSheet('font-size: 10px; color: #ffd93c;')
            stage_layout.addWidget(submitted_label)

        # Дата принятия (завершения)
        if stage.get('completed'):
            completed_label = QLabel(f"Принято: {stage.get('completed_date', 'N/A')}")
            completed_label.setStyleSheet('font-size: 10px; color: #27AE60; font-weight: bold;')
            stage_layout.addWidget(completed_label)

        stage_frame.setLayout(stage_layout)
        return stage_frame

    def refresh_payments_tab(self):
        """ИСПРАВЛЕНИЕ: Обновление вкладки оплат"""
        if hasattr(self, 'payments_tab_index') and self.payments_tab_index >= 0:
            try:
                # Находим tabs
                tabs = self.findChild(QTabWidget)
                if tabs:
                    old_widget = tabs.widget(self.payments_tab_index)
                    tabs.removeTab(self.payments_tab_index)
                    if old_widget:
                        old_widget.deleteLater()

                    payments_widget = self.create_payments_widget()
                    tabs.insertTab(self.payments_tab_index, payments_widget, 'Оплаты надзора')
                    print(f"Вкладка оплат обновлена")
            except Exception as e:
                print(f" Ошибка обновления вкладки оплат: {e}")

    def refresh_project_info_tab(self):
        """ИСПРАВЛЕНИЕ: Обновление вкладки информации о проекте"""
        if hasattr(self, 'project_info_tab_index') and self.project_info_tab_index >= 0:
            try:
                tabs = self.findChild(QTabWidget)
                if tabs:
                    old_widget = tabs.widget(self.project_info_tab_index)
                    tabs.removeTab(self.project_info_tab_index)
                    if old_widget:
                        old_widget.deleteLater()

                    info_widget = self.create_project_info_widget()
                    tabs.insertTab(self.project_info_tab_index, info_widget, 'Информация о проекте')
                    print(f"Вкладка информации о проекте обновлена")
            except Exception as e:
                print(f" Ошибка обновления вкладки информации: {e}")

    def create_files_widget(self):
        """Создание виджета файлов надзора"""
        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлены стили как в основном CRM (#23)
        GROUP_BOX_STYLE = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 10px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2C3E50;
            }
        """

        widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 15, 20, 20)

        # ИСПРАВЛЕНИЕ 06.02.2026: Используем GroupBox как в основном CRM
        files_group = QGroupBox("Файлы авторского надзора")
        files_group.setStyleSheet(GROUP_BOX_STYLE)
        layout = QVBoxLayout()

        # Кнопка загрузки по центру на половину ширины
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch(1)

        upload_btn = IconLoader.create_icon_button('upload', 'Загрузить файл', 'Загрузить файл на Яндекс.Диск', icon_size=12)
        upload_btn.setFixedHeight(32)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 6px 20px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 200px;
            }
            QPushButton:hover { background-color: #e6c435; }
        ''')
        upload_btn.clicked.connect(self.upload_supervision_file)
        buttons_layout.addWidget(upload_btn, 2)

        buttons_layout.addStretch(1)
        layout.addLayout(buttons_layout)

        # Таблица файлов
        self.files_table = QTableWidget()
        apply_no_focus_delegate(self.files_table)  # Убираем пунктирную рамку фокуса
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(['Название файла', 'Тип', 'Дата загрузки', 'Действия'])
        self.files_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.files_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.files_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectRows)

        # Запрещаем изменение высоты строк
        self.files_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.files_table.verticalHeader().setDefaultSectionSize(32)

        layout.addWidget(self.files_table, 1)  # stretch=1 чтобы таблица заняла всю высоту

        # Загружаем список файлов
        self.load_supervision_files()

        # ИСПРАВЛЕНИЕ 06.02.2026: Закрываем GroupBox
        files_group.setLayout(layout)
        main_layout.addWidget(files_group, 1)  # stretch=1 чтобы таблица заняла всю высоту

        widget.setLayout(main_layout)
        return widget

    def load_supervision_files(self, validate=True):
        """Загрузка списка файлов надзора"""
        if not hasattr(self, 'files_table'):
            return
        try:
            # Получаем contract_id из card_data
            contract_id = self.card_data.get('contract_id')
            if not contract_id:
                return

            files = []

            # Пробуем загрузить из API
            if self.api_client and self.api_client.is_online:
                try:
                    # Новый формат: stage='supervision'
                    api_files = self.api_client.get_project_files(contract_id, stage='supervision')

                    # Обратная совместимость: ищем старые файлы с file_type='Файл надзора'
                    if not api_files:
                        all_files = self.api_client.get_project_files(contract_id)
                        api_files = [f for f in (all_files or [])
                                     if f.get('file_type') == 'Файл надзора' or f.get('stage') == 'supervision']

                    if api_files:
                        files = [
                            {
                                'id': f.get('id'),
                                'file_name': f.get('file_name'),
                                'file_type': f.get('file_type'),
                                'yandex_path': f.get('yandex_path'),
                                'public_link': f.get('public_link'),
                                'created_at': f.get('upload_date') or f.get('created_at')
                            }
                            for f in api_files
                        ]
                        print(f"[API] Загружено {len(files)} файлов надзора")
                except Exception as api_err:
                    print(f"[WARN] Ошибка загрузки файлов из API: {api_err}")

            # Fallback на локальную БД
            if not files:
                conn = self.db.connect()
                cursor = conn.cursor()
                # stage='supervision' для новых файлов + file_type='Файл надзора' для старых
                cursor.execute('''
                    SELECT id, file_name, file_type, yandex_path, public_link, upload_date as created_at
                    FROM project_files
                    WHERE contract_id = ? AND (stage = 'supervision' OR file_type = 'Файл надзора')
                    ORDER BY upload_date DESC
                ''', (contract_id,))
                rows = cursor.fetchall()
                self.db.close()
                # Конвертируем в список словарей для унификации с API
                files = [
                    {
                        'id': r[0],
                        'file_name': r[1],
                        'file_type': r[2],
                        'yandex_path': r[3],
                        'public_link': r[4],
                        'created_at': r[5]
                    }
                    for r in rows
                ]

            self.files_table.setRowCount(len(files))

            for row, file_data in enumerate(files):
                # Название файла
                name_item = QTableWidgetItem(file_data['file_name'] or 'Без названия')
                name_item.setData(Qt.UserRole, file_data['id'])
                self.files_table.setItem(row, 0, name_item)

                # Тип
                type_item = QTableWidgetItem(file_data['file_type'] or 'Файл')
                self.files_table.setItem(row, 1, type_item)

                # Дата
                from utils.date_utils import format_date
                date_str = format_date(file_data['created_at']) if file_data['created_at'] else ''
                date_item = QTableWidgetItem(date_str)
                self.files_table.setItem(row, 2, date_item)

                # Кнопки действий
                actions_widget = QWidget()
                actions_layout = QHBoxLayout()
                actions_layout.setContentsMargins(4, 2, 4, 2)
                actions_layout.setSpacing(4)

                # Кнопка открыть (как во вкладке оплат)
                file_link = file_data.get('public_link') or ''
                file_yp = file_data.get('yandex_path') or ''
                if file_link or file_yp:
                    open_btn = IconLoader.create_icon_button('eye', '', 'Открыть файл', icon_size=12)
                    open_btn.setFixedSize(20, 20)
                    open_btn.setStyleSheet('''
                        QPushButton {
                            background-color: #d4e4bc;
                            border: 1px solid #c0d4a8;
                            border-radius: 4px;
                            padding: 0px;
                        }
                        QPushButton:hover {
                            background-color: #c0d4a8;
                        }
                    ''')
                    if file_link:
                        open_btn.clicked.connect(lambda checked, link=file_link: self.open_file_link(link))
                    else:
                        # Нет публичной ссылки — попробуем получить при клике
                        open_btn.clicked.connect(
                            lambda checked, yp=file_yp, fid=file_data['id']: self._open_file_by_yandex_path(yp, fid)
                        )
                        open_btn.setToolTip('Получить ссылку и открыть файл')
                    actions_layout.addWidget(open_btn)

                # Кнопка редактирования данных (бюджет, поставщик и т.д.)
                file_stage = file_data.get('file_type') or ''
                edit_data_btn = IconLoader.create_icon_button('settings', '', 'Редактировать данные файла', icon_size=12)
                edit_data_btn.setFixedSize(20, 20)
                edit_data_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #E3F2FD;
                        border: 1px solid #90CAF9;
                        border-radius: 4px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #BBDEFB;
                    }
                ''')
                edit_data_btn.clicked.connect(
                    lambda checked, fstage=file_stage, fid=file_data['id']: self._edit_file_timeline_data(fstage, fid)
                )
                actions_layout.addWidget(edit_data_btn)

                # Кнопка удалить (как во вкладке оплат)
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить файл', icon_size=12)
                delete_btn.setFixedSize(20, 20)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 4px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #FFCCCC;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, fid=file_data['id'], fpath=file_data['yandex_path']: self.delete_supervision_file(fid, fpath))
                actions_layout.addWidget(delete_btn)

                actions_layout.setAlignment(Qt.AlignCenter)
                actions_widget.setLayout(actions_layout)
                self.files_table.setCellWidget(row, 3, actions_widget)

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки файлов надзора: {e}")

        # Фоновая валидация файлов на Яндекс.Диске (только при первичной загрузке, не после валидации)
        if validate:
            self.validate_supervision_files_on_yandex()

    def _show_sync_label(self):
        """Показать надпись синхронизации"""
        self._active_sync_count += 1
        if hasattr(self, 'sync_label'):
            self.sync_label.setVisible(True)

    def _on_sync_ended(self):
        """Скрыть надпись синхронизации когда все операции завершены"""
        self._active_sync_count = max(0, self._active_sync_count - 1)
        if self._active_sync_count == 0 and hasattr(self, 'sync_label'):
            self.sync_label.setVisible(False)

    def validate_supervision_files_on_yandex(self):
        """Фоновая валидация файлов надзора на Яндекс.Диске"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        self._show_sync_label()

        def validate():
            try:
                # Step 1: Сканируем ЯД на наличие НОВЫХ файлов (не в БД)
                new_files_found = False
                if self.api_client and self.api_client.is_online:
                    try:
                        scan_result = self.api_client.scan_contract_files(contract_id, scope='supervision')
                        new_count = scan_result.get('new_files_added', 0)
                        if new_count > 0:
                            print(f"[YD-SYNC-SV] Найдено {new_count} новых файлов на ЯД")
                            new_files_found = True
                        else:
                            print(f"[YD-SYNC-SV] Новых файлов не найдено")
                    except Exception as scan_err:
                        print(f"[YD-SYNC-SV] Ошибка сканирования ЯД: {scan_err}")

                # Step 2: Загружаем текущий список файлов
                files = []

                # При наличии API — берём файлы с СЕРВЕРНЫМИ ID (для серверной валидации)
                if self.api_client and self.api_client.is_online:
                    try:
                        api_files = self.api_client.get_project_files(contract_id, stage='supervision')
                        if not api_files:
                            all_files = self.api_client.get_project_files(contract_id)
                            api_files = [f for f in (all_files or [])
                                         if f.get('file_type') == 'Файл надзора' or f.get('stage') == 'supervision']
                        if api_files:
                            files = api_files
                    except Exception as api_err:
                        print(f"[VALIDATE-SV] Ошибка загрузки файлов из API: {api_err}")

                # Fallback на локальную БД
                if not files:
                    local_db = DatabaseManager()
                    conn = local_db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT * FROM project_files
                        WHERE contract_id = ? AND (stage = 'supervision' OR file_type = 'Файл надзора')
                        ORDER BY upload_date DESC
                    ''', (contract_id,))
                    files = [dict(row) for row in cursor.fetchall()]
                    local_db.close()

                if not files:
                    print(f"[VALIDATE-SV] Нет файлов надзора для contract_id={contract_id}")
                    return

                print(f"[VALIDATE-SV] Найдено {len(files)} файлов надзора, проверяем...")

                # Серверная валидация (только если файлы загружены из API — ID серверные)
                removed_ids = []
                server_validated = False
                if self.api_client and self.api_client.is_online:
                    file_ids = [f['id'] for f in files if f.get('id')]
                    if file_ids:
                        try:
                            results = self.data.validate_files(file_ids, auto_clean=True)
                            if results:
                                removed_ids = [r['file_id'] for r in results if not r.get('exists', True)]
                                server_validated = True
                                print(f"[VALIDATE-SV] Серверная валидация: {len(removed_ids)} мёртвых")
                        except Exception as api_err:
                            print(f"[VALIDATE-SV] Серверная валидация не удалась: {api_err}")

                # Fallback: прямая проверка через Яндекс.Диск (для локальных файлов)
                if not server_validated:
                    from utils.yandex_disk import YandexDiskManager
                    from config import YANDEX_DISK_TOKEN
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    if not yd.token:
                        print("[VALIDATE-SV] Токен не установлен, пропуск")
                        return
                    for f in files:
                        yp = f.get('yandex_path')
                        fid = f.get('id')
                        if yp and fid:
                            if not yd.file_exists(yp):
                                removed_ids.append(fid)
                                print(f"[VALIDATE-SV] Файл не найден: {yp}")

                ui_needs_update = new_files_found

                if removed_ids:
                    if not server_validated:
                        # Удаляем только из локальной БД если валидация была локальной
                        local_db2 = DatabaseManager()
                        for fid in removed_ids:
                            try:
                                local_db2.delete_project_file(fid)
                            except Exception as del_err:
                                print(f"[VALIDATE-SV] Ошибка удаления файла {fid}: {del_err}")
                        local_db2.close()
                    print(f"[VALIDATE-SV] Удалено {len(removed_ids)} мёртвых файлов")
                    ui_needs_update = True
                else:
                    print(f"[VALIDATE-SV] Все файлы надзора на месте")

                if ui_needs_update:
                    try:
                        self._reload_files_signal.emit()
                    except RuntimeError:
                        pass

            except Exception as e:
                import traceback
                print(f"[ERROR] Ошибка валидации файлов надзора: {e}")
                traceback.print_exc()
            finally:
                try:
                    self._sync_ended.emit()
                except RuntimeError:
                    pass

        thread = threading.Thread(target=validate, daemon=True)
        thread.start()

    def upload_supervision_file(self):
        """Загрузка файла надзора на Яндекс.Диск с выбором стадии и даты"""
        if not self.yandex_disk:
            CustomMessageBox(self, 'Ошибка', 'Yandex Disk не инициализирован', 'error').exec_()
            return

        # Получаем путь к папке договора
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Не найден ID договора', 'error').exec_()
            return

        # Получаем папку договора через API или локальную БД
        contract_folder = self._get_contract_yandex_folder(contract_id)
        if not contract_folder:
            CustomMessageBox(self, 'Ошибка', 'Папка договора на Яндекс.Диске не найдена', 'error').exec_()
            return

        # Список стадий надзора для выбора (имена должны совпадать с SUPERVISION_STAGE_MAPPING)
        stages = list(SUPERVISION_STAGE_MAPPING.keys())

        # ИСПРАВЛЕНИЕ 07.02.2026: Открываем кастомный диалог загрузки файла (#23)
        dialog = SupervisionFileUploadDialog(self, self.card_data, stages, self.api_client)
        if dialog.exec_() != QDialog.Accepted:
            return

        # Получаем данные из диалога
        result = dialog.get_result()
        if not result:
            return

        file_path = result['file_path']
        stage = result['stage']
        date = result['date']
        file_name = result['file_name']

        # Сохраняем доп. данные для обновления таблицы сроков после загрузки
        self._upload_timeline_data = {
            'budget_planned': result.get('budget_planned', 0),
            'budget_actual': result.get('budget_actual', 0),
            'supplier': result.get('supplier', ''),
            'commission': result.get('commission', 0),
            'notes': result.get('notes', ''),
            'stage_name': stage,
        }

        # Прогресс загрузки с кастомным стилем
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QMetaObject, Q_ARG

        progress = QProgressDialog('Загрузка файла...', 'Отмена', 0, 100, self)
        progress.setWindowTitle('Загрузка на Яндекс.Диск')
        progress.setWindowModality(Qt.WindowModal)
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
            QLabel {
                color: #333333;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                text-align: center;
                background-color: #F5F5F5;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #ffd93c;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 5px 15px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover {
                background-color: #BDBDBD;
            }
        """)
        progress.show()
        QApplication.processEvents()

        # Сохраняем контекст для обработчиков
        self._upload_progress = progress
        self._upload_date = date

        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                # Создаем подпапку "Авторский надзор"
                supervision_folder = f"{contract_folder}/Авторский надзор"
                yd.create_folder(supervision_folder)

                # Создаем подпапку для стадии
                stage_folder = f"{supervision_folder}/{stage}"
                yd.create_folder(stage_folder)

                QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 30))
                QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection,
                                         Q_ARG(str, f"Загрузка: {file_name}..."))

                # Загружаем файл
                yandex_path = f"{stage_folder}/{file_name}"
                result_upload = yd.upload_file(file_path, yandex_path)

                QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 70))

                if result_upload:
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection,
                                             Q_ARG(str, "Получение публичной ссылки..."))
                    public_link = yd.get_public_link(yandex_path)

                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 100))
                    QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)

                    self.supervision_upload_completed.emit(
                        file_name, stage, date, public_link or '', yandex_path, contract_id
                    )
                else:
                    QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)
                    self.supervision_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
                QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)
                self.supervision_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_supervision_upload_completed(self, file_name, stage, date, public_link, yandex_path, contract_id):
        """Обработчик успешной загрузки файла надзора (вызывается из главного потока через сигнал)"""
        try:
            # Сохраняем в БД (локально)
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO project_files (contract_id, stage, file_type, yandex_path, public_link, file_name, upload_date)
                VALUES (?, 'supervision', ?, ?, ?, ?, datetime('now'))
            ''', (contract_id, stage, yandex_path, public_link, file_name))
            conn.commit()
            self.db.close()

            # Синхронизируем с API
            if self.api_client and self.api_client.is_online:
                try:
                    server_id = self.api_client.add_project_file(
                        contract_id=contract_id,
                        stage='supervision',
                        file_type=stage,
                        public_link=public_link or '',
                        yandex_path=yandex_path,
                        file_name=file_name
                    )
                    if server_id:
                        print(f"[API] Файл надзора синхронизирован, server_id={server_id}")
                    else:
                        print(f"[WARN] Файл сохранен локально, но не синхронизирован с сервером")
                except Exception as api_err:
                    print(f"[WARN] Ошибка синхронизации файла с API: {api_err}")

            # Обновляем таблицу сроков надзора (бюджет, поставщик, комиссия, примечания)
            extra = getattr(self, '_upload_timeline_data', None)
            if extra:
                stage_name = extra.get('stage_name', '')
                stage_code = SUPERVISION_STAGE_MAPPING.get(stage_name, '')
                if stage_code and self.card_data.get('id'):
                    timeline_updates = {}
                    if extra.get('budget_planned'):
                        timeline_updates['budget_planned'] = extra['budget_planned']
                    if extra.get('budget_actual'):
                        timeline_updates['budget_actual'] = extra['budget_actual']
                        # Пересчёт экономии
                        bp = extra.get('budget_planned', 0) or 0
                        ba = extra['budget_actual']
                        timeline_updates['budget_savings'] = bp - ba
                    if extra.get('supplier'):
                        timeline_updates['supplier'] = extra['supplier']
                    if extra.get('commission'):
                        timeline_updates['commission'] = extra['commission']
                    if extra.get('notes'):
                        timeline_updates['notes'] = extra['notes']

                    if timeline_updates:
                        try:
                            self.data.update_supervision_timeline_entry(
                                self.card_data['id'], stage_code, timeline_updates
                            )
                            print(f"[TIMELINE] Обновлены данные стадии {stage_code}: {timeline_updates}")
                        except Exception as tl_err:
                            print(f"[WARN] Ошибка обновления таблицы сроков: {tl_err}")

                self._upload_timeline_data = None

            CustomMessageBox(self, 'Успех', f'Файл "{file_name}" успешно загружен\nСтадия: {stage}\nДата: {date}', 'success').exec_()

            # Добавляем запись в историю проекта
            if self.employee:
                description = f"Добавлен файл надзора: {file_name} (Стадия: {stage}, Дата: {date})"
                self._add_action_history('file_upload', description)

            # Обновляем список файлов
            self.refresh_files_list()

            # Обновляем виджет таблицы сроков если он создан
            try:
                if hasattr(self, 'sv_timeline_widget') and self.sv_timeline_widget:
                    self.sv_timeline_widget._load_data()
            except Exception:
                pass

        except Exception as e:
            print(f"[ERROR] Ошибка сохранения файла надзора: {e}")
            CustomMessageBox(self, 'Ошибка', f'Файл загружен, но ошибка сохранения: {e}', 'error').exec_()

    def _on_supervision_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файла надзора"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки: {error_msg}', 'error').exec_()
        print(f"[ERROR] Ошибка загрузки файла надзора: {error_msg}")

    def delete_supervision_file(self, file_id, yandex_path):
        """Удаление файла надзора"""
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            'Вы уверены, что хотите удалить этот файл?\n\nФайл будет удален с Яндекс.Диска.'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        try:
            # Сначала удаляем через серверный API (удалит из серверной БД + с ЯД)
            if self.api_client and self.api_client.is_online:
                try:
                    self.api_client.delete_file_record(file_id)
                    print(f"[API] Файл надзора удален с сервера (БД + ЯД), id={file_id}")
                except Exception as api_err:
                    print(f"[ERROR] Ошибка удаления файла с сервера: {api_err}")
                    CustomMessageBox(self, 'Ошибка', f'Не удалось удалить файл с сервера: {api_err}', 'error').exec_()
                    return
                # Удаляем из локальной БД после успешного удаления на сервере
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM project_files WHERE id = ?', (file_id,))
                conn.commit()
                self.db.close()
            else:
                # Offline: удаляем локально и с ЯД напрямую
                if self.yandex_disk and yandex_path:
                    self.yandex_disk.delete_file(yandex_path)
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('DELETE FROM project_files WHERE id = ?', (file_id,))
                conn.commit()
                self.db.close()

            CustomMessageBox(self, 'Успех', 'Файл удален', 'success').exec_()

            # Добавляем запись в историю проекта
            if self.employee:
                description = f"Удален файл надзора"
                self._add_action_history('file_delete', description)

            # Обновляем список
            self.refresh_files_list()

        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось удалить файл: {e}', 'error').exec_()
            print(f"[ERROR] Ошибка удаления файла надзора: {e}")

    def refresh_files_list(self):
        """Обновление списка файлов с синхронизацией с Яндекс.Диском"""
        contract_id = self.card_data.get('contract_id')
        if contract_id and self.api_client and self.api_client.is_online:
            self._show_sync_label()
            # Сначала сканируем ЯД на наличие новых файлов (в фоне)
            def scan_thread():
                try:
                    result = self.api_client.scan_contract_files(contract_id, scope='supervision')
                    new_count = result.get('new_files_added', 0)
                    if new_count > 0:
                        print(f"[YD-SYNC] Найдено {new_count} новых файлов на ЯД для contract_id={contract_id}")
                    else:
                        print(f"[YD-SYNC] Новых файлов не найдено")
                except Exception as e:
                    print(f"[YD-SYNC] Ошибка сканирования ЯД: {e}")
                finally:
                    try:
                        self._sync_ended.emit()
                    except RuntimeError:
                        pass
                # В любом случае перезагружаем список (через сигнал — потокобезопасно)
                try:
                    self._reload_files_signal.emit()
                except RuntimeError:
                    pass

            thread = threading.Thread(target=scan_thread, daemon=True)
            thread.start()
        else:
            self.load_supervision_files()

    def _add_action_history(self, action_type: str, description: str, entity_type: str = 'supervision_card', entity_id: int = None):
        """ИСПРАВЛЕНИЕ 06.02.2026: Добавление метода записи истории действий (#22)"""
        if entity_id is None:
            entity_id = self.card_data['id']

        user_id = self.employee.get('id') if self.employee else None

        if self.api_client:
            try:
                history_data = {
                    'user_id': user_id,
                    'action_type': action_type,
                    'entity_type': entity_type,
                    'entity_id': entity_id,
                    'description': description
                }
                self.api_client.create_action_history(history_data)
                print(f"[API] История действий надзора записана: {action_type}")
            except Exception as e:
                print(f"[WARNING] Ошибка записи истории надзора через API: {e}")
                # Fallback на локальную БД
                self.db.add_action_history(
                    user_id=user_id,
                    action_type=action_type,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    description=description
                )
        else:
            self.db.add_action_history(
                user_id=user_id,
                action_type=action_type,
                entity_type=entity_type,
                entity_id=entity_id,
                description=description
            )

    def open_file_link(self, link):
        """Открытие ссылки на файл"""
        if link:
            from PyQt5.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(link))

    def _open_file_by_yandex_path(self, yandex_path, file_id):
        """Получить публичную ссылку по yandex_path и открыть файл"""
        try:
            if not self.yandex_disk:
                CustomMessageBox(self, 'Ошибка', 'Yandex Disk не инициализирован', 'error').exec_()
                return
            public_link = self.yandex_disk.get_public_link(yandex_path)
            if public_link:
                # Сохраняем ссылку в локальную БД чтобы не запрашивать повторно
                try:
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('UPDATE project_files SET public_link = ? WHERE id = ?', (public_link, file_id))
                    conn.commit()
                    self.db.close()
                except Exception:
                    pass
                self.open_file_link(public_link)
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось получить публичную ссылку', 'error').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка получения ссылки: {e}', 'error').exec_()

    def _edit_file_timeline_data(self, stage_name, file_id):
        """Редактирование данных файла (бюджет, поставщик, комиссия, примечания)"""
        # Определяем stage_code из stage_name
        stage_code = SUPERVISION_STAGE_MAPPING.get(stage_name, '')

        # Загружаем текущие данные из timeline если есть
        current_data = {}
        if stage_code and self.card_data.get('id'):
            try:
                entries = self.data.get_supervision_timeline(self.card_data['id'])
                for entry in (entries or []):
                    if entry.get('stage_code') == stage_code:
                        current_data = entry
                        break
            except Exception:
                pass

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setFixedWidth(420)

        main_layout = QVBoxLayout(dialog)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout(border_frame)
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        title_bar = CustomTitleBar(dialog, 'Редактирование данных стадии', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        content = QWidget()
        content.setStyleSheet('QWidget { background-color: #FFFFFF; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }')
        layout = QVBoxLayout(content)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)

        stage_label = QLabel(f'Стадия: {stage_name}')
        stage_label.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        layout.addWidget(stage_label)

        form = QFormLayout()
        form.setSpacing(8)
        form.setLabelAlignment(Qt.AlignRight)

        field_style = '''
            QLineEdit {
                border: 1px solid #E0E0E0; border-radius: 4px;
                padding: 4px 8px; font-size: 12px; background-color: #FAFAFA;
            }
            QLineEdit:focus { border-color: #ffd93c; background-color: #FFFFFF; }
        '''

        bp_edit = QLineEdit(str(current_data.get('budget_planned', 0) or ''))
        bp_edit.setFixedHeight(28)
        bp_edit.setPlaceholderText('0')
        bp_edit.setStyleSheet(field_style)
        form.addRow('Бюджет план:', bp_edit)

        ba_edit = QLineEdit(str(current_data.get('budget_actual', 0) or ''))
        ba_edit.setFixedHeight(28)
        ba_edit.setPlaceholderText('0')
        ba_edit.setStyleSheet(field_style)
        form.addRow('Бюджет факт:', ba_edit)

        sup_edit = QLineEdit(current_data.get('supplier', '') or '')
        sup_edit.setFixedHeight(28)
        sup_edit.setPlaceholderText('Название поставщика')
        sup_edit.setStyleSheet(field_style)
        form.addRow('Поставщик:', sup_edit)

        com_edit = QLineEdit(str(current_data.get('commission', 0) or ''))
        com_edit.setFixedHeight(28)
        com_edit.setPlaceholderText('0')
        com_edit.setStyleSheet(field_style)
        form.addRow('Комиссия:', com_edit)

        notes_edit = QLineEdit(current_data.get('notes', '') or '')
        notes_edit.setFixedHeight(28)
        notes_edit.setPlaceholderText('Примечания')
        notes_edit.setStyleSheet(field_style)
        form.addRow('Примечания:', notes_edit)

        layout.addLayout(form)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c; color: #333333; padding: 0px 20px;
                font-weight: bold; border-radius: 6px; border: none;
            }
            QPushButton:hover { background-color: #e6c435; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0; color: #333333; padding: 0px 20px;
                border-radius: 6px; border: none;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def parse_num(text):
            text = text.strip().replace(' ', '').replace(',', '.')
            try:
                return float(text) if text else 0
            except ValueError:
                return 0

        def save_data():
            if not stage_code or not self.card_data.get('id'):
                CustomMessageBox(dialog, 'Ошибка', 'Не удалось определить стадию', 'error').exec_()
                return

            bp = parse_num(bp_edit.text())
            ba = parse_num(ba_edit.text())
            updates = {
                'budget_planned': bp,
                'budget_actual': ba,
                'budget_savings': bp - ba,
                'supplier': sup_edit.text().strip(),
                'commission': parse_num(com_edit.text()),
                'notes': notes_edit.text().strip(),
            }

            try:
                self.data.update_supervision_timeline_entry(
                    self.card_data['id'], stage_code, updates
                )
                # Обновляем таблицу сроков если открыта
                if hasattr(self, 'sv_timeline_widget') and self.sv_timeline_widget:
                    self.sv_timeline_widget._load_data()
                dialog.accept()
            except Exception as e:
                CustomMessageBox(dialog, 'Ошибка', f'Ошибка сохранения: {e}', 'error').exec_()

        save_btn.clicked.connect(save_data)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(cancel_btn)
        layout.addLayout(btn_layout)

        border_layout.addWidget(content)
        main_layout.addWidget(border_frame)
        dialog.exec_()

    def load_data(self):
        """Загрузка данных (только для менеджеров)"""
        if self.is_dan_role:
            return

        self._loading_data = True

        # Старший менеджер
        for i in range(self.senior_manager.count()):
            if self.senior_manager.itemData(i) == self.card_data.get('senior_manager_id'):
                self.senior_manager.setCurrentIndex(i)
                break

        # ДАН
        for i in range(self.dan.count()):
            if self.dan.itemData(i) == self.card_data.get('dan_id'):
                self.dan.setCurrentIndex(i)
                break

        # Дата начала
        start_date_str = self.card_data.get('start_date', '')
        if start_date_str:
            if 'T' in start_date_str:
                start_date_str = start_date_str.split('T')[0]
            if ' ' in start_date_str:
                start_date_str = start_date_str.split(' ')[0]
            sd = QDate.fromString(start_date_str, 'yyyy-MM-dd')
            if sd.isValid():
                self.start_date_edit.setDate(sd)

        # Дедлайн
        if self.card_data.get('deadline'):
            self.deadline.setDate(QDate.fromString(self.card_data['deadline'], 'yyyy-MM-dd'))

        # Теги
        self.tags.setText(self.card_data.get('tags', ''))

        self._loading_data = False

    def connect_autosave_signals(self):
        """ИСПРАВЛЕНИЕ: Подключение сигналов для автосохранения данных при изменении"""
        self.senior_manager.currentIndexChanged.connect(self.auto_save_field)
        self.dan.currentIndexChanged.connect(self.auto_save_field)
        self.start_date_edit.dateChanged.connect(self.auto_save_field)
        self.deadline.dateChanged.connect(self.auto_save_field)
        self.tags.textChanged.connect(self.auto_save_field)

    def auto_save_field(self):
        """ИСПРАВЛЕНИЕ 30.01.2026: Автоматическое сохранение с API синхронизацией"""
        if self._loading_data:
            return  # Не сохраняем во время загрузки данных

        try:
            # Сохраняем изменения
            updates = {
                'senior_manager_id': self.senior_manager.currentData(),
                'dan_id': self.dan.currentData(),
                'start_date': self.start_date_edit.date().toString('yyyy-MM-dd'),
                'deadline': self.deadline.date().toString('yyyy-MM-dd'),
                'tags': self.tags.text().strip()
            }

            # Сначала пробуем API, потом локальную БД
            if self.api_client and self.api_client.is_online:
                try:
                    self.api_client.update_supervision_card(self.card_data['id'], updates)
                except Exception as api_error:
                    print(f"[WARN] Ошибка API автосохранения: {api_error}, fallback на локальную БД")
                    self.db.update_supervision_card(self.card_data['id'], updates)
            else:
                self.db.update_supervision_card(self.card_data['id'], updates)

            # Обновляем данные карточки
            self.card_data.update(updates)

            # Обновляем таблицу сроков при изменении start_date
            if hasattr(self, 'sv_timeline_widget') and self.sv_timeline_widget:
                try:
                    self.sv_timeline_widget.card_data = self.card_data
                    self.sv_timeline_widget._load_data()
                except Exception:
                    pass

        except Exception as e:
            print(f"Ошибка автосохранения: {e}")
            import traceback
            traceback.print_exc()

    def save_changes(self):
        """Сохранение изменений с API синхронизацией"""
        if self.is_dan_role:
            return

        updates = {
            'senior_manager_id': self.senior_manager.currentData(),
            'dan_id': self.dan.currentData(),
            'start_date': self.start_date_edit.date().toString('yyyy-MM-dd'),
            'deadline': self.deadline.date().toString('yyyy-MM-dd'),
            'tags': self.tags.text().strip()
        }

        # ИСПРАВЛЕНИЕ: Сначала пробуем API, потом локальную БД
        if self.api_client and self.api_client.is_online:
            try:
                self.api_client.update_supervision_card(self.card_data['id'], updates)
                print("[API] Изменения карточки надзора сохранены через API")
            except Exception as api_error:
                print(f"[WARN] Ошибка API сохранения: {api_error}, fallback на локальную БД")
                self.db.update_supervision_card(self.card_data['id'], updates)
        else:
            self.db.update_supervision_card(self.card_data['id'], updates)
            print("[LOCAL] Изменения карточки надзора сохранены локально")

        # ИСПРАВЛЕНИЕ: Обновляем вкладки после сохранения
        self.refresh_payments_tab()
        self.refresh_project_info_tab()

        # Обновляем родительскую вкладку
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMSupervisionTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()

        # ИСПРАВЛЕНИЕ: Закрываем диалог без показа сообщения
        self.accept()

    def _on_start_date_manual_change(self):
        """Изменение даты начала вручную — открыть календарь"""
        cal = self.start_date_edit.calendarWidget()
        if cal:
            today = QDate.currentDate()
            cal.setCurrentPage(today.year(), today.month())
        self.start_date_edit.setFocus()
        # Программно показать выпадающий календарь
        self.start_date_edit.setCalendarPopup(True)
        cal_popup = self.start_date_edit.findChild(QFrame)
        if cal_popup:
            cal_popup.show()
        else:
            # Альтернативный способ — клик по кнопке дропдауна
            self.start_date_edit.setReadOnly(False)
            self.start_date_edit.lineEdit().setFocus() if hasattr(self.start_date_edit, 'lineEdit') else None

    def _pause_from_edit_tab(self):
        """Приостановка карточки из вкладки редактирования"""
        dialog = PauseDialog(self, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            reason = dialog.reason_text.toPlainText().strip()
            if reason:
                try:
                    if self.api_client and self.api_client.is_online:
                        try:
                            self.api_client.pause_supervision_card(
                                self.card_data['id'],
                                reason
                            )
                        except Exception as e:
                            print(f"[WARN] API ошибка pause: {e}")
                            self.db.pause_supervision_card(
                                self.card_data['id'],
                                reason,
                                self.employee['id']
                            )
                    else:
                        self.db.pause_supervision_card(
                            self.card_data['id'],
                            reason,
                            self.employee['id']
                        )

                    # Обновляем состояние
                    self.card_data['is_paused'] = True
                    self.card_data['pause_reason'] = reason
                    from datetime import datetime
                    self.card_data['paused_at'] = datetime.now().strftime('%Y-%m-%d')

                    # Меняем кнопку на "Возобновить"
                    self.pause_btn.setText('Возобновить')
                    self.pause_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #27AE60; color: white;
                            padding: 0px 10px; border-radius: 4px; border: none;
                            font-size: 10px; font-weight: bold; min-height: 28px;
                        }
                        QPushButton:hover { background-color: #229954; }
                    """)
                    try:
                        self.pause_btn.clicked.disconnect()
                    except Exception:
                        pass
                    self.pause_btn.clicked.connect(self._resume_from_edit_tab)

                    # Обновляем родительскую вкладку
                    self.refresh_parent_tab()

                except Exception as e:
                    from ui.custom_message_box import CustomMessageBox
                    CustomMessageBox(self, 'Ошибка', f'Ошибка приостановки: {e}', 'error').exec_()

    def _resume_from_edit_tab(self):
        """Возобновление карточки из вкладки редактирования"""
        from ui.custom_message_box import CustomMessageBox
        reply = CustomMessageBox(
            self, 'Подтверждение',
            'Возобновить работу над проектом?\nДедлайн будет продлён на время приостановки.',
            'question'
        )
        reply.exec_()

        # CustomMessageBox возвращает result() == QDialog.Accepted при подтверждении
        if reply.result() == QDialog.Accepted:
            try:
                # Рассчитываем дни приостановки для продления дедлайна
                paused_at_str = self.card_data.get('paused_at', '')
                pause_days = 0
                if paused_at_str:
                    if 'T' in paused_at_str:
                        paused_at_str = paused_at_str.split('T')[0]
                    if ' ' in paused_at_str:
                        paused_at_str = paused_at_str.split(' ')[0]
                    from datetime import datetime, date
                    try:
                        paused_date = datetime.strptime(paused_at_str, '%Y-%m-%d').date()
                        pause_days = (date.today() - paused_date).days
                    except Exception:
                        pass

                if self.api_client and self.api_client.is_online:
                    try:
                        self.api_client.resume_supervision_card(
                            self.card_data['id'],
                            self.employee['id']
                        )
                    except Exception as e:
                        print(f"[WARN] API ошибка resume: {e}")
                        self.db.resume_supervision_card(
                            self.card_data['id'],
                            self.employee['id']
                        )
                else:
                    self.db.resume_supervision_card(
                        self.card_data['id'],
                        self.employee['id']
                    )

                # Продлеваем дедлайн на дни приостановки
                if pause_days > 0 and self.card_data.get('deadline'):
                    deadline_str = self.card_data['deadline']
                    if 'T' in deadline_str:
                        deadline_str = deadline_str.split('T')[0]
                    from datetime import datetime, timedelta
                    try:
                        deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d').date()
                        new_deadline = deadline_date + timedelta(days=pause_days)
                        new_deadline_str = new_deadline.strftime('%Y-%m-%d')

                        # Сохраняем новый дедлайн
                        update_data = {'deadline': new_deadline_str}
                        if self.api_client and self.api_client.is_online:
                            try:
                                self.api_client.update_supervision_card(
                                    self.card_data['id'], update_data
                                )
                            except Exception:
                                self.db.update_supervision_card(
                                    self.card_data['id'], update_data
                                )
                        else:
                            self.db.update_supervision_card(
                                self.card_data['id'], update_data
                            )

                        self.card_data['deadline'] = new_deadline_str
                        self._loading_data = True
                        self.deadline.setDate(QDate.fromString(new_deadline_str, 'yyyy-MM-dd'))
                        self._loading_data = False
                    except Exception as e:
                        print(f"[WARN] Ошибка продления дедлайна: {e}")

                # Обновляем состояние
                self.card_data['is_paused'] = False
                self.card_data['pause_reason'] = None
                self.card_data['paused_at'] = None

                # Меняем кнопку на "Приостановить"
                self.pause_btn.setText('Приостановить')
                self.pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #F39C12; color: white;
                        padding: 0px 10px; border-radius: 4px; border: none;
                        font-size: 10px; font-weight: bold; min-height: 28px;
                    }
                    QPushButton:hover { background-color: #E67E22; }
                """)
                try:
                    self.pause_btn.clicked.disconnect()
                except Exception:
                    pass
                self.pause_btn.clicked.connect(self._pause_from_edit_tab)

                # Обновляем родительскую вкладку
                self.refresh_parent_tab()

            except Exception as e:
                CustomMessageBox(self, 'Ошибка', f'Ошибка возобновления: {e}', 'error').exec_()

    def refresh_parent_tab(self):
        """Обновить родительскую вкладку CRMSupervisionTab"""
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMSupervisionTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()

    def reassign_dan(self):
        """Переназначить исполнителя ДАН"""
        current_dan_name = self.dan.currentText()

        dialog = SupervisionReassignDANDialog(
            self,
            self.card_data['id'],
            current_dan_name,
            api_client=self.api_client
        )

        if dialog.exec_() == QDialog.Accepted:
            # Обновляем отображение после переназначения
            self.load_data()
            print("[INFO] ДАН успешно переназначен, данные обновлены")

    def on_employee_changed(self, combo_box, role_name):
        """ИСПРАВЛЕНИЕ 30.01.2026: Автоматическое создание/обновление выплаты с API синхронизацией"""
        # Пропускаем, если данные загружаются
        if self._loading_data:
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            print("[WARN] Нет contract_id, пропускаем создание выплаты")
            return

        employee_id = combo_box.currentData()

        print(f"\n[EMPLOYEE_CHANGED] Роль: {role_name}, Employee ID: {employee_id}")

        # Сначала обновляем информацию о сотруднике через API/БД
        role_to_field = {
            'Старший менеджер проектов': 'senior_manager_id',
            'ДАН': 'dan_id'
        }

        field_name = role_to_field.get(role_name)
        if field_name:
            updates = {field_name: employee_id}
            # ИСПРАВЛЕНИЕ: Сначала API, потом локальная БД
            if self.api_client and self.api_client.is_online:
                try:
                    self.api_client.update_supervision_card(self.card_data['id'], updates)
                    print(f"[API] Обновлено поле {field_name} в карточке авторского надзора")
                except Exception as api_error:
                    print(f"[WARN] Ошибка API: {api_error}, fallback на локальную БД")
                    self.db.update_supervision_card(self.card_data['id'], updates)
            else:
                self.db.update_supervision_card(self.card_data['id'], updates)
                print(f"[LOCAL] Обновлено поле {field_name} в карточке авторского надзора")

        try:
            # ИСПРАВЛЕНИЕ: Удаляем оплаты через API если доступно
            if self.api_client and self.api_client.is_online:
                try:
                    # Получаем платежи для удаления
                    payments = self.api_client.get_payments_by_supervision_card(self.card_data['id'])
                    deleted_count = 0
                    for payment in payments:
                        if payment.get('role') == role_name:
                            self.api_client.delete_payment(payment['id'])
                            deleted_count += 1
                    if deleted_count > 0:
                        print(f"[API] Удалено {deleted_count} старых оплат надзора для роли {role_name}")
                except Exception as api_error:
                    print(f"[WARN] Ошибка API удаления платежей: {api_error}, fallback на локальную БД")
                    self._delete_payments_locally(role_name)
            else:
                self._delete_payments_locally(role_name)

            # ИСПРАВЛЕНО 06.02.2026: Создаем платеж при назначении исполнителя (как в CRM)
            if employee_id:
                # Проверяем, нет ли уже платежа для этой роли
                existing_payments = []
                if self.api_client and self.api_client.is_online:
                    try:
                        existing_payments = self.api_client.get_payments_by_supervision_card(self.card_data['id'])
                        existing_payments = [p for p in existing_payments if p.get('role') == role_name and not p.get('reassigned')]
                    except Exception as e:
                        print(f"[WARN] Ошибка проверки существующих платежей: {e}")

                if existing_payments:
                    print(f"[INFO] Платеж для роли {role_name} уже существует, пропускаем создание")
                else:
                    # Рассчитываем сумму через API или локальную БД
                    if self.api_client and self.api_client.is_online:
                        try:
                            result = self.api_client.calculate_payment_amount(
                                contract_id, employee_id, role_name,
                                stage_name=None, supervision_card_id=self.card_data['id']
                            )
                            calculated_amount = float(result) if result else 0
                            print(f"[API] Рассчитана сумма для {role_name}: {calculated_amount:.2f} руб")
                        except Exception as e:
                            print(f"[WARN] Ошибка API расчета: {e}, fallback на локальную БД")
                            calculated_amount = self.db.calculate_payment_amount(
                                contract_id, employee_id, role_name,
                                stage_name=None, supervision_card_id=self.card_data['id']
                            )
                    else:
                        calculated_amount = self.db.calculate_payment_amount(
                            contract_id, employee_id, role_name,
                            stage_name=None, supervision_card_id=self.card_data['id']
                        )

                    if calculated_amount == 0:
                        print(f"[WARN] Тариф для {role_name} = 0 или не установлен. Создаем оплату с нулевой суммой")

                    # Создаем платеж
                    from PyQt5.QtCore import QDate
                    payment_data = {
                        'contract_id': contract_id,
                        'supervision_card_id': self.card_data['id'],
                        'employee_id': employee_id,
                        'role': role_name,
                        'stage_name': None,
                        'calculated_amount': calculated_amount,
                        'final_amount': calculated_amount,
                        'payment_type': 'Полная оплата',
                        'report_month': None  # В работе - без месяца
                    }

                    if self.api_client and self.api_client.is_online:
                        try:
                            result = self.api_client.create_payment(payment_data)
                            print(f"[API] Создан платеж для {role_name}: {calculated_amount:.2f} руб")
                        except Exception as e:
                            print(f"[WARN] Ошибка API создания платежа: {e}, fallback на локальную БД")
                            self._create_payment_locally(payment_data)
                    else:
                        self._create_payment_locally(payment_data)
            else:
                print(f"[INFO] Сотрудник не назначен, выплаты удалены")

            # Обновляем вкладку оплат
            self.refresh_payments_tab()
            print(f"Вкладка оплат обновлена")

        except Exception as e:
            print(f"[ERROR] Ошибка при обновлении выплат: {e}")
            import traceback
            traceback.print_exc()

    def _delete_payments_locally(self, role_name):
        """Вспомогательный метод для удаления платежей локально"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM payments
                WHERE supervision_card_id = ? AND role = ?
            ''', (self.card_data['id'], role_name))
            deleted_count = cursor.rowcount
            conn.commit()
            self.db.close()
            if deleted_count > 0:
                print(f"[LOCAL] Удалено {deleted_count} старых оплат надзора для роли {role_name}")
        except Exception as e:
            print(f"[ERROR] Ошибка локального удаления платежей: {e}")

    def _create_payment_locally(self, payment_data):
        """ДОБАВЛЕНО 06.02.2026: Вспомогательный метод для создания платежа локально"""
        try:
            from datetime import datetime
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO payments (
                    contract_id, supervision_card_id, employee_id, role, stage_name,
                    calculated_amount, final_amount, payment_type, report_month, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                payment_data.get('contract_id'),
                payment_data.get('supervision_card_id'),
                payment_data.get('employee_id'),
                payment_data.get('role'),
                payment_data.get('stage_name'),
                payment_data.get('calculated_amount', 0),
                payment_data.get('final_amount', 0),
                payment_data.get('payment_type', 'Полная оплата'),
                payment_data.get('report_month'),
                datetime.now().isoformat()
            ))
            conn.commit()
            self.db.close()
            print(f"[LOCAL] Создан платеж для {payment_data.get('role')}: {payment_data.get('final_amount', 0):.2f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка локального создания платежа: {e}")
            import traceback
            traceback.print_exc()

    # ========== RESIZE: Изменение размера окна мышью ==========

    def get_resize_edge(self, pos):
        """Определение края для изменения размера"""
        rect = self.rect()
        margin = self.resize_margin
        on_left = pos.x() <= margin
        on_right = pos.x() >= rect.width() - margin
        if on_left:
            return 'left'
        elif on_right:
            return 'right'
        return None

    def set_cursor_shape(self, edge):
        """Установка формы курсора"""
        if edge in ('left', 'right'):
            self.setCursor(Qt.SizeHorCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        """Начало изменения размера"""
        if event.button() == Qt.LeftButton:
            edge = self.get_resize_edge(event.pos())
            if edge:
                self.resizing = True
                self.resize_edge = edge
                self.resize_start_pos = event.globalPos()
                self.resize_start_geometry = self.geometry()
                self.grabMouse()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Процесс изменения размера"""
        if self.resizing and self.resize_edge:
            delta = event.globalPos() - self.resize_start_pos
            old_geo = self.resize_start_geometry
            x, y, w, h = old_geo.x(), old_geo.y(), old_geo.width(), old_geo.height()
            min_w = 1100

            if self.resize_edge == 'left':
                new_w = w - delta.x()
                if new_w >= min_w:
                    x = old_geo.x() + delta.x()
                    w = new_w
            elif self.resize_edge == 'right':
                new_w = w + delta.x()
                if new_w >= min_w:
                    w = new_w

            self.setGeometry(x, y, w, h)
            event.accept()
        else:
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Завершение изменения размера"""
        if event.button() == Qt.LeftButton and self.resizing:
            self.releaseMouse()
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def event(self, event):
        """Обработка событий наведения мыши"""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.HoverMove:
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)
        elif event.type() == QEvent.HoverLeave:
            if not self.resizing:
                self.setCursor(Qt.ArrowCursor)
        return super().event(event)

    def leaveEvent(self, event):
        """Сброс курсора при выходе мыши"""
        if not self.resizing:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

    # ========== /RESIZE ==========

    def showEvent(self, event):
        """Центрирование при первом показе + отложенная инициализация тяжёлых вкладок"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()
            # Инициализируем тяжёлые вкладки ПОСЛЕ показа окна (избегаем мелькание popup)
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self._init_deferred_tabs)

    def _init_deferred_tabs(self):
        """Создание тяжёлых вкладок после показа диалога (предотвращает мелькание)"""
        if self._deferred_tabs_ready:
            return
        self._deferred_tabs_ready = True

        current_tab = self.tabs.currentIndex()

        # Таблица сроков надзора
        try:
            from ui.supervision_timeline_widget import SupervisionTimelineWidget
            self.sv_timeline_widget = SupervisionTimelineWidget(
                card_data=self.card_data,
                data=self.data,
                db=self.db,
                api_client=self.api_client,
                employee=self.employee,
                parent=self
            )
            self.tabs.removeTab(self._timeline_tab_index)
            self.tabs.insertTab(self._timeline_tab_index, self.sv_timeline_widget, 'Таблица сроков')
        except Exception as e:
            print(f"[SupervisionCardEditDialog] Ошибка создания таблицы сроков: {e}")

        # Оплаты надзора
        payments_widget = self.create_payments_widget()
        self.tabs.removeTab(self.payments_tab_index)
        self.tabs.insertTab(self.payments_tab_index, payments_widget, 'Оплаты надзора')

        # Информация о проекте
        info_widget = self.create_project_info_widget()
        self.tabs.removeTab(self.project_info_tab_index)
        self.tabs.insertTab(self.project_info_tab_index, info_widget, 'Информация о проекте')

        # Файлы надзора
        files_widget = self.create_files_widget()
        self.tabs.removeTab(self.files_tab_index)
        self.tabs.insertTab(self.files_tab_index, files_widget, 'Файлы надзора')

        # Восстановить текущую вкладку
        self.tabs.setCurrentIndex(current_tab)

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

class SupervisionStatisticsDialog(QDialog):
    """Диалог статистики надзора"""

    def __init__(self, parent, api_client=None):
        super().__init__(parent)
        self.db = DatabaseManager()
        self.api_client = api_client
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: none;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Статистика CRM Авторского надзора', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Заголовок
        header = QLabel('Статистика исполнителей авторского надзора')
        header.setStyleSheet('font-size: 16px; font-weight: bold; padding: 5px;')
        layout.addWidget(header)
        
        # ФИЛЬТРЫ (весь код остается БЕЗ ИЗМЕНЕНИЙ)
        filters_group = QGroupBox('Фильтры')
        filters_main_layout = QVBoxLayout()
        
        # Строка 1: Период
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel('Период:'))
        
        self.period_combo = CustomComboBox()
        self.period_combo.addItems(['Все время', 'Месяц', 'Квартал', 'Год'])
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        row1_layout.addWidget(self.period_combo)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2030)
        self.year_spin.setValue(QDate.currentDate().year())
        self.year_spin.valueChanged.connect(self.load_statistics)
        self.year_spin.setPrefix('Год: ')
        self.year_spin.setMinimumHeight(24)
        self.year_spin.setMaximumHeight(24)
        self.year_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 0px 8px 0px 8px;
                color: #333333;
                font-size: 12px;
                height: 22px;
                min-height: 22px;
                max-height: 22px;
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
        row1_layout.addWidget(self.year_spin)
        self.year_spin.hide()
        
        self.quarter_combo = CustomComboBox()
        self.quarter_combo.addItems(['Q1', 'Q2', 'Q3', 'Q4'])
        self.quarter_combo.setCurrentIndex((QDate.currentDate().month() - 1) // 3)
        self.quarter_combo.currentIndexChanged.connect(self.load_statistics)
        row1_layout.addWidget(self.quarter_combo)
        self.quarter_combo.hide()
        
        self.month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        self.month_combo.addItems(months)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.currentIndexChanged.connect(self.load_statistics)
        row1_layout.addWidget(self.month_combo)
        self.month_combo.hide()
        
        row1_layout.addStretch()
        filters_main_layout.addLayout(row1_layout)
        
        # Строка 2: Адрес, Стадия
        row2_layout = QHBoxLayout()
        
        row2_layout.addWidget(QLabel('Адрес:'))
        self.address_combo = CustomComboBox()
        self.address_combo.addItem('Все', None)
        self.address_combo.setMinimumWidth(300)
        self.load_addresses()
        self.address_combo.currentIndexChanged.connect(self.load_statistics)
        row2_layout.addWidget(self.address_combo)
        
        row2_layout.addWidget(QLabel('Стадия:'))
        self.stage_combo = CustomComboBox()
        self.stage_combo.addItem('Все', None)
        self.stage_combo.setMinimumWidth(200)
        stages = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники',
            'Стадия 3: Закупка оборудования', 'Стадия 4: Закупка дверей и окон',
            'Стадия 5: Закупка настенных материалов', 'Стадия 6: Закупка напольных материалов',
            'Стадия 7: Лепного декора', 'Стадия 8: Освещения',
            'Стадия 9: бытовой техники', 'Стадия 10: Закупка заказной мебели',
            'Стадия 11: Закупка фабричной мебели', 'Стадия 12: Закупка декора',
            'Выполненный проект'
        ]
        for stage in stages:
            self.stage_combo.addItem(stage)
        self.stage_combo.currentIndexChanged.connect(self.load_statistics)
        row2_layout.addWidget(self.stage_combo)
        
        row2_layout.addStretch()
        filters_main_layout.addLayout(row2_layout)
        
        # Строка 3: Исполнитель, Менеджер, Статус
        row3_layout = QHBoxLayout()
        
        row3_layout.addWidget(QLabel('ДАН:'))
        self.executor_combo = CustomComboBox()
        self.executor_combo.addItem('Все', None)
        self.executor_combo.setMinimumWidth(180)
        self.load_executors()
        self.executor_combo.currentIndexChanged.connect(self.load_statistics)
        row3_layout.addWidget(self.executor_combo)
        
        row3_layout.addWidget(QLabel('Ст.менеджер:'))
        self.manager_combo = CustomComboBox()
        self.manager_combo.addItem('Все', None)
        self.manager_combo.setMinimumWidth(180)
        self.load_managers()
        self.manager_combo.currentIndexChanged.connect(self.load_statistics)
        row3_layout.addWidget(self.manager_combo)
        
        row3_layout.addWidget(QLabel('Статус:'))
        self.status_filter = CustomComboBox()
        self.status_filter.addItems(['Все', 'В работе', 'Приостановлено', 'Работа сдана'])
        self.status_filter.setMinimumWidth(150)
        self.status_filter.currentIndexChanged.connect(self.load_statistics)
        row3_layout.addWidget(self.status_filter)
        
        row3_layout.addStretch()
        
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить все фильтры', icon_size=12)
        reset_btn.setStyleSheet('padding: 5px 15px;')
        reset_btn.clicked.connect(self.reset_filters)
        row3_layout.addWidget(reset_btn)
        
        filters_main_layout.addLayout(row3_layout)
        
        filters_group.setLayout(filters_main_layout)
        layout.addWidget(filters_group)
        
        # Таблица
        self.stats_table = QTableWidget()
        apply_no_focus_delegate(self.stats_table)  # Убираем пунктирную рамку фокуса
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
            }
            QTableCornerButton::section {
                background-color: #fafafa;
                border: none;
                border-bottom: 1px solid #e6e6e6;
                border-right: 1px solid #f0f0f0;
                border-top-left-radius: 8px;
            }
        """)
        self.stats_table.setColumnCount(7)
        self.stats_table.setHorizontalHeaderLabels([
            'Договор', 'Адрес', 'Стадия', 'Ст.менеджер', 'ДАН', 'Дедлайн', 'Статус'
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)

        # Запрещаем изменение высоты строк
        self.stats_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.stats_table.verticalHeader().setDefaultSectionSize(32)

        layout.addWidget(self.stats_table, 1)
        
        # Кнопки экспорта и закрытия
        buttons_layout = QHBoxLayout()
        
        excel_btn = IconLoader.create_icon_button('export', 'Экспорт в Excel', icon_size=12)
        excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        excel_btn.clicked.connect(self.export_to_excel)
        buttons_layout.addWidget(excel_btn)
        
        pdf_btn = IconLoader.create_icon_button('export', 'Экспорт в PDF', icon_size=12)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        pdf_btn.clicked.connect(self.export_to_pdf)
        buttons_layout.addWidget(pdf_btn)
        
        buttons_layout.addStretch()
        
        close_btn = QPushButton('Закрыть')
        close_btn.setStyleSheet('padding: 8px 20px;')
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumSize(1200, 900)
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.load_statistics)
    
    def load_addresses(self):
        """Загрузка списка адресов"""
        try:
            if self.api_client:
                try:
                    addresses = self.api_client.get_supervision_addresses()
                except Exception as e:
                    print(f"[WARN] API ошибка загрузки адресов: {e}")
                    addresses = self.db.get_supervision_addresses()
            else:
                addresses = self.db.get_supervision_addresses()
            for addr in addresses:
                display = f"{addr['contract_number']} - {addr['address']}"
                self.address_combo.addItem(display, addr['contract_id'])
        except Exception as e:
            print(f"Ошибка загрузки адресов: {e}")

    def load_executors(self):
        """Загрузка ДАН'ов"""
        try:
            if self.api_client:
                try:
                    dans = self.api_client.get_employees_by_position('ДАН')
                except Exception as e:
                    print(f"[WARN] API ошибка загрузки ДАН: {e}")
                    dans = self.db.get_employees_by_position('ДАН')
            else:
                dans = self.db.get_employees_by_position('ДАН')
            for dan in dans:
                self.executor_combo.addItem(dan['full_name'], dan['id'])
        except Exception as e:
            print(f"Ошибка загрузки ДАН'ов: {e}")

    def load_managers(self):
        """Загрузка менеджеров"""
        try:
            if self.api_client:
                try:
                    managers = self.api_client.get_employees_by_position('Старший менеджер проектов')
                except Exception as e:
                    print(f"[WARN] API ошибка загрузки менеджеров: {e}")
                    managers = self.db.get_employees_by_position('Старший менеджер проектов')
            else:
                managers = self.db.get_employees_by_position('Старший менеджер проектов')
            for mgr in managers:
                self.manager_combo.addItem(mgr['full_name'], mgr['id'])
        except Exception as e:
            print(f"Ошибка загрузки менеджеров: {e}")
    
    def reset_filters(self):
        """Сброс фильтров"""
        self.period_combo.setCurrentText('Все время')
        self.address_combo.setCurrentIndex(0)
        self.stage_combo.setCurrentIndex(0)
        self.executor_combo.setCurrentIndex(0)
        self.manager_combo.setCurrentIndex(0)
        self.status_filter.setCurrentIndex(0)
        self.load_statistics()
    
    def on_period_changed(self, period):
        """Изменение периода"""
        self.year_spin.setVisible(period != 'Все время')
        self.quarter_combo.setVisible(period == 'Квартал')
        self.month_combo.setVisible(period == 'Месяц')
        self.load_statistics()
    
    def load_statistics(self):
        """Загрузка статистики с фильтрами"""
        period = self.period_combo.currentText()
        year = self.year_spin.value()
        quarter = self.quarter_combo.currentText() if self.quarter_combo.isVisible() else None
        month = self.month_combo.currentIndex() + 1 if self.month_combo.isVisible() else None
        
        address_id = self.address_combo.currentData()
        stage = self.stage_combo.currentText() if self.stage_combo.currentIndex() > 0 else None
        executor_id = self.executor_combo.currentData()
        manager_id = self.manager_combo.currentData()
        status = self.status_filter.currentText() if self.status_filter.currentIndex() > 0 else None

        if self.api_client:
            try:
                stats = self.api_client.get_supervision_statistics_filtered(
                    period, year, quarter, month,
                    address_id, stage, executor_id, manager_id, status
                )
            except Exception as e:
                print(f"[WARN] API ошибка get_supervision_statistics_filtered: {e}")
                stats = self.db.get_supervision_statistics_filtered(
                    period, year, quarter, month,
                    address_id, stage, executor_id, manager_id, status
                )
        else:
            stats = self.db.get_supervision_statistics_filtered(
                period, year, quarter, month,
                address_id, stage, executor_id, manager_id, status
            )
        
        self.stats_table.setRowCount(len(stats))
        
        for row, stat in enumerate(stats):
            self.stats_table.setItem(row, 0, QTableWidgetItem(stat.get('contract_number', '')))
            self.stats_table.setItem(row, 1, QTableWidgetItem(stat.get('address', '')))
            self.stats_table.setItem(row, 2, QTableWidgetItem(stat.get('column_name', '')))
            self.stats_table.setItem(row, 3, QTableWidgetItem(stat.get('senior_manager_name', 'Не назначен')))
            self.stats_table.setItem(row, 4, QTableWidgetItem(stat.get('dan_name', 'Не назначен')))
            self.stats_table.setItem(row, 5, QTableWidgetItem(stat.get('deadline', '')))
            
            if stat.get('dan_completed'):
                status_text = 'Работа сдана'
            elif stat.get('is_paused'):
                status_text = '⏸ Приостановлено'
            else:
                status_text = 'В работе'
            
            self.stats_table.setItem(row, 6, QTableWidgetItem(status_text))
    
    def export_to_excel(self):
        """Экспорт в Excel"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                'Сохранить в Excel',
                f'supervision_stats_{QDate.currentDate().toString("yyyy-MM-dd")}.csv',
                'CSV Files (*.csv)'
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file, delimiter=';')
                    
                    headers = ['Договор', 'Адрес', 'Колонка', 'Ст.менеджер', 'ДАН', 'Дедлайн', 'Статус']
                    writer.writerow(headers)
                    
                    for row in range(self.stats_table.rowCount()):
                        row_data = []
                        for col in range(self.stats_table.columnCount()):
                            item = self.stats_table.item(row, col)
                            row_data.append(item.text() if item else '')
                        writer.writerow(row_data)
                
                # ========== ЗАМЕНИЛИ QMessageBox ==========
                CustomMessageBox(self, 'Успех', f'Статистика экспортирована:\n{filename}', 'success').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось экспортировать:\n{str(e)}', 'error').exec_()
            
    def export_to_pdf(self):
        """Экспорт в PDF"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Экспорт в PDF')
        dialog.setMinimumWidth(550)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel('Экспорт статистики в PDF')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #E74C3C;')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        info = QLabel(f'Будет экспортировано записей: <b>{self.stats_table.rowCount()}</b>')
        info.setStyleSheet('font-size: 11px; color: #555;')
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        filename_layout = QFormLayout()
        
        self.filename_input = QLineEdit()
        default_filename = f'Отчет АН {QDate.currentDate().toString("yyyy-MM-dd")}'
        self.filename_input.setText(default_filename)
        self.filename_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #DDD;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        filename_layout.addRow('Имя файла:', self.filename_input)
        
        layout.addLayout(filename_layout)
        
        hint = QLabel('Файл будет сохранен в выбранную папку с расширением .pdf')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic;')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        
        folder_btn = QPushButton('Выбрать папку и экспортировать')
        folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        folder_btn.clicked.connect(lambda: self.perform_pdf_export(dialog))
        layout.addWidget(folder_btn)
        
        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(dialog.reject)
        layout.addWidget(cancel_btn)
        
        dialog.setLayout(layout)
        dialog.exec_()
      
    def perform_pdf_export(self, parent_dialog):
        """Выполнение экспорта PDF"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            from PyQt5.QtPrintSupport import QPrinter
            from PyQt5.QtGui import (QTextDocument, QTextCursor, QTextTableFormat, 
                                     QTextCharFormat, QFont, QColor, QBrush, 
                                     QTextBlockFormat, QTextLength, QPixmap, QTextImageFormat)
            
            folder = QFileDialog.getExistingDirectory(
                self,
                'Выберите папку для сохранения',
                '',
                QFileDialog.ShowDirsOnly
            )
            
            if not folder:
                return
            
            filename = self.filename_input.text().strip()
            if not filename:
                filename = f'supervision_stats_{QDate.currentDate().toString("yyyy-MM-dd")}'
            
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            full_path = f"{folder}/{filename}"
            
            printer = QPrinter(QPrinter.HighResolution)
            printer.setOutputFormat(QPrinter.PdfFormat)
            printer.setOutputFileName(full_path)
            printer.setPageMargins(0, 0, 0, 0, QPrinter.Millimeter)
            printer.setPageSize(QPrinter.A4)
            
            doc = QTextDocument()       
            cursor = QTextCursor(doc)
            
            # ЛОГОТИП
            block_format = QTextBlockFormat()
            block_format.setAlignment(Qt.AlignCenter)
            cursor.setBlockFormat(block_format)
            
            logo_path = resource_path('resources/logo.png')
            
            if os.path.exists(logo_path):
                try:
                    pixmap = QPixmap(logo_path)
                    
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                        image = scaled_pixmap.toImage()
                        
                        doc.addResource(QTextDocument.ImageResource, 
                                      QUrl.fromLocalFile(logo_path),
                                      image)
                        
                        image_format = QTextImageFormat()
                        image_format.setName(logo_path)
                        image_format.setWidth(scaled_pixmap.width())
                        image_format.setHeight(scaled_pixmap.height())
                        
                        cursor.insertImage(image_format)
                        cursor.insertText('\n\n')
                    else:
                        logo_format = QTextCharFormat()
                        logo_format.setFont(QFont('Arial', 36, QFont.Bold))
                        logo_format.setForeground(QColor('#FF9800'))
                        cursor.insertText('FC\n\n', logo_format)
                except Exception as e:
                    logo_format = QTextCharFormat()
                    logo_format.setFont(QFont('Arial', 36, QFont.Bold))
                    logo_format.setForeground(QColor('#FF9800'))
                    cursor.insertText('FC\n\n', logo_format)
            else:
                logo_format = QTextCharFormat()
                logo_format.setFont(QFont('Arial', 36, QFont.Bold))
                logo_format.setForeground(QColor('#FF9800'))
                cursor.insertText('FC\n\n', logo_format)
            
            company_format = QTextCharFormat()
            company_format.setFont(QFont('Arial', 18, QFont.Bold))
            company_format.setForeground(QColor('#000000'))
            cursor.insertText('FESTIVAL COLOR\n', company_format)
            
            subtitle_format = QTextCharFormat()
            subtitle_format.setFont(QFont('Arial', 10))
            subtitle_format.setForeground(QColor('#666'))
            cursor.insertText('Система управления проектами\n\n', subtitle_format)
            
            cursor.insertText('\n')
            line_format = QTextCharFormat()
            line_format.setForeground(QColor('#E0E0E0'))
            cursor.insertText('─' * 60 + '\n\n', line_format)
            
            title_format = QTextCharFormat()
            title_format.setFont(QFont('Arial', 14, QFont.Bold))
            title_format.setForeground(QColor('#2C3E50'))
            cursor.insertText('Статистика CRM Авторского надзора\n\n', title_format)
            
            date_format = QTextCharFormat()
            date_format.setFont(QFont('Arial', 8))
            date_format.setForeground(QColor('#95A5A6'))
            cursor.insertText(f'Дата формирования: {QDate.currentDate().toString("dd.MM.yyyy")}\n\n', date_format)
            
            cursor.insertText('─' * 80 + '\n\n', line_format)
            
            # Сводка
            left_block = QTextBlockFormat()
            left_block.setAlignment(Qt.AlignLeft)
            cursor.setBlockFormat(left_block)
            
            summary_title_format = QTextCharFormat()
            summary_title_format.setFont(QFont('Arial', 10, QFont.Bold))
            summary_title_format.setForeground(QColor('#FF9800'))
            cursor.insertText('Краткая сводка\n\n', summary_title_format)
            
            total_projects = self.stats_table.rowCount()
            paused_count = 0
            completed_work_count = 0
            in_work_count = 0
            
            for row in range(total_projects):
                status_item = self.stats_table.item(row, 6)
                if status_item:
                    status_text = status_item.text()
                    if 'Приостановлено' in status_text:
                        paused_count += 1
                    elif 'Работа сдана' in status_text:
                        completed_work_count += 1
                    else:
                        in_work_count += 1
            
            summary_format = QTextCharFormat()
            summary_format.setFont(QFont('Arial', 8))
            
            cursor.insertText(f'• Всего проектов: {total_projects}\n', summary_format)
            cursor.insertText(f'• В работе: {in_work_count}\n', summary_format)
            cursor.insertText(f'• Работа сдана: {completed_work_count}\n', summary_format)
            cursor.insertText(f'• Приостановлено: {paused_count}\n\n', summary_format)
            
            cursor.insertText('─' * 80 + '\n\n', line_format)
            
            # Таблица
            table_title_format = QTextCharFormat()
            table_title_format.setFont(QFont('Arial', 10, QFont.Bold))
            table_title_format.setForeground(QColor('#FF9800'))
            cursor.insertText('Детальная статистика\n\n', table_title_format)
            
            table_format = QTextTableFormat()
            table_format.setBorder(1)
            table_format.setBorderBrush(QBrush(QColor('#CCCCCC')))
            table_format.setCellPadding(4)
            table_format.setCellSpacing(0)
            table_format.setHeaderRowCount(1)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))
            
            table = cursor.insertTable(
                self.stats_table.rowCount() + 1,
                self.stats_table.columnCount(),
                table_format
            )
            
            # Заголовки
            header_format = QTextCharFormat()
            header_format.setFont(QFont('Arial', 9, QFont.Bold))
            header_format.setForeground(QColor('white'))
            header_format.setBackground(QColor('#808080'))
            
            for col in range(self.stats_table.columnCount()):
                cell = table.cellAt(0, col)
                cell_cursor = cell.firstCursorPosition()
                
                cell_format = cell.format()
                cell_format.setBackground(QBrush(QColor('#808080')))
                cell.setFormat(cell_format)
                
                cell_cursor.insertText(
                    self.stats_table.horizontalHeaderItem(col).text(),
                    header_format
                )
            
            # Данные
            for row in range(self.stats_table.rowCount()):
                if row % 2 == 0:
                    row_bg = QColor('#FFFFFF')
                else:
                    row_bg = QColor('#F5F5F5')
                
                data_format = QTextCharFormat()
                data_format.setFont(QFont('Arial', 8))
                data_format.setForeground(QColor('#333'))
                
                for col in range(self.stats_table.columnCount()):
                    item = self.stats_table.item(row, col)
                    cell = table.cellAt(row + 1, col)
                    
                    cell_format = cell.format()
                    cell_format.setBackground(QBrush(row_bg))
                    cell.setFormat(cell_format)
                    
                    cell_cursor = cell.firstCursorPosition()
                    
                    if col == 6 and item:
                        status_text = item.text()
                        
                        if 'Приостановлено' in status_text:
                            status_format = QTextCharFormat()
                            status_format.setFont(QFont('Arial', 8, QFont.Bold))
                            status_format.setForeground(QColor('#F39C12'))
                            cell_cursor.insertText(status_text, status_format)
                        elif 'Работа сдана' in status_text:
                            status_format = QTextCharFormat()
                            status_format.setFont(QFont('Arial', 8, QFont.Bold))
                            status_format.setForeground(QColor('#27AE60'))
                            cell_cursor.insertText(status_text, status_format)
                        else:
                            cell_cursor.insertText(status_text, data_format)
                    else:
                        cell_cursor.insertText(
                            item.text() if item else '',
                            data_format
                        )
            
            # Подвал
            cursor.movePosition(QTextCursor.End)
            cursor.insertText('\n\n')
            
            footer_block = QTextBlockFormat()
            footer_block.setAlignment(Qt.AlignCenter)
            cursor.setBlockFormat(footer_block)
            
            footer_format = QTextCharFormat()
            footer_format.setFont(QFont('Arial', 8))
            footer_format.setForeground(QColor('#999'))
            cursor.insertText(
                f'\n{"─" * 60}\n'
                f'Документ сформирован автоматически системой Festival Color\n'
                f'{QDate.currentDate().toString("dd.MM.yyyy")}',
                footer_format
            )
            
            doc.print_(printer)
            
            parent_dialog.accept()
            
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle('Успех')
            success_dialog.setMinimumWidth(500)
            
            success_layout = QVBoxLayout()
            success_layout.setSpacing(15)
            success_layout.setContentsMargins(20, 20, 20, 20)
            
            success_title = QLabel('PDF успешно создан!')
            success_title.setStyleSheet('font-size: 14px; font-weight: bold; color: #27AE60;')
            success_title.setAlignment(Qt.AlignCenter)
            success_layout.addWidget(success_title)
            
            path_frame = QFrame()
            path_frame.setStyleSheet('''
                QFrame {
                    background-color: #f5f5f5;
                    border: none;
                    border-radius: 4px;
                    padding: 10px;
                }
            ''')
            path_layout = QVBoxLayout()
            path_layout.setContentsMargins(0, 0, 0, 0)
            
            path_label = QLabel(full_path)
            path_label.setWordWrap(True)
            path_label.setStyleSheet('font-size: 10px; color: #333;')
            path_label.setAlignment(Qt.AlignCenter)
            path_layout.addWidget(path_label)
            
            path_frame.setLayout(path_layout)
            success_layout.addWidget(path_frame)
            
            open_folder_btn = QPushButton('Открыть папку с файлом')
            open_folder_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd93c;
                    color: white;
                    padding: 10px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2980B9; }
            """)
            open_folder_btn.clicked.connect(lambda: self.open_folder(folder))
            success_layout.addWidget(open_folder_btn)
            
            ok_btn = QPushButton('OK')
            ok_btn.setStyleSheet("""
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
            ok_btn.clicked.connect(success_dialog.accept)
            success_layout.addWidget(ok_btn)
            
            success_dialog.setLayout(success_layout)
            success_dialog.exec_()
            
        except Exception as e:
            print(f" Ошибка экспорта PDF: {e}")
            import traceback
            traceback.print_exc()
            QMessageBox.critical(self, 'Ошибка', f'Не удалось создать PDF:\n{str(e)}')
        
    def open_folder(self, folder_path):
        """Открытие папки в проводнике"""
        try:
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(folder_path)
            elif platform.system() == 'Darwin':
                os.system(f'open "{folder_path}"')
            else:
                os.system(f'xdg-open "{folder_path}"')
        except Exception as e:
            print(f"Не удалось открыть папку: {e}")
            
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)
                
class SupervisionCompletionDialog(QDialog):
    """Диалог завершения проекта авторского надзора"""

    def __init__(self, parent, card_id, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.db = DatabaseManager()
        self.api_client = api_client
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: none;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Завершение проекта авторского надзора', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        info = QLabel('Выберите статус завершения проекта:')
        info.setStyleSheet('font-size: 14px; font-weight: bold;')
        layout.addWidget(info)
        
        form_layout = QFormLayout()
        
        self.status = CustomComboBox()
        self.status.addItems(['Проект СДАН', 'Проект РАСТОРГНУТ'])
        self.status.currentTextChanged.connect(self.on_status_changed)
        form_layout.addRow('Статус:', self.status)
        
        self.termination_reason_group = QGroupBox('Причина расторжения')
        termination_layout = QVBoxLayout()
        
        self.termination_reason = QTextEdit()
        self.termination_reason.setMaximumHeight(100)
        termination_layout.addWidget(self.termination_reason)
        
        self.termination_reason_group.setLayout(termination_layout)
        self.termination_reason_group.hide()
        
        layout.addLayout(form_layout)
        layout.addWidget(self.termination_reason_group)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton('Завершить проект')
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self.complete_project)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(500)
    
    def on_status_changed(self, status):
        if 'РАСТОРГНУТ' in status:
            self.termination_reason_group.show()
        else:
            self.termination_reason_group.hide()
    
    def complete_project(self):
        status = self.status.currentText()
        
        if 'РАСТОРГНУТ' in status and not self.termination_reason.toPlainText().strip():
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Ошибка', 'Укажите причину расторжения', 'warning').exec_()
            return
        
        try:
            if self.api_client:
                try:
                    contract_id = self.api_client.get_contract_id_by_supervision_card(self.card_id)
                except Exception as e:
                    print(f"[WARN] API ошибка get_contract_id: {e}")
                    contract_id = self.db.get_contract_id_by_supervision_card(self.card_id)
            else:
                contract_id = self.db.get_contract_id_by_supervision_card(self.card_id)

            clean_status = status.replace('Проект ', '')

            updates = {
                'status': clean_status
            }

            if 'РАСТОРГНУТ' in status:
                updates['termination_reason'] = self.termination_reason.toPlainText().strip()

            if self.api_client:
                try:
                    self.api_client.update_contract(contract_id, updates)
                except Exception as e:
                    print(f"[WARN] API ошибка update_contract: {e}")
                    self.db.update_contract(contract_id, updates)
            else:
                self.db.update_contract(contract_id, updates)
            
            print(f"Проект авторского надзора завершен со статусом: {clean_status}")
            
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Успех', 'Проект завершен и перемещен в архив', 'success').exec_()
            self.accept()
            
        except Exception as e:
            print(f" Ошибка завершения проекта: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось завершить проект: {e}', 'error').exec_()
    
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

class AddProjectNoteDialog(QDialog):
    """Диалог добавления записи в историю проекта"""

    def __init__(self, parent, card_id, employee, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.employee = employee
        self.db = DatabaseManager()
        self.api_client = api_client
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: none;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Добавить запись в историю', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel('Добавление записи в историю проекта')
        header.setStyleSheet('font-size: 14px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)
        
        label = QLabel('Введите информацию:')
        layout.addWidget(label)
        
        self.note_text = QTextEdit()
        self.note_text.setPlaceholderText('Например: Согласована покупка керамогранита...')
        self.note_text.setMinimumHeight(120)
        layout.addWidget(self.note_text)
        
        hint = QLabel('Эта запись будет сохранена с датой и вашим именем')
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic;')
        layout.addWidget(hint)
        
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        save_btn.clicked.connect(self.save_note)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(self.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(500)
    
    def save_note(self):
        message = self.note_text.toPlainText().strip()
        
        if not message:
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Ошибка', 'Введите текст записи', 'warning').exec_()
            return
        
        try:
            if self.api_client:
                try:
                    self.api_client.add_supervision_history(
                        self.card_id,
                        'note',
                        message,
                        self.employee['id']
                    )
                except Exception as e:
                    print(f"[WARN] API ошибка add_supervision_history: {e}")
                    self.db.add_supervision_history(
                        self.card_id,
                        'note',
                        message,
                        self.employee['id']
                    )
            else:
                self.db.add_supervision_history(
                    self.card_id,
                    'note',
                    message,
                    self.employee['id']
                )
            
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Успех', 'Запись добавлена в историю проекта', 'success').exec_()
            self.accept()
            
        except Exception as e:
            print(f" Ошибка сохранения записи: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()
    
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

class SupervisionStageDeadlineDialog(QDialog):
    """Диалог установки дедлайна для стадии надзора"""

    def __init__(self, parent, card_id, stage_name, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.stage_name = stage_name
        self.db = DatabaseManager()
        self.api_client = api_client
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: none;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Установка дедлайна стадии', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ========== КОНТЕНТ ==========
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel('Укажите дедлайн для стадии:')
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
        
        stage_label = QLabel(f'"{self.stage_name}"')
        stage_label.setStyleSheet('font-size: 16px; font-weight: bold; color: #FF9800;')
        stage_label.setWordWrap(True)
        stage_label.setAlignment(Qt.AlignCenter)
        stage_layout.addWidget(stage_label)
        
        stage_frame.setLayout(stage_layout)
        layout.addWidget(stage_frame)
        
        # Поле дедлайна
        deadline_layout = QHBoxLayout()
        deadline_layout.addStretch()
        
        deadline_layout.addWidget(QLabel('Дедлайн:'))
        
        self.deadline_widget = CustomDateEdit()
        self.deadline_widget.setCalendarPopup(True)
        add_today_button_to_dateedit(self.deadline_widget)
        self.deadline_widget.setDate(QDate.currentDate().addDays(7))
        self.deadline_widget.setDisplayFormat('dd.MM.yyyy')
        self.deadline_widget.setMinimumWidth(150)
        self.deadline_widget.setStyleSheet("""
            QDateEdit {
                padding: 6px;
                border: 1px solid #CCC;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        deadline_layout.addWidget(self.deadline_widget)
        
        deadline_layout.addStretch()
        layout.addLayout(deadline_layout)
        
        hint = QLabel('Этот дедлайн будет отображаться на карточке')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic; margin-top: 5px;')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        
        save_btn = QPushButton('Установить дедлайн')
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        save_btn.clicked.connect(self.save_deadline)
        layout.addWidget(save_btn)

        skip_btn = QPushButton('Пропустить')
        skip_btn.setFixedHeight(36)
        skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 36px;
                min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        skip_btn.clicked.connect(self.reject)
        layout.addWidget(skip_btn)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(500)
    
    def save_deadline(self):
        """Сохранение дедлайна"""
        deadline = self.deadline_widget.date().toString('yyyy-MM-dd')

        try:
            if self.api_client:
                try:
                    self.api_client.update_supervision_card(self.card_id, {
                        'deadline': deadline
                    })
                except Exception as e:
                    print(f"[WARN] API ошибка save_deadline: {e}")
                    self.db.update_supervision_card(self.card_id, {
                        'deadline': deadline
                    })
            else:
                self.db.update_supervision_card(self.card_id, {
                    'deadline': deadline
                })
            
            # ========== ЗАМЕНИЛИ на CustomMessageBox ==========
            CustomMessageBox(
                self, 
                'Успех', 
                f'Дедлайн установлен на {self.deadline_widget.date().toString("dd.MM.yyyy")}!', 
                'success'
            ).exec_()
            
            self.accept()
            
        except Exception as e:
            print(f" Ошибка сохранения дедлайна: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось установить дедлайн: {e}', 'error').exec_()
    
    def showEvent(self, event):
        """Центрирование при первом показе"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)


# ИСПРАВЛЕНИЕ 28.01.2026: Диалог переназначения ДАН


class SupervisionReassignDANDialog(QDialog):
    """ИСПРАВЛЕНИЕ 28.01.2026: Диалог переназначения ДАН для надзора"""

    def __init__(self, parent, card_id, current_dan_name, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.current_dan_name = current_dan_name
        self.db = DatabaseManager()
        self.api_client = api_client

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        title_bar = CustomTitleBar(self, 'Переназначить ДАН', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        info_label = QLabel('Переназначение исполнителя ДАН:')
        info_label.setStyleSheet('font-size: 13px; font-weight: bold;')
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        current_frame = QFrame()
        current_frame.setStyleSheet("""
            QFrame {
                background-color: #FFF3CD;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        current_layout = QVBoxLayout()
        current_layout.setContentsMargins(0, 0, 0, 0)

        current_label = QLabel(f"Текущий ДАН: <b>{self.current_dan_name}</b>")
        current_label.setStyleSheet('font-size: 11px; color: #333;')
        current_label.setAlignment(Qt.AlignCenter)
        current_layout.addWidget(current_label)

        current_frame.setLayout(current_layout)
        layout.addWidget(current_frame)

        form_layout = QFormLayout()
        self.dan_combo = CustomComboBox()

        if self.api_client:
            try:
                all_employees = self.api_client.get_employees()
                dans = [e for e in all_employees if e.get('position') == 'ДАН']
            except Exception as e:
                print(f"[API ERROR] Ошибка получения сотрудников: {e}")
                dans = self.db.get_employees_by_position('ДАН')
        else:
            dans = self.db.get_employees_by_position('ДАН')

        if not dans:
            CustomMessageBox(self, 'Внимание', 'Нет доступных сотрудников с должностью "ДАН"', 'warning').exec_()
            self.reject()
            return

        for dan in dans:
            self.dan_combo.addItem(dan['full_name'], dan['id'])

        try:
            if self.api_client:
                card_data = self.api_client.get_supervision_card(self.card_id)
                current_dan_id = card_data.get('dan_id')
            else:
                card_data = self.db.get_supervision_card_by_id(self.card_id)
                current_dan_id = card_data.get('dan_id')

            if current_dan_id:
                for i in range(self.dan_combo.count()):
                    if self.dan_combo.itemData(i) == current_dan_id:
                        self.dan_combo.setCurrentIndex(i)
                        break
        except Exception as e:
            print(f"[WARNING] Не удалось получить ID текущего ДАН: {e}")

        form_layout.addRow('Новый ДАН:', self.dan_combo)
        layout.addLayout(form_layout)

        hint = QLabel('Исполнитель будет изменен БЕЗ перемещения карточки')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #FF9800; font-size: 10px; font-style: italic; font-weight: bold;')
        layout.addWidget(hint)

        save_btn = QPushButton('Переназначить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                padding: 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #F57C00; }
        """)
        save_btn.clicked.connect(self.save_reassignment)
        layout.addWidget(save_btn)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
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
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)

        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setFixedWidth(450)

    def save_reassignment(self):
        """Сохранение нового назначения ДАН"""
        new_dan_id = self.dan_combo.currentData()

        if not new_dan_id:
            CustomMessageBox(self, 'Ошибка', 'Выберите ДАН', 'warning').exec_()
            return

        try:
            # ИСПРАВЛЕНИЕ 29.01.2026: Получаем старого ДАН и contract_id для переназначения платежей
            old_dan_id = None
            contract_id = None

            if self.api_client:
                try:
                    card_data = self.api_client.get_supervision_card(self.card_id)
                    if card_data:
                        old_dan_id = card_data.get('dan_id')
                        contract_id = card_data.get('contract_id')
                        print(f"[DEBUG] Старый ДАН: {old_dan_id}, contract_id: {contract_id}")
                except Exception as e:
                    print(f"[WARN] Ошибка получения данных карточки: {e}")

            # Если не получили через API - пробуем локально
            if old_dan_id is None:
                card_data = self.db.get_supervision_card_data(self.card_id)
                if card_data:
                    old_dan_id = card_data.get('dan_id')
                    contract_id = card_data.get('contract_id')

            if self.api_client:
                try:
                    update_data = {'dan_id': new_dan_id}
                    self.api_client.update_supervision_card(self.card_id, update_data)
                    print(f"[API] ДАН переназначен через API")

                    # ИСПРАВЛЕНИЕ 29.01.2026: Переназначение платежей
                    if contract_id and old_dan_id and new_dan_id != old_dan_id:
                        self._reassign_dan_payments(contract_id, old_dan_id, new_dan_id)

                    CustomMessageBox(self, 'Успех', 'ДАН успешно переназначен', 'success').exec_()
                    self.accept()
                    return
                except Exception as e:
                    print(f"[API ERROR] Ошибка переназначения через API: {e}")
                    import traceback
                    traceback.print_exc()
                    print("[INFO] Пытаемся сохранить локально...")

            self.db.update_supervision_card(self.card_id, {'dan_id': new_dan_id})
            print(f"[DB] ДАН переназначен: dan_id={new_dan_id}")

            CustomMessageBox(self, 'Успех', 'ДАН успешно переназначен', 'success').exec_()
            self.accept()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка переназначения: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось переназначить ДАН:\n{str(e)}', 'error').exec_()

    def _reassign_dan_payments(self, contract_id, old_dan_id, new_dan_id):
        """ИСПРАВЛЕНИЕ 29.01.2026: Переназначение платежей ДАН"""
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            role = 'ДАН'

            # Получаем все платежи для этого контракта
            try:
                all_payments = self.api_client.get_payments_for_contract(contract_id)
            except Exception as e:
                print(f"[WARN] Ошибка получения платежей через API: {e}")
                all_payments = []

            # Ищем платежи для старого ДАН
            old_payments = []
            print(f"[DEBUG] Поиск платежей ДАН: role='{role}', old_dan_id={old_dan_id}")
            print(f"[DEBUG] Всего платежей для контракта: {len(all_payments)}")

            for payment in all_payments:
                # ИСПРАВЛЕНИЕ 30.01.2026: Пропускаем уже переназначенные платежи
                # чтобы избежать дублирования при повторном переназначении
                if payment.get('reassigned'):
                    print(f"[DEBUG] Пропускаем уже переназначенный платеж ДАН ID={payment.get('id')}")
                    continue

                payment_role = payment.get('role') or ''
                payment_employee_id = payment.get('employee_id')

                if payment_role == role and payment_employee_id == old_dan_id:
                    old_payments.append(payment)
                    print(f"[DEBUG] НАЙДЕН платеж ID={payment.get('id')}, тип={payment.get('payment_type')}")

            print(f"[DEBUG] Найдено платежей ДАН для переназначения: {len(old_payments)}")

            if old_payments:
                for old_payment in old_payments:
                    old_payment_id = old_payment.get('id')
                    payment_type = old_payment.get('payment_type', 'Неизвестно')

                    # 1. Помечаем старую запись как переназначенную
                    try:
                        self.api_client.update_payment(old_payment_id, {
                            'reassigned': True,
                            'report_month': current_month
                        })
                        print(f"[API] Старый платеж ДАН {old_payment_id} ({payment_type}) помечен как переназначенный")
                    except Exception as e:
                        print(f"[WARN] Ошибка обновления старого платежа ДАН через API: {e}")

                    # 2. Создаем новую запись для нового ДАН
                    # ИСПРАВЛЕНИЕ 30.01.2026: reassigned=False для НОВЫХ платежей
                    new_payment_data = {
                        'contract_id': contract_id,
                        'supervision_card_id': self.card_id,
                        'employee_id': new_dan_id,
                        'role': role,
                        'stage_name': old_payment.get('stage_name'),
                        'calculated_amount': old_payment.get('calculated_amount', 0),
                        'manual_amount': old_payment.get('manual_amount'),
                        'final_amount': old_payment.get('final_amount', 0),
                        'is_manual': old_payment.get('is_manual', 0),
                        'payment_type': payment_type,
                        'report_month': current_month,
                        'reassigned': False,
                        'old_employee_id': old_dan_id
                    }

                    try:
                        self.api_client.create_payment(new_payment_data)
                        print(f"[API] Создан новый платеж ДАН ({payment_type}) для исполнителя {new_dan_id}")
                    except Exception as e:
                        print(f"[WARN] Ошибка создания нового платежа ДАН через API: {e}")
            else:
                # Если старых платежей нет - создаём новые для нового ДАН
                print(f"[INFO] Платежи для старого ДАН не найдены, создаём новые")

                # Рассчитываем сумму для новых платежей
                try:
                    full_amount = 0

                    # Пробуем через API
                    if self.api_client:
                        try:
                            print(f"[DEBUG] Вызов calculate_payment_amount для ДАН: contract_id={contract_id}, employee_id={new_dan_id}, role={role}")
                            result = self.api_client.calculate_payment_amount(contract_id, new_dan_id, role)
                            print(f"[DEBUG] Результат API calculate_payment_amount ДАН: {result}")
                            full_amount = float(result) if result else 0
                        except Exception as e:
                            print(f"[WARN] Ошибка API расчёта суммы ДАН: {e}")

                    # Если API вернул 0 или ошибку - пробуем локальную БД
                    if full_amount == 0:
                        try:
                            full_amount = self.db.calculate_payment_amount(contract_id, new_dan_id, role)
                            print(f"[DEBUG] Результат локальной БД calculate_payment_amount ДАН: {full_amount}")
                        except Exception as e:
                            print(f"[WARN] Ошибка локальной БД расчёта суммы ДАН: {e}")

                    print(f"[DEBUG] Итоговая рассчитанная сумма для ДАН: {full_amount}")

                    if full_amount == 0:
                        print(f"[WARN] Тариф для роли 'ДАН' не найден или равен 0. Проверьте настройки тарифов!")

                    # Создаём полную оплату для ДАН
                    # ИСПРАВЛЕНИЕ 30.01.2026: reassigned=False для НОВЫХ платежей
                    payment_data = {
                        'contract_id': contract_id,
                        'supervision_card_id': self.card_id,
                        'employee_id': new_dan_id,
                        'role': role,
                        'stage_name': None,
                        'calculated_amount': full_amount,
                        'final_amount': full_amount,
                        'payment_type': 'Полная оплата',
                        'report_month': current_month,
                        'reassigned': False,
                        'old_employee_id': old_dan_id
                    }

                    try:
                        self.api_client.create_payment(payment_data)
                        print(f"[API] Создан новый платеж ДАН (Полная оплата) для исполнителя {new_dan_id}: {full_amount:.2f}")
                    except Exception as e:
                        print(f"[WARN] Ошибка создания платежа ДАН через API: {e}")

                except Exception as e:
                    print(f"[ERROR] Ошибка создания новых платежей ДАН: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"[ERROR] Ошибка переназначения платежей ДАН: {e}")
            import traceback
            traceback.print_exc()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 2 + screen.top()
        self.move(x, y)


class AssignExecutorsDialog(QDialog):
    """Диалог назначения исполнителей (ДАН и СМП) при перемещении карточки на рабочую стадию"""

    def __init__(self, parent, card_id, stage_name, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.stage_name = stage_name
        self.db = DatabaseManager()
        self.api_client = api_client
        self.assigned_dan_id = None
        self.assigned_smp_id = None

        # Убираем стандартную рамку
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        # Кастомный title bar
        title_bar = CustomTitleBar(self, 'Назначение исполнителей', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Контент
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        title = QLabel('Для перемещения на рабочую стадию необходимо назначить исполнителей')
        title.setStyleSheet('font-size: 12px; color: #333;')
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # Название стадии
        stage_label = QLabel(f'Стадия: "{self.stage_name}"')
        stage_label.setStyleSheet('font-size: 14px; font-weight: bold; color: #FF9800;')
        stage_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(stage_label)

        # Форма назначения
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Старший менеджер проектов
        self.smp_combo = CustomComboBox()
        self._load_managers()
        form_layout.addRow('Старший менеджер:', self.smp_combo)

        # ДАН
        self.dan_combo = CustomComboBox()
        self._load_dans()
        form_layout.addRow('ДАН:', self.dan_combo)

        layout.addLayout(form_layout)

        # Подсказка
        hint = QLabel('После назначения исполнителей карточка будет перемещена на стадию')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic; margin-top: 10px;')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Назначить и продолжить')
        save_btn.setFixedHeight(36)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 20px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        save_btn.clicked.connect(self.save_and_continue)
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 20px;
                border-radius: 4px;
                border: none;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setMinimumWidth(450)

    def _load_managers(self):
        """Загрузка списка старших менеджеров"""
        managers = []
        if self.api_client and self.api_client.is_online:
            try:
                managers = self.api_client.get_employees_by_position('Старший менеджер проектов')
            except Exception as e:
                print(f"[WARN] API ошибка загрузки СМП: {e}")
                managers = self.db.get_employees_by_position('Старший менеджер проектов')
        else:
            managers = self.db.get_employees_by_position('Старший менеджер проектов')

        self.smp_combo.addItem('Не назначен', None)
        for manager in managers:
            self.smp_combo.addItem(manager['full_name'], manager['id'])

    def _load_dans(self):
        """Загрузка списка ДАН"""
        dans = []
        if self.api_client and self.api_client.is_online:
            try:
                dans = self.api_client.get_employees_by_position('ДАН')
            except Exception as e:
                print(f"[WARN] API ошибка загрузки ДАН: {e}")
                dans = self.db.get_employees_by_position('ДАН')
        else:
            dans = self.db.get_employees_by_position('ДАН')

        self.dan_combo.addItem('Не назначен', None)
        for dan in dans:
            self.dan_combo.addItem(dan['full_name'], dan['id'])

    def save_and_continue(self):
        """Сохранение назначенных исполнителей"""
        self.assigned_dan_id = self.dan_combo.currentData()
        self.assigned_smp_id = self.smp_combo.currentData()

        # Проверяем, что хотя бы один исполнитель назначен
        if not self.assigned_dan_id and not self.assigned_smp_id:
            QMessageBox.warning(
                self,
                'Внимание',
                'Необходимо назначить хотя бы одного исполнителя (ДАН или Старшего менеджера)'
            )
            return

        # Сохраняем в БД
        updates = {}
        if self.assigned_dan_id:
            updates['dan_id'] = self.assigned_dan_id
        if self.assigned_smp_id:
            updates['senior_manager_id'] = self.assigned_smp_id

        if updates:
            if self.api_client and self.api_client.is_online:
                try:
                    self.api_client.update_supervision_card(self.card_id, updates)
                    print(f"[API] Назначены исполнители для карточки {self.card_id}: {updates}")
                except Exception as e:
                    print(f"[WARN] API ошибка назначения исполнителей: {e}")
                    self.db.update_supervision_card(self.card_id, updates)
            else:
                self.db.update_supervision_card(self.card_id, updates)
                print(f"[LOCAL] Назначены исполнители для карточки {self.card_id}: {updates}")

        self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 2 + screen.top()
        self.move(x, y)


class SupervisionFileUploadDialog(QDialog):
    """Диалог загрузки файла для карточки авторского надзора с выбором стадии и даты"""

    def __init__(self, parent, card_data, stages, api_client=None):
        super().__init__(parent)
        self.card_data = card_data
        self.stages = stages  # Список стадий для выбора
        self.api_client = api_client
        self.db = DatabaseManager()
        self.selected_file_path = None
        self.result_data = None  # Для передачи данных родителю

        # Убираем стандартную рамку
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        # Кастомный title bar
        title_bar = CustomTitleBar(self, 'Загрузка файла', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Контент
        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # Информация о проекте
        project_info = self.card_data.get('address', '') or self.card_data.get('contract_number', 'Без адреса')
        info_label = QLabel(f'Проект: {project_info}')
        info_label.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Форма
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        form_layout.setLabelAlignment(Qt.AlignRight)

        # Выбор файла
        file_widget = QWidget()
        file_layout = QHBoxLayout()
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)

        self.file_label = QLabel('Файл не выбран')
        self.file_label.setStyleSheet('''
            QLabel {
                color: #666;
                font-size: 12px;
                padding: 4px 8px;
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                min-height: 20px;
            }
        ''')
        self.file_label.setMinimumWidth(200)
        file_layout.addWidget(self.file_label, 1)

        browse_btn = QPushButton('Обзор...')
        browse_btn.setFixedHeight(28)
        browse_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 12px;
                border-radius: 4px;
                border: none;
                font-size: 12px;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        browse_btn.clicked.connect(self.browse_file)
        file_layout.addWidget(browse_btn)

        file_widget.setLayout(file_layout)
        form_layout.addRow('Файл:', file_widget)

        # Выбор стадии
        self.stage_combo = CustomComboBox()
        self.stage_combo.setFixedHeight(28)
        self.stage_combo.addItem('-- Выберите стадию --', None)
        for stage in self.stages:
            self.stage_combo.addItem(stage, stage)
        form_layout.addRow('Стадия:', self.stage_combo)

        # Выбор даты
        self.date_edit = CustomDateEdit()
        self.date_edit.setFixedHeight(28)
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow('Дата:', self.date_edit)

        # Разделитель
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet('color: #E0E0E0;')
        form_layout.addRow(separator)

        # Доп. поля: данные для таблицы сроков надзора
        fields_hint = QLabel('Данные для таблицы сроков (необязательно)')
        fields_hint.setStyleSheet('color: #888; font-size: 10px; font-style: italic;')
        form_layout.addRow(fields_hint)

        field_style = '''
            QLineEdit {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 12px;
                background-color: #FAFAFA;
            }
            QLineEdit:focus {
                border-color: #ffd93c;
                background-color: #FFFFFF;
            }
        '''

        # Бюджет план
        self.budget_planned_edit = QLineEdit()
        self.budget_planned_edit.setFixedHeight(28)
        self.budget_planned_edit.setPlaceholderText('0')
        self.budget_planned_edit.setStyleSheet(field_style)
        form_layout.addRow('Бюджет план:', self.budget_planned_edit)

        # Бюджет факт
        self.budget_actual_edit = QLineEdit()
        self.budget_actual_edit.setFixedHeight(28)
        self.budget_actual_edit.setPlaceholderText('0')
        self.budget_actual_edit.setStyleSheet(field_style)
        form_layout.addRow('Бюджет факт:', self.budget_actual_edit)

        # Поставщик
        self.supplier_edit = QLineEdit()
        self.supplier_edit.setFixedHeight(28)
        self.supplier_edit.setPlaceholderText('Название поставщика')
        self.supplier_edit.setStyleSheet(field_style)
        form_layout.addRow('Поставщик:', self.supplier_edit)

        # Комиссия
        self.commission_edit = QLineEdit()
        self.commission_edit.setFixedHeight(28)
        self.commission_edit.setPlaceholderText('0')
        self.commission_edit.setStyleSheet(field_style)
        form_layout.addRow('Комиссия:', self.commission_edit)

        # Примечания
        self.notes_edit = QLineEdit()
        self.notes_edit.setFixedHeight(28)
        self.notes_edit.setPlaceholderText('Примечания')
        self.notes_edit.setStyleSheet(field_style)
        form_layout.addRow('Примечания:', self.notes_edit)

        layout.addLayout(form_layout)

        # Подсказка
        hint = QLabel('После загрузки файл будет привязан к выбранной стадии.\nДанные бюджета и поставщика обновятся в таблице сроков.')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic; margin-top: 10px;')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        self.upload_btn = QPushButton('Загрузить')
        self.upload_btn.setFixedHeight(28)
        self.upload_btn.setEnabled(False)  # Изначально неактивна
        self.upload_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 20px;
                font-weight: bold;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #e6c435; }
            QPushButton:pressed { background-color: #d4b42e; }
            QPushButton:disabled {
                background-color: #E0E0E0;
                color: #999;
            }
        """)
        self.upload_btn.clicked.connect(self.upload_file)
        buttons_layout.addWidget(self.upload_btn)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 20px;
                border-radius: 6px;
                border: none;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        self.setFixedWidth(420)

    def browse_file(self):
        """Открыть диалог выбора файла"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Выберите файл',
            '',
            'Все файлы (*.*);;Изображения (*.png *.jpg *.jpeg);;PDF (*.pdf);;Документы (*.doc *.docx)'
        )
        if file_path:
            self.selected_file_path = file_path
            # Показываем только имя файла
            file_name = os.path.basename(file_path)
            self.file_label.setText(file_name)
            self.file_label.setStyleSheet('''
                QLabel {
                    color: #333;
                    font-size: 12px;
                    padding: 4px 8px;
                    background-color: #E8F5E9;
                    border: 1px solid #81C784;
                    border-radius: 4px;
                    min-height: 20px;
                }
            ''')
            self.update_upload_button()

    def update_upload_button(self):
        """Обновить состояние кнопки загрузки"""
        has_file = self.selected_file_path is not None
        has_stage = self.stage_combo.currentData() is not None
        self.upload_btn.setEnabled(has_file and has_stage)

    def _parse_number(self, text):
        """Парсинг числа из строки (поддержка пробелов, запятых)"""
        text = text.strip().replace(' ', '').replace(',', '.')
        if not text:
            return 0
        try:
            return float(text)
        except ValueError:
            return 0

    def upload_file(self):
        """Подготовить данные и закрыть диалог"""
        if not self.selected_file_path:
            return

        stage = self.stage_combo.currentData()
        if not stage:
            return

        date = self.date_edit.date().toString('dd.MM.yyyy')

        # Сохраняем данные для передачи родителю
        self.result_data = {
            'file_path': self.selected_file_path,
            'stage': stage,
            'date': date,
            'file_name': os.path.basename(self.selected_file_path),
            # Доп. поля для таблицы сроков
            'budget_planned': self._parse_number(self.budget_planned_edit.text()),
            'budget_actual': self._parse_number(self.budget_actual_edit.text()),
            'supplier': self.supplier_edit.text().strip(),
            'commission': self._parse_number(self.commission_edit.text()),
            'notes': self.notes_edit.text().strip(),
        }

        self.accept()

    def get_result(self):
        """Получить результат диалога"""
        return self.result_data

    def showEvent(self, event):
        super().showEvent(event)
        # Подключаем сигнал изменения стадии
        self.stage_combo.currentIndexChanged.connect(self.update_upload_button)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 2 + screen.top()
        self.move(x, y)
