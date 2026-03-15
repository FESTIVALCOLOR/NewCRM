# -*- coding: utf-8 -*-
"""
Вкладка «Отчеты по сотрудникам» — KPI-аналитика + отчёты по заказам и зарплатам.

Интегрирует:
  - KPI-дашборд (6 карточек)
  - Вкладки по ролям (динамические) с таблицей сравнения
  - Детальная карточка сотрудника
  - Существующие таблицы (выполненные заказы, зарплаты) + PDF экспорт
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QComboBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QFileDialog, QSpinBox, QFrame, QSplitter, QGridLayout, QScrollArea,
    QSizePolicy,
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor

from ui.custom_combobox import CustomComboBox
from database.db_manager import DatabaseManager
from utils.pdf_utils import build_table_pdf
from utils.icon_loader import IconLoader
from utils.calendar_helpers import ICONS_PATH
from utils.table_settings import apply_no_focus_delegate
from utils.data_access import DataAccess
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# ── Маппинги ──────────────────────────────────────────────────────────

PROJECT_TYPE_MAP = {
    'Индивидуальный': 'individual',
    'Шаблонный': 'template',
    'Авторский надзор': 'supervision',
}

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

# ── Стили ─────────────────────────────────────────────────────────────

CARD_STYLE = """
    QFrame {{
        background-color: {bg};
        border: 1px solid #E0E0E0;
        border-radius: 8px;
        padding: 8px;
    }}
