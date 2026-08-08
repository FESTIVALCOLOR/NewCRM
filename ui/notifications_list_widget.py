# -*- coding: utf-8 -*-
"""
Виджет списка уведомлений.
Отображает уведомления с фильтрацией по типу и статусу прочтения.
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTableWidget,
    QTableWidgetItem, QPushButton, QComboBox, QLabel,
    QHeaderView, QAbstractItemView,
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor
import logging

logger = logging.getLogger(__name__)


class NotificationsListWidget(QWidget):
    """Виджет списка уведомлений"""

    # Соответствие индекса фильтра типу уведомления
    _TYPE_MAP = {
        1: 'assigned',
        2: 'crm_stage_change',
        3: 'deadline',
        4: 'payment',
        5: 'supervision',
    }

    _TYPE_LABELS = {
        'assigned': 'Назначение',
        'crm_stage_change': 'Стадия',
        'deadline': 'Дедлайн',
        'payment': 'Оплата',
        'supervision': 'Надзор',
    }

    def __init__(self, data_access, parent=None):
        super().__init__(parent)
        self.data = data_access
        self._all_notifications = []
        self._setup_ui()
        QTimer.singleShot(100, self.load_notifications)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Фильтры
        filter_layout = QHBoxLayout()

        self.read_filter = QComboBox()
        self.read_filter.addItems(['Все', 'Непрочитанные'])
        self.read_filter.currentIndexChanged.connect(self.apply_filters)
        self.read_filter.setFixedHeight(28)
        self.read_filter.setStyleSheet(
            'font-size: 12px; border: 1px solid #d9d9d9; border-radius: 4px; padding: 0px 8px;'
        )
        filter_layout.addWidget(self.read_filter)

        self.type_filter = QComboBox()
        self.type_filter.addItems([
            'Все типы', 'Назначения', 'Стадии', 'Дедлайны', 'Оплаты', 'Надзор',
        ])
        self.type_filter.currentIndexChanged.connect(self.apply_filters)
        self.type_filter.setFixedHeight(28)
        self.type_filter.setStyleSheet(
            'font-size: 12px; border: 1px solid #d9d9d9; border-radius: 4px; padding: 0px 8px;'
        )
        filter_layout.addWidget(self.type_filter)

        filter_layout.addStretch()

        self.mark_all_btn = QPushButton('Прочитать все')
        self.mark_all_btn.setFixedHeight(28)
        self.mark_all_btn.setStyleSheet(
            'max-height: 26px; padding: 0px 14px; font-size: 12px;'
            ' border: 1px solid #d9d9d9; border-radius: 4px; background: #f5f5f5;'
        )
        self.mark_all_btn.clicked.connect(self.mark_all_read)
        filter_layout.addWidget(self.mark_all_btn)

        self.refresh_btn = QPushButton('Обновить')
        self.refresh_btn.setFixedHeight(28)
        self.refresh_btn.setStyleSheet(
            'max-height: 26px; padding: 0px 14px; font-size: 12px;'
            ' border: 1px solid #d9d9d9; border-radius: 4px; background: #f5f5f5;'
        )
        self.refresh_btn.clicked.connect(self.load_notifications)
        filter_layout.addWidget(self.refresh_btn)

        layout.addLayout(filter_layout)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            'Тип', 'Заголовок', 'Сообщение', 'Дата', 'Статус',
        ])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setDefaultSectionSize(120)
        self.table.setColumnWidth(0, 100)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(3, 130)
        self.table.setColumnWidth(4, 80)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet('''
            QTableWidget {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                font-size: 12px;
            }
            QTableWidget::item {
                padding: 4px 8px;
            }
            QHeaderView::section {
                background: #F5F5F5;
                border: none;
                border-bottom: 1px solid #E0E0E0;
                padding: 6px;
                font-size: 12px;
                font-weight: bold;
            }
        ''')
        self.table.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.table)

        # Счётчик
        self.count_label = QLabel('')
        self.count_label.setStyleSheet('font-size: 11px; color: #888;')
        layout.addWidget(self.count_label)

    def load_notifications(self):
        """Загрузить уведомления через DataAccess"""
        try:
            result = self.data.get_notifications()
            if result and isinstance(result, list):
                self._all_notifications = result
            else:
                self._all_notifications = []
        except Exception as e:
            logger.error(f'Ошибка загрузки уведомлений: {e}')
            self._all_notifications = []
        self.apply_filters()

    def apply_filters(self):
        """Применить фильтры и обновить таблицу"""
        items = list(self._all_notifications)

        # Фильтр по прочитанности
        if self.read_filter.currentIndex() == 1:  # Непрочитанные
            items = [n for n in items if not n.get('is_read')]

        # Фильтр по типу
        type_idx = self.type_filter.currentIndex()
        if type_idx > 0:
            target_type = self._TYPE_MAP.get(type_idx, '')
            items = [n for n in items if n.get('notification_type') == target_type]

        self._display_items(items)

    def _display_items(self, items):
        """Отобразить список в таблице"""
        self.table.setRowCount(len(items))

        for row, n in enumerate(items):
            is_read = n.get('is_read', False)
            bg_color = QColor('#FFFFFF') if is_read else QColor('#FFF8E1')

            # Тип
            type_text = self._TYPE_LABELS.get(
                n.get('notification_type', ''), n.get('notification_type', ''),
            )
            type_item = QTableWidgetItem(type_text)
            type_item.setBackground(bg_color)
            type_item.setData(Qt.UserRole, n)
            self.table.setItem(row, 0, type_item)

            # Заголовок
            title_item = QTableWidgetItem(n.get('title', ''))
            title_item.setBackground(bg_color)
            self.table.setItem(row, 1, title_item)

            # Сообщение
            msg_item = QTableWidgetItem(n.get('message', ''))
            msg_item.setBackground(bg_color)
            self.table.setItem(row, 2, msg_item)

            # Дата
            created = n.get('created_at', '')
            if created:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(created.replace('Z', '+00:00'))
                    created = dt.strftime('%d.%m.%Y %H:%M')
                except Exception:
                    pass
            date_item = QTableWidgetItem(created)
            date_item.setBackground(bg_color)
            self.table.setItem(row, 3, date_item)

            # Статус
            status_text = 'Прочитано' if is_read else 'Новое'
            status_item = QTableWidgetItem(status_text)
            status_item.setBackground(bg_color)
            if not is_read:
                status_item.setForeground(QColor('#E67E22'))
            self.table.setItem(row, 4, status_item)

        unread = sum(1 for n in self._all_notifications if not n.get('is_read'))
        self.count_label.setText(
            f'Показано: {len(items)} из {len(self._all_notifications)} | Непрочитанных: {unread}'
        )

    def mark_all_read(self):
        """Отметить все как прочитанные"""
        try:
            self.data.mark_all_notifications_read()
            for n in self._all_notifications:
                n['is_read'] = True
            self.apply_filters()
        except Exception as e:
            logger.error(f'Ошибка mark_all_read: {e}')

    def _on_double_click(self, index):
        """Двойной клик — отметить уведомление как прочитанное"""
        row = index.row()
        item = self.table.item(row, 0)
        if not item:
            return
        n = item.data(Qt.UserRole)
        if n and not n.get('is_read'):
            try:
                nid = n.get('id')
                if nid:
                    self.data.mark_notification_read(nid)
                    n['is_read'] = True
                    self.apply_filters()
            except Exception as e:
                logger.error(f'Ошибка mark_read: {e}')
