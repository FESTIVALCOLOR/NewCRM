# -*- coding: utf-8 -*-
"""Архивные классы CRM, выделенные из crm_tab.py"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                             QLabel, QScrollArea, QFrame, QDialog, QFormLayout,
                             QLineEdit, QComboBox, QDateEdit,
                             QGroupBox, QSpinBox, QTableWidget, QHeaderView,
                             QTableWidgetItem, QTabWidget, QTextEdit)
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
            details_parts.append(f"{self.card_data['area']} м²")
        if self.card_data.get('city'):
            details_parts.append(self.card_data['city'])

        if details_parts:
            # Создаем контейнер для иконок и текста
            details_container = QWidget()
            details_layout = QHBoxLayout()
            details_layout.setSpacing(4)
            details_layout.setContentsMargins(0, 0, 0, 0)
            details_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            if self.card_data.get('area'):
                # Иконка площади
                area_icon = IconLoader.create_icon_button('box', '', '', icon_size=11)
                area_icon.setFixedSize(11, 11)
                area_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
                area_icon.setEnabled(False)
                details_layout.addWidget(area_icon, 0, Qt.AlignVCenter)

                # Текст площади
                area_label = QLabel(f"{self.card_data['area']} м²")
                area_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                area_label.setAlignment(Qt.AlignVCenter)
                details_layout.addWidget(area_label, 0, Qt.AlignVCenter)

                if self.card_data.get('city'):
                    # Разделитель
                    sep_label = QLabel("|")
                    sep_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                    sep_label.setAlignment(Qt.AlignVCenter)
                    details_layout.addWidget(sep_label, 0, Qt.AlignVCenter)

            if self.card_data.get('city'):
                # Иконка города
                city_icon = IconLoader.create_icon_button('map-pin', '', '', icon_size=11)
                city_icon.setFixedSize(11, 11)
                city_icon.setStyleSheet('border: none; background: transparent; padding: 0;')
                city_icon.setEnabled(False)
                details_layout.addWidget(city_icon, 0, Qt.AlignVCenter)

                # Текст города
                city_label = QLabel(self.card_data['city'])
                city_label.setStyleSheet('color: #666; font-size: 11px; background-color: transparent;')
                city_label.setAlignment(Qt.AlignVCenter)
                details_layout.addWidget(city_label, 0, Qt.AlignVCenter)

            details_layout.addStretch()
            details_container.setLayout(details_layout)
            info_layout.addWidget(details_container)

        # ИСПРАВЛЕНИЕ: Тип агента отдельно с цветом
        if self.card_data.get('agent_type'):
            agent_type = self.card_data['agent_type']
            agent_color = self.data.get_agent_color(agent_type)

            agent_label = QLabel(agent_type)
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
            agent_label.setAlignment(Qt.AlignLeft)
            info_layout.addWidget(agent_label)
        
        if status:
            status_label = QLabel(f"Статус: {status}")
            if 'СДАН' in status:
                status_label.setStyleSheet('''
                    color: white;
                    background-color: #27AE60;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                ''')
            elif 'РАСТОРГНУТ' in status:
                status_label.setStyleSheet('''
                    color: white;
                    background-color: #E74C3C;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                ''')
            elif 'НАДЗОР' in status:
                status_label.setStyleSheet('''
                    color: white;
                    background-color: #2196F3;
                    padding: 3px 8px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                ''')
            info_layout.addWidget(status_label)

        layout.addLayout(info_layout)

        # Добавляем stretch, чтобы кнопки всегда были внизу
        layout.addStretch(1)

        # ========== КНОПКА "ПЕРЕВЕСТИ В АВТОРСКИЙ НАДЗОР" ==========
        # Показываем только для карточек, статус которых НЕ "АВТОРСКИЙ НАДЗОР"
        if 'АВТОРСКИЙ НАДЗОР' not in status and 'НАДЗОР' not in status:
            supervision_btn = IconLoader.create_icon_button(
                'shield', 'В авторский надзор', 'Перевести в авторский надзор', icon_size=12)
            supervision_btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    padding: 4px 20px;
                    border-radius: 4px;
                    font-size: 10px;
                    font-weight: bold;
                    max-height: 19px;
                    min-height: 19px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #1565C0;
                }
            """)
            supervision_btn.clicked.connect(self._transfer_to_supervision)
            layout.addWidget(supervision_btn, 0, Qt.AlignCenter)

        # ========== КНОПКА ПОДРОБНЕЕ (SVG) ==========
        details_btn = IconLoader.create_icon_button('info', 'Подробнее', 'Просмотр деталей', icon_size=12)
        details_btn.setStyleSheet("""
            QPushButton {
                background-color: #E0E0E0;
                color: #333333;
                border: none;
                padding: 4px 100px;
                border-radius: 4px;
                font-size: 11px;
                font-weight: bold;
                max-height: 19px;
                min-height: 19px;
            }
            QPushButton:hover {
                background-color: #D0D0D0;
            }
            QPushButton:pressed {
                background-color: #C0C0C0;
            }
        """)
        details_btn.clicked.connect(self.show_details)
        layout.addWidget(details_btn, 0, Qt.AlignCenter)

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
                    border: none;
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
                deadline_label = QLabel(f"<b>Общий дедлайн:</b> {self.card_data['deadline']}")
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

            # Для надзорных карточек используем supervision_history
            if self.card_type == 'supervision':
                supervision_history = self.data.get_supervision_history(self.card_data.get('id')) or []
                if supervision_history:
                    for entry in supervision_history:
                        entry_type = entry.get('entry_type', '')
                        message = entry.get('message', '')
                        created_at = entry.get('created_at', '')
                        if isinstance(created_at, str) and 'T' in created_at:
                            created_at = created_at.split('T')[0]
                        type_colors = {
                            'card_moved': '#1565C0', 'assignment_change': '#E65100',
                            'stage_completed': '#2E7D32', 'pause': '#F57F17',
                            'resume': '#388E3C', 'data_change': '#6A1B9A',
                            'file_upload': '#00695C', 'row_added': '#283593',
                            'row_deleted': '#B71C1C',
                        }
                        color = type_colors.get(entry_type, '#616161')
                        entry_label = QLabel(f"<span style='color: {color}; font-weight: bold;'>{created_at}</span> — {message}")
                        entry_label.setWordWrap(True)
                        entry_label.setStyleSheet('font-size: 10px; padding: 2px 0;')
                        info_layout.addRow(entry_label)
                else:
                    empty = QLabel('История отсутствует')
                    empty.setStyleSheet('color: #999; font-style: italic;')
                    info_layout.addRow(empty)
            else:
                stages = self.data.get_stage_history(self.card_data.get('id'))

                if stages:
                    completed_stages = []
                    active_stages = []

                    for stage in stages:
                        if stage.get('completed'):
                            completed_stages.append(stage)
                        else:
                            active_stages.append(stage)

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

                        dates_parts = [f"Назначено: {format_date(stage.get('assigned_date'), 'N/A')}", f"Дедлайн: {format_date(stage.get('deadline'), 'N/A')}"]
                        if stage.get('submitted_date'):
                            dates_parts.append(f"Сдано: {format_date(stage.get('submitted_date'), 'N/A')}")

                        dates = QLabel(" | ".join(dates_parts))
                        dates.setStyleSheet('font-size: 10px; color: #666;')
                        stage_layout.addWidget(dates)

                        if stage.get('completed'):
                            completed_label = QLabel(f"Принято: {format_date(stage.get('completed_date'), 'N/A')}")
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
            
            restore_btn = IconLoader.create_icon_button('refresh3', 'Вернуть в активные проекты', icon_size=12)
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
                card_id = self.card_data['id']

                # ИСПРАВЛЕНИЕ: Синхронизация с API
                if self.data.is_online:
                    try:
                        # 1. Обновляем статус договора через API
                        self.data.update_contract(contract_id, {
                            'status': 'В работе',
                            'termination_reason': None
                        })
                        print(f"[API] Статус договора {contract_id} изменен на 'В работе'")

                        # 2. Перемещаем CRM карточку через API
                        self.data.move_crm_card(card_id, 'Выполненный проект')
                        print(f"[API] CRM карточка {card_id} перемещена в 'Выполненный проект'")

                    except Exception as api_e:
                        print(f"[WARN] Ошибка API при возврате проекта: {api_e}, fallback на локальную БД")
                        self.data.update_contract(contract_id, {
                            'status': 'В работе',
                            'termination_reason': None
                        })
                        self.data.update_crm_card_column(card_id, 'Выполненный проект')
                else:
                    # Offline режим - только локальная БД
                    self.data.update_contract(contract_id, {
                        'status': 'В работе',
                        'termination_reason': None
                    })
                    self.data.update_crm_card_column(card_id, 'Выполненный проект')

                # ИСПРАВЛЕНИЕ 06.02.2026: Убран диалог "Успех"
                self.accept()

                parent = self.parent()
                while parent:
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

