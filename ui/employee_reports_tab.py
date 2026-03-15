# -*- coding: utf-8 -*-
"""
Вкладка «Отчеты по сотрудникам» — KPI-аналитика.

Заменяет старую страницу (отчёты по заказам/зарплатам) на полноценный
KPI-дашборд согласно руководству:
  - 6 KPI-карточек сводного дашборда
  - Топ-5 лучших / проблемных
  - Вкладки по ролям с таблицей сравнения
  - Детальная карточка сотрудника (мини-KPI, проекты, отзывы, тренд)
"""
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox, QPushButton,
    QComboBox, QTabWidget, QTableWidget, QTableWidgetItem, QHeaderView,
    QSpinBox, QFrame, QGridLayout, QScrollArea, QSizePolicy, QFileDialog,
)
from PyQt5.QtCore import Qt, QDate, QTimer
from PyQt5.QtGui import QColor, QFont

from ui.custom_combobox import CustomComboBox
from ui.chart_widget import (
    LineChartWidget, StackedBarChartWidget, HorizontalBarWidget,
    MATPLOTLIB_AVAILABLE,
)
from database.db_manager import DatabaseManager
from utils.icon_loader import IconLoader
from utils.calendar_helpers import ICONS_PATH
from utils.table_settings import apply_no_focus_delegate
from utils.data_access import DataAccess
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

# Заголовки таблицы по роли (раздел 8 руководства — специфичные столбцы)
ROLE_TABLE_HEADERS = {
    # CRM: Ст. менеджеры (инд/шабл)
    ('senior_manager', 'individual'): [
        'Сотрудник', 'KPI', 'Проектов', 'Сдано', 'Расторг.',
        'NPS', 'Нагрузка', 'Тренд',
    ],
    ('senior_manager', 'template'): [
        'Сотрудник', 'KPI', 'Проектов', 'Сдано', 'Расторг.',
        'NPS', 'Нагрузка', 'Тренд',
    ],
    # Надзор: Ст. менеджеры
    ('senior_manager', 'supervision'): [
        'Сотрудник', 'KPI', 'Ведёт', 'Сдано', 'Экономия',
        'Визиты', 'NPS', 'Тренд',
    ],
    # СДП
    ('sdp', 'individual'): [
        'Сотрудник', 'KPI', 'В срок', 'Просрочки', 'Правки',
        'Нагрузка', 'NPS', 'Тренд',
    ],
    # ГАП
    ('gap', 'individual'): [
        'Сотрудник', 'KPI', 'В срок', 'Просрочки', 'Правки',
        'Нагрузка', 'NPS', 'Тренд',
    ],
    ('gap', 'template'): [
        'Сотрудник', 'KPI', 'В срок', 'Просрочки', 'Правки',
        'Нагрузка', 'NPS', 'Тренд',
    ],
    # Менеджеры (шаблонные)
    ('manager', 'template'): [
        'Сотрудник', 'KPI', 'В срок', 'Просрочки', 'Правки',
        'Нагрузка', 'NPS', 'Тренд',
    ],
    # Чертёжники / Дизайнеры
    ('draftsman', 'individual'): [
        'Сотрудник', 'KPI', 'Стадий', 'В срок', 'Правки',
        'Площадь (м²)', 'Нагрузка', 'Тренд',
    ],
    ('draftsman', 'template'): [
        'Сотрудник', 'KPI', 'Стадий', 'В срок', 'Правки',
        'Площадь (м²)', 'Нагрузка', 'Тренд',
    ],
    ('designer', 'individual'): [
        'Сотрудник', 'KPI', 'Стадий', 'В срок', 'Правки',
        'Площадь (м²)', 'Нагрузка', 'Тренд',
    ],
    ('designer', 'template'): [
        'Сотрудник', 'KPI', 'Стадий', 'В срок', 'Правки',
        'Площадь (м²)', 'Нагрузка', 'Тренд',
    ],
    # Замерщики
    ('measurer', 'individual'): [
        'Сотрудник', 'KPI', 'Замеров', 'В срок', 'Ср. дней',
        'Нагрузка', 'NPS', 'Тренд',
    ],
    # ДАН (надзор)
    ('dan', 'supervision'): [
        'Сотрудник', 'KPI', 'Ведёт', 'Визиты', 'Дефекты',
        '% устр.', 'Экономия', 'Просрочки', 'Тренд',
    ],
}

# Fallback заголовки
CRM_TABLE_HEADERS_DEFAULT = [
    'Сотрудник', 'KPI', 'В срок', 'Просрочки', 'Правки',
    'Нагрузка', 'NPS', 'Тренд',
]
SUPERVISION_TABLE_HEADERS_DEFAULT = [
    'Сотрудник', 'KPI', 'Закупки', 'Дефекты', 'Визиты',
    'Экономия', 'Нагрузка', 'NPS', 'Тренд',
]


