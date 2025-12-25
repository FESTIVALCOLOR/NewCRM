# -*- coding: utf-8 -*-
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,

                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QDateEdit,
                             QListWidget, QListWidgetItem, QTabWidget, QTextEdit,
                             QGroupBox, QSpinBox, QTableWidget, QHeaderView,
                             QTableWidgetItem, QDoubleSpinBox)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QMimeData, QDate, pyqtSignal, QSize, QUrl, QTimer
from PyQt5.QtGui import QDrag, QPixmap, QColor, QCursor
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import (QTextDocument, QTextCursor, QTextTableFormat,
                         QTextCharFormat, QFont, QBrush,
                         QTextBlockFormat, QTextLength, QTextImageFormat)
from database.db_manager import DatabaseManager
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_combobox import CustomComboBox
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from utils.calendar_styles import CALENDAR_STYLE, add_today_button_to_dateedit, ICONS_PATH
from utils.tab_helpers import disable_wheel_on_tabwidget
from utils.date_utils import format_date, format_month_year
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
from utils.resource_path import resource_path
from functools import partial
import json
import os
import threading

class DraggableListWidget(QListWidget):
    """Кастомный QListWidget с контролируемым Drag & Drop"""
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
            self.setAcceptDrops(False)
            self.setDragEnabled(False)
        
        self.setSelectionMode(QListWidget.SingleSelection)
        
        print(f"[DraggableListWidget] Создан для колонки '{parent_column.column_name}', can_drag={can_drag}")
    
    def startDrag(self, supportedActions):
        """Начало перетаскивания"""
        if not self.can_drag:
            return
        
        item = self.currentItem()
        if item:
            card_id = item.data(Qt.UserRole)
            print(f"\n[DRAG START] Карточка ID={card_id} из колонки '{self.parent_column.column_name}'")
        
        super().startDrag(supportedActions)
    
    def dropEvent(self, event):
        """Обработка drop"""
        if not self.can_drag:
            event.ignore()
            return
        
        source = event.source()
        
        print(f"\n[DROP EVENT] На QListWidget колонки '{self.parent_column.column_name}'")
        print(f"             Источник: {type(source).__name__}")
        
        if not isinstance(source, DraggableListWidget):
            print(f"   Источник не DraggableListWidget")
            event.ignore()
            return
        
        item = source.currentItem()
        if not item:
            print(f"   Нет текущего элемента")
            event.ignore()
            return
        
        card_id = item.data(Qt.UserRole)
        print(f"  ✓ ID карточки: {card_id}")
        
        source_column = source.parent_column
        target_column = self.parent_column
        
        print(f"  ✓ Из колонки: '{source_column.column_name}'")
        print(f"  ✓ В колонку: '{target_column.column_name}'")
        
        if source_column == target_column:
            print(f"  → Та же колонка, стандартное перемещение")
            super().dropEvent(event)
            event.accept()
            return
        
        print(f"  → Разные колонки, испускаем сигнал")
        
        source_column.card_moved.emit(
            card_id,
            source_column.column_name,
            target_column.column_name,
            source_column.project_type
        )
        
        event.accept()
            
class CRMTab(QWidget):
    def __init__(self, employee, can_edit=True, api_client=None):
        super().__init__()
        self.employee = employee
        self.can_edit = can_edit
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.db = DatabaseManager()

        self.init_ui()
        self.load_cards_for_current_tab()
   
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(5, 5, 5, 5)
        
        # Заголовок и кнопка статистики
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        header = QLabel('CRM - Управление проектами')
        header.setStyleSheet('font-size: 14px; font-weight: bold; padding: 5px;')
        header_layout.addWidget(header)
        
        header_layout.addStretch(1)
        
        # ========== КНОПКА СТАТИСТИКИ (SVG) ==========
        if self.employee['position'] not in ['Дизайнер', 'Чертёжник', 'Замерщик']:
            stats_btn = IconLoader.create_icon_button('stats', 'Статистика CRM', 'Показать статистику проектов', icon_size=16)
            stats_btn.setStyleSheet("""
                QPushButton {
                    background-color: #27AE60;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    margin-top: 0px;
                    border-radius: 4px;
                    font-size: 13px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #229954; }
                QPushButton:pressed { background-color: #1E8449; }
            """)
            stats_btn.setFixedWidth(180)
            stats_btn.clicked.connect(self.show_statistics_current_tab)
            header_layout.addWidget(stats_btn)
        # =============================================
        
        main_layout.addLayout(header_layout)
        
        # Вкладки для типов проектов
        self.project_tabs = QTabWidget()
        self.project_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #CCCCCC;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background-color: #E8E8E8;
                min-width: 180px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 2px solid white;
            }
            QTabBar::tab:hover {
                background-color: #F0F0F0;
            }
        """)
        
        # === ИНДИВИДУАЛЬНЫЕ ПРОЕКТЫ ===
        individual_main_widget = QWidget()
        individual_main_layout = QVBoxLayout()
        individual_main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.individual_subtabs = QTabWidget()
        self.individual_subtabs.setStyleSheet("""
            QTabBar::tab {
                padding: 4px 16px;
                font-size: 11px;
            }
        """)
        
        self.individual_widget = self.create_crm_board('Индивидуальный')
        self.individual_subtabs.addTab(self.individual_widget, 'Активные проекты')

        if self.employee['position'] not in ['Дизайнер', 'Чертёжник', 'Замерщик']:
            self.individual_archive_widget = self.create_archive_board('Индивидуальный')
            self.individual_subtabs.addTab(self.individual_archive_widget, 'Архив (0)')
        
        individual_main_layout.addWidget(self.individual_subtabs)
        individual_main_widget.setLayout(individual_main_layout)
        
        self.project_tabs.addTab(individual_main_widget, 'Индивидуальные проекты')
        
        # === ШАБЛОННЫЕ ПРОЕКТЫ ===
        if self.employee['position'] != 'Дизайнер':
            template_main_widget = QWidget()
            template_main_layout = QVBoxLayout()
            template_main_layout.setContentsMargins(0, 0, 0, 0)
            
            self.template_subtabs = QTabWidget()
            self.template_subtabs.setStyleSheet("""
                QTabBar::tab {
                    padding: 4px 16px;
                    font-size: 11px;
                }
            """)
            
            self.template_widget = self.create_crm_board('Шаблонный')
            self.template_subtabs.addTab(self.template_widget, 'Активные проекты')

            if self.employee['position'] not in ['Дизайнер', 'Чертёжник', 'Замерщик']:
                self.template_archive_widget = self.create_archive_board('Шаблонный')
                self.template_subtabs.addTab(self.template_archive_widget, 'Архив (0)')
            
            template_main_layout.addWidget(self.template_subtabs)
            template_main_widget.setLayout(template_main_layout)
            
            self.project_tabs.addTab(template_main_widget, 'Шаблонные проекты')
            
        self.project_tabs.currentChanged.connect(self.on_tab_changed)
        
        main_layout.addWidget(self.project_tabs, 1)
        
        self.setLayout(main_layout)
        
    def update_project_tab_counters(self):
        """Обновление счетчиков в названиях вкладок проектов"""
        try:
            individual_count = 0
            if hasattr(self, 'individual_widget') and hasattr(self.individual_widget, 'columns'):
                for column in self.individual_widget.columns.values():
                    individual_count += column.cards_list.count()
            
            template_count = 0
            if hasattr(self, 'template_widget') and hasattr(self.template_widget, 'columns'):
                for column in self.template_widget.columns.values():
                    template_count += column.cards_list.count()
            
            individual_archive_count = 0
            if hasattr(self, 'individual_archive_widget') and hasattr(self.individual_archive_widget, 'archive_layout'):
                layout = self.individual_archive_widget.archive_layout
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item.widget() and isinstance(item.widget(), ArchiveCard):
                        individual_archive_count += 1
            
            template_archive_count = 0
            if hasattr(self, 'template_archive_widget') and hasattr(self.template_archive_widget, 'archive_layout'):
                layout = self.template_archive_widget.archive_layout
                for i in range(layout.count()):
                    item = layout.itemAt(i)
                    if item.widget() and isinstance(item.widget(), ArchiveCard):
                        template_archive_count += 1
            
            self.project_tabs.setTabText(0, f'Индивидуальные проекты ({individual_count})')
            
            if self.employee['position'] != 'Дизайнер':
                self.project_tabs.setTabText(1, f'Шаблонные проекты ({template_count})')
            
            if hasattr(self, 'individual_subtabs'):
                self.individual_subtabs.setTabText(0, f'Активные проекты ({individual_count})')
                
                if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                    self.individual_subtabs.setTabText(1, f'Архив ({individual_archive_count})')
            
            if hasattr(self, 'template_subtabs') and self.employee['position'] != 'Дизайнер':
                self.template_subtabs.setTabText(0, f'Активные проекты ({template_count})')
                
                if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                    self.template_subtabs.setTabText(1, f'Архив ({template_archive_count})')
            
            print(f"✓ Счетчики обновлены:")
            print(f"  • Индивидуальные активные: {individual_count}")
            print(f"  • Индивидуальные архив: {individual_archive_count}")
            print(f"  • Шаблонные активные: {template_count}")
            print(f"  • Шаблонные архив: {template_archive_count}")
            
        except Exception as e:
            print(f"⚠ Ошибка обновления счетчиков: {e}")
            import traceback
            traceback.print_exc()
         
    def show_statistics_current_tab(self):
        """Показ статистики для текущей вкладки"""
        current_index = self.project_tabs.currentIndex()
        if current_index == 0:
            self.show_crm_statistics('Индивидуальный')
        elif current_index == 1:
            self.show_crm_statistics('Шаблонный')
    
    def create_crm_board(self, project_type):
        """Создание доски CRM для типа проекта"""
        widget = QWidget()
        main_board_layout = QVBoxLayout()
        main_board_layout.setContentsMargins(0, 0, 0, 0)
        main_board_layout.setSpacing(0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll.setStyleSheet("QScrollArea { border: none; }")
        
        columns_widget = QWidget()
        columns_layout = QHBoxLayout()
        columns_layout.setSpacing(10)
        columns_layout.setContentsMargins(10, 10, 10, 10)
        
        if project_type == 'Индивидуальный':
            columns = [
                'Новый заказ',
                'В ожидании',
                'Стадия 1: планировочные решения',
                'Стадия 2: концепция дизайна',
                'Стадия 3: рабочие чертежи',
                'Выполненный проект'
            ]
        else:
            columns = [
                'Новый заказ',
                'В ожидании',
                'Стадия 1: планировочные решения',
                'Стадия 2: рабочие чертежи',
                'Выполненный проект'
            ]
        
        columns_dict = {}
        
        for column_name in columns:
            column = CRMColumn(column_name, project_type, self.employee, self.can_edit, self.db)
            column.card_moved.connect(self.on_card_moved)
            columns_dict[column_name] = column
            columns_layout.addWidget(column)
        
        widget.columns = columns_dict
        widget.project_type = project_type
        
        columns_widget.setLayout(columns_layout)
        scroll.setWidget(columns_widget)
        
        main_board_layout.addWidget(scroll, 1)
        widget.setLayout(main_board_layout)
        
        return widget
    
    def load_cards_for_current_tab(self):
        """Загрузка карточек для текущей активной вкладки"""
        current_index = self.project_tabs.currentIndex()
        if current_index == 0:
            self.load_cards_for_type('Индивидуальный')
            if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                self.load_archive_cards('Индивидуальный')
        elif current_index == 1:
            self.load_cards_for_type('Шаблонный')
            if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                self.load_archive_cards('Шаблонный')
                
    def load_cards_for_type(self, project_type):
        """Загрузка карточек для конкретного типа проекта"""
        print(f"\n=== ЗАГРУЗКА КАРТОЧЕК: {project_type} ===")
        
        try:
            cards = self.db.get_crm_cards_by_project_type(project_type)
            print(f"Получено из БД: {len(cards) if cards else 0} карточек")
            
            if project_type == 'Индивидуальный':
                board_widget = self.individual_widget
            else:
                board_widget = self.template_widget
            
            if not hasattr(board_widget, 'columns'):
                print(f" Нет атрибута columns")
                return
            
            columns_dict = board_widget.columns
            
            print("Очистка колонок:")
            for column in columns_dict.values():
                column.clear_cards()
            
            if cards:
                print("Добавление карточек:")
                for card_data in cards:
                    # ========== ЗАЩИТА ОТ БИТЫХ ДАННЫХ ==========
                    try:
                        if not self.should_show_card_for_employee(card_data):
                            print(f"  ⊘ Карточка ID={card_data.get('id')} скрыта")
                            continue
                        
                        column_name = card_data.get('column_name')
                        if column_name and column_name in columns_dict:
                            columns_dict[column_name].add_card(card_data)
                        else:
                            print(f"  ⚠ Колонка '{column_name}' не найдена!")
                            
                    except Exception as card_error:
                        print(f"   ОШИБКА при обработке карточки ID={card_data.get('id')}: {card_error}")
                        import traceback
                        traceback.print_exc()
                        # ПРОДОЛЖАЕМ загрузку остальных карточек
                        continue
                    # ============================================
            
            print("\n✓ Результат:")
            for column_name, column in columns_dict.items():
                count = column.cards_list.count()
                if count > 0:
                    print(f"  {column_name}: {count} карточек")
                    
            self.update_project_tab_counters()
            
            print(f"{'='*40}\n")
                    
        except Exception as e:
            print(f" КРИТИЧЕСКАЯ ОШИБКА: {e}")
            import traceback
            traceback.print_exc()
            
            # ========== АВАРИЙНОЕ СООБЩЕНИЕ ==========
            try:
                CustomMessageBox(
                    self, 
                    'Ошибка загрузки', 
                    f'Не удалось загрузить карточки:\n\n{str(e)}\n\n'
                    'Попробуйте перезапустить программу.\n'
                    'Если ошибка повторяется - обратитесь к администратору.', 
                    'error'
                ).exec_()
            except Exception:
                pass
            # =========================================
            
    def on_tab_changed(self, index):
        """Обработка переключения вкладок"""
        print(f"\n▶ Переключение на вкладку: {index}")
        if index == 0:
            self.load_cards_for_type('Индивидуальный')
            if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                self.load_archive_cards('Индивидуальный')
        elif index == 1:
            self.load_cards_for_type('Шаблонный')
            if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                self.load_archive_cards('Шаблонный')
    
    def on_card_moved(self, card_id, from_column, to_column, project_type):
        """Обработка перемещения карточки"""
        print(f"\n{'='*60}")
        print(f"🔄 ОБРАБОТКА ПЕРЕМЕЩЕНИЯ КАРТОЧКИ")
        print(f"   ID карточки: {card_id}")
        print(f"   Из колонки: '{from_column}'")
        print(f"   В колонку: '{to_column}'")
        print(f"   Тип проекта: {project_type}")
        print(f"{'='*60}")
        
        try:
            card_data = self.db.get_crm_card_data(card_id)
            
            if card_data:
                if 'концепция' in from_column and card_data.get('designer_completed') == 1:
                    QMessageBox.warning(
                        self, 
                        'Работа не принята', 
                        'Дизайнер сдал работу, но вы еще не приняли её!\n\n'
                        'Сначала нажмите кнопку "Принять работу" на карточке,\n'
                        'затем переместите её на следующую стадию.'
                    )
                    self.load_cards_for_type(project_type)
                    return
                
                if ('планировочные' in from_column or 'чертежи' in from_column) and card_data.get('draftsman_completed') == 1:
                    QMessageBox.warning(
                        self,
                        'Работа не принята',
                        'Чертёжник сдал работу, но вы еще не приняли её!\n\n'
                        'Сначала нажмите кнопку "Принять работу" на карточке,\n'
                        'затем переместите её на следующую стадию.'
                    )
                    self.load_cards_for_type(project_type)
                    return

                # ИСПРАВЛЕНИЕ: Проверка сдачи и принятия работы перед перемещением
                # Руководители могут перемещать свободно, автоматически принимая стадии
                if self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов']:
                    # Для руководителей: автоматически принимаем пропущенные стадии
                    if from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                        conn = self.db.connect()
                        cursor = conn.cursor()

                        # Получаем всех исполнителей данной стадии, которые еще не завершили работу
                        cursor.execute('''
                        SELECT se.executor_id, e.full_name as executor_name, e.position
                        FROM stage_executors se
                        JOIN employees e ON se.executor_id = e.id
                        WHERE se.crm_card_id = ? AND se.stage_name = ? AND se.completed = 0
                        ''', (card_id, from_column))

                        executors = cursor.fetchall()

                        if executors:
                            print(f"\n[AUTO ACCEPT] Автоматическое принятие стадии '{from_column}'")
                            print(f"             Найдено исполнителей: {len(executors)}")

                            # Получаем информацию о контракте для определения типа проекта
                            cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (card_id,))
                            card_row = cursor.fetchone()
                            contract_id = card_row['contract_id'] if card_row else None

                            contract = None
                            if contract_id:
                                cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
                                contract_row = cursor.fetchone()
                                contract = {'project_type': contract_row['project_type']} if contract_row else None

                            current_month = QDate.currentDate().toString('yyyy-MM')

                            # Обрабатываем каждого исполнителя
                            for executor in executors:
                                executor_id = executor['executor_id']
                                executor_name = executor['executor_name']
                                executor_position = executor['position']

                                print(f"  → Обработка: {executor_name} ({executor_position})")

                                # 1. Отмечаем стадию как сдану и принятую в stage_executors
                                cursor.execute('''
                                UPDATE stage_executors
                                SET submitted_date = CURRENT_TIMESTAMP,
                                    completed = 1,
                                    completed_date = CURRENT_TIMESTAMP
                                WHERE crm_card_id = ? AND stage_name = ? AND executor_id = ? AND completed = 0
                                ''', (card_id, from_column, executor_id))

                                # 2. Добавляем запись в manager_stage_acceptance (для информации о проекте)
                                cursor.execute('''
                                INSERT INTO manager_stage_acceptance
                                (crm_card_id, stage_name, executor_name, accepted_by)
                                VALUES (?, ?, ?, ?)
                                ''', (card_id, from_column, executor_name, self.employee['id']))

                                print(f"    ✓ Стадия отмечена как принятая")

                                # 3. Обновляем отчетный месяц в payments
                                if contract:
                                    # Для индивидуальных проектов - обновляем ДОПЛАТУ
                                    if contract['project_type'] == 'Индивидуальный':
                                        cursor.execute('''
                                        UPDATE payments
                                        SET report_month = ?
                                        WHERE contract_id = ?
                                          AND employee_id = ?
                                          AND stage_name = ?
                                          AND payment_type = 'Доплата'
                                        ''', (current_month, contract_id, executor_id, from_column))

                                        if cursor.rowcount > 0:
                                            print(f"    ✓ Отчетный месяц ДОПЛАТЫ установлен: {current_month}")

                                    # Для шаблонных проектов - обновляем ПОЛНУЮ ОПЛАТУ
                                    elif contract['project_type'] == 'Шаблонный':
                                        can_set_month = True

                                        # Для чертежника проверяем количество принятых стадий
                                        if 'чертёжник' in executor_position.lower() or 'чертежник' in executor_position.lower():
                                            cursor.execute('''
                                            SELECT COUNT(*) as accepted_count
                                            FROM manager_stage_acceptance
                                            WHERE crm_card_id = ? AND executor_name = ?
                                            ''', (card_id, executor_name))

                                            result = cursor.fetchone()
                                            accepted_count = result['accepted_count'] if result else 0

                                            # Если это первая стадия, НЕ устанавливаем месяц
                                            if accepted_count < 2:
                                                can_set_month = False
                                                print(f"     Первая стадия чертежника - месяц НЕ устанавливается")

                                        if can_set_month:
                                            cursor.execute('''
                                            UPDATE payments
                                            SET report_month = ?
                                            WHERE contract_id = ?
                                              AND employee_id = ?
                                              AND stage_name = ?
                                              AND payment_type = 'Полная оплата'
                                            ''', (current_month, contract_id, executor_id, from_column))

                                            if cursor.rowcount > 0:
                                                print(f"    ✓ Отчетный месяц ПОЛНОЙ ОПЛАТЫ установлен: {current_month}")

                            print(f"✓ Стадия '{from_column}' автоматически принята для {len(executors)} исполнителей")

                        conn.commit()
                        self.db.close()
                # ГАП/СДП/Менеджер могут перемещать если работа сдана, принята и согласована
                elif self.employee['position'] in ['ГАП', 'СДП', 'Менеджер']:
                    if from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                        # Проверяем что работа сдана, принята и согласована
                        conn = self.db.connect()
                        cursor = conn.cursor()

                        # Проверяем состояние выполнения стадии
                        cursor.execute('''
                        SELECT submitted_date, completed
                        FROM stage_executors
                        WHERE crm_card_id = ? AND stage_name = ?
                        ORDER BY assigned_date DESC
                        LIMIT 1
                        ''', (card_id, from_column))

                        stage_info = cursor.fetchone()

                        # Проверяем согласование стадии
                        cursor.execute('''
                        SELECT is_approved
                        FROM approval_stages
                        WHERE crm_card_id = ? AND stage_name = ?
                        ''', (card_id, from_column))

                        approval_info = cursor.fetchone()
                        self.db.close()

                        # Определяем статусы
                        submitted = stage_info and stage_info['submitted_date'] is not None
                        completed = stage_info and stage_info['completed'] == 1
                        approved = approval_info and approval_info['is_approved'] == 1

                        # Проверяем все три условия
                        if not (submitted and completed and approved):
                            CustomMessageBox(
                                self,
                                'Перемещение запрещено',
                                f'<b>Невозможно переместить карточку!</b><br><br>'
                                f'Текущая стадия: <b>"{from_column}"</b><br><br>'
                                f'Для перемещения необходимо:<br>'
                                f'{"✓" if submitted else "✗"} Работа должна быть сдана исполнителем<br>'
                                f'{"✓" if completed else "✗"} Работа должна быть принята менеджером<br>'
                                f'{"✓" if approved else "✗"} Стадия должна быть отмечена как выполненная<br><br>'
                                f'<i>Сначала выполните все требования, затем переместите карточку.</i>',
                                'warning'
                            ).exec_()
                            self.load_cards_for_type(project_type)
                            return
                else:
                    # Для всех остальных пользователей: строгая проверка
                    if from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                        # Получаем информацию о текущей стадии
                        conn = self.db.connect()
                        cursor = conn.cursor()

                        cursor.execute('''
                        SELECT submitted_date, completed
                        FROM stage_executors
                        WHERE crm_card_id = ? AND stage_name = ?
                        ORDER BY assigned_date DESC
                        LIMIT 1
                        ''', (card_id, from_column))

                        stage_info = cursor.fetchone()
                        self.db.close()

                        if stage_info:
                            submitted = stage_info['submitted_date'] is not None
                            completed = stage_info['completed'] == 1

                            if not submitted or not completed:
                                CustomMessageBox(
                                    self,
                                    'Перемещение запрещено',
                                    f'<b>Невозможно переместить карточку!</b><br><br>'
                                    f'Текущая стадия: <b>"{from_column}"</b><br><br>'
                                    f'Для перемещения необходимо:<br>'
                                    f'{"✓" if submitted else "✗"} Работа должна быть сдана исполнителем<br>'
                                    f'{"✓" if completed else "✗"} Работа должна быть принята менеджером<br><br>'
                                    f'<i>Сначала выполните все требования, затем переместите карточку.</i>',
                                    'warning'
                                ).exec_()
                                self.load_cards_for_type(project_type)
                                return
        except Exception as e:
            print(f"⚠ Ошибка проверки принятия работы: {e}")

        try:
            self.db.update_crm_card_column(card_id, to_column)
            print(f"✓ БД обновлена успешно")
        except Exception as e:
            print(f" Ошибка обновления БД: {e}")
            QMessageBox.critical(self, 'Ошибка', f'Не удалось переместить карточку: {e}')
            return

        # ========== ИСПРАВЛЕННЫЙ БЛОК СБРОСА ==========
        # Полный сброс ТОЛЬКО при возврате из архива
        if from_column == 'Выполненный проект':
            try:
                print(f"🔄 Возврат из архива: полный сброс данных")
                self.db.reset_stage_completion(card_id)
                self.db.reset_approval_stages(card_id)
                self.db.update_crm_card(card_id, {
                    'deadline': None,
                    'is_approved': 0
                })
                print(f"✓ Карточка очищена для повторного прохождения")
            except Exception as e:
                print(f"⚠ Ошибка полного сброса: {e}")

        # При обычном перемещении - сбрасываем ТОЛЬКО отметки о сдаче
        elif to_column != from_column:
            try:
                self.db.reset_stage_completion(card_id)
                print(f"✓ Отметки о сдаче сброшены (согласования сохранены)")
            except Exception as e:
                print(f"⚠ Ошибка сброса отметок: {e}")
        # ==============================================

        # Сброс дедлайна (ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ)
        reset_deadline_columns = ['Новый заказ', 'Выполненный проект']
        if to_column in reset_deadline_columns:
            try:
                updates = {'deadline': None}
                self.db.update_crm_card(card_id, updates)
                print(f"✓ Дедлайн сброшен для колонки '{to_column}'")
            except Exception as e:
                print(f"⚠ Ошибка сброса дедлайна: {e}")
        
        if from_column == 'Новый заказ' and to_column != 'Выполненный проект':
            try:
                contract_id = self.db.get_contract_id_by_crm_card(card_id)
                self.db.update_contract(contract_id, {'status': 'В работе'})
                print(f"✓ Статус изменен на 'В работе'")
            except Exception as e:
                print(f"⚠ Ошибка установки статуса: {e}")
        
        if self.requires_executor_selection(to_column):
            print(f"⚠ Требуется выбор исполнителя для стадии '{to_column}'")
            self.select_executor(card_id, to_column, project_type)
        
        if to_column == 'Выполненный проект':
            print(f"✓ Проект перемещен в 'Выполненный проект' - открываем диалог завершения")
            dialog = ProjectCompletionDialog(self, card_id)
            if dialog.exec_() == QDialog.Accepted:
                self.load_cards_for_type(project_type)
                if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                    self.load_archive_cards(project_type)
            else:
                self.load_cards_for_type(project_type)
        else:
            print(f"\n🔄 Перезагрузка карточек...")
            self.load_cards_for_type(project_type)
        
        print(f"{'='*60}\n")
        
    def requires_executor_selection(self, column_name):
        """Проверка, требуется ли выбор исполнителя"""
        stage_columns = [
            'Стадия 1: планировочные решения',
            'Стадия 2: концепция дизайна',
            'Стадия 2: рабочие чертежи',
            'Стадия 3: рабочие чертежи'
        ]
        return column_name in stage_columns
    
    def select_executor(self, card_id, stage_name, project_type):
        """Диалог выбора исполнителя"""
        dialog = ExecutorSelectionDialog(self, card_id, stage_name, project_type)
        if dialog.exec_() != QDialog.Accepted:
            QMessageBox.warning(self, 'Внимание', 'Выберите исполнителя для стадии')
    
    def complete_project(self, card_id):
        """Завершение проекта"""
        dialog = ProjectCompletionDialog(self, card_id)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_current_tab()

    def show_crm_statistics(self, project_type):
        """Показ статистики CRM"""
        dialog = CRMStatisticsDialog(self, project_type, self.employee)
        dialog.exec_()
       
    def refresh_current_tab(self):
        """Обновление текущей активной вкладки"""
        current_index = self.project_tabs.currentIndex()
        if current_index == 0:
            self.load_cards_for_type('Индивидуальный')
            if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                self.load_archive_cards('Индивидуальный')
        elif current_index == 1:
            self.load_cards_for_type('Шаблонный')
            if self.employee['position'] not in ['Дизайнер', 'Чертёжник']:
                self.load_archive_cards('Шаблонный')
                
        self.update_project_tab_counters()
                
    def create_archive_board(self, project_type):
        """Создание архивной доски для типа проекта"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        archive_header = QLabel(f'Архив {project_type.lower()}ных проектов')
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

        toggle_btn = IconLoader.create_icon_button('arrow-down-circle', '', 'Развернуть фильтры', icon_size=16)
        toggle_btn.setFixedSize(24, 24)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover {
                background-color: #E8F4F8;
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
        year_spin.setFixedHeight(42)  # Фиксированная высота как у QComboBox
        year_spin.setStyleSheet(f"""
            QSpinBox {{
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                padding-left: 8px;
                padding-right: 8px;
                color: #333333;
                font-size: 12px;
            }}
            QSpinBox:hover {{
                border-color: #3498DB;
            }}
            QSpinBox::up-button,
            QSpinBox::down-button {{
                background-color: #F8F9FA;
                border: none;
                width: 20px;
                border-radius: 3px;
            }}
            QSpinBox::up-button:hover,
            QSpinBox::down-button:hover {{
                background-color: #E8F4F8;
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

        apply_btn = IconLoader.create_icon_button('check-square', 'Применить фильтры', icon_size=14)
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

        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить фильтры', icon_size=14)
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
            self.apply_archive_filters(project_type)

        apply_btn.clicked.connect(apply_filters)

        # Обработчик сброса фильтров
        def reset_filters():
            period_combo.setCurrentText('Все время')
            address_input.clear()
            city_combo.setCurrentIndex(0)
            agent_combo.setCurrentIndex(0)
            self.apply_archive_filters(project_type)

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
        self.load_archive_filter_data(project_type, city_combo, agent_combo)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

        cards_container = QWidget()
        from ui.flow_layout import FlowLayout
        self.archive_layout = FlowLayout()
        self.archive_layout.setSpacing(10)
        self.archive_layout.setContentsMargins(10, 10, 10, 10)

        cards_container.setLayout(self.archive_layout)
        scroll.setWidget(cards_container)

        layout.addWidget(scroll)

        widget.setLayout(layout)
        widget.project_type = project_type
        widget.archive_layout = self.archive_layout

        return widget
    
    def load_archive_cards(self, project_type):
        """Загрузка архивных карточек"""
        print(f"\n=== ЗАГРУЗКА АРХИВА: {project_type} ===")

        try:
            # Проверяем, есть ли виджет архива (для замерщиков его нет)
            if project_type == 'Индивидуальный':
                if not hasattr(self, 'individual_archive_widget'):
                    print("  Архив недоступен для текущей роли")
                    return
                archive_widget = self.individual_archive_widget
            else:
                if not hasattr(self, 'template_archive_widget'):
                    print("  Архив недоступен для текущей роли")
                    return
                archive_widget = self.template_archive_widget

            cards = self.db.get_archived_crm_cards(project_type)
            print(f"Получено из БД: {len(cards) if cards else 0} архивных карточек")

            archive_layout = archive_widget.archive_layout
            while archive_layout.count():
                child = archive_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            if cards:
                for card_data in cards:
                    print(f"  Добавление архивной карточки: ID={card_data.get('id')}, Статус={card_data.get('status')}")
                    archive_card = ArchiveCard(card_data, self.db, employee=self.employee)
                    archive_layout.addWidget(archive_card)
            else:
                empty_label = QLabel('Архив пуст')
                empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
                empty_label.setAlignment(Qt.AlignCenter)
                archive_layout.addWidget(empty_label)

            # Примечание: FlowLayout не поддерживает addStretch, карточки автоматически располагаются

            print(f"✓ Архив загружен: {len(cards) if cards else 0} карточек\n")
            
            self.update_project_tab_counters()
            
        except Exception as e:
            print(f" ОШИБКА загрузки архива: {e}")
            import traceback
            traceback.print_exc()

    def load_archive_filter_data(self, project_type, city_combo, agent_combo):
        """Загрузка данных для фильтров архива"""
        try:
            # Получаем все архивные карточки для заполнения фильтров
            cards = self.db.get_archived_crm_cards(project_type)

            # Собираем уникальные города
            cities = set()
            for card in cards:
                city = card.get('city')
                if city:
                    cities.add(city)

            # Добавляем города в комбобокс
            for city in sorted(cities):
                city_combo.addItem(city, city)

            # Получаем всех агентов из базы данных
            agents = self.db.get_all_agents()
            for agent in agents:
                agent_name = agent['name']
                agent_combo.addItem(agent_name, agent_name)

        except Exception as e:
            print(f" ОШИБКА загрузки данных фильтров: {e}")

    def apply_archive_filters(self, project_type):
        """Применение фильтров к архивным карточкам"""
        print(f"\n=== ПРИМЕНЕНИЕ ФИЛЬТРОВ К АРХИВУ: {project_type} ===")

        try:
            # Получаем виджет архива
            if project_type == 'Индивидуальный':
                archive_widget = self.individual_archive_widget
            else:
                archive_widget = self.template_archive_widget

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
            cards = self.db.get_archived_crm_cards(project_type)

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

                            if card_date.isValid():
                                card_year = card_date.year()
                                card_month = card_date.month()
                                card_quarter = (card_month - 1) // 3 + 1

                                if period == 'Год' and card_year != year:
                                    continue
                                elif period == 'Квартал' and (card_year != year or card_quarter != quarter):
                                    continue
                                elif period == 'Месяц' and (card_year != year or card_month != month):
                                    continue
                            else:
                                # Если дата невалидна, пропускаем
                                continue
                        except Exception:
                            # Если не удалось распарсить дату, пропускаем
                            continue
                    else:
                        # Если поле даты отсутствует, пропускаем
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
                    archive_card = ArchiveCard(card_data, self.db, employee=self.employee)
                    archive_layout.addWidget(archive_card)
            else:
                empty_label = QLabel('Нет карточек, соответствующих фильтрам')
                empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
                empty_label.setAlignment(Qt.AlignCenter)
                archive_layout.addWidget(empty_label)

            # Примечание: FlowLayout не поддерживает addStretch, карточки автоматически располагаются

            print(f"✓ Фильтрация завершена: {len(filtered_cards)} из {len(cards)} карточек\n")

        except Exception as e:
            print(f" ОШИБКА применения фильтров: {e}")
            import traceback
            traceback.print_exc()

    def should_show_card_for_employee(self, card_data):
        """Проверка, должен ли сотрудник видеть карточку"""
        position = self.employee.get('position', '')
        secondary_position = self.employee.get('secondary_position', '')
        employee_name = self.employee.get('full_name', '')
        employee_id = self.employee.get('id')
        column_name = card_data.get('column_name', '')
        project_type = card_data.get('project_type', '')
        
        print(f"\n  🔍 Проверка карточки ID={card_data.get('id')}:")
        print(f"     Должность: {position} | ID сотрудника: {employee_id}")
        print(f"     Колонка: '{column_name}' | Тип проекта: {project_type}")
        
        # ========== РУКОВОДИТЕЛЬ И СТАРШИЙ МЕНЕДЖЕР ВИДЯТ ВСЁ ==========
        if position in ['Руководитель студии', 'Старший менеджер проектов']:
            print(f"     ✓ Руководящая роль - показываем")
            return True
        
        # ========== НАЗНАЧЕННЫЙ МЕНЕДЖЕР (ДЛЯ ВСЕХ СТАДИЙ) ==========
        if position == 'Менеджер' or secondary_position == 'Менеджер':
            assigned_manager_id = card_data.get('manager_id')
            print(f"     Назначенный менеджер ID: {assigned_manager_id}")
            if assigned_manager_id == employee_id:
                print(f"     ✓ Назначен менеджером - показываем")
                return True
        
        # ========== НАЗНАЧЕННЫЙ ГАП ==========
        # ИСПРАВЛЕНИЕ: ГАП видит ВСЕ карточки, на которые назначен (не только на определенных стадиях)
        if position == 'ГАП' or secondary_position == 'ГАП':
            assigned_gap_id = card_data.get('gap_id')
            print(f"     Назначенный ГАП ID: {assigned_gap_id}")

            if assigned_gap_id == employee_id:
                print(f"     ✓ ГАП назначен на этот проект - показываем")
                return True

        # ========== НАЗНАЧЕННЫЙ СДП ==========
        # ИСПРАВЛЕНИЕ: СДП видит ВСЕ карточки, на которые назначен (не только на определенных стадиях)
        if position == 'СДП' or secondary_position == 'СДП':
            assigned_sdp_id = card_data.get('sdp_id')
            print(f"     Назначенный СДП ID: {assigned_sdp_id}")

            if assigned_sdp_id == employee_id:
                print(f"     ✓ СДП назначен на этот проект - показываем")
                return True
        
        # ========== ДИЗАЙНЕР (СУЩЕСТВУЮЩАЯ ЛОГИКА) ==========
        if position == 'Дизайнер' or secondary_position == 'Дизайнер':
            if column_name == 'Стадия 2: концепция дизайна':
                designer_name = card_data.get('designer_name')
                designer_completed = card_data.get('designer_completed', 0)
                
                print(f"     Назначен дизайнер: {designer_name}")
                print(f"     Работа завершена: {designer_completed == 1}")
                
                result = (designer_name == employee_name) and (designer_completed != 1)
                print(f"     Результат: {'✓ показываем' if result else '✗ скрываем'}")
                return result
        
        # ========== ЧЕРТЁЖНИК (СУЩЕСТВУЮЩАЯ ЛОГИКА) ==========
        if position == 'Чертёжник' or secondary_position == 'Чертёжник':
            if project_type == 'Индивидуальный':
                allowed_columns = ['Стадия 1: планировочные решения', 'Стадия 3: рабочие чертежи']
            else:
                allowed_columns = ['Стадия 1: планировочные решения', 'Стадия 2: рабочие чертежи']

            if column_name in allowed_columns:
                draftsman_name = card_data.get('draftsman_name')
                draftsman_completed = card_data.get('draftsman_completed', 0)

                print(f"     Назначен чертёжник: {draftsman_name}")
                print(f"     Работа завершена: {draftsman_completed == 1}")

                result = (draftsman_name == employee_name) and (draftsman_completed != 1)
                print(f"     Результат: {'✓ показываем' if result else '✗ скрываем'}")
                return result

        # ========== ЗАМЕРЩИК ==========
        if position == 'Замерщик' or secondary_position == 'Замерщик':
            assigned_surveyor_id = card_data.get('surveyor_id')
            print(f"     Назначенный замерщик ID: {assigned_surveyor_id}")

            # Замерщик видит только карточки, где он назначен замерщиком И замер НЕ загружен
            if assigned_surveyor_id == employee_id:
                # Проверяем, загружен ли файл замера
                has_measurement = card_data.get('measurement_image_link') or card_data.get('survey_date')
                print(f"     Замер загружен: {bool(has_measurement)}")

                if not has_measurement:
                    print(f"     ✓ Назначен замерщиком и замер НЕ загружен - показываем")
                    return True
                else:
                    print(f"     ✗ Замер уже загружен - скрываем")
                    return False

        print(f"     ✗ Условия не выполнены - скрываем")
        return False
        
class CRMColumn(QFrame):
    card_moved = pyqtSignal(int, str, str, str)
    
    def __init__(self, column_name, project_type, employee, can_edit, db):
        super().__init__()
        self.column_name = column_name
        self.project_type = project_type
        self.employee = employee
        self.can_edit = can_edit
        self.db = db
        self.header_label = None
        self.init_ui()
        
    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(300)
        self.setMaximumWidth(600)
        self.setStyleSheet("""
            CRMColumn {
                background-color: #F5F5F5;
                border: 1px solid #CCCCCC;
                border-radius: 5px;
            }
        """)
        
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.header_label = QLabel()
        self.header_label.setStyleSheet("""
            font-weight: bold;
            font-size: 13px;
            padding: 10px;
            background-color: #E8F4F8;
            border-radius: 3px;
        """)
        self.header_label.setWordWrap(True)
        self.update_header_count()
        layout.addWidget(self.header_label)
        
        can_drag = self.can_edit
        self.cards_list = DraggableListWidget(self, can_drag)
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
            QListWidget::item:selected {
                background-color: transparent;
                border: none;
            }
        """)
        
        self.cards_list.setFocusPolicy(Qt.NoFocus)
        self.cards_list.setSpacing(5)
        self.cards_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        
        layout.addWidget(self.cards_list, 1)
        self.setLayout(layout)
      
    def update_header_count(self):
        """Обновление счетчика карточек в заголовке"""
        count = self.cards_list.count() if hasattr(self, 'cards_list') else 0
        
        if count == 0:
            self.header_label.setText(self.column_name)
        else:
            self.header_label.setText(f"{self.column_name} ({count})")
    
    def add_card(self, card_data):
        """Добавление карточки в колонку"""
        card_id = card_data.get('id')
        print(f"  [ADD] Добавление в '{self.column_name}': ID={card_id}")
        
        # ========== ЗАЩИТА ОТ КРАША ==========
        try:
            card_widget = CRMCard(card_data, self.can_edit, self.db, self.employee)
            
            recommended_size = card_widget.sizeHint()
            exact_height = recommended_size.height()
            
            card_widget.setMinimumHeight(exact_height)
            
            item = QListWidgetItem()
            item.setData(Qt.UserRole, card_id)
            item.setSizeHint(QSize(200, exact_height + 10))
            
            self.cards_list.addItem(item)
            self.cards_list.setItemWidget(item, card_widget)
            
            self.cards_list.updateGeometry()
            self.update_header_count()
            
            print(f"       ✓ Карточка добавлена успешно (высота: {exact_height}px)")
            
        except Exception as e:
            print(f"   ОШИБКА создания карточки ID={card_id}: {e}")
            import traceback
            traceback.print_exc()
            
            # Создаем пустую заглушку, чтобы не ломать интерфейс
            try:
                error_widget = QLabel(f" Ошибка загрузки\nкарточки ID={card_id}")
                error_widget.setStyleSheet('''
                    background-color: #FADBD8;
                    border: 2px solid #E74C3C;
                    border-radius: 4px;
                    padding: 10px;
                    font-size: 10px;
                    color: #C0392B;
                ''')
                error_widget.setFixedHeight(80)
                
                item = QListWidgetItem()
                item.setData(Qt.UserRole, card_id)
                item.setSizeHint(QSize(200, 90))
                
                self.cards_list.addItem(item)
                self.cards_list.setItemWidget(item, error_widget)
                
                print(f"       → Добавлена заглушка об ошибке")
            except Exception:
                pass
        # ====================================
            
    def clear_cards(self):
        """Очистка всех карточек"""
        count = self.cards_list.count()
        self.cards_list.clear()
        
        self.update_header_count()
        
        print(f"  [CLEAR] '{self.column_name}': было {count}, стало {self.cards_list.count()}")

class CRMCard(QFrame):
    def __init__(self, card_data, can_edit, db, employee=None):
        super().__init__()
        self.card_data = card_data
        self.can_edit = can_edit
        self.db = db
        self.employee = employee
        
        # ========== ЗАЩИТА ==========
        try:
            self.init_ui()
        except Exception as e:
            print(f" ОШИБКА init_ui() для карточки ID={card_data.get('id')}: {e}")
            import traceback
            traceback.print_exc()
            
            # Создаем минимальный интерфейс
            self.setStyleSheet("background-color: #FADBD8; border: 2px solid #E74C3C;")
            layout = QVBoxLayout()
            error_label = QLabel(f" Ошибка отображения карточки\nID: {card_data.get('id')}")
            error_label.setStyleSheet("color: #C0392B; padding: 10px;")
            layout.addWidget(error_label)
            self.setLayout(layout)
        # ============================
        
    def calculate_working_days(self, start_date, end_date):
        """Подсчет рабочих дней между датами"""
        if start_date > end_date:
            return -self.calculate_working_days(end_date, start_date)
        
        working_days = 0
        current = start_date
        
        holidays = [
            QDate(2024, 1, 1), QDate(2024, 1, 2), QDate(2024, 1, 3),
            QDate(2024, 1, 4), QDate(2024, 1, 5), QDate(2024, 1, 6),
            QDate(2024, 1, 7), QDate(2024, 1, 8),
            QDate(2024, 2, 23), QDate(2024, 3, 8),
            QDate(2024, 5, 1), QDate(2024, 5, 9),
            QDate(2024, 6, 12), QDate(2024, 11, 4),
            QDate(2025, 1, 1), QDate(2025, 1, 2), QDate(2025, 1, 3),
            QDate(2025, 1, 4), QDate(2025, 1, 5), QDate(2025, 1, 6),
            QDate(2025, 1, 7), QDate(2025, 1, 8),
            QDate(2025, 2, 23), QDate(2025, 3, 8),
            QDate(2025, 5, 1), QDate(2025, 5, 9),
            QDate(2025, 6, 12), QDate(2025, 11, 4),
        ]
        
        while current <= end_date:
            day_of_week = current.dayOfWeek()
            is_holiday = current in holidays
            
            if day_of_week < 6 and not is_holiday:
                working_days += 1
            
            current = current.addDays(1)
        
        return working_days
    
    def sizeHint(self):
        """Рекомендуемый размер карточки"""
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')

        # Проверяем, является ли пользователь замерщиком
        is_surveyor = self.employee and self.employee.get('position') == 'Замерщик'

        # Для замерщика - компактная карточка
        if is_surveyor:
            height = 120  # Базовая высота: номер договора + адрес + площадь/город
            # Добавляем высоту для кнопки "Добавить замер"
            has_measurement = self.card_data.get('measurement_image_link') or self.card_data.get('survey_date')
            if not has_measurement:  # Убрали проверку can_edit, т.к. замерщик может добавлять замер всегда
                height += 45  # Высота кнопки
            return QSize(200, height)

        # Для остальных ролей - обычная логика
        height = 150

        employees_visible = True
        if hasattr(self, 'employees_container'):
            employees_visible = self.employees_container.isVisible()

        if employees_visible:
            employees_count = 0
            if self.card_data.get('senior_manager_name'):
                employees_count += 1
            if self.card_data.get('sdp_name'):
                employees_count += 1
            if self.card_data.get('gap_name'):
                employees_count += 1
            if self.card_data.get('manager_name'):
                employees_count += 1
            if self.card_data.get('surveyor_name'):
                employees_count += 1
            if self.card_data.get('designer_name'):
                employees_count += 1
            if self.card_data.get('draftsman_name'):
                employees_count += 1
            
            if employees_count > 0:
                height += 35 + (employees_count * 24)
        else:
            height += 35
        
        if self.card_data.get('tags'):
            height += 28
        
        if self.card_data.get('designer_deadline') or self.card_data.get('draftsman_deadline') or self.card_data.get('deadline'):
            height += 28
        
        if self.employee and self.employee.get('position') not in ['Дизайнер', 'Чертёжник']:
            if ('концепция дизайна' in current_column and self.card_data.get('designer_completed') == 1) or \
               (('планировочные' in current_column or 'чертежи' in current_column) and self.card_data.get('draftsman_completed') == 1):
                height += 60
                height += 38
        
        buttons_count = 0
        if self.employee:
            # Кнопка "Сдать работу" для дизайнеров/чертёжников
            if self.employee['position'] in ['Дизайнер', 'Чертёжник']:
                if self.is_assigned_to_current_user(self.employee):
                    buttons_count += 1
            # Кнопка "Редактирование карточки" для всех с правами редактирования
            if self.can_edit:
                buttons_count += 1

        if self.card_data.get('project_data_link'):
            buttons_count += 1

        # Кнопка "Дата замера" (только если дата НЕ установлена и есть права)
        if self.can_edit and not self.card_data.get('survey_date'):
            buttons_count += 1

        # Кнопка ТЗ (только если файл НЕ установлен и есть права)
        if self.can_edit and not self.card_data.get('tech_task_file'):
            buttons_count += 1

        if buttons_count > 0:
            height += 38 * buttons_count

        return QSize(200, min(height, 800))

    def get_work_status(self):
        """Определение статуса работы над карточкой"""
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')

        # Проверяем статус работы дизайнера (Стадия 2: концепция дизайна)
        if 'Стадия 2' in current_column and 'концепция' in current_column:
            designer_name = self.card_data.get('designer_name')
            designer_completed = self.card_data.get('designer_completed', 0)

            if designer_name and designer_completed == 0:
                # Дизайнер назначен, но еще не сдал работу
                return "В работе у исполнителя"

            if designer_completed == 1:
                # Дизайнер сдал, теперь проверяет СДП
                return "В работе у СДП"

        # Проверяем статус работы чертежника
        is_draftsman_column = False
        if project_type == 'Индивидуальный':
            is_draftsman_column = ('Стадия 1' in current_column and 'планировочные' in current_column) or \
                                  ('Стадия 3' in current_column and 'чертежи' in current_column)
        else:  # Шаблонный
            is_draftsman_column = ('Стадия 1' in current_column and 'планировочные' in current_column) or \
                                  ('Стадия 2' in current_column and 'чертежи' in current_column)

        if is_draftsman_column:
            draftsman_name = self.card_data.get('draftsman_name')
            draftsman_completed = self.card_data.get('draftsman_completed', 0)

            if draftsman_name and draftsman_completed == 0:
                # Чертежник назначен, но еще не сдал работу
                return "В работе у исполнителя"

            if draftsman_completed == 1:
                # Чертежник сдал, теперь проверяет ГАП
                return "В работе у ГАП"

        return None  # Нет активной работы

    def init_ui(self):
        self.setFrameShape(QFrame.Box)
        self.setLineWidth(1)
        self.setStyleSheet("""
            CRMCard {
                background-color: white;
                border: 2px solid #CCCCCC;
                border-radius: 8px;
            }
            CRMCard:hover {
                border: 2px solid #4A90E2;
                background-color: #F0F8FF;
            }
        """)
        
        self.setMinimumWidth(200)
        self.setMaximumWidth(600)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)
        
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')

        # ========== НОВОЕ: ВЕРХНЯЯ СТРОКА С НОМЕРОМ ДОГОВОРА И СТАТУСОМ ==========
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        top_row.setContentsMargins(0, 0, 0, 0)

        # 1. Номер договора (слева)
        contract_number = QLabel(f"Договор: {self.card_data.get('contract_number', 'N/A')}")
        contract_number.setStyleSheet('font-size: 10px; color: #888; background-color: transparent;')
        contract_number.setFixedHeight(16)
        top_row.addWidget(contract_number, 1)  # stretch factor 1 - растягивается

        # 2. Статус работы (справа) - только если карточка в работе у исполнителя/СДП/ГАП
        work_status = self.get_work_status()
        if work_status:
            status_label = QLabel(work_status)
            status_label.setStyleSheet('''
                background-color: white;
                color: #27AE60;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 6px;
                border: 2px solid #27AE60;
                border-radius: 3px;
            ''')
            status_label.setFixedHeight(20)
            status_label.setAlignment(Qt.AlignCenter)
            top_row.addWidget(status_label, 0)  # stretch factor 0 - не растягивается

        layout.addLayout(top_row)
        
        # 2. Адрес
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

        # 3. Площадь, город и тип агента на одной строке
        info_row = QHBoxLayout()
        info_row.setSpacing(8)
        info_row.setContentsMargins(0, 0, 0, 0)

        # Площадь и город
        info_parts = []
        if self.card_data.get('area'):
            info_parts.append(f"📐 {self.card_data['area']} м²")
        if self.card_data.get('city'):
            info_parts.append(f"📍 {self.card_data['city']}")

        if info_parts:
            info = QLabel(" | ".join(info_parts))
            info.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            info.setWordWrap(True)
            info_row.addWidget(info, 1)

        # Тип агента с цветом
        if self.card_data.get('agent_type'):
            agent_type = self.card_data['agent_type']
            agent_color = self.db.get_agent_color(agent_type)

            agent_label = QLabel(agent_type)
            agent_label.setFixedHeight(24)  # Фиксированная высота
            if agent_color:
                agent_label.setStyleSheet(f'''
                    background-color: {agent_color};
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 3px;
                    border: 2px solid {agent_color};
                ''')
            else:
                agent_label.setStyleSheet('''
                    background-color: #95A5A6;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 3px;
                    border: 2px solid #95A5A6;
                ''')
            agent_label.setAlignment(Qt.AlignCenter)
            info_row.addWidget(agent_label, 0)

        layout.addLayout(info_row)

        # Проверяем, является ли пользователь замерщиком
        is_surveyor = self.employee and self.employee.get('position') == 'Замерщик'

        # 4. СОТРУДНИКИ (СВОРАЧИВАЕМЫЕ) - скрываем для замерщика
        if not is_surveyor:
            employees_widget = self.create_collapsible_employees_section()
            if employees_widget:
                layout.addWidget(employees_widget, 0)

        # 5. Теги - скрываем для замерщика
        if not is_surveyor and self.card_data.get('tags'):
            tags_label = QLabel(f"🏷️ {self.card_data['tags']}")
            tags_label.setStyleSheet('''
                color: white;
                background-color: #FF6B6B;
                padding: 3px 8px;
                border-radius: 3px;
                font-size: 10px;
                font-weight: bold;
            ''')
            tags_label.setFixedHeight(28)
            layout.addWidget(tags_label, 0)

        # 6. Дедлайн - скрываем для замерщика
        if not is_surveyor:
            deadline_to_show = None

            if 'концепция дизайна' in current_column and self.card_data.get('designer_deadline'):
                deadline_to_show = self.card_data['designer_deadline']
            elif ('планировочные' in current_column or 'чертежи' in current_column) and self.card_data.get('draftsman_deadline'):
                deadline_to_show = self.card_data['draftsman_deadline']
            elif self.card_data.get('deadline'):
                deadline_to_show = self.card_data['deadline']

            if deadline_to_show:
                try:
                    deadline_date = QDate.fromString(deadline_to_show, 'yyyy-MM-dd')
                    current_date = QDate.currentDate()

                    # Форматируем дату для отображения в формате dd.MM.yyyy
                    deadline_display = deadline_date.toString('dd.MM.yyyy')

                    working_days = self.calculate_working_days(current_date, deadline_date)

                    if working_days < 0:
                        bg_color = '#8B0000'
                        text_color = 'white'
                        text = f"⏰ {deadline_display}  ПРОСРОЧЕН ({abs(working_days)} раб.дн.)"
                    elif working_days == 0:
                        bg_color = '#DC143C'
                        text_color = 'white'
                        text = f"⏰ {deadline_display}  СЕГОДНЯ!"
                    elif working_days <= 1:
                        bg_color = '#E74C3C'
                        text_color = 'white'
                        text = f"⏰ {deadline_display}  ({working_days} раб.дн.)"
                    elif working_days <= 2:
                        bg_color = '#F39C12'
                        text_color = 'white'
                        text = f"⏰ {deadline_display} ({working_days} раб.дн.)"
                    else:
                        bg_color = '#95A5A6'
                        text_color = 'white'
                        text = f"⏰ {deadline_display} ({working_days} раб.дн.)"

                    deadline_label = QLabel(text)
                    deadline_label.setStyleSheet(f'''
                        color: {text_color};
                        background-color: {bg_color};
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                    ''')
                    deadline_label.setFixedHeight(28)
                    layout.addWidget(deadline_label, 0)

                except Exception as e:
                    # В случае ошибки пытаемся преобразовать в нормальный формат
                    try:
                        deadline_date = QDate.fromString(deadline_to_show, 'yyyy-MM-dd')
                        deadline_display = deadline_date.toString('dd.MM.yyyy')
                    except:
                        deadline_display = deadline_to_show
                    deadline_label = QLabel(f"⏰ Дедлайн: {deadline_display}")
                    deadline_label.setStyleSheet('''
                        color: white;
                        background-color: #95A5A6;
                        padding: 3px 8px;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                    ''')
                    deadline_label.setFixedHeight(28)
                    layout.addWidget(deadline_label, 0)
                
        # ========== НОВЫЙ БЛОК ОТЛАДКИ (ДОБАВЬТЕ СЮДА) ==========
        print(f"\n{'='*60}")
        print(f"[CARD INIT] Карточка ID={self.card_data.get('id')}")
        print(f"{'='*60}")
        print(f"  Текущий сотрудник: {self.employee.get('full_name') if self.employee else 'НЕТ'}")
        print(f"  Должность: {self.employee.get('position') if self.employee else 'НЕТ'}")
        print(f"  Дополнительная: {self.employee.get('secondary_position', 'Нет') if self.employee else 'НЕТ'}")
        print(f"  Колонка карточки: '{current_column}'")
        print(f"  Дизайнер на карточке: '{self.card_data.get('designer_name', 'Не назначен')}'")
        print(f"  Чертёжник на карточке: '{self.card_data.get('draftsman_name', 'Не назначен')}'")
        print(f"  can_edit: {self.can_edit}")

        if self.employee:
            is_executor = self.employee.get('position') in ['Дизайнер', 'Чертёжник']
            print(f"  Является исполнителем: {is_executor}")
            
            if is_executor:
                print(f"\n  → Проверяем, назначен ли исполнитель...")
        else:
            print(f"   self.employee = None!")

        print(f"{'='*60}\n")
        # =========================================================                
        
        # 6.5. ИНДИКАТОР "РАБОТА СДАНА" + КНОПКА "ПРИНЯТЬ РАБОТУ"
        if self.employee and self.employee.get('position') not in ['Дизайнер', 'Чертёжник']:
            completed_info = []
            
            if 'концепция дизайна' in current_column and self.card_data.get('designer_completed') == 1:
                designer_name = self.card_data.get('designer_name', 'N/A')
                completed_info.append(f"Дизайнер {designer_name}")
            
            if ('планировочные' in current_column or 'чертежи' in current_column) and self.card_data.get('draftsman_completed') == 1:
                draftsman_name = self.card_data.get('draftsman_name', 'N/A')
                completed_info.append(f"Чертёжник {draftsman_name}")
            
            if completed_info:
                work_done_label = QLabel(f"Работа сдана: {', '.join(completed_info)}\n Требуется проверка и перемещение на следующую стадию")
                work_done_label.setWordWrap(True)
                work_done_label.setStyleSheet('''
                    color: white;
                    background-color: #27AE60;
                    padding: 8px 10px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                    border: 2px solid #1E8449;
                ''')
                work_done_label.setMaximumHeight(60)
                layout.addWidget(work_done_label, 0)
                
                # ========== КНОПКА "ПРИНЯТЬ РАБОТУ" (SVG) ==========
                accept_btn = IconLoader.create_icon_button('accept', 'Принять работу', 'Принять выполненную работу', icon_size=14)
                accept_btn.setStyleSheet("""
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
                accept_btn.setFixedHeight(32)
                accept_btn.clicked.connect(self.accept_work)
                layout.addWidget(accept_btn, 0)

        # 7. КНОПКИ
        buttons_added = False

        # Кнопка "Сдать работу" для дизайнеров/чертежников, назначенных на карточку
        if self.employee and self.employee.get('position') in ['Дизайнер', 'Чертёжник']:
            if self.is_assigned_to_current_user(self.employee):
                # ========== КНОПКА "СДАТЬ РАБОТУ" (SVG) ==========
                submit_btn = IconLoader.create_icon_button('submit', 'Сдать работу', 'Отметить работу как выполненную', icon_size=14)
                submit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        border: none;
                        padding: 8px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #229954; }
                    QPushButton:pressed { background-color: #1E8449; }
                """)
                submit_btn.setFixedHeight(38)
                submit_btn.clicked.connect(self.submit_work)
                layout.addWidget(submit_btn, 0)
                buttons_added = True

        # Кнопка "Редактирование карточки" для всех с правами редактирования (кроме замерщика)
        if self.can_edit and not is_surveyor:
            # ========== КНОПКА РЕДАКТИРОВАНИЯ (SVG) ==========
            edit_btn = IconLoader.create_icon_button('edit', 'Редактирование карточки', 'Редактировать данные карточки', icon_size=14)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #4A90E2;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #357ABD; }
                QPushButton:pressed { background-color: #2868A8; }
            """)
            edit_btn.setFixedHeight(38)
            edit_btn.clicked.connect(self.edit_card)
            layout.addWidget(edit_btn, 0)
            buttons_added = True

        # ========== КНОПКА "ДАННЫЕ ПРОЕКТА" (SVG) ==========
        if self.card_data.get('project_data_link'):
            data_btn = IconLoader.create_icon_button('folder', 'Данные проекта', 'Открыть папку проекта', icon_size=14)
            data_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498DB;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #2980B9; }
                QPushButton:pressed { background-color: #21618C; }
            """)
            data_btn.setFixedHeight(38)
            data_btn.clicked.connect(self.show_project_data)
            layout.addWidget(data_btn, 0)
            buttons_added = True

        # ========== КНОПКА "ДАТА ЗАМЕРА" ==========
        # Показываем кнопку только если замер НЕ загружен и есть права (для Руководителя, Старшего менеджера, Менеджера и Замерщика)
        # Проверяем как новое поле (measurement_image_link из contracts), так и старое (survey_date из crm_cards)
        has_measurement = self.card_data.get('measurement_image_link') or self.card_data.get('survey_date')
        is_surveyor = self.employee and self.employee.get('position') == 'Замерщик'
        can_add_measurement = self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер', 'Замерщик']
        # Для замерщика разрешаем добавлять замер без can_edit, для остальных требуется can_edit
        if not has_measurement and can_add_measurement and (self.can_edit or is_surveyor):
            survey_btn = IconLoader.create_icon_button('calendar-plus', 'Добавить замер', 'Установить дату замера', icon_size=14)
            survey_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F39C12;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #E67E22; }
                QPushButton:pressed { background-color: #D35400; }
            """)
            survey_btn.clicked.connect(self.add_survey_date)
            survey_btn.setFixedHeight(38)
            layout.addWidget(survey_btn, 0)
            buttons_added = True

        # ========== КНОПКА "ТЗ" ==========
        # Показываем кнопку только если ТЗ НЕ добавлено и есть права (только для Руководителя, Старшего менеджера и Менеджера)
        # Проверяем как новое поле (tech_task_link из contracts), так и старое (tech_task_file из crm_cards)
        # Кнопка "Добавить ТЗ" (не показываем замерщику)
        has_tech_task = self.card_data.get('tech_task_link') or self.card_data.get('tech_task_file')
        can_add_tech_task = self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']
        if self.can_edit and not has_tech_task and can_add_tech_task and not is_surveyor:
            tz_btn = IconLoader.create_icon_button('plus-circle', 'Добавить ТЗ', 'Добавить техническое задание', icon_size=14)
            tz_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9B59B6;
                    color: white;
                    border: none;
                    padding: 8px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover { background-color: #8E44AD; }
                QPushButton:pressed { background-color: #7D3C98; }
            """)
            tz_btn.clicked.connect(self.add_tech_task)
            tz_btn.setFixedHeight(38)
            layout.addWidget(tz_btn, 0)
            buttons_added = True

        self.setLayout(layout)
                
    def create_collapsible_employees_section(self):
        """Создание СВОРАЧИВАЕМОЙ секции с сотрудниками"""
        employees = []
        
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')
        
        highlight_role = self.get_highlight_role(current_column, project_type)
        
        if self.card_data.get('senior_manager_name'):
            employees.append(('👔 Ст.менеджер', self.card_data['senior_manager_name'], 'senior_manager', False))
        if self.card_data.get('sdp_name'):
            employees.append(('🎨 СДП', self.card_data['sdp_name'], 'sdp', False))
        if self.card_data.get('gap_name'):
            employees.append(('📋 ГАП', self.card_data['gap_name'], 'gap', False))
        if self.card_data.get('manager_name'):
            employees.append(('💼 Менеджер', self.card_data['manager_name'], 'manager', False))
        if self.card_data.get('surveyor_name'):
            employees.append(('📏 Замерщик', self.card_data['surveyor_name'], 'surveyor', False))
        
        if self.card_data.get('designer_name'):
            is_completed = self.card_data.get('designer_completed', 0) == 1
            employees.append(('🎨 Дизайнер', self.card_data['designer_name'], 'designer', is_completed))
        
        if self.card_data.get('draftsman_name'):
            is_completed = self.card_data.get('draftsman_completed', 0) == 1
            employees.append(('✏️ Чертёжник', self.card_data['draftsman_name'], 'draftsman', is_completed))
        
        if not employees:
            return None
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.team_toggle_btn = QPushButton(f"👥 Команда ({len(employees)})  ▶")
        self.team_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 5px;
                text-align: left;
                font-size: 10px;
                font-weight: bold;
                color: #555;
            }
            QPushButton:hover {
                background-color: #E8E9EA;
            }
        """)
        self.team_toggle_btn.setFixedHeight(30)
        self.team_toggle_btn.clicked.connect(self.toggle_team_section)

        main_layout.addWidget(self.team_toggle_btn)
        
        self.employees_container = QFrame()
        self.employees_container.setStyleSheet("""
            QFrame {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-top: none;
                border-bottom-left-radius: 4px;
                border-bottom-right-radius: 4px;
                padding: 4px;
            }
        """)
        
        employees_layout = QVBoxLayout()
        employees_layout.setSpacing(2)
        employees_layout.setContentsMargins(3, 3, 3, 3)
        
        # ========== ЦИКЛ С КНОПКАМИ ==========
        for role, name, role_key, is_completed in employees:
            # Создаем горизонтальный layout для строки
            employee_row_widget = QWidget()
            employee_row_layout = QHBoxLayout()
            employee_row_layout.setContentsMargins(0, 0, 0, 0)
            employee_row_layout.setSpacing(5)
            
            # Метка с именем сотрудника
            if is_completed:
                display_text = f"{role}: {name} "
            else:
                display_text = f"{role}: {name}"
            
            employee_label = QLabel(display_text)
            employee_label.setWordWrap(True)
            
            if is_completed:
                employee_label.setStyleSheet('''
                    font-size: 12px; 
                    color: #1B5E20; 
                    font-weight: bold;
                    background-color: #C8E6C9;
                    padding: 3px 5px;
                    border-radius: 3px;
                    border: 1px solid #81C784;
                ''')
            elif role_key == highlight_role:
                employee_label.setStyleSheet('''
                    font-size: 12px; 
                    color: #F57C00; 
                    font-weight: bold;
                    background-color: #FFE082;
                    padding: 3px 5px;
                    border-radius: 3px;
                    border: 1px solid #FFB74D;
                ''')
            else:
                employee_label.setStyleSheet('font-size: 10px; color: #444; background-color: transparent;')
            
            employee_row_layout.addWidget(employee_label, 1)
            
            # ========== КНОПКА "ПЕРЕНАЗНАЧИТЬ" ==========
            # Кнопка доступна только для управленческих ролей и только для дизайнеров/чертежников
            can_show_reassign = (
                self.employee and
                self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер', 'СДП', 'ГАП'] and
                role_key in ['designer', 'draftsman'] and
                self.can_edit and
                not is_completed
            )

            if can_show_reassign:
                print(f"  [DEBUG] Создаём кнопку переназначения для {role_key}")
                
                reassign_btn = QPushButton('🔄')
                reassign_btn.setToolTip('Переназначить исполнителя')
                reassign_btn.setFixedSize(26, 22)
                reassign_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 12px;
                        padding: 0px;
                    }
                    QPushButton:hover {
                        background-color: #F57C00;
                    }
                    QPushButton:pressed {
                        background-color: #E65100;
                    }
                    
                    /* ========== СВЕТЛАЯ ВСПЛЫВАЮЩАЯ ПОДСКАЗКА ========== */
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #333333;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                        padding: 5px 8px;
                        font-size: 11px;
                    }
                """)
                
                # Используем partial для передачи параметра
                reassign_btn.clicked.connect(partial(self.reassign_executor, role_key))
                
                employee_row_layout.addWidget(reassign_btn)
            
            employee_row_widget.setLayout(employee_row_layout)
            employees_layout.addWidget(employee_row_widget)
        # =====================================
        
        # ========== ВОТ ЭТА СТРОКА БЫЛА ПРОПУЩЕНА! ==========
        self.employees_container.setLayout(employees_layout)
        # ====================================================
        
        main_layout.addWidget(self.employees_container)
        
        self.employees_container.hide()
        
        main_widget.setLayout(main_layout)
        return main_widget
        
    def toggle_team_section(self):
        """Раскрытие/сворачивание секции команды"""
        is_visible = self.employees_container.isVisible()
        
        if is_visible:
            self.employees_container.hide()
            self.team_toggle_btn.setText(self.team_toggle_btn.text().replace('▼', '▶'))
            print("  🔽 Команда свернута")
        else:
            self.employees_container.show()
            self.team_toggle_btn.setText(self.team_toggle_btn.text().replace('▶', '▼'))
            print("  🔼 Команда развернута")
        
        self.update_card_height_immediately()
    
    def update_card_height_immediately(self):
        """Немедленное обновление высоты карточки БЕЗ прыганий"""
        new_height = self.sizeHint().height()
        
        print(f"  📏 Новая высота: {new_height}px")
        
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
                        print(f"  ✓ Item обновлен: {new_height + 10}px")
                        return
                break
            parent_widget = parent_widget.parent()
            
    def is_assigned_to_current_user(self, current_employee):
        """Проверка, назначен ли текущий пользователь исполнителем"""
        current_column = self.card_data.get('column_name', '')
        employee_name = current_employee.get('full_name', '')
        position = current_employee.get('position', '')
        secondary_position = current_employee.get('secondary_position', '')  # ← НОВОЕ
        
        print(f"  Проверка назначения:")
        print(f"    Колонка: {current_column}")
        print(f"    Основная должность: {position}")
        if secondary_position:
            print(f"    Дополнительная должность: {secondary_position}")
        print(f"    Имя сотрудника: {employee_name}")
        
        # ========== ДИЗАЙНЕР (ОСНОВНАЯ ИЛИ ДОПОЛНИТЕЛЬНАЯ) ==========
        if position == 'Дизайнер' or secondary_position == 'Дизайнер':
            designer_name = self.card_data.get('designer_name', '')
            print(f"    Назначенный дизайнер: {designer_name}")
            if 'концепция дизайна' in current_column:
                result = designer_name == employee_name
                print(f"    Результат: {result}")
                return result
        # =============================================================
        
        # ========== ЧЕРТЁЖНИК (ОСНОВНАЯ ИЛИ ДОПОЛНИТЕЛЬНАЯ) ==========
        if position == 'Чертёжник' or secondary_position == 'Чертёжник':
            draftsman_name = self.card_data.get('draftsman_name', '')
            print(f"    Назначенный чертёжник: {draftsman_name}")
            if 'планировочные' in current_column or 'чертежи' in current_column:
                result = draftsman_name == employee_name
                print(f"    Результат: {result}")
                return result
        # ==============================================================
        
        print(f"    Результат: False (условия не выполнены)")
        return False
    
    def submit_work(self):
        """Отметка о сдаче работы"""
        current_employee = self.employee
        if not current_employee:
            return
        
        current_column = self.card_data.get('column_name', '')
        
        # ========== ЗАМЕНИЛИ стандартный QDialog ==========
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            f'Подтвердить сдачу работы?\n\n'
            f'Стадия "{current_column}" будет отмечена как выполненная\n'
            f'и передана на проверку менеджеру.'
        ).exec_()
        
        if reply == QDialog.Accepted:
            try:
                self.db.complete_stage_for_executor(
                    self.card_data['id'],
                    current_column,
                    current_employee['id']
                )
                
                # ========== ЗАМЕНИЛИ стандартный success_dialog ==========
                CustomMessageBox(
                    self, 
                    'Успех', 
                    'Работа сдана!\n\nОжидайте проверки менеджера для\nперемещения на следующую стадию.', 
                    'success'
                ).exec_()
                
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()
                
            except Exception as e:
                print(f" Ошибка сдачи работы: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(self, 'Ошибка', f'Не удалось отметить работу: {e}', 'error').exec_()
    
    def accept_work(self):
        """Принятие работы менеджером"""
        current_column = self.card_data.get('column_name', '')
        
        if 'концепция дизайна' in current_column:
            executor_name = self.card_data.get('designer_name', 'Дизайнер')
            executor_role = 'дизайнер'
        else:
            executor_name = self.card_data.get('draftsman_name', 'Чертёжник')
            executor_role = 'чертёжник'
        
        # ========== ЗАМЕНИЛИ стандартный dialog ==========
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            f'Принять работу по стадии:\n\n'
            f'"{current_column}"\n\n'
            f'Исполнитель: {executor_name}'
        ).exec_()
        
        if reply == QDialog.Accepted:
            try:
                self.db.save_manager_acceptance(
                    self.card_data['id'],
                    current_column,
                    executor_name,
                    self.employee['id']
                )

                # ========== НОВОЕ: ОТМЕТКА СТАДИИ КАК СДАННОЙ ==========
                # Получаем ID исполнителя для отметки стадии как выполненной
                try:
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    cursor.execute('''
                    SELECT id FROM employees WHERE full_name = ? LIMIT 1
                    ''', (executor_name,))

                    executor_row = cursor.fetchone()
                    self.db.close()

                    if executor_row:
                        executor_id = executor_row['id']
                        # Отмечаем стадию как выполненную (completed = 1)
                        self.db.complete_stage_for_executor(
                            self.card_data['id'],
                            current_column,
                            executor_id
                        )
                        print(f"✓ Стадия отмечена как сданная для {executor_name}")
                except Exception as e:
                    print(f" Ошибка отметки стадии как сданной: {e}")
                # =======================================================

                # ========== НОВОЕ: ОБНОВЛЕНИЕ ОТЧЕТНОГО МЕСЯЦА ДОПЛАТЫ ==========
                try:
                    contract_id = self.card_data['contract_id']
                    contract = self.db.get_contract_by_id(contract_id)
                    current_month = QDate.currentDate().toString('yyyy-MM')
                    
                    print(f"\n[ACCEPT WORK] Принятие работы:")
                    print(f"   Стадия: {current_column}")
                    print(f"   Исполнитель: {executor_name}")
                    print(f"   Текущий месяц: {current_month}")
                    
                    # Получаем ID исполнителя
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    
                    # Находим ID исполнителя по имени
                    cursor.execute('''
                    SELECT id FROM employees WHERE full_name = ? LIMIT 1
                    ''', (executor_name,))
                    
                    executor_row = cursor.fetchone()
                    if not executor_row:
                        print(f" Не найден исполнитель: {executor_name}")
                        self.db.close()
                        return
                    
                    executor_id = executor_row['id']
                    print(f"   ID исполнителя: {executor_id}")
                    
                    # ТОЛЬКО для индивидуальных проектов - обновляем отчетный месяц ДОПЛАТЫ
                    if contract['project_type'] == 'Индивидуальный':
                        # ИСПРАВЛЕНИЕ: Убираем условие на пустой месяц, всегда обновляем
                        cursor.execute('''
                        UPDATE payments
                        SET report_month = ?
                        WHERE contract_id = ?
                          AND employee_id = ?
                          AND stage_name = ?
                          AND payment_type = 'Доплата'
                        ''', (current_month, contract_id, executor_id, current_column))

                        rows_updated = cursor.rowcount

                        if rows_updated > 0:
                            print(f"   ✓ Отчетный месяц ДОПЛАТЫ установлен: {current_month}")
                        else:
                            print(f"    Не найдена доплата для обновления (contract_id={contract_id}, executor_id={executor_id}, stage={current_column})")
                    
                    # Для шаблонных - устанавливаем отчетный месяц ПОЛНОЙ ОПЛАТЫ
                    elif contract['project_type'] == 'Шаблонный':
                        # ИСПРАВЛЕНИЕ: Для чертежника устанавливаем месяц только после ВТОРОЙ стадии
                        can_set_month = True

                        if executor_role == 'чертёжник':
                            # Проверяем, сколько стадий уже принято для этого чертежника
                            # (включая текущую, которая уже была сохранена выше)
                            cursor.execute('''
                            SELECT COUNT(*) as accepted_count
                            FROM manager_stage_acceptance
                            WHERE crm_card_id = ? AND executor_name = ?
                            ''', (self.card_data['id'], executor_name))

                            result = cursor.fetchone()
                            accepted_count = result['accepted_count'] if result else 0

                            print(f"   Количество принятых стадий чертежника: {accepted_count}")

                            # Если это первая стадия (accepted_count = 1), НЕ устанавливаем месяц
                            # Только при второй и последующих (accepted_count >= 2) устанавливаем
                            if accepted_count < 2:
                                can_set_month = False
                                print(f"    Это первая стадия чертежника - месяц НЕ устанавливается")
                            else:
                                print(f"   ✓ Это вторая или последующая стадия чертежника - месяц будет установлен")

                        if can_set_month:
                            # ИСПРАВЛЕНИЕ: Убираем условие на пустой месяц, всегда обновляем
                            cursor.execute('''
                            UPDATE payments
                            SET report_month = ?
                            WHERE contract_id = ?
                              AND employee_id = ?
                              AND stage_name = ?
                              AND payment_type = 'Полная оплата'
                            ''', (current_month, contract_id, executor_id, current_column))

                            rows_updated = cursor.rowcount

                            if rows_updated > 0:
                                print(f"   ✓ Отчетный месяц ПОЛНОЙ ОПЛАТЫ установлен: {current_month}")
                            else:
                                print(f"    Не найдена выплата для обновления (contract_id={contract_id}, executor_id={executor_id}, stage={current_column})")
                    
                    conn.commit()
                    self.db.close()
                    
                except Exception as e:
                    print(f" Ошибка обновления отчетного месяца: {e}")
                    import traceback
                    traceback.print_exc()
                # ================================================================
                
                if executor_role == 'дизайнер':
                    self.db.reset_designer_completion(self.card_data['id'])
                else:
                    self.db.reset_draftsman_completion(self.card_data['id'])
                
                # ========== ЗАМЕНИЛИ стандартный success_dialog ==========
                CustomMessageBox(
                    self, 
                    'Успех', 
                    f'Работа по стадии "{current_column}" принята!\n\n'
                    f'Теперь переместите карточку на следующую стадию.', 
                    'success'
                ).exec_()
                
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()
                
            except Exception as e:
                print(f" Ошибка принятия работы: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось принять работу: {e}', 'error').exec_()

                
    def edit_card(self):
        """Редактирование карточки"""
        dialog = CardEditDialog(self, self.card_data, False, self.employee)
        if dialog.exec_() == QDialog.Accepted:
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()
            
    def show_project_data(self):
        """Показать данные проекта"""
        project_data_link = self.card_data.get('project_data_link', '')
        if project_data_link:
            dialog = ProjectDataDialog(self, project_data_link)
            dialog.exec_()
        else:
            QMessageBox.information(self, 'Информация', 'Ссылка на данные проекта не установлена')

    def add_tech_task(self):
        """Добавить техническое задание"""
        dialog = TechTaskDialog(self, self.card_data.get('id'))
        if dialog.exec_() == QDialog.Accepted:
            # Перезагружаем карточки
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()

    def view_tech_task(self):
        """Просмотр технического задания"""
        tech_task_file = self.card_data.get('tech_task_file', '')
        tech_task_date = self.card_data.get('tech_task_date', '')
        if tech_task_file:
            import webbrowser
            webbrowser.open(tech_task_file)
        else:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Информация', 'Файл ТЗ не найден', 'warning').exec_()

    def add_survey_date(self):
        """Добавить замер с загрузкой изображения"""
        dialog = MeasurementDialog(self, self.card_data.get('id'), self.employee)
        if dialog.exec_() == QDialog.Accepted:
            # Перезагружаем карточки
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()

    def view_survey_date(self):
        """Просмотр даты замера"""
        dialog = SurveyDateDialog(self, self.card_data.get('id'))
        if dialog.exec_() == QDialog.Accepted:
            # Перезагружаем карточки
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()

    def get_highlight_role(self, column_name, project_type):
        """Определение, какую роль подсвечивать"""
        if project_type == 'Индивидуальный':
            if column_name == 'Стадия 1: планировочные решения':
                return 'draftsman'
            elif column_name == 'Стадия 2: концепция дизайна':
                return 'designer'
            elif column_name == 'Стадия 3: рабочие чертежи':
                return 'draftsman'
        elif project_type == 'Шаблонный':
            if column_name == 'Стадия 1: планировочные решения':
                return 'draftsman'
            elif column_name == 'Стадия 2: рабочие чертежи':
                return 'draftsman'
        
        return None
    
    def reassign_executor(self, executor_type):
        """Переназначение исполнителя без перемещения карточки"""
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')

        # Определяем параметры (только для дизайнера и чертежника)
        if executor_type == 'designer':
            position = 'Дизайнер'
            stage_keyword = 'концепция'
            current_name = self.card_data.get('designer_name', 'Не назначен')
        elif executor_type == 'draftsman':
            position = 'Чертёжник'
            current_name = self.card_data.get('draftsman_name', 'Не назначен')
            if 'планировочные' in current_column.lower():
                stage_keyword = 'планировочные'
            else:
                stage_keyword = 'чертежи'
        else:
            return
        
        # Открываем диалог переназначения
        dialog = ReassignExecutorDialog(
            self, 
            self.card_data['id'], 
            position, 
            stage_keyword, 
            executor_type,
            current_name,
            current_column
        )
        
        if dialog.exec_() == QDialog.Accepted:
            # Перезагружаем текущую вкладку
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()

class ProjectDataDialog(QDialog):
    """Диалог просмотра данных проекта"""
    
    def __init__(self, parent, project_data_link):
        super().__init__(parent)
        self.project_data_link = project_data_link
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Данные проекта', simple_mode=True)
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
        
        header = QLabel('Ссылка на данные проекта:')
        header.setStyleSheet('font-size: 14px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)
        
        link_frame = QFrame()
        link_frame.setStyleSheet("""
            QFrame {
                background-color: #E8F4F8;
                border: 2px solid #3498DB;
                border-radius: 6px;
                padding: 15px;
            }
        """)
        link_layout = QVBoxLayout()
        
        link_label = QLabel(f'<a href="{self.project_data_link}" style="color: #3498DB; font-size: 12px; text-decoration: underline;">{self.project_data_link}</a>')
        link_label.setOpenExternalLinks(True)
        link_label.setWordWrap(True)
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_layout.addWidget(link_label)
        
        link_frame.setLayout(link_layout)
        layout.addWidget(link_frame)
        
        copy_btn = QPushButton('Копировать ссылку')
        copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        copy_btn.clicked.connect(self.copy_link)
        layout.addWidget(copy_btn)
        
        open_btn = QPushButton('Открыть в браузере')
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        open_btn.clicked.connect(self.open_in_browser)
        layout.addWidget(open_btn)
        
        close_btn = QPushButton('Закрыть')
        close_btn.setStyleSheet('padding: 10px 20px; margin-top: 10px;')
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(950)
    
    def copy_link(self):
        """Копирование ссылки в буфер обмена"""
        from PyQt5.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(self.project_data_link)
        # ========== ЗАМЕНИЛИ QMessageBox ==========
        CustomMessageBox(self, 'Успех', 'Ссылка скопирована в буфер обмена!', 'success').exec_()
    
    def open_in_browser(self):
        """Открытие ссылки в браузере"""
        from PyQt5.QtGui import QDesktopServices
        from PyQt5.QtCore import QUrl
        QDesktopServices.openUrl(QUrl(self.project_data_link))
    
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

class CardEditDialog(QDialog):
    # Сигналы для межпоточного взаимодействия при загрузке тех.задания
    tech_task_upload_completed = pyqtSignal(str, str, str, int)  # public_link, yandex_path, file_name, contract_id
    tech_task_upload_error = pyqtSignal(str)  # error_msg
    files_verification_completed = pyqtSignal()  # Сигнал завершения проверки файлов

    # Сигналы для референсов и фотофиксации
    references_upload_completed = pyqtSignal(str, int)  # folder_link, contract_id
    references_upload_error = pyqtSignal(str)  # error_msg
    photo_doc_upload_completed = pyqtSignal(str, int)  # folder_link, contract_id
    photo_doc_upload_error = pyqtSignal(str)  # error_msg

    # НОВЫЕ СИГНАЛЫ для файлов стадий проекта
    stage_files_uploaded = pyqtSignal(str)  # stage - успешная загрузка файлов
    stage_upload_error = pyqtSignal(str)  # error_msg - ошибка загрузки

    def __init__(self, parent, card_data, view_only=False, employee=None):
        super().__init__(parent)
        self.card_data = card_data
        self.view_only = view_only
        self.employee = employee
        self.db = DatabaseManager()
        self._loading_data = False  # Флаг для предотвращения автосохранения при загрузке

        # Переменные для ресайза окна
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
        self.resize_margin = 8

        # Подключаем сигналы к обработчикам
        self.tech_task_upload_completed.connect(self._on_project_tech_task_uploaded)
        self.tech_task_upload_error.connect(self._on_project_tech_task_upload_error)
        self.references_upload_completed.connect(self._on_references_uploaded)
        self.references_upload_error.connect(self._on_references_upload_error)
        self.photo_doc_upload_completed.connect(self._on_photo_doc_uploaded)
        self.photo_doc_upload_error.connect(self._on_photo_doc_upload_error)
        self.files_verification_completed.connect(self.refresh_file_labels)

        # Подключаем сигналы для файлов стадий
        self.stage_files_uploaded.connect(self.on_stage_files_uploaded)
        self.stage_upload_error.connect(self.on_stage_upload_error)

        self.init_ui()
        self.load_data()

        # ИСПРАВЛЕНИЕ: Подключаем автосохранение после загрузки данных
        if not self.view_only:
            self.connect_autosave_signals()

    def truncate_filename(self, filename, max_length=50):
        """Обрезает длинное имя файла с многоточием в середине"""
        if len(filename) <= max_length:
            return filename

        # Разделяем имя и расширение
        import os
        name, ext = os.path.splitext(filename)

        # Рассчитываем сколько символов оставить в начале и конце
        ext_len = len(ext)
        available = max_length - ext_len - 3  # 3 для "..."

        if available <= 0:
            return filename[:max_length - 3] + "..."

        # Половину символов в начало, половину в конец (перед расширением)
        start_len = available // 2
        end_len = available - start_len

        return name[:start_len] + "..." + name[-end_len:] + ext

    def init_ui(self):
        title = 'Просмотр карточки' if self.view_only else 'Редактирование карточки проекта'

        # ========== ГЛАВНЫЙ LAYOUT ==========
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Убираем стандартную рамку окна, добавляем кастомный title bar
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Window)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)

        # ========== КОНТЕЙНЕР С РАМКОЙ ==========
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

        # ========== КОНТЕНТ (С ПРОКРУТКОЙ) ==========
        from PyQt5.QtWidgets import QScrollArea

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: #FFFFFF;
                border: none;
                border-bottom-left-radius: 10px;
                border-bottom-right-radius: 10px;
            }
        """)

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

        # ИСПРАВЛЕНИЕ: Делаем tabs атрибутом класса для возможности обновления
        self.tabs = QTabWidget()

        # === ПРОВЕРКА ПРАВ ДОСТУПА ===
        # Определяем роли для управления доступом
        position = self.employee.get('position') if self.employee else None
        secondary_position = self.employee.get('secondary_position') if self.employee else None

        # Исполнители (Дизайнер, Чертёжник, Замерщик) не видят вкладку "Исполнители и дедлайн"
        is_executor = position in ['Дизайнер', 'Чертёжник', 'Замерщик']

        # СДП/ГАП имеют ограниченный доступ (просмотр + редактирование тегов и дедлайнов исполнителей)
        is_sdp_or_gap = position in ['СДП', 'ГАП'] or secondary_position in ['СДП', 'ГАП']

        # Полный доступ: Руководитель, Старший менеджер, Менеджер
        has_full_access = position in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']

        # === ВКЛАДКА 1: ИСПОЛНИТЕЛИ И ДЕДЛАЙН (для всех кроме исполнителей) ===
        if not is_executor:
            # Главный виджет вкладки
            edit_widget = QWidget()
            edit_main_layout = QVBoxLayout(edit_widget)
            edit_main_layout.setContentsMargins(0, 0, 0, 0)
            edit_main_layout.setSpacing(0)

            # Создаем scroll area для контента
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.NoFrame)
            scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

            # Контент внутри scroll area
            scroll_content = QWidget()
            edit_layout = QVBoxLayout(scroll_content)
            edit_layout.setSpacing(15)
            edit_layout.setContentsMargins(20, 15, 20, 20)

            # Стиль для QGroupBox (как в "Данные по проекту")
            GROUP_BOX_STYLE = """
                QGroupBox {
                    font-weight: bold;
                    font-size: 11px;
                    color: #2C3E50;
                    border: 1px solid #E0E0E0;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    left: 10px;
                    padding: 0 5px;
                }
            """

            # ========== БЛОК 1: ИНФОРМАЦИЯ ПРОЕКТА ==========
            project_info_group = QGroupBox("Информация проекта")
            project_info_group.setStyleSheet(GROUP_BOX_STYLE)
            project_info_layout = QVBoxLayout()
            project_info_layout.setSpacing(12)

            # Дедлайн проекта (статичное поле + кнопка изменения)
            deadline_row = QHBoxLayout()
            deadline_row.setSpacing(8)
            deadline_label = QLabel('Дедлайн проекта:')
            deadline_label.setStyleSheet('font-weight: bold; color: #555;')
            deadline_row.addWidget(deadline_label)

            self.deadline_display = QLabel('Не установлен')
            self.deadline_display.setStyleSheet('''
                QLabel {
                    background-color: #F8F9FA;
                    padding: 6px 10px;
                    border: 1px solid #E0E0E0;
                    border-radius: 3px;
                    font-size: 11px;
                }
            ''')
            self.deadline_display.setFixedHeight(32)
            deadline_row.addWidget(self.deadline_display, 1)

            # Кнопка "Изменить дедлайн" (только для полного доступа)
            if has_full_access:
                edit_deadline_btn = QPushButton('Изменить дедлайн')
                edit_deadline_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498DB;
                        color: white;
                        padding: 6px 10px;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #2980B9; }
                    QPushButton:pressed { background-color: #1F618D; }
                """)
                edit_deadline_btn.setFixedHeight(32)
                edit_deadline_btn.clicked.connect(self.change_project_deadline)
                deadline_row.addWidget(edit_deadline_btn)

            project_info_layout.addLayout(deadline_row)

            # Теги
            tags_row = QHBoxLayout()
            tags_row.setSpacing(8)
            tags_label = QLabel('Теги:')
            tags_label.setStyleSheet('font-weight: bold; color: #555;')
            tags_row.addWidget(tags_label)

            self.tags = QLineEdit()
            self.tags.setPlaceholderText('Срочный, VIP, Проблемный...')
            self.tags.setFixedHeight(32)
            # Теги могут редактировать все (СДП/ГАП тоже)
            tags_row.addWidget(self.tags, 1)
            project_info_layout.addLayout(tags_row)

            # Статус проекта
            status_row = QHBoxLayout()
            status_row.setSpacing(8)
            status_label = QLabel('Статус проекта:')
            status_label.setStyleSheet('font-weight: bold; color: #555;')
            status_row.addWidget(status_label)

            self.status_combo = CustomComboBox()
            self.status_combo.addItems(['Новый заказ', 'В работе', 'СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
            self.status_combo.setFixedHeight(32)
            self.status_combo.setEnabled(has_full_access)  # Только для полного доступа
            status_row.addWidget(self.status_combo, 1)
            project_info_layout.addLayout(status_row)

            project_info_group.setLayout(project_info_layout)
            edit_layout.addWidget(project_info_group)

            # ========== БЛОК 2: КОМАНДА ПРОЕКТА ==========
            team_group = QGroupBox("Команда проекта")
            team_group.setStyleSheet(GROUP_BOX_STYLE)
            team_layout = QVBoxLayout()
            team_layout.setSpacing(12)

            # Подзаголовок: Руководство проекта
            leadership_label = QLabel('<b>Руководство проекта:</b>')
            leadership_label.setStyleSheet('color: #2C3E50; font-size: 11px; margin-top: 5px;')
            team_layout.addWidget(leadership_label)

            # Старший менеджер
            senior_mgr_row = QHBoxLayout()
            senior_mgr_row.setSpacing(8)
            senior_mgr_label = QLabel('Старший менеджер:')
            senior_mgr_label.setStyleSheet('color: #555;')
            senior_mgr_row.addWidget(senior_mgr_label)

            self.senior_manager = CustomComboBox()
            self.senior_manager.setFixedHeight(32)
            self.senior_manager.setEnabled(has_full_access)  # Только для полного доступа
            managers = self.db.get_employees_by_position('Старший менеджер проектов')
            self.senior_manager.addItem('Не назначен', None)
            for manager in managers:
                self.senior_manager.addItem(manager['full_name'], manager['id'])
            senior_mgr_row.addWidget(self.senior_manager, 1)
            team_layout.addLayout(senior_mgr_row)

            # СДП
            sdp_row = QHBoxLayout()
            sdp_row.setSpacing(8)
            sdp_label = QLabel('СДП:')
            sdp_label.setStyleSheet('color: #555;')
            sdp_row.addWidget(sdp_label)

            self.sdp = CustomComboBox()
            self.sdp.setFixedHeight(32)
            self.sdp.setEnabled(has_full_access)  # Только для полного доступа
            sdps = self.db.get_employees_by_position('СДП')
            self.sdp.addItem('Не назначен', None)
            for sdp in sdps:
                self.sdp.addItem(sdp['full_name'], sdp['id'])
            sdp_row.addWidget(self.sdp, 1)
            team_layout.addLayout(sdp_row)

            # ГАП
            gap_row = QHBoxLayout()
            gap_row.setSpacing(8)
            gap_label = QLabel('ГАП:')
            gap_label.setStyleSheet('color: #555;')
            gap_row.addWidget(gap_label)

            self.gap = CustomComboBox()
            self.gap.setFixedHeight(32)
            self.gap.setEnabled(has_full_access)  # Только для полного доступа
            gaps = self.db.get_employees_by_position('ГАП')
            self.gap.addItem('Не назначен', None)
            for gap in gaps:
                self.gap.addItem(gap['full_name'], gap['id'])
            gap_row.addWidget(self.gap, 1)
            team_layout.addLayout(gap_row)

            # Подзаголовок: Поддержка
            support_label = QLabel('<b>Поддержка:</b>')
            support_label.setStyleSheet('color: #2C3E50; font-size: 11px; margin-top: 10px;')
            team_layout.addWidget(support_label)

            # Менеджер
            manager_row = QHBoxLayout()
            manager_row.setSpacing(8)
            manager_label = QLabel('Менеджер:')
            manager_label.setStyleSheet('color: #555;')
            manager_row.addWidget(manager_label)

            self.manager = CustomComboBox()
            self.manager.setFixedHeight(32)
            self.manager.setEnabled(has_full_access)  # Только для полного доступа
            managers_list = self.db.get_employees_by_position('Менеджер')
            self.manager.addItem('Не назначен', None)
            for mgr in managers_list:
                self.manager.addItem(mgr['full_name'], mgr['id'])
            manager_row.addWidget(self.manager, 1)
            team_layout.addLayout(manager_row)

            # Замерщик
            surveyor_row = QHBoxLayout()
            surveyor_row.setSpacing(8)
            surveyor_label = QLabel('Замерщик:')
            surveyor_label.setStyleSheet('color: #555;')
            surveyor_row.addWidget(surveyor_label)

            self.surveyor = CustomComboBox()
            self.surveyor.setFixedHeight(32)
            self.surveyor.setEnabled(has_full_access)  # Только для полного доступа
            surveyors = self.db.get_employees_by_position('Замерщик')
            self.surveyor.addItem('Не назначен', None)
            for surv in surveyors:
                self.surveyor.addItem(surv['full_name'], surv['id'])
            surveyor_row.addWidget(self.surveyor, 1)

            # Кнопка "Замер произведен" (только для полного доступа)
            if has_full_access:
                survey_btn = QPushButton('Замер произведен')
                survey_btn.setToolTip('Отметить дату замера')
                survey_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        padding: 6px 10px;
                        border-radius: 3px;
                        font-size: 10px;
                        font-weight: bold;
                    }
                    QPushButton:hover { background-color: #229954; }
                    QPushButton:pressed { background-color: #1E8449; }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #333333;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                        padding: 5px 8px;
                        font-size: 11px;
                    }
                """)
                survey_btn.setFixedHeight(32)
                survey_btn.clicked.connect(self.mark_survey_complete)

                # Проверяем, был ли замер уже отмечен как выполненный
                # Проверяем в истории действий наличие записи "Замер выполнен"
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT COUNT(*) as count
                        FROM action_history
                        WHERE entity_type = 'contract'
                        AND entity_id = ?
                        AND (description LIKE '%Замер выполнен%' OR description LIKE '%Замер произведен%')
                    ''', (contract_id,))
                    result = cursor.fetchone()
                    conn.close()

                    if result and result['count'] > 0:
                        # Замер уже был отмечен - блокируем кнопку
                        survey_btn.setEnabled(False)
                        survey_btn.setStyleSheet("""
                            QPushButton {
                                background-color: #95A5A6;
                                color: white;
                                padding: 6px 10px;
                                border-radius: 3px;
                                font-size: 10px;
                                font-weight: bold;
                            }
                            QToolTip {
                                background-color: #FFFFFF;
                                color: #333333;
                                border: 1px solid #CCCCCC;
                                border-radius: 4px;
                                padding: 5px 8px;
                                font-size: 11px;
                            }
                        """)
                        survey_btn.setToolTip('Замер уже отмечен как выполненный')

                surveyor_row.addWidget(survey_btn)

            team_layout.addLayout(surveyor_row)

            # Дата замера (статичная информация + кнопка изменить)
            survey_date_row = QHBoxLayout()
            survey_date_row.setSpacing(8)
            survey_date_label_text = QLabel('Дата замера:')
            survey_date_label_text.setStyleSheet('color: #555;')
            survey_date_row.addWidget(survey_date_label_text)

            self.survey_date_label = QLabel('Не установлена')
            self.survey_date_label.setStyleSheet('''
                QLabel {
                    background-color: #F8F9FA;
                    padding: 6px 10px;
                    border: 1px solid #E0E0E0;
                    border-radius: 3px;
                    font-size: 10px;
                }
            ''')
            self.survey_date_label.setFixedHeight(28)
            survey_date_row.addWidget(self.survey_date_label, 1)

            # Кнопка "Изменить дату" замера (только для полного доступа)
            if has_full_access:
                edit_survey_btn = QPushButton('Изменить дату')
                edit_survey_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95a5a6;
                        color: white;
                        padding: 6px 10px;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover { background-color: #7f8c8d; }
                    QPushButton:pressed { background-color: #6d7879; }
                """)
                edit_survey_btn.setFixedHeight(28)
                edit_survey_btn.clicked.connect(self.edit_survey_date)
                survey_date_row.addWidget(edit_survey_btn)

            team_layout.addLayout(survey_date_row)

            hint_survey = QLabel('💡 Дата проведения замера помещения')
            hint_survey.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
            team_layout.addWidget(hint_survey)

            # Подзаголовок: Дедлайны исполнителей
            executors_label = QLabel('<b>Дедлайны исполнителей:</b>')
            executors_label.setStyleSheet('color: #2C3E50; font-size: 11px; margin-top: 10px;')
            team_layout.addWidget(executors_label)

            # ========== БЛОК ДИЗАЙНЕРА ==========
            if self.card_data.get('designer_name'):
                designer_group = QGroupBox('🎨 Дизайнер')
                designer_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 2px solid #E0E0E0;
                        border-radius: 6px;
                        margin-top: 10px;
                        padding-top: 10px;
                        background-color: #F8F9FA;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                        color: #555;
                    }
                """)

                designer_layout = QVBoxLayout()
                designer_layout.setSpacing(8)
                designer_layout.setContentsMargins(10, 10, 10, 10)

                # Строка с именем и кнопкой
                name_row = QHBoxLayout()

                designer_name_label = QLabel(f"<b>{self.card_data['designer_name']}</b>")
                designer_name_label.setStyleSheet('font-size: 12px; color: #333; background-color: transparent;')
                name_row.addWidget(designer_name_label)

                name_row.addStretch()

                reassign_designer_btn = QPushButton('🔄 Переназначить')
                reassign_designer_btn.setToolTip('Выбрать другого дизайнера')
                reassign_designer_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 5px 10px;
                    }
                    QPushButton:hover { background-color: #F57C00; }
                    QPushButton:pressed { background-color: #E65100; }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #333333;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                        padding: 5px 8px;
                        font-size: 11px;
                    }
                """)
                reassign_designer_btn.setFixedHeight(26)
                reassign_designer_btn.setEnabled(has_full_access or is_sdp_or_gap)  # Для руководства и СДП/ГАП
                reassign_designer_btn.clicked.connect(
                    lambda: self.reassign_executor_from_dialog('designer')
                )
                name_row.addWidget(reassign_designer_btn)

                designer_layout.addLayout(name_row)

                # Строка с дедлайном
                deadline_row = QHBoxLayout()
                deadline_row.addWidget(QLabel('Дедлайн:'))

                self.designer_deadline = CustomDateEdit()
                self.designer_deadline.setCalendarPopup(True)
                add_today_button_to_dateedit(self.designer_deadline)
                self.designer_deadline.setDate(QDate.currentDate())
                self.designer_deadline.setDisplayFormat('dd.MM.yyyy')
                self.designer_deadline.setStyleSheet(CALENDAR_STYLE)

                if self.card_data.get('designer_deadline'):
                    self.designer_deadline.setDate(QDate.fromString(self.card_data['designer_deadline'], 'yyyy-MM-dd'))

                deadline_row.addWidget(self.designer_deadline, 1)
                designer_layout.addLayout(deadline_row)

                designer_group.setLayout(designer_layout)
                team_layout.addWidget(designer_group)
            else:
                self.designer_deadline = None

            # ========== БЛОК ЧЕРТЁЖНИКА ==========
            if self.card_data.get('draftsman_name'):
                draftsman_group = QGroupBox('✏️ Чертёжник')
                draftsman_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 2px solid #E0E0E0;
                        border-radius: 6px;
                        margin-top: 10px;
                        padding-top: 10px;
                        background-color: #F8F9FA;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        left: 10px;
                        padding: 0 5px;
                        color: #555;
                    }
                """)

                draftsman_layout = QVBoxLayout()
                draftsman_layout.setSpacing(8)
                draftsman_layout.setContentsMargins(10, 10, 10, 10)

                # Строка с именем и кнопкой
                name_row = QHBoxLayout()

                draftsman_name_label = QLabel(f"<b>{self.card_data['draftsman_name']}</b>")
                draftsman_name_label.setStyleSheet('font-size: 12px; color: #333; background-color: transparent;')
                name_row.addWidget(draftsman_name_label)

                name_row.addStretch()

                reassign_draftsman_btn = QPushButton('🔄 Переназначить')
                reassign_draftsman_btn.setToolTip('Выбрать другого чертёжника')
                reassign_draftsman_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        padding: 5px 10px;
                    }
                    QPushButton:hover { background-color: #F57C00; }
                    QPushButton:pressed { background-color: #E65100; }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #333333;
                        border: 1px solid #CCCCCC;
                        border-radius: 4px;
                        padding: 5px 8px;
                        font-size: 11px;
                    }
                """)
                reassign_draftsman_btn.setFixedHeight(26)
                reassign_draftsman_btn.setEnabled(has_full_access or is_sdp_or_gap)  # Для руководства и СДП/ГАП
                reassign_draftsman_btn.clicked.connect(
                    lambda: self.reassign_executor_from_dialog('draftsman')
                )
                name_row.addWidget(reassign_draftsman_btn)

                draftsman_layout.addLayout(name_row)

                # Строка с дедлайном
                deadline_row = QHBoxLayout()
                deadline_row.addWidget(QLabel('Дедлайн:'))

                self.draftsman_deadline = CustomDateEdit()
                self.draftsman_deadline.setCalendarPopup(True)
                add_today_button_to_dateedit(self.draftsman_deadline)
                self.draftsman_deadline.setDate(QDate.currentDate())
                self.draftsman_deadline.setDisplayFormat('dd.MM.yyyy')
                self.draftsman_deadline.setStyleSheet(CALENDAR_STYLE)

                if self.card_data.get('draftsman_deadline'):
                    self.draftsman_deadline.setDate(QDate.fromString(self.card_data['draftsman_deadline'], 'yyyy-MM-dd'))

                deadline_row.addWidget(self.draftsman_deadline, 1)
                draftsman_layout.addLayout(deadline_row)

                draftsman_group.setLayout(draftsman_layout)
                team_layout.addWidget(draftsman_group)
            else:
                self.draftsman_deadline = None

            hint_executor_deadlines = QLabel('💡 Эти дедлайны отображаются исполнителям на карточке')
            hint_executor_deadlines.setWordWrap(True)
            hint_executor_deadlines.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
            team_layout.addWidget(hint_executor_deadlines)

            team_group.setLayout(team_layout)
            edit_layout.addWidget(team_group)

            # ========== ПОДКЛЮЧЕНИЕ АВТОМАТИЧЕСКОГО СОЗДАНИЯ ВЫПЛАТ ==========
            self.senior_manager.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.senior_manager, 'Старший менеджер проектов')
            )
            self.sdp.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.sdp, 'СДП')
            )
            self.gap.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.gap, 'ГАП')
            )
            self.manager.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.manager, 'Менеджер')
            )
            self.surveyor.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.surveyor, 'Замерщик')
            )
            # =========================================================================

            edit_layout.addStretch()

            # Добавляем scroll area в главный layout
            scroll.setWidget(scroll_content)
            edit_main_layout.addWidget(scroll)

            # Добавляем вкладку "Исполнители и дедлайн" (переименовано из "Редактирование")
            self.tabs.addTab(edit_widget, 'Исполнители и дедлайн')

        # === ВКЛАДКА 2: ДАННЫЕ ПО ПРОЕКТУ ===
        project_data_widget = self.create_project_data_widget()
        self.project_data_tab_index = self.tabs.addTab(project_data_widget, 'Данные по проекту')

        if not is_executor:
            # === ВКЛАДКА 3: ИСТОРИЯ ПО ПРОЕКТУ (переименовано из "Информация о проекте") ===
            info_widget = self.create_project_info_widget()
            self.project_info_tab_index = self.tabs.addTab(info_widget, 'История по проекту')
        else:
            self.project_info_tab_index = -1  # Вкладка не создана

        # === ВКЛАДКА 4: ОПЛАТЫ ===
        self.payments_tab_index = -1  # Храним индекс вкладки оплат
        if self.employee and self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            payments_widget = self.create_payments_tab()
            self.payments_tab_index = self.tabs.addTab(payments_widget, '💰 Оплаты')

        # Для исполнителей (дизайнеров и чертежников) открываем сразу вкладку "Данные по проекту"
        if is_executor:
            self.tabs.setCurrentIndex(0)  # Первая и единственная вкладка

        layout.addWidget(self.tabs, 1)   
            
        # Кнопки
        if not self.view_only:
            buttons_layout = QHBoxLayout()
            
            if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов']:
                delete_btn = IconLoader.create_icon_button('delete', 'Удалить заказ', 'Полностью удалить заказ', icon_size=16)
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
            
            save_btn = QPushButton('Сохранить')
            save_btn.clicked.connect(self.save_changes)
            save_btn.setStyleSheet('padding: 10px 30px; font-weight: bold;')
            
            cancel_btn = QPushButton('Отмена')
            cancel_btn.clicked.connect(self.reject)
            cancel_btn.setStyleSheet('padding: 10px 30px;')
            
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            
            layout.addLayout(buttons_layout)
        else:
            # Блокируем переключение вкладок колесом мыши
            disable_wheel_on_tabwidget(self.tabs)

            self.setEnabled(False)
            close_btn = QPushButton('Закрыть')
            close_btn.setEnabled(True)
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)

        content_widget.setLayout(layout)

        # ИСПРАВЛЕНИЕ: Ограничиваем максимальную высоту content_widget
        # чтобы предотвратить двойной скролл
        from PyQt5.QtWidgets import QDesktopWidget
        available_screen = QDesktopWidget().availableGeometry()

        # Рассчитываем высоту окна (90% экрана)
        target_height = int(available_screen.height() * 0.90)

        # КРИТИЧЕСКИ ВАЖНО: Высота контента = высота окна минус 100px (для title bar и кнопок)
        max_content_height = target_height - 50
        content_widget.setMaximumHeight(max_content_height)

        scroll_area.setWidget(content_widget)

        border_layout.addWidget(scroll_area)
        border_frame.setLayout(border_layout)

        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # ========== ИСПРАВЛЕНИЕ: РЕГУЛИРУЕМОЕ ОКНО ==========
        # target_height уже рассчитан выше при установке высоты content_widget

        # Ширина
        target_width = 950

        # Устанавливаем размеры окна
        self.setMinimumWidth(950)  # Минимальная ширина
        self.setFixedHeight(target_height)  # ФИКСИРОВАННАЯ высота 90% экрана - нельзя растягивать
        self.resize(target_width, target_height)
        # ===================================================================
        
    def mark_survey_complete(self):
        """Отметка о проведенном замере"""
        surveyor_id = self.surveyor.currentData()
        
        if not surveyor_id:
            CustomMessageBox(
                self, 
                'Ошибка', 
                'Сначала выберите замерщика!', 
                'warning'
            ).exec_()
            return
        
        # Диалог выбора даты
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        
        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Рамка
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
        border_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title Bar
        from ui.custom_title_bar import CustomTitleBar
        title_bar = CustomTitleBar(dialog, 'Дата замера', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)
        
        # ИСПРАВЛЕНИЕ: Уменьшены размеры на 30%
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(10)  # было 15
        layout.setContentsMargins(10, 10, 10, 10)  # было 20, 20, 20, 20

        info_label = QLabel('Укажите дату проведенного замера:')
        info_label.setStyleSheet('font-size: 11px; font-weight: bold;')  # было 12px
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)

        # Поле даты
        date_edit = CustomDateEdit()
        date_edit.setCalendarPopup(True)
        add_today_button_to_dateedit(date_edit)
        date_edit.setDate(QDate.currentDate())
        date_edit.setDisplayFormat('dd.MM.yyyy')
        date_edit.setStyleSheet("""
            QDateEdit {
                padding: 6px;
                font-size: 11px;
                border: 1px solid #DDD;
                border-radius: 4px;
            }
        """)
        layout.addWidget(date_edit)

        # Кнопки
        buttons_layout = QHBoxLayout()

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px 14px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 11px;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        save_btn.clicked.connect(
            lambda: self.save_survey_date(date_edit.date(), surveyor_id, dialog)
        )

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet('padding: 12px 14px; font-size: 11px;')  # было 10px 20px
        cancel_btn.clicked.connect(dialog.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        dialog.setLayout(main_layout)

        dialog.setFixedWidth(280)  # было 400
        dialog.exec_()

    def save_survey_date(self, survey_date, surveyor_id, dialog):
        """Сохранение даты замера"""
        try:
            contract_id = self.card_data['contract_id']
            
            # Сохраняем в таблицу surveys
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Проверяем, нет ли уже записи
            cursor.execute('''
            SELECT id FROM surveys WHERE contract_id = ?
            ''', (contract_id,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем существующую
                cursor.execute('''
                UPDATE surveys
                SET surveyor_id = ?, survey_date = ?
                WHERE contract_id = ?
                ''', (surveyor_id, survey_date.toString('yyyy-MM-dd'), contract_id))
                
                print(f"✓ Дата замера обновлена")
            else:
                # Создаем новую
                cursor.execute('''
                INSERT INTO surveys (contract_id, surveyor_id, survey_date, created_by)
                VALUES (?, ?, ?, ?)
                ''', (contract_id, surveyor_id, survey_date.toString('yyyy-MM-dd'), 
                      self.employee['id']))
                
                print(f"✓ Дата замера создана")
            
            conn.commit()
            self.db.close()
            
            # ========== ИСПРАВЛЕНИЕ: ОБНОВЛЯЕМ ОТЧЕТНЫЙ МЕСЯЦ ЗАМЕРЩИКА ==========
            contract = self.db.get_contract_by_id(contract_id)
            report_month = survey_date.toString('yyyy-MM')

            # Проверяем, есть ли уже выплата замерщику
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT id FROM payments
            WHERE contract_id = ? AND employee_id = ? AND role = 'Замерщик'
            ''', (contract_id, surveyor_id))

            existing_payment = cursor.fetchone()

            if existing_payment:
                # Обновляем отчетный месяц существующей выплаты
                cursor.execute('''
                UPDATE payments
                SET report_month = ?
                WHERE contract_id = ? AND employee_id = ? AND role = 'Замерщик'
                ''', (report_month, contract_id, surveyor_id))
                conn.commit()
                print(f"✓ Отчетный месяц замерщика обновлен: {report_month}")
            else:
                # Создаем выплату если её нет (для любого типа проекта)
                self.db.close()
                self.db.create_payment_record(
                    contract_id, surveyor_id, 'Замерщик',
                    payment_type='Полная оплата',
                    report_month=report_month,
                    crm_card_id=self.card_data['id']
                )
                print(f"✓ Выплата замерщику создана в отчетном месяце {report_month}")
                conn = self.db.connect()

            self.db.close()
            # ======================================================================

            # Обновляем contracts.measurement_date в БД
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE contracts
                SET measurement_date = ?
                WHERE id = ?
            ''', (survey_date.toString('yyyy-MM-dd'), contract_id))
            conn.commit()
            self.db.close()

            # Обновляем crm_cards.survey_date
            updates = {'survey_date': survey_date.toString('yyyy-MM-dd'), 'surveyor_id': surveyor_id}
            self.db.update_crm_card(self.card_data['id'], updates)
            self.card_data['survey_date'] = survey_date.toString('yyyy-MM-dd')
            self.card_data['surveyor_id'] = surveyor_id

            # Обновляем оба label - в редактировании и в данных по проекту
            self.survey_date_label.setText(survey_date.toString('dd.MM.yyyy'))
            if hasattr(self, 'project_data_survey_date_label'):
                self.project_data_survey_date_label.setText(survey_date.toString('dd.MM.yyyy'))

            # ИСПРАВЛЕНИЕ: Обновляем вкладки после создания выплаты замерщику
            self.refresh_payments_tab()
            self.refresh_project_info_tab()

            # ИСПРАВЛЕНИЕ: Добавляем запись в историю проекта
            if self.employee and existing is None:  # Только если это первый раз
                from datetime import datetime
                # Получаем имя замерщика
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT full_name FROM employees WHERE id = ?', (surveyor_id,))
                surveyor_result = cursor.fetchone()
                surveyor_name = surveyor_result['full_name'] if surveyor_result else 'Неизвестный'
                conn.close()

                description = f"Замер выполнен: {survey_date.toString('dd.MM.yyyy')} | Замерщик: {surveyor_name}"

                self.db.add_action_history(
                    user_id=self.employee.get('id'),
                    action_type='survey_complete',
                    entity_type='crm_card',
                    entity_id=self.card_data['id'],
                    description=description
                )

                # Обновляем историю в UI
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                # ИСПРАВЛЕНИЕ: Блокируем кнопку "Замер произведен" сразу после использования
                # Находим кнопку в layout и блокируем её
                for widget in self.findChildren(QPushButton):
                    if widget.text() == 'Замер произведен':
                        widget.setEnabled(False)
                        widget.setStyleSheet("""
                            QPushButton {
                                background-color: #95A5A6;
                                color: white;
                                padding: 6px 10px;
                                border-radius: 3px;
                                font-size: 10px;
                                font-weight: bold;
                            }
                            QToolTip {
                                background-color: #FFFFFF;
                                color: #333333;
                                border: 1px solid #CCCCCC;
                                border-radius: 4px;
                                padding: 5px 8px;
                                font-size: 11px;
                            }
                        """)
                        widget.setToolTip('Замер уже отмечен как выполненный')
                        break

            # Формируем сообщение в зависимости от типа проекта
            if contract and contract['project_type'] == 'Индивидуальный':
                message = (f'Дата замера сохранена: {survey_date.toString("dd.MM.yyyy")}\n\n'
                          f'Выплата замерщику добавлена в отчетный месяц {report_month}')
            else:
                message = (f'Дата замера сохранена: {survey_date.toString("dd.MM.yyyy")}\n\n'
                          f'Выплата будет создана при сдаче проекта')

            CustomMessageBox(self, 'Успех', message, 'success').exec_()

            dialog.accept()
            
        except Exception as e:
            print(f" Ошибка сохранения замера: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

    def edit_survey_date(self):
        """Открывает диалог для изменения даты замера"""
        from PyQt5.QtCore import QDate
        from utils.calendar_styles import add_today_button_to_dateedit

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #2C3E50;
                border-radius: 8px;
            }
        """)
        dialog.setFixedWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Добавляем заголовок (простой режим - только кнопка закрыть)
        title_bar = CustomTitleBar(dialog, "Изменить дату замера", simple_mode=True)
        layout.addWidget(title_bar)

        # Контент
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Поле даты
        date_label = QLabel('Дата замера:')
        date_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(date_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QDateEdit:focus {
                border: 2px solid #3498DB;
            }
        """)

        # Добавляем кастомный календарь с кнопкой "Сегодня"
        add_today_button_to_dateedit(date_input)

        # Устанавливаем текущую дату или сегодня
        if self.card_data.get('survey_date'):
            try:
                from datetime import datetime
                survey_date = datetime.strptime(self.card_data['survey_date'], '%Y-%m-%d')
                date_input.setDate(QDate(survey_date.year, survey_date.month, survey_date.day))
            except:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_survey_date():
            try:
                selected_date = date_input.date()
                date_str = selected_date.toString('yyyy-MM-dd')

                # Обновляем в БД - и crm_cards, и contracts
                updates = {'survey_date': date_str}
                self.db.update_crm_card(self.card_data['id'], updates)
                self.card_data['survey_date'] = date_str

                # Обновляем contracts.measurement_date
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE contracts
                        SET measurement_date = ?
                        WHERE id = ?
                    ''', (date_str, contract_id))
                    conn.commit()
                    self.db.close()

                # ========== ОБНОВЛЯЕМ ОТЧЕТНЫЙ МЕСЯЦ ЗАМЕРЩИКА ==========
                contract_id = self.card_data.get('contract_id')
                surveyor_id = self.card_data.get('surveyor_id')

                if contract_id and surveyor_id:
                    report_month = selected_date.toString('yyyy-MM')

                    # Проверяем, есть ли уже выплата замерщику
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    cursor.execute('''
                    SELECT id FROM payments
                    WHERE contract_id = ? AND employee_id = ? AND role = 'Замерщик'
                    ''', (contract_id, surveyor_id))

                    existing_payment = cursor.fetchone()

                    if existing_payment:
                        # Обновляем отчетный месяц существующей выплаты
                        cursor.execute('''
                        UPDATE payments
                        SET report_month = ?
                        WHERE contract_id = ? AND employee_id = ? AND role = 'Замерщик'
                        ''', (report_month, contract_id, surveyor_id))
                        conn.commit()
                        print(f"✓ Отчетный месяц замерщика обновлен: {report_month}")
                    else:
                        # Если выплаты нет, проверяем тип проекта
                        contract = self.db.get_contract_by_id(contract_id)
                        if contract and contract['project_type'] == 'Индивидуальный':
                            # Для индивидуальных создаем выплату
                            self.db.close()
                            self.db.create_payment_record(
                                contract_id, surveyor_id, 'Замерщик',
                                payment_type='Полная оплата',
                                report_month=report_month,
                                crm_card_id=self.card_data['id']
                            )
                            print(f"✓ Выплата замерщику создана в отчетном месяце {report_month}")
                            conn = self.db.connect()
                        else:
                            print(f"ℹ️ Шаблонный проект: выплата замерщику будет создана при сдаче проекта")

                    self.db.close()
                # ========================================================

                # Обновляем оба label - в редактировании и в данных по проекту
                self.survey_date_label.setText(selected_date.toString('dd.MM.yyyy'))
                if hasattr(self, 'project_data_survey_date_label'):
                    self.project_data_survey_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_payments_tab()
                self.refresh_project_info_tab()

                CustomMessageBox(dialog, 'Успех', f'Дата замера изменена: {selected_date.toString("dd.MM.yyyy")}\nОтчетный месяц обновлен', 'success').exec_()
                dialog.accept()

            except Exception as e:
                print(f" Ошибка изменения даты замера: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(dialog, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

        save_btn.clicked.connect(save_survey_date)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        layout.addLayout(content_layout)

        dialog.exec_()

    def change_project_deadline(self):
        """Открывает диалог для изменения дедлайна проекта с указанием причины"""
        from PyQt5.QtCore import QDate
        from utils.calendar_styles import add_today_button_to_dateedit

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #2C3E50;
                border-radius: 8px;
            }
        """)
        dialog.setFixedWidth(450)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Добавляем заголовок
        title_bar = CustomTitleBar(dialog, "Изменить дедлайн проекта", simple_mode=True)
        layout.addWidget(title_bar)

        # Контент
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Текущий дедлайн
        current_deadline_label = QLabel('Текущий дедлайн:')
        current_deadline_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(current_deadline_label)

        current_deadline_text = QLabel()
        if self.card_data.get('deadline'):
            from datetime import datetime
            try:
                deadline = datetime.strptime(self.card_data['deadline'], '%Y-%m-%d')
                current_deadline_text.setText(deadline.strftime('%d.%m.%Y'))
            except:
                current_deadline_text.setText('Не установлен')
        else:
            current_deadline_text.setText('Не установлен')

        current_deadline_text.setStyleSheet('''
            background-color: #F8F9FA;
            padding: 8px;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            font-size: 11px;
            color: #555;
        ''')
        content_layout.addWidget(current_deadline_text)

        # Новый дедлайн
        new_deadline_label = QLabel('Новый дедлайн:')
        new_deadline_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(new_deadline_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QDateEdit:focus {
                border: 2px solid #3498DB;
            }
        """)

        # Добавляем кастомный календарь с кнопкой "Сегодня"
        add_today_button_to_dateedit(date_input)

        # Устанавливаем текущий дедлайн или сегодня
        if self.card_data.get('deadline'):
            try:
                from datetime import datetime
                deadline_date = datetime.strptime(self.card_data['deadline'], '%Y-%m-%d')
                date_input.setDate(QDate(deadline_date.year, deadline_date.month, deadline_date.day))
            except:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Причина изменения (обязательное поле)
        reason_label = QLabel('Причина изменения:')
        reason_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(reason_label)

        reason_input = QLineEdit()
        reason_input.setPlaceholderText('Укажите причину изменения дедлайна...')
        reason_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498DB;
            }
        """)
        content_layout.addWidget(reason_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_deadline():
            try:
                # Проверка на заполнение причины
                reason = reason_input.text().strip()
                if not reason:
                    CustomMessageBox(dialog, 'Ошибка', 'Необходимо указать причину изменения дедлайна', 'warning').exec_()
                    return

                selected_date = date_input.date()
                new_deadline_str = selected_date.toString('yyyy-MM-dd')
                old_deadline_str = self.card_data.get('deadline', 'Не установлен')

                # Проверяем, что дедлайн действительно изменился
                if new_deadline_str == old_deadline_str:
                    CustomMessageBox(dialog, 'Информация', 'Дедлайн не изменился', 'warning').exec_()
                    return

                # Обновляем в БД
                updates = {'deadline': new_deadline_str}
                self.db.update_crm_card(self.card_data['id'], updates)
                self.card_data['deadline'] = new_deadline_str

                # Обновляем отображение на форме
                self.deadline_display.setText(selected_date.toString('dd.MM.yyyy'))

                # Добавляем запись в историю действий
                employee_id = self.employee.get('id') if self.employee else None
                if employee_id:
                    # Форматируем старый дедлайн
                    old_deadline_formatted = 'Не установлен'
                    if old_deadline_str and old_deadline_str != 'Не установлен':
                        try:
                            from datetime import datetime
                            old_date = datetime.strptime(old_deadline_str, '%Y-%m-%d')
                            old_deadline_formatted = old_date.strftime('%d.%m.%Y')
                        except:
                            old_deadline_formatted = old_deadline_str

                    description = f"Дедлайн изменен с {old_deadline_formatted} на {selected_date.toString('dd.MM.yyyy')}. Причина: {reason}"

                    self.db.add_action_history(
                        user_id=employee_id,
                        action_type='deadline_changed',
                        entity_type='crm_card',
                        entity_id=self.card_data['id'],
                        description=description
                    )
                    self.reload_project_history()

                    # Принудительно обрабатываем отложенные события Qt
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()

                CustomMessageBox(
                    dialog,
                    'Успех',
                    f'Дедлайн изменен: {selected_date.toString("dd.MM.yyyy")}',
                    'success'
                ).exec_()
                dialog.accept()

            except Exception as e:
                print(f" Ошибка изменения дедлайна: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(dialog, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

        save_btn.clicked.connect(save_deadline)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        layout.addLayout(content_layout)

        dialog.exec_()

    def upload_project_tech_task_file(self):
        """Загрузка файла тех.задания на Яндекс.Диск из вкладки 'Данные по проекту'"""
        print(f"[DEBUG] upload_project_tech_task_file() вызван")
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        from PyQt5.QtCore import Qt

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF файл тех.задания",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            print(f"[DEBUG] Файл не выбран, выход")
            return

        print(f"[DEBUG] Выбран файл: {file_path}")

        # Получаем yandex_folder_path из договора
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result['yandex_folder_path']:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        contract_folder = result['yandex_folder_path']
        file_name = os.path.basename(file_path)

        # Создаем прогресс-диалог
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, 3, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файла")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)

        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                print(f"[DEBUG] upload_thread: начинаем загрузку на Яндекс.Диск")
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if progress.wasCanceled():
                        return
                    progress.setValue(step)
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    progress.setLabelText(f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)")

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Анкета",
                    file_name,
                    progress_callback=update_progress
                )
                print(f"[DEBUG] upload_thread: результат загрузки: {result}")

                if result:
                    progress.setValue(3)
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # Отправляем сигнал в главный поток с полными данными
                    print(f"[DEBUG] upload_thread: отправляем сигнал tech_task_upload_completed")
                    self.tech_task_upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name'],
                        contract_id
                    )
                    print(f"[DEBUG] upload_thread: сигнал отправлен")
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    print(f"[DEBUG] upload_thread: загрузка не удалась, отправляем сигнал ошибки")
                    self.tech_task_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск")

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                print(f"[DEBUG] upload_thread: исключение: {e}")
                self.tech_task_upload_error.emit(str(e))

        print(f"[DEBUG] Запускаем фоновый поток загрузки")
        thread = threading.Thread(target=upload_thread)
        thread.start()
        print(f"[DEBUG] Фоновый поток запущен")

    def _on_project_tech_task_uploaded(self, public_link, yandex_path, file_name, contract_id):
        """Обработчик успешной загрузки файла тех.задания"""
        print(f"[DEBUG] _on_project_tech_task_uploaded вызван: public_link={public_link}, file_name={file_name}")

        if public_link:
            # Обновляем все поля тех.задания в БД договора
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE contracts
                SET tech_task_link = ?,
                    tech_task_yandex_path = ?,
                    tech_task_file_name = ?
                WHERE id = ?
            ''', (public_link, yandex_path, file_name, contract_id))
            conn.commit()
            conn.close()

            # Обновляем лейбл (обрезаем длинное имя)
            truncated_name = self.truncate_filename(file_name)
            self.project_data_tz_file_label.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            # Обновляем старый лейбл если он существует (для совместимости)
            if hasattr(self, 'tech_task_file_label'):
                self.tech_task_file_label.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            # Деактивируем кнопку загрузки
            if hasattr(self, 'upload_tz_btn'):
                self.upload_tz_btn.setEnabled(False)

            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime
                employee_name = self.employee.get('full_name', 'Неизвестный')
                date_str = datetime.now().strftime('%d.%m.%Y')
                description = f"Добавлены файлы в Техническое задание"

                self.db.add_action_history(
                    user_id=self.employee.get('id'),
                    action_type='file_upload',
                    entity_type='crm_card',
                    entity_id=self.card_data['id'],
                    description=description
                )
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"[OK] Добавлена запись в историю: {description}")

            # Отправляем сигнал для обновления других открытых окон
            self.files_verification_completed.emit()
        else:
            self.project_data_tz_file_label.setText('Не загружен')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл на Яндекс.Диск', 'error').exec_()

    def _on_project_tech_task_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файла тех.задания"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файла: {error_msg}', 'error').exec_()

    def upload_references_files(self):
        """Загрузка множественных файлов референсов на Яндекс.Диск"""
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        from PyQt5.QtCore import Qt

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы референсов",
            "",
            "Images and PDF (*.png *.jpg *.jpeg *.pdf);;All Files (*.*)"
        )

        if not file_paths:
            return

        # Получаем yandex_folder_path из договора
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result['yandex_folder_path']:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        contract_folder = result['yandex_folder_path']

        # Создаем прогресс-диалог
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, len(file_paths), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файлов")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)

        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        # Загружаем файлы на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(current, total, fname, phase):
                    if progress.wasCanceled():
                        return
                    progress.setValue(current)
                    percent = int((current / total) * 100)
                    progress.setLabelText(f"Загрузка: {fname}\n({current}/{total} файлов - {percent}%)")

                # Загружаем файлы
                uploaded_files = yd.upload_stage_files(
                    file_paths,
                    contract_folder,
                    'references',
                    progress_callback=update_progress
                )

                if uploaded_files:
                    progress.setValue(len(file_paths))
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)

                    # Получаем ссылку на папку
                    folder_path = yd.get_stage_folder_path(contract_folder, 'references')
                    folder_link = yd.get_public_link(folder_path)

                    # Отправляем сигнал в главный поток
                    self.references_upload_completed.emit(folder_link if folder_link else folder_path, contract_id)
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.references_upload_error.emit("Не удалось загрузить файлы на Яндекс.Диск")

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                self.references_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_references_uploaded(self, folder_link, contract_id):
        """Обработчик успешной загрузки референсов"""
        # Обновляем БД
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('UPDATE contracts SET references_yandex_path = ? WHERE id = ?', (folder_link, contract_id))
        conn.commit()
        conn.close()

        # Обновляем лейбл
        self.project_data_references_label.setText(f'<a href="{folder_link}">Открыть папку с референсами</a>')

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = f"Добавлены файлы в Референсы"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_upload',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            print(f"[OK] Добавлена запись в историю: {description}")

    def _on_references_upload_error(self, error_msg):
        """Обработчик ошибки загрузки референсов"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов: {error_msg}', 'error').exec_()

    def upload_photo_documentation_files(self):
        """Загрузка множественных файлов фотофиксации на Яндекс.Диск"""
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        from PyQt5.QtCore import Qt

        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите файлы фотофиксации",
            "",
            "Images, PDF and Videos (*.png *.jpg *.jpeg *.pdf *.mp4 *.mov *.avi);;All Files (*.*)"
        )

        if not file_paths:
            return

        # Получаем yandex_folder_path из договора
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result['yandex_folder_path']:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        contract_folder = result['yandex_folder_path']

        # Создаем прогресс-диалог
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, len(file_paths), self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файлов")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)

        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        # Загружаем файлы на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(current, total, fname, phase):
                    if progress.wasCanceled():
                        return
                    progress.setValue(current)
                    percent = int((current / total) * 100)
                    progress.setLabelText(f"Загрузка: {fname}\n({current}/{total} файлов - {percent}%)")

                # Загружаем файлы
                uploaded_files = yd.upload_stage_files(
                    file_paths,
                    contract_folder,
                    'photo_documentation',
                    progress_callback=update_progress
                )

                if uploaded_files:
                    progress.setValue(len(file_paths))
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)

                    # Получаем ссылку на папку
                    folder_path = yd.get_stage_folder_path(contract_folder, 'photo_documentation')
                    folder_link = yd.get_public_link(folder_path)

                    # Отправляем сигнал в главный поток
                    self.photo_doc_upload_completed.emit(folder_link if folder_link else folder_path, contract_id)
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.photo_doc_upload_error.emit("Не удалось загрузить файлы на Яндекс.Диск")

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                self.photo_doc_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_photo_doc_uploaded(self, folder_link, contract_id):
        """Обработчик успешной загрузки фотофиксации"""
        # Обновляем БД
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('UPDATE contracts SET photo_documentation_yandex_path = ? WHERE id = ?', (folder_link, contract_id))
        conn.commit()
        conn.close()

        # Обновляем лейбл
        self.project_data_photo_doc_label.setText(f'<a href="{folder_link}">Открыть папку с фотофиксацией</a>')

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = f"Добавлены файлы в Фотофиксацию"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_upload',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            print(f"[OK] Добавлена запись в историю: {description}")

    def _on_photo_doc_upload_error(self, error_msg):
        """Обработчик ошибки загрузки фотофиксации"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов: {error_msg}', 'error').exec_()

    def add_measurement(self):
        """Добавить замер с загрузкой изображения"""
        dialog = MeasurementDialog(self, self.card_data.get('id'), self.employee)
        if dialog.exec_() == QDialog.Accepted:
            # Обновляем только labels с данными о замере без перезагрузки вкладки
            self.reload_measurement_data()

    def reload_measurement_data(self):
        """Обновить данные о замере в labels"""
        # Получаем contract_id - может быть как из contract_data, так и из card_data
        contract_id = None
        card_id = None
        if hasattr(self, 'contract_data') and self.contract_data:
            contract_id = self.contract_data.get('id')
        elif hasattr(self, 'card_data') and self.card_data:
            contract_id = self.card_data.get('contract_id')
            card_id = self.card_data.get('id')

        if not contract_id:
            return

        # Получаем данные замера из базы
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT measurement_image_link, measurement_file_name, measurement_date FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()

        if result:
            # Обновляем изображение замера
            if result['measurement_image_link']:
                measurement_link = result['measurement_image_link']
                # Используем сохраненное имя файла, если оно есть
                file_name = result['measurement_file_name'] if result['measurement_file_name'] else 'Замер'
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{measurement_link}" title="{file_name}">{truncated_name}</a>'
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText(html_link)
            else:
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText('Не загружен')

            # Обновляем дату замера
            if result['measurement_date']:
                from datetime import datetime
                try:
                    measurement_date = datetime.strptime(result['measurement_date'], '%Y-%m-%d')
                    date_str = measurement_date.strftime('%d.%m.%Y')
                    # Обновляем дату в "Данные по проекту"
                    if hasattr(self, 'project_data_survey_date_label'):
                        self.project_data_survey_date_label.setText(date_str)
                    # Обновляем дату в "Редактирование"
                    if hasattr(self, 'survey_date_label'):
                        self.survey_date_label.setText(date_str)
                except:
                    if hasattr(self, 'project_data_survey_date_label'):
                        self.project_data_survey_date_label.setText('Не установлена')
                    if hasattr(self, 'survey_date_label'):
                        self.survey_date_label.setText('Не установлена')
            else:
                if hasattr(self, 'project_data_survey_date_label'):
                    self.project_data_survey_date_label.setText('Не установлена')
                if hasattr(self, 'survey_date_label'):
                    self.survey_date_label.setText('Не установлена')

        # Обновляем surveyor в вкладке редактирования
        if card_id and hasattr(self, 'surveyor'):
            cursor.execute('SELECT surveyor_id FROM crm_cards WHERE id = ?', (card_id,))
            surveyor_id_result = cursor.fetchone()
            if surveyor_id_result and surveyor_id_result['surveyor_id']:
                self.set_combo_by_id(self.surveyor, surveyor_id_result['surveyor_id'])

        conn.close()

    def delete_tech_task_file(self):
        """Удалить файл ТЗ из базы данных и с Яндекс.Диска"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить файл ТЗ?'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        # Получаем contract_id
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        # Получаем путь к файлу на Яндекс.Диске перед удалением из БД
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT tech_task_yandex_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        yandex_path = result['tech_task_yandex_path'] if result and result['tech_task_yandex_path'] else None

        # Удаляем все поля тех.задания из БД
        cursor.execute('''
            UPDATE contracts
            SET tech_task_link = NULL,
                tech_task_yandex_path = NULL,
                tech_task_file_name = NULL
            WHERE id = ?
        ''', (contract_id,))
        cursor.execute('UPDATE crm_cards SET tech_task_file = NULL WHERE contract_id = ?', (contract_id,))
        conn.commit()
        conn.close()

        # Удаляем файл с Яндекс.Диска
        if yandex_path:
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                yd.delete_file(yandex_path)
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = "Удален файл ТЗ"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_delete',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_tz_file_label'):
            self.project_data_tz_file_label.setText('Не загружен')
        if hasattr(self, 'upload_tz_btn'):
            self.upload_tz_btn.setEnabled(True)  # Активируем кнопку загрузки

        CustomMessageBox(self, 'Успех', 'Файл ТЗ успешно удален', 'success').exec_()

        # Отправляем сигнал для обновления UI (чтобы другие открытые окна тоже обновились)
        # Делаем это после закрытия MessageBox чтобы избежать конфликтов
        self.files_verification_completed.emit()

    def delete_references_folder(self):
        """Удалить папку с референсами из базы данных и с Яндекс.Диска"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить ВСЕ референсы?\nВся папка будет удалена с Яндекс.Диска.'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        # Получаем contract_id
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        # Получаем путь к папке на Яндекс.Диске перед удалением из БД
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path, references_yandex_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()

        contract_folder = result['yandex_folder_path'] if result and result['yandex_folder_path'] else None

        # Удаляем поле из БД
        cursor.execute('UPDATE contracts SET references_yandex_path = NULL WHERE id = ?', (contract_id,))
        conn.commit()
        conn.close()

        # Удаляем папку с Яндекс.Диска
        if contract_folder:
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                folder_path = yd.get_stage_folder_path(contract_folder, 'references')
                if folder_path:
                    yd.delete_folder(folder_path)
            except Exception as e:
                print(f"[WARN] Не удалось удалить папку с Яндекс.Диска: {e}")

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = "Удалена папка с референсами"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_delete',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_references_label'):
            self.project_data_references_label.setText('Не загружена')

        CustomMessageBox(self, 'Успех', 'Папка с референсами успешно удалена', 'success').exec_()
        self.files_verification_completed.emit()

    def delete_photo_documentation_folder(self):
        """Удалить папку с фотофиксацией из базы данных и с Яндекс.Диска"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить ВСЮ фотофиксацию?\nВся папка будет удалена с Яндекс.Диска.'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        # Получаем contract_id
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        # Получаем путь к папке на Яндекс.Диске перед удалением из БД
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path, photo_documentation_yandex_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()

        contract_folder = result['yandex_folder_path'] if result and result['yandex_folder_path'] else None

        # Удаляем поле из БД
        cursor.execute('UPDATE contracts SET photo_documentation_yandex_path = NULL WHERE id = ?', (contract_id,))
        conn.commit()
        conn.close()

        # Удаляем папку с Яндекс.Диска
        if contract_folder:
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                folder_path = yd.get_stage_folder_path(contract_folder, 'photo_documentation')
                if folder_path:
                    yd.delete_folder(folder_path)
            except Exception as e:
                print(f"[WARN] Не удалось удалить папку с Яндекс.Диска: {e}")

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = "Удалена папка с фотофиксацией"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_delete',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_photo_doc_label'):
            self.project_data_photo_doc_label.setText('Не загружена')

        CustomMessageBox(self, 'Успех', 'Папка с фотофиксацией успешно удалена', 'success').exec_()
        self.files_verification_completed.emit()

    # ========== МЕТОДЫ ДЛЯ РАБОТЫ С ШАБЛОНАМИ ПРОЕКТОВ ==========

    def add_project_templates(self):
        """Добавление ссылок на шаблоны проекта"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QFrame, QScrollArea

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setMinimumWidth(600)

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
        border_layout.setContentsMargins(10, 10, 10, 10)
        border_layout.setSpacing(0)

        # Title bar
        title_bar = CustomTitleBar(dialog, "Добавить шаблоны проекта", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")
        content_layout = QVBoxLayout()
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(20, 20, 20, 20)

        # Заголовок
        header_label = QLabel('Добавьте ссылки на шаблоны (можно добавить несколько)')
        header_label.setStyleSheet('font-weight: bold; font-size: 12px; color: #2C3E50;')
        content_layout.addWidget(header_label)

        # Скроллируемая область для полей ввода
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setMaximumHeight(300)

        # Контейнер для полей ввода ссылок
        self.template_inputs_container = QWidget()
        self.template_inputs_layout = QVBoxLayout()
        self.template_inputs_layout.setSpacing(10)
        self.template_inputs_container.setLayout(self.template_inputs_layout)

        scroll_area.setWidget(self.template_inputs_container)
        content_layout.addWidget(scroll_area)

        # Добавляем первое поле ввода
        self.template_input_fields = []
        self.add_template_input_field()

        # Кнопка добавить еще поле
        add_more_btn = QPushButton('+ Добавить еще ссылку')
        add_more_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                padding: 8px 15px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        add_more_btn.clicked.connect(self.add_template_input_field)
        content_layout.addWidget(add_more_btn)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        save_btn.clicked.connect(lambda: self.save_project_templates(dialog))

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 25px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        content_layout.addLayout(buttons_layout)

        content_widget.setLayout(content_layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)

        dialog.setLayout(main_layout)
        dialog.exec_()

    def add_template_input_field(self):
        """Добавление поля ввода для ссылки на шаблон"""
        from PyQt5.QtWidgets import QHBoxLayout, QLineEdit, QPushButton

        row = QHBoxLayout()

        input_field = QLineEdit()
        input_field.setPlaceholderText('Введите URL ссылки на шаблон')
        input_field.setStyleSheet('''
            QLineEdit {
                padding: 6px;
                border: 1px solid #DDD;
                border-radius: 3px;
                font-size: 10px;
            }
        ''')
        row.addWidget(input_field, 1)

        # Кнопка удаления поля (показывается только если полей больше одного)
        if len(self.template_input_fields) > 0:
            remove_btn = QPushButton('X')
            remove_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                }
            """)
            remove_btn.clicked.connect(lambda: self.remove_template_input_field(row, input_field))
            row.addWidget(remove_btn)

        self.template_inputs_layout.addLayout(row)
        self.template_input_fields.append(input_field)

    def remove_template_input_field(self, row, input_field):
        """Удаление поля ввода для ссылки"""
        # Удаляем виджеты из layout
        while row.count():
            item = row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Удаляем сам layout
        self.template_inputs_layout.removeItem(row)

        # Удаляем поле из списка
        if input_field in self.template_input_fields:
            self.template_input_fields.remove(input_field)

    def save_project_templates(self, dialog):
        """Сохранение ссылок на шаблоны в БД"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        # Собираем все непустые ссылки
        template_urls = []
        for input_field in self.template_input_fields:
            url = input_field.text().strip()
            if url:
                template_urls.append(url)

        if not template_urls:
            CustomMessageBox(self, 'Внимание', 'Введите хотя бы одну ссылку', 'warning').exec_()
            return

        # Сохраняем в БД
        for url in template_urls:
            self.db.add_project_template(contract_id, url)

        dialog.accept()

        # Обновляем список ссылок в UI
        self.load_project_templates()

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = f"Добавлены ссылки на шаблоны проекта ({len(template_urls)} шт.)"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_upload',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            print(f"[OK] Добавлена запись в историю: {description}")

        CustomMessageBox(self, 'Успех', f'Добавлено ссылок: {len(template_urls)}', 'success').exec_()

    def load_project_templates(self):
        """Загрузка и отображение ссылок на шаблоны"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Получаем ссылки из БД
        templates = self.db.get_project_templates(contract_id)

        # Очищаем контейнер
        layout = self.templates_container.layout()
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Если шаблонов нет
        if not templates:
            empty_label = QLabel('Нет добавленных шаблонов')
            empty_label.setStyleSheet('color: #999; font-size: 10px; padding: 10px;')
            layout.addWidget(empty_label)
            return

        # Добавляем каждую ссылку
        for template in templates:
            self.create_template_link_widget(template, layout)

    def create_template_link_widget(self, template, parent_layout):
        """Создание виджета для отображения одной ссылки на шаблон"""
        from PyQt5.QtWidgets import QHBoxLayout, QLabel, QPushButton, QFrame

        row = QHBoxLayout()
        row.setSpacing(8)

        # Контейнер для ссылки
        link_label = QLabel(f'<a href="{template["template_url"]}">{template["template_url"]}</a>')
        link_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                font-size: 10px;
            }
            QLabel a {
                color: #3498DB;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        link_label.setOpenExternalLinks(True)
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_label.setCursor(QCursor(Qt.PointingHandCursor))
        link_label.setWordWrap(True)
        row.addWidget(link_label, 1)

        # Кнопка удаления (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            delete_btn = QPushButton('X')
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 4px 8px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                    color: #C0392B;
                    border: 1px solid #C0392B;
                }
            """)
            delete_btn.setToolTip('Удалить ссылку')
            delete_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_btn.clicked.connect(lambda: self.delete_project_template(template['id']))
            row.addWidget(delete_btn)

        # Добавляем row в контейнер
        widget = QWidget()
        widget.setLayout(row)
        parent_layout.addWidget(widget)

    def delete_project_template(self, template_id):
        """Удаление ссылки на шаблон"""
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить эту ссылку на шаблон?'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        # Удаляем из БД
        success = self.db.delete_project_template(template_id)

        if success:
            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime
                description = "Удалена ссылка на шаблон проекта"

                self.db.add_action_history(
                    user_id=self.employee.get('id'),
                    action_type='file_delete',
                    entity_type='crm_card',
                    entity_id=self.card_data['id'],
                    description=description
                )
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"[OK] Добавлена запись в историю: {description}")

            # Обновляем список в UI
            self.load_project_templates()
            CustomMessageBox(self, 'Успех', 'Ссылка удалена', 'success').exec_()
        else:
            CustomMessageBox(self, 'Ошибка', 'Не удалось удалить ссылку', 'error').exec_()

    # ==========================================================

    def delete_measurement_file(self):
        """Удалить изображение замера из базы данных и с Яндекс.Диска"""
        # Подтверждение удаления
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вы уверены, что хотите удалить изображение замера?'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        # Получаем contract_id
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        # Получаем путь к файлу на Яндекс.Диске перед удалением из БД
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT measurement_yandex_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        yandex_path = result['measurement_yandex_path'] if result and result['measurement_yandex_path'] else None

        # Удаляем данные из БД
        cursor.execute('''
            UPDATE contracts
            SET measurement_image_link = NULL,
                measurement_yandex_path = NULL,
                measurement_file_name = NULL,
                measurement_date = NULL
            WHERE id = ?
        ''', (contract_id,))
        conn.commit()
        conn.close()

        # Удаляем файл с Яндекс.Диска
        if yandex_path:
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                yd.delete_file(yandex_path)
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = "Удален файл замера"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_delete',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_survey_file_label'):
            self.project_data_survey_file_label.setText('Не загружен')
        if hasattr(self, 'project_data_survey_date_label'):
            self.project_data_survey_date_label.setText('Не установлена')
        if hasattr(self, 'upload_survey_btn'):
            self.upload_survey_btn.setEnabled(True)  # Активируем кнопку загрузки

        CustomMessageBox(self, 'Успех', 'Изображение замера успешно удалено', 'success').exec_()

        # Отправляем сигнал для обновления UI (чтобы другие открытые окна тоже обновились)
        # Делаем это после закрытия MessageBox чтобы избежать конфликтов
        self.files_verification_completed.emit()

    def edit_tech_task_file(self):
        """Открывает диалог для изменения файла ТЗ"""

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #2C3E50;
                border-radius: 8px;
            }
        """)
        dialog.setFixedWidth(500)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Добавляем заголовок (простой режим - только кнопка закрыть)
        title_bar = CustomTitleBar(dialog, "Изменить файл ТЗ", simple_mode=True)
        layout.addWidget(title_bar)

        # Контент
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Поле URL
        url_label = QLabel('Ссылка на файл ТЗ:')
        url_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(url_label)

        url_input = QLineEdit()
        url_input.setPlaceholderText('Введите URL файла...')
        url_input.setStyleSheet("""
            QLineEdit {
                padding: 8px;
                border: 1px solid #BDC3C7;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QLineEdit:focus {
                border: 2px solid #3498DB;
            }
        """)

        # Устанавливаем текущий URL
        current_file = self.card_data.get('tech_task_file', '')
        url_input.setText(current_file)

        content_layout.addWidget(url_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A085;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #138D75; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_tech_task_file():
            try:
                file_url = url_input.text().strip()

                # Обновляем в БД
                updates = {'tech_task_file': file_url}
                self.db.update_crm_card(self.card_data['id'], updates)
                self.card_data['tech_task_file'] = file_url

                # Обновляем label
                if file_url:
                    self.tech_task_file_label.setText(f'<a href="{file_url}">{file_url}</a>')
                else:
                    self.tech_task_file_label.setText('Не загружен')

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_project_info_tab()

                CustomMessageBox(dialog, 'Успех', 'Файл ТЗ обновлен', 'success').exec_()
                dialog.accept()

            except Exception as e:
                print(f" Ошибка изменения файла ТЗ: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(dialog, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

        save_btn.clicked.connect(save_tech_task_file)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        layout.addLayout(content_layout)

        dialog.exec_()

    def edit_tech_task_date(self):
        """Открывает диалог для изменения даты ТЗ"""
        from PyQt5.QtCore import QDate
        from utils.calendar_styles import add_today_button_to_dateedit

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 8px;
            }
        """)
        dialog.setFixedWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Добавляем заголовок (простой режим - только кнопка закрыть)
        title_bar = CustomTitleBar(dialog, "Изменить дату ТЗ", simple_mode=True)
        layout.addWidget(title_bar)

        # Контент
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Поле даты
        date_label = QLabel('Дата ТЗ:')
        date_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(date_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QDateEdit:focus {
                border: 2px solid #3498DB;
            }
        """)

        # Добавляем кастомный календарь с кнопкой "Сегодня"
        add_today_button_to_dateedit(date_input)

        # Устанавливаем текущую дату или сегодня
        if self.card_data.get('tech_task_date'):
            try:
                from datetime import datetime
                tz_date = datetime.strptime(self.card_data['tech_task_date'], '%Y-%m-%d')
                date_input.setDate(QDate(tz_date.year, tz_date.month, tz_date.day))
            except:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_tech_task_date():
            try:
                selected_date = date_input.date()
                date_str = selected_date.toString('yyyy-MM-dd')

                # Обновляем в БД crm_cards
                updates = {'tech_task_date': date_str}
                self.db.update_crm_card(self.card_data['id'], updates)
                self.card_data['tech_task_date'] = date_str

                # Обновляем label в вкладке "Исполнители и дедлайн"
                if hasattr(self, 'tech_task_date_label'):
                    self.tech_task_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем label в вкладке "Данные по проекту"
                if hasattr(self, 'project_data_tz_date_label'):
                    self.project_data_tz_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_project_info_tab()

                CustomMessageBox(dialog, 'Успех', f'Дата ТЗ изменена: {selected_date.toString("dd.MM.yyyy")}', 'success').exec_()
                dialog.accept()

            except Exception as e:
                print(f" Ошибка изменения даты ТЗ: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(dialog, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

        save_btn.clicked.connect(save_tech_task_date)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        layout.addLayout(content_layout)

        dialog.exec_()

    def edit_measurement_date(self):
        """Открывает диалог для изменения даты замера"""
        from PyQt5.QtCore import QDate
        from utils.calendar_styles import add_today_button_to_dateedit

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 8px;
            }
        """)
        dialog.setFixedWidth(400)

        layout = QVBoxLayout(dialog)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Добавляем заголовок (простой режим - только кнопка закрыть)
        title_bar = CustomTitleBar(dialog, "Изменить данные замера", simple_mode=True)
        layout.addWidget(title_bar)

        # Контент
        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Поле замерщика
        surveyor_label = QLabel('Замерщик:')
        surveyor_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(surveyor_label)

        surveyor_input = CustomComboBox()
        surveyor_input.setFixedHeight(36)
        surveyors = self.db.get_employees_by_position('Замерщик')
        surveyor_input.addItem('Не назначен', None)
        for surv in surveyors:
            surveyor_input.addItem(surv['full_name'], surv['id'])

        # Устанавливаем текущего замерщика
        if self.card_data.get('surveyor_id'):
            for i in range(surveyor_input.count()):
                if surveyor_input.itemData(i) == self.card_data.get('surveyor_id'):
                    surveyor_input.setCurrentIndex(i)
                    break

        surveyor_input.setStyleSheet("""
            QComboBox {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QComboBox:focus {
                border: 2px solid #3498DB;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        content_layout.addWidget(surveyor_input)

        # Поле даты
        date_label = QLabel('Дата замера:')
        date_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(date_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
            }
            QDateEdit:focus {
                border: 2px solid #3498DB;
            }
        """)

        # Добавляем кастомный календарь с кнопкой "Сегодня"
        add_today_button_to_dateedit(date_input)

        # Устанавливаем текущую дату или сегодня
        if self.card_data.get('survey_date'):
            try:
                from datetime import datetime
                survey_date = datetime.strptime(self.card_data['survey_date'], '%Y-%m-%d')
                date_input.setDate(QDate(survey_date.year, survey_date.month, survey_date.day))
            except:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_measurement_date():
            try:
                selected_date = date_input.date()
                date_str = selected_date.toString('yyyy-MM-dd')
                surveyor_id = surveyor_input.currentData()

                # Обновляем в БД - и crm_cards, и contracts
                updates = {
                    'survey_date': date_str,
                    'surveyor_id': surveyor_id
                }
                self.db.update_crm_card(self.card_data['id'], updates)
                self.card_data['survey_date'] = date_str
                self.card_data['surveyor_id'] = surveyor_id

                # Обновляем contracts.measurement_date
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE contracts
                        SET measurement_date = ?
                        WHERE id = ?
                    ''', (date_str, contract_id))
                    conn.commit()
                    self.db.close()

                # Обновляем оба label - в данных по проекту и в редактировании
                self.project_data_survey_date_label.setText(selected_date.toString('dd.MM.yyyy'))
                if hasattr(self, 'survey_date_label'):
                    self.survey_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем surveyor ComboBox в вкладке редактирования
                if hasattr(self, 'surveyor'):
                    self.set_combo_by_id(self.surveyor, surveyor_id)

                # Вызываем reload_measurement_data для обновления всех данных замера
                self.reload_measurement_data()

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_project_info_tab()

                CustomMessageBox(dialog, 'Успех', 'Данные замера успешно обновлены', 'success').exec_()
                dialog.accept()

            except Exception as e:
                print(f" Ошибка изменения данных замера: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(dialog, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

        save_btn.clicked.connect(save_measurement_date)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        layout.addLayout(content_layout)

        dialog.exec_()

    def refresh_payments_tab(self):
        """ИСПРАВЛЕНИЕ: Обновление вкладки оплат после изменений"""
        if self.payments_tab_index >= 0:
            try:
                # ИСПРАВЛЕНИЕ: Сохраняем текущую активную вкладку
                current_tab_index = self.tabs.currentIndex()

                # Удаляем старую вкладку
                old_widget = self.tabs.widget(self.payments_tab_index)
                self.tabs.removeTab(self.payments_tab_index)
                if old_widget:
                    old_widget.deleteLater()

                # Создаем новую вкладку с обновленными данными
                payments_widget = self.create_payments_tab()
                self.tabs.insertTab(self.payments_tab_index, payments_widget, '💰 Оплаты')

                # ИСПРАВЛЕНИЕ: Возвращаемся на вкладку оплат, если она была активна
                if current_tab_index == self.payments_tab_index:
                    self.tabs.setCurrentIndex(self.payments_tab_index)

                print(f"✓ Вкладка оплат обновлена")
            except Exception as e:
                print(f" Ошибка обновления вкладки оплат: {e}")

    def refresh_project_info_tab(self):
        """ИСПРАВЛЕНИЕ: Обновление вкладки информации о проекте"""
        if hasattr(self, 'project_info_tab_index') and self.project_info_tab_index >= 0:
            try:
                # Удаляем старую вкладку
                old_widget = self.tabs.widget(self.project_info_tab_index)
                self.tabs.removeTab(self.project_info_tab_index)
                if old_widget:
                    old_widget.deleteLater()

                # Создаем новую вкладку с обновленными данными
                info_widget = self.create_project_info_widget()
                self.tabs.insertTab(self.project_info_tab_index, info_widget, 'Информация о проекте')

                print(f"✓ Вкладка информации о проекте обновлена")
            except Exception as e:
                print(f" Ошибка обновления вкладки информации: {e}")

    def create_project_data_widget(self):
        """Создание виджета данных по проекту"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 20)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Импорты для секций
        from PyQt5.QtWidgets import QGroupBox
        from ui.file_list_widget import FileListWidget
        from ui.file_gallery_widget import FileGalleryWidget
        from ui.variation_gallery_widget import VariationGalleryWidget

        # Заголовок
        # ========== СЕКЦИЯ: ТЗ И ЗАМЕР (ПАРАЛЛЕЛЬНО) ==========
        tz_survey_row = QHBoxLayout()
        tz_survey_row.setSpacing(10)
        tz_survey_row.setAlignment(Qt.AlignTop)  # Выравнивание по верхнему краю

        # ========== ЛЕВЫЙ БЛОК: ТЕХНИЧЕСКОЕ ЗАДАНИЕ ==========
        tz_group = QGroupBox("Техническое задание")
        tz_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: #2C3E50;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 15px;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 5px;
            }
        """)
        tz_layout = QVBoxLayout()
        tz_layout.setSpacing(8)

        # Файл ТЗ
        tz_file_row = QHBoxLayout()
        tz_file_row.setSpacing(8)

        self.project_data_tz_file_label = QLabel('Не загружен')
        self.project_data_tz_file_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                font-size: 10px;
            }
            QLabel a {
                color: #3498DB;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.project_data_tz_file_label.setWordWrap(False)
        self.project_data_tz_file_label.setFixedHeight(28)  # Фиксированная высота для выравнивания
        self.project_data_tz_file_label.setTextFormat(Qt.RichText)  # Поддержка HTML для отображения ссылок
        self.project_data_tz_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.LinksAccessibleByMouse)
        self.project_data_tz_file_label.setOpenExternalLinks(True)
        self.project_data_tz_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        # ИСПРАВЛЕНИЕ: Добавляем обрезку текста с троеточием через CSS
        self.project_data_tz_file_label.setProperty('class', 'ellipsis-label')
        tz_file_row.addWidget(self.project_data_tz_file_label, 1)

        # Кнопка загрузки ТЗ (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            self.upload_tz_btn = QPushButton('Загрузить PDF')
            self.upload_tz_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            self.upload_tz_btn.setFixedHeight(28)
            self.upload_tz_btn.clicked.connect(self.upload_project_tech_task_file)
            tz_file_row.addWidget(self.upload_tz_btn)

        # Кнопка удаления ТЗ (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            delete_tz_btn = QPushButton('X')
            delete_tz_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 4px 4px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                    color: #C0392B;
                    border: 1px solid #C0392B;
                }
            """)
            delete_tz_btn.setFixedSize(28, 28)
            delete_tz_btn.setToolTip('Удалить файл ТЗ')
            delete_tz_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_tz_btn.clicked.connect(self.delete_tech_task_file)
            tz_file_row.addWidget(delete_tz_btn)

        tz_layout.addLayout(tz_file_row)

        hint_tz_file = QLabel('💡 PDF файл с техническим заданием')
        hint_tz_file.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        tz_layout.addWidget(hint_tz_file)

        # Дата ТЗ
        tz_date_row = QHBoxLayout()
        tz_date_row.setSpacing(8)

        self.project_data_tz_date_label = QLabel('Не установлена')
        self.project_data_tz_date_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                font-size: 10px;
            }
        ''')
        tz_date_row.addWidget(self.project_data_tz_date_label, 1)

        # Кнопка изменения даты ТЗ (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            edit_tz_date_btn = QPushButton('Изменить дату')
            edit_tz_date_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            edit_tz_date_btn.setFixedHeight(28)
            edit_tz_date_btn.clicked.connect(self.edit_tech_task_date)
            tz_date_row.addWidget(edit_tz_date_btn)

        tz_layout.addLayout(tz_date_row)

        hint_tz_date = QLabel('💡 Дата утверждения технического задания')
        hint_tz_date.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        tz_layout.addWidget(hint_tz_date)

        tz_group.setLayout(tz_layout)
        # ИСПРАВЛЕНИЕ: Устанавливаем размеры для группы ТЗ чтобы она занимала строго 50%
        tz_group.setMinimumWidth(200)  # Минимальная ширина для читаемости
        tz_survey_row.addWidget(tz_group, 1)  # Занимает 1 часть (50%)

        # ========== ПРАВЫЙ БЛОК: ЗАМЕР ==========
        survey_group = QGroupBox("Замер")
        survey_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: #2C3E50;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 15px;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 5px;
            }
        """)
        survey_layout = QVBoxLayout()
        survey_layout.setSpacing(8)

        # Файл изображения замера
        survey_file_row = QHBoxLayout()
        survey_file_row.setSpacing(8)

        self.project_data_survey_file_label = QLabel('Не загружен')
        self.project_data_survey_file_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                font-size: 10px;
            }
            QLabel a {
                color: #3498DB;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.project_data_survey_file_label.setWordWrap(False)
        self.project_data_survey_file_label.setFixedHeight(28)
        self.project_data_survey_file_label.setTextFormat(Qt.RichText)  # Поддержка HTML для отображения ссылок
        self.project_data_survey_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.LinksAccessibleByMouse)
        self.project_data_survey_file_label.setOpenExternalLinks(True)
        self.project_data_survey_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        # ИСПРАВЛЕНИЕ: Добавляем обрезку текста с троеточием через CSS
        self.project_data_survey_file_label.setProperty('class', 'ellipsis-label')
        survey_file_row.addWidget(self.project_data_survey_file_label, 1)

        # Кнопка загрузки замера (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            self.upload_survey_btn = QPushButton('Добавить замер')
            self.upload_survey_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            self.upload_survey_btn.setFixedHeight(28)
            self.upload_survey_btn.clicked.connect(self.add_measurement)
            survey_file_row.addWidget(self.upload_survey_btn)

        # Кнопка удаления замера (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            delete_survey_btn = QPushButton('X')
            delete_survey_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 4px 4px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                    color: #C0392B;
                    border: 1px solid #C0392B;
                }
            """)
            delete_survey_btn.setFixedSize(28, 28)
            delete_survey_btn.setToolTip('Удалить изображение замера')
            delete_survey_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_survey_btn.clicked.connect(self.delete_measurement_file)
            survey_file_row.addWidget(delete_survey_btn)

        survey_layout.addLayout(survey_file_row)

        hint_survey_file = QLabel('💡 Фотография или сканированный лист замера')
        hint_survey_file.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        survey_layout.addWidget(hint_survey_file)

        # Дата замера
        survey_date_row = QHBoxLayout()
        survey_date_row.setSpacing(8)

        self.project_data_survey_date_label = QLabel('Не установлена')
        self.project_data_survey_date_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                font-size: 10px;
            }
        ''')
        survey_date_row.addWidget(self.project_data_survey_date_label, 1)

        # Кнопка изменения даты замера (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            edit_survey_date_btn = QPushButton('Изменить дату')
            edit_survey_date_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            edit_survey_date_btn.setFixedHeight(28)
            edit_survey_date_btn.clicked.connect(self.edit_measurement_date)
            survey_date_row.addWidget(edit_survey_date_btn)

        survey_layout.addLayout(survey_date_row)

        hint_survey_date = QLabel('💡 Дата выполнения замера объекта')
        hint_survey_date.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        survey_layout.addWidget(hint_survey_date)

        survey_group.setLayout(survey_layout)
        # ИСПРАВЛЕНИЕ: Устанавливаем размеры для группы Замера чтобы она занимала строго 50%
        survey_group.setMinimumWidth(200)  # Минимальная ширина для читаемости
        tz_survey_row.addWidget(survey_group, 1)  # Занимает 1 часть (50%)

        form_layout.addRow(tz_survey_row)

        # ========== РЕФЕРЕНСЫ/ШАБЛОНЫ И ФОТОФИКСАЦИЯ ==========
        ref_photo_row = QHBoxLayout()
        ref_photo_row.setSpacing(10)
        ref_photo_row.setAlignment(Qt.AlignTop)  # Выравнивание по верхнему краю

        # Проверяем тип проекта
        project_type = self.card_data.get('project_type', 'Индивидуальный')

        # ========== ЛЕВЫЙ БЛОК: РЕФЕРЕНСЫ (для индивидуальных) ИЛИ ШАБЛОНЫ ПРОЕКТА (для шаблонных) ==========
        if project_type == 'Шаблонный':
            # Блок "Шаблоны проекта" для шаблонных проектов
            references_group = QGroupBox("Шаблоны проекта")
        else:
            # Блок "Референсы" для индивидуальных проектов
            references_group = QGroupBox("Референсы")
        references_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: #2C3E50;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 15px;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 5px;
            }
        """)
        references_layout = QVBoxLayout()
        references_layout.setSpacing(8)

        if project_type == 'Шаблонный':
            # ===== ДЛЯ ШАБЛОННЫХ ПРОЕКТОВ: СПИСОК ССЫЛОК НА ШАБЛОНЫ =====

            # Контейнер для списка ссылок
            self.templates_container = QWidget()
            templates_list_layout = QVBoxLayout()
            templates_list_layout.setSpacing(4)
            templates_list_layout.setContentsMargins(0, 0, 0, 0)
            self.templates_container.setLayout(templates_list_layout)

            # Скролл для списка ссылок
            templates_scroll = QScrollArea()
            templates_scroll.setWidget(self.templates_container)
            templates_scroll.setWidgetResizable(True)
            templates_scroll.setFrameShape(QFrame.NoFrame)
            templates_scroll.setMaximumHeight(150)
            references_layout.addWidget(templates_scroll)

            # Кнопка добавления шаблонов (только для Руководителя, Старшего менеджера и Менеджера)
            if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
                add_template_btn = QPushButton('Загрузить шаблоны')
                add_template_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95a5a6;
                        color: white;
                        padding: 6px 10px;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover { background-color: #7f8c8d; }
                """)
                add_template_btn.setFixedHeight(28)
                add_template_btn.clicked.connect(self.add_project_templates)
                references_layout.addWidget(add_template_btn)

            hint_templates = QLabel('💡 Ссылки на используемые в проекте шаблоны')
            hint_templates.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
            references_layout.addWidget(hint_templates)

            # Загружаем существующие шаблоны из БД
            self.load_project_templates()

        else:
            # ===== ДЛЯ ИНДИВИДУАЛЬНЫХ ПРОЕКТОВ: ССЫЛКА НА ПАПКУ С РЕФЕРЕНСАМИ =====

            # Ссылка на папку с референсами
            ref_folder_row = QHBoxLayout()
            ref_folder_row.setSpacing(8)

            self.project_data_references_label = QLabel('Не загружена')
            self.project_data_references_label.setStyleSheet('''
                QLabel {
                    background-color: #F8F9FA;
                    padding: 6px 10px;
                    border: 1px solid #E0E0E0;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QLabel a {
                    color: #3498DB;
                    text-decoration: none;
                }
                QLabel a:hover {
                    color: #2980B9;
                    text-decoration: underline;
                }
            ''')
            self.project_data_references_label.setWordWrap(False)
            self.project_data_references_label.setOpenExternalLinks(True)
            self.project_data_references_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.project_data_references_label.setCursor(QCursor(Qt.PointingHandCursor))
            ref_folder_row.addWidget(self.project_data_references_label, 1)

            # Кнопка загрузки референсов (только для Руководителя, Старшего менеджера и Менеджера)
            if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
                self.upload_references_btn = QPushButton('Загрузить файлы')
                self.upload_references_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95a5a6;
                        color: white;
                        padding: 6px 10px;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover { background-color: #7f8c8d; }
                """)
                self.upload_references_btn.setFixedHeight(28)
                self.upload_references_btn.clicked.connect(self.upload_references_files)
                ref_folder_row.addWidget(self.upload_references_btn)

            # Кнопка удаления референсов (только для Руководителя, Старшего менеджера и Менеджера)
            if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
                delete_references_btn = QPushButton('X')
                delete_references_btn.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        color: #E74C3C;
                        border: 1px solid #E74C3C;
                        border-radius: 3px;
                        font-size: 12px;
                        font-weight: bold;
                        padding: 4px 4px;
                    }
                    QPushButton:hover {
                        background-color: #FFE5E5;
                        color: #C0392B;
                        border: 1px solid #C0392B;
                    }
                """)
                delete_references_btn.setFixedSize(28, 28)
                delete_references_btn.setToolTip('Удалить все референсы')
                delete_references_btn.setCursor(QCursor(Qt.PointingHandCursor))
                delete_references_btn.clicked.connect(self.delete_references_folder)
                ref_folder_row.addWidget(delete_references_btn)

            references_layout.addLayout(ref_folder_row)

            hint_references = QLabel('💡 Изображения и PDF файлы с референсами')
            hint_references.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
            references_layout.addWidget(hint_references)

        references_group.setLayout(references_layout)
        ref_photo_row.addWidget(references_group, 1)  # Занимает 1 часть (50%)

        # ========== ПРАВЫЙ БЛОК: ФОТОФИКСАЦИЯ ==========
        photo_doc_group = QGroupBox("Фотофиксация")
        photo_doc_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: #2C3E50;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 15px;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 5px;
            }
        """)
        photo_doc_layout = QVBoxLayout()
        photo_doc_layout.setSpacing(8)

        # Ссылка на папку с фотофиксацией
        photo_doc_folder_row = QHBoxLayout()
        photo_doc_folder_row.setSpacing(8)

        self.project_data_photo_doc_label = QLabel('Не загружена')
        self.project_data_photo_doc_label.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 6px 10px;
                border: 1px solid #E0E0E0;
                border-radius: 3px;
                font-size: 10px;
            }
            QLabel a {
                color: #3498DB;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.project_data_photo_doc_label.setWordWrap(False)
        self.project_data_photo_doc_label.setOpenExternalLinks(True)
        self.project_data_photo_doc_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.project_data_photo_doc_label.setCursor(QCursor(Qt.PointingHandCursor))
        photo_doc_folder_row.addWidget(self.project_data_photo_doc_label, 1)

        # Кнопка загрузки фотофиксации (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            self.upload_photo_doc_btn = QPushButton('Загрузить файлы')
            self.upload_photo_doc_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 6px 10px;
                    border-radius: 3px;
                    font-size: 10px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            self.upload_photo_doc_btn.setFixedHeight(28)
            self.upload_photo_doc_btn.clicked.connect(self.upload_photo_documentation_files)
            photo_doc_folder_row.addWidget(self.upload_photo_doc_btn)

        # Кнопка удаления фотофиксации (только для Руководителя, Старшего менеджера и Менеджера)
        if self.employee and self.employee.get('position') in ['Руководитель студии', 'Старший менеджер проектов', 'Менеджер']:
            delete_photo_doc_btn = QPushButton('X')
            delete_photo_doc_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 3px;
                    font-size: 12px;
                    font-weight: bold;
                    padding: 4px 4px;
                }
                QPushButton:hover {
                    background-color: #FFE5E5;
                    color: #C0392B;
                    border: 1px solid #C0392B;
                }
            """)
            delete_photo_doc_btn.setFixedSize(28, 28)
            delete_photo_doc_btn.setToolTip('Удалить всю фотофиксацию')
            delete_photo_doc_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_photo_doc_btn.clicked.connect(self.delete_photo_documentation_folder)
            photo_doc_folder_row.addWidget(delete_photo_doc_btn)

        photo_doc_layout.addLayout(photo_doc_folder_row)

        hint_photo_doc = QLabel('💡 Изображения, PDF и видео файлы с фотофиксацией')
        hint_photo_doc.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        photo_doc_layout.addWidget(hint_photo_doc)

        photo_doc_group.setLayout(photo_doc_layout)
        ref_photo_row.addWidget(photo_doc_group, 1)  # Занимает 1 часть (50%)

        form_layout.addRow(ref_photo_row)

        # ========== СЕКЦИЯ: 1 СТАДИЯ - ПЛАНИРОВОЧНОЕ РЕШЕНИЕ ==========
        stage1_group = QGroupBox("1 стадия - Планировочное решение")
        stage1_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 11px;
                color: #2C3E50;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                margin-top: 8px;
                padding-top: 15px;
            }
            QGroupBox::title {
                left: 10px;
                padding: 0 5px;
            }
        """)

        stage1_layout = QVBoxLayout()

        # Стадия 1 - могут удалять и загружать все кроме дизайнера
        can_delete_stage1 = not (self.employee and self.employee.get('position') == 'Дизайнер')
        can_upload_stage1 = not (self.employee and self.employee.get('position') == 'Дизайнер')

        self.stage1_list = FileListWidget(
            title="PDF файлы планировочного решения",
            stage="stage1",
            file_types=['pdf'],
            can_delete=can_delete_stage1,
            can_upload=can_upload_stage1
        )
        self.stage1_list.upload_requested.connect(self.upload_stage_files)
        self.stage1_list.delete_requested.connect(self.delete_stage_file)
        stage1_layout.addWidget(self.stage1_list)

        stage1_group.setLayout(stage1_layout)
        form_layout.addRow(stage1_group)

        # ========== СТАДИИ 2 И 3: РАЗНЫЕ ДЛЯ ИНДИВИДУАЛЬНЫХ И ШАБЛОННЫХ ==========
        if project_type == 'Шаблонный':
            # ДЛЯ ШАБЛОННЫХ ПРОЕКТОВ:
            # Стадия 2 - Чертежный проект (бывшая стадия 3)
            # Стадия 3 - 3D Визуализация (дополнительная) (из бывшей стадии 2, без концепции-коллажей)

            # ========== СЕКЦИЯ: 2 СТАДИЯ - ЧЕРТЕЖНЫЙ ПРОЕКТ ==========
            stage2_group = QGroupBox("2 стадия - Чертежный проект")
            stage2_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 11px;
                    color: #2C3E50;
                    border: 1px solid #E0E0E0;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    left: 10px;
                    padding: 0 5px;
                }
            """)

            stage2_layout = QVBoxLayout()

            # Стадия 2 - могут удалять и загружать все кроме дизайнера
            can_delete_stage2 = not (self.employee and self.employee.get('position') == 'Дизайнер')
            can_upload_stage2 = not (self.employee and self.employee.get('position') == 'Дизайнер')

            self.stage3_list = FileListWidget(  # используем stage3_list для совместимости с БД
                title="PDF и Excel файлы чертежного проекта",
                stage="stage3",
                file_types=['pdf', 'excel'],
                can_delete=can_delete_stage2,
                can_upload=can_upload_stage2
            )
            self.stage3_list.upload_requested.connect(self.upload_stage_files)
            self.stage3_list.delete_requested.connect(self.delete_stage_file)
            stage2_layout.addWidget(self.stage3_list)

            stage2_group.setLayout(stage2_layout)
            form_layout.addRow(stage2_group)

            # ========== СЕКЦИЯ: 3 СТАДИЯ - 3D ВИЗУАЛИЗАЦИЯ (ДОПОЛНИТЕЛЬНАЯ) ==========
            stage3_group = QGroupBox("3 стадия - 3D Визуализация (дополнительная)")
            stage3_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 11px;
                    color: #2C3E50;
                    border: 1px solid #E0E0E0;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    left: 10px;
                    padding: 0 5px;
                }
            """)

            stage3_layout = QVBoxLayout()

            # Стадия 3 - могут удалять и загружать все кроме чертежника
            can_delete_stage3 = not (self.employee and self.employee.get('position') == 'Чертёжник')
            can_upload_stage3 = not (self.employee and self.employee.get('position') == 'Чертёжник')

            # Только 3D визуализация (без концепции-коллажей)
            self.stage2_3d_gallery = VariationGalleryWidget(
                title="3D визуализация",
                stage="stage2_3d",
                file_types=['image', 'pdf'],
                can_delete=can_delete_stage3,
                can_upload=can_upload_stage3
            )
            self.stage2_3d_gallery.upload_requested.connect(self.upload_stage_files_with_variation)
            self.stage2_3d_gallery.delete_requested.connect(self.delete_stage_file_with_variation)
            self.stage2_3d_gallery.add_variation_requested.connect(self.add_variation_folder)
            self.stage2_3d_gallery.delete_variation_requested.connect(self.delete_variation_folder)
            stage3_layout.addWidget(self.stage2_3d_gallery)

            stage3_group.setLayout(stage3_layout)
            form_layout.addRow(stage3_group)

        else:
            # ДЛЯ ИНДИВИДУАЛЬНЫХ ПРОЕКТОВ - ОРИГИНАЛЬНАЯ СТРУКТУРА:
            # Стадия 2 - Концепция дизайна (концепция-коллажи + 3D визуализация)
            # Стадия 3 - Чертежный проект

            # ========== СЕКЦИЯ: 2 СТАДИЯ - КОНЦЕПЦИЯ ДИЗАЙНА ==========

            stage2_group = QGroupBox("2 стадия - Концепция дизайна")
            stage2_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 11px;
                    color: #2C3E50;
                    border: 1px solid #E0E0E0;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    left: 10px;
                    padding: 0 5px;
                }
            """)

            stage2_layout = QVBoxLayout()

            # Стадия 2 - могут удалять и загружать все кроме чертежника
            can_delete_stage2 = not (self.employee and self.employee.get('position') == 'Чертёжник')
            can_upload_stage2 = not (self.employee and self.employee.get('position') == 'Чертёжник')

            # Подсекция: Концепция-коллажи (с поддержкой вариаций)
            self.stage2_concept_gallery = VariationGalleryWidget(
                title="Концепция-коллажи",
                stage="stage2_concept",
                file_types=['image', 'pdf'],
                can_delete=can_delete_stage2,
                can_upload=can_upload_stage2
            )
            self.stage2_concept_gallery.upload_requested.connect(self.upload_stage_files_with_variation)
            self.stage2_concept_gallery.delete_requested.connect(self.delete_stage_file_with_variation)
            self.stage2_concept_gallery.add_variation_requested.connect(self.add_variation_folder)
            self.stage2_concept_gallery.delete_variation_requested.connect(self.delete_variation_folder)
            stage2_layout.addWidget(self.stage2_concept_gallery)

            # Подсекция: 3D визуализация (с поддержкой вариаций)
            self.stage2_3d_gallery = VariationGalleryWidget(
                title="3D визуализация",
                stage="stage2_3d",
                file_types=['image', 'pdf'],
                can_delete=can_delete_stage2,
                can_upload=can_upload_stage2
            )
            self.stage2_3d_gallery.upload_requested.connect(self.upload_stage_files_with_variation)
            self.stage2_3d_gallery.delete_requested.connect(self.delete_stage_file_with_variation)
            self.stage2_3d_gallery.add_variation_requested.connect(self.add_variation_folder)
            self.stage2_3d_gallery.delete_variation_requested.connect(self.delete_variation_folder)
            stage2_layout.addWidget(self.stage2_3d_gallery)

            stage2_group.setLayout(stage2_layout)
            form_layout.addRow(stage2_group)

            # ========== СЕКЦИЯ: 3 СТАДИЯ - ЧЕРТЕЖНЫЙ ПРОЕКТ ==========
            stage3_group = QGroupBox("3 стадия - Чертежный проект")
            stage3_group.setStyleSheet("""
                QGroupBox {
                    font-weight: bold;
                    font-size: 11px;
                    color: #2C3E50;
                    border: 1px solid #E0E0E0;
                    border-radius: 5px;
                    margin-top: 8px;
                    padding-top: 15px;
                }
                QGroupBox::title {
                    left: 10px;
                    padding: 0 5px;
                }
            """)

            stage3_layout = QVBoxLayout()

            # Стадия 3 - могут удалять и загружать все кроме дизайнера
            can_delete_stage3 = not (self.employee and self.employee.get('position') == 'Дизайнер')
            can_upload_stage3 = not (self.employee and self.employee.get('position') == 'Дизайнер')

            self.stage3_list = FileListWidget(
                title="PDF и Excel файлы чертежного проекта",
                stage="stage3",
                file_types=['pdf', 'excel'],
                can_delete=can_delete_stage3,
                can_upload=can_upload_stage3
            )
            self.stage3_list.upload_requested.connect(self.upload_stage_files)
            self.stage3_list.delete_requested.connect(self.delete_stage_file)
            stage3_layout.addWidget(self.stage3_list)

            stage3_group.setLayout(stage3_layout)
            form_layout.addRow(stage3_group)

        content_widget.setLayout(form_layout)
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        widget.setLayout(layout)

        return widget

    def create_project_info_widget(self):
        """Создание виджета информации о проекте"""
        widget = QWidget()
        layout = QVBoxLayout()

        header = QLabel('Информация о проекте')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)

        # ИСПРАВЛЕНИЕ: Компактная отметка о замере (одной строчкой)
        try:
            contract_id = self.card_data.get('contract_id')
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT survey_date, e.full_name as surveyor_name
            FROM surveys s
            LEFT JOIN employees e ON s.surveyor_id = e.id
            WHERE s.contract_id = ?
            ORDER BY s.id DESC
            LIMIT 1
            ''', (contract_id,))

            survey = cursor.fetchone()
            self.db.close()

            if survey:
                survey_date = QDate.fromString(survey['survey_date'], 'yyyy-MM-dd')
                survey_label = QLabel(
                    f"✓ Замер выполнен: {survey_date.toString('dd.MM.yyyy')} | Замерщик: {survey['surveyor_name']}"
                )
                survey_label.setStyleSheet('''
                    color: #27AE60;
                    font-size: 10px;
                    font-weight: bold;
                    background-color: #E8F8F5;
                    padding: 5px;
                    border-radius: 3px;
                    margin-bottom: 8px;
                ''')
                layout.addWidget(survey_label)
        except Exception as e:
            print(f" Ошибка загрузки информации о замере: {e}")

        # ========== НОВОЕ: ВЫПОЛНЕННЫЕ СТАДИИ ==========
        # Показываем стадии, которые были отмечены как сданные (completed = 1)
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            # ОТЛАДКА: Проверяем все записи в stage_executors для этой карточки
            cursor.execute('''
            SELECT se.stage_name, e.full_name as executor_name, se.completed, se.completed_date
            FROM stage_executors se
            LEFT JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ?
            ''', (self.card_data['id'],))

            all_stages = cursor.fetchall()
            print(f"\n[DEBUG] Все стадии для карточки {self.card_data['id']}:")
            for s in all_stages:
                print(f"  - {s['stage_name']} | Исполнитель: {s['executor_name']} | Completed: {s['completed']} | Дата: {s['completed_date']}")

            cursor.execute('''
            SELECT se.stage_name, e.full_name as executor_name, se.completed_date
            FROM stage_executors se
            LEFT JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ? AND se.completed = 1
            ORDER BY se.completed_date ASC
            ''', (self.card_data['id'],))

            completed_stages = cursor.fetchall()
            print(f"[DEBUG] Выполненных стадий найдено: {len(completed_stages)}")
            self.db.close()

            if completed_stages:
                # Заголовок
                completed_header = QLabel('✓ Выполненные стадии:')
                completed_header.setStyleSheet('font-size: 11px; font-weight: bold; color: #27AE60; margin-bottom: 4px; margin-top: 4px;')
                layout.addWidget(completed_header)

                # Контейнер для стадий
                for stage in completed_stages:
                    date_str = format_date(stage.get('completed_date'))

                    stage_label = QLabel(
                        f"✓ {stage['stage_name']} | Исполнитель: {stage['executor_name']} | Дата: {date_str}"
                    )
                    stage_label.setStyleSheet('''
                        color: #27AE60;
                        font-size: 10px;
                        font-weight: bold;
                        background-color: #E8F8F5;
                        padding: 5px;
                        border-radius: 3px;
                        margin-bottom: 4px;
                    ''')
                    layout.addWidget(stage_label)

        except Exception as e:
            print(f" Ошибка загрузки выполненных стадий: {e}")
            import traceback
            traceback.print_exc()
        # ===============================================

        accepted_stages = self.db.get_accepted_stages(self.card_data['id'])

        if accepted_stages:
            # ИСПРАВЛЕНИЕ: Список согласованных стадий (как в "Принятых стадиях" CRM надзора)
            acceptance_header = QLabel('Согласованные стадии:')
            acceptance_header.setStyleSheet('font-size: 11px; font-weight: bold; color: #27AE60; margin-bottom: 4px; margin-top: 4px;')
            layout.addWidget(acceptance_header)

            # Отображаем каждую стадию в виде зеленой строки
            for accepted in accepted_stages:
                # Формируем текст: "Стадия 'название' принята [должностью]"
                # Используем реальную должность того, кто принял
                accepted_by_position = accepted.get('accepted_by_position', 'Менеджер')

                # Склоняем должность в творительный падеж (кем?)
                position_mapping = {
                    'Руководитель студии': 'руководителем студии',
                    'Старший менеджер проектов': 'старшим менеджером проектов',
                    'Менеджер': 'менеджером',
                    'СДП': 'СДП',
                    'ГАП': 'ГАП',
                }

                position_text = position_mapping.get(accepted_by_position, accepted_by_position.lower() + 'ом')

                stage_text = f"Стадия '{accepted['stage_name']}' принята {position_text}"

                # Добавляем имя того, кто принял
                if accepted.get('accepted_by_name'):
                    stage_text += f" ({accepted['accepted_by_name']})"

                stage_text += f". Исполнитель: {accepted['executor_name']}"

                # Добавляем дату принятия
                stage_text += f" | Дата: {format_date(accepted['accepted_date'])}"

                # Создаем label с зеленым оформлением
                stage_label = QLabel(f"✓ {stage_text}")
                stage_label.setStyleSheet('''
                    color: #27AE60;
                    font-size: 10px;
                    font-weight: bold;
                    background-color: #E8F8F5;
                    padding: 5px;
                    border-radius: 3px;
                    margin-bottom: 4px;
                ''')
                stage_label.setWordWrap(True)
                layout.addWidget(stage_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet('background-color: #E0E0E0; margin: 8px 0px;')
        separator.setFixedHeight(2)
        layout.addWidget(separator)

        history_header = QLabel('История ведения проекта')
        history_header.setStyleSheet('font-size: 12px; font-weight: bold; margin-bottom: 8px;')
        layout.addWidget(history_header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #DDD; border-radius: 4px; background: white; }")

        info_container = QWidget()
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(10)
        self.info_layout.setContentsMargins(10, 10, 10, 10)

        # Получаем историю стадий
        stages = self.db.get_stage_history(self.card_data['id'])

        # Получаем историю действий из action_history
        action_history_items = []
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT ah.action_type, ah.description, ah.action_date, e.full_name as user_name
            FROM action_history ah
            LEFT JOIN employees e ON ah.user_id = e.id
            WHERE ah.entity_type = 'crm_card' AND ah.entity_id = ?
            ORDER BY ah.action_date DESC
            ''', (self.card_data['id'],))

            action_history_items = cursor.fetchall()
            self.db.close()
        except Exception as e:
            print(f" Ошибка загрузки истории действий: {e}")
            import traceback
            traceback.print_exc()

        # Объединяем историю: сначала действия, потом стадии
        has_content = False

        # Добавляем историю действий
        if action_history_items:
            has_content = True
            for action in action_history_items:
                from datetime import datetime
                try:
                    action_date = datetime.strptime(action['action_date'], '%Y-%m-%d %H:%M:%S')
                    date_str = action_date.strftime('%d.%m.%Y %H:%M')
                except:
                    date_str = action['action_date']

                action_text = f"📋 {date_str} | {action['user_name']}: {action['description']}"

                # Создаем label с синим оформлением
                action_label = QLabel(action_text)
                action_label.setStyleSheet('''
                    color: #2C3E50;
                    font-size: 10px;
                    background-color: #EBF5FB;
                    padding: 8px;
                    border-radius: 4px;
                    margin-bottom: 6px;
                ''')
                action_label.setWordWrap(True)
                self.info_layout.addWidget(action_label)

        # Добавляем историю стадий
        if stages:
            has_content = True
            for stage in stages:
                stage_widget = self.create_stage_info_widget(stage)
                self.info_layout.addWidget(stage_widget)

        if not has_content:
            empty_label = QLabel('История проекта пуста')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            self.info_layout.addWidget(empty_label)
        
        self.info_layout.addStretch()
        
        info_container.setLayout(self.info_layout)
        scroll.setWidget(info_container)
        
        layout.addWidget(scroll, 1)
        
        widget.setLayout(layout)
        return widget
    
    def create_stage_info_widget(self, stage):
        """Создание виджета для записи о стадии"""
        stage_frame = QFrame()

        # Конвертируем Row в dict для удобного доступа
        stage_dict = dict(stage)

        if stage_dict.get('completed'):
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

        header = QLabel(f"{icon} {format_date(stage_dict.get('assigned_date', ''), '—')} | {stage_dict.get('stage_name', 'N/A')}")
        header.setStyleSheet('font-size: 9px; font-weight: bold; color: #555;')
        stage_layout.addWidget(header)

        executor = QLabel(f"Исполнитель: {stage_dict.get('executor_name', 'Не назначен')}")
        executor.setStyleSheet('font-size: 10px; color: #333;')
        stage_layout.addWidget(executor)

        # ИСПРАВЛЕНИЕ: Добавлены все даты в нужном порядке
        deadline = QLabel(f"Дедлайн: {format_date(stage_dict.get('deadline'), 'N/A')}")
        deadline.setStyleSheet('font-size: 10px; color: #333;')
        stage_layout.addWidget(deadline)

        # Дата сдачи работы
        if stage_dict.get('submitted_date'):
            submitted_label = QLabel(f"📤 Сдано: {format_date(stage_dict.get('submitted_date'), 'N/A')}")
            submitted_label.setStyleSheet('font-size: 10px; color: #3498DB; font-weight: bold;')
            stage_layout.addWidget(submitted_label)

        # Дата принятия (завершения)
        if stage_dict.get('completed'):
            completed_label = QLabel(f"✓ Принято: {format_date(stage_dict.get('completed_date'), 'N/A')}")
            completed_label.setStyleSheet('font-size: 10px; color: #27AE60; font-weight: bold;')
            stage_layout.addWidget(completed_label)

        stage_frame.setLayout(stage_layout)
        return stage_frame

    def reload_project_history(self):
        """Обновление истории проекта без перезагрузки всей вкладки"""
        print(f"[DEBUG reload_project_history] Начало выполнения")

        if not hasattr(self, 'info_layout'):
            print(f"[DEBUG reload_project_history] info_layout не существует, выход")
            return

        print(f"[DEBUG reload_project_history] Очистка текущей истории...")
        # Очищаем текущую историю
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        print(f"[DEBUG reload_project_history] История очищена")

        # Получаем историю стадий
        stages = []
        if self.card_data.get('id'):
            try:
                print(f"[DEBUG reload_project_history] Загрузка стадий из БД...")
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                SELECT s.stage_name, s.assigned_date, s.deadline, s.submitted_date, s.completed, s.completed_date,
                       e.full_name as executor_name
                FROM stage_executors s
                LEFT JOIN employees e ON s.executor_id = e.id
                WHERE s.crm_card_id = ?
                ORDER BY s.id DESC
                ''', (self.card_data['id'],))
                stages = cursor.fetchall()
                conn.close()
                print(f"[DEBUG reload_project_history] Загружено {len(stages)} стадий")
            except Exception as e:
                print(f" Ошибка загрузки истории стадий: {e}")
                import traceback
                traceback.print_exc()

        # Получаем историю действий из action_history
        action_history_items = []
        try:
            print(f"[DEBUG reload_project_history] Загрузка действий из БД...")
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT ah.action_type, ah.description, ah.action_date, e.full_name as user_name
            FROM action_history ah
            LEFT JOIN employees e ON ah.user_id = e.id
            WHERE ah.entity_type = 'crm_card' AND ah.entity_id = ?
            ORDER BY ah.action_date DESC
            ''', (self.card_data['id'],))

            action_history_items = cursor.fetchall()
            conn.close()
            print(f"[DEBUG reload_project_history] Загружено {len(action_history_items)} действий")
        except Exception as e:
            print(f" Ошибка загрузки истории действий: {e}")
            import traceback
            traceback.print_exc()

        # Объединяем историю: сначала действия, потом стадии
        has_content = False

        print(f"[DEBUG reload_project_history] Добавление действий в UI...")
        # Добавляем историю действий
        if action_history_items:
            has_content = True
            for action in action_history_items:
                from datetime import datetime
                try:
                    action_date = datetime.strptime(action['action_date'], '%Y-%m-%d %H:%M:%S')
                    date_str = action_date.strftime('%d.%m.%Y %H:%M')
                except:
                    date_str = action['action_date']

                action_text = f"📋 {date_str} | {action['user_name']}: {action['description']}"

                # Создаем label с синим оформлением
                action_label = QLabel(action_text)
                action_label.setStyleSheet('''
                    color: #2C3E50;
                    font-size: 10px;
                    background-color: #EBF5FB;
                    padding: 8px;
                    border-radius: 4px;
                    margin-bottom: 6px;
                ''')
                action_label.setWordWrap(True)
                self.info_layout.addWidget(action_label)
        print(f"[DEBUG reload_project_history] Действия добавлены")

        print(f"[DEBUG reload_project_history] Добавление стадий в UI...")
        # Добавляем историю стадий
        if stages:
            has_content = True
            for stage in stages:
                stage_widget = self.create_stage_info_widget(stage)
                self.info_layout.addWidget(stage_widget)
        print(f"[DEBUG reload_project_history] Стадии добавлены")

        if not has_content:
            empty_label = QLabel('История проекта пуста')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            self.info_layout.addWidget(empty_label)

        self.info_layout.addStretch()
        print(f"[DEBUG reload_project_history] Завершено успешно")

    def load_data(self):
        # ИСПРАВЛЕНИЕ: Предотвращаем автосохранение во время загрузки
        self._loading_data = True

        # Загружаем свежие данные из БД, чтобы гарантировать актуальность информации о файлах
        if self.card_data and self.card_data.get('id'):
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM crm_cards WHERE id = ?', (self.card_data['id'],))
            fresh_data = cursor.fetchone()
            conn.close()
            if fresh_data:
                # Обновляем card_data свежими данными из БД
                self.card_data = dict(fresh_data)

        # Виджеты из вкладки "Редактирование" (могут отсутствовать для дизайнеров/чертежников)
        if hasattr(self, 'deadline_display') and self.card_data.get('deadline'):
            deadline_date = QDate.fromString(self.card_data['deadline'], 'yyyy-MM-dd')
            self.deadline_display.setText(deadline_date.toString('dd.MM.yyyy'))

        if hasattr(self, 'tags'):
            self.tags.setText(self.card_data.get('tags', ''))

        contract_id = self.card_data.get('contract_id')
        if contract_id:
            contract = self.db.get_contract_by_id(contract_id)
            if contract and contract.get('status'):
                if hasattr(self, 'status_combo'):
                    self.status_combo.setCurrentText(contract['status'])

        if hasattr(self, 'senior_manager'):
            self.set_combo_by_id(self.senior_manager, self.card_data.get('senior_manager_id'))
        if hasattr(self, 'sdp'):
            self.set_combo_by_id(self.sdp, self.card_data.get('sdp_id'))
        if hasattr(self, 'gap'):
            self.set_combo_by_id(self.gap, self.card_data.get('gap_id'))
        if hasattr(self, 'manager'):
            self.set_combo_by_id(self.manager, self.card_data.get('manager_id'))
        if hasattr(self, 'surveyor'):
            self.set_combo_by_id(self.surveyor, self.card_data.get('surveyor_id'))

        # ========== ЗАГРУЗКА ДАТЫ ЗАМЕРА ==========
        # survey_date_label находится в вкладке "Редактирование"
        if hasattr(self, 'survey_date_label'):
            if self.card_data.get('survey_date'):
                from datetime import datetime
                try:
                    survey_date = datetime.strptime(self.card_data['survey_date'], '%Y-%m-%d')
                    self.survey_date_label.setText(survey_date.strftime('%d.%m.%Y'))
                except:
                    self.survey_date_label.setText('Не установлена')
            else:
                self.survey_date_label.setText('Не установлена')
        # ==========================================

        # ========== ЗАГРУЗКА ТЗ ==========
        # ВАЖНО: Всегда загружаем актуальные данные из БД, чтобы избежать двоения при удалении
        contract_id = self.card_data.get('contract_id')
        tech_task_link_from_contract = None
        tech_task_file_name_from_contract = None
        if contract_id:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT tech_task_link, tech_task_file_name FROM contracts WHERE id = ?', (contract_id,))
            result = cursor.fetchone()
            conn.close()
            # Берём данные из БД даже если они пустые (файл удалён)
            if result:
                tech_task_link_from_contract = result['tech_task_link']
                tech_task_file_name_from_contract = result['tech_task_file_name']

        # Приоритет: только файл из договора (БД), НЕ используем кэш card_data
        tech_task_file = tech_task_link_from_contract or ''

        # Обновляем лейблы на обеих вкладках
        if tech_task_file:
            # Используем сохраненное имя файла, если оно есть
            file_name = tech_task_file_name_from_contract if tech_task_file_name_from_contract else 'ТехЗадание.pdf'
            truncated_name = self.truncate_filename(file_name)
            html_link = f'<a href="{tech_task_file}" title="{file_name}">{truncated_name}</a>'

            if hasattr(self, 'tech_task_file_label'):
                self.tech_task_file_label.setText(html_link)
            if hasattr(self, 'project_data_tz_file_label'):
                self.project_data_tz_file_label.setText(html_link)
            if hasattr(self, 'upload_tz_btn'):
                self.upload_tz_btn.setEnabled(False)  # Деактивируем кнопку загрузки
        else:
            if hasattr(self, 'tech_task_file_label'):
                self.tech_task_file_label.setText('Не загружен')
            if hasattr(self, 'project_data_tz_file_label'):
                self.project_data_tz_file_label.setText('Не загружен')
            if hasattr(self, 'upload_tz_btn'):
                self.upload_tz_btn.setEnabled(True)  # Активируем кнопку загрузки

        if self.card_data.get('tech_task_date'):
            from datetime import datetime
            try:
                tech_task_date = datetime.strptime(self.card_data['tech_task_date'], '%Y-%m-%d')
                date_str = tech_task_date.strftime('%d.%m.%Y')
                if hasattr(self, 'tech_task_date_label'):
                    self.tech_task_date_label.setText(date_str)
                if hasattr(self, 'project_data_tz_date_label'):
                    self.project_data_tz_date_label.setText(date_str)
            except:
                if hasattr(self, 'tech_task_date_label'):
                    self.tech_task_date_label.setText('Не установлена')
                if hasattr(self, 'project_data_tz_date_label'):
                    self.project_data_tz_date_label.setText('Не установлена')
        else:
            if hasattr(self, 'tech_task_date_label'):
                self.tech_task_date_label.setText('Не установлена')
            if hasattr(self, 'project_data_tz_date_label'):
                self.project_data_tz_date_label.setText('Не установлена')
        # ================================

        # ========== ЗАГРУЗКА ЗАМЕРА ==========
        # Получаем данные замера из договора
        if contract_id:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT measurement_image_link, measurement_file_name, measurement_date FROM contracts WHERE id = ?', (contract_id,))
            result = cursor.fetchone()
            conn.close()

            if result:
                # Изображение замера
                if result['measurement_image_link']:
                    measurement_link = result['measurement_image_link']
                    # Используем сохраненное имя файла, если оно есть
                    file_name = result['measurement_file_name'] if result['measurement_file_name'] else 'Замер'
                    truncated_name = self.truncate_filename(file_name)
                    html_link = f'<a href="{measurement_link}" title="{file_name}">{truncated_name}</a>'

                    if hasattr(self, 'project_data_survey_file_label'):
                        self.project_data_survey_file_label.setText(html_link)
                    if hasattr(self, 'upload_survey_btn'):
                        self.upload_survey_btn.setEnabled(False)  # Деактивируем кнопку загрузки
                else:
                    if hasattr(self, 'project_data_survey_file_label'):
                        self.project_data_survey_file_label.setText('Не загружен')
                    if hasattr(self, 'upload_survey_btn'):
                        self.upload_survey_btn.setEnabled(True)  # Активируем кнопку загрузки

                # Дата замера
                if result['measurement_date']:
                    from datetime import datetime
                    try:
                        measurement_date = datetime.strptime(result['measurement_date'], '%Y-%m-%d')
                        date_str = measurement_date.strftime('%d.%m.%Y')
                        if hasattr(self, 'project_data_survey_date_label'):
                            self.project_data_survey_date_label.setText(date_str)
                    except:
                        if hasattr(self, 'project_data_survey_date_label'):
                            self.project_data_survey_date_label.setText('Не установлена')
                else:
                    if hasattr(self, 'project_data_survey_date_label'):
                        self.project_data_survey_date_label.setText('Не установлена')
            else:
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText('Не загружен')
                if hasattr(self, 'project_data_survey_date_label'):
                    self.project_data_survey_date_label.setText('Не установлена')
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(True)  # Активируем кнопку загрузки
        else:
            if hasattr(self, 'project_data_survey_file_label'):
                self.project_data_survey_file_label.setText('Не загружен')
            if hasattr(self, 'upload_survey_btn'):
                self.upload_survey_btn.setEnabled(True)  # Активируем кнопку загрузки
            if hasattr(self, 'project_data_survey_date_label'):
                self.project_data_survey_date_label.setText('Не установлена')
        # ================================

        # Проверяем файлы на Яндекс.Диске в фоновом режиме
        self.verify_files_on_yandex_disk()

        # Загружаем файлы стадий
        if hasattr(self, 'stage1_list'):
            self.reload_stage_files('stage1')
        if hasattr(self, 'stage2_concept_gallery'):
            self.reload_stage_files('stage2_concept')
        if hasattr(self, 'stage2_3d_gallery'):
            self.reload_stage_files('stage2_3d')
        if hasattr(self, 'stage3_list'):
            self.reload_stage_files('stage3')

        # ИСПРАВЛЕНИЕ: Разрешаем автосохранение после загрузки
        self._loading_data = False

    def set_combo_by_id(self, combo, employee_id):
        if employee_id:
            for i in range(combo.count()):
                if combo.itemData(i) == employee_id:
                    combo.setCurrentIndex(i)
                    break

    def verify_files_on_yandex_disk(self):
        """Проверка существования файлов на Яндекс.Диске в фоновом режиме"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        def check_files():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                conn = self.db.connect()
                cursor = conn.cursor()

                # Получаем данные о файлах
                cursor.execute('''
                    SELECT tech_task_yandex_path, tech_task_link, tech_task_file_name,
                           measurement_yandex_path, measurement_image_link, measurement_file_name
                    FROM contracts WHERE id = ?
                ''', (contract_id,))
                result = cursor.fetchone()

                if not result:
                    conn.close()
                    return

                needs_update = False
                update_data = {}

                # Проверяем тех.задание
                if result['tech_task_yandex_path']:
                    if not yd.file_exists(result['tech_task_yandex_path']):
                        print(f"[INFO] Файл ТЗ не найден на Яндекс.Диске, удаляем из БД")
                        update_data['tech_task_link'] = ''
                        update_data['tech_task_yandex_path'] = ''
                        update_data['tech_task_file_name'] = ''
                        needs_update = True

                # Проверяем замер
                if result['measurement_yandex_path']:
                    if not yd.file_exists(result['measurement_yandex_path']):
                        print(f"[INFO] Файл замера не найден на Яндекс.Диске, удаляем из БД")
                        update_data['measurement_image_link'] = ''
                        update_data['measurement_yandex_path'] = ''
                        update_data['measurement_file_name'] = ''
                        needs_update = True

                # Обновляем БД если нужно
                if needs_update:
                    for key, value in update_data.items():
                        cursor.execute(f'UPDATE contracts SET {key} = ? WHERE id = ?', (value, contract_id))
                    conn.commit()

                    # Отправляем сигнал для обновления UI в главном потоке
                    print("[INFO] Обновляем UI после проверки файлов на Яндекс.Диске")
                    self.files_verification_completed.emit()

                conn.close()

            except Exception as e:
                print(f"[ERROR] Ошибка при проверке файлов на Яндекс.Диске: {e}")

        # Запускаем проверку в фоновом потоке
        thread = threading.Thread(target=check_files, daemon=True)
        thread.start()

    def refresh_file_labels(self):
        """Обновление меток файлов после проверки"""
        print(f"[DEBUG REFRESH] refresh_file_labels() вызвана в CRM CardEditDialog")

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            print(f"[DEBUG REFRESH] contract_id отсутствует, выход")
            return

        print(f"[DEBUG REFRESH] Перезагружаем данные для договора {contract_id}")

        # Перезагружаем данные из БД
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tech_task_link, tech_task_file_name,
                       measurement_image_link, measurement_file_name,
                       references_yandex_path, photo_documentation_yandex_path
                FROM contracts WHERE id = ?
            ''', (contract_id,))
            result = cursor.fetchone()
            conn.close()

            if not result:
                print(f"[DEBUG REFRESH] Не удалось получить данные из БД")
                return

            print(f"[DEBUG REFRESH] Получены данные из БД:")
            print(f"  - tech_task_link: {result['tech_task_link'] if result['tech_task_link'] else 'None'}")
            print(f"  - tech_task_file_name: {result['tech_task_file_name'] if result['tech_task_file_name'] else 'None'}")
            print(f"  - measurement_image_link: {result['measurement_image_link'] if result['measurement_image_link'] else 'None'}")
            print(f"  - measurement_file_name: {result['measurement_file_name'] if result['measurement_file_name'] else 'None'}")
            print(f"  - references_yandex_path: {result['references_yandex_path'] if result['references_yandex_path'] else 'None'}")
            print(f"  - photo_documentation_yandex_path: {result['photo_documentation_yandex_path'] if result['photo_documentation_yandex_path'] else 'None'}")

            # Обновляем метку ТЗ
            if result['tech_task_link']:
                file_name = result['tech_task_file_name'] if result['tech_task_file_name'] else 'ТехЗадание.pdf'
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{result["tech_task_link"]}" title="{file_name}">{truncated_name}</a>'
                print(f"[DEBUG REFRESH] Обновляем tech_task_file_label: {html_link}")

                if hasattr(self, 'tech_task_file_label'):
                    self.tech_task_file_label.setText(html_link)
                if hasattr(self, 'project_data_tz_file_label'):
                    self.project_data_tz_file_label.setText(html_link)
                if hasattr(self, 'upload_tz_btn'):
                    self.upload_tz_btn.setEnabled(False)  # Деактивируем кнопку загрузки
            else:
                print(f"[DEBUG REFRESH] ТЗ отсутствует, устанавливаем 'Не загружен'")
                if hasattr(self, 'tech_task_file_label'):
                    self.tech_task_file_label.setText('Не загружен')
                if hasattr(self, 'project_data_tz_file_label'):
                    self.project_data_tz_file_label.setText('Не загружен')
                if hasattr(self, 'upload_tz_btn'):
                    self.upload_tz_btn.setEnabled(True)  # Активируем кнопку загрузки

            # Обновляем метку замера
            if result['measurement_image_link']:
                file_name = result['measurement_file_name'] if result['measurement_file_name'] else 'Замер'
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{result["measurement_image_link"]}" title="{file_name}">{truncated_name}</a>'
                print(f"[DEBUG REFRESH] Обновляем measurement_file_label: {html_link}")

                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText(html_link)
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(False)  # Деактивируем кнопку загрузки
            else:
                print(f"[DEBUG REFRESH] Замер отсутствует, устанавливаем 'Не загружен'")
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText('Не загружен')
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(True)  # Активируем кнопку загрузки

            # Обновляем метку референсов (для индивидуальных проектов)
            if result['references_yandex_path']:
                html_link = f'<a href="{result["references_yandex_path"]}">Открыть папку с референсами</a>'
                print(f"[DEBUG REFRESH] Обновляем references_label: {html_link}")
                if hasattr(self, 'project_data_references_label'):
                    self.project_data_references_label.setText(html_link)
            else:
                print(f"[DEBUG REFRESH] Референсы отсутствуют, устанавливаем 'Не загружена'")
                if hasattr(self, 'project_data_references_label'):
                    self.project_data_references_label.setText('Не загружена')

            # Загружаем шаблоны проектов (для шаблонных проектов)
            project_type = self.card_data.get('project_type', 'Индивидуальный')
            if project_type == 'Шаблонный' and hasattr(self, 'templates_container'):
                self.load_project_templates()

            # Обновляем метку фотофиксации
            if result['photo_documentation_yandex_path']:
                html_link = f'<a href="{result["photo_documentation_yandex_path"]}">Открыть папку с фотофиксацией</a>'
                print(f"[DEBUG REFRESH] Обновляем photo_doc_label: {html_link}")
                if hasattr(self, 'project_data_photo_doc_label'):
                    self.project_data_photo_doc_label.setText(html_link)
            else:
                print(f"[DEBUG REFRESH] Фотофиксация отсутствует, устанавливаем 'Не загружена'")
                if hasattr(self, 'project_data_photo_doc_label'):
                    self.project_data_photo_doc_label.setText('Не загружена')

            print(f"[DEBUG REFRESH] Обновление меток завершено")

        except Exception as e:
            print(f"[ERROR REFRESH] Ошибка при обновлении меток: {e}")

    def connect_autosave_signals(self):
        """ИСПРАВЛЕНИЕ: Подключение сигналов для автосохранения данных при изменении"""
        # Подключаем сигналы только для существующих виджетов
        if hasattr(self, 'status_combo'):
            self.status_combo.currentIndexChanged.connect(self.auto_save_field)
        if hasattr(self, 'senior_manager'):
            self.senior_manager.currentIndexChanged.connect(self.auto_save_field)
        if hasattr(self, 'sdp'):
            self.sdp.currentIndexChanged.connect(self.auto_save_field)
        if hasattr(self, 'gap'):
            self.gap.currentIndexChanged.connect(self.auto_save_field)
        if hasattr(self, 'manager'):
            self.manager.currentIndexChanged.connect(self.auto_save_field)
        if hasattr(self, 'surveyor'):
            self.surveyor.currentIndexChanged.connect(self.auto_save_field)
        # deadline больше не имеет автосохранения - изменяется через диалог
        if hasattr(self, 'tags'):
            self.tags.textChanged.connect(self.auto_save_field)

    def auto_save_field(self):
        """ИСПРАВЛЕНИЕ: Автоматическое сохранение при изменении полей"""
        if self._loading_data:
            return  # Не сохраняем во время загрузки данных

        try:
            # ИСПРАВЛЕНИЕ: Получаем старые значения для отслеживания изменений
            old_values = {
                'senior_manager_id': self.card_data.get('senior_manager_id'),
                'sdp_id': self.card_data.get('sdp_id'),
                'gap_id': self.card_data.get('gap_id'),
                'manager_id': self.card_data.get('manager_id'),
                'surveyor_id': self.card_data.get('surveyor_id'),
            }

            # Сохраняем изменения (только для существующих виджетов)
            updates = {}
            # deadline не сохраняется автоматически - только через диалог
            if hasattr(self, 'tags'):
                updates['tags'] = self.tags.text().strip()
            if hasattr(self, 'senior_manager'):
                updates['senior_manager_id'] = self.senior_manager.currentData()
            if hasattr(self, 'sdp'):
                updates['sdp_id'] = self.sdp.currentData()
            if hasattr(self, 'gap'):
                updates['gap_id'] = self.gap.currentData()
            if hasattr(self, 'manager'):
                updates['manager_id'] = self.manager.currentData()
            if hasattr(self, 'surveyor'):
                updates['surveyor_id'] = self.surveyor.currentData()

            self.db.update_crm_card(self.card_data['id'], updates)

            # Обновляем статус контракта
            contract_id = self.card_data.get('contract_id')
            if contract_id and hasattr(self, 'status_combo'):
                new_status = self.status_combo.currentText()
                self.db.update_contract(contract_id, {'status': new_status})

            # ИСПРАВЛЕНИЕ: Удаляем оплаты при снятии назначения сотрудника
            if contract_id:
                conn = self.db.connect()
                cursor = conn.cursor()
                payment_deleted = False

                # Проверяем каждую роль
                role_mapping = {
                    'senior_manager_id': 'Старший менеджер проектов',
                    'sdp_id': 'СДП',
                    'gap_id': 'Главный архитектор проектов',
                    'manager_id': 'Менеджер проектов',
                    'surveyor_id': 'Замерщик',
                }

                for field_name, role_name in role_mapping.items():
                    old_id = old_values.get(field_name)
                    new_id = updates.get(field_name)

                    # ИСПРАВЛЕНИЕ: Переназначение сотрудника (был А, стал Б)
                    if old_id is not None and new_id is not None and old_id != new_id:
                        # Ищем запись оплаты старого сотрудника
                        cursor.execute('''
                        SELECT id, * FROM payments
                        WHERE contract_id = ? AND employee_id = ? AND role = ?
                        ''', (contract_id, old_id, role_name))

                        old_payment = cursor.fetchone()
                        if old_payment:
                            # Помечаем старую запись как переназначенную
                            cursor.execute('''
                            UPDATE payments
                            SET reassigned = 1, updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            ''', (old_payment['id'],))

                            # Создаем новую запись для нового сотрудника
                            cursor.execute('''
                            INSERT INTO payments (
                                contract_id, crm_card_id, supervision_card_id,
                                employee_id, role, stage_name,
                                calculated_amount, manual_amount, final_amount,
                                is_manual, payment_type, report_month,
                                reassigned, old_employee_id
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                            ''', (
                                old_payment['contract_id'],
                                old_payment['crm_card_id'],
                                old_payment['supervision_card_id'],
                                new_id,  # Новый сотрудник
                                old_payment['role'],
                                old_payment['stage_name'],
                                old_payment['calculated_amount'],
                                old_payment['manual_amount'],
                                old_payment['final_amount'],
                                old_payment['is_manual'],
                                old_payment['payment_type'],
                                old_payment['report_month'],
                                old_id  # ID старого сотрудника
                            ))

                            payment_deleted = True
                            print(f"✓ Создана новая запись оплаты для роли '{role_name}' (ID: {new_id}), старая помечена как переназначенная")

                    # Если был назначен сотрудник, а теперь "Не назначен" (None)
                    elif old_id is not None and new_id is None:
                        cursor.execute('''
                        DELETE FROM payments
                        WHERE contract_id = ? AND employee_id = ? AND role = ?
                        ''', (contract_id, old_id, role_name))

                        if cursor.rowcount > 0:
                            payment_deleted = True
                            print(f"✓ Удалена оплата для роли '{role_name}' (ID сотрудника: {old_id})")

                conn.commit()
                self.db.close()

                # Обновляем вкладку оплат если были удаления
                if payment_deleted:
                    self.refresh_payments_tab()

            # Обновляем данные карточки
            self.card_data.update(updates)

            # ИСПРАВЛЕНИЕ: Не обновляем канбан при автосохранении, чтобы не закрывать диалог
            # Обновление канбана произойдет при закрытии диалога через метод reject()

            print("✓ Данные автоматически сохранены")

        except Exception as e:
            print(f" Ошибка автосохранения: {e}")

    def save_changes(self):
        # Сохраняем только данные существующих виджетов
        updates = {}
        # deadline не сохраняется здесь - только через диалог
        if hasattr(self, 'tags'):
            updates['tags'] = self.tags.text().strip()
        if hasattr(self, 'senior_manager'):
            updates['senior_manager_id'] = self.senior_manager.currentData()
        if hasattr(self, 'sdp'):
            updates['sdp_id'] = self.sdp.currentData()
        if hasattr(self, 'gap'):
            updates['gap_id'] = self.gap.currentData()
        if hasattr(self, 'manager'):
            updates['manager_id'] = self.manager.currentData()
        if hasattr(self, 'surveyor'):
            updates['surveyor_id'] = self.surveyor.currentData()

        # Сохраняем только если есть что обновлять
        if updates:
            self.db.update_crm_card(self.card_data['id'], updates)

        try:
            if hasattr(self, 'designer_deadline') and self.designer_deadline and self.card_data.get('designer_name'):
                deadline = self.designer_deadline.date().toString('yyyy-MM-dd')
                print(f"\n[SAVE] Сохранение дедлайна дизайнера: {deadline}")
                success = self.db.update_stage_executor_deadline(
                    self.card_data['id'],
                    'концепция',
                    deadline
                )
                if success:
                    print("✓ Дедлайн дизайнера сохранен")
                else:
                    print(" Не удалось сохранить дедлайн дизайнера")
            
            if hasattr(self, 'draftsman_deadline') and self.draftsman_deadline and self.card_data.get('draftsman_name'):
                deadline = self.draftsman_deadline.date().toString('yyyy-MM-dd')
                print(f"\n[SAVE] Сохранение дедлайна чертёжника: {deadline}")
                
                current_column = self.card_data.get('column_name', '').lower()
                
                if 'планировочные' in current_column:
                    search_key = 'планировочные'
                else:
                    search_key = 'чертежи'
                
                print(f"[SAVE] Используем ключевое слово: '{search_key}'")
                
                success = self.db.update_stage_executor_deadline(
                    self.card_data['id'],
                    search_key,
                    deadline
                )
                if success:
                    print("✓ Дедлайн чертёжника сохранен")
                else:
                    print(" Не удалось сохранить дедлайн чертёжника")

        except Exception as e:
            print(f" Ошибка обновления дедлайнов исполнителей: {e}")
            import traceback
            traceback.print_exc()

        contract_id = self.card_data.get('contract_id')
        if contract_id and hasattr(self, 'status_combo'):
            new_status = self.status_combo.currentText()
            self.db.update_contract(contract_id, {'status': new_status})

            # ИСПРАВЛЕНИЕ: Установка отчетного месяца при закрытии проекта
            if new_status in ['СДАН', 'АВТОРСКИЙ НАДЗОР']:
                current_month = QDate.currentDate().toString('yyyy-MM')

                # Обновляем отчетный месяц для менеджеров и ГАП
                conn = self.db.connect()
                cursor = conn.cursor()

                cursor.execute('''
                UPDATE payments
                SET report_month = ?
                WHERE contract_id = ?
                  AND role IN ('Старший менеджер проектов', 'Главный архитектор проектов', 'Менеджер проектов')
                  AND (report_month IS NULL OR report_month = '')
                ''', (current_month, contract_id))

                # Обновляем доплату для СДП
                cursor.execute('''
                UPDATE payments
                SET report_month = ?
                WHERE contract_id = ?
                  AND role = 'СДП'
                  AND payment_type = 'Доплата'
                  AND (report_month IS NULL OR report_month = '')
                ''', (current_month, contract_id))

                conn.commit()
                self.db.close()

                print(f"✓ Отчетный месяц {current_month} установлен для менеджеров и доплаты СДП")

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
            'СДП': 'sdp_id',
            'ГАП': 'gap_id',
            'Менеджер': 'manager_id',
            'Замерщик': 'surveyor_id'
        }

        field_name = role_to_field.get(role_name)
        if field_name:
            updates = {field_name: employee_id}
            self.db.update_crm_card(self.card_data['id'], updates)
            print(f"✓ Обновлено поле {field_name} в CRM карточке")

        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            # Удаляем существующие выплаты для этой роли
            cursor.execute('''
            DELETE FROM payments
            WHERE contract_id = ? AND role = ?
            ''', (contract_id, role_name))

            deleted_count = cursor.rowcount
            if deleted_count > 0:
                print(f"✓ Удалено {deleted_count} старых выплат для роли {role_name}")

            conn.commit()
            self.db.close()

            # Если выбран сотрудник (не "Не назначен"), создаем новые выплаты
            if employee_id:
                # Специальная обработка для СДП - создаем аванс и доплату
                if role_name == 'СДП':
                    full_amount = self.db.calculate_payment_amount(contract_id, employee_id, role_name)

                    if full_amount == 0:
                        print(f"[WARN] Тариф для СДП = 0 или не установлен. Создаем оплату с нулевой суммой")

                    advance_amount = full_amount / 2
                    balance_amount = full_amount / 2

                    from PyQt5.QtCore import QDate
                    current_month = QDate.currentDate().toString('yyyy-MM')

                    # Создаем аванс
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    # ИСПРАВЛЕНИЕ: Добавляем crm_card_id и stage_name (NULL для СДП = весь проект)
                    cursor.execute('''
                    INSERT INTO payments
                    (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                     final_amount, payment_type, report_month)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (contract_id, self.card_data['id'], employee_id, role_name, None, advance_amount,
                          advance_amount, 'Аванс', current_month))

                    advance_id = cursor.lastrowid

                    # Создаем доплату
                    cursor.execute('''
                    INSERT INTO payments
                    (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                     final_amount, payment_type, report_month)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (contract_id, self.card_data['id'], employee_id, role_name, None, balance_amount,
                          balance_amount, 'Доплата', ''))

                    balance_id = cursor.lastrowid

                    conn.commit()
                    self.db.close()

                    print(f"✓ Созданы аванс (ID={advance_id}, {advance_amount:.2f} ₽) и доплата (ID={balance_id}, {balance_amount:.2f} ₽) для СДП")

                # Для остальных ролей - создаем одну выплату "Полная оплата"
                else:
                    payment_id = self.db.create_payment_record(
                        contract_id, employee_id, role_name,
                        payment_type='Полная оплата',
                        report_month='',
                        crm_card_id=self.card_data['id']
                    )

                    if payment_id:
                        print(f"✓ Создана выплата ID={payment_id} для роли {role_name}")
            else:
                print(f"ℹ️ Сотрудник не назначен, выплаты удалены")

            # Обновляем вкладку оплат
            self.refresh_payments_tab()
            print(f"✓ Вкладка оплат обновлена")

        except Exception as e:
            print(f"[ERROR] Ошибка при обновлении выплат: {e}")
            import traceback
            traceback.print_exc()

    def reassign_executor_from_dialog(self, executor_type):
        """Переназначение исполнителя из диалога редактирования"""
        current_column = self.card_data.get('column_name', '')
        
        # Определяем параметры
        if executor_type == 'designer':
            position = 'Дизайнер'
            stage_keyword = 'концепция'
            current_name = self.card_data.get('designer_name', 'Не назначен')
        else:  # draftsman
            position = 'Чертёжник'
            current_name = self.card_data.get('draftsman_name', 'Не назначен')
            if 'планировочные' in current_column.lower():
                stage_keyword = 'планировочные'
            else:
                stage_keyword = 'чертежи'
        
        # Открываем диалог переназначения
        dialog = ReassignExecutorDialog(
            self, 
            self.card_data['id'], 
            position, 
            stage_keyword, 
            executor_type,
            current_name,
            current_column
        )
        
        if dialog.exec_() == QDialog.Accepted:
            # ИСПРАВЛЕНИЕ: Обновляем данные карточки
            self.card_data = self.db.get_crm_card_data(self.card_data['id'])

            # Обновляем только отображаемые данные исполнителей без полной перезагрузки
            self._loading_data = True  # Отключаем автосохранение

            # Обновляем блоки дизайнера и чертежника
            if hasattr(self, 'designer_name_label') and self.card_data.get('designer_name'):
                self.designer_name_label.setText(self.card_data['designer_name'])
            if hasattr(self, 'designer_deadline') and self.card_data.get('designer_deadline'):
                self.designer_deadline.setDate(QDate.fromString(self.card_data['designer_deadline'], 'yyyy-MM-dd'))

            if hasattr(self, 'draftsman_name_label') and self.card_data.get('draftsman_name'):
                self.draftsman_name_label.setText(self.card_data['draftsman_name'])
            if hasattr(self, 'draftsman_deadline') and self.card_data.get('draftsman_deadline'):
                self.draftsman_deadline.setDate(QDate.fromString(self.card_data['draftsman_deadline'], 'yyyy-MM-dd'))

            self._loading_data = False  # Включаем обратно автосохранение

            # ИСПРАВЛЕНИЕ: Не вызываем parent.refresh_current_tab() здесь,
            # чтобы не закрывать диалог. Обновление канбана произойдет при закрытии диалога.

            # Показываем сообщение об успехе без закрытия диалога
            CustomMessageBox(
                self,
                'Успех',
                'Исполнитель переназначен! Данные обновлены.',
                'success'
            ).exec_()

            print("✓ Исполнитель переназначен, диалог остался открытым")       
    
    def delete_order(self):
        """Удаление заказа"""
        # ========== ЗАМЕНИЛИ QMessageBox ==========
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            f"Вы точно хотите удалить заказ?\n\n"
            f"Договор: {self.card_data.get('contract_number', 'N/A')}\n"
            f"Адрес: {self.card_data.get('address', 'N/A')}\n\n"
            f"ВНИМАНИЕ: Это действие нельзя отменить!\n"
            f"Будут удалены:\n"
            f"• Карточка в CRM\n"
            f"• Договор\n"
            f"• Все связанные данные (исполнители, этапы согласования)"
        ).exec_()
        
        if reply == QDialog.Accepted:
            try:
                contract_id = self.card_data.get('contract_id')
                crm_card_id = self.card_data.get('id')
                
                self.db.delete_order(contract_id, crm_card_id)
                
                CustomMessageBox(
                    self, 
                    'Успех', 
                    'Заказ успешно удален из системы',
                    'success'
                ).exec_()
                self.accept()
                
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()
                
            except Exception as e:
                print(f" Ошибка удаления заказа: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить заказ:\n{str(e)}', 'error').exec_()
                
    def create_payments_tab(self):
        """Создание вкладки оплат"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        header = QLabel('Оплаты по проекту')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)
        
        # Таблица выплат
        table = QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
            }
            QTableCornerButton::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
        """)
        table.setColumnCount(10)  # ИСПРАВЛЕНИЕ: Увеличено с 9 до 10 (добавлен столбец удаления)
        table.setHorizontalHeaderLabels([
            'Должность', 'ФИО', 'Стадия', 'Тип выплаты', 'Выплата (₽)', 'Аванс (₽)', 'Доплата (₽)', 'Отчетный месяц', 'Корректировка', 'Действия'
        ])
        # ИСПРАВЛЕНИЕ: Перераспределение ширины столбцов с минимальными значениями
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Должность
        header.setSectionResizeMode(1, QHeaderView.Stretch)            # ФИО
        header.setMinimumSectionSize(150)  # Минимальная ширина для читаемости
        header.resizeSection(1, 200)  # Начальная ширина ФИО
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)  # Стадия
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)  # Тип выплаты
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Выплата
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)  # Аванс
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)  # Доплата
        header.setSectionResizeMode(7, QHeaderView.Stretch)            # Отчетный месяц
        header.resizeSection(7, 150)  # Начальная ширина Отчетный месяц
        header.setSectionResizeMode(8, QHeaderView.ResizeToContents)  # Корректировка
        header.setSectionResizeMode(9, QHeaderView.ResizeToContents)  # Действия
        
        # Загружаем выплаты из БД
        payments = self.db.get_payments_for_contract(self.card_data['contract_id'])
        table.setRowCount(len(payments))
        
        print(f"\n[PAYMENTS TAB] Загружено выплат: {len(payments)}")
        
        for row, payment in enumerate(payments):
            # Определяем цвет строки в зависимости от статуса
            if payment.get('reassigned'):
                row_color = QColor('#FFF9C4')  # Светло-желтый для переназначения
            else:
                payment_status = payment.get('payment_status')
                if payment_status == 'to_pay':
                    row_color = QColor('#FFF3CD')  # Светло-желтый
                elif payment_status == 'paid':
                    row_color = QColor('#D4EDDA')  # Светло-зеленый
                else:
                    row_color = QColor('#FFFFFF')  # Белый

            # Должность
            role_label = QLabel(payment['role'])
            role_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
            role_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setCellWidget(row, 0, role_label)

            # ФИО
            name_label = QLabel(payment['employee_name'])
            name_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
            name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setCellWidget(row, 1, name_label)

            # Стадия
            stage_text = payment.get('stage_name', '-')
            stage_label = QLabel(stage_text)
            stage_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
            stage_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setCellWidget(row, 2, stage_label)

            # Тип выплаты
            payment_type = payment.get('payment_type', 'Полная оплата')
            type_label = QLabel(payment_type)
            type_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
            type_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setCellWidget(row, 3, type_label)

            # ИСПРАВЛЕНИЕ: Разделяем суммы по столбцам
            # Полная выплата (столбец 4)
            if payment_type == 'Полная оплата':
                full_widget = QWidget()
                full_widget.setStyleSheet(f"background-color: {row_color.name()};")
                full_layout = QHBoxLayout()
                full_layout.setContentsMargins(5, 0, 5, 0)

                full_label = QLabel(f"{payment['final_amount']:,.2f} ₽")
                full_label.setStyleSheet('font-weight: bold; color: #27AE60;')

                if payment.get('is_manual'):
                    manual_icon = QLabel(' ★')
                    manual_icon.setStyleSheet('color: #FF9800; font-size: 7px;')
                    manual_icon.setToolTip('Сумма установлена вручную')
                    full_layout.addWidget(manual_icon)

                full_layout.addWidget(full_label)
                full_layout.addStretch()
                full_widget.setLayout(full_layout)
                table.setCellWidget(row, 4, full_widget)

                # Аванс - пустой
                advance_empty = QLabel('-')
                advance_empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
                advance_empty.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 5, advance_empty)

                # Доплата - пустой
                balance_empty = QLabel('-')
                balance_empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
                balance_empty.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 6, balance_empty)
            # Аванс (столбец 5)
            elif payment_type == 'Аванс':
                # Полная выплата - пустой
                full_empty = QLabel('-')
                full_empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
                full_empty.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 4, full_empty)
                advance_widget = QWidget()
                advance_widget.setStyleSheet(f"background-color: {row_color.name()};")
                advance_layout = QHBoxLayout()
                advance_layout.setContentsMargins(5, 0, 5, 0)

                advance_label = QLabel(f"{payment['final_amount']:,.2f} ₽")
                advance_label.setStyleSheet('font-weight: bold; color: #3498DB;')

                if payment.get('is_manual'):
                    manual_icon = QLabel(' ★')
                    manual_icon.setStyleSheet('color: #FF9800; font-size: 7px;')
                    manual_icon.setToolTip('Сумма установлена вручную')
                    advance_layout.addWidget(manual_icon)

                advance_layout.addWidget(advance_label)
                advance_layout.addStretch()
                advance_widget.setLayout(advance_layout)
                table.setCellWidget(row, 5, advance_widget)

                # Доплата - пустой
                balance_empty2 = QLabel('-')
                balance_empty2.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
                balance_empty2.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 6, balance_empty2)
            # Доплата (столбец 6)
            else:  # payment_type == 'Доплата'
                # Полная выплата - пустой
                full_empty2 = QLabel('-')
                full_empty2.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
                full_empty2.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 4, full_empty2)

                # Аванс - пустой
                advance_empty2 = QLabel('-')
                advance_empty2.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px;")
                advance_empty2.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 5, advance_empty2)
                balance_widget = QWidget()
                balance_widget.setStyleSheet(f"background-color: {row_color.name()};")
                balance_layout = QHBoxLayout()
                balance_layout.setContentsMargins(5, 0, 5, 0)

                balance_label = QLabel(f"{payment['final_amount']:,.2f} ₽")
                balance_label.setStyleSheet('font-weight: bold; color: #E67E22;')

                if payment.get('is_manual'):
                    manual_icon = QLabel(' ★')
                    manual_icon.setStyleSheet('color: #FF9800; font-size: 7px;')
                    manual_icon.setToolTip('Сумма установлена вручную')
                    balance_layout.addWidget(manual_icon)

                balance_layout.addWidget(balance_label)
                balance_layout.addStretch()
                balance_widget.setLayout(balance_layout)
                table.setCellWidget(row, 6, balance_widget)

            # ИСПРАВЛЕНИЕ: Отчетный месяц с учетом статуса контракта (столбец 7)
            report_month = payment.get('report_month', 'Не установлен')
            contract_status = payment.get('contract_status', '')

            # Определяем текст и цвет отчетного месяца
            if contract_status == 'РАСТОРГНУТ':
                month_text = 'Отмена оплаты'
                month_color = '#E74C3C'  # Красный
            elif (contract_status in ['Новый заказ', 'В работе']) and (not report_month or report_month == 'Не установлен'):
                month_text = 'в работе'
                month_color = '#95A5A6'  # Серый
            elif report_month and report_month != 'Не установлен':
                # Преобразуем дату в название месяца
                try:
                    from datetime import datetime
                    date_obj = datetime.strptime(report_month, '%Y-%m')
                    months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                 'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
                    month_text = f"{months_ru[date_obj.month - 1]} {date_obj.year}"
                    month_color = '#333333'  # Черный
                except Exception:
                    month_text = report_month
                    month_color = '#333333'
            else:
                month_text = 'Не установлен'
                month_color = '#E74C3C'  # Красный

            month_label = QLabel(month_text)
            month_label.setStyleSheet(f"background-color: {row_color.name()}; color: {month_color}; padding: 5px;")
            month_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setCellWidget(row, 7, month_label)

            # Кнопка корректировки (столбец 8, только для руководителей)
            if self.employee['position'] in ['Руководитель студии', 'Старший менеджер проектов']:
                # Создаем виджет-контейнер для кнопки корректировки
                adjust_widget = QWidget()
                adjust_widget.setStyleSheet(f"background-color: {row_color.name()};")
                adjust_layout = QHBoxLayout()
                adjust_layout.setContentsMargins(0, 0, 0, 0)

                adjust_btn = QPushButton('✏️ Изменить')
                adjust_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 3px;
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

                delete_btn = QPushButton('🗑️ Удалить')
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E74C3C;
                        color: white;
                        padding: 5px 10px;
                        border-radius: 3px;
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

            print(f"  • {payment['role']}: {payment['employee_name']} - {payment_type} - {payment['final_amount']:.2f} ₽")

        layout.addWidget(table)

        # ИСПРАВЛЕНИЕ: Предупреждение о переназначении
        has_reassigned = any(p.get('reassigned') for p in payments)
        if has_reassigned:
            warning_label = QLabel(
                ' <b>ВНИМАНИЕ!</b> Обнаружено переназначение сотрудников (строки выделены желтым).<br>'
                'Необходимо <b>вручную перераспределить оплату</b> между старым и новым сотрудниками.'
            )
            warning_label.setStyleSheet('''
                background-color: #FFF3CD;
                color: #856404;
                border: 2px solid #FFC107;
                border-radius: 4px;
                padding: 10px;
                font-size: 11px;
                margin: 10px 0;
            ''')
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)

        # Итоговая сумма
        total_amount = sum(p['final_amount'] for p in payments)
        total_label = QLabel(f'<b>Итого к выплате: {total_amount:,.2f} ₽</b>')
        total_label.setStyleSheet('''
            font-size: 14px;
            padding: 10px;
            background-color: #E8F4F8;
            margin-top: 10px;
        ''')
        layout.addWidget(total_label)
        
        widget.setLayout(layout)
        return widget
    
    def adjust_payment_amount(self, payment_id):
        """Диалог корректировки суммы выплаты"""
        # Получаем текущие данные выплаты
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT final_amount, report_month
                FROM payments
                WHERE id = ?
            """, (payment_id,))
            payment_data = cursor.fetchone()
            self.db.close()

            if payment_data:
                current_amount = payment_data['final_amount']
                current_report_month = payment_data['report_month']
            else:
                current_amount = 0
                current_report_month = QDate.currentDate().toString('yyyy-MM')
        except Exception as e:
            print(f"Ошибка при загрузке данных выплаты: {e}")
            current_amount = 0
            current_report_month = QDate.currentDate().toString('yyyy-MM')

        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)

        # Главный layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Рамка
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

        # Title Bar
        title_bar = CustomTitleBar(dialog, 'Корректировка выплаты', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # ИСПРАВЛЕНИЕ: Уменьшены размеры на 30%
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(10)  # было 15
        layout.setContentsMargins(14, 14, 14, 14)  # было 20, 20, 20, 20

        # Подсказка
        hint_label = QLabel('Введите новую сумму выплаты:')
        hint_label.setStyleSheet('font-size: 10px; color: #666666;')  # было 12px
        layout.addWidget(hint_label)

        # ИСПРАВЛЕНИЕ: Поле ввода суммы с кастомными стрелками
        amount_container = QWidget()
        amount_layout = QHBoxLayout()
        amount_layout.setContentsMargins(0, 0, 0, 0)
        amount_layout.setSpacing(4)  # было 5

        amount_spin = QDoubleSpinBox()
        amount_spin.setRange(0, 10000000)
        amount_spin.setSuffix(' ₽')
        amount_spin.setDecimals(2)
        amount_spin.setValue(current_amount)
        amount_spin.setSpecialValueText('Введите сумму...')
        amount_spin.setButtonSymbols(QDoubleSpinBox.NoButtons)  # Убираем стандартные кнопки
        amount_spin.setStyleSheet("""
            QDoubleSpinBox {
                padding: 6px;
                font-size: 11px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QDoubleSpinBox:focus {
                border: 1px solid #3498DB;
            }
        """)
        amount_layout.addWidget(amount_spin, 1)

        # Кастомные кнопки вверх/вниз с иконками
        buttons_container = QWidget()
        buttons_vert_layout = QVBoxLayout()
        buttons_vert_layout.setContentsMargins(0, 0, 0, 0)
        buttons_vert_layout.setSpacing(2)

        up_btn = QPushButton()
        up_btn.setIcon(IconLoader.load('arrow-up-circle'))
        up_btn.setIconSize(QSize(14, 14))  # было 20, 20
        up_btn.setFixedSize(17, 17)  # было 24, 24
        up_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
            QPushButton:hover { background-color: #E8F8F5; border-radius: 3px; }
        """)
        up_btn.clicked.connect(lambda: amount_spin.stepUp())

        down_btn = QPushButton()
        down_btn.setIcon(IconLoader.load('arrow-down-circle'))
        down_btn.setIconSize(QSize(14, 14))  # было 20, 20
        down_btn.setFixedSize(17, 17)  # было 24, 24
        down_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 0px;
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
        months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                     'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_combo.addItems(months_ru)

        # Устанавливаем текущий месяц из БД
        try:
            if current_report_month and current_report_month != 'Не установлен':
                from datetime import datetime
                date_obj = datetime.strptime(current_report_month, '%Y-%m')
                month_combo.setCurrentIndex(date_obj.month - 1)
            else:
                month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        except Exception:
            month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        month_combo.setStyleSheet("""
            QComboBox {
                padding: 6px;
                font-size: 11px;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #3498DB;
            }
        """)
        month_layout.addWidget(month_combo, 1)

        # Выбор года
        year_combo = CustomComboBox()
        current_year = QDate.currentDate().year()
        for year in range(current_year - 2, current_year + 3):
            year_combo.addItem(str(year))

        # Устанавливаем текущий год из БД
        try:
            if current_report_month and current_report_month != 'Не установлен':
                from datetime import datetime
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
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                background-color: #FFFFFF;
            }
            QComboBox:focus {
                border: 1px solid #3498DB;
            }
        """)
        month_layout.addWidget(year_combo)

        layout.addLayout(month_layout)

        # Кнопки
        buttons_layout = QHBoxLayout()

        save_btn = QPushButton('✓ Сохранить')
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

        dialog.setFixedWidth(280)  # было 400

        # Центрирование на экране
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - dialog.width()) // 2 + screen.left()
        y = (screen.height() - dialog.height()) // 3 + screen.top()
        dialog.move(x, y)

        # ИСПРАВЛЕНИЕ: Автофокус на поле ввода + выделение текста
        amount_spin.setFocus()
        amount_spin.selectAll()

        dialog.exec_()

    def save_manual_amount(self, payment_id, amount, month, year, dialog):
        """Сохранение ручной суммы и отчетного месяца"""
        # Формируем отчетный месяц в формате YYYY-MM
        report_month = f"{year}-{month:02d}"

        # Обновляем сумму
        self.db.update_payment_manual(payment_id, amount)

        # Обновляем отчетный месяц
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE payments
                SET report_month = ?
                WHERE id = ?
            """, (report_month, payment_id))
            conn.commit()
            self.db.close()
        except Exception as e:
            print(f"Ошибка при обновлении отчетного месяца: {e}")

        # Показываем сообщение с русским названием месяца
        months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                     'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_name = months_ru[month - 1]

        CustomMessageBox(self, 'Успех',
                        f'Сумма обновлена: {amount:,.2f} ₽\nОтчетный месяц: {month_name} {year}',
                        'success').exec_()
        dialog.accept()

        # Обновляем вкладку оплат в карточке
        self.refresh_payments_tab()

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

                print(f"✓ Оплата удалена: {role} - {employee_name} (ID: {payment_id})")

                # Показываем сообщение об успехе
                CustomMessageBox(
                    self,
                    'Успех',
                    f'Оплата успешно удалена:\n{role} - {employee_name}',
                    'success'
                ).exec_()

                # Обновляем вкладку оплат
                self.refresh_payments_tab()

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
        
    def reject(self):
        """ИСПРАВЛЕНИЕ: Обновляем канбан при закрытии диалога"""
        # Обновляем родительскую вкладку (канбан доску)
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()

        super().reject()

    def on_stage_files_uploaded(self, stage):
        """Обработчик успешной загрузки файлов стадии"""
        print(f"[DEBUG] on_stage_files_uploaded начался для stage={stage}")
        print(f"[OK] Файлы стадии {stage} успешно загружены")

        print(f"[DEBUG] Вызов reload_stage_files...")
        self.reload_stage_files(stage)
        print(f"[DEBUG] reload_stage_files завершен")

        # Добавляем запись в историю проекта
        if self.employee:
            print(f"[DEBUG] Добавление записи в историю...")
            from datetime import datetime

            # Определяем тип проекта из contracts (а не из card_data!)
            contract_id = self.card_data.get('contract_id')
            if contract_id:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
                result = cursor.fetchone()
                conn.close()
                project_type = result['project_type'] if result else None
            else:
                project_type = None

            print(f"[DEBUG] project_type из contracts: '{project_type}'")
            is_template = project_type == 'Шаблонный'
            print(f"[DEBUG] is_template: {is_template}, stage: {stage}")

            # Определяем название стадии для отображения
            stage_names = {
                'stage1': '1 стадия - Планировочное решение',
                'stage2_concept': '2 стадия - Концепция дизайна (Концепция-коллажи)',
                'stage2_3d': '3 стадия - 3D визуализация (дополнительная)' if is_template else '2 стадия - Концепция дизайна (3D визуализация)',
                'stage3': '2 стадия - Чертежный проект' if is_template else '3 стадия - Чертежный проект'
            }
            stage_name = stage_names.get(stage, stage)
            print(f"[DEBUG] Выбранное название стадии: '{stage_name}'")
            description = f"Добавлены файлы в стадию: {stage_name}"

            print(f"[DEBUG] Вызов add_action_history...")
            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_upload',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            print(f"[DEBUG] add_action_history завершен")

            print(f"[DEBUG] Вызов reload_project_history...")
            try:
                self.reload_project_history()
                print(f"[DEBUG] reload_project_history завершен")

                # Принудительно обрабатываем отложенные события Qt (deleteLater и др.)
                from PyQt5.QtWidgets import QApplication
                print(f"[DEBUG] Вызов processEvents для обработки deleteLater...")
                QApplication.processEvents()
                print(f"[DEBUG] processEvents завершен")

                print(f"[OK] Добавлена запись в историю: {description}")
            except Exception as e:
                print(f"[ERROR] Ошибка в reload_project_history или processEvents: {e}")
                import traceback
                traceback.print_exc()

        print(f"[DEBUG] on_stage_files_uploaded завершен")

    def on_stage_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файлов"""
        from ui.custom_message_box import CustomMessageBox
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов:\n{error_msg}', 'error').exec_()

    def upload_stage_files(self, stage):
        """Множественная загрузка файлов для стадии"""
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        import threading
        import os
        from config import YANDEX_DISK_TOKEN
        from utils.yandex_disk import YandexDiskManager
        from utils.preview_generator import PreviewGenerator

        # Определяем фильтр файлов
        if stage == 'stage1':
            file_filter = "PDF Files (*.pdf)"
        elif stage in ['stage2_concept', 'stage2_3d']:
            file_filter = "Images and PDF (*.jpg *.jpeg *.png *.pdf)"
        elif stage == 'stage3':
            file_filter = "PDF and Excel (*.pdf *.xls *.xlsx)"
        else:
            file_filter = "All Files (*.*)"

        file_paths, _ = QFileDialog.getOpenFileNames(self, "Выберите файлы для загрузки", "", file_filter)
        if not file_paths:
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result['yandex_folder_path']:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', 'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.', 'warning').exec_()
            return

        contract_folder = result['yandex_folder_path']

        # Количество шагов: загрузка файлов + обработка файлов
        total_steps = len(file_paths) * 2
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, total_steps, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файлов")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        # Убираем стандартную рамку и добавляем кастомную
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        # Устанавливаем фиксированные размеры (увеличены на 20%)
        progress.setFixedSize(420, 144)  # было бы 350x120, увеличено на 20%

        # Стилизация прогресс-бара (светло-зеленый) + закругленные углы
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        def upload_thread():
            try:
                from database.db_manager import DatabaseManager

                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                # Callback для обновления прогресса загрузки
                def update_upload_progress(current, total, file_name, phase):
                    if progress.wasCanceled():
                        return
                    step = current + 1
                    percent = int((step / total) * 50)  # первые 50% - загрузка
                    progress.setValue(step)
                    progress.setLabelText(f"Загрузка на Яндекс.Диск: {file_name}\n{step}/{total} ({percent}%)")

                uploaded_files = yd.upload_stage_files(file_paths, contract_folder, stage, progress_callback=update_upload_progress)

                # Создаем новое подключение к БД для потока
                thread_db = DatabaseManager()

                for i, file_data in enumerate(uploaded_files):
                    if progress.wasCanceled():
                        break

                    current = i + 1
                    total = len(uploaded_files)
                    # Вторые 50% - обработка файлов (превьюшки + БД)
                    step = len(file_paths) + current
                    percent = 50 + int((current / total) * 50)
                    progress.setValue(step)
                    progress.setLabelText(f"Обработка {file_data['file_name']}...\n{current}/{total} ({percent}%)")

                    ext = os.path.splitext(file_data['file_name'])[1].lower()
                    if ext in ['.jpg', '.jpeg', '.png']:
                        file_type = 'image'
                    elif ext == '.pdf':
                        file_type = 'pdf'
                    elif ext in ['.xls', '.xlsx']:
                        file_type = 'excel'
                    else:
                        file_type = 'unknown'

                    preview_cache_path = None
                    if file_type in ['image', 'pdf']:
                        cache_path = PreviewGenerator.get_cache_path(contract_id, stage, file_data['file_name'])
                        pixmap = PreviewGenerator.generate_preview_for_file(file_data['local_path'], file_type)
                        if pixmap:
                            PreviewGenerator.save_preview_to_cache(pixmap, cache_path)
                            preview_cache_path = cache_path

                    thread_db.add_project_file(
                        contract_id=contract_id,
                        stage=stage,
                        file_type=file_type,
                        public_link=file_data['public_link'],
                        yandex_path=file_data['yandex_path'],
                        file_name=file_data['file_name'],
                        preview_cache_path=preview_cache_path
                    )
                    print(f"[DEBUG upload_thread] Файл {file_data['file_name']} добавлен в БД")

                print(f"[DEBUG upload_thread] Закрытие прогресс-диалога через QTimer...")
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                print(f"[DEBUG upload_thread] Отправка сигнала stage_files_uploaded...")
                self.stage_files_uploaded.emit(stage)
                print(f"[DEBUG upload_thread] Сигнал отправлен, поток завершен")
            except Exception as e:
                print(f"[DEBUG upload_thread] Ошибка: {e}")
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                self.stage_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def delete_stage_file(self, file_id, stage):
        """Удаление файла стадии"""
        from ui.custom_message_box import CustomQuestionBox
        from PyQt5.QtWidgets import QDialog
        from config import YANDEX_DISK_TOKEN
        from utils.yandex_disk import YandexDiskManager
        import os

        reply = CustomQuestionBox(self, 'Подтверждение', 'Вы уверены, что хотите удалить этот файл?').exec_()
        if reply != QDialog.Accepted:
            return

        print(f"[DEBUG] Удаление файла с ID: {file_id}")
        file_info = self.db.delete_project_file(file_id)
        print(f"[DEBUG] Информация о файле из БД: {file_info}")

        if file_info:
            print(f"[DEBUG] Попытка удаления файла из Яндекс.Диска: {file_info.get('yandex_path')}")
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                yd.delete_file(file_info['yandex_path'])
                print(f"[OK] Файл успешно удален из Яндекс.Диска: {file_info['yandex_path']}")
            except Exception as e:
                print(f"[ERROR] Не удалось удалить файл с Яндекс.Диска: {e}")
                import traceback
                traceback.print_exc()

            if file_info.get('preview_cache_path'):
                try:
                    if os.path.exists(file_info['preview_cache_path']):
                        os.remove(file_info['preview_cache_path'])
                except:
                    pass

            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime

                # Определяем тип проекта из contracts
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
                    result = cursor.fetchone()
                    conn.close()
                    project_type = result['project_type'] if result else None
                else:
                    project_type = None

                is_template = project_type == 'Шаблонный'

                # Определяем название стадии для более понятного описания с учетом типа проекта
                stage_names = {
                    'stage1': 'Стадия 1 - Планировочное решение',
                    'stage2_concept': 'Стадия 2 (Концепция)',
                    'stage2_3d': '3 стадия - 3D визуализация (дополнительная)' if is_template else 'Стадия 2 (3D)',
                    'stage3': '2 стадия - Чертежный проект' if is_template else 'Стадия 3 (Чертежный проект)'
                }
                stage_name = stage_names.get(stage, stage)
                description = f"Удален файл из {stage_name}: {file_info.get('file_name', 'файл')}"

                self.db.add_action_history(
                    user_id=self.employee.get('id'),
                    action_type='file_delete',
                    entity_type='crm_card',
                    entity_id=self.card_data['id'],
                    description=description
                )
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

            self.reload_stage_files(stage)
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Успех', 'Файл удален', 'success').exec_()

    def upload_stage_files_with_variation(self, stage, variation):
        """Загрузка файлов для стадии с указанием вариации"""
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        import threading
        import os
        from config import YANDEX_DISK_TOKEN
        from utils.yandex_disk import YandexDiskManager
        from utils.preview_generator import PreviewGenerator

        # Определяем фильтр файлов
        if stage in ['stage2_concept', 'stage2_3d']:
            file_filter = "Images and PDF (*.jpg *.jpeg *.png *.pdf)"
        else:
            file_filter = "All Files (*.*)"

        file_paths, _ = QFileDialog.getOpenFileNames(self, f"Выберите файлы для Вариации {variation}", "", file_filter)
        if not file_paths:
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        result = cursor.fetchone()
        conn.close()

        if not result or not result['yandex_folder_path']:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', 'Папка договора на Яндекс.Диске не найдена.', 'warning').exec_()
            return

        contract_folder = result['yandex_folder_path']

        # Создаем прогресс-диалог
        total_steps = len(file_paths) * 2
        progress = QProgressDialog("Подготовка к загрузке...", "Отмена", 0, total_steps, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Загрузка файлов")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #C0392B;
            }
            QDialogButtonBox {
                alignment: center;
            }
        """)
        progress.show()

        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                current_step = 0

                def update_progress(index, total, fname, phase):
                    nonlocal current_step
                    if progress.wasCanceled():
                        return
                    current_step = index
                    progress.setValue(current_step)
                    percent = int((current_step / total_steps) * 100)
                    progress.setLabelText(f"Загрузка: {fname}\n({index}/{len(file_paths)} файлов - {percent}%)")

                # Загружаем файлы с указанием вариации
                uploaded_files = yd.upload_stage_files(
                    file_paths,
                    contract_folder,
                    stage,
                    variation=variation,
                    progress_callback=update_progress
                )

                if not uploaded_files:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    self.stage_upload_error.emit("Не удалось загрузить файлы")
                    return

                # Генерируем превью и сохраняем в БД
                for i, uploaded_file in enumerate(uploaded_files):
                    if progress.wasCanceled():
                        return

                    current_step = len(file_paths) + i
                    progress.setValue(current_step)
                    percent = int((current_step / total_steps) * 100)
                    progress.setLabelText(f"Обработка: {uploaded_file['file_name']}\n({i+1}/{len(uploaded_files)} файлов - {percent}%)")

                    # Генерация превью
                    preview_cache_path = None
                    file_type = 'pdf' if uploaded_file['file_name'].lower().endswith('.pdf') else 'image'

                    if file_type in ['image', 'pdf']:
                        cache_path = PreviewGenerator.get_cache_path(contract_id, stage, uploaded_file['file_name'])
                        pixmap = PreviewGenerator.generate_preview_for_file(uploaded_file['local_path'], file_type)
                        if pixmap:
                            PreviewGenerator.save_preview_to_cache(pixmap, cache_path)
                            preview_cache_path = cache_path

                    # Сохраняем в БД с указанием вариации
                    self.db.add_project_file(
                        contract_id=contract_id,
                        stage=stage,
                        file_type=file_type,
                        public_link=uploaded_file.get('public_link', ''),
                        yandex_path=uploaded_file['yandex_path'],
                        file_name=uploaded_file['file_name'],
                        preview_cache_path=preview_cache_path,
                        variation=variation
                    )

                progress.setValue(total_steps)
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                self.stage_files_uploaded.emit(stage)

            except Exception as e:
                print(f"[ERROR] Ошибка загрузки файлов: {e}")
                import traceback
                traceback.print_exc()
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                self.stage_upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def delete_stage_file_with_variation(self, file_id, stage, variation):
        """Удаление файла стадии с учетом вариации"""
        self.delete_stage_file(file_id, stage)

    def add_variation_folder(self, stage):
        """Создание новой вариации (папки на Яндекс.Диске)"""
        # Папка будет создана автоматически при первой загрузке файлов
        print(f"[INFO] Создание новой вариации для {stage}")

    def delete_variation_folder(self, stage, variation):
        """Удаление вариации (папки и всех файлов)"""
        from ui.custom_message_box import CustomQuestionBox
        from PyQt5.QtWidgets import QDialog, QProgressDialog
        from config import YANDEX_DISK_TOKEN
        from utils.yandex_disk import YandexDiskManager
        import os

        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            f'Вы уверены, что хотите удалить Вариацию {variation}?\nВсе файлы этой вариации будут удалены.'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Получаем все файлы этой вариации
        files = self.db.get_project_files(contract_id, stage)
        variation_files = [f for f in files if f.get('variation', 1) == variation]

        if not variation_files:
            # Если файлов нет, просто удаляем вкладку
            if stage == 'stage2_concept' and hasattr(self, 'stage2_concept_gallery'):
                self.stage2_concept_gallery.remove_variation_tab(variation)
            elif stage == 'stage2_3d' and hasattr(self, 'stage2_3d_gallery'):
                self.stage2_3d_gallery.remove_variation_tab(variation)
            return

        # Создаем прогресс-диалог
        total_steps = len(variation_files) + 1  # файлы + папка
        progress = QProgressDialog("Удаление файлов...", None, 0, total_steps, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("Удаление вариации")
        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)
        progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        progress.setFixedSize(420, 144)
        progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
        """)
        progress.show()

        yd = YandexDiskManager(YANDEX_DISK_TOKEN)

        # Удаляем файлы из БД и Яндекс.Диска
        for i, file_data in enumerate(variation_files):
            percent = int((i / total_steps) * 100)
            progress.setValue(i)
            progress.setLabelText(f"Удаление: {file_data['file_name']}\n({i+1}/{len(variation_files)} файлов - {percent}%)")

            file_info = self.db.delete_project_file(file_data['id'])
            if file_info:
                try:
                    yd.delete_file(file_info['yandex_path'])
                except Exception as e:
                    print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")

                if file_info.get('preview_cache_path'):
                    try:
                        if os.path.exists(file_info['preview_cache_path']):
                            os.remove(file_info['preview_cache_path'])
                    except:
                        pass

        # Удаляем папку вариации с Яндекс.Диска
        progress.setValue(len(variation_files))
        progress.setLabelText(f"Удаление папки...\n({total_steps}/{total_steps} - 100%)")

        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
            result = cursor.fetchone()
            conn.close()

            if result and result['yandex_folder_path']:
                variation_folder = yd.get_stage_folder_path(
                    result['yandex_folder_path'],
                    stage,
                    variation=variation
                )
                if variation_folder:
                    yd.delete_folder(variation_folder)
        except Exception as e:
            print(f"[WARN] Не удалось удалить папку вариации с Яндекс.Диска: {e}")

        # Завершаем прогресс
        progress.setValue(total_steps)
        # ИСПРАВЛЕНИЕ: Закрываем прогресс через QTimer для безопасности
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, progress.close)

        # Добавляем запись в историю проекта
        if self.employee and len(variation_files) > 0:
            from datetime import datetime

            # Определяем тип проекта из contracts
            contract_id = self.card_data.get('contract_id')
            if contract_id:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
                result = cursor.fetchone()
                conn.close()
                project_type = result['project_type'] if result else None
            else:
                project_type = None

            is_template = project_type == 'Шаблонный'

            # Определяем название стадии для более понятного описания с учетом типа проекта
            stage_names = {
                'stage2_concept': 'Стадия 2 (Концепция)',
                'stage2_3d': '3 стадия - 3D визуализация (дополнительная)' if is_template else 'Стадия 2 (3D)'
            }
            stage_name = stage_names.get(stage, stage)
            description = f"Удалена Вариация {variation} из {stage_name} ({len(variation_files)} файлов)"

            self.db.add_action_history(
                user_id=self.employee.get('id'),
                action_type='file_delete',
                entity_type='crm_card',
                entity_id=self.card_data['id'],
                description=description
            )
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Удаляем вкладку из UI
        if stage == 'stage2_concept' and hasattr(self, 'stage2_concept_gallery'):
            self.stage2_concept_gallery.remove_variation_tab(variation)
        elif stage == 'stage2_3d' and hasattr(self, 'stage2_3d_gallery'):
            self.stage2_3d_gallery.remove_variation_tab(variation)

    def reload_stage_files(self, stage):
        """Перезагрузка файлов стадии"""
        from database.db_manager import DatabaseManager

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Создаем новое подключение к БД (thread-safe)
        db = DatabaseManager()
        files = db.get_project_files(contract_id, stage)

        if stage == 'stage1' and hasattr(self, 'stage1_list'):
            self.stage1_list.load_files(files)
        elif stage == 'stage2_concept' and hasattr(self, 'stage2_concept_gallery'):
            # Группируем файлы по вариациям
            variations = {}
            for file_data in files:
                variation = file_data.get('variation', 1)
                if variation not in variations:
                    variations[variation] = []
                variations[variation].append(file_data)

            # Загружаем каждую вариацию
            for variation, variation_files in variations.items():
                self.stage2_concept_gallery.load_files_for_variation(
                    variation, variation_files, self.load_preview_for_file
                )
        elif stage == 'stage2_3d' and hasattr(self, 'stage2_3d_gallery'):
            # Группируем файлы по вариациям
            variations = {}
            for file_data in files:
                variation = file_data.get('variation', 1)
                if variation not in variations:
                    variations[variation] = []
                variations[variation].append(file_data)

            # Загружаем каждую вариацию
            for variation, variation_files in variations.items():
                self.stage2_3d_gallery.load_files_for_variation(
                    variation, variation_files, self.load_preview_for_file
                )
        elif stage == 'stage3' and hasattr(self, 'stage3_list'):
            self.stage3_list.load_files(files)

    def load_preview_for_file(self, file_data):
        """Загрузка превью для файла из кэша"""
        from utils.preview_generator import PreviewGenerator
        import os

        # Пытаемся загрузить из сохраненного пути кэша
        if file_data.get('preview_cache_path'):
            # Проверяем существование файла кэша
            if os.path.exists(file_data['preview_cache_path']):
                pixmap = PreviewGenerator.load_preview_from_cache(file_data['preview_cache_path'])
                if pixmap:
                    return pixmap

        # Если кэш не найден, можно добавить fallback логику здесь
        # (например, повторная генерация превью из Яндекс.Диска)

        return None

    def get_resize_edge(self, pos):
        """Определение края/угла для изменения размера"""
        rect = self.rect()
        margin = self.resize_margin

        on_left = pos.x() <= margin
        on_right = pos.x() >= rect.width() - margin
        on_top = pos.y() <= margin
        on_bottom = pos.y() >= rect.height() - margin

        # Углы (приоритет)
        if on_top and on_left:
            return 'top-left'
        elif on_top and on_right:
            return 'top-right'
        elif on_bottom and on_left:
            return 'bottom-left'
        elif on_bottom and on_right:
            return 'bottom-right'

        # Края
        elif on_top:
            return 'top'
        elif on_bottom:
            return 'bottom'
        elif on_left:
            return 'left'
        elif on_right:
            return 'right'

        return None

    def set_cursor_shape(self, edge):
        """Установка формы курсора"""
        if edge == 'top-left' or edge == 'bottom-right':
            self.setCursor(Qt.SizeFDiagCursor)
        elif edge == 'top-right' or edge == 'bottom-left':
            self.setCursor(Qt.SizeBDiagCursor)
        elif edge == 'left' or edge == 'right':
            self.setCursor(Qt.SizeHorCursor)
        elif edge == 'top' or edge == 'bottom':
            self.setCursor(Qt.SizeVerCursor)
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
                event.accept()
                return
        super().mousePressEvent(event)

    def event(self, event):
        """Обработка событий наведения мыши"""
        if event.type() == event.HoverMove:
            # Изменяем курсор при наведении (без нажатия)
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)

        return super().event(event)

    def mouseMoveEvent(self, event):
        """Процесс изменения размера"""
        if self.resizing and self.resize_edge:
            delta = event.globalPos() - self.resize_start_pos

            old_geometry = self.resize_start_geometry
            x = old_geometry.x()
            y = old_geometry.y()
            w = old_geometry.width()
            h = old_geometry.height()

            edge = self.resize_edge
            # Минимальная ширина для 2 столбцов: 2 * 123 + 20 + margins ≈ 400px
            min_w, min_h = 400, 600

            if 'left' in edge:
                new_x = x + delta.x()
                new_w = w - delta.x()
                if new_w >= min_w:
                    x = new_x
                    w = new_w

            elif 'right' in edge:
                new_w = w + delta.x()
                if new_w >= min_w:
                    w = new_w

            if 'top' in edge:
                new_y = y + delta.y()
                new_h = h - delta.y()
                if new_h >= min_h:
                    y = new_y
                    h = new_h

            elif 'bottom' in edge:
                new_h = h + delta.y()
                if new_h >= min_h:
                    h = new_h

            self.setGeometry(x, y, w, h)

            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Завершение изменения размера"""
        if event.button() == Qt.LeftButton and self.resizing:
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        """Обработка изменения размера окна"""
        super().resizeEvent(event)

        # Используем QTimer для обновления галерей после завершения resize
        if hasattr(self, '_resize_galleries_timer'):
            self._resize_galleries_timer.stop()

        from PyQt5.QtCore import QTimer
        self._resize_galleries_timer = QTimer()
        self._resize_galleries_timer.setSingleShot(True)
        self._resize_galleries_timer.timeout.connect(self._trigger_galleries_resize)
        self._resize_galleries_timer.start(150)

    def _trigger_galleries_resize(self):
        """Принудительно обновляет галереи после изменения размера окна"""
        from PyQt5.QtWidgets import QApplication

        # Принудительно обрабатываем все отложенные события layout'ов
        QApplication.processEvents()

        if hasattr(self, 'stage2_concept_gallery'):
            # VariationGalleryWidget содержит несколько FileGalleryWidget внутри
            if hasattr(self.stage2_concept_gallery, 'variation_galleries'):
                for variation, gallery in self.stage2_concept_gallery.variation_galleries.items():
                    if gallery.preview_widgets:
                        # Сбрасываем current_columns чтобы гарантировать перестройку
                        gallery.current_columns = -1
                        gallery._do_resize()

        if hasattr(self, 'stage2_3d_gallery'):
            # VariationGalleryWidget содержит несколько FileGalleryWidget внутри
            if hasattr(self.stage2_3d_gallery, 'variation_galleries'):
                for variation, gallery in self.stage2_3d_gallery.variation_galleries.items():
                    if gallery.preview_widgets:
                        # Сбрасываем current_columns чтобы гарантировать перестройку
                        gallery.current_columns = -1
                        gallery._do_resize()

class ExecutorSelectionDialog(QDialog):
    def __init__(self, parent, card_id, stage_name, project_type):
        super().__init__(parent)
        self.card_id = card_id
        self.stage_name = stage_name
        self.project_type = project_type
        self.db = DatabaseManager()
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Выбор исполнителя', simple_mode=True)
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
        
        info = QLabel(f'Выберите исполнителя для стадии:')
        info.setStyleSheet('font-size: 13px; font-weight: bold;')
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        stage_frame = QFrame()
        stage_frame.setStyleSheet('''
            QFrame {
                background-color: transparent;
                border: none;
                padding: 0px;
            }
        ''')
        stage_layout = QVBoxLayout()
        
        stage_label = QLabel(f"<b>{self.stage_name}</b>")
        stage_label.setWordWrap(True)
        stage_label.setStyleSheet('font-size: 12px; color: #333;')
        stage_label.setAlignment(Qt.AlignCenter)
        stage_layout.addWidget(stage_label)
        
        stage_frame.setLayout(stage_layout)
        layout.addWidget(stage_frame)

        # ========== НОВОЕ: ИСТОРИЯ ИСПОЛНИТЕЛЕЙ ==========
        # Получаем историю всех исполнителей на предыдущих стадиях
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT DISTINCT se.stage_name, e.full_name, se.assigned_date
            FROM stage_executors se
            JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ?
            ORDER BY se.assigned_date DESC
            ''', (self.card_id,))

            history_records = cursor.fetchall()
            self.db.close()

            if history_records:
                history_frame = QFrame()
                history_frame.setStyleSheet("""
                    QFrame {
                        background-color: #F0F0F0;
                        border: none;
                        border-radius: 4px;
                        padding: 8px;
                    }
                """)
                history_layout = QVBoxLayout()
                history_layout.setContentsMargins(5, 5, 5, 5)
                history_layout.setSpacing(3)

                history_title = QLabel("История исполнителей на других стадиях:")
                history_title.setStyleSheet('font-size: 9px; color: #666; font-style: italic;')
                history_layout.addWidget(history_title)

                # Показываем максимум 5 последних записей
                for record in history_records[:5]:
                    from datetime import datetime
                    try:
                        assigned_date = datetime.strptime(record['assigned_date'], '%Y-%m-%d %H:%M:%S')
                        date_str = assigned_date.strftime('%d.%m.%Y')
                    except Exception:
                        date_str = record['assigned_date'][:10] if record['assigned_date'] else '—'

                    history_item = QLabel(f"• {record['stage_name']}: {record['full_name']} ({date_str})")
                    history_item.setStyleSheet('font-size: 9px; color: #555;')
                    history_layout.addWidget(history_item)

                history_frame.setLayout(history_layout)
                layout.addWidget(history_frame)

        except Exception as e:
            print(f" Не удалось загрузить историю исполнителей: {e}")
        # ==================================================

        form_layout = QFormLayout()

        if 'Стадия 1' in self.stage_name:
            position = 'Чертёжник'
        elif 'Стадия 2' in self.stage_name and 'концепция' in self.stage_name:
            position = 'Дизайнер'
        elif 'Стадия 2' in self.stage_name or 'Стадия 3' in self.stage_name:
            position = 'Чертёжник'
        else:
            position = 'Чертёжник'
        
        self.executor_combo = CustomComboBox()
        executors = self.db.get_employees_by_position(position)

        if not executors:
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Внимание', f'Нет доступных сотрудников с должностью "{position}"', 'warning').exec_()
            self.reject()
            return

        for executor in executors:
            self.executor_combo.addItem(executor['full_name'], executor['id'])

        # ИСПРАВЛЕНИЕ: Предлагаем исполнителя из предыдущих стадий
        previous_executor_id = self.db.get_previous_executor_by_position(self.card_id, position)
        if previous_executor_id:
            for i in range(self.executor_combo.count()):
                if self.executor_combo.itemData(i) == previous_executor_id:
                    self.executor_combo.setCurrentIndex(i)
                    print(f"✓ Предложен исполнитель из предыдущих стадий (ID={previous_executor_id})")
                    break

        form_layout.addRow('Исполнитель:', self.executor_combo)
        
        self.stage_deadline = CustomDateEdit()
        self.stage_deadline.setCalendarPopup(True)
        self.stage_deadline.setDate(QDate.currentDate().addDays(7))
        self.stage_deadline.setDisplayFormat('dd.MM.yyyy')
        self.stage_deadline.setStyleSheet(CALENDAR_STYLE)  # ← ДОБАВЛЕНО
        form_layout.addRow('Дедлайн:', self.stage_deadline)
        
        layout.addLayout(form_layout)
        
        hint = QLabel('💡 Исполнитель получит доступ к карточке после назначения')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic;')
        layout.addWidget(hint)
        
        save_btn = QPushButton('✓ Назначить')
        save_btn.setStyleSheet("""
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
        save_btn.clicked.connect(self.assign_executor)
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
        
        self.setMinimumWidth(450)
    
    def assign_executor(self):
        executor_id = self.executor_combo.currentData()
        deadline = self.stage_deadline.date().toString('yyyy-MM-dd')
        
        current_user_id = self.parent().employee['id']
        
        # Назначаем исполнителя
        self.db.assign_stage_executor(
            self.card_id,
            self.stage_name,
            executor_id,
            current_user_id,
            deadline
        )
        
        # ========== СОЗДАЕМ ВЫПЛАТЫ (АВАНС + ДОПЛАТА) ==========
        try:
            contract_id = self.db.get_contract_id_by_crm_card(self.card_id)
            contract = self.db.get_contract_by_id(contract_id)
            
            # Определяем роль исполнителя
            if 'концепция' in self.stage_name:
                role = 'Дизайнер'
            else:
                role = 'Чертёжник'
            
            # ИСПРАВЛЕНИЕ: Для индивидуальных - создаем АВАНС (50%) и ДОПЛАТУ (50%)
            if contract['project_type'] == 'Индивидуальный':
                # Рассчитываем полную сумму
                full_amount = self.db.calculate_payment_amount(
                    contract_id, executor_id, role, self.stage_name
                )

                # Делим пополам
                advance_amount = full_amount / 2
                balance_amount = full_amount / 2

                current_month = QDate.currentDate().toString('yyyy-MM')

                conn = self.db.connect()
                cursor = conn.cursor()

                # Создаем аванс (50%) - с отчетным месяцем назначения
                cursor.execute('''
                INSERT INTO payments
                (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                 final_amount, payment_type, report_month)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (contract_id, self.card_id, executor_id, role, self.stage_name, advance_amount,
                      advance_amount, 'Аванс', current_month))

                advance_id = cursor.lastrowid

                # Создаем доплату (50%) - без отчетного месяца (установится при принятии)
                cursor.execute('''
                INSERT INTO payments
                (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                 final_amount, payment_type, report_month)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (contract_id, self.card_id, executor_id, role, self.stage_name, balance_amount,
                      balance_amount, 'Доплата', ''))

                balance_id = cursor.lastrowid

                conn.commit()
                self.db.close()

                print(f"✓ Индивидуальный проект: создан аванс (ID={advance_id}, {advance_amount:.2f} ₽) и доплата (ID={balance_id}, {balance_amount:.2f} ₽) для {role}")
            else:
                # ========== ИСПРАВЛЕНИЕ: ШАБЛОННЫЕ ПРОЕКТЫ - СПЕЦИАЛЬНАЯ ЛОГИКА ==========
                # Для стадии 1 (планировочные) создаём выплату с суммой 0.00
                # Для стадии 2 и выше создаём выплату с тарифом из таблицы
                is_stage_1 = ('Стадия 1' in self.stage_name or 'планировочные' in self.stage_name.lower())

                # Создаём выплату с суммой 0.00 для стадии 1, иначе с тарифом
                conn = self.db.connect()
                cursor = conn.cursor()

                # Рассчитываем сумму (для стадии 1 будет 0, для стадии 2+ берём из тарифов)
                if is_stage_1:
                    calculated_amount = 0.00
                    final_amount = 0.00
                    print(f"[INFO] Стадия 1: создаём выплату с суммой 0.00 для {role}")
                else:
                    calculated_amount = self.db.calculate_payment_amount(
                        contract_id, executor_id, role, self.stage_name
                    )
                    final_amount = calculated_amount
                    print(f"[INFO] Стадия 2+: создаём выплату с тарифом {calculated_amount:.2f} ₽ для {role}")

                cursor.execute('''
                INSERT INTO payments
                (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                 final_amount, payment_type, report_month)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (contract_id, self.card_id, executor_id, role, self.stage_name, calculated_amount,
                      final_amount, 'Полная оплата', ''))  # Пустой месяц, установится при сдаче

                conn.commit()
                self.db.close()
                # =========================================================================
            
            print(f"✓ Выплаты созданы для {role} по стадии {self.stage_name}")
            
        except Exception as e:
            print(f" Ошибка создания выплат: {e}")
        # ========================================================
        
        CustomMessageBox(self, 'Успех', 'Исполнитель назначен', 'success').exec_()
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

class ProjectCompletionDialog(QDialog):
    def __init__(self, parent, card_id):
        super().__init__(parent)
        self.card_id = card_id
        self.db = DatabaseManager()
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Завершение проекта', simple_mode=True)
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
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        form_layout = QFormLayout()
        
        self.status = CustomComboBox()
        self.status.addItems(['Проект СДАН', 'Проект передан в АВТОРСКИЙ НАДЗОР', 'Проект РАСТОРГНУТ'])
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
        
        save_btn = QPushButton('Завершить проект')
        save_btn.clicked.connect(self.complete_project)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        layout.addWidget(save_btn)
        
        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 12px 20px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #7F8C8D; }
        """)
        layout.addWidget(cancel_btn)
        
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
            contract_id = self.db.get_contract_id_by_crm_card(self.card_id)
            
            updates = {
                'status': status.replace('Проект ', '').replace('передан в ', '')
            }
            
            if 'РАСТОРГНУТ' in status:
                updates['termination_reason'] = self.termination_reason.toPlainText().strip()
            
            self.db.update_contract(contract_id, updates)
            
            if 'АВТОРСКИЙ НАДЗОР' in status:
                print(f"\n▶ Создание карточки надзора для договора {contract_id}...")
                supervision_card_id = self.db.create_supervision_card(contract_id)
                print(f"  Результат: supervision_card_id = {supervision_card_id}")
            
            print(f"✓ Проект завершен со статусом: {updates['status']}")
            
            # ========== НОВОЕ: УСТАНОВКА ОТЧЕТНОГО МЕСЯЦА ==========
            current_month = QDate.currentDate().toString('yyyy-MM')
            
            conn = self.db.connect()
            cursor = conn.cursor()
            
            # Устанавливаем отчетный месяц для всех выплат без месяца
            cursor.execute('''
            UPDATE payments
            SET report_month = ?
            WHERE contract_id = ? 
              AND (report_month IS NULL OR report_month = '')
            ''', (current_month, contract_id))
            
            rows_updated = cursor.rowcount
            conn.commit()
            self.db.close()
            
            print(f"✓ Установлен отчетный месяц {current_month} для {rows_updated} выплат")
            # =======================================================            
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
      
class CRMStatisticsDialog(QDialog):
    def __init__(self, parent, project_type, employee):
        super().__init__(parent)
        self.project_type = project_type
        self.employee = employee
        self.db = DatabaseManager()
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, f'Статистика CRM - {self.project_type} проекты', simple_mode=True)
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
        
        header = QLabel(f'Статистика: {self.project_type} проекты')
        header.setStyleSheet('font-size: 16px; font-weight: bold; padding: 5px;')
        layout.addWidget(header)
        
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabBar::tab {
                min-width: 220px;
                padding: 10px 10px;
                font-size: 14px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background-color: #E8F4F8;
            }
        """)
        
        # === ВКЛАДКА: Статистика исполнителей ===
        executors_widget = QWidget()
        executors_layout = QVBoxLayout()
        executors_layout.setContentsMargins(10, 10, 10, 10)
        
        filters_group = QGroupBox('Фильтры')
        filters_layout = QVBoxLayout()

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
                background-color: #E8F4F8;
                border-radius: 12px;
            }
        """)
        header_row.addWidget(toggle_filters_btn)
        header_row.addStretch()
        filters_layout.addLayout(header_row)

        # Контейнер для фильтров (который можно сворачивать)
        filters_content = QWidget()
        filters_content_layout = QVBoxLayout(filters_content)
        filters_content_layout.setContentsMargins(0, 0, 0, 0)
        filters_content_layout.setSpacing(8)
        filters_content.hide()  # По умолчанию свернуто

        period_layout = QHBoxLayout()
        period_layout.addWidget(QLabel('Период:'))
        
        self.period_combo = CustomComboBox()
        self.period_combo.addItems(['Все время', 'Месяц', 'Квартал', 'Год'])
        self.period_combo.currentTextChanged.connect(self.on_period_changed)
        period_layout.addWidget(self.period_combo)
        
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2030)
        self.year_spin.setValue(QDate.currentDate().year())
        self.year_spin.valueChanged.connect(self.load_statistics)
        self.year_spin.setPrefix('Год: ')
        period_layout.addWidget(self.year_spin)
        
        self.quarter_combo = CustomComboBox()
        self.quarter_combo.addItems(['Q1', 'Q2', 'Q3', 'Q4'])
        self.quarter_combo.setCurrentIndex((QDate.currentDate().month() - 1) // 3)
        self.quarter_combo.currentIndexChanged.connect(self.load_statistics)
        period_layout.addWidget(self.quarter_combo)
        self.quarter_combo.hide()
        
        self.month_combo = CustomComboBox()
        months = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        self.month_combo.addItems(months)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.month_combo.currentIndexChanged.connect(self.load_statistics)
        period_layout.addWidget(self.month_combo)
        self.month_combo.hide()
        
        period_layout.addStretch()
        filters_content_layout.addLayout(period_layout)

        row2_layout = QHBoxLayout()
        
        row2_layout.addWidget(QLabel('Проект:'))
        self.project_combo = CustomComboBox()
        self.project_combo.addItem('Все проекты', None)
        self.project_combo.setMinimumWidth(250)
        self.load_projects()
        self.project_combo.currentIndexChanged.connect(self.load_statistics)
        row2_layout.addWidget(self.project_combo)
        
        row2_layout.addWidget(QLabel('Исполнитель:'))
        self.executor_combo = CustomComboBox()
        self.executor_combo.addItem('Все', None)
        self.executor_combo.setMinimumWidth(200)
        self.load_executors()
        self.executor_combo.currentIndexChanged.connect(self.load_statistics)
        row2_layout.addWidget(self.executor_combo)
        
        row2_layout.addStretch()
        filters_content_layout.addLayout(row2_layout)

        row3_layout = QHBoxLayout()
        
        row3_layout.addWidget(QLabel('Стадия:'))
        self.stage_combo = CustomComboBox()
        self.stage_combo.addItem('Все', None)
        self.stage_combo.setMinimumWidth(250)
        if self.project_type == 'Индивидуальный':
            stages = [
                'Стадия 1: планировочные решения',
                'Стадия 2: концепция дизайна',
                'Стадия 3: рабочие чертежи'
            ]
        else:
            stages = [
                'Стадия 1: планировочные решения',
                'Стадия 2: рабочие чертежи'
            ]
        for stage in stages:
            self.stage_combo.addItem(stage)
        self.stage_combo.currentIndexChanged.connect(self.load_statistics)
        row3_layout.addWidget(self.stage_combo)
        
        row3_layout.addWidget(QLabel('Статус:'))
        self.status_combo = CustomComboBox()
        self.status_combo.addItems(['Все', 'Выполнено', 'В работе', 'Просрочено'])
        self.status_combo.setMinimumWidth(150)
        self.status_combo.currentIndexChanged.connect(self.load_statistics)
        row3_layout.addWidget(self.status_combo)
        
        row3_layout.addStretch()
        
        # ========== КНОПКА СБРОСА (SVG) ==========
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить фильтры', icon_size=14)
        reset_btn.clicked.connect(self.reset_filters)
        reset_btn.setStyleSheet('padding: 5px 15px;')
        row3_layout.addWidget(reset_btn)

        filters_content_layout.addLayout(row3_layout)

        # Добавляем контейнер фильтров в основной layout
        filters_layout.addWidget(filters_content)

        # Обработчик сворачивания/разворачивания фильтров
        def toggle_filters_stat():
            is_visible = filters_content.isVisible()
            filters_content.setVisible(not is_visible)
            if is_visible:
                toggle_filters_btn.setIcon(IconLoader.load('arrow-down-circle'))
                toggle_filters_btn.setToolTip('Развернуть фильтры')
            else:
                toggle_filters_btn.setIcon(IconLoader.load('arrow-up-circle'))
                toggle_filters_btn.setToolTip('Свернуть фильтры')

        toggle_filters_btn.clicked.connect(toggle_filters_stat)

        filters_group.setLayout(filters_layout)
        executors_layout.addWidget(filters_group)
        
        summary_layout = QHBoxLayout()
        
        self.total_label = QLabel('Всего записей: 0')
        self.total_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #E8F4F8; border-radius: 3px;')
        summary_layout.addWidget(self.total_label)
        
        self.completed_label = QLabel('Выполнено: 0')
        self.completed_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #D5F4E6; border-radius: 3px;')
        summary_layout.addWidget(self.completed_label)
        
        self.in_progress_label = QLabel('В работе: 0')
        self.in_progress_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #FFF3CD; border-radius: 3px;')
        summary_layout.addWidget(self.in_progress_label)
        
        self.overdue_label = QLabel('Просрочено: 0')
        self.overdue_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #FADBD8; border-radius: 3px;')
        summary_layout.addWidget(self.overdue_label)
        
        summary_layout.addStretch()
        executors_layout.addLayout(summary_layout)
        
        self.stats_table = QTableWidget()
        self.stats_table.setStyleSheet("""
            QTableWidget {
                background-color: #FFFFFF;
            }
            QTableCornerButton::section {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
            }
        """)
        self.stats_table.setColumnCount(8)
        self.stats_table.setHorizontalHeaderLabels([
            'Дата назначения', 'Исполнитель', 'Стадия', 'Назначил',
            'Дедлайн', 'Сдано', 'Статус', 'Проект'
        ])
        self.stats_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stats_table.setAlternatingRowColors(True)
        self.stats_table.setSelectionBehavior(QTableWidget.SelectRows)
        
        self.stats_table.setStyleSheet("""
            QTableWidget::item {
                padding: 2px 2px;
            }
        """)
        self.stats_table.verticalHeader().setDefaultSectionSize(30)
        
        executors_layout.addWidget(self.stats_table, 1)
        
        executors_widget.setLayout(executors_layout)
        tabs.addTab(executors_widget, 'Статистика исполнителей')
        
        layout.addWidget(tabs, 1)

        # ========== КНОПКИ ЭКСПОРТА (SVG) ==========
        buttons_layout = QHBoxLayout()
        
        excel_btn = IconLoader.create_icon_button('export', 'Экспорт в Excel', icon_size=16)
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
        
        pdf_btn = IconLoader.create_icon_button('export', 'Экспорт в PDF', icon_size=16)
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
        close_btn.clicked.connect(self.accept)
        close_btn.setStyleSheet('padding: 8px 16px;')
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        # ========== ИСПРАВЛЕНИЕ: АДАПТИВНЫЕ РАЗМЕРЫ ==========
        from PyQt5.QtWidgets import QDesktopWidget
        available_screen = QDesktopWidget().availableGeometry()
        
        max_height = min(int(available_screen.height() * 0.85), 900)
        max_width = min(int(available_screen.width() * 0.9), 1200)
        
        self.setMinimumSize(1200, 900)
        self.setMaximumSize(max_width, max_height)
        # ======================================================
        
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(100, self.load_statistics)
    
    def load_projects(self):
        """Загрузка списка проектов для текущего типа"""
        try:
            projects = self.db.get_projects_by_type(self.project_type)
            
            for project in projects:
                display_text = f"{project['contract_number']} - {project['address']}"
                if project.get('city'):
                    display_text += f" ({project['city']})"
                
                self.project_combo.addItem(display_text, project['contract_id'])
        except Exception as e:
            print(f"Ошибка загрузки проектов: {e}")
            
    def on_period_changed(self, period):
        """Обработка изменения периода"""
        self.year_spin.setVisible(period != 'Все время')
        self.quarter_combo.setVisible(period == 'Квартал')
        self.month_combo.setVisible(period == 'Месяц')
        self.load_statistics()
    
    def load_executors(self):
        """Загрузка списка исполнителей"""
        try:
            designers = self.db.get_employees_by_position('Дизайнер')
            draftsmen = self.db.get_employees_by_position('Чертёжник')
            
            all_executors = designers + draftsmen
            
            seen = set()
            for executor in all_executors:
                if executor['id'] not in seen:
                    self.executor_combo.addItem(
                        f"{executor['full_name']} ({executor['position']})",
                        executor['id']
                    )
                    seen.add(executor['id'])
        except Exception as e:
            print(f"Ошибка загрузки исполнителей: {e}")
            
    def reset_filters(self):
        """Сброс всех фильтров"""
        self.period_combo.setCurrentText('Все время')
        self.project_combo.setCurrentIndex(0)
        self.executor_combo.setCurrentIndex(0)
        self.stage_combo.setCurrentIndex(0)
        self.status_combo.setCurrentIndex(0)
        self.year_spin.setValue(QDate.currentDate().year())
        self.quarter_combo.setCurrentIndex((QDate.currentDate().month() - 1) // 3)
        self.month_combo.setCurrentIndex(QDate.currentDate().month() - 1)
        self.load_statistics()
        
    def load_statistics(self):
        """Загрузка статистики с учетом фильтров"""
        required_attributes = [
            'period_combo', 'year_spin', 'quarter_combo', 'month_combo',
            'project_combo', 'executor_combo', 'stage_combo', 'status_combo',
            'total_label', 'completed_label', 'in_progress_label', 'overdue_label',
            'stats_table'
        ]
        
        for attr in required_attributes:
            if not hasattr(self, attr):
                print(f"⚠ Атрибут '{attr}' еще не создан, пропускаем загрузку статистики")
                return
        
        period = self.period_combo.currentText()
        year = self.year_spin.value()
        quarter = None
        month = None
        
        if period == 'Квартал':
            quarter = self.quarter_combo.currentText()
        elif period == 'Месяц':
            month = self.month_combo.currentIndex() + 1
        
        project_id = self.project_combo.currentData()
        executor_id = self.executor_combo.currentData()
        stage_name = self.stage_combo.currentText() if self.stage_combo.currentIndex() > 0 else None
        status_filter = self.status_combo.currentText()
        
        stats = self.db.get_crm_statistics_filtered(
            self.project_type,
            period,
            year,
            quarter,
            month,
            project_id,
            executor_id,
            stage_name,
            status_filter
        )
        
        total = len(stats)
        completed = sum(1 for s in stats if s.get('completed'))
        in_progress = sum(1 for s in stats if not s.get('completed') and not self.is_overdue(s.get('deadline')))
        overdue = sum(1 for s in stats if not s.get('completed') and self.is_overdue(s.get('deadline')))
        
        self.total_label.setText(f'Всего записей: {total}')
        self.completed_label.setText(f'Выполнено: {completed}')
        self.in_progress_label.setText(f'В работе: {in_progress}')
        self.overdue_label.setText(f'Просрочено: {overdue}')
        
        self.stats_table.setRowCount(len(stats))
        
        for row, stat in enumerate(stats):
            is_overdue = self.is_overdue(stat.get('deadline')) and not stat.get('completed')
            is_completed = stat.get('completed')
            
            if is_overdue:
                row_color = QColor(255, 230, 230)
            elif is_completed:
                row_color = QColor(230, 255, 230)
            else:
                row_color = QColor(255, 255, 255)
            
            date_item = QTableWidgetItem(stat.get('assigned_date', ''))
            date_item.setBackground(row_color)
            self.stats_table.setItem(row, 0, date_item)
            
            executor_item = QTableWidgetItem(stat.get('executor_name', ''))
            executor_item.setBackground(row_color)
            self.stats_table.setItem(row, 1, executor_item)
            
            stage_item = QTableWidgetItem(stat.get('stage_name', ''))
            stage_item.setBackground(row_color)
            self.stats_table.setItem(row, 2, stage_item)
            
            assigned_item = QTableWidgetItem(stat.get('assigned_by_name', ''))
            assigned_item.setBackground(row_color)
            self.stats_table.setItem(row, 3, assigned_item)
            
            deadline_item = QTableWidgetItem(stat.get('deadline', ''))
            deadline_item.setBackground(row_color)
            self.stats_table.setItem(row, 4, deadline_item)

            # ИСПРАВЛЕНИЕ: Колонка "Сдано"
            submitted_item = QTableWidgetItem(stat.get('submitted_date', '') if stat.get('submitted_date') else '')
            submitted_item.setBackground(row_color)
            self.stats_table.setItem(row, 5, submitted_item)

            if stat.get('completed'):
                status_text = f"✓ Завершено {stat.get('completed_date', '')}"
                status_item = QTableWidgetItem(status_text)
            elif is_overdue:
                status_item = QTableWidgetItem('⚠ Просрочено')
            else:
                status_item = QTableWidgetItem('⏳ В работе')

            status_item.setBackground(row_color)
            self.stats_table.setItem(row, 6, status_item)

            project_item = QTableWidgetItem(stat.get('project_info', ''))
            project_item.setBackground(row_color)
            self.stats_table.setItem(row, 7, project_item)
         
    def is_overdue(self, deadline_str):
        """Проверка просрочки дедлайна"""
        if not deadline_str:
            return False
        try:
            deadline = QDate.fromString(deadline_str, 'yyyy-MM-dd')
            return deadline < QDate.currentDate()
        except Exception:
            return False
    
    def export_to_excel(self):
        """Экспорт статистики в Excel"""
        try:
            from PyQt5.QtWidgets import QFileDialog
            import csv
            
            filename, _ = QFileDialog.getSaveFileName(
                self,
                'Сохранить статистику',
                f'crm_statistics_{self.project_type}_{QDate.currentDate().toString("yyyy-MM-dd")}.csv',
                'CSV Files (*.csv)'
            )
            
            if filename:
                with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
                    writer = csv.writer(file, delimiter=';')
                    
                    headers = [
                        'Дата назначения', 'Исполнитель', 'Стадия',
                        'Назначил', 'Дедлайн', 'Сдано', 'Статус', 'Проект'
                    ]
                    writer.writerow(headers)
                    
                    for row in range(self.stats_table.rowCount()):
                        row_data = []
                        for col in range(self.stats_table.columnCount()):
                            item = self.stats_table.item(row, col)
                            row_data.append(item.text() if item else '')
                        writer.writerow(row_data)
                
                # ========== ЗАМЕНИЛИ QMessageBox ==========
                CustomMessageBox(self, 'Успех', f'Статистика экспортирована в:\n{filename}', 'success').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось экспортировать данные:\n{str(e)}', 'error').exec_()
                   
    def export_to_pdf(self):
        """Экспорт в PDF"""
        dialog = ExportPDFDialog(self, f'Отчет CRM {self.project_type} {QDate.currentDate().toString("yyyy-MM-dd")}')
        
        if dialog.exec_() == QDialog.Accepted:
            filename = dialog.get_filename()
            folder = dialog.get_folder()
            
            if folder and filename:
                full_path = f"{folder}/{filename}"
                
                try:
                    from PyQt5.QtPrintSupport import QPrinter
                    from PyQt5.QtGui import (QTextDocument, QTextCursor, QTextTableFormat, 
                                             QTextCharFormat, QFont, QColor, QBrush, 
                                             QTextBlockFormat, QTextLength, QPixmap, QTextImageFormat)
                    from PyQt5.QtCore import QUrl
                    
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
                    cursor.insertText(f'Статистика CRM: {self.project_type} проекты\n\n', title_format)
                    
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
                    completed_count = 0
                    in_work_count = 0
                    overdue_count = 0
                    
                    for row in range(total_projects):
                        status_item = self.stats_table.item(row, 5)
                        if status_item:
                            status_text = status_item.text()
                            if 'Завершено' in status_text:
                                completed_count += 1
                            elif 'Просрочено' in status_text:
                                overdue_count += 1
                            else:
                                in_work_count += 1
                    
                    summary_format = QTextCharFormat()
                    summary_format.setFont(QFont('Arial', 8))
                    
                    cursor.insertText(f'• Всего записей: {total_projects}\n', summary_format)
                    cursor.insertText(f'• Выполнено: {completed_count}\n', summary_format)
                    cursor.insertText(f'• В работе: {in_work_count}\n', summary_format)
                    cursor.insertText(f'• Просрочено: {overdue_count}\n\n', summary_format)
                    
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
                            
                            if col == 5 and item:
                                status_text = item.text()
                                
                                if 'Просрочено' in status_text:
                                    status_format = QTextCharFormat()
                                    status_format.setFont(QFont('Arial', 8, QFont.Bold))
                                    status_format.setForeground(QColor('#E74C3C'))
                                    cell_cursor.insertText(status_text, status_format)
                                elif 'Завершено' in status_text:
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
                    
                    # Диалог успеха
                    success_dialog = PDFExportSuccessDialog(self, full_path, folder)
                    success_dialog.exec_()
                    
                except Exception as e:
                    print(f" Ошибка экспорта PDF: {e}")
                    import traceback
                    traceback.print_exc()
                    CustomMessageBox(self, 'Ошибка', f'Не удалось создать PDF:\n{str(e)}', 'error').exec_()

          
    def perform_pdf_export_with_params(self, folder, filename):
        """Выполнение экспорта PDF с параметрами"""
        try:
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
            cursor.insertText(f'Статистика CRM: {self.project_type} проекты\n\n', title_format)
            
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
            completed_count = 0
            in_work_count = 0
            overdue_count = 0
            
            for row in range(total_projects):
                status_item = self.stats_table.item(row, 5)
                if status_item:
                    status_text = status_item.text()
                    if 'Завершено' in status_text:
                        completed_count += 1
                    elif 'Просрочено' in status_text:
                        overdue_count += 1
                    else:
                        in_work_count += 1
            
            summary_format = QTextCharFormat()
            summary_format.setFont(QFont('Arial', 8))
            
            cursor.insertText(f'• Всего записей: {total_projects}\n', summary_format)
            cursor.insertText(f'• Выполнено: {completed_count}\n', summary_format)
            cursor.insertText(f'• В работе: {in_work_count}\n', summary_format)
            cursor.insertText(f'• Просрочено: {overdue_count}\n\n', summary_format)
            
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
                    
                    if col == 5 and item:
                        status_text = item.text()
                        
                        if 'Просрочено' in status_text:
                            status_format = QTextCharFormat()
                            status_format.setFont(QFont('Arial', 8, QFont.Bold))
                            status_format.setForeground(QColor('#E74C3C'))
                            cell_cursor.insertText(status_text, status_format)
                        elif 'Завершено' in status_text:
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
            
            # Диалог успеха
            success_dialog = QDialog(self)
            success_dialog.setWindowTitle('Успех')
            success_dialog.setMinimumWidth(500)
            
            success_layout = QVBoxLayout()
            success_layout.setSpacing(15)
            success_layout.setContentsMargins(20, 20, 20, 20)
            
            success_title = QLabel('✓ PDF успешно создан!')
            success_title.setStyleSheet('font-size: 14px; font-weight: bold; color: #27AE60;')
            success_title.setAlignment(Qt.AlignCenter)
            success_layout.addWidget(success_title)
            
            path_frame = QFrame()
            path_frame.setStyleSheet('''
                QFrame {
                    background-color: #E8F4F8;
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
                    background-color: #3498DB;
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
            
            success_dialog = PDFExportSuccessDialog(self, full_path, folder)
            success_dialog.exec_()
            
        except Exception as e:
            print(f" Ошибка экспорта PDF: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось создать PDF:\n{str(e)}', 'error').exec_()
        
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

class ExportPDFDialog(QDialog):
    """Диалог выбора имени файла для экспорта PDF"""
    
    def __init__(self, parent, default_filename):
        super().__init__(parent)
        self.default_filename = default_filename
        self.selected_folder = None
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Экспорт в PDF', simple_mode=True)
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
        
        header = QLabel('Экспорт статистики в PDF')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #E74C3C;')
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)
        
        # Подсчет записей из родительской таблицы
        parent_dialog = self.parent()
        if hasattr(parent_dialog, 'stats_table'):
            row_count = parent_dialog.stats_table.rowCount()
            info = QLabel(f'Будет экспортировано записей: <b>{row_count}</b>')
        else:
            info = QLabel('Будет экспортирована статистика')
        
        info.setStyleSheet('font-size: 11px; color: #555;')
        info.setAlignment(Qt.AlignCenter)
        layout.addWidget(info)
        
        filename_layout = QFormLayout()
        
        self.filename_input = QLineEdit()
        self.filename_input.setText(self.default_filename)
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
        
        hint = QLabel('💡 Файл будет сохранен в выбранную папку с расширением .pdf')
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
        folder_btn.clicked.connect(self.select_folder)
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
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(550)
    
    def select_folder(self):
        """Выбор папки"""
        from PyQt5.QtWidgets import QFileDialog
        
        folder = QFileDialog.getExistingDirectory(
            self,
            'Выберите папку для сохранения',
            '',
            QFileDialog.ShowDirsOnly
        )
        
        if folder:
            self.selected_folder = folder
            self.accept()
    
    def get_filename(self):
        """Получить имя файла"""
        filename = self.filename_input.text().strip()
        if not filename:
            filename = self.default_filename
        if not filename.endswith('.pdf'):
            filename += '.pdf'
        return filename
    
    def get_folder(self):
        """Получить выбранную папку"""
        return self.selected_folder
    
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
            
class PDFExportSuccessDialog(QDialog):
    """Диалог успешного экспорта PDF"""
    
    def __init__(self, parent, file_path, folder_path):
        super().__init__(parent)
        self.file_path = file_path
        self.folder_path = folder_path
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

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
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
        """)
        
        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)
        
        # ========== КАСТОМНЫЙ TITLE BAR ==========
        title_bar = CustomTitleBar(self, 'Успех', simple_mode=True)
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
        
        success_title = QLabel('✓ PDF успешно создан!')
        success_title.setStyleSheet('font-size: 14px; font-weight: bold; color: #27AE60;')
        success_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_title)
        
        path_frame = QFrame()
        path_frame.setStyleSheet('''
            QFrame {
                background-color: #E8F4F8;
                border: none;
                border-radius: 4px;
                padding: 10px;
            }
        ''')
        path_layout = QVBoxLayout()
        path_layout.setContentsMargins(0, 0, 0, 0)
        
        path_label = QLabel(self.file_path)
        path_label.setWordWrap(True)
        path_label.setStyleSheet('font-size: 10px; color: #333;')
        path_label.setAlignment(Qt.AlignCenter)
        path_layout.addWidget(path_label)
        
        path_frame.setLayout(path_layout)
        layout.addWidget(path_frame)
        
        open_folder_btn = QPushButton('Открыть папку с файлом')
        open_folder_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                padding: 10px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #2980B9; }
        """)
        open_folder_btn.clicked.connect(self.open_folder)
        layout.addWidget(open_folder_btn)
        
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
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)
        
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        self.setMinimumWidth(500)
    
    def open_folder(self):
        """Открытие папки"""
        try:
            import platform
            
            if platform.system() == 'Windows':
                os.startfile(self.folder_path)
            elif platform.system() == 'Darwin':
                os.system(f'open "{self.folder_path}"')
            else:
                os.system(f'xdg-open "{self.folder_path}"')
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

        
class ArchiveCard(QFrame):
    """Упрощенная карточка для архива"""

    def __init__(self, card_data, db, card_type='crm', employee=None):
        super().__init__()
        self.card_data = card_data
        self.db = db
        self.card_type = card_type  # 'crm' или 'supervision'
        self.employee = employee  # Информация о текущем сотруднике
        self.init_ui()
    
    def init_ui(self):
        self.setFrameShape(QFrame.Box)
        
        status = self.card_data.get('status', '')
        
        if 'СДАН' in status:
            card_bg_color = '#E8F8F5'
            border_color = '#27AE60'
        elif 'РАСТОРГНУТ' in status:
            card_bg_color = '#FADBD8'
            border_color = '#E74C3C'
        else:
            card_bg_color = '#FAFAFA'
            border_color = '#DDDDDD'
        
        self.setStyleSheet(f"""
            ArchiveCard {{
                background-color: {card_bg_color};
                border: 1px solid {border_color};
                border-radius: 6px;
                padding: 10px;
            }}
            ArchiveCard:hover {{
                background-color: {card_bg_color};
                border: 2px solid {border_color};
            }}
        """)

        # Устанавливаем фиксированный размер для всех карточек
        # Ширина: 295px - оптимально для 3 карточек в ряду при минимальной ширине окна 950px
        self.setFixedSize(328, 220)

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(15, 12, 15, 12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        contract_label = QLabel(f"<b>Договор:</b> {self.card_data.get('contract_number', 'N/A')}")
        contract_label.setStyleSheet('font-size: 11px; color: #666; background-color: transparent;')
        info_layout.addWidget(contract_label)
        
        address = self.card_data.get('address', 'Адрес не указан')
        address_label = QLabel(f"<b>{address}</b>")
        address_label.setWordWrap(True)
        address_label.setStyleSheet('font-size: 13px; color: #222; font-weight: bold; background-color: transparent;')
        info_layout.addWidget(address_label)
        
        details_parts = []
        if self.card_data.get('area'):
            details_parts.append(f"📐 {self.card_data['area']} м²")
        if self.card_data.get('city'):
            details_parts.append(f"📍 {self.card_data['city']}")

        if details_parts:
            details_label = QLabel(" | ".join(details_parts))
            details_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            info_layout.addWidget(details_label)

        # ИСПРАВЛЕНИЕ: Тип агента отдельно с цветом
        if self.card_data.get('agent_type'):
            agent_type = self.card_data['agent_type']
            agent_color = self.db.get_agent_color(agent_type)

            agent_label = QLabel(agent_type)
            if agent_color:
                agent_label.setStyleSheet(f'''
                    background-color: {agent_color};
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 3px;
                    border: 2px solid {agent_color};
                ''')
            else:
                agent_label.setStyleSheet('''
                    background-color: #95A5A6;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 3px;
                    border: 2px solid #95A5A6;
                ''')
            agent_label.setAlignment(Qt.AlignLeft)
            info_layout.addWidget(agent_label)
        
        if status:
            status_label = QLabel(f"Статус: {status}")
            if 'СДАН' in status:
                status_label.setStyleSheet('''
                    color: white;
                    background-color: #27AE60;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                ''')
            elif 'РАСТОРГНУТ' in status:
                status_label.setStyleSheet('''
                    color: white;
                    background-color: #E74C3C;
                    padding: 3px 8px;
                    border-radius: 3px;
                    font-size: 10px;
                    font-weight: bold;
                ''')
            info_layout.addWidget(status_label)

        layout.addLayout(info_layout)

        # Добавляем stretch, чтобы кнопка всегда была внизу
        layout.addStretch(1)

        # ========== КНОПКА ПОДРОБНЕЕ (SVG) ==========
        details_btn = IconLoader.create_icon_button('info', 'Подробнее', 'Просмотр деталей', icon_size=14)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 8px 100px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
            QPushButton:pressed {
                background-color: #21618C;
            }
        """)
        details_btn.clicked.connect(self.show_details)
        layout.addWidget(details_btn, 0, Qt.AlignCenter)
        
        self.setLayout(layout)
        
    def show_details(self):
        """Показать полную информацию о проекте"""
        dialog = ArchiveCardDetailsDialog(self, self.card_data, self.db, self.card_type, self.employee)
        dialog.exec_()
        
class ArchiveCardDetailsDialog(QDialog):
    """Диалог с полной информацией об архивной карточке"""

    def __init__(self, parent, card_data, db, card_type='crm', employee=None):
        super().__init__(parent)
        self.card_data = card_data
        self.db = db
        self.card_type = card_type  # 'crm' или 'supervision'
        self.employee = employee  # Информация о текущем сотруднике
        
        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

        self.init_ui()
        
    def init_ui(self):
        try:
            address = self.card_data.get('address', 'N/A')
            
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
                    border: 1px solid #CCCCCC;
                    border-top-left-radius: 10px;
                    border-top-right-radius: 10px;
                }
            """)
            
            border_layout = QVBoxLayout()
            border_layout.setContentsMargins(0, 0, 0, 0)
            border_layout.setSpacing(0)
            
            # ========== КАСТОМНЫЙ TITLE BAR ==========
            title_bar = CustomTitleBar(self, f'Детали проекта: {address}', simple_mode=True)
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
            
            header = QLabel(f"<h2>{address}</h2>")
            header.setWordWrap(True)
            layout.addWidget(header)
            
            tabs = QTabWidget()
            
            # === ВКЛАДКА 1: Основная информация ===
            info_widget = QWidget()
            info_main_layout = QVBoxLayout()
            info_main_layout.setContentsMargins(0, 0, 0, 0)
            
            info_scroll = QScrollArea()
            info_scroll.setWidgetResizable(True)
            info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            info_content = QWidget()
            info_layout = QFormLayout()
            info_layout.setSpacing(10)
            
            info_layout.addRow('<b>Договор:</b>', QLabel(str(self.card_data.get('contract_number', 'N/A'))))
            info_layout.addRow('<b>Адрес:</b>', QLabel(str(self.card_data.get('address', 'N/A'))))
            info_layout.addRow('<b>Площадь:</b>', QLabel(f"{self.card_data.get('area', 'N/A')} м²"))
            info_layout.addRow('<b>Город:</b>', QLabel(str(self.card_data.get('city', 'N/A'))))
            info_layout.addRow('<b>Тип агента:</b>', QLabel(str(self.card_data.get('agent_type', 'N/A'))))
            info_layout.addRow('<b>Статус:</b>', QLabel(str(self.card_data.get('status', 'N/A'))))
            
            if self.card_data.get('termination_reason'):
                reason_label = QLabel(str(self.card_data['termination_reason']))
                reason_label.setWordWrap(True)
                reason_label.setStyleSheet('color: #E74C3C; padding: 5px; background-color: #FADBD8; border-radius: 3px;')
                info_layout.addRow('<b>Причина расторжения:</b>', reason_label)
            
            separator = QLabel('<hr>')
            info_layout.addRow(separator)

            # Теги и общий дедлайн
            if self.card_data.get('tags'):
                tags_label = QLabel(f"<b>Теги:</b> {self.card_data['tags']}")
                tags_label.setStyleSheet('padding: 5px; background-color: #FFF3CD; border-radius: 3px; border: none;')
                tags_label.setWordWrap(True)
                info_layout.addRow(tags_label)

            if self.card_data.get('deadline'):
                deadline_label = QLabel(f"<b>Общий дедлайн:</b> {self.card_data['deadline']}")
                deadline_label.setStyleSheet('padding: 5px; background-color: #E8F4F8; border-radius: 3px; border: none;')
                info_layout.addRow(deadline_label)

            # ИСПРАВЛЕНИЕ: Компактная отметка о замере (одной строчкой)
            if self.card_type == 'crm':
                try:
                    contract_id = self.card_data.get('contract_id')
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    cursor.execute('''
                    SELECT survey_date, e.full_name as surveyor_name
                    FROM surveys s
                    LEFT JOIN employees e ON s.surveyor_id = e.id
                    WHERE s.contract_id = ?
                    ORDER BY s.id DESC
                    LIMIT 1
                    ''', (contract_id,))

                    survey = cursor.fetchone()
                    self.db.close()

                    if survey:
                        survey_date = QDate.fromString(survey['survey_date'], 'yyyy-MM-dd')
                        survey_label = QLabel(
                            f"✓ Замер выполнен: {survey_date.toString('dd.MM.yyyy')} | Замерщик: {survey['surveyor_name']}"
                        )
                        survey_label.setStyleSheet('''
                            color: #27AE60;
                            font-size: 10px;
                            font-weight: bold;
                            background-color: #E8F8F5;
                            padding: 5px;
                            border-radius: 3px;
                            margin-bottom: 4px;
                        ''')
                        survey_label.setWordWrap(True)
                        info_layout.addRow(survey_label)
                except Exception as e:
                    print(f" Ошибка загрузки информации о замере: {e}")

                # НОВОЕ: ВЫПОЛНЕННЫЕ СТАДИИ
                try:
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    cursor.execute('''
                    SELECT se.stage_name, e.full_name as executor_name, se.completed_date
                    FROM stage_executors se
                    LEFT JOIN employees e ON se.executor_id = e.id
                    WHERE se.crm_card_id = ? AND se.completed = 1
                    ORDER BY se.completed_date ASC
                    ''', (self.card_data['id'],))

                    completed_stages = cursor.fetchall()
                    self.db.close()

                    if completed_stages:
                        for stage in completed_stages:
                            date_str = format_date(stage.get('completed_date'))

                            stage_label = QLabel(
                                f"✓ {stage['stage_name']} | Исполнитель: {stage['executor_name']} | Дата: {date_str}"
                            )
                            stage_label.setStyleSheet('''
                                color: #27AE60;
                                font-size: 10px;
                                font-weight: bold;
                                background-color: #E8F8F5;
                                padding: 5px;
                                border-radius: 3px;
                                margin-bottom: 4px;
                            ''')
                            stage_label.setWordWrap(True)
                            info_layout.addRow(stage_label)

                except Exception as e:
                    print(f" Ошибка загрузки выполненных стадий: {e}")

            elif self.card_type == 'supervision':
                # НОВОЕ: ПРИНЯТЫЕ СТАДИИ НАДЗОРА
                try:
                    conn = self.db.connect()
                    cursor = conn.cursor()

                    # Получаем принятые стадии из истории проекта надзора
                    # Нужно найти supervision_card_id для этого contract_id
                    cursor.execute('''
                    SELECT id FROM supervision_cards WHERE contract_id = ?
                    ''', (self.card_data.get('contract_id'),))

                    supervision_card = cursor.fetchone()

                    if supervision_card:
                        cursor.execute('''
                        SELECT created_at, message
                        FROM supervision_project_history
                        WHERE supervision_card_id = ? AND entry_type = 'accepted'
                        ORDER BY created_at ASC
                        ''', (supervision_card['id'],))

                        accepted_history = cursor.fetchall()
                        self.db.close()

                        if accepted_history:
                            for history in accepted_history:
                                date_str = format_date(history['created_at'])
                                message = history['message']

                                stage_label = QLabel(f"✓ {message} | Дата: {date_str}")
                                stage_label.setStyleSheet('''
                                    color: #27AE60;
                                    font-size: 10px;
                                    font-weight: bold;
                                    background-color: #E8F8F5;
                                    padding: 5px;
                                    border-radius: 3px;
                                    margin-bottom: 4px;
                                ''')
                                stage_label.setWordWrap(True)
                                info_layout.addRow(stage_label)
                    else:
                        self.db.close()

                except Exception as e:
                    print(f" Ошибка загрузки принятых стадий надзора: {e}")

            history_label = QLabel('<b>История проекта:</b>')
            history_label.setStyleSheet('margin-top: 10px; font-size: 12px;')
            info_layout.addRow(history_label)

            stages = self.db.get_stage_history(self.card_data.get('id'))

            if stages:
                # Разделяем стадии по приоритетам
                completed_stages = []  # Приоритет 1: Завершенные стадии
                active_stages = []     # Приоритет 2: Назначенные/активные стадии

                for stage in stages:
                    if stage.get('completed'):
                        completed_stages.append(stage)
                    else:
                        active_stages.append(stage)

                # Выводим стадии с приоритетами
                all_prioritized_stages = completed_stages + active_stages

                for stage in all_prioritized_stages:
                    stage_frame = QFrame()

                    if stage.get('completed'):
                        bg_color = '#D5F4E6'
                    else:
                        bg_color = '#F8F9FA'

                    stage_frame.setStyleSheet(f'''
                        QFrame {{
                            background-color: {bg_color};
                            border: none;
                            border-radius: 4px;
                            padding: 2px;
                            margin: 2px 0px;
                        }}
                    ''')

                    stage_layout = QVBoxLayout()
                    stage_layout.setSpacing(3)

                    stage_name = QLabel(f"<b>{stage.get('stage_name', 'N/A')}</b>")
                    stage_layout.addWidget(stage_name)

                    executor = QLabel(f"Исполнитель: {stage.get('executor_name', 'Не назначен')}")
                    executor.setStyleSheet('font-size: 10px; color: #666;')
                    stage_layout.addWidget(executor)

                    # ИСПРАВЛЕНИЕ: Объединяем Назначено, Дедлайн и Сдано в одну строку
                    dates_parts = [f"Назначено: {format_date(stage.get('assigned_date'), 'N/A')}", f"Дедлайн: {format_date(stage.get('deadline'), 'N/A')}"]
                    if stage.get('submitted_date'):
                        dates_parts.append(f"Сдано: {format_date(stage.get('submitted_date'), 'N/A')}")

                    dates = QLabel(" | ".join(dates_parts))
                    dates.setStyleSheet('font-size: 10px; color: #666;')
                    stage_layout.addWidget(dates)

                    # ИСПРАВЛЕНИЕ: Дата принятия (завершения)
                    if stage.get('completed'):
                        completed_label = QLabel(f"✓ Принято: {format_date(stage.get('completed_date'), 'N/A')}")
                        completed_label.setStyleSheet('font-size: 10px; color: #27AE60; font-weight: bold;')
                        stage_layout.addWidget(completed_label)

                    stage_frame.setLayout(stage_layout)
                    info_layout.addRow(stage_frame)
            else:
                empty = QLabel('История отсутствует')
                empty.setStyleSheet('color: #999; font-style: italic;')
                info_layout.addRow(empty)
            
            info_content.setLayout(info_layout)
            info_scroll.setWidget(info_content)
            info_main_layout.addWidget(info_scroll)
            info_widget.setLayout(info_main_layout)
            tabs.addTab(info_widget, 'Основная информация')
            
            # === ВКЛАДКА 2: Команда ===
            team_widget = QWidget()
            team_main_layout = QVBoxLayout()
            team_main_layout.setContentsMargins(0, 0, 0, 0)
            
            team_scroll = QScrollArea()
            team_scroll.setWidgetResizable(True)
            team_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            team_content = QWidget()
            team_layout = QFormLayout()
            team_layout.setSpacing(10)
            
            if self.card_data.get('senior_manager_name'):
                team_layout.addRow('👔 Старший менеджер:', QLabel(str(self.card_data['senior_manager_name'])))
            if self.card_data.get('sdp_name'):
                team_layout.addRow('🎨 СДП:', QLabel(str(self.card_data['sdp_name'])))
            if self.card_data.get('gap_name'):
                team_layout.addRow('📋 ГАП:', QLabel(str(self.card_data['gap_name'])))
            if self.card_data.get('manager_name'):
                team_layout.addRow('💼 Менеджер:', QLabel(str(self.card_data['manager_name'])))
            if self.card_data.get('surveyor_name'):
                team_layout.addRow('📏 Замерщик:', QLabel(str(self.card_data['surveyor_name'])))
            if self.card_data.get('designer_name'):
                team_layout.addRow('🎨 Дизайнер:', QLabel(str(self.card_data['designer_name'])))
            if self.card_data.get('draftsman_name'):
                team_layout.addRow('✏️ Чертёжник:', QLabel(str(self.card_data['draftsman_name'])))
            if self.card_data.get('dan_name'):
                team_layout.addRow('🎨 ДАН:', QLabel(str(self.card_data['dan_name'])))
            
            if team_layout.rowCount() == 0:
                empty_label = QLabel('Команда не назначена')
                empty_label.setStyleSheet('color: #999; font-style: italic;')
                team_layout.addRow(empty_label)
            
            team_content.setLayout(team_layout)
            team_scroll.setWidget(team_content)
            team_main_layout.addWidget(team_scroll)
            team_widget.setLayout(team_main_layout)
            tabs.addTab(team_widget, 'Команда')

            # ========== ВКЛАДКА ОПЛАТЫ ==========
            # ИСПРАВЛЕНИЕ: Определяем, нужно ли показывать вкладку оплат
            contract_id = self.card_data.get('contract_id')
            contract_status = self.card_data.get('status', '')

            # Проверяем права доступа к вкладке оплаты (только Руководитель и Старший менеджер)
            position = self.employee.get('position') if self.employee else None
            can_view_payments = position in ['Руководитель студии', 'Старший менеджер проектов']

            # Определяем тип оплат и название вкладки
            show_payments_tab = False
            payments_tab_title = '💰 Оплаты'
            payments = []

            # Показываем вкладку оплат только если есть права доступа
            if can_view_payments and contract_id:
                if self.card_type == 'supervision':
                    # Для CRM надзора: показываем только оплаты надзора
                    payments = self.db.get_payments_for_supervision(contract_id)
                    payments_tab_title = '💰 Оплаты надзора'
                    show_payments_tab = True
                elif self.card_type == 'crm':
                    # Для основной CRM: показываем CRM-оплаты для СДАН, РАСТОРГНУТ, АВТОРСКИЙ НАДЗОР
                    if contract_status in ['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР']:
                        payments = self.db.get_payments_for_crm(contract_id)
                        payments_tab_title = '💰 Оплаты'
                        show_payments_tab = True

            # Создаем вкладку оплат только если нужно ее показывать
            if show_payments_tab:
                payments_widget = QWidget()
                payments_layout = QVBoxLayout()
                payments_layout.setContentsMargins(15, 15, 15, 15)
                payments_layout.setSpacing(10)

                # Заголовок
                payments_header = QLabel(payments_tab_title)
                payments_header.setStyleSheet('''
                    font-size: 13px;
                    font-weight: bold;
                    color: #2C3E50;
                    padding-bottom: 5px;
                ''')
                payments_layout.addWidget(payments_header)

                if payments:
                    # Создаем таблицу для отображения выплат
                    payments_table = QTableWidget()
                    # ВАЖНО: НЕ устанавливаем background-color для QTableWidget,
                    # чтобы цвета ячеек работали корректно
                    payments_table.setStyleSheet("""
                        QTableCornerButton::section {
                            background-color: #F5F5F5;
                            border: 1px solid #E0E0E0;
                        }
                    """)
                    payments_table.setColumnCount(8)
                    payments_table.setHorizontalHeaderLabels([
                        'Должность', 'ФИО', 'Стадия', 'Тип выплаты',
                        'Выплата (₽)', 'Аванс (₽)', 'Доплата (₽)', 'Отчетный месяц'
                    ])

                    payments_table.setRowCount(len(payments))
                    payments_table.setEditTriggers(QTableWidget.NoEditTriggers)
                    payments_table.setSelectionMode(QTableWidget.NoSelection)
                    payments_table.verticalHeader().setVisible(False)

                    # Заполняем таблицу данными
                    for row, payment in enumerate(payments):
                        # Определяем цвет строки в зависимости от статуса оплаты
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
                        payments_table.setCellWidget(row, 0, role_label)

                        # ФИО
                        name_label = QLabel(payment.get('employee_name', ''))
                        name_label.setStyleSheet(f"background-color: {row_color.name()};")
                        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 1, name_label)

                        # Стадия
                        stage_label = QLabel(payment.get('stage_name', '-'))
                        stage_label.setStyleSheet(f"background-color: {row_color.name()};")
                        stage_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 2, stage_label)

                        # Тип выплаты
                        payment_type = payment.get('payment_type', 'Полная оплата')
                        type_label = QLabel(payment_type)
                        type_label.setStyleSheet(f"background-color: {row_color.name()};")
                        type_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 3, type_label)

                        # ИСПРАВЛЕНИЕ: Используем правильные колонки из базы данных
                        final_amount = payment.get('final_amount', 0)

                        # Распределяем суммы по типу выплаты
                        if payment_type == 'Полная оплата':
                            # Выплата
                            amount_label = QLabel(f"{final_amount:,.0f}".replace(',', ' '))
                            amount_label.setStyleSheet(f"background-color: {row_color.name()};")
                            amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            payments_table.setCellWidget(row, 4, amount_label)

                            # Аванс и Доплата
                            advance_empty = QLabel('-')
                            advance_empty.setStyleSheet(f"background-color: {row_color.name()};")
                            advance_empty.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 5, advance_empty)

                            balance_empty = QLabel('-')
                            balance_empty.setStyleSheet(f"background-color: {row_color.name()};")
                            balance_empty.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 6, balance_empty)
                        elif payment_type == 'Аванс':
                            # Аванс
                            amount_empty = QLabel('-')
                            amount_empty.setStyleSheet(f"background-color: {row_color.name()};")
                            amount_empty.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 4, amount_empty)

                            advance_label = QLabel(f"{final_amount:,.0f}".replace(',', ' '))
                            advance_label.setStyleSheet(f"background-color: {row_color.name()};")
                            advance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            payments_table.setCellWidget(row, 5, advance_label)

                            balance_empty2 = QLabel('-')
                            balance_empty2.setStyleSheet(f"background-color: {row_color.name()};")
                            balance_empty2.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 6, balance_empty2)
                        elif payment_type == 'Доплата':
                            # Доплата
                            amount_empty2 = QLabel('-')
                            amount_empty2.setStyleSheet(f"background-color: {row_color.name()};")
                            amount_empty2.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 4, amount_empty2)

                            advance_empty3 = QLabel('-')
                            advance_empty3.setStyleSheet(f"background-color: {row_color.name()};")
                            advance_empty3.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 5, advance_empty3)

                            balance_label = QLabel(f"{final_amount:,.0f}".replace(',', ' '))
                            balance_label.setStyleSheet(f"background-color: {row_color.name()};")
                            balance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            payments_table.setCellWidget(row, 6, balance_label)

                        # Отчетный месяц
                        report_month = payment.get('report_month', '')
                        formatted_month = format_month_year(report_month) if report_month else '-'
                        month_label = QLabel(formatted_month)
                        month_label.setStyleSheet(f"background-color: {row_color.name()};")
                        month_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 7, month_label)

                    # Настройка размеров колонок
                    payments_table.horizontalHeader().setStretchLastSection(True)
                    payments_table.setColumnWidth(0, 120)
                    payments_table.setColumnWidth(1, 150)
                    payments_table.setColumnWidth(2, 200)
                    payments_table.setColumnWidth(3, 100)
                    payments_table.setColumnWidth(4, 100)
                    payments_table.setColumnWidth(5, 100)
                    payments_table.setColumnWidth(6, 100)

                    # Стили таблицы
                    # ВАЖНО: НЕ устанавливаем background-color для QTableWidget,
                    # чтобы цвета ячеек работали корректно
                    payments_table.setStyleSheet('''
                        QTableWidget {
                            border: 1px solid #E0E0E0;
                            gridline-color: #E0E0E0;
                        }
                        QTableWidget::item {
                            padding: 1px;
                            border-bottom: 1px solid #F0F0F0;
                        }
                        QHeaderView::section {
                            background-color: #F8F9FA;
                            color: #2C3E50;
                            padding: 8px;
                            border: none;
                            border-bottom: 2px solid #E0E0E0;
                            font-weight: bold;
                        }
                    ''')

                    # ИСПРАВЛЕНИЕ: Таблица растягивается на всю доступную высоту
                    payments_layout.addWidget(payments_table, 1)

                    # ИСПРАВЛЕНИЕ: Подсчет итоговых сумм по типам выплат
                    total_amount = sum(p.get('final_amount', 0) for p in payments if p.get('payment_type') == 'Полная оплата')
                    total_advance = sum(p.get('final_amount', 0) for p in payments if p.get('payment_type') == 'Аванс')
                    total_balance = sum(p.get('final_amount', 0) for p in payments if p.get('payment_type') == 'Доплата')

                    # Итоговая строка с разбивкой по типам
                    total_frame = QFrame()
                    total_frame.setStyleSheet('''
                        QFrame {
                            background-color: #F8F9FA;
                            border: 1px solid #E0E0E0;
                            padding: 5px;
                        }
                    ''')
                    total_layout = QHBoxLayout()
                    total_layout.setContentsMargins(10, 5, 10, 5)

                    # Скрываем "Итого:" чтобы было больше места для сумм
                    total_layout.addStretch()

                    if total_amount > 0:
                        amount_label = QLabel(f"Выплата: {total_amount:,.0f} ₽".replace(',', ' '))
                        amount_label.setStyleSheet('font-weight: bold; color: #2C3E50; font-size: 11px;')
                        total_layout.addWidget(amount_label)

                    if total_advance > 0:
                        advance_label = QLabel(f"Аванс: {total_advance:,.0f} ₽".replace(',', ' '))
                        advance_label.setStyleSheet('font-weight: bold; color: #3498DB; font-size: 11px;')
                        total_layout.addWidget(advance_label)

                    if total_balance > 0:
                        balance_label = QLabel(f"Доплата: {total_balance:,.0f} ₽".replace(',', ' '))
                        balance_label.setStyleSheet('font-weight: bold; color: #27AE60; font-size: 11px;')
                        total_layout.addWidget(balance_label)

                    total_frame.setLayout(total_layout)
                    payments_layout.addWidget(total_frame)

                    # НОВОЕ: Общая итоговая сумма всех выплат
                    grand_total = total_amount + total_advance + total_balance
                    if grand_total > 0:
                        grand_total_frame = QFrame()
                        grand_total_frame.setStyleSheet('''
                            QFrame {
                                background-color: #F8F9FA;
                                border: none;
                                padding: 3px;
                                margin-top: 2px;
                            }
                        ''')
                        grand_total_layout = QHBoxLayout()
                        grand_total_layout.setContentsMargins(5, 2, 5, 2)

                        grand_total_layout.addStretch()

                        grand_label = QLabel('ИТОГО:')
                        grand_label.setStyleSheet('font-weight: bold; color: #333333; font-size: 12px;')
                        grand_total_layout.addWidget(grand_label)

                        grand_amount_label = QLabel(f"{grand_total:,.0f} ₽".replace(',', ' '))
                        grand_amount_label.setStyleSheet('font-weight: bold; color: #333333; font-size: 14px;')
                        grand_total_layout.addWidget(grand_amount_label)

                        grand_total_frame.setLayout(grand_total_layout)
                        payments_layout.addWidget(grand_total_frame)

                else:
                    empty_label = QLabel('Нет данных об оплатах')
                    empty_label.setStyleSheet('color: #999; font-style: italic; padding: 10px;')
                    payments_layout.addWidget(empty_label)

                # ИСПРАВЛЕНИЕ: Убрали stretch чтобы таблица занимала всю высоту
                payments_widget.setLayout(payments_layout)
                tabs.addTab(payments_widget, payments_tab_title)

            # ========== ВКЛАДКА ДАННЫЕ ПО ПРОЕКТУ ==========
            # Показываем вкладку для всех, но с разными правами доступа
            project_data_widget = QWidget()
            project_data_layout = QVBoxLayout()
            project_data_layout.setContentsMargins(15, 15, 15, 15)
            project_data_layout.setSpacing(10)

            # Заголовок
            project_data_header = QLabel('📁 Данные по проекту')
            project_data_header.setStyleSheet('''
                font-size: 13px;
                font-weight: bold;
                color: #2C3E50;
                padding-bottom: 5px;
            ''')
            project_data_layout.addWidget(project_data_header)

            # Определяем права доступа
            can_edit_project_data = position in ['Руководитель студии', 'Старший менеджер проектов']

            # Информационное сообщение о правах
            if not can_edit_project_data:
                info_label = QLabel('ℹ️ Данные отображаются в режиме просмотра')
                info_label.setStyleSheet('''
                    color: #7F8C8D;
                    font-size: 11px;
                    font-style: italic;
                    padding: 5px;
                    background-color: #ECF0F1;
                    border-radius: 3px;
                ''')
                project_data_layout.addWidget(info_label)

            # Создаем ScrollArea для контента
            project_data_scroll = QScrollArea()
            project_data_scroll.setWidgetResizable(True)
            project_data_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            project_data_scroll.setStyleSheet("QScrollArea { border: none; background: white; }")

            project_data_content = QWidget()
            project_data_content_layout = QVBoxLayout()
            project_data_content_layout.setSpacing(15)

            # Контент вкладки "Данные по проекту" для архива (режим только для чтения)
            try:
                # Получаем данные из contracts
                contract_id = self.card_data.get('contract_id')
                project_type = self.card_data.get('project_type', 'Индивидуальный')

                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT c.tech_task_link, c.tech_task_file_name,
                           c.measurement_image_link, c.measurement_file_name,
                           c.references_yandex_path, c.photo_documentation_yandex_path,
                           cc.tech_task_date
                    FROM contracts c
                    LEFT JOIN crm_cards cc ON c.id = cc.contract_id
                    WHERE c.id = ?
                ''', (contract_id,))
                contract_data = cursor.fetchone()

                if contract_data:
                    # Создаем group boxes для каждой секции

                    # ========== СЕКЦИЯ: ТЗ И ЗАМЕР ==========
                    tz_survey_row = QHBoxLayout()
                    tz_survey_row.setSpacing(10)

                    # Левый блок: Техническое задание
                    tz_group = QGroupBox("Техническое задание")
                    tz_group.setStyleSheet("""
                        QGroupBox {
                            font-weight: bold;
                            font-size: 11px;
                            color: #2C3E50;
                            border: 1px solid #E0E0E0;
                            border-radius: 5px;
                            margin-top: 8px;
                            padding-top: 15px;
                        }
                        QGroupBox::title {
                            left: 10px;
                            padding: 0 5px;
                        }
                    """)
                    tz_layout = QVBoxLayout()
                    tz_layout.setSpacing(8)

                    # Дата ТЗ
                    tz_date_label = QLabel('Не указана')
                    if contract_data['tech_task_date']:
                        date = QDate.fromString(contract_data['tech_task_date'], 'yyyy-MM-dd')
                        tz_date_label.setText(date.toString('dd.MM.yyyy'))
                    tz_date_label.setStyleSheet('color: #2C3E50; font-size: 10px; font-weight: normal;')
                    tz_layout.addWidget(QLabel('Дата ТЗ:'))
                    tz_layout.addWidget(tz_date_label)

                    # Файл ТЗ
                    if contract_data['tech_task_link']:
                        file_name = contract_data['tech_task_file_name'] or 'ТехЗадание.pdf'
                        tz_file_label = QLabel(f'<a href="{contract_data["tech_task_link"]}">{file_name}</a>')
                        tz_file_label.setOpenExternalLinks(True)
                        tz_file_label.setStyleSheet('color: #3498DB; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 3px;')
                        tz_layout.addWidget(QLabel('Файл ТЗ:'))
                        tz_layout.addWidget(tz_file_label)
                    else:
                        tz_layout.addWidget(QLabel('Файл ТЗ: Не загружен'))

                    tz_group.setLayout(tz_layout)
                    tz_survey_row.addWidget(tz_group, 1)

                    # Правый блок: Замер
                    survey_group = QGroupBox("Замер")
                    survey_group.setStyleSheet("""
                        QGroupBox {
                            font-weight: bold;
                            font-size: 11px;
                            color: #2C3E50;
                            border: 1px solid #E0E0E0;
                            border-radius: 5px;
                            margin-top: 8px;
                            padding-top: 15px;
                        }
                        QGroupBox::title {
                            left: 10px;
                            padding: 0 5px;
                        }
                    """)
                    survey_layout = QVBoxLayout()
                    survey_layout.setSpacing(8)

                    if contract_data['measurement_image_link']:
                        file_name = contract_data['measurement_file_name'] or 'Замер'
                        survey_file_label = QLabel(f'<a href="{contract_data["measurement_image_link"]}">{file_name}</a>')
                        survey_file_label.setOpenExternalLinks(True)
                        survey_file_label.setStyleSheet('color: #3498DB; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 3px;')
                        survey_layout.addWidget(QLabel('Файл замера:'))
                        survey_layout.addWidget(survey_file_label)
                    else:
                        survey_layout.addWidget(QLabel('Файл замера: Не загружен'))

                    survey_group.setLayout(survey_layout)
                    tz_survey_row.addWidget(survey_group, 1)

                    project_data_content_layout.addLayout(tz_survey_row)

                    # ========== СЕКЦИЯ: РЕФЕРЕНСЫ/ШАБЛОНЫ И ФОТОФИКСАЦИЯ ==========
                    ref_photo_row = QHBoxLayout()
                    ref_photo_row.setSpacing(10)

                    # Левый блок: Референсы/Шаблоны
                    ref_group = QGroupBox("Референсы" if project_type == 'Индивидуальный' else "Шаблоны проекта")
                    ref_group.setStyleSheet("""
                        QGroupBox {
                            font-weight: bold;
                            font-size: 11px;
                            color: #2C3E50;
                            border: 1px solid #E0E0E0;
                            border-radius: 5px;
                            margin-top: 8px;
                            padding-top: 15px;
                        }
                        QGroupBox::title {
                            left: 10px;
                            padding: 0 5px;
                        }
                    """)
                    ref_layout = QVBoxLayout()
                    ref_layout.setSpacing(8)

                    if project_type == 'Шаблонный':
                        # Показываем список шаблонов
                        templates = self.db.get_project_templates(contract_id)
                        if templates:
                            for template in templates:
                                template_label = QLabel(f'<a href="{template["template_url"]}">{template["template_url"]}</a>')
                                template_label.setOpenExternalLinks(True)
                                template_label.setWordWrap(True)
                                template_label.setStyleSheet('color: #3498DB; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 3px; margin-bottom: 4px;')
                                ref_layout.addWidget(template_label)
                        else:
                            ref_layout.addWidget(QLabel('Шаблоны не загружены'))
                    else:
                        # Показываем ссылку на папку референсов
                        if contract_data['references_yandex_path']:
                            ref_label = QLabel(f'<a href="{contract_data["references_yandex_path"]}">Открыть папку с референсами</a>')
                            ref_label.setOpenExternalLinks(True)
                            ref_label.setStyleSheet('color: #3498DB; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 3px;')
                            ref_layout.addWidget(ref_label)
                        else:
                            ref_layout.addWidget(QLabel('Референсы не загружены'))

                    ref_group.setLayout(ref_layout)
                    ref_photo_row.addWidget(ref_group, 1)

                    # Правый блок: Фотофиксация
                    photo_group = QGroupBox("Фотофиксация")
                    photo_group.setStyleSheet("""
                        QGroupBox {
                            font-weight: bold;
                            font-size: 11px;
                            color: #2C3E50;
                            border: 1px solid #E0E0E0;
                            border-radius: 5px;
                            margin-top: 8px;
                            padding-top: 15px;
                        }
                        QGroupBox::title {
                            left: 10px;
                            padding: 0 5px;
                        }
                    """)
                    photo_layout = QVBoxLayout()
                    photo_layout.setSpacing(8)

                    if contract_data['photo_documentation_yandex_path']:
                        photo_label = QLabel(f'<a href="{contract_data["photo_documentation_yandex_path"]}">Открыть папку с фотофиксацией</a>')
                        photo_label.setOpenExternalLinks(True)
                        photo_label.setStyleSheet('color: #3498DB; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 3px;')
                        photo_layout.addWidget(photo_label)
                    else:
                        photo_layout.addWidget(QLabel('Фотофиксация не загружена'))

                    photo_group.setLayout(photo_layout)
                    ref_photo_row.addWidget(photo_group, 1)

                    project_data_content_layout.addLayout(ref_photo_row)

                    # ========== СЕКЦИИ СТАДИЙ ==========
                    # Загружаем файлы для каждой стадии из таблицы project_files
                    cursor = conn.cursor()

                    # Определяем какие стадии показывать в зависимости от типа проекта
                    if project_type == 'Шаблонный':
                        stages = [
                            ('stage1', '1 стадия - Планировочное решение'),
                            ('stage3', '2 стадия - Чертежный проект'),
                            ('stage2_3d', '3 стадия - 3D Визуализация (дополнительная)')
                        ]
                    else:
                        stages = [
                            ('stage1', '1 стадия - Планировочное решение'),
                            ('stage2', '2 стадия - Концепция-коллажи и 3D'),
                            ('stage3', '3 стадия - Чертежный проект')
                        ]

                    for stage_key, stage_title in stages:
                        stage_group = QGroupBox(stage_title)
                        stage_group.setStyleSheet("""
                            QGroupBox {
                                font-weight: bold;
                                font-size: 11px;
                                color: #2C3E50;
                                border: 1px solid #E0E0E0;
                                border-radius: 5px;
                                margin-top: 8px;
                                padding-top: 15px;
                            }
                            QGroupBox::title {
                                left: 10px;
                                padding: 0 5px;
                            }
                        """)
                        stage_layout = QVBoxLayout()
                        stage_layout.setSpacing(4)

                        # Загружаем файлы для этой стадии
                        cursor.execute('''
                            SELECT file_name, public_link
                            FROM project_files
                            WHERE contract_id = ? AND stage = ?
                            ORDER BY id ASC
                        ''', (contract_id, stage_key))

                        files = cursor.fetchall()

                        if files:
                            for file in files:
                                file_label = QLabel(f'<a href="{file["public_link"]}">{file["file_name"]}</a>')
                                file_label.setOpenExternalLinks(True)
                                file_label.setStyleSheet('color: #3498DB; font-size: 10px; padding: 4px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 3px; margin-bottom: 2px;')
                                stage_layout.addWidget(file_label)
                        else:
                            no_files_label = QLabel('Файлы не загружены')
                            no_files_label.setStyleSheet('color: #999; font-size: 10px; font-style: italic;')
                            stage_layout.addWidget(no_files_label)

                        stage_group.setLayout(stage_layout)
                        project_data_content_layout.addWidget(stage_group)

                    conn.close()
                else:
                    conn.close()
                    error_label = QLabel('Не удалось загрузить данные проекта')
                    error_label.setStyleSheet('color: #E74C3C; font-size: 11px;')
                    project_data_content_layout.addWidget(error_label)

            except Exception as e:
                print(f"[ERROR] Ошибка загрузки данных проекта в архиве: {e}")
                error_label = QLabel(f'Ошибка загрузки данных: {str(e)}')
                error_label.setStyleSheet('color: #E74C3C; font-size: 11px;')
                project_data_content_layout.addWidget(error_label)

            project_data_content_layout.addStretch()
            project_data_content.setLayout(project_data_content_layout)
            project_data_scroll.setWidget(project_data_content)
            project_data_layout.addWidget(project_data_scroll)

            project_data_widget.setLayout(project_data_layout)
            tabs.addTab(project_data_widget, '📁 Данные по проекту')

            layout.addWidget(tabs, 1)
            
            buttons_layout = QHBoxLayout()
            
            restore_btn = IconLoader.create_icon_button('refresh3', 'Вернуть в активные проекты', icon_size=16)
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #3498DB;
                    color: white;
                    padding: 8px 20px;
                    border-radius: 4px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background-color: #2980B9;
                }
            """)
            restore_btn.clicked.connect(self.restore_to_active)
            buttons_layout.addWidget(restore_btn)
            
            buttons_layout.addStretch()
            
            close_btn = QPushButton('Закрыть')
            close_btn.setStyleSheet('padding: 8px 20px;')
            close_btn.clicked.connect(self.accept)
            buttons_layout.addWidget(close_btn)
            
            layout.addLayout(buttons_layout)
            
        except Exception as e:
            print(f"Ошибка создания диалога деталей: {e}")
            import traceback
            traceback.print_exc()
            
        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        
        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)
        
        # ========== ИСПРАВЛЕНИЕ: УВЕЛИЧЕННЫЕ РАЗМЕРЫ (50% ШИРИНА, 90% ВЫСОТА) ==========
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
            
    def restore_to_active(self):
        """Возврат проекта в активные"""
        # ========== ЗАМЕНИЛИ QMessageBox.question ==========
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Вернуть проект в активные (столбец "Выполненный проект")?'
        ).exec_()
        
        if reply == QDialog.Accepted:
            try:
                contract_id = self.card_data.get('contract_id')
                
                self.db.update_contract(contract_id, {
                    'status': 'В работе',
                    'termination_reason': None
                })
                
                self.db.update_crm_card_column(self.card_data['id'], 'Выполненный проект')
                
                # ========== ЗАМЕНИЛИ QMessageBox.information ==========
                CustomMessageBox(self, 'Успех', 'Проект возвращен в активные', 'success').exec_()
                self.accept()
                
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()
                
            except Exception as e:
                print(f"Ошибка возврата проекта: {e}")
                CustomMessageBox(self, 'Ошибка', f'Не удалось вернуть проект: {e}', 'error').exec_()
    
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
        
class ReassignExecutorDialog(QDialog):
    """Диалог переназначения исполнителя БЕЗ перемещения карточки"""
    
    def __init__(self, parent, card_id, position, stage_keyword, executor_type, current_executor_name, stage_name):
        super().__init__(parent)
        self.card_id = card_id
        self.position = position
        self.stage_keyword = stage_keyword
        self.executor_type = executor_type
        self.current_executor_name = current_executor_name
        self.stage_name = stage_name
        self.db = DatabaseManager()
        
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        
        self.init_ui()
    
    def init_ui(self):
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
        
        # Title Bar
        title_bar = CustomTitleBar(self, 'Переназначить исполнителя', simple_mode=True)
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
        
        info_label = QLabel(f'Переназначение исполнителя для стадии:')
        info_label.setStyleSheet('font-size: 13px; font-weight: bold;')
        info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(info_label)
        
        stage_label = QLabel(f"<b>{self.stage_name}</b>")
        stage_label.setWordWrap(True)
        stage_label.setStyleSheet('font-size: 12px; color: #555;')
        stage_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(stage_label)
        
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
        
        current_label = QLabel(f"Текущий исполнитель: <b>{self.current_executor_name}</b>")
        current_label.setStyleSheet('font-size: 11px; color: #333;')
        current_label.setAlignment(Qt.AlignCenter)
        current_layout.addWidget(current_label)
        
        current_frame.setLayout(current_layout)
        layout.addWidget(current_frame)

        # ========== НОВОЕ: ИСТОРИЯ ИСПОЛНИТЕЛЕЙ ==========
        # Получаем историю всех исполнителей на предыдущих стадиях
        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            cursor.execute('''
            SELECT DISTINCT se.stage_name, e.full_name, se.assigned_date
            FROM stage_executors se
            JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ?
            ORDER BY se.assigned_date DESC
            ''', (self.card_id,))

            history_records = cursor.fetchall()
            self.db.close()

            if history_records:
                history_frame = QFrame()
                history_frame.setStyleSheet("""
                    QFrame {
                        background-color: #F0F0F0;
                        border: none;
                        border-radius: 4px;
                        padding: 8px;
                    }
                """)
                history_layout = QVBoxLayout()
                history_layout.setContentsMargins(5, 5, 5, 5)
                history_layout.setSpacing(3)

                history_title = QLabel("История исполнителей на других стадиях:")
                history_title.setStyleSheet('font-size: 9px; color: #666; font-style: italic;')
                history_layout.addWidget(history_title)

                # Показываем максимум 5 последних записей
                for record in history_records[:5]:
                    from datetime import datetime
                    try:
                        assigned_date = datetime.strptime(record['assigned_date'], '%Y-%m-%d %H:%M:%S')
                        date_str = assigned_date.strftime('%d.%m.%Y')
                    except Exception:
                        date_str = record['assigned_date'][:10] if record['assigned_date'] else '—'

                    history_item = QLabel(f"• {record['stage_name']}: {record['full_name']} ({date_str})")
                    history_item.setStyleSheet('font-size: 9px; color: #555;')
                    history_layout.addWidget(history_item)

                history_frame.setLayout(history_layout)
                layout.addWidget(history_frame)

        except Exception as e:
            print(f" Не удалось загрузить историю исполнителей: {e}")
        # ==================================================

        form_layout = QFormLayout()
        
        self.executor_combo = CustomComboBox()
        executors = self.db.get_employees_by_position(self.position)
        
        if not executors:
            CustomMessageBox(self, 'Внимание', f'Нет доступных сотрудников с должностью "{self.position}"', 'warning').exec_()
            self.reject()
            return
        
        for executor in executors:
            self.executor_combo.addItem(executor['full_name'], executor['id'])
        
        form_layout.addRow('Новый исполнитель:', self.executor_combo)
        
        # Поле дедлайна
        self.deadline_edit = CustomDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat('dd.MM.yyyy')
        self.deadline_edit.setStyleSheet(CALENDAR_STYLE)
        
        # Загружаем текущий дедлайн из БД
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT deadline FROM stage_executors
            WHERE crm_card_id = ? AND stage_name LIKE ?
            ORDER BY id DESC LIMIT 1
            ''', (self.card_id, f'%{self.stage_keyword}%'))
            
            record = cursor.fetchone()
            if record and record['deadline']:
                self.deadline_edit.setDate(QDate.fromString(record['deadline'], 'yyyy-MM-dd'))
            else:
                self.deadline_edit.setDate(QDate.currentDate().addDays(7))
            
            self.db.close()
        except Exception as e:
            print(f" Не удалось загрузить дедлайн: {e}")
            self.deadline_edit.setDate(QDate.currentDate().addDays(7))
        
        form_layout.addRow('Дедлайн:', self.deadline_edit)
        
        layout.addLayout(form_layout)
        
        hint = QLabel(' Исполнитель будет изменен БЕЗ перемещения карточки')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #FF9800; font-size: 10px; font-style: italic; font-weight: bold;')
        layout.addWidget(hint)
        
        save_btn = QPushButton('✓ Переназначить')
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
        
        self.setMinimumWidth(500)
    
    def save_reassignment(self):
        """Сохранение нового назначения"""
        new_executor_id = self.executor_combo.currentData()
        new_deadline = self.deadline_edit.date().toString('yyyy-MM-dd')

        try:
            conn = self.db.connect()
            cursor = conn.cursor()

            # ИСПРАВЛЕНИЕ: Находим старого исполнителя и ID записи stage_executors
            cursor.execute('''
            SELECT id, executor_id FROM stage_executors
            WHERE crm_card_id = ? AND stage_name LIKE ?
            ORDER BY id DESC LIMIT 1
            ''', (self.card_id, f'%{self.stage_keyword}%'))

            record = cursor.fetchone()
            if record:
                record_id = record['id']
                old_executor_id = record['executor_id']

                # Обновляем исполнителя и дедлайн (сбрасываем статус завершения)
                cursor.execute('''
                UPDATE stage_executors
                SET executor_id = ?, deadline = ?, completed = 0, completed_date = NULL
                WHERE id = ?
                ''', (new_executor_id, new_deadline, record_id))

                print(f"✓ Исполнитель переназначен: executor_id={new_executor_id}, deadline={new_deadline}")

                # ИСПРАВЛЕНИЕ: Переносим оплату со старого исполнителя на нового
                # Находим карточку для получения contract_id
                cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (self.card_id,))
                card_record = cursor.fetchone()

                if card_record and old_executor_id and new_executor_id != old_executor_id:
                    contract_id = card_record['contract_id']

                    # Определяем роль по должности
                    role_map = {
                        'Дизайнер': 'Дизайнер',
                        'Чертёжник': 'Чертёжник'
                    }
                    role = role_map.get(self.position, self.position)

                    # Ищем оплату старого исполнителя по этой стадии
                    cursor.execute('''
                    SELECT id FROM payments
                    WHERE contract_id = ?
                      AND employee_id = ?
                      AND role = ?
                      AND stage_name LIKE ?
                    ''', (contract_id, old_executor_id, role, f'%{self.stage_keyword}%'))

                    payment_record = cursor.fetchone()

                    if payment_record:
                        # ИСПРАВЛЕНИЕ: Помечаем старую запись как переназначенную
                        cursor.execute('''
                        UPDATE payments
                        SET reassigned = 1, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        ''', (payment_record['id'],))

                        # Получаем данные старой записи
                        cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_record['id'],))
                        old_payment = cursor.fetchone()

                        # Создаем новую запись для нового исполнителя
                        cursor.execute('''
                        INSERT INTO payments (
                            contract_id, crm_card_id, supervision_card_id,
                            employee_id, role, stage_name,
                            calculated_amount, manual_amount, final_amount,
                            is_manual, payment_type, report_month,
                            reassigned, old_employee_id
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                        ''', (
                            old_payment['contract_id'],
                            old_payment['crm_card_id'],
                            old_payment['supervision_card_id'],
                            new_executor_id,  # Новый исполнитель
                            old_payment['role'],
                            old_payment['stage_name'],
                            old_payment['calculated_amount'],
                            old_payment['manual_amount'],
                            old_payment['final_amount'],
                            old_payment['is_manual'],
                            old_payment['payment_type'],
                            old_payment['report_month'],
                            old_executor_id  # Сохраняем ID старого исполнителя
                        ))

                        print(f"✓ Создана новая запись оплаты для исполнителя {new_executor_id}, старая запись помечена как переназначенная")
                    else:
                        print(f" Оплата для старого исполнителя не найдена (возможно, еще не создана)")

                conn.commit()
            else:
                print(f" Не найдена запись stage_executors для переназначения")

            self.db.close()

            CustomMessageBox(self, 'Успех', 'Исполнитель успешно переназначен', 'success').exec_()
            self.accept()

        except Exception as e:
            print(f" Ошибка переназначения: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось переназначить исполнителя:\n{str(e)}', 'error').exec_()
    
    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 3 + screen.top()
        self.move(x, y)


class SurveyDateDialog(QDialog):
    """Диалог установки даты замера"""
    def __init__(self, parent, card_id):
        super().__init__(parent)
        self.card_id = card_id
        self.db = DatabaseManager()

        # Убираем стандартную рамку окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

    def init_ui(self):
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
        border_layout.setContentsMargins(10, 10, 10, 10)
        border_layout.setSpacing(0)

        # Title bar
        title_bar = CustomTitleBar(self, "Дата замера", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Дата замера
        date_label = QLabel('Дата замера:')
        layout.addWidget(date_label)

        self.survey_date = CustomDateEdit()
        self.survey_date.setCalendarPopup(True)

        # Загружаем существующую дату или устанавливаем текущую
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT survey_date FROM crm_cards WHERE id = ?", (self.card_id,))
        result = cursor.fetchone()
        self.db.close()

        if result and result[0]:
            from datetime import datetime
            try:
                existing_date = datetime.strptime(result[0], '%Y-%m-%d')
                self.survey_date.setDate(QDate(existing_date.year, existing_date.month, existing_date.day))
            except:
                self.survey_date.setDate(QDate.currentDate())
        else:
            self.survey_date.setDate(QDate.currentDate())

        self.survey_date.setDisplayFormat('dd.MM.yyyy')
        from utils.calendar_styles import CALENDAR_STYLE, add_today_button_to_dateedit
        self.survey_date.setStyleSheet(CALENDAR_STYLE)
        add_today_button_to_dateedit(self.survey_date)
        layout.addWidget(self.survey_date)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A085;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138D75;
            }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 30px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # Размер окна
        self.setFixedSize(400, 220)

    def save(self):
        """Сохранение даты замера"""
        survey_date = self.survey_date.date().toString('yyyy-MM-dd')

        # Обновляем карточку
        updates = {
            'survey_date': survey_date
        }

        try:
            self.db.update_crm_card(self.card_id, updates)
            self.accept()
        except Exception as e:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить дату замера:\n{str(e)}', 'error').exec_()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 3 + screen.top()
        self.move(x, y)


class TechTaskDialog(QDialog):
    """Диалог добавления технического задания"""
    # Сигналы для обработки загрузки файлов из фонового потока
    tech_task_upload_completed = pyqtSignal(str, str, str, int)  # public_link, yandex_path, file_name, contract_id
    tech_task_upload_error = pyqtSignal(str)  # error_msg

    def __init__(self, parent, card_id):
        super().__init__(parent)
        self.card_id = card_id
        self.db = DatabaseManager()
        self.uploaded_file_link = None

        # Подключаем сигналы загрузки
        self.tech_task_upload_completed.connect(self._on_file_uploaded)
        self.tech_task_upload_error.connect(self._on_file_upload_error)

        # Убираем стандартную рамку окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()
        self.load_existing_file()

    def truncate_filename(self, filename, max_length=50):
        """Обрезает длинное имя файла с многоточием в середине"""
        if len(filename) <= max_length:
            return filename

        # Разделяем имя и расширение
        import os
        name, ext = os.path.splitext(filename)

        # Рассчитываем сколько символов оставить в начале и конце
        ext_len = len(ext)
        available = max_length - ext_len - 3  # 3 для "..."

        if available <= 0:
            return filename[:max_length - 3] + "..."

        # Половину символов в начало, половину в конец (перед расширением)
        start_len = available // 2
        end_len = available - start_len

        return name[:start_len] + "..." + name[-end_len:] + ext

    def init_ui(self):
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
        border_layout.setContentsMargins(10, 10, 10, 10)
        border_layout.setSpacing(0)

        # Title bar
        title_bar = CustomTitleBar(self, "Добавить техническое задание", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Виджет загрузки файла ТЗ
        file_label = QLabel('Файл ТЗ (PDF):')
        layout.addWidget(file_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)

        self.file_label_display = QLabel('Не загружен')
        self.file_label_display.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 12px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                max-width: 300px;
                text-overflow: ellipsis;
                overflow: hidden;
                white-space: nowrap;
            }
            QLabel a {
                color: #3498DB;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.file_label_display.setWordWrap(False)
        self.file_label_display.setOpenExternalLinks(True)
        self.file_label_display.setTextInteractionFlags(Qt.TextBrowserInteraction)
        file_row.addWidget(self.file_label_display, 1)

        upload_btn = QPushButton('Загрузить PDF')
        upload_btn.setFixedWidth(120)
        upload_btn.clicked.connect(self.upload_file)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #3498DB;
                color: white;
                border: none;
                padding: 12px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980B9;
            }
        ''')
        file_row.addWidget(upload_btn)

        layout.addLayout(file_row)

        # Дата добавления ТЗ
        date_label = QLabel('Дата добавления ТЗ:')
        layout.addWidget(date_label)

        self.tech_task_date = CustomDateEdit()
        self.tech_task_date.setCalendarPopup(True)
        self.tech_task_date.setDate(QDate.currentDate())
        self.tech_task_date.setDisplayFormat('dd.MM.yyyy')
        from utils.calendar_styles import CALENDAR_STYLE, add_today_button_to_dateedit
        self.tech_task_date.setStyleSheet(CALENDAR_STYLE)
        add_today_button_to_dateedit(self.tech_task_date)
        layout.addWidget(self.tech_task_date)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 30px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # Размер окна
        self.setFixedSize(500, 280)

    def load_existing_file(self):
        """Загрузка существующего файла ТЗ из договора"""
        # Получаем contract_id из карточки
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (self.card_id,))
        result = cursor.fetchone()

        if result and result['contract_id']:
            contract_id = result['contract_id']
            # Получаем tech_task_link и tech_task_file_name из договора
            cursor.execute('SELECT tech_task_link, tech_task_file_name FROM contracts WHERE id = ?', (contract_id,))
            contract_result = cursor.fetchone()

            if contract_result and contract_result['tech_task_link']:
                tech_task_link = contract_result['tech_task_link']
                self.uploaded_file_link = tech_task_link
                # Используем сохраненное имя файла, если оно есть
                file_name = contract_result['tech_task_file_name'] if contract_result['tech_task_file_name'] else 'ТехЗадание.pdf'
                truncated_name = self.truncate_filename(file_name)
                self.file_label_display.setText(f'<a href="{tech_task_link}" title="{file_name}">{truncated_name}</a>')

        conn.close()

    def upload_file(self):
        """Загрузка файла ТЗ на Яндекс.Диск"""
        from PyQt5.QtWidgets import QFileDialog

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF файл тех.задания",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return

        # Получаем contract_id и yandex_folder_path
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (self.card_id,))
        result = cursor.fetchone()

        if not result or not result['contract_id']:
            conn.close()
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        contract_id = result['contract_id']

        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        contract_result = cursor.fetchone()
        conn.close()

        if not contract_result or not contract_result['yandex_folder_path']:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        contract_folder = contract_result['yandex_folder_path']
        file_name = os.path.basename(file_path)

        # Показываем индикатор загрузки
        self.file_label_display.setText(f'Загрузка {file_name}...')

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                print(f"[DEBUG TechTaskDialog] upload_thread: начинаем загрузку")
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Анкета",
                    file_name
                )
                print(f"[DEBUG TechTaskDialog] upload_thread: результат загрузки: {result}")

                # Извлекаем данные из результата
                if result:
                    public_link = result['public_link']
                    yandex_path = result['yandex_path']
                    file_name_result = result['file_name']
                else:
                    public_link = yandex_path = file_name_result = None

                print(f"[DEBUG TechTaskDialog] upload_thread: отправляем сигнал tech_task_upload_completed")
                # Отправляем сигнал в главный поток
                self.tech_task_upload_completed.emit(public_link, yandex_path, file_name_result, contract_id)
                print(f"[DEBUG TechTaskDialog] upload_thread: сигнал отправлен")

            except Exception as e:
                print(f"[DEBUG TechTaskDialog] upload_thread: исключение: {e}")
                self.tech_task_upload_error.emit(str(e))

        print(f"[DEBUG TechTaskDialog] Запускаем фоновый поток")
        thread = threading.Thread(target=upload_thread)
        thread.start()
        print(f"[DEBUG TechTaskDialog] Фоновый поток запущен")

    def _on_file_uploaded(self, public_link, yandex_path, file_name, contract_id):
        """Обработчик успешной загрузки файла"""
        print(f"[DEBUG TechTaskDialog] _on_file_uploaded вызван: public_link={public_link}, file_name={file_name}")
        if public_link:
            # Обновляем все поля tech_task в таблице contracts
            print(f"[DEBUG TechTaskDialog] Обновляем БД")
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE contracts
                SET tech_task_link = ?,
                    tech_task_yandex_path = ?,
                    tech_task_file_name = ?
                WHERE id = ?
            ''', (public_link, yandex_path, file_name, contract_id))
            conn.commit()
            conn.close()

            self.uploaded_file_link = public_link
            truncated_name = self.truncate_filename(file_name)
            self.file_label_display.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')
        else:
            print(f"[DEBUG TechTaskDialog] public_link отсутствует, показываем ошибку")
            self.file_label_display.setText('Не загружен')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл на Яндекс.Диск', 'error').exec_()

    def _on_file_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файла"""
        self.file_label_display.setText('Не загружен')
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файла: {error_msg}', 'error').exec_()

    def save(self):
        """Сохранение ТЗ"""
        if not self.uploaded_file_link:
            CustomMessageBox(self, 'Ошибка', 'Сначала загрузите файл ТЗ', 'warning').exec_()
            return

        tech_task_date = self.tech_task_date.date().toString('yyyy-MM-dd')

        # Обновляем карточку
        updates = {
            'tech_task_file': self.uploaded_file_link,
            'tech_task_date': tech_task_date
        }

        try:
            self.db.update_crm_card(self.card_id, updates)
            self.accept()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить ТЗ:\n{str(e)}', 'error').exec_()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 3 + screen.top()
        self.move(x, y)


class MeasurementDialog(QDialog):
    """Диалог добавления замера с загрузкой изображения"""
    # Сигналы для межпоточного взаимодействия
    upload_completed = pyqtSignal(str, str, str, int)  # public_link, yandex_path, file_name, contract_id
    upload_error = pyqtSignal(str)  # error_msg

    def __init__(self, parent, card_id, employee=None):
        super().__init__(parent)
        self.card_id = card_id
        self.employee = employee
        self.db = DatabaseManager()
        self.uploaded_image_link = None

        # Подключаем сигналы к обработчикам
        self.upload_completed.connect(self._on_image_uploaded)
        self.upload_error.connect(self._on_image_upload_error)

        # Убираем стандартную рамку окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()
        self.load_existing_measurement()

    def truncate_filename(self, filename, max_length=50):
        """Обрезает длинное имя файла с многоточием в середине"""
        if len(filename) <= max_length:
            return filename

        # Разделяем имя и расширение
        import os
        name, ext = os.path.splitext(filename)

        # Рассчитываем сколько символов оставить в начале и конце
        ext_len = len(ext)
        available = max_length - ext_len - 3  # 3 для "..."

        if available <= 0:
            return filename[:max_length - 3] + "..."

        # Половину символов в начало, половину в конец (перед расширением)
        start_len = available // 2
        end_len = available - start_len

        return name[:start_len] + "..." + name[-end_len:] + ext

    def init_ui(self):
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
        border_layout.setContentsMargins(10, 10, 10, 10)
        border_layout.setSpacing(0)

        # Title bar
        title_bar = CustomTitleBar(self, "Добавить замер", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Виджет загрузки изображения замера
        file_label = QLabel('Изображение замера:')
        layout.addWidget(file_label)

        file_row = QHBoxLayout()
        file_row.setSpacing(10)

        self.file_label_display = QLabel('Не загружено')
        self.file_label_display.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 12px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                max-width: 300px;
                text-overflow: ellipsis;
                overflow: hidden;
                white-space: nowrap;
            }
            QLabel a {
                color: #3498DB;
                text-decoration: none;
            }
            QLabel a:hover {
                color: #2980B9;
                text-decoration: underline;
            }
        ''')
        self.file_label_display.setWordWrap(False)
        self.file_label_display.setOpenExternalLinks(True)
        self.file_label_display.setTextInteractionFlags(Qt.TextBrowserInteraction)
        file_row.addWidget(self.file_label_display, 1)

        upload_btn = QPushButton('Загрузить')
        upload_btn.setFixedWidth(120)
        upload_btn.clicked.connect(self.upload_image)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #27AE60;
                color: white;
                border: none;
                padding: 12px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        ''')
        file_row.addWidget(upload_btn)

        layout.addLayout(file_row)

        # Замерщик
        surveyor_label = QLabel('Замерщик:')
        layout.addWidget(surveyor_label)

        self.surveyor_combo = CustomComboBox()
        self.surveyor_combo.setFixedHeight(36)
        surveyors = self.db.get_employees_by_position('Замерщик')
        self.surveyor_combo.addItem('Не назначен', None)
        for surv in surveyors:
            self.surveyor_combo.addItem(surv['full_name'], surv['id'])
        self.surveyor_combo.setStyleSheet('''
            QComboBox {
                background-color: #F8F9FA;
                padding: 8px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
            }
            QComboBox:hover {
                border: 1px solid #3498DB;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox:disabled {
                background-color: #E0E0E0;
                color: #999999;
            }
        ''')

        # Блокируем выбор замерщика для самого замерщика
        if self.employee and self.employee.get('position') == 'Замерщик':
            self.surveyor_combo.setEnabled(False)

        layout.addWidget(self.surveyor_combo)

        # Дата замера
        date_label = QLabel('Дата замера:')
        layout.addWidget(date_label)

        self.measurement_date = CustomDateEdit()
        self.measurement_date.setCalendarPopup(True)
        self.measurement_date.setDate(QDate.currentDate())
        self.measurement_date.setDisplayFormat('dd.MM.yyyy')
        from utils.calendar_styles import CALENDAR_STYLE, add_today_button_to_dateedit
        self.measurement_date.setStyleSheet(CALENDAR_STYLE)
        add_today_button_to_dateedit(self.measurement_date)
        layout.addWidget(self.measurement_date)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 30px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # Размер окна
        self.setFixedSize(500, 350)

    def load_existing_measurement(self):
        """Загрузка существующих данных о замере из договора"""
        # Получаем contract_id и surveyor_id из карточки
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT contract_id, surveyor_id FROM crm_cards WHERE id = ?', (self.card_id,))
        result = cursor.fetchone()

        if result and result['contract_id']:
            contract_id = result['contract_id']

            # Устанавливаем surveyor_id в ComboBox
            if result['surveyor_id']:
                surveyor_id = result['surveyor_id']
                # Находим индекс в ComboBox по surveyor_id
                for i in range(self.surveyor_combo.count()):
                    if self.surveyor_combo.itemData(i) == surveyor_id:
                        self.surveyor_combo.setCurrentIndex(i)
                        break

            # Получаем данные замера из договора
            cursor.execute('SELECT measurement_image_link, measurement_file_name, measurement_date FROM contracts WHERE id = ?', (contract_id,))
            contract_result = cursor.fetchone()

            if contract_result:
                if contract_result['measurement_image_link']:
                    measurement_link = contract_result['measurement_image_link']
                    self.uploaded_image_link = measurement_link
                    # Используем сохраненное имя файла, если оно есть
                    file_name = contract_result['measurement_file_name'] if contract_result['measurement_file_name'] else 'Замер'
                    truncated_name = self.truncate_filename(file_name)
                    self.file_label_display.setText(f'<a href="{measurement_link}" title="{file_name}">{truncated_name}</a>')

                if contract_result['measurement_date']:
                    measurement_date = QDate.fromString(contract_result['measurement_date'], 'yyyy-MM-dd')
                    self.measurement_date.setDate(measurement_date)

        conn.close()

    def upload_image(self):
        """Загрузка изображения замера на Яндекс.Диск"""
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        from PyQt5.QtCore import Qt

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение замера",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )

        if not file_path:
            return

        # Получаем contract_id и yandex_folder_path
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (self.card_id,))
        result = cursor.fetchone()

        if not result or not result['contract_id']:
            conn.close()
            CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
            return

        contract_id = result['contract_id']

        cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
        contract_result = cursor.fetchone()
        conn.close()

        if not contract_result or not contract_result['yandex_folder_path']:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        contract_folder = contract_result['yandex_folder_path']
        file_name = os.path.basename(file_path)

        # Создаем прогресс-диалог и сохраняем его как атрибут экземпляра
        self.progress = QProgressDialog("Подготовка к загрузке...", None, 0, 3, self)
        self.progress.setWindowModality(Qt.WindowModal)
        self.progress.setWindowTitle("Загрузка файла")
        self.progress.setMinimumDuration(0)
        self.progress.setAutoClose(False)  # НЕ закрываем автоматически
        self.progress.setAutoReset(False)
        self.progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.progress.setFixedSize(420, 144)
        self.progress.setCancelButton(None)  # Убираем кнопку отмены

        self.progress.setStyleSheet("""
            QProgressDialog {
                background-color: white;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
            }
            QLabel {
                color: #2C3E50;
                font-size: 12px;
                padding: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar {
                border: 1px solid #CCCCCC;
                border-radius: 3px;
                text-align: center;
                background-color: #F0F0F0;
                height: 20px;
                margin: 10px;
                min-width: 380px;
                max-width: 380px;
            }
            QProgressBar::chunk {
                background-color: #90EE90;
                border-radius: 2px;
            }
        """)
        self.progress.show()

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            print(f"[DEBUG MeasurementDialog] upload_thread начался, contract_id={contract_id}")
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    self.progress.setValue(step)
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    self.progress.setLabelText(f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)")

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Замер",
                    file_name,
                    progress_callback=update_progress
                )
                print(f"[DEBUG MeasurementDialog] Загрузка завершена, result={result}")

                if result:
                    self.progress.setValue(3)
                    # Отправляем сигнал в главный поток с полными данными
                    print(f"[DEBUG MeasurementDialog] Отправляем сигнал upload_completed...")
                    self.upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name'],
                        contract_id
                    )
                    print(f"[DEBUG MeasurementDialog] Сигнал upload_completed отправлен")
                else:
                    self.upload_error.emit("Не удалось загрузить файл")

            except Exception as e:
                print(f"[DEBUG MeasurementDialog] Исключение в upload_thread: {e}")
                import traceback
                traceback.print_exc()
                self.upload_error.emit(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_image_uploaded(self, public_link, yandex_path, file_name, contract_id):
        """Обработчик успешной загрузки изображения"""
        print(f"[DEBUG MeasurementDialog] _on_image_uploaded вызван: public_link={public_link}, yandex_path={yandex_path}, file_name={file_name}")

        # Закрываем прогресс-диалог
        if hasattr(self, 'progress') and self.progress:
            # ИСПРАВЛЕНИЕ: Закрываем прогресс через QTimer для безопасности
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.progress.close)
            self.progress = None

        if public_link:
            # Обновляем все поля замера в таблице contracts
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE contracts
                SET measurement_image_link = ?,
                    measurement_yandex_path = ?,
                    measurement_file_name = ?
                WHERE id = ?
            ''', (public_link, yandex_path, file_name, contract_id))
            conn.commit()
            conn.close()

            self.uploaded_image_link = public_link
            print(f"[DEBUG MeasurementDialog] self.uploaded_image_link установлен: {self.uploaded_image_link}")
            truncated_name = self.truncate_filename(file_name)
            self.file_label_display.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            # Обновляем данные в родительском окне
            parent = self.parent()
            if parent and hasattr(parent, 'reload_measurement_data'):
                parent.reload_measurement_data()
        else:
            print(f"[DEBUG MeasurementDialog] public_link пустой!")
            self.file_label_display.setText('Не загружено')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить изображение на Яндекс.Диск', 'error').exec_()

    def _on_image_upload_error(self, error_msg):
        """Обработчик ошибки загрузки изображения"""
        # Закрываем прогресс-диалог
        if hasattr(self, 'progress') and self.progress:
            # ИСПРАВЛЕНИЕ: Закрываем прогресс через QTimer для безопасности
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.progress.close)
            self.progress = None

        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки изображения: {error_msg}', 'error').exec_()

    def save(self):
        """Сохранение данных замера"""
        print(f"[DEBUG MeasurementDialog] save() вызван: self.uploaded_image_link={self.uploaded_image_link}")
        if not self.uploaded_image_link:
            print(f"[DEBUG MeasurementDialog] self.uploaded_image_link пустой, показываем ошибку")
            CustomMessageBox(self, 'Ошибка', 'Сначала загрузите изображение замера', 'warning').exec_()
            return

        measurement_date = self.measurement_date.date().toString('yyyy-MM-dd')
        surveyor_id = self.surveyor_combo.currentData()

        # Получаем contract_id из карточки
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT contract_id FROM crm_cards WHERE id = ?', (self.card_id,))
        result = cursor.fetchone()

        if result and result['contract_id']:
            contract_id = result['contract_id']
            # Обновляем дату в contracts
            cursor.execute('''
                UPDATE contracts
                SET measurement_date = ?
                WHERE id = ?
            ''', (measurement_date, contract_id))

            # Обновляем surveyor_id и survey_date в crm_cards
            cursor.execute('''
                UPDATE crm_cards
                SET surveyor_id = ?, survey_date = ?
                WHERE id = ?
            ''', (surveyor_id, measurement_date, self.card_id))

            conn.commit()

        conn.close()

        # Обновляем данные в родительском окне
        parent = self.parent()

        # Добавляем запись в историю проекта
        if parent and hasattr(parent, 'employee') and parent.employee:
            from datetime import datetime
            description = f"Добавлены файлы в Замер"

            self.db.add_action_history(
                user_id=parent.employee.get('id'),
                action_type='file_upload',
                entity_type='crm_card',
                entity_id=self.card_id,
                description=description
            )
            # Обновляем историю в родительском окне
            if hasattr(parent, 'reload_project_history'):
                parent.reload_project_history()
            print(f"[OK] Добавлена запись в историю: {description}")

        if parent:
            # Обновляем card_data с новыми значениями
            if hasattr(parent, 'card_data'):
                parent.card_data['surveyor_id'] = surveyor_id
                parent.card_data['survey_date'] = measurement_date
            # Обновляем отображение данных замера
            if hasattr(parent, 'reload_measurement_data'):
                parent.reload_measurement_data()
            # Принудительно обновляем labels с датой и замерщиком
            from datetime import datetime
            try:
                date_obj = datetime.strptime(measurement_date, '%Y-%m-%d')
                date_str = date_obj.strftime('%d.%m.%Y')
                if hasattr(parent, 'survey_date_label'):
                    parent.survey_date_label.setText(date_str)
                if hasattr(parent, 'project_data_survey_date_label'):
                    parent.project_data_survey_date_label.setText(date_str)
            except:
                pass

        try:
            self.accept()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить данные замера:\n{str(e)}', 'error').exec_()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 3 + screen.top()
        self.move(x, y)


class SurveyDateDialog(QDialog):
    """Диалог установки даты замера"""
    def __init__(self, parent, card_id):
        super().__init__(parent)
        self.card_id = card_id
        self.db = DatabaseManager()

        # Убираем стандартную рамку окна
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

    def init_ui(self):
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

        # Title bar
        title_bar = CustomTitleBar(self, "Дата замера", simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        border_layout.addWidget(title_bar)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #FFFFFF;")

        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        # Дата замера
        date_label = QLabel('Дата замера:')
        layout.addWidget(date_label)

        self.survey_date = CustomDateEdit()
        self.survey_date.setCalendarPopup(True)

        # Загружаем существующую дату или устанавливаем текущую
        conn = self.db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT survey_date FROM crm_cards WHERE id = ?", (self.card_id,))
        result = cursor.fetchone()
        self.db.close()

        if result and result[0]:
            from datetime import datetime
            try:
                existing_date = datetime.strptime(result[0], '%Y-%m-%d')
                self.survey_date.setDate(QDate(existing_date.year, existing_date.month, existing_date.day))
            except:
                self.survey_date.setDate(QDate.currentDate())
        else:
            self.survey_date.setDate(QDate.currentDate())

        self.survey_date.setDisplayFormat('dd.MM.yyyy')
        from utils.calendar_styles import CALENDAR_STYLE, add_today_button_to_dateedit
        self.survey_date.setStyleSheet(CALENDAR_STYLE)
        add_today_button_to_dateedit(self.survey_date)
        layout.addWidget(self.survey_date)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #16A085;
                color: white;
                padding: 10px 30px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #138D75;
            }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 10px 30px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7F8C8D;
            }
        """)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)

        layout.addLayout(buttons_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)

        border_frame.setLayout(border_layout)
        main_layout.addWidget(border_frame)
        self.setLayout(main_layout)

        # Размер окна
        self.setFixedSize(400, 220)

    def save(self):
        """Сохранение даты замера"""
        survey_date = self.survey_date.date().toString('yyyy-MM-dd')

        # Обновляем карточку
        updates = {
            'survey_date': survey_date
        }

        try:
            self.db.update_crm_card(self.card_id, updates)
            self.accept()
        except Exception as e:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить дату замера:\n{str(e)}', 'error').exec_()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from PyQt5.QtWidgets import QDesktopWidget
        screen = QDesktopWidget().availableGeometry()
        x = (screen.width() - self.width()) // 2 + screen.left()
        y = (screen.height() - self.height()) // 3 + screen.top()
        self.move(x, y)

