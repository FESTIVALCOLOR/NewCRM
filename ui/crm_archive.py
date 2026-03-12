# -*- coding: utf-8 -*-
"""Архивные классы CRM, выделенные из crm_tab.py"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QDateEdit,
                             QGroupBox, QSpinBox, QTableWidget, QHeaderView,
                             QTableWidgetItem, QTabWidget, QTextEdit, QSizePolicy)
from PyQt5.QtCore import Qt, QDate, pyqtSignal, QUrl, QTimer
from PyQt5.QtGui import QColor
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from utils.icon_loader import IconLoader
from ui.custom_title_bar import CustomTitleBar
from ui.custom_combobox import CustomComboBox
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
from utils.table_settings import ProportionalResizeTable, apply_no_focus_delegate
from utils.date_utils import format_date, format_month_year
from config import YANDEX_DISK_TOKEN
from utils.resource_path import resource_path
import os
import threading


class ArchiveCard(QFrame):
    """Упрощенная карточка для архива"""

    def __init__(self, card_data, db, card_type='crm', employee=None, api_client=None):
        super().__init__()
        self.card_data = card_data
        self.data = DataAccess(api_client=api_client)
        self.db = self.data.db
        self.card_type = card_type  # 'crm' или 'supervision'
        self.employee = employee  # Информация о текущем сотруднике
        self.api_client = api_client  # сохраняем для передачи в дочерние диалоги
        self.init_ui()
    
    def init_ui(self):
        self.setFrameShape(QFrame.Box)

        # ИСПРАВЛЕНИЕ: API возвращает contract_status, а не status
        status = self.card_data.get('contract_status') or self.card_data.get('status', '')

        if 'СДАН' in status:
            card_bg_color = '#E8F8F5'
            border_color = '#27AE60'
        elif 'РАСТОРГНУТ' in status:
            card_bg_color = '#FADBD8'
            border_color = '#E74C3C'
        elif 'АВТОРСКИЙ НАДЗОР' in status or 'НАДЗОР' in status:
            card_bg_color = '#E3F2FD'
            border_color = '#2196F3'
        else:
            card_bg_color = '#FAFAFA'
            border_color = '#DDDDDD'
        
        self.setStyleSheet(f"""
            ArchiveCard {{
                background-color: {card_bg_color};
                border: 1px solid {border_color};
                border-radius: 4px;
                padding: 10px;
            }}
            ArchiveCard:hover {{
                background-color: {card_bg_color};
                border: 2px solid {border_color};
            }}
        """)

        # Фиксированный размер для одинаковой сетки карточек
        self.setFixedSize(328, 235)

        layout = QVBoxLayout()
        layout.setSpacing(6)
        layout.setContentsMargins(15, 12, 15, 12)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        contract_label = QLabel(f"<b>Договор:</b> {self.card_data.get('contract_number', 'N/A')}")
        contract_label.setStyleSheet('font-size: 11px; color: #666; background-color: transparent;')
        info_layout.addWidget(contract_label)

        address = self.card_data.get('address', 'Адрес не указан')
        address_label = QLabel(f"<b>{address}</b>")
        address_label.setWordWrap(True)
        address_label.setStyleSheet('font-size: 13px; color: #222; font-weight: bold; background-color: transparent;')
        info_layout.addWidget(address_label)

        # Площадь, город и тип агента на одной строке (как в активных карточках)
        info_row = QHBoxLayout()
        info_row.setSpacing(4)
        info_row.setContentsMargins(0, 0, 0, 0)

        info_container = QWidget()
        details_layout = QHBoxLayout()
        details_layout.setSpacing(4)
        details_layout.setContentsMargins(0, 0, 0, 0)
        details_layout.setAlignment(Qt.AlignVCenter)

        if self.card_data.get('area'):
            area_icon = IconLoader.create_icon_button('box', '', '', icon_size=11)
            area_icon.setFixedSize(11, 11)
            area_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
            area_icon.setEnabled(False)
            details_layout.addWidget(area_icon, 0, Qt.AlignVCenter)

            area_label = QLabel(f"{self.card_data['area']} м²")
            area_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            details_layout.addWidget(area_label, 0, Qt.AlignVCenter)

            if self.card_data.get('city'):
                sep_label = QLabel("|")
                sep_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                details_layout.addWidget(sep_label, 0, Qt.AlignVCenter)

        if self.card_data.get('city'):
            city_icon = IconLoader.create_icon_button('map-pin', '', '', icon_size=11)
            city_icon.setFixedSize(11, 11)
            city_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
            city_icon.setEnabled(False)
            details_layout.addWidget(city_icon, 0, Qt.AlignVCenter)

            city_label = QLabel(self.card_data['city'])
            city_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
            details_layout.addWidget(city_label, 0, Qt.AlignVCenter)

        details_layout.addStretch()
        info_container.setLayout(details_layout)
        info_row.addWidget(info_container, 1)

        # Тип агента — справа в той же строке
        if self.card_data.get('agent_type'):
            agent_type = self.card_data['agent_type']
            agent_color = self.data.get_agent_color(agent_type)

            agent_label = QLabel(agent_type)
            agent_label.setFixedHeight(22)
            color = agent_color or '#95A5A6'
            agent_label.setStyleSheet(f'''
                background-color: {color};
                color: white;
                font-size: 10px;
                font-weight: bold;
                padding: 2px 6px;
                border-radius: 4px;
            ''')
            agent_label.setAlignment(Qt.AlignCenter)
            info_row.addWidget(agent_label, 0)

        info_layout.addLayout(info_row)

        if status:
            status_label = QLabel(f"Статус: {status}")
            if 'СДАН' in status:
                status_style = 'color: white; background-color: #27AE60;'
            elif 'РАСТОРГНУТ' in status:
                status_style = 'color: white; background-color: #E74C3C;'
            elif 'НАДЗОР' in status:
                status_style = 'color: white; background-color: #2196F3;'
            else:
                status_style = 'color: white; background-color: #95A5A6;'
            status_label.setStyleSheet(f'{status_style} padding: 3px 8px; border-radius: 4px; font-size: 10px; font-weight: bold;')
            info_layout.addWidget(status_label)

        layout.addLayout(info_layout)

        # Stretch для прижатия кнопок к низу
        layout.addStretch(1)

        # ========== КНОПКА "ПЕРЕВЕСТИ В АВТОРСКИЙ НАДЗОР" ==========
        if 'АВТОРСКИЙ НАДЗОР' not in status and 'НАДЗОР' not in status:
            supervision_btn = IconLoader.create_icon_button(
                'shield-white', 'В авторский надзор', 'Перевести в авторский надзор', icon_size=12)
            supervision_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 4px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                    max-height: 22px;
                    min-height: 22px;
                }
                QPushButton:hover { background-color: #1976D2; }
                QPushButton:pressed { background-color: #1565C0; }
            """)
            supervision_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            supervision_btn.clicked.connect(self._transfer_to_supervision)
            layout.addWidget(supervision_btn)

        # ========== КНОПКА ПОДРОБНЕЕ ==========
        details_btn = IconLoader.create_icon_button('info', 'Подробнее', 'Просмотр деталей', icon_size=12)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                border: none;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 22px;
                min-height: 22px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        details_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        details_btn.clicked.connect(self.show_details)
        layout.addWidget(details_btn)

        self.setLayout(layout)
        
    def _transfer_to_supervision(self):
        """Перевести карточку в статус 'АВТОРСКИЙ НАДЗОР'"""
        reply = CustomQuestionBox(
            self,
            'Подтверждение',
            'Перевести карточку в авторский надзор?'
        ).exec_()

        if reply == QDialog.Accepted:
            try:
                contract_id = self.card_data.get('contract_id')
                if not contract_id:
                    CustomMessageBox(self, 'Ошибка', 'Не найден contract_id', 'error').exec_()
                    return

                self.data.update_contract(contract_id, {'status': 'АВТОРСКИЙ НАДЗОР'})

                CustomMessageBox(
                    self, 'Успех',
                    'Карточка переведена в авторский надзор',
                    'success'
                ).exec_()

                # Обновляем список архива через родительский CRMTab
                parent = self.parent()
                while parent:
                    from ui.crm_tab import CRMTab
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                    parent = parent.parent()

                # Обновляем вкладку СРМ надзора чтобы новая карточка появилась сразу
                try:
                    from ui.main_window import MainWindow
                    main_win = self.window()
                    if isinstance(main_win, MainWindow) and main_win.crm_supervision_tab:
                        main_win.crm_supervision_tab.refresh_current_tab()
                except Exception:
                    pass

            except Exception as e:
                print(f"[ArchiveCard] Ошибка перевода в авторский надзор: {e}")
                import traceback
                traceback.print_exc()
                CustomMessageBox(self, 'Ошибка', f'Не удалось перевести: {e}', 'error').exec_()

    def show_details(self):
        """Показать полную информацию о проекте"""
        # ИСПРАВЛЕНИЕ: Передаём api_client для возможности синхронизации
        dialog = ArchiveCardDetailsDialog(self, self.card_data, self.data.db, self.card_type, self.employee, self.api_client)
        dialog.exec_()

