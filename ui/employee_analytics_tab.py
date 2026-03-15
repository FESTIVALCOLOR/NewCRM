# -*- coding: utf-8 -*-
"""
Вкладка «Аналитика сотрудников» — KPI, сравнение, детальная карточка.

Структура:
  - Верхняя панель: фильтры (тип проекта, период) + обзор KPI
  - Средняя часть: вкладки по ролям (Ст.менеджеры, СДП, ГАП, ...)
  - Нижняя часть: детальная карточка выбранного сотрудника
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QComboBox, QTabWidget, QTableWidget,
    QTableWidgetItem, QHeaderView, QSpinBox, QScrollArea,
    QFrame, QSplitter, QSizePolicy, QGridLayout,
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QFont, QColor

from ui.custom_combobox import CustomComboBox
from database.db_manager import DatabaseManager
from utils.data_access import DataAccess
from utils.icon_loader import IconLoader
from utils.calendar_helpers import ICONS_PATH
from utils.table_settings import apply_no_focus_delegate

import logging

logger = logging.getLogger(__name__)


# ── Стили ────────────────────────────────────────────────────────────

CARD_STYLE = """
    QFrame {{
        background-color: {bg};
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 12px;
    }}
"""

KPI_GOOD = '#27AE60'
KPI_MEDIUM = '#F39C12'
KPI_BAD = '#E74C3C'

TABLE_STYLE = """
    QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #d9d9d9;
        border-radius: 8px;
        gridline-color: #f0f0f0;
    }
    QTableCornerButton::section {
        background-color: #fafafa;
        border: none;
        border-bottom: 1px solid #e6e6e6;
        border-right: 1px solid #f0f0f0;
        border-top-left-radius: 8px;
    }
    QHeaderView::section {
        background-color: #fafafa;
        border: none;
        border-bottom: 1px solid #e6e6e6;
        border-right: 1px solid #f0f0f0;
        padding: 6px 8px;
        font-weight: bold;
        color: #333;
    }
