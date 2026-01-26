# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,

                             QGroupBox, QPushButton, QComboBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QHeaderView,
                             QFileDialog, QMessageBox, QSpinBox)
from PyQt5.QtCore import Qt, QDate
from ui.custom_combobox import CustomComboBox
from database.db_manager import DatabaseManager
from utils.pdf_generator import PDFGenerator
from utils.icon_loader import IconLoader  # ← ДОБАВЛЕНО
from utils.calendar_helpers import ICONS_PATH
from datetime import datetime

class EmployeeReportsTab(QWidget):
    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.db = DatabaseManager()
        self.pdf_gen = PDFGenerator()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Заголовок
        header = QLabel(' Отчеты по сотрудникам ')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #333333; padding: 5px;')
        layout.addWidget(header)
        
        # Вкладки по типам проектов
        self.report_tabs = QTabWidget()
        
        # Индивидуальные проекты
        self.individual_tab = self.create_report_tab('Индивидуальный')
        self.report_tabs.addTab(self.individual_tab, 'Индивидуальные проекты')
        
        # Шаблонные проекты
        self.template_tab = self.create_report_tab('Шаблонный')
        self.report_tabs.addTab(self.template_tab, 'Шаблонные проекты')
        
        # Авторский надзор
        self.supervision_tab = self.create_report_tab('Авторский надзор')
        self.report_tabs.addTab(self.supervision_tab, 'Авторский надзор')
        
        layout.addWidget(self.report_tabs)
        
        self.setLayout(layout)
    
    def create_report_tab(self, project_type):
        """Создание вкладки отчета"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # Фильтры периода
        filters_group = QGroupBox('Период отчета')
        filters_main_layout = QVBoxLayout()

        # Кнопка свернуть/развернуть
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 5)

        toggle_filters_btn = IconLoader.create_icon_button('arrow-down-circle', '', 'Развернуть фильтры', icon_size=12)
        toggle_filters_btn.setFixedSize(20, 20)
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
        filters_content.hide()  # По умолчанию свернуто

        filters_layout.addWidget(QLabel('Тип периода:'))
        period_combo = CustomComboBox()
        period_combo.addItems(['Месяц', 'Квартал', 'Год'])
        period_combo.setObjectName(f'period_{project_type}')
        period_combo.currentTextChanged.connect(lambda: self.load_report_data(project_type))
        filters_layout.addWidget(period_combo)
        
        filters_layout.addWidget(QLabel('Год:'))
        year_spin = QSpinBox()
        year_spin.setRange(2020, 2030)
        year_spin.setValue(QDate.currentDate().year())
        year_spin.setObjectName(f'year_{project_type}')
        year_spin.valueChanged.connect(lambda: self.load_report_data(project_type))
        year_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #FFFFFF;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
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
                background-color: #ffffff;
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
        filters_layout.addWidget(year_spin)
        
        filters_layout.addWidget(QLabel('Квартал:'))
        quarter_combo = CustomComboBox()
        quarter_combo.addItems(['Q1', 'Q2', 'Q3', 'Q4'])
        quarter_combo.setObjectName(f'quarter_{project_type}')
        quarter_combo.currentTextChanged.connect(lambda: self.load_report_data(project_type))
        filters_layout.addWidget(quarter_combo)
        
        filters_layout.addWidget(QLabel('Месяц:'))
        month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_combo.addItems(months)
        month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        month_combo.setObjectName(f'month_{project_type}')
        month_combo.currentTextChanged.connect(lambda: self.load_report_data(project_type))
        filters_layout.addWidget(month_combo)
        
        # ========== ИЗМЕНЕНО: SVG иконка ==========
        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить', icon_size=12)
        refresh_btn.clicked.connect(lambda: self.load_report_data(project_type))
        filters_layout.addWidget(refresh_btn)
        # ==========================================

        filters_layout.addStretch()

        # Добавляем контейнер фильтров в основной layout
        filters_main_layout.addWidget(filters_content)

        # Обработчик сворачивания/разворачивания фильтров
        def toggle_filters_emp():
            is_visible = filters_content.isVisible()
            filters_content.setVisible(not is_visible)
            if is_visible:
                toggle_filters_btn.setIcon(IconLoader.load('arrow-down-circle'))
                toggle_filters_btn.setToolTip('Развернуть фильтры')
            else:
                toggle_filters_btn.setIcon(IconLoader.load('arrow-up-circle'))
                toggle_filters_btn.setToolTip('Свернуть фильтры')

        toggle_filters_btn.clicked.connect(toggle_filters_emp)

        filters_group.setLayout(filters_main_layout)
        layout.addWidget(filters_group)
        
        # Таблицы статистики
        tables_layout = QHBoxLayout()
        
        # Таблица выполненных заказов
        completed_group = QGroupBox('Выполненные заказы')
        completed_layout = QVBoxLayout()
        
        completed_table = QTableWidget()
        completed_table.setStyleSheet("""
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
        completed_table.setObjectName(f'completed_table_{project_type}')
        completed_table.setColumnCount(3)
        completed_table.setHorizontalHeaderLabels(['Исполнитель', 'Должность', 'Количество'])
        completed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        completed_table.setMaximumHeight(300)

        # Запрещаем изменение высоты строк
        completed_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        completed_table.verticalHeader().setDefaultSectionSize(32)

        completed_layout.addWidget(completed_table)
        completed_group.setLayout(completed_layout)
        tables_layout.addWidget(completed_group)
        
        # Таблица зарплат
        salary_group = QGroupBox('Сумма зарплаты')
        salary_layout = QVBoxLayout()
        
        salary_table = QTableWidget()
        salary_table.setStyleSheet("""
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
        salary_table.setObjectName(f'salary_table_{project_type}')
        salary_table.setColumnCount(3)
        salary_table.setHorizontalHeaderLabels(['Исполнитель', 'Должность', 'Сумма'])
        salary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        salary_table.setMaximumHeight(300)

        # Запрещаем изменение высоты строк
        salary_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        salary_table.verticalHeader().setDefaultSectionSize(32)

        salary_layout.addWidget(salary_table)
        salary_group.setLayout(salary_layout)
        tables_layout.addWidget(salary_group)
        
        layout.addLayout(tables_layout)
        
        # Кнопки экспорта
        export_layout = QHBoxLayout()
        export_layout.addStretch()
        
        # ========== ИЗМЕНЕНО: SVG иконки ==========
        export_completed_btn = IconLoader.create_icon_button('export', 'Экспорт: Выполненные заказы', icon_size=12)
        export_completed_btn.clicked.connect(lambda: self.export_report(project_type, 'completed'))
        export_layout.addWidget(export_completed_btn)
        
        export_salary_btn = IconLoader.create_icon_button('export', 'Экспорт: Зарплаты', icon_size=12)
        export_salary_btn.clicked.connect(lambda: self.export_report(project_type, 'salary'))
        export_layout.addWidget(export_salary_btn)
        # =========================================
        
        layout.addLayout(export_layout)
        
        widget.setLayout(layout)
        
        # Загружаем начальные данные
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, lambda: self.load_report_data(project_type))
        
        return widget
    
    def load_report_data(self, project_type):
        """Загрузка данных отчета"""
        try:
            # Получаем виджет вкладки
            if project_type == 'Индивидуальный':
                tab_widget = self.individual_tab
            elif project_type == 'Шаблонный':
                tab_widget = self.template_tab
            else:
                tab_widget = self.supervision_tab
            
            # Получаем значения фильтров
            period_combo = tab_widget.findChild(QComboBox, f'period_{project_type}')
            year_spin = tab_widget.findChild(QSpinBox, f'year_{project_type}')
            quarter_combo = tab_widget.findChild(QComboBox, f'quarter_{project_type}')
            month_combo = tab_widget.findChild(QComboBox, f'month_{project_type}')
            
            if not period_combo or not year_spin:
                print(f"[WARN] Не найдены виджеты фильтров для {project_type}")
                return
            
            period = period_combo.currentText()
            year = year_spin.value()
            quarter = quarter_combo.currentText() if period == 'Квартал' else None
            month = month_combo.currentIndex() + 1 if period == 'Месяц' else None
            
            # Получаем данные из API или БД
            if self.api_client:
                try:
                    report_data = self.api_client.get_employee_report_data(project_type, period, year, quarter, month)
                except Exception as e:
                    print(f"[WARN] API ошибка get_employee_report_data: {e}")
                    report_data = self.db.get_employee_report_data(project_type, period, year, quarter, month)
            else:
                report_data = self.db.get_employee_report_data(project_type, period, year, quarter, month)
            
            # Обновляем таблицы
            self.update_completed_table(tab_widget, project_type, report_data.get('completed', []))
            self.update_salary_table(tab_widget, project_type, report_data.get('salaries', []))
            
        except Exception as e:
            print(f"❌ Ошибка загрузки данных отчета: {e}")
            import traceback
            traceback.print_exc()
    
    def update_completed_table(self, tab_widget, project_type, data):
        """Обновление таблицы выполненных заказов"""
        table = tab_widget.findChild(QTableWidget, f'completed_table_{project_type}')
        
        if not table:
            return
        
        table.setRowCount(len(data))
        
        for row, item in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(item.get('employee_name', '')))
            table.setItem(row, 1, QTableWidgetItem(item.get('position', '')))
            table.setItem(row, 2, QTableWidgetItem(str(item.get('count', 0))))
    
    def update_salary_table(self, tab_widget, project_type, data):
        """Обновление таблицы зарплат"""
        table = tab_widget.findChild(QTableWidget, f'salary_table_{project_type}')
        
        if not table:
            return
        
        table.setRowCount(len(data))
        
        total = 0
        for row, item in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(item.get('employee_name', '')))
            table.setItem(row, 1, QTableWidgetItem(item.get('position', '')))
            
            salary = item.get('total_salary', 0)
            amount_item = QTableWidgetItem(f"{salary:,.2f} ₽")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 2, amount_item)
            
            total += salary
        
        # Добавляем строку итого
        if data:
            table.setRowCount(len(data) + 1)
            total_label = QTableWidgetItem('ИТОГО:')
            font = total_label.font()
            font.setBold(True)
            total_label.setFont(font)
            table.setItem(len(data), 1, total_label)
            
            total_item = QTableWidgetItem(f"{total:,.2f} ₽")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setBackground(Qt.lightGray)
            font = total_item.font()
            font.setBold(True)
            total_item.setFont(font)
            table.setItem(len(data), 2, total_item)
    
    def export_report(self, project_type, report_type):
        """Экспорт отчета в PDF"""
        try:
            # Получаем виджет вкладки
            if project_type == 'Индивидуальный':
                tab_widget = self.individual_tab
            elif project_type == 'Шаблонный':
                tab_widget = self.template_tab
            else:
                tab_widget = self.supervision_tab
            
            # Получаем параметры периода
            period_combo = tab_widget.findChild(QComboBox, f'period_{project_type}')
            year_spin = tab_widget.findChild(QSpinBox, f'year_{project_type}')
            quarter_combo = tab_widget.findChild(QComboBox, f'quarter_{project_type}')
            month_combo = tab_widget.findChild(QComboBox, f'month_{project_type}')
            
            period = period_combo.currentText()
            year = year_spin.value()
            quarter = quarter_combo.currentText() if period == 'Квартал' else None
            month = month_combo.currentIndex() + 1 if period == 'Месяц' else None
            
            # Диалог сохранения
            filename, _ = QFileDialog.getSaveFileName(
                self,
                'Сохранить отчет',
                f'Отчет_сотрудники_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
                'PDF Files (*.pdf)'
            )
            
            if filename:
                # Получаем данные
                if self.api_client:
                    try:
                        report_data = self.api_client.get_employee_report_data(project_type, period, year, quarter, month)
                    except Exception as e:
                        print(f"[WARN] API ошибка get_employee_report_data: {e}")
                        report_data = self.db.get_employee_report_data(project_type, period, year, quarter, month)
                else:
                    report_data = self.db.get_employee_report_data(project_type, period, year, quarter, month)
                
                # Генерируем PDF
                if report_type == 'completed':
                    data = report_data.get('completed', [])
                    headers = ['Исполнитель', 'Должность', 'Количество проектов']
                    title = f'Выполненные заказы - {project_type}'
                    
                    pdf_data = [[item.get('employee_name', ''), 
                                item.get('position', ''), 
                                str(item.get('count', 0))] for item in data]
                else:  # salary
                    data = report_data.get('salaries', [])
                    headers = ['Исполнитель', 'Должность', 'Сумма (₽)']
                    title = f'Зарплаты - {project_type}'
                    
                    pdf_data = [[item.get('employee_name', ''), 
                                item.get('position', ''), 
                                f"{item.get('total_salary', 0):,.2f}"] for item in data]
                
                self.pdf_gen.generate_report(filename, title, pdf_data, headers)
                
                QMessageBox.information(self, 'Успех', f'Отчет сохранен:\n{filename}')
        
        except Exception as e:
            QMessageBox.critical(self, 'Ошибка', f'Ошибка экспорта отчета:\n{str(e)}')
            import traceback
            traceback.print_exc()