class ArchiveCardDetailsDialog(QDialog):
    """Диалог с полной информацией об архивной карточке"""
    _sync_ended = pyqtSignal()

    def __init__(self, parent, card_data, db, card_type='crm', employee=None, api_client=None):
        super().__init__(parent)
        self.card_data = card_data
        self.data = getattr(parent, 'data', None) or DataAccess(api_client=api_client)
        self.db = self.data.db
        self.card_type = card_type  # 'crm' или 'supervision'
        self.employee = employee  # Информация о текущем сотруднике
        self.api_client = api_client  # сохраняем для передачи в дочерние диалоги
        self._active_sync_count = 0
        self._sync_ended.connect(self._on_sync_ended)

        # ========== RESIZE SUPPORT ==========
        self.resizing = False
        self.resize_edge = None
        self.resize_start_pos = None
        self.resize_start_geometry = None
        self.resize_margin = 8

        # ========== УБИРАЕМ СТАНДАРТНУЮ РАМКУ ==========
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Исправление черного фона всплывающих подсказок
        from utils.tooltip_fix import apply_tooltip_palette
        apply_tooltip_palette(self)

        self.init_ui()

        # Запускаем синхронизацию файлов после построения UI
        self._run_file_sync()
        
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
                    border: 1px solid #E0E0E0;
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
            # ИСПРАВЛЕНИЕ: API возвращает contract_status, а не status
            status_value = self.card_data.get('contract_status') or self.card_data.get('status', 'N/A')
            info_layout.addRow('<b>Статус:</b>', QLabel(str(status_value)))
            
            if self.card_data.get('termination_reason'):
                reason_label = QLabel(str(self.card_data['termination_reason']))
                reason_label.setWordWrap(True)
                reason_label.setStyleSheet('color: #E74C3C; padding: 5px; background-color: #FADBD8; border-radius: 4px;')
                info_layout.addRow('<b>Причина расторжения:</b>', reason_label)
            
            separator = QLabel('<hr>')
            info_layout.addRow(separator)

            # Теги и общий дедлайн
            if self.card_data.get('tags'):
                tags_label = QLabel(f"<b>Теги:</b> {self.card_data['tags']}")
                tags_label.setStyleSheet('padding: 5px; background-color: #FFF3CD; border-radius: 4px; border: none;')
                tags_label.setWordWrap(True)
                info_layout.addRow(tags_label)

            if self.card_data.get('deadline'):
                deadline_label = QLabel(f"<b>Общий дедлайн:</b> {format_date(self.card_data['deadline'], 'N/A')}")
                deadline_label.setStyleSheet('padding: 5px; background-color: #ffffff; border-radius: 4px; border: none;')
                info_layout.addRow(deadline_label)

            # ИСПРАВЛЕНИЕ: Компактная отметка о замере (одной строчкой)
            if self.card_type == 'crm':
                try:
                    contract_id = self.card_data.get('contract_id')
                    conn = self.data.db.connect()
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
                    self.data.db.close()

                    if survey:
                        survey_date = QDate.fromString(survey['survey_date'], 'yyyy-MM-dd')
                        survey_label = QLabel(
                            f"Замер выполнен: {survey_date.toString('dd.MM.yyyy')} | Замерщик: {survey['surveyor_name']}"
                        )
                        survey_label.setStyleSheet('''
                            color: #27AE60;
                            font-size: 10px;
                            font-weight: bold;
                            background-color: #E8F8F5;
                            padding: 5px;
                            border-radius: 4px;
                            margin-bottom: 4px;
                        ''')
                        survey_label.setWordWrap(True)
                        info_layout.addRow(survey_label)
                except Exception as e:
                    print(f" Ошибка загрузки информации о замере: {e}")

                # НОВОЕ: ВЫПОЛНЕННЫЕ СТАДИИ
                try:
                    conn = self.data.db.connect()
                    cursor = conn.cursor()

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
                        for stage in completed_stages:
                            date_str = format_date(stage.get('completed_date'))

                            stage_label = QLabel(
                                f"{stage['stage_name']} | Исполнитель: {stage['executor_name']} | Дата: {date_str}"
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
                            stage_label.setWordWrap(True)
                            info_layout.addRow(stage_label)

                except Exception as e:
                    print(f" Ошибка загрузки выполненных стадий: {e}")

            elif self.card_type == 'supervision':
                # НОВОЕ: ПРИНЯТЫЕ СТАДИИ НАДЗОРА
                try:
                    conn = self.data.db.connect()
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
                        self.data.db.close()

                        if accepted_history:
                            for history in accepted_history:
                                date_str = format_date(history['created_at'])
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
                                info_layout.addRow(stage_label)
                    else:
                        self.data.db.close()

                except Exception as e:
                    print(f" Ошибка загрузки принятых стадий надзора: {e}")

            history_label = QLabel('<b>История проекта:</b>')
            history_label.setStyleSheet('margin-top: 10px; font-size: 12px;')
            info_layout.addRow(history_label)

            # Фильтр по типу действия
            filter_row = QHBoxLayout()
            filter_lbl = QLabel('Фильтр:')
            filter_lbl.setStyleSheet('font-size: 10px; color: #666;')
            filter_row.addWidget(filter_lbl)
            self._archive_history_filter = QComboBox()
            self._archive_history_filter.addItems([
                'Все действия', 'Стадии исполнителей',
                'Перемещение карточки', 'Пауза / возобновление',
                'Назначение исполнителей', 'Сдача / приёмка работы',
                'Стадии и согласование', 'Оплаты',
                'Изменение дедлайна', 'Загрузка файлов',
                'Удаление файлов', 'Замер', 'Прочее',
            ])
            self._archive_history_filter.setStyleSheet('font-size: 10px; padding: 2px 5px;')
            self._archive_history_filter.setFixedWidth(200)
            filter_row.addWidget(self._archive_history_filter)
            filter_row.addStretch()
            filter_widget = QWidget()
            filter_widget.setLayout(filter_row)
            info_layout.addRow(filter_widget)

            # Контейнер для истории (будет обновляться фильтром)
            self._archive_history_container = QVBoxLayout()
            history_container_widget = QWidget()
            history_container_widget.setLayout(self._archive_history_container)
            info_layout.addRow(history_container_widget)

            # Загружаем данные
            card_id = self.card_data.get('id')

            # Стадии исполнителей
            self._archive_stages = self.data.get_stage_history(card_id) or []

            # ActionHistory (все записи)
            self._archive_action_history = []
            try:
                if self.card_type == 'supervision':
                    self._archive_action_history = self.data.get_supervision_history(card_id) or []
                else:
                    entity_type = 'crm_card'
                    try:
                        self._archive_action_history = self.data.get_action_history(entity_type, card_id) or []
                    except Exception:
                        pass
            except Exception as e:
                print(f"[ARCHIVE] Ошибка загрузки истории: {e}")

            # Подключаем фильтр
            self._archive_history_filter.currentTextChanged.connect(self._on_archive_history_filter)
            # Рендерим начальное состояние
            self._on_archive_history_filter('Все действия')
            
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
                team_layout.addRow('Старший менеджер:', QLabel(str(self.card_data['senior_manager_name'])))
            if self.card_data.get('sdp_name'):
                team_layout.addRow('СДП:', QLabel(str(self.card_data['sdp_name'])))
            if self.card_data.get('gap_name'):
                team_layout.addRow('ГАП:', QLabel(str(self.card_data['gap_name'])))
            if self.card_data.get('manager_name'):
                team_layout.addRow('Менеджер:', QLabel(str(self.card_data['manager_name'])))
            if self.card_data.get('surveyor_name'):
                team_layout.addRow('Замерщик:', QLabel(str(self.card_data['surveyor_name'])))
            if self.card_data.get('designer_name'):
                team_layout.addRow('Дизайнер:', QLabel(str(self.card_data['designer_name'])))
            if self.card_data.get('draftsman_name'):
                team_layout.addRow('Чертёжник:', QLabel(str(self.card_data['draftsman_name'])))
            if self.card_data.get('dan_name'):
                team_layout.addRow('ДАН:', QLabel(str(self.card_data['dan_name'])))
            
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
            contract_id = self.card_data.get('contract_id')

            # Проверяем права доступа к вкладке оплаты
            from utils.permissions import _has_perm
            can_view_payments = _has_perm(self.employee, self.api_client, 'crm_cards.payments')

            # Определяем тип оплат и название вкладки
            show_payments_tab = False
            payments_tab_title = 'Оплаты'
            payments = []

            # Показываем вкладку оплат если есть права — архивные карточки
            # всегда имеют статус СДАН/РАСТОРГНУТ/АВТОРСКИЙ НАДЗОР
            if can_view_payments and contract_id:
                if self.card_type == 'supervision':
                    payments = self.data.get_payments_for_supervision(contract_id)
                    payments_tab_title = 'Оплаты надзора'
                    show_payments_tab = True
                elif self.card_type == 'crm':
                    payments = self.data.get_payments_for_crm(contract_id)
                    payments_tab_title = 'Оплаты'
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
                    # Создаем таблицу для отображения выплат - используем ProportionalResizeTable
                    payments_table = ProportionalResizeTable()
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
                        'Выплата', 'Аванс', 'Доплата', 'Отчетный месяц'
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
                        role_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                        role_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 0, role_label)

                        # ФИО
                        name_label = QLabel(payment.get('employee_name', ''))
                        name_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                        name_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 1, name_label)

                        # Стадия
                        stage_label = QLabel(payment.get('stage_name', '-'))
                        stage_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                        stage_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 2, stage_label)

                        # Тип выплаты
                        payment_type = payment.get('payment_type', 'Полная оплата')
                        type_label = QLabel(payment_type)
                        type_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                        type_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 3, type_label)

                        # ИСПРАВЛЕНИЕ: Используем правильные колонки из базы данных
                        final_amount = payment.get('final_amount', 0)

                        # Распределяем суммы по типу выплаты
                        if payment_type == 'Полная оплата':
                            # Выплата
                            amount_label = QLabel(f"{final_amount:,.0f}".replace(',', ' '))
                            amount_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            amount_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            payments_table.setCellWidget(row, 4, amount_label)

                            # Аванс и Доплата
                            advance_empty = QLabel('-')
                            advance_empty.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            advance_empty.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 5, advance_empty)

                            balance_empty = QLabel('-')
                            balance_empty.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            balance_empty.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 6, balance_empty)
                        elif payment_type == 'Аванс':
                            # Аванс
                            amount_empty = QLabel('-')
                            amount_empty.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            amount_empty.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 4, amount_empty)

                            advance_label = QLabel(f"{final_amount:,.0f}".replace(',', ' '))
                            advance_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            advance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            payments_table.setCellWidget(row, 5, advance_label)

                            balance_empty2 = QLabel('-')
                            balance_empty2.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            balance_empty2.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 6, balance_empty2)
                        elif payment_type == 'Доплата':
                            # Доплата
                            amount_empty2 = QLabel('-')
                            amount_empty2.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            amount_empty2.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 4, amount_empty2)

                            advance_empty3 = QLabel('-')
                            advance_empty3.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            advance_empty3.setAlignment(Qt.AlignCenter)
                            payments_table.setCellWidget(row, 5, advance_empty3)

                            balance_label = QLabel(f"{final_amount:,.0f}".replace(',', ' '))
                            balance_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                            balance_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            payments_table.setCellWidget(row, 6, balance_label)

                        # Отчетный месяц
                        report_month = payment.get('report_month', '')
                        formatted_month = format_month_year(report_month) if report_month else '-'
                        month_label = QLabel(formatted_month)
                        month_label.setStyleSheet(f"background-color: {row_color.name()}; border-radius: 2px;")
                        month_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        payments_table.setCellWidget(row, 7, month_label)

                    # Настройка пропорционального изменения размера колонок
                    # Колонки: Должность, ФИО, Стадия, Тип выплаты, Выплата, Аванс, Доплата, Отчетный месяц
                    # Пропорции: 0.12, 0.17, 0.20, 0.12, 0.10, 0.10, 0.10, 0.09
                    payments_table.setup_proportional_resize(
                        column_ratios=[0.12, 0.17, 0.20, 0.12, 0.10, 0.10, 0.10, 0.09],
                        fixed_columns={},  # Все колонки пропорциональные
                        min_width=50
                    )

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
                        advance_label.setStyleSheet('font-weight: bold; color: #ffd93c; font-size: 11px;')
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
            project_data_header = QLabel('Данные по проекту')
            project_data_header.setStyleSheet('''
                font-size: 13px;
                font-weight: bold;
                color: #2C3E50;
                padding-bottom: 5px;
            ''')
            project_data_layout.addWidget(project_data_header)

            # Определяем права доступа
            from utils.permissions import _has_perm
            can_edit_project_data = _has_perm(self.employee, self.api_client, 'crm_cards.update')

            # Информационное сообщение о правах
            if not can_edit_project_data:
                info_label = QLabel('[INFO] Данные отображаются в режиме просмотра')
                info_label.setStyleSheet('''
                    color: #7F8C8D;
                    font-size: 11px;
                    font-style: italic;
                    padding: 5px;
                    background-color: #ECF0F1;
                    border-radius: 4px;
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

                conn = self.data.db.connect()
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
                        tz_file_label.setStyleSheet('color: #ffd93c; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 4px;')
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
                        survey_file_label.setStyleSheet('color: #ffd93c; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 4px;')
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
                        templates = self.data.get_project_templates(contract_id)
                        if templates:
                            for template in templates:
                                template_label = QLabel(f'<a href="{template["template_url"]}">{template["template_url"]}</a>')
                                template_label.setOpenExternalLinks(True)
                                template_label.setWordWrap(True)
                                template_label.setStyleSheet('color: #ffd93c; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 4px; margin-bottom: 4px;')
                                ref_layout.addWidget(template_label)
                        else:
                            ref_layout.addWidget(QLabel('Шаблоны не загружены'))
                    else:
                        # Показываем ссылку на папку референсов
                        if contract_data['references_yandex_path']:
                            ref_label = QLabel(f'<a href="{contract_data["references_yandex_path"]}">Открыть папку с референсами</a>')
                            ref_label.setOpenExternalLinks(True)
                            ref_label.setStyleSheet('color: #ffd93c; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 4px;')
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
                        photo_label.setStyleSheet('color: #ffd93c; font-size: 10px; padding: 5px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 4px;')
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
                            ('stage2_concept', '2 стадия - Концепция-коллажи'),
                            ('stage2_3d', '2 стадия - 3D визуализация'),
                            ('stage3', '3 стадия - Чертежный проект')
                        ]

                    # Для надзорных карточек добавляем стадию надзора
                    if self.card_type == 'supervision':
                        stages.append(('supervision', 'Авторский надзор'))

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
                            SELECT id, file_name, public_link, yandex_path
                            FROM project_files
                            WHERE contract_id = ? AND stage = ?
                            ORDER BY id ASC
                        ''', (contract_id, stage_key))

                        files = cursor.fetchall()

                        if files:
                            for file in files:
                                f_link = file['public_link'] if file['public_link'] else ''
                                f_yp = file['yandex_path'] if len(file) > 3 and file['yandex_path'] else ''
                                if f_link:
                                    file_label = QLabel(f'<a href="{f_link}">{file["file_name"]}</a>')
                                    file_label.setOpenExternalLinks(True)
                                else:
                                    file_label = QLabel(file['file_name'] or 'Без названия')
                                file_label.setStyleSheet('color: #ffd93c; font-size: 10px; padding: 4px; background-color: #F8F9FA; border: 1px solid #E0E0E0; border-radius: 4px; margin-bottom: 2px;')
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
            tabs.addTab(project_data_widget, 'Данные по проекту')

            layout.addWidget(tabs, 1)
            
            buttons_layout = QHBoxLayout()

            restore_perm = 'supervision.move' if self.card_type == 'supervision' else 'crm_cards.move'
            can_restore = _has_perm(self.employee, self.api_client, restore_perm)
            restore_btn = IconLoader.create_icon_button('refresh-black', 'Вернуть в активные проекты', icon_size=12)
            restore_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffd93c;
                    color: #333333;
                    padding: 0px 30px;
                    border-radius: 4px;
                    border: none;
                    font-weight: bold;
                    max-height: 36px;
                    min-height: 36px;
                }
                QPushButton:hover { background-color: #f0c929; }
                QPushButton:pressed { background-color: #e0b919; }
            """)
            restore_btn.setFixedHeight(36)
            restore_btn.clicked.connect(self.restore_to_active)
            restore_btn.setVisible(can_restore)
            buttons_layout.addWidget(restore_btn)

            self.sync_label = QLabel('Синхронизация...')
            self.sync_label.setStyleSheet('color: #999999; font-size: 11px;')
            self.sync_label.setVisible(False)
            buttons_layout.addWidget(self.sync_label)

            buttons_layout.addStretch()

            close_btn = QPushButton('Закрыть')
            close_btn.setStyleSheet("""
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
            close_btn.setFixedHeight(36)
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

        self.setMinimumWidth(700)
        self.setMinimumHeight(400)
        self.resize(target_width, target_height)

        # Включаем отслеживание мыши для resize-курсоров
        self.setMouseTracking(True)
        self.setAttribute(Qt.WA_Hover, True)
        # =======================================================  
            
    def _on_archive_history_filter(self, filter_text):
        """Фильтрация истории архивной карточки"""
        container = self._archive_history_container
        # Очищаем
        while container.count():
            child = container.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        # Маппинг фильтров на action_type
        filter_map = {
            'Перемещение карточки': ['card_moved'],
            'Пауза / возобновление': ['card_paused', 'card_resumed', 'pause', 'resume'],
            'Назначение исполнителей': ['executor_assigned', 'executor_deleted', 'executor_completed', 'assignment_change'],
            'Сдача / приёмка работы': ['work_submitted', 'work_accepted', 'work_rejected', 'acceptance', 'accepted'],
            'Стадии и согласование': ['stage_completed', 'stages_reset', 'approval_completed', 'approval_reset', 'designer_reset', 'draftsman_reset'],
            'Оплаты': ['payment_created', 'payment_updated'],
            'Изменение дедлайна': ['deadline_changed', 'executor_deadline_changed'],
            'Загрузка файлов': ['file_upload'],
            'Удаление файлов': ['file_delete'],
            'Замер': ['survey_complete', 'survey_date_changed'],
        }

        show_stages = filter_text in ('Все действия', 'Стадии исполнителей')
        show_actions = filter_text != 'Стадии исполнителей'
        has_content = False

        # ActionHistory
        if show_actions and self._archive_action_history:
            allowed = filter_map.get(filter_text)
            if filter_text == 'Прочее':
                all_known = set()
                for types in filter_map.values():
                    all_known.update(types)
                items = [a for a in self._archive_action_history
                         if a.get('action_type', a.get('entry_type', '')) not in all_known]
            elif allowed:
                items = [a for a in self._archive_action_history
                         if a.get('action_type', a.get('entry_type', '')) in allowed]
            else:
                items = self._archive_action_history

            for action in items:
                has_content = True
                date_str = action.get('action_date', action.get('created_at', ''))
                if isinstance(date_str, str) and 'T' in date_str:
                    date_str = date_str.split('T')[0]
                desc = action.get('description', action.get('message', ''))
                user = action.get('user_name', '')
                text = f"{format_date(date_str, date_str)}"
                if user:
                    text += f" | {user}"
                text += f": {desc}"

                lbl = QLabel(text)
                lbl.setWordWrap(True)
                lbl.setStyleSheet('color: #2C3E50; font-size: 10px; background-color: #EBF5FB; padding: 6px; border-radius: 4px;')
                container.addWidget(lbl)

        # Стадии исполнителей
        if show_stages and self._archive_stages:
            for stage in self._archive_stages:
                has_content = True
                stage_frame = QFrame()
                bg = '#D5F4E6' if stage.get('completed') else '#F8F9FA'
                stage_frame.setStyleSheet(f'QFrame {{ background-color: {bg}; border: none; border-radius: 4px; padding: 2px; margin: 2px 0px; }}')

                sl = QVBoxLayout()
                sl.setSpacing(3)
                sl.addWidget(QLabel(f"<b>{stage.get('stage_name', 'N/A')}</b>"))

                ex = QLabel(f"Исполнитель: {stage.get('executor_name', 'Не назначен')}")
                ex.setStyleSheet('font-size: 10px; color: #666;')
                sl.addWidget(ex)

                dp = [f"Назначено: {format_date(stage.get('assigned_date'), 'N/A')}", f"Дедлайн: {format_date(stage.get('deadline'), 'N/A')}"]
                if stage.get('submitted_date'):
                    dp.append(f"Сдано: {format_date(stage.get('submitted_date'), 'N/A')}")
                dl = QLabel(" | ".join(dp))
                dl.setStyleSheet('font-size: 10px; color: #666;')
                sl.addWidget(dl)

                if stage.get('completed'):
                    cl = QLabel(f"Принято: {format_date(stage.get('completed_date'), 'N/A')}")
                    cl.setStyleSheet('font-size: 10px; color: #27AE60; font-weight: bold;')
                    sl.addWidget(cl)

                stage_frame.setLayout(sl)
                container.addWidget(stage_frame)

        if not has_content:
            empty = QLabel('История отсутствует')
            empty.setStyleSheet('color: #999; font-style: italic;')
            container.addWidget(empty)

        container.addStretch()

    def _get_stage_columns(self):
        """Получить список рабочих стадий для выбора при возврате из архива."""
        if self.card_type == 'supervision':
            return [
                'Стадия 1: Закупка керамогранита',
                'Стадия 2: Закупка сантехники',
                'Стадия 3: Закупка оборудования',
                'Стадия 4: Закупка дверей и окон',
                'Стадия 5: Закупка настенных материалов',
                'Стадия 6: Закупка напольных материалов',
                'Стадия 7: Лепной декор',
                'Стадия 8: Освещение',
                'Стадия 9: Бытовая техника',
                'Стадия 10: Закупка заказной мебели',
                'Стадия 11: Закупка фабричной мебели',
                'Стадия 12: Закупка декора',
            ]
        project_type = self.card_data.get('project_type', 'Индивидуальный')
        if project_type == 'Индивидуальный':
            return [
                'Стадия 1: планировочные решения',
                'Стадия 2: концепция дизайна',
                'Стадия 3: рабочие чертежи',
            ]
        else:
            return [
                'Стадия 1: планировочные решения',
                'Стадия 2: рабочие чертежи',
                'Стадия 3: 3д визуализация (Дополнительная)',
            ]

    def restore_to_active(self):
        """Возврат проекта в активные — с выбором стадии"""
        stages = self._get_stage_columns()

        # Кастомный frameless диалог выбора стадии
        dialog = QDialog(self)
        dialog.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        dialog.setAttribute(Qt.WA_TranslucentBackground, True)
        dialog.setFixedSize(460, 260)

        # Корневой layout (прозрачный)
        root_layout = QVBoxLayout(dialog)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # Контейнер с рамкой
        border_frame = QFrame()
        border_frame.setObjectName("restoreBorderFrame")
        border_frame.setStyleSheet("""
            QFrame#restoreBorderFrame {
                background-color: #FFFFFF;
                border: 1px solid #E0E0E0;
                border-radius: 10px;
            }
        """)
        frame_layout = QVBoxLayout(border_frame)
        frame_layout.setContentsMargins(0, 0, 0, 0)
        frame_layout.setSpacing(0)

        # Кастомный title bar
        title_bar = CustomTitleBar(dialog, 'Возврат в активные', simple_mode=True)
        title_bar.setStyleSheet("""
            CustomTitleBar {
                background-color: #FFFFFF;
                border-bottom: 1px solid #E0E0E0;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
            }
        """)
        frame_layout.addWidget(title_bar)

        # Контент
        content = QWidget()
        content.setStyleSheet("QWidget { background-color: #FFFFFF; border-bottom-left-radius: 10px; border-bottom-right-radius: 10px; }")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(28, 20, 28, 28)

        desc = QLabel('Выберите стадию, в которую нужно вернуть проект.\nБудет сброшена выбранная стадия и все последующие.')
        desc.setWordWrap(True)
        desc.setStyleSheet('font-size: 12px; color: #757575;')
        content_layout.addWidget(desc)

        combo = QComboBox()
        combo.setStyleSheet("""
            QComboBox {
                font-size: 13px; padding: 6px 10px; border: 1px solid #d9d9d9;
                border-radius: 4px; background: #fff; min-height: 28px;
            }
            QComboBox:hover { border-color: #b0b0b0; }
            QComboBox::drop-down { border: none; width: 28px; }
            QComboBox QAbstractItemView {
                background-color: #fff; border: 1px solid #d9d9d9;
                selection-background-color: #ffd93c; selection-color: #333;
            }
        """)
        for stage in stages:
            combo.addItem(stage)
        content_layout.addWidget(combo)

        content_layout.addStretch()

        buttons_layout = QHBoxLayout()
        cancel_btn = QPushButton('Отмена')
        cancel_btn.setFixedHeight(36)
        cancel_btn.setMinimumWidth(100)
        cancel_btn.setCursor(Qt.PointingHandCursor)
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0; color: #333333; padding: 0px 20px;
                border-radius: 4px; border: none; font-weight: bold;
                max-height: 36px; min-height: 36px;
            }
            QPushButton:hover { background-color: #D0D0D0; }
            QPushButton:pressed { background-color: #C0C0C0; }
        """)
        cancel_btn.clicked.connect(dialog.reject)
        buttons_layout.addWidget(cancel_btn)

        buttons_layout.addStretch()

        ok_btn = QPushButton('Вернуть')
        ok_btn.setFixedHeight(36)
        ok_btn.setMinimumWidth(100)
        ok_btn.setCursor(Qt.PointingHandCursor)
        ok_btn.setStyleSheet("""
            QPushButton {
                background-color: #ffd93c; color: #333333; padding: 0px 30px;
                border-radius: 4px; border: none; font-weight: bold;
                max-height: 36px; min-height: 36px;
            }
            QPushButton:hover { background-color: #f0c929; }
            QPushButton:pressed { background-color: #e0b919; }
        """)
        ok_btn.clicked.connect(dialog.accept)
        buttons_layout.addWidget(ok_btn)

        content_layout.addLayout(buttons_layout)
        frame_layout.addWidget(content)
        root_layout.addWidget(border_frame)

        # Центрирование на родителе
        from utils.dialog_helpers import center_dialog_on_parent
        QTimer.singleShot(0, lambda: center_dialog_on_parent(dialog))

        if dialog.exec_() != QDialog.Accepted:
            return

        target_column = combo.currentText()

        try:
            contract_id = self.card_data.get('contract_id')
            card_id = self.card_data['id']
            is_supervision = self.card_type == 'supervision'

            # 1. Обновляем статус договора
            new_status = 'Авторский надзор' if is_supervision else 'В работе'
            self.data.update_contract(contract_id, {
                'status': new_status,
                'termination_reason': None
            })
            print(f"[API] Статус договора {contract_id} изменен на '{new_status}'")

            # 2. Перемещаем карточку в выбранную стадию
            if is_supervision:
                self.data.move_supervision_card(card_id, target_column)
                print(f"[API] Карточка надзора {card_id} перемещена в '{target_column}'")
            else:
                self.data.move_crm_card(card_id, target_column)
                print(f"[API] CRM карточка {card_id} перемещена в '{target_column}'")

            # 3. Каскадный сброс: выбранная стадия + все последующие
            selected_idx = stages.index(target_column)
            stages_to_reset = stages[selected_idx:]  # от выбранной до конца

            if is_supervision:
                # У надзора упрощённая модель — сбрасываем dan_completed
                self.data.reset_supervision_stage_completion(card_id)
                print(f"[API] Сброшен dan_completed для карточки надзора {card_id}")
            else:
                # Каскадный сброс: от выбранной стадии и далее
                self.data.reset_stage_by_name(card_id, stages_to_reset)
                print(f"[API] Каскадный сброс {len(stages_to_reset)} стадий для карточки {card_id}: {stages_to_reset}")

            self.accept()

            # 4. Обновляем родительский виджет (CRM или надзор)
            parent = self.parent()
            while parent:
                if is_supervision:
                    from ui.crm_supervision_tab import CRMSupervisionTab
                    if isinstance(parent, CRMSupervisionTab):
                        parent.refresh_current_tab()
                        break
                else:
                    from ui.crm_tab import CRMTab
                    if isinstance(parent, CRMTab):
                        parent.refresh_current_tab()
                        break
                parent = parent.parent()

        except Exception as e:
            print(f"Ошибка возврата проекта: {e}")
            import traceback
            traceback.print_exc()
            CustomMessageBox(self, 'Ошибка', f'Не удалось вернуть проект: {e}', 'error').exec_()
    
    def _show_sync_label(self):
        self._active_sync_count += 1
        if hasattr(self, 'sync_label'):
            self.sync_label.setVisible(True)

    def _on_sync_ended(self):
        self._active_sync_count = max(0, self._active_sync_count - 1)
        if self._active_sync_count == 0 and hasattr(self, 'sync_label'):
            self.sync_label.setVisible(False)

    def _run_file_sync(self):
        """Запуск фоновой синхронизации файлов с Яндекс.Диском"""
        if not self.data.is_online:
            return

        contract_id = self.card_data.get('contract_id')
        if not contract_id:
            return

        self._show_sync_label()

        # Таймаут: скрыть надпись через 30 секунд если sync зависнет
        QTimer.singleShot(30000, self._on_sync_ended)

        def sync_thread():
            try:
                # Сканируем файлы на Яндекс.Диске
                scan_result = self.data.scan_contract_files(contract_id)
                new_count = scan_result.get('new_files_added', 0)
                contract_updated = scan_result.get('contract_updated', False)

                if new_count > 0 or contract_updated:
                    print(f"[ARCHIVE-SYNC] Обнаружены изменения: {new_count} новых файлов, contract_updated={contract_updated}")

                    # Синхронизируем локальную БД
                    try:
                        from utils.db_sync import sync_all_data
                        sync_all_data(self.data.api_client, self.data.db)
                    except Exception as sync_e:
                        print(f"[ARCHIVE-SYNC] Ошибка синхронизации БД: {sync_e}")
            except Exception as e:
                print(f"[ARCHIVE-SYNC] Ошибка сканирования: {e}")
            finally:
                # ИСПРАВЛЕНИЕ R-03: emit через QTimer для thread-safety
                from PyQt5.QtCore import QTimer
                QTimer.singleShot(0, self._sync_ended.emit)

        import threading
        t = threading.Thread(target=sync_thread, daemon=True)
        t.start()

    # ========== RESIZE SUPPORT (аналогично CardEditDialog) ==========

    def get_resize_edge(self, pos):
        """Определение края/угла для изменения размера"""
        rect = self.rect()
        margin = self.resize_margin
        on_left = pos.x() <= margin
        on_right = pos.x() >= rect.width() - margin
        on_top = pos.y() <= margin
        on_bottom = pos.y() >= rect.height() - margin

        if on_top and on_left:
            return 'top-left'
        elif on_top and on_right:
            return 'top-right'
        elif on_bottom and on_left:
            return 'bottom-left'
        elif on_bottom and on_right:
            return 'bottom-right'
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
        if edge in ('top-left', 'bottom-right'):
            self.setCursor(Qt.SizeFDiagCursor)
        elif edge in ('top-right', 'bottom-left'):
            self.setCursor(Qt.SizeBDiagCursor)
        elif edge in ('left', 'right'):
            self.setCursor(Qt.SizeHorCursor)
        elif edge in ('top', 'bottom'):
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
                self.grabMouse()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Процесс изменения размера"""
        if self.resizing and self.resize_edge:
            delta = event.globalPos() - self.resize_start_pos
            old = self.resize_start_geometry
            x, y, w, h = old.x(), old.y(), old.width(), old.height()
            edge = self.resize_edge
            min_w, min_h = 700, 400

            if 'left' in edge:
                new_w = w - delta.x()
                if new_w >= min_w:
                    x = old.x() + delta.x()
                    w = new_w
            elif 'right' in edge:
                new_w = w + delta.x()
                if new_w >= min_w:
                    w = new_w

            if 'top' in edge:
                new_h = h - delta.y()
                if new_h >= min_h:
                    y = old.y() + delta.y()
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
            self.releaseMouse()
            self.resizing = False
            self.resize_edge = None
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def event(self, event):
        """Обработка hover для смены курсора на границах"""
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.HoverMove:
            if not self.resizing:
                edge = self.get_resize_edge(event.pos())
                self.set_cursor_shape(edge)
        elif event.type() == QEvent.HoverLeave:
            if not self.resizing:
                self.setCursor(Qt.ArrowCursor)
        return super().event(event)

    # ========== SHOW / CENTER ==========

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

