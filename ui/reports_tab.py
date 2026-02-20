# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QPushButton, QComboBox,
                             QMessageBox, QFileDialog, QTabWidget, QScrollArea,
                             QDialog, QFormLayout, QLineEdit)
from PyQt5.QtCore import Qt, QDate, QUrl, QTimer
from PyQt5.QtGui import QFont, QPixmap, QTextDocument, QTextCursor, QTextTableFormat, QTextCharFormat, QBrush, QColor, QTextBlockFormat, QTextImageFormat
from PyQt5.QtPrintSupport import QPrinter
from ui.custom_combobox import CustomComboBox
import os
from database.db_manager import DatabaseManager
from ui.chart_widget import FunnelBarChart, ExecutorLoadChart, ProjectTypePieChart
from utils.icon_loader import IconLoader
from utils.resource_path import resource_path
from utils.data_access import DataAccess
from datetime import datetime

# Опциональный импорт matplotlib
try:
    import matplotlib
    matplotlib.use('Qt5Agg')
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    print("[WARN] matplotlib не установлен. Графики в отчетах будут недоступны.")

class ReportsTab(QWidget):
    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.db = DatabaseManager()
        self.data_access = DataAccess(api_client=self.api_client, db=self.db)
        self._data_loaded = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)

        # Заголовок
        header_layout = QHBoxLayout()

        header = QLabel(' Отчеты и Статистика ')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #333333; padding: 5px;')
        header_layout.addWidget(header)
        header_layout.addStretch()

        export_all_btn = IconLoader.create_action_button(
            'export', 'Экспорт в PDF',
            bg_color='#E74C3C', hover_color='#C0392B', icon_color='#ffffff')
        export_all_btn.clicked.connect(self.export_full_report)
        header_layout.addWidget(export_all_btn)
        
        main_layout.addLayout(header_layout)
        
        # ОБЩИЕ ФИЛЬТРЫ
        filters_group = QGroupBox('Фильтры периода')
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

        filters_main_layout = QVBoxLayout()

        # Кнопка свернуть/развернуть
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 5)

        toggle_filters_btn = IconLoader.create_icon_button('arrow-down-circle', '', 'Развернуть фильтры', icon_size=16)
        toggle_filters_btn.setFixedSize(24, 24)
        toggle_filters_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #ffffff;
                border-radius: 12px;
            }
        """)
        header_row.addWidget(toggle_filters_btn)
        header_row.addStretch()
        filters_main_layout.addLayout(header_row)

        # Контейнер для фильтров
        filters_content = QWidget()
        filters_layout = QHBoxLayout(filters_content)
        filters_layout.setContentsMargins(0, 0, 0, 0)
        filters_layout.setSpacing(8)
        filters_content.hide()  # По умолчанию свернуто
        
        # Год
        filters_layout.addWidget(QLabel('Год:'))
        self.year_combo = CustomComboBox()
        for year in range(2020, 2041):
            self.year_combo.addItem(str(year))
        self.year_combo.setCurrentText(str(datetime.now().year))
        self.year_combo.currentTextChanged.connect(self.load_all_statistics)
        self.year_combo.setStyleSheet('padding: 8px;')
        self.year_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        filters_layout.addWidget(self.year_combo)
        
        # Квартал
        filters_layout.addWidget(QLabel('Квартал:'))
        self.quarter_combo = CustomComboBox()
        self.quarter_combo.addItems(['Все', 'Q1', 'Q2', 'Q3', 'Q4'])
        self.quarter_combo.currentTextChanged.connect(self.on_quarter_changed)
        self.quarter_combo.setStyleSheet('padding: 8px;')
        self.quarter_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        filters_layout.addWidget(self.quarter_combo)
        
        # Месяц
        filters_layout.addWidget(QLabel('Месяц:'))
        self.month_combo = CustomComboBox()
        months = ['Все', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        self.month_combo.addItems(months)
        self.month_combo.currentTextChanged.connect(self.on_month_changed)
        self.month_combo.setStyleSheet('padding: 8px;')
        self.month_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        filters_layout.addWidget(self.month_combo)
        
        # Тип агента
        filters_layout.addWidget(QLabel('Тип агента:'))
        self.agent_type_combo = CustomComboBox()
        self.load_agent_types()
        self.agent_type_combo.currentTextChanged.connect(self.load_all_statistics)
        self.agent_type_combo.setStyleSheet('padding: 8px;')
        self.agent_type_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        filters_layout.addWidget(self.agent_type_combo)
        
        # Город
        filters_layout.addWidget(QLabel('Город:'))
        self.city_combo = CustomComboBox()
        self.load_cities()
        self.city_combo.currentTextChanged.connect(self.load_all_statistics)
        self.city_combo.setStyleSheet('padding: 8px;')
        self.city_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        filters_layout.addWidget(self.city_combo)
        
        filters_layout.addStretch()

        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить все фильтры', icon_size=12)
        reset_btn.setStyleSheet("""
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
                background-color: #FFF3E0;
                border-color: #FF9800;
            }
        """)
        reset_btn.clicked.connect(self.reset_filters)
        filters_layout.addWidget(reset_btn)

        # Добавляем контейнер фильтров в основной layout
        filters_main_layout.addWidget(filters_content)

        # Обработчик сворачивания/разворачивания фильтров
        def toggle_filters_rep():
            is_visible = filters_content.isVisible()
            filters_content.setVisible(not is_visible)
            if is_visible:
                toggle_filters_btn.setIcon(IconLoader.load('arrow-down-circle'))
                toggle_filters_btn.setToolTip('Развернуть фильтры')
            else:
                toggle_filters_btn.setIcon(IconLoader.load('arrow-up-circle'))
                toggle_filters_btn.setToolTip('Свернуть фильтры')

        toggle_filters_btn.clicked.connect(toggle_filters_rep)

        filters_group.setLayout(filters_main_layout)
        main_layout.addWidget(filters_group)
        
        # ВКЛАДКИ
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                background: white;
            }
            QTabBar::tab {
                background-color: #F5F5F5;
                border: 1px solid #d9d9d9;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                padding: 10px 100px;
                margin-right: 2px;
                font-size: 13px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid white;
            }
            QTabBar::tab:hover {
                background-color: #ffffff;
            }
        """)
        
        # Вкладка 1: Индивидуальные проекты
        individual_tab = self.create_statistics_tab('Индивидуальный')
        self.tabs.addTab(individual_tab, '  Индивидуальные проекты  ')
        
        # Вкладка 2: Шаблонные проекты
        template_tab = self.create_statistics_tab('Шаблонный')
        self.tabs.addTab(template_tab, '   Шаблонные проекты   ')
        
        # Вкладка 3: Авторский надзор
        supervision_tab = self.create_supervision_statistics_tab()
        self.tabs.addTab(supervision_tab, '  Авторский надзор  ')

        # Вкладка 4: Аналитика (графики)
        analytics_tab = self._create_analytics_tab()
        self.tabs.addTab(analytics_tab, '  Аналитика  ')

        main_layout.addWidget(self.tabs, 1)

        self.setLayout(main_layout)
    
    def _create_analytics_tab(self):
        """Вкладка аналитики с графиками: воронка, нагрузка, типы проектов"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title = QLabel("Аналитика проектов")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #2C3E50;")
        layout.addWidget(title)

        # Ряд 1: Типы проектов + Воронка
        row1 = QHBoxLayout()
        row1.setSpacing(15)

        self.pie_chart = ProjectTypePieChart()
        self.pie_chart.setMinimumHeight(320)
        self.pie_chart.setStyleSheet("background: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 8px;")
        row1.addWidget(self.pie_chart)

        self.funnel_chart = FunnelBarChart()
        self.funnel_chart.setMinimumHeight(320)
        self.funnel_chart.setStyleSheet("background: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 8px;")
        row1.addWidget(self.funnel_chart)

        layout.addLayout(row1)

        # Ряд 2: Нагрузка исполнителей
        self.executor_chart = ExecutorLoadChart()
        self.executor_chart.setMinimumHeight(320)
        self.executor_chart.setStyleSheet("background: #FAFAFA; border: 1px solid #E0E0E0; border-radius: 8px;")
        layout.addWidget(self.executor_chart)

        layout.addStretch()

        content.setLayout(layout)
        scroll.setWidget(content)
        return scroll

    def _load_analytics_charts(self):
        """Загрузка данных для графиков аналитики"""
        try:
            # Типы проектов (из текущей статистики)
            contracts = self.data_access.get_all_contracts()

            individual = sum(1 for c in contracts if c.get('project_type') == 'Индивидуальный')
            template = sum(1 for c in contracts if c.get('project_type') == 'Шаблонный')
            supervision = sum(1 for c in contracts if c.get('supervision'))
            self.pie_chart.set_data(individual, template, supervision)

            # Воронка
            funnel_data = self.data_access.get_funnel_statistics()
            funnel = funnel_data.get("funnel", {})
            if funnel:
                self.funnel_chart.set_data(funnel)

            # Нагрузка исполнителей
            executors = self.data_access.get_executor_load()
            if executors:
                self.executor_chart.set_data(executors)

        except Exception as e:
            print(f"Ошибка загрузки графиков аналитики: {e}")

    def create_statistics_tab(self, project_type):
        """Создание вкладки статистики для типа проекта"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)

        clean_type = project_type.strip()

        # ТОЛЬКО ДИАГРАММЫ - карточки статистики показываются в дашборде main_window
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(15)

        cities_chart = self.create_chart(f'{clean_type}_cities_chart', 'Распределение по городам')
        agents_chart = self.create_chart(f'{clean_type}_agents_chart', 'Распределение по типам агентов')

        row1_layout.addWidget(cities_chart)
        row1_layout.addWidget(agents_chart)

        layout.addLayout(row1_layout)

        layout.addStretch()

        content.setLayout(layout)
        scroll.setWidget(content)

        return scroll
    
    def create_supervision_statistics_tab(self):
        """Создание вкладки статистики авторского надзора"""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(15, 15, 15, 15)

        # ТОЛЬКО ДИАГРАММЫ - карточки статистики показываются в дашборде main_window
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(15)

        cities_chart = self.create_chart('supervision_cities_chart', 'Распределение по городам')
        agents_chart = self.create_chart('supervision_agents_chart', 'Распределение по типам агентов')

        row1_layout.addWidget(cities_chart)
        row1_layout.addWidget(agents_chart)

        layout.addLayout(row1_layout)

        layout.addStretch()

        content.setLayout(layout)
        scroll.setWidget(content)

        return scroll

    def create_chart(self, object_name, title):
        """Создание круговой диаграммы"""
        group = QGroupBox(title)
        group.setObjectName(object_name)
        group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #d9d9d9;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #2C3E50;
            }
        """)

        layout = QVBoxLayout()

        if MATPLOTLIB_AVAILABLE:
            figure = plt.Figure(figsize=(6, 4), dpi=100)
            canvas = FigureCanvas(figure)
            canvas.setObjectName('canvas')
            layout.addWidget(canvas)
        else:
            # Заглушка если matplotlib не установлен
            label = QLabel("Графики недоступны.\nУстановите matplotlib для отображения диаграмм.")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #999; padding: 40px;")
            layout.addWidget(label)

        group.setLayout(layout)

        return group
    
    def load_cities(self):
        """Загрузка списка городов"""
        try:
            self.city_combo.clear()
            self.city_combo.addItem('Все')

            cities = self.data_access.get_cities()
            for city in cities:
                self.city_combo.addItem(city)
        except Exception as e:
            print(f"Ошибка загрузки городов: {e}")
    
    def load_agent_types(self):
        """Загрузка типов агентов из договоров"""
        try:
            self.agent_type_combo.clear()
            self.agent_type_combo.addItem('Все')

            agents = self.data_access.get_agent_types()
            for agent in agents:
                self.agent_type_combo.addItem(agent)
        except Exception as e:
            print(f"Ошибка загрузки типов агентов: {e}")
    
    def on_quarter_changed(self):
        """Обработка изменения квартала"""
        if self.quarter_combo.currentText() != 'Все':
            self.month_combo.blockSignals(True)
            self.month_combo.setCurrentText('Все')
            self.month_combo.blockSignals(False)
        self.load_all_statistics()
    
    def on_month_changed(self):
        """Обработка изменения месяца"""
        if self.month_combo.currentText() != 'Все':
            self.quarter_combo.blockSignals(True)
            self.quarter_combo.setCurrentText('Все')
            self.quarter_combo.blockSignals(False)
        self.load_all_statistics()
    
    def reset_filters(self):
        """Сброс всех фильтров"""
        self.year_combo.setCurrentText(str(datetime.now().year))
        self.quarter_combo.setCurrentText('Все')
        self.month_combo.setCurrentText('Все')
        self.agent_type_combo.setCurrentText('Все')
        self.city_combo.setCurrentText('Все')
    
    def ensure_data_loaded(self):
        """Ленивая загрузка: данные загружаются при первом показе таба"""
        if not self._data_loaded:
            self._data_loaded = True
            self.load_all_statistics()

    def load_all_statistics(self):
        """Загрузка всей статистики"""
        year_text = self.year_combo.currentText()
        quarter = self.quarter_combo.currentText() if self.quarter_combo.currentText() != 'Все' else None
        month_text = self.month_combo.currentText()
        month = self.month_combo.currentIndex() if month_text != 'Все' else None
        agent_type = self.agent_type_combo.currentText() if self.agent_type_combo.currentText() != 'Все' else None
        city = self.city_combo.currentText() if self.city_combo.currentText() != 'Все' else None
        
        if quarter is None and month is None:
            year = int(year_text)
        else:
            year = int(year_text)
        
        self.load_project_statistics('Индивидуальный', year, quarter, month, agent_type, city)
        self.load_project_statistics('Шаблонный', year, quarter, month, agent_type, city)
        self.load_supervision_statistics(year, quarter, month, agent_type, city)
        self._load_analytics_charts()
    
    def load_project_statistics(self, project_type, year, quarter, month, agent_type, city):
        """Загрузка статистики для типа проекта"""
        try:
            stats = self.data_access.get_project_statistics(
                project_type=project_type, year=year, quarter=quarter,
                month=month, agent_type=agent_type, city=city
            )

            # Обновляем только диаграммы - карточки статистики в дашборде main_window
            self.update_pie_chart(f'{project_type}_cities_chart', stats['by_cities'])
            self.update_pie_chart(f'{project_type}_agents_chart', stats['by_agents'])

        except Exception as e:
            print(f"Ошибка загрузки статистики: {e}")
            import traceback
            traceback.print_exc()

    def load_supervision_statistics(self, year, quarter, month, agent_type, city):
        """Загрузка статистики авторского надзора"""
        try:
            stats = self.data_access.get_supervision_statistics_report(
                year=year, quarter=quarter, month=month,
                agent_type=agent_type, city=city
            )

            # Обновляем только диаграммы - карточки статистики в дашборде main_window
            self.update_pie_chart('supervision_cities_chart', stats['by_cities'])
            self.update_pie_chart('supervision_agents_chart', stats['by_agents'])

        except Exception as e:
            print(f"Ошибка загрузки статистики надзора: {e}")
            import traceback
            traceback.print_exc()
    
    def update_pie_chart(self, chart_name, data):
        """Обновление круговой диаграммы"""
        if not MATPLOTLIB_AVAILABLE:
            return

        chart = self.findChild(QGroupBox, chart_name)
        if chart:
            canvas = chart.findChild(FigureCanvas, 'canvas')
            if canvas:
                figure = canvas.figure
                figure.clear()
                
                if data and sum(data.values()) > 0:
                    ax = figure.add_subplot(111)
                    
                    labels = list(data.keys())
                    values = list(data.values())
                    
                    colors = ['#388E3C', '#F57C00', '#1976D2', '#C62828', '#7B1FA2', '#0097A7']
                    
                    wedges, texts, autotexts = ax.pie(
                        values,
                        labels=labels,
                        autopct='%1.1f%%',
                        colors=colors[:len(labels)],
                        startangle=90
                    )
                    
                    for autotext in autotexts:
                        autotext.set_color('white')
                        autotext.set_fontweight('bold')
                        autotext.set_fontsize(10)
                    
                    ax.axis('equal')
                else:
                    ax = figure.add_subplot(111)
                    ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center', fontsize=14, color='#999')
                    ax.axis('off')
                
                canvas.draw()
    
    def export_full_report(self):
        """Экспорт полного отчета в PDF"""
        dialog = QDialog(self)
        dialog.setWindowTitle('Экспорт в PDF')
        dialog.setMinimumWidth(550)
        
        dialog_layout = QVBoxLayout()
        dialog_layout.setSpacing(15)
        dialog_layout.setContentsMargins(20, 20, 20, 20)
        
        header = QLabel('Экспорт полного отчета в PDF')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #E74C3C;')
        header.setAlignment(Qt.AlignCenter)
        dialog_layout.addWidget(header)
        
        filename_layout = QFormLayout()
        
        filename_input = QLineEdit()
        default_filename = f'Полный отчет {datetime.now().strftime("%Y-%m-%d")}'
        filename_input.setText(default_filename)
        filename_input.setStyleSheet('padding: 8px; border: 1px solid #DDD; border-radius: 6px;')
        filename_layout.addRow('Имя файла:', filename_input)
        
        dialog_layout.addLayout(filename_layout)
        
        folder_btn = QPushButton('Выбрать папку и экспортировать')
        folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 12px;
                border-radius: 6px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        folder_btn.clicked.connect(lambda: self.perform_pdf_export(dialog, filename_input))
        dialog_layout.addWidget(folder_btn)
        
        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet('padding: 12px;')
        cancel_btn.clicked.connect(dialog.reject)
        dialog_layout.addWidget(cancel_btn)
        
        dialog.setLayout(dialog_layout)
        dialog.exec_()
    
    def perform_pdf_export(self, parent_dialog, filename_input):
        """Выполнение экспорта PDF"""
        try:
            folder = QFileDialog.getExistingDirectory(self, 'Выберите папку')
            
            if not folder:
                return
            
            filename = filename_input.text().strip()
            if not filename:
                filename = f'report_{datetime.now().strftime("%Y%m%d")}'
            
            if not filename.endswith('.pdf'):
                filename += '.pdf'
            
            full_path = f"{folder}/{filename}"

            year = int(self.year_combo.currentText())
            quarter = self.quarter_combo.currentText() if self.quarter_combo.currentText() != 'Все' else None
            month = self.month_combo.currentIndex() if self.month_combo.currentText() != 'Все' else None

            individual = self.data_access.get_project_statistics(
                project_type='Индивидуальный', year=year, quarter=quarter,
                month=month, agent_type=None, city=None
            )
            template = self.data_access.get_project_statistics(
                project_type='Шаблонный', year=year, quarter=quarter,
                month=month, agent_type=None, city=None
            )
            supervision = self.data_access.get_supervision_statistics_report(
                year=year, quarter=quarter, month=month, agent_type=None, city=None
            )
            
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
                pixmap = QPixmap(logo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaledToHeight(80, Qt.SmoothTransformation)
                    image = scaled_pixmap.toImage()
                    doc.addResource(QTextDocument.ImageResource, QUrl.fromLocalFile(logo_path), image)
                    
                    image_format = QTextImageFormat()
                    image_format.setName(logo_path)
                    image_format.setWidth(scaled_pixmap.width())
                    image_format.setHeight(scaled_pixmap.height())
                    cursor.insertImage(image_format)
                    cursor.insertText('\n\n')
            
            # ЗАГОЛОВКИ
            company_format = QTextCharFormat()
            company_format.setFont(QFont('Arial', 18, QFont.Bold))
            cursor.insertText('FESTIVAL COLOR\n', company_format)
            
            subtitle_format = QTextCharFormat()
            subtitle_format.setFont(QFont('Arial', 10))
            subtitle_format.setForeground(QColor('#666'))
            cursor.insertText('Полный отчет по проектам\n\n', subtitle_format)
            
            cursor.insertText('\n')
            
            title_format = QTextCharFormat()
            title_format.setFont(QFont('Arial', 14, QFont.Bold))
            cursor.insertText(f'Статистика за {year} год\n\n', title_format)
            
            date_format = QTextCharFormat()
            date_format.setFont(QFont('Arial', 8))
            date_format.setForeground(QColor('#95A5A6'))
            cursor.insertText(f'Дата: {QDate.currentDate().toString("dd.MM.yyyy")}\n\n', date_format)
            
            # ТАБЛИЦА
            from PyQt5.QtGui import QTextLength  # Добавьте этот импорт в начало файла если его нет
            
            table_format = QTextTableFormat()
            table_format.setBorder(1)
            table_format.setBorderBrush(QBrush(QColor('#CCCCCC')))
            table_format.setCellPadding(4)
            table_format.setCellSpacing(0)
            table_format.setHeaderRowCount(1)
            table_format.setWidth(QTextLength(QTextLength.PercentageLength, 100))  # ← РАСТЯНУТЬ НА ВСЮ ШИРИНУ
            
            table = cursor.insertTable(4, 7, table_format)
            
            # Заголовки
            header_format = QTextCharFormat()
            header_format.setFont(QFont('Arial', 9, QFont.Bold))
            header_format.setForeground(QColor('white'))
            
            headers = ['Тип', 'Всего', 'Площадь', 'Активные', 'Выполненные', 'Расторгнуто', 'Просрочки']
            for col, h in enumerate(headers):
                cell = table.cellAt(0, col)
                
                # ← ФОРМАТИРОВАНИЕ ЯЧЕЙКИ ЗАГОЛОВКА
                cell_format = cell.format()
                cell_format.setBackground(QBrush(QColor('#808080')))
                cell.setFormat(cell_format)
                
                cell_cursor = cell.firstCursorPosition()
                cell_cursor.insertText(h, header_format)
            
            # Данные
            data_format = QTextCharFormat()
            data_format.setFont(QFont('Arial', 8))
            data_format.setForeground(QColor('#333'))
            
            for row, (name, stats) in enumerate([
                ('Индивидуальные', individual),
                ('Шаблонные', template),
                ('Авторский надзор', supervision)
            ], start=1):
                # ← ЧЕРЕДОВАНИЕ ФОНА СТРОК
                if row % 2 == 0:
                    row_bg = QColor('#FFFFFF')
                else:
                    row_bg = QColor('#F5F5F5')
                
                # Заполнение ячеек с форматированием
                for col, value in enumerate([
                    name,
                    str(stats['total_orders']),
                    f"{stats['total_area']:.0f} м²",
                    str(stats['active']),
                    str(stats['completed']),
                    str(stats['cancelled']),
                    str(stats['overdue'])
                ]):
                    cell = table.cellAt(row, col)
                    
                    # ← ПРИМЕНЕНИЕ ФОНА К ЯЧЕЙКЕ
                    cell_format = cell.format()
                    cell_format.setBackground(QBrush(row_bg))
                    cell.setFormat(cell_format)
                    
                    cell_cursor = cell.firstCursorPosition()
                    cell_cursor.insertText(value, data_format)
            
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
                f'Документ сформирован системой Festival Color\n'
                f'{QDate.currentDate().toString("dd.MM.yyyy")}',
                footer_format
            )
            
            doc.print_(printer)
            
            parent_dialog.accept()
            
            # Диалог успеха
            success = QDialog(self)
            success.setWindowTitle('Успех')
            success.setMinimumWidth(500)
            
            success_layout = QVBoxLayout()
            success_layout.setSpacing(15)
            success_layout.setContentsMargins(20, 20, 20, 20)
            
            success_title = QLabel('PDF создан!')
            success_title.setStyleSheet('font-size: 14px; font-weight: bold; color: #27AE60;')
            success_title.setAlignment(Qt.AlignCenter)
            success_layout.addWidget(success_title)
            
            path_label = QLabel(full_path)
            path_label.setWordWrap(True)
            path_label.setStyleSheet('padding: 10px; background-color: #ffffff; border-radius: 6px;')
            success_layout.addWidget(path_label)
            
            open_btn = QPushButton('Открыть папку')
            open_btn.setStyleSheet('background-color: #ffd93c; color: white; padding: 10px; border-radius: 6px;')
            open_btn.clicked.connect(lambda: self.open_folder(folder))
            success_layout.addWidget(open_btn)
            
            ok_btn = QPushButton('OK')
            ok_btn.setStyleSheet('padding: 10px;')
            ok_btn.clicked.connect(success.accept)
            success_layout.addWidget(ok_btn)
            
            success.setLayout(success_layout)
            success.exec_()
            
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка экспорта:\n{str(e)}')
            import traceback
            traceback.print_exc()
     
    def open_folder(self, folder_path):
        """Открытие папки"""
        import platform
        try:
            if platform.system() == 'Windows':
                os.startfile(folder_path)
            elif platform.system() == 'Darwin':
                os.system(f'open "{folder_path}"')
            else:
                os.system(f'xdg-open "{folder_path}"')
        except Exception as e:
            print(f"Ошибка открытия папки: {e}")