"""

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

# 4 уровня цветовой кодировки по руководству
KPI_COLORS = {
    'excellent': '#27AE60',   # ≥80%
    'normal': '#F1C40F',      # 60-79%
    'attention': '#E67E22',   # 40-59%
    'critical': '#E74C3C',    # <40%
}

KPI_BG = {
    'excellent': '#E8F5E9',
    'normal': '#FFF8E1',
    'attention': '#FFF3E0',
    'critical': '#FFEBEE',
}


def _kpi_color(value):
    """4-уровневая цветовая кодировка KPI."""
    if value is None:
        return '#999'
    if value >= 80:
        return KPI_COLORS['excellent']
    if value >= 60:
        return KPI_COLORS['normal']
    if value >= 40:
        return KPI_COLORS['attention']
    return KPI_COLORS['critical']


def _kpi_bg(value):
    """Фоновый цвет KPI-карточки."""
    if value is None:
        return '#FAFAFA'
    if value >= 80:
        return KPI_BG['excellent']
    if value >= 60:
        return KPI_BG['normal']
    if value >= 40:
        return KPI_BG['attention']
    return KPI_BG['critical']


class EmployeeReportsTab(QWidget):
    """Вкладка отчётов и аналитики сотрудников."""

    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client
        self.db = DatabaseManager()
        self.data_access = DataAccess(api_client=self.api_client, db=self.db)
        self._loading = False
        self._dashboard_cache = {}
        self._role_cache = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        header = QLabel(' Отчеты по сотрудникам')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #333; padding: 5px;')
        layout.addWidget(header)

        # Вкладки по типам проектов
        self.report_tabs = QTabWidget()
        self.report_tabs.currentChanged.connect(self._on_project_tab_changed)

        self.individual_tab = self._create_project_tab('Индивидуальный')
        self.report_tabs.addTab(self.individual_tab, 'Индивидуальные проекты')

        self.template_tab = self._create_project_tab('Шаблонный')
        self.report_tabs.addTab(self.template_tab, 'Шаблонные проекты')

        self.supervision_tab = self._create_project_tab('Авторский надзор')
        self.report_tabs.addTab(self.supervision_tab, 'Авторский надзор')

        layout.addWidget(self.report_tabs)
        self.setLayout(layout)

    # ══════════════════════════════════════════════════════════════════
    # СОЗДАНИЕ ВКЛАДКИ ПРОЕКТА (KPI + отчёты)
    # ══════════════════════════════════════════════════════════════════

    def _create_project_tab(self, project_type):
        """Создаёт вкладку для типа проекта: аналитика + отчёты."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(8)
        layout.setContentsMargins(4, 4, 4, 4)

        pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')

        # ── Фильтры ──────────────────────────────────────────────
        filters_row = QHBoxLayout()
        filters_row.addWidget(QLabel('Год:'))
        year_spin = QSpinBox()
        year_spin.setRange(2020, 2030)
        year_spin.setValue(QDate.currentDate().year())
        year_spin.setObjectName(f'year_{project_type}')
        year_spin.setStyleSheet(f"""
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
        filters_row.addWidget(year_spin)

        filters_row.addWidget(QLabel('Квартал:'))
        quarter_combo = CustomComboBox()
        quarter_combo.addItems(['Все', 'Q1', 'Q2', 'Q3', 'Q4'])
        quarter_combo.setObjectName(f'quarter_{project_type}')
        filters_row.addWidget(quarter_combo)

        filters_row.addWidget(QLabel('Месяц:'))
        month_combo = CustomComboBox()
        months = ['Все', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь',
                  'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
        month_combo.addItems(months)
        month_combo.setObjectName(f'month_{project_type}')
        filters_row.addWidget(month_combo)

        refresh_btn = IconLoader.create_icon_button('refresh', 'Обновить', icon_size=12)
        refresh_btn.clicked.connect(lambda: self._refresh_all(project_type))
        filters_row.addWidget(refresh_btn)
        filters_row.addStretch()
        layout.addLayout(filters_row)

        # ── 6 KPI-карточек (по руководству) ──────────────────────
        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(6)
        kpi_cards = []
        card_defs = [
            ('Сотрудников', '—', '#F0F4FF'),
            ('Средний KPI', '—', '#FAFAFA'),
            ('Выполнение в срок', '—', '#E8F5E9'),
            ('Средняя нагрузка', '—', '#F0F4FF'),
            ('NPS клиентов', '—', '#FFF8E1'),
            ('Активных проектов', '—', '#F0F4FF'),
        ]
        for label, value, bg in card_defs:
            card = self._create_kpi_card(label, value, bg)
            kpi_row.addWidget(card)
            kpi_cards.append(card)
        layout.addLayout(kpi_row)
        # Сохраняем ссылки
        container.setProperty('kpi_cards', kpi_cards)

        # ── Вкладки ролей ─────────────────────────────────────────
        role_tabs = QTabWidget()
        role_tabs.setObjectName(f'role_tabs_{project_type}')
        role_tabs.setStyleSheet("""
            QTabWidget::pane { border: 1px solid #E0E0E0; border-radius: 4px; }
            QTabBar::tab {
                padding: 5px 14px; margin-right: 2px;
                border: 1px solid #E0E0E0; border-bottom: none;
                border-radius: 4px 4px 0 0; background: #FAFAFA;
            }
            QTabBar::tab:selected { background: #FFFFFF; font-weight: bold; }
        """)

        roles = ROLE_TABS.get(pt_code, [])
        for role_code, role_label in roles:
            tab = QWidget()
            tab.setProperty('role_code', role_code)
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(4, 4, 4, 4)

            table = QTableWidget()
            table.setObjectName(f'role_table_{project_type}_{role_code}')
            table.setStyleSheet(TABLE_STYLE)
            apply_no_focus_delegate(table)
            table.setColumnCount(8)
            table.setHorizontalHeaderLabels([
                'Сотрудник', 'KPI', 'Kсрок', 'Kкачество',
                'Kскорость', 'NPS', 'Проектов', 'Зарплата'
            ])
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, 8):
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            table.verticalHeader().setDefaultSectionSize(32)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            table.cellClicked.connect(
                lambda r, c, pt=project_type: self._on_employee_clicked(r, c, pt))

            tab_layout.addWidget(table)
            role_tabs.addTab(tab, role_label)

        role_tabs.currentChanged.connect(
            lambda idx, pt=project_type: self._on_role_tab_changed(idx, pt))
        layout.addWidget(role_tabs)

        # ── Детальная карточка сотрудника ──────────────────────────
        detail_widget = QWidget()
        detail_widget.setObjectName(f'detail_{project_type}')
        detail_layout = QVBoxLayout(detail_widget)
        detail_layout.setContentsMargins(0, 4, 0, 0)

        detail_header = QLabel('Детальная карточка сотрудника')
        detail_header.setStyleSheet('font-size: 13px; font-weight: bold; color: #555; padding: 4px;')
        detail_layout.addWidget(detail_header)

        detail_info = QLabel('Выберите сотрудника из таблицы выше')
        detail_info.setObjectName(f'detail_info_{project_type}')
        detail_info.setStyleSheet('color: #999; padding: 8px;')
        detail_layout.addWidget(detail_info)

        detail_content = QWidget()
        detail_content.setObjectName(f'detail_content_{project_type}')
        detail_content_layout = QVBoxLayout(detail_content)
        detail_content_layout.setContentsMargins(0, 0, 0, 0)
        detail_content.hide()
        detail_layout.addWidget(detail_content)

        layout.addWidget(detail_widget)

        # ── Существующие отчёты (заказы + зарплаты) ───────────────
        reports_group = QGroupBox('Отчёты по заказам и зарплатам')
        reports_layout = QVBoxLayout()

        tables_row = QHBoxLayout()

        # Таблица выполненных заказов
        completed_group = QGroupBox('Выполненные заказы')
        completed_layout = QVBoxLayout()
        completed_table = QTableWidget()
        apply_no_focus_delegate(completed_table)
        completed_table.setStyleSheet(TABLE_STYLE)
        completed_table.setObjectName(f'completed_table_{project_type}')
        completed_table.setColumnCount(3)
        completed_table.setHorizontalHeaderLabels(['Исполнитель', 'Должность', 'Количество'])
        completed_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        completed_table.setMaximumHeight(250)
        completed_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        completed_table.verticalHeader().setDefaultSectionSize(32)
        completed_layout.addWidget(completed_table)
        completed_group.setLayout(completed_layout)
        tables_row.addWidget(completed_group)

        # Таблица зарплат
        salary_group = QGroupBox('Сумма зарплаты')
        salary_layout = QVBoxLayout()
        salary_table = QTableWidget()
        apply_no_focus_delegate(salary_table)
        salary_table.setStyleSheet(TABLE_STYLE)
        salary_table.setObjectName(f'salary_table_{project_type}')
        salary_table.setColumnCount(3)
        salary_table.setHorizontalHeaderLabels(['Исполнитель', 'Должность', 'Сумма'])
        salary_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        salary_table.setMaximumHeight(250)
        salary_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        salary_table.verticalHeader().setDefaultSectionSize(32)
        salary_layout.addWidget(salary_table)
        salary_group.setLayout(salary_layout)
        tables_row.addWidget(salary_group)

        reports_layout.addLayout(tables_row)

        # Экспорт
        export_row = QHBoxLayout()
        export_row.addStretch()
        export_completed_btn = IconLoader.create_icon_button(
            'export', 'Экспорт: Выполненные заказы', icon_size=12)
        export_completed_btn.clicked.connect(
            lambda: self._export_report(project_type, 'completed'))
        export_row.addWidget(export_completed_btn)
        export_salary_btn = IconLoader.create_icon_button(
            'export', 'Экспорт: Зарплаты', icon_size=12)
        export_salary_btn.clicked.connect(
            lambda: self._export_report(project_type, 'salary'))
        export_row.addWidget(export_salary_btn)
        reports_layout.addLayout(export_row)

        reports_group.setLayout(reports_layout)
        layout.addWidget(reports_group)

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ══════════════════════════════════════════════════════════════════
    # ЗАГРУЗКА ДАННЫХ
    # ══════════════════════════════════════════════════════════════════

    def ensure_data_loaded(self):
        """Ленивая загрузка при первом показе."""
        QTimer.singleShot(200, lambda: self._refresh_all('Индивидуальный'))

    def _on_project_tab_changed(self, index):
        types = ['Индивидуальный', 'Шаблонный', 'Авторский надзор']
        if 0 <= index < len(types):
            self._refresh_all(types[index])

    def _on_role_tab_changed(self, index, project_type):
        if index < 0:
            return
        pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')
        roles = ROLE_TABS.get(pt_code, [])
        if 0 <= index < len(roles):
            self._load_role_data(project_type, roles[index][0])

    def _get_tab_widget(self, project_type):
        if project_type == 'Индивидуальный':
            return self.individual_tab
        elif project_type == 'Шаблонный':
            return self.template_tab
        return self.supervision_tab

    def _get_container(self, project_type):
        tab = self._get_tab_widget(project_type)
        return tab.widget() if hasattr(tab, 'widget') else tab

    def _get_period_params(self, project_type) -> dict:
        container = self._get_container(project_type)
        year_spin = container.findChild(QSpinBox, f'year_{project_type}')
        quarter_combo = container.findChild(QComboBox, f'quarter_{project_type}')
        month_combo = container.findChild(QComboBox, f'month_{project_type}')

        params = {'year': year_spin.value() if year_spin else QDate.currentDate().year()}
        if quarter_combo:
            q_text = quarter_combo.currentText()
            if q_text != 'Все' and len(q_text) > 1 and q_text[1].isdigit():
                params['quarter'] = int(q_text[1])
        if month_combo:
            m_idx = month_combo.currentIndex()
            if m_idx > 0:
                params['month'] = m_idx
        return params

    def _refresh_all(self, project_type):
        """Обновляет аналитику + отчёты для типа проекта."""
        if self._loading:
            return
        self._loading = True
        try:
            pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')
            period = self._get_period_params(project_type)

            # 1. Дашборд KPI
            try:
                dashboard = self.data_access.get_analytics_dashboard(pt_code, **period)
            except Exception as e:
                logger.warning(f"Ошибка дашборда аналитики: {e}")
                dashboard = {}
            self._dashboard_cache[project_type] = dashboard
            self._update_kpi_cards(project_type, dashboard)

            # 2. Данные текущей роли
            container = self._get_container(project_type)
            role_tabs = container.findChild(QTabWidget, f'role_tabs_{project_type}')
            if role_tabs and role_tabs.count() > 0:
                current = role_tabs.currentWidget()
                if current:
                    role_code = current.property('role_code')
                    if role_code:
                        self._load_role_data(project_type, role_code)

            # 3. Отчёты по заказам/зарплатам (существующая логика)
            self._load_report_tables(project_type, period)

        except Exception as e:
            logger.error(f"Ошибка загрузки аналитики: {e}", exc_info=True)
        finally:
            self._loading = False

    def _load_role_data(self, project_type, role_code):
        """Загрузка таблицы сравнения по роли."""
        pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')
        period = self._get_period_params(project_type)

        try:
            data = self.data_access.get_analytics_by_role(role_code, pt_code, **period)
        except Exception as e:
            logger.warning(f"Ошибка загрузки роли {role_code}: {e}")
            data = {}
        self._role_cache[f'{project_type}_{role_code}'] = data
        self._update_role_table(project_type, role_code, data)

    def _load_employee_detail(self, project_type, employee_id):
        """Загрузка детальной карточки сотрудника."""
        pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')
        period = self._get_period_params(project_type)

        try:
            detail = self.data_access.get_analytics_employee_detail(
                employee_id, pt_code, **period)
        except Exception as e:
            logger.warning(f"Ошибка загрузки деталей сотрудника {employee_id}: {e}")
            detail = {}
        self._update_detail_card(project_type, detail)

    def _load_report_tables(self, project_type, period):
        """Загрузка таблиц выполненных заказов и зарплат."""
        try:
            report_data = self.data_access.get_employee_report_data(
                self.employee.get('id', 0),
                project_type=project_type,
                period='За год',
                year=period.get('year', QDate.currentDate().year()),
                quarter=period.get('quarter'),
                month=period.get('month'),
            )
        except Exception as e:
            logger.warning(f"DataAccess get_employee_report_data: {e}")
            report_data = {'completed': [], 'salaries': []}

        container = self._get_container(project_type)
        self._fill_completed_table(container, project_type, report_data.get('completed', []))
        self._fill_salary_table(container, project_type, report_data.get('salaries', []))

    # ══════════════════════════════════════════════════════════════════
    # ОБНОВЛЕНИЕ UI
    # ══════════════════════════════════════════════════════════════════

    def _update_kpi_cards(self, project_type, dashboard):
        """Обновляет 6 KPI-карточек."""
        container = self._get_container(project_type)
        kpi_cards = container.property('kpi_cards')
        if not kpi_cards or not dashboard:
            return

        summary = dashboard.get('summary', {})

        avg_kpi = summary.get('avg_kpi', 0) or 0
        on_time = summary.get('avg_on_time_rate', 0) or 0
        avg_nps = summary.get('avg_nps')

        cards_data = [
            ('Сотрудников', str(summary.get('total_employees', 0)), '#F0F4FF'),
            ('Средний KPI', f"{avg_kpi:.0f}%", _kpi_bg(avg_kpi)),
            ('Выполнение в срок', f"{on_time:.0f}%", _kpi_bg(on_time)),
            ('Средняя нагрузка', f"{summary.get('avg_concurrent_load', 0):.1f}", '#F0F4FF'),
            ('NPS клиентов', f"{avg_nps:.1f}" if avg_nps else '—', '#FFF8E1'),
            ('Активных проектов', str(summary.get('active_projects', 0)), '#F0F4FF'),
        ]

        for i, (label, value, bg) in enumerate(cards_data):
            if i < len(kpi_cards):
                self._update_card_widget(kpi_cards[i], label, value, bg)

    def _update_role_table(self, project_type, role_code, data):
        """Обновляет таблицу сравнения по роли."""
        container = self._get_container(project_type)
        table = container.findChild(
            QTableWidget, f'role_table_{project_type}_{role_code}')
        if not table:
            return

        employees = data.get('employees', [])
        table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            kpi_total = emp.get('kpi_total', 0) or 0

            # Имя
            name_item = QTableWidgetItem(emp.get('full_name', ''))
            name_item.setData(Qt.UserRole, emp.get('employee_id'))
            table.setItem(row, 0, name_item)

            # KPI (цветной)
            kpi_item = QTableWidgetItem(f"{kpi_total:.0f}%")
            kpi_item.setTextAlignment(Qt.AlignCenter)
            kpi_item.setForeground(QColor(_kpi_color(kpi_total)))
            font = kpi_item.font()
            font.setBold(True)
            kpi_item.setFont(font)
            table.setItem(row, 1, kpi_item)

            # Компоненты KPI
            for col, key in enumerate(
                    ['k_deadline', 'k_quality', 'k_speed', 'k_nps'], start=2):
                val = emp.get(key)
                text = f"{val:.0f}%" if val is not None else '—'
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                if val is not None:
                    item.setForeground(QColor(_kpi_color(val)))
                table.setItem(row, col, item)

            # Проектов
            projects_item = QTableWidgetItem(str(emp.get('concurrent_projects', 0)))
            projects_item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, 6, projects_item)

            # Зарплата
            salary = emp.get('total_salary', 0)
            salary_item = QTableWidgetItem(
                f"{salary:,.0f}" if salary else '—')
            salary_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 7, salary_item)

    def _update_detail_card(self, project_type, detail):
        """Обновляет детальную карточку сотрудника."""
        container = self._get_container(project_type)
        info_label = container.findChild(QLabel, f'detail_info_{project_type}')
        content = container.findChild(QWidget, f'detail_content_{project_type}')

        if not detail or not detail.get('employee'):
            if info_label:
                info_label.setText('Нет данных по сотруднику')
                info_label.show()
            if content:
                content.hide()
            return

        if info_label:
            info_label.hide()
        if not content:
            return
        content.show()

        # Очищаем
        layout = content.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        emp = detail['employee']
        kpi = detail.get('kpi', {})
        metrics = detail.get('metrics', {})
        projects = detail.get('projects', [])
        reviews = detail.get('client_reviews', [])
        trend = detail.get('kpi_monthly', [])

        # Имя + KPI
        info_row = QHBoxLayout()
        name_label = QLabel(
            f"<b>{emp.get('full_name', '')}</b> — {emp.get('position', '')}")
        name_label.setStyleSheet('font-size: 14px; color: #333;')
        info_row.addWidget(name_label)
        info_row.addStretch()

        kpi_total = kpi.get('total', 0) or 0
        kpi_label = QLabel(f"KPI: <b>{kpi_total:.0f}%</b>")
        kpi_label.setStyleSheet(
            f'font-size: 16px; color: {_kpi_color(kpi_total)};')
        info_row.addWidget(kpi_label)

        info_w = QWidget()
        info_w.setLayout(info_row)
        layout.addWidget(info_w)

        # KPI-компоненты (6 мини-карточек)
        kpi_grid = QGridLayout()
        components = [
            ('Kсрок', kpi.get('k_deadline')),
            ('Kкачество', kpi.get('k_quality')),
            ('Kскорость', kpi.get('k_speed')),
            ('K NPS', kpi.get('k_nps')),
            ('Проектов', f"{metrics.get('concurrent_projects', 0)}/{metrics.get('recommended_max_load', '?')}"),
            ('Зарплата', f"{metrics.get('total_salary', 0):,.0f}"),
        ]
        for col, (label, val) in enumerate(components):
            if isinstance(val, str):
                text = val
            elif val is not None:
                text = f"{val:.0f}%"
            else:
                text = '—'
            w = self._create_mini_card(label, text)
            kpi_grid.addWidget(w, 0, col)

        kpi_w = QWidget()
        kpi_w.setLayout(kpi_grid)
        layout.addWidget(kpi_w)

        # Проекты
        if projects:
            proj_group = QGroupBox(f'Проекты ({len(projects)})')
            proj_layout = QVBoxLayout()
            proj_table = QTableWidget()
            apply_no_focus_delegate(proj_table)
            proj_table.setStyleSheet(TABLE_STYLE)
            proj_table.setColumnCount(5)
            proj_table.setHorizontalHeaderLabels([
                'Договор', 'Адрес', 'Стадия', 'Статус', 'Отклонение (дн.)'])
            proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            for c in range(2, 5):
                proj_table.horizontalHeader().setSectionResizeMode(c, QHeaderView.ResizeToContents)
            proj_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            proj_table.verticalHeader().setDefaultSectionSize(28)
            proj_table.setRowCount(len(projects))
            proj_table.setMaximumHeight(min(200, 32 + len(projects) * 28))

            for row, p in enumerate(projects):
                proj_table.setItem(row, 0, QTableWidgetItem(
                    str(p.get('contract_number', ''))))
                proj_table.setItem(row, 1, QTableWidgetItem(
                    p.get('address', '')))
                proj_table.setItem(row, 2, QTableWidgetItem(
                    p.get('current_stage', '')))
                proj_table.setItem(row, 3, QTableWidgetItem(
                    p.get('status', '')))
                deviation = p.get('deviation_days')
                dev_item = QTableWidgetItem(
                    str(deviation) if deviation else '—')
                dev_item.setTextAlignment(Qt.AlignCenter)
                if deviation and deviation > 0:
                    dev_item.setForeground(QColor(KPI_COLORS['critical']))
                proj_table.setItem(row, 4, dev_item)

            proj_layout.addWidget(proj_table)
            proj_group.setLayout(proj_layout)
            layout.addWidget(proj_group)

        # Отзывы клиентов (до 10)
        if reviews:
            rev_group = QGroupBox(f'Отзывы клиентов ({len(reviews)})')
            rev_layout = QVBoxLayout()
            for review in reviews[:10]:
                nps = review.get('nps_score', '—')
                csat = review.get('csat_score', '—')
                contract = review.get('contract_number', '?')
                comment = (review.get('comment') or '')[:100]
                r_label = QLabel(
                    f"NPS: <b>{nps}</b> | CSAT: <b>{csat}</b> | "
                    f"Договор: {contract} | <i>{comment}</i>")
                r_label.setStyleSheet('color: #555; padding: 2px 0;')
                r_label.setWordWrap(True)
                rev_layout.addWidget(r_label)
            rev_group.setLayout(rev_layout)
            layout.addWidget(rev_group)

        # Тренд KPI
        if trend:
            trend_group = QGroupBox('Тренд KPI (последние месяцы)')
            trend_layout = QHBoxLayout()
            for t in trend[-6:]:
                kpi_val = t.get('kpi_total', 0) or 0
                month_label = QLabel(
                    f"<b>{t.get('month', '')}</b><br>{kpi_val:.0f}%")
                month_label.setAlignment(Qt.AlignCenter)
                month_label.setStyleSheet(
                    f'color: {_kpi_color(kpi_val)}; '
                    f'padding: 4px 8px; background: #FAFAFA; '
                    f'border-radius: 4px; border: 1px solid #EEE;')
                trend_layout.addWidget(month_label)
            trend_group.setLayout(trend_layout)
            layout.addWidget(trend_group)

    # ══════════════════════════════════════════════════════════════════
    # ОБРАБОТЧИКИ СОБЫТИЙ
    # ══════════════════════════════════════════════════════════════════

    def _on_employee_clicked(self, row, col, project_type):
        """Клик по сотруднику → детальная карточка."""
        container = self._get_container(project_type)
        role_tabs = container.findChild(QTabWidget, f'role_tabs_{project_type}')
        if not role_tabs:
            return
        current = role_tabs.currentWidget()
        if not current:
            return
        role_code = current.property('role_code')
        table = container.findChild(
            QTableWidget, f'role_table_{project_type}_{role_code}')
        if not table:
            return
        name_item = table.item(row, 0)
        if name_item:
            employee_id = name_item.data(Qt.UserRole)
            if employee_id:
                self._load_employee_detail(project_type, int(employee_id))

    # ══════════════════════════════════════════════════════════════════
    # СУЩЕСТВУЮЩИЕ ОТЧЁТЫ (выполненные + зарплаты)
    # ══════════════════════════════════════════════════════════════════

    def _fill_completed_table(self, container, project_type, data):
        table = container.findChild(QTableWidget, f'completed_table_{project_type}')
        if not table:
            return
        table.setRowCount(len(data))
        for row, item in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(item.get('employee_name', '')))
            table.setItem(row, 1, QTableWidgetItem(item.get('position', '')))
            table.setItem(row, 2, QTableWidgetItem(str(item.get('count', 0))))

    def _fill_salary_table(self, container, project_type, data):
        table = container.findChild(QTableWidget, f'salary_table_{project_type}')
        if not table:
            return
        table.setRowCount(len(data))
        total = 0
        for row, item in enumerate(data):
            table.setItem(row, 0, QTableWidgetItem(item.get('employee_name', '')))
            table.setItem(row, 1, QTableWidgetItem(item.get('position', '')))
            salary = item.get('total_salary', 0)
            amount_item = QTableWidgetItem(f"{salary:,.2f} ₽")
            amount_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, 2, amount_item)
            total += salary
        if data:
            table.setRowCount(len(data) + 1)
            total_label = QTableWidgetItem('ИТОГО:')
            font = total_label.font()
            font.setBold(True)
            total_label.setFont(font)
            table.setItem(len(data), 1, total_label)
            total_item = QTableWidgetItem(f"{total:,.2f} ₽")
            total_item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            total_item.setBackground(Qt.lightGray)
            font = total_item.font()
            font.setBold(True)
            total_item.setFont(font)
            table.setItem(len(data), 2, total_item)

    def _export_report(self, project_type, report_type):
        """Экспорт отчёта в PDF."""
        try:
            period = self._get_period_params(project_type)
            filename, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить отчет',
                f'Отчет Сотрудники {report_type} от {datetime.now().strftime("%d.%m.%Y")}.pdf',
                'PDF Files (*.pdf)')
            if not filename:
                return

            try:
                report_data = self.data_access.get_employee_report_data(
                    self.employee.get('id', 0),
                    project_type=project_type, period='За год',
                    year=period.get('year'), quarter=period.get('quarter'),
                    month=period.get('month'))
            except Exception as e:
                logger.warning("get_employee_report_data: %s", e)
                report_data = {'completed': [], 'salaries': []}

            if report_type == 'completed':
                data = report_data.get('completed', [])
                headers = ['Исполнитель', 'Должность', 'Количество проектов']
                title = f'Выполненные заказы - {project_type}'
                pdf_data = [[i.get('employee_name', ''), i.get('position', ''),
                             str(i.get('count', 0))] for i in data]
            else:
                data = report_data.get('salaries', [])
                headers = ['Исполнитель', 'Должность', 'Сумма (руб.)']
                title = f'Зарплаты - {project_type}'
                pdf_data = [[i.get('employee_name', ''), i.get('position', ''),
                             f"{i.get('total_salary', 0):,.2f}"] for i in data]

            build_table_pdf(
                output_path=filename, title=title,
                headers=headers, rows=pdf_data,
                summary_items=[('Всего записей', str(len(pdf_data)))])

        except Exception as e:
            logger.error("Ошибка экспорта: %s", e, exc_info=True)
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(self, 'Ошибка', f'Ошибка экспорта:\n{e}', 'error').exec_()

    # ══════════════════════════════════════════════════════════════════
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _create_kpi_card(label, value, bg):
        card = QFrame()
        card.setStyleSheet(CARD_STYLE.format(bg=bg))
        card.setFixedHeight(68)
        card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(2)
        lbl = QLabel(label)
        lbl.setStyleSheet('font-size: 10px; color: #888; border: none;')
        lbl.setAlignment(Qt.AlignLeft)
        layout.addWidget(lbl)
        val = QLabel(value)
        val.setStyleSheet('font-size: 16px; font-weight: bold; color: #333; border: none;')
        val.setAlignment(Qt.AlignLeft)
        layout.addWidget(val)
        return card

    @staticmethod
    def _update_card_widget(card, label, value, bg):
        card.setStyleSheet(CARD_STYLE.format(bg=bg))
        labels = card.findChildren(QLabel)
        if len(labels) >= 2:
            labels[0].setText(label)
            labels[1].setText(value)

    @staticmethod
    def _create_mini_card(label, value):
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
        val.setStyleSheet('font-size: 13px; font-weight: bold; color: #333; border: none;')
        val.setAlignment(Qt.AlignCenter)
        layout.addWidget(val)
        return card
