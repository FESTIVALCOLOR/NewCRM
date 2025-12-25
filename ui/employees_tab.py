# -*- coding: utf-8 -*-
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QLabel, QMessageBox, QHeaderView,
                             QDateEdit, QCheckBox, QGroupBox, QTextEdit, QFrame,
                             QTabWidget)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate
from database.db_manager import DatabaseManager
from config import POSITIONS
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox
from ui.custom_combobox import CustomComboBox
from utils.calendar_styles import CALENDAR_STYLE, add_today_button_to_dateedit

class EmployeesTab(QWidget):
    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.db = DatabaseManager()
        
        # ========== ОПРЕДЕЛЯЕМ ПРАВА ==========
        self.can_edit = employee['position'] in [
            'Руководитель студии', 
            'Старший менеджер проектов'
        ]
        # ======================================
        
        self.init_ui()
        self.load_employees()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # Заголовок и кнопка добавления
        header_layout = QHBoxLayout()
        title = QLabel(' Управление сотрудниками ')
        title.setStyleSheet('font-size: 14px; font-weight: bold; color: #333333; padding: 5px;')
        header_layout.addWidget(title)
        header_layout.addStretch()

        # ========== КНОПКА ПОИСКА ==========
        search_btn = IconLoader.create_icon_button('search', 'Поиск', 'Поиск сотрудников', icon_size=16)
        search_btn.clicked.connect(self.open_search)
        search_btn.setStyleSheet('''
            QPushButton {
                padding: 8px 16px;
                font-weight: 500;
                color: #333;
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                margin-right: 10px;
            }
            QPushButton:hover {
                background-color: #E8F4F8;
                border-color: #3498DB;
            }
        ''')
        header_layout.addWidget(search_btn)
        # ===================================

        # Кнопка добавления
        if self.can_edit: 
            add_btn = IconLoader.create_icon_button('add2', '  Добавить сотрудника  ', icon_size=16)
            add_btn.clicked.connect(self.add_employee)
            add_btn.setStyleSheet('padding: 8px 16px; font-weight: bold;')
            header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # ========== ЗАМЕНА: Кнопки-фильтры вместо QTabWidget ==========
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(0, 5, 0, 5)

        self.filter_buttons = {}
        departments = [
            ('all', '  Все отделы  '),
            ('admin', '   Административный отдел   '),
            ('project', '  Проектный отдел  '),
            ('executive', '  Исполнительный отдел  ')
        ]

        for dept_key, dept_name in departments:
            btn = QPushButton(dept_name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 8px 16px;
                    border: 1px solid #E0E0E0;
                    background-color: #FFFFFF;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #F5F5F5;
                }
                QPushButton:checked {
                    background-color: #4A90E2;
                    color: white;
                    border-color: #4A90E2;
                    font-weight: bold;
                }
            """)
            btn.clicked.connect(lambda checked, key=dept_key: self.on_filter_changed(key))
            filter_layout.addWidget(btn)
            self.filter_buttons[dept_key] = btn

        # По умолчанию выбрано "Все отделы"
        self.filter_buttons['all'].setChecked(True)

        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        # =============================================================

        # Таблица сотрудников
        self.employees_table = QTableWidget()
        self.employees_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
            }
            QTableCornerButton::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
        """)
        self.employees_table.setColumnCount(8)  # ← Было 7, стало 8
        self.employees_table.setHorizontalHeaderLabels([
            ' ID ', ' ФИО ', ' Должность ', ' Телефон ', ' Email ', 
            ' Дата рождения ', ' Статус ', ' Действия '  # ← ИЗМЕНЕНО
        ])

        # ========== СКРЫВАЕМ КОЛОНКУ ID ==========
        self.employees_table.setColumnHidden(0, True)
        # =========================================

        header = self.employees_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        self.employees_table.setColumnWidth(0, 50)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        self.employees_table.setColumnWidth(2, 200)
        header.setSectionResizeMode(3, QHeaderView.Interactive)
        self.employees_table.setColumnWidth(3, 150)
        header.setSectionResizeMode(4, QHeaderView.Interactive)
        self.employees_table.setColumnWidth(4, 220)
        header.setSectionResizeMode(5, QHeaderView.Interactive)  # ← Дата рождения
        self.employees_table.setColumnWidth(5, 140)
        header.setSectionResizeMode(6, QHeaderView.Interactive)  # ← Статус
        self.employees_table.setColumnWidth(6, 100)
        header.setSectionResizeMode(7, QHeaderView.Fixed)  # ← Действия
        self.employees_table.setColumnWidth(7, 100)

        self.employees_table.setSortingEnabled(True)
        self.employees_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.employees_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.employees_table.setAlternatingRowColors(True)

        layout.addWidget(self.employees_table)

        self.setLayout(layout)

        # Загрузка данных по умолчанию
        self.load_employees()
        
    def open_search(self):
        """Открытие диалога поиска сотрудников"""
        dialog = EmployeeSearchDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            search_params = dialog.get_search_params()
            self.apply_search(search_params)
            
    def apply_search(self, params):
        """Применение фильтров поиска"""
        self.employees_table.setSortingEnabled(False)
        
        employees = self.db.get_all_employees()
        
        filtered_employees = []
        for emp in employees:
            if params.get('name'):
                if params['name'].lower() not in emp.get('full_name', '').lower():
                    continue
            
            if params.get('position'):
                if (params['position'] != emp.get('position', '') and 
                    params['position'] != emp.get('secondary_position', '')):
                    continue
            
            # ========== НОВОЕ: ФИЛЬТР ПО СТАТУСУ ==========
            if params.get('status'):
                if params['status'] != emp.get('status', ''):
                    continue
            # ==============================================
            
            if params.get('phone'):
                if params['phone'] not in emp.get('phone', ''):
                    continue
            
            if params.get('email'):
                if params['email'].lower() not in emp.get('email', '').lower():
                    continue
            
            if params.get('login'):
                if params['login'].lower() not in emp.get('login', '').lower():
                    continue
            
            filtered_employees.append(emp)
        
        # Перезагружаем таблицу с отфильтрованными данными
        self.employees_table.setRowCount(len(filtered_employees))
        
        for row, emp in enumerate(filtered_employees):
            self.employees_table.setRowHeight(row, 30)
            self.employees_table.setItem(row, 0, QTableWidgetItem(str(emp['id'])))
            self.employees_table.setItem(row, 1, QTableWidgetItem(emp['full_name']))
            
            # Должность (с дополнительной)
            position_display = emp['position']
            if emp.get('secondary_position'):
                position_display = f"{emp['position']}/{emp['secondary_position']}"
            self.employees_table.setItem(row, 2, QTableWidgetItem(position_display))
            
            self.employees_table.setItem(row, 3, QTableWidgetItem(emp.get('phone', '')))
            self.employees_table.setItem(row, 4, QTableWidgetItem(emp.get('email', '')))
            
            # ========== НОВОЕ: ДАТА РОЖДЕНИЯ ==========
            birth_date_str = emp.get('birth_date', '')
            if birth_date_str:
                try:
                    birth_date = QDate.fromString(birth_date_str, 'yyyy-MM-dd')
                    formatted_date = birth_date.toString('dd.MM.yyyy')
                except Exception:
                    formatted_date = ''
            else:
                formatted_date = ''
            self.employees_table.setItem(row, 5, QTableWidgetItem(formatted_date))
            # ==========================================
            
            # ========== НОВОЕ: СТАТУС ==========
            status = emp.get('status', 'активный')
            status_item = QTableWidgetItem(status)
            
            if status == 'активный':
                status_item.setForeground(Qt.darkGreen)
            elif status == 'уволен':
                status_item.setForeground(Qt.red)
            elif status == 'в резерве':
                status_item.setForeground(Qt.darkYellow)
            
            self.employees_table.setItem(row, 6, status_item)
            # ===================================

            # Кнопки действий (в колонке 7)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)

            view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=14)
            view_btn.setFixedSize(24, 24)
            view_btn.setStyleSheet('''
                QPushButton {
                    background-color: #F8F9FA;
                    border: 1px solid #E0E0E0;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #E8F4F8;
                }
            ''')
            view_btn.clicked.connect(lambda checked, e=emp: self.view_employee(e))
            actions_layout.addWidget(view_btn)

            if self.can_edit:
                edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=14)
                edit_btn.setFixedSize(24, 24)
                edit_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #d4e4bc;
                        border: 1px solid #c0d4a8;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #c0d4a8;
                    }
                ''')
                edit_btn.clicked.connect(lambda checked, e=emp: self.edit_employee(e))
                actions_layout.addWidget(edit_btn)

                # Кнопка удаления
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить', icon_size=14)
                delete_btn.setFixedSize(24, 24)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, e=emp: self.delete_employee(e))
                actions_layout.addWidget(delete_btn)

            actions_widget.setLayout(actions_layout)
            self.employees_table.setCellWidget(row, 7, actions_widget)


        self.employees_table.setSortingEnabled(True)
        
        CustomMessageBox(
            self, 
            'Результаты поиска', 
            f'Найдено сотрудников: {len(filtered_employees)}', 
            'info'
        ).exec_()
        
    def on_filter_changed(self, department_key):
        """Обработка переключения фильтра"""
        # Снимаем выделение со всех кнопок
        for btn in self.filter_buttons.values():
            btn.setChecked(False)
        
        # Выделяем нажатую кнопку
        self.filter_buttons[department_key].setChecked(True)
        
        # Загружаем данные
        if department_key == 'all':
            self.load_employees()
        else:
            self.load_employees(department=department_key)

    def load_employees(self, department=None):
        """Загрузка списка сотрудников с фильтрацией по отделу"""
        self.employees_table.setSortingEnabled(False)

        # Загружаем сотрудников из API или локальной БД
        if self.api_client:
            # Многопользовательский режим - загружаем из API
            employees = self.api_client.get_employees()
        else:
            # Локальный режим - загружаем из локальной БД
            employees = self.db.get_all_employees()

        if department == 'admin':
            positions = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
            employees = [emp for emp in employees if emp['position'] in positions]

        elif department == 'project':
            # ИСПРАВЛЕНО: единственное число
            positions = ['Дизайнер', 'Чертёжник']
            employees = [emp for emp in employees if emp['position'] in positions]

        elif department == 'executive':
            positions = ['Менеджер', 'ДАН', 'Замерщик']
            employees = [emp for emp in employees if emp['position'] in positions]

        self.employees_table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            self.employees_table.setRowHeight(row, 30)
            self.employees_table.setItem(row, 0, QTableWidgetItem(str(emp['id'])))
            self.employees_table.setItem(row, 1, QTableWidgetItem(emp['full_name']))
            
            # Должность (с дополнительной)
            position_display = emp['position']
            if emp.get('secondary_position'):
                position_display = f"{emp['position']}/{emp['secondary_position']}"
            self.employees_table.setItem(row, 2, QTableWidgetItem(position_display))
            
            self.employees_table.setItem(row, 3, QTableWidgetItem(emp.get('phone', '')))
            self.employees_table.setItem(row, 4, QTableWidgetItem(emp.get('email', '')))
            
            # ========== НОВОЕ: ДАТА РОЖДЕНИЯ ==========
            birth_date_str = emp.get('birth_date', '')
            if birth_date_str:
                try:
                    birth_date = QDate.fromString(birth_date_str, 'yyyy-MM-dd')
                    formatted_date = birth_date.toString('dd.MM.yyyy')
                except Exception:
                    formatted_date = ''
            else:
                formatted_date = ''
            self.employees_table.setItem(row, 5, QTableWidgetItem(formatted_date))
            # ==========================================
            
            # ========== НОВОЕ: СТАТУС ==========
            status = emp.get('status', 'активный')
            status_item = QTableWidgetItem(status)
            
            # Цветовая индикация статуса
            if status == 'активный':
                status_item.setForeground(Qt.darkGreen)
            elif status == 'уволен':
                status_item.setForeground(Qt.red)
            elif status == 'в резерве':
                status_item.setForeground(Qt.darkYellow)
            
            self.employees_table.setItem(row, 6, status_item)
            # ===================================

            # Кнопки действий (теперь в колонке 7)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)

            view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=14)
            view_btn.setFixedSize(24, 24)
            view_btn.setStyleSheet('''
                QPushButton {
                    background-color: #F8F9FA;
                    border: 1px solid #E0E0E0;
                    border-radius: 3px;
                }
                QPushButton:hover {
                    background-color: #E8F4F8;
                }
            ''')
            view_btn.clicked.connect(lambda checked, e=emp: self.view_employee(e))
            actions_layout.addWidget(view_btn)

            # Кнопка "Редактировать" (только для админов)
            if self.can_edit:
                edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=14)
                edit_btn.setFixedSize(24, 24)
                edit_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #d4e4bc;
                        border: 1px solid #c0d4a8;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #c0d4a8;
                    }
                ''')
                edit_btn.clicked.connect(lambda checked, e=emp: self.edit_employee(e))
                actions_layout.addWidget(edit_btn)

                # Кнопка удаления
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить', icon_size=14)
                delete_btn.setFixedSize(24, 24)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 3px;
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, e=emp: self.delete_employee(e))
                actions_layout.addWidget(delete_btn)

            actions_widget.setLayout(actions_layout)
            self.employees_table.setCellWidget(row, 7, actions_widget)
            
        self.employees_table.setSortingEnabled(True)

    def add_employee(self):
        """Открытие диалога добавления сотрудника"""
        dialog = EmployeeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self.load_employees()
            
    def view_employee(self, employee_data):
        """Просмотр информации о сотруднике"""
        dialog = EmployeeDialog(self, employee_data, view_only=True)
        dialog.exec_()
    
    def edit_employee(self, employee_data):
        """Редактирование сотрудника"""
        
        # ========== ПРОВЕРКА ПРАВ ==========
        if self.employee['position'] == 'Старший менеджер проектов':
            admin_positions = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
            if employee_data['position'] in admin_positions:
                CustomMessageBox(
                    self, 
                    'Доступ запрещен', 
                    'У вас нет прав для редактирования сотрудников административного отдела.\n\n'
                    'Только Руководитель студии может редактировать эти должности.',
                    'warning'
                ).exec_()
                return
        # ===================================
        
        dialog = EmployeeDialog(self, employee_data)
        if dialog.exec_() == QDialog.Accepted:
            self.load_employees()

    def delete_employee(self, employee_data):
        """Удаление сотрудника"""
        from ui.custom_message_box import CustomQuestionBox

        # Только Руководитель студии может удалять сотрудников
        if self.employee['position'] != 'Руководитель студии':
            CustomMessageBox(
                self,
                'Ошибка',
                'У вас недостаточно прав для удаления сотрудников.\nТолько Руководитель студии может удалять сотрудников.',
                'error'
            ).exec_()
            return

        # Нельзя удалить самого себя
        if employee_data['id'] == self.employee['id']:
            CustomMessageBox(
                self,
                'Ошибка',
                'Нельзя удалить самого себя.',
                'error'
            ).exec_()
            return

        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            f"Вы уверены, что хотите удалить сотрудника {employee_data['full_name']}?"
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                if self.api_client:
                    # API режим
                    self.api_client.delete_employee(employee_data['id'])
                else:
                    # Локальный режим
                    self.db.delete_employee(employee_data['id'])

                CustomMessageBox(
                    self,
                    'Успех',
                    'Сотрудник успешно удален',
                    'success'
                ).exec_()

                self.load_employees()

            except Exception as e:
                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить сотрудника: {str(e)}',
                    'error'
                ).exec_()

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
        
