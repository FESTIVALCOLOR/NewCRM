from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QDateEdit,
                             QTabWidget, QTextEdit,
                             QTableWidget, QHeaderView, QTableWidgetItem, QGroupBox,
                             QFileDialog, QDoubleSpinBox)
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
from utils.table_settings import ProportionalResizeTable, apply_no_focus_delegate, TableSettings
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
from utils.dialog_helpers import create_progress_dialog
from utils.data_access import DataAccess
from utils.permissions import _has_perm
import os
import threading


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
        self.is_dan_role = not _has_perm(employee, api_client, 'supervision.move')

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

        # Видимость кнопок чата по permissions (после init_ui, когда layout подключён)
        _can_create = _has_perm(self.employee, self.api_client, 'messenger.create_chat')
        _can_view = _has_perm(self.employee, self.api_client, 'messenger.view_chat')
        _can_delete = _has_perm(self.employee, self.api_client, 'messenger.delete_chat')
        self.sv_create_chat_btn.setVisible(_can_create)
        self.sv_open_chat_btn.setVisible(_can_view)
        self.sv_delete_chat_btn.setVisible(_can_delete)
        # Кнопки скриптов: видимы если есть право просмотра чатов
        self.sv_start_script_btn.setVisible(_can_view)
        self.sv_end_script_btn.setVisible(_can_view)

        # Загрузить состояние чата (после layout подключён — нет ghost windows)
        self._sv_chat_data = None
        self._load_supervision_chat_state()

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
            contract = self.data.get_contract(contract_id)
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
            managers = self.data.get_employees_by_position('Старший менеджер проектов') or []
            self.senior_manager.addItem('Не назначен', None)
            for manager in managers:
                self.senior_manager.addItem(manager['full_name'], manager['id'])
            form_layout.addRow('Старший менеджер:', self.senior_manager)

            # ДАН (отображается как текст — изменяется только через кнопку "Переназначить")
            self.dan_label = QLabel('Не назначен')
            self.dan_label.setStyleSheet('font-weight: bold; font-size: 13px; padding: 4px 8px;')
            # Скрытый combo для совместимости (сохранение ID)
            self.dan = CustomComboBox()
            dans = self.data.get_employees_by_position('ДАН') or []
            self.dan.addItem('Не назначен', None)
            for dan in dans:
                self.dan.addItem(dan['full_name'], dan['id'])
            self.dan.setVisible(False)

            dan_row = QHBoxLayout()
            dan_row.addWidget(self.dan_label)

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

            # Руководитель студии
            self.studio_director = CustomComboBox()
            directors = self.data.get_employees_by_position('Руководитель студии') or []
            self.studio_director.addItem('Не назначен', None)
            for director in directors:
                self.studio_director.addItem(director['full_name'], director['id'])
            form_layout.addRow('Руководитель студии:', self.studio_director)

            # ========== НОВОЕ: ПОДКЛЮЧЕНИЕ АВТОМАТИЧЕСКОГО СОЗДАНИЯ ВЫПЛАТ ==========
            # Подключаем обработчики изменения сотрудников для автоматического
            # создания/обновления записей о выплатах
            self.senior_manager.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.senior_manager, 'Старший менеджер проектов')
            )
            # ДАН заблокирован — изменяется только через кнопку "Переназначить"
            # self.dan.currentIndexChanged.connect(
            #     lambda: self.on_employee_changed(self.dan, 'ДАН')
            # )
            # =========================================================================

            # Дата начала надзора
            start_date_row = QHBoxLayout()
            start_date_row.setSpacing(8)

            self.start_date_label = QLabel(QDate.currentDate().toString('dd.MM.yyyy'))
            self.start_date_label.setStyleSheet('font-weight: bold; font-size: 13px; padding: 4px 8px;')
            start_date_row.addWidget(self.start_date_label)
            # Скрытый виджет для совместимости (auto_save_field)
            self.start_date_edit = CustomDateEdit()
            self.start_date_edit.setCalendarPopup(True)
            self.start_date_edit.setDisplayFormat('dd.MM.yyyy')
            self.start_date_edit.setDate(QDate.currentDate())
            self.start_date_edit.setVisible(False)

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

            # Дедлайн (read-only, рассчитывается из таблицы сроков)
            deadline_container = QWidget()
            deadline_layout = QHBoxLayout(deadline_container)
            deadline_layout.setContentsMargins(0, 0, 0, 0)
            self.deadline_label = QLabel('—')
            self.deadline_label.setStyleSheet('font-weight: bold; font-size: 13px; padding: 4px 8px;')
            deadline_layout.addWidget(self.deadline_label)
            deadline_hint = QLabel('(из таблицы сроков, обновляется автоматически)')
            deadline_hint.setStyleSheet('color: #888; font-size: 11px; padding-left: 8px;')
            deadline_layout.addWidget(deadline_hint)
            deadline_layout.addStretch()
            form_layout.addRow('Дедлайн стадии:', deadline_container)
            # Скрытый виджет для совместимости (сохранение)
            self.deadline = CustomDateEdit()
            self.deadline.setCalendarPopup(True)
            self.deadline.setDate(QDate.currentDate())
            self.deadline.setVisible(False)

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
        self.sv_visits_widget = None
        self._timeline_placeholder = QWidget()
        self._timeline_tab_index = self.tabs.addTab(self._timeline_placeholder, 'Таблица сроков')

        self._visits_placeholder = QWidget()
        self._visits_tab_index = self.tabs.addTab(self._visits_placeholder, 'Таблица выездов и дефектов')

        self._payments_placeholder = QWidget()
        self.payments_tab_index = self.tabs.addTab(self._payments_placeholder, 'Оплаты надзора')

        self._info_placeholder = QWidget()
        self.project_info_tab_index = self.tabs.addTab(self._info_placeholder, 'Информация о проекте')

        # Надпись синхронизации
        self.sync_label = QLabel('Синхронизация...')
        self.sync_label.setStyleSheet('color: #999999; font-size: 11px;')
        self.sync_label.setVisible(False)

        self._deferred_tabs_ready = False

        layout.addWidget(self.tabs, 1)

        # Кнопки
        buttons_layout = QHBoxLayout()

        # Кнопка удаления заказа (по праву supervision.delete_order)
        if _has_perm(self.employee, self.api_client, 'supervision.delete_order'):
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

        # --- Кнопки чата (надзор) ---
        self.sv_create_chat_btn = IconLoader.create_icon_button(
            'message-circle', 'Создать чат', 'Создать чат в мессенджере', icon_size=14
        )
        self.sv_create_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c; color: #ffffff;
                padding: 0px 16px; border-radius: 4px; border: 1px solid #e6c236;
                font-weight: bold; max-height: 36px; min-height: 36px;
            }
            QPushButton:hover { background-color: #ffdb4d; border-color: #d9b530; }
            QPushButton:pressed { background-color: #e6c236; }
            QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
        """)
        self.sv_create_chat_btn.setFixedHeight(36)
        self.sv_create_chat_btn.clicked.connect(self._on_create_supervision_chat)

        self.sv_open_chat_btn = IconLoader.create_icon_button(
            'external-link', 'Открыть чат', 'Открыть чат в мессенджере', icon_size=14
        )
        self.sv_open_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #333333;
                padding: 0px 16px; border-radius: 4px; border: 1px solid #d9d9d9;
                font-weight: bold; max-height: 36px; min-height: 36px;
            }
            QPushButton:hover { background-color: #fafafa; border-color: #c0c0c0; }
            QPushButton:pressed { background-color: #f0f0f0; border-color: #b0b0b0; }
            QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
        """)
        self.sv_open_chat_btn.setFixedHeight(36)
        self.sv_open_chat_btn.clicked.connect(self._on_open_supervision_chat)

        self.sv_delete_chat_btn = IconLoader.create_icon_button(
            'trash', 'Удалить чат', 'Удалить чат из мессенджера', icon_size=14
        )
        self.sv_delete_chat_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #F44336;
                padding: 0px 16px; border-radius: 4px; border: 1px solid #F44336;
                font-weight: bold; max-height: 36px; min-height: 36px;
            }
            QPushButton:hover { background-color: #FFF5F5; border-color: #E74C3C; }
            QPushButton:pressed { background-color: #FFEBEE; }
            QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
        """)
        self.sv_delete_chat_btn.setFixedHeight(36)
        self.sv_delete_chat_btn.clicked.connect(self._on_delete_supervision_chat)

        buttons_layout.addWidget(self.sv_create_chat_btn)
        buttons_layout.addWidget(self.sv_open_chat_btn)
        buttons_layout.addWidget(self.sv_delete_chat_btn)

        # --- Кнопки скриптов мессенджера (надзор, иконки без текста) ---
        self.sv_start_script_btn = IconLoader.create_icon_button(
            'play', '', 'Начальный скрипт — отправить в чат', icon_size=16
        )
        self.sv_start_script_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #333333;
                padding: 0px; border-radius: 2px; border: 1px solid #d9d9d9;
                min-width: 36px; max-width: 36px;
                min-height: 36px; max-height: 36px;
            }
            QPushButton:hover { background-color: #fafafa; border-color: #c0c0c0; }
            QPushButton:pressed { background-color: #f0f0f0; border-color: #b0b0b0; }
            QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
        """)
        self.sv_start_script_btn.setFixedSize(36, 36)
        self.sv_start_script_btn.clicked.connect(self._on_send_supervision_start_script)

        self.sv_end_script_btn = IconLoader.create_icon_button(
            'check-circle', '', 'Завершающий скрипт — отправить в чат', icon_size=16
        )
        self.sv_end_script_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffffff; color: #333333;
                padding: 0px; border-radius: 2px; border: 1px solid #d9d9d9;
                min-width: 36px; max-width: 36px;
                min-height: 36px; max-height: 36px;
            }
            QPushButton:hover { background-color: #fafafa; border-color: #c0c0c0; }
            QPushButton:pressed { background-color: #f0f0f0; border-color: #b0b0b0; }
            QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
        """)
        self.sv_end_script_btn.setFixedSize(36, 36)
        self.sv_end_script_btn.clicked.connect(self._on_send_supervision_end_script)

        buttons_layout.addWidget(self.sv_start_script_btn)
        buttons_layout.addWidget(self.sv_end_script_btn)

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
        history = self.data.get_supervision_history(self.card_data['id'])
        
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
            icon_name = None
        elif entry_type == 'resume':
            bg_color = '#ffffff'
            icon_name = 'play'
        elif entry_type == 'submitted':
            bg_color = '#D6EAF8'
            icon_name = None
        elif entry_type == 'accepted':
            bg_color = '#D5F4E6'
            icon_name = None
        else:
            bg_color = '#F8F9FA'
            icon_name = None

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

        header_row = QHBoxLayout()
        header_row.setSpacing(3)
        header_row.setContentsMargins(0, 0, 0, 0)
        if icon_name:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(IconLoader.load(icon_name).pixmap(QSize(9, 9)))
            icon_lbl.setFixedSize(QSize(9, 9))
            header_row.addWidget(icon_lbl)
        header_label = QLabel(f"{created_at} | {created_by}")
        header_label.setStyleSheet('font-size: 9px; font-weight: bold; color: #555;')
        header_row.addWidget(header_label)
        header_row.addStretch()
        header_widget = QWidget()
        header_widget.setLayout(header_row)
        entry_layout.addWidget(header_widget)
        
        # Сообщение
        message_label = QLabel(entry.get('message', ''))
        message_label.setWordWrap(True)
        message_label.setStyleSheet('font-size: 10px; color: #333;')
        entry_layout.addWidget(message_label)
        
        entry_frame.setLayout(entry_layout)
        return entry_frame
    
    def add_history_entry(self):
        """Добавление новой записи в историю"""
        from ui.supervision_dialogs import AddProjectNoteDialog
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
        history = self.data.get_supervision_history(self.card_data['id'])
        
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

    # =========================
    # МЕТОДЫ МЕССЕНДЖЕР-ЧАТА (НАДЗОР)
    # =========================

    def _load_supervision_chat_state(self):
        """Загрузить состояние чата надзора и обновить кнопки"""
        try:
            sv_id = self.card_data.get('id')
            if sv_id and self.data.is_multi_user:
                self._sv_chat_data = self.data.get_supervision_chat(sv_id)
            else:
                self._sv_chat_data = None
        except Exception:
            self._sv_chat_data = None
        self._update_supervision_chat_buttons()

    def _update_supervision_chat_buttons(self):
        """Обновить enabled/disabled кнопок чата надзора"""
        has_chat = (
            self._sv_chat_data is not None
            and self._sv_chat_data.get('chat', {}).get('is_active', False)
        )
        is_online = self.data.is_multi_user

        self.sv_create_chat_btn.setEnabled(not has_chat and is_online)
        self.sv_open_chat_btn.setEnabled(has_chat)
        self.sv_delete_chat_btn.setEnabled(has_chat and is_online)

        # Кнопки скриптов доступны только при наличии чата и подключении к серверу
        if hasattr(self, 'sv_start_script_btn'):
            self.sv_start_script_btn.setEnabled(has_chat and is_online)
            self.sv_end_script_btn.setEnabled(has_chat and is_online)

        if not is_online:
            self.sv_create_chat_btn.setToolTip("Требуется подключение к серверу")
        elif has_chat:
            self.sv_create_chat_btn.setToolTip("Чат уже создан")
        else:
            self.sv_delete_chat_btn.setToolTip("Чат не создан")
            self.sv_open_chat_btn.setToolTip("Чат не создан")

    def _on_create_supervision_chat(self):
        """Создать чат для карточки надзора через диалог выбора мессенджера"""
        from ui.messenger_select_dialog import MessengerSelectDialog
        dialog = MessengerSelectDialog(
            parent=self,
            card_data=self.card_data,
            api_client=self.api_client,
            db=self.data.db,
            data_access=self.data,
            employee=self.employee,
            card_type="supervision",
        )
        if dialog.exec_() == QDialog.Accepted:
            self._sv_chat_data = dialog.result_chat_data
            self._update_supervision_chat_buttons()

    def _on_open_supervision_chat(self):
        """Открыть чат надзора"""
        if not self._sv_chat_data:
            return
        chat = self._sv_chat_data.get('chat', {})
        invite_link = chat.get('invite_link', '')
        if invite_link:
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(invite_link))
        else:
            CustomMessageBox(self, 'Внимание', 'Ссылка на чат не найдена', 'warning').exec_()

    def _on_delete_supervision_chat(self):
        """Удалить чат надзора"""
        if not self._sv_chat_data or not self.data.is_multi_user:
            return
        chat = self._sv_chat_data.get('chat', {})
        chat_id = chat.get('id')
        if not chat_id:
            return

        reply = CustomQuestionBox(
            self, 'Удалить чат',
            f'Вы уверены, что хотите удалить чат?\n\n'
            f'Чат: {chat.get("chat_title", "")}\n\n'
            f'Все участники будут исключены.'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                self.data.delete_messenger_chat(chat_id)
                self._sv_chat_data = None
                self._update_supervision_chat_buttons()
                CustomMessageBox(self, 'Успех', 'Чат удалён', 'success').exec_()
            except Exception as e:
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить чат:\n{str(e)}', 'error').exec_()

    def _on_send_supervision_start_script(self):
        """Отправить начальный скрипт в чат надзора"""
        supervision_card_id = self.card_data.get('id') if self.card_data else None
        if not supervision_card_id:
            return
        try:
            result = self.data.trigger_script(supervision_card_id, 'supervision_start', entity_type='supervision')
            if result:
                CustomMessageBox(self, 'Скрипт', 'Начальный скрипт отправлен в чат', 'success').exec_()
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось отправить скрипт', 'warning').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', str(e), 'error').exec_()

    def _on_send_supervision_end_script(self):
        """Отправить завершающий скрипт в чат надзора"""
        supervision_card_id = self.card_data.get('id') if self.card_data else None
        if not supervision_card_id:
            return
        try:
            result = self.data.trigger_script(supervision_card_id, 'supervision_end', entity_type='supervision')
            if result:
                CustomMessageBox(self, 'Скрипт', 'Завершающий скрипт отправлен в чат', 'success').exec_()
            else:
                CustomMessageBox(self, 'Ошибка', 'Не удалось отправить скрипт', 'warning').exec_()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', str(e), 'error').exec_()

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

                self.data.delete_supervision_order(contract_id, supervision_card_id)

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
            payments = self.data.get_payments_for_supervision(contract_id)

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
                            old_emp = self.data.get_employee(old_emp_id)
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

                # Кнопки действий (столбец 8, по праву supervision.payments)
                if _has_perm(self.employee, self.api_client, 'supervision.payments'):
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
        if not _has_perm(self.employee, self.api_client, 'supervision.payments'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на управление платежами', 'error').exec_()
            return
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
                self.data.delete_payment(payment_id)
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
        """Вспомогательный метод для удаления платежа (через DataAccess)"""
        self.data.delete_payment(payment_id)

    def adjust_payment_amount(self, payment_id):
        """ИСПРАВЛЕНИЕ 30.01.2026: Диалог корректировки с API синхронизацией"""
        if not _has_perm(self.employee, self.api_client, 'supervision.payments'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на управление платежами', 'error').exec_()
            return
        from PyQt5.QtWidgets import QDialog, QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QDoubleSpinBox, QComboBox, QFrame
        from PyQt5.QtCore import Qt, QDate
        from ui.custom_title_bar import CustomTitleBar

        # ИСПРАВЛЕНИЕ: Сначала пробуем API, потом локальную БД
        payment = self.data.get_payment(payment_id)
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
        self.data.update_payment(payment_id, {
            'manual_amount': amount,
            'final_amount': amount,
            'is_manual': True,
            'report_month': report_month,
            'reassigned': False
        })
        print(f"Платёж {payment_id} обновлён")

        # Завершаем сохранение - обновляем UI
        self._finish_save_manual_amount(payment_id, amount, report_month, dialog)

    def _save_payment_locally(self, payment_id, amount, report_month):
        """Вспомогательный метод для сохранения платежа (через DataAccess)"""
        self.data.update_payment_manual(payment_id, amount, report_month=report_month)
        # Сбрасываем reassigned через DataAccess (не raw SQL)
        self.data.update_payment(payment_id, {'reassigned': False})

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
            accepted_history = self.data.execute_raw_query(
                """SELECT created_at, message
                FROM supervision_project_history
                WHERE supervision_card_id = ? AND entry_type = 'accepted'
                ORDER BY created_at ASC""",
                (self.card_data['id'],)
            )

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
        submitted_stages = self.data.get_submitted_stages(self.card_data['id'])

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

        # История ведения проекта с фильтрацией
        history_header_row = QHBoxLayout()
        history_header = QLabel('История ведения проекта')
        history_header.setStyleSheet('font-size: 12px; font-weight: bold;')
        history_header_row.addWidget(history_header)

        # Фильтр по типу события
        filter_label = QLabel('Фильтр:')
        filter_label.setStyleSheet('font-size: 10px; color: #666; margin-left: 20px;')
        history_header_row.addWidget(filter_label)

        from PyQt5.QtWidgets import QComboBox
        self._sv_history_filter = QComboBox()
        self._sv_history_filter.addItems([
            'Все события',
            'Перемещение карточки',
            'Назначение сотрудников',
            'Завершение стадий',
            'Изменение данных',
            'Загрузка файлов',
            'Выезды и дефекты',
            'Прочее',
        ])
        self._sv_history_filter.setStyleSheet('font-size: 10px; padding: 2px 5px;')
        self._sv_history_filter.setFixedWidth(200)
        self._sv_history_filter.currentTextChanged.connect(self._on_sv_history_filter_changed)
        history_header_row.addWidget(self._sv_history_filter)
        history_header_row.addStretch()
        layout.addLayout(history_header_row)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #DDD; border-radius: 4px; background: white; }")

        info_container = QWidget()
        self._sv_history_layout = QVBoxLayout()
        self._sv_history_layout.setSpacing(10)
        self._sv_history_layout.setContentsMargins(10, 10, 10, 10)

        # Журнал всех изменений из supervision_project_history
        self._all_sv_history = self.data.get_supervision_history(self.card_data['id']) or []

        self._render_sv_history(self._all_sv_history)

        info_container.setLayout(self._sv_history_layout)
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

    def _create_history_entry_widget(self, entry):
        """Виджет для одной записи журнала изменений"""
        entry_type = entry.get('entry_type', '')
        message = entry.get('message', '')
        created_at = entry.get('created_at', '')
        created_by_name = entry.get('created_by_name', '')

        # Цвет и иконка по типу события
        type_config = {
            'card_moved': ('#E3F2FD', '#1565C0'),
            'assignment_change': ('#FFF3E0', '#E65100'),
            'stage_completed': ('#E8F5E9', '#2E7D32'),
            'accepted': ('#E8F5E9', '#2E7D32'),
            'pause': ('#FFF9C4', '#F57F17'),
            'resume': ('#E8F5E9', '#388E3C'),
            'auto_resume': ('#E8F5E9', '#388E3C'),
            'data_change': ('#F3E5F5', '#6A1B9A'),
            'file_upload': ('#E0F7FA', '#00695C'),
            'row_added': ('#E8EAF6', '#283593'),
            'row_deleted': ('#FFEBEE', '#B71C1C'),
            'payment_change': ('#FFF3E0', '#BF360C'),
        }
        bg_color, text_color = type_config.get(entry_type, ('#F5F5F5', '#616161'))

        frame = QFrame()
        frame.setStyleSheet(f"""
            QFrame {{
                background-color: {bg_color};
                border: none;
                border-radius: 4px;
                padding: 4px;
            }}
        """)

        frame_layout = QVBoxLayout()
        frame_layout.setSpacing(1)
        frame_layout.setContentsMargins(6, 3, 6, 3)

        # Дата и автор
        date_str = ''
        if created_at:
            try:
                if isinstance(created_at, str):
                    from datetime import datetime
                    dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    date_str = dt.strftime('%d.%m.%Y %H:%M')
                else:
                    date_str = created_at.strftime('%d.%m.%Y %H:%M')
            except Exception:
                date_str = str(created_at)[:16]

        header_parts = []
        if date_str:
            header_parts.append(date_str)
        if created_by_name:
            header_parts.append(created_by_name)
        header_text = ' | '.join(header_parts) if header_parts else ''

        if header_text:
            header_label = QLabel(header_text)
            header_label.setStyleSheet(f'font-size: 9px; color: #888;')
            frame_layout.addWidget(header_label)

        msg_label = QLabel(message)
        msg_label.setStyleSheet(f'font-size: 10px; color: {text_color}; font-weight: bold;')
        msg_label.setWordWrap(True)
        frame_layout.addWidget(msg_label)

        frame.setLayout(frame_layout)
        return frame

    def _render_sv_history(self, entries):
        """Отрисовка записей истории"""
        # Очищаем layout
        while self._sv_history_layout.count():
            child = self._sv_history_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        if entries:
            for entry in entries:
                entry_widget = self._create_history_entry_widget(entry)
                self._sv_history_layout.addWidget(entry_widget)
        else:
            empty_label = QLabel('История проекта пуста')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            self._sv_history_layout.addWidget(empty_label)

        self._sv_history_layout.addStretch()

    def _on_sv_history_filter_changed(self, filter_text):
        """Фильтрация истории надзора по типу события"""
        if not hasattr(self, '_all_sv_history'):
            return

        filter_map = {
            'Перемещение карточки': ['card_moved'],
            'Назначение сотрудников': ['assignment_change'],
            'Завершение стадий': ['stage_completed', 'accepted'],
            'Изменение данных': ['data_change', 'pause', 'resume', 'auto_resume'],
            'Загрузка файлов': ['file_upload'],
            'Выезды и дефекты': ['row_added', 'row_deleted'],
        }

        if filter_text == 'Все события':
            filtered = self._all_sv_history
        elif filter_text == 'Прочее':
            all_known = set()
            for types in filter_map.values():
                all_known.update(types)
            filtered = [e for e in self._all_sv_history if e.get('entry_type', '') not in all_known]
        else:
            allowed_types = filter_map.get(filter_text, [])
            filtered = [e for e in self._all_sv_history if e.get('entry_type', '') in allowed_types]

        self._render_sv_history(filtered)

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
        """Загрузка списка файлов надзора — делегируем в виджеты вкладок"""
        # Загрузить файлы в виджет таблицы сроков
        if self.sv_timeline_widget and hasattr(self.sv_timeline_widget, 'load_files'):
            self.sv_timeline_widget.load_files()
        # Загрузить отчёты в виджет выездов
        if self.sv_visits_widget and hasattr(self.sv_visits_widget, 'load_reports'):
            self.sv_visits_widget.load_reports()
        # Совместимость: если файлы_table ещё существуют (legacy), обновить
        if not hasattr(self, 'files_table'):
            return
        try:
            # Получаем contract_id из card_data
            contract_id = self.card_data.get('contract_id')
            if not contract_id:
                return

            files = []

            # Пробуем загрузить из API
            # Загружаем файлы через DataAccess
            api_files = self.data.get_project_files(contract_id, stage='supervision')
            if not api_files:
                all_files = self.data.get_project_files(contract_id)
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
                if self.data.is_multi_user:
                    try:
                        scan_result = self.data.scan_contract_files(contract_id, scope='supervision')
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

                # Берём файлы через DataAccess
                api_files = self.data.get_project_files(contract_id, stage='supervision')
                if not api_files:
                    all_files = self.data.get_project_files(contract_id)
                    api_files = [f for f in (all_files or [])
                                 if f.get('file_type') == 'Файл надзора' or f.get('stage') == 'supervision']
                if api_files:
                    files = api_files

                if not files:
                    print(f"[VALIDATE-SV] Нет файлов надзора для contract_id={contract_id}")
                    return

                print(f"[VALIDATE-SV] Найдено {len(files)} файлов надзора, проверяем...")

                # Серверная валидация (только если файлы загружены из API — ID серверные)
                removed_ids = []
                server_validated = False
                if self.data.is_multi_user:
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
        if not _has_perm(self.employee, self.api_client, 'supervision.files_upload'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на загрузку файлов', 'error').exec_()
            return
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
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        stages = list(SUPERVISION_STAGE_MAPPING.keys())

        # ИСПРАВЛЕНИЕ 07.02.2026: Открываем кастомный диалог загрузки файла (#23)
        from ui.supervision_dialogs import SupervisionFileUploadDialog
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

        progress = create_progress_dialog('Загрузка на Яндекс.Диск', 'Загрузка файла...', 'Отмена', 100, self)
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

    def upload_supervision_report_file(self):
        """Загрузка файла отчёта (блок «Отчёты» во вкладке выездов)"""
        if not self.yandex_disk:
            CustomMessageBox(self, 'Ошибка', 'Yandex Disk не инициализирован', 'error').exec_()
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            CustomMessageBox(self, 'Ошибка', 'Не найден ID договора', 'error').exec_()
            return

        contract_folder = self._get_contract_yandex_folder(contract_id)
        if not contract_folder:
            CustomMessageBox(self, 'Ошибка', 'Папка договора на Яндекс.Диске не найдена', 'error').exec_()
            return

        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        stages = list(SUPERVISION_STAGE_MAPPING.keys())

        from ui.supervision_dialogs import SupervisionFileUploadDialog
        dialog = SupervisionFileUploadDialog(self, self.card_data, stages, self.api_client, simple_mode=True)
        if dialog.exec_() != QDialog.Accepted:
            return

        result = dialog.get_result()
        if not result:
            return

        file_path = result['file_path']
        stage = result['stage']
        date = result['date']
        file_name = result['file_name']

        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QMetaObject, Q_ARG
        progress = create_progress_dialog('Загрузка на Яндекс.Диск', 'Загрузка файла...', 'Отмена', 100, self)
        QApplication.processEvents()

        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                report_folder = f"{contract_folder}/Авторский надзор/Отчёты/{stage}"
                yd.create_folder(f"{contract_folder}/Авторский надзор")
                yd.create_folder(f"{contract_folder}/Авторский надзор/Отчёты")
                yd.create_folder(report_folder)

                QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 30))

                yandex_path = f"{report_folder}/{file_name}"
                result_upload = yd.upload_file(file_path, yandex_path)

                QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 70))

                if result_upload:
                    public_link = yd.get_public_link(yandex_path)
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 100))
                    QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)

                    # Сохраняем как supervision_reports
                    from PyQt5.QtCore import QTimer
                    def save_report():
                        try:
                            file_data = {
                                'contract_id': contract_id,
                                'stage': 'supervision_reports',
                                'file_type': stage,
                                'yandex_path': yandex_path,
                                'public_link': public_link or '',
                                'file_name': file_name,
                            }
                            self.data.add_project_file(file_data)
                            CustomMessageBox(self, 'Успех', f'Отчёт "{file_name}" успешно загружен', 'success').exec_()
                            self.refresh_files_list()
                        except Exception as e:
                            print(f"[ERROR] Ошибка сохранения отчёта: {e}")
                    QTimer.singleShot(0, save_report)
                else:
                    QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, lambda: CustomMessageBox(
                        self, 'Ошибка', 'Не удалось загрузить файл', 'error').exec_())

            except Exception as e:
                QMetaObject.invokeMethod(progress, "close", Qt.QueuedConnection)
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, lambda: CustomMessageBox(
                    self, 'Ошибка', f'Ошибка загрузки: {e}', 'error').exec_())

        thread = threading.Thread(target=upload_thread, daemon=True)
        thread.start()

    def _on_supervision_upload_completed(self, file_name, stage, date, public_link, yandex_path, contract_id):
        """Обработчик успешной загрузки файла надзора (вызывается из главного потока через сигнал)"""
        try:
            # Сохраняем через DataAccess
            file_data = {
                'contract_id': contract_id,
                'stage': 'supervision',
                'file_type': stage,
                'yandex_path': yandex_path,
                'public_link': public_link or '',
                'file_name': file_name,
            }
            result = self.data.add_project_file(file_data)
            if result:
                print(f"[DataAccess] Файл надзора сохранен, id={result}")
            else:
                print(f"[WARN] Файл сохранен локально, но не синхронизирован с сервером")

            # Обновляем таблицу сроков надзора (бюджет, поставщик, комиссия, примечания)
            extra = getattr(self, '_upload_timeline_data', None)
            if extra:
                from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
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
                self._add_project_history('file_upload', f'Загружен файл: {file_name} (стадия: {stage})')

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
        if not _has_perm(self.employee, self.api_client, 'supervision.files_delete'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на удаление файлов', 'error').exec_()
            return
        reply = CustomQuestionBox(
            self,
            'Подтверждение удаления',
            'Вы уверены, что хотите удалить этот файл?\n\nФайл будет удален с Яндекс.Диска.'
        ).exec_()

        if reply != QDialog.Accepted:
            return

        try:
            # Удаляем файл через DataAccess (удаляет и локально, и через API)
            if self.data.is_multi_user:
                try:
                    self.data.delete_file_record(file_id)
                    print(f"[DataAccess] Файл надзора удален с сервера (БД + ЯД), id={file_id}")
                except Exception as api_err:
                    print(f"[ERROR] Ошибка удаления файла с сервера: {api_err}")
                    CustomMessageBox(self, 'Ошибка', f'Не удалось удалить файл с сервера: {api_err}', 'error').exec_()
                    return
            else:
                # Offline: удаляем локально и с ЯД напрямую
                if self.yandex_disk and yandex_path:
                    self.yandex_disk.delete_file(yandex_path)
                self.data.delete_file_record(file_id)

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
        if contract_id and self.data.is_multi_user:
            self._show_sync_label()
            # Сначала сканируем ЯД на наличие новых файлов (в фоне)
            def scan_thread():
                try:
                    result = self.data.scan_contract_files(contract_id, scope='supervision')
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

        self.data.add_action_history(
            user_id=user_id,
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            description=description
        )
        print(f"[DataAccess] История действий надзора записана: {action_type}")

    def _add_project_history(self, entry_type: str, message: str):
        """Запись в журнал истории проекта надзора"""
        try:
            user_id = self.employee.get('id') if self.employee else None
            self.data.add_supervision_history(
                self.card_data['id'], user_id or 0, entry_type, message
            )
        except Exception as e:
            print(f"[WARN] Ошибка записи истории проекта: {e}")

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
                    self.data.execute_raw_update(
                        'UPDATE project_files SET public_link = ? WHERE id = ?', (public_link, file_id)
                    )
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
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        stage_code = SUPERVISION_STAGE_MAPPING.get(stage_name, '')

        # Загружаем текущие данные из timeline если есть
        current_data = {}
        if stage_code and self.card_data.get('id'):
            try:
                timeline_result = self.data.get_supervision_timeline(self.card_data['id'])
                entries = timeline_result.get('entries', []) if isinstance(timeline_result, dict) else (timeline_result or [])
                for entry in entries:
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
                if hasattr(self, 'dan_label'):
                    self.dan_label.setText(self.dan.itemText(i))
                break

        # Руководитель студии
        for i in range(self.studio_director.count()):
            if self.studio_director.itemData(i) == self.card_data.get('studio_director_id'):
                self.studio_director.setCurrentIndex(i)
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
                if hasattr(self, 'start_date_label'):
                    self.start_date_label.setText(sd.toString('dd.MM.yyyy'))

        # Дедлайн (read-only label + скрытый виджет для совместимости)
        if self.card_data.get('deadline'):
            deadline_str = self.card_data['deadline']
            if 'T' in deadline_str:
                deadline_str = deadline_str.split('T')[0]
            dl = QDate.fromString(deadline_str, 'yyyy-MM-dd')
            if dl.isValid():
                self.deadline.setDate(dl)
                self.deadline_label.setText(dl.toString('dd.MM.yyyy'))
            else:
                self.deadline_label.setText(deadline_str)
        else:
            self.deadline_label.setText('Не установлен')

        # Теги
        self.tags.setText(self.card_data.get('tags', ''))

        self._loading_data = False

    def connect_autosave_signals(self):
        """ИСПРАВЛЕНИЕ: Подключение сигналов для автосохранения данных при изменении"""
        # senior_manager НЕ подключаем здесь — он уже подключен к on_employee_changed
        # который делает update_supervision_card + обновление платежей
        # ДАН заблокирован — auto_save вызывается из reassign_dan → load_data
        self.studio_director.currentIndexChanged.connect(self.auto_save_field)
        # start_date_edit теперь read-only — изменяется только через кнопку "Изменить дату"
        # deadline теперь read-only (рассчитывается из таблицы сроков)
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
                'studio_director_id': self.studio_director.currentData(),
                'start_date': self.start_date_edit.date().toString('yyyy-MM-dd'),
                'deadline': self.deadline.date().toString('yyyy-MM-dd'),
                'tags': self.tags.text().strip()
            }

            self.data.update_supervision_card(self.card_data['id'], updates)

            # Обновляем данные карточки (+ ФИО для виджетов)
            self.card_data.update(updates)
            self.card_data['studio_director_name'] = self.studio_director.currentText() if self.studio_director.currentData() else ''
            self.card_data['senior_manager_name'] = self.senior_manager.currentText() if self.senior_manager.currentData() else ''
            self.card_data['dan_name'] = self.dan.currentText() if self.dan.currentData() else ''

            # Обновляем списки исполнителей и данные в таблицах сроков и выездов
            if hasattr(self, 'sv_timeline_widget') and self.sv_timeline_widget:
                try:
                    self.sv_timeline_widget.card_data = self.card_data
                    self.sv_timeline_widget._executor_names = self.sv_timeline_widget._get_executor_names()
                    self.sv_timeline_widget._load_data()
                except Exception:
                    pass
            if hasattr(self, 'sv_visits_widget') and self.sv_visits_widget:
                try:
                    self.sv_visits_widget.card_data = self.card_data
                    self.sv_visits_widget._executor_names = self.sv_visits_widget._get_executor_names()
                    self.sv_visits_widget._load_data()
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
            'studio_director_id': self.studio_director.currentData(),
            'start_date': self.start_date_edit.date().toString('yyyy-MM-dd'),
            'deadline': self.deadline.date().toString('yyyy-MM-dd'),
            'tags': self.tags.text().strip()
        }

        self.data.update_supervision_card(self.card_data['id'], updates)
        print("[DataAccess] Изменения карточки надзора сохранены")

        # ИСПРАВЛЕНИЕ: Обновляем вкладки после сохранения
        self.refresh_payments_tab()
        self.refresh_project_info_tab()

        # Обновляем родительскую вкладку
        from ui.crm_supervision_tab import CRMSupervisionTab
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMSupervisionTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()

        # ИСПРАВЛЕНИЕ: Закрываем диалог без показа сообщения
        self.accept()

    def _on_start_date_manual_change(self):
        """Изменение даты начала вручную — открыть календарь для выбора"""
        from ui.supervision_dialogs import SupervisionStartDateDialog
        dlg = SupervisionStartDateDialog(
            self,
            current_date=self.start_date_edit.date(),
            data=self.data
        )
        if dlg.exec_() == QDialog.Accepted:
            old_date = self.start_date_edit.date().toString('dd.MM.yyyy')
            new_date = dlg.selected_date.toString('dd.MM.yyyy')
            self._loading_data = True
            self.start_date_edit.setDate(dlg.selected_date)
            self._loading_data = False
            self.start_date_label.setText(dlg.selected_date.toString('dd.MM.yyyy'))
            self.auto_save_field()
            self._add_project_history(
                'data_change',
                f'Дата начала изменена: {old_date} -> {new_date}'
            )

    def _pause_from_edit_tab(self):
        """Приостановка карточки из вкладки редактирования"""
        from ui.supervision_dialogs import PauseDialog
        dialog = PauseDialog(self, api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            reason = dialog.reason_text.toPlainText().strip()
            if reason:
                try:
                    self.data.pause_supervision_card(
                        self.card_data['id'],
                        reason
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
        from ui.custom_message_box import CustomQuestionBox
        reply = CustomQuestionBox(
            self, 'Подтверждение',
            'Возобновить работу над проектом?\nДедлайн будет продлён на время приостановки.'
        )
        if reply.exec_() != QDialog.Accepted:
            return
        if True:
            try:
                # Сервер сам сдвигает deadline и plan_dates на рабочие дни паузы
                self.data.resume_supervision_card(
                    self.card_data['id'],
                    self.employee['id']
                )

                # Получаем обновлённые данные с сервера (дедлайн уже сдвинут)
                updated = self.data.get_supervision_card(self.card_data['id'])
                if updated and isinstance(updated, dict):
                    new_deadline = updated.get('deadline', '')
                    if new_deadline:
                        if 'T' in new_deadline:
                            new_deadline = new_deadline.split('T')[0]
                        self.card_data['deadline'] = new_deadline
                        self._loading_data = True
                        dl = QDate.fromString(new_deadline, 'yyyy-MM-dd')
                        self.deadline.setDate(dl)
                        if hasattr(self, 'deadline_label'):
                            self.deadline_label.setText(dl.toString('dd.MM.yyyy'))
                        self._loading_data = False

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
        from ui.crm_supervision_tab import CRMSupervisionTab
        parent = self.parent()
        while parent:
            if isinstance(parent, CRMSupervisionTab):
                parent.refresh_current_tab()
                break
            parent = parent.parent()

    def reassign_dan(self):
        """Переназначить исполнителя ДАН"""
        from ui.supervision_dialogs import SupervisionReassignDANDialog
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
            'ДАН': 'dan_id',
            'Руководитель студии': 'studio_director_id'
        }

        field_name = role_to_field.get(role_name)
        if field_name:
            updates = {field_name: employee_id}
            self.data.update_supervision_card(self.card_data['id'], updates)
            # Запись в историю проекта
            emp_name = combo_box.currentText() if employee_id else 'Не назначен'
            self._add_project_history(
                'assignment_change',
                f'{role_name} назначен: {emp_name}'
            )
            print(f"[DataAccess] Обновлено поле {field_name} в карточке авторского надзора")

        try:
            # ИСПРАВЛЕНИЕ: Удаляем оплаты через API если доступно
            payments_to_delete = self.data.get_payments_by_supervision_card(self.card_data['id'])
            deleted_count = 0
            for payment in (payments_to_delete or []):
                if payment.get('role') == role_name:
                    self.data.delete_payment(payment['id'])
                    deleted_count += 1
            if deleted_count > 0:
                print(f"[DataAccess] Удалено {deleted_count} старых оплат надзора для роли {role_name}")

            # ИСПРАВЛЕНО 06.02.2026: Создаем платеж при назначении исполнителя (как в CRM)
            if employee_id:
                # Проверяем, нет ли уже платежа для этой роли
                all_existing = self.data.get_payments_by_supervision_card(self.card_data['id'])
                existing_payments = [p for p in (all_existing or []) if p.get('role') == role_name and not p.get('reassigned')]

                if existing_payments:
                    print(f"[INFO] Платеж для роли {role_name} уже существует, пропускаем создание")
                else:
                    # Рассчитываем сумму через DataAccess
                    calculated_amount = 0
                    try:
                        result = self.data.calculate_payment_amount(
                            contract_id, employee_id, role_name,
                            stage_name=None, supervision_card_id=self.card_data['id']
                        )
                        calculated_amount = float(result) if result else 0
                        print(f"[DataAccess] Рассчитана сумма для {role_name}: {calculated_amount:.2f} руб")
                    except Exception as e:
                        print(f"[WARN] Ошибка расчета суммы: {e}")

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

                    self.data.create_payment(payment_data)
                    print(f"[DataAccess] Создан платеж для {role_name}: {calculated_amount:.2f} руб")
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
        """Вспомогательный метод для удаления платежей (через DataAccess API)"""
        try:
            payments = self.data.get_payments_by_supervision_card(self.card_data['id']) or []
            deleted_count = 0
            for p in payments:
                if p.get('role') == role_name:
                    self.data.delete_payment(p['id'])
                    deleted_count += 1
            if deleted_count > 0:
                print(f"[DataAccess] Удалено {deleted_count} старых оплат надзора для роли {role_name}")
        except Exception as e:
            print(f"[ERROR] Ошибка удаления платежей: {e}")

    def _create_payment_locally(self, payment_data):
        """Вспомогательный метод для создания платежа (через DataAccess)"""
        try:
            self.data.create_payment(payment_data)
            print(f"[DataAccess] Создан платеж для {payment_data.get('role')}: {payment_data.get('final_amount', 0):.2f} руб")
        except Exception as e:
            print(f"[ERROR] Ошибка создания платежа: {e}")
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
                db=self.data.db,
                api_client=self.data.api_client,
                employee=self.employee,
                parent=self
            )
            self.tabs.removeTab(self._timeline_tab_index)
            self.tabs.insertTab(self._timeline_tab_index, self.sv_timeline_widget, 'Таблица сроков')
            # Загрузить файлы в блок файлов timeline widget
            if hasattr(self.sv_timeline_widget, 'load_files'):
                self.sv_timeline_widget.load_files()
        except Exception as e:
            print(f"[SupervisionCardEditDialog] Ошибка создания таблицы сроков: {e}")

        # Таблица выездов и дефектов
        try:
            from ui.supervision_visits_widget import SupervisionVisitsWidget
            self.sv_visits_widget = SupervisionVisitsWidget(
                card_data=self.card_data,
                data=self.data,
                db=self.data.db,
                api_client=self.data.api_client,
                employee=self.employee,
                parent=self
            )
            self.tabs.removeTab(self._visits_tab_index)
            self.tabs.insertTab(self._visits_tab_index, self.sv_visits_widget, 'Таблица выездов и дефектов')
        except Exception as e:
            print(f"[SupervisionCardEditDialog] Ошибка создания таблицы выездов: {e}")

        # Оплаты надзора
        payments_widget = self.create_payments_widget()
        self.tabs.removeTab(self.payments_tab_index)
        self.tabs.insertTab(self.payments_tab_index, payments_widget, 'Оплаты надзора')

        # Информация о проекте
        info_widget = self.create_project_info_widget()
        self.tabs.removeTab(self.project_info_tab_index)
        self.tabs.insertTab(self.project_info_tab_index, info_widget, 'Информация о проекте')

        # Восстановить текущую вкладку
        self.tabs.setCurrentIndex(current_tab)

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

