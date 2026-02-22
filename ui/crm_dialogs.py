# -*- coding: utf-8 -*-
"""Мелкие диалоги CRM, выделенные из crm_tab.py"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QDateEdit,
                             QGroupBox, QSpinBox, QTableWidget, QHeaderView,
                             QTableWidgetItem, QTabWidget, QTextEdit)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import (QColor, QPixmap, QTextDocument, QTextCursor, QTextTableFormat,
                         QTextCharFormat, QFont, QBrush,
                         QTextBlockFormat, QTextLength, QTextImageFormat)
from PyQt5.QtPrintSupport import QPrinter
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_combobox import CustomComboBox
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
from utils.table_settings import ProportionalResizeTable, apply_no_focus_delegate
from utils.date_utils import format_date, format_month_year
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
from utils.resource_path import resource_path
from utils.dialog_helpers import create_progress_dialog
import os
import threading



class RejectWithCorrectionsDialog(QDialog):
    """Диалог отправки на исправление с загрузкой файла правок на ЯД"""

    def __init__(self, parent, stage_name, contract_id, api_client, db):
        super().__init__(parent)
        self.stage_name = stage_name
        self.contract_id = contract_id
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = api_client
        self.corrections_folder_path = ''
        self.selected_file = ''
        self.setWindowTitle('Отправить на исправление')
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setFixedWidth(420)
        self.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        # Заголовок
        title = QLabel(f'Отправить на исправление')
        title.setStyleSheet('font-size: 14px; font-weight: bold; color: #E74C3C;')
        layout.addWidget(title)

        # Описание
        desc = QLabel(f'Стадия: {self.stage_name}\n\nВыберите файл с правками для загрузки на Яндекс.Диск (необязательно):')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 11px; color: #555;')
        layout.addWidget(desc)

        # Выбор файла
        file_row = QHBoxLayout()
        self.file_label = QLabel('Файл не выбран')
        self.file_label.setStyleSheet('font-size: 10px; color: #999; padding: 4px 8px; border: 1px dashed #CCC; border-radius: 4px;')
        self.file_label.setMinimumHeight(28)
        file_row.addWidget(self.file_label, 1)

        select_btn = QPushButton('Выбрать файл')
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #DDD;
                border-radius: 4px;
                padding: 4px 12px;
                font-size: 10px;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        """)
        select_btn.setFixedHeight(28)
        select_btn.clicked.connect(self._select_file)
        file_row.addWidget(select_btn)
        layout.addLayout(file_row)

        # Кнопки
        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #F5F5F5;
                border: 1px solid #DDD;
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 11px;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover { background-color: #E8E8E8; }
        """)
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        self.send_btn = QPushButton('Отправить на исправление')
        self.send_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 16px;
                font-size: 11px;
                font-weight: bold;
                min-height: 20px;
                max-height: 20px;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        self.send_btn.setFixedHeight(28)
        self.send_btn.clicked.connect(self._submit)
        btn_row.addWidget(self.send_btn)

        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _select_file(self):
        from PyQt5.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 'Выбрать файл правок', '',
            'Все файлы (*.*);;Документы (*.pdf *.doc *.docx);;Изображения (*.png *.jpg *.jpeg)'
        )
        if file_path:
            self.selected_file = file_path
            import os
            self.file_label.setText(os.path.basename(file_path))
            self.file_label.setStyleSheet('font-size: 10px; color: #333; padding: 4px 8px; border: 1px solid #27AE60; border-radius: 4px; background-color: #E8F8F5;')

    def _submit(self):
        """Отправка: загрузка файла на ЯД (если выбран) и закрытие диалога"""
        if self.selected_file:
            self.send_btn.setEnabled(False)
            self.send_btn.setText('Загрузка...')
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

            try:
                from utils.yandex_disk import YandexDiskManager
                from config import YANDEX_DISK_TOKEN

                # Получаем путь к папке договора на ЯД
                contract_folder = None
                if self.contract_id:
                    # Используем тот же метод что и CRMCard
                    try:
                        if self.data.is_multi_user:
                            contract = self.data.get_contract(self.contract_id)
                            contract_folder = contract.get('yandex_folder_path') if contract else None
                        else:
                            conn = self.data.db.connect()
                            cursor = conn.cursor()
                            cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (self.contract_id,))
                            result = cursor.fetchone()
                            conn.close()
                            contract_folder = result['yandex_folder_path'] if result else None
                    except Exception as e:
                        print(f"[WARN] Не удалось получить папку договора: {e}")

                if contract_folder and YANDEX_DISK_TOKEN:
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                    # Создаем папку правок
                    corrections_path = yd.create_corrections_folder(contract_folder, self.stage_name)

                    if corrections_path:
                        self.corrections_folder_path = corrections_path
                        import os
                        file_name = os.path.basename(self.selected_file)
                        yandex_file_path = f"{corrections_path}/{file_name}"

                        # Загружаем файл
                        yd.upload_file(self.selected_file, yandex_file_path)
                else:
                    print("[WARN] Нет папки договора или токена ЯД — файл не загружен")

            except Exception as e:
                print(f"[ERROR] Ошибка загрузки файла правок: {e}")
                CustomMessageBox(self, 'Предупреждение',
                    f'Файл правок не удалось загрузить на Яндекс.Диск:\n{e}\n\nИсправление все равно будет отправлено.',
                    'warning').exec_()

        self.accept()



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
                border: 1px solid #E0E0E0;
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
                background-color: #f5f5f5;
                border: 2px solid #ffd93c;
                border-radius: 4px;
                padding: 15px;
            }
        """)
        link_layout = QVBoxLayout()
        
        link_label = QLabel(f'<a href="{self.project_data_link}" style="color: #ffd93c; font-size: 12px; text-decoration: underline;">{self.project_data_link}</a>')
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
                background-color: #ffd93c;
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
        # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие
    
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