class EmployeeDialog(QDialog):
    def __init__(self, parent, employee_data=None, view_only=False):
        super().__init__(parent)
        self.employee_data = employee_data
        self.view_only = view_only
        self.db = DatabaseManager()
        # Получаем api_client от родителя, если он есть
        self.api_client = getattr(parent, 'api_client', None)

        # ========== НОВОЕ: ПРОВЕРКА ПРАВ ==========
        self.current_user = parent.employee  # Получаем текущего пользователя
        # ==========================================

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()
        
        if employee_data:
            self.fill_data()
    
    def init_ui(self):
        title = 'Просмотр сотрудника' if self.view_only else ('Добавление сотрудника' if not self.employee_data else 'Редактирование сотрудника')
        
        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("borderFrame")
        border_frame.setStyleSheet("""
            QFrame#borderFrame {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # Кастомный title bar
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
        
        # Основная информация
        main_group = QGroupBox('Основная информация')
        main_layout_form = QFormLayout()
        
        self.full_name = QLineEdit()
        self.full_name.setPlaceholderText('Иванов Иван Иванович')
        main_layout_form.addRow('ФИО*:', self.full_name)
        
        self.position = CustomComboBox()

        # ========== ФИЛЬТРУЕМ ДОЛЖНОСТИ ДЛЯ СТАРШЕГО МЕНЕДЖЕРА ==========
        if self.current_user['position'] == 'Старший менеджер проектов':
            # Убираем руководящие должности
            restricted_positions = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
            filtered_positions = [pos for pos in POSITIONS if pos not in restricted_positions]
            self.position.addItems(filtered_positions)
        else:
            self.position.addItems(POSITIONS)
        # ================================================================

        main_layout_form.addRow('Должность*:', self.position)

        # ========== НОВОЕ: ВТОРАЯ ДОЛЖНОСТЬ ==========
        self.secondary_position = CustomComboBox()
        self.secondary_position.addItem('Нет', '')  # Пустое значение по умолчанию

        if self.current_user['position'] == 'Старший менеджер проектов':
            restricted_positions = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
            filtered_positions = [pos for pos in POSITIONS if pos not in restricted_positions]
            for pos in filtered_positions:
                self.secondary_position.addItem(pos, pos)
        else:
            for pos in POSITIONS:
                self.secondary_position.addItem(pos, pos)

        main_layout_form.addRow('Доп. должность:', self.secondary_position)
        # ==============================================
        
        # ========== НОВОЕ: СТАТУС СОТРУДНИКА ==========
        self.status = CustomComboBox()
        self.status.addItems(['активный', 'уволен', 'в резерве'])
        main_layout_form.addRow('Статус:', self.status)
        # ==============================================

        self.birth_date = CustomDateEdit()
        self.birth_date.setCalendarPopup(True)
        add_today_button_to_dateedit(self.birth_date)
        self.birth_date.setDate(QDate(1990, 1, 1))
        self.birth_date.setDisplayFormat('dd.MM.yyyy')
        main_layout_form.addRow('Дата рождения:', self.birth_date)
        
        main_group.setLayout(main_layout_form)
        layout.addWidget(main_group)
        
        # Контактная информация
        contact_group = QGroupBox('Контактная информация')
        contact_layout = QFormLayout()
        
        # В методе init_ui() класса EmployeeDialog
        self.phone = QLineEdit()
        self.phone.setPlaceholderText('+7 (999) 123-45-67')
        self.phone.setInputMask('+7 (999) 000-00-00;_') 
        contact_layout.addRow('Телефон:', self.phone)
        
        self.email = QLineEdit()
        self.email.setPlaceholderText('example@mail.com')
        contact_layout.addRow('Email:', self.email)
        
        self.address = QTextEdit()
        self.address.setPlaceholderText('Адрес проживания')
        self.address.setMaximumHeight(80)
        contact_layout.addRow('Адрес:', self.address)
        
        contact_group.setLayout(contact_layout)
        layout.addWidget(contact_group)
        
        # Данные для входа
        login_group = QGroupBox('Данные для входа в систему')
        login_layout = QFormLayout()
        
        self.login = QLineEdit()
        self.login.setPlaceholderText('ivanov')
        login_layout.addRow('Логин*:', self.login)
        
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.Password)
        
        if self.employee_data:
            self.password.setPlaceholderText('Оставьте пустым, чтобы не менять пароль')
            login_layout.addRow('Новый пароль:', self.password)
        else:
            self.password.setPlaceholderText('Минимум 4 символа')
            login_layout.addRow('Пароль*:', self.password)
        
        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.Password)
        self.password_confirm.setPlaceholderText('Повторите пароль')
        login_layout.addRow('Подтверждение:', self.password_confirm)
        
        login_group.setLayout(login_layout)
        layout.addWidget(login_group)
        
        # Кнопки
        if not self.view_only:
            buttons_layout = QHBoxLayout()
            buttons_layout.addStretch()
            
            save_btn = QPushButton('Сохранить')
            save_btn.clicked.connect(self.save_employee)
            save_btn.setStyleSheet('padding: 10px 30px; font-weight: bold;')
            
            cancel_btn = QPushButton('Отмена')
            cancel_btn.clicked.connect(self.reject)
            cancel_btn.setStyleSheet('padding: 10px 30px;')
            
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            
            layout.addLayout(buttons_layout)
        else:
            # ========== РЕЖИМ ПРОСМОТРА ==========
            close_btn = QPushButton('Закрыть')
            close_btn.clicked.connect(self.reject)
            close_btn.setStyleSheet('padding: 10px 30px; font-weight: bold;')
            layout.addWidget(close_btn)
            # =====================================

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # ========== БЛОКИРОВКА ПОЛЕЙ (ПОСЛЕ setLayout!) ==========
        if self.view_only:
            # Отключаем текстовые поля
            for child in self.findChildren(QLineEdit):
                child.setReadOnly(True)
            
            # Отключаем QTextEdit
            for child in self.findChildren(QTextEdit):
                child.setReadOnly(True)
            
            # БЛОКИРУЕМ QComboBox (запрещаем открытие списка)
            for child in self.findChildren(QComboBox):
                child.setEnabled(False)
            
            # БЛОКИРУЕМ QDateEdit (запрещаем открытие календаря)
            for child in self.findChildren(QDateEdit):
                child.setEnabled(False)
        # ==========================================================

        self.setMinimumWidth(650)
    
    def format_phone(self, text):
        """Форматирование телефона"""
        self.phone.blockSignals(True)
        
        digits = ''.join(filter(str.isdigit, text))
        
        if digits.startswith('8'):
            digits = '7' + digits[1:]
        
        if len(digits) == 0:
            formatted = ''
        elif len(digits) <= 1:
            formatted = '+' + digits
        elif len(digits) <= 4:
            formatted = f'+{digits[0]} ({digits[1:]}'
        elif len(digits) <= 7:
            formatted = f'+{digits[0]} ({digits[1:4]}) {digits[4:]}'
        elif len(digits) <= 9:
            formatted = f'+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:]}'
        else:
            formatted = f'+{digits[0]} ({digits[1:4]}) {digits[4:7]}-{digits[7:9]}-{digits[9:11]}'
        
        cursor_pos = self.phone.cursorPosition()
        self.phone.setText(formatted)
        self.phone.setCursorPosition(min(cursor_pos, len(formatted)))
        
        self.phone.blockSignals(False)
    
    def fill_data(self):
        """Заполнение формы данными сотрудника"""
        if self.employee_data:
            self.full_name.setText(self.employee_data['full_name'])
            self.position.setCurrentText(self.employee_data['position'])
            
            # Загрузка второй должности
            secondary_pos = self.employee_data.get('secondary_position', '')
            if secondary_pos:
                index = self.secondary_position.findData(secondary_pos)
                if index >= 0:
                    self.secondary_position.setCurrentIndex(index)
            
            # ========== НОВОЕ: ЗАГРУЗКА СТАТУСА ==========
            status_value = self.employee_data.get('status', 'активный')
            self.status.setCurrentText(status_value)
            # =============================================
            
            if self.employee_data.get('birth_date'):
                self.birth_date.setDate(QDate.fromString(self.employee_data['birth_date'], 'yyyy-MM-dd'))

            self.phone.setText(self.employee_data.get('phone', ''))
            self.email.setText(self.employee_data.get('email', ''))
            self.address.setPlainText(self.employee_data.get('address', ''))
            self.login.setText(self.employee_data['login'])
        
    def save_employee(self):
        """Сохранение сотрудника"""
        if not self.full_name.text().strip() or not self.login.text().strip():
            CustomMessageBox(self, 'Ошибка', 'Заполните все обязательные поля (ФИО, Логин)', 'warning').exec_()
            return
        
        # Проверка пароля при создании
        if not self.employee_data:
            if not self.password.text().strip():
                CustomMessageBox(self, 'Ошибка', 'Введите пароль', 'warning').exec_()
                return
            
            if len(self.password.text()) < 4:
                CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать минимум 4 символа', 'warning').exec_()
                return
            
            if self.password.text() != self.password_confirm.text():
                CustomMessageBox(self, 'Ошибка', 'Пароли не совпадают', 'warning').exec_()
                return
        else:
            # При редактировании пароль опционален
            if self.password.text().strip():
                if len(self.password.text()) < 4:
                    CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать минимум 4 символа', 'warning').exec_()
                    return
                
                if self.password.text() != self.password_confirm.text():
                    CustomMessageBox(self, 'Ошибка', 'Пароли не совпадают', 'warning').exec_()
                    return

        # Определяем department на основе position
        position = self.position.currentText()
        if position in ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']:
            department = 'Административный отдел'
        elif position in ['Дизайнер', 'Чертёжник']:
            department = 'Проектный отдел'
        elif position in ['Менеджер', 'ДАН', 'Замерщик']:
            department = 'Исполнительный отдел'
        else:
            department = 'Другое'

        employee_data = {
            'full_name': self.full_name.text().strip(),
            'position': self.position.currentText(),
            'secondary_position': self.secondary_position.currentData() or '',
            'department': department,  # Добавлено для API
            'status': self.status.currentText(),
            'birth_date': self.birth_date.date().toString('yyyy-MM-dd'),
            'phone': self.phone.text().strip(),
            'email': self.email.text().strip(),
            'address': self.address.toPlainText().strip(),
            'login': self.login.text().strip()
        }
        
        if self.password.text().strip():
            employee_data['password'] = self.password.text().strip()
        
        try:
            # ========== ПРОВЕРКА ИЗМЕНЕНИЯ СТАТУСА ==========
            status_changed = False
            if self.employee_data:  # Если редактирование
                old_status = self.employee_data.get('status', 'активный')
                new_status = employee_data['status']
                
                if old_status != new_status:
                    status_changed = True
                    print(f"⚠️ СТАТУС ИЗМЕНЁН: '{old_status}' → '{new_status}'")
            # ================================================

            if self.api_client:
                # Многопользовательский режим - сохраняем через API
                if self.employee_data:
                    self.api_client.update_employee(self.employee_data['id'], employee_data)
                else:
                    self.api_client.create_employee(employee_data)
            else:
                # Локальный режим - сохраняем в локальную БД
                if self.employee_data:
                    self.db.update_employee(self.employee_data['id'], employee_data)
                else:
                    self.db.add_employee(employee_data)

            # ========== УВЕДОМЛЕНИЕ О ПЕРЕЗАХОДЕ ==========
            if status_changed and self.employee_data:
                # Проверяем, редактирует ли сотрудник сам себя
                current_user = self.parent().employee

                if self.employee_data['id'] == current_user['id']:
                    # Редактирует сам себя - принудительный выход
                    CustomMessageBox(
                        self,
                        'Статус изменен',
                        'Ваш статус был изменен!\n\n'
                        'Необходимо перезайти в систему для применения изменений.\n\n'
                        'Приложение будет закрыто.',
                        'warning'
                    ).exec_()

                    # Закрываем все окна и возвращаемся к Login
                    from PyQt5.QtWidgets import QApplication
                    QApplication.quit()

                    import sys
                    python = sys.executable
                    os.execl(python, python, *sys.argv)

                else:
                    # Редактирует другого сотрудника - просто уведомление
                    CustomMessageBox(
                        self,
                        'Статус изменен',
                        f'Статус сотрудника изменен на "{new_status}".\n\n'
                        f'Если этот сотрудник сейчас в системе, ему нужно перезайти\n'
                        f'для применения изменений.',
                        'info'
                    ).exec_()
            # ==============================================

            # ИСПРАВЛЕНИЕ: Закрываем диалог без показа сообщения
            self.accept()
            
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить сотрудника:\n{str(e)}', 'error').exec_()
            
    def update_employee(self, employee_id, employee_data):
        """Обновление сотрудника"""
        conn = self.connect()
        cursor = conn.cursor()
        
        # Динамически формируем SET clause
        set_clause = ', '.join([f'{key} = ?' for key in employee_data.keys()])
        values = list(employee_data.values()) + [employee_id]
        
        cursor.execute(
            f'UPDATE employees SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
            values
        )
        conn.commit()
        self.close()
    
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

class EmployeeSearchDialog(QDialog):
    """Диалог поиска сотрудников"""
    def __init__(self, parent):
        super().__init__(parent)
        
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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        title_bar = CustomTitleBar(self, 'Поиск сотрудников', simple_mode=True)
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
        
        form_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText('Введите ФИО')
        form_layout.addRow('ФИО:', self.name_input)
        
        self.position_combo = CustomComboBox()
        self.position_combo.addItem('Все должности', '')
        for pos in POSITIONS:
            self.position_combo.addItem(pos, pos)
        form_layout.addRow('Должность:', self.position_combo)

        # ========== НОВОЕ: ФИЛЬТР ПО СТАТУСУ ==========
        self.status_combo = CustomComboBox()
        self.status_combo.addItem('Все статусы', '')
        self.status_combo.addItem('активный', 'активный')
        self.status_combo.addItem('уволен', 'уволен')
        self.status_combo.addItem('в резерве', 'в резерве')
        form_layout.addRow('Статус:', self.status_combo)
        # ==============================================       
        
        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText('+7 (999) 123-45-67')
        form_layout.addRow('Телефон:', self.phone_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('example@mail.com')
        form_layout.addRow('Email:', self.email_input)
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('ivanov')
        form_layout.addRow('Логин:', self.login_input)
        
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        
        search_btn = IconLoader.create_icon_button('search2', 'Найти', 'Выполнить поиск', icon_size=16)
        search_btn.clicked.connect(self.accept)
        search_btn.setStyleSheet('''
            QPushButton {
                padding: 10px 30px;
                font-weight: bold;
                background-color: #3498DB;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        ''')
        
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить фильтры', icon_size=16)
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setStyleSheet('padding: 10px 30px;')
        
        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet('padding: 10px 30px;')
        
        buttons_layout.addWidget(search_btn)
        buttons_layout.addWidget(reset_btn)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setFixedWidth(500)
    
    def reset_filters(self):
        """Сброс всех фильтров"""
        self.name_input.clear()
        self.position_combo.setCurrentIndex(0)
        self.phone_input.clear()
        self.email_input.clear()
        self.login_input.clear()
        
        self.parent().load_employees()
        
        CustomMessageBox(
            self, 
            'Сброс', 
            'Фильтры сброшены, показаны все сотрудники', 
            'success'
        ).exec_()
    
    def get_search_params(self):
        """Получение параметров поиска"""
        return {
            'name': self.name_input.text().strip(),
            'position': self.position_combo.currentData() or '',
            'status': self.status_combo.currentData() or '', 
            'phone': self.phone_input.text().strip(),
            'email': self.email_input.text().strip(),
            'login': self.login_input.text().strip()
        }
    
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