def _get_role_headers(role_code, pt_code):
    """Получить заголовки таблицы для конкретной роли и типа проекта."""
    headers = ROLE_TABLE_HEADERS.get((role_code, pt_code))
    if headers:
        return headers
    if pt_code == 'supervision':
        return SUPERVISION_TABLE_HEADERS_DEFAULT
    return CRM_TABLE_HEADERS_DEFAULT

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
    'excellent': '#2E7D32',   # ≥80%
    'normal': '#F57F17',      # 60-79%
    'attention': '#E65100',   # 40-59%
    'critical': '#C62828',    # <40%
}

KPI_BG = {
    'excellent': '#E8F5E9',
    'normal': '#FFF8E1',
    'attention': '#FFF3E0',
    'critical': '#FFEBEE',
}

TREND_ICONS = {
    'up': '▲',
    'down': '▼',
    'stable': '—',
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
    """Вкладка KPI-аналитики по сотрудникам."""

    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client
        self.db = DatabaseManager()
        self.data_access = DataAccess(api_client=self.api_client, db=self.db)
        self._loading = False
        self._dashboard_cache = {}
        self._role_cache = {}
        # Хранение ссылок на KPI-карточки (setProperty не работает с Python list!)
        self._kpi_cards = {}
        # Ссылки на Топ-5 виджеты
        self._top5_widgets = {}
        # Определяем уровень доступа по должности (раздел 5 руководства)
        position = (employee or {}).get('position', '')
        if position == 'Руководитель студии':
            self.access_level = 'full'
        elif position == 'Старший менеджер проектов':
            self.access_level = 'team'
        elif position in ('СДП', 'ГАП', 'Менеджер'):
            self.access_level = 'executors'
        else:
            self.access_level = 'self'
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)

        header_row = QHBoxLayout()
        header = QLabel(' Отчеты по сотрудникам')
        header.setStyleSheet('font-size: 14px; font-weight: bold; color: #333; padding: 5px;')
        header_row.addWidget(header)
        header_row.addStretch()

        export_btn = IconLoader.create_icon_button('download', 'Экспорт PDF', icon_size=12)
        export_btn.setStyleSheet("""
            QPushButton {
                background: #F0F4FF; border: 1px solid #C5CAE9; border-radius: 4px;
                padding: 4px 12px; color: #333; font-size: 11px;
            }
            QPushButton:hover { background: #E8EAF6; }
        """)
        export_btn.clicked.connect(self._export_to_pdf)
        header_row.addWidget(export_btn)
        layout.addLayout(header_row)

        if self.access_level == 'self':
            # Исполнители/Замерщики/ДАН — только свой профиль
            self._build_self_only_view(layout)
        else:
            # Руководитель/СМ/СДП/ГАП/Менеджер — полная/частичная страница
            self._build_full_view(layout)

        self.setLayout(layout)

    def _build_self_only_view(self, layout):
        """Режим «только свой профиль» — без дашборда и таблиц сравнения."""
        info = QLabel('Моя статистика')
        info.setStyleSheet('font-size: 13px; font-weight: bold; color: #555; padding: 4px;')
        layout.addWidget(info)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        container = QWidget()
        container.setObjectName('self_detail_container')
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(4, 4, 4, 4)

        detail_content = QWidget()
        detail_content.setObjectName('detail_content_self')
        detail_content_layout = QVBoxLayout(detail_content)
        detail_content_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.addWidget(detail_content)
        container_layout.addStretch()

        scroll.setWidget(container)
        layout.addWidget(scroll)
        self._self_detail_content = detail_content

    def _build_full_view(self, layout):
        """Полная страница с дашбордом, вкладками ролей и карточками."""
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

    # ══════════════════════════════════════════════════════════════════
    # СОЗДАНИЕ ВКЛАДКИ ПРОЕКТА
    # ══════════════════════════════════════════════════════════════════

    def _create_project_tab(self, project_type):
        """Создаёт вкладку для типа проекта — единый скролл."""
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

        # ── 6 KPI-карточек ─────────────────────────────────────────
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
        # Сохраняем ссылки в dict (НЕ setProperty — Python list через QVariant ненадёжен)
        self._kpi_cards[project_type] = kpi_cards

        # ── Топ-5 лучших и проблемных ───────────────────────────────
        top_row = QHBoxLayout()
        top_row.setSpacing(8)

        top_best = QGroupBox('Топ-5 лучших')
        top_best.setStyleSheet("""
            QGroupBox {
                border: 1px solid #C8E6C9; border-radius: 6px;
                margin-top: 10px; padding-top: 12px; background: #F1F8E9;
            }
            QGroupBox::title {
                subcontrol-origin: margin; padding: 2px 8px;
                color: #2E7D32; font-weight: bold;
            }
        """)
        top_best_layout = QVBoxLayout()
        top_best_label = QLabel('Загрузка...')
        top_best_label.setObjectName(f'top_best_{project_type}')
        top_best_label.setStyleSheet('color: #555; font-size: 11px;')
        top_best_layout.addWidget(top_best_label)
        top_best.setLayout(top_best_layout)
        top_row.addWidget(top_best)

        top_worst = QGroupBox('Топ-5 проблемных')
        top_worst.setStyleSheet("""
            QGroupBox {
                border: 1px solid #FFCDD2; border-radius: 6px;
                margin-top: 10px; padding-top: 12px; background: #FFF8F8;
            }
            QGroupBox::title {
                subcontrol-origin: margin; padding: 2px 8px;
                color: #C62828; font-weight: bold;
            }
        """)
        top_worst_layout = QVBoxLayout()
        top_worst_label = QLabel('Загрузка...')
        top_worst_label.setObjectName(f'top_worst_{project_type}')
        top_worst_label.setStyleSheet('color: #555; font-size: 11px;')
        top_worst_layout.addWidget(top_worst_label)
        top_worst.setLayout(top_worst_layout)
        top_row.addWidget(top_worst)

        layout.addLayout(top_row)

        # ── График тренда KPI (6 месяцев) ────────────────────────
        trend_chart = LineChartWidget('Тренд KPI (6 месяцев)')
        trend_chart.setObjectName(f'dashboard_trend_{project_type}')
        trend_chart.setFixedHeight(280)
        layout.addWidget(trend_chart)

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
            headers = _get_role_headers(role_code, pt_code)

            tab = QWidget()
            tab.setProperty('role_code', role_code)
            tab_layout = QVBoxLayout(tab)
            tab_layout.setContentsMargins(4, 4, 4, 4)

            table = QTableWidget()
            table.setObjectName(f'role_table_{project_type}_{role_code}')
            table.setStyleSheet(TABLE_STYLE)
            apply_no_focus_delegate(table)
            table.setColumnCount(len(headers))
            table.setHorizontalHeaderLabels(headers)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
            for col in range(1, len(headers)):
                table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
            table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            table.verticalHeader().setDefaultSectionSize(32)
            table.setSelectionBehavior(QTableWidget.SelectRows)
            table.setSelectionMode(QTableWidget.SingleSelection)
            # Убираем внутренний вертикальный скролл — пусть таблица растёт
            table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            table.cellClicked.connect(
                lambda r, c, pt=project_type: self._on_employee_clicked(r, c, pt))

            tab_layout.addWidget(table)

            # 3 графика сравнения по роли (согласно руководству)
            charts_row = QHBoxLayout()
            charts_row.setSpacing(6)

            kpi_bar_chart = HorizontalBarWidget('Сравнение KPI')
            kpi_bar_chart.setObjectName(f'role_kpi_chart_{project_type}_{role_code}')
            kpi_bar_chart.setFixedHeight(260)
            charts_row.addWidget(kpi_bar_chart)

            ontime_chart = StackedBarChartWidget('В срок / Просрочки')
            ontime_chart.setObjectName(f'role_ontime_chart_{project_type}_{role_code}')
            ontime_chart.setFixedHeight(260)
            charts_row.addWidget(ontime_chart)

            dynamics_chart = LineChartWidget('Динамика по месяцам')
            dynamics_chart.setObjectName(f'role_dynamics_chart_{project_type}_{role_code}')
            dynamics_chart.setFixedHeight(260)
            charts_row.addWidget(dynamics_chart)

            tab_layout.addLayout(charts_row)
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
        detail_header.setStyleSheet(
            'font-size: 13px; font-weight: bold; color: #555; padding: 4px;')
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

        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    # ══════════════════════════════════════════════════════════════════
    # ЗАГРУЗКА ДАННЫХ
    # ══════════════════════════════════════════════════════════════════

    def ensure_data_loaded(self):
        """Ленивая загрузка при первом показе."""
        if self.access_level == 'self':
            QTimer.singleShot(200, self._load_self_profile)
        else:
            QTimer.singleShot(200, lambda: self._refresh_all('Индивидуальный'))

    def _load_self_profile(self):
        """Загружает собственную карточку для исполнителей."""
        emp_id = (self.employee or {}).get('id')
        if not emp_id:
            return
        # Загружаем по всем типам проектов, берём первый с данными
        for pt_code in ('individual', 'template', 'supervision'):
            try:
                detail = self.data_access.get_analytics_employee_detail(
                    emp_id, pt_code)
            except Exception:
                detail = {}
            if detail and detail.get('employee'):
                self._update_detail_card_in_widget(
                    self._self_detail_content, pt_code, detail)
                return
        # Если нет данных ни по одному типу
        lbl = QLabel('Нет данных по вашим проектам')
        lbl.setStyleSheet('color: #999; padding: 16px; font-size: 13px;')
        self._self_detail_content.layout().addWidget(lbl)

    def _on_project_tab_changed(self, index):
        if self.access_level == 'self':
            return
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
        """Обновляет аналитику для типа проекта."""
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
            self._update_top5(project_type, dashboard)
            self._update_dashboard_trend(project_type, dashboard)

            # 2. Данные текущей роли
            container = self._get_container(project_type)
            role_tabs = container.findChild(QTabWidget, f'role_tabs_{project_type}')
            if role_tabs and role_tabs.count() > 0:
                current = role_tabs.currentWidget()
                if current:
                    role_code = current.property('role_code')
                    if role_code:
                        self._load_role_data(project_type, role_code)

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
            logger.warning(f"Ошибка загрузки деталей: {e}")
            detail = {}
        self._update_detail_card(project_type, detail)

    # ══════════════════════════════════════════════════════════════════
    # ОБНОВЛЕНИЕ UI
    # ══════════════════════════════════════════════════════════════════

    def _update_kpi_cards(self, project_type, dashboard):
        """Обновляет 6 KPI-карточек."""
        kpi_cards = self._kpi_cards.get(project_type, [])
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

    def _update_top5(self, project_type, dashboard):
        """Обновляет Топ-5 лучших и проблемных."""
        container = self._get_container(project_type)

        # Лучшие
        best_label = container.findChild(QLabel, f'top_best_{project_type}')
        top = dashboard.get('top_performers', [])
        if best_label:
            if top:
                lines = []
                for i, emp in enumerate(top[:5], 1):
                    kpi = emp.get('kpi_total', 0) or 0
                    trend = TREND_ICONS.get(emp.get('trend', 'stable'), '—')
                    lines.append(
                        f"<b>{i}.</b> {emp.get('full_name', '')} — "
                        f"<span style='color:{_kpi_color(kpi)}'><b>{kpi:.0f}%</b></span> "
                        f"{trend}")
                best_label.setText('<br>'.join(lines))
            else:
                best_label.setText('Нет данных')

        # Проблемные
        worst_label = container.findChild(QLabel, f'top_worst_{project_type}')
        under = dashboard.get('underperformers', [])
        if worst_label:
            if under:
                lines = []
                for i, emp in enumerate(under[:5], 1):
                    kpi = emp.get('kpi_total', 0) or 0
                    overdue = emp.get('overdue_count', emp.get('stages_overdue', 0))
                    lines.append(
                        f"<b>{i}.</b> {emp.get('full_name', '')} — "
                        f"<span style='color:{_kpi_color(kpi)}'><b>{kpi:.0f}%</b></span> "
                        f"({overdue} просроч.)")
                worst_label.setText('<br>'.join(lines))
            else:
                worst_label.setText('Нет проблемных сотрудников')

    def _update_dashboard_trend(self, project_type, dashboard):
        """Обновляет линейный график тренда KPI на дашборде (6 месяцев)."""
        container = self._get_container(project_type)
        chart = container.findChild(LineChartWidget, f'dashboard_trend_{project_type}')
        if not chart or not MATPLOTLIB_AVAILABLE:
            return
        trend_data = dashboard.get('kpi_trend', [])
        if not trend_data:
            return
        months = [t.get('month', '') for t in trend_data]
        avg_values = [t.get('avg_kpi', 0) or 0 for t in trend_data]
        series = [{'x': months, 'y': avg_values, 'label': 'Средний KPI', 'color': '#4A90D9'}]
        # Если есть min/max — добавим
        if any(t.get('min_kpi') is not None for t in trend_data):
            min_values = [t.get('min_kpi', 0) or 0 for t in trend_data]
            max_values = [t.get('max_kpi', 0) or 0 for t in trend_data]
            series.append({'x': months, 'y': max_values, 'label': 'Макс', 'color': '#7ED321'})
            series.append({'x': months, 'y': min_values, 'label': 'Мин', 'color': '#F5A623'})
        chart.set_data(series)

    def _update_role_table(self, project_type, role_code, data):
        """Обновляет таблицу сравнения по роли (столбцы зависят от роли)."""
        container = self._get_container(project_type)
        table = container.findChild(
            QTableWidget, f'role_table_{project_type}_{role_code}')
        if not table:
            return

        pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')
        headers = _get_role_headers(role_code, pt_code)
        employees = data.get('employees', [])

        # Обновляем заголовки (количество столбцов может отличаться)
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for col in range(1, len(headers)):
            table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        table.setRowCount(len(employees))

        for row, emp in enumerate(employees):
            kpi_total = emp.get('kpi_total', 0) or 0

            # Столбец 0: Сотрудник (всегда)
            name_item = QTableWidgetItem(emp.get('full_name', ''))
            name_item.setData(Qt.UserRole, emp.get('employee_id'))
            table.setItem(row, 0, name_item)

            # Столбец 1: KPI (всегда, цветной, жирный)
            kpi_item = QTableWidgetItem(f"{kpi_total:.0f}%")
            kpi_item.setTextAlignment(Qt.AlignCenter)
            kpi_item.setForeground(QColor(_kpi_color(kpi_total)))
            f = kpi_item.font()
            f.setBold(True)
            kpi_item.setFont(f)
            table.setItem(row, 1, kpi_item)

            # Столбцы 2..N-2: специфичные данные по роли
            # Тренд всегда последний
            col = 2
            for h in headers[2:-1]:  # пропускаем Сотрудник, KPI и Тренд
                col = headers.index(h)
                self._fill_role_cell(table, row, col, h, emp, role_code, pt_code)

            # Последний столбец: Тренд (всегда)
            trend_col = len(headers) - 1
            trend_code = emp.get('trend', 'stable')
            trend_text = TREND_ICONS.get(trend_code, '—')
            trend_item = QTableWidgetItem(trend_text)
            trend_item.setTextAlignment(Qt.AlignCenter)
            if trend_code == 'up':
                trend_item.setForeground(QColor(KPI_COLORS['excellent']))
            elif trend_code == 'down':
                trend_item.setForeground(QColor(KPI_COLORS['critical']))
            table.setItem(row, trend_col, trend_item)

        # Автовысота таблицы (убираем внутренний скролл)
        row_h = table.verticalHeader().defaultSectionSize()
        header_h = table.horizontalHeader().height()
        total_h = header_h + row_h * max(len(employees), 1) + 4
        table.setFixedHeight(min(total_h, 500))

        # ── 3 графика сравнения по роли ──────────────────────────
        self._update_role_charts(project_type, role_code, data)

    def _fill_role_cell(self, table, row, col, header, emp, role_code, pt_code):
        """Заполняет ячейку таблицы в зависимости от заголовка столбца."""
        # Карта заголовок → (ключ_данных, формат)
        if header == 'В срок':
            self._set_pct_cell(table, row, col, emp.get('k_deadline'))
        elif header == 'Просрочки':
            val = emp.get('stages_overdue', 0) or 0
            item = QTableWidgetItem(str(val))
            item.setTextAlignment(Qt.AlignCenter)
            if val > 0:
                item.setForeground(QColor(KPI_COLORS['critical']))
            table.setItem(row, col, item)
        elif header == 'Ср.просрочка (дн.)':
            val = emp.get('avg_overdue_days', 0) or 0
            item = QTableWidgetItem(f"{val:.1f}" if val else '0')
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Правки':
            item = QTableWidgetItem(str(emp.get('revision_count', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Нагрузка':
            concurrent = emp.get('concurrent_projects', 0) or 0
            max_load = emp.get('recommended_max', '?')
            item = QTableWidgetItem(f"{concurrent}/{max_load}")
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'NPS':
            nps = emp.get('k_nps')
            item = QTableWidgetItem(f"{nps:.0f}" if nps is not None else '—')
            item.setTextAlignment(Qt.AlignCenter)
            if nps is not None:
                item.setForeground(QColor(_kpi_color(nps)))
            table.setItem(row, col, item)
        elif header == 'Проектов':
            item = QTableWidgetItem(str(emp.get('concurrent_projects', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Сдано':
            item = QTableWidgetItem(str(emp.get('stages_completed', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Расторг.':
            item = QTableWidgetItem(str(emp.get('terminated_count', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Стадий':
            item = QTableWidgetItem(str(emp.get('stages_completed', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Площадь (м²)':
            area = emp.get('total_area', 0) or 0
            item = QTableWidgetItem(f"{area:.0f}" if area else '—')
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Замеров':
            item = QTableWidgetItem(str(emp.get('stages_completed', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Ср. дней':
            val = emp.get('avg_overdue_days', 0) or 0
            item = QTableWidgetItem(f"{val:.1f}" if val else '—')
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == 'Закупки':
            self._set_pct_cell(table, row, col, emp.get('k_deadline'))
        elif header == 'Дефекты':
            self._set_pct_cell(table, row, col, emp.get('k_quality'))
        elif header in ('Визиты', ):
            self._set_pct_cell(table, row, col, emp.get('k_speed'))
        elif header == 'Экономия':
            val = emp.get('budget_savings', 0) or 0
            item = QTableWidgetItem(f"{val:,.0f}" if val else '—')
            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            table.setItem(row, col, item)
        elif header == 'Ведёт':
            item = QTableWidgetItem(str(emp.get('concurrent_projects', 0) or 0))
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)
        elif header == '% устр.':
            self._set_pct_cell(table, row, col, emp.get('k_quality'))
        else:
            item = QTableWidgetItem('—')
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row, col, item)

    def _update_role_charts(self, project_type, role_code, data):
        """Обновляет 3 графика сравнения по роли."""
        if not MATPLOTLIB_AVAILABLE:
            return
        container = self._get_container(project_type)
        employees = data.get('employees', [])
        kpi_monthly = data.get('kpi_monthly', [])

        # 1. Сравнение KPI (горизонтальные бары)
        kpi_chart = container.findChild(
            HorizontalBarWidget, f'role_kpi_chart_{project_type}_{role_code}')
        if kpi_chart and employees:
            names = [e.get('full_name', '')[:20] for e in employees]
            kpis = [e.get('kpi_total', 0) or 0 for e in employees]
            colors = [_kpi_color(k) for k in kpis]
            kpi_chart.set_data(names, kpis, colors)

        # 2. В срок / Просрочки (stacked bar)
        ontime_chart = container.findChild(
            StackedBarChartWidget, f'role_ontime_chart_{project_type}_{role_code}')
        if ontime_chart and employees:
            names = [e.get('full_name', '')[:15] for e in employees]
            on_time_vals = [e.get('stages_on_time', 0) for e in employees]
            overdue_vals = [e.get('stages_overdue', 0) for e in employees]
            series = [
                {'label': 'В срок', 'values': on_time_vals, 'color': '#7ED321'},
                {'label': 'Просрочки', 'values': overdue_vals, 'color': '#E74C3C'},
            ]
            ontime_chart.set_data(names, series, stacked=True)

        # 3. Динамика по месяцам (линейный)
        dynamics_chart = container.findChild(
            LineChartWidget, f'role_dynamics_chart_{project_type}_{role_code}')
        if dynamics_chart and kpi_monthly:
            months = [m.get('month', '') for m in kpi_monthly]
            avg_vals = [m.get('avg_kpi', 0) or 0 for m in kpi_monthly]
            series = [{'x': months, 'y': avg_vals, 'label': 'Средний KPI роли', 'color': '#4A90D9'}]
            dynamics_chart.set_data(series)

    def _update_detail_card_in_widget(self, widget, pt_code, detail):
        """Рисует детальную карточку в произвольном виджете (для self-профиля)."""
        layout = widget.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        # pt_code → project_type name для поиска
        rev_map = {'individual': 'Индивидуальный', 'template': 'Шаблонный',
                   'supervision': 'Авторский надзор'}
        project_type = rev_map.get(pt_code, 'Индивидуальный')
        self._fill_detail_layout(layout, project_type, detail)

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
        self._fill_detail_layout(layout, project_type, detail)

    def _fill_detail_layout(self, layout, project_type, detail):
        """Заполняет layout детальной карточки — общая логика для full и self режимов."""
        emp = detail['employee']
        kpi = detail.get('kpi', {})
        metrics = detail.get('metrics', {})
        projects = detail.get('projects', [])
        reviews = detail.get('client_reviews', [])
        trend = detail.get('kpi_monthly', [])

        pt_code = PROJECT_TYPE_MAP.get(project_type, 'individual')
        is_supervision = (pt_code == 'supervision')

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
        if is_supervision:
            components = [
                ('KPI надзора', kpi.get('total')),
                ('Закупки в срок', kpi.get('k_deadline')),
                ('Дефекты', kpi.get('k_quality')),
                ('Визиты', kpi.get('k_speed')),
                ('Экономия', f"{metrics.get('budget_savings', 0):,.0f}"),
                ('NPS', kpi.get('k_nps')),
            ]
        else:
            components = [
                ('Выполнение в срок', kpi.get('k_deadline')),
                ('Качество', kpi.get('k_quality')),
                ('Скорость', kpi.get('k_speed')),
                ('NPS', kpi.get('k_nps')),
                ('Нагрузка', f"{metrics.get('concurrent_projects', 0)}/{metrics.get('recommended_max_load', '?')}"),
                ('Зарплата', f"{metrics.get('total_salary', 0):,.0f}"),
            ]
        for col, (label, val) in enumerate(components):
            if isinstance(val, str):
                text = val
            elif val is not None:
                text = f"{val:.0f}%"
            else:
                text = '—'
            color = _kpi_color(val) if isinstance(val, (int, float)) else '#333'
            w = self._create_mini_card(label, text, color)
            kpi_grid.addWidget(w, 0, col)

        kpi_w = QWidget()
        kpi_w.setLayout(kpi_grid)
        layout.addWidget(kpi_w)

        # 4 графика детальной карточки (согласно руководству)
        if MATPLOTLIB_AVAILABLE:
            charts_row1 = QHBoxLayout()
            charts_row2 = QHBoxLayout()

            # 1. Динамика KPI (линейный)
            kpi_dynamics = LineChartWidget('Динамика KPI')
            kpi_dynamics.setFixedHeight(240)
            if trend:
                months = [t.get('month', '') for t in trend[-12:]]
                kpi_vals = [t.get('kpi_total', 0) or 0 for t in trend[-12:]]
                kpi_dynamics.set_data([{
                    'x': months, 'y': kpi_vals,
                    'label': 'KPI', 'color': '#4A90D9',
                }])
            charts_row1.addWidget(kpi_dynamics)

            # 2. Просрочки по стадиям (stacked bar)
            stages_breakdown = detail.get('stages_breakdown', [])
            stages_chart = StackedBarChartWidget('Стадии: в срок / просрочки')
            stages_chart.setFixedHeight(240)
            if stages_breakdown:
                stage_names = [s.get('stage', '')[:15] for s in stages_breakdown]
                on_time_vals = [s.get('on_time', 0) for s in stages_breakdown]
                overdue_vals = [s.get('overdue', 0) for s in stages_breakdown]
                stages_chart.set_data(stage_names, [
                    {'label': 'В срок', 'values': on_time_vals, 'color': '#7ED321'},
                    {'label': 'Просрочки', 'values': overdue_vals, 'color': '#E74C3C'},
                ], stacked=True)
            charts_row1.addWidget(stages_chart)

            # 3. Нагрузка по месяцам (линейный)
            load_monthly = detail.get('load_monthly', [])
            load_chart = LineChartWidget('Нагрузка по месяцам')
            load_chart.setFixedHeight(240)
            if load_monthly:
                l_months = [m.get('month', '') for m in load_monthly]
                l_vals = [m.get('concurrent_projects', 0) for m in load_monthly]
                load_chart.set_data([{
                    'x': l_months, 'y': l_vals,
                    'label': 'Проектов', 'color': '#F5A623',
                }])
            charts_row2.addWidget(load_chart)

            # 4. Распределение KPI-компонентов (bar)
            kpi_components_chart = StackedBarChartWidget('Компоненты KPI')
            kpi_components_chart.setFixedHeight(240)
            if kpi:
                if is_supervision:
                    comp_names = ['Закупки', 'Дефекты', 'Визиты', 'NPS']
                    comp_vals = [
                        kpi.get('k_deadline', 0) or 0, kpi.get('k_quality', 0) or 0,
                        kpi.get('k_speed', 0) or 0, kpi.get('k_nps', 0) or 0,
                    ]
                else:
                    comp_names = ['Сроки', 'Качество', 'Скорость', 'NPS']
                    comp_vals = [
                        kpi.get('k_deadline', 0) or 0, kpi.get('k_quality', 0) or 0,
                        kpi.get('k_speed', 0) or 0, kpi.get('k_nps', 0) or 0,
                    ]
                colors = [_kpi_color(v) for v in comp_vals]
                kpi_components_chart.set_data(comp_names, [
                    {'label': 'Значение', 'values': comp_vals, 'color': '#4A90D9'},
                ], stacked=False)
            charts_row2.addWidget(kpi_components_chart)

            charts_w1 = QWidget()
            charts_w1.setLayout(charts_row1)
            layout.addWidget(charts_w1)
            charts_w2 = QWidget()
            charts_w2.setLayout(charts_row2)
            layout.addWidget(charts_w2)

        # Таблица проектов (расширенная по руководству)
        if projects:
            proj_group = QGroupBox(f'Проекты ({len(projects)})')
            proj_layout = QVBoxLayout()
            proj_table = QTableWidget()
            apply_no_focus_delegate(proj_table)
            proj_table.setStyleSheet(TABLE_STYLE)

            if is_supervision:
                cols = ['Договор', 'Адрес', 'Статус', 'Стадий',
                        'Дефектов', 'Визитов', 'Экономия', 'NPS']
            else:
                cols = ['Договор', 'Адрес', 'Стадия', 'Назначен', 'Дедлайн',
                        'Завершён', 'Отклонение', 'Правки', 'Статус', 'NPS']

            proj_table.setColumnCount(len(cols))
            proj_table.setHorizontalHeaderLabels(cols)
            proj_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            proj_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            for c in range(2, len(cols)):
                proj_table.horizontalHeader().setSectionResizeMode(
                    c, QHeaderView.ResizeToContents)
            proj_table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
            proj_table.verticalHeader().setDefaultSectionSize(28)
            proj_table.setRowCount(len(projects))
            proj_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            proj_table.setFixedHeight(
                min(300, proj_table.horizontalHeader().height() + len(projects) * 28 + 4))

            for row, p in enumerate(projects):
                proj_table.setItem(row, 0, QTableWidgetItem(
                    str(p.get('contract_number', ''))))
                proj_table.setItem(row, 1, QTableWidgetItem(
                    p.get('address', '')))

                if is_supervision:
                    proj_table.setItem(row, 2, QTableWidgetItem(
                        p.get('status', '')))
                    proj_table.setItem(row, 3, QTableWidgetItem(
                        str(p.get('stages_completed', 0))))
                    proj_table.setItem(row, 4, QTableWidgetItem(
                        str(p.get('defects_found', 0))))
                    proj_table.setItem(row, 5, QTableWidgetItem(
                        str(p.get('visits', 0))))
                    proj_table.setItem(row, 6, QTableWidgetItem(
                        f"{p.get('budget_savings', 0):,.0f}"))
                    nps = p.get('nps_score')
                    proj_table.setItem(row, 7, QTableWidgetItem(
                        str(nps) if nps is not None else '—'))
                else:
                    proj_table.setItem(row, 2, QTableWidgetItem(
                        p.get('current_stage', p.get('stage_name', ''))))
                    proj_table.setItem(row, 3, QTableWidgetItem(
                        p.get('assigned_date', '') or ''))
                    proj_table.setItem(row, 4, QTableWidgetItem(
                        p.get('deadline', '') or ''))
                    proj_table.setItem(row, 5, QTableWidgetItem(
                        p.get('completed_date', '') or ''))
                    deviation = p.get('deviation_days')
                    dev_item = QTableWidgetItem(
                        str(deviation) if deviation else '—')
                    dev_item.setTextAlignment(Qt.AlignCenter)
                    if deviation and deviation > 0:
                        dev_item.setForeground(QColor(KPI_COLORS['critical']))
                    proj_table.setItem(row, 6, dev_item)
                    proj_table.setItem(row, 7, QTableWidgetItem(
                        str(p.get('revision_count', 0))))
                    proj_table.setItem(row, 8, QTableWidgetItem(
                        p.get('status', '')))
                    nps = p.get('nps_score')
                    proj_table.setItem(row, 9, QTableWidgetItem(
                        str(nps) if nps is not None else '—'))

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

        # Тренд KPI (последние 6 месяцев)
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
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ══════════════════════════════════════════════════════════════════

    @staticmethod
    def _set_pct_cell(table, row, col, value):
        """Ячейка с процентом и цветовой кодировкой."""
        text = f"{value:.0f}%" if value is not None else '—'
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        if value is not None:
            item.setForeground(QColor(_kpi_color(value)))
        table.setItem(row, col, item)

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
        val.setStyleSheet(
            'font-size: 16px; font-weight: bold; color: #333; border: none;')
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
    def _create_mini_card(label, value, color='#333'):
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
        val.setStyleSheet(
            f'font-size: 13px; font-weight: bold; color: {color}; border: none;')
        val.setAlignment(Qt.AlignCenter)
        layout.addWidget(val)
        return card

    # ══════════════════════════════════════════════════════════════════
    # ЭКСПОРТ PDF
    # ══════════════════════════════════════════════════════════════════

    def _export_to_pdf(self):
        """Экспорт текущего вида в PDF (pixel-perfect скриншоты секций)."""
        try:
            from datetime import datetime
            from utils.pdf_utils import (
                register_fonts, make_page_footer,
                grab_widget_png, fit_image, open_file,
            )
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import mm
            from utils.resource_path import resource_path
            import os

            date_str = datetime.now().strftime('%d.%m.%Y')
            default_name = f'Отчеты по сотрудникам от {date_str}'

            filename, _ = QFileDialog.getSaveFileName(
                self, 'Сохранить отчёт', default_name, 'PDF файлы (*.pdf)')
            if not filename:
                return

            font_name, font_bold = register_fonts()
            page_size = landscape(A4)
            MARGIN_LR = 10 * mm
            MARGIN_TOP = 8 * mm
            MARGIN_BOT = 12 * mm
            PAGE_W_MM = (page_size[0] - 2 * MARGIN_LR) / mm
            RENDER_SCALE = 3.0

            doc = SimpleDocTemplate(
                filename, pagesize=page_size,
                leftMargin=MARGIN_LR, rightMargin=MARGIN_LR,
                topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOT,
            )

            style_title = ParagraphStyle(
                'EmpTitle', fontName=font_bold, fontSize=16,
                textColor=colors.HexColor('#333333'),
                alignment=1, spaceAfter=2 * mm,
            )
            style_sub = ParagraphStyle(
                'EmpSub', fontName=font_name, fontSize=8,
                textColor=colors.HexColor('#666666'),
                alignment=1, spaceAfter=3 * mm,
                backColor=colors.HexColor('#F8F9FA'),
            )

            footer_cb = make_page_footer(page_size, font_name)
            elements = []

            # Логотип
            logo_path = resource_path('resources/logo_pdf.png')
            if not os.path.exists(logo_path):
                logo_path = resource_path('resources/logo.png')
            if os.path.exists(logo_path):
                try:
                    from reportlab.platypus import Image as RLImage
                    logo = RLImage(logo_path, width=35 * mm, height=20 * mm,
                                   kind='proportional')
                    logo.hAlign = 'CENTER'
                    elements.append(logo)
                    elements.append(Spacer(1, 4 * mm))
                except Exception:
                    pass

            elements.append(Paragraph('ОТЧЁТЫ ПО СОТРУДНИКАМ', style_title))
            elements.append(Spacer(1, 2 * mm))

            # Определяем текущий контекст
            if self.access_level == 'self':
                elements.append(Paragraph(
                    f'<b>Режим:</b> Моя статистика | '
                    f'<b>Дата:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}',
                    style_sub))
                elements.append(Spacer(1, 4 * mm))

                # Захват карточки «свой профиль»
                result = grab_widget_png(self._self_detail_content, RENDER_SCALE)
                if result:
                    buf, w_px, h_px = result
                    img = fit_image(buf, w_px, h_px, PAGE_W_MM, 180)
                    img.hAlign = 'CENTER'
                    elements.append(img)
            else:
                # Полный вид — захват текущей вкладки проекта
                idx = self.report_tabs.currentIndex()
                tab_name = self.report_tabs.tabText(idx)
                elements.append(Paragraph(
                    f'<b>Тип проекта:</b> {tab_name} | '
                    f'<b>Дата:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}',
                    style_sub))
                elements.append(Spacer(1, 4 * mm))

                current_tab = self.report_tabs.currentWidget()
                if current_tab:
                    # Внутри QScrollArea — контейнер
                    inner = current_tab.widget() if hasattr(current_tab, 'widget') else current_tab
                    if inner:
                        result = grab_widget_png(inner, RENDER_SCALE)
                        if result:
                            buf, w_px, h_px = result
                            max_h = max(300, PAGE_W_MM * (h_px / w_px) if w_px > 0 else 300)
                            img = fit_image(buf, w_px, h_px, PAGE_W_MM, max_h)
                            img.hAlign = 'CENTER'
                            elements.append(img)

            if len(elements) <= 3:  # Только заголовок + spacers — нет контента
                try:
                    from ui.custom_message_box import CustomMessageBox
                    CustomMessageBox(self, 'Внимание', 'Нет данных для экспорта. Загрузите отчёт.', 'warning').exec_()
                except Exception:
                    pass
                return

            doc.build(elements,
                      onFirstPage=footer_cb,
                      onLaterPages=footer_cb)

            open_file(filename)
            logger.info(f'PDF экспорт: {filename}')

        except Exception as e:
            logger.error(f'Ошибка экспорта PDF: {e}', exc_info=True)
            try:
                from ui.custom_message_box import CustomMessageBox
                CustomMessageBox(self, 'Ошибка', f'Не удалось создать PDF: {e}', 'error').exec_()
            except Exception:
                pass
