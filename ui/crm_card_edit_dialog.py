# -*- coding: utf-8 -*-
# CardEditDialog - выделен из ui/crm_tab.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QMessageBox, QDateEdit,
                             QListWidget, QListWidgetItem, QTabWidget, QTextEdit,
                             QGroupBox, QSpinBox, QTableWidget, QHeaderView,
                             QTableWidgetItem, QDoubleSpinBox)
from ui.custom_dateedit import CustomDateEdit
from PyQt5.QtCore import Qt, QMimeData, QDate, pyqtSignal, QSize, QUrl, QTimer, QEvent
from PyQt5.QtGui import QDrag, QPixmap, QColor, QCursor
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import (QTextDocument, QTextCursor, QTextTableFormat,
                         QTextCharFormat, QFont, QBrush,
                         QTextBlockFormat, QTextLength, QTextImageFormat)
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_combobox import CustomComboBox
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from utils.calendar_helpers import CALENDAR_STYLE, add_today_button_to_dateedit, ICONS_PATH
from utils.tab_helpers import disable_wheel_on_tabwidget
from utils.table_settings import ProportionalResizeTable, apply_no_focus_delegate, TableSettings
from utils.date_utils import format_date, format_month_year
from utils.yandex_disk import YandexDiskManager
from config import YANDEX_DISK_TOKEN
from utils.resource_path import resource_path
from utils.dialog_helpers import create_progress_dialog
from functools import partial
import json
import os
import threading

