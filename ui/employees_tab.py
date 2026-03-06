# -*- coding: utf-8 -*-
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QTableWidget, QTableWidgetItem, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QLabel, QMessageBox, QHeaderView,
                             QDateEdit, QCheckBox, QGroupBox, QTextEdit, QFrame,
                             QTabWidget)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate, QTimer
from database.db_manager import DatabaseManager
from config import POSITIONS
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
from utils.table_settings import ProportionalResizeTable
from utils.data_access import DataAccess

class EmployeesTab(QWidget):
    def __init__(self, employee, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.api_client = api_client
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db

        # ========== ОПРЕДЕЛЯЕМ ПРАВА (через permissions) ==========
        from utils.permissions import _has_perm
        self.can_create = _has_perm(employee, api_client, 'employees.create')
        self.can_edit = _has_perm(employee, api_client, 'employees.update')
        self.can_delete = _has_perm(employee, api_client, 'employees.delete')
        # ======================================

        self._data_loaded = False
        self.current_department = None  # Текущий выбранный фильтр отдела
        self.init_ui()
    
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

        search_btn = IconLoader.create_action_button('search', 'Поиск сотрудников')
        search_btn.clicked.connect(self.open_search)
        header_layout.addWidget(search_btn)

        if self.can_create:
            add_btn = IconLoader.create_action_button(
                'add', 'Добавить сотрудника',
                bg_color='#ffd93c', hover_color='#ffdb4d', icon_color='#000000')
            add_btn.clicked.connect(self.add_employee)
            header_layout.addWidget(add_btn)

        layout.addLayout(header_layout)

        # ========== ЗАМЕНА: Кнопки-фильтры вместо QTabWidget ==========
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(5)
        filter_layout.setContentsMargins(0, 5, 0, 5)

        self.filter_buttons = {}
        departments = [
            ('all', 'Все отделы'),
            ('admin', 'Административный отдел'),
            ('project', 'Проектный отдел'),
            ('executive', 'Исполнительный отдел')
        ]

        for dept_key, dept_name in departments:
            btn = QPushButton(dept_name)
            btn.setCheckable(True)
            btn.setStyleSheet("""
                QPushButton {
                    padding: 2px 8px;
                    font-size: 11px;
                    border: 1px solid #d9d9d9;
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

        # Таблица сотрудников - используем ProportionalResizeTable для растягивания + ручного изменения
        self.employees_table = ProportionalResizeTable()
        self.employees_table.setStyleSheet("""
            QTableWidget {
                background-color: #fafafa;
                border: 1px solid #d9d9d9;
                border-radius: 8px;
            }
            QTableWidget QTableCornerButton::section {
                background-color: #fafafa;
                border: none;
            }
            QTableWidget QHeaderView {
                background-color: #fafafa;
            }
            QTableWidget QHeaderView::section {
                background-color: #fafafa;
                border: none;
                border-bottom: 1px solid #e6e6e6;
                border-right: 1px solid #f0f0f0;
                padding: 4px;
            }
            QTableWidget QHeaderView::section:last {
                border-top-right-radius: 7px;
            }
            QTableWidget::item {
                background-color: #FFFFFF;
            }
            QTableWidget QScrollBar {
                background-color: #FFFFFF;
            }
        """)
        self.employees_table.setColumnCount(8)
        self.employees_table.setHorizontalHeaderLabels([
            ' ID ', ' ФИО ', ' Должность ', ' Телефон ', ' Email ',
            ' Дата рождения ', ' Статус ', ' Действия '
        ])

        # ========== СКРЫВАЕМ КОЛОНКУ ID ==========
        self.employees_table.setColumnHidden(0, True)
        # =========================================

        # Настройка пропорционального изменения размера:
        # - Колонки 0-6 растягиваются пропорционально И можно менять вручную
        # - Колонка 7 (Действия) фиксирована 110px
        self.employees_table.setup_proportional_resize(
            column_ratios=[0.05, 0.22, 0.18, 0.14, 0.18, 0.13, 0.10],  # Пропорции для колонок 0-6
            fixed_columns={7: 110},  # Действия = 110px фиксированно
            min_width=50
        )

        # Запрещаем изменение высоты строк
        self.employees_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.employees_table.verticalHeader().setDefaultSectionSize(32)

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

        employees = self.data.get_all_employees()

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
            
            # ========== СТАТУС (QLabel для гарантированного CSS-цвета) ==========
            status = emp.get('status', 'активный')
            status_item = QTableWidgetItem(status)
            self.employees_table.setItem(row, 6, status_item)
            self.employees_table.setCellWidget(row, 6, self._create_status_widget(status))
            # ===================================================================

            # Кнопки действий (в колонке 7)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)

            view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=12)
            view_btn.setFixedSize(20, 20)
            view_btn.setStyleSheet('''
                QPushButton {
                    background-color: #F8F9FA;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #f5f5f5;
                }
            ''')
            view_btn.clicked.connect(lambda checked, e=emp: self.view_employee(e))
            actions_layout.addWidget(view_btn)

            if self.can_edit:
                edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=12)
                edit_btn.setFixedSize(20, 20)
                edit_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #d4e4bc;
                        border: 1px solid #c0d4a8;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0d4a8;
                    }
                ''')
                edit_btn.clicked.connect(lambda checked, e=emp: self.edit_employee(e))
                actions_layout.addWidget(edit_btn)

            # Кнопка удаления — только для Руководителя студии
            if self.can_delete:
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить', icon_size=12)
                delete_btn.setFixedSize(20, 20)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, e=emp: self.delete_employee(e))
                actions_layout.addWidget(delete_btn)

            # Кнопка "Пригласить" — отправить welcome email + Telegram-ссылку
            if self.can_edit:
                invite_btn = IconLoader.create_icon_button('mail', '', 'Отправить приглашение', icon_size=12)
                invite_btn.setFixedSize(20, 20)
                invite_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #E8F4FD;
                        border: 1px solid #B0D4F1;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #BDD9F2;
                    }
                    QPushButton:disabled {
                        background-color: #E8F4E8;
                        border: 1px solid #B0D4B0;
                    }
                ''')
                # Если telegram уже подключён — кнопка показывает статус, но остаётся активной
                if emp.get('telegram_user_id'):
                    invite_btn.setToolTip('Telegram подключён. Можно отправить повторное приглашение')
                invite_btn.clicked.connect(lambda checked, e=emp: self.send_invite(e))
                actions_layout.addWidget(invite_btn)

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

        # Сохраняем текущий фильтр
        self.current_department = None if department_key == 'all' else department_key

        # Загружаем данные
        self.load_employees(department=self.current_department)

    def ensure_data_loaded(self):
        """Ленивая загрузка: данные загружаются при первом показе таба.
        При повторном переключении — пропускаем если кэш свежий (<30с)."""
        import time as _time
        now = _time.monotonic()
        first_time = not self._data_loaded

        if first_time:
            self._data_loaded = True
            self._last_load_time = now
            # Всегда через API — локальная БД может содержать устаревшие/тестовые данные
            self._reload_employees(prefer_local=False)
        elif now - getattr(self, '_last_load_time', 0) < 30:
            return
        else:
            self._last_load_time = now
            self._reload_employees(prefer_local=False)

    def load_employees(self, department=None):
        """Загрузка списка сотрудников с фильтрацией по отделу"""
        self.employees_table.setSortingEnabled(False)

        try:
            employees = self.data.get_all_employees()
        except Exception as e:
            CustomMessageBox(self, "Ошибка загрузки", f"Не удалось загрузить сотрудников: {e}", "warning").exec_()
            employees = None

        if not employees:
            self.employees_table.setRowCount(0)
            self.employees_table.setSortingEnabled(True)
            return

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
            
            # ========== СТАТУС (QLabel для гарантированного CSS-цвета) ==========
            status = emp.get('status', 'активный')
            status_item = QTableWidgetItem(status)
            self.employees_table.setItem(row, 6, status_item)
            self.employees_table.setCellWidget(row, 6, self._create_status_widget(status))
            # ===================================================================

            # Кнопки действий (теперь в колонке 7)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout()
            actions_layout.setContentsMargins(0, 0, 0, 0)
            actions_layout.setSpacing(4)

            view_btn = IconLoader.create_icon_button('view', '', 'Просмотр', icon_size=12)
            view_btn.setFixedSize(20, 20)
            view_btn.setStyleSheet('''
                QPushButton {
                    background-color: #F8F9FA;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #f5f5f5;
                }
            ''')
            view_btn.clicked.connect(lambda checked, e=emp: self.view_employee(e))
            actions_layout.addWidget(view_btn)

            # Кнопка "Редактировать" (только для админов)
            if self.can_edit:
                edit_btn = IconLoader.create_icon_button('edit2', '', 'Редактировать', icon_size=12)
                edit_btn.setFixedSize(20, 20)
                edit_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #d4e4bc;
                        border: 1px solid #c0d4a8;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0d4a8;
                    }
                ''')
                edit_btn.clicked.connect(lambda checked, e=emp: self.edit_employee(e))
                actions_layout.addWidget(edit_btn)

            # Кнопка удаления — только для Руководителя студии
            if self.can_delete:
                delete_btn = IconLoader.create_icon_button('delete2', '', 'Удалить', icon_size=12)
                delete_btn.setFixedSize(20, 20)
                delete_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #FFE6E6;
                        border: 1px solid #FFCCCC;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #E74C3C;
                    }
                ''')
                delete_btn.clicked.connect(lambda checked, e=emp: self.delete_employee(e))
                actions_layout.addWidget(delete_btn)

            # Кнопка "Пригласить" — отправить welcome email + Telegram-ссылку
            if self.can_edit:
                invite_btn = IconLoader.create_icon_button('mail', '', 'Отправить приглашение', icon_size=12)
                invite_btn.setFixedSize(20, 20)
                invite_btn.setStyleSheet('''
                    QPushButton {
                        background-color: #E8F4FD;
                        border: 1px solid #B0D4F1;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #BDD9F2;
                    }
                    QPushButton:disabled {
                        background-color: #E8F4E8;
                        border: 1px solid #B0D4B0;
                    }
                ''')
                # Если telegram уже подключён — кнопка показывает статус, но остаётся активной
                if emp.get('telegram_user_id'):
                    invite_btn.setToolTip('Telegram подключён. Можно отправить повторное приглашение')
                invite_btn.clicked.connect(lambda checked, e=emp: self.send_invite(e))
                actions_layout.addWidget(invite_btn)

            actions_widget.setLayout(actions_layout)
            self.employees_table.setCellWidget(row, 7, actions_widget)

        self.employees_table.setSortingEnabled(True)

    @staticmethod
    def _create_status_widget(status):
        """Создать виджет статуса с цветом (CSS гарантирует цвет, в отличие от setForeground)"""
        color_map = {
            'активный': '#2E7D32',    # Зелёный
            'уволен': '#D32F2F',       # Красный
            'в резерве': '#F57F17',    # Тёмно-жёлтый
        }
        color = color_map.get(status, '#333333')
        label = QLabel(status)
        label.setStyleSheet(f"color: {color}; background-color: #FFFFFF; padding-left: 4px; font-weight: bold;")
        return label

    def _reload_employees(self, prefer_local=False):
        """Перезагрузить таблицу с сохранением текущего фильтра отдела.

        Args:
            prefer_local: Если True, читать из локальной БД (после локального сохранения,
                         чтобы не получить устаревшие данные с сервера).
        """
        if prefer_local:
            self.data.prefer_local = True
        try:
            self.load_employees(department=self.current_department)
        finally:
            if prefer_local:
                self.data.prefer_local = False

    def _refresh_dashboard(self):
        """Обновить дашборд после изменения данных"""
        mw = self.window()
        if hasattr(mw, 'refresh_current_dashboard'):
            mw.refresh_current_dashboard()

    def add_employee(self):
        """Открытие диалога добавления сотрудника"""
        from utils.permissions import _has_perm
        if not _has_perm(self.employee, self.api_client, 'employees.create'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на создание сотрудников.', 'error').exec_()
            return
        dialog = EmployeeDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            self._reload_employees(prefer_local=True)
            self._refresh_dashboard()
            
    def view_employee(self, employee_data):
        """Просмотр информации о сотруднике"""
        dialog = EmployeeDialog(self, employee_data, view_only=True)
        dialog.exec_()
    
    def edit_employee(self, employee_data):
        """Редактирование сотрудника"""
        
        # ========== ПРОВЕРКА ПРАВ ==========
        from utils.permissions import _has_perm
        admin_positions = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
        if not _has_perm(self.employee, self.api_client, 'access.admin'):
            if employee_data.get('position', '') in admin_positions:
                CustomMessageBox(
                    self,
                    'Доступ запрещен',
                    'У вас нет прав для редактирования сотрудников административного отдела.\n\n'
                    'Только администратор может редактировать эти должности.',
                    'warning'
                ).exec_()
                return
        # ===================================
        
        dialog = EmployeeDialog(self, employee_data)
        if dialog.exec_() == QDialog.Accepted:
            self._reload_employees(prefer_local=True)
            self._refresh_dashboard()

    def delete_employee(self, employee_data):
        """Удаление сотрудника"""
        from ui.custom_message_box import CustomQuestionBox
        from utils.permissions import _has_perm

        # Проверка права на удаление сотрудников
        if not _has_perm(self.employee, self.api_client, 'employees.delete'):
            CustomMessageBox(
                self,
                'Ошибка',
                'У вас недостаточно прав для удаления сотрудников.',
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

        # Проверяем наличие активных назначений у сотрудника
        active_warning = ''
        try:
            active_cards = self.data.get_employee_active_assignments(employee_data['id'])
            if active_cards:
                count = len(active_cards) if isinstance(active_cards, list) else 0
                if count > 0:
                    active_warning = f"\n\nВНИМАНИЕ: Сотрудник назначен на {count} активных стадий. При удалении назначения будут сброшены."
        except Exception:
            pass

        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            f"Вы уверены, что хотите удалить сотрудника {employee_data['full_name']}?{active_warning}"
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                self.data.delete_employee(employee_data['id'])

                CustomMessageBox(
                    self,
                    'Успех',
                    'Сотрудник успешно удален',
                    'success'
                ).exec_()

                self._reload_employees(prefer_local=True)
                self._refresh_dashboard()

            except Exception as e:
                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить сотрудника: {str(e)}',
                    'error'
                ).exec_()

    def send_invite(self, employee):
        """Отправить приглашение сотруднику (welcome email + Telegram deep link)"""
        emp_id = employee.get('id')
        emp_name = employee.get('full_name', 'Сотрудник')
        emp_email = employee.get('email', '')

        if not emp_email:
            CustomMessageBox(
                self, 'Нет email',
                f'Email сотрудника {emp_name} не заполнен.\nДобавьте email и повторите.',
                'warning'
            ).exec_()
            return

        try:
            result = self.data.send_employee_invite(emp_id)
            if result:
                CustomMessageBox(
                    self, 'Приглашение отправлено',
                    f'Письмо с данными для входа и ссылкой на Telegram бот отправлено на {emp_email}.',
                    'success'
                ).exec_()
            else:
                CustomMessageBox(
                    self, 'Ошибка',
                    'Не удалось отправить приглашение. Проверьте настройки SMTP в администрировании.',
                    'error'
                ).exec_()
        except Exception as e:
            CustomMessageBox(
                self, 'Ошибка',
                f'Ошибка отправки приглашения: {e}',
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

    def on_sync_update(self, updated_employees):
        """
        Обработчик обновления данных от SyncManager.
        Вызывается при изменении сотрудников другими пользователями.
        """
        try:
            # Проверяем, есть ли реальные изменения (не пустой список)
            if not updated_employees:
                return

            print(f"[SYNC] Получено обновление сотрудников: {len(updated_employees)} записей")
            # Обновляем из локальной БД (данные уже синхронизированы), не блокируя UI
            self._reload_employees(prefer_local=True)
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации сотрудников: {e}")

class EmployeeDialog(QDialog):
    def __init__(self, parent, employee_data=None, view_only=False):
        super().__init__(parent)
        self.employee_data = employee_data
        self.view_only = view_only
        self.data = getattr(parent, 'data', DataAccess())
        self.db = self.data.db
        self.api_client = self.data.api_client

        # ========== НОВОЕ: ПРОВЕРКА ПРАВ ==========
        self.current_user = parent.employee  # Получаем текущего пользователя
        self.api_client = getattr(parent, 'api_client', None)
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
                border: none;
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

        # ========== ФИЛЬТРУЕМ ДОЛЖНОСТИ — ТОЛЬКО АДМИН МОЖЕТ НАЗНАЧАТЬ АДМИНСКИЕ ==========
        from utils.permissions import _has_perm
        has_admin = _has_perm(self.current_user, self.api_client, 'access.admin')
        if not has_admin:
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

        if not has_admin:
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
        self.phone.setPlaceholderText('+7 (XXX) XXX-XX-XX')
        self.phone.textChanged.connect(self.format_phone)
        self.phone.focusInEvent = lambda e: self.on_phone_focus_in(self.phone, e)
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
            self.password.setPlaceholderText('Минимум 6 символов, буква + цифра')
            login_layout.addRow('Пароль*:', self.password)
        
        self.password_confirm = QLineEdit()
        self.password_confirm.setEchoMode(QLineEdit.Password)
        self.password_confirm.setPlaceholderText('Повторите пароль')
        login_layout.addRow('Подтверждение:', self.password_confirm)
        
        login_group.setLayout(login_layout)
        layout.addWidget(login_group)
        
        # Кнопка "Администрирование" — по праву access.admin
        if not self.view_only:
            from utils.permissions import _has_perm
            if _has_perm(self.current_user, self.api_client, 'access.admin'):
                admin_btn = QPushButton('Администрирование')
                admin_btn.setStyleSheet("""
                    QPushButton {
                        padding: 8px 20px; color: #FFFFFF;
                        background-color: #7B1FA2; border-radius: 4px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #6A1B9A; }
                """)
                admin_btn.clicked.connect(self._open_admin_dialog)
                layout.addWidget(admin_btn)

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
        """Форматирование телефона +7 (XXX) XXX-XX-XX"""
        self.phone.blockSignals(True)

        # Если поле пустое, оставляем пустым (для placeholder)
        if not text:
            self.phone.blockSignals(False)
            return

        cursor_pos = self.phone.cursorPosition()

        # Извлекаем только цифры
        digits = ''.join(filter(str.isdigit, text))

        # Если нет цифр, очищаем поле
        if not digits:
            self.phone.setText('')
            self.phone.blockSignals(False)
            return

        # Подсчитываем сколько цифр было до курсора
        digits_before_cursor = len(''.join(filter(str.isdigit, text[:cursor_pos])))

        # Убираем первую 7 или 8, если пользователь её ввёл
        if digits.startswith('7') or digits.startswith('8'):
            digits = digits[1:]

        # Ограничиваем 10 цифрами (код города + номер)
        digits = digits[:10]

        # Форматируем номер: +7 (XXX) XXX-XX-XX
        if len(digits) == 0:
            formatted = '+7 ('
            new_cursor_pos = 4
        elif len(digits) <= 3:
            formatted = f'+7 ({digits}'
            new_cursor_pos = 4 + len(digits)
        elif len(digits) <= 6:
            formatted = f'+7 ({digits[:3]}) {digits[3:]}'
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            else:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
        elif len(digits) <= 8:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}'
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            else:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
        else:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}'
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            elif digits_before_cursor <= 8:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
            else:
                new_cursor_pos = 16 + (digits_before_cursor - 8)

        self.phone.setText(formatted)
        self.phone.setCursorPosition(min(new_cursor_pos, len(formatted)))

        self.phone.blockSignals(False)

    def on_phone_focus_in(self, line_edit, event):
        """При фокусе на поле телефона начинаем с префикса +7 ("""
        from PyQt5.QtWidgets import QLineEdit
        QLineEdit.focusInEvent(line_edit, event)

        # Если поле пустое, ставим начальный префикс
        if not line_edit.text().strip():
            line_edit.setText('+7 (')
            line_edit.setCursorPosition(4)

    def _open_permissions_dialog(self):
        """Открыть диалог управления правами доступа"""
        if not self.employee_data or not self.data:
            return
        dlg = PermissionsDialog(self, self.employee_data, self.data)
        dlg.exec_()

    def _open_admin_dialog(self):
        """Открыть диалог администрирования"""
        try:
            from ui.admin_dialog import AdminDialog
            data_access = getattr(self.parent(), 'data', None) if self.parent() else None
            dlg = AdminDialog(
                parent=self,
                api_client=self.api_client,
                data_access=data_access,
                employee=self.current_user,
            )
            dlg.exec_()
        except Exception as e:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', f'Не удалось открыть администрирование: {e}', 'warning').exec_()

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
        from utils.permissions import _has_perm
        if not self.employee_data:
            if not _has_perm(self.current_user, self.api_client, 'employees.create'):
                CustomMessageBox(self, 'Ошибка', 'У вас нет прав на создание сотрудников.', 'error').exec_()
                return
        else:
            if not _has_perm(self.current_user, self.api_client, 'employees.update'):
                CustomMessageBox(self, 'Ошибка', 'У вас нет прав на редактирование сотрудников.', 'error').exec_()
                return
        if not self.full_name.text().strip() or not self.login.text().strip():
            CustomMessageBox(self, 'Ошибка', 'Заполните все обязательные поля (ФИО, Логин)', 'warning').exec_()
            return
        
        # Проверка пароля при создании
        if not self.employee_data:
            if not self.password.text().strip():
                CustomMessageBox(self, 'Ошибка', 'Введите пароль', 'warning').exec_()
                return
            
            if len(self.password.text()) < 6:
                CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать минимум 6 символов', 'warning').exec_()
                return
            if not any(c.isdigit() for c in self.password.text()):
                CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать хотя бы одну цифру', 'warning').exec_()
                return
            if not any(c.isalpha() for c in self.password.text()):
                CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать хотя бы одну букву', 'warning').exec_()
                return

            if self.password.text() != self.password_confirm.text():
                CustomMessageBox(self, 'Ошибка', 'Пароли не совпадают', 'warning').exec_()
                return
        else:
            # При редактировании пароль опционален
            if self.password.text().strip():
                if len(self.password.text()) < 6:
                    CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать минимум 6 символов', 'warning').exec_()
                    return
                if not any(c.isdigit() for c in self.password.text()):
                    CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать хотя бы одну цифру', 'warning').exec_()
                    return
                if not any(c.isalpha() for c in self.password.text()):
                    CustomMessageBox(self, 'Ошибка', 'Пароль должен содержать хотя бы одну букву', 'warning').exec_()
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
            'role': self.position.currentText(),  # role совпадает с position (нет отдельного UI-поля)
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
                    print(f"[WARN] СТАТУС ИЗМЕНЁН: '{old_status}' → '{new_status}'")
            # ================================================

            if self.employee_data:
                self.data.update_employee(self.employee_data['id'], employee_data)
            else:
                self.data.create_employee(employee_data)

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
                border: none;
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
        self.phone_input.setPlaceholderText('+7 (XXX) XXX-XX-XX')
        self.phone_input.textChanged.connect(self.format_phone_input)
        self.phone_input.focusInEvent = lambda e: self.on_phone_focus_in(self.phone_input, e)
        form_layout.addRow('Телефон:', self.phone_input)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText('example@mail.com')
        form_layout.addRow('Email:', self.email_input)
        
        self.login_input = QLineEdit()
        self.login_input.setPlaceholderText('ivanov')
        form_layout.addRow('Логин:', self.login_input)
        
        layout.addLayout(form_layout)
        
        buttons_layout = QHBoxLayout()
        
        search_btn = IconLoader.create_icon_button('search2', 'Найти', 'Выполнить поиск', icon_size=12)
        search_btn.clicked.connect(self.accept)
        search_btn.setStyleSheet('''
            QPushButton {
                padding: 10px 30px;
                font-weight: bold;
                background-color: #ffd93c;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        ''')
        
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить', 'Сбросить фильтры', icon_size=12)
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

        # Сбрасываем фильтр отдела на "Все отделы"
        parent_tab = self.parent()
        if hasattr(parent_tab, 'current_department'):
            parent_tab.current_department = None
            for btn in parent_tab.filter_buttons.values():
                btn.setChecked(False)
            parent_tab.filter_buttons['all'].setChecked(True)
        parent_tab.load_employees()

        CustomMessageBox(
            self,
            'Сброс',
            'Фильтры сброшены, показаны все сотрудники',
            'success'
        ).exec_()

    def format_phone_input(self, text):
        """Форматирование телефона +7 (XXX) XXX-XX-XX"""
        self.phone_input.blockSignals(True)

        if not text:
            self.phone_input.blockSignals(False)
            return

        cursor_pos = self.phone_input.cursorPosition()
        digits = ''.join(filter(str.isdigit, text))

        if not digits:
            self.phone_input.setText('')
            self.phone_input.blockSignals(False)
            return

        digits_before_cursor = len(''.join(filter(str.isdigit, text[:cursor_pos])))

        if digits.startswith('7') or digits.startswith('8'):
            digits = digits[1:]

        digits = digits[:10]

        if len(digits) == 0:
            formatted = '+7 ('
            new_cursor_pos = 4
        elif len(digits) <= 3:
            formatted = f'+7 ({digits}'
            new_cursor_pos = 4 + len(digits)
        elif len(digits) <= 6:
            formatted = f'+7 ({digits[:3]}) {digits[3:]}'
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            else:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
        elif len(digits) <= 8:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:]}'
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            else:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
        else:
            formatted = f'+7 ({digits[:3]}) {digits[3:6]}-{digits[6:8]}-{digits[8:]}'
            if digits_before_cursor <= 3:
                new_cursor_pos = 4 + digits_before_cursor
            elif digits_before_cursor <= 6:
                new_cursor_pos = 9 + (digits_before_cursor - 3)
            elif digits_before_cursor <= 8:
                new_cursor_pos = 13 + (digits_before_cursor - 6)
            else:
                new_cursor_pos = 16 + (digits_before_cursor - 8)

        self.phone_input.setText(formatted)
        self.phone_input.setCursorPosition(min(new_cursor_pos, len(formatted)))

        self.phone_input.blockSignals(False)

    def on_phone_focus_in(self, line_edit, event):
        """При фокусе на поле телефона начинаем с префикса +7 ("""
        from PyQt5.QtWidgets import QLineEdit
        QLineEdit.focusInEvent(line_edit, event)

        # Если поле пустое, ставим начальный префикс
        if not line_edit.text().strip():
            line_edit.setText('+7 (')
            line_edit.setCursorPosition(4)

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


class PermissionsDialog(QDialog):
    """Диалог управления правами доступа сотрудника"""

    PERMISSION_GROUPS = {
        'Сотрудники': ['employees.create', 'employees.update', 'employees.delete'],
        'Клиенты': ['clients.delete'],
        'Договоры': ['contracts.delete'],
        'CRM': [
            'crm_cards.update', 'crm_cards.move', 'crm_cards.delete',
            'crm_cards.assign_executor', 'crm_cards.delete_executor',
            'crm_cards.reset_stages', 'crm_cards.reset_approval',
            'crm_cards.complete_approval', 'crm_cards.reset_designer',
            'crm_cards.reset_draftsman',
        ],
        'Надзор': [
            'supervision.update', 'supervision.move', 'supervision.pause_resume',
            'supervision.reset_stages', 'supervision.complete_stage',
            'supervision.delete_order',
        ],
        'Платежи': ['payments.delete'],
        'Зарплаты': ['salaries.delete'],
        'Агенты': ['agents.create'],
        'Мессенджер': ['messenger.create_chat', 'messenger.delete_chat', 'messenger.view_chat'],
    }

    def __init__(self, parent, employee_data, data_access):
        super().__init__(parent)
        self.employee_data = employee_data
        self.data = data_access
        self.checkboxes = {}
        self.definitions = {}

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMinimumWidth(550)

        self._init_ui()
        self._load_data()

    def _init_ui(self):
        emp_name = self.employee_data.get('full_name', '')
        title = f'Права доступа: {emp_name}'

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

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

        content_widget = QWidget()
        content_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

        content_layout = QVBoxLayout()
        content_layout.setSpacing(10)
        content_layout.setContentsMargins(20, 15, 20, 15)

        self.info_label = QLabel('')
        self.info_label.setStyleSheet('color: #757575; font-size: 12px;')
        content_layout.addWidget(self.info_label)

        from PyQt5.QtWidgets import QScrollArea
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMaximumHeight(400)
        scroll.setStyleSheet('QScrollArea { border: none; }')

        scroll_content = QWidget()
        groups_layout = QVBoxLayout()
        groups_layout.setSpacing(8)

        for group_name, perm_names in self.PERMISSION_GROUPS.items():
            group_box = QGroupBox(group_name)
            group_layout = QVBoxLayout()
            group_layout.setSpacing(4)

            for perm_name in perm_names:
                cb = QCheckBox(perm_name)
                cb.setProperty('perm_name', perm_name)
                self.checkboxes[perm_name] = cb
                group_layout.addWidget(cb)

            group_box.setLayout(group_layout)
            groups_layout.addWidget(group_box)

        scroll_content.setLayout(groups_layout)
        scroll.setWidget(scroll_content)
        content_layout.addWidget(scroll)

        buttons_layout = QHBoxLayout()

        reset_btn = QPushButton('По умолчанию')
        reset_btn.setStyleSheet('padding: 8px 20px;')
        reset_btn.clicked.connect(self._reset_to_defaults)
        buttons_layout.addWidget(reset_btn)

        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet('padding: 8px 20px; font-weight: bold;')
        save_btn.clicked.connect(self._save_permissions)
        buttons_layout.addWidget(save_btn)

        cancel_btn = QPushButton('Закрыть')
        cancel_btn.setStyleSheet('padding: 8px 20px;')
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)

        content_layout.addLayout(buttons_layout)

        content_widget.setLayout(content_layout)
        border_layout.addWidget(content_widget)
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

    def _load_data(self):
        """Загрузить определения прав и текущие права сотрудника"""
        try:
            defs = self.data.get_permission_definitions()
            if isinstance(defs, list):
                self.definitions = {d['name']: d['description'] for d in defs}

            for perm_name, cb in self.checkboxes.items():
                desc = self.definitions.get(perm_name, perm_name)
                cb.setText(desc)

            emp_id = self.employee_data.get('id')
            result = self.data.get_employee_permissions(emp_id)
            if isinstance(result, dict):
                current_perms = result.get('permissions', [])
                is_superuser = result.get('is_superuser', False)

                if is_superuser:
                    self.info_label.setText('Системный пользователь — все права включены, изменение невозможно')
                    for cb in self.checkboxes.values():
                        cb.setChecked(True)
                        cb.setEnabled(False)
                else:
                    self.info_label.setText(f'Роль: {self.employee_data.get("position", "")}')
                    for perm_name, cb in self.checkboxes.items():
                        cb.setChecked(perm_name in current_perms)

        except Exception as e:
            print(f"[PermissionsDialog] Ошибка загрузки прав: {e}")
            self.info_label.setText(f'Ошибка загрузки: {str(e)}')

    def _save_permissions(self):
        """Сохранить выбранные права"""
        try:
            emp_id = self.employee_data.get('id')
            selected = [name for name, cb in self.checkboxes.items() if cb.isChecked()]
            result = self.data.set_employee_permissions(emp_id, selected)
            if result:
                CustomMessageBox(self, 'Успешно', 'Права доступа сохранены', 'info').exec_()
                self.accept()
        except Exception as e:
            print(f"[PermissionsDialog] Ошибка сохранения прав: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {str(e)}', 'warning').exec_()

    def _reset_to_defaults(self):
        """Сбросить права до дефолтных по роли"""
        try:
            emp_id = self.employee_data.get('id')
            self.data.reset_employee_permissions(emp_id)
            self._load_data()
            CustomMessageBox(self, 'Успешно', 'Права сброшены по умолчанию', 'info').exec_()
        except Exception as e:
            print(f"[PermissionsDialog] Ошибка сброса прав: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось сбросить: {str(e)}', 'warning').exec_()
