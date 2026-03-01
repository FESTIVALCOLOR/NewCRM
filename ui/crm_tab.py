# -*- coding: utf-8 -*-
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
from ui.base_kanban_tab import BaseDraggableList, BaseKanbanColumn
from functools import partial
from utils.button_debounce import debounce_click
import json
import os
import threading


# ========== Реэкспорт из utils/permissions (обратная совместимость) ==========
from utils.permissions import (  # noqa: F401
    _emp_has_pos, _emp_only_pos,
    _user_permissions_cache, _load_user_permissions, _has_perm,
    has_any_perm, invalidate_cache,
)
# =============================================================================


class DraggableListWidget(BaseDraggableList):
    """Кастомный QListWidget с контролируемым Drag & Drop.
    __init__ и startDrag наследуются из BaseDraggableList."""

    def dropEvent(self, event):
        """Обработка drop"""
        if not self.can_drag:
            event.ignore()
            return

        # S2.1: Проверка права crm.update перед перемещением карточки
        column = self.parent_column
        if hasattr(column, 'employee') and hasattr(column, 'api_client'):
            if not _has_perm(column.employee, column.api_client, 'crm_cards.update'):
                print("[DROP EVENT] Отказано: нет права crm.update")
                event.ignore()
                return

        source = event.source()
        
        print(f"\n[DROP EVENT] На QListWidget колонки '{self.parent_column.column_name}'")
        print(f"             Источник: {type(source).__name__}")
        
        if not isinstance(source, DraggableListWidget):
            event.ignore()
            return

        item = source.currentItem()
        if not item:
            event.ignore()
            return

        card_id = item.data(Qt.UserRole)

        source_column = source.parent_column
        target_column = self.parent_column

        if source_column == target_column:
            super().dropEvent(event)
            event.accept()
            return

        # CopyAction вместо MoveAction: запрещаем Qt автоматически удалять
        # source item. Мы перестроим карточки полностью через load_cards_for_type().
        # Без этого: MoveAction удаляет item → clear() пытается удалить снова → segfault
        event.setDropAction(Qt.CopyAction)
        event.accept()

        # Отложенный emit: dropEvent + DnD cleanup должны полностью завершиться
        # ПЕРЕД вызовом on_card_moved() → load_cards_for_type() → QListWidget.clear()
        QTimer.singleShot(50, lambda: source_column.card_moved.emit(
            card_id,
            source_column.column_name,
            target_column.column_name,
            source_column.project_type
        ))
            