# Импорт helper-функций прав доступа
# ПРИМЕЧАНИЕ: CRMTab, TechTaskDialog, MeasurementDialog, ReassignExecutorDialog,
# PreviewLoaderThread импортируются lazy (внутри методов) для избежания циклических импортов
from utils.permissions import (_emp_has_pos, _emp_only_pos, _has_perm,
                               _load_user_permissions)


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

    # Сигнал для обновления превью в UI (thread-safe)
    preview_loaded = pyqtSignal(int, object)  # file_id, QPixmap
    stage_upload_error = pyqtSignal(str)  # error_msg - ошибка загрузки
    _reload_stage_files_signal = pyqtSignal()  # потокобезопасный сигнал для перезагрузки файлов стадий
    _sync_ended = pyqtSignal()  # Сигнал завершения фоновой синхронизации

    def __init__(self, parent, card_data, view_only=False, employee=None, api_client=None):
        super().__init__(parent)
        self.card_data = card_data
        self.view_only = view_only
        self.employee = employee
        self._loading_data = False  # Флаг для предотвращения автосохранения при загрузке

        # API клиент - принимаем напрямую или ищем через иерархию виджетов
        self.api_client = api_client
        self.parent_tab = None
        if self.api_client is None:
            widget = parent
            while widget:
                if hasattr(widget, 'api_client'):
                    self.api_client = widget.api_client
                    self.parent_tab = widget
                    break
                widget = widget.parent() if hasattr(widget, 'parent') and callable(widget.parent) else None
        else:
            # Ищем parent_tab для refresh_current_tab
            widget = parent
            while widget:
                if hasattr(widget, 'refresh_current_tab'):
                    self.parent_tab = widget
                    break
                widget = widget.parent() if hasattr(widget, 'parent') and callable(widget.parent) else None

        # DataAccess - ищем у родителя или создаем новый
        self.data = getattr(self.parent_tab, 'data', None)
        if self.data is None:
            self.data = DataAccess(api_client=self.api_client)
        self.db = self.data.db

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

        # Подключаем сигнал для потокобезопасной перезагрузки файлов стадий
        self._reload_stage_files_signal.connect(self._reload_all_stage_files)

        # Синхронизация
        self._active_sync_count = 0
        self._sync_ended.connect(self._on_sync_ended)

        # Подключаем сигнал для фоновой загрузки превью
        self.preview_loaded.connect(self._on_preview_loaded)
        self._preview_loader_thread = None  # Поток загрузки превью
        self._preview_widgets_map = {}  # file_id -> FilePreviewWidget

        self.init_ui()
        # load_data() вызывается отложенно в _init_deferred_tabs() после showEvent

        # Устанавливаем event filter для перехвата событий мыши от дочерних виджетов
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().installEventFilter(self)

        # Фоновая загрузка превью запустится после load_data в _init_deferred_tabs


    def _get_contract_yandex_folder(self, contract_id):
        """Получение пути к папке договора на Яндекс.Диске"""
        if not contract_id:
            return None

        try:
            contract = self.data.get_contract(contract_id)
            return contract.get('yandex_folder_path') if contract else None
        except Exception as e:
            print(f"[ERROR CardEditDialog] Ошибка получения пути к папке договора: {e}")
            return None

    def _add_action_history(self, action_type: str, description: str, entity_type: str = 'crm_card', entity_id: int = None):
        """Вспомогательный метод для добавления записи в историю действий через API или локальную БД"""
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
        print(f"История действий записана: {action_type}")


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
                border: 1px solid #E0E0E0;
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
        self.tabs.setStyleSheet("""
            QTabWidget::tab-bar {
                left: 20px;
            }
        """)

        # === ПРОВЕРКА ПРАВ ДОСТУПА (через permissions) ===
        is_executor = not _has_perm(self.employee, self.api_client, 'crm_cards.move')
        has_full_access = _has_perm(self.employee, self.api_client, 'crm_cards.assign_executor')
        has_admin_access = _has_perm(self.employee, self.api_client, 'employees.update')
        has_deadlines_access = _has_perm(self.employee, self.api_client, 'crm_cards.deadlines')
        has_move_access = _has_perm(self.employee, self.api_client, 'crm_cards.move')
        is_sdp_or_gap = not has_full_access and not is_executor

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
            project_info_layout.setSpacing(8)

            # Стиль для меток и значений
            LABEL_STYLE = 'font-weight: bold; color: #555; min-width: 120px;'
            VALUE_STYLE = '''
                QLabel {
                    background-color: #F8F9FA;
                    padding: 4px 8px;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    font-size: 11px;
                }
            '''

            # Договор
            contract_row = QHBoxLayout()
            contract_row.setSpacing(8)
            contract_lbl = QLabel('Договор:')
            contract_lbl.setStyleSheet(LABEL_STYLE)
            contract_lbl.setFixedWidth(120)
            contract_row.addWidget(contract_lbl)
            contract_val = QLabel(str(self.card_data.get('contract_number', 'N/A')))
            contract_val.setStyleSheet(VALUE_STYLE)
            contract_row.addWidget(contract_val, 1)
            project_info_layout.addLayout(contract_row)

            # Адрес
            address_row = QHBoxLayout()
            address_row.setSpacing(8)
            address_lbl = QLabel('Адрес:')
            address_lbl.setStyleSheet(LABEL_STYLE)
            address_lbl.setFixedWidth(120)
            address_row.addWidget(address_lbl)
            address_val = QLabel(str(self.card_data.get('address', 'N/A')))
            address_val.setStyleSheet(VALUE_STYLE)
            address_row.addWidget(address_val, 1)
            project_info_layout.addLayout(address_row)

            # Площадь
            area_row = QHBoxLayout()
            area_row.setSpacing(8)
            area_lbl = QLabel('Площадь:')
            area_lbl.setStyleSheet(LABEL_STYLE)
            area_lbl.setFixedWidth(120)
            area_row.addWidget(area_lbl)
            area_val = QLabel(f"{self.card_data.get('area', 'N/A')} м2")
            area_val.setStyleSheet(VALUE_STYLE)
            area_row.addWidget(area_val, 1)
            project_info_layout.addLayout(area_row)

            # Город
            city_row = QHBoxLayout()
            city_row.setSpacing(8)
            city_lbl = QLabel('Город:')
            city_lbl.setStyleSheet(LABEL_STYLE)
            city_lbl.setFixedWidth(120)
            city_row.addWidget(city_lbl)
            city_val = QLabel(str(self.card_data.get('city', 'N/A')))
            city_val.setStyleSheet(VALUE_STYLE)
            city_row.addWidget(city_val, 1)
            project_info_layout.addLayout(city_row)

            # Тип агента
            agent_row = QHBoxLayout()
            agent_row.setSpacing(8)
            agent_lbl = QLabel('Тип агента:')
            agent_lbl.setStyleSheet(LABEL_STYLE)
            agent_lbl.setFixedWidth(120)
            agent_row.addWidget(agent_lbl)
            agent_val = QLabel(str(self.card_data.get('agent_type', 'N/A')))
            agent_val.setStyleSheet(VALUE_STYLE)
            agent_row.addWidget(agent_val, 1)
            project_info_layout.addLayout(agent_row)

            # Подтип проекта
            subtype_val = self.card_data.get('project_subtype') or ''
            subtype_row = QHBoxLayout()
            subtype_row.setSpacing(8)
            subtype_lbl = QLabel('Подтип проекта:')
            subtype_lbl.setStyleSheet(LABEL_STYLE)
            subtype_lbl.setFixedWidth(120)
            subtype_row.addWidget(subtype_lbl)
            self.subtype_val_label = QLabel(str(subtype_val) if subtype_val else 'Не указан')
            self.subtype_val_label.setStyleSheet(VALUE_STYLE)
            subtype_row.addWidget(self.subtype_val_label, 1)
            project_info_layout.addLayout(subtype_row)

            # Разделитель
            separator = QFrame()
            separator.setFrameShape(QFrame.HLine)
            separator.setStyleSheet('background-color: #E0E0E0; max-height: 1px; margin: 5px 0;')
            project_info_layout.addWidget(separator)

            # Дедлайн проекта (статичное поле + кнопка изменения)
            deadline_row = QHBoxLayout()
            deadline_row.setSpacing(8)
            deadline_label = QLabel('Дедлайн проекта:')
            deadline_label.setStyleSheet(LABEL_STYLE)
            deadline_label.setFixedWidth(120)
            deadline_row.addWidget(deadline_label)

            self.deadline_display = QLabel('Не установлен')
            self.deadline_display.setStyleSheet('''
                QLabel {
                    background-color: #F8F9FA;
                    padding: 6px 10px;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    font-size: 11px;
                }
            ''')
            self.deadline_display.setFixedHeight(28)
            deadline_row.addWidget(self.deadline_display, 1)

            # Кнопка "Изменить дедлайн" (по праву crm_cards.deadlines)
            edit_deadline_btn = None
            if has_deadlines_access:
                edit_deadline_btn = QPushButton('Изменить дедлайн')
                edit_deadline_btn.setFixedHeight(28)
                edit_deadline_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E0E0E0;
                        color: #333333;
                        padding: 0px 12px;
                        border-radius: 4px;
                        border: none;
                        font-weight: bold;
                        max-height: 28px;
                        min-height: 28px;
                    }
                    QPushButton:hover { background-color: #D0D0D0; }
                    QPushButton:pressed { background-color: #C0C0C0; }
                """)
                edit_deadline_btn.clicked.connect(self.change_project_deadline)
                deadline_row.addWidget(edit_deadline_btn)

            project_info_layout.addLayout(deadline_row)

            # Теги
            tags_row = QHBoxLayout()
            tags_row.setSpacing(8)
            tags_label = QLabel('Теги:')
            tags_label.setStyleSheet(LABEL_STYLE)
            tags_label.setFixedWidth(120)
            tags_row.addWidget(tags_label)

            self.tags = QLineEdit()
            self.tags.setPlaceholderText('Срочный, VIP, Проблемный...')
            self.tags.setFixedHeight(28)
            # Теги могут редактировать все (СДП/ГАП тоже)
            tags_row.addWidget(self.tags, 1)
            project_info_layout.addLayout(tags_row)

            # Статус проекта
            status_row = QHBoxLayout()
            status_row.setSpacing(8)
            status_label = QLabel('Статус проекта:')
            status_label.setStyleSheet(LABEL_STYLE)
            status_label.setFixedWidth(120)
            status_row.addWidget(status_label)

            self.status_combo = CustomComboBox()
            self.status_combo.addItems(['Новый заказ', 'В работе', 'СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
            self.status_combo.setFixedHeight(28)
            self.status_combo.setEnabled(has_move_access)  # По праву crm_cards.move
            status_row.addWidget(self.status_combo, 1)
            project_info_layout.addLayout(status_row)

            project_info_group.setLayout(project_info_layout)
            edit_layout.addWidget(project_info_group)

            # ========== БЛОК 2: КОМАНДА ПРОЕКТА ==========
            team_group = QGroupBox("Команда проекта")
            team_group.setStyleSheet(GROUP_BOX_STYLE)
            team_layout = QVBoxLayout()
            team_layout.setSpacing(8)

            # Подзаголовок: Руководство проекта
            leadership_label = QLabel('<b>Руководство проекта:</b>')
            leadership_label.setStyleSheet('color: #2C3E50; font-size: 11px; margin-top: 5px;')
            team_layout.addWidget(leadership_label)

            # Старший менеджер
            senior_mgr_row = QHBoxLayout()
            senior_mgr_row.setSpacing(8)
            senior_mgr_label = QLabel('Старший менеджер:')
            senior_mgr_label.setStyleSheet(LABEL_STYLE)
            senior_mgr_label.setFixedWidth(120)
            senior_mgr_row.addWidget(senior_mgr_label)

            # Один запрос на всех сотрудников вместо 5 отдельных (быстрее ~5x)
            all_employees = self.data.get_all_employees()
            def _emps_by_pos(pos):
                return [e for e in all_employees if e.get('position') == pos or e.get('secondary_position') == pos]

            self.senior_manager = CustomComboBox()
            self.senior_manager.setFixedHeight(28)
            self.senior_manager.setEnabled(has_admin_access)
            self.senior_manager.addItem('Не назначен', None)
            for manager in _emps_by_pos('Старший менеджер проектов'):
                self.senior_manager.addItem(manager['full_name'], manager['id'])
            senior_mgr_row.addWidget(self.senior_manager, 1)
            team_layout.addLayout(senior_mgr_row)

            # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
            project_type = self.card_data.get('project_type', '')
            if project_type == 'Индивидуальный':
                # СДП
                sdp_row = QHBoxLayout()
                sdp_row.setSpacing(8)
                sdp_label = QLabel('СДП:')
                sdp_label.setStyleSheet(LABEL_STYLE)
                sdp_label.setFixedWidth(120)
                sdp_row.addWidget(sdp_label)

                self.sdp = CustomComboBox()
                self.sdp.setFixedHeight(28)
                self.sdp.setEnabled(has_admin_access)
                self.sdp.addItem('Не назначен', None)
                for sdp in _emps_by_pos('СДП'):
                    self.sdp.addItem(sdp['full_name'], sdp['id'])
                sdp_row.addWidget(self.sdp, 1)
                team_layout.addLayout(sdp_row)
            else:
                self.sdp = None  # Для шаблонных проектов СДП не нужен

            # ГАП
            gap_row = QHBoxLayout()
            gap_row.setSpacing(8)
            gap_label = QLabel('ГАП:')
            gap_label.setStyleSheet(LABEL_STYLE)
            gap_label.setFixedWidth(120)
            gap_row.addWidget(gap_label)

            self.gap = CustomComboBox()
            self.gap.setFixedHeight(28)
            self.gap.setEnabled(has_admin_access)
            self.gap.addItem('Не назначен', None)
            for gap in _emps_by_pos('ГАП'):
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
            manager_label.setStyleSheet(LABEL_STYLE)
            manager_label.setFixedWidth(120)
            manager_row.addWidget(manager_label)

            self.manager = CustomComboBox()
            self.manager.setFixedHeight(28)
            self.manager.setEnabled(has_admin_access)
            self.manager.addItem('Не назначен', None)
            for mgr in _emps_by_pos('Менеджер'):
                self.manager.addItem(mgr['full_name'], mgr['id'])
            manager_row.addWidget(self.manager, 1)
            team_layout.addLayout(manager_row)

            # Замерщик
            surveyor_row = QHBoxLayout()
            surveyor_row.setSpacing(8)
            surveyor_label = QLabel('Замерщик:')
            surveyor_label.setStyleSheet(LABEL_STYLE)
            surveyor_label.setFixedWidth(120)
            surveyor_row.addWidget(surveyor_label)

            self.surveyor = CustomComboBox()
            self.surveyor.setFixedHeight(28)
            self.surveyor.setEnabled(has_admin_access)
            self.surveyor.addItem('Не назначен', None)
            for surv in _emps_by_pos('Замерщик'):
                self.surveyor.addItem(surv['full_name'], surv['id'])
            surveyor_row.addWidget(self.surveyor, 1)

            team_layout.addLayout(surveyor_row)

            # Дата замера (статичная информация + кнопка изменить)
            survey_date_row = QHBoxLayout()
            survey_date_row.setSpacing(8)
            survey_date_label_text = QLabel('Дата замера:')
            survey_date_label_text.setStyleSheet(LABEL_STYLE)
            survey_date_label_text.setFixedWidth(120)
            survey_date_row.addWidget(survey_date_label_text)

            self.survey_date_label = QLabel('Не установлена')
            self.survey_date_label.setStyleSheet('''
                QLabel {
                    background-color: #F8F9FA;
                    padding: 6px 10px;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    font-size: 11px;
                }
            ''')
            self.survey_date_label.setFixedHeight(28)
            survey_date_row.addWidget(self.survey_date_label, 1)

            # Кнопка "Изменить дату" замера (по праву crm_cards.deadlines)
            if has_deadlines_access:
                edit_survey_btn = QPushButton('Изменить дату')
                # Синхронизация ширины с кнопкой "Изменить дедлайн"
                if edit_deadline_btn:
                    edit_survey_btn.setMinimumWidth(edit_deadline_btn.sizeHint().width())
                edit_survey_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E0E0E0;
                        color: #333333;
                        padding: 0px 12px;
                        border-radius: 4px;
                        border: none;
                        font-weight: bold;
                        max-height: 28px;
                        min-height: 28px;
                    }
                    QPushButton:hover { background-color: #D0D0D0; }
                    QPushButton:pressed { background-color: #C0C0C0; }
                """)
                edit_survey_btn.setFixedHeight(28)
                edit_survey_btn.clicked.connect(self.edit_survey_date)
                survey_date_row.addWidget(edit_survey_btn)

            team_layout.addLayout(survey_date_row)

            hint_survey = QLabel('Дата проведения замера помещения')
            hint_survey.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
            team_layout.addWidget(hint_survey)

            # Подзаголовок: Дедлайны исполнителей
            executors_label = QLabel('<b>Дедлайны исполнителей:</b>')
            executors_label.setStyleSheet('color: #2C3E50; font-size: 11px; margin-top: 10px;')
            team_layout.addWidget(executors_label)

            # ========== БЛОК ДИЗАЙНЕРА ==========
            if self.card_data.get('designer_name'):
                designer_group = QGroupBox('Дизайнер')
                designer_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 1px solid #E0E0E0;
                        border-radius: 4px;
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

                reassign_designer_btn = IconLoader.create_icon_button('refresh-black', 'Переназначить', 'Выбрать другого дизайнера', icon_size=12)
                # Синхронизация ширины с кнопкой "Изменить дедлайн"
                if edit_deadline_btn:
                    reassign_designer_btn.setMinimumWidth(edit_deadline_btn.sizeHint().width())
                reassign_designer_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E0E0E0;
                        color: #333333;
                        padding: 0px 12px;
                        border-radius: 4px;
                        border: none;
                        font-weight: bold;
                        max-height: 28px;
                        min-height: 28px;
                    }
                    QPushButton:hover { background-color: #D0D0D0; }
                    QPushButton:pressed { background-color: #C0C0C0; }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #333333;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 8px;
                        font-size: 11px;
                    }
                """)
                reassign_designer_btn.setFixedHeight(28)
                reassign_designer_btn.setEnabled(has_full_access)  # Для руководства и менеджеров
                reassign_designer_btn.clicked.connect(
                    lambda: self.reassign_executor_from_dialog('designer')
                )
                name_row.addWidget(reassign_designer_btn)

                designer_layout.addLayout(name_row)

                # Строка с дедлайном (read-only + кнопка изменить)
                deadline_row = QHBoxLayout()
                deadline_row.addWidget(QLabel('Дедлайн:'))

                # Сохраняем значение дедлайна
                self.designer_deadline_value = self.card_data.get('designer_deadline', '')
                self.designer_deadline_display = QLabel('Не установлен')
                self.designer_deadline_display.setStyleSheet('''
                    background-color: #FFFFFF;
                    padding: 0px 8px;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    font-size: 11px;
                    color: #555;
                    max-height: 28px;
                    min-height: 28px;
                ''')
                self.designer_deadline_display.setFixedHeight(28)
                if self.designer_deadline_value:
                    d = QDate.fromString(self.designer_deadline_value, 'yyyy-MM-dd')
                    if d.isValid():
                        self.designer_deadline_display.setText(d.toString('dd.MM.yyyy'))

                deadline_row.addWidget(self.designer_deadline_display, 1)

                if has_deadlines_access:
                    edit_designer_deadline_btn = QPushButton('Изменить')
                    edit_designer_deadline_btn.setFixedHeight(28)
                    edit_designer_deadline_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #E0E0E0;
                            color: #333333;
                            padding: 0px 12px;
                            border-radius: 4px;
                            border: none;
                            font-weight: bold;
                            max-height: 28px;
                            min-height: 28px;
                        }
                        QPushButton:hover { background-color: #D0D0D0; }
                        QPushButton:pressed { background-color: #C0C0C0; }
                    """)
                    edit_designer_deadline_btn.clicked.connect(
                        lambda: self.change_executor_deadline('designer')
                    )
                    deadline_row.addWidget(edit_designer_deadline_btn)

                designer_layout.addLayout(deadline_row)

                designer_group.setLayout(designer_layout)
                team_layout.addWidget(designer_group)
            else:
                self.designer_deadline_value = ''
                self.designer_deadline_display = None

            # ========== БЛОК ЧЕРТЁЖНИКА ==========
            if self.card_data.get('draftsman_name'):
                draftsman_group = QGroupBox('Чертёжник')
                draftsman_group.setStyleSheet("""
                    QGroupBox {
                        font-weight: bold;
                        border: 1px solid #E0E0E0;
                        border-radius: 4px;
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

                reassign_draftsman_btn = IconLoader.create_icon_button('refresh-black', 'Переназначить', 'Выбрать другого чертёжника', icon_size=12)
                # Синхронизация ширины с кнопкой "Изменить дедлайн"
                if edit_deadline_btn:
                    reassign_draftsman_btn.setMinimumWidth(edit_deadline_btn.sizeHint().width())
                reassign_draftsman_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E0E0E0;
                        color: #333333;
                        padding: 0px 12px;
                        border-radius: 4px;
                        border: none;
                        font-weight: bold;
                        max-height: 28px;
                        min-height: 28px;
                    }
                    QPushButton:hover { background-color: #D0D0D0; }
                    QPushButton:pressed { background-color: #C0C0C0; }
                    QToolTip {
                        background-color: #FFFFFF;
                        color: #333333;
                        border: none;
                        border-radius: 4px;
                        padding: 5px 8px;
                        font-size: 11px;
                    }
                """)
                reassign_draftsman_btn.setFixedHeight(28)
                reassign_draftsman_btn.setEnabled(has_full_access)  # Для руководства и менеджеров
                reassign_draftsman_btn.clicked.connect(
                    lambda: self.reassign_executor_from_dialog('draftsman')
                )
                name_row.addWidget(reassign_draftsman_btn)

                draftsman_layout.addLayout(name_row)

                # Строка с дедлайном (read-only + кнопка изменить)
                deadline_row = QHBoxLayout()
                deadline_row.addWidget(QLabel('Дедлайн:'))

                # Сохраняем значение дедлайна
                self.draftsman_deadline_value = self.card_data.get('draftsman_deadline', '')
                self.draftsman_deadline_display = QLabel('Не установлен')
                self.draftsman_deadline_display.setStyleSheet('''
                    background-color: #FFFFFF;
                    padding: 0px 8px;
                    border: 1px solid #E0E0E0;
                    border-radius: 4px;
                    font-size: 11px;
                    color: #555;
                    max-height: 28px;
                    min-height: 28px;
                ''')
                self.draftsman_deadline_display.setFixedHeight(28)
                if self.draftsman_deadline_value:
                    d = QDate.fromString(self.draftsman_deadline_value, 'yyyy-MM-dd')
                    if d.isValid():
                        self.draftsman_deadline_display.setText(d.toString('dd.MM.yyyy'))

                deadline_row.addWidget(self.draftsman_deadline_display, 1)

                if has_deadlines_access:
                    edit_draftsman_deadline_btn = QPushButton('Изменить')
                    edit_draftsman_deadline_btn.setFixedHeight(28)
                    edit_draftsman_deadline_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #E0E0E0;
                            color: #333333;
                            padding: 0px 12px;
                            border-radius: 4px;
                            border: none;
                            font-weight: bold;
                            max-height: 28px;
                            min-height: 28px;
                        }
                        QPushButton:hover { background-color: #D0D0D0; }
                        QPushButton:pressed { background-color: #C0C0C0; }
                    """)
                    edit_draftsman_deadline_btn.clicked.connect(
                        lambda: self.change_executor_deadline('draftsman')
                    )
                    deadline_row.addWidget(edit_draftsman_deadline_btn)

                draftsman_layout.addLayout(deadline_row)

                draftsman_group.setLayout(draftsman_layout)
                team_layout.addWidget(draftsman_group)
            else:
                self.draftsman_deadline_value = ''
                self.draftsman_deadline_display = None

            hint_executor_deadlines = QLabel('Эти дедлайны отображаются исполнителям на карточке')
            hint_executor_deadlines.setWordWrap(True)
            hint_executor_deadlines.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
            team_layout.addWidget(hint_executor_deadlines)

            team_group.setLayout(team_layout)
            edit_layout.addWidget(team_group)

            # ========== ПОДКЛЮЧЕНИЕ АВТОМАТИЧЕСКОГО СОЗДАНИЯ ВЫПЛАТ ==========
            self.senior_manager.currentIndexChanged.connect(
                lambda: self.on_employee_changed(self.senior_manager, 'Старший менеджер проектов')
            )
            # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
            if self.sdp:
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

        # === ОТЛОЖЕННЫЕ ВКЛАДКИ (создаются после showEvent для мгновенного открытия) ===
        self.timeline_widget = None
        self._is_executor = is_executor

        self._timeline_placeholder = QWidget()
        self._timeline_tab_index = self.tabs.addTab(self._timeline_placeholder, 'Таблица сроков')

        self._project_data_placeholder = QWidget()
        self.project_data_tab_index = self.tabs.addTab(self._project_data_placeholder, 'Данные по проекту')

        if not is_executor:
            self._history_placeholder = QWidget()
            self.project_info_tab_index = self.tabs.addTab(self._history_placeholder, 'История по проекту')
        else:
            self.project_info_tab_index = -1

        self.payments_tab_index = -1
        if _has_perm(self.employee, self.api_client, 'crm_cards.payments'):
            self._payments_placeholder = QWidget()
            self.payments_tab_index = self.tabs.addTab(self._payments_placeholder, 'Оплаты')

        # Для исполнителей открываем сразу вкладку "Данные по проекту"
        if is_executor:
            self.tabs.setCurrentIndex(0)

        self._deferred_tabs_ready = False

        layout.addWidget(self.tabs, 1)

        # Надпись синхронизации
        self.sync_label = QLabel('Синхронизация...')
        self.sync_label.setStyleSheet('color: #999999; font-size: 11px;')
        self.sync_label.setVisible(False)

        # Кнопки
        if not self.view_only:
            buttons_layout = QHBoxLayout()

            if _has_perm(self.employee, self.api_client, 'crm_cards.delete'):
                delete_btn = IconLoader.create_icon_button('delete', 'Удалить заказ', 'Полностью удалить заказ', icon_size=12)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E74C3C;
                        color: white;
                        padding: 0px 30px;
                        border-radius: 4px;
                        border: none;
                        font-weight: bold;
                        max-height: 36px;
                        min-height: 36px;
                    }
                    QPushButton:hover { background-color: #C0392B; }
                    QPushButton:pressed { background-color: #A93226; }
                """)
                delete_btn.setFixedHeight(36)
                delete_btn.clicked.connect(self.delete_order)
                buttons_layout.addWidget(delete_btn)

            buttons_layout.addWidget(self.sync_label)

            # Stretch для центровки кнопок чата
            buttons_layout.addStretch()

            # --- Кнопки чата ---
            self.create_chat_btn = IconLoader.create_icon_button(
                'message-circle', 'Создать чат', 'Создать чат в мессенджере', icon_size=14
            )
            self.create_chat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd93c;
                    color: #ffffff;
                    padding: 0px 16px;
                    border-radius: 4px;
                    border: 1px solid #e6c236;
                    font-weight: bold;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #ffdb4d; border-color: #d9b530; }
                QPushButton:pressed { background-color: #e6c236; }
                QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
            """)
            self.create_chat_btn.setFixedHeight(36)
            self.create_chat_btn.clicked.connect(self._on_create_chat)

            self.open_chat_btn = IconLoader.create_icon_button(
                'external-link', 'Открыть чат', 'Открыть чат в мессенджере', icon_size=14
            )
            self.open_chat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #333333;
                    padding: 0px 16px;
                    border-radius: 4px;
                    border: 1px solid #d9d9d9;
                    font-weight: bold;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #fafafa; border-color: #c0c0c0; }
                QPushButton:pressed { background-color: #f0f0f0; border-color: #b0b0b0; }
                QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
            """)
            self.open_chat_btn.setFixedHeight(36)
            self.open_chat_btn.clicked.connect(self._on_open_chat)

            self.delete_chat_btn = IconLoader.create_icon_button(
                'trash', 'Удалить чат', 'Удалить чат из мессенджера', icon_size=14
            )
            self.delete_chat_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #F44336;
                    padding: 0px 16px;
                    border-radius: 4px;
                    border: 1px solid #F44336;
                    font-weight: bold;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #FFF5F5; border-color: #E74C3C; }
                QPushButton:pressed { background-color: #FFEBEE; }
                QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
            """)
            self.delete_chat_btn.setFixedHeight(36)
            self.delete_chat_btn.clicked.connect(self._on_delete_chat)

            buttons_layout.addWidget(self.create_chat_btn)
            buttons_layout.addWidget(self.open_chat_btn)
            buttons_layout.addWidget(self.delete_chat_btn)

            # --- Кнопки скриптов мессенджера (иконки без текста, текст в tooltip) ---
            self.start_script_btn = IconLoader.create_icon_button(
                'play', '', 'Начальный скрипт — отправить в чат', icon_size=16
            )
            self.start_script_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #333333;
                    padding: 0px;
                    border-radius: 2px;
                    border: 1px solid #d9d9d9;
                    min-width: 36px; max-width: 36px;
                    min-height: 36px; max-height: 36px;
                }
                QPushButton:hover { background-color: #fafafa; border-color: #c0c0c0; }
                QPushButton:pressed { background-color: #f0f0f0; border-color: #b0b0b0; }
                QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
            """)
            self.start_script_btn.setFixedSize(36, 36)
            self.start_script_btn.clicked.connect(self._on_send_start_script)

            self.end_script_btn = IconLoader.create_icon_button(
                'check-circle', '', 'Завершающий скрипт — отправить в чат', icon_size=16
            )
            self.end_script_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffffff;
                    color: #333333;
                    padding: 0px;
                    border-radius: 2px;
                    border: 1px solid #d9d9d9;
                    min-width: 36px; max-width: 36px;
                    min-height: 36px; max-height: 36px;
                }
                QPushButton:hover { background-color: #fafafa; border-color: #c0c0c0; }
                QPushButton:pressed { background-color: #f0f0f0; border-color: #b0b0b0; }
                QPushButton:disabled { background-color: #fafafa; color: #b0b0b0; border-color: #e6e6e6; }
            """)
            self.end_script_btn.setFixedSize(36, 36)
            self.end_script_btn.clicked.connect(self._on_send_end_script)

            buttons_layout.addWidget(self.start_script_btn)
            buttons_layout.addWidget(self.end_script_btn)

            # Кнопка "Настройки чатов" перенесена в Администрирование (ui/admin_dialog.py)

            buttons_layout.addStretch()

            # Флаг для отложенной инициализации чата (после setLayout)
            self._need_chat_init = True

            save_btn = QPushButton('Сохранить')
            save_btn.clicked.connect(self.save_changes)
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
            save_btn.setFixedHeight(36)

            cancel_btn = QPushButton('Отмена')
            cancel_btn.clicked.connect(self.reject)
            cancel_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    color: #333333;
                    padding: 0px 30px;
                    font-weight: bold;
                    border-radius: 4px;
                    border: none;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #D0D0D0; }
                QPushButton:pressed { background-color: #C0C0C0; }
            """)
            cancel_btn.setFixedHeight(36)
            
            buttons_layout.addWidget(save_btn)
            buttons_layout.addWidget(cancel_btn)
            
            layout.addLayout(buttons_layout)
        else:
            # Блокируем переключение вкладок колесом мыши
            disable_wheel_on_tabwidget(self.tabs)

            self.setEnabled(False)
            view_buttons_layout = QHBoxLayout()
            self.sync_label.setEnabled(True)
            view_buttons_layout.addWidget(self.sync_label)
            view_buttons_layout.addStretch()
            close_btn = QPushButton('Закрыть')
            close_btn.setEnabled(True)
            close_btn.clicked.connect(self.reject)
            view_buttons_layout.addWidget(close_btn)
            layout.addLayout(view_buttons_layout)

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

        # Ширина: фиксированная 1200px
        target_width = 1200

        # Устанавливаем размеры окна
        self.setMinimumWidth(1100)  # Минимальная ширина
        self.setFixedHeight(target_height)  # ФИКСИРОВАННАЯ высота 90% экрана - нельзя растягивать
        self.resize(target_width, target_height)
        # ===================================================================

        # Инициализация кнопок чата после setLayout (чтобы виджеты имели parent)
        if getattr(self, '_need_chat_init', False):
            _can_create = _has_perm(self.employee, self.data.api_client, 'messenger.create_chat')
            _can_view = _has_perm(self.employee, self.data.api_client, 'messenger.view_chat')
            _can_delete = _has_perm(self.employee, self.data.api_client, 'messenger.delete_chat')
            self.create_chat_btn.setVisible(_can_create)
            self.open_chat_btn.setVisible(_can_view)
            self.delete_chat_btn.setVisible(_can_delete)
            # Кнопки скриптов: видимы если есть право просмотра чатов
            self.start_script_btn.setVisible(_can_view)
            self.end_script_btn.setVisible(_can_view)
            self._messenger_chat_data = None
            self._load_messenger_chat_state()

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
                border: 1px solid #E0E0E0;
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
            conn = self.data.db.connect()
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
                
                print(f"Дата замера обновлена")
            else:
                # Создаем новую
                cursor.execute('''
                INSERT INTO surveys (contract_id, surveyor_id, survey_date, created_by)
                VALUES (?, ?, ?, ?)
                ''', (contract_id, surveyor_id, survey_date.toString('yyyy-MM-dd'),
                      self.employee['id'] if self.employee else None))
                
                print(f"Дата замера создана")
            
            conn.commit()
            self.data.db.close()
            
            # ========== ИСПРАВЛЕНИЕ: ОБНОВЛЯЕМ ОТЧЕТНЫЙ МЕСЯЦ ЗАМЕРЩИКА ==========
            contract = self.data.get_contract(contract_id)
            report_month = survey_date.toString('yyyy-MM')

            # Проверяем, есть ли уже выплата замерщику и создаем/обновляем
            try:
                payments = self.data.get_payments_for_contract(contract_id)
                existing_payment = next(
                    (p for p in payments if p.get('employee_id') == surveyor_id and p.get('role') == 'Замерщик'),
                    None
                )
                if existing_payment:
                    self.data.update_payment(existing_payment['id'], {'report_month': report_month})
                    print(f"Отчетный месяц замерщика обновлен: {report_month}")
                else:
                    payment_data = {
                        'contract_id': contract_id,
                        'employee_id': surveyor_id,
                        'role': 'Замерщик',
                        'payment_type': 'Полная оплата',
                        'report_month': report_month,
                        'crm_card_id': self.card_data['id']
                    }
                    self.data.create_payment(payment_data)
                    print(f"Выплата замерщику создана в отчетном месяце {report_month}")
            except Exception as e:
                print(f"[WARNING] Ошибка работы с оплатами замерщика: {e}")
            # ======================================================================

            # Обновляем contracts.measurement_date в БД
            conn = self.data.db.connect()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE contracts
                SET measurement_date = ?
                WHERE id = ?
            ''', (survey_date.toString('yyyy-MM-dd'), contract_id))
            conn.commit()
            self.data.db.close()

            # Обновляем crm_cards.survey_date
            updates = {'survey_date': survey_date.toString('yyyy-MM-dd'), 'surveyor_id': surveyor_id}
            self.data.update_crm_card(self.card_data["id"], updates)
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
                conn = self.data.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT full_name FROM employees WHERE id = ?', (surveyor_id,))
                surveyor_result = cursor.fetchone()
                surveyor_name = surveyor_result['full_name'] if surveyor_result else 'Неизвестный'
                conn.close()

                description = f"Замер выполнен: {survey_date.toString('dd.MM.yyyy')} | Замерщик: {surveyor_name}"

                # Используем contract как entity_type для соответствия с проверкой
                contract_id = self.card_data.get('contract_id')
                self._add_action_history('survey_complete', description, entity_type='contract', entity_id=contract_id)

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
                                border-radius: 4px;
                                font-size: 10px;
                                font-weight: bold;
                            }
                            QToolTip {
                                background-color: #FFFFFF;
                                color: #333333;
                                border: none;
                                border-radius: 4px;
                                padding: 5px 8px;
                                font-size: 11px;
                            }
                        """)
                        widget.setToolTip('Замер уже отмечен как выполненный')
                        break

            # Формируем сообщение в зависимости от типа проекта
            if contract and contract['project_type'] == 'Индивидуальный':
                print(f'[OK] Дата замера сохранена: {survey_date.toString("dd.MM.yyyy")}, выплата в {report_month}')
            else:
                print(f'[OK] Дата замера сохранена: {survey_date.toString("dd.MM.yyyy")}, выплата при сдаче')

            # Данные сохранены, закрываем диалог (без окна успеха)
            dialog.accept()
            
        except Exception as e:
            print(f" Ошибка сохранения замера: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

    def edit_survey_date(self):
        """Открывает диалог для изменения даты замера"""
        from PyQt5.QtCore import QDate
        from utils.calendar_helpers import add_today_button_to_dateedit

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
        date_input.setFixedHeight(28)
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QDateEdit:focus {
                border: 1px solid #2C3E50;
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
            except Exception:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_survey_date():
            try:
                selected_date = date_input.date()
                date_str = selected_date.toString('yyyy-MM-dd')

                # Обновляем в БД - и crm_cards, и contracts
                updates = {'survey_date': date_str}
                self.data.update_crm_card(self.card_data["id"], updates)
                self.card_data['survey_date'] = date_str
                if hasattr(self, '_cached_contract') and self._cached_contract:
                    self._cached_contract['measurement_date'] = date_str

                # Сразу пересчитываем дату начала разработки в таблице сроков
                if hasattr(self, 'timeline_widget') and self.timeline_widget:
                    try:
                        self.timeline_widget.refresh_start_date()
                    except Exception:
                        pass

                # Обновляем contracts.measurement_date и surveys.survey_date
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.data.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE contracts
                        SET measurement_date = ?
                        WHERE id = ?
                    ''', (date_str, contract_id))
                    # Обновляем запись в таблице surveys
                    cursor.execute('''
                        UPDATE surveys
                        SET survey_date = ?
                        WHERE contract_id = ?
                    ''', (date_str, contract_id))
                    conn.commit()
                    self.data.db.close()
                    # Синхронизируем с API
                    if self.data.is_online:
                        try:
                            self.data.update_contract(contract_id, {'measurement_date': date_str})
                        except Exception:
                            pass

                # ========== ОБНОВЛЯЕМ ОТЧЕТНЫЙ МЕСЯЦ ЗАМЕРЩИКА ==========
                contract_id = self.card_data.get('contract_id')
                surveyor_id = self.card_data.get('surveyor_id')

                if contract_id and surveyor_id:
                    report_month = selected_date.toString('yyyy-MM')
                    try:
                        payments = self.data.get_payments_for_contract(contract_id)
                        existing_payment = next(
                            (p for p in payments if p.get('employee_id') == surveyor_id and p.get('role') == 'Замерщик'),
                            None
                        )
                        if existing_payment:
                            self.data.update_payment(existing_payment['id'], {'report_month': report_month})
                            print(f"Отчетный месяц замерщика обновлен: {report_month}")
                        else:
                            contract = self.data.get_contract(contract_id)
                            if contract and contract['project_type'] == 'Индивидуальный':
                                payment_data = {
                                    'contract_id': contract_id,
                                    'employee_id': surveyor_id,
                                    'role': 'Замерщик',
                                    'payment_type': 'Полная оплата',
                                    'report_month': report_month,
                                    'crm_card_id': self.card_data['id']
                                }
                                self.data.create_payment(payment_data)
                                print(f"Выплата замерщику создана в отчетном месяце {report_month}")
                            else:
                                print(f"[INFO] Шаблонный проект: выплата замерщику будет создана при сдаче проекта")
                    except Exception as e:
                        print(f"[WARNING] Ошибка работы с оплатами замерщика: {e}")
                # ========================================================

                # Обновляем оба label - в редактировании и в данных по проекту
                self.survey_date_label.setText(selected_date.toString('dd.MM.yyyy'))
                if hasattr(self, 'project_data_survey_date_label'):
                    self.project_data_survey_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_payments_tab()
                self.refresh_project_info_tab()

                # Добавляем запись в историю
                if self.employee:
                    description = f"Дата замера изменена на {selected_date.toString('dd.MM.yyyy')}"
                    contract_id = self.card_data.get('contract_id')
                    self._add_action_history('survey_date_changed', description, entity_type='contract', entity_id=contract_id)
                    self.reload_project_history()

                # Закрываем диалог без показа окна успеха
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
        from utils.calendar_helpers import add_today_button_to_dateedit

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
            except Exception:
                current_deadline_text.setText('Не установлен')
        else:
            current_deadline_text.setText('Не установлен')

        current_deadline_text.setFixedHeight(28)
        current_deadline_text.setStyleSheet('''
            background-color: #F8F9FA;
            padding: 0px 8px;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            font-size: 11px;
            color: #555;
            max-height: 28px;
            min-height: 28px;
        ''')
        content_layout.addWidget(current_deadline_text)

        # Новый дедлайн
        new_deadline_label = QLabel('Новый дедлайн:')
        new_deadline_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(new_deadline_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setFixedHeight(28)
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QDateEdit:focus {
                border: 1px solid #2C3E50;
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
            except Exception:
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
        reason_input.setFixedHeight(28)
        reason_input.setStyleSheet("""
            QLineEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QLineEdit:focus {
                border: 1px solid #2C3E50;
            }
        """)
        content_layout.addWidget(reason_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
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
                self.data.update_crm_card(self.card_data["id"], updates)
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
                        except Exception:
                            old_deadline_formatted = old_deadline_str

                    description = f"Дедлайн изменен с {old_deadline_formatted} на {selected_date.toString('dd.MM.yyyy')}. Причина: {reason}"

                    self._add_action_history('deadline_changed', description)
                    self.reload_project_history()

                    # Принудительно обрабатываем отложенные события Qt
                    from PyQt5.QtWidgets import QApplication
                    QApplication.processEvents()

                # Закрываем диалог без показа окна успеха
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

    def change_executor_deadline(self, executor_type):
        """Открывает диалог для изменения дедлайна исполнителя (дизайнера/чертёжника) с причиной"""
        from PyQt5.QtCore import QDate
        from utils.calendar_helpers import add_today_button_to_dateedit

        if executor_type == 'designer':
            title = 'Изменить дедлайн дизайнера'
            current_value = getattr(self, 'designer_deadline_value', '')
            search_key = 'концепция'
        else:
            title = 'Изменить дедлайн чертёжника'
            current_value = getattr(self, 'draftsman_deadline_value', '')
            current_column = self.card_data.get('column_name', '').lower()
            search_key = 'планировочные' if 'планировочные' in current_column else 'чертежи'

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

        title_bar = CustomTitleBar(dialog, title, simple_mode=True)
        layout.addWidget(title_bar)

        content_layout = QVBoxLayout()
        content_layout.setContentsMargins(20, 20, 20, 20)
        content_layout.setSpacing(15)

        # Текущий дедлайн
        current_label = QLabel('Текущий дедлайн:')
        current_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(current_label)

        current_text = QLabel()
        if current_value:
            try:
                from datetime import datetime
                d = datetime.strptime(current_value, '%Y-%m-%d')
                current_text.setText(d.strftime('%d.%m.%Y'))
            except Exception:
                current_text.setText('Не установлен')
        else:
            current_text.setText('Не установлен')
        current_text.setFixedHeight(28)
        current_text.setStyleSheet('''
            background-color: #F8F9FA;
            padding: 0px 8px;
            border: 1px solid #E0E0E0;
            border-radius: 4px;
            font-size: 11px;
            color: #555;
            max-height: 28px;
            min-height: 28px;
        ''')
        content_layout.addWidget(current_text)

        # Новый дедлайн
        new_label = QLabel('Новый дедлайн:')
        new_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(new_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setFixedHeight(28)
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QDateEdit:focus {
                border: 1px solid #2C3E50;
            }
        """)
        add_today_button_to_dateedit(date_input)

        if current_value:
            try:
                from datetime import datetime
                d = datetime.strptime(current_value, '%Y-%m-%d')
                date_input.setDate(QDate(d.year, d.month, d.day))
            except Exception:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())
        content_layout.addWidget(date_input)

        # Причина
        reason_label = QLabel('Причина изменения:')
        reason_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(reason_label)

        reason_input = QLineEdit()
        reason_input.setPlaceholderText('Укажите причину изменения дедлайна...')
        reason_input.setFixedHeight(28)
        reason_input.setStyleSheet("""
            QLineEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QLineEdit:focus {
                border: 1px solid #2C3E50;
            }
        """)
        content_layout.addWidget(reason_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_executor_deadline():
            try:
                reason = reason_input.text().strip()
                if not reason:
                    CustomMessageBox(dialog, 'Ошибка', 'Необходимо указать причину изменения дедлайна', 'warning').exec_()
                    return

                selected_date = date_input.date()
                new_deadline_str = selected_date.toString('yyyy-MM-dd')

                if new_deadline_str == current_value:
                    CustomMessageBox(dialog, 'Информация', 'Дедлайн не изменился', 'warning').exec_()
                    return

                # Сохраняем дедлайн через stage_executors
                success = self.data.update_stage_executor_deadline(
                    self.card_data['id'], search_key, new_deadline_str)

                if not success:
                    CustomMessageBox(dialog, 'Ошибка', 'Не удалось сохранить дедлайн', 'error').exec_()
                    return

                # Обновляем локальные данные и отображение
                if executor_type == 'designer':
                    self.designer_deadline_value = new_deadline_str
                    self.card_data['designer_deadline'] = new_deadline_str
                    if self.designer_deadline_display:
                        self.designer_deadline_display.setText(selected_date.toString('dd.MM.yyyy'))
                else:
                    self.draftsman_deadline_value = new_deadline_str
                    self.card_data['draftsman_deadline'] = new_deadline_str
                    if self.draftsman_deadline_display:
                        self.draftsman_deadline_display.setText(selected_date.toString('dd.MM.yyyy'))

                # История действий
                old_fmt = 'Не установлен'
                if current_value:
                    try:
                        from datetime import datetime
                        old_d = datetime.strptime(current_value, '%Y-%m-%d')
                        old_fmt = old_d.strftime('%d.%m.%Y')
                    except Exception:
                        old_fmt = current_value

                role_name = 'дизайнера' if executor_type == 'designer' else 'чертёжника'
                description = f"Дедлайн {role_name} изменен с {old_fmt} на {selected_date.toString('dd.MM.yyyy')}. Причина: {reason}"
                self._add_action_history('executor_deadline_changed', description)
                self.reload_project_history()

                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                dialog.accept()

            except Exception as e:
                print(f" Ошибка изменения дедлайна исполнителя: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(dialog, 'Ошибка', f'Не удалось сохранить: {e}', 'error').exec_()

        save_btn.clicked.connect(save_executor_deadline)

        buttons_layout.addWidget(save_btn)
        buttons_layout.addWidget(cancel_btn)
        content_layout.addLayout(buttons_layout)

        layout.addLayout(content_layout)

        dialog.exec_()

    def upload_project_tech_task_file(self):
        """ИСПРАВЛЕНИЕ 06.02.2026: Сначала открываем диалог ТЗ, как у замера (#13)"""
        from ui.crm_tab import TechTaskDialog
        dialog = TechTaskDialog(self, self.card_data.get('id'), api_client=self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            # Обновляем отображение ТЗ файла
            self.refresh_payments_tab()
        return

    def upload_project_tech_task_file_direct(self):
        """Прямая загрузка файла тех.задания на Яндекс.Диск (не используется)"""
        from PyQt5.QtWidgets import QFileDialog
        from PyQt5.QtCore import Qt

        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите PDF файл тех.задания",
            "",
            "PDF Files (*.pdf)"
        )

        if not file_path:
            return


        # Получаем yandex_folder_path из договора
        contract_id = self.card_data.get('contract_id')
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

        # Создаем прогресс-диалог
        progress = create_progress_dialog("Загрузка файла", "Подготовка к загрузке...", "Отмена", 3, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        # Загружаем файл на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(step, fname, phase):
                    if cancel_event.is_set():
                        return
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    phase_names = {
                        'preparing': 'Подготовка...',
                        'uploading': 'Загрузка на Яндекс.Диск...',
                        'finalizing': 'Завершение...'
                    }
                    percent = int((step / 3) * 100)
                    label_text = f"{phase_names.get(phase, phase)}\n{fname} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                result = yd.upload_file_to_contract_folder(
                    file_path,
                    contract_folder,
                    "Анкета",
                    file_name,
                    progress_callback=update_progress
                )

                if result:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, 3))
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    QTimer.singleShot(0, lambda: self.tech_task_upload_completed.emit(
                        result['public_link'],
                        result['yandex_path'],
                        result['file_name'],
                        contract_id
                    ))
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    QTimer.singleShot(0, lambda: self.tech_task_upload_error.emit("Не удалось загрузить файл на Яндекс.Диск"))

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _err = str(e)
                QTimer.singleShot(0, lambda: self.tech_task_upload_error.emit(_err))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_project_tech_task_uploaded(self, public_link, yandex_path, file_name, contract_id):
        """Обработчик успешной загрузки файла тех.задания"""

        if public_link:
            # Обновляем все поля тех.задания в БД договора (локально)
            conn = self.data.db.connect()
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

            # Синхронизируем с API
            if self.data.is_online:
                try:
                    result = self.data.update_contract(contract_id, {
                        'tech_task_link': public_link,
                        'tech_task_yandex_path': yandex_path,
                        'tech_task_file_name': file_name
                    })
                    if result:
                        print(f"[API] ТЗ синхронизировано с сервером, contract_id={contract_id}")
                    else:
                        print(f"[WARN] ТЗ сохранено локально, но не синхронизировано с сервером")
                except Exception as api_err:
                    print(f"[WARN] Ошибка синхронизации ТЗ с API: {api_err}")

            # Обновляем лейбл (обрезаем длинное имя)
            truncated_name = self.truncate_filename(file_name)
            self.project_data_tz_file_label.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            # Обновляем старый лейбл если он существует (для совместимости)
            if hasattr(self, 'tech_task_file_label'):
                self.tech_task_file_label.setText(f'<a href="{public_link}" title="{file_name}">{truncated_name}</a>')

            # Деактивируем кнопку загрузки после успешной загрузки
            if hasattr(self, 'upload_tz_btn'):
                self.upload_tz_btn.setEnabled(False)

            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime
                employee_name = self.employee.get('full_name', 'Неизвестный')
                date_str = datetime.now().strftime('%d.%m.%Y')
                description = f"Добавлены файлы в Техническое задание"

                self._add_action_history('file_upload', description)
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"[OK] Добавлена запись в историю: {description}")

            # Обновляем card_data чтобы кнопка "Добавить ТЗ" скрылась на карточке
            self.card_data['tech_task_link'] = public_link
            self.card_data['tech_task_yandex_path'] = yandex_path
            self.card_data['tech_task_file_name'] = file_name
            self.card_data['tech_task_file'] = file_name

            # Обновляем карточки в колонке CRM
            if hasattr(self, 'parent_tab') and self.parent_tab and hasattr(self.parent_tab, 'refresh_current_tab'):
                self.parent_tab.refresh_current_tab()

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
        from PyQt5.QtWidgets import QFileDialog
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

        contract_folder = self._get_contract_yandex_folder(contract_id)

        if not contract_folder:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        # Создаем прогресс-диалог
        progress = create_progress_dialog("Загрузка файлов", "Подготовка к загрузке...", "Отмена", len(file_paths), self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        # Загружаем файлы на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(current, total, fname, phase):
                    if cancel_event.is_set():
                        return
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, current))
                    percent = int((current / total) * 100)
                    label_text = f"Загрузка: {fname}\n({current}/{total} файлов - {percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                # Загружаем файлы
                uploaded_files = yd.upload_stage_files(
                    file_paths,
                    contract_folder,
                    'references',
                    progress_callback=update_progress
                )

                if uploaded_files:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, len(file_paths)))
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)

                    # Получаем ссылку на папку
                    folder_path = yd.get_stage_folder_path(contract_folder, 'references')
                    folder_link = yd.get_public_link(folder_path)

                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    _link = folder_link if folder_link else folder_path
                    _cid = contract_id
                    QTimer.singleShot(0, lambda: self.references_upload_completed.emit(_link, _cid))
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    QTimer.singleShot(0, lambda: self.references_upload_error.emit("Не удалось загрузить файлы на Яндекс.Диск"))

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _err = str(e)
                QTimer.singleShot(0, lambda: self.references_upload_error.emit(_err))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_references_uploaded(self, folder_link, contract_id):
        """Обработчик успешной загрузки референсов"""
        try:
            # Обновляем через DataAccess (API + локальная БД)
            self.data.update_contract(contract_id, {'references_yandex_path': folder_link})
            print(f"[DataAccess] Ссылка на референсы обновлена")

            # Обновляем лейбл
            self.project_data_references_label.setText(f'<a href="{folder_link}">Открыть папку с референсами</a>')

            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime
                description = f"Добавлены файлы в Референсы"

                self._add_action_history('file_upload', description)
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"[OK] Добавлена запись в историю: {description}")

        except Exception as e:
            print(f"[ERROR] Критическая ошибка сохранения референсов: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить данные референсов:\n{str(e)}', 'error').exec_()

    def _on_references_upload_error(self, error_msg):
        """Обработчик ошибки загрузки референсов"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов: {error_msg}', 'error').exec_()

    def upload_photo_documentation_files(self):
        """Загрузка множественных файлов фотофиксации на Яндекс.Диск"""
        from PyQt5.QtWidgets import QFileDialog
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

        contract_folder = self._get_contract_yandex_folder(contract_id)

        if not contract_folder:
            CustomMessageBox(
                self,
                'Ошибка',
                'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.',
                'warning'
            ).exec_()
            return

        # Создаем прогресс-диалог
        progress = create_progress_dialog("Загрузка файлов", "Подготовка к загрузке...", "Отмена", len(file_paths), self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        # Загружаем файлы на Яндекс.Диск асинхронно
        def upload_thread():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                def update_progress(current, total, fname, phase):
                    if cancel_event.is_set():
                        return
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, current))
                    percent = int((current / total) * 100)
                    label_text = f"Загрузка: {fname}\n({current}/{total} файлов - {percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                # Загружаем файлы
                uploaded_files = yd.upload_stage_files(
                    file_paths,
                    contract_folder,
                    'photo_documentation',
                    progress_callback=update_progress
                )

                if uploaded_files:
                    from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, len(file_paths)))
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)

                    # Получаем ссылку на папку
                    folder_path = yd.get_stage_folder_path(contract_folder, 'photo_documentation')
                    folder_link = yd.get_public_link(folder_path)

                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    _link = folder_link if folder_link else folder_path
                    _cid = contract_id
                    QTimer.singleShot(0, lambda: self.photo_doc_upload_completed.emit(_link, _cid))
                else:
                    # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, progress.close)
                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    QTimer.singleShot(0, lambda: self.photo_doc_upload_error.emit("Не удалось загрузить файлы на Яндекс.Диск"))

            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _err = str(e)
                QTimer.singleShot(0, lambda: self.photo_doc_upload_error.emit(_err))

        thread = threading.Thread(target=upload_thread)
        thread.start()

    def _on_photo_doc_uploaded(self, folder_link, contract_id):
        """Обработчик успешной загрузки фотофиксации"""
        try:
            # Обновляем через DataAccess (API + локальная БД)
            self.data.update_contract(contract_id, {'photo_documentation_yandex_path': folder_link})
            print(f"[DataAccess] Ссылка на фотофиксацию обновлена")

            # Обновляем лейбл
            self.project_data_photo_doc_label.setText(f'<a href="{folder_link}">Открыть папку с фотофиксацией</a>')

            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime
                description = f"Добавлены файлы в Фотофиксацию"

                self._add_action_history('file_upload', description)
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"[OK] Добавлена запись в историю: {description}")

        except Exception as e:
            print(f"[ERROR] Критическая ошибка сохранения фотофиксации: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось сохранить данные фотофиксации:\n{str(e)}', 'error').exec_()

    def _on_photo_doc_upload_error(self, error_msg):
        """Обработчик ошибки загрузки фотофиксации"""
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов: {error_msg}', 'error').exec_()

    def add_measurement(self):
        """Добавить замер с загрузкой изображения"""
        from ui.crm_tab import MeasurementDialog
        dialog = MeasurementDialog(self, self.card_data.get('id'), self.employee, api_client=self.api_client)
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
        conn = self.data.db.connect()
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
                except Exception:
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
        yandex_path = None
        try:
            contract = self.data.get_contract(contract_id)
            yandex_path = contract.get('tech_task_yandex_path') if contract else None
            print(f"[DEBUG] Получен tech_task_yandex_path: {yandex_path}")
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к файлу ТЗ: {e}")
            import traceback
            traceback.print_exc()

        # Удаляем все поля тех.задания из БД/API
        try:
            update_data = {
                'tech_task_link': None,
                'tech_task_yandex_path': None,
                'tech_task_file_name': None
            }
            self.data.update_contract(contract_id, update_data)
            # Также обновляем CRM карточку
            card_id = self.card_data.get('id')
            if card_id:
                self.data.update_crm_card(card_id, {'tech_task_file': None})
        except Exception as e:
            print(f"[ERROR] Ошибка удаления данных ТЗ: {e}")

        # Удаляем файл с Яндекс.Диска
        if yandex_path:
            try:
                print(f"[DEBUG] Удаляем файл ТЗ с Яндекс.Диска: {yandex_path}")
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                result = yd.delete_file(yandex_path)
                print(f"[DEBUG] Результат удаления ТЗ: {result}")
            except Exception as e:
                print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")
                import traceback
                traceback.print_exc()
        else:
            print(f"[WARN] yandex_path пустой, файл ТЗ на ЯД не удаляется")

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = "Удален файл ТЗ"

            self._add_action_history('file_delete', description)
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_tz_file_label'):
            self.project_data_tz_file_label.setText('Не загружен')
        if hasattr(self, 'upload_tz_btn'):
            self.upload_tz_btn.setEnabled(True)  # Активируем кнопку после удаления файла

        # Обновляем card_data чтобы кнопка "Добавить ТЗ" появилась на карточке
        self.card_data['tech_task_link'] = None
        self.card_data['tech_task_yandex_path'] = None
        self.card_data['tech_task_file_name'] = None
        self.card_data['tech_task_file'] = None

        # Обновляем карточки в колонке CRM
        if hasattr(self, 'parent_tab') and self.parent_tab and hasattr(self.parent_tab, 'refresh_current_tab'):
            self.parent_tab.refresh_current_tab()

        # Отправляем сигнал для обновления UI
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
        contract_folder = None
        try:
            contract = self.data.get_contract(contract_id)
            contract_folder = contract.get('yandex_folder_path') if contract else None
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к папке: {e}")

        # Удаляем поле из БД/API
        try:
            self.data.update_contract(contract_id, {'references_yandex_path': None})
        except Exception as e:
            print(f"[ERROR] Ошибка удаления references_yandex_path: {e}")

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

            self._add_action_history('file_delete', description)
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_references_label'):
            self.project_data_references_label.setText('Не загружена')

        # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие
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
        contract_folder = None
        try:
            contract = self.data.get_contract(contract_id)
            contract_folder = contract.get('yandex_folder_path') if contract else None
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к папке: {e}")

        # Удаляем поле из БД/API
        try:
            self.data.update_contract(contract_id, {'photo_documentation_yandex_path': None})
        except Exception as e:
            print(f"[ERROR] Ошибка удаления photo_documentation_yandex_path: {e}")

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

            self._add_action_history('file_delete', description)
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Обновляем UI
        if hasattr(self, 'project_data_photo_doc_label'):
            self.project_data_photo_doc_label.setText('Не загружена')

        # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие
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
                border: 1px solid #E0E0E0;
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
                background-color: #ffd93c;
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
                border-radius: 4px;
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
                    border-radius: 4px;
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
            self.data.add_project_template(contract_id, url)

        dialog.accept()

        # Обновляем список ссылок в UI
        self.load_project_templates()

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime
            description = f"Добавлены ссылки на шаблоны проекта ({len(template_urls)} шт.)"

            self._add_action_history('file_upload', description)
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            print(f"[OK] Добавлена запись в историю: {description}")

        # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие

    def load_project_templates(self):
        """Загрузка и отображение ссылок на шаблоны"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Получаем ссылки из БД
        templates = self.data.get_project_templates(contract_id)

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
                border-radius: 4px;
                font-size: 10px;
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
        link_label.setOpenExternalLinks(True)
        link_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        link_label.setCursor(QCursor(Qt.PointingHandCursor))
        link_label.setWordWrap(True)
        row.addWidget(link_label, 1)

        # Кнопка удаления этапа
        if _has_perm(self.employee, self.api_client, 'crm_cards.update'):
            delete_btn = QPushButton('X')
            delete_btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: #E74C3C;
                    border: 1px solid #E74C3C;
                    border-radius: 4px;
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
        success = self.data.delete_project_template(template_id)

        if success:
            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime
                description = "Удалена ссылка на шаблон проекта"

                self._add_action_history('file_delete', description)
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
                print(f"[OK] Добавлена запись в историю: {description}")

            # Обновляем список в UI
            self.load_project_templates()
            # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие
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
        yandex_path = None
        try:
            contract = self.data.get_contract(contract_id)
            yandex_path = contract.get('measurement_yandex_path') if contract else None
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к файлу замера: {e}")

        # Удаляем данные через DataAccess
        try:
            update_data = {
                'measurement_image_link': None,
                'measurement_yandex_path': None,
                'measurement_file_name': None,
                'measurement_date': None
            }
            self.data.update_contract(contract_id, update_data)
            print(f"[DataAccess] Данные замера удалены для договора {contract_id}")
        except Exception as e:
            print(f"[ERROR] Ошибка удаления данных замера: {e}")

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

            self._add_action_history('file_delete', description)
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

        # Обновляем card_data чтобы кнопка "Добавить замер" появилась на карточке
        self.card_data['measurement_image_link'] = None
        self.card_data['measurement_yandex_path'] = None
        self.card_data['measurement_file_name'] = None
        self.card_data['measurement_date'] = None
        self.card_data['survey_date'] = None

        # Обновляем карточки в колонке CRM
        if hasattr(self, 'parent_tab') and self.parent_tab and hasattr(self.parent_tab, 'refresh_current_tab'):
            self.parent_tab.refresh_current_tab()

        # Отправляем сигнал для обновления UI (чтобы другие открытые окна тоже обновились)
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
                border: 2px solid #ffd93c;
            }
        """)

        # Устанавливаем текущий URL
        current_file = self.card_data.get('tech_task_file', '')
        url_input.setText(current_file)

        content_layout.addWidget(url_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # ИСПРАВЛЕНИЕ 07.02.2026: Стандартная высота кнопок 28px (#8)
        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover { background-color: #e6c435; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 20px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                min-height: 28px;
                max-height: 28px;
            }
            QPushButton:hover { background-color: #BDBDBD; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_tech_task_file():
            try:
                file_url = url_input.text().strip()

                # Обновляем в БД
                updates = {'tech_task_file': file_url}
                self.data.update_crm_card(self.card_data["id"], updates)
                self.card_data['tech_task_file'] = file_url

                # Обновляем label
                if file_url:
                    self.tech_task_file_label.setText(f'<a href="{file_url}">{file_url}</a>')
                else:
                    self.tech_task_file_label.setText('Не загружен')

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_project_info_tab()

                # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие
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
        from utils.calendar_helpers import add_today_button_to_dateedit

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #E0E0E0;
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
        date_input.setFixedHeight(28)
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QDateEdit:focus {
                border: 1px solid #2C3E50;
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
            except Exception:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)

        def save_tech_task_date():
            try:
                selected_date = date_input.date()
                date_str = selected_date.toString('yyyy-MM-dd')

                # Обновляем в БД crm_cards
                updates = {'tech_task_date': date_str}
                self.data.update_crm_card(self.card_data["id"], updates)
                self.card_data['tech_task_date'] = date_str

                # Сразу пересчитываем дату начала разработки в таблице сроков
                if hasattr(self, 'timeline_widget') and self.timeline_widget:
                    try:
                        self.timeline_widget.refresh_start_date()
                    except Exception as e:
                        print(f"[CardEditDialog] Ошибка обновления таблицы сроков: {e}")

                # Обновляем label в вкладке "Исполнители и дедлайн"
                if hasattr(self, 'tech_task_date_label'):
                    self.tech_task_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем label в вкладке "Данные по проекту"
                if hasattr(self, 'project_data_tz_date_label'):
                    self.project_data_tz_date_label.setText(selected_date.toString('dd.MM.yyyy'))

                # Обновляем вкладки (без закрытия окна редактирования)
                self.refresh_project_info_tab()

                # Добавляем запись в историю
                if self.employee:
                    description = f"Дата ТЗ изменена на {selected_date.toString('dd.MM.yyyy')}"
                    contract_id = self.card_data.get('contract_id')
                    self._add_action_history('tech_task_date_changed', description, entity_type='contract', entity_id=contract_id)
                    self.reload_project_history()

                # Закрываем диалог без показа окна успеха
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
        from utils.calendar_helpers import add_today_button_to_dateedit

        # Создаем диалоговое окно
        dialog = QDialog()
        dialog.setWindowFlags(dialog.windowFlags() | Qt.FramelessWindowHint)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: white;
                border: 1px solid #E0E0E0;
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
        surveyor_input.setFixedHeight(28)
        surveyors = self.data.get_employees_by_position('Замерщик')
        surveyor_input.addItem('Не назначен', None)
        for surv in surveyors:
            surveyor_input.addItem(surv['full_name'], surv['id'])

        # Устанавливаем текущего замерщика
        if self.card_data.get('surveyor_id'):
            for i in range(surveyor_input.count()):
                if surveyor_input.itemData(i) == self.card_data.get('surveyor_id'):
                    surveyor_input.setCurrentIndex(i)
                    break

        content_layout.addWidget(surveyor_input)

        # Поле даты
        date_label = QLabel('Дата замера:')
        date_label.setStyleSheet('font-size: 11px; font-weight: bold; color: #2C3E50;')
        content_layout.addWidget(date_label)

        date_input = CustomDateEdit()
        date_input.setCalendarPopup(True)
        date_input.setDisplayFormat('dd.MM.yyyy')
        date_input.setFixedHeight(28)
        date_input.setStyleSheet("""
            QDateEdit {
                padding: 0px 8px;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 11px;
                background-color: white;
                max-height: 28px;
                min-height: 28px;
            }
            QDateEdit:focus {
                border: 1px solid #2C3E50;
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
            except Exception:
                date_input.setDate(QDate.currentDate())
        else:
            date_input.setDate(QDate.currentDate())

        content_layout.addWidget(date_input)

        # Кнопки
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        save_btn = QPushButton('Сохранить')
        save_btn.setFixedHeight(28)
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)

        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(28)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                padding: 0px 30px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
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
                self.data.update_crm_card(self.card_data["id"], updates)
                self.card_data['survey_date'] = date_str
                self.card_data['surveyor_id'] = surveyor_id

                # Обновляем contracts.measurement_date
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.data.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                        UPDATE contracts
                        SET measurement_date = ?
                        WHERE id = ?
                    ''', (date_str, contract_id))
                    conn.commit()
                    self.data.db.close()

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

                # Данные сохранены, закрываем диалог (без окна успеха)
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
                self.tabs.insertTab(self.payments_tab_index, payments_widget, 'Оплаты')

                # ИСПРАВЛЕНИЕ: Возвращаемся на вкладку оплат, если она была активна
                if current_tab_index == self.payments_tab_index:
                    self.tabs.setCurrentIndex(self.payments_tab_index)

                print(f"Вкладка оплат обновлена")
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

                print(f"Вкладка информации о проекте обновлена")
            except Exception as e:
                print(f" Ошибка обновления вкладки информации: {e}")

    def create_project_data_widget(self):
        """Создание виджета данных по проекту"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        content_widget = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(8)
        form_layout.setContentsMargins(20, 15, 20, 20)
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
                border-radius: 4px;
                font-size: 10px;
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
        self.project_data_tz_file_label.setWordWrap(False)
        self.project_data_tz_file_label.setFixedHeight(28)  # Фиксированная высота для выравнивания
        self.project_data_tz_file_label.setTextFormat(Qt.RichText)  # Поддержка HTML для отображения ссылок
        self.project_data_tz_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.LinksAccessibleByMouse)
        self.project_data_tz_file_label.setOpenExternalLinks(True)
        self.project_data_tz_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        # ИСПРАВЛЕНИЕ: Добавляем обрезку текста с троеточием через CSS
        self.project_data_tz_file_label.setProperty('class', 'ellipsis-label')
        tz_file_row.addWidget(self.project_data_tz_file_label, 1)

        # Кнопка загрузки ТЗ
        if _has_perm(self.employee, self.api_client, 'crm_cards.files_upload'):
            self.upload_tz_btn = QPushButton('Загрузить файлы')
            self.upload_tz_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    border: none;
                    font-size: 10px;
                    max-height: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            self.upload_tz_btn.setFixedSize(120, 28)
            self.upload_tz_btn.clicked.connect(self.upload_project_tech_task_file)
            tz_file_row.addWidget(self.upload_tz_btn)

        # Кнопка удаления ТЗ
        if _has_perm(self.employee, self.api_client, 'crm_cards.files_delete'):
            delete_tz_btn = IconLoader.create_icon_button('delete', '', 'Удалить файл ТЗ', icon_size=14)
            delete_tz_btn.setFixedSize(28, 28)
            delete_tz_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                    min-height: 28px;
                    max-height: 28px;
                    min-width: 28px;
                    max-width: 28px;
                }
                QPushButton:hover { background-color: #C0392B; }
            """)
            delete_tz_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_tz_btn.clicked.connect(self.delete_tech_task_file)
            tz_file_row.addWidget(delete_tz_btn)

        tz_layout.addLayout(tz_file_row)

        hint_tz_file = QLabel('PDF файл с техническим заданием')
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
                border-radius: 4px;
                font-size: 10px;
            }
        ''')
        self.project_data_tz_date_label.setFixedHeight(28)  # Фиксированная высота для выравнивания
        tz_date_row.addWidget(self.project_data_tz_date_label, 1)

        # Кнопка изменения даты ТЗ
        if _has_perm(self.employee, self.api_client, 'crm_cards.deadlines'):
            edit_tz_date_btn = QPushButton('Изменить дату')
            edit_tz_date_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    border: none;
                    font-size: 10px;
                    max-height: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            edit_tz_date_btn.setFixedSize(156, 28)  # = 120 + 8 (spacing) + 28 = 156px
            edit_tz_date_btn.clicked.connect(self.edit_tech_task_date)
            tz_date_row.addWidget(edit_tz_date_btn)

        tz_layout.addLayout(tz_date_row)

        hint_tz_date = QLabel('Дата утверждения технического задания')
        hint_tz_date.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        tz_layout.addWidget(hint_tz_date)

        tz_group.setLayout(tz_layout)
        # ИСПРАВЛЕНИЕ: Устанавливаем размеры для группы ТЗ
        tz_group.setMinimumWidth(200)  # Минимальная ширина для читаемости
        tz_group.setMinimumHeight(130)  # Фиксированная минимальная высота для выравнивания
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
                border-radius: 4px;
                font-size: 10px;
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
        self.project_data_survey_file_label.setWordWrap(False)
        self.project_data_survey_file_label.setFixedHeight(28)
        self.project_data_survey_file_label.setTextFormat(Qt.RichText)  # Поддержка HTML для отображения ссылок
        self.project_data_survey_file_label.setTextInteractionFlags(Qt.TextBrowserInteraction | Qt.LinksAccessibleByMouse)
        self.project_data_survey_file_label.setOpenExternalLinks(True)
        self.project_data_survey_file_label.setCursor(QCursor(Qt.PointingHandCursor))
        # ИСПРАВЛЕНИЕ: Добавляем обрезку текста с троеточием через CSS
        self.project_data_survey_file_label.setProperty('class', 'ellipsis-label')
        survey_file_row.addWidget(self.project_data_survey_file_label, 1)

        # Кнопка загрузки замера
        if _has_perm(self.employee, self.api_client, 'crm_cards.files_upload'):
            self.upload_survey_btn = QPushButton('Загрузить файлы')
            self.upload_survey_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    border: none;
                    font-size: 10px;
                    max-height: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            self.upload_survey_btn.setFixedSize(120, 28)
            self.upload_survey_btn.clicked.connect(self.add_measurement)
            survey_file_row.addWidget(self.upload_survey_btn)

        # Кнопка удаления замера
        if _has_perm(self.employee, self.api_client, 'crm_cards.files_delete'):
            delete_survey_btn = IconLoader.create_icon_button('delete', '', 'Удалить изображение замера', icon_size=14)
            delete_survey_btn.setFixedSize(28, 28)
            delete_survey_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                    min-height: 28px;
                    max-height: 28px;
                    min-width: 28px;
                    max-width: 28px;
                }
                QPushButton:hover { background-color: #C0392B; }
            """)
            delete_survey_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_survey_btn.clicked.connect(self.delete_measurement_file)
            survey_file_row.addWidget(delete_survey_btn)

        survey_layout.addLayout(survey_file_row)

        hint_survey_file = QLabel('Фотография или сканированный лист замера')
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
                border-radius: 4px;
                font-size: 10px;
            }
        ''')
        self.project_data_survey_date_label.setFixedHeight(28)  # Фиксированная высота для выравнивания
        survey_date_row.addWidget(self.project_data_survey_date_label, 1)

        # Кнопка изменения даты замера
        if _has_perm(self.employee, self.api_client, 'crm_cards.deadlines'):
            edit_survey_date_btn = QPushButton('Изменить дату')
            edit_survey_date_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    border: none;
                    font-size: 10px;
                    max-height: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            edit_survey_date_btn.setFixedSize(156, 28)  # = 120 + 8 (spacing) + 28 = 156px
            edit_survey_date_btn.clicked.connect(self.edit_measurement_date)
            survey_date_row.addWidget(edit_survey_date_btn)

        survey_layout.addLayout(survey_date_row)

        hint_survey_date = QLabel('Дата выполнения замера объекта')
        hint_survey_date.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        survey_layout.addWidget(hint_survey_date)

        survey_group.setLayout(survey_layout)
        # ИСПРАВЛЕНИЕ: Устанавливаем размеры для группы Замера
        survey_group.setMinimumWidth(200)  # Минимальная ширина для читаемости
        survey_group.setMinimumHeight(130)  # Фиксированная минимальная высота для выравнивания
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

            # Кнопка добавления шаблонов
            if _has_perm(self.employee, self.api_client, 'crm_cards.files_upload'):
                add_template_btn = QPushButton('Загрузить шаблоны')
                # ИСПРАВЛЕНИЕ 07.02.2026: Стандартная высота 28px (#11,12)
                add_template_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E0E0E0;
                        color: #333333;
                        padding: 0px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        min-height: 28px;
                        max-height: 28px;
                    }
                    QPushButton:hover { background-color: #BDBDBD; }
                """)
                add_template_btn.setFixedHeight(28)
                add_template_btn.clicked.connect(self.add_project_templates)
                references_layout.addWidget(add_template_btn)

            hint_templates = QLabel('Ссылки на используемые в проекте шаблоны')
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
                    border-radius: 4px;
                    font-size: 10px;
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
            self.project_data_references_label.setWordWrap(False)
            self.project_data_references_label.setFixedHeight(28)
            self.project_data_references_label.setOpenExternalLinks(True)
            self.project_data_references_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
            self.project_data_references_label.setCursor(QCursor(Qt.PointingHandCursor))
            ref_folder_row.addWidget(self.project_data_references_label, 1)

            # Кнопка загрузки референсов
            if _has_perm(self.employee, self.api_client, 'crm_cards.files_upload'):
                self.upload_references_btn = QPushButton('Загрузить файлы')
                self.upload_references_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95a5a6;
                        color: white;
                        padding: 0px 10px;
                        border-radius: 6px;
                        border: none;
                        font-size: 10px;
                        max-height: 28px;
                        min-height: 28px;
                    }
                    QPushButton:hover { background-color: #7f8c8d; }
                """)
                self.upload_references_btn.setFixedSize(120, 28)
                self.upload_references_btn.clicked.connect(self.upload_references_files)
                ref_folder_row.addWidget(self.upload_references_btn)

            # Кнопка удаления референсов
            if _has_perm(self.employee, self.api_client, 'crm_cards.files_delete'):
                delete_references_btn = IconLoader.create_icon_button('delete', '', 'Удалить все референсы', icon_size=14)
                delete_references_btn.setFixedSize(28, 28)
                delete_references_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E74C3C;
                        color: white;
                        border: none;
                        border-radius: 6px;
                        padding: 0px;
                        min-height: 28px;
                        max-height: 28px;
                        min-width: 28px;
                        max-width: 28px;
                    }
                    QPushButton:hover { background-color: #C0392B; }
                """)
                delete_references_btn.setCursor(QCursor(Qt.PointingHandCursor))
                delete_references_btn.clicked.connect(self.delete_references_folder)
                ref_folder_row.addWidget(delete_references_btn)

            references_layout.addLayout(ref_folder_row)

            hint_references = QLabel('Изображения и PDF файлы с референсами')
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
                border-radius: 4px;
                font-size: 10px;
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
        self.project_data_photo_doc_label.setWordWrap(False)
        self.project_data_photo_doc_label.setFixedHeight(28)
        self.project_data_photo_doc_label.setOpenExternalLinks(True)
        self.project_data_photo_doc_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.project_data_photo_doc_label.setCursor(QCursor(Qt.PointingHandCursor))
        photo_doc_folder_row.addWidget(self.project_data_photo_doc_label, 1)

        # Кнопка загрузки фотофиксации
        if _has_perm(self.employee, self.api_client, 'crm_cards.files_upload'):
            self.upload_photo_doc_btn = QPushButton('Загрузить файлы')
            self.upload_photo_doc_btn.setStyleSheet("""
                QPushButton {
                    background-color: #95a5a6;
                    color: white;
                    padding: 0px 10px;
                    border-radius: 6px;
                    border: none;
                    font-size: 10px;
                    max-height: 28px;
                    min-height: 28px;
                }
                QPushButton:hover { background-color: #7f8c8d; }
            """)
            self.upload_photo_doc_btn.setFixedSize(120, 28)
            self.upload_photo_doc_btn.clicked.connect(self.upload_photo_documentation_files)
            photo_doc_folder_row.addWidget(self.upload_photo_doc_btn)

        # Кнопка удаления фотофиксации
        if _has_perm(self.employee, self.api_client, 'crm_cards.files_delete'):
            delete_photo_doc_btn = IconLoader.create_icon_button('delete', '', 'Удалить все файлы фотофиксации', icon_size=14)
            delete_photo_doc_btn.setFixedSize(28, 28)
            delete_photo_doc_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E74C3C;
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 0px;
                    min-height: 28px;
                    max-height: 28px;
                    min-width: 28px;
                    max-width: 28px;
                }
                QPushButton:hover { background-color: #C0392B; }
            """)
            delete_photo_doc_btn.setCursor(QCursor(Qt.PointingHandCursor))
            delete_photo_doc_btn.clicked.connect(self.delete_photo_documentation_folder)
            photo_doc_folder_row.addWidget(delete_photo_doc_btn)

        photo_doc_layout.addLayout(photo_doc_folder_row)

        hint_photo_doc = QLabel('Изображения, PDF и видео файлы с фотофиксацией')
        hint_photo_doc.setStyleSheet('color: #666; font-size: 9px; font-style: italic;')
        photo_doc_layout.addWidget(hint_photo_doc)

        photo_doc_group.setLayout(photo_doc_layout)
        ref_photo_row.addWidget(photo_doc_group, 1)  # Занимает 1 часть (50%)

        form_layout.addRow(ref_photo_row)

        # ========== Загрузка данных о правках по стадиям ==========
        self._corrections_by_stage = {}
        try:
            if self.data.is_multi_user:
                wf_states = self.data.get_workflow_state(self.card_data['id'])
                if wf_states and isinstance(wf_states, list):
                    for wf in wf_states:
                        rfp = wf.get('revision_file_path', '') or ''
                        sname = wf.get('stage_name', '') or ''
                        if rfp and sname:
                            self._corrections_by_stage[sname] = rfp
                elif wf_states and isinstance(wf_states, dict):
                    rfp = wf_states.get('revision_file_path', '') or ''
                    sname = wf_states.get('stage_name', '') or ''
                    if rfp and sname:
                        self._corrections_by_stage[sname] = rfp
        except Exception:
            pass

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

        # Стадия 1 — права на загрузку/удаление файлов через permissions
        emp_pos = self.employee.get('position', '') if self.employee else ''
        emp_sec = self.employee.get('secondary_position', '') if self.employee else ''
        is_only_draftsman = (emp_pos == 'Чертёжник' and emp_sec != 'Дизайнер')
        can_delete_stage1 = _has_perm(self.employee, self.api_client, 'crm_cards.files_delete')
        can_upload_stage1 = _has_perm(self.employee, self.api_client, 'crm_cards.files_upload')

        self.stage1_list = FileListWidget(
            title="PDF файлы планировочного решения",
            stage="stage1",
            file_types=['pdf'],
            can_delete=can_delete_stage1,
            can_upload=can_upload_stage1
        )
        self.stage1_list.upload_requested.connect(self.upload_stage_files)
        self.stage1_list.delete_requested.connect(self.delete_stage_file)
        self._add_corrections_button(self.stage1_list, 'Стадия 1')
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

            # Стадия 2 (шаблонные) — через permissions
            can_delete_stage2 = _has_perm(self.employee, self.api_client, 'crm_cards.files_delete')
            can_upload_stage2 = _has_perm(self.employee, self.api_client, 'crm_cards.files_upload')

            self.stage3_list = FileListWidget(  # используем stage3_list для совместимости с БД
                title="PDF и Excel файлы чертежного проекта",
                stage="stage3",
                file_types=['pdf', 'excel'],
                can_delete=can_delete_stage2,
                can_upload=can_upload_stage2
            )
            self.stage3_list.upload_requested.connect(self.upload_stage_files)
            self.stage3_list.delete_requested.connect(self.delete_stage_file)
            self._add_corrections_button(self.stage3_list, 'Стадия 2')
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

            # Стадия 3 (шаблонные) - могут удалять и загружать все кроме чистого чертёжника
            can_delete_stage3 = not is_only_draftsman
            can_upload_stage3 = not is_only_draftsman

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
            self._add_corrections_button(self.stage2_3d_gallery, 'Стадия 3')
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

            # Стадия 2 (индивидуальные) - могут удалять и загружать все кроме чистого чертёжника
            can_delete_stage2 = not is_only_draftsman
            can_upload_stage2 = not is_only_draftsman

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
            self._add_corrections_button(self.stage2_concept_gallery, 'Стадия 2')
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

            # Стадия 3 (индивидуальные) — через permissions
            can_delete_stage3 = _has_perm(self.employee, self.api_client, 'crm_cards.files_delete')
            can_upload_stage3 = _has_perm(self.employee, self.api_client, 'crm_cards.files_upload')

            self.stage3_list = FileListWidget(
                title="PDF и Excel файлы чертежного проекта",
                stage="stage3",
                file_types=['pdf', 'excel'],
                can_delete=can_delete_stage3,
                can_upload=can_upload_stage3
            )
            self.stage3_list.upload_requested.connect(self.upload_stage_files)
            self.stage3_list.delete_requested.connect(self.delete_stage_file)
            self._add_corrections_button(self.stage3_list, 'Стадия 3')
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
        layout.setContentsMargins(20, 15, 20, 20)

        header = QLabel('Информация о проекте')
        header.setStyleSheet('font-size: 13px; font-weight: bold; margin-bottom: 10px;')
        layout.addWidget(header)

        # Компактная отметка о замере (из card_data — единый источник)
        survey_date_str = self.card_data.get('survey_date', '')
        surveyor_name = self.card_data.get('surveyor_name', '')
        # Если ФИО нет в card_data, подтягиваем по surveyor_id
        if not surveyor_name:
            surveyor_id = self.card_data.get('surveyor_id')
            if surveyor_id:
                try:
                    emp = self.data.get_employee(surveyor_id)
                    if emp:
                        surveyor_name = emp.get('full_name', '')
                except Exception:
                    pass
        if survey_date_str:
            survey_qdate = QDate.fromString(survey_date_str, 'yyyy-MM-dd')
            survey_text = f"Замер выполнен: {survey_qdate.toString('dd.MM.yyyy')}"
            if surveyor_name:
                survey_text += f" | Замерщик: {surveyor_name}"
            survey_label = QLabel(survey_text)
            survey_label.setStyleSheet('''
                color: #27AE60;
                font-size: 10px;
                font-weight: bold;
                background-color: #E8F8F5;
                padding: 5px;
                border-radius: 4px;
                margin-bottom: 8px;
            ''')
            layout.addWidget(survey_label)

        # ========== НОВОЕ: ВЫПОЛНЕННЫЕ СТАДИИ ==========
        # Показываем стадии, которые были отмечены как сданные (completed = 1)
        try:
            conn = self.data.db.connect()
            cursor = conn.cursor()

            # ОТЛАДКА: Проверяем все записи в stage_executors для этой карточки
            cursor.execute('''
            SELECT se.stage_name, e.full_name as executor_name, se.completed, se.completed_date
            FROM stage_executors se
            LEFT JOIN employees e ON se.executor_id = e.id
            WHERE se.crm_card_id = ?
            ''', (self.card_data['id'],))

            all_stages = cursor.fetchall()
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
            self.data.db.close()

            if completed_stages:
                # Заголовок
                completed_header = QLabel('Выполненные стадии:')
                completed_header.setStyleSheet('font-size: 11px; font-weight: bold; color: #27AE60; margin-bottom: 4px; margin-top: 4px;')
                layout.addWidget(completed_header)

                # Контейнер для стадий
                for stage in completed_stages:
                    stage_dict = dict(stage) if not isinstance(stage, dict) else stage
                    date_str = format_date(stage_dict.get('completed_date'))

                    stage_label = QLabel(
                        f"{stage_dict.get('stage_name', '')} | Исполнитель: {stage_dict.get('executor_name', '')} | Дата: {date_str}"
                    )
                    stage_label.setStyleSheet('''
                        color: #27AE60;
                        font-size: 10px;
                        font-weight: bold;
                        background-color: #E8F8F5;
                        padding: 5px;
                        border-radius: 4px;
                        margin-bottom: 4px;
                    ''')
                    layout.addWidget(stage_label)

        except Exception as e:
            print(f" Ошибка загрузки выполненных стадий: {e}")
            import traceback
            traceback.print_exc()
        # ===============================================

        accepted_stages = self.data.get_accepted_stages(self.card_data['id'])

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
                stage_label = QLabel(f"{stage_text}")
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

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setStyleSheet('background-color: #E0E0E0; margin: 8px 0px;')
        separator.setFixedHeight(2)
        layout.addWidget(separator)

        history_header = QLabel('История ведения проекта')
        history_header.setStyleSheet('font-size: 12px; font-weight: bold; margin-bottom: 8px;')
        layout.addWidget(history_header)

        # Фильтр по типу действия
        filter_layout = QHBoxLayout()
        filter_label = QLabel('Фильтр:')
        filter_label.setStyleSheet('font-size: 10px; color: #666;')
        filter_layout.addWidget(filter_label)

        self._history_filter_combo = QComboBox()
        self._history_filter_combo.addItems([
            'Все действия',
            'Изменение дедлайна',
            'Загрузка файлов',
            'Удаление файлов',
            'Замер',
            'Дата ТЗ',
            'Прочее',
        ])
        self._history_filter_combo.setStyleSheet('font-size: 10px; padding: 2px 5px;')
        self._history_filter_combo.setFixedWidth(200)
        self._history_filter_combo.currentTextChanged.connect(self._on_history_filter_changed)
        filter_layout.addWidget(self._history_filter_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #DDD; border-radius: 4px; background: white; }")

        info_container = QWidget()
        self.info_layout = QVBoxLayout()
        self.info_layout.setSpacing(10)
        self.info_layout.setContentsMargins(10, 10, 10, 10)

        # Получаем историю стадий
        stages = self.data.get_stage_history(self.card_data['id'])

        # Получаем историю действий из API или локальной БД
        action_history_items = []
        try:
            if self.data.is_multi_user:
                # Загружаем через API
                try:
                    api_history = self.data.get_action_history('crm_card', self.card_data['id'])
                    # Преобразуем формат API в формат локальной БД
                    for item in api_history:
                        action_history_items.append({
                            'action_type': item.get('action_type', ''),
                            'description': item.get('description', ''),
                            'action_date': item.get('action_date', ''),
                            'user_name': item.get('user_name', 'Неизвестно')
                        })
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки истории: {e}, fallback на локальную БД")
                    # Fallback на локальную БД
                    conn = self.data.db.connect()
                    cursor = conn.cursor()
                    cursor.execute('''
                    SELECT ah.action_type, ah.description, ah.action_date, e.full_name as user_name
                    FROM action_history ah
                    LEFT JOIN employees e ON ah.user_id = e.id
                    WHERE ah.entity_type = 'crm_card' AND ah.entity_id = ?
                    ORDER BY ah.action_date DESC
                    ''', (self.card_data['id'],))
                    action_history_items = cursor.fetchall()
                    self.data.db.close()
            else:
                # Загружаем из локальной БД
                conn = self.data.db.connect()
                cursor = conn.cursor()

                cursor.execute('''
                SELECT ah.action_type, ah.description, ah.action_date, e.full_name as user_name
                FROM action_history ah
                LEFT JOIN employees e ON ah.user_id = e.id
                WHERE ah.entity_type = 'crm_card' AND ah.entity_id = ?
                ORDER BY ah.action_date DESC
                ''', (self.card_data['id'],))

                action_history_items = cursor.fetchall()
                self.data.db.close()
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки истории действий: {e}")

        # Сохраняем исходные данные для фильтрации
        self._all_history_items = action_history_items
        self._history_stages = stages

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
                except Exception:
                    date_str = action['action_date']

                action_text = f"{date_str} | {action['user_name']}: {action['description']}"

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
            submitted_label = QLabel(f"Сдано: {format_date(stage_dict.get('submitted_date'), 'N/A')}")
            submitted_label.setStyleSheet('font-size: 10px; color: #ffd93c; font-weight: bold;')
            stage_layout.addWidget(submitted_label)

        # Дата принятия (завершения)
        if stage_dict.get('completed'):
            completed_label = QLabel(f"Принято: {format_date(stage_dict.get('completed_date'), 'N/A')}")
            completed_label.setStyleSheet('font-size: 10px; color: #27AE60; font-weight: bold;')
            stage_layout.addWidget(completed_label)

        stage_frame.setLayout(stage_layout)
        return stage_frame

    def reload_project_history(self):
        """Обновление истории проекта без перезагрузки всей вкладки"""

        if not hasattr(self, 'info_layout'):
            return

        # Очищаем текущую историю
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Получаем историю стадий
        stages = []
        if self.card_data.get('id'):
            try:
                conn = self.data.db.connect()
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
            except Exception as e:
                print(f" Ошибка загрузки истории стадий: {e}")
                import traceback
                traceback.print_exc()

        # Получаем историю действий из API или локальной БД
        action_history_items = []
        try:
            if self.data.is_multi_user:
                # Загружаем через API
                try:
                    api_history = self.data.get_action_history('crm_card', self.card_data['id'])
                    # Преобразуем формат API в формат локальной БД
                    for item in api_history:
                        action_history_items.append({
                            'action_type': item.get('action_type', ''),
                            'description': item.get('description', ''),
                            'action_date': item.get('action_date', ''),
                            'user_name': item.get('user_name', 'Неизвестно')
                        })
                except Exception as e:
                    print(f"[WARN] Ошибка API загрузки истории: {e}, fallback на локальную БД")
                    # Fallback на локальную БД
                    conn = self.data.db.connect()
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
            else:
                conn = self.data.db.connect()
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
        except Exception as e:
            print(f"[ERROR] Ошибка загрузки истории действий: {e}")
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
                except Exception:
                    date_str = action['action_date']

                action_text = f"{date_str} | {action['user_name']}: {action['description']}"

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

    def _on_history_filter_changed(self, filter_text):
        """Фильтрация истории по типу действия"""
        if not hasattr(self, 'info_layout') or not hasattr(self, '_all_history_items'):
            return

        # Маппинг фильтров на action_type
        filter_map = {
            'Изменение дедлайна': ['deadline_changed', 'executor_deadline_changed'],
            'Загрузка файлов': ['file_upload'],
            'Удаление файлов': ['file_delete'],
            'Замер': ['survey_complete', 'survey_date_changed'],
            'Дата ТЗ': ['tech_task_date_changed'],
        }

        allowed_types = filter_map.get(filter_text)

        # Определяем отфильтрованные элементы
        if filter_text == 'Все действия':
            filtered_items = self._all_history_items
        elif filter_text == 'Прочее':
            # Все типы, не входящие ни в один фильтр
            all_known = set()
            for types in filter_map.values():
                all_known.update(types)
            filtered_items = [a for a in self._all_history_items
                              if a.get('action_type', '') not in all_known]
        elif allowed_types:
            filtered_items = [a for a in self._all_history_items
                              if a.get('action_type', '') in allowed_types]
        else:
            filtered_items = self._all_history_items

        # Очищаем текущий layout
        while self.info_layout.count():
            child = self.info_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        has_content = False

        # Рендерим отфильтрованные действия
        if filtered_items:
            has_content = True
            for action in filtered_items:
                from datetime import datetime
                try:
                    action_date = datetime.strptime(action['action_date'], '%Y-%m-%d %H:%M:%S')
                    date_str = action_date.strftime('%d.%m.%Y %H:%M')
                except Exception:
                    date_str = action['action_date']

                action_text = f"{date_str} | {action['user_name']}: {action['description']}"

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

        # Стадии показываем всегда (не фильтруются)
        stages = getattr(self, '_history_stages', [])
        if stages:
            has_content = True
            for stage in stages:
                stage_widget = self.create_stage_info_widget(stage)
                self.info_layout.addWidget(stage_widget)

        if not has_content:
            empty_label = QLabel('Нет записей по выбранному фильтру')
            empty_label.setStyleSheet('color: #999; font-size: 12px; padding: 20px;')
            empty_label.setAlignment(Qt.AlignCenter)
            self.info_layout.addWidget(empty_label)

        self.info_layout.addStretch()

    def load_data(self):
        # ИСПРАВЛЕНИЕ: Предотвращаем автосохранение во время загрузки
        self._loading_data = True

        # Загружаем данные из локальной БД (мгновенно) — они уже синхронизированы
        # Мержим вместо замены: single-card endpoint не содержит полей из контракта
        # (project_subtype, agent_type, address, area и др.), которые были в исходном card_data
        self.data.prefer_local = True
        try:
            if self.card_data and self.card_data.get('id'):
                fresh_data = self.data.get_crm_card(self.card_data['id'])
                if fresh_data:
                    self.card_data.update(fresh_data)
        finally:
            self.data.prefer_local = False

        # Обновляем подтип проекта (может не быть при первичной загрузке)
        if hasattr(self, 'subtype_val_label'):
            subtype = self.card_data.get('project_subtype') or ''
            self.subtype_val_label.setText(str(subtype) if subtype else 'Не указан')

        # Виджеты из вкладки "Редактирование" (могут отсутствовать для дизайнеров/чертежников)
        if hasattr(self, 'deadline_display'):
            # ИСПРАВЛЕНИЕ 30.01.2026: Если deadline в карточке пустой, берём из stage_executors
            deadline_str = self.card_data.get('deadline')
            if not deadline_str and self.card_data.get('stage_executors'):
                # Берём максимальный дедлайн из stage_executors
                try:
                    stage_executors = self.card_data.get('stage_executors', [])
                    deadlines = []
                    for se in stage_executors:
                        se_deadline = se.get('deadline')
                        if se_deadline:
                            deadlines.append(se_deadline)
                    if deadlines:
                        deadline_str = max(deadlines)  # Берём максимальный
                        print(f"[load_data] Дедлайн проекта взят из stage_executors: {deadline_str}")
                except Exception as e:
                    print(f"[WARNING] Ошибка получения дедлайна из stage_executors: {e}")

            if deadline_str:
                deadline_date = QDate.fromString(deadline_str, 'yyyy-MM-dd')
                self.deadline_display.setText(deadline_date.toString('dd.MM.yyyy'))
            else:
                self.deadline_display.setText('Не установлен')

        if hasattr(self, 'tags'):
            self.tags.setText(self.card_data.get('tags', ''))

        contract_id = self.card_data.get('contract_id')
        # Один запрос на контракт — кэшируем для всех секций load_data
        self._cached_contract = None
        if contract_id:
            self.data.prefer_local = True
            try:
                self._cached_contract = self.data.get_contract(contract_id)
            finally:
                self.data.prefer_local = False
            if self._cached_contract and self._cached_contract.get('status'):
                if hasattr(self, 'status_combo'):
                    self.status_combo.setCurrentText(self._cached_contract['status'])

        if hasattr(self, 'senior_manager'):
            self.set_combo_by_id(self.senior_manager, self.card_data.get('senior_manager_id'))
        # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
        if hasattr(self, 'sdp') and self.sdp:
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
                except Exception:
                    self.survey_date_label.setText('Не установлена')
            else:
                self.survey_date_label.setText('Не установлена')
        # ==========================================

        # ========== ЗАГРУЗКА ТЗ ==========
        # Используем кэшированный контракт (один запрос вместо нескольких)
        tech_task_link_from_contract = None
        tech_task_file_name_from_contract = None
        if self._cached_contract:
            tech_task_link_from_contract = self._cached_contract.get('tech_task_link')
            tech_task_file_name_from_contract = self._cached_contract.get('tech_task_file_name')

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
                self.upload_tz_btn.setEnabled(False)  # Деактивируем кнопку если файл загружен
        else:
            if hasattr(self, 'tech_task_file_label'):
                self.tech_task_file_label.setText('Не загружен')
            if hasattr(self, 'project_data_tz_file_label'):
                self.project_data_tz_file_label.setText('Не загружен')
            if hasattr(self, 'upload_tz_btn'):
                self.upload_tz_btn.setEnabled(True)  # Активируем кнопку если файл не загружен

        if self.card_data.get('tech_task_date'):
            from datetime import datetime
            try:
                tech_task_date = datetime.strptime(self.card_data['tech_task_date'], '%Y-%m-%d')
                date_str = tech_task_date.strftime('%d.%m.%Y')
                if hasattr(self, 'tech_task_date_label'):
                    self.tech_task_date_label.setText(date_str)
                if hasattr(self, 'project_data_tz_date_label'):
                    self.project_data_tz_date_label.setText(date_str)
            except Exception:
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
        # Файл замера — из кэшированного контракта
        if self._cached_contract:
            measurement_link = self._cached_contract.get('measurement_image_link')
            measurement_file_name = self._cached_contract.get('measurement_file_name')

            if measurement_link:
                file_name = measurement_file_name if measurement_file_name else 'Замер'
                truncated_name = self.truncate_filename(file_name)
                html_link = f'<a href="{measurement_link}" title="{file_name}">{truncated_name}</a>'
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText(html_link)
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(False)
            else:
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText('Не загружен')
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(True)
        else:
            if hasattr(self, 'project_data_survey_file_label'):
                self.project_data_survey_file_label.setText('Не загружен')
            if hasattr(self, 'upload_survey_btn'):
                self.upload_survey_btn.setEnabled(True)

        # Дата замера — из card_data (единый источник, синхронизирован с вкладкой "Исполнители")
        survey_date_val = self.card_data.get('survey_date', '')
        if not survey_date_val and self._cached_contract:
            survey_date_val = self._cached_contract.get('measurement_date', '')
        if survey_date_val:
            from datetime import datetime
            try:
                sd_obj = datetime.strptime(survey_date_val, '%Y-%m-%d')
                if hasattr(self, 'project_data_survey_date_label'):
                    self.project_data_survey_date_label.setText(sd_obj.strftime('%d.%m.%Y'))
            except Exception:
                if hasattr(self, 'project_data_survey_date_label'):
                    self.project_data_survey_date_label.setText('Не установлена')
        else:
            if hasattr(self, 'project_data_survey_date_label'):
                self.project_data_survey_date_label.setText('Не установлена')
        # ================================

        # ========== ЗАГРУЗКА РЕФЕРЕНСОВ И ФОТОФИКСАЦИИ ==========
        # Используем кэшированный контракт
        if self._cached_contract:
            ref_result = {
                'references_yandex_path': self._cached_contract.get('references_yandex_path'),
                'photo_documentation_yandex_path': self._cached_contract.get('photo_documentation_yandex_path')
            }
        else:
            ref_result = None

            if ref_result:
                references_path = ref_result.get('references_yandex_path')
                photo_doc_path = ref_result.get('photo_documentation_yandex_path')

                # Референсы
                if references_path:
                    html_link = f'<a href="{references_path}">Открыть папку с референсами</a>'
                    if hasattr(self, 'project_data_references_label'):
                        self.project_data_references_label.setText(html_link)
                else:
                    if hasattr(self, 'project_data_references_label'):
                        self.project_data_references_label.setText('Не загружена')

                # Фотофиксация
                if photo_doc_path:
                    html_link = f'<a href="{photo_doc_path}">Открыть папку с фотофиксацией</a>'
                    if hasattr(self, 'project_data_photo_doc_label'):
                        self.project_data_photo_doc_label.setText(html_link)
                else:
                    if hasattr(self, 'project_data_photo_doc_label'):
                        self.project_data_photo_doc_label.setText('Не загружена')
            else:
                if hasattr(self, 'project_data_references_label'):
                    self.project_data_references_label.setText('Не загружена')
                if hasattr(self, 'project_data_photo_doc_label'):
                    self.project_data_photo_doc_label.setText('Не загружена')
        # ================================

        # Проверяем файлы на Яндекс.Диске в фоновом режиме
        self.verify_files_on_yandex_disk()

        # Загружаем файлы ВСЕХ стадий одним запросом и распределяем локально
        self._load_all_stage_files_batch()

        # Фоновая валидация файлов стадий на Яндекс.Диске
        self.validate_stage_files_on_yandex()

        # ИСПРАВЛЕНИЕ: Разрешаем автосохранение после загрузки
        self._loading_data = False

        # Подключаем автосохранение после загрузки данных
        if not self.view_only:
            self.connect_autosave_signals()

    def set_combo_by_id(self, combo, employee_id):
        if employee_id:
            for i in range(combo.count()):
                if combo.itemData(i) == employee_id:
                    combo.setCurrentIndex(i)
                    break

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

    def verify_files_on_yandex_disk(self):
        """Проверка существования файлов на Яндекс.Диске в фоновом режиме"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        self._show_sync_label()

        def check_files():
            try:
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                if not yd.token:
                    print("[VERIFY] Токен Яндекс.Диска не установлен, пропуск проверки")
                    return

                # Получаем данные через DataAccess (API с fallback на локальную БД)
                contract = self.data.get_contract(contract_id)
                if not contract:
                    print(f"[VERIFY] Контракт {contract_id} не найден")
                    return

                needs_update = False
                update_data = {}

                # Проверяем тех.задание
                tz_path = contract.get('tech_task_yandex_path', '')
                if tz_path:
                    print(f"[VERIFY] Проверяем ТЗ: {tz_path}")
                    exists = yd.file_exists(tz_path)
                    print(f"[VERIFY] ТЗ существует: {exists}")
                    if not exists:
                        update_data['tech_task_link'] = ''
                        update_data['tech_task_yandex_path'] = ''
                        update_data['tech_task_file_name'] = ''
                        needs_update = True

                # Проверяем замер
                meas_path = contract.get('measurement_yandex_path', '')
                if meas_path:
                    print(f"[VERIFY] Проверяем замер: {meas_path}")
                    exists = yd.file_exists(meas_path)
                    print(f"[VERIFY] Замер существует: {exists}")
                    if not exists:
                        update_data['measurement_image_link'] = ''
                        update_data['measurement_yandex_path'] = ''
                        update_data['measurement_file_name'] = ''
                        needs_update = True

                # Референсы и фотофиксация проверяются через scan endpoint на сервере
                # (scan сам определяет наличие файлов и создаёт/очищает ссылки)

                if needs_update:
                    print(f"[VERIFY] Обновляем БД: {list(update_data.keys())}")
                    # Обновляем локальную БД
                    from database.db_manager import DatabaseManager
                    local_db = DatabaseManager()
                    conn = local_db.connect()
                    cursor = conn.cursor()
                    for key, value in update_data.items():
                        try:
                            cursor.execute(f'UPDATE contracts SET {key} = ? WHERE id = ?', (value, contract_id))
                        except Exception:
                            pass
                    conn.commit()
                    local_db.close()
                    print(f"[VERIFY] Обновлена локальная БД")

                    # Обновляем серверную БД
                    if self.data.is_online:
                        try:
                            self.data.update_contract(contract_id, update_data)
                            print(f"[VERIFY] Обновлена серверная БД")
                        except Exception as api_err:
                            print(f"[VERIFY] Ошибка обновления сервера: {api_err}")

                    # Обновляем UI через QTimer (thread-safe)
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self.refresh_file_labels)
                else:
                    print(f"[VERIFY] Все contract-level файлы на месте")

            except Exception as e:
                import traceback
                print(f"[ERROR] Ошибка при проверке файлов на Яндекс.Диске: {e}")
                traceback.print_exc()
            finally:
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, self._sync_ended.emit)

        thread = threading.Thread(target=check_files, daemon=True)
        thread.start()

    def validate_stage_files_on_yandex(self):
        """Фоновая валидация и синхронизация файлов стадий с Яндекс.Диском"""
        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        self._show_sync_label()

        # ИСПРАВЛЕНИЕ R-07: Кешируем is_online в main thread перед запуском фонового потока
        is_online = self.data.is_online

        def validate():
            try:
                from database.db_manager import DatabaseManager

                # Шаг 1: Сканируем ЯД на наличие новых файлов (не в БД)
                new_files_found = False
                contract_updated = False
                if is_online:
                    try:
                        scan_result = self.data.scan_contract_files(contract_id)
                        new_count = scan_result.get('new_files_added', 0)
                        contract_updated = scan_result.get('contract_updated', False)
                        if new_count > 0:
                            print(f"[YD-SYNC] Найдено {new_count} новых файлов на ЯД")
                            new_files_found = True
                        else:
                            print(f"[YD-SYNC] Новых файлов не найдено")
                        if contract_updated:
                            print(f"[YD-SYNC] Контракт обновлён (references/photo_documentation)")
                            # Синхронизируем локальную БД с обновлённым контрактом
                            try:
                                from utils.db_sync import sync_all_data
                                sync_all_data(self.data.api_client, self.data.db)
                            except Exception as sync_e:
                                print(f"[YD-SYNC] Ошибка синхронизации БД: {sync_e}")
                    except Exception as scan_err:
                        print(f"[YD-SYNC] Ошибка сканирования ЯД: {scan_err}")

                # Шаг 2: Загружаем актуальный список файлов
                all_files = []
                if is_online:
                    try:
                        api_files = self.data.get_project_files(contract_id)
                        if api_files:
                            all_files = api_files
                    except Exception as api_err:
                        print(f"[VALIDATE] Ошибка загрузки файлов из API: {api_err}")

                if not all_files:
                    local_db = DatabaseManager()
                    all_files = local_db.get_project_files(contract_id) or []

                if not all_files:
                    print(f"[VALIDATE] Нет файлов стадий для contract_id={contract_id}")
                    if new_files_found:
                        # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, self._reload_stage_files_signal.emit)
                    return

                print(f"[VALIDATE] Найдено {len(all_files)} файлов стадий, проверяем...")

                # Шаг 3: Серверная валидация (только если файлы загружены из API — ID серверные)
                removed_ids = []
                server_validated = False
                if is_online:
                    file_ids = [f['id'] for f in all_files if f.get('id')]
                    if file_ids:
                        try:
                            results = self.data.validate_files(file_ids, auto_clean=True)
                            if results:
                                removed_ids = [r['file_id'] for r in results if not r.get('exists', True)]
                                server_validated = True
                                print(f"[VALIDATE] Серверная валидация: {len(removed_ids)} мёртвых файлов")
                        except Exception as api_err:
                            print(f"[VALIDATE] Серверная валидация не удалась: {api_err}")

                # Fallback: прямая проверка через Яндекс.Диск клиент (для локальных файлов)
                if not server_validated:
                    print(f"[VALIDATE] Используем прямую проверку через Яндекс.Диск")
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    if not yd.token:
                        print("[VALIDATE] Токен не установлен, пропуск")
                        return
                    for f in all_files:
                        yp = f.get('yandex_path')
                        fid = f.get('id')
                        if yp and fid:
                            if not yd.file_exists(yp):
                                removed_ids.append(fid)
                                print(f"[VALIDATE] Файл не найден: {yp}")

                ui_needs_update = new_files_found or contract_updated

                if removed_ids:
                    if not server_validated:
                        local_db2 = DatabaseManager()
                        for fid in removed_ids:
                            try:
                                local_db2.delete_project_file(fid)
                            except Exception as del_err:
                                print(f"[VALIDATE] Ошибка удаления файла {fid}: {del_err}")
                        local_db2.close()
                    print(f"[VALIDATE] Удалено {len(removed_ids)} мёртвых файлов из локальной БД")
                    ui_needs_update = True
                else:
                    print(f"[VALIDATE] Все файлы стадий на месте")

                if ui_needs_update:
                    try:
                        # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                        from PyQt5.QtCore import QTimer
                        QTimer.singleShot(0, self._reload_stage_files_signal.emit)
                    except RuntimeError:
                        pass  # Диалог уже закрыт

            except Exception as e:
                import traceback
                print(f"[ERROR] Ошибка валидации файлов стадий: {e}")
                traceback.print_exc()
            finally:
                try:
                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    from PyQt5.QtCore import QTimer
                    QTimer.singleShot(0, self._sync_ended.emit)
                except RuntimeError:
                    pass  # Диалог уже закрыт

        thread = threading.Thread(target=validate, daemon=True)
        thread.start()

    def _reload_all_stage_files(self):
        """Перезагрузка файлов всех стадий после синхронизации с ЯД"""
        try:
            stages = ['measurement', 'stage1', 'stage2_concept', 'stage2_3d', 'stage3', 'references', 'photo_documentation']
            for stage in stages:
                if hasattr(self, f'{stage}_list') or hasattr(self, f'{stage}_gallery'):
                    self.reload_stage_files(stage)
            # Обновляем метки файлов и данные ТЗ (могли обновиться через scan)
            self.refresh_file_labels()
            print("[YD-SYNC] UI файлов обновлен")
        except Exception as e:
            print(f"[ERROR] Ошибка обновления UI файлов: {e}")

    def refresh_file_labels(self):
        """Обновление меток файлов после проверки"""

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return


        # Перезагружаем данные через DataAccess
        try:
            result = self.data.get_contract(contract_id)

            if not result:
                return

            # Обновляем метку ТЗ
            tz_link = result.get('tech_task_link') or ''
            tz_yp = result.get('tech_task_yandex_path') or ''
            if tz_link or tz_yp:
                file_name = result.get('tech_task_file_name') or 'ТехЗадание.pdf'
                truncated_name = self.truncate_filename(file_name)
                if tz_link:
                    html_link = f'<a href="{tz_link}" title="{file_name}">{truncated_name}</a>'
                else:
                    html_link = truncated_name

                if hasattr(self, 'tech_task_file_label'):
                    self.tech_task_file_label.setText(html_link)
                if hasattr(self, 'project_data_tz_file_label'):
                    self.project_data_tz_file_label.setText(html_link)
                if hasattr(self, 'upload_tz_btn'):
                    self.upload_tz_btn.setEnabled(False)
            else:
                if hasattr(self, 'tech_task_file_label'):
                    self.tech_task_file_label.setText('Не загружен')
                if hasattr(self, 'project_data_tz_file_label'):
                    self.project_data_tz_file_label.setText('Не загружен')
                if hasattr(self, 'upload_tz_btn'):
                    self.upload_tz_btn.setEnabled(True)

            # Обновляем метку замера
            meas_link = result.get('measurement_image_link') or ''
            meas_yp = result.get('measurement_yandex_path') or ''
            if meas_link or meas_yp:
                file_name = result.get('measurement_file_name') or 'Замер'
                truncated_name = self.truncate_filename(file_name)
                if meas_link:
                    html_link = f'<a href="{meas_link}" title="{file_name}">{truncated_name}</a>'
                else:
                    html_link = truncated_name

                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText(html_link)
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(False)
            else:
                if hasattr(self, 'project_data_survey_file_label'):
                    self.project_data_survey_file_label.setText('Не загружен')
                if hasattr(self, 'upload_survey_btn'):
                    self.upload_survey_btn.setEnabled(True)

            # Обновляем метку референсов
            ref_path = result.get('references_yandex_path') or ''
            if ref_path:
                html_link = f'<a href="{ref_path}">Открыть папку с референсами</a>'
                if hasattr(self, 'project_data_references_label'):
                    self.project_data_references_label.setText(html_link)
            else:
                if hasattr(self, 'project_data_references_label'):
                    self.project_data_references_label.setText('Не загружена')

            # Загружаем шаблоны проектов (для шаблонных проектов)
            project_type = self.card_data.get('project_type', 'Индивидуальный')
            if project_type == 'Шаблонный' and hasattr(self, 'templates_container'):
                self.load_project_templates()

            # Обновляем метку фотофиксации
            if result['photo_documentation_yandex_path']:
                html_link = f'<a href="{result["photo_documentation_yandex_path"]}">Открыть папку с фотофиксацией</a>'
                if hasattr(self, 'project_data_photo_doc_label'):
                    self.project_data_photo_doc_label.setText(html_link)
            else:
                if hasattr(self, 'project_data_photo_doc_label'):
                    self.project_data_photo_doc_label.setText('Не загружена')

            # Перезагружаем файлы стадий (могли быть удалены валидацией)
            if hasattr(self, 'stage1_list'):
                self.reload_stage_files('stage1')
            if hasattr(self, 'stage2_concept_gallery'):
                self.reload_stage_files('stage2_concept')
            if hasattr(self, 'stage2_3d_gallery'):
                self.reload_stage_files('stage2_3d')
            if hasattr(self, 'stage3_list'):
                self.reload_stage_files('stage3')

        except Exception as e:
            print(f"[ERROR REFRESH] Ошибка при обновлении меток: {e}")

    def connect_autosave_signals(self):
        """ИСПРАВЛЕНИЕ: Подключение сигналов для автосохранения данных при изменении"""
        # Подключаем сигналы только для существующих виджетов
        if hasattr(self, 'status_combo'):
            self.status_combo.currentIndexChanged.connect(self.auto_save_field)
        if hasattr(self, 'senior_manager'):
            self.senior_manager.currentIndexChanged.connect(self.auto_save_field)
        # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
        if hasattr(self, 'sdp') and self.sdp:
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
            # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
            if hasattr(self, 'sdp') and self.sdp:
                updates['sdp_id'] = self.sdp.currentData()
            if hasattr(self, 'gap'):
                updates['gap_id'] = self.gap.currentData()
            if hasattr(self, 'manager'):
                updates['manager_id'] = self.manager.currentData()
            if hasattr(self, 'surveyor'):
                updates['surveyor_id'] = self.surveyor.currentData()

            self.data.update_crm_card(self.card_data["id"], updates)

            # Обновляем статус контракта
            contract_id = self.card_data.get('contract_id')
            if contract_id and hasattr(self, 'status_combo'):
                new_status = self.status_combo.currentText()
                # ИСПРАВЛЕНИЕ: Синхронизация статуса с API
                if self.data.is_online:
                    try:
                        self.data.update_contract(contract_id, {'status': new_status})
                        print(f"[API] Статус договора обновлен: {new_status}")

                        # ИСПРАВЛЕНИЕ: Если статус АВТОРСКИЙ НАДЗОР - создаём карточку надзора
                        if new_status == 'АВТОРСКИЙ НАДЗОР':
                            try:
                                # Проверяем существует ли уже карточка надзора
                                supervision_cards = self.data.get_supervision_cards()
                                existing = [c for c in supervision_cards if c.get('contract_id') == contract_id]
                                if not existing:
                                    result = self.data.create_supervision_card({
                                        'contract_id': contract_id,
                                        'column_name': 'Новый заказ'
                                    })
                                    print(f"[API] Создана карточка надзора ID={result.get('id')} для договора {contract_id}")
                                else:
                                    print(f"[INFO] Карточка надзора для договора {contract_id} уже существует")
                            except Exception as sup_e:
                                print(f"[WARN] Ошибка создания карточки надзора через API: {sup_e}")
                                # Fallback на локальную БД
                                self.data.create_supervision_card(contract_id)
                    except Exception as e:
                        print(f"[WARN] Ошибка API обновления статуса: {e}, fallback на локальную БД")
                        self.data.update_contract(contract_id, {'status': new_status})
                else:
                    self.data.update_contract(contract_id, {'status': new_status})

            # ИСПРАВЛЕНИЕ: Удаляем оплаты при снятии назначения сотрудника
            if contract_id:
                conn = self.data.db.connect()
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
                            print(f"Создана новая запись оплаты для роли '{role_name}' (ID: {new_id}), старая помечена как переназначенная")

                    # Если был назначен сотрудник, а теперь "Не назначен" (None)
                    elif old_id is not None and new_id is None:
                        cursor.execute('''
                        DELETE FROM payments
                        WHERE contract_id = ? AND employee_id = ? AND role = ?
                        ''', (contract_id, old_id, role_name))

                        if cursor.rowcount > 0:
                            payment_deleted = True
                            print(f"Удалена оплата для роли '{role_name}' (ID сотрудника: {old_id})")

                conn.commit()
                self.data.db.close()

                # Обновляем вкладку оплат если были удаления
                if payment_deleted:
                    self.refresh_payments_tab()

            # Обновляем данные карточки
            self.card_data.update(updates)

            # ИСПРАВЛЕНИЕ: Не обновляем канбан при автосохранении, чтобы не закрывать диалог
            # Обновление канбана произойдет при закрытии диалога через метод reject()

            print("Данные автоматически сохранены")

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
        # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
        if hasattr(self, 'sdp') and self.sdp:
            updates['sdp_id'] = self.sdp.currentData()
        if hasattr(self, 'gap'):
            updates['gap_id'] = self.gap.currentData()
        if hasattr(self, 'manager'):
            updates['manager_id'] = self.manager.currentData()
        if hasattr(self, 'surveyor'):
            updates['surveyor_id'] = self.surveyor.currentData()

        # Сохраняем только если есть что обновлять
        if updates:
            self.data.update_crm_card(self.card_data["id"], updates)

        # Дедлайны исполнителей сохраняются через change_executor_deadline()
        # (read-only QLabel, изменение только через диалог с причиной)

        contract_id = self.card_data.get('contract_id')
        if contract_id and hasattr(self, 'status_combo'):
            new_status = self.status_combo.currentText()
            # Обновляем статус через DataAccess
            self.data.update_contract(contract_id, {'status': new_status})
            print(f"[DataAccess] Статус договора обновлен: {new_status}")

            # Если статус АВТОРСКИЙ НАДЗОР - создаём карточку надзора
            if new_status == 'АВТОРСКИЙ НАДЗОР':
                try:
                    if self.data.is_multi_user:
                        supervision_cards = self.data.get_supervision_cards()
                        existing = [c for c in supervision_cards if c.get('contract_id') == contract_id]
                        if not existing:
                            result = self.data.create_supervision_card({
                                'contract_id': contract_id,
                                'column_name': 'Новый заказ'
                            })
                            print(f"[DataAccess] Создана карточка надзора для договора {contract_id}")
                        else:
                            print(f"[INFO] Карточка надзора для договора {contract_id} уже существует")
                    else:
                        self.data.create_supervision_card(contract_id)
                except Exception as sup_e:
                    print(f"[WARN] Ошибка создания карточки надзора: {sup_e}")

            # ИСПРАВЛЕНИЕ: Установка отчетного месяца при закрытии проекта
            if new_status in ['СДАН', 'АВТОРСКИЙ НАДЗОР']:
                current_month = QDate.currentDate().toString('yyyy-MM')

                # Обновляем отчетный месяц для менеджеров и ГАП
                conn = self.data.db.connect()
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
                self.data.db.close()

                print(f"Отчетный месяц {current_month} установлен для менеджеров и доплаты СДП")

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
            self.data.update_crm_card(self.card_data["id"], updates)
            # Обновляем локальные данные карточки
            self.card_data[field_name] = employee_id
            print(f"OK Обновлено поле {field_name} в CRM карточке")

        try:
            # Удаляем существующие выплаты для этой роли
            if self.data.is_multi_user:
                try:
                    # Получаем все выплаты и удаляем те, что для этой роли
                    payments = self.data.get_payments_for_contract(contract_id)
                    deleted_count = 0
                    for p in payments:
                        if p.get('role') == role_name:
                            self.data.delete_payment(p['id'])
                            deleted_count += 1
                    if deleted_count > 0:
                        print(f"Удалено {deleted_count} старых выплат через API для роли {role_name}")
                except Exception as e:
                    print(f"[WARNING] Ошибка удаления выплат через API: {e}")
            else:
                conn = self.data.db.connect()
                cursor = conn.cursor()
                cursor.execute('''
                DELETE FROM payments
                WHERE contract_id = ? AND role = ?
                ''', (contract_id, role_name))
                deleted_count = cursor.rowcount
                if deleted_count > 0:
                    print(f"Удалено {deleted_count} старых выплат для роли {role_name}")
                conn.commit()
                self.data.db.close()

            # Если выбран сотрудник (не "Не назначен"), создаем новые выплаты
            if employee_id:
                # ИСПРАВЛЕНИЕ 07.02.2026: Для шаблонных проектов СМП и Менеджер
                # получают оплату по окладу, платежи в CRM создавать НЕ нужно (#17)
                project_type = self.card_data.get('project_type', '')
                if project_type == 'Шаблонный' and role_name in ['Старший менеджер проектов', 'Менеджер']:
                    print(f"[SKIP] Пропуск создания платежа для {role_name} в шаблонном проекте (оплата по окладу)")
                    # Обновляем вкладку оплат и выходим
                    self.refresh_payments_tab()
                    return

                # Специальная обработка для СДП - создаем аванс и доплату
                if role_name == 'СДП':
                    # ИСПРАВЛЕНО: Рассчитываем сумму через API или локальную БД
                    if self.data.is_multi_user:
                        try:
                            result = self.data.calculate_payment_amount(contract_id, employee_id, role_name)
                            # ИСПРАВЛЕНИЕ 25.01.2026: API возвращает число, а не словарь
                            full_amount = float(result) if result else 0
                            print(f"[API] Рассчитана сумма для СДП: {full_amount:.2f} ₽")
                        except Exception as e:
                            print(f"[WARN] Ошибка API расчета суммы СДП: {e}, fallback на локальную БД")
                            full_amount = self.data.calculate_payment_amount(contract_id, employee_id, role_name)
                    else:
                        full_amount = self.data.calculate_payment_amount(contract_id, employee_id, role_name)

                    if full_amount == 0:
                        print(f"[WARN] Тариф для СДП = 0 или не установлен. Создаем оплату с нулевой суммой")

                    advance_amount = full_amount / 2
                    balance_amount = full_amount / 2

                    from PyQt5.QtCore import QDate
                    current_month = QDate.currentDate().toString('yyyy-MM')

                    # ИСПРАВЛЕНИЕ 06.02.2026: Добавлен fallback на локальную БД при ошибке API (#16)
                    payments_created = False
                    if self.data.is_multi_user:
                        try:
                            # Создаем аванс через API
                            advance_data = {
                                'contract_id': contract_id,
                                'crm_card_id': self.card_data['id'],
                                'employee_id': employee_id,
                                'role': role_name,
                                'stage_name': None,
                                'calculated_amount': advance_amount,
                                'final_amount': advance_amount,
                                'payment_type': 'Аванс',
                                'report_month': current_month
                            }
                            advance_result = self.data.create_payment(advance_data)

                            # Создаем доплату через API
                            balance_data = {
                                'contract_id': contract_id,
                                'crm_card_id': self.card_data['id'],
                                'employee_id': employee_id,
                                'role': role_name,
                                'stage_name': None,
                                'calculated_amount': balance_amount,
                                'final_amount': balance_amount,
                                'payment_type': 'Доплата',
                                'report_month': None  # None для статуса "В работе"
                            }
                            balance_result = self.data.create_payment(balance_data)

                            payments_created = True
                            print(f"Созданы аванс и доплата через API для СДП")
                        except Exception as e:
                            print(f"[WARNING] Ошибка создания выплат СДП через API: {e}, fallback на локальную БД")

                    # Fallback на локальную БД если API не сработал
                    if not payments_created:
                        # Создаем через локальную БД
                        conn = self.data.db.connect()
                        cursor = conn.cursor()

                        cursor.execute('''
                        INSERT INTO payments
                        (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                         final_amount, payment_type, report_month)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (contract_id, self.card_data['id'], employee_id, role_name, None, advance_amount,
                              advance_amount, 'Аванс', current_month))

                        advance_id = cursor.lastrowid

                        cursor.execute('''
                        INSERT INTO payments
                        (contract_id, crm_card_id, employee_id, role, stage_name, calculated_amount,
                         final_amount, payment_type, report_month)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (contract_id, self.card_data['id'], employee_id, role_name, None, balance_amount,
                              balance_amount, 'Доплата', None))

                        balance_id = cursor.lastrowid

                        conn.commit()
                        self.data.db.close()

                        print(f"Созданы аванс (ID={advance_id}, {advance_amount:.2f} ₽) и доплата (ID={balance_id}, {balance_amount:.2f} ₽) для СДП (локально)")

                # Для остальных ролей - создаем одну выплату "Полная оплата"
                else:
                    # ИСПРАВЛЕНО: Рассчитываем сумму через API или локальную БД
                    calculated_amount = 0
                    if self.data.is_multi_user:
                        try:
                            result = self.data.calculate_payment_amount(
                                contract_id, employee_id, role_name
                            )
                            # ИСПРАВЛЕНИЕ 25.01.2026: API возвращает число, а не словарь
                            calculated_amount = float(result) if result else 0
                            print(f"[API] Рассчитана сумма для {role_name}: {calculated_amount:.2f} ₽")
                        except Exception as e:
                            print(f"[WARN] Ошибка API расчета суммы: {e}, fallback на локальную БД")
                            calculated_amount = self.data.calculate_payment_amount(
                                contract_id, employee_id, role_name
                            )
                    else:
                        calculated_amount = self.data.calculate_payment_amount(
                            contract_id, employee_id, role_name
                        )

                    # ИСПРАВЛЕНИЕ 06.02.2026: Добавлен fallback на локальную БД при ошибке API (#16)
                    payment_created = False
                    if self.data.is_multi_user:
                        try:
                            payment_data = {
                                'contract_id': contract_id,
                                'employee_id': employee_id,
                                'role': role_name,
                                'payment_type': 'Полная оплата',
                                'report_month': None,  # None для статуса "В работе" - отобразится как "в работе"
                                'crm_card_id': self.card_data['id'],
                                'calculated_amount': calculated_amount,
                                'final_amount': calculated_amount
                            }
                            result = self.data.create_payment(payment_data)
                            payment_created = True
                            print(f"Создана выплата через API для роли {role_name}, сумма: {calculated_amount:.2f} ₽")
                        except Exception as e:
                            print(f"[WARNING] Ошибка создания выплаты через API: {e}, fallback на локальную БД")

                    # Fallback на локальную БД если API не сработал
                    if not payment_created:
                        payment_id = self.data.create_payment_record(
                            contract_id, employee_id, role_name,
                            payment_type='Полная оплата',
                            report_month=None,  # None для статуса "В работе"
                            crm_card_id=self.card_data['id']
                        )

                        if payment_id:
                            print(f"Создана выплата ID={payment_id} для роли {role_name} (локально)")
            else:
                print(f"[INFO] Сотрудник не назначен, выплаты удалены")

            # Обновляем вкладку оплат
            self.refresh_payments_tab()
            print(f"Вкладка оплат обновлена")

        except Exception as e:
            print(f"[ERROR] Ошибка при обновлении выплат: {e}")
            import traceback
            traceback.print_exc()

    def reassign_executor_from_dialog(self, executor_type):
        """Переназначение исполнителя из диалога редактирования"""
        # Проверка на None, чтобы избежать AttributeError
        if self.card_data is None:
            CustomMessageBox(
                self,
                'Ошибка',
                'Данные карточки не загружены. Пожалуйста, закройте диалог и попробуйте снова.',
                'error'
            ).exec_()
            return

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
        from ui.crm_tab import ReassignExecutorDialog
        dialog = ReassignExecutorDialog(
            self,
            self.card_data['id'],
            position,
            stage_keyword,
            executor_type,
            current_name,
            current_column,
            api_client=self.api_client
        )
        
        if dialog.exec_() == QDialog.Accepted:
            # ИСПРАВЛЕНИЕ: Обновляем данные карточки (пробуем API, потом БД)
            self.card_data = self.data.get_crm_card(self.card_data['id'])

            # Обновляем только отображаемые данные исполнителей без полной перезагрузки
            self._loading_data = True  # Отключаем автосохранение

            # Обновляем блоки дизайнера и чертежника
            if hasattr(self, 'designer_name_label') and self.card_data.get('designer_name'):
                self.designer_name_label.setText(self.card_data['designer_name'])
            if hasattr(self, 'designer_deadline_display') and self.designer_deadline_display and self.card_data.get('designer_deadline'):
                self.designer_deadline_value = self.card_data['designer_deadline']
                d = QDate.fromString(self.designer_deadline_value, 'yyyy-MM-dd')
                if d.isValid():
                    self.designer_deadline_display.setText(d.toString('dd.MM.yyyy'))

            if hasattr(self, 'draftsman_name_label') and self.card_data.get('draftsman_name'):
                self.draftsman_name_label.setText(self.card_data['draftsman_name'])
            if hasattr(self, 'draftsman_deadline_display') and self.draftsman_deadline_display and self.card_data.get('draftsman_deadline'):
                self.draftsman_deadline_value = self.card_data['draftsman_deadline']
                d = QDate.fromString(self.draftsman_deadline_value, 'yyyy-MM-dd')
                if d.isValid():
                    self.draftsman_deadline_display.setText(d.toString('dd.MM.yyyy'))

            self._loading_data = False  # Включаем обратно автосохранение

            # ИСПРАВЛЕНИЕ 06.02.2026: Обновляем вкладку оплат после переназначения (#6)
            self.refresh_payments_tab()

            # ИСПРАВЛЕНИЕ: Не вызываем parent.refresh_current_tab() здесь,
            # чтобы не закрывать диалог. Обновление канбана произойдет при закрытии диалога.

            # Показываем сообщение об успехе без закрытия диалога
            CustomMessageBox(
                self,
                'Успех',
                'Исполнитель переназначен! Данные обновлены.',
                'success'
            ).exec_()

            print("Исполнитель переназначен, диалог остался открытым")       
    
    def delete_order(self):
        """Удаление заказа"""
        from ui.crm_tab import CRMTab
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
            f"• Папка на Яндекс.Диске\n"
            f"• Все связанные данные (исполнители, этапы согласования)"
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                contract_id = self.card_data.get('contract_id')
                crm_card_id = self.card_data.get('id')

                # Сначала находим родителя до закрытия диалога
                crm_tab_parent = None
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        crm_tab_parent = parent
                        break
                    parent = parent.parent()

                # Удаление через API или локально
                if self.data.is_multi_user:
                    try:
                        # API режим - удаляем через API
                        self.data.delete_contract(contract_id)
                        print(f"[OK] Договор удален через API: {contract_id}")
                    except Exception as e:
                        print(f"[ERROR] Ошибка API удаления: {e}")
                        # Fallback на локальное удаление
                        self.data.delete_order(contract_id, crm_card_id)
                else:
                    # Локальный режим
                    self.data.delete_order(contract_id, crm_card_id)

                CustomMessageBox(
                    self,
                    'Успех',
                    'Заказ успешно удален из системы',
                    'success'
                ).exec_()

                # Закрываем диалог
                self.accept()

                # Обновляем родительский CRM таб
                if crm_tab_parent:
                    crm_tab_parent.refresh_current_tab()

            except Exception as e:
                print(f" Ошибка удаления заказа: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить заказ:\n{str(e)}', 'error').exec_()
                
    # =========================
    # МЕТОДЫ МЕССЕНДЖЕР-ЧАТА
    # =========================

    def _load_messenger_chat_state(self):
        """Загрузить состояние чата и обновить кнопки"""
        try:
            crm_card_id = self.card_data.get('id')
            if crm_card_id and hasattr(self, 'data_access') and self.data_access:
                self._messenger_chat_data = self.data_access.get_messenger_chat(crm_card_id)
            elif crm_card_id and self.data.is_multi_user:
                self._messenger_chat_data = self.data.get_messenger_chat(crm_card_id)
            else:
                self._messenger_chat_data = None
        except Exception:
            self._messenger_chat_data = None

        self._update_chat_buttons_state()

    def _update_chat_buttons_state(self):
        """Обновить enabled/disabled состояние кнопок чата"""
        has_chat = (
            self._messenger_chat_data is not None
            and self._messenger_chat_data.get('chat', {}).get('is_active', False)
        )
        is_online = self.data.is_multi_user

        if hasattr(self, 'create_chat_btn'):
            self.create_chat_btn.setEnabled(not has_chat and is_online)
            self.open_chat_btn.setEnabled(has_chat)
            self.delete_chat_btn.setEnabled(has_chat and is_online)

            # Кнопки скриптов доступны только при наличии чата и подключении к серверу
            if hasattr(self, 'start_script_btn'):
                self.start_script_btn.setEnabled(has_chat and is_online)
                self.end_script_btn.setEnabled(has_chat and is_online)

            if not is_online:
                self.create_chat_btn.setToolTip("Требуется подключение к серверу")
                self.delete_chat_btn.setToolTip("Требуется подключение к серверу")
            elif has_chat:
                self.create_chat_btn.setToolTip("Чат уже создан")
            else:
                self.delete_chat_btn.setToolTip("Чат не создан")
                self.open_chat_btn.setToolTip("Чат не создан")

    def _on_create_chat(self):
        """Обработчик кнопки 'Создать чат'"""
        from ui.messenger_select_dialog import MessengerSelectDialog
        dialog = MessengerSelectDialog(
            parent=self,
            card_data=self.card_data,
            api_client=self.api_client,
            db=self.db,
            data_access=getattr(self, 'data_access', None),
            employee=self.employee,
        )
        if dialog.exec_() == QDialog.Accepted:
            self._messenger_chat_data = dialog.result_chat_data
            self._update_chat_buttons_state()

    def _on_open_chat(self):
        """Обработчик кнопки 'Открыть чат'"""
        if not self._messenger_chat_data:
            return

        chat = self._messenger_chat_data.get('chat', {})
        invite_link = chat.get('invite_link', '')

        if invite_link:
            from PyQt5.QtGui import QDesktopServices
            from PyQt5.QtCore import QUrl
            QDesktopServices.openUrl(QUrl(invite_link))
        else:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(
                self, 'Ошибка',
                'Ссылка на чат не найдена. Попробуйте пересоздать чат.',
                'error'
            ).exec_()

    def _on_delete_chat(self):
        """Обработчик кнопки 'Удалить чат'"""
        if not self._messenger_chat_data:
            return

        from ui.custom_message_box import CustomQuestionBox
        reply = CustomQuestionBox(
            self,
            'Удаление чата',
            'Внимание! Все сообщения в чате будут удалены безвозвратно.\n\n'
            'Вы уверены, что хотите удалить чат?'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                chat = self._messenger_chat_data.get('chat', {})
                chat_id = chat.get('id')
                if chat_id:
                    if hasattr(self, 'data_access') and self.data_access:
                        self.data_access.delete_messenger_chat(chat_id)
                    elif self.data.is_multi_user:
                        self.data.delete_messenger_chat(chat_id)

                    self._messenger_chat_data = None
                    self._update_chat_buttons_state()

                    from ui.custom_message_box import CustomMessageBox
                    CustomMessageBox(self, 'Успех', 'Чат успешно удалён', 'success').exec_()
            except Exception as e:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить чат:\n{str(e)}', 'error').exec_()

    def _on_send_start_script(self):
        """Отправить начальный скрипт в чат"""
        card_id = self.card_data.get('id') if self.card_data else None
        if not card_id:
            return
        try:
            result = self.data.trigger_script(card_id, 'project_start')
            if result:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Скрипт', 'Начальный скрипт отправлен в чат', 'success').exec_()
            else:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Ошибка', 'Не удалось отправить скрипт', 'warning').exec_()
        except Exception as e:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', str(e), 'error').exec_()

    def _on_send_end_script(self):
        """Отправить завершающий скрипт в чат"""
        card_id = self.card_data.get('id') if self.card_data else None
        if not card_id:
            return
        try:
            result = self.data.trigger_script(card_id, 'project_end')
            if result:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Скрипт', 'Завершающий скрипт отправлен в чат', 'success').exec_()
            else:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Ошибка', 'Не удалось отправить скрипт', 'warning').exec_()
        except Exception as e:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', str(e), 'error').exec_()

    def _on_chat_admin(self):
        """Обработчик кнопки 'Настройки чатов' (Директор)"""
        from ui.messenger_admin_dialog import MessengerAdminDialog
        dialog = MessengerAdminDialog(
            parent=self,
            api_client=self.api_client,
            data_access=getattr(self, 'data_access', None),
            employee=self.employee,
        )
        dialog.exec_()

    def create_payments_tab(self):
        """Создание вкладки оплат с раздельными блоками для каждой группы"""
        import re

        # Стиль для GroupBox как в других вкладках
        # ИСПРАВЛЕНИЕ 07.02.2026: Минимальные отступы чтобы контент начинался от верха (#11,12)
        GROUP_BOX_STYLE = """
            QGroupBox {
                font-weight: bold;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
                margin-top: 4px;
                padding-top: 2px;
                background-color: #FAFAFA;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #2C3E50;
            }
        """

        # Стиль для таблиц без выделения ячеек
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
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # Scroll Area для всей вкладки
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background-color: transparent; border: none; }")

        scroll_content = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 15, 20, 20)

        # Загружаем выплаты из API или БД
        payments = self.data.get_payments_for_contract(self.card_data['contract_id'])

        # Приоритеты ролей
        role_priority = {
            'Старший менеджер проектов': 1,
            'СДП': 2,
            'ГАП': 3,
            'Менеджер': 4,
            'Менеджер проектов': 4,
            'Помощник менеджера': 4,
            'Замерщик': 5,
            'Дизайнер': 6,
            'Чертёжник': 7,
        }
        payment_type_priority = {'Аванс': 1, 'Доплата': 2, 'Полная оплата': 3}

        def get_stage_num(stage):
            if stage:
                match = re.search(r'[Сс]тадия\s*(\d+)', stage)
                if match:
                    return int(match.group(1))
            return 0

        # ИСПРАВЛЕНИЕ: Сортировка исполнителей по стадии -> сотрудник -> тип платежа
        def payment_sort_key(p):
            role = p.get('role', '')
            ptype = p.get('payment_type', '')
            stage = p.get('stage_name', '') or ''
            employee_id = p.get('employee_id', 0)
            payment_id = p.get('id', 0)
            stage_num = get_stage_num(stage)
            role_prio = role_priority.get(role, 50)

            if role in ('Дизайнер', 'Чертёжник'):
                # Исполнители: стадия -> сотрудник -> роль -> тип платежа
                return (6, stage_num, employee_id, role_prio, payment_type_priority.get(ptype, 99), payment_id)
            else:
                return (role_prio, 0, 0, 0, payment_type_priority.get(ptype, 99), payment_id)

        payments = sorted(payments, key=payment_sort_key)

        # Разделяем платежи на группы
        def get_payment_group(p):
            role = p.get('role', '')
            if role in ('Старший менеджер проектов', 'СДП', 'ГАП'):
                return 'management'
            elif role in ('Менеджер', 'Менеджер проектов', 'Помощник менеджера', 'Замерщик'):
                return 'support'
            else:
                return 'executors'

        groups = {'management': [], 'support': [], 'executors': []}
        for p in payments:
            groups[get_payment_group(p)].append(p)

        print(f"\n[PAYMENTS TAB] Загружено выплат: {len(payments)}")

        group_info = [
            ('management', 'Руководство проекта'),
            ('support', 'Поддержка проекта'),
            ('executors', 'Исполнители')
        ]

        # Создаём блок для каждой группы
        for group_key, group_title in group_info:
            group_payments = groups[group_key]
            if not group_payments:
                continue

            # GroupBox для группы - ИСПРАВЛЕНИЕ 07.02.2026: Уменьшены отступы (#11,12)
            group_box = QGroupBox(group_title)
            group_box.setStyleSheet(GROUP_BOX_STYLE)
            group_layout = QVBoxLayout()
            group_layout.setContentsMargins(10, 2, 10, 8)  # ИСПРАВЛЕНИЕ 07.02.2026: Минимальные отступы (#11,12)

            # Таблица для группы - используем ProportionalResizeTable
            table = ProportionalResizeTable()
            table.setFont(QFont("Manrope", 10))
            table.setStyleSheet(TABLE_STYLE)
            table.setSelectionMode(QTableWidget.NoSelection)
            table.setFocusPolicy(Qt.NoFocus)
            table.verticalHeader().setVisible(False)
            table.verticalHeader().setDefaultSectionSize(36)
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)    # Убираем вертикальный скролл
            table.setColumnCount(9)  # Уменьшено: объединили Корректировка и Действия
            table.setHorizontalHeaderLabels([
                'Должность', 'ФИО', 'Стадия', 'Тип', 'Выплата', 'Аванс', 'Доплата', 'Месяц', 'Действия'
            ])

            # Настройка пропорционального изменения размера колонок
            # Колонки: Должность, ФИО, Стадия, Тип, Выплата, Аванс, Доплата, Месяц, Действия
            # Пропорции: 0.13, 0.17, 0.22, 0.08, 0.07, 0.07, 0.07, 0.09, фиксированная=110
            table.setup_proportional_resize(
                column_ratios=[0.13, 0.17, 0.22, 0.08, 0.07, 0.07, 0.07, 0.09],
                fixed_columns={8: 110},  # Действия - фиксированная ширина
                min_width=50
            )

            table.setRowCount(len(group_payments))

            for row, payment in enumerate(group_payments):
                # Определяем цвет строки в зависимости от статуса
                if payment.get('reassigned'):
                    row_color = QColor('#FFF9C4')  # Светло-желтый для переназначения
                else:
                    payment_status = payment.get('payment_status')
                    if payment_status == 'to_pay':
                        row_color = QColor('#FFF3CD')
                    elif payment_status == 'paid':
                        row_color = QColor('#D4EDDA')
                    else:
                        row_color = QColor('#FFFFFF')

                # Должность
                role_label = QLabel(payment['role'])
                role_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                role_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 0, role_label)

                # ФИО
                employee_name = payment.get('employee_name')
                if not employee_name:
                    emp_id = payment.get('employee_id')
                    if emp_id:
                        try:
                            emp = self.data.get_employee(emp_id)
                            employee_name = emp.get('full_name', 'Неизвестный') if emp else 'Неизвестный'
                        except Exception:
                            employee_name = 'Неизвестный'
                    else:
                        employee_name = 'Неизвестный'

                if payment.get('reassigned'):
                    employee_name = f"* {employee_name} *"

                name_label = QLabel(employee_name)
                if payment.get('reassigned'):
                    name_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; font-weight: bold; border-radius: 2px;")
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
                    name_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 1, name_label)

                # Стадия
                stage_text = payment.get('stage_name') or '-'
                stage_label = QLabel(stage_text)
                stage_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                stage_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                table.setCellWidget(row, 2, stage_label)

                # Тип выплаты
                payment_type = payment.get('payment_type', 'Полная оплата')
                type_label = QLabel(payment_type)
                type_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                type_label.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 3, type_label)

                # Разделяем суммы по столбцам
                amount_text = f"{payment['final_amount']:,.0f}"
                manual_tip = 'Сумма установлена вручную' if payment.get('is_manual') else ''

                if payment_type == 'Полная оплата':
                    full_label = QLabel(amount_text)
                    full_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                    full_label.setAlignment(Qt.AlignCenter)
                    if manual_tip:
                        full_label.setToolTip(manual_tip)
                    table.setCellWidget(row, 4, full_label)
                    for col in [5, 6]:
                        empty = QLabel('-')
                        empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                        empty.setAlignment(Qt.AlignCenter)
                        table.setCellWidget(row, col, empty)
                elif payment_type == 'Аванс':
                    full_empty = QLabel('-')
                    full_empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                    full_empty.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 4, full_empty)
                    adv_label = QLabel(amount_text)
                    adv_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                    adv_label.setAlignment(Qt.AlignCenter)
                    if manual_tip:
                        adv_label.setToolTip(manual_tip)
                    table.setCellWidget(row, 5, adv_label)
                    bal_empty = QLabel('-')
                    bal_empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                    bal_empty.setAlignment(Qt.AlignCenter)
                    table.setCellWidget(row, 6, bal_empty)
                else:  # Доплата
                    for col in [4, 5]:
                        empty = QLabel('-')
                        empty.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                        empty.setAlignment(Qt.AlignCenter)
                        table.setCellWidget(row, col, empty)
                    bal_label = QLabel(amount_text)
                    bal_label.setStyleSheet(f"background-color: {row_color.name()}; padding: 5px; border-radius: 2px;")
                    bal_label.setAlignment(Qt.AlignCenter)
                    if manual_tip:
                        bal_label.setToolTip(manual_tip)
                    table.setCellWidget(row, 6, bal_label)

                # Отчетный месяц (столбец 7)
                report_month = payment.get('report_month', '')
                contract_status = payment.get('contract_status', '')

                if contract_status == 'РАСТОРГНУТ':
                    month_text = 'Отмена оплаты'
                    month_color = '#E74C3C'
                elif not report_month:
                    month_text = 'в работе'
                    month_color = '#95A5A6'
                else:
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(report_month, '%Y-%m')
                        months_ru = ['Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                                     'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
                        month_text = f"{months_ru[date_obj.month - 1]} {date_obj.year}"
                        month_color = '#333333'
                    except Exception:
                        month_text = report_month
                        month_color = '#333333'

                month_label = QLabel(month_text)
                month_label.setStyleSheet(f"background-color: {row_color.name()}; color: {month_color}; padding: 5px; border-radius: 2px;")
                month_label.setAlignment(Qt.AlignCenter)
                table.setCellWidget(row, 7, month_label)

                # Кнопки действий (столбец 8)
                if _has_perm(self.employee, self.api_client, 'crm_cards.payments'):
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
                    adj_btn.clicked.connect(lambda checked, p_id=payment['id']: self.adjust_payment_amount(p_id))
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
                    del_btn.clicked.connect(lambda checked, p_id=payment['id'], p_role=payment['role'], p_name=payment.get('employee_name', ''): self.delete_payment(p_id, p_role, p_name))
                    actions_layout.addWidget(del_btn)

                    actions_layout.setAlignment(Qt.AlignCenter)
                    actions_widget.setLayout(actions_layout)
                    table.setCellWidget(row, 8, actions_widget)

                print(f"  • {payment['role']}: {payment.get('employee_name', 'N/A')} - {payment_type} - {payment['final_amount']:.2f}")

            # Высота таблицы подстраивается под количество строк
            table_height = 36 * len(group_payments) + 36  # 36px на строку + 36px на заголовок
            table.setFixedHeight(table_height)

            group_layout.addWidget(table)
            group_box.setLayout(group_layout)
            layout.addWidget(group_box)

        # Предупреждение о переназначении
        has_reassigned = any(p.get('reassigned') for p in payments)
        if has_reassigned:
            warning_label = QLabel(
                '<b>ВНИМАНИЕ!</b> Обнаружено переназначение сотрудников (строки выделены желтым).'
            )
            warning_label.setStyleSheet('''
                background-color: #FFF3CD; color: #856404; border: 2px solid #FFC107;
                border-radius: 4px; padding: 10px; font-size: 11px; margin: 10px 0;
            ''')
            warning_label.setWordWrap(True)
            layout.addWidget(warning_label)

        # Итоговая сумма - считаем все платежи без флага reassigned (актуальные платежи)
        # Итоговая сумма - считаем ВСЕ платежи (включая переназначенных исполнителей)
        total_amount = sum(p['final_amount'] for p in payments)
        total_label = QLabel(f'<b>Итого к выплате: {total_amount:,.0f} руб.</b>')
        total_label.setStyleSheet('font-size: 14px; padding: 10px; background-color: #ffffff; margin-top: 10px;')
        layout.addWidget(total_label)

        layout.addStretch()
        scroll_content.setLayout(layout)
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        widget.setLayout(main_layout)
        return widget
    
    def adjust_payment_amount(self, payment_id):
        """Диалог корректировки суммы выплаты"""
        # Получаем текущие данные выплаты - сначала из API, затем из локальной БД
        current_amount = 0
        current_report_month = QDate.currentDate().toString('yyyy-MM')

        # Пробуем загрузить из API
        if self.data.is_multi_user:
            try:
                payment_data = self.data.get_payment(payment_id)
                if payment_data:
                    current_amount = payment_data.get('final_amount', 0) or 0
                    current_report_month = payment_data.get('report_month') or QDate.currentDate().toString('yyyy-MM')
                    print(f"[API] Загружены данные платежа {payment_id}: сумма={current_amount}")
            except Exception as e:
                print(f"[WARN] Ошибка API при загрузке данных выплаты: {e}, fallback на локальную БД")
                # Fallback на локальную БД
                try:
                    conn = self.data.db.connect()
                    cursor = conn.cursor()
                    cursor.execute("""
                        SELECT final_amount, report_month
                        FROM payments
                        WHERE id = ?
                    """, (payment_id,))
                    payment_data = cursor.fetchone()
                    self.data.db.close()

                    if payment_data:
                        current_amount = payment_data['final_amount'] or 0
                        current_report_month = payment_data['report_month'] or QDate.currentDate().toString('yyyy-MM')
                except Exception as e2:
                    print(f"Ошибка при загрузке данных выплаты из локальной БД: {e2}")
        else:
            # Нет API клиента - используем локальную БД
            try:
                conn = self.data.db.connect()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT final_amount, report_month
                    FROM payments
                    WHERE id = ?
                """, (payment_id,))
                payment_data = cursor.fetchone()
                self.data.db.close()

                if payment_data:
                    current_amount = payment_data['final_amount'] or 0
                    current_report_month = payment_data['report_month'] or QDate.currentDate().toString('yyyy-MM')
            except Exception as e:
                print(f"Ошибка при загрузке данных выплаты: {e}")

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
                border: 1px solid #E0E0E0;
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

        # ИСПРАВЛЕНИЕ: Автофокус на поле ввода + выделение текста
        amount_spin.setFocus()
        amount_spin.selectAll()

        dialog.exec_()

    def save_manual_amount(self, payment_id, amount, month, year, dialog):
        """Сохранение ручной суммы и отчетного месяца"""
        # Формируем отчетный месяц в формате YYYY-MM
        report_month = f"{year}-{month:02d}"

        updated = False

        # Сначала пробуем обновить через API
        if self.data.is_multi_user:
            try:
                self.data.update_payment(payment_id, {
                    'manual_amount': amount,
                    'final_amount': amount,
                    'is_manual': True,
                    'report_month': report_month,
                    'reassigned': False  # Сбрасываем флаг переназначения при редактировании
                })
                print(f"[API] Оплата обновлена: ID={payment_id}, сумма={amount}, месяц={report_month}")
                updated = True
            except Exception as e:
                print(f"[WARN] Ошибка обновления оплаты через API: {e}")
                # Fallback на локальную БД

        # Fallback или локальный режим - обновляем локальную БД
        if not updated:
            # Обновляем сумму
            self.data.update_payment_manual(payment_id, amount)

            # Обновляем отчетный месяц
            try:
                conn = self.data.db.connect()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE payments
                    SET report_month = ?,
                        reassigned = 0
                    WHERE id = ?
                """, (report_month, payment_id))
                conn.commit()
                self.data.db.close()
                print(f"[LOCAL] Оплата обновлена: ID={payment_id}, сумма={amount}, месяц={report_month}")
            except Exception as e:
                print(f"[ERROR] Ошибка при обновлении отчетного месяца: {e}")

        # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие
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
            'Это действие нельзя отменить!'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                deleted = False

                # Сначала пробуем удалить через API
                if self.data.is_multi_user:
                    try:
                        self.data.delete_payment(payment_id)
                        print(f"[API] Оплата удалена: {role} - {employee_name} (ID: {payment_id})")
                        deleted = True
                    except Exception as e:
                        print(f"[WARN] Ошибка удаления оплаты через API: {e}")
                        # Fallback на локальную БД

                # Fallback или локальный режим - удаляем из локальной БД
                if not deleted:
                    conn = self.data.db.connect()
                    cursor = conn.cursor()

                    cursor.execute('''
                    DELETE FROM payments
                    WHERE id = ?
                    ''', (payment_id,))

                    conn.commit()
                    self.data.db.close()
                    print(f"[LOCAL] Оплата удалена: {role} - {employee_name} (ID: {payment_id})")

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
                print(f"[ERROR] Ошибка удаления оплаты: {e}")
                import traceback
                traceback.print_exc()

                CustomMessageBox(
                    self,
                    'Ошибка',
                    f'Не удалось удалить оплату:\n{str(e)}',
                    'error'
                ).exec_()

    def showEvent(self, event):
        """Центрирование при первом показе + отложенная инициализация тяжёлых вкладок"""
        super().showEvent(event)
        if not hasattr(self, '_centered'):
            self._centered = True
            self.center_on_screen()
            QTimer.singleShot(0, self._init_deferred_tabs)

    def center_on_screen(self):
        """Центрирование относительно родительского окна"""
        from utils.dialog_helpers import center_dialog_on_parent
        center_dialog_on_parent(self)

    def _init_deferred_tabs(self):
        """Поэтапная инициализация: сначала load_data для Tab 1, потом остальные вкладки"""
        if self._deferred_tabs_ready:
            return
        self._deferred_tabs_ready = True

        # Шаг 1: Загрузить данные Tab 1 (комбобоксы, дедлайны)
        self.load_data()

        # Шаг 2: Создать остальные вкладки в следующих тиках event loop
        QTimer.singleShot(0, self._init_deferred_step2)

    def _init_deferred_step2(self):
        """Создание тяжёлых вкладок порциями (не блокирует UI)"""
        from PyQt5.QtWidgets import QApplication
        app = QApplication.instance()
        current_tab = self.tabs.currentIndex()

        # Данные по проекту, история, оплаты — из локальной БД (мгновенно)
        self.data.prefer_local = True
        try:
            # Данные по проекту
            project_data_widget = self.create_project_data_widget()
            self.tabs.removeTab(self.project_data_tab_index)
            self.tabs.insertTab(self.project_data_tab_index, project_data_widget, 'Данные по проекту')
            # После создания виджета — обновляем labels файлов из кэшированного контракта
            # (load_data() выполнился ДО создания виджетов, hasattr возвращал False)
            self._update_project_data_file_labels()
            app.processEvents()

            # История по проекту
            if self.project_info_tab_index >= 0:
                info_widget = self.create_project_info_widget()
                self.tabs.removeTab(self.project_info_tab_index)
                self.tabs.insertTab(self.project_info_tab_index, info_widget, 'История по проекту')

            # Оплаты
            if self.payments_tab_index >= 0:
                payments_widget = self.create_payments_tab()
                self.tabs.removeTab(self.payments_tab_index)
                self.tabs.insertTab(self.payments_tab_index, payments_widget, 'Оплаты')
        finally:
            self.data.prefer_local = False

        app.processEvents()

        # Таблица сроков — данные только на сервере, грузим через API
        try:
            from ui.timeline_widget import ProjectTimelineWidget
            self.timeline_widget = ProjectTimelineWidget(
                card_data=self.card_data, data=self.data, db=self.db,
                api_client=self.api_client, employee=self.employee, parent=self
            )
            # Подписываемся на обновление дедлайна из таймлайна
            self.timeline_widget.deadline_updated.connect(self._on_timeline_deadline_updated)
            self.tabs.removeTab(self._timeline_tab_index)
            self.tabs.insertTab(self._timeline_tab_index, self.timeline_widget, 'Таблица сроков')
        except Exception as e:
            print(f"[CardEditDialog] Ошибка создания таблицы сроков: {e}")

        self.tabs.setCurrentIndex(current_tab)

        # Фоновая загрузка превью
        QTimer.singleShot(300, self._start_background_preview_loading)

    def _on_timeline_deadline_updated(self, deadline_str):
        """Обновить отображение дедлайна проекта когда timeline пересчитал"""
        if hasattr(self, 'deadline_display') and deadline_str:
            d = QDate.fromString(deadline_str, 'yyyy-MM-dd')
            if d.isValid():
                self.deadline_display.setText(d.toString('dd.MM.yyyy'))

    def _update_project_data_file_labels(self):
        """Обновить labels файлов ТЗ/замер/референсов из кэшированного контракта.
        Вызывается после создания project_data_widget в _init_deferred_step2,
        т.к. load_data() выполняется ДО создания виджетов."""
        contract = self._cached_contract
        if not contract:
            return

        # ТЗ файл
        tech_task_link = contract.get('tech_task_link')
        tech_task_file_name = contract.get('tech_task_file_name')
        if tech_task_link and hasattr(self, 'project_data_tz_file_label'):
            file_name = tech_task_file_name or 'ТехЗадание.pdf'
            truncated_name = self.truncate_filename(file_name)
            self.project_data_tz_file_label.setText(
                f'<a href="{tech_task_link}" title="{file_name}">{truncated_name}</a>')
            if hasattr(self, 'upload_tz_btn'):
                self.upload_tz_btn.setEnabled(False)

        # Дата ТЗ
        if self.card_data.get('tech_task_date') and hasattr(self, 'project_data_tz_date_label'):
            from datetime import datetime
            try:
                td = datetime.strptime(self.card_data['tech_task_date'], '%Y-%m-%d')
                self.project_data_tz_date_label.setText(td.strftime('%d.%m.%Y'))
            except Exception:
                pass

        # Замер файл
        measurement_link = contract.get('measurement_image_link')
        measurement_file_name = contract.get('measurement_file_name')
        if measurement_link and hasattr(self, 'project_data_survey_file_label'):
            file_name = measurement_file_name or 'Замер'
            truncated_name = self.truncate_filename(file_name)
            self.project_data_survey_file_label.setText(
                f'<a href="{measurement_link}" title="{file_name}">{truncated_name}</a>')
            if hasattr(self, 'upload_survey_btn'):
                self.upload_survey_btn.setEnabled(False)

        # Дата замера
        survey_date_val = self.card_data.get('survey_date', '')
        if not survey_date_val:
            survey_date_val = contract.get('measurement_date', '')
        if survey_date_val and hasattr(self, 'project_data_survey_date_label'):
            from datetime import datetime
            try:
                sd = datetime.strptime(survey_date_val, '%Y-%m-%d')
                self.project_data_survey_date_label.setText(sd.strftime('%d.%m.%Y'))
            except Exception:
                pass

        # Референсы
        ref_path = contract.get('references_yandex_path')
        if ref_path and hasattr(self, 'project_data_references_label'):
            self.project_data_references_label.setText(
                f'<a href="{ref_path}">Открыть папку с референсами</a>')

        # Фотофиксация
        photo_path = contract.get('photo_documentation_yandex_path')
        if photo_path and hasattr(self, 'project_data_photo_doc_label'):
            self.project_data_photo_doc_label.setText(
                f'<a href="{photo_path}">Открыть папку с фотофиксацией</a>')

    def reject(self):
        """ИСПРАВЛЕНИЕ: Обновляем канбан при закрытии диалога"""
        from ui.crm_tab import CRMTab
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
        print(f"[OK] Файлы стадии {stage} успешно загружены")

        self.reload_stage_files(stage)

        # Добавляем запись в историю проекта
        if self.employee:
            from datetime import datetime

            # Определяем тип проекта из contracts (а не из card_data!)
            contract_id = self.card_data.get('contract_id')
            if contract_id:
                conn = self.data.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT project_type FROM contracts WHERE id = ?', (contract_id,))
                result = cursor.fetchone()
                conn.close()
                project_type = result['project_type'] if result else None
            else:
                project_type = None

            is_template = project_type == 'Шаблонный'

            # Определяем название стадии для отображения
            stage_names = {
                'stage1': '1 стадия - Планировочное решение',
                'stage2_concept': '2 стадия - Концепция дизайна (Концепция-коллажи)',
                'stage2_3d': '3 стадия - 3D визуализация (дополнительная)' if is_template else '2 стадия - Концепция дизайна (3D визуализация)',
                'stage3': '2 стадия - Чертежный проект' if is_template else '3 стадия - Чертежный проект'
            }
            stage_name = stage_names.get(stage, stage)
            description = f"Добавлены файлы в стадию: {stage_name}"

            self._add_action_history('file_upload', description)

            try:
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt (deleteLater и др.)
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                print(f"[OK] Добавлена запись в историю: {description}")
            except Exception as e:
                print(f"[ERROR] Ошибка в reload_project_history или processEvents: {e}")
                import traceback
                traceback.print_exc()


    def on_stage_upload_error(self, error_msg):
        """Обработчик ошибки загрузки файлов"""
        from ui.custom_message_box import CustomMessageBox
        CustomMessageBox(self, 'Ошибка', f'Ошибка загрузки файлов:\n{error_msg}', 'error').exec_()

    def _add_corrections_button(self, file_widget, stage_keyword):
        """Добавляет кнопку 'Правки' в header_layout виджета файлов (рядом с 'Загрузить файлы').
        file_widget: FileListWidget или VariationGalleryWidget (с атрибутом header_layout)
        stage_keyword: строка для поиска в ключах _corrections_by_stage (напр. 'Стадия 1')
        """
        if not hasattr(self, '_corrections_by_stage') or not self._corrections_by_stage:
            return
        if not hasattr(file_widget, 'header_layout'):
            return

        # Найти путь правок для этой стадии
        corr_path = None
        for sname, spath in self._corrections_by_stage.items():
            if stage_keyword.lower() in sname.lower():
                corr_path = spath
                break

        if not corr_path:
            return

        btn = QPushButton('Правки')
        btn.setStyleSheet("""
            QPushButton {
                background-color: #E74C3C;
                color: white;
                padding: 0px 10px;
                border-radius: 6px;
                border: none;
                font-size: 10px;
                max-height: 28px;
                min-height: 28px;
            }
            QPushButton:hover { background-color: #C0392B; }
        """)
        btn.setFixedSize(80, 28)
        btn.setCursor(QCursor(Qt.PointingHandCursor))

        def open_folder():
            import webbrowser
            import urllib.parse
            if not corr_path or not isinstance(corr_path, str):
                return
            # corr_path содержит полный путь на ЯД (напр. disk:/АРХИВ ПРОЕКТОВ/.../правки)
            clean = corr_path.replace('disk:/', '').replace('disk:', '').lstrip('/')
            encoded = urllib.parse.quote(clean)
            webbrowser.open(f"https://disk.yandex.ru/client/disk/{encoded}")

        btn.clicked.connect(open_folder)
        # Вставляем перед последним элементом (удалить) или в конец
        file_widget.header_layout.addWidget(btn)

    def upload_stage_files(self, stage):
        """Множественная загрузка файлов для стадии"""
        from PyQt5.QtWidgets import QFileDialog
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

        contract_folder = self._get_contract_yandex_folder(contract_id)

        if not contract_folder:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', 'Папка договора на Яндекс.Диске не найдена.\nСначала сохраните договор.', 'warning').exec_()
            return

        # Количество шагов: загрузка файлов + обработка файлов
        total_steps = len(file_paths) * 2
        progress = create_progress_dialog("Загрузка файлов", "Подготовка к загрузке...", "Отмена", total_steps, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        def upload_thread():
            try:
                from database.db_manager import DatabaseManager
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG

                yd = YandexDiskManager(YANDEX_DISK_TOKEN)

                # Callback для обновления прогресса загрузки
                def update_upload_progress(current, total, file_name, phase):
                    if cancel_event.is_set():
                        return
                    step = current + 1
                    percent = int((step / total) * 50)  # первые 50% - загрузка
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    label_text = f"Загрузка на Яндекс.Диск: {file_name}\n{step}/{total} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

                uploaded_files = yd.upload_stage_files(file_paths, contract_folder, stage, progress_callback=update_upload_progress)

                # Создаем новое подключение к БД для потока
                thread_db = DatabaseManager()

                for i, file_data in enumerate(uploaded_files):
                    if cancel_event.is_set():
                        break

                    current = i + 1
                    total = len(uploaded_files)
                    # Вторые 50% - обработка файлов (превьюшки + БД)
                    step = len(file_paths) + current
                    percent = 50 + int((current / total) * 50)
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, step))
                    label_text = f"Обработка {file_data['file_name']}...\n{current}/{total} ({percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

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

                    # КРИТИЧНО: Добавляем запись на сервер через API!
                    if self.data.is_multi_user:
                        try:
                            file_record_data = {
                                'contract_id': contract_id,
                                'stage': stage,
                                'file_type': file_type,
                                'public_link': file_data['public_link'],
                                'yandex_path': file_data['yandex_path'],
                                'file_name': file_data['file_name'],
                                'file_order': current - 1,  # current начинается с 1
                                'variation': 1  # Будет учтено при добавлении вариаций
                            }
                            self.data.create_file_record(file_record_data)
                            print(f"[API] Файл '{file_data['file_name']}' добавлен через API")
                        except Exception as e:
                            print(f"[API ERROR] Не удалось добавить файл через API: {e}")
                            import traceback
                            traceback.print_exc()
                            # Продолжаем - файл уже сохранен локально

                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _stage = stage
                QTimer.singleShot(0, lambda: self.stage_files_uploaded.emit(_stage))
            except Exception as e:
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _err = str(e)
                QTimer.singleShot(0, lambda: self.stage_upload_error.emit(_err))

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

        # Сначала удаляем через API (сервер удалит и из БД, и с ЯД)
        file_info = None
        if self.data.is_online:
            try:
                # Получаем инфо о файле перед удалением
                response = self.data.api_client._request(
                    'GET',
                    f"{self.data.api_client.base_url}/api/files/{file_id}",
                    mark_offline=False
                )
                file_info = self.data.api_client._handle_response(response)
                # Удаляем через серверный API (удалит из серверной БД + с ЯД)
                self.data.delete_file_record(file_id)
                print(f"[API] Файл стадии удален с сервера (БД + ЯД), id={file_id}")
            except Exception as api_err:
                print(f"[ERROR] Ошибка удаления файла с сервера: {api_err}")
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Ошибка', f'Не удалось удалить файл с сервера: {api_err}', 'error').exec_()
                return
            # Удаляем из локальной БД после успешного удаления на сервере
            self.data.delete_project_file(file_id)
        else:
            # Offline режим: удаляем локально и с ЯД напрямую
            file_info = self.data.delete_project_file(file_id)
            if file_info and file_info.get('yandex_path'):
                try:
                    yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                    yd.delete_file(file_info['yandex_path'])
                    print(f"[OK] Файл удален из Яндекс.Диска: {file_info['yandex_path']}")
                except Exception as e:
                    print(f"[ERROR] Не удалось удалить файл с Яндекс.Диска: {e}")

        if file_info:

            # Очистка preview кэша
            try:
                cache_path = file_info.get('preview_cache_path')
                if not cache_path:
                    # Fallback: пробуем стандартный путь кэша
                    from utils.preview_generator import PreviewGenerator
                    contract_id_for_cache = self.card_data.get('contract_id')
                    file_name = file_info.get('file_name', '')
                    if contract_id_for_cache and file_name:
                        cache_path = PreviewGenerator.get_cache_path(
                            contract_id_for_cache, stage, file_name
                        ) if hasattr(PreviewGenerator, 'get_cache_path') else None
                if cache_path and os.path.exists(cache_path):
                    os.remove(cache_path)
            except Exception:
                pass

            # Добавляем запись в историю проекта
            if self.employee:
                from datetime import datetime

                # Определяем тип проекта из contracts
                contract_id = self.card_data.get('contract_id')
                if contract_id:
                    conn = self.data.db.connect()
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

                self._add_action_history('file_delete', description)
                self.reload_project_history()

                # Принудительно обрабатываем отложенные события Qt
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

            self.reload_stage_files(stage)
            # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех" - авто-принятие

    def upload_stage_files_with_variation(self, stage, variation):
        """Загрузка файлов для стадии с указанием вариации"""
        from PyQt5.QtWidgets import QFileDialog
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

        contract_folder = self._get_contract_yandex_folder(contract_id)

        if not contract_folder:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', 'Папка договора на Яндекс.Диске не найдена.', 'warning').exec_()
            return

        # Создаем прогресс-диалог
        total_steps = len(file_paths) * 2
        progress = create_progress_dialog("Загрузка файлов", "Подготовка к загрузке...", "Отмена", total_steps, self)

        # R-02 FIX: Потокобезопасная проверка отмены вместо progress.wasCanceled() из фонового потока
        cancel_event = threading.Event()
        progress.canceled.connect(cancel_event.set)

        def upload_thread():
            try:
                from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
                yd = YandexDiskManager(YANDEX_DISK_TOKEN)
                current_step = 0

                def update_progress(index, total, fname, phase):
                    nonlocal current_step
                    if cancel_event.is_set():
                        return
                    current_step = index
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, current_step))
                    percent = int((current_step / total_steps) * 100)
                    label_text = f"Загрузка: {fname}\n({index}/{len(file_paths)} файлов - {percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

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
                    # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                    QTimer.singleShot(0, lambda: self.stage_upload_error.emit("Не удалось загрузить файлы"))
                    return

                # Генерируем превью и сохраняем в БД
                for i, uploaded_file in enumerate(uploaded_files):
                    if cancel_event.is_set():
                        return

                    current_step = len(file_paths) + i
                    # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                    QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, current_step))
                    percent = int((current_step / total_steps) * 100)
                    label_text = f"Обработка: {uploaded_file['file_name']}\n({i+1}/{len(uploaded_files)} файлов - {percent}%)"
                    QMetaObject.invokeMethod(progress, "setLabelText", Qt.QueuedConnection, Q_ARG(str, label_text))

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
                    self.data.add_project_file(
                        contract_id=contract_id,
                        stage=stage,
                        file_type=file_type,
                        public_link=uploaded_file.get('public_link', ''),
                        yandex_path=uploaded_file['yandex_path'],
                        file_name=uploaded_file['file_name'],
                        preview_cache_path=preview_cache_path,
                        variation=variation
                    )

                    # КРИТИЧНО: Добавляем запись на сервер через API!
                    if self.data.is_multi_user:
                        try:
                            file_record_data = {
                                'contract_id': contract_id,
                                'stage': stage,
                                'file_type': file_type,
                                'public_link': uploaded_file.get('public_link', ''),
                                'yandex_path': uploaded_file['yandex_path'],
                                'file_name': uploaded_file['file_name'],
                                'file_order': i,  # Порядковый номер в текущем батче
                                'variation': variation
                            }
                            self.data.create_file_record(file_record_data)
                            print(f"[API] Файл '{uploaded_file['file_name']}' (вариация {variation}) добавлен через API")
                        except Exception as e:
                            print(f"[API ERROR] Не удалось добавить файл через API: {e}")
                            import traceback
                            traceback.print_exc()
                            # Продолжаем - файл уже сохранен локально

                # ИСПРАВЛЕНИЕ 25.01.2026: Безопасный вызов Qt методов из фонового потока
                QMetaObject.invokeMethod(progress, "setValue", Qt.QueuedConnection, Q_ARG(int, total_steps))
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _stage = stage
                QTimer.singleShot(0, lambda: self.stage_files_uploaded.emit(_stage))

            except Exception as e:
                print(f"[ERROR] Ошибка загрузки файлов: {e}")
                import traceback
                traceback.print_exc()
                # ИСПРАВЛЕНИЕ: Закрываем прогресс из главного потока через QTimer
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, progress.close)
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                _err = str(e)
                QTimer.singleShot(0, lambda: self.stage_upload_error.emit(_err))

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
        from PyQt5.QtWidgets import QDialog
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
        files = self.data.get_project_files(contract_id, stage)
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
        progress = create_progress_dialog("Удаление вариации", "Удаление файлов...", None, total_steps, self)

        yd = YandexDiskManager(YANDEX_DISK_TOKEN)

        # Удаляем файлы из БД и Яндекс.Диска
        for i, file_data in enumerate(variation_files):
            percent = int((i / total_steps) * 100)
            progress.setValue(i)
            progress.setLabelText(f"Удаление: {file_data['file_name']}\n({i+1}/{len(variation_files)} файлов - {percent}%)")

            file_info = None
            if self.data.is_online:
                try:
                    self.data.delete_file_record(file_data['id'])
                    file_info = file_data
                    self.data.delete_project_file(file_data['id'])
                except Exception as e:
                    print(f"[WARN] Ошибка удаления файла с сервера: {e}")
                    continue
            else:
                file_info = self.data.delete_project_file(file_data['id'])
                if file_info and file_info.get('yandex_path'):
                    try:
                        yd.delete_file(file_info['yandex_path'])
                    except Exception as e:
                        print(f"[WARN] Не удалось удалить файл с Яндекс.Диска: {e}")

                if file_info.get('preview_cache_path'):
                    try:
                        if os.path.exists(file_info['preview_cache_path']):
                            os.remove(file_info['preview_cache_path'])
                    except Exception:
                        pass

        # Удаляем папку вариации с Яндекс.Диска
        progress.setValue(len(variation_files))
        progress.setLabelText(f"Удаление папки...\n({total_steps}/{total_steps} - 100%)")

        try:
            contract_folder = self._get_contract_yandex_folder(contract_id)

            if contract_folder:
                variation_folder = yd.get_stage_folder_path(
                    contract_folder,
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
                conn = self.data.db.connect()
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

            self._add_action_history('file_delete', description)
            self.reload_project_history()

            # Принудительно обрабатываем отложенные события Qt
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

        # Удаляем вкладку из UI
        if stage == 'stage2_concept' and hasattr(self, 'stage2_concept_gallery'):
            self.stage2_concept_gallery.remove_variation_tab(variation)
        elif stage == 'stage2_3d' and hasattr(self, 'stage2_3d_gallery'):
            self.stage2_3d_gallery.remove_variation_tab(variation)

    def _load_all_stage_files_batch(self):
        """Загрузка файлов ВСЕХ стадий из локальной БД (мгновенно)"""
        from database.db_manager import DatabaseManager

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Читаем из локальной БД — мгновенно, без сетевых задержек
        # Фоновый validate_stage_files_on_yandex обновит при необходимости
        db = DatabaseManager()
        all_files = db.get_project_files(contract_id)

        if not all_files:
            all_files = []

        # Фильтруем правки
        all_files = [f for f in all_files if '/правки/' not in (f.get('yandex_path') or '').lower()]

        # Распределяем по стадиям
        by_stage = {}
        for f in all_files:
            s = f.get('stage', '')
            if s not in by_stage:
                by_stage[s] = []
            by_stage[s].append(f)

        # Обновляем виджеты каждой стадии
        if hasattr(self, 'stage1_list'):
            self.stage1_list.load_files(by_stage.get('stage1', []))
        if hasattr(self, 'stage2_concept_gallery'):
            self._load_variation_gallery(self.stage2_concept_gallery, by_stage.get('stage2_concept', []))
        if hasattr(self, 'stage2_3d_gallery'):
            self._load_variation_gallery(self.stage2_3d_gallery, by_stage.get('stage2_3d', []))
        if hasattr(self, 'stage3_list'):
            self.stage3_list.load_files(by_stage.get('stage3', []))

    def _load_variation_gallery(self, gallery, files):
        """Загрузка файлов с группировкой по вариациям в галерею"""
        variations = {}
        for file_data in files:
            variation = file_data.get('variation', 1)
            if variation not in variations:
                variations[variation] = []
            variations[variation].append(file_data)
        for variation, variation_files in variations.items():
            gallery.load_files(variation_files, variation)

    def reload_stage_files(self, stage):
        """Перезагрузка файлов стадии (API → fallback на локальную БД)"""
        from database.db_manager import DatabaseManager

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Сначала пробуем API (файлы из серверной PostgreSQL, включая результаты scan)
        files = None
        if self.data.is_online:
            try:
                api_files = self.data.get_project_files(contract_id, stage)
                if api_files is not None:
                    files = api_files
            except Exception as e:
                print(f"[WARN] API файлы для {stage}: {e}")

        # Fallback на локальную БД
        if files is None:
            db = DatabaseManager()
            files = db.get_project_files(contract_id, stage)

        # Фильтруем файлы из папки "правки/" — они отображаются отдельно через кнопку "Правки"
        if files:
            files = [f for f in files if '/правки/' not in (f.get('yandex_path') or '').lower()]

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
        """Загрузка превью для файла из кэша.

        ВАЖНО: Эта функция НЕ делает сетевых запросов для ускорения загрузки UI.
        Если кэша нет - возвращает None и файл отображается с плейсхолдером.
        """
        from utils.preview_generator import PreviewGenerator
        import os

        # Способ 1: Из сохраненного пути кэша в БД
        if file_data.get('preview_cache_path'):
            if os.path.exists(file_data['preview_cache_path']):
                pixmap = PreviewGenerator.load_preview_from_cache(file_data['preview_cache_path'])
                if pixmap:
                    return pixmap

        # Способ 2: Проверяем стандартный путь кэша (может быть создан ранее)
        contract_id = file_data.get('contract_id', 0)
        stage = file_data.get('stage', 'unknown')
        file_name = file_data.get('file_name', '')

        if contract_id and file_name:
            cache_path = PreviewGenerator.get_cache_path(contract_id, stage, file_name)
            if os.path.exists(cache_path):
                pixmap = PreviewGenerator.load_preview_from_cache(cache_path)
                if pixmap:
                    return pixmap

        # Если кэша нет - возвращаем None, превью будет загружено асинхронно
        return None

    def _start_background_preview_loading(self):
        """Запуск фоновой загрузки превью для файлов без кэша"""
        from ui.crm_tab import PreviewLoaderThread
        from utils.preview_generator import PreviewGenerator

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        # Собираем все файлы изображений без кэша
        files_to_load = []

        # Получаем все файлы проекта
        all_files = self.data.get_project_files(contract_id, 'stage2_concept')
        all_files += self.data.get_project_files(contract_id, 'stage2_3d')

        for file_data in all_files:
            if file_data.get('file_type') != 'image':
                continue

            file_id = file_data.get('id')
            public_link = file_data.get('public_link', '')
            yandex_path = file_data.get('yandex_path', '')
            stage = file_data.get('stage', 'unknown')
            file_name = file_data.get('file_name', '')

            if (not public_link and not yandex_path) or not file_name:
                continue

            # Проверяем, есть ли уже кэш
            cache_path = PreviewGenerator.get_cache_path(contract_id, stage, file_name)
            if os.path.exists(cache_path):
                continue  # Уже есть кэш

            files_to_load.append((file_id, public_link, contract_id, stage, file_name, yandex_path))

        if not files_to_load:
            print(f"[PreviewLoader] Все превью уже в кэше для contract_id={contract_id}")
            return

        print(f"[PreviewLoader] Запуск фоновой загрузки {len(files_to_load)} превью для contract_id={contract_id}")

        # Останавливаем предыдущий поток если есть
        if self._preview_loader_thread and self._preview_loader_thread.is_alive():
            self._preview_loader_thread.stop()

        # Запускаем новый поток
        self._preview_loader_thread = PreviewLoaderThread(
            files_to_load=files_to_load,
            callback=self._on_preview_loaded_from_thread,
            yandex_token=YANDEX_DISK_TOKEN
        )
        self._preview_loader_thread.start()

    def _on_preview_loaded_from_thread(self, file_id, pixmap):
        """Callback из потока загрузки - переводит в главный поток через QTimer"""
        # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety (вызывается из PreviewLoaderThread)
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(0, lambda: self.preview_loaded.emit(file_id, pixmap))

    def _on_preview_loaded(self, file_id, pixmap):
        """Обработчик сигнала - обновляет превью в UI (выполняется в главном потоке)"""
        # Ищем виджет превью по file_id в галереях
        preview_widget = self._find_preview_widget_by_file_id(file_id)
        if preview_widget:
            preview_widget.update_preview(pixmap)
            print(f"[PreviewLoader] Обновлено превью для file_id={file_id}")

    def _find_preview_widget_by_file_id(self, file_id):
        """Поиск виджета превью по ID файла в галереях"""
        # Проверяем кэш
        if file_id in self._preview_widgets_map:
            widget = self._preview_widgets_map[file_id]
            # Проверяем, что виджет ещё существует
            try:
                widget.isVisible()  # Проверка на deleted widget
                return widget
            except RuntimeError:
                del self._preview_widgets_map[file_id]

        # Ищем в галерее концептов
        if hasattr(self, 'stage2_concept_gallery'):
            widget = self._find_widget_in_variation_gallery(self.stage2_concept_gallery, file_id)
            if widget:
                self._preview_widgets_map[file_id] = widget
                return widget

        # Ищем в галерее 3D
        if hasattr(self, 'stage2_3d_gallery'):
            widget = self._find_widget_in_variation_gallery(self.stage2_3d_gallery, file_id)
            if widget:
                self._preview_widgets_map[file_id] = widget
                return widget

        return None

    def _find_widget_in_variation_gallery(self, variation_gallery, file_id):
        """Поиск виджета превью в VariationGalleryWidget"""
        # VariationGalleryWidget содержит variation_galleries = {variation_number: FileGalleryWidget}
        # Каждый FileGalleryWidget содержит preview_widgets
        if not hasattr(variation_gallery, 'variation_galleries'):
            return None

        for variation_num, file_gallery in variation_gallery.variation_galleries.items():
            if hasattr(file_gallery, 'preview_widgets'):
                for preview_widget in file_gallery.preview_widgets:
                    if hasattr(preview_widget, 'file_id') and preview_widget.file_id == file_id:
                        return preview_widget

        return None

    def closeEvent(self, event):
        """Остановка фоновых потоков и очистка при закрытии диалога"""
        # Удаляем event filter
        from PyQt5.QtWidgets import QApplication
        QApplication.instance().removeEventFilter(self)

        # Останавливаем фоновые потоки
        if self._preview_loader_thread and self._preview_loader_thread.is_alive():
            self._preview_loader_thread.stop()
        super().closeEvent(event)

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
                # ВАЖНО: Захватываем мышь чтобы получать события даже за пределами окна
                self.grabMouse()
                event.accept()
                return
        super().mousePressEvent(event)

    def eventFilter(self, obj, event):
        """Глобальный перехватчик событий мыши для корректной работы resize"""
        # Проверяем, что obj является QWidget (не QWindow или другой объект)
        from PyQt5.QtWidgets import QWidget
        if not isinstance(obj, QWidget):
            return super().eventFilter(obj, event)

        # Перехватываем отпускание кнопки мыши для сброса resize состояния
        # Это нужно на случай если mouseReleaseEvent не дошел до диалога
        if event.type() == QEvent.MouseButtonRelease:
            if event.button() == Qt.LeftButton and self.resizing:
                self.releaseMouse()
                self.resizing = False
                self.resize_edge = None
                self.setCursor(Qt.ArrowCursor)
                return False  # Пропускаем событие дальше

        # Обрабатываем только события от виджетов внутри этого диалога
        if not self.isAncestorOf(obj) and obj != self:
            return super().eventFilter(obj, event)

        # Перехватываем движение мыши для изменения курсора на границах
        if event.type() == QEvent.MouseMove:
            if not self.resizing:
                # Преобразуем координаты в координаты диалога
                global_pos = event.globalPos()
                local_pos = self.mapFromGlobal(global_pos)
                edge = self.get_resize_edge(local_pos)
                self.set_cursor_shape(edge)

        # Перехватываем выход мыши для сброса курсора
        elif event.type() == QEvent.Leave:
            if not self.resizing:
                self.setCursor(Qt.ArrowCursor)

        return super().eventFilter(obj, event)

    def event(self, event):
        """Обработка событий наведения мыши"""
        if event.type() == QEvent.HoverMove:
            # Изменяем курсор при наведении (без нажатия)
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)
        elif event.type() == QEvent.HoverLeave:
            # Сброс курсора при выходе мыши за пределы окна
            if not self.resizing:
                self.setCursor(Qt.ArrowCursor)

        return super().event(event)

    def leaveEvent(self, event):
        """Сброс курсора при выходе мыши за пределы диалога"""
        if not self.resizing:
            self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)

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
            min_w, min_h = 1100, 600

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
            # ВАЖНО: Освобождаем захват мыши
            self.releaseMouse()
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