class ExecutorSelectionDialog(QDialog):
    def __init__(self, parent, card_id, stage_name, project_type, api_client=None, contract_id=None):
        super().__init__(parent)
        self.card_id = card_id
        self.stage_name = stage_name
        self.project_type = project_type
        self.contract_id = contract_id
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client

        # Загрузка norm_days из timeline
        self._norm_days = 0
        self._current_substep = ''
        self._load_timeline_norm_days()

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

        self.init_ui()

    def _load_timeline_norm_days(self):
        """Загрузить norm_days первого незаполненного подэтапа текущей стадии
        и дату предыдущего подэтапа для расчёта дедлайна."""
        self._prev_actual_date = ''  # дата предыдущего подэтапа (для расчёта дедлайна)
        self._current_stage_code = ''  # stage_code подэтапа для обновления custom_norm_days
        if not self.contract_id:
            return
        try:
            entries = self.data.get_project_timeline(self.contract_id)
            if not entries:
                return
            # Определяем stage_group из stage_name
            stage_group = ''
            if 'Стадия 1' in self.stage_name:
                stage_group = 'STAGE1'
            elif 'Стадия 2' in self.stage_name:
                stage_group = 'STAGE2'
            elif 'Стадия 3' in self.stage_name:
                stage_group = 'STAGE3'

            if not stage_group:
                return

            # Сортируем по sort_order для корректного определения предыдущего подэтапа
            sorted_entries = sorted(entries, key=lambda x: x.get('sort_order', 0))

            # prev_date сквозной по всем стадиям: дедлайн считается от
            # последней заполненной actual_date в timeline (не только текущей стадии),
            # т.к. стадии выполняются последовательно.
            prev_date = ''
            for e in sorted_entries:
                if e.get('executor_role', '') == 'header':
                    continue
                if (e.get('stage_group') == stage_group
                        and not e.get('actual_date')
                        and e.get('norm_days', 0) > 0):
                    # Нашли первый незаполненный подэтап в текущей стадии
                    self._norm_days = int(e.get('norm_days', 0))
                    self._current_substep = e.get('stage_name', '')
                    self._current_stage_code = e.get('stage_code', '')
                    self._prev_actual_date = prev_date  # дата предыдущего заполненного
                    break
                # Обновляем prev_date только для non-header строк с actual_date
                ad = e.get('actual_date', '')
                if ad:
                    prev_date = ad
        except Exception as ex:
            print(f"[ExecutorDialog] Ошибка загрузки timeline: {ex}")
    
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
                border: 1px solid #E0E0E0;
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
            SELECT se.stage_name, e.full_name, se.assigned_date
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
                        # Пробуем сначала с временем
                        assigned_date = datetime.strptime(record['assigned_date'], '%Y-%m-%d %H:%M:%S')
                        date_str = assigned_date.strftime('%d-%m-%Y')
                    except Exception:
                        try:
                            # Пробуем без времени
                            assigned_date = datetime.strptime(record['assigned_date'][:10], '%Y-%m-%d')
                            date_str = assigned_date.strftime('%d-%m-%Y')
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

        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлена поддержка стадии 3д визуализации (#18)
        if 'Стадия 1' in self.stage_name:
            position = 'Чертёжник'
        elif 'Стадия 2' in self.stage_name and 'концепция' in self.stage_name:
            position = 'Дизайнер'
        elif '3д визуализация' in self.stage_name.lower() or 'визуализация' in self.stage_name.lower():
            position = 'Дизайнер'  # 3д визуализация - работа дизайнера
        elif 'Стадия 2' in self.stage_name or 'Стадия 3' in self.stage_name:
            position = 'Чертёжник'
        else:
            position = 'Чертёжник'

        # ИСПРАВЛЕНИЕ 06.02.2026: Стандартная высота 28px (#14)
        self.executor_combo = CustomComboBox()
        self.executor_combo.setFixedHeight(28)

        # ИСПРАВЛЕНИЕ 30.01.2026: Получаем сотрудников включая двойные должности (secondary_position)
        try:
            all_employees = self.data.get_all_employees()
            # Фильтруем по основной ИЛИ дополнительной должности
            executors = [e for e in all_employees
                        if e.get('position') == position
                        or e.get('secondary_position') == position]
            print(f"[OK] Поиск сотрудников с должностью '{position}' (включая secondary_position):")
            for e in executors:
                secondary = e.get('secondary_position', '')
                secondary_text = f" + {secondary}" if secondary else ""
                print(f"  [OK] {e['full_name']} ({e['position']}{secondary_text})")
        except Exception as e:
            print(f"[DataAccess ERROR] Ошибка получения сотрудников: {e}")
            executors = []

        if not executors:
            # ========== ЗАМЕНИЛИ QMessageBox ==========
            CustomMessageBox(self, 'Внимание', f'Нет доступных сотрудников с должностью "{position}"', 'warning').exec_()
            self.reject()
            return

        for executor in executors:
            self.executor_combo.addItem(executor['full_name'], executor['id'])

        # ИСПРАВЛЕНИЕ: Предлагаем исполнителя из предыдущих стадий
        # Получаем предыдущего исполнителя через DataAccess
        previous_executor_id = None
        try:
            card_data = self.data.get_crm_card(self.card_id)
            stage_executors = card_data.get('stage_executors', [])
            for se in stage_executors:
                exec_id = se.get('executor_id')
                if exec_id:
                    # Проверяем, что этот исполнитель в списке доступных
                    for executor in executors:
                        if executor['id'] == exec_id:
                            previous_executor_id = exec_id
                            break
                if previous_executor_id:
                    break
        except Exception as e:
            print(f"[DataAccess] Ошибка получения предыдущего исполнителя: {e}")

        if previous_executor_id:
            for i in range(self.executor_combo.count()):
                if self.executor_combo.itemData(i) == previous_executor_id:
                    self.executor_combo.setCurrentIndex(i)
                    print(f"Предложен исполнитель из предыдущих стадий (ID={previous_executor_id})")
                    break

        form_layout.addRow('Исполнитель:', self.executor_combo)
        
        # Норма дней из таблицы сроков
        if self._norm_days > 0:
            norm_label = QLabel(f'Норма дней: {self._norm_days} раб. дн.')
            norm_label.setStyleSheet('color: #2F5496; font-size: 11px; font-weight: 600;')
            form_layout.addRow('', norm_label)
            if self._current_substep:
                substep_label = QLabel(f'Подэтап: {self._current_substep}')
                substep_label.setStyleSheet('color: #666; font-size: 10px;')
                substep_label.setWordWrap(True)
                form_layout.addRow('', substep_label)

        self.stage_deadline = CustomDateEdit()
        self.stage_deadline.setCalendarPopup(True)
        # Авторасчёт дедлайна из norm_days
        # База: дата предыдущего подэтапа (если есть), иначе сегодня
        if self._norm_days > 0:
            from utils.calendar_helpers import add_working_days
            base_date = getattr(self, '_prev_actual_date', '') or ''
            if not base_date:
                base_date = QDate.currentDate().toString('yyyy-MM-dd')
            auto_deadline = add_working_days(base_date, self._norm_days)
            if auto_deadline:
                d = QDate.fromString(auto_deadline, 'yyyy-MM-dd')
                if d.isValid():
                    self.stage_deadline.setDate(d)
                else:
                    self.stage_deadline.setDate(QDate.currentDate().addDays(7))
            else:
                self.stage_deadline.setDate(QDate.currentDate().addDays(7))
        else:
            self.stage_deadline.setDate(QDate.currentDate().addDays(7))
        self.stage_deadline.setDisplayFormat('dd.MM.yyyy')
        self.stage_deadline.setStyleSheet(CALENDAR_STYLE)
        form_layout.addRow('Дедлайн:', self.stage_deadline)

        layout.addLayout(form_layout)

        hint = QLabel('Исполнитель получит доступ к карточке после назначения')
        hint.setWordWrap(True)
        hint.setStyleSheet('color: #666; font-size: 10px; font-style: italic;')
        layout.addWidget(hint)
        
        # ИСПРАВЛЕНИЕ 07.02.2026: Желтая кнопка как в unified_styles (#14)
        save_btn = QPushButton('Назначить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 4px 12px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #e6c435; }
        """)
        save_btn.clicked.connect(self.assign_executor)
        layout.addWidget(save_btn)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #95A5A6;
                color: white;
                padding: 4px 12px;
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

        # Назначаем исполнителя через DataAccess
        try:
            stage_data = {
                'stage_name': self.stage_name,
                'executor_id': executor_id,
                'deadline': deadline,
                'assigned_by': current_user_id
            }
            self.data.assign_stage_executor(self.card_id, stage_data)
            print(f"[DataAccess] Исполнитель назначен на стадию {self.stage_name}")
        except Exception as e:
            print(f"[DataAccess ERROR] Ошибка назначения исполнителя: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось назначить исполнителя: {e}', 'error').exec_()
            return

        # ========== СОХРАНЕНИЕ custom_norm_days (если СДП изменил дедлайн) ==========
        if self._norm_days > 0 and self._current_stage_code and self.contract_id:
            try:
                from utils.calendar_helpers import add_working_days, working_days_between
                base_date = self._prev_actual_date or ''
                if not base_date:
                    base_date = QDate.currentDate().toString('yyyy-MM-dd')
                auto_deadline = add_working_days(base_date, self._norm_days)
                if auto_deadline and deadline != auto_deadline:
                    # СДП установил дату, отличную от авторасчёта — сохраняем custom_norm_days
                    custom_days = working_days_between(base_date, deadline)
                    if custom_days and custom_days != self._norm_days:
                        self.data.update_timeline_entry(
                            self.contract_id,
                            self._current_stage_code,
                            {'custom_norm_days': custom_days}
                        )
                        print(f"[Timeline] custom_norm_days={custom_days} для {self._current_stage_code} "
                              f"(стандарт: {self._norm_days})")
            except Exception as ex:
                print(f"[Timeline] Ошибка сохранения custom_norm_days: {ex}")

        # ========== СОЗДАЕМ ВЫПЛАТЫ (АВАНС + ДОПЛАТА) ==========
        try:
            contract_id = self.data.get_contract_id_by_crm_card(self.card_id)

            # ИСПРАВЛЕНИЕ 30.01.2026: Проверка наличия contract_id
            if not contract_id:
                print(f"[ERROR] contract_id не найден для crm_card_id={self.card_id}")
                raise Exception(f"Договор не найден для карточки {self.card_id}")

            contract = self.data.get_contract(contract_id)

            # ИСПРАВЛЕНИЕ 30.01.2026: Проверка наличия контракта
            if not contract:
                print(f"[ERROR] Договор с ID={contract_id} не найден в БД")
                raise Exception(f"Договор ID={contract_id} не найден")

            # ИСПРАВЛЕНИЕ 06.02.2026: Добавлена поддержка стадии 3д визуализации (#18)
            # Определяем роль исполнителя
            if 'концепция' in self.stage_name or 'визуализация' in self.stage_name.lower():
                role = 'Дизайнер'
            else:
                role = 'Чертёжник'

            # ИСПРАВЛЕНИЕ: Для индивидуальных - создаем АВАНС (50%) и ДОПЛАТУ (50%)
            if contract['project_type'] == 'Индивидуальный':
                # Рассчитываем полную сумму
                full_amount = self.data.calculate_payment_amount(
                    contract_id, executor_id, role, self.stage_name
                )

                # Делим пополам
                advance_amount = full_amount / 2
                balance_amount = full_amount / 2

                current_month = QDate.currentDate().toString('yyyy-MM')

                # Создаем аванс через DataAccess
                advance_data = {
                    'contract_id': contract_id,
                    'crm_card_id': self.card_id,
                    'employee_id': executor_id,
                    'role': role,
                    'stage_name': self.stage_name,
                    'calculated_amount': advance_amount,
                    'final_amount': advance_amount,
                    'payment_type': 'Аванс',
                    'report_month': current_month
                }
                self.data.create_payment(advance_data)

                balance_data = {
                    'contract_id': contract_id,
                    'crm_card_id': self.card_id,
                    'employee_id': executor_id,
                    'role': role,
                    'stage_name': self.stage_name,
                    'calculated_amount': balance_amount,
                    'final_amount': balance_amount,
                    'payment_type': 'Доплата',
                    'report_month': ''
                }
                self.data.create_payment(balance_data)
                print(f"[DataAccess] Индивидуальный проект: созданы аванс и доплата для {role}")
            else:
                # ========== ИСПРАВЛЕНИЕ 06.02.2026: ШАБЛОННЫЕ ПРОЕКТЫ - СПЕЦИАЛЬНАЯ ЛОГИКА (#16) ==========
                # Для стадии 1 (планировочные) создаём выплату с суммой 0.00
                # Для стадии 2 и выше создаём выплату с тарифом из таблицы
                is_stage_1 = ('Стадия 1' in self.stage_name or 'планировочные' in self.stage_name.lower())

                # Рассчитываем сумму (для стадии 1 будет 0, для стадии 2+ берём из тарифов)
                if is_stage_1:
                    calculated_amount = 0.00
                    final_amount = 0.00
                    print(f"[INFO] Стадия 1: создаём выплату с суммой 0.00 для {role}")
                else:
                    # Расчёт суммы через DataAccess
                    result = self.data.calculate_payment_amount(
                        contract_id, executor_id, role, self.stage_name
                    )
                    calculated_amount = float(result) if result else 0
                    final_amount = calculated_amount
                    print(f"[INFO] Стадия 2+: создаём выплату с тарифом {calculated_amount:.2f} для {role}")

                # Создаём выплату через DataAccess
                payment_data = {
                    'contract_id': contract_id,
                    'crm_card_id': self.card_id,
                    'employee_id': executor_id,
                    'role': role,
                    'stage_name': self.stage_name,
                    'calculated_amount': calculated_amount,
                    'final_amount': final_amount,
                    'payment_type': 'Полная оплата',
                    'report_month': ''
                }
                self.data.create_payment(payment_data)
                print(f"[DataAccess] Шаблонный проект: создана выплата для {role}")
                # =========================================================================

            print(f"Выплаты созданы для {role} по стадии {self.stage_name}")

        except Exception as e:
            print(f"Ошибка создания выплат: {e}")
        # ========================================================

        # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех"
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
    def __init__(self, parent, card_id, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client
        
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
                border: 1px solid #E0E0E0;
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
            CustomMessageBox(self, 'Ошибка', 'Укажите причину расторжения', 'warning').exec_()
            return

        try:
            contract_id = self.data.get_contract_id_by_crm_card(self.card_id)

            # Формируем данные для обновления договора
            contract_status = status.replace('Проект ', '').replace('передан в ', '')
            updates = {
                'status': contract_status,
                'status_changed_date': QDate.currentDate().toString('yyyy-MM-dd')
            }

            if 'РАСТОРГНУТ' in status:
                updates['termination_reason'] = self.termination_reason.toPlainText().strip()

            # Обновляем через DataAccess
            supervision_card_id = None

            # 1. Обновляем договор
            self.data.update_contract(contract_id, updates)
            print(f"[DataAccess] Договор {contract_id} обновлен: {updates}")

            # 2. Создаём карточку надзора (если нужно)
            if 'АВТОРСКИЙ НАДЗОР' in status:
                print(f"\n Создание карточки надзора для договора {contract_id}...")
                supervision_data = {
                    'contract_id': contract_id,
                    'column_name': 'Новый заказ'
                }
                result = self.data.create_supervision_card(supervision_data)
                supervision_card_id = result.get('id') if isinstance(result, dict) else result
                print(f"[DataAccess] Создана карточка надзора ID={supervision_card_id}")

            # 3. Устанавливаем отчетный месяц
            current_month = QDate.currentDate().toString('yyyy-MM')
            try:
                self.data.set_payments_report_month(contract_id, current_month)
                print(f"[DataAccess] Установлен отчетный месяц {current_month}")
            except Exception as e:
                print(f"[WARN] Ошибка установки отчетного месяца: {e}")
                # Fallback на локальную БД
                self._set_report_month_locally(contract_id, current_month)

            print(f"Проект завершен со статусом: {contract_status}")
            if supervision_card_id:
                print(f"  Результат: supervision_card_id = {supervision_card_id}")

            # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех"
            self.accept()

        except Exception as e:
            print(f" Ошибка завершения проекта: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось завершить проект: {e}', 'error').exec_()

    def _complete_project_locally(self, contract_id, updates, status):
        """Локальное завершение проекта (offline fallback)"""
        self.data.update_contract(contract_id, updates)

        if 'АВТОРСКИЙ НАДЗОР' in status:
            print(f"\n [LOCAL] Создание карточки надзора для договора {contract_id}...")
            supervision_card_id = self.data.create_supervision_card(contract_id)
            print(f"  [LOCAL] Результат: supervision_card_id = {supervision_card_id}")

        current_month = QDate.currentDate().toString('yyyy-MM')
        self._set_report_month_locally(contract_id, current_month)

    def _set_report_month_locally(self, contract_id, current_month):
        """Установка отчетного месяца локально"""
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
            UPDATE payments
            SET report_month = ?
            WHERE contract_id = ?
              AND (report_month IS NULL OR report_month = '')
            ''', (current_month, contract_id))
            rows_updated = cursor.rowcount
            conn.commit()
            self.db.close()
            print(f"[LOCAL] Установлен отчетный месяц {current_month} для {rows_updated} выплат")
        except Exception as e:
            print(f"[ERROR] Ошибка установки отчетного месяца локально: {e}")
    
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
        self.data = getattr(parent, 'data', None) or DataAccess()
        self.db = self.data.db
        
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
                border: 1px solid #E0E0E0;
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
                background-color: #f5f5f5;
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

        toggle_filters_btn = IconLoader.create_icon_button('arrow-down-circle', '', 'Развернуть фильтры', icon_size=12)
        toggle_filters_btn.setFixedSize(20, 20)
        toggle_filters_btn.setStyleSheet("""
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
            # ИСПРАВЛЕНИЕ 06.02.2026: Добавлена стадия 3д визуализации (#18)
            stages = [
                'Стадия 1: планировочные решения',
                'Стадия 2: рабочие чертежи',
                'Стадия 3: 3д визуализация (Дополнительная)'
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
        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить фильтры', icon_size=12)
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
        self.total_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #ffffff; border-radius: 4px;')
        summary_layout.addWidget(self.total_label)
        
        self.completed_label = QLabel('Выполнено: 0')
        self.completed_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #D5F4E6; border-radius: 4px;')
        summary_layout.addWidget(self.completed_label)
        
        self.in_progress_label = QLabel('В работе: 0')
        self.in_progress_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #FFF3CD; border-radius: 4px;')
        summary_layout.addWidget(self.in_progress_label)
        
        self.overdue_label = QLabel('Просрочено: 0')
        self.overdue_label.setStyleSheet('font-weight: bold; padding: 5px; background-color: #FADBD8; border-radius: 4px;')
        summary_layout.addWidget(self.overdue_label)
        
        summary_layout.addStretch()
        executors_layout.addLayout(summary_layout)
        
        self.stats_table = QTableWidget()
        apply_no_focus_delegate(self.stats_table)
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
        
        excel_btn = IconLoader.create_icon_button('export', 'Экспорт в Excel', icon_size=12)
        # ИСПРАВЛЕНИЕ 06.02.2026: Уменьшен padding для стандартной высоты 28px (#11)
        excel_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #229954; }
        """)
        excel_btn.clicked.connect(self.export_to_excel)
        buttons_layout.addWidget(excel_btn)
        
        pdf_btn = IconLoader.create_icon_button('export', 'Экспорт в PDF', icon_size=12)
        # ИСПРАВЛЕНИЕ 06.02.2026: Уменьшен padding для стандартной высоты 28px (#11)
        pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 4px 12px;
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
        # ИСПРАВЛЕНИЕ 06.02.2026: Уменьшен padding для стандартной высоты 28px (#11)
        close_btn.setStyleSheet('padding: 4px 12px;')
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
            projects = self.data.get_projects_by_type(self.project_type)
            
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
            designers = self.data.get_employees_by_position('Дизайнер')
            draftsmen = self.data.get_employees_by_position('Чертёжник')
            
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
                print(f"[WARN] Атрибут '{attr}' еще не создан, пропускаем загрузку статистики")
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
        
        stats = self.data.get_crm_statistics_filtered(
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
                status_text = f"Завершено {stat.get('completed_date', '')}"
                status_item = QTableWidgetItem(status_text)
            elif is_overdue:
                status_item = QTableWidgetItem('[WARN] Просрочено')
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

                # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех"
                pass
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
                border: 1px solid #E0E0E0;
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
                border: 1px solid #E0E0E0;
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
        
        success_title = QLabel('PDF успешно создан!')
        success_title.setStyleSheet('font-size: 14px; font-weight: bold; color: #27AE60;')
        success_title.setAlignment(Qt.AlignCenter)
        layout.addWidget(success_title)
        
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
                background-color: #ffd93c;
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

        
class ReassignExecutorDialog(QDialog):
    """Диалог переназначения исполнителя БЕЗ перемещения карточки"""

    def __init__(self, parent, card_id, position, stage_keyword, executor_type, current_executor_name, stage_name, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.position = position
        self.stage_keyword = stage_keyword
        self.executor_type = executor_type
        self.stage_name = stage_name
        self.real_stage_name = None  # ИСПРАВЛЕНИЕ 25.01.2026: Реальное имя стадии из БД
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client

        # ИСПРАВЛЕНИЕ 28.01.2026: Получаем реальное имя исполнителя из БД/API
        real_executor_name = self._get_real_executor_name()
        self.current_executor_name = real_executor_name if real_executor_name else current_executor_name

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self.init_ui()

    def _get_real_executor_name(self):
        """Получить реальное имя исполнителя из DataAccess"""
        try:
            card_data = self.data.get_crm_card(self.card_id)
            stage_executors = card_data.get('stage_executors', [])
            for se in stage_executors:
                if self.stage_keyword.lower() in se.get('stage_name', '').lower():
                    executor_id = se.get('executor_id')
                    if executor_id:
                        employees = self.data.get_all_employees()
                        for emp in employees:
                            if emp.get('id') == executor_id:
                                return emp.get('full_name')
        except Exception as e:
            print(f"[WARNING] Ошибка получения имени исполнителя: {e}")

        # Fallback на raw SQL (если DataAccess не вернул результат)
        try:
            conn = self.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
            SELECT e.full_name
            FROM stage_executors se
            JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ? AND se.stage_name LIKE ?
            ORDER BY se.id DESC LIMIT 1
            ''', (self.card_id, f'%{self.stage_keyword}%'))
            record = cursor.fetchone()
            self.db.close()
            return record['full_name'] if record else None
        except Exception as e:
            print(f"[WARNING] Ошибка получения имени исполнителя (raw SQL): {e}")
            return None

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
                border: 1px solid #E0E0E0;
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

        # ========== НОВОЕ: ИСТОРИЯ ПЕРЕНАЗНАЧЕНИЙ ==========
        # Получаем историю переназначений для этой карточки
        try:
            history_records = []

            # Загружаем историю переназначений через DataAccess
            try:
                action_history = self.data.get_action_history('crm_card', self.card_id)
                for ah in action_history:
                    if ah.get('action_type') == 'reassign':
                        description = ah.get('description', '')
                        created_at = ah.get('action_date', '')
                        history_records.append({
                            'description': description,
                            'created_at': created_at
                        })
                print(f"[DataAccess] Загружено записей истории переназначений: {len(history_records)}")
            except Exception as e:
                print(f"[WARN] Ошибка загрузки истории переназначений: {e}")
                history_records = []

            # Также добавляем текущих исполнителей на других стадиях
            current_executors = []
            try:
                card_data = self.data.get_crm_card(self.card_id)
                stage_executors = card_data.get('stage_executors', [])
                employees = self.data.get_all_employees()
                emp_map = {e.get('id'): e.get('full_name', 'Неизвестно') for e in employees}

                for se in stage_executors:
                    emp_id = se.get('executor_id')
                    emp_name = emp_map.get(emp_id, 'Неизвестно')
                    assigned_date = se.get('assigned_date') or se.get('created_at', '')
                    current_executors.append({
                        'stage_name': se.get('stage_name'),
                        'full_name': emp_name,
                        'assigned_date': assigned_date
                    })
            except Exception as e:
                print(f"[WARN] Ошибка загрузки текущих исполнителей: {e}")

            if history_records or current_executors:
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

                # Показываем текущих исполнителей
                if current_executors:
                    executors_title = QLabel("Текущие исполнители:")
                    executors_title.setStyleSheet('font-size: 9px; color: #666; font-style: italic;')
                    history_layout.addWidget(executors_title)

                    for record in current_executors:
                        from datetime import datetime
                        try:
                            date_val = record.get('assigned_date', '')
                            if 'T' in str(date_val):
                                assigned_date = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                            else:
                                assigned_date = datetime.strptime(str(date_val)[:10], '%Y-%m-%d')
                            date_str = assigned_date.strftime('%d-%m-%Y')
                        except Exception:
                            date_str = str(record.get('assigned_date', ''))[:10] if record.get('assigned_date') else '-'

                        exec_item = QLabel(f"  {record['stage_name']}: {record['full_name']} ({date_str})")
                        exec_item.setStyleSheet('font-size: 9px; color: #555;')
                        history_layout.addWidget(exec_item)

                # Показываем историю переназначений
                if history_records:
                    history_title = QLabel("История переназначений:")
                    history_title.setStyleSheet('font-size: 9px; color: #666; font-style: italic; margin-top: 5px;')
                    history_layout.addWidget(history_title)

                    for record in history_records[:5]:
                        from datetime import datetime
                        try:
                            date_val = record.get('created_at', '')
                            if 'T' in str(date_val):
                                created_date = datetime.fromisoformat(date_val.replace('Z', '+00:00'))
                            else:
                                created_date = datetime.strptime(str(date_val)[:19], '%Y-%m-%d %H:%M:%S')
                            date_str = created_date.strftime('%d-%m-%Y')
                        except Exception:
                            date_str = '-'

                        description = record.get('description', '')
                        history_item = QLabel(f"  {date_str}: {description}")
                        history_item.setStyleSheet('font-size: 9px; color: #555;')
                        history_item.setWordWrap(True)
                        history_layout.addWidget(history_item)

                history_frame.setLayout(history_layout)
                layout.addWidget(history_frame)

        except Exception as e:
            print(f"[WARN] Не удалось загрузить историю исполнителей: {e}")
            import traceback
            traceback.print_exc()
        # ==================================================

        form_layout = QFormLayout()

        self.executor_combo = CustomComboBox()

        # ИСПРАВЛЕНИЕ 30.01.2026: Получаем сотрудников включая двойные должности (secondary_position)
        try:
            all_employees = self.data.get_all_employees()
            # Фильтруем по основной ИЛИ дополнительной должности
            executors = [e for e in all_employees
                        if e.get('position') == self.position
                        or e.get('secondary_position') == self.position]
            print(f"[DEBUG] Найдено сотрудников для должности '{self.position}': {len(executors)} (включая secondary_position)")
        except Exception as e:
            print(f"[DataAccess ERROR] Ошибка получения сотрудников: {e}")
            executors = []

        if not executors:
            CustomMessageBox(self, 'Внимание', f'Нет доступных сотрудников с должностью "{self.position}"', 'warning').exec_()
            self.reject()
            return

        # Получаем ID текущего исполнителя для установки в combobox
        current_executor_id = None
        try:
            card_data = self.data.get_crm_card(self.card_id)
            stage_executors = card_data.get('stage_executors', [])
            for se in stage_executors:
                if self.stage_keyword.lower() in se.get('stage_name', '').lower():
                    current_executor_id = se.get('executor_id')
                    # ИСПРАВЛЕНИЕ 25.01.2026: Сохраняем реальное имя стадии из БД
                    self.real_stage_name = se.get('stage_name')
                    break

            if not current_executor_id:
                # Fallback на raw SQL
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                SELECT executor_id, stage_name FROM stage_executors
                WHERE crm_card_id = ? AND stage_name LIKE ?
                ORDER BY id DESC LIMIT 1
                ''', (self.card_id, f'%{self.stage_keyword}%'))
                record = cursor.fetchone()
                if record:
                    current_executor_id = record['executor_id']
                    self.real_stage_name = record['stage_name']
                self.db.close()
        except Exception as e:
            print(f"[WARNING] Не удалось получить ID текущего исполнителя: {e}")

        # Добавляем сотрудников в combobox
        for executor in executors:
            self.executor_combo.addItem(executor['full_name'], executor['id'])

        # Устанавливаем текущего исполнителя
        if current_executor_id:
            for i in range(self.executor_combo.count()):
                if self.executor_combo.itemData(i) == current_executor_id:
                    self.executor_combo.setCurrentIndex(i)
                    break

        form_layout.addRow('Новый исполнитель:', self.executor_combo)
        
        # Поле дедлайна
        self.deadline_edit = CustomDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        self.deadline_edit.setDisplayFormat('dd.MM.yyyy')
        self.deadline_edit.setStyleSheet(CALENDAR_STYLE)

        # Загружаем текущий дедлайн через DataAccess
        try:
            deadline_value = None
            try:
                card_data = self.data.get_crm_card(self.card_id)
                stage_executors = card_data.get('stage_executors', [])
                for se in stage_executors:
                    if self.stage_keyword.lower() in se.get('stage_name', '').lower():
                        deadline_value = se.get('deadline')
                        break
            except Exception as e:
                print(f"[DataAccess] Ошибка получения дедлайна: {e}")

            if not deadline_value:
                # Fallback на raw SQL
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                SELECT deadline FROM stage_executors
                WHERE crm_card_id = ? AND stage_name LIKE ?
                ORDER BY id DESC LIMIT 1
                ''', (self.card_id, f'%{self.stage_keyword}%'))
                record = cursor.fetchone()
                if record and record['deadline']:
                    deadline_value = record['deadline']
                self.db.close()

            if deadline_value:
                self.deadline_edit.setDate(QDate.fromString(str(deadline_value), 'yyyy-MM-dd'))
            else:
                self.deadline_edit.setDate(QDate.currentDate().addDays(7))
        except Exception as e:
            print(f" Не удалось загрузить дедлайн: {e}")
            self.deadline_edit.setDate(QDate.currentDate().addDays(7))
        
        form_layout.addRow('Дедлайн:', self.deadline_edit)
        
        layout.addLayout(form_layout)
        
        hint = QLabel(' Исполнитель будет изменен БЕЗ перемещения карточки')
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

        # Увеличена ширина на 20% для размещения истории переназначений
        self.setMinimumWidth(600)

    def save_reassignment(self):
        """Сохранение нового назначения"""
        new_executor_id = self.executor_combo.currentData()
        new_deadline = self.deadline_edit.date().toString('yyyy-MM-dd')

        if not new_executor_id:
            CustomMessageBox(self, 'Ошибка', 'Выберите исполнителя', 'warning').exec_()
            return

        try:
            # Получаем старого исполнителя ДО обновления (нужно для переназначения оплат)
            old_executor_id = None
            contract_id = None

            try:
                card_data = self.data.get_crm_card(self.card_id)
                if card_data:
                    contract_id = card_data.get('contract_id')
                    stage_name_to_use = self.real_stage_name or self.stage_name
                    stage_executors = card_data.get('stage_executors', [])
                    print(f"[DEBUG] Ищем стадию: stage_name_to_use='{stage_name_to_use}', stage_keyword='{self.stage_keyword}'")
                    print(f"[DEBUG] Доступные stage_executors: {[s.get('stage_name') for s in stage_executors]}")
                    for se in stage_executors:
                        stage_name_in_data = se.get('stage_name', '')
                        if (stage_name_in_data == stage_name_to_use or
                            self.stage_keyword.lower() in stage_name_in_data.lower()):
                            old_executor_id = se.get('executor_id')
                            print(f"[DEBUG] Найден stage_executor '{stage_name_in_data}', executor_id={old_executor_id}")
                            break
                print(f"[DEBUG] Старый исполнитель (DataAccess): {old_executor_id}, contract_id: {contract_id}")
            except Exception as e:
                print(f"[WARN] Не удалось получить старого исполнителя через DataAccess: {e}")

            # Если не получили через DataAccess, пробуем raw SQL
            if old_executor_id is None:
                conn = self.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                SELECT se.executor_id, cc.contract_id
                FROM stage_executors se
                JOIN crm_cards cc ON cc.id = se.crm_card_id
                WHERE se.crm_card_id = ? AND se.stage_name LIKE ?
                ORDER BY se.id DESC LIMIT 1
                ''', (self.card_id, f'%{self.stage_keyword}%'))
                record = cursor.fetchone()
                if record:
                    old_executor_id = record['executor_id']
                    contract_id = record['contract_id']
                self.db.close()
                print(f"[DEBUG] Старый исполнитель (локально): {old_executor_id}, contract_id: {contract_id}")

            # Обновляем исполнителя через DataAccess
            try:
                update_data = {
                    'executor_id': new_executor_id,
                    'deadline': new_deadline,
                    'completed': False
                }
                # ИСПРАВЛЕНИЕ 25.01.2026: Используем real_stage_name из БД, а не stage_name из колонки
                stage_name_to_use = self.real_stage_name or self.stage_name
                print(f"[DEBUG] Переназначение: stage_name_to_use={stage_name_to_use}, real_stage_name={self.real_stage_name}")
                self.data.update_stage_executor(self.card_id, stage_name_to_use, update_data)
                print(f"[DataAccess] Исполнитель переназначен")

                # Переназначение оплат после успешного вызова
                if contract_id and old_executor_id and new_executor_id != old_executor_id:
                    self._reassign_payments_via_api(contract_id, old_executor_id, new_executor_id, stage_name_to_use)
                    # Запись в историю проекта
                    self._add_reassignment_history(old_executor_id, new_executor_id, stage_name_to_use)

                self.accept()
                return
            except Exception as e:
                print(f"[DataAccess ERROR] Ошибка переназначения: {e}")
                import traceback
                traceback.print_exc()
                # Пробуем fallback на raw SQL
                print("[INFO] Пытаемся сохранить локально...")

            # Fallback на локальную БД
            conn = self.db.connect()
            cursor = conn.cursor()

            # Находим старого исполнителя и ID записи stage_executors
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

                print(f"Исполнитель переназначен: executor_id={new_executor_id}, deadline={new_deadline}")

                # Переносим оплату со старого исполнителя на нового
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
                        # Помечаем старую запись как переназначенную
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

                        print(f"Создана новая запись оплаты для исполнителя {new_executor_id}, старая запись помечена как переназначенная")
                    else:
                        print(f" Оплата для старого исполнителя не найдена (возможно, еще не создана)")

                conn.commit()
            else:
                conn.close()
                self.db.close()
                CustomMessageBox(self, 'Ошибка', 'Не найдена запись для переназначения', 'error').exec_()
                return

            self.db.close()

            # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех"
            self.accept()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка переназначения: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось переназначить исполнителя:\n{str(e)}', 'error').exec_()
            try:
                self.db.close()
            except Exception:
                pass

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

    def _check_payment_exists(self, all_payments, contract_id, employee_id, role, stage_name, payment_type):
        """ИСПРАВЛЕНИЕ 01.02.2026: Проверка идемпотентности - существует ли уже такой платеж"""
        for p in all_payments:
            # Пропускаем переназначенные платежи
            if p.get('reassigned'):
                continue
            # Проверяем совпадение ключевых полей
            if (p.get('contract_id') == contract_id and
                p.get('employee_id') == employee_id and
                p.get('role') == role and
                p.get('payment_type') == payment_type):
                # Для stage_name проверяем частичное совпадение
                p_stage = (p.get('stage_name') or '').lower()
                check_stage = (stage_name or '').lower()
                if check_stage in p_stage or p_stage in check_stage or not check_stage:
                    print(f"[IDEMPOTENT] Платеж уже существует: ID={p.get('id')}, {role}/{payment_type}")
                    return p  # Возвращаем существующий платеж
        return None

    def _reassign_payments_via_api(self, contract_id, old_executor_id, new_executor_id, stage_name):
        """Переназначение оплат через API при смене исполнителя"""
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')

            # Определяем роль по должности
            role_map = {
                'Дизайнер': 'Дизайнер',
                'Чертёжник': 'Чертёжник'
            }
            role = role_map.get(self.position, self.position)

            # Получаем все платежи для этого контракта
            try:
                all_payments = self.data.get_payments_for_contract(contract_id)
            except Exception as e:
                print(f"[WARN] Ошибка получения платежей: {e}")
                all_payments = []

            # Ищем ВСЕ платежи для этой стадии, старого исполнителя и роли (Аванс + Доплата)
            old_payments = []
            print(f"[DEBUG] Поиск платежей: stage_keyword='{self.stage_keyword}', stage_name='{stage_name}', role='{role}', old_executor_id={old_executor_id}")
            print(f"[DEBUG] Всего платежей для контракта: {len(all_payments)}")

            for payment in all_payments:
                # ИСПРАВЛЕНИЕ 30.01.2026: Пропускаем уже переназначенные платежи
                # чтобы избежать дублирования при повторном переназначении
                if payment.get('reassigned'):
                    print(f"[DEBUG] Пропускаем уже переназначенный платеж ID={payment.get('id')}")
                    continue

                payment_stage = payment.get('stage_name') or ''  # Защита от None
                payment_role = payment.get('role') or ''  # Защита от None
                payment_employee_id = payment.get('employee_id')

                # Пропускаем платежи без stage_name (например, для ролей без стадии)
                if not payment_stage:
                    continue

                # Проверяем соответствие стадии (используем lower() для регистронезависимого сравнения)
                stage_match = self.stage_keyword.lower() in payment_stage.lower() or stage_name.lower() in payment_stage.lower()
                role_match = payment_role == role
                emp_match = payment_employee_id == old_executor_id

                if stage_match and role_match and emp_match:
                    old_payments.append(payment)
                    print(f"[DEBUG] НАЙДЕН платеж ID={payment.get('id')}, тип={payment.get('payment_type')}")

            print(f"[DEBUG] Найдено платежей для переназначения: {len(old_payments)}")

            if old_payments:
                for old_payment in old_payments:
                    old_payment_id = old_payment.get('id')
                    payment_type = old_payment.get('payment_type', 'Неизвестно')

                    # 1. Помечаем старую запись как переназначенную
                    try:
                        self.data.update_payment(old_payment_id, {
                            'reassigned': True,
                            'report_month': current_month
                        })
                        print(f"[DataAccess] Старый платеж {old_payment_id} ({payment_type}) помечен как переназначенный")
                    except Exception as e:
                        print(f"[WARN] Ошибка обновления старого платежа {old_payment_id}: {e}")

                    # 2. Создаем новую запись для нового исполнителя
                    # ИСПРАВЛЕНИЕ 29.01.2026:
                    # - Аванс: report_month = текущий месяц
                    # - Доплата: report_month = None (статус "В работе", заполнится при приёмке)
                    if payment_type == 'Доплата':
                        new_report_month = None  # "В работе"
                    else:
                        new_report_month = current_month  # Аванс и другие - текущий месяц

                    # ИСПРАВЛЕНИЕ 30.01.2026: Если старая сумма = 0, пересчитываем по тарифам
                    old_calculated = old_payment.get('calculated_amount', 0) or 0
                    old_final = old_payment.get('final_amount', 0) or 0
                    is_manual = old_payment.get('is_manual', 0)
                    manual_amount = old_payment.get('manual_amount')

                    if old_calculated == 0 and old_final == 0 and not is_manual:
                        # Пересчитываем сумму по тарифам
                        print(f"[INFO] Старый платеж имел сумму 0, пересчитываем по тарифам")
                        try:
                            full_amount = 0
                            stage_name_for_calc = old_payment.get('stage_name') or stage_name

                            try:
                                result = self.data.calculate_payment_amount(
                                    contract_id, new_executor_id, role, stage_name_for_calc
                                )
                                full_amount = float(result) if result else 0
                                print(f"[DataAccess] Рассчитанная сумма: {full_amount}")
                            except Exception as e:
                                print(f"[WARN] Ошибка расчёта суммы: {e}")

                            # Аванс и Доплата - по 50%
                            half_amount = full_amount / 2 if full_amount > 0 else 0
                            old_calculated = half_amount
                            old_final = half_amount

                        except Exception as e:
                            print(f"[ERROR] Ошибка пересчёта суммы: {e}")

                    # ИСПРАВЛЕНИЕ 30.01.2026: Новые платежи НЕ должны иметь reassigned=True!
                    # reassigned=True только для СТАРЫХ (заменённых) платежей
                    new_payment_data = {
                        'contract_id': contract_id,
                        'crm_card_id': self.card_id,
                        'supervision_card_id': old_payment.get('supervision_card_id'),
                        'employee_id': new_executor_id,
                        'role': role,
                        'stage_name': old_payment.get('stage_name'),
                        'calculated_amount': old_calculated,
                        'manual_amount': manual_amount,
                        'final_amount': old_final,
                        'is_manual': is_manual,
                        'payment_type': payment_type,
                        'report_month': new_report_month,
                        'reassigned': False,
                        'old_employee_id': old_executor_id
                    }

                    try:
                        # ИСПРАВЛЕНИЕ 01.02.2026: Проверка идемпотентности перед созданием
                        existing = self._check_payment_exists(
                            all_payments, contract_id, new_executor_id, role,
                            old_payment.get('stage_name'), payment_type
                        )
                        if existing:
                            print(f"[IDEMPOTENT] Пропускаем создание - платеж уже существует: ID={existing.get('id')}")
                            continue

                        result = self.data.create_payment(new_payment_data)
                        status_text = f"месяц: {new_report_month}" if new_report_month else "статус: В работе"
                        print(f"[DataAccess] Создан новый платеж ({payment_type}) для исполнителя {new_executor_id}, сумма={old_final:.2f}, {status_text}")
                    except Exception as e:
                        print(f"[WARN] Ошибка создания нового платежа ({payment_type}): {e}")
            else:
                # ИСПРАВЛЕНИЕ 29.01.2026: Если старых платежей нет - создаём новые для нового исполнителя
                print(f"[INFO] Платежи для старого исполнителя не найдены, создаём новые для нового исполнителя")

                # Рассчитываем сумму для новых платежей
                try:
                    full_amount = 0

                    # Расчёт суммы через DataAccess
                    try:
                        print(f"[DEBUG] Вызов calculate_payment_amount: contract_id={contract_id}, employee_id={new_executor_id}, role={role}, stage_name={stage_name}")
                        result = self.data.calculate_payment_amount(contract_id, new_executor_id, role, stage_name)
                        print(f"[DEBUG] Результат calculate_payment_amount: {result}")
                        full_amount = float(result) if result else 0
                    except Exception as e:
                        print(f"[WARN] Ошибка расчёта суммы: {e}")

                    print(f"[DEBUG] Итоговая рассчитанная сумма для {role}: {full_amount}")

                    if full_amount == 0:
                        print(f"[WARN] Тариф для роли '{role}' не найден или равен 0. Проверьте настройки тарифов!")

                    # Создаём Аванс (50%) и Доплату (50%)
                    advance_amount = full_amount / 2
                    balance_amount = full_amount / 2

                    # Создаём Аванс - отчётный месяц = месяц переназначения
                    # ИСПРАВЛЕНИЕ 30.01.2026: reassigned=False для НОВЫХ платежей
                    advance_data = {
                        'contract_id': contract_id,
                        'crm_card_id': self.card_id,
                        'employee_id': new_executor_id,
                        'role': role,
                        'stage_name': stage_name,
                        'calculated_amount': advance_amount,
                        'final_amount': advance_amount,
                        'payment_type': 'Аванс',
                        'report_month': current_month,  # Аванс - месяц переназначения
                        'reassigned': False,
                        'old_employee_id': old_executor_id
                    }

                    try:
                        # ИСПРАВЛЕНИЕ 01.02.2026: Проверка идемпотентности перед созданием Аванса
                        existing_advance = self._check_payment_exists(
                            all_payments, contract_id, new_executor_id, role, stage_name, 'Аванс'
                        )
                        if existing_advance:
                            print(f"[IDEMPOTENT] Пропускаем создание Аванса - уже существует: ID={existing_advance.get('id')}")
                        else:
                            self.data.create_payment(advance_data)
                            print(f"[DataAccess] Создан новый платеж (Аванс) для исполнителя {new_executor_id}: {advance_amount:.2f}, месяц: {current_month}")
                    except Exception as e:
                        print(f"[WARN] Ошибка создания Аванса: {e}")

                    # Создаём Доплату - отчётный месяц ПУСТОЙ (статус "В работе")
                    # Заполнится автоматически при приёмке работы
                    # ИСПРАВЛЕНИЕ 30.01.2026: reassigned=False для НОВЫХ платежей
                    balance_data = {
                        'contract_id': contract_id,
                        'crm_card_id': self.card_id,
                        'employee_id': new_executor_id,
                        'role': role,
                        'stage_name': stage_name,
                        'calculated_amount': balance_amount,
                        'final_amount': balance_amount,
                        'payment_type': 'Доплата',
                        'report_month': None,  # None = "В работе", заполнится при приёмке
                        'reassigned': False,
                        'old_employee_id': old_executor_id
                    }

                    try:
                        # ИСПРАВЛЕНИЕ 01.02.2026: Проверка идемпотентности перед созданием Доплаты
                        existing_balance = self._check_payment_exists(
                            all_payments, contract_id, new_executor_id, role, stage_name, 'Доплата'
                        )
                        if existing_balance:
                            print(f"[IDEMPOTENT] Пропускаем создание Доплаты - уже существует: ID={existing_balance.get('id')}")
                        else:
                            self.data.create_payment(balance_data)
                            print(f"[DataAccess] Создан новый платеж (Доплата) для исполнителя {new_executor_id}: {balance_amount:.2f}, статус: В работе")
                    except Exception as e:
                        print(f"[WARN] Ошибка создания Доплаты через API: {e}")

                except Exception as e:
                    print(f"[ERROR] Ошибка создания новых платежей: {e}")
                    import traceback
                    traceback.print_exc()

        except Exception as e:
            print(f"[ERROR] Ошибка переназначения оплат через API: {e}")
            import traceback
            traceback.print_exc()

    def _add_reassignment_history(self, old_executor_id, new_executor_id, stage_name):
        """Добавление записи в историю проекта о переназначении исполнителя"""
        try:
            # Получаем имена исполнителей через DataAccess
            old_name = "Неизвестно"
            new_name = "Неизвестно"

            try:
                employees = self.data.get_all_employees()
                for emp in employees:
                    if emp.get('id') == old_executor_id:
                        old_name = emp.get('full_name', 'Неизвестно')
                    if emp.get('id') == new_executor_id:
                        new_name = emp.get('full_name', 'Неизвестно')
            except Exception as e:
                print(f"[WARN] Не удалось получить имена сотрудников: {e}")

            # Формируем описание
            description = f"Переназначение стадии '{stage_name}': {old_name} -> {new_name}"

            # Записываем в историю через DataAccess
            try:
                user_data = self.data.get_current_user()
                user_id = user_data.get('id', 1) if user_data else 1

                self.data.add_action_history(
                    user_id=user_id,
                    action_type='reassign',
                    entity_type='crm_card',
                    entity_id=self.card_id,
                    description=description
                )
                print(f"[DataAccess] Записано в историю: {description}")
            except Exception as e:
                print(f"[WARN] Ошибка записи в историю: {e}")

        except Exception as e:
            print(f"[ERROR] Ошибка добавления в историю: {e}")
            import traceback
            traceback.print_exc()


class SurveyDateDialog(QDialog):
    """Диалог установки даты замера"""
    def __init__(self, parent, card_id, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client

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
                border: 1px solid #E0E0E0;
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
        try:
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
                except Exception:
                    self.survey_date.setDate(QDate.currentDate())
            else:
                self.survey_date.setDate(QDate.currentDate())
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки даты замера: {e}")
            self.survey_date.setDate(QDate.currentDate())

        self.survey_date.setDisplayFormat('dd.MM.yyyy')
        from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
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
            self.data.update_crm_card(self.card_id, updates)
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

    def __init__(self, parent, card_id, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client
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
                border: 1px solid #E0E0E0;
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
        # ИСПРАВЛЕНИЕ 07.02.2026: Фиксированная высота 28px как у кнопки (#8)
        self.file_label_display.setFixedHeight(28)
        self.file_label_display.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 4px 12px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                max-width: 300px;
                min-height: 20px;
                max-height: 20px;
            }
            QLabel a {
                color: #ffd93c;
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
        upload_btn.setFixedWidth(130)
        upload_btn.setFixedHeight(28)
        upload_btn.clicked.connect(self.upload_file)
        # ИСПРАВЛЕНИЕ 07.02.2026: Стили по unified_styles (#8, #11, #12)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                border: none;
                padding: 0px 15px;
                border-radius: 6px;
                font-weight: bold;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover {
                background-color: #e6c435;
            }
            QPushButton:pressed {
                background-color: #d4b42e;
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
        from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
        self.tech_task_date.setStyleSheet(CALENDAR_STYLE)
        add_today_button_to_dateedit(self.tech_task_date)
        layout.addWidget(self.tech_task_date)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #f0c929;
            }
            QPushButton:pressed {
                background-color: #e0b919;
            }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
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

        # ИСПРАВЛЕНИЕ 07.02.2026: Увеличен размер диалога (#8)
        self.setMinimumSize(450, 250)
        self.setMaximumSize(600, 350)

    def load_existing_file(self):
        """Загрузка существующего файла ТЗ из договора"""
        # ИСПРАВЛЕНИЕ 07.02.2026: Сбрасываем значение перед загрузкой (#8)
        self.file_label_display.setText('Не загружен')
        self.uploaded_file_link = None

        try:
            # Получаем contract_id из карточки
            card = self.data.get_crm_card(self.card_id)
            if not card or not card.get('contract_id'):
                return

            contract_id = card['contract_id']
            # Получаем tech_task_link и tech_task_file_name из договора
            contract = self.data.get_contract(contract_id)

            if contract and contract.get('tech_task_link'):
                tech_task_link = contract['tech_task_link']
                self.uploaded_file_link = tech_task_link
                # Используем сохраненное имя файла, если оно есть
                file_name = contract.get('tech_task_file_name') or 'ТехЗадание.pdf'
                truncated_name = self.truncate_filename(file_name)
                self.file_label_display.setText(f'<a href="{tech_task_link}" title="{file_name}">{truncated_name}</a>')
        except Exception as e:
            print(f"[WARNING] Ошибка загрузки существующего файла ТЗ: {e}")

    def _get_contract_yandex_folder(self, contract_id):
        """Получение пути к папке договора на Яндекс.Диске"""
        if not contract_id:
            return None

        try:
            contract = self.data.get_contract(contract_id)
            return contract.get('yandex_folder_path') if contract else None
        except Exception as e:
            print(f"[ERROR TechTaskDialog] Ошибка получения пути к папке договора: {e}")
            return None

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

        try:
            # Получаем contract_id из crm_cards
            card = self.data.get_crm_card(self.card_id)
            contract_id = card.get('contract_id') if card else None

            if not contract_id:
                CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
                return

            contract_folder = self._get_contract_yandex_folder(contract_id)

            if not contract_folder:
                CustomMessageBox(
                    self,
                    'Ошибка',
                    'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                    'warning'
                ).exec_()
                return

            file_name = os.path.basename(file_path)

            # ИСПРАВЛЕНИЕ 07.02.2026: Стили для диалога прогресса (#13)
            from PyQt5.QtWidgets import QProgressDialog, QApplication
            progress = QProgressDialog("Загрузка файла ТЗ на Яндекс.Диск...", None, 0, 0, self)
            progress.setWindowTitle("Загрузка")
            progress.setWindowModality(Qt.WindowModal)
            progress.setCancelButton(None)
            progress.setMinimumDuration(0)
            progress.setValue(0)
            progress.setStyleSheet("""
                QProgressDialog {
                    background-color: #FFFFFF;
                    border: 1px solid #E0E0E0;
                    border-radius: 8px;
                }
                QProgressBar {
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    text-align: center;
                    background-color: #F5F5F5;
                }
                QProgressBar::chunk {
                    background-color: #ffd93c;
                    border-radius: 3px;
                }
                QLabel {
                    font-size: 12px;
                    color: #333333;
                }
            """)
            progress.show()
            QApplication.processEvents()

            # Загружаем файл на Яндекс.Диск в фоновом потоке через QThread
            from PyQt5.QtCore import QThread, pyqtSignal

            class UploadThread(QThread):
                finished = pyqtSignal(dict)  # result
                error = pyqtSignal(str)  # error_msg

                def __init__(self, file_path, contract_folder, file_name):
                    super().__init__()
                    self.file_path = file_path
                    self.contract_folder = contract_folder
                    self.file_name = file_name

                def run(self):
                    try:
                        yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                        result = yd.upload_file_to_contract_folder(
                            self.file_path,
                            self.contract_folder,
                            "Анкета",
                            self.file_name
                        )
                        if result:
                            self.finished.emit(result)
                        else:
                            self.error.emit("Не удалось загрузить файл")
                    except Exception as e:
                        import traceback
                        print(f"[ERROR] Ошибка загрузки ТЗ на Яндекс.Диск:")
                        traceback.print_exc()
                        self.error.emit(str(e))

            self.upload_thread = UploadThread(file_path, contract_folder, file_name)

            def on_upload_finished(result):
                progress.close()
                public_link = result.get('public_link')
                yandex_path = result.get('yandex_path')
                file_name_result = result.get('file_name')
                self.tech_task_upload_completed.emit(public_link, yandex_path, file_name_result, contract_id)

            def on_upload_error(error_msg):
                progress.close()
                self.tech_task_upload_error.emit(error_msg)

            self.upload_thread.finished.connect(on_upload_finished)
            self.upload_thread.error.connect(on_upload_error)
            self.upload_thread.start()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка загрузки ТЗ: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось загрузить файл:\n{str(e)}', 'error').exec_()

    def _on_file_uploaded(self, public_link, yandex_path, file_name, contract_id):
        """Обработчик успешной загрузки файла"""
        if not public_link:
            self.file_label_display.setText('Не загружен')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить файл на Яндекс.Диск', 'error').exec_()
            return

        try:
            update_data = {
                'tech_task_link': public_link,
                'tech_task_yandex_path': yandex_path,
                'tech_task_file_name': file_name
            }
            self.data.update_contract(contract_id, update_data)
            print(f"[OK] ТЗ обновлено для договора {contract_id}")

            self.uploaded_file_link = public_link
            truncated_name = self.truncate_filename(file_name)
            self.file_label_display.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            print(f"[SUCCESS] ТЗ успешно загружено: {file_name}")

        except Exception as e:
            print(f"[ERROR] Критическая ошибка сохранения ТЗ: {e}")
            import traceback
            traceback.print_exc()
            self.file_label_display.setText('Не загружен')
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить данные ТЗ:\n{str(e)}', 'error').exec_()

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
            self.data.update_crm_card(self.card_id, updates)
            self.accept()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка сохранения ТЗ: {e}")
            import traceback
            traceback.print_exc()
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

    def __init__(self, parent, card_id, employee=None, api_client=None):
        super().__init__(parent)
        self.card_id = card_id
        self.employee = employee
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = self.data.api_client
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
                border: 1px solid #E0E0E0;
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
        self.file_label_display.setFixedHeight(28)
        self.file_label_display.setStyleSheet('''
            QLabel {
                background-color: #F8F9FA;
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                max-width: 300px;
                max-height: 28px;
                min-height: 28px;
            }
            QLabel a {
                color: #2C3E50;
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
        upload_btn.setFixedHeight(28)  # Выравниваем с полем ввода
        upload_btn.clicked.connect(self.upload_image)
        upload_btn.setStyleSheet('''
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                border: none;
                padding: 0px 12px;
                border-radius: 4px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
            }
        ''')
        file_row.addWidget(upload_btn)

        layout.addLayout(file_row)

        # Замерщик
        surveyor_label = QLabel('Замерщик:')
        layout.addWidget(surveyor_label)

        self.surveyor_combo = CustomComboBox()
        self.surveyor_combo.setFixedHeight(28)
        # Загружаем замерщиков
        surveyors = self.data.get_employees_by_position('Замерщик')
        self.surveyor_combo.addItem('Не назначен', None)
        for surv in surveyors:
            self.surveyor_combo.addItem(surv['full_name'], surv['id'])

        # Блокируем выбор замерщика для самого замерщика
        from ui.crm_tab import _emp_has_pos
        if _emp_has_pos(self.employee, 'Замерщик'):
            self.surveyor_combo.setEnabled(False)

        layout.addWidget(self.surveyor_combo)

        # Дата замера
        date_label = QLabel('Дата замера:')
        layout.addWidget(date_label)

        self.measurement_date = CustomDateEdit()
        self.measurement_date.setCalendarPopup(True)
        self.measurement_date.setDate(QDate.currentDate())
        self.measurement_date.setDisplayFormat('dd.MM.yyyy')
        from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit
        self.measurement_date.setStyleSheet(CALENDAR_STYLE)
        add_today_button_to_dateedit(self.measurement_date)
        layout.addWidget(self.measurement_date)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.clicked.connect(self.save)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                font-weight: bold;
                border-radius: 4px;
                border: none;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #f0c929;
            }
            QPushButton:pressed {
                background-color: #e0b919;
            }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.clicked.connect(self.reject)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                border: none;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
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
        try:
            # Получаем contract_id и surveyor_id из карточки
            card = self.data.get_crm_card(self.card_id)
            if not card or not card.get('contract_id'):
                return

            contract_id = card['contract_id']
            surveyor_id = card.get('surveyor_id')

            # Устанавливаем surveyor_id в ComboBox
            if surveyor_id:
                for i in range(self.surveyor_combo.count()):
                    if self.surveyor_combo.itemData(i) == surveyor_id:
                        self.surveyor_combo.setCurrentIndex(i)
                        break

            # Получаем данные замера из договора
            contract = self.data.get_contract(contract_id)
            if contract:
                if contract.get('measurement_image_link'):
                    measurement_link = contract['measurement_image_link']
                    self.uploaded_image_link = measurement_link
                    file_name = contract.get('measurement_file_name') or 'Замер'
                    truncated_name = self.truncate_filename(file_name)
                    self.file_label_display.setText(f'<a href="{measurement_link}" title="{file_name}">{truncated_name}</a>')

                if contract.get('measurement_date'):
                    measurement_date = QDate.fromString(contract['measurement_date'], 'yyyy-MM-dd')
                    self.measurement_date.setDate(measurement_date)

        except Exception as e:
            print(f"[WARNING] Ошибка загрузки данных замера: {e}")

    def _get_contract_yandex_folder(self, contract_id):
        """Получение пути к папке договора на Яндекс.Диске"""
        if not contract_id:
            return None

        try:
            contract = self.data.get_contract(contract_id)
            return contract.get('yandex_folder_path') if contract else None
        except Exception as e:
            print(f"[ERROR MeasurementDialog] Ошибка получения пути к папке договора: {e}")
            return None

    def upload_image(self):
        """Загрузка изображения замера на Яндекс.Диск"""
        from PyQt5.QtWidgets import QFileDialog, QProgressDialog
        from PyQt5.QtCore import Qt, QThread, pyqtSignal

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите изображение замера",
            "",
            "Image Files (*.png *.jpg *.jpeg *.gif *.bmp)"
        )

        if not file_path:
            return

        try:
            # Получаем contract_id из crm_cards
            card = self.data.get_crm_card(self.card_id)
            contract_id = card.get('contract_id') if card else None

            if not contract_id:
                CustomMessageBox(self, 'Ошибка', 'Договор не найден', 'error').exec_()
                return

            contract_folder = self._get_contract_yandex_folder(contract_id)

            if not contract_folder:
                CustomMessageBox(
                    self,
                    'Ошибка',
                    'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                    'warning'
                ).exec_()
                return

            file_name = os.path.basename(file_path)

            # Создаем прогресс-диалог и сохраняем его как атрибут экземпляра
            self.progress = QProgressDialog("Подготовка к загрузке...", None, 0, 3, self)
            self.progress.setWindowModality(Qt.WindowModal)
            self.progress.setWindowTitle("Загрузка файла")
            self.progress.setMinimumDuration(0)
            self.progress.setAutoClose(False)
            self.progress.setAutoReset(False)
            self.progress.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
            self.progress.setFixedSize(420, 144)
            self.progress.setCancelButton(None)

            self.progress.setStyleSheet("""
                QProgressDialog {
                    background-color: white;
                    border: 1px solid #E0E0E0;
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
                    border: none;
                    border-radius: 4px;
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

            # Используем QThread вместо threading.Thread для совместимости с PyQt
            class UploadThread(QThread):
                finished_signal = pyqtSignal(dict)  # result
                error_signal = pyqtSignal(str)  # error_msg
                progress_signal = pyqtSignal(int, str, str)  # step, filename, phase

                def __init__(self, file_path, contract_folder, file_name, contract_id):
                    super().__init__()
                    self.file_path = file_path
                    self.contract_folder = contract_folder
                    self.file_name = file_name
                    self.contract_id = contract_id

                def run(self):
                    try:
                        yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                        def update_progress(step, fname, phase):
                            self.progress_signal.emit(step, fname, phase)

                        result = yd.upload_file_to_contract_folder(
                            self.file_path,
                            self.contract_folder,
                            "Замер",
                            self.file_name,
                            progress_callback=update_progress
                        )

                        if result:
                            result['contract_id'] = self.contract_id
                            self.finished_signal.emit(result)
                        else:
                            self.error_signal.emit("Не удалось загрузить файл")

                    except Exception as e:
                        import traceback
                        print(f"[ERROR] Ошибка загрузки замера на Яндекс.Диск:")
                        traceback.print_exc()
                        self.error_signal.emit(str(e))

            self.upload_thread = UploadThread(file_path, contract_folder, file_name, contract_id)

            def on_progress_update(step, fname, phase):
                if hasattr(self, 'progress') and self.progress:
                    self.progress.setValue(step)
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    self.progress.setLabelText(f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)")

            def on_upload_finished(result):
                if hasattr(self, 'progress') and self.progress:
                    self.progress.setValue(3)
                public_link = result.get('public_link')
                yandex_path = result.get('yandex_path')
                file_name_result = result.get('file_name')
                contract_id_result = result.get('contract_id')
                self.upload_completed.emit(public_link, yandex_path, file_name_result, contract_id_result)

            def on_upload_error(error_msg):
                self.upload_error.emit(error_msg)

            self.upload_thread.progress_signal.connect(on_progress_update)
            self.upload_thread.finished_signal.connect(on_upload_finished)
            self.upload_thread.error_signal.connect(on_upload_error)
            self.upload_thread.start()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка загрузки замера: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось загрузить файл:\n{str(e)}', 'error').exec_()

    def _on_image_uploaded(self, public_link, yandex_path, file_name, contract_id):
        """Обработчик успешной загрузки изображения"""

        # Закрываем прогресс-диалог
        if hasattr(self, 'progress') and self.progress:
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(0, self.progress.close)
            self.progress = None

        if not public_link:
            self.file_label_display.setText('Не загружено')
            CustomMessageBox(self, 'Ошибка', 'Не удалось загрузить изображение на Яндекс.Диск', 'error').exec_()
            return

        try:
            update_data = {
                'measurement_image_link': public_link,
                'measurement_yandex_path': yandex_path,
                'measurement_file_name': file_name
            }
            self.data.update_contract(contract_id, update_data)
            print(f"[OK] Замер обновлен для договора {contract_id}")

            self.uploaded_image_link = public_link
            truncated_name = self.truncate_filename(file_name)
            self.file_label_display.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            print(f"[SUCCESS] Замер успешно загружен: {file_name}")

            # Обновляем данные в родительском окне
            parent = self.parent()
            if parent and hasattr(parent, 'reload_measurement_data'):
                parent.reload_measurement_data()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка сохранения замера: {e}")
            import traceback
            traceback.print_exc()
            self.file_label_display.setText('Не загружено')
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить данные замера:\n{str(e)}', 'error').exec_()

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
        if not self.uploaded_image_link:
            CustomMessageBox(self, 'Ошибка', 'Сначала загрузите изображение замера', 'warning').exec_()
            return

        measurement_date = self.measurement_date.date().toString('yyyy-MM-dd')
        surveyor_id = self.surveyor_combo.currentData()

        try:
            # Получаем contract_id из карточки
            card = self.data.get_crm_card(self.card_id)
            contract_id = card.get('contract_id') if card else None

            if contract_id:
                # Обновляем дату в contracts
                self.data.update_contract(contract_id, {'measurement_date': measurement_date})
                # Обновляем surveyor_id и survey_date в crm_cards
                self.data.update_crm_card(self.card_id, {
                    'surveyor_id': surveyor_id,
                    'survey_date': measurement_date
                })
                print(f"[OK] Данные замера обновлены")

            # Обновляем данные в родительском окне
            parent = self.parent()

            # Добавляем запись в историю проекта
            if parent and hasattr(parent, 'employee') and parent.employee:
                from datetime import datetime
                user_id = parent.employee.get('id')

                # Получаем имя замерщика
                surveyor_name = ''
                if surveyor_id:
                    try:
                        emps = self.data.get_employees_by_position('Замерщик')
                        for e in emps:
                            if e.get('id') == surveyor_id:
                                surveyor_name = e.get('full_name', '')
                                break
                    except Exception:
                        pass

                date_obj = datetime.strptime(measurement_date, '%Y-%m-%d')
                date_display = date_obj.strftime('%d.%m.%Y')
                description = f"Замер выполнен: {date_display} | Замерщик: {surveyor_name}"

                self.data.add_action_history(
                    user_id=user_id,
                    action_type='survey_complete',
                    entity_type='contract',
                    entity_id=contract_id,
                    description=description
                )

                # Создаём выплату замерщику (если ещё нет)
                if surveyor_id and contract_id:
                    try:
                        report_month = datetime.strptime(measurement_date, '%Y-%m-%d').strftime('%Y-%m')
                        payments = self.data.get_payments_for_contract(contract_id)
                        has_surveyor_payment = any(
                            p.get('employee_id') == surveyor_id and p.get('role') == 'Замерщик'
                            for p in (payments or [])
                        )
                        if not has_surveyor_payment:
                            self.data.create_payment({
                                'contract_id': contract_id,
                                'employee_id': surveyor_id,
                                'role': 'Замерщик',
                                'payment_type': 'Полная оплата',
                                'report_month': report_month,
                                'crm_card_id': self.card_id
                            })
                            print(f"[OK] Выплата замерщику создана: {report_month}")
                    except Exception as e:
                        print(f"[WARNING] Ошибка создания выплаты замерщику: {e}")

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
                except Exception:
                    pass

            self.accept()

        except Exception as e:
            print(f"[ERROR] Критическая ошибка сохранения замера: {e}")
            import traceback
            traceback.print_exc()
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