class CRMTab(QWidget):
    def __init__(self, employee, can_edit=True, api_client=None, parent=None):
        super().__init__(parent)
        self.employee = employee
        self.can_edit = can_edit
        self.api_client = api_client  # Клиент для работы с API (многопользовательский режим)
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db

        self._data_loaded = False
        self._loading_guard = False
        self.init_ui()
   
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(0, 5, 0, 5)
        
        # Заголовок и кнопка статистики
        header_layout = QHBoxLayout()
        header_layout.setSpacing(10)
        
        header = QLabel('CRM - Управление проектами')
        header.setStyleSheet('font-size: 13px; font-weight: bold; color: #333333;')
        header_layout.addWidget(header)
        
        header_layout.addStretch(1)

        refresh_btn = IconLoader.create_action_button('refresh', 'Обновить данные с сервера')
        refresh_btn.clicked.connect(self.refresh_current_tab)
        header_layout.addWidget(refresh_btn)

        if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
            stats_btn = IconLoader.create_action_button('stats', 'Показать статистику проектов')
            stats_btn.clicked.connect(self.show_statistics_current_tab)
            header_layout.addWidget(stats_btn)
        
        main_layout.addLayout(header_layout)
        
        # Вкладки для типов проектов
        self.project_tabs = QTabWidget()
        self.project_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                border-radius: 4px;
            }
            QTabBar::tab {
                padding: 6px 16px;
                font-size: 12px;
                font-weight: bold;
                border: 1px solid #d9d9d9;
                border-bottom: none;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                background-color: #E8E8E8;
                min-width: 180px;
            }
            QTabBar::tab:selected {
                background-color: white;
                border-bottom: 1px solid #d9d9d9;
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

        if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
            self.individual_archive_widget = self.create_archive_board('Индивидуальный')
            self.individual_subtabs.addTab(self.individual_archive_widget, 'Архив (0)')

        individual_main_layout.addWidget(self.individual_subtabs)
        individual_main_widget.setLayout(individual_main_layout)

        self.project_tabs.addTab(individual_main_widget, 'Индивидуальные проекты')

        # === ШАБЛОННЫЕ ПРОЕКТЫ (скрыто от чистого СДП) ===
        if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
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

            if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
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
            
            if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                self.project_tabs.setTabText(1, f'Шаблонные проекты ({template_count})')
            
            if hasattr(self, 'individual_subtabs'):
                self.individual_subtabs.setTabText(0, f'Активные проекты ({individual_count})')
                
                if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                    self.individual_subtabs.setTabText(1, f'Архив ({individual_archive_count})')
            
            if hasattr(self, 'template_subtabs') and _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                self.template_subtabs.setTabText(0, f'Активные проекты ({template_count})')
                
                if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                    self.template_subtabs.setTabText(1, f'Архив ({template_archive_count})')
            
            
        except Exception as e:
            print(f"[WARN] Ошибка обновления счетчиков: {e}")
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
        columns_layout.setContentsMargins(0, 5, 0, 0)
        
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
            # ИСПРАВЛЕНИЕ 06.02.2026: Добавлена дополнительная стадия 3д визуализации (#18)
            columns = [
                'Новый заказ',
                'В ожидании',
                'Стадия 1: планировочные решения',
                'Стадия 2: рабочие чертежи',
                'Стадия 3: 3д визуализация (Дополнительная)',
                'Выполненный проект'
            ]
        
        columns_dict = {}
        
        for column_name in columns:
            column = CRMColumn(column_name, project_type, self.employee, self.can_edit, self.db, api_client=self.api_client)
            column.card_moved.connect(self.on_card_moved)
            columns_dict[column_name] = column
            columns_layout.addWidget(column)

        # ИСПРАВЛЕНИЕ 07.02.2026: Выравнивание по левому краю при сворачивании (#19)
        columns_layout.addStretch()

        widget.columns = columns_dict
        widget.project_type = project_type

        columns_widget.setLayout(columns_layout)
        scroll.setWidget(columns_widget)
        
        main_board_layout.addWidget(scroll, 1)
        widget.setLayout(main_board_layout)
        
        return widget
    
    def ensure_data_loaded(self):
        """Ленивая загрузка: данные загружаются при первом показе таба"""
        if not self._data_loaded:
            import time as _time
            _t0 = _time.perf_counter()
            self._data_loaded = True
            self._loading_guard = True
            self.data.prefer_local = True
            try:
                # Загружаем ТОЛЬКО текущую подвкладку (Индивидуальный или Шаблонный)
                current_index = self.project_tabs.currentIndex()
                current_type = 'Индивидуальный' if current_index == 0 else 'Шаблонный'
                self.load_cards_for_type(current_type)
            finally:
                self.data.prefer_local = False
                self._loading_guard = False
            print(f"[PERF] ensure_data_loaded БЛОКИРОВКА: {(_time.perf_counter()-_t0)*1000:.0f}ms")
            # Вторую подвкладку и архив загружаем отложенно, не блокируя UI
            other_type = 'Шаблонный' if current_index == 0 else 'Индивидуальный'
            if other_type == 'Шаблонный' and not hasattr(self, 'template_widget'):
                # СДП — шаблонных нет, сразу грузим архив
                if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                    QTimer.singleShot(200, self._deferred_load_archive)
            else:
                QTimer.singleShot(200, lambda t=other_type: self._deferred_load_other(t))

    def _deferred_load_other(self, project_type):
        """Отложенная загрузка второй подвкладки и архива"""
        self.data.prefer_local = True
        try:
            self.load_cards_for_type(project_type)
        finally:
            self.data.prefer_local = False
        # Архив — ещё позже
        if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
            QTimer.singleShot(300, self._deferred_load_archive)

    def _deferred_load_archive(self):
        """Отложенная загрузка архивных карточек (через API, не prefer_local)"""
        # Архив загружаем через API — локальная БД не содержит crm_cards
        self.load_archive_cards('Индивидуальный')
        if hasattr(self, 'template_archive_widget'):
            self.load_archive_cards('Шаблонный')

    def load_cards_for_current_tab(self):
        """Загрузка карточек для текущей активной вкладки"""
        current_index = self.project_tabs.currentIndex()
        if current_index == 0:
            self.load_cards_for_type('Индивидуальный')
            if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                self.load_archive_cards('Индивидуальный')
        elif current_index == 1:
            self.load_cards_for_type('Шаблонный')
            if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                self.load_archive_cards('Шаблонный')
                
    def load_cards_for_type(self, project_type):
        """Загрузка карточек для конкретного типа проекта с fallback на локальную БД"""
        import time as _time
        _t0 = _time.perf_counter()
        cards = None

        try:
            cards = self.data.get_crm_cards(project_type)
            _t1 = _time.perf_counter()
            print(f"[PERF] get_crm_cards({project_type}): {(_t1-_t0)*1000:.0f}ms, {len(cards) if cards else 0} шт")

            if project_type == 'Индивидуальный':
                board_widget = self.individual_widget
            else:
                if not hasattr(self, 'template_widget'):
                    return
                board_widget = self.template_widget

            if not hasattr(board_widget, 'columns'):
                return

            columns_dict = board_widget.columns

            # Отключаем отрисовку на время массовой загрузки
            for column in columns_dict.values():
                column.cards_list.setUpdatesEnabled(False)
                column.clear_cards()

            if cards:
                for card_data in cards:
                    try:
                        if not self.should_show_card_for_employee(card_data):
                            continue

                        column_name = card_data.get('column_name')
                        if column_name and column_name in columns_dict:
                            columns_dict[column_name].add_card(card_data, bulk=True)

                    except Exception as card_error:
                        try:
                            print(f"ОШИБКА при обработке карточки ID={card_data.get('id')}: {card_error}")
                        except (UnicodeEncodeError, OSError):
                            pass
                        continue

            _t2 = _time.perf_counter()
            print(f"[PERF] Виджеты карточек ({project_type}): {(_t2-_t1)*1000:.0f}ms")

            # Пакетное обновление после загрузки всех карточек
            for column in columns_dict.values():
                column.cards_list.updateGeometry()
                column.update_header_count()
                column.cards_list.setUpdatesEnabled(True)

            self.update_project_tab_counters()
            _t3 = _time.perf_counter()
            print(f"[PERF] ИТОГО load_cards_for_type({project_type}): {(_t3-_t0)*1000:.0f}ms")

        except Exception as e:
            # S3.2: Обработка ошибок без краша UI — traceback в лог, пустой список карточек
            try:
                print(f"[load_cards_for_type] КРИТИЧЕСКАЯ ОШИБКА ({project_type}): {e}")
                import traceback
                traceback.print_exc()
            except (UnicodeEncodeError, OSError):
                pass

            # Восстанавливаем отрисовку колонок (могли быть заблокированы выше)
            try:
                if project_type == 'Индивидуальный':
                    bw = getattr(self, 'individual_widget', None)
                else:
                    bw = getattr(self, 'template_widget', None)
                if bw and hasattr(bw, 'columns'):
                    for col in bw.columns.values():
                        col.cards_list.setUpdatesEnabled(True)
                        col.update_header_count()
            except Exception:
                pass
            # =========================================

    def _show_offline_notification(self, error=None):
        """Показать уведомление об offline режиме"""
        try:
            msg = 'Сервер недоступен. Данные загружены из локальной базы.\n'
            msg += 'Изменения будут синхронизированы при восстановлении связи.'
            if error:
                msg += f'\n\nОшибка: {str(error)[:100]}'
            CustomMessageBox(self, 'Offline режим', msg, 'warning').exec_()
        except Exception:
            pass

    def _api_update_card_with_fallback(self, card_id: int, updates: dict):
        """Обновить CRM карточку с fallback на локальную БД и очередью offline"""
        self.data.update_crm_card(card_id, updates)
            
    def on_tab_changed(self, index):
        """Обработка переключения вкладок"""
        # Пропускаем если ensure_data_loaded уже загружает данные
        if getattr(self, '_loading_guard', False):
            return
        # Активные карточки — из локальной БД (мгновенно)
        self.data.prefer_local = True
        try:
            if index == 0:
                self.load_cards_for_type('Индивидуальный')
            elif index == 1:
                self.load_cards_for_type('Шаблонный')
        finally:
            self.data.prefer_local = False

        # Архив — через API (локальная БД не содержит crm_cards)
        if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
            if index == 0:
                self.load_archive_cards('Индивидуальный')
            elif index == 1:
                self.load_archive_cards('Шаблонный')

        # Переключаем дашборд в соответствии с выбранной вкладкой
        mw = self.window()
        if hasattr(mw, 'switch_dashboard'):
            dashboard_key = 'СРМ (Индивидуальные)' if index == 0 else 'СРМ (Шаблонные)'
            mw.switch_dashboard(dashboard_key)
    
    def _get_sync_manager(self):
        """Получить SyncManager из главного окна"""
        mw = self.window()
        return getattr(mw, 'sync_manager', None)

    def on_card_moved(self, card_id, from_column, to_column, project_type):
        """Обработка перемещения карточки"""
        # Приостанавливаем синхронизацию на время перемещения
        sync = self._get_sync_manager()
        if sync:
            sync.pause_sync()
        try:
            self._do_card_move(card_id, from_column, to_column, project_type, sync)
        finally:
            # Гарантированно возобновляем синхронизацию
            if sync:
                sync.resume_sync()

    def _do_card_move(self, card_id, from_column, to_column, project_type, sync):
        """Внутренняя логика перемещения карточки (выделена для try/finally)"""
        # === ПРАВИЛО: Нельзя вернуться в "Новый заказ" ===
        if to_column == 'Новый заказ' and from_column != 'Новый заказ':
            CustomMessageBox(
                self, 'Перемещение запрещено',
                'Нельзя вернуть карточку в "Новый заказ".\n'
                'Используйте столбец "В ожидании" для приостановки.',
                'warning'
            ).exec_()
            self.load_cards_for_type(project_type)
            return

        # === ПРАВИЛО: Из "В ожидании" — только в прежний столбец или "Выполненный проект" ===
        if from_column == 'В ожидании' and to_column not in ['В ожидании', 'Выполненный проект']:
            card_info = self.data.get_crm_card(card_id)
            prev_col = card_info.get('previous_column') if card_info else None
            if prev_col and prev_col != 'Новый заказ' and to_column != prev_col:
                CustomMessageBox(
                    self, 'Перемещение запрещено',
                    f'Из "В ожидании" можно вернуть только в "{prev_col}" или "Выполненный проект".',
                    'warning'
                ).exec_()
                self.load_cards_for_type(project_type)
                return

        # Проверяем нужен ли выбор исполнителя ПЕРЕД перемещением
        if self.requires_executor_selection(to_column):
            # Получаем contract_id для передачи в диалог (для norm_days)
            _card_info = self.data.get_crm_card(card_id)
            _contract_id = _card_info.get('contract_id') if _card_info else None
            dialog = ExecutorSelectionDialog(self, card_id, to_column, project_type, self.api_client, contract_id=_contract_id)
            if dialog.exec_() != QDialog.Accepted:
                self.load_cards_for_type(project_type)
                return

        try:
            card_data = self.data.get_crm_card(card_id)

            if card_data:
                if 'концепция' in from_column and card_data.get('designer_completed') == 1:
                    CustomMessageBox(
                        self,
                        'Работа не принята',
                        'Дизайнер сдал работу, но вы еще не приняли её!\n\n'
                        'Сначала нажмите кнопку "Принять работу" на карточке,\n'
                        'затем переместите её на следующую стадию.',
                        'warning'
                    ).exec_()
                    self.load_cards_for_type(project_type)
                    return
                
                if ('планировочные' in from_column or 'чертежи' in from_column) and card_data.get('draftsman_completed') == 1:
                    CustomMessageBox(
                        self,
                        'Работа не принята',
                        'Чертёжник сдал работу, но вы еще не приняли её!\n\n'
                        'Сначала нажмите кнопку "Принять работу" на карточке,\n'
                        'затем переместите её на следующую стадию.',
                        'warning'
                    ).exec_()
                    self.load_cards_for_type(project_type)
                    return

                # ИСПРАВЛЕНИЕ: Проверка сдачи и принятия работы перед перемещением
                # Руководители могут перемещать свободно, автоматически принимая стадии
                if _has_perm(self.employee, self.api_client, 'crm_cards.complete_approval'):
                    # Для руководителей: автоматически принимаем пропущенные стадии
                    if from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                        # S-05: Используем DataAccess вместо прямого SQL
                        executors = self.data.get_incomplete_stage_executors(card_id, from_column)

                        if executors:
                            print(f"\n[AUTO ACCEPT] Автоматическое принятие стадии '{from_column}'")
                            print(f"             Найдено исполнителей: {len(executors)}")
                            count = self.data.auto_accept_stage(
                                card_id, from_column, self.employee['id'], project_type
                            )
                            print(f"Стадия '{from_column}' автоматически принята для {count} исполнителей")
                # Остальные с правом перемещения: проверяют сдачу и принятие
                elif _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                    if from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                        # S-05: Используем DataAccess вместо прямого SQL
                        info = self.data.get_stage_completion_info(card_id, from_column)
                        stage_info = info.get('stage')
                        approval_info = info.get('approval')
                        self.data.db.close()

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
                                f'{"" if submitted else ""} Работа должна быть сдана исполнителем<br>'
                                f'{"" if completed else ""} Работа должна быть принята менеджером<br>'
                                f'{"" if approved else ""} Стадия должна быть отмечена как выполненная<br><br>'
                                f'<i>Сначала выполните все требования, затем переместите карточку.</i>',
                                'warning'
                            ).exec_()
                            self.load_cards_for_type(project_type)
                            return
                else:
                    # Для всех остальных пользователей: строгая проверка
                    if from_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
                        # S-05: Используем DataAccess вместо прямого SQL
                        info = self.data.get_stage_completion_info(card_id, from_column)
                        stage_info = info.get('stage')

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
                                    f'{"" if submitted else ""} Работа должна быть сдана исполнителем<br>'
                                    f'{"" if completed else ""} Работа должна быть принята менеджером<br><br>'
                                    f'<i>Сначала выполните все требования, затем переместите карточку.</i>',
                                    'warning'
                                ).exec_()
                                self.load_cards_for_type(project_type)
                                return
        except Exception as e:
            print(f"! Ошибка проверки принятия работы: {e}")

        # Диалог завершения проекта ПЕРЕД перемещением, чтобы отмена не перемещала карточку
        if to_column == 'Выполненный проект':
            print(f"Показываем диалог завершения ПЕРЕД перемещением")
            completion_dialog = ProjectCompletionDialog(self, card_id, self.api_client)
            if completion_dialog.exec_() != QDialog.Accepted:
                print(f"Завершение отменено, карточка остается в '{from_column}'")
                self.load_cards_for_type(project_type)
                return
            # Диалог принят — продолжаем перемещение
            self._completion_accepted = True

        try:
            # Перемещение карточки: API-first с fallback на локальную БД
            api_success = False
            if self.data.is_online:
                try:
                    self.data.move_crm_card(card_id, to_column)
                    api_success = True
                except Exception as api_error:
                    print(f"! [API ERROR] {api_error}")

            if not api_success:
                # Fallback: обновляем через DataAccess (который тоже попробует API, затем локально)
                self.data.update_crm_card_column(card_id, to_column)

        except Exception as e:
            print(f" Ошибка обновления БД: {e}")
            CustomMessageBox(self, 'Ошибка', f'Не удалось переместить карточку: {e}', 'error').exec_()
            return

        # S9.3: Уведомление об успешном перемещении карточки
        print(f"[CRM] Карточка ID={card_id} успешно перемещена: '{from_column}' -> '{to_column}' ({project_type})")

        # ========== ИСПРАВЛЕННЫЙ БЛОК СБРОСА ==========
        # Полный сброс ТОЛЬКО при возврате из архива
        if from_column == 'Выполненный проект':
            try:
                print(f"[RESET] Возврат из архива: полный сброс данных")
                self.data.reset_stage_completion(card_id)
                self.data.reset_approval_stages(card_id)
                updates = {'deadline': None, 'is_approved': 0}
                self._api_update_card_with_fallback(card_id, updates)
                print(f"+ Карточка очищена для повторного прохождения")
            except Exception as e:
                print(f"! Ошибка полного сброса: {e}")

        # При обычном перемещении - сбрасываем ТОЛЬКО отметки о сдаче
        elif to_column != from_column:
            try:
                self.data.reset_stage_completion(card_id)
                print(f"+ Отметки о сдаче сброшены (согласования сохранены)")
            except Exception as e:
                print(f"! Ошибка сброса отметок: {e}")
        # ==============================================

        # Сброс дедлайна (ОСТАЕТСЯ БЕЗ ИЗМЕНЕНИЙ)
        reset_deadline_columns = ['Новый заказ', 'Выполненный проект']
        if to_column in reset_deadline_columns:
            try:
                updates = {'deadline': None}
                self._api_update_card_with_fallback(card_id, updates)
                print(f"+ Дедлайн сброшен для колонки '{to_column}'")
            except Exception as e:
                print(f"! Ошибка сброса дедлайна: {e}")

        if from_column == 'Новый заказ' and to_column != 'Выполненный проект':
            try:
                card_data = self.data.get_crm_card(card_id)
                contract_id = card_data.get('contract_id') if card_data else None
                if contract_id:
                    self.data.update_contract(contract_id, {'status': 'В работе'})
                print(f"+ Статус изменен на 'В работе'")
            except Exception as e:
                print(f"! Ошибка установки статуса: {e}")

        # ИСПРАВЛЕНИЕ 07.02.2026: Выбор исполнителя теперь происходит ДО перемещения (в начале функции)
        # Старый код удален, см. блок в начале on_card_moved()

        if to_column == 'Выполненный проект':
            # Диалог завершения уже был показан ПЕРЕД перемещением
            self.load_cards_for_type(project_type)
            if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
                self.load_archive_cards(project_type)
        else:
            print(f"\n[RELOAD] Перезагрузка карточек...")
            self.load_cards_for_type(project_type)

        print(f"{'='*60}\n")
        
    def requires_executor_selection(self, column_name):
        """Проверка, требуется ли выбор исполнителя"""
        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлена стадия 3д визуализации (#18)
        stage_columns = [
            'Стадия 1: планировочные решения',
            'Стадия 2: концепция дизайна',
            'Стадия 2: рабочие чертежи',
            'Стадия 3: рабочие чертежи',
            'Стадия 3: 3д визуализация (Дополнительная)'
        ]
        return column_name in stage_columns
    
    def select_executor(self, card_id, stage_name, project_type):
        """Диалог выбора исполнителя"""
        _card_info = self.data.get_crm_card(card_id)
        _contract_id = _card_info.get('contract_id') if _card_info else None
        dialog = ExecutorSelectionDialog(self, card_id, stage_name, project_type, self.api_client, contract_id=_contract_id)
        if dialog.exec_() != QDialog.Accepted:
            CustomMessageBox(self, 'Внимание', 'Выберите исполнителя для стадии', 'warning').exec_()
    
    def complete_project(self, card_id):
        """Завершение проекта"""
        dialog = ProjectCompletionDialog(self, card_id, self.api_client)
        if dialog.exec_() == QDialog.Accepted:
            self.refresh_current_tab()

    def show_crm_statistics(self, project_type):
        """Показ статистики CRM"""
        dialog = CRMStatisticsDialog(self, project_type, self.employee)
        dialog.exec_()
       
    def refresh_current_tab(self):
        """Обновление текущей активной вкладки"""
        current_index = self.project_tabs.currentIndex()
        # Активные карточки — из локальной БД (мгновенно)
        self.data.prefer_local = True
        try:
            if current_index == 0:
                self.load_cards_for_type('Индивидуальный')
            elif current_index == 1:
                self.load_cards_for_type('Шаблонный')
        finally:
            self.data.prefer_local = False

        # Архив — через API (локальная БД не содержит crm_cards)
        if _has_perm(self.employee, self.api_client, 'crm_cards.move'):
            if current_index == 0:
                self.load_archive_cards('Индивидуальный')
            elif current_index == 1:
                self.load_archive_cards('Шаблонный')

        self.update_project_tab_counters()

        # Обновляем дашборд
        mw = self.window()
        if hasattr(mw, 'refresh_current_dashboard'):
            mw.refresh_current_dashboard()
                
    def create_archive_board(self, project_type):
        """Создание архивной доски для типа проекта"""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 5, 0, 10)
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

        # ========== ФИЛЬТРЫ (СТИЛЬ КАК В ЗАРПЛАТАХ) ==========
        filters_group = QGroupBox('Фильтры')
        filters_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                border: none;
                border-radius: 0px;
                margin-top: 5px;
                padding-top: 5px;
                background-color: #f5f5f5;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 5px;
                color: #333333;
            }
        """)
        filters_layout = QVBoxLayout()

        # Кнопка свернуть/развернуть
        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 5)

        toggle_btn = IconLoader.create_icon_button('arrow-down-circle', '', 'Развернуть фильтры', icon_size=14)
        toggle_btn.setFixedSize(24, 24)
        toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                padding: 2px;
            }
            QPushButton:hover {
                background-color: #D4E4BC;
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

        apply_btn = IconLoader.create_icon_button('check-square', 'Применить фильтры', icon_size=12)
        # ИСПРАВЛЕНИЕ 06.02.2026: Уменьшен padding для стандартной высоты 28px (#12)
        apply_btn.setStyleSheet("""
            QPushButton {
                background-color: #27AE60;
                color: white;
                padding: 4px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
        """)
        buttons_layout.addWidget(apply_btn)

        reset_btn = IconLoader.create_icon_button('refresh', 'Сбросить фильтры', icon_size=12)
        # ИСПРАВЛЕНИЕ 06.02.2026: Уменьшен padding для стандартной высоты 28px (#12)
        reset_btn.setStyleSheet("""
            QPushButton {
                padding: 4px 12px;
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

        # ИСПРАВЛЕНИЕ 07.02.2026: Автоприменение фильтров при изменении (НОВОЕ 3)
        # Все фильтры автоматически применяются при изменении значения
        period_combo.currentTextChanged.connect(apply_filters)
        year_spin.valueChanged.connect(apply_filters)
        quarter_combo.currentIndexChanged.connect(apply_filters)
        month_combo.currentIndexChanged.connect(apply_filters)
        date_criterion_combo.currentIndexChanged.connect(apply_filters)
        city_combo.currentIndexChanged.connect(apply_filters)
        agent_combo.currentIndexChanged.connect(apply_filters)
        address_input.textChanged.connect(apply_filters)

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
        try:
            if project_type == 'Индивидуальный':
                if not hasattr(self, 'individual_archive_widget'):
                    return
                archive_widget = self.individual_archive_widget
            else:
                if not hasattr(self, 'template_archive_widget'):
                    return
                archive_widget = self.template_archive_widget

            # Используем DataAccess (учитывает prefer_local)
            cards = self.data.get_archived_crm_cards(project_type)

            archive_layout = archive_widget.archive_layout
            while archive_layout.count():
                child = archive_layout.takeAt(0)
                if child.widget():
                    child.widget().deleteLater()

            if cards:
                for card_data in cards:
                    archive_card = ArchiveCard(card_data, self.db, employee=self.employee, api_client=self.api_client)
                    archive_layout.addWidget(archive_card)
            else:
                empty_label = QLabel('Архив пуст')
                empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
                empty_label.setAlignment(Qt.AlignCenter)
                archive_layout.addWidget(empty_label)

            self.update_project_tab_counters()

        except Exception as e:
            print(f"ОШИБКА загрузки архива: {e}")
            import traceback
            traceback.print_exc()

    def load_archive_filter_data(self, project_type, city_combo, agent_combo):
        """Загрузка данных для фильтров архива"""
        try:
            # Используем DataAccess (учитывает prefer_local)
            cards = self.data.get_archived_crm_cards(project_type)

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
            agents = self.data.get_all_agents()
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
                if not hasattr(self, 'individual_archive_widget'):
                    return
                archive_widget = self.individual_archive_widget
            else:
                if not hasattr(self, 'template_archive_widget'):
                    return
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
            # ИСПРАВЛЕНИЕ: Проверяем is_online перед API запросом
            if self.data.is_online:
                try:
                    cards = self.data.get_archived_crm_cards(project_type)
                except Exception as e:
                    print(f"[WARN] API ошибка загрузки архива для фильтрации: {e}")
                    cards = self.data.get_archived_crm_cards(project_type)
            else:
                cards = self.data.get_archived_crm_cards(project_type)

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
                    # ИСПРАВЛЕНИЕ: Передаём api_client для синхронизации
                    archive_card = ArchiveCard(card_data, self.db, employee=self.employee, api_client=self.api_client)
                    archive_layout.addWidget(archive_card)
            else:
                empty_label = QLabel('Нет карточек, соответствующих фильтрам')
                empty_label.setStyleSheet('color: #999; font-size: 14px; padding: 20px;')
                empty_label.setAlignment(Qt.AlignCenter)
                archive_layout.addWidget(empty_label)

            # Примечание: FlowLayout не поддерживает addStretch, карточки автоматически располагаются

            print(f"Фильтрация завершена: {len(filtered_cards)} из {len(cards)} карточек\n")

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

        # Руководитель и старший менеджер видят всё
        if _emp_has_pos(self.employee, 'Руководитель студии', 'Старший менеджер проектов'):
            return True

        # Назначенный менеджер
        if _emp_has_pos(self.employee, 'Менеджер'):
            if card_data.get('manager_id') == employee_id:
                return True

        # Назначенный ГАП
        if _emp_has_pos(self.employee, 'ГАП'):
            if card_data.get('gap_id') == employee_id:
                return True

        # Назначенный СДП
        if _emp_has_pos(self.employee, 'СДП'):
            if card_data.get('sdp_id') == employee_id:
                return True

        # Дизайнер
        if _emp_has_pos(self.employee, 'Дизайнер'):
            if column_name == 'Стадия 2: концепция дизайна':
                designer_name = card_data.get('designer_name')
                designer_completed = card_data.get('designer_completed', 0)
                return (designer_name == employee_name) and (designer_completed != 1)

        # Чертёжник
        if _emp_has_pos(self.employee, 'Чертёжник'):
            if project_type == 'Индивидуальный':
                allowed_columns = ['Стадия 1: планировочные решения', 'Стадия 3: рабочие чертежи']
            else:
                allowed_columns = ['Стадия 1: планировочные решения', 'Стадия 2: рабочие чертежи']

            if column_name in allowed_columns:
                draftsman_name = card_data.get('draftsman_name')
                draftsman_completed = card_data.get('draftsman_completed', 0)
                return (draftsman_name == employee_name) and (draftsman_completed != 1)

        # Замерщик
        if _emp_has_pos(self.employee, 'Замерщик'):
            if card_data.get('surveyor_id') == employee_id:
                has_measurement = card_data.get('measurement_image_link') or card_data.get('survey_date')
                return not has_measurement

        return False

    def on_sync_update(self, updated_cards):
        """
        Обработчик обновления данных от SyncManager.
        Вызывается при изменении CRM карточек другими пользователями.
        Данные уже обновлены в локальной БД — используем prefer_local для мгновенного обновления UI.
        """
        try:
            print(f"[SYNC] Получено обновление CRM карточек: {len(updated_cards)} записей")
            # Обновляем из локальной БД (данные уже синхронизированы), не блокируя UI
            self.data.prefer_local = True
            try:
                self.load_cards_for_current_tab()
            finally:
                self.data.prefer_local = False
        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации CRM карточек: {e}")
            import traceback
            traceback.print_exc()


# ИСПРАВЛЕНИЕ 07.02.2026: Класс для вертикального текста в свёрнутых колонках (#19)
class VerticalLabel(QWidget):
    """Виджет с вертикальным текстом для свёрнутых колонок"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self.setMinimumWidth(40)
        self.setMaximumWidth(40)

    def setText(self, text):
        self._text = text
        self.update()

    def text(self):
        return self._text

    def paintEvent(self, event):
        from PyQt5.QtGui import QPainter, QFont, QFontMetrics
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Фон
        painter.fillRect(self.rect(), QColor('#ffffff'))

        # Настройка шрифта
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(QColor('#333333'))

        # Поворот на 90 градусов (текст снизу вверх)
        painter.translate(self.width() / 2 + 5, self.height() - 10)
        painter.rotate(-90)

        # Рисуем текст
        painter.drawText(0, 0, self._text)

        painter.end()

    def sizeHint(self):
        return QSize(40, 200)


class CRMColumn(BaseKanbanColumn):
    card_moved = pyqtSignal(int, str, str, str)

    def __init__(self, column_name, project_type, employee, can_edit, db, api_client=None):
        super().__init__()
        self.column_name = column_name
        self.project_type = project_type
        self.employee = employee
        self.can_edit = can_edit
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.api_client = api_client
        self._board_name = f"crm_{project_type.lower().replace(' ', '_')}"
        self.init_ui()
        self._apply_initial_collapse_state()
        
    def init_ui(self):
        self.setFrameShape(QFrame.StyledPanel)
        self.setMinimumWidth(self._original_min_width)
        self.setMaximumWidth(self._original_max_width)
        self.setStyleSheet("""
            CRMColumn {
                background-color: #F5F5F5;
                border: 1px solid #d9d9d9;
                border-radius: 5px;
            }
        """)

        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        # ИСПРАВЛЕНИЕ 06.02.2026: Заголовок с кнопкой сворачивания (#19)
        header_container = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(5)

        self.header_label = QLabel()
        self.header_label.setStyleSheet("""
            font-weight: bold;
            font-size: 13px;
            padding: 10px;
            background-color: #ffffff;
            border-radius: 4px;
        """)
        self.header_label.setWordWrap(True)
        self.update_header_count()
        header_layout.addWidget(self.header_label, 1)

        # Кнопка сворачивания - используем иконку стрелки как у фильтров
        self.collapse_btn = IconLoader.create_icon_button('arrow-left-circle', '', 'Свернуть колонку', icon_size=14)
        self.collapse_btn.setFixedSize(20, 20)
        self.collapse_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: none;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #E0E0E0; }
        """)
        self.collapse_btn.clicked.connect(self.toggle_collapse)
        header_layout.addWidget(self.collapse_btn)

        header_container.setLayout(header_layout)
        layout.addWidget(header_container)
        
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

    # ИСПРАВЛЕНИЕ 07.02.2026: Применение начального состояния сворачивания (#19)
    def _apply_initial_collapse_state(self):
        """Применить начальное состояние сворачивания (из настроек или по умолчанию)"""
        # Проверяем, есть ли сохранённое состояние
        saved_state = self._settings.get_column_collapsed_state(
            self._board_name, self.column_name, default=None
        )

        # Если есть сохранённое состояние - используем его
        if saved_state is not None:
            if saved_state:
                self._collapse_column()
        else:
            # Нет сохранённого состояния - применяем умолчание
            # Столбец "3д визуализация (Дополнительная)" свёрнут по умолчанию (только для шаблонных)
            is_3d_viz = '3д визуализация' in self.column_name.lower() or '3d визуализация' in self.column_name.lower()
            is_template = self.project_type == 'Шаблонный'
            if is_3d_viz and is_template:
                print(f"[CRM] Сворачиваю колонку по умолчанию: {self.column_name}")
                self._collapse_column()

    # _collapse_column, _expand_column, toggle_collapse, update_header_count
    # наследуются из BaseKanbanColumn

    def _make_vertical_label(self):
        """Создать вертикальный лейбл для свёрнутой колонки."""
        return VerticalLabel()

    def _create_card_widget(self, card_data):
        """Создать виджет CRM-карточки."""
        return CRMCard(card_data, self.can_edit, self.db, self.employee, api_client=self.api_client)

    def add_card(self, card_data, bulk=False):
        """Добавление карточки в колонку. bulk=True пропускает updateGeometry/update_header_count."""
        card_id = card_data.get('id')

        try:
            card_widget = CRMCard(card_data, self.can_edit, self.db, self.employee, api_client=self.api_client)

            recommended_size = card_widget.sizeHint()
            exact_height = recommended_size.height()

            card_widget.setMinimumHeight(exact_height)

            item = QListWidgetItem()
            item.setData(Qt.UserRole, card_id)
            item.setSizeHint(QSize(200, exact_height + 10))

            self.cards_list.addItem(item)
            self.cards_list.setItemWidget(item, card_widget)

            if not bulk:
                self.cards_list.updateGeometry()
                self.update_header_count()

        except Exception as e:
            try:
                print(f"ОШИБКА создания карточки ID={card_id}: {e}")
                import traceback
                traceback.print_exc()
            except (UnicodeEncodeError, OSError):
                pass

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
            except Exception:
                pass
            
    # clear_cards наследуется из BaseKanbanColumn

class CRMCard(QFrame):
    def __init__(self, card_data, can_edit, db, employee=None, api_client=None):
        super().__init__()
        self.card_data = card_data
        self.can_edit = can_edit
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.employee = employee
        self.api_client = api_client

        # ========== ЗАЩИТА ==========
        try:
            self.init_ui()
        except Exception as e:
            try:
                print(f" ОШИБКА init_ui() для карточки ID={card_data.get('id')}: {e}")
                import traceback
                traceback.print_exc()
            except (UnicodeEncodeError, OSError):
                pass
            
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

    def _get_contract_yandex_folder(self, contract_id):
        """Получение пути к папке договора на Яндекс.Диске

        Returns:
            str: Путь к папке на Яндекс.Диске или None
        """
        if not contract_id:
            return None

        try:
            if self.data.is_multi_user:
                # Многопользовательский режим - получаем через API
                contract = self.data.get_contract(contract_id)
                return contract.get('yandex_folder_path') if contract else None
            else:
                # Локальный режим - получаем из локальной БД
                conn = self.data.db.connect()
                cursor = conn.cursor()
                cursor.execute('SELECT yandex_folder_path FROM contracts WHERE id = ?', (contract_id,))
                result = cursor.fetchone()
                conn.close()
                return result['yandex_folder_path'] if result else None
        except Exception as e:
            print(f"[ERROR] Ошибка получения пути к папке договора: {e}")
            return None

    def sizeHint(self):
        """Рекомендуемый размер карточки"""
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')

        # Проверяем, является ли пользователь замерщиком
        is_surveyor = _emp_has_pos(self.employee, 'Замерщик')

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
        
        if self.employee and _has_perm(self.employee, self.api_client, 'crm_cards.move'):
            if ('концепция дизайна' in current_column and self.card_data.get('designer_completed') == 1) or \
               (('планировочные' in current_column or 'чертежи' in current_column) and self.card_data.get('draftsman_completed') == 1):
                height += 100  # work_done_label (wordWrap, до 4 строк)
                height += 114  # 3 кнопки: Принять(28+6) + На исправление(28+6) + Клиенту(28+6)

        buttons_count = 0
        if self.employee:
            # Кнопка "Сдать работу" / "Ожидайте проверку" для дизайнеров/чертёжников
            if _emp_has_pos(self.employee, 'Дизайнер', 'Чертёжник'):
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
        """Определение статуса работы над карточкой.
        Проверяющие по стадиям:
        - Индивидуальные: Стадия 1,2 → СДП; Стадия 3 → ГАП
        - Шаблонные: Стадия 1 → Менеджер; Стадия 2 → ГАП; Стадия 3 → Менеджер
        """
        current_column = self.card_data.get('column_name', '')
        project_type = self.card_data.get('project_type', '')

        # Определяем проверяющего по стадии и типу проекта
        def get_reviewer_name(col, proj_type):
            if proj_type == 'Индивидуальный':
                if 'Стадия 1' in col or 'Стадия 2' in col:
                    return 'СДП'
                if 'Стадия 3' in col:
                    return 'ГАП'
            else:  # Шаблонный
                if 'Стадия 1' in col:
                    return 'Менеджер'
                if 'Стадия 2' in col:
                    return 'ГАП'
                if 'Стадия 3' in col:
                    return 'Менеджер'
            return 'Менеджер'

        reviewer = get_reviewer_name(current_column, project_type)

        # Проверяем статус работы дизайнера (Стадия 2: концепция дизайна — только индивидуальные)
        if 'Стадия 2' in current_column and 'концепция' in current_column:
            designer_name = self.card_data.get('designer_name')
            designer_completed = self.card_data.get('designer_completed', 0)

            if designer_name and designer_completed == 0:
                return "В работе у исполнителя"

            if designer_completed == 1:
                return f"В работе у {reviewer}"

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
                return "В работе у исполнителя"

            if draftsman_completed == 1:
                return f"В работе у {reviewer}"

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
                border: 2px solid #909090;
                background-color: #f5f5f5;
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
                background-color: transparent;
                color: #27AE60;
                font-size: 9px;
                font-weight: bold;
                padding: 2px 6px;
                border: 2px solid #27AE60;
                border-radius: 4px;
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

        # Площадь и город с иконками
        info_container = QWidget()
        info_layout = QHBoxLayout()
        info_layout.setSpacing(4)
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setAlignment(Qt.AlignVCenter)

        if self.card_data.get('area'):
            # Иконка площади
            area_icon = IconLoader.create_icon_button('box', '', '', icon_size=12)
            area_icon.setFixedSize(12, 12)
            area_icon.setStyleSheet('border: none; background: transparent; padding: 0; margin: 0;')
            area_icon.setEnabled(False)
            info_layout.addWidget(area_icon, 0, Qt.AlignVCenter)

            # Текст площади
            area_label = QLabel(f"{self.card_data['area']} м²")
            area_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            area_label.setAlignment(Qt.AlignVCenter)
            info_layout.addWidget(area_label, 0, Qt.AlignVCenter)

            if self.card_data.get('city'):
                # Разделитель
                sep_label = QLabel("|")
                sep_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                sep_label.setAlignment(Qt.AlignVCenter)
                info_layout.addWidget(sep_label, 0, Qt.AlignVCenter)

        if self.card_data.get('city'):
            # Иконка города
            city_icon = IconLoader.create_icon_button('map-pin', '', '', icon_size=12)
            city_icon.setFixedSize(12, 12)
            city_icon.setStyleSheet('border: none; background: transparent; padding: 0; margin: 0;')
            city_icon.setEnabled(False)
            info_layout.addWidget(city_icon, 0, Qt.AlignVCenter)

            # Текст города
            city_label = QLabel(self.card_data['city'])
            city_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            city_label.setAlignment(Qt.AlignVCenter)
            info_layout.addWidget(city_label, 0, Qt.AlignVCenter)

        info_layout.addStretch()
        info_container.setLayout(info_layout)
        info_row.addWidget(info_container, 1)

        # Тип агента с цветом
        if self.card_data.get('agent_type'):
            agent_type = self.card_data['agent_type']
            agent_color = self.data.get_agent_color(agent_type)

            agent_label = QLabel(agent_type)
            agent_label.setFixedHeight(24)  # Фиксированная высота
            if agent_color:
                agent_label.setStyleSheet(f'''
                    background-color: {agent_color};
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    border: 2px solid {agent_color};
                ''')
            else:
                agent_label.setStyleSheet('''
                    background-color: #95A5A6;
                    color: white;
                    font-size: 10px;
                    font-weight: bold;
                    padding: 3px 8px;
                    border-radius: 4px;
                    border: 2px solid #95A5A6;
                ''')
            agent_label.setAlignment(Qt.AlignCenter)
            info_row.addWidget(agent_label, 0)

        layout.addLayout(info_row)

        # Проверяем, является ли пользователь замерщиком
        is_surveyor = _emp_has_pos(self.employee, 'Замерщик')

        # 4. СОТРУДНИКИ (СВОРАЧИВАЕМЫЕ) - скрываем для замерщика
        if not is_surveyor:
            employees_widget = self.create_collapsible_employees_section()
            if employees_widget:
                layout.addWidget(employees_widget, 0)

        # 5. Теги - скрываем для замерщика
        if not is_surveyor and self.card_data.get('tags'):
            tags_container = QWidget()
            tags_layout = QHBoxLayout()
            tags_layout.setSpacing(4)
            tags_layout.setContentsMargins(8, 3, 8, 3)
            tags_layout.setAlignment(Qt.AlignVCenter)

            # Иконка тега
            tag_icon = IconLoader.create_icon_button('tag', '', '', icon_size=10)
            tag_icon.setFixedSize(10, 10)
            tag_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
            tag_icon.setEnabled(False)
            tags_layout.addWidget(tag_icon, 0, Qt.AlignVCenter)

            # Текст тега
            tags_text = QLabel(self.card_data['tags'])
            tags_text.setStyleSheet('color: white; font-size: 10px; font-weight: bold; background-color: transparent;')
            tags_text.setAlignment(Qt.AlignVCenter)
            tags_layout.addWidget(tags_text, 0, Qt.AlignVCenter)

            tags_layout.addStretch()
            tags_container.setLayout(tags_layout)
            tags_container.setStyleSheet('''
                background-color: #FF6B6B;
                border-radius: 4px;
            ''')
            tags_container.setFixedHeight(28)
            layout.addWidget(tags_container, 0)

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
                        text = f"{deadline_display}  ПРОСРОЧЕН ({abs(working_days)} раб.дн.)"
                    elif working_days == 0:
                        bg_color = '#DC143C'
                        text_color = 'white'
                        text = f"{deadline_display}  СЕГОДНЯ!"
                    elif working_days <= 1:
                        bg_color = '#E74C3C'
                        text_color = 'white'
                        text = f"{deadline_display}  ({working_days} раб.дн.)"
                    elif working_days <= 2:
                        bg_color = '#F39C12'
                        text_color = 'white'
                        text = f"{deadline_display} ({working_days} раб.дн.)"
                    else:
                        bg_color = '#E0E0E0'
                        text_color = '#333333'
                        text = f"{deadline_display} ({working_days} раб.дн.)"

                    # Создаем контейнер для иконки и текста
                    deadline_container = QWidget()
                    deadline_layout = QHBoxLayout()
                    deadline_layout.setSpacing(4)
                    deadline_layout.setContentsMargins(8, 3, 8, 3)
                    deadline_layout.setAlignment(Qt.AlignVCenter)

                    # Иконка дедлайна
                    deadline_icon = IconLoader.create_icon_button('deadline', '', '', icon_size=10)
                    deadline_icon.setFixedSize(10, 10)
                    deadline_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
                    deadline_icon.setEnabled(False)
                    deadline_layout.addWidget(deadline_icon, 0, Qt.AlignVCenter)

                    # Текст дедлайна
                    deadline_text = QLabel(text)
                    deadline_text.setStyleSheet(f'color: {text_color}; font-size: 10px; font-weight: bold; background-color: transparent;')
                    deadline_text.setAlignment(Qt.AlignVCenter)
                    deadline_layout.addWidget(deadline_text, 0, Qt.AlignVCenter)

                    deadline_layout.addStretch()
                    deadline_container.setLayout(deadline_layout)
                    deadline_container.setStyleSheet(f'''
                        background-color: {bg_color};
                        border-radius: 4px;
                    ''')
                    deadline_container.setFixedHeight(28)
                    layout.addWidget(deadline_container, 0)

                except Exception as e:
                    # В случае ошибки пытаемся преобразовать в нормальный формат
                    try:
                        deadline_date = QDate.fromString(deadline_to_show, 'yyyy-MM-dd')
                        deadline_display = deadline_date.toString('dd.MM.yyyy')
                    except Exception:
                        deadline_display = deadline_to_show

                    # Создаем контейнер для иконки и текста
                    deadline_container = QWidget()
                    deadline_layout = QHBoxLayout()
                    deadline_layout.setSpacing(4)
                    deadline_layout.setContentsMargins(8, 3, 8, 3)
                    deadline_layout.setAlignment(Qt.AlignVCenter)

                    # Иконка дедлайна
                    deadline_icon = IconLoader.create_icon_button('deadline', '', '', icon_size=10)
                    deadline_icon.setFixedSize(10, 10)
                    deadline_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
                    deadline_icon.setEnabled(False)
                    deadline_layout.addWidget(deadline_icon, 0, Qt.AlignVCenter)

                    # Текст дедлайна
                    deadline_text = QLabel(f"Дедлайн: {deadline_display}")
                    deadline_text.setStyleSheet('color: #333333; font-size: 10px; font-weight: bold; background-color: transparent;')
                    deadline_text.setAlignment(Qt.AlignVCenter)
                    deadline_layout.addWidget(deadline_text, 0, Qt.AlignVCenter)

                    deadline_layout.addStretch()
                    deadline_container.setLayout(deadline_layout)
                    deadline_container.setStyleSheet('''
                        background-color: #E0E0E0;
                        border-radius: 4px;
                    ''')
                    deadline_container.setFixedHeight(28)
                    layout.addWidget(deadline_container, 0)
                
        
        # 6.5. ИНДИКАТОР "РАБОТА СДАНА" + КНОПКА "ПРИНЯТЬ РАБОТУ"
        # Менеджер может принимать/отклонять работу только в шаблонных проектах
        is_template_project = self.card_data.get('project_type', '') == 'Шаблонный'
        is_only_manager = _emp_only_pos(self.employee, 'Менеджер')
        can_review_work = _has_perm(self.employee, self.api_client, 'crm_cards.complete_approval')
        if is_only_manager and not is_template_project:
            can_review_work = False
        if self.employee and can_review_work:
            completed_info = []
            
            if 'концепция дизайна' in current_column and self.card_data.get('designer_completed') == 1:
                designer_name = self.card_data.get('designer_name', 'N/A')
                completed_info.append(f"Дизайнер {designer_name}")
            
            if ('планировочные' in current_column or 'чертежи' in current_column) and self.card_data.get('draftsman_completed') == 1:
                draftsman_name = self.card_data.get('draftsman_name', 'N/A')
                completed_info.append(f"Чертёжник {draftsman_name}")
            
            if completed_info:
                work_done_label = QLabel(f"Работа сдана: {', '.join(completed_info)}\nТребуется проверка и перемещение на следующую стадию")
                work_done_label.setWordWrap(True)
                work_done_label.setStyleSheet('''
                    color: white;
                    background-color: #27AE60;
                    padding: 10px 12px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                    border: 2px solid #1E8449;
                ''')
                layout.addWidget(work_done_label, 0)
                
                # ========== КНОПКА "ПРИНЯТЬ РАБОТУ" (SVG) ==========
                accept_btn = IconLoader.create_icon_button('accept', 'Принять работу', 'Принять выполненную работу', icon_size=12)
                accept_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #1E8449;
                        color: white;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        min-height: 20px;
                        max-height: 20px;
                    }
                    QPushButton:hover { background-color: #17703C; }
                """)
                accept_btn.setFixedHeight(28)
                accept_btn.clicked.connect(self.accept_work)
                layout.addWidget(accept_btn, 0)

                # Кнопка "Отправить на исправление"
                reject_btn = QPushButton('На исправление')
                reject_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #E74C3C;
                        color: white;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        min-height: 20px;
                        max-height: 20px;
                    }
                    QPushButton:hover { background-color: #C0392B; }
                """)
                reject_btn.setFixedHeight(28)
                reject_btn.clicked.connect(self.reject_work)
                layout.addWidget(reject_btn, 0)

                # Кнопка "Отправить на согласование"
                client_send_btn = QPushButton('Клиенту на согласование')
                client_send_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498DB;
                        color: white;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 10px;
                        font-weight: bold;
                        min-height: 20px;
                        max-height: 20px;
                    }
                    QPushButton:hover { background-color: #2980B9; }
                """)
                client_send_btn.setFixedHeight(28)
                client_send_btn.clicked.connect(self.send_to_client)
                layout.addWidget(client_send_btn, 0)

                # Кнопка "Клиент согласовал" — показывается когда статус workflow = client_approval
                try:
                    wf_states = self.data.get_workflow_state(self.card_data['id']) or []
                    is_client_approval = any(
                        s.get('status') == 'client_approval'
                        and s.get('stage_name') == current_column
                        for s in wf_states
                    )
                except Exception:
                    is_client_approval = False

                if is_client_approval:
                    client_ok_btn = QPushButton('Клиент согласовал')
                    client_ok_btn.setStyleSheet("""
                        QPushButton {
                            background-color: #27AE60;
                            color: white;
                            padding: 4px 12px;
                            border-radius: 4px;
                            font-size: 10px;
                            font-weight: bold;
                            min-height: 20px;
                            max-height: 20px;
                        }
                        QPushButton:hover { background-color: #1E8449; }
                    """)
                    client_ok_btn.setFixedHeight(28)
                    client_ok_btn.clicked.connect(self.client_approved)
                    layout.addWidget(client_ok_btn, 0)

        # 7. КНОПКИ
        buttons_added = False

        # Кнопка "Сдать работу" / "Ожидайте проверку" для дизайнеров/чертежников
        emp_pos = self.employee.get('position', '') if self.employee else ''
        emp_sec = self.employee.get('secondary_position', '') if self.employee else ''
        is_executor_role = emp_pos in ['Дизайнер', 'Чертёжник'] or emp_sec in ['Дизайнер', 'Чертёжник']
        if self.employee and is_executor_role:
            # Проверяем, сдана ли уже работа
            work_already_submitted = False
            if 'концепция дизайна' in current_column:
                emp_name = self.employee.get('full_name', '')
                if self.card_data.get('designer_name') == emp_name and self.card_data.get('designer_completed', 0) == 1:
                    work_already_submitted = True
            elif 'планировочные' in current_column or 'чертежи' in current_column:
                emp_name = self.employee.get('full_name', '')
                if self.card_data.get('draftsman_name') == emp_name and self.card_data.get('draftsman_completed', 0) == 1:
                    work_already_submitted = True

            if work_already_submitted:
                # Работа уже сдана — показываем неактивную кнопку "Ожидайте проверку"
                waiting_btn = QPushButton('Ожидайте проверку')
                waiting_btn.setEnabled(False)
                waiting_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95A5A6;
                        color: white;
                        border: none;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                        max-height: 19px;
                        min-height: 19px;
                    }
                """)
                layout.addWidget(waiting_btn, 0)
                buttons_added = True
            elif self.is_assigned_to_current_user(self.employee):
                # ========== КНОПКА "СДАТЬ РАБОТУ" (SVG) ==========
                submit_btn = IconLoader.create_icon_button('submit', 'Сдать работу', 'Отметить работу как выполненную', icon_size=12)
                submit_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #27AE60;
                        color: white;
                        border: none;
                        padding: 4px 12px;
                        border-radius: 4px;
                        font-size: 11px;
                        font-weight: bold;
                        max-height: 19px;
                        min-height: 19px;
                    }
                    QPushButton:hover { background-color: #229954; }
                    QPushButton:pressed { background-color: #1E8449; }
                """)
                submit_btn.clicked.connect(self.submit_work)
                layout.addWidget(submit_btn, 0)
                buttons_added = True

        # Кнопка "Редактирование карточки" для всех с правами редактирования (кроме замерщика)
        if self.can_edit and not is_surveyor:
            # S2.2: Проверка права crm.update для кнопки редактирования
            has_update_perm = _has_perm(self.employee, self.api_client, 'crm_cards.update')
            # ========== КНОПКА РЕДАКТИРОВАНИЯ (SVG) ==========
            edit_btn = IconLoader.create_icon_button('edit', 'Редактирование карточки', 'Редактировать данные карточки', icon_size=12)
            edit_btn.setStyleSheet("""
                QPushButton {
                    background-color: #E0E0E0;
                    color: #333333;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    max-height: 19px;
                    min-height: 19px;
                }
                QPushButton:hover { background-color: #D0D0D0; }
                QPushButton:pressed { background-color: #C0C0C0; }
            """)
            edit_btn.setEnabled(has_update_perm)
            if not has_update_perm:
                edit_btn.setStyleSheet(edit_btn.styleSheet() + "QPushButton:disabled { opacity: 0.5; background-color: #e0e0e0; }")
            edit_btn.clicked.connect(self.edit_card)
            layout.addWidget(edit_btn, 0)
            buttons_added = True

        # ========== КНОПКА "ДАННЫЕ ПРОЕКТА" (SVG) ==========
        if self.card_data.get('project_data_link'):
            data_btn = IconLoader.create_icon_button('folder', 'Данные проекта', 'Открыть папку проекта', icon_size=12)
            data_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd93c;
                    color: white;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    max-height: 19px;
                    min-height: 19px;
                }
                QPushButton:hover { background-color: #2980B9; }
                QPushButton:pressed { background-color: #21618C; }
            """)
            data_btn.clicked.connect(self.show_project_data)
            layout.addWidget(data_btn, 0)
            buttons_added = True

        # ========== КНОПКА "ДАТА ЗАМЕРА" ==========
        # Показываем кнопку только если замер НЕ загружен и есть права (для Руководителя, Старшего менеджера, Менеджера и Замерщика)
        # Проверяем как новое поле (measurement_image_link из contracts), так и старое (survey_date из crm_cards)
        has_measurement = self.card_data.get('measurement_image_link') or self.card_data.get('survey_date')
        is_surveyor = _emp_has_pos(self.employee, 'Замерщик')
        can_add_measurement = _has_perm(self.employee, self.api_client, 'crm_cards.update') or is_surveyor
        # Для замерщика разрешаем добавлять замер без can_edit, для остальных требуется can_edit
        if not has_measurement and can_add_measurement and (self.can_edit or is_surveyor):
            survey_btn = IconLoader.create_icon_button('calendar-plus', 'Добавить замер', 'Установить дату замера', icon_size=12)
            survey_btn.setStyleSheet("""
                QPushButton {
                    background-color: #F39C12;
                    color: white;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    max-height: 19px;
                    min-height: 19px;
                }
                QPushButton:hover { background-color: #E67E22; }
                QPushButton:pressed { background-color: #D35400; }
            """)
            # S2.2: Визуальный индикатор если нет права crm.update
            has_update_perm_survey = _has_perm(self.employee, self.api_client, 'crm_cards.update')
            survey_btn.setEnabled(has_update_perm_survey)
            if not has_update_perm_survey:
                survey_btn.setStyleSheet(survey_btn.styleSheet() + "QPushButton:disabled { opacity: 0.5; background-color: #e0e0e0; }")
            survey_btn.clicked.connect(self.add_survey_date)
            layout.addWidget(survey_btn, 0)
            buttons_added = True

        # ========== КНОПКА "ТЗ" ==========
        # Показываем кнопку только если ТЗ НЕ добавлено и есть права (только для Руководителя, Старшего менеджера и Менеджера)
        # Проверяем как новое поле (tech_task_link из contracts), так и старое (tech_task_file из crm_cards)
        # Кнопка "Добавить ТЗ" (не показываем замерщику)
        has_tech_task = self.card_data.get('tech_task_link') or self.card_data.get('tech_task_file')
        can_add_tech_task = _has_perm(self.employee, self.api_client, 'crm_cards.update')
        if self.can_edit and not has_tech_task and can_add_tech_task and not is_surveyor:
            tz_btn = IconLoader.create_icon_button('plus-circle', 'Добавить ТЗ', 'Добавить техническое задание', icon_size=12)
            tz_btn.setStyleSheet("""
                QPushButton {
                    background-color: #9B59B6;
                    color: white;
                    border: none;
                    padding: 4px 12px;
                    border-radius: 4px;
                    font-size: 11px;
                    font-weight: bold;
                    max-height: 19px;
                    min-height: 19px;
                }
                QPushButton:hover { background-color: #8E44AD; }
                QPushButton:pressed { background-color: #7D3C98; }
            """)
            # S2.2: Визуальный индикатор если нет права crm.update
            has_update_perm_tz = _has_perm(self.employee, self.api_client, 'crm_cards.update')
            tz_btn.setEnabled(has_update_perm_tz)
            if not has_update_perm_tz:
                tz_btn.setStyleSheet(tz_btn.styleSheet() + "QPushButton:disabled { opacity: 0.5; background-color: #e0e0e0; }")
            tz_btn.clicked.connect(self.add_tech_task)
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
            employees.append(('Ст.менеджер', self.card_data['senior_manager_name'], 'senior_manager', False))
        # ИСПРАВЛЕНИЕ 06.02.2026: СДП только для индивидуальных проектов (#20)
        if project_type == 'Индивидуальный' and self.card_data.get('sdp_name'):
            employees.append(('СДП', self.card_data['sdp_name'], 'sdp', False))
        if self.card_data.get('gap_name'):
            employees.append(('ГАП', self.card_data['gap_name'], 'gap', False))
        if self.card_data.get('manager_name'):
            employees.append(('Менеджер', self.card_data['manager_name'], 'manager', False))
        if self.card_data.get('surveyor_name'):
            employees.append(('Замерщик', self.card_data['surveyor_name'], 'surveyor', False))

        if self.card_data.get('designer_name'):
            is_completed = self.card_data.get('designer_completed', 0) == 1
            employees.append(('Дизайнер', self.card_data['designer_name'], 'designer', is_completed))

        if self.card_data.get('draftsman_name'):
            is_completed = self.card_data.get('draftsman_completed', 0) == 1
            employees.append(('Чертёжник', self.card_data['draftsman_name'], 'draftsman', is_completed))
        
        if not employees:
            return None
        
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        self.team_toggle_btn = IconLoader.create_icon_button('team', f"Команда ({len(employees)})", '', icon_size=10)
        self.team_toggle_btn.setIcon(IconLoader.load('chevron-right'))
        self.team_toggle_btn.setIconSize(QSize(10, 10))
        self.team_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #F8F9FA;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 3px 5px;
                text-align: left;
                font-size: 10px;
                font-weight: bold;
                color: #555;
                max-height: 20px;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #E8E9EA;
            }
        """)
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
                    border-radius: 4px;
                    border: 1px solid #81C784;
                ''')
            elif role_key == highlight_role:
                employee_label.setStyleSheet('''
                    font-size: 12px; 
                    color: #F57C00; 
                    font-weight: bold;
                    background-color: #FFE082;
                    padding: 3px 5px;
                    border-radius: 4px;
                    border: 1px solid #FFB74D;
                ''')
            else:
                employee_label.setStyleSheet('font-size: 10px; color: #444; background-color: transparent;')
            
            employee_row_layout.addWidget(employee_label, 1)
            
            # ========== КНОПКА "ПЕРЕНАЗНАЧИТЬ" ==========
            # Кнопка доступна только для управленческих ролей и только для дизайнеров/чертежников
            can_show_reassign = (
                _has_perm(self.employee, self.api_client, 'crm_cards.assign_executor') and
                role_key in ['designer', 'draftsman'] and
                not is_completed
            )

            if can_show_reassign:

                reassign_btn = IconLoader.create_icon_button('refresh', '', 'Переназначить исполнителя', icon_size=12)
                reassign_btn.setFixedSize(22, 22)
                reassign_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #FF9800;
                        color: white;
                        border: none;
                        border-radius: 4px;
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
                        border: none;
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
            self.team_toggle_btn.setIcon(IconLoader.load('chevron-right'))
            self.team_toggle_btn.setIconSize(QSize(10, 10))
        else:
            self.employees_container.show()
            self.team_toggle_btn.setIcon(IconLoader.load('chevron-down'))
            self.team_toggle_btn.setIconSize(QSize(10, 10))

        self.update_card_height_immediately()

    def update_card_height_immediately(self):
        """Немедленное обновление высоты карточки БЕЗ прыганий"""
        from PyQt5.QtWidgets import QApplication
        # Используем sizeHint() — ручной расчет высоты, корректно учитывающий wordWrap и видимость секций
        new_height = self.sizeHint().height()
        self.setFixedHeight(new_height)

        parent_widget = self.parent()
        while parent_widget:
            if isinstance(parent_widget, QListWidget):
                for i in range(parent_widget.count()):
                    item = parent_widget.item(i)
                    if parent_widget.itemWidget(item) == self:
                        item.setSizeHint(QSize(200, new_height + 10))
                        parent_widget.scheduleDelayedItemsLayout()
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
    
    @debounce_click(delay_ms=2000)
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
                # Обновляем stage_executors.completed на сервере (API)
                api_ok = False
                if self.data.is_multi_user:
                    try:
                        api_ok = self.data.complete_stage_for_executor(
                            self.card_data['id'],
                            current_column,
                            current_employee['id']
                        )
                    except Exception as e:
                        print(f"[API] Ошибка complete_stage_for_executor: {e}")

                # Fallback: обновляем локальную БД
                if not api_ok:
                    self.data.complete_stage_for_executor(
                        self.card_data['id'],
                        current_column,
                        current_employee['id']
                    )

                # Записываем дату в timeline через workflow
                try:
                    if self.data.is_multi_user:
                        self.data.workflow_submit(self.card_data['id'])
                except Exception:
                    pass

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
    
    @debounce_click(delay_ms=2000)
    def accept_work(self):
        """Принятие работы менеджером"""
        if not _has_perm(self.employee, self.api_client, 'crm_cards.complete_approval'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на принятие работы', 'error').exec_()
            return
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
                # Сохраняем принятие работы
                self.data.save_manager_acceptance(
                    self.card_data['id'],
                    current_column,
                    executor_name,
                    self.employee['id']
                )

                # Записываем дату приемки в timeline через workflow
                try:
                    if self.data.is_multi_user:
                        self.data.workflow_accept(self.card_data['id'])
                except Exception:
                    pass

                # ========== НОВОЕ: ОБНОВЛЕНИЕ ОТЧЕТНОГО МЕСЯЦА ДОПЛАТЫ ==========
                try:
                    contract_id = self.card_data['contract_id']
                    contract = self.data.get_contract(contract_id)
                    current_month = QDate.currentDate().toString('yyyy-MM')
                    
                    print(f"\n[ACCEPT WORK] Принятие работы:")
                    print(f"   Стадия: {current_column}")
                    print(f"   Исполнитель: {executor_name}")
                    print(f"   Текущий месяц: {current_month}")
                    
                    # Получаем ID исполнителя
                    conn = self.data.db.connect()
                    cursor = conn.cursor()
                    
                    # Находим ID исполнителя по имени
                    cursor.execute('''
                    SELECT id FROM employees WHERE full_name = ? LIMIT 1
                    ''', (executor_name,))
                    
                    executor_row = cursor.fetchone()
                    if not executor_row:
                        print(f" Не найден исполнитель: {executor_name}")
                        self.data.db.close()
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
                            print(f"   Отчетный месяц ДОПЛАТЫ установлен: {current_month}")
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
                                print(f"   Это вторая или последующая стадия чертежника - месяц будет установлен")

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
                                print(f"   Отчетный месяц ПОЛНОЙ ОПЛАТЫ установлен: {current_month}")
                            else:
                                print(f"    Не найдена выплата для обновления (contract_id={contract_id}, executor_id={executor_id}, stage={current_column})")
                    
                    conn.commit()
                    self.data.db.close()
                    
                except Exception as e:
                    print(f" Ошибка обновления отчетного месяца: {e}")
                    import traceback
                    traceback.print_exc()
                # ================================================================
                
                # Сброс completed
                if executor_role == 'дизайнер':
                    self.data.reset_designer_completion(self.card_data['id'])
                else:
                    self.data.reset_draftsman_completion(self.card_data['id'])
                
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


    @debounce_click(delay_ms=2000)
    def reject_work(self):
        """Отправить работу на исправление с загрузкой файла правок на ЯД"""
        if not _has_perm(self.employee, self.api_client, 'crm_cards.complete_approval'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на отправку на исправление', 'error').exec_()
            return
        current_column = self.card_data.get('column_name', '')
        contract_id = self.card_data.get('contract_id')

        # Открываем диалог загрузки файла правок
        dialog = RejectWithCorrectionsDialog(self, current_column, contract_id, self.data.api_client, self.data.db)
        if dialog.exec_() == QDialog.Accepted:
            try:
                corrections_path = dialog.corrections_folder_path or ''
                if self.data.is_multi_user:
                    self.data.workflow_reject(self.card_data['id'], corrections_path=corrections_path)
                CustomMessageBox(
                    self, 'Отправлено',
                    f'Работа по стадии "{current_column}" отправлена на исправление.',
                    'success'
                ).exec_()
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()
            except Exception as e:
                CustomMessageBox(self, 'Ошибка', f'Не удалось отправить на исправление: {e}', 'error').exec_()

    def send_to_client(self):
        """Отправить на согласование клиенту"""
        if not _has_perm(self.employee, self.api_client, 'crm_cards.complete_approval'):
            CustomMessageBox(self, 'Ошибка', 'У вас нет прав на отправку клиенту', 'error').exec_()
            return
        current_column = self.card_data.get('column_name', '')
        reply = CustomQuestionBox(
            self,
            'Согласование с клиентом',
            f'Отправить работу по стадии "{current_column}" на согласование клиенту?\n\n'
            f'Дедлайн будет приостановлен до получения ответа.'
        ).exec_()
        if reply == QDialog.Accepted:
            try:
                if self.data.is_multi_user:
                    self.data.workflow_client_send(self.card_data['id'])
                CustomMessageBox(
                    self, 'Отправлено',
                    f'Работа отправлена клиенту на согласование.\nДедлайн приостановлен.',
                    'success'
                ).exec_()
                parent = self.parent()
                while parent:
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()
            except Exception as e:
                CustomMessageBox(self, 'Ошибка', f'Не удалось отправить клиенту: {e}', 'error').exec_()

    def client_approved(self):
        """Клиент согласовал работу"""
        current_column = self.card_data.get('column_name', '')
        try:
            if self.data.is_multi_user:
                self.data.workflow_client_ok(self.card_data['id'])
            CustomMessageBox(
                self, 'Согласовано',
                f'Клиент согласовал работу по стадии "{current_column}".\nДедлайн возобновлен.',
                'success'
            ).exec_()
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()
        except Exception as e:
            CustomMessageBox(self, 'Ошибка', f'Ошибка: {e}', 'error').exec_()

    def edit_card(self):
        """Редактирование карточки"""
        from ui.crm_card_edit_dialog import CardEditDialog
        dialog = CardEditDialog(self, self.card_data, False, self.employee, api_client=self.api_client)
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
            CustomMessageBox(self, 'Информация', 'Ссылка на данные проекта не установлена').exec_()

    def add_tech_task(self):
        """Добавить техническое задание"""
        dialog = TechTaskDialog(self, self.card_data.get('id'), api_client=self.api_client)
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
        dialog = MeasurementDialog(self, self.card_data.get('id'), self.employee, api_client=self.api_client)
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
        dialog = SurveyDateDialog(self, self.card_data.get('id'), self.api_client)
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
            current_column,
            api_client=self.api_client
        )
        
        if dialog.exec_() == QDialog.Accepted:
            # Перезагружаем текущую вкладку
            parent = self.parent()
            while parent:
                if isinstance(parent, CRMTab):
                    parent.refresh_current_tab()
                    break
                parent = parent.parent()

class PreviewLoaderThread(threading.Thread):
    """Фоновый поток для загрузки превью изображений с Яндекс.Диска.

    ИСПРАВЛЕНИЕ R-04: Добавлен флаг _stopped для защиты от SEGFAULT при обращении
    к удалённому Qt-объекту. Callback вызывается через QTimer.singleShot(0, ...)
    для гарантии выполнения в главном потоке.
    """

    def __init__(self, files_to_load, callback, yandex_token):
        super().__init__(daemon=True)
        # files_to_load: [(file_id, public_link, contract_id, stage, file_name, yandex_path), ...]
        self.files_to_load = files_to_load
        self.callback = callback  # Функция вызывается с (file_id, pixmap)
        self.yandex_token = yandex_token
        self._stop_event = threading.Event()
        # ИСПРАВЛЕНИЕ R-04: быстрый флаг для предотвращения callback на удалённый объект
        self._stopped = False

    def stop(self):
        """Остановить загрузку и заблокировать дальнейшие callback"""
        self._stopped = True
        self._stop_event.set()

    def _safe_callback(self, file_id, pixmap):
        """Безопасный вызов callback через QTimer в главном потоке.

        ИСПРАВЛЕНИЕ R-04: Проверяем _stopped перед вызовом, чтобы не обращаться
        к удалённому Qt-объекту. QTimer.singleShot гарантирует вызов в main thread.
        """
        if self._stopped:
            return
        from PyQt5.QtCore import QTimer
        # Захватываем значения в замыкание
        _fid = file_id
        _pix = pixmap
        _cb = self.callback
        _self = self

        def _do_callback():
            if _self._stopped:
                return
            try:
                _cb(_fid, _pix)
            except RuntimeError:
                pass  # Qt-объект уже удалён

        QTimer.singleShot(0, _do_callback)

    def run(self):
        """Загрузка превью в фоновом потоке"""
        from utils.preview_generator import PreviewGenerator
        from utils.yandex_disk import YandexDiskManager
        import tempfile
        import urllib.request
        import urllib.parse

        for item in self.files_to_load:
            if self._stop_event.is_set():
                break
            # Поддержка обоих форматов: с yandex_path и без
            if len(item) >= 6:
                file_id, public_link, contract_id, stage, file_name, yandex_path = item
            else:
                file_id, public_link, contract_id, stage, file_name = item
                yandex_path = ''

            try:
                # Проверяем кэш ещё раз (мог появиться)
                cache_path = PreviewGenerator.get_cache_path(contract_id, stage, file_name)
                if os.path.exists(cache_path):
                    pixmap = PreviewGenerator.load_preview_from_cache(cache_path)
                    if pixmap:
                        # ИСПРАВЛЕНИЕ R-04: безопасный callback через main thread
                        self._safe_callback(file_id, pixmap)
                        continue

                # Если нет public_link, пробуем скачать через Яндекс API по yandex_path
                if not public_link and yandex_path and self.yandex_token:
                    try:
                        yd = YandexDiskManager(self.yandex_token)
                        public_link = yd.get_public_link(yandex_path)
                    except Exception:
                        pass

                if not public_link:
                    continue

                # Формируем прямую ссылку для скачивания
                # Яндекс.Диск: добавляем ?dl=1 для прямого скачивания
                download_url = public_link
                if '?' in download_url:
                    download_url += '&dl=1'
                else:
                    download_url += '?dl=1'

                # Скачиваем во временный файл
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file_name)[1]) as tmp_file:
                    tmp_path = tmp_file.name

                try:
                    # Используем urllib для скачивания
                    req = urllib.request.Request(download_url, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                    })
                    with urllib.request.urlopen(req, timeout=30) as response:
                        with open(tmp_path, 'wb') as f:
                            f.write(response.read())

                    # Генерируем превью
                    pixmap = PreviewGenerator.generate_image_preview(tmp_path)
                    if pixmap:
                        # Сохраняем в кэш
                        PreviewGenerator.save_preview_to_cache(pixmap, cache_path)
                        # ИСПРАВЛЕНИЕ R-04: безопасный callback через main thread
                        self._safe_callback(file_id, pixmap)

                finally:
                    # Удаляем временный файл
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass

            except Exception as e:
                print(f"[PreviewLoader] Ошибка загрузки превью для file_id={file_id}: {e}")
                continue


# ========== ИМПОРТ ВЫДЕЛЕННЫХ КЛАССОВ (в конце файла для избежания циклических импортов) ==========
from ui.crm_dialogs import (RejectWithCorrectionsDialog, ProjectDataDialog,  # noqa: E402
    ExecutorSelectionDialog, ProjectCompletionDialog, CRMStatisticsDialog,
    ExportPDFDialog, PDFExportSuccessDialog, ReassignExecutorDialog,
    SurveyDateDialog, TechTaskDialog, MeasurementDialog)
from ui.crm_archive import ArchiveCard, ArchiveCardDetailsDialog  # noqa: E402
# ================================================

