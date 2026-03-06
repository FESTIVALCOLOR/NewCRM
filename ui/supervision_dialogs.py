from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QDateEdit,
                             QTextEdit,
                             QTableWidget, QHeaderView, QTableWidgetItem, QGroupBox,
                             QSpinBox, QFileDialog)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QSize, QUrl, QTimer
from PyQt5.QtGui import QColor
from database.db_manager import DatabaseManager
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from ui.custom_combobox import CustomComboBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit, ICONS_PATH
from utils.resource_path import resource_path
from utils.table_settings import apply_no_focus_delegate
from utils.data_access import DataAccess
import os


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
        
class SupervisionStatisticsDialog(QDialog):
    """Диалог статистики надзора"""

    def __init__(self, parent, api_client=None):
        super().__init__(parent)
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client

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
            'Стадия 7: Лепной декор', 'Стадия 8: Освещение',
            'Стадия 9: Бытовая техника', 'Стадия 10: Закупка заказной мебели',
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
            addresses = self.data.get_supervision_addresses()
            for addr in addresses:
                display = f"{addr['contract_number']} - {addr['address']}"
                self.address_combo.addItem(display, addr['contract_id'])
        except Exception as e:
            print(f"Ошибка загрузки адресов: {e}")

    def load_executors(self):
        """Загрузка ДАН'ов"""
        try:
            dans = self.data.get_employees_by_position('ДАН')
            for dan in dans:
                self.executor_combo.addItem(dan['full_name'], dan['id'])
        except Exception as e:
            print(f"Ошибка загрузки ДАН'ов: {e}")

    def load_managers(self):
        """Загрузка менеджеров"""
        try:
            managers = self.data.get_employees_by_position('Старший менеджер проектов')
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

        stats = self.data.get_supervision_statistics_filtered(
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
        import logging
        from PyQt5.QtWidgets import QFileDialog
        from utils.pdf_utils import build_table_pdf
        _logger = logging.getLogger(__name__)

        default_name = f'Отчет Статистика авторского надзора от {QDate.currentDate().toString("dd.MM.yyyy")}'
        filename, _ = QFileDialog.getSaveFileName(
            self, 'Сохранить PDF', default_name, 'PDF файлы (*.pdf)'
        )
        if not filename:
            return

        try:
            headers = [self.stats_table.horizontalHeaderItem(col).text()
                       for col in range(self.stats_table.columnCount())]
            rows = []
            total = self.stats_table.rowCount()
            paused = completed_work = in_work = 0

            for row in range(total):
                row_data = []
                for col in range(self.stats_table.columnCount()):
                    item = self.stats_table.item(row, col)
                    row_data.append(item.text() if item else '')
                rows.append(row_data)

                status_item = self.stats_table.item(row, 6)
                if status_item:
                    st = status_item.text()
                    if 'Приостановлено' in st:
                        paused += 1
                    elif 'Работа сдана' in st:
                        completed_work += 1
                    else:
                        in_work += 1

            build_table_pdf(
                output_path=filename,
                title='Статистика CRM Авторского надзора',
                headers=headers,
                rows=rows,
                summary_items=[
                    ('Всего проектов', str(total)),
                    ('В работе', str(in_work)),
                    ('Работа сдана', str(completed_work)),
                    ('Приостановлено', str(paused)),
                ],
                status_column=6,
                status_colors={
                    'Приостановлено': '#F39C12',
                    'Работа сдана': '#27AE60',
                },
            )
        except Exception as e:
            _logger.error(f"Ошибка экспорта PDF: {e}", exc_info=True)
            CustomMessageBox(self, 'Ошибка', f'Не удалось создать PDF:\n{e}', 'error').exec_()
        
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
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client

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
            contract_id = self.data.get_contract_id_by_supervision_card(self.card_id)

            clean_status = status.replace('Проект ', '')

            updates = {
                'status': clean_status
            }

            if 'РАСТОРГНУТ' in status:
                updates['termination_reason'] = self.termination_reason.toPlainText().strip()

            self.data.update_contract(contract_id, updates)
            
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
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client

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
            self.data.add_supervision_history(
                self.card_id,
                self.employee['id'],
                'note',
                message
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

    def __init__(self, parent, card_id, stage_name, api_client=None, employee=None):
        super().__init__(parent)
        self.card_id = card_id
        self.stage_name = stage_name
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client
        self.employee = employee or getattr(parent, 'employee', None)

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
        """Сохранение дедлайна в карточку и в таблицу сроков (plan_date)"""
        from utils.permissions import _has_perm
        if self.employee and not _has_perm(self.employee, self.api_client, 'supervision.deadlines'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на управление дедлайнами.', 'error').exec_()
            return
        deadline = self.deadline_widget.date().toString('yyyy-MM-dd')

        try:
            self.data.update_supervision_card(self.card_id, {
                'deadline': deadline
            })

            # Обновляем plan_date в таблице сроков для текущей стадии
            try:
                timeline_data = self.data.get_supervision_timeline(self.card_id) or {}
                # get_supervision_timeline возвращает {'entries': [...], 'totals': {...}}
                timeline_entries = timeline_data.get('entries', []) if isinstance(timeline_data, dict) else timeline_data
                for entry in timeline_entries:
                    if entry.get('stage_name') == self.stage_name:
                        stage_code = entry.get('stage_code', '')
                        self.data.update_supervision_timeline_entry(
                            self.card_id, stage_code, {'plan_date': deadline}
                        )
                        print(f"[DEADLINE] plan_date обновлён для стадии '{self.stage_name}' (code={stage_code}): {deadline}")
                        break
            except Exception as e:
                print(f"[WARN] Не удалось обновить plan_date в timeline: {e}")

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

    def __init__(self, parent, card_id, current_dan_name, api_client=None, employee=None):
        super().__init__(parent)
        self.card_id = card_id
        self.current_dan_name = current_dan_name
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = api_client
        self.employee = employee or getattr(parent, 'employee', None)

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

        dans = self.data.get_employees_by_position('ДАН')

        if not dans:
            CustomMessageBox(self, 'Внимание', 'Нет доступных сотрудников с должностью "ДАН"', 'warning').exec_()
            self.reject()
            return

        for dan in dans:
            self.dan_combo.addItem(dan['full_name'], dan['id'])

        try:
            card_data = self.data.get_supervision_card(self.card_id)
            current_dan_id = card_data.get('dan_id') if card_data else None

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
        from utils.permissions import _has_perm
        if self.employee and not _has_perm(self.employee, self.api_client, 'supervision.assign_executor'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на переназначение исполнителей.', 'error').exec_()
            return
        new_dan_id = self.dan_combo.currentData()

        if not new_dan_id:
            CustomMessageBox(self, 'Ошибка', 'Выберите ДАН', 'warning').exec_()
            return

        try:
            # ИСПРАВЛЕНИЕ 29.01.2026: Получаем старого ДАН и contract_id для переназначения платежей
            old_dan_id = None
            contract_id = None

            card_data = self.data.get_supervision_card(self.card_id)
            if card_data:
                old_dan_id = card_data.get('dan_id')
                contract_id = card_data.get('contract_id')
                print(f"[DEBUG] Старый ДАН: {old_dan_id}, contract_id: {contract_id}")

            self.data.update_supervision_card(self.card_id, {'dan_id': new_dan_id})
            print(f"[DataAccess] ДАН переназначен: dan_id={new_dan_id}")

            # ИСПРАВЛЕНИЕ 29.01.2026: Переназначение платежей
            if contract_id and old_dan_id and new_dan_id != old_dan_id:
                self._reassign_dan_payments(contract_id, old_dan_id, new_dan_id)

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
            all_payments = self.data.get_payments_for_contract(contract_id) or []

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
                    self.data.update_payment(old_payment_id, {
                        'reassigned': True,
                        'report_month': current_month
                    })
                    print(f"[DataAccess] Старый платеж ДАН {old_payment_id} ({payment_type}) помечен как переназначенный")

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

                    self.data.create_payment(new_payment_data)
                    print(f"[DataAccess] Создан новый платеж ДАН ({payment_type}) для исполнителя {new_dan_id}")
            else:
                # Если старых платежей нет - создаём новые для нового ДАН
                print(f"[INFO] Платежи для старого ДАН не найдены, создаём новые")

                # Рассчитываем сумму для новых платежей
                try:
                    full_amount = 0

                    # Рассчитываем сумму через DataAccess
                    try:
                        print(f"[DEBUG] Вызов calculate_payment_amount для ДАН: contract_id={contract_id}, employee_id={new_dan_id}, role={role}")
                        result = self.data.calculate_payment_amount(contract_id, new_dan_id, role)
                        print(f"[DEBUG] Результат calculate_payment_amount ДАН: {result}")
                        full_amount = float(result) if result else 0
                    except Exception as e:
                        print(f"[WARN] Ошибка расчёта суммы ДАН: {e}")

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

                    self.data.create_payment(payment_data)
                    print(f"[DataAccess] Создан новый платеж ДАН (Полная оплата) для исполнителя {new_dan_id}: {full_amount:.2f}")

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
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)


class AssignExecutorsDialog(QDialog):
    """Диалог назначения исполнителей (ДАН и СМП) при перемещении карточки на рабочую стадию"""

    def __init__(self, parent, card_id, stage_name, api_client=None, employee=None):
        super().__init__(parent)
        self.card_id = card_id
        self.stage_name = stage_name
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = api_client
        self.employee = employee or getattr(parent, 'employee', None)
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
        managers = self.data.get_employees_by_position('Старший менеджер проектов')

        self.smp_combo.addItem('Не назначен', None)
        for manager in managers:
            self.smp_combo.addItem(manager['full_name'], manager['id'])

    def _load_dans(self):
        """Загрузка списка ДАН"""
        dans = self.data.get_employees_by_position('ДАН')

        self.dan_combo.addItem('Не назначен', None)
        for dan in dans:
            self.dan_combo.addItem(dan['full_name'], dan['id'])

    def save_and_continue(self):
        """Сохранение назначенных исполнителей"""
        from utils.permissions import _has_perm
        if self.employee and not _has_perm(self.employee, self.api_client, 'supervision.assign_executor'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на назначение исполнителей.', 'error').exec_()
            return
        self.assigned_dan_id = self.dan_combo.currentData()
        self.assigned_smp_id = self.smp_combo.currentData()

        # Проверяем, что хотя бы один исполнитель назначен
        if not self.assigned_dan_id and not self.assigned_smp_id:
            CustomMessageBox(
                self,
                'Внимание',
                'Необходимо назначить хотя бы одного исполнителя (ДАН или Старшего менеджера)',
                'warning'
            ).exec_()
            return

        # Сохраняем в БД
        updates = {}
        if self.assigned_dan_id:
            updates['dan_id'] = self.assigned_dan_id
        if self.assigned_smp_id:
            updates['senior_manager_id'] = self.assigned_smp_id

        if updates:
            self.data.update_supervision_card(self.card_id, updates)
            print(f"[DataAccess] Назначены исполнители для карточки {self.card_id}: {updates}")

        self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)


class SupervisionFileUploadDialog(QDialog):
    """Диалог загрузки файла для карточки авторского надзора с выбором стадии и даты"""

    def __init__(self, parent, card_data, stages, api_client=None, simple_mode=False, employee=None):
        super().__init__(parent)
        self.card_data = card_data
        self.stages = stages  # Список стадий для выбора
        self.simple_mode = simple_mode  # True = только файл, стадия, дата (без бюджета)
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = api_client
        self.employee = employee or getattr(parent, 'employee', None)
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
        self.date_edit.setCalendarPopup(True)
        self.date_edit.setDisplayFormat('dd.MM.yyyy')
        self.date_edit.setFixedHeight(28)
        self.date_edit.setDate(QDate.currentDate())
        form_layout.addRow('Дата:', self.date_edit)

        if self.simple_mode:
            # Простой режим: только файл, стадия, дата — без полей бюджета
            pass
        else:
            # Разделитель
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setStyleSheet('color: #E0E0E0;')
            form_layout.addRow(separator)

            # Доп. поля: данные для таблицы сроков надзора
            fields_hint = QLabel('Данные для таблицы сроков (необязательно)')
            fields_hint.setStyleSheet('color: #888; font-size: 10px; font-style: italic;')
            form_layout.addRow(fields_hint)

        if not self.simple_mode:
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
        if self.simple_mode:
            hint = QLabel('После загрузки файл будет привязан к выбранной стадии.')
        else:
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
        from utils.permissions import _has_perm
        if self.employee and not _has_perm(self.employee, self.api_client, 'supervision.files_upload'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на загрузку файлов.', 'error').exec_()
            return
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
        }
        if not self.simple_mode:
            # Доп. поля для таблицы сроков
            self.result_data.update({
                'budget_planned': self._parse_number(self.budget_planned_edit.text()),
                'budget_actual': self._parse_number(self.budget_actual_edit.text()),
                'supplier': self.supplier_edit.text().strip(),
                'commission': self._parse_number(self.commission_edit.text()),
                'notes': self.notes_edit.text().strip(),
            })

        self.accept()

    def get_result(self):
        """Получить результат диалога"""
        return self.result_data

    def showEvent(self, event):
        super().showEvent(event)
        # Подключаем сигнал изменения стадии (однократно, иначе утечка при повторных showEvent)
        if not hasattr(self, '_signals_connected'):
            self._signals_connected = True
            self.stage_combo.currentIndexChanged.connect(self.update_upload_button)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()

    def center_on_screen(self):
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)


class SupervisionStartDateDialog(QDialog):
    """Диалог изменения даты начала надзора — кастомный календарь в стиле проекта"""

    def __init__(self, parent=None, current_date=None, data=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.selected_date = current_date or QDate.currentDate()

        border_widget = QFrame(self)
        border_widget.setStyleSheet("""
            QFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)

        border_layout = QVBoxLayout()
        border_layout.setContentsMargins(0, 0, 0, 0)
        border_layout.setSpacing(0)

        title_bar = CustomTitleBar(self, 'Изменить дату начала', simple_mode=True)
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

        label = QLabel('Выберите новую дату начала:')
        label.setStyleSheet('font-size: 12px; font-weight: bold; color: #333;')
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        date_layout = QHBoxLayout()
        date_layout.addStretch()

        from ui.custom_dateedit import CustomDateEdit
        from utils.calendar_helpers import add_today_button_to_dateedit

        self.date_widget = CustomDateEdit()
        self.date_widget.setCalendarPopup(True)
        add_today_button_to_dateedit(self.date_widget)
        self.date_widget.setDate(current_date or QDate.currentDate())
        self.date_widget.setDisplayFormat('dd.MM.yyyy')
        self.date_widget.setMinimumWidth(150)
        self.date_widget.setStyleSheet("""
            QDateEdit {
                padding: 6px;
                border: 1px solid #CCC;
                border-radius: 4px;
                font-size: 11px;
            }
        """)
        date_layout.addWidget(self.date_widget)
        date_layout.addStretch()
        layout.addLayout(date_layout)

        # Кнопки
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedSize(100, 32)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0; color: #333;
                border: none; border-radius: 4px;
                font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
        """)
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedSize(100, 32)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50; color: white;
                border: none; border-radius: 4px;
                font-weight: bold; font-size: 11px;
            }
            QPushButton:hover { background-color: #45a049; }
        """)
        save_btn.clicked.connect(self._save)
        btn_layout.addWidget(save_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        content_widget.setLayout(layout)
        border_layout.addWidget(content_widget)
        border_widget.setLayout(border_layout)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(border_widget)

        self.setMinimumWidth(400)

    def _save(self):
        self.selected_date = self.date_widget.date()
        self.accept()

    def showEvent(self, event):
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            from utils.dialog_helpers import center_dialog_on_parent
            center_dialog_on_parent(self)