"""

ROLE_TABS = {
    'individual': [
        ('senior_manager', 'Старшие менеджеры'),
        ('sdp', 'СДП'),
        ('gap', 'ГАП'),
        ('draftsman', 'Чертёжники'),
        ('designer', 'Дизайнеры'),
        ('measurer', 'Замерщики'),
    ],
    'template': [
        ('senior_manager', 'Старшие менеджеры'),
        ('manager', 'Менеджеры'),
        ('gap', 'ГАП'),
        ('draftsman', 'Чертёжники'),
        ('designer', 'Дизайнеры'),
    ],
    'supervision': [
        ('senior_manager', 'Старшие менеджеры'),
        ('dan', 'ДАН'),
    ],
}

PROJECT_TYPE_MAP = {
    'Индивидуальные': 'individual',
    'Шаблонные': 'template',
    'Авторский надзор': 'supervision',
}


class EmployeeAnalyticsTab(QWidget):
    """Вкладка аналитики сотрудников."""

    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client
        self.db = DatabaseManager()
        self.data_access = DataAccess(api_client=self.api_client, db=self.db)
        self._loading = False
        self._current_dashboard = {}
        self._current_role_data = {}
        self._data_loaded = False
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # ── Заголовок + фильтры ──────────────────────────────────────
        header_row = QHBoxLayout()

        title = QLabel(' Аналитика сотрудников')
        title.setStyleSheet('font-size: 15px; font-weight: bold; color: #333;')
        header_row.addWidget(title)
        header_row.addStretch()

        # Тип проекта
        header_row.addWidget(QLabel('Тип проекта:'))
        self.project_type_combo = CustomComboBox()
        self.project_type_combo.addItems(['Индивидуальные', 'Шаблонные', 'Авторский надзор'])
        self.project_type_combo.currentTextChanged.connect(self._on_project_type_changed)
        header_row.addWidget(self.project_type_combo)

        # Период
        header_row.addWidget(QLabel('Год:'))
        self.year_spin = QSpinBox()
        self.year_spin.setRange(2020, 2030)
        self.year_spin.setValue(QDate.currentDate().year())
        self.year_spin.setStyleSheet(f"""
            QSpinBox {{
                background: #fff; border: none; border-radius: 4px;
                padding: 4px 8px; color: #333; font-size: 12px;
            }}
            QSpinBox::up-button, QSpinBox::down-button {{
                background: #F8F9FA; border: none; width: 20px; border-radius: 4px;
            }}
            QSpinBox::up-arrow {{ image: url({ICONS_PATH}/arrow-up-circle.svg); width: 14px; height: 14px; }}
            QSpinBox::down-arrow {{ image: url({ICONS_PATH}/arrow-down-circle.svg); width: 14px; height: 14px; }}
        """)
        header_row.addWidget(self.year_spin)

        header_row.addWidget(QLabel('Квартал:'))
        self.quarter_combo = CustomComboBox()
        self.quarter_combo.addItems(['Все', 'Q1', 'Q2', 'Q3', 'Q4'])
        header_row.addWidget(self.quarter_combo)

        header_row.addWidget(QLabel('Месяц:'))
        self.month_combo = CustomComboBox()
        months = ['Все', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        self.month_combo.addItems(months)
        header_row.addWidget(self.month_combo)

        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить', icon_size=12)
        refresh_btn.clicked.connect(self._load_all_data)
        header_row.addWidget(refresh_btn)

        main_layout.addLayout(header_row)

        # ── Сплиттер: верх (дашборд + роли) / низ (детальная карточка) ──
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(4)

        # ── Верхняя часть: KPI обзор + вкладки ролей ──
        top_widget = QWidget()
        top_layout = QVBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(6)

        # KPI-карточки обзора
        self.kpi_cards_layout = QHBoxLayout()
        self.kpi_cards_layout.setSpacing(8)
        self._kpi_card_widgets = []
        for _ in range(4):
            card = self._create_kpi_card('—', '—', '#FAFAFA')
            self.kpi_cards_layout.addWidget(card)
            self._kpi_card_widgets.append(card)
        top_layout.addLayout(self.kpi_cards_layout)

        # Вкладки ролей
        self.role_tabs = QTabWidget()
        self.role_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E0E0E0; border-radius: 4px; }
            QTabBar::tab {
                padding: 6px 16px; margin-right: 2px;
                border: 1px solid #E0E0E0; border-bottom: none;
                border-radius: 4px 4px 0 0; background: #FAFAFA;
            }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; }
        """)
        self.role_tabs.currentChanged.connect(self._on_role_tab_changed)
        top_layout.addWidget(self.role_tabs)

        splitter.addWidget(top_widget)

        # ── Нижняя часть: детальная карточка сотрудника ──
        self.detail_widget = QWidget()
        detail_layout = QVBoxLayout(self.detail_widget)
        detail_layout.setContentsMargins(0, 4, 0, 0)

        detail_header = QLabel('Детальная карточка сотрудника')
        detail_header.setStyleSheet('font-size: 13px; font-weight: bold; color: #555; padding: 4px;')
        detail_layout.addWidget(detail_header)

        self.detail_info_label = QLabel('Выберите сотрудника из таблицы выше')
        self.detail_info_label.setStyleSheet('color: #999; padding: 8px;')
        detail_layout.addWidget(self.detail_info_label)

        # Контейнер для детальных данных
        self.detail_content = QWidget()
        self.detail_content_layout = QVBoxLayout(self.detail_content)
        self.detail_content_layout.setContentsMargins(0, 0, 0, 0)
        self.detail_content.hide()
        detail_layout.addWidget(self.detail_content)

        detail_layout.addStretch()
        splitter.addWidget(self.detail_widget)

        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        main_layout.addWidget(splitter)
        self.setLayout(main_layout)

    # ── Ленивая загрузка данных ──────────────────────────────────────

    def ensure_data_loaded(self):
        """Вызывается при первом показе вкладки."""
        if not self._data_loaded:
            self._data_loaded = True
            QTimer.singleShot(100, self._load_all_data)

    # ── Обработчики фильтров ─────────────────────────────────────────

    def _on_project_type_changed(self, text):
        self._rebuild_role_tabs()
        self._load_all_data()

    def _on_role_tab_changed(self, index):
        if index >= 0 and self.role_tabs.count() > 0:
            role_code = self.role_tabs.widget(index).property('role_code')
            if role_code:
                self._load_role_data(role_code)

    def _get_project_type(self) -> str:
        return PROJECT_TYPE_MAP.get(self.project_type_combo.currentText(), 'individual')

    def _get_period_params(self) -> dict:
        params = {'year': self.year_spin.value()}
        q_text = self.quarter_combo.currentText()
        if q_text != 'Все' and len(q_text) > 1 and q_text[1].isdigit():
            params['quarter'] = int(q_text[1])
        m_idx = self.month_combo.currentIndex()
        if m_idx > 0:
            params['month'] = m_idx
        return params

    # ── Построение вкладок ролей ─────────────────────────────────────

    def _rebuild_role_tabs(self):
        self.role_tabs.blockSignals(True)
        self.role_tabs.clear()

        pt = self._get_project_type()
        roles = ROLE_TABS.get(pt, [])

        for role_code, role_label in roles:
            tab = QWidget()
            tab.setProperty('role_code', role_code)
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(4, 4, 4, 4)

            # Таблица сравнения сотрудников
            table = QTableWidget()
            table.setObjectName(f'role_table_{role_code}')
            table.setStyleSheet(TABLE_STYLE)
            apply_no_focus_delegate(table)
            table.setColumnCount(7)
            table.setHorizontalHeaderLabels([
                'Сотрудник', 'KPI', 'Kсрок', 'Kкач', 'Kскор', 'NPS', 'Проектов'
            ])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, 7):
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            table.verticalHeader().setDefaultSectionSize(32)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.cellClicked.connect(self._on_employee_clicked)

            tab_layout.addWidget(table)
            self.role_tabs.addTab(tab, role_label)

        self.role_tabs.blockSignals(False)

    # ── Загрузка данных ──────────────────────────────────────────────

    def _load_all_data(self):
        """Загрузка дашборда + текущей роли."""
        if self._loading:
            return
        self._loading = True

        try:
            pt = self._get_project_type()
            period = self._get_period_params()

            # Дашборд
            try:
                self._current_dashboard = self.data_access.get_analytics_dashboard(
                    pt, **period
                )
            except Exception as e:
                logger.warning(f"Ошибка загрузки дашборда: {e}")
                self._current_dashboard = {}

            self._update_kpi_cards()

            # Перестраиваем вкладки если ещё не построены
            if self.role_tabs.count() == 0:
                self._rebuild_role_tabs()

            # Загружаем данные текущей роли
            if self.role_tabs.count() > 0:
                current = self.role_tabs.currentWidget()
                if current:
                    role_code = current.property('role_code')
                    if role_code:
                        self._load_role_data(role_code)

        except Exception as e:
            logger.error(f"Ошибка загрузки аналитики: {e}", exc_info=True)
        finally:
            self._loading = False

    def _load_role_data(self, role_code: str):
        """Загрузка данных сравнения по роли."""
        pt = self._get_project_type()
        period = self._get_period_params()

        try:
            self._current_role_data = self.data_access.get_analytics_by_role(
                role_code, pt, **period
            )
        except Exception as e:
            logger.warning(f"Ошибка загрузки роли {role_code}: {e}")
            self._current_role_data = {}

        self._update_role_table(role_code)

    def _load_employee_detail(self, employee_id: int):
        """Загрузка детальной карточки сотрудника."""
        pt = self._get_project_type()
        period = self._get_period_params()

        try:
            detail = self.data_access.get_analytics_employee_detail(
                employee_id, pt, **period
            )
        except Exception as e:
            logger.warning(f"Ошибка загрузки деталей сотрудника {employee_id}: {e}")
            detail = {}

        self._update_detail_card(detail)

    # ── Обновление UI ────────────────────────────────────────────────

    def _update_kpi_cards(self):
        """Обновляет KPI-карточки обзора."""
        data = self._current_dashboard
        if not data:
            return

        cards_data = [
            ('Средний KPI', f"{data.get('avg_kpi', 0):.0f}%",
             self._kpi_color(data.get('avg_kpi', 0))),
            ('Сотрудников', str(data.get('total_employees', 0)), '#F0F4FF'),
            ('Лучший', self._top_name(data.get('top_performers', [])), '#F0FFF0'),
            ('Требует внимания', self._top_name(data.get('underperformers', [])), '#FFF5F5'),
        ]

        for i, (label, value, bg) in enumerate(cards_data):
            if i < len(self._kpi_card_widgets):
                self._update_kpi_card(self._kpi_card_widgets[i], label, value, bg)

    def _update_role_table(self, role_code: str):
        """Обновляет таблицу сравнения по роли."""
        data = self._current_role_data
        employees = data.get('employees', [])

        table = self.role_tabs.currentWidget().findChild(
            QTableWidget, f'role_table_{role_code}'
        )
        if not table:
            return

        table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            kpi_data = emp.get('kpi', {})
            kpi_total = kpi_data.get('kpi_total', 0)

            # Имя
            name_item = QTableWidgetItem(emp.get('name', ''))
            name_item.setData(Qt.UserRole, emp.get('id'))
            table.setItem(row, 0, name_item)

            # KPI (цветной)
            kpi_item = QTableWidgetItem(f"{kpi_total:.0f}%")
            kpi_item.setTextAlignment(Qt.AlignCenter)
            kpi_item.setForeground(QColor(self._kpi_color(kpi_total)))
            font = kpi_item.font()
            font.setBold(True)
            kpi_item.setFont(font)
            table.setItem(row, 1, kpi_item)

            # Компоненты KPI
            for col, key in enumerate(['k_deadline', 'k_quality', 'k_speed', 'k_nps'], start=2):
                val = kpi_data.get(key)
                text = f"{val:.0f}%" if val is not None else '—'
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col, item)

            # Проектов
            projects_item = QTableWidgetItem(str(emp.get('active_projects', 0)))
            projects_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 6, projects_item)

    def _update_detail_card(self, detail: dict):
        """Обновляет детальную карточку сотрудника."""
        if not detail or not detail.get('employee'):
            self.detail_info_label.setText('Нет данных по сотруднику')
            self.detail_info_label.show()
            self.detail_content.hide()
            return

        self.detail_info_label.hide()
        self.detail_content.show()

        # Очищаем предыдущий контент
        layout = self.detail_content_layout
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        emp = detail['employee']
        kpi = detail.get('kpi', {})
        projects = detail.get('projects', [])
        reviews = detail.get('reviews', [])
        trend = detail.get('kpi_trend', [])

        # Верхняя строка: имя + KPI
        info_row = QHBoxLayout()
        name_label = QLabel(f"<b>{emp.get('name', '')}</b> — {emp.get('position', '')}")
        name_label.setStyleSheet('font-size: 14px; color: #333;')
        info_row.addWidget(name_label)
        info_row.addStretch()

        kpi_total = kpi.get('kpi_total', 0)
        kpi_label = QLabel(f"KPI: <b>{kpi_total:.0f}%</b>")
        kpi_label.setStyleSheet(f'font-size: 16px; color: {self._kpi_color(kpi_total)};')
        info_row.addWidget(kpi_label)

        info_widget = QWidget()
        info_widget.setLayout(info_row)
        layout.addWidget(info_widget)

        # KPI-компоненты
        kpi_grid = QGridLayout()
        components = [
            ('Kсрок', kpi.get('k_deadline')),
            ('Kкачество', kpi.get('k_quality')),
            ('Kскорость', kpi.get('k_speed')),
            ('K NPS', kpi.get('k_nps')),
        ]
        for col, (label, val) in enumerate(components):
            text = f"{val:.0f}%" if val is not None else '—'
            w = self._create_mini_kpi_card(label, text)
            kpi_grid.addWidget(w, 0, col)

        # Доп. метрики
        extra = [
            ('Проектов', str(detail.get('active_projects', 0))),
            ('Средний NPS', f"{detail.get('avg_nps', 0):.1f}" if detail.get('avg_nps') else '—'),
            ('Ревизий', str(kpi.get('revision_count', 0))),
        ]
        for col, (label, val) in enumerate(extra):
            w = self._create_mini_kpi_card(label, val)
            kpi_grid.addWidget(w, 1, col)

        kpi_widget = QWidget()
        kpi_widget.setLayout(kpi_grid)
        layout.addWidget(kpi_widget)

        # Активные проекты
        if projects:
            projects_group = QGroupBox(f'Активные проекты ({len(projects)})')
            projects_layout = QVBoxLayout()

            projects_table = QTableWidget()
            apply_no_focus_delegate(projects_table)
            projects_table.setStyleSheet(TABLE_STYLE)
            projects_table.setColumnCount(3)
            projects_table.setHorizontalHeaderLabels(['Договор', 'Адрес', 'Статус'])
            projects_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            projects_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            projects_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            projects_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            projects_table.verticalHeader().setDefaultSectionSize(28)
            projects_table.setRowCount(len(projects))
            projects_table.setMaximumHeight(min(200, 32 + len(projects) * 28))

            for row, proj in enumerate(projects):
                projects_table.setItem(row, 0, QTableWidgetItem(
                    str(proj.get('contract_number', ''))))
                projects_table.setItem(row, 1, QTableWidgetItem(
                    proj.get('address', '')))
                projects_table.setItem(row, 2, QTableWidgetItem(
                    proj.get('status', '')))

            projects_layout.addWidget(projects_table)
            projects_group.setLayout(projects_layout)
            layout.addWidget(projects_group)

        # Отзывы клиентов
        if reviews:
            reviews_group = QGroupBox(f'Отзывы клиентов ({len(reviews)})')
            reviews_layout = QVBoxLayout()

            for review in reviews[:5]:
                r_label = QLabel(
                    f"NPS: <b>{review.get('nps_score', '—')}</b> | "
                    f"CSAT: <b>{review.get('csat_score', '—')}</b> | "
                    f"Договор: {review.get('contract_number', '?')} | "
                    f"<i>{review.get('comment', '')[:100]}</i>"
                )
                r_label.setStyleSheet('color: #555; padding: 2px 0;')
                r_label.setWordWrap(True)
                reviews_layout.addWidget(r_label)

            reviews_group.setLayout(reviews_layout)
            layout.addWidget(reviews_group)

        # Тренд KPI
        if trend:
            trend_group = QGroupBox('Тренд KPI (последние месяцы)')
            trend_layout = QHBoxLayout()

            for t in trend[-6:]:
                month_label = QLabel(
                    f"<b>{t.get('month', '')}</b><br>"
                    f"{t.get('kpi_total', 0):.0f}%"
                )
                month_label.setAlignment(Qt.AlignCenter)
                kpi_val = t.get('kpi_total', 0)
                month_label.setStyleSheet(
                    f'color: {self._kpi_color(kpi_val)}; '
                    f'padding: 4px 8px; background: #FAFAFA; '
                    f'border-radius: 4px; border: 1px solid #EEE;'
                )
                trend_layout.addWidget(month_label)

            trend_group.setLayout(trend_layout)
            layout.addWidget(trend_group)

    # ── Обработчик кликов по таблице ─────────────────────────────────

    def _on_employee_clicked(self, row, col):
        """Клик по строке в таблице сравнения → загрузить детальную карточку."""
        table = self.sender()
        if not table:
            return
        name_item = table.item(row, 0)
        if not name_item:
            return
        employee_id = name_item.data(Qt.UserRole)
        if employee_id:
            self._load_employee_detail(int(employee_id))

    # ── Вспомогательные методы ───────────────────────────────────────

    @staticmethod
    def _kpi_color(value) -> str:
        if value is None:
            return '#999'
        if value >= 80:
            return KPI_GOOD
        if value >= 50:
            return KPI_MEDIUM
        return KPI_BAD

    @staticmethod
    def _top_name(performers: list) -> str:
        if not performers:
            return '—'
        return performers[0].get('name', '—')

    @staticmethod
    def _create_kpi_card(label: str, value: str, bg: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet(CARD_STYLE.format(bg=bg))
        card.setFixedHeight(72)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)

        lbl = QLabel(label)
        lbl.setStyleSheet('font-size: 11px; color: #888; border: none;')
        lbl.setAlignment(Qt.AlignLeft)
        layout.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet('font-size: 18px; font-weight: bold; color: #333; border: none;')
        val.setAlignment(Qt.AlignLeft)
        layout.addWidget(val)

        return card

    @staticmethod
    def _update_kpi_card(card: QFrame, label: str, value: str, bg: str):
        card.setStyleSheet(CARD_STYLE.format(bg=bg))
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            labels[0].setText(label)
            labels[1].setText(value)

    @staticmethod
    def _create_mini_kpi_card(label: str, value: str) -> QFrame:
        card = QFrame()
        card.setStyleSheet("""
            QFrame {
                background: #F8F9FA; border: 1px solid #EEE;
                border-radius: 6px; padding: 6px;
            }
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(0)

        lbl = QLabel(label)
        lbl.setStyleSheet('font-size: 10px; color: #888; border: none;')
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        val = QLabel(value)
        val.setStyleSheet('font-size: 14px; font-weight: bold; color: #333; border: none;')
        val.setAlignment(Qt.AlignCenter)
        layout.addWidget(val)

        return card
