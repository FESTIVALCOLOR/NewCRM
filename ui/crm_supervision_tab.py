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
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
import os

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
        self.db = DatabaseManager()
        # Получаем offline_manager от родителя (main_window)
        self.offline_manager = getattr(parent, 'offline_manager', None) if parent else None

        # Инициализация Yandex Disk
        try:
            self.yandex_disk = YandexDiskManager(YANDEX_DISK_TOKEN)
        except Exception as e:
            print(f"[WARNING] Не удалось инициализировать Yandex Disk: {e}")
            self.yandex_disk = None

        self.init_ui()
        # ОПТИМИЗАЦИЯ: Отложенная загрузка данных для ускорения запуска
        QTimer.singleShot(0, self.load_cards_for_current_tab)
    
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

        # ========== КНОПКА ОБНОВЛЕНИЯ ДАННЫХ ==========
        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить', 'Обновить данные с сервера', icon_size=12)
        refresh_btn.clicked.connect(self.refresh_current_tab)
        refresh_btn.setStyleSheet('''
            QPushButton {
                padding: 2px 8px;
                font-weight: 500;
                font-size: 11px;
                color: #000000;
                background-color: #ffffff;
                border: 1px solid #d9d9d9;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #e3f2fd;
                border-color: #2196F3;
            }
        ''')
        header_layout.addWidget(refresh_btn)
        # ================================================

        # ========== КНОПКА СТАТИСТИКИ (SVG) ==========
        if self.employee['position'] not in ['ДАН']:
            stats_btn = IconLoader.create_icon_button('stats', 'Статистика CRM', 'Показать статистику надзора', icon_size=12)
            stats_btn.setStyleSheet("""
                QPushButton {
                    padding: 2px 8px;
                    font-weight: 500;
                    font-size: 11px;
                    color: #000000;
                    background-color: #ffffff;
                    border: 1px solid #d9d9d9;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #fafafa;
                    border-color: #c0c0c0;
                }
            """)
            stats_btn.clicked.connect(self.show_statistics)
            header_layout.addWidget(stats_btn)
        # =============================================
        
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
        if self.employee['position'] not in ['ДАН']:
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
            if self.api_client and self.api_client.is_online:
                try:
                    cards = self.api_client.get_supervision_cards(status='archived')
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки архива: {e}")
                    cards = self.db.get_supervision_cards_archived()
            else:
                cards = self.db.get_supervision_cards_archived()

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
            if self.api_client and self.api_client.is_online:
                try:
                    cards = self.api_client.get_supervision_cards(status='archived')
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки архива: {e}")
                    cards = self.db.get_supervision_cards_archived()
            else:
                cards = self.db.get_supervision_cards_archived()

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
                    archive_card = ArchiveCard(card_data, self.db, card_type='supervision')
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

    def load_cards_for_current_tab(self):
        """Загрузка карточек для текущей вкладки"""
        self.load_active_cards()
        if self.employee['position'] not in ['ДАН']:
            self.load_archive_cards()
            
    def load_active_cards(self):
        """Загрузка активных карточек с fallback на локальную БД"""
        print("\n=== ЗАГРУЗКА АКТИВНЫХ КАРТОЧЕК НАДЗОРА ===")

        cards = None
        api_error = None

        # Попытка загрузки через API (только если online)
        if self.api_client and self.api_client.is_online:
            try:
                cards = self.api_client.get_supervision_cards(status="active")
                print(f"[API] Получено: {len(cards)} карточек")
            except Exception as e:
                api_error = e
                print(f"[API ERROR] {e}")
                print("[FALLBACK] Переключение на локальную БД...")

        # Fallback на локальную БД
        if cards is None:
            try:
                cards = self.db.get_supervision_cards_active()
                print(f"[DB] Получено: {len(cards)} карточек")

                # Показываем уведомление об offline режиме
                if api_error and not hasattr(self, '_offline_notification_shown'):
                    self._offline_notification_shown = True
                    self._show_offline_notification(api_error)
            except Exception as db_error:
                print(f"[DB ERROR] {db_error}")
                self._show_critical_error(api_error, db_error)
                return

        for card in cards:
            print(f"  - Card ID={card.get('id')} | Contract={card.get('contract_id')} | "
                  f"Колонка='{card.get('column_name')}' | Статус={card.get('status')}")

        if not hasattr(self.active_widget, 'columns'):
            print(" Нет атрибута columns в active_widget")
            return

        columns_dict = self.active_widget.columns

        # Очищаем колонки
        for column in columns_dict.values():
            column.clear_cards()

        # Добавляем карточки с учетом прав
        for card_data in cards:
            # Проверяем, должен ли видеть ДАН эту карточку
            if self.employee['position'] == 'ДАН':
                if card_data.get('dan_id') != self.employee['id']:
                    print(f"  - Скрыта для ДАН: Card ID={card_data.get('id')}")
                    continue

            column_name = card_data.get('column_name', 'Новый заказ')

            print(f"  + Добавление карточки ID={card_data.get('id')} в колонку '{column_name}'")

            if column_name in columns_dict:
                columns_dict[column_name].add_card(card_data)
            else:
                print(f"  ! Колонка '{column_name}' не найдена!")
                print(f"  Доступные колонки: {list(columns_dict.keys())}")

        self.update_tab_counters()
        print("="*40 + "\n")

    def load_archive_cards(self):
        """Загрузка архивных карточек с fallback на локальную БД"""
        print("\n=== ЗАГРУЗКА АРХИВА НАДЗОРА ===")

        cards = None
        api_error = None

        # Попытка загрузки через API (только если online)
        if self.api_client and self.api_client.is_online:
            try:
                cards = self.api_client.get_supervision_cards(status="archived")
                print(f"[API] Получено: {len(cards)} архивных карточек")
            except Exception as e:
                api_error = e
                print(f"[API ERROR] {e}")
                print("[FALLBACK] Переключение на локальную БД...")

        # Fallback на локальную БД
        if cards is None:
            try:
                cards = self.db.get_supervision_cards_archived()
                print(f"[DB] Получено: {len(cards)} архивных карточек")
            except Exception as db_error:
                print(f"[DB ERROR] {db_error}")
                cards = []  # Пустой архив при ошибке

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
                if self.employee['position'] == 'ДАН':
                    if card_data.get('dan_id') != self.employee['id']:
                        continue

                archive_card = ArchiveCard(card_data, self.db, card_type='supervision')
                archive_layout.addWidget(archive_card)
        else:
            empty_label = QLabel('Архив пуст')
            empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            archive_layout.addWidget(empty_label)
        
        archive_layout.addStretch(1)

        self.update_tab_counters()
        print("="*40 + "\n")

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
        if self.api_client and self.api_client.is_online:
            try:
                self.api_client.update_supervision_card(card_id, updates)
                return
            except Exception as e:
                print(f"[API ERROR] {e}, fallback на локальную БД")

        # Fallback на локальную БД
        self.db.update_supervision_card(card_id, updates)

        # Добавляем в очередь offline операций
        if self.api_client and self.offline_manager:
            from utils.offline_manager import OperationType
            self.offline_manager.queue_operation(
                OperationType.UPDATE, 'supervision_card', card_id, updates
            )

    def update_tab_counters(self):
        """Обновление счетчиков вкладок"""
        # Подсчет активных
        active_count = 0
        if hasattr(self.active_widget, 'columns'):
            for column in self.active_widget.columns.values():
                active_count += column.cards_list.count()
        
        self.tabs.setTabText(0, f'Активные проекты ({active_count})')
        
        # Подсчет архива
        if self.employee['position'] not in ['ДАН']:
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
            # ИСПРАВЛЕНИЕ: Проверка и автоматическое принятие работы при перемещении
            if self.employee['position'] not in ['ДАН'] and from_column not in ['Новый заказ', 'Выполненный проект']:
                # Получаем данные карточки через API или локальную БД
                card_info = None
                if self.api_client:
                    try:
                        card_data = self.api_client.get_supervision_card(card_id)
                        if card_data:
                            card_info = {
                                'dan_completed': card_data.get('dan_completed', 0),
                                'dan_name': card_data.get('dan_name', 'ДАН')
                            }
                    except Exception as e:
                        print(f"[WARN] Ошибка API: {e}")

                if card_info is None:
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    cursor.execute('''
                    SELECT sc.dan_completed, e.full_name as dan_name
                    FROM supervision_cards sc
                    LEFT JOIN employees e ON sc.dan_id = e.id
                    WHERE sc.id = ?
                    ''', (card_id,))

                    card_info = cursor.fetchone()
                    self.db.close()

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
                    if dan_completed == 0 and self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов']:
                        print(f"\n[AUTO ACCEPT] Автоматическое принятие стадии надзора '{from_column}'")

                        # Добавляем запись в историю о принятии
                        if self.api_client:
                            try:
                                self.api_client.add_supervision_history(
                                    card_id,
                                    'accepted',
                                    f"Стадия '{from_column}' автоматически принята при перемещении руководством. Исполнитель: {dan_name}",
                                    self.employee['id']
                                )
                            except Exception as e:
                                print(f"[WARN] Ошибка API add_supervision_history: {e}")
                                self.db.add_supervision_history(
                                    card_id,
                                    'accepted',
                                    f"Стадия '{from_column}' автоматически принята при перемещении руководством. Исполнитель: {dan_name}",
                                    self.employee['id']
                                )
                        else:
                            self.db.add_supervision_history(
                                card_id,
                                'accepted',
                                f"Стадия '{from_column}' автоматически принята при перемещении руководством. Исполнитель: {dan_name}",
                                self.employee['id']
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
                                # Получаем назначенных исполнителей
                                cursor.execute('''
                                SELECT dan_id, senior_manager_id
                                FROM supervision_cards
                                WHERE id = ?
                                ''', (card_id,))

                                executors_row = cursor.fetchone()

                                if executors_row:
                                    # Создаем оплату для ДАН
                                    if executors_row['dan_id']:
                                        if self.api_client:
                                            try:
                                                payment_data = {
                                                    'contract_id': contract_id,
                                                    'employee_id': executors_row['dan_id'],
                                                    'role': 'ДАН',
                                                    'stage_name': from_column,
                                                    'payment_type': 'Полная оплата',
                                                    'report_month': current_month,
                                                    'supervision_card_id': card_id
                                                }
                                                result = self.api_client.create_payment(payment_data)
                                                print(f"    Создана оплата для ДАН через API по стадии '{from_column}'")
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
                                        if self.api_client:
                                            try:
                                                payment_data = {
                                                    'contract_id': contract_id,
                                                    'employee_id': executors_row['senior_manager_id'],
                                                    'role': 'Старший менеджер проектов',
                                                    'stage_name': from_column,
                                                    'payment_type': 'Полная оплата',
                                                    'report_month': current_month,
                                                    'supervision_card_id': card_id
                                                }
                                                result = self.api_client.create_payment(payment_data)
                                                print(f"    Создана оплата для СМП через API по стадии '{from_column}'")
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
            if self.employee['position'] not in ['ДАН']:
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

        if self.api_client:
            try:
                self.api_client.update_contract(contract_id, {'termination_reason': reason.strip()})
            except Exception as e:
                print(f"[WARN] API ошибка сохранения причины: {e}")
                self.db.update_contract(contract_id, {'termination_reason': reason.strip()})
        else:
            self.db.update_contract(contract_id, {'termination_reason': reason.strip()})
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

class SupervisionColumn(QFrame):
    """Колонка для карточек надзора"""
    card_moved = pyqtSignal(int, str, str)

    def __init__(self, column_name, employee, db, api_client=None):
        super().__init__()
        self.column_name = column_name
        self.employee = employee
        self.db = db
        self.api_client = api_client
        self.init_ui()
    
    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(340)
        self.setMaximumWidth(360)
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
        
        # Заголовок
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
        layout.addWidget(self.header_label)
        
        # Список карточек
        can_drag = self.employee['position'] not in ['ДАН']
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
    
    def update_header_count(self):
        """Обновление счетчика"""
        count = self.cards_list.count() if hasattr(self, 'cards_list') else 0
        
        if count == 0:
            self.header_label.setText(self.column_name)
        else:
            self.header_label.setText(f"{self.column_name} ({count})")
    
    def add_card(self, card_data):
        """Добавление карточки"""
        card_widget = SupervisionCard(card_data, self.employee, self.db, self.api_client)
        
        recommended_size = card_widget.sizeHint()
        exact_height = recommended_size.height()
        card_widget.setMinimumHeight(exact_height)
        
        item = QListWidgetItem()
        item.setData(Qt.UserRole, card_data.get('id'))
        item.setSizeHint(QSize(200, exact_height + 10))
        
        self.cards_list.addItem(item)
        self.cards_list.setItemWidget(item, card_widget)
        
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
            self.setStyleSheet("""
                SupervisionCard {
                    background-color: white;
                    border: 2px solid #CCCCCC;
                    border-radius: 8px;
                }
                SupervisionCard:hover {
                    border: 2px solid #d9d9d9;
                    background-color: #fafafa;
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
        if self.employee['position'] not in ['ДАН'] and self.card_data.get('dan_completed'):
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
        if self.employee['position'] not in ['ДАН']:
            # ========== 1. ДОБАВИТЬ ЗАПИСЬ (SVG) ==========
            add_note_btn = IconLoader.create_icon_button('note', 'Добавить запись', 'Добавить запись в историю', icon_size=12)
            add_note_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95A5A6;
                    color: white;
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #7F8C8D; }
            """)
            add_note_btn.setFixedHeight(32)
            add_note_btn.clicked.connect(self.add_project_note)
            layout.addWidget(add_note_btn, 0)
            
            # ========== 2. ПРИОСТАНОВИТЬ/ВОЗОБНОВИТЬ (SVG) ==========
            if self.card_data.get('is_paused'):
                pause_btn = IconLoader.create_icon_button('play', 'Возобновить', 'Возобновить работу над проектом', icon_size=12)
                pause_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
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
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #E67E22; }
                """)
                pause_btn.clicked.connect(self.pause_card)
            
            pause_btn.setFixedHeight(38)
            layout.addWidget(pause_btn, 0)
            
            # ========== 3. РЕДАКТИРОВАНИЕ (SVG) ==========
            edit_btn = IconLoader.create_icon_button('edit', 'Редактирование', 'Редактировать карточку', icon_size=12)
            edit_btn.setStyleSheet("""
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
            edit_btn.setFixedHeight(38)
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
                    padding: 6px 12px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #7F8C8D; }
            """)
            add_note_btn.setFixedHeight(32)
            add_note_btn.clicked.connect(self.add_project_note)
            layout.addWidget(add_note_btn, 0)
            
            # ========== 2. СДАТЬ РАБОТУ ИЛИ ОЖИДАНИЕ ==========
            if not self.card_data.get('dan_completed'):
                submit_btn = IconLoader.create_icon_button('submit', 'Сдать работу', 'Отметить работу как выполненную', icon_size=12)
                submit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #229954; }
                """)
                submit_btn.setFixedHeight(38)
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
        
        # Кнопка-заголовок
        self.team_toggle_btn = QPushButton(f"Команда ({len(team_members)})  ▶")
        self.team_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px;
                text-align: left;
                font-size: 9px;
                font-weight: bold;
                color: #555;
            }
            QPushButton:hover { background-color: #E8E9EA; }
        """)
        self.team_toggle_btn.setFixedHeight(30)
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
        team_layout.setSpacing(2)
        team_layout.setContentsMargins(3, 3, 3, 3)
        
        for role, name in team_members:
            label = QLabel(f"{role}: {name}")
            label.setStyleSheet('font-size: 10px; color: #444;')
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
        
        if self.employee['position'] not in ['ДАН'] and self.card_data.get('dan_completed'):
            height += 55
            height += 38
        
        if self.card_data.get('is_paused'):
            height += 28
        
        if self.card_data.get('deadline'):
            height += 28
        
        if self.card_data.get('tags'):
            height += 28
        
        buttons_count = 1
        
        if self.employee['position'] not in ['ДАН']:
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
                if self.api_client:
                    try:
                        self.api_client.pause_supervision_card(
                            self.card_data['id'],
                            reason,
                            self.employee['id']
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

    def __init__(self, parent, card_data, employee, api_client=None):
        super().__init__(parent)
        self.card_data = card_data
        self.employee = employee
        self.db = DatabaseManager()
        self.api_client = api_client

        # Инициализация Yandex Disk
        try:
            self.yandex_disk = YandexDiskManager(YANDEX_DISK_TOKEN)
        except Exception as e:
            print(f"[WARNING] Не удалось инициализировать Yandex Disk: {e}")
            self.yandex_disk = None

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._loading_data = False
        self.init_ui()
        self.load_data()

        # ИСПРАВЛЕНИЕ: Подключаем автосохранение после загрузки данных
        if self.employee['position'] not in ['ДАН']:
            self.connect_autosave_signals()

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
        title = 'История проекта' if self.employee['position'] == 'ДАН' else 'Редактирование карточки надзора'

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

        # ВКЛАДКА 1: РЕДАКТИРОВАНИЕ (только для менеджеров)
        if self.employee['position'] not in ['ДАН']:
            edit_widget = QWidget()
            edit_layout = QVBoxLayout()

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
            form_layout.addRow('ДАН:', self.dan)

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

            # Дедлайн
            self.deadline = CustomDateEdit()
            self.deadline.setCalendarPopup(True)
            add_today_button_to_dateedit(self.deadline)
            self.deadline.setDate(QDate.currentDate())
            form_layout.addRow('Дедлайн:', self.deadline)

            # Теги
            self.tags = QLineEdit()
            self.tags.setPlaceholderText('Срочный, VIP...')
            form_layout.addRow('Теги:', self.tags)

            edit_layout.addLayout(form_layout)
            edit_layout.addStretch()
            edit_widget.setLayout(edit_layout)

            self.tabs.addTab(edit_widget, 'Редактирование')

        # ВКЛАДКА 2: ОПЛАТЫ НАДЗОРА (для ВСЕХ)
        payments_widget = self.create_payments_widget()
        self.payments_tab_index = self.tabs.addTab(payments_widget, 'Оплаты надзора')

        # ВКЛАДКА 3: ИНФОРМАЦИЯ О ПРОЕКТЕ (для ВСЕХ)
        info_widget = self.create_project_info_widget()
        self.project_info_tab_index = self.tabs.addTab(info_widget, 'Информация о проекте')

        # ВКЛАДКА 4: ФАЙЛЫ НАДЗОРА (для ВСЕХ)
        files_widget = self.create_files_widget()
        self.files_tab_index = self.tabs.addTab(files_widget, 'Файлы надзора')

        # История проекта теперь интегрирована в "Информация о проекте"
        # history_widget = self.create_history_widget()
        # self.tabs.addTab(history_widget, 'История проекта')

        layout.addWidget(self.tabs, 1)
        
        # Кнопки
        buttons_layout = QHBoxLayout()

        # НОВОЕ: Кнопка удаления заказа (только для руководителей)
        if self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов']:
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

        buttons_layout.addStretch()

        if self.employee['position'] not in ['ДАН']:
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

        # Ширина: 
        target_width = 950

        self.setMinimumWidth(950)
        self.setMinimumHeight(target_height)
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
        widget = QWidget()
        layout = QVBoxLayout()

        contract_id = self.card_data.get('contract_id')

        header = QLabel('Оплаты надзора по проекту')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)

        # Таблица оплат
        from PyQt5.QtWidgets import QTableWidget, QHeaderView, QTableWidgetItem, QHBoxLayout
        table = QTableWidget()
        # ВАЖНО: НЕ устанавливаем background-color для QTableWidget,
        # чтобы цвета ячеек работали корректно
        table.setStyleSheet("""
            QTableCornerButton::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
        """)
        table.setColumnCount(10)  # ИСПРАВЛЕНИЕ: Увеличено с 9 до 10 (добавлен столбец удаления)
        table.setHorizontalHeaderLabels([
            'Должность', 'ФИО', 'Стадия', 'Тип выплаты',
            'Выплата', 'Аванс', 'Доплата', 'Отчетный месяц', 'Корректировка', 'Действия'
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
            table.setRowCount(len(payments))

            for row, payment in enumerate(payments):
                # Определяем цвет строки в зависимости от статуса оплаты
                from PyQt5.QtGui import QColor
                payment_status = payment.get('payment_status')
                if payment_status == 'to_pay':
                    row_color = QColor('#FFF3CD')  # Светло-желтый
                elif payment_status == 'paid':
                    row_color = QColor('#D4EDDA')  # Светло-зеленый
                else:
                    row_color = QColor('#FFFFFF')  # Белый

                # Должность
                role_label = QLabel(payment.get('role', ''))
                role_label.setStyleSheet(f"background-color: {row_color.name()};")
                role_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 0, role_label)

                # ФИО
                name_label = QLabel(payment.get('employee_name', ''))
                name_label.setStyleSheet(f"background-color: {row_color.name()};")
                name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 1, name_label)

                # Стадия
                stage_label = QLabel(payment.get('stage_name', '') or '-')
                stage_label.setStyleSheet(f"background-color: {row_color.name()};")
                stage_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 2, stage_label)

                # Тип выплаты
                type_label = QLabel(payment.get('payment_type', ''))
                type_label.setStyleSheet(f"background-color: {row_color.name()};")
                type_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 3, type_label)

                # Выплата
                final_amount = payment.get('final_amount', 0)
                amount_label = QLabel(f"{final_amount:,.2f} ₽")
                amount_label.setStyleSheet(f"background-color: {row_color.name()};")
                amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                table.setCellWidget(row, 4, amount_label)

                # Аванс/Доплата
                payment_type = payment.get('payment_type', '')
                if payment_type == 'Аванс':
                    advance_label = QLabel(f"{final_amount:,.2f} ₽")
                    advance_label.setStyleSheet(f"background-color: {row_color.name()};")
                    advance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    table.setCellWidget(row, 5, advance_label)

                    balance_empty = QLabel('-')
                    balance_empty.setStyleSheet(f"background-color: {row_color.name()};")
                    balance_empty.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 6, balance_empty)
                elif payment_type == 'Доплата':
                    advance_empty = QLabel('-')
                    advance_empty.setStyleSheet(f"background-color: {row_color.name()};")
                    advance_empty.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 5, advance_empty)

                    balance_label = QLabel(f"{final_amount:,.2f} ₽")
                    balance_label.setStyleSheet(f"background-color: {row_color.name()};")
                    balance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                    table.setCellWidget(row, 6, balance_label)
                else:
                    advance_empty2 = QLabel('-')
                    advance_empty2.setStyleSheet(f"background-color: {row_color.name()};")
                    advance_empty2.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 5, advance_empty2)

                    balance_empty2 = QLabel('-')
                    balance_empty2.setStyleSheet(f"background-color: {row_color.name()};")
                    balance_empty2.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 6, balance_empty2)

                # Отчетный месяц
                from utils.date_utils import format_month_year
                formatted_month = format_month_year(payment.get('report_month', ''))
                month_label = QLabel(formatted_month)
                month_label.setStyleSheet(f"background-color: {row_color.name()};")
                month_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 7, month_label)

                # Кнопка корректировки (столбец 8, только для руководителей)
                if self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов']:
                    # Создаем виджет-контейнер для кнопки корректировки
                    adjust_widget = QWidget()
                    adjust_widget.setStyleSheet(f"background-color: {row_color.name()};")
                    adjust_layout = QHBoxLayout()
                    adjust_layout.setContentsMargins(0, 0, 0, 0)

                    adjust_btn = QPushButton('Изменить')
                    adjust_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #FF9800;
                            color: white;
                            padding: 5px 10px;
                            border-radius: 4px;
                            font-size: 10px;
                        }
                        QPushButton:hover { background-color: #F57C00; }
                    """)
                    adjust_btn.clicked.connect(
                        lambda checked, p_id=payment['id']: self.adjust_payment_amount(p_id)
                    )
                    adjust_layout.addWidget(adjust_btn)
                    adjust_widget.setLayout(adjust_layout)
                    table.setCellWidget(row, 8, adjust_widget)

                    # Создаем виджет-контейнер для кнопки удаления
                    delete_widget = QWidget()
                    delete_widget.setStyleSheet(f"background-color: {row_color.name()};")
                    delete_layout = QHBoxLayout()
                    delete_layout.setContentsMargins(0, 0, 0, 0)

                    delete_btn = QPushButton('[DELETE] Удалить')
                    delete_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #E74C3C;
                            color: white;
                            padding: 5px 10px;
                            border-radius: 4px;
                            font-size: 10px;
                        }
                        QPushButton:hover { background-color: #C0392B; }
                    """)
                    delete_btn.clicked.connect(
                        lambda checked, p_id=payment['id'], p_role=payment['role'], p_name=payment['employee_name']:
                        self.delete_payment(p_id, p_role, p_name)
                    )
                    delete_layout.addWidget(delete_btn)
                    delete_widget.setLayout(delete_layout)
                    table.setCellWidget(row, 9, delete_widget)

        # Настройка столбцов
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setMinimumSectionSize(150)
        header.resizeSection(1, 200)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        header.resizeSection(7, 150)
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Действия

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

        layout.addWidget(table)

        # Итого
        if contract_id:
            if self.api_client:
                try:
                    payments = self.api_client.get_payments_for_contract(contract_id)
                except Exception as e:
                    print(f"[WARNING] Ошибка загрузки оплат из API: {e}")
                    payments = self.db.get_payments_for_contract(contract_id)
            else:
                payments = self.db.get_payments_for_contract(contract_id)
            total = sum(p.get('final_amount', 0) for p in payments)
            total_label = QLabel(f'<b>Итого:</b> {total:,.2f} ₽')
            total_label.setStyleSheet('''
                font-size: 14px;
                padding: 10px;
                background-color: #f5f5f5;
                margin-top: 10px;
            ''')
            layout.addWidget(total_label)

        widget.setLayout(layout)
        return widget

    def delete_payment(self, payment_id, role, employee_name):
        """Удаление записи об оплате"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            f'Вы уверены, что хотите удалить оплату?\n\n'
            f'Должность: {role}\n'
            f'ФИО: {employee_name}\n\n'
            f' Это действие нельзя отменить!'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                # Удаляем запись из базы данных
                conn = self.db.connect()
                cursor = conn.cursor()

                cursor.execute('''
                DELETE FROM payments
                WHERE id = ?
                ''', (payment_id,))

                conn.commit()
                self.db.close()

                print(f"Оплата удалена: {role} - {employee_name} (ID: {payment_id})")

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
                print(f" Ошибка удаления оплаты: {e}")
                import traceback
                traceback.print_exc()

                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить оплату:\n{str(e)}',
                    'error'
                ).exec_()

    def adjust_payment_amount(self, payment_id):
        """Диалог корректировки суммы оплаты и отчетного месяца"""
        from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QComboBox, QFrame
        from PyQt5.QtCore import Qt, QDate
        from ui.custom_title_bar import CustomTitleBar

        # Получаем текущие данные оплаты
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

        # Конвертируем sqlite3.Row в dict для удобства работы
        payment = dict(payment_row)

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
                border: none;
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

        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(12)

        # Информация о платеже
        info_label = QLabel(f"<b>{payment['role']}</b><br>{payment['employee_name']}")
        info_label.setStyleSheet('font-size: 11px; color: #555; margin-bottom: 5px;')
        layout.addWidget(info_label)

        # Поле для ввода суммы
        amount_layout = QHBoxLayout()
        amount_label = QLabel('Сумма (₽):')
        amount_label.setStyleSheet('font-size: 11px; font-weight: bold;')
        amount_layout.addWidget(amount_label)

        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, 999999)
        amount_spin.setValue(current_amount)
        amount_spin.setDecimals(2)
        amount_spin.setStyleSheet("""
            QDoubleSpinBox {
                padding: 6px;
                font-size: 11px;
                border: none;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #ffd93c;
            }
        """)
        amount_layout.addWidget(amount_spin)
        layout.addLayout(amount_layout)

        # Выбор отчетного месяца
        month_layout = QHBoxLayout()
        month_label = QLabel('Отчетный месяц:')
        month_label.setStyleSheet('font-size: 11px; font-weight: bold;')
        month_layout.addWidget(month_label)

        month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_combo.addItems(months)

        # Устанавливаем текущий месяц из БД
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
                border: none;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #ffd93c;
            }
        """)
        month_layout.addWidget(month_combo)

        # Выбор года
        year_combo = CustomComboBox()
        current_year = QDate.currentDate().year()
        for year in range(current_year - 2, current_year + 3):
            year_combo.addItem(str(year))

        # Устанавливаем текущий год из БД
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
                border: none;
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
                background-color: #27AE60;
                color: white;
                padding: 7px 14px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #229954; }
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

        dialog.setFixedWidth(400)

        # Центрирование на экране
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - dialog.width()) // 2 + screen.left()
        y = (screen.height() - dialog.height()) // 3 + screen.top()
        dialog.move(x, y)

        # Автофокус на поле ввода + выделение текста
        amount_spin.setFocus()
        amount_spin.selectAll()

        dialog.exec_()

    def save_manual_amount(self, payment_id, amount, month, year, dialog):
        """Сохранение ручной суммы и отчетного месяца"""
        # Формируем отчетный месяц в формате YYYY-MM
        report_month = f"{year}-{month:02d}"

        # Обновляем сумму
        if self.api_client:
            try:
                self.api_client.update_payment_manual(payment_id, amount, report_month)
            except Exception as e:
                print(f"[WARN] API ошибка update_payment_manual: {e}")
                self.db.update_payment_manual(payment_id, amount)
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                UPDATE payments
                SET report_month = ?
                WHERE id = ?
                ''', (report_month, payment_id))
                conn.commit()
                self.db.close()
        else:
            self.db.update_payment_manual(payment_id, amount)
            # Обновляем отчетный месяц
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE payments
            SET report_month = ?
            WHERE id = ?
            ''', (report_month, payment_id))
            conn.commit()
            self.db.close()

        print(f"Оплата обновлена: ID={payment_id}, сумма={amount} ₽, месяц={report_month}")

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
        widget = QWidget()
        layout = QVBoxLayout()

        header = QLabel('Информация о проекте')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)

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

        widget.setLayout(layout)
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
        widget = QWidget()
        layout = QVBoxLayout()

        header = QLabel('Файлы авторского надзора')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)

        # Кнопки управления файлами
        buttons_layout = QHBoxLayout()

        upload_btn = IconLoader.create_icon_button('upload', 'Загрузить файл', 'Загрузить файл на Яндекс.Диск', icon_size=12)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980B9; }
        ''')
        upload_btn.clicked.connect(self.upload_supervision_file)
        buttons_layout.addWidget(upload_btn)

        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить', 'Обновить список файлов', icon_size=12)
        refresh_btn.setStyleSheet('''
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #219A52; }
        ''')
        refresh_btn.clicked.connect(self.refresh_files_list)
        buttons_layout.addWidget(refresh_btn)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        # Таблица файлов
        self.files_table = QTableWidget()
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

        layout.addWidget(self.files_table)

        # Загружаем список файлов
        self.load_supervision_files()

        widget.setLayout(layout)
        return widget

    def load_supervision_files(self):
        """Загрузка списка файлов надзора"""
        try:
            # Получаем contract_id из card_data
            contract_id = self.card_data.get('contract_id')
            if not contract_id:
                return

            files = []

            # Пробуем загрузить из API
            if self.api_client and self.api_client.is_online:
                try:
                    api_files = self.api_client.get_project_files(contract_id, stage='supervision')
                    if api_files:
                        files = [
                            {
                                'id': f.get('id'),
                                'file_name': f.get('file_name'),
                                'file_type': f.get('file_type'),
                                'yandex_path': f.get('yandex_path'),
                                'public_link': f.get('public_link'),
                                'created_at': f.get('created_at')
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
                cursor.execute('''
                    SELECT id, file_name, file_type, yandex_path, public_link, created_at
                    FROM project_files
                    WHERE contract_id = ? AND stage = 'supervision'
                    ORDER BY created_at DESC
                ''', (contract_id,))
                files = cursor.fetchall()
                self.db.close()

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

                # Кнопка открыть
                if file_data['public_link']:
                    open_btn = IconLoader.create_icon_button('link', '', 'Открыть файл', icon_size=12)
                    open_btn.setFixedSize(28, 28)
                    open_btn.clicked.connect(lambda checked, link=file_data['public_link']: self.open_file_link(link))
                    actions_layout.addWidget(open_btn)

                # Кнопка удалить
                delete_btn = IconLoader.create_icon_button('delete', '', 'Удалить файл', icon_size=12)
                delete_btn.setFixedSize(28, 28)
                delete_btn.setStyleSheet('QPushButton:hover { background-color: #FFEBEE; }')
                delete_btn.clicked.connect(lambda checked, fid=file_data['id'], fpath=file_data['yandex_path']: self.delete_supervision_file(fid, fpath))
                actions_layout.addWidget(delete_btn)

                actions_layout.addStretch()
                actions_widget.setLayout(actions_layout)
                self.files_table.setCellWidget(row, 3, actions_widget)

        except Exception as e:
            print(f"[ERROR] Ошибка загрузки файлов надзора: {e}")

    def upload_supervision_file(self):
        """Загрузка файла надзора на Яндекс.Диск"""
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

        # Диалог выбора файла
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'Выберите файл для загрузки',
            '',
            'Все файлы (*);;Изображения (*.png *.jpg *.jpeg);;PDF (*.pdf);;Документы (*.doc *.docx)'
        )

        if not file_path:
            return

        # Прогресс загрузки
        progress = QProgressDialog('Загрузка файла...', 'Отмена', 0, 100, self)
        progress.setWindowTitle('Загрузка на Яндекс.Диск')
        progress.setWindowModality(Qt.WindowModal)
        progress.show()

        try:
            # Создаем подпапку "Авторский надзор" если не существует
            supervision_folder = f"{contract_folder}/Авторский надзор"
            self.yandex_disk.create_folder(supervision_folder)

            progress.setValue(30)

            # Загружаем файл
            file_name = os.path.basename(file_path)
            yandex_path = f"{supervision_folder}/{file_name}"

            # Загрузка
            result = self.yandex_disk.upload_file(file_path, yandex_path)

            progress.setValue(70)

            if result:
                # Получаем публичную ссылку
                public_link = self.yandex_disk.get_public_link(yandex_path)

                progress.setValue(80)

                # Сохраняем в БД (локально)
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO project_files (contract_id, stage, file_type, yandex_path, public_link, file_name, created_at)
                    VALUES (?, 'supervision', 'Файл надзора', ?, ?, ?, datetime('now'))
                ''', (contract_id, yandex_path, public_link, file_name))
                local_file_id = cursor.lastrowid
                conn.commit()
                self.db.close()

                progress.setValue(90)

                # Синхронизируем с API
                if self.api_client and self.api_client.is_online:
                    try:
                        server_id = self.api_client.add_project_file(
                            contract_id=contract_id,
                            stage='supervision',
                            file_type='Файл надзора',
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

                progress.setValue(100)
                progress.close()

                CustomMessageBox(self, 'Успех', f'Файл "{file_name}" успешно загружен', 'success').exec_()

                # Добавляем запись в историю проекта
                if self.employee:
                    description = f"Добавлен файл надзора: {file_name}"
                    self._add_action_history('file_upload', description)

                # Обновляем список
                self.refresh_files_list()
            else:
                progress.close()
                CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл', 'error').exec_()

        except Exception as e:
            progress.close()
            CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки: {e}', 'error').exec_()
            print(f"[ERROR] Ошибка загрузки файла надзора: {e}")

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
            # Удаляем с Яндекс.Диска
            if self.yandex_disk and yandex_path:
                self.yandex_disk.delete_file(yandex_path)

            # Удаляем из локальной БД
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM project_files WHERE id = ?', (file_id,))
            conn.commit()
            self.db.close()

            # Синхронизируем удаление с API
            if self.api_client and self.api_client.is_online:
                try:
                    result = self.api_client.delete_project_file(file_id)
                    if result:
                        print(f"[API] Файл надзора удален с сервера, id={file_id}")
                    else:
                        print(f"[WARN] Файл удален локально, но не удален с сервера")
                except Exception as api_err:
                    print(f"[WARN] Ошибка удаления файла с сервера: {api_err}")

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
        """Обновление списка файлов"""
        self.load_supervision_files()

    def open_file_link(self, link):
        """Открытие ссылки на файл"""
        if link:
            from PyQt5.QtGui import QDesktopServices
            QDesktopServices.openUrl(QUrl(link))

    def load_data(self):
        """Загрузка данных (только для менеджеров)"""
        if self.employee['position'] == 'ДАН':
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
        self.deadline.dateChanged.connect(self.auto_save_field)
        self.tags.textChanged.connect(self.auto_save_field)

    def auto_save_field(self):
        """ИСПРАВЛЕНИЕ: Автоматическое сохранение при изменении полей"""
        if self._loading_data:
            return  # Не сохраняем во время загрузки данных

        try:
            # Сохраняем изменения
            updates = {
                'senior_manager_id': self.senior_manager.currentData(),
                'dan_id': self.dan.currentData(),
                'deadline': self.deadline.date().toString('yyyy-MM-dd'),
                'tags': self.tags.text().strip()
            }

            self.db.update_supervision_card(self.card_data['id'], updates)

            # Обновляем данные карточки
            self.card_data.update(updates)

            # ИСПРАВЛЕНИЕ: Не обновляем вкладки при автосохранении, чтобы не закрывать диалог
            # Обновление будет только при явном сохранении кнопкой "Сохранить"

            print("Данные автоматически сохранены")

        except Exception as e:
            print(f" Ошибка автосохранения: {e}")
            import traceback
            traceback.print_exc()

    def save_changes(self):
        """Сохранение изменений (только для менеджеров)"""
        if self.employee['position'] == 'ДАН':
            return

        updates = {
            'senior_manager_id': self.senior_manager.currentData(),
            'dan_id': self.dan.currentData(),
            'deadline': self.deadline.date().toString('yyyy-MM-dd'),
            'tags': self.tags.text().strip()
        }

        self.db.update_supervision_card(self.card_data['id'], updates)

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

    def on_employee_changed(self, combo_box, role_name):
        """НОВОЕ: Автоматическое создание/обновление выплаты при выборе сотрудника"""
        # Пропускаем, если данные загружаются
        if self._loading_data:
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            print("[WARN] Нет contract_id, пропускаем создание выплаты")
            return

        employee_id = combo_box.currentData()

        print(f"\n[EMPLOYEE_CHANGED] Роль: {role_name}, Employee ID: {employee_id}")

        # Сначала обновляем информацию о сотруднике в БД
        role_to_field = {
            'Старший менеджер проектов': 'senior_manager_id',
            'ДАН': 'dan_id'
        }

        field_name = role_to_field.get(role_name)
        if field_name:
            updates = {field_name: employee_id}
            self.db.update_supervision_card(self.card_data['id'], updates)
            print(f"Обновлено поле {field_name} в карточке авторского надзора")

        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            # ИСПРАВЛЕНИЕ: Удаляем только оплаты надзора для этой роли (с supervision_card_id)
            cursor.execute('''
            DELETE FROM payments
            WHERE supervision_card_id = ? AND role = ?
            ''', (self.card_data['id'], role_name))

            deleted_count = cursor.rowcount
            if deleted_count > 0:
                print(f"Удалено {deleted_count} старых оплат надзора для роли {role_name}")

            conn.commit()
            self.db.close()

            # ИСПРАВЛЕНИЕ: НЕ создаем оплату при назначении исполнителя
            # Оплаты будут создаваться автоматически при перемещении карточки на стадии
            if employee_id:
                print(f"[INFO] Оплаты будут создаваться автоматически при прохождении стадий надзора")
            else:
                print(f"[INFO] Сотрудник не назначен, выплаты удалены")

            # Обновляем вкладку оплат
            self.refresh_payments_tab()
            print(f"Вкладка оплат обновлена")

        except Exception as e:
            print(f"[ERROR] Ошибка при обновлении выплат: {e}")
            import traceback
            traceback.print_exc()

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
