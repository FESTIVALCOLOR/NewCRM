from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QTableWidget, QTableWidgetItem, QLabel, QComboBox,
                             QTabWidget, QHeaderView, QDialog, QFormLayout,
                             QDoubleSpinBox, QSpinBox, QTextEdit, QMessageBox, QGroupBox, QFrame,
                             QStyledItemDelegate, QStyleOptionViewItem, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, QModelIndex, QSize, QPropertyAnimation, QParallelAnimationGroup, QTimer
from PyQt5.QtGui import QColor, QPainter
from database.db_manager import DatabaseManager
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from ui.custom_combobox import CustomComboBox
from utils.icon_loader import IconLoader
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit, ICONS_PATH
from utils.offline_manager import OperationType


class CollapsibleBox(QWidget):
    """Сворачиваемый виджет для фильтров"""
    def __init__(self, title="Фильтры", parent=None):
        super().__init__(parent)

        self.toggle_button = QPushButton(title)
        self.toggle_button.setCheckable(True)
        self.toggle_button.setChecked(False)  # По умолчанию свернуто
        self.toggle_button.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 8px;
                border: none;
                background-color: #f5f5f5;
                font-weight: bold;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #D4E4BC;
            }
        """)
        self.toggle_button.clicked.connect(self.on_toggle)

        self.content_area = QWidget()
        self.content_area.setMaximumHeight(0)
        self.content_area.setMinimumHeight(0)
        self.content_area.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        lay = QVBoxLayout(self)
        lay.setSpacing(0)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.addWidget(self.toggle_button)
        lay.addWidget(self.content_area)

    def on_toggle(self):
        """Обработка сворачивания/разворачивания"""
        checked = self.toggle_button.isChecked()
        if checked:
            self.toggle_button.setText("▼ " + self.toggle_button.text().replace("▶ ", "").replace("▼ ", ""))
            self.content_area.setMaximumHeight(16777215)  # Максимальная высота
        else:
            self.toggle_button.setText("▶ " + self.toggle_button.text().replace("▶ ", "").replace("▼ ", ""))
            self.content_area.setMaximumHeight(0)

    def setContentLayout(self, layout):
        """Установка содержимого"""
        old_layout = self.content_area.layout()
        if old_layout:
            QWidget().setLayout(old_layout)
        self.content_area.setLayout(layout)
        # Устанавливаем начальный текст со стрелкой
        self.toggle_button.setText("▶ " + self.toggle_button.text().replace("▶ ", "").replace("▼ ", ""))


class PaymentStatusDelegate(QStyledItemDelegate):
    """Делегат для отрисовки цвета фона строк в зависимости от статуса оплаты"""

    def paint(self, painter, option, index):
        # Получаем данные о статусе из UserRole
        status = index.data(Qt.UserRole)

        if status == 'to_pay':
            option.palette.setColor(option.palette.Base, QColor('#FFF3CD'))
            option.palette.setColor(option.palette.AlternateBase, QColor('#FFF3CD'))
        elif status == 'paid':
            option.palette.setColor(option.palette.Base, QColor('#D4EDDA'))
            option.palette.setColor(option.palette.AlternateBase, QColor('#D4EDDA'))

        # Вызываем стандартную отрисовку
        super().paint(painter, option, index)

class SalariesTab(QWidget):
    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.db = DatabaseManager()
        # Получаем offline_manager от родителя (main_window)
        self.offline_manager = getattr(parent, 'offline_manager', None) if parent else None
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Заголовок + Кнопка тарифов
        header_layout = QHBoxLayout()
        
        header = QLabel(' Управление зарплатами ')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #333333; padding: 5px;')
        header_layout.addWidget(header)
        
        header_layout.addStretch()

        # ========== КНОПКА ТАРИФОВ (ТОЛЬКО ДЛЯ РУКОВОДИТЕЛЯ) ==========
        if self.employee['position'] == 'Руководитель студии':
            try:
                from ui.rates_dialog import RatesDialog

                rates_btn = QPushButton('Тарифы')
                rates_btn.setIcon(IconLoader.load('settings', 'Тарифы'))
                rates_btn.setIconSize(QSize(12, 12))
                rates_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        padding: 2px 8px;
                        font-size: 11px;
                        border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #F57C00; }
                """)
                rates_btn.clicked.connect(lambda: RatesDialog(self, api_client=self.api_client).exec_())
                header_layout.addWidget(rates_btn)

            except Exception as e:
                print(f" Не удалось создать кнопку тарифов: {e}")
        # =============================================================
        
        layout.addLayout(header_layout)
               
        # Вкладки
        self.tabs = QTabWidget()
        
        # Все выплаты
        self.all_payments_tab = self.create_all_payments_tab()
        self.tabs.addTab(self.all_payments_tab, ' Все выплаты ')
        
        # Индивидуальные проекты
        self.individual_tab = self.create_payment_type_tab('Индивидуальные проекты')
        self.tabs.addTab(self.individual_tab, '  Индивидуальные проекты  ')
        
        # Шаблонные проекты
        self.template_tab = self.create_payment_type_tab('Шаблонные проекты')
        self.tabs.addTab(self.template_tab, ' Шаблонные проекты ')
        
        # Оклады
        self.salary_tab = self.create_payment_type_tab('Оклады')
        self.tabs.addTab(self.salary_tab, ' Оклады ')
        
        # Авторский надзор
        self.supervision_tab = self.create_payment_type_tab('Авторский надзор')
        self.tabs.addTab(self.supervision_tab, ' Авторский надзор ')
        
        layout.addWidget(self.tabs)

        self.setLayout(layout)
        # ОПТИМИЗАЦИЯ: Отложенная загрузка данных для ускорения запуска
        QTimer.singleShot(0, self.load_all_payments)
    
    def create_all_payments_tab(self):
        """Вкладка всех выплат"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Сворачиваемые фильтры
        collapsible = CollapsibleBox("Фильтры")
        filters_main_layout = QVBoxLayout()

        # Первая строка: период
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel('Период:     '))

        self.period_filter = CustomComboBox()
        self.period_filter.addItems(['Месяц', 'Квартал', 'Год', 'Все'])
        self.period_filter.setCurrentIndex(0)
        self.period_filter.currentTextChanged.connect(self.on_period_filter_changed)
        row1_layout.addWidget(self.period_filter)

        self.year_filter = CustomComboBox()
        for year in range(2020, 2041):
            self.year_filter.addItem(str(year))
        self.year_filter.setCurrentText(str(QDate.currentDate().year()))
        self.year_filter.currentTextChanged.connect(self.apply_all_payments_filters)
        row1_layout.addWidget(self.year_filter)

        self.quarter_filter = CustomComboBox()
        self.quarter_filter.addItems(['Q1', 'Q2', 'Q3', 'Q4'])
        self.quarter_filter.setCurrentIndex((QDate.currentDate().month() - 1) // 3)
        self.quarter_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        self.quarter_filter.hide()
        row1_layout.addWidget(self.quarter_filter)

        self.month_filter = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        self.month_filter.addItems(months)
        self.month_filter.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row1_layout.addWidget(self.month_filter)

        row1_layout.addStretch()
        filters_main_layout.addLayout(row1_layout)

        # Вторая строка: адрес, исполнитель, должность
        row2_layout = QHBoxLayout()

        row2_layout.addWidget(QLabel('Адрес:       '))
        self.address_filter = CustomComboBox()
        self.address_filter.addItem('Все', None)
        self.address_filter.setMinimumWidth(200)
        self.address_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row2_layout.addWidget(self.address_filter)

        row2_layout.addWidget(QLabel('Исполнитель: '))
        self.employee_filter = CustomComboBox()
        self.employee_filter.addItem('Все', None)
        self.employee_filter.setMinimumWidth(150)
        self.employee_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row2_layout.addWidget(self.employee_filter)

        row2_layout.addWidget(QLabel('Должность:'))
        self.position_filter = CustomComboBox()
        self.position_filter.addItem('Все', None)
        self.position_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row2_layout.addWidget(self.position_filter)

        row2_layout.addStretch()
        filters_main_layout.addLayout(row2_layout)

        # Третья строка: тип агента, тип проекта, статус
        row3_layout = QHBoxLayout()

        row3_layout.addWidget(QLabel('Тип агента:'))
        self.agent_type_filter = CustomComboBox()
        self.agent_type_filter.addItem('Все', None)
        self.agent_type_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row3_layout.addWidget(self.agent_type_filter)

        row3_layout.addWidget(QLabel('Тип проекта:'))
        self.project_type_filter = CustomComboBox()
        self.project_type_filter.addItem('Все', None)
        self.project_type_filter.addItems(['Индивидуальный', 'Шаблонный', 'Авторский надзор'])
        self.project_type_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row3_layout.addWidget(self.project_type_filter)

        row3_layout.addWidget(QLabel('Статус:'))
        self.status_filter = CustomComboBox()
        self.status_filter.addItems(['Все', 'К оплате', 'Оплачено'])
        self.status_filter.currentIndexChanged.connect(self.apply_all_payments_filters)
        row3_layout.addWidget(self.status_filter)

        row3_layout.addStretch()
        filters_main_layout.addLayout(row3_layout)

        collapsible.setContentLayout(filters_main_layout)
        layout.addWidget(collapsible)
        
        # Таблица
        self.all_payments_table = QTableWidget()
        # ВАЖНО: НЕ устанавливаем background-color для QTableWidget,
        # чтобы цвета ячеек работали корректно
        self.all_payments_table.setStyleSheet("""
            QTableWidget {
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
        self.all_payments_table.setColumnCount(9)
        self.all_payments_table.setHorizontalHeaderLabels([
            'Тип проекта', 'Тип агента', 'Исполнитель', 'Должность', 'Сумма к выплате',
            'Тип выплаты', 'Адрес договора', 'Отчетный месяц', 'Действия'
        ])
        self.all_payments_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        # НЕ используем setAlternatingRowColors, чтобы можно было окрашивать строки вручную
        self.all_payments_table.setAlternatingRowColors(False)
        # Устанавливаем делегат для окраски строк
        self.all_payments_table.setItemDelegate(PaymentStatusDelegate())
        # Включаем сортировку по столбцам
        self.all_payments_table.setSortingEnabled(True)

        # Запрещаем изменение высоты строк
        self.all_payments_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.all_payments_table.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(self.all_payments_table)
        
        # Итого
        self.totals_label = QLabel()
        self.totals_label.setStyleSheet('''
            font-size: 14px; 
            font-weight: bold; 
            padding: 10px;
            background-color: #ffffff;
            border-radius: 5px;
        ''')
        layout.addWidget(self.totals_label)
        
        widget.setLayout(layout)
        return widget
    
    def create_payment_type_tab(self, payment_type):
        """Создание вкладки типа оплаты"""
        widget = QWidget()
        layout = QVBoxLayout()

        if payment_type == 'Оклады':
            # Кнопка добавления
            add_btn = QPushButton('+ Добавить выплату оклада')
            add_btn.clicked.connect(lambda: self.add_salary_payment())
            add_btn.setStyleSheet('padding: 8px 15px; font-weight: bold;')
            layout.addWidget(add_btn)

        # Фильтры
        filters_box = CollapsibleBox("Фильтры", widget)
        filters_layout = QVBoxLayout()

        # Первая строка: период
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel('Период:'))
        period_filter = CustomComboBox()
        period_filter.addItems(['Месяц', 'Квартал', 'Год', 'Все'])
        period_filter.setCurrentIndex(0)  # По умолчанию "Месяц"
        period_filter.setMinimumWidth(100)
        row1_layout.addWidget(period_filter)

        # Месяц
        month_filter = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_filter.addItems(months)
        current_month = QDate.currentDate().month()
        month_filter.setCurrentIndex(current_month - 1)
        month_filter.setMinimumWidth(120)
        row1_layout.addWidget(month_filter)

        # Год
        year_filter = QSpinBox()
        year_filter.setRange(2020, 2040)
        year_filter.setValue(QDate.currentDate().year())
        year_filter.setMinimumWidth(80)
        year_filter.setFixedHeight(42)
        year_filter.setStyleSheet(f"""
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
        row1_layout.addWidget(year_filter)

        # Квартал
        quarter_filter = CustomComboBox()
        quarter_filter.addItems(['Q1', 'Q2', 'Q3', 'Q4'])
        quarter_filter.setCurrentIndex((current_month - 1) // 3)
        quarter_filter.setMinimumWidth(80)
        quarter_filter.hide()  # Скрыт по умолчанию
        row1_layout.addWidget(quarter_filter)

        row1_layout.addStretch()
        filters_layout.addLayout(row1_layout)

        # Вторая строка: специфические фильтры в зависимости от типа
        row2_layout = QHBoxLayout()

        if payment_type != 'Оклады':
            # Для всех кроме окладов: адрес, исполнитель, должность
            row2_layout.addWidget(QLabel('Адрес:'))
            address_filter = CustomComboBox()
            address_filter.addItem('Все', None)
            address_filter.setMinimumWidth(150)
            row2_layout.addWidget(address_filter)

            row2_layout.addWidget(QLabel('Исполнитель:'))
            employee_filter = CustomComboBox()
            employee_filter.addItem('Все', None)
            employee_filter.setMinimumWidth(150)
            row2_layout.addWidget(employee_filter)

            row2_layout.addWidget(QLabel('Должность:'))
            position_filter = CustomComboBox()
            position_filter.addItem('Все', None)
            position_filter.setMinimumWidth(120)
            row2_layout.addWidget(position_filter)
        else:
            # Для окладов: только исполнитель и тип проекта
            row2_layout.addWidget(QLabel('Исполнитель:'))
            employee_filter = CustomComboBox()
            employee_filter.addItem('Все', None)
            employee_filter.setMinimumWidth(150)
            row2_layout.addWidget(employee_filter)

            row2_layout.addWidget(QLabel('Тип проекта:'))
            project_type_filter = CustomComboBox()
            project_type_filter.addItem('Все', None)
            project_type_filter.addItems(['Индивидуальный', 'Шаблонный', 'Авторский надзор'])
            project_type_filter.setMinimumWidth(150)
            row2_layout.addWidget(project_type_filter)

        row2_layout.addStretch()
        filters_layout.addLayout(row2_layout)

        # Третья строка: дополнительные фильтры для не-окладов
        if payment_type != 'Оклады':
            row3_layout = QHBoxLayout()

            row3_layout.addWidget(QLabel('Тип агента:'))
            agent_type_filter = CustomComboBox()
            agent_type_filter.addItem('Все', None)
            agent_type_filter.setMinimumWidth(120)
            row3_layout.addWidget(agent_type_filter)

            row3_layout.addWidget(QLabel('Статус оплаты:'))
            status_filter = CustomComboBox()
            status_filter.addItem('Все', None)
            status_filter.addItems(['К оплате', 'Оплачено', 'Частично оплачено'])
            status_filter.setMinimumWidth(150)
            row3_layout.addWidget(status_filter)

            row3_layout.addStretch()
            filters_layout.addLayout(row3_layout)

        # Устанавливаем содержимое фильтров
        filters_box.setContentLayout(filters_layout)
        layout.addWidget(filters_box)

        # Сохраняем ссылки на фильтры
        widget.period_filter = period_filter
        widget.month_filter = month_filter
        widget.year_filter = year_filter
        widget.quarter_filter = quarter_filter
        widget.employee_filter = employee_filter

        if payment_type != 'Оклады':
            widget.address_filter = address_filter
            widget.position_filter = position_filter
            widget.agent_type_filter = agent_type_filter
            widget.status_filter = status_filter
        else:
            widget.project_type_filter = project_type_filter

        # Обработчик изменения периода
        def on_period_changed(period):
            month_filter.setVisible(period == 'Месяц')
            year_filter.setVisible(period in ['Месяц', 'Год', 'Квартал'])
            quarter_filter.setVisible(period == 'Квартал')
            # Автоматически применяем фильтры при изменении периода
            self.apply_payment_type_filters(payment_type)

        period_filter.currentTextChanged.connect(on_period_changed)
        month_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
        year_filter.valueChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
        quarter_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
        employee_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))

        # Подключаем фильтры в зависимости от типа
        if payment_type != 'Оклады':
            address_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
            position_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
            agent_type_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
            status_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))
        else:
            project_type_filter.currentIndexChanged.connect(lambda: self.apply_payment_type_filters(payment_type))

        # Таблица
        table = QTableWidget()
        # ВАЖНО: НЕ устанавливаем background-color для QTableWidget,
        # чтобы цвета ячеек работали корректно
        table.setStyleSheet("""
            QTableWidget {
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
        table.setObjectName(f'table_{payment_type}')
        # НЕ используем setAlternatingRowColors, чтобы можно было окрашивать строки вручную
        table.setAlternatingRowColors(False)
        # Устанавливаем делегат для окраски строк
        table.setItemDelegate(PaymentStatusDelegate())

        # Настройка колонок
        if payment_type == 'Индивидуальные проекты':
            table.setColumnCount(12)
            table.setHorizontalHeaderLabels([
                '№', 'Адрес', 'Площадь', 'Город', 'Тип агента',
                'Стадия', 'Исполнитель', 'Должность', 'Сумма (₽)',
                'Тип выплаты', 'Отчетный месяц', 'Действия'
            ])
            # Адаптивная ширина столбцов
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # №
            header.setSectionResizeMode(1, QHeaderView.Stretch)           # Адрес - растягивается
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Площадь
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Город
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Тип агента
            header.setSectionResizeMode(5, QHeaderView.Stretch)           # Стадия - растягивается
            header.setSectionResizeMode(6, QHeaderView.Stretch)           # Исполнитель - растягивается
            header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Должность
            header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Сумма
            header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Тип выплаты
            header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # Отчетный месяц
            header.setSectionResizeMode(11, QHeaderView.Fixed)            # Действия
            table.setColumnWidth(11, 150)  # Фиксированная ширина для кнопок действий
        
        elif payment_type == 'Шаблонные проекты':
            table.setColumnCount(12)
            table.setHorizontalHeaderLabels([
                '№', 'Адрес', 'Площадь', 'Город', 'Тип агента',
                'Стадия', 'Исполнитель', 'Должность', 'Сумма (₽)',
                'Тип выплаты', 'Отчетный месяц', 'Действия'
            ])
            # Адаптивная ширина столбцов
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # №
            header.setSectionResizeMode(1, QHeaderView.Stretch)           # Адрес
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Площадь
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Город
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Тип агента
            header.setSectionResizeMode(5, QHeaderView.Stretch)           # Стадия
            header.setSectionResizeMode(6, QHeaderView.Stretch)           # Исполнитель
            header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Должность
            header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Сумма
            header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Тип выплаты
            header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # Отчетный месяц
            header.setSectionResizeMode(11, QHeaderView.Fixed)            # Действия
            table.setColumnWidth(11, 150)

        elif payment_type == 'Авторский надзор':
            table.setColumnCount(12)
            table.setHorizontalHeaderLabels([
                '№', 'Адрес', 'Площадь', 'Город', 'Тип агента',
                'Стадия', 'Исполнитель', 'Должность', 'Сумма (₽)',
                'Тип выплаты', 'Отчетный месяц', 'Действия'
            ])
            # Адаптивная ширина столбцов
            header = table.horizontalHeader()
            header.setSectionResizeMode(QHeaderView.Interactive)
            header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # №
            header.setSectionResizeMode(1, QHeaderView.Stretch)           # Адрес
            header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Площадь
            header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Город
            header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Тип агента
            header.setSectionResizeMode(5, QHeaderView.Stretch)           # Стадия
            header.setSectionResizeMode(6, QHeaderView.Stretch)           # Исполнитель
            header.setSectionResizeMode(7, QHeaderView.ResizeToContents)  # Должность
            header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Сумма
            header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Тип выплаты
            header.setSectionResizeMode(10, QHeaderView.ResizeToContents) # Отчетный месяц
            header.setSectionResizeMode(11, QHeaderView.Fixed)            # Действия
            table.setColumnWidth(11, 150)
        
        elif payment_type == 'Оклады':
            table.setColumnCount(5)
            table.setHorizontalHeaderLabels([
                'Исполнитель', 'Тип проекта', 'Сумма оклада', 'Отчетный месяц', 'Действия'
            ])
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        else:
            table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        table.setSelectionBehavior(QTableWidget.SelectRows)
        # Включаем сортировку по столбцам
        table.setSortingEnabled(True)

        # Запрещаем изменение высоты строк
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.verticalHeader().setDefaultSectionSize(36)

        layout.addWidget(table)

        # Метка для итогов
        totals_label = QLabel()
        totals_label.setObjectName(f'totals_{payment_type}')
        totals_label.setStyleSheet('''
            font-size: 14px;
            font-weight: bold;
            padding: 10px;
            background-color: #ffffff;
            border-radius: 5px;
        ''')
        layout.addWidget(totals_label)

        widget.setLayout(layout)
        return widget
    
    def create_payment_actions(self, payment, payment_type):
        """Кнопки действий для выплаты"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(5)
        
        # Кнопка "Оплачено" (иконка галочки)
        paid_btn = QPushButton()
        paid_btn.setIcon(IconLoader.load('check-active'))
        paid_btn.setIconSize(QSize(16, 16))
        if payment.get('is_paid'):
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 7px 12px;
                    border-radius: 4px;
                    font-size: 10px;
                }
            """)
            paid_btn.setEnabled(False)
            paid_btn.setToolTip('Оплачено')
        else:
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95A5A6;
                    color: white;
                    padding: 7px 12px;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #7F8C8D; }
            """)
            paid_btn.setToolTip('Отметить как оплачено')
            paid_btn.clicked.connect(lambda: self.mark_as_paid(payment['id']))
        
        layout.addWidget(paid_btn)
        
        widget.setLayout(layout)
        return widget

    def create_all_payments_actions(self, payment, is_salary, table, row):
        """Создание виджета с кнопками действий для таблицы 'Все выплаты'"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(5)

        current_status = payment.get('payment_status')

        # Кнопка "К оплате" (иконка денег)
        to_pay_btn = QPushButton()
        to_pay_btn.setIcon(IconLoader.load('tag'))
        to_pay_btn.setIconSize(QSize(14, 14))
        if current_status == 'to_pay':
            to_pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F39C12;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #E67E22; }
            """)
        else:
            to_pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #333;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    border: 1px solid #DDD;
                }
                QPushButton:hover { background-color: #E8E8E8; }
            """)
        to_pay_btn.setToolTip('Отметить к оплате')
        to_pay_btn.clicked.connect(lambda: self.set_payment_status(payment, 'to_pay', table, row, is_salary))
        layout.addWidget(to_pay_btn)

        # Кнопка "Оплачено" (иконка галочки)
        paid_btn = QPushButton()
        paid_btn.setIcon(IconLoader.load('money'))
        paid_btn.setIconSize(QSize(14, 14))
        if current_status == 'paid':
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #229954; }
            """)
        else:
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F5F5F5;
                    color: #333;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    border: 1px solid #DDD;
                }
                QPushButton:hover { background-color: #E8E8E8; }
            """)
        paid_btn.setToolTip('Отметить как оплачено')
        paid_btn.clicked.connect(lambda: self.set_payment_status(payment, 'paid', table, row, is_salary))
        layout.addWidget(paid_btn)

        # Кнопка удаления (только для руководителей)
        if self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов']:
            delete_btn = QPushButton()
            delete_btn.setIcon(IconLoader.load('delete2'))
            delete_btn.setIconSize(QSize(14, 14))
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #C0392B; }
            """)
            delete_btn.setToolTip('Удалить оплату')
            delete_btn.clicked.connect(
                lambda: self.delete_payment_universal(payment['id'], payment['source'], payment['position'], payment['employee_name'])
            )
            layout.addWidget(delete_btn)

        widget.setLayout(layout)
        return widget

    def create_crm_payment_actions(self, payment, payment_type, table, row):
        """Кнопки действий для выплат CRM"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(3)

        # Кнопка "К оплате" (иконка денег)
        to_pay_btn = QPushButton()
        to_pay_btn.setIcon(IconLoader.load('tag'))
        to_pay_btn.setIconSize(QSize(14, 14))
        current_status = payment.get('payment_status')
        if current_status == 'to_pay':
            to_pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F39C12;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
        else:
            to_pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ECF0F1;
                    color: #7F8C8D;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #F39C12; color: white; }
            """)
        to_pay_btn.setToolTip('Отметить к оплате')
        to_pay_btn.clicked.connect(
            lambda: self.set_payment_status(payment, 'to_pay', table, row)
        )
        layout.addWidget(to_pay_btn)

        # Кнопка "Оплачено" (иконка галочки)
        paid_btn = QPushButton()
        paid_btn.setIcon(IconLoader.load('money'))
        paid_btn.setIconSize(QSize(14, 14))
        if current_status == 'paid':
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
        else:
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ECF0F1;
                    color: #7F8C8D;
                    padding: 6px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #27AE60; color: white; }
            """)
        paid_btn.setToolTip('Отметить как оплачено')
        paid_btn.clicked.connect(
            lambda: self.set_payment_status(payment, 'paid', table, row)
        )
        layout.addWidget(paid_btn)

        # Кнопка "Изменить"
        edit_btn = QPushButton()
        edit_btn.setIcon(IconLoader.load('edit2'))
        edit_btn.setIconSize(QSize(14, 14))
        edit_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        edit_btn.setToolTip('Изменить выплату')
        edit_btn.clicked.connect(
            lambda: self.edit_crm_payment(payment, payment_type)
        )
        layout.addWidget(edit_btn)

        # Кнопка "Удалить"
        delete_btn = QPushButton()
        delete_btn.setIcon(IconLoader.load('delete2'))
        delete_btn.setIconSize(QSize(14, 14))
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        delete_btn.setToolTip('Удалить выплату')
        delete_btn.clicked.connect(
            lambda: self.delete_crm_payment(payment, payment_type)
        )
        layout.addWidget(delete_btn)

        widget.setLayout(layout)
        return widget

    def edit_crm_payment(self, payment, payment_type):
        """Редактирование выплаты CRM"""
        try:
            dialog = EditPaymentDialog(self, payment, api_client=self.api_client)
            if dialog.exec_() == QDialog.Accepted:
                # Обновляем данные выплаты
                payment_data = dialog.get_payment_data()

                # ИСПРАВЛЕНО: Используем API если доступен
                if self.api_client and self.api_client.is_online:
                    try:
                        self.api_client.update_payment(payment['id'], {
                            'final_amount': payment_data['amount'],
                            'payment_type': payment_data['payment_type'],
                            'report_month': payment_data['report_month']
                        })
                        print(f"[API] Выплата обновлена: ID={payment['id']}")
                    except Exception as e:
                        print(f"[WARN] Ошибка API обновления: {e}, fallback на локальную БД")
                        self._update_payment_locally(payment['id'], payment_data)
                elif self.api_client:
                    # Offline режим
                    self._update_payment_locally(payment['id'], payment_data)
                    if self.offline_manager:
                        from utils.offline_manager import OperationType
                        self.offline_manager.queue_operation(
                            OperationType.UPDATE, 'payment', payment['id'], {
                                'final_amount': payment_data['amount'],
                                'payment_type': payment_data['payment_type'],
                                'report_month': payment_data['report_month']
                            }
                        )
                    CustomMessageBox(self, 'Offline режим',
                        'Выплата обновлена локально.\nИзменения будут синхронизированы при восстановлении подключения.', 'info').exec_()
                else:
                    # Локальный режим без API
                    self._update_payment_locally(payment['id'], payment_data)

                CustomMessageBox(
                    self,
                    'Успех',
                    'Выплата успешно обновлена',
                    'success'
                ).exec_()

                # Обновляем таблицы
                self.load_all_payments()

        except Exception as e:
            print(f" Ошибка редактирования выплаты: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(
                self,
                'Ошибка',
                f'Не удалось обновить выплату:\n{str(e)}',
                'error'
            ).exec_()

    def _update_payment_locally(self, payment_id: int, payment_data: dict):
        """Обновление платежа в локальной БД"""
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('''
        UPDATE payments
        SET final_amount = ?,
            payment_type = ?,
            report_month = ?
        WHERE id = ?
        ''', (
            payment_data['amount'],
            payment_data['payment_type'],
            payment_data['report_month'],
            payment_id
        ))
        conn.commit()
        self.db.close()

    def delete_crm_payment(self, payment, payment_type):
        """Удаление выплаты CRM - удаляет из payments и обновляет CRM"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            f'Вы уверены, что хотите удалить выплату?\n\n'
            f'Исполнитель: {payment.get("employee_name")}\n'
            f'Сумма: {payment.get("final_amount", 0):,.2f} ₽\n\n'
            f' Это действие нельзя отменить!'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                # Удаляем запись из базы данных
                conn = self.db.connect()
                cursor = conn.cursor()

                cursor.execute('DELETE FROM payments WHERE id = ?', (payment['id'],))

                conn.commit()
                self.db.close()

                print(f"Выплата удалена: {payment.get('employee_name')} (ID: {payment['id']})")

                # Показываем сообщение об успехе
                CustomMessageBox(
                    self,
                    'Успех',
                    f'Выплата успешно удалена',
                    'success'
                ).exec_()

                # Обновляем таблицы
                self.load_all_payments()

            except Exception as e:
                print(f" Ошибка удаления выплаты: {e}")
                import traceback
                traceback.print_exc()

                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить выплату:\n{str(e)}',
                    'error'
                ).exec_()

    def mark_as_paid(self, payment_id):
        """Отметка выплаты как оплаченной"""
        try:
            if self.api_client:
                try:
                    self.api_client.mark_payment_as_paid(payment_id, self.employee['id'])
                except Exception as e:
                    print(f"[WARN] Ошибка API отметки оплаты: {e}, fallback на локальную БД")
                    self.db.mark_payment_as_paid(payment_id, self.employee['id'])
            else:
                self.db.mark_payment_as_paid(payment_id, self.employee['id'])
            
            # Перезагружаем таблицу
            self.load_all_payments()
            
            # Подсвечиваем строку зеленым
            table = self.sender().parent().parent()  # Получаем таблицу
            for row in range(table.rowCount()):
                if table.cellWidget(row, table.columnCount() - 1):
                    # Проверяем ID выплаты
                    # (логика проверки)
                    for col in range(table.columnCount()):
                        item = table.item(row, col)
                        if item:
                            item.setBackground(QColor('#D5F4E6'))  # Бледно-зеленый
            
            CustomMessageBox(self, 'Успех', 'Выплата отмечена как оплаченная', 'success').exec_()
            
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось отметить: {e}', 'error').exec_()

    def delete_payment_universal(self, payment_id, source, role, employee_name):
        """Универсальное удаление записи об оплате (из payments или salaries)"""
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
                if self.api_client and self.api_client.is_online:
                    try:
                        # ИСПРАВЛЕНО: delete_payment принимает только payment_id
                        self.api_client.delete_payment(payment_id)
                        print(f"[API] Оплата удалена: {role} - {employee_name} (ID: {payment_id}, Source: {source})")
                    except Exception as e:
                        print(f"[WARN] Ошибка API удаления: {e}, fallback на локальную БД")
                        self._delete_payment_locally(payment_id, source)
                        self._queue_payment_delete(payment_id, source)
                elif self.api_client:
                    # Offline режим - удаляем локально и добавляем в очередь
                    self._delete_payment_locally(payment_id, source)
                    self._queue_payment_delete(payment_id, source)
                    CustomMessageBox(self, 'Offline режим',
                        'Оплата удалена локально.\nИзменения будут синхронизированы при восстановлении подключения.', 'info').exec_()
                else:
                    # Локальный режим без API
                    self._delete_payment_locally(payment_id, source)

                print(f"[OK] Оплата удалена: {role} - {employee_name} (ID: {payment_id}, Source: {source})")

                # Показываем сообщение об успехе
                CustomMessageBox(
                    self,
                    'Успех',
                    f'Оплата успешно удалена:\n{role} - {employee_name}',
                    'success'
                ).exec_()

                # Обновляем таблицы
                self.load_all_payments()

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

    def delete_payment(self, payment_id, role, employee_name):
        """Удаление записи об оплате (старый метод для обратной совместимости)"""
        self.delete_payment_universal(payment_id, 'CRM', role, employee_name)

    def _delete_payment_locally(self, payment_id: int, source: str):
        """Удаление платежа из локальной SQLite базы данных"""
        try:
            self.db.delete_payment(payment_id)
            print(f"[LOCAL] Платеж удален локально: ID={payment_id}, Source={source}")
        except Exception as e:
            print(f"[ERROR] Ошибка локального удаления платежа: {e}")
            raise

    def _queue_payment_delete(self, payment_id: int, source: str):
        """Добавление операции удаления платежа в очередь для синхронизации"""
        if self.offline_manager:
            self.offline_manager.queue_operation(
                OperationType.DELETE,
                'payment',
                payment_id,
                {'source': source}
            )
            print(f"[QUEUE] Удаление платежа добавлено в очередь: ID={payment_id}, Source={source}")

    def on_period_filter_changed(self):
        """Обработка изменения типа периода"""
        period = self.period_filter.currentText()
        self.year_filter.setVisible(period != 'Все')
        self.quarter_filter.setVisible(period == 'Квартал')
        self.month_filter.setVisible(period == 'Месяц')
        self.apply_all_payments_filters()

    def apply_all_payments_filters(self):
        """Применение всех фильтров для таблицы всех выплат"""
        self.load_all_payments()

    def load_all_payments(self):
        """Загрузка всех выплат с применением фильтров"""
        period = self.period_filter.currentText()
        year = int(self.year_filter.currentText())

        # Отключаем сортировку перед загрузкой данных
        self.all_payments_table.setSortingEnabled(False)

        # Получаем данные в зависимости от выбранного периода
        if period == 'Месяц':
            month = self.month_filter.currentIndex() + 1
            if self.api_client and self.api_client.is_online:
                try:
                    payments = self.api_client.get_all_payments(month, year)
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки выплат: {e}")
                    payments = self.db.get_all_payments(month, year)
            else:
                payments = self.db.get_all_payments(month, year)
        elif period == 'Квартал':
            quarter = self.quarter_filter.currentIndex() + 1
            # Получаем все выплаты за квартал
            all_payments = []
            for month in range((quarter - 1) * 3 + 1, quarter * 3 + 1):
                if self.api_client and self.api_client.is_online:
                    try:
                        all_payments.extend(self.api_client.get_all_payments(month, year))
                    except Exception as e:
                        print(f"[WARN] Ошибка API загрузки выплат: {e}")
                        all_payments.extend(self.db.get_all_payments(month, year))
                else:
                    all_payments.extend(self.db.get_all_payments(month, year))
            payments = all_payments
        elif period == 'Год':
            # Получаем все выплаты за год
            all_payments = []
            for month in range(1, 13):
                if self.api_client and self.api_client.is_online:
                    try:
                        all_payments.extend(self.api_client.get_all_payments(month, year))
                    except Exception as e:
                        print(f"[WARN] Ошибка API загрузки выплат: {e}")
                        all_payments.extend(self.db.get_all_payments(month, year))
                else:
                    all_payments.extend(self.db.get_all_payments(month, year))
            payments = all_payments
        else:  # 'Все'
            # Получаем все выплаты за все время
            all_payments = []
            for y in range(2020, 2031):
                for month in range(1, 13):
                    if self.api_client and self.api_client.is_online:
                        try:
                            all_payments.extend(self.api_client.get_all_payments(month, y))
                        except Exception as e:
                            print(f"[WARN] Ошибка API загрузки выплат: {e}")
                            all_payments.extend(self.db.get_all_payments(month, y))
                    else:
                        all_payments.extend(self.db.get_all_payments(month, y))
            payments = all_payments

        # Загружаем уникальные значения для фильтров
        addresses = sorted(set(p.get('address', '') for p in payments if p.get('address')))
        employees = sorted(set(p.get('employee_name', '') for p in payments if p.get('employee_name')))
        positions = sorted(set(p.get('position', '') for p in payments if p.get('position')))
        agent_types = sorted(set(p.get('payment_type', '') for p in payments if p.get('payment_type')))

        # Обновляем комбобоксы фильтров (сохраняя текущие выборы если возможно)
        current_address = self.address_filter.currentData()
        current_employee = self.employee_filter.currentData()
        current_position = self.position_filter.currentData()
        current_agent = self.agent_type_filter.currentData()

        # Блокируем сигналы чтобы избежать рекурсии
        self.address_filter.blockSignals(True)
        self.employee_filter.blockSignals(True)
        self.position_filter.blockSignals(True)
        self.agent_type_filter.blockSignals(True)

        self.address_filter.clear()
        self.address_filter.addItem('Все', None)
        for addr in addresses:
            self.address_filter.addItem(addr, addr)
        if current_address:
            index = self.address_filter.findData(current_address)
            if index >= 0:
                self.address_filter.setCurrentIndex(index)

        self.employee_filter.clear()
        self.employee_filter.addItem('Все', None)
        for emp in employees:
            self.employee_filter.addItem(emp, emp)
        if current_employee:
            index = self.employee_filter.findData(current_employee)
            if index >= 0:
                self.employee_filter.setCurrentIndex(index)

        self.position_filter.clear()
        self.position_filter.addItem('Все', None)
        for pos in positions:
            self.position_filter.addItem(pos, pos)
        if current_position:
            index = self.position_filter.findData(current_position)
            if index >= 0:
                self.position_filter.setCurrentIndex(index)

        self.agent_type_filter.clear()
        self.agent_type_filter.addItem('Все', None)
        for agent in agent_types:
            self.agent_type_filter.addItem(agent, agent)
        if current_agent:
            index = self.agent_type_filter.findData(current_agent)
            if index >= 0:
                self.agent_type_filter.setCurrentIndex(index)

        # Разблокируем сигналы
        self.address_filter.blockSignals(False)
        self.employee_filter.blockSignals(False)
        self.position_filter.blockSignals(False)
        self.agent_type_filter.blockSignals(False)

        # Применяем фильтры
        filtered_payments = []
        for payment in payments:
            # Фильтр по адресу
            if self.address_filter.currentData() and payment.get('address') != self.address_filter.currentData():
                continue
            # Фильтр по исполнителю
            if self.employee_filter.currentData() and payment.get('employee_name') != self.employee_filter.currentData():
                continue
            # Фильтр по должности
            if self.position_filter.currentData() and payment.get('position') != self.position_filter.currentData():
                continue
            # Фильтр по типу агента
            if self.agent_type_filter.currentData() and payment.get('payment_type') != self.agent_type_filter.currentData():
                continue
            # Фильтр по типу проекта
            if self.project_type_filter.currentText() != 'Все':
                project_type = payment.get('project_type', '')
                if self.project_type_filter.currentText() != project_type:
                    continue
            # Фильтр по статусу
            if self.status_filter.currentText() != 'Все':
                status = payment.get('payment_status', '')
                if self.status_filter.currentText() == 'К оплате' and status != 'to_pay':
                    continue
                if self.status_filter.currentText() == 'Оплачено' and status != 'paid':
                    continue

            filtered_payments.append(payment)

        payments = filtered_payments

        self.all_payments_table.setRowCount(len(payments))
        
        total_month = 0
        total_year = 0
        
        for row, payment in enumerate(payments):
            # Тип проекта
            project_type = payment.get('project_type', '-')
            if not project_type:
                project_type = '-'
            self.all_payments_table.setItem(row, 0, QTableWidgetItem(project_type))

            # Тип агента (из договора: Петрович, Фестиваль и т.д.)
            # payment_type в SQL запросе теперь содержит c.agent_type из договора
            agent_type = payment.get('payment_type', '-')
            if not agent_type:
                agent_type = '-'
            self.all_payments_table.setItem(row, 1, QTableWidgetItem(agent_type))

            # Исполнитель
            self.all_payments_table.setItem(row, 2, QTableWidgetItem(payment['employee_name']))

            # Должность
            self.all_payments_table.setItem(row, 3, QTableWidgetItem(payment['position']))

            # Сумма к выплате
            amount_item = QTableWidgetItem(f"{payment['amount']:,.2f} ₽")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.all_payments_table.setItem(row, 4, amount_item)

            # Тип выплаты
            payment_subtype = payment.get('payment_subtype')
            if payment['source'] == 'Оклад':
                payment_subtype = 'Оклад'
            elif not payment_subtype:
                payment_subtype = '-'
            self.all_payments_table.setItem(row, 5, QTableWidgetItem(payment_subtype))

            # Адрес договора
            self.all_payments_table.setItem(row, 6, QTableWidgetItem(payment.get('address', '-')))

            # Отчетный месяц - форматируем
            report_month = payment.get('report_month', 'Не установлен')
            if report_month and report_month != 'Не установлен':
                try:
                    from datetime import datetime
                    month_date = datetime.strptime(report_month, '%Y-%m')
                    months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
                    report_month = f"{months_ru[month_date.month - 1]} {month_date.year}"
                except:
                    pass
            self.all_payments_table.setItem(row, 7, QTableWidgetItem(report_month))

            # Кнопки действий (столбец 8)
            is_salary = (payment['source'] == 'Оклад')
            actions_widget = self.create_all_payments_actions(payment, is_salary, self.all_payments_table, row)
            self.all_payments_table.setCellWidget(row, 8, actions_widget)

            # Применяем цвет строки в зависимости от статуса
            status = payment.get('payment_status')
            self.apply_row_color(self.all_payments_table, row, status)

            total_month += payment['amount']

        # Получаем итого за год
        if self.api_client:
            try:
                year_payments = self.api_client.get_year_payments(year)
            except Exception as e:
                print(f"[WARN] Ошибка API загрузки годовых выплат: {e}")
                year_payments = self.db.get_year_payments(year)
        else:
            year_payments = self.db.get_year_payments(year)
        total_year = sum(p['amount'] for p in year_payments)
        
        self.totals_label.setText(
            f'Итого за месяц: {total_month:,.2f} ₽  |  '
            f'Итого за год: {total_year:,.2f} ₽'
        )

        # Включаем сортировку после загрузки данных
        self.all_payments_table.setSortingEnabled(True)

        # Загружаем данные по типам
        self.load_payment_type_data('Индивидуальные проекты')
        self.load_payment_type_data('Шаблонные проекты')
        self.load_payment_type_data('Оклады')
        self.load_payment_type_data('Авторский надзор')

    def _get_payments_by_type_from_db(self, payment_type, project_type_filter):
        """Получение выплат по типу из локальной БД"""
        conn = self.db.connect()
        cursor = conn.cursor()

        # Для Окладов загружаем только из salaries
        if payment_type == 'Оклады':
            cursor.execute('''
            SELECT s.id, s.contract_id, s.employee_id, s.payment_type, s.stage_name,
                   s.amount, s.report_month, s.created_at, s.project_type, s.payment_status,
                   e.full_name as employee_name, e.position,
                   c.contract_number, c.address, c.area, c.city, c.agent_type,
                   'Оклад' as source
            FROM salaries s
            JOIN employees e ON s.employee_id = e.id
            LEFT JOIN contracts c ON s.contract_id = c.id
            ORDER BY s.id DESC
            ''')
        # Для остальных типов - объединяем payments и salaries
        elif project_type_filter:
            # Для Авторского надзора используем supervision_cards + salaries
            if project_type_filter == 'Авторский надзор':
                cursor.execute('''
                SELECT p.id, p.contract_id, p.employee_id, p.role, p.stage_name,
                       p.final_amount, p.payment_type, p.report_month, p.payment_status,
                       e.full_name as employee_name, e.position,
                       c.contract_number, c.address, c.area, c.city, c.agent_type,
                       sc.column_name as card_stage,
                       'CRM Надзор' as source
                FROM payments p
                JOIN employees e ON p.employee_id = e.id
                LEFT JOIN supervision_cards sc ON p.supervision_card_id = sc.id
                LEFT JOIN contracts c ON sc.contract_id = c.id
                WHERE p.supervision_card_id IS NOT NULL

                UNION ALL

                SELECT s.id, s.contract_id, s.employee_id, s.payment_type as role, s.stage_name,
                       s.amount as final_amount, 'Оклад' as payment_type, s.report_month, s.payment_status,
                       e.full_name as employee_name, e.position,
                       c.contract_number, c.address, c.area, c.city, c.agent_type,
                       NULL as card_stage,
                       'Оклад' as source
                FROM salaries s
                JOIN employees e ON s.employee_id = e.id
                LEFT JOIN contracts c ON s.contract_id = c.id
                WHERE s.project_type = ?

                ORDER BY 1 DESC
                ''', (project_type_filter,))
            else:
                # Для индивидуальных и шаблонных используем crm_cards + salaries
                cursor.execute('''
                SELECT p.id, p.contract_id, p.employee_id, p.role, p.stage_name,
                       p.final_amount, p.payment_type, p.report_month, p.payment_status,
                       e.full_name as employee_name, e.position,
                       c.contract_number, c.address, c.area, c.city, c.agent_type,
                       cc.column_name as card_stage,
                       'CRM' as source
                FROM payments p
                JOIN employees e ON p.employee_id = e.id
                LEFT JOIN crm_cards cc ON p.crm_card_id = cc.id
                LEFT JOIN contracts c ON cc.contract_id = c.id
                WHERE c.project_type = ?

                UNION ALL

                SELECT s.id, s.contract_id, s.employee_id, s.payment_type as role, s.stage_name,
                       s.amount as final_amount, 'Оклад' as payment_type, s.report_month, s.payment_status,
                       e.full_name as employee_name, e.position,
                       c.contract_number, c.address, c.area, c.city, c.agent_type,
                       NULL as card_stage,
                       'Оклад' as source
                FROM salaries s
                JOIN employees e ON s.employee_id = e.id
                LEFT JOIN contracts c ON s.contract_id = c.id
                WHERE s.project_type = ?

                ORDER BY 1 DESC
                ''', (project_type_filter, project_type_filter))
        else:
            # Не должно сюда попасть
            cursor.execute('''
            SELECT p.*, e.full_name as employee_name, e.position,
                   'CRM' as source
            FROM payments p
            JOIN employees e ON p.employee_id = e.id
            WHERE p.contract_id IS NULL
            ORDER BY p.id DESC
            ''')

        data = [dict(row) for row in cursor.fetchall()]
        self.db.close()
        return data

    def load_payment_type_data(self, payment_type):
        """Загрузка данных для конкретного типа оплаты"""
        # Находим соответствующую таблицу
        if payment_type == 'Индивидуальные проекты':
            parent_widget = self.individual_tab
        elif payment_type == 'Шаблонные проекты':
            parent_widget = self.template_tab
        elif payment_type == 'Оклады':
            parent_widget = self.salary_tab
        else:
            parent_widget = self.supervision_tab

        table = parent_widget.findChild(QTableWidget, f'table_{payment_type}')

        if table:
            # Отключаем сортировку перед загрузкой данных
            table.setSortingEnabled(False)

            try:
                # Получаем выплаты по типу проекта
                if payment_type == 'Индивидуальные проекты':
                    project_type_filter = 'Индивидуальный'
                elif payment_type == 'Шаблонные проекты':
                    project_type_filter = 'Шаблонный'
                elif payment_type == 'Авторский надзор':
                    project_type_filter = 'Авторский надзор'
                else:
                    project_type_filter = None

                # Проверяем наличие API клиента
                if self.api_client:
                    try:
                        data = self.api_client.get_payments_by_type(payment_type, project_type_filter)
                    except Exception as e:
                        print(f"[WARN] Ошибка API загрузки выплат по типу: {e}, fallback на локальную БД")
                        data = self._get_payments_by_type_from_db(payment_type, project_type_filter)
                else:
                    data = self._get_payments_by_type_from_db(payment_type, project_type_filter)

                # Заполняем фильтры уникальными значениями
                addresses = set()
                employees = set()
                positions = set()
                agent_types = set()

                for item in data:
                    if payment_type != 'Оклады':
                        if item.get('address'):
                            addresses.add(item['address'])
                        if item.get('agent_type'):
                            agent_types.add(item['agent_type'])
                        if item.get('position') or item.get('role'):
                            positions.add(item.get('position') or item.get('role'))
                    if item.get('employee_name'):
                        employees.add(item['employee_name'])

                # Блокируем сигналы при обновлении фильтров
                parent_widget.employee_filter.blockSignals(True)

                # Обновляем комбобоксы
                parent_widget.employee_filter.clear()
                parent_widget.employee_filter.addItem('Все', None)
                for emp in sorted(employees):
                    parent_widget.employee_filter.addItem(emp, emp)

                if payment_type != 'Оклады':
                    parent_widget.address_filter.blockSignals(True)
                    parent_widget.position_filter.blockSignals(True)
                    parent_widget.agent_type_filter.blockSignals(True)

                    parent_widget.address_filter.clear()
                    parent_widget.address_filter.addItem('Все', None)
                    for addr in sorted(addresses):
                        parent_widget.address_filter.addItem(addr, addr)

                    parent_widget.position_filter.clear()
                    parent_widget.position_filter.addItem('Все', None)
                    for pos in sorted(positions):
                        parent_widget.position_filter.addItem(pos, pos)

                    parent_widget.agent_type_filter.clear()
                    parent_widget.agent_type_filter.addItem('Все', None)
                    for agent in sorted(agent_types):
                        parent_widget.agent_type_filter.addItem(agent, agent)

                    parent_widget.address_filter.blockSignals(False)
                    parent_widget.position_filter.blockSignals(False)
                    parent_widget.agent_type_filter.blockSignals(False)

                parent_widget.employee_filter.blockSignals(False)

                table.setRowCount(len(data))
                
                for row, item in enumerate(data):
                    col = 0
                    
                    # Заполнение в зависимости от типа
                    if payment_type == 'Оклады':
                        # Для окладов: Исполнитель, Тип проекта, Сумма оклада, Отчетный месяц, Действия
                        table.setItem(row, col, QTableWidgetItem(item['employee_name']))
                        col += 1
                        table.setItem(row, col, QTableWidgetItem(item.get('project_type', 'Индивидуальный')))
                        col += 1
                        amount_item = QTableWidgetItem(f"{item.get('amount', 0):,.2f} ₽")
                        amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        table.setItem(row, col, amount_item)
                        col += 1

                        # Отчетный месяц - форматируем
                        report_month = item.get('report_month', 'Не установлен')
                        if report_month and report_month != 'Не установлен':
                            try:
                                from datetime import datetime
                                month_date = datetime.strptime(report_month, '%Y-%m')
                                months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                            'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
                                report_month = f"{months_ru[month_date.month - 1]} {month_date.year}"
                            except:
                                pass
                        table.setItem(row, col, QTableWidgetItem(report_month))
                        col += 1

                        # Кнопки действий
                        actions_widget = self.create_salary_payment_actions(item, payment_type, table, row)
                        table.setCellWidget(row, col, actions_widget)

                        # Применяем цвет строки в зависимости от статуса
                        self.apply_row_color(table, row, item.get('payment_status'))

                        continue  # Переходим к следующей строке, не обрабатываем дальше

                    elif payment_type in ['Индивидуальные проекты', 'Шаблонные проекты', 'Авторский надзор']:
                        contract_item = QTableWidgetItem(item['contract_number'])
                        # Сохраняем статус оплаты в UserRole для фильтрации
                        contract_item.setData(Qt.UserRole, item.get('payment_status'))
                        table.setItem(row, col, contract_item)
                        col += 1
                        table.setItem(row, col, QTableWidgetItem(item['address']))
                        col += 1
                        table.setItem(row, col, QTableWidgetItem(str(item.get('area', ''))))
                        col += 1
                        table.setItem(row, col, QTableWidgetItem(item.get('city', '')))
                        col += 1
                        table.setItem(row, col, QTableWidgetItem(item.get('agent_type', '')))
                        col += 1
                        # Стадия - за какую стадию идет оплата (из payments.stage_name)
                        stage = item.get('stage_name')
                        if not stage or stage == 'None':
                            # Если стадия не указана - значит оплата за весь проект
                            stage = 'Весь проект'
                        table.setItem(row, col, QTableWidgetItem(stage))
                        col += 1

                    # Исполнитель и должность
                    table.setItem(row, col, QTableWidgetItem(item['employee_name']))
                    col += 1
                    table.setItem(row, col, QTableWidgetItem(item['role']))
                    col += 1

                    # Сумма (объединенная для всех типов проектов)
                    payment_type_value = item.get('payment_type', '')
                    amount_item = QTableWidgetItem(f"{item['final_amount']:,.2f} ₽")
                    amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)

                    # Цвет в зависимости от типа выплаты
                    if payment_type_value == 'Аванс':
                        amount_item.setForeground(QColor('#ffd93c'))  # Синий для аванса
                    elif payment_type_value == 'Доплата':
                        amount_item.setForeground(QColor('#E67E22'))  # Оранжевый для доплаты
                    elif payment_type_value == 'Полная оплата':
                        amount_item.setForeground(QColor('#27AE60'))  # Зеленый для полной оплаты

                    table.setItem(row, col, amount_item)
                    col += 1

                    # Тип выплаты
                    payment_type_display = payment_type_value if payment_type_value else 'Оклад'
                    table.setItem(row, col, QTableWidgetItem(payment_type_display))
                    col += 1

                    # Отчетный месяц - преобразуем формат
                    report_month = item.get('report_month', 'Не установлен')
                    if report_month != 'Не установлен':
                        try:
                            # Преобразуем из "2025-11" в "Ноябрь 2025"
                            from datetime import datetime
                            month_date = datetime.strptime(report_month, '%Y-%m')
                            months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
                            report_month = f"{months_ru[month_date.month - 1]} {month_date.year}"
                        except:
                            pass
                    table.setItem(row, col, QTableWidgetItem(report_month))
                    col += 1

                    # Кнопки действий
                    actions_widget = self.create_crm_payment_actions(item, payment_type, table, row)
                    table.setCellWidget(row, col, actions_widget)

                    # Применяем цвет строки в зависимости от статуса
                    self.apply_row_color(table, row, item.get('payment_status'))

                # Подсчитываем итоги
                from datetime import datetime
                current_month = self.month_filter.currentIndex() + 1
                current_year = int(self.year_filter.currentText())
                current_month_str = f'{current_year}-{current_month:02d}'

                total_month = 0
                total_year = 0

                for item in data:
                    # Определяем сумму в зависимости от типа
                    amount = item.get('final_amount') or item.get('amount', 0)

                    report_month = item.get('report_month', '')
                    if report_month:
                        # Подсчет за текущий месяц
                        if report_month.startswith(current_month_str):
                            total_month += amount

                        # Подсчет за весь год
                        if report_month.startswith(str(current_year)):
                            total_year += amount

                # Обновляем метку итогов
                totals_label = parent_widget.findChild(QLabel, f'totals_{payment_type}')
                if totals_label:
                    totals_label.setText(
                        f'Итого за месяц: {total_month:,.2f} ₽  |  '
                        f'Итого за год: {total_year:,.2f} ₽'
                    )

                # Включаем сортировку после загрузки данных
                table.setSortingEnabled(True)

            except Exception as e:
                print(f" Ошибка загрузки выплат: {e}")
                import traceback
                traceback.print_exc()
            # =========================================================

    def apply_payment_type_filters(self, payment_type):
        """Применение фильтров к вкладке типа оплаты"""
        # Получаем виджет вкладки
        if payment_type == 'Индивидуальные проекты':
            parent_widget = self.individual_tab
        elif payment_type == 'Шаблонные проекты':
            parent_widget = self.template_tab
        elif payment_type == 'Оклады':
            parent_widget = self.salary_tab
        else:
            parent_widget = self.supervision_tab

        # Получаем таблицу и фильтры
        table = parent_widget.findChild(QTableWidget, f'table_{payment_type}')
        if not table:
            return

        period = parent_widget.period_filter.currentText()
        month = parent_widget.month_filter.currentIndex() + 1
        year = parent_widget.year_filter.value()
        quarter = parent_widget.quarter_filter.currentIndex() + 1
        employee_filter = parent_widget.employee_filter.currentData()

        # Дополнительные фильтры в зависимости от типа
        if payment_type != 'Оклады':
            address_filter = parent_widget.address_filter.currentData()
            position_filter = parent_widget.position_filter.currentData()
            agent_type_filter = parent_widget.agent_type_filter.currentData()
            status_filter = parent_widget.status_filter.currentText()
        else:
            project_type_filter = parent_widget.project_type_filter.currentData()

        # Фильтруем строки таблицы
        for row in range(table.rowCount()):
            show_row = True

            # Фильтр по периоду (проверяем отчетный месяц)
            if period != 'Все':
                if payment_type == 'Оклады':
                    report_month_item = table.item(row, 3)  # Отчетный месяц
                else:
                    report_month_item = table.item(row, 10)  # Отчетный месяц

                if report_month_item:
                    report_month_text = report_month_item.text()
                    # Преобразуем "Ноябрь 2025" обратно в месяц и год
                    if report_month_text and report_month_text != 'Не установлен':
                        try:
                            months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                        'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
                            parts = report_month_text.split()
                            if len(parts) >= 2:
                                month_name = parts[0]
                                year_value = int(parts[1])
                                month_value = months_ru.index(month_name) + 1

                                if period == 'Месяц':
                                    if month_value != month or year_value != year:
                                        show_row = False
                                elif period == 'Квартал':
                                    row_quarter = (month_value - 1) // 3 + 1
                                    if row_quarter != quarter or year_value != year:
                                        show_row = False
                                elif period == 'Год':
                                    if year_value != year:
                                        show_row = False
                        except:
                            pass

            # Фильтр по исполнителю
            if employee_filter and show_row:
                if payment_type == 'Оклады':
                    employee_item = table.item(row, 0)
                else:
                    employee_item = table.item(row, 6)

                if employee_item and employee_item.text() != employee_filter:
                    show_row = False

            # Дополнительные фильтры для не-окладов
            if payment_type != 'Оклады' and show_row:
                # Фильтр по адресу
                if address_filter:
                    address_item = table.item(row, 1)
                    if address_item and address_filter not in address_item.text():
                        show_row = False

                # Фильтр по должности
                if position_filter and show_row:
                    position_item = table.item(row, 7)
                    if position_item and position_item.text() != position_filter:
                        show_row = False

                # Фильтр по типу агента
                if agent_type_filter and show_row:
                    agent_item = table.item(row, 4)
                    if agent_item and agent_item.text() != agent_type_filter:
                        show_row = False

                # Фильтр по статусу
                if status_filter and status_filter != 'Все' and show_row:
                    # Получаем статус из UserRole (установлен делегатом)
                    status_item = table.item(row, 0)
                    if status_item:
                        row_status = status_item.data(Qt.UserRole)
                        if row_status != status_filter:
                            show_row = False
            else:
                # Фильтр по типу проекта для окладов
                if payment_type == 'Оклады' and project_type_filter and show_row:
                    project_type_item = table.item(row, 1)
                    if project_type_item and project_type_item.text() != project_type_filter:
                        show_row = False

            table.setRowHidden(row, not show_row)

    def reset_payment_type_filters(self, payment_type):
        """Сброс фильтров вкладки типа оплаты"""
        # Получаем виджет вкладки
        if payment_type == 'Индивидуальные проекты':
            parent_widget = self.individual_tab
        elif payment_type == 'Шаблонные проекты':
            parent_widget = self.template_tab
        elif payment_type == 'Оклады':
            parent_widget = self.salary_tab
        else:
            parent_widget = self.supervision_tab

        # Сбрасываем все фильтры
        parent_widget.period_filter.setCurrentIndex(0)  # Месяц
        parent_widget.month_filter.setCurrentIndex(QDate.currentDate().month() - 1)
        parent_widget.year_filter.setValue(QDate.currentDate().year())
        parent_widget.employee_filter.setCurrentIndex(0)  # Все

        if payment_type != 'Оклады':
            parent_widget.address_filter.setCurrentIndex(0)
            parent_widget.position_filter.setCurrentIndex(0)
            parent_widget.agent_type_filter.setCurrentIndex(0)
            parent_widget.status_filter.setCurrentIndex(0)
        else:
            parent_widget.project_type_filter.setCurrentIndex(0)

        # Показываем все строки
        table = parent_widget.findChild(QTableWidget, f'table_{payment_type}')
        if table:
            for row in range(table.rowCount()):
                table.setRowHidden(row, False)

    def fill_individual_row(self, table, row, data):
        """Заполнение строки индивидуального проекта"""
        table.setItem(row, 0, QTableWidgetItem(data['contract_number']))
        table.setItem(row, 1, QTableWidgetItem(data['address']))
        table.setItem(row, 2, QTableWidgetItem(str(data['area'])))
        table.setItem(row, 3, QTableWidgetItem(data['city']))
        
        # Замер
        table.setItem(row, 4, QTableWidgetItem(
            f"{data.get('surveyor_name', '-')}\n{data.get('surveyor_amount', 0):,.0f} ₽"
        ))
        
        # Стадии
        table.setItem(row, 5, QTableWidgetItem(
            f"{data.get('stage1_executor', '-')}\n{data.get('stage1_amount', 0):,.0f} ₽"
        ))
        table.setItem(row, 6, QTableWidgetItem(
            f"{data.get('stage2_executor', '-')}\n{data.get('stage2_amount', 0):,.0f} ₽"
        ))
        table.setItem(row, 7, QTableWidgetItem(
            f"{data.get('stage3_executor', '-')}\n{data.get('stage3_amount', 0):,.0f} ₽"
        ))
        
        # Руководители
        table.setItem(row, 8, QTableWidgetItem(
            f"{data.get('senior_manager', '-')}\n{data.get('sm_amount', 0):,.0f} ₽"
        ))
        table.setItem(row, 9, QTableWidgetItem(
            f"{data.get('sdp', '-')}\n{data.get('sdp_amount', 0):,.0f} ₽"
        ))
        table.setItem(row, 10, QTableWidgetItem(
            f"{data.get('gap', '-')}\n{data.get('gap_amount', 0):,.0f} ₽"
        ))
    
    def fill_template_row(self, table, row, data):
        """Заполнение строки шаблонного проекта"""
        table.setItem(row, 0, QTableWidgetItem(data['contract_number']))
        table.setItem(row, 1, QTableWidgetItem(data['address']))
        table.setItem(row, 2, QTableWidgetItem(str(data['area'])))
        table.setItem(row, 3, QTableWidgetItem(data['city']))
        table.setItem(row, 4, QTableWidgetItem(
            f"{data.get('surveyor_name', '-')}\n{data.get('surveyor_amount', 0):,.0f} ₽"
        ))
        table.setItem(row, 5, QTableWidgetItem(
            f"{data.get('executor', '-')}\n{data.get('amount', 0):,.0f} ₽"
        ))
        table.setItem(row, 6, QTableWidgetItem(
            f"{data.get('gap', '-')}\n{data.get('gap_amount', 0):,.0f} ₽"
        ))
    
    def fill_salary_row(self, table, row, data):
        """Заполнение строки оклада"""
        table.setItem(row, 0, QTableWidgetItem(data['employee_name']))
        table.setItem(row, 1, QTableWidgetItem(f"{data['amount']:,.2f} ₽"))
        table.setItem(row, 2, QTableWidgetItem(data['report_month']))
    
    def fill_supervision_row(self, table, row, data):
        """Заполнение строки авторского надзора"""
        table.setItem(row, 0, QTableWidgetItem(data['contract_number']))
        table.setItem(row, 1, QTableWidgetItem(data['address']))
        table.setItem(row, 2, QTableWidgetItem(str(data['area'])))
        table.setItem(row, 3, QTableWidgetItem(data['city']))
        table.setItem(row, 4, QTableWidgetItem(data['executor_name']))
        table.setItem(row, 5, QTableWidgetItem(f"{data['amount']:,.2f} ₽"))
    
    def create_payment_actions(self, payment_data, payment_type):
        """Создание кнопок действий для выплаты"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        
        edit_btn = QPushButton('✏️')
        edit_btn.setMaximumWidth(35)
        edit_btn.clicked.connect(lambda: self.edit_payment(payment_data, payment_type))
        
        delete_btn = QPushButton('🗑️')
        delete_btn.setMaximumWidth(35)
        delete_btn.clicked.connect(lambda: self.delete_payment(payment_data['id']))
        
        layout.addWidget(edit_btn)
        layout.addWidget(delete_btn)
        
        widget.setLayout(layout)
        return widget
    
    def add_salary_payment(self):
        """Добавление выплаты оклада"""
        dialog = PaymentDialog(self, payment_type='Оклады', api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_all_payments()

    def add_payment(self, payment_type):
        """Добавление выплаты"""
        dialog = PaymentDialog(self, payment_type=payment_type, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_all_payments()
    
    def edit_payment(self, payment_data, payment_type):
        """Редактирование выплаты"""
        dialog = PaymentDialog(self, payment_data=payment_data, payment_type=payment_type, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.load_all_payments()
    
    def delete_payment(self, payment_id):
        """Удаление выплаты"""
        reply = QMessageBox.question(
            self,
            'Подтверждение',
            'Удалить эту выплату?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.api_client:
                try:
                    self.api_client.delete_payment(payment_id)
                except Exception as e:
                    print(f"[WARN] API ошибка delete_payment: {e}")
                    self.db.delete_payment(payment_id)
            else:
                self.db.delete_payment(payment_id)
            self.load_all_payments()

    def create_salary_payment_actions(self, payment, payment_type, table, row):
        """Кнопки действий для окладов с новым дизайном"""
        widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(3)

        # Кнопка "К оплате"
        to_pay_btn = QPushButton('К оплате')
        current_status = payment.get('payment_status')
        if current_status == 'to_pay':
            to_pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F39C12;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
        else:
            to_pay_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ECF0F1;
                    color: #7F8C8D;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #F39C12; color: white; }
            """)
        to_pay_btn.setToolTip('Отметить к оплате')
        to_pay_btn.clicked.connect(
            lambda: self.set_payment_status(payment, 'to_pay', table, row, is_salary=True)
        )
        layout.addWidget(to_pay_btn)

        # Кнопка "Оплачено"
        paid_btn = QPushButton('Оплачено')
        if current_status == 'paid':
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                }
            """)
        else:
            paid_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ECF0F1;
                    color: #7F8C8D;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #27AE60; color: white; }
            """)
        paid_btn.setToolTip('Отметить как оплачено')
        paid_btn.clicked.connect(
            lambda: self.set_payment_status(payment, 'paid', table, row, is_salary=True)
        )
        layout.addWidget(paid_btn)

        widget.setLayout(layout)
        return widget

    def set_payment_status(self, payment, status, table, row, is_salary=False):
        """Установка статуса оплаты с toggle логикой"""
        try:
            # Toggle логика: если статус уже установлен, то сбрасываем его
            current_status = payment.get('payment_status')
            if current_status == status:
                # Сбрасываем статус
                new_status = None
                print(f"[OK] Сброс статуса для ID={payment['id']}")
            else:
                # Устанавливаем новый статус
                new_status = status
                print(f"[OK] Установка статуса '{status}' для ID={payment['id']}")

            # ИСПРАВЛЕНО: Используем API если доступен
            if self.api_client and self.api_client.is_online:
                try:
                    if is_salary:
                        self.api_client.update_salary(payment['id'], {'payment_status': new_status})
                    else:
                        self.api_client.update_payment(payment['id'], {'payment_status': new_status})
                    print(f"[API] Статус обновлен: ID={payment['id']}, status={new_status}")
                except Exception as e:
                    print(f"[WARN] Ошибка API обновления статуса: {e}, fallback на локальную БД")
                    self._update_status_locally(payment['id'], new_status, is_salary)
            elif self.api_client:
                # Offline режим
                self._update_status_locally(payment['id'], new_status, is_salary)
                if self.offline_manager:
                    from utils.offline_manager import OperationType
                    entity_type = 'salary' if is_salary else 'payment'
                    self.offline_manager.queue_operation(
                        OperationType.UPDATE, entity_type, payment['id'],
                        {'payment_status': new_status}
                    )
            else:
                # Локальный режим без API
                self._update_status_locally(payment['id'], new_status, is_salary)

            # Обновляем все таблицы для синхронизации
            self.load_all_payments()
            self.load_payment_type_data('Оклады')
            self.load_payment_type_data('Индивидуальные проекты')
            self.load_payment_type_data('Шаблонные проекты')
            self.load_payment_type_data('Авторский надзор')

            # Синхронизируем с CRM если это payments
            if not is_salary:
                self.sync_status_with_crm(payment, new_status)

        except Exception as e:
            print(f"[ERROR] Ошибка установки статуса: {e}")
            import traceback
            traceback.print_exc()

    def _update_status_locally(self, payment_id: int, new_status, is_salary: bool):
        """Обновление статуса в локальной БД"""
        conn = self.db.connect()
        cursor = conn.cursor()
        table_name = 'salaries' if is_salary else 'payments'
        cursor.execute(f'''
        UPDATE {table_name}
        SET payment_status = ?
        WHERE id = ?
        ''', (new_status, payment_id))
        conn.commit()
        self.db.close()

    def apply_row_color(self, table, row, status):
        """Применение цвета к строке в зависимости от статуса"""
        if status == 'to_pay':
            color = QColor('#FFF3CD')  # Светло-желтый
        elif status == 'paid':
            color = QColor('#D4EDDA')  # Светло-зеленый
        else:
            color = QColor('#FFFFFF')  # Белый

        # КЛЮЧЕВОЕ РЕШЕНИЕ: Создаем QWidget для каждой обычной ячейки с фоном
        from PyQt5.QtWidgets import QLabel
        color_name = color.name()

        for col in range(table.columnCount()):
            existing_widget = table.cellWidget(row, col)

            if existing_widget and col == table.columnCount() - 1:
                # Последний столбец - это уже виджет с кнопками, просто меняем его фон
                existing_widget.setStyleSheet(f"background-color: {color_name};")
            else:
                # Для остальных столбцов создаем QLabel с текстом и фоном
                item = table.item(row, col)
                if item:
                    text = item.text()
                    alignment = item.textAlignment()
                else:
                    text = ""
                    alignment = int(Qt.AlignLeft | Qt.AlignVCenter)

                label = QLabel(text)
                label.setStyleSheet(f"background-color: {color_name}; padding: 5px;")
                label.setAlignment(Qt.Alignment(alignment))

                table.setCellWidget(row, col, label)

    def sync_status_with_crm(self, payment, status):
        """Синхронизация статуса с CRM"""
        # Синхронизация происходит автоматически через базу данных.
        # payment_status хранится в таблице payments, и CRM карточки
        # читают это поле при загрузке, поэтому явная синхронизация не требуется.
        # При следующем открытии CRM карточки статус будет отображаться корректно.
        pass


class PaymentDialog(QDialog):
    def __init__(self, parent, payment_data=None, payment_type=None, api_client=None):
        super().__init__(parent)
        self.payment_data = payment_data
        self.payment_type = payment_type
        self.db = DatabaseManager()
        self.api_client = api_client
        # Получаем offline_manager для работы в offline режиме
        self.offline_manager = getattr(parent, 'offline_manager', None)

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
        
        if payment_data:
            self.fill_data()
    
    def init_ui(self):
        title = f'{"Редактирование" if self.payment_data else "Добавление"} выплаты'
        
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
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        form_layout = QFormLayout()
        
        # Поля в зависимости от типа
        if self.payment_type == 'Оклады':
            # Исполнитель
            self.employee_combo = CustomComboBox()
            if self.api_client:
                try:
                    employees = self.api_client.get_employees()
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки сотрудников: {e}")
                    employees = self.db.get_all_employees()
            else:
                employees = self.db.get_all_employees()
            for emp in employees:
                self.employee_combo.addItem(emp['full_name'], emp['id'])
            form_layout.addRow('Исполнитель:', self.employee_combo)

            # Тип проекта
            self.project_type_combo = CustomComboBox()
            self.project_type_combo.addItems(['Индивидуальный', 'Шаблонный', 'Авторский надзор'])
            form_layout.addRow('Тип проекта:', self.project_type_combo)

            # Сумма
            self.amount = QDoubleSpinBox()
            self.amount.setMaximum(1000000)
            self.amount.setSuffix(' ₽')
            form_layout.addRow('Сумма оклада:', self.amount)

            # Месяц
            self.month_combo = CustomComboBox()
            months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                      'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
            self.month_combo.addItems(months)
            form_layout.addRow('Отчетный месяц:', self.month_combo)
        else:
            # Договор
            self.contract_combo = CustomComboBox()
            if self.api_client:
                try:
                    contracts = self.api_client.get_contracts()
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки договоров: {e}")
                    contracts = self.db.get_all_contracts()
            else:
                contracts = self.db.get_all_contracts()
            for contract in contracts:
                self.contract_combo.addItem(
                    f"{contract['contract_number']} - {contract['address']}",
                    contract['id']
                )
            form_layout.addRow('Договор:', self.contract_combo)

            # Исполнитель
            self.employee_combo = CustomComboBox()
            if self.api_client:
                try:
                    employees = self.api_client.get_employees()
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки сотрудников: {e}")
                    employees = self.db.get_all_employees()
            else:
                employees = self.db.get_all_employees()
            for emp in employees:
                self.employee_combo.addItem(emp['full_name'], emp['id'])
            form_layout.addRow('Исполнитель:', self.employee_combo)
            
            # Сумма
            self.amount = QDoubleSpinBox()
            self.amount.setMaximum(10000000)
            self.amount.setSuffix(' ₽')
            form_layout.addRow('Сумма:', self.amount)
            
            # Предоплата
            self.advance = QDoubleSpinBox()
            self.advance.setMaximum(10000000)
            self.advance.setSuffix(' ₽')
            form_layout.addRow('Предоплата:', self.advance)
        
        # Комментарий
        self.comments = QTextEdit()
        self.comments.setMaximumHeight(80)
        form_layout.addRow('Комментарий:', self.comments)
        
        layout.addLayout(form_layout)
        
        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self.save_payment)
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
        
        self.setMinimumWidth(600)
    
    def fill_data(self):
        """Заполнение данных"""
        # Реализация заполнения
        pass
    
    def save_payment(self):
        """Сохранение выплаты"""
        payment_data = {
            'payment_type': self.payment_type,
            'employee_id': self.employee_combo.currentData(),
            'amount': self.amount.value(),
            'comments': self.comments.toPlainText()
        }
        
        if self.payment_type != 'Оклады':
            payment_data['contract_id'] = self.contract_combo.currentData()
            payment_data['advance_payment'] = self.advance.value()
        else:
            month_index = self.month_combo.currentIndex() + 1
            payment_data['report_month'] = f"{QDate.currentDate().year()}-{month_index:02d}"
            payment_data['project_type'] = self.project_type_combo.currentText()
        
        if self.payment_data:
            if self.api_client:
                try:
                    self.api_client.update_salary(self.payment_data['id'], payment_data)
                except Exception as e:
                    print(f"[WARN] Ошибка API обновления оклада: {e}")
                    self.db.update_salary(self.payment_data['id'], payment_data)
            else:
                self.db.update_salary(self.payment_data['id'], payment_data)
        else:
            if self.api_client:
                try:
                    self.api_client.add_salary(payment_data)
                except Exception as e:
                    print(f"[WARN] Ошибка API добавления оклада: {e}")
                    self.db.add_salary(payment_data)
            else:
                self.db.add_salary(payment_data)
        
        # ========== ЗАМЕНИЛИ QMessageBox ==========
        CustomMessageBox(self, 'Успех', 'Выплата сохранена', 'success').exec_()
        self.accept()
    
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


class EditPaymentDialog(QDialog):
    """Диалог редактирования выплаты"""
    def __init__(self, parent, payment_data, api_client=None):
        super().__init__(parent)
        self.payment_data = payment_data
        self.api_client = api_client
        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle('Редактирование выплаты')
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        main_layout = QVBoxLayout()

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)

        # Контент
        content_widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(20)

        # Заголовок
        title = QLabel('Изменение выплаты')
        title.setStyleSheet('font-size: 18px; font-weight: bold; padding: 10px;')
        layout.addWidget(title)

        # Форма
        form_layout = QFormLayout()
        form_layout.setSpacing(15)

        # Исполнитель (только для отображения)
        self.employee_label = QLabel(self.payment_data.get('employee_name', '-'))
        form_layout.addRow('Исполнитель:', self.employee_label)

        # Тип выплаты
        self.payment_type_combo = CustomComboBox()
        self.payment_type_combo.addItems(['Аванс', 'Доплата', 'Полная оплата'])
        current_payment_type = self.payment_data.get('payment_type', 'Полная оплата')
        index = self.payment_type_combo.findText(current_payment_type)
        if index >= 0:
            self.payment_type_combo.setCurrentIndex(index)
        form_layout.addRow('Тип выплаты:', self.payment_type_combo)

        # Сумма
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 10000000)
        self.amount_spin.setValue(self.payment_data.get('final_amount', 0))
        self.amount_spin.setSuffix(' ₽')
        self.amount_spin.setStyleSheet('padding: 5px; font-size: 13px;')
        form_layout.addRow('Сумма:', self.amount_spin)

        # Отчетный месяц
        self.month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        self.month_combo.addItems(months)

        # Устанавливаем текущий месяц
        report_month = self.payment_data.get('report_month', '')
        if report_month:
            try:
                from datetime import datetime
                month_date = datetime.strptime(report_month, '%Y-%m')
                self.month_combo.setCurrentIndex(month_date.month - 1)
                self.year_value = month_date.year
            except:
                self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
                self.year_value = QDate.currentDate().year()
        else:
            self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
            self.year_value = QDate.currentDate().year()

        form_layout.addRow('Отчетный месяц:', self.month_combo)

        layout.addLayout(form_layout)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(36)
        save_btn.clicked.connect(self.accept)
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

    def get_payment_data(self):
        """Получение данных выплаты"""
        month = self.month_combo.currentIndex() + 1
        report_month = f"{self.year_value}-{month:02d}"

        return {
            'amount': self.amount_spin.value(),
            'payment_type': self.payment_type_combo.currentText(),
            'report_month': report_month
        }
