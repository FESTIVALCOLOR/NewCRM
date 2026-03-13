# -*- coding: utf-8 -*-
"""
Страница Отчёты и Статистика — полная аналитика по клиентам, договорам и CRM.

Архитектура: QScrollArea с последовательными секциями вместо QTabWidget.
Загрузка данных — через DataAccess (API-first с fallback на локальную SQLite).
Обновление UI — строго в главном потоке через QTimer.singleShot(0, ...).
"""

import logging
import threading
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea, QLabel,
    QComboBox, QPushButton, QGridLayout, QTabWidget, QFrame,
    QFileDialog, QSizePolicy, QLayout
)
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QRect, QSize, QPoint
from PyQt5.QtGui import QFont

from ui.custom_message_box import CustomMessageBox
from ui.dashboard_widget import KPICard, MiniKPICard
from ui.chart_widget import (
    SectionWidget, LineChartWidget, StackedBarChartWidget,
    HorizontalBarWidget, FunnelBarChart, ProjectTypePieChart
)
from utils.data_access import DataAccess
from utils.resource_path import resource_path
from utils.pdf_utils import (
    register_fonts, make_page_footer, pdf_section_header,
    grab_widget_png, chart_to_png, fit_image, open_file,
)

logger = logging.getLogger(__name__)


class FlowLayout(QLayout):
    """Адаптивный layout — виджеты переносятся на следующую строку при нехватке ширины"""

    def __init__(self, parent=None, spacing=8):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._do_layout(QRect(0, 0, width, 0), test_only=True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._do_layout(rect, test_only=False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        size += QSize(m.left() + m.right(), m.top() + m.bottom())
        return size

    def _do_layout(self, rect, test_only):
        """Раскладка с растяжкой: элементы заполняют всю ширину ряда"""
        if not self._items:
            return 0

        spacing = self._spacing
        available_w = rect.width()

        # Разбиваем элементы на ряды по минимальной ширине
        rows = []
        current_row = []
        row_natural_w = 0

        for item in self._items:
            item_w = item.sizeHint().width()
            needed = row_natural_w + item_w + (spacing if current_row else 0)

            if current_row and needed > available_w:
                rows.append(current_row)
                current_row = [item]
                row_natural_w = item_w
            else:
                current_row.append(item)
                row_natural_w = needed

        if current_row:
            rows.append(current_row)

        # Раскладываем ряды, растягивая элементы на всю ширину
        y = rect.y()
        for row in rows:
            n = len(row)
            total_spacing = spacing * (n - 1)
            per_item_w = (available_w - total_spacing) // n if n else 0

            line_height = 0
            x = rect.x()
            for i, item in enumerate(row):
                h = item.sizeHint().height()
                # Последний элемент забирает остаток ширины (компенсация округления)
                w = per_item_w if i < n - 1 else (rect.x() + available_w - x)
                if not test_only:
                    item.setGeometry(QRect(QPoint(x, y), QSize(w, h)))
                x += w + spacing
                line_height = max(line_height, h)

            y += line_height + spacing

        return y - spacing - rect.y()


class ReportsTab(QWidget):
    """Страница Отчёты и Статистика — полная аналитика по клиентам, договорам и CRM"""

    data_loaded = pyqtSignal()  # Сигнал завершения загрузки данных

    def __init__(self, employee, api_client=None):
        super().__init__()
        self.employee = employee
        self.api_client = api_client
        self.data_access = DataAccess(api_client=api_client)
        self._data_loaded = False
        self._loading = False

        # Кеш для данных
        self._cache = {}

        # KPI карточки (динамические по агентам)
        self._kpi_cards = {}
        self._agent_kpi_cards = []

        self.init_ui()

    def init_ui(self):
        """Инициализация интерфейса"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Секция 0: Глобальные фильтры (sticky сверху)
        self._create_filter_bar(main_layout)

        # Скролл-область для всех аналитических секций
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setStyleSheet("QScrollArea { background: #F8F9FA; border: none; }")

        scroll_content = QWidget()
        self.sections_layout = QVBoxLayout(scroll_content)
        self.sections_layout.setContentsMargins(16, 16, 16, 16)
        self.sections_layout.setSpacing(16)

        # Секции (ссылки для PDF-экспорта скриншотами)
        self._pdf_sections = []

        # Секция 1: KPI-карточки
        self._create_kpi_section()

        # Секция 2: Клиенты
        self._create_clients_section()

        # Секция 3: Договоры
        self._create_contracts_section()

        # Секция 4: CRM аналитика
        self._create_crm_section()

        # Секция 5: Авторский надзор
        self._create_supervision_section()

        self.sections_layout.addStretch()
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)

    # ===================================================================
    # СЕКЦИЯ 0: ФИЛЬТРЫ
    # ===================================================================

    def _create_filter_bar(self, parent_layout):
        """Создать панель глобальных фильтров (sticky сверху)"""
        filter_frame = QFrame()
        filter_frame.setStyleSheet(
            "QFrame { background: #FFFFFF; border-bottom: 1px solid #E0E0E0; }"
        )
        layout = QHBoxLayout(filter_frame)
        layout.setContentsMargins(16, 8, 16, 8)
        layout.setSpacing(12)

        # Заголовок страницы
        title = QLabel("Отчёты и Статистика")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #333333; border: none; background: transparent;")
        layout.addWidget(title)
        layout.addStretch()

        # ComboBox фильтры
        self.filter_year = self._create_filter_combo("Год", layout)
        self.filter_quarter = self._create_filter_combo(
            "Квартал", layout, ["Все", "Q1", "Q2", "Q3", "Q4"]
        )
        self.filter_month = self._create_filter_combo("Месяц", layout, [
            "Все", "Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
            "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"
        ])
        self.filter_agent = self._create_filter_combo("Тип агента", layout)
        self.filter_city = self._create_filter_combo("Город", layout)
        self.filter_project_type = self._create_filter_combo("Тип проекта", layout, [
            "Все", "Индивидуальный", "Шаблонный"
        ])

        # Кнопка сброса фильтров — выровнена по нижнему краю с комбобоксами
        btn_reset = QPushButton("Сбросить")
        btn_reset.setFixedHeight(26)
        btn_reset.setStyleSheet("""
            QPushButton {
                background: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 0 14px;
                color: #333;
                font-size: 12px;
            }
            QPushButton:hover { background: #E0E0E0; }
        """)
        btn_reset.clicked.connect(self.reset_filters)
        layout.addWidget(btn_reset, 0, Qt.AlignBottom)

        # Кнопка экспорта в PDF
        btn_export = QPushButton("Экспорт PDF")
        btn_export.setFixedHeight(26)
        btn_export.setStyleSheet("""
            QPushButton {
                background: #ffd93c;
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 0 14px;
                color: #333;
                font-weight: bold;
                font-size: 12px;
            }
            QPushButton:hover { background: #ffce00; }
        """)
        btn_export.clicked.connect(self.export_to_pdf)
        layout.addWidget(btn_export, 0, Qt.AlignBottom)

        parent_layout.addWidget(filter_frame)

        # Подключить сигналы всех фильтров
        for combo in [self.filter_year, self.filter_quarter, self.filter_month,
                      self.filter_agent, self.filter_city, self.filter_project_type]:
            combo.currentTextChanged.connect(self._on_filter_changed)

    def _create_filter_combo(self, label_text, layout, items=None):
        """Создать ComboBox фильтра с подписью сверху"""
        frame = QFrame()
        frame.setStyleSheet("border: none; background: transparent;")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(0, 0, 0, 0)
        fl.setSpacing(2)

        lbl = QLabel(label_text)
        lbl.setStyleSheet("font-size: 9px; color: #999; border: none; background: transparent;")
        fl.addWidget(lbl)

        combo = QComboBox()
        combo.setMinimumWidth(110)
        combo.setStyleSheet("""
            QComboBox {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                padding: 4px 8px;
                background: white;
                font-size: 11px;
            }
            QComboBox:hover { border-color: #ffd93c; }
            QComboBox::drop-down { border: none; }
        """)
        if items:
            combo.addItems(items)
        fl.addWidget(combo)
        layout.addWidget(frame)
        return combo

    # ===================================================================
    # СЕКЦИЯ 1: KPI-КАРТОЧКИ
    # ===================================================================

    def _create_kpi_section(self):
        """Создать секцию KPI-карточек с FlowLayout для адаптивного распределения"""
        section = SectionWidget("Ключевые показатели", "Сводные KPI-метрики за выбранный период")

        self.kpi_layout = QVBoxLayout()
        self.kpi_layout.setSpacing(8)

        # Все фиксированные KPI-карточки в один FlowLayout — адаптивная раскладка
        self.kpi_flow = FlowLayout(spacing=8)
        self._kpi_cards["total_clients"] = self._make_kpi("Всего клиентов", "users", "#2196F3")
        self._kpi_cards["new_clients"] = self._make_kpi("Новых клиентов", "user-plus", "#4CAF50")
        self._kpi_cards["returning_clients"] = self._make_kpi("Повторных клиентов", "users", "#9C27B0")
        self._kpi_cards["total_contracts"] = self._make_kpi("Всего договоров", "clipboard1", "#FF9800")
        self._kpi_cards["total_amount"] = self._make_kpi("Общая стоимость", "money", "#F57C00")
        self._kpi_cards["avg_amount"] = self._make_kpi("Средний чек", "trending-up", "#E91E63")
        self._kpi_cards["total_area"] = self._make_kpi("Общая площадь", "codepen1", "#00BCD4")
        self._kpi_cards["avg_area"] = self._make_kpi("Средняя площадь", "codepen2", "#607D8B")
        for key in ["total_clients", "new_clients", "returning_clients",
                     "total_contracts", "total_amount", "avg_amount",
                     "total_area", "avg_area"]:
            self.kpi_flow.addWidget(self._kpi_cards[key])

        kpi_flow_widget = QWidget()
        kpi_flow_widget.setLayout(self.kpi_flow)
        self.kpi_layout.addWidget(kpi_flow_widget)

        # Динамические карточки по агентам — тоже FlowLayout
        self.kpi_agents_clients_layout = FlowLayout(spacing=8)
        self.kpi_agents_contracts_layout = FlowLayout(spacing=8)
        self.kpi_agents_area_layout = FlowLayout(spacing=8)

        for flow_lo in [self.kpi_agents_clients_layout,
                        self.kpi_agents_contracts_layout,
                        self.kpi_agents_area_layout]:
            w = QWidget()
            w.setLayout(flow_lo)
            self.kpi_layout.addWidget(w)

        kpi_widget = QWidget()
        kpi_widget.setLayout(self.kpi_layout)
        section.add_widget(kpi_widget)
        self.sections_layout.addWidget(section)
        self._pdf_sections.append(section)

    def _make_kpi(self, title, icon_name, color):
        """Создать KPI-карточку со значением-заглушкой"""
        card = KPICard(title=title, icon_name=icon_name, border_color=color)
        card.set_value("—")
        return card

    # ===================================================================
    # СЕКЦИЯ 2: КЛИЕНТЫ
    # ===================================================================

    def _create_clients_section(self):
        """Создать секцию аналитики клиентов"""
        section = SectionWidget("Клиенты", "Статистика по клиентской базе")

        # Мини-дашборд: FlowLayout для адаптивного распределения
        mini_flow = FlowLayout(spacing=8)
        self._mini_clients = {}
        items = [
            ("total", "Всего", "#2196F3"),
            ("individual", "Физлица", "#4CAF50"),
            ("legal", "Юрлица", "#FF9800"),
            ("new", "Новых", "#9C27B0"),
            ("returning", "Повторных", "#E91E63"),
            ("from_agents", "От агентов", "#00BCD4"),
        ]
        for key, title, color in items:
            card = MiniKPICard(title=title, border_color=color)
            card.set_value("—")
            self._mini_clients[key] = card
            mini_flow.addWidget(card)
        mini_flow_w = QWidget()
        mini_flow_w.setLayout(mini_flow)
        section.add_widget(mini_flow_w)

        # Графики 2x2 с равными колонками
        grid = QGridLayout()
        grid.setSpacing(12)

        self.chart_clients_dynamics = LineChartWidget("Динамика новых клиентов")
        self.chart_clients_types = ProjectTypePieChart()
        self.chart_clients_by_agent = HorizontalBarWidget("Клиенты по агентам")
        self.chart_clients_new_vs_returning = StackedBarChartWidget("Новые vs Повторные")

        grid.addWidget(self.chart_clients_dynamics, 0, 0)
        grid.addWidget(self.chart_clients_types, 0, 1)
        grid.addWidget(self.chart_clients_by_agent, 1, 0)
        grid.addWidget(self.chart_clients_new_vs_returning, 1, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)

        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        section.add_widget(grid_widget)
        self.sections_layout.addWidget(section)
        self._pdf_sections.append(section)

    # ===================================================================
    # СЕКЦИЯ 3: ДОГОВОРЫ
    # ===================================================================

    def _create_contracts_section(self):
        """Создать секцию аналитики договоров"""
        section = SectionWidget("Договоры", "Статистика по договорам и финансам")

        # Мини-дашборд: FlowLayout для адаптивного распределения
        mini_flow = FlowLayout(spacing=8)
        self._mini_contracts = {}
        items = [
            ("total", "Всего", "#FF9800"),
            ("individual", "Индивидуальных", "#F57C00"),
            ("template", "Шаблонных", "#C62828"),
            ("amount", "Стоимость", "#F57C00"),
            ("avg", "Средний чек", "#E91E63"),
        ]
        for key, title, color in items:
            card = MiniKPICard(title=title, border_color=color)
            card.set_value("—")
            self._mini_contracts[key] = card
            mini_flow.addWidget(card)
        mini_flow_w = QWidget()
        mini_flow_w.setLayout(mini_flow)
        section.add_widget(mini_flow_w)

        # Графики 3x2 с равными колонками
        grid = QGridLayout()
        grid.setSpacing(12)

        self.chart_contracts_dynamics = StackedBarChartWidget("Договоры по месяцам")
        self.chart_contracts_amount = LineChartWidget("Стоимость по месяцам")
        self.chart_contracts_types = ProjectTypePieChart()
        self.chart_contracts_cities = HorizontalBarWidget("ТОП городов")
        self.chart_contracts_by_agent = StackedBarChartWidget("Договоры по агентам")
        self.chart_contracts_amount_by_agent = HorizontalBarWidget("Стоимость по агентам")

        grid.addWidget(self.chart_contracts_dynamics, 0, 0)
        grid.addWidget(self.chart_contracts_amount, 0, 1)
        grid.addWidget(self.chart_contracts_types, 1, 0)
        grid.addWidget(self.chart_contracts_cities, 1, 1)
        grid.addWidget(self.chart_contracts_by_agent, 2, 0)
        grid.addWidget(self.chart_contracts_amount_by_agent, 2, 1)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 1)

        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        section.add_widget(grid_widget)
        self.sections_layout.addWidget(section)
        self._pdf_sections.append(section)

    # ===================================================================
    # СЕКЦИЯ 4: CRM АНАЛИТИКА
    # ===================================================================

    def _create_crm_section(self):
        """Создать секцию CRM-аналитики с подвкладками по типам проектов"""
        section = SectionWidget("CRM Аналитика", "Воронка продаж, сроки и просрочки")

        # QTabWidget: Индивидуальные / Шаблонные
        self.crm_tabs = QTabWidget()
        self.crm_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E0E0E0;
                border-radius: 4px;
                background: white;
            }
            QTabBar::tab {
                padding: 8px 20px;
                font-size: 12px;
            }
            QTabBar::tab:selected {
                background: #ffd93c;
                border-bottom: 2px solid #F57C00;
                font-weight: bold;
            }
            QTabBar::tab:!selected {
                background: #F5F5F5;
            }
        """)

        self._crm_individual = self._create_crm_subtab("Индивидуальный")
        self._crm_template = self._create_crm_subtab("Шаблонный")

        self.crm_tabs.addTab(self._crm_individual["widget"], "Индивидуальные проекты")
        self.crm_tabs.addTab(self._crm_template["widget"], "Шаблонные проекты")

        section.add_widget(self.crm_tabs)
        self.sections_layout.addWidget(section)
        self._pdf_sections.append(section)

    def _create_crm_subtab(self, project_type):
        """Создать содержимое одной подвкладки CRM"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)
        layout.setContentsMargins(8, 8, 8, 8)

        # Мини-KPI: FlowLayout для адаптивного распределения
        mini_flow = FlowLayout(spacing=8)
        mini_cards = {}
        items = [
            ("on_time_pct", "Проектов в срок", "#4CAF50"),
            ("stages_on_time_pct", "Стадий в срок", "#2196F3"),
            ("avg_deviation", "Ср. отклонение (дни)", "#FF9800"),
            ("paused", "На паузе", "#9E9E9E"),
        ]
        for key, title, color in items:
            card = MiniKPICard(title=title, border_color=color)
            card.set_value("—")
            mini_cards[key] = card
            mini_flow.addWidget(card)
        mini_flow_w = QWidget()
        mini_flow_w.setLayout(mini_flow)
        layout.addWidget(mini_flow_w)

        # Воронка — на всю ширину, фиксированная высота
        funnel = FunnelBarChart()
        funnel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        layout.addWidget(funnel)

        # Время стадий vs норматив — в горизонтальном скролле для большого числа стадий
        stage_duration = StackedBarChartWidget(f"Время стадий vs норматив — {project_type}")
        stage_scroll = QScrollArea()
        stage_scroll.setWidgetResizable(False)
        stage_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        stage_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        stage_scroll.setWidget(stage_duration)
        stage_scroll.setFrameShape(QFrame.NoFrame)
        stage_scroll.setStyleSheet("QScrollArea { background: transparent; border: none; }")
        stage_scroll.setMinimumHeight(480)
        stage_scroll.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        stage_scroll.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        layout.addWidget(stage_scroll)

        # Прижимаем контент к верху — spacer забирает лишнюю высоту
        layout.addStretch(1)

        return {
            "widget": widget,
            "mini_cards": mini_cards,
            "mini_flow_w": mini_flow_w,
            "funnel": funnel,
            "stage_duration": stage_duration,
            "stage_scroll": stage_scroll,
        }

    # ===================================================================
    # СЕКЦИЯ 5: АВТОРСКИЙ НАДЗОР
    # ===================================================================

    def _create_supervision_section(self):
        """Создать секцию авторского надзора"""
        section = SectionWidget("Авторский надзор", "Стадии закупок, бюджет и качество")

        # Мини-дашборд: 4 фиксированных + динамические по агентам — FlowLayout
        self._supervision_mini_bar_layout = FlowLayout(spacing=8)
        self._mini_supervision = {}
        for key, title, color in [
            ("total", "Всего надзоров", "#388E3C"),
            ("active", "Активных", "#4CAF50"),
            ("individual", "По индивид.", "#F57C00"),
            ("template", "По шаблонным", "#C62828"),
        ]:
            card = MiniKPICard(title=title, border_color=color)
            card.set_value("—")
            self._mini_supervision[key] = card
            self._supervision_mini_bar_layout.addWidget(card)
        sv_mini_w = QWidget()
        sv_mini_w.setLayout(self._supervision_mini_bar_layout)
        section.add_widget(sv_mini_w)

        # Графики с равными колонками
        grid = QGridLayout()
        grid.setSpacing(12)

        self.chart_sv_stages = StackedBarChartWidget("12 стадий закупок")
        self.chart_sv_budget = StackedBarChartWidget("Бюджет: план vs факт")
        self.chart_sv_cities = HorizontalBarWidget("Надзоры по городам")
        self.chart_sv_agents = HorizontalBarWidget("Надзоры по агентам")
        self.chart_sv_project_types = ProjectTypePieChart()

        grid.addWidget(self.chart_sv_stages, 0, 0)
        grid.addWidget(self.chart_sv_budget, 0, 1)
        grid.addWidget(self.chart_sv_cities, 1, 0)
        grid.addWidget(self.chart_sv_agents, 1, 1)
        grid.addWidget(self.chart_sv_project_types, 2, 0)

        # Мини-KPI: экономия, дефекты, визиты — вертикально рядом с Pie chart
        self._mini_sv_kpi = {}
        sv_kpi_layout = QVBoxLayout()
        sv_kpi_layout.setSpacing(0)
        sv_kpi_layout.setContentsMargins(0, 0, 0, 0)
        sv_kpi_layout.addStretch(1)
        for key, title, color in [
            ("savings", "Экономия бюджета", "#4CAF50"),
            ("defects", "Дефекты", "#FF9800"),
            ("visits", "Визиты на объект", "#2196F3"),
        ]:
            card = MiniKPICard(title=title, border_color=color)
            card.set_value("—")
            self._mini_sv_kpi[key] = card
            sv_kpi_layout.addWidget(card)
            sv_kpi_layout.addStretch(1)

        sv_kpi_widget = QWidget()
        sv_kpi_widget.setLayout(sv_kpi_layout)
        grid.addWidget(sv_kpi_widget, 2, 1)

        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(0, 1)
        grid.setRowStretch(1, 1)
        grid.setRowStretch(2, 1)

        grid_widget = QWidget()
        grid_widget.setLayout(grid)
        section.add_widget(grid_widget)

        self.sections_layout.addWidget(section)
        self._pdf_sections.append(section)

    # ===================================================================
    # ЗАГРУЗКА ДАННЫХ
    # ===================================================================

    def ensure_data_loaded(self):
        """Ленивая загрузка при первом показе вкладки.
        При повторном переключении — пропускаем если кэш свежий (<30с)."""
        import time as _time
        now = _time.monotonic()
        if not self._loading:
            if not self._data_loaded:
                self._data_loaded = True
                self._last_load_time = now
                self._load_filter_options()
                self.reload_all_sections()
            elif now - getattr(self, '_last_load_time', 0) < 30:
                return
            else:
                self._last_load_time = now
                self.reload_all_sections()

    def _load_filter_options(self):
        """Загрузить опции для ComboBox-фильтров из DataAccess"""
        try:
            years = self.data_access.get_contract_years()
            self.filter_year.blockSignals(True)
            self.filter_year.clear()
            self.filter_year.addItem("Все")
            for y in sorted(years or [], reverse=True):
                self.filter_year.addItem(str(y))
            self.filter_year.blockSignals(False)
        except Exception as e:
            logger.error(f"Ошибка загрузки годов для фильтра: {e}")

        try:
            agents = self.data_access.get_all_agents()
            self.filter_agent.blockSignals(True)
            self.filter_agent.clear()
            self.filter_agent.addItem("Все")
            for a in (agents or []):
                name = a.get("name", "") if isinstance(a, dict) else str(a)
                if name:
                    self.filter_agent.addItem(name)
            self.filter_agent.blockSignals(False)
        except Exception as e:
            logger.error(f"Ошибка загрузки агентов для фильтра: {e}")

        try:
            cities = self.data_access.get_cities()
            self.filter_city.blockSignals(True)
            self.filter_city.clear()
            self.filter_city.addItem("Все")
            for c in (cities or []):
                if c:
                    self.filter_city.addItem(str(c))
            self.filter_city.blockSignals(False)
        except Exception as e:
            logger.error(f"Ошибка загрузки городов для фильтра: {e}")

    def _get_current_filters(self):
        """Собрать словарь текущих значений фильтров"""
        filters = {}

        year_text = self.filter_year.currentText()
        if year_text and year_text != "Все":
            try:
                filters["year"] = int(year_text)
            except ValueError:
                pass

        quarter_text = self.filter_quarter.currentText()
        if quarter_text and quarter_text != "Все":
            try:
                filters["quarter"] = int(quarter_text.replace("Q", ""))
            except ValueError:
                pass

        month_idx = self.filter_month.currentIndex()
        if month_idx > 0:
            filters["month"] = month_idx

        agent_text = self.filter_agent.currentText()
        if agent_text and agent_text != "Все":
            filters["agent_type"] = agent_text

        city_text = self.filter_city.currentText()
        if city_text and city_text != "Все":
            filters["city"] = city_text

        ptype_text = self.filter_project_type.currentText()
        if ptype_text and ptype_text != "Все":
            filters["project_type"] = ptype_text

        return filters

    def _on_filter_changed(self, _text=None):
        """Обработчик изменения любого фильтра"""
        if self._data_loaded:
            self.reload_all_sections()

    def reset_filters(self):
        """Сбросить все фильтры в положение 'Все'"""
        for combo in [self.filter_year, self.filter_quarter, self.filter_month,
                      self.filter_agent, self.filter_city, self.filter_project_type]:
            combo.blockSignals(True)
            combo.setCurrentIndex(0)
            combo.blockSignals(False)
        self.reload_all_sections()

    def reload_all_sections(self):
        """Перезагрузить все секции с текущими фильтрами (фоновый поток)"""
        if self._loading:
            return
        self._loading = True
        filters = self._get_current_filters()

        def _load():
            # Только временные фильтры для CRM и надзора
            time_filters = {
                k: v for k, v in filters.items()
                if k in ("year", "quarter", "month")
            }
            year_filter = filters.get("year")

            def _safe_call(name, func, default=None):
                """Безопасный вызов API — при ошибке возвращает default"""
                try:
                    result = func()
                    logger.info(f"[Reports] {name}: OK, type={type(result).__name__}, "
                                f"len={len(result) if isinstance(result, (dict, list)) else 'N/A'}")
                    return result
                except Exception as e:
                    logger.error(f"[Reports] {name}: ОШИБКА — {e}")
                    return default

            summary = _safe_call("summary",
                lambda: self.data_access.get_reports_summary(**filters), {})
            clients_dyn = _safe_call("clients_dynamics",
                lambda: self.data_access.get_reports_clients_dynamics(year=year_filter), [])
            contracts_dyn = _safe_call("contracts_dynamics",
                lambda: self.data_access.get_reports_contracts_dynamics(
                    year=year_filter,
                    agent_type=filters.get("agent_type"),
                    city=filters.get("city")), [])
            crm_ind = _safe_call("crm_individual",
                lambda: self.data_access.get_reports_crm_analytics(
                    project_type="Индивидуальный", **time_filters), {})
            crm_tmpl = _safe_call("crm_template",
                lambda: self.data_access.get_reports_crm_analytics(
                    project_type="Шаблонный", **time_filters), {})
            sv = _safe_call("supervision",
                lambda: self.data_access.get_reports_supervision_analytics(**time_filters), {})
            dist_agent = _safe_call("dist_agent",
                lambda: self.data_access.get_reports_distribution("agent", **time_filters), [])
            dist_city = _safe_call("dist_city",
                lambda: self.data_access.get_reports_distribution("city", **time_filters), [])

            self._cache = {
                "summary": summary or {},
                "clients_dynamics": clients_dyn or [],
                "contracts_dynamics": contracts_dyn or [],
                "crm_individual": crm_ind or {},
                "crm_template": crm_tmpl or {},
                "supervision": sv or {},
                "dist_agent": dist_agent or [],
                "dist_city": dist_city or [],
            }

            # Обновить UI строго в главном потоке
            QTimer.singleShot(0, self._update_all_ui)

        thread = threading.Thread(target=_load, daemon=True)
        thread.start()

    # ===================================================================
    # ОБНОВЛЕНИЕ UI (только главный поток)
    # ===================================================================

    def _update_all_ui(self):
        """Обновить все виджеты данными из кеша (вызывается в главном потоке)"""
        try:
            self._update_kpi_section()
            self._update_clients_section()
            self._update_contracts_section()
            logger.info("[Reports] KPI/Clients/Contracts updated OK")
        except Exception as e:
            logger.error(f"Ошибка обновления UI (KPI/Clients/Contracts): {e}", exc_info=True)
        try:
            self._update_crm_section()
            logger.info("[Reports] CRM section updated OK")
        except Exception as e:
            logger.error(f"Ошибка обновления UI (CRM): {e}", exc_info=True)
        try:
            self._update_supervision_section()
            logger.info("[Reports] Supervision section updated OK")
        except Exception as e:
            logger.error(f"Ошибка обновления UI (Supervision): {e}", exc_info=True)
        try:
            self._data_loaded = True
            self.data_loaded.emit()
        except Exception as e:
            logger.error(f"Ошибка emit data_loaded: {e}")
        finally:
            self._loading = False

    def _update_kpi_section(self):
        """Обновить KPI-карточки сводных метрик"""
        s = self._cache.get("summary", {})

        # Клиенты
        self._kpi_cards["total_clients"].set_value(str(s.get("total_clients", 0)))
        self._kpi_cards["total_clients"].set_trend(s.get("trend_clients") or 0)
        self._kpi_cards["new_clients"].set_value(str(s.get("new_clients", 0)))
        self._kpi_cards["returning_clients"].set_value(str(s.get("returning_clients", 0)))

        # Договоры
        self._kpi_cards["total_contracts"].set_value(str(s.get("total_contracts", 0)))
        self._kpi_cards["total_contracts"].set_trend(s.get("trend_contracts") or 0)

        amount = s.get("total_amount", 0) or 0
        self._kpi_cards["total_amount"].set_value(
            f"{amount:,.0f}\u00a0руб".replace(",", "\u00a0")
        )
        self._kpi_cards["total_amount"].set_trend(s.get("trend_amount") or 0)

        avg = s.get("avg_amount", 0) or 0
        self._kpi_cards["avg_amount"].set_value(
            f"{avg:,.0f}\u00a0руб".replace(",", "\u00a0")
        )

        # Площадь
        area = s.get("total_area", 0) or 0
        self._kpi_cards["total_area"].set_value(
            f"{area:,.0f}\u00a0м\u00b2".replace(",", "\u00a0")
        )
        avg_area = s.get("avg_area", 0) or 0
        self._kpi_cards["avg_area"].set_value(
            f"{avg_area:,.0f}\u00a0м\u00b2".replace(",", "\u00a0")
        )

        # Динамические карточки по агентам
        by_agent = s.get("by_agent", []) or []
        self._rebuild_agent_kpi_cards(by_agent)

    def _rebuild_agent_kpi_cards(self, by_agent):
        """Пересоздать динамические KPI-карточки по агентам"""
        # Удалить все старые карточки
        for cards_list in self._agent_kpi_cards:
            for card in cards_list:
                if card is not None:
                    card.setParent(None)
                    card.deleteLater()
        self._agent_kpi_cards = []

        # Очистить все три layout-а агентских рядов
        for lo in [self.kpi_agents_clients_layout,
                   self.kpi_agents_contracts_layout,
                   self.kpi_agents_area_layout]:
            while lo.count():
                item = lo.takeAt(0)
                if item is not None:
                    w = item.widget()
                    if w is not None:
                        w.setParent(None)

        clients_cards = []
        contracts_cards = []
        area_cards = []

        for agent in by_agent:
            name = agent.get("agent_name", "")
            color = agent.get("agent_color") or "#607D8B"

            # Клиенты агента
            c1 = KPICard(
                title=f"Клиенты — {name}",
                icon_name="user",
                border_color=color
            )
            c1.set_value(str(agent.get("clients", 0)))
            self.kpi_agents_clients_layout.addWidget(c1)
            clients_cards.append(c1)

            # Договоры агента (кол-во + сумма)
            c2 = KPICard(
                title=f"Договоры — {name}",
                icon_name="clipboard1",
                border_color=color
            )
            contracts_val = agent.get("contracts", 0) or 0
            amount_val = agent.get("amount", 0) or 0
            c2.set_value(
                f"{contracts_val}\u00a0/\u00a0{amount_val:,.0f}\u00a0руб".replace(",", "\u00a0")
            )
            self.kpi_agents_contracts_layout.addWidget(c2)
            contracts_cards.append(c2)

            # Площадь агента
            c3 = KPICard(
                title=f"Площадь — {name}",
                icon_name="codepen1",
                border_color=color
            )
            area_val = agent.get("area", 0) or 0
            c3.set_value(f"{area_val:,.0f}\u00a0м\u00b2".replace(",", "\u00a0"))
            self.kpi_agents_area_layout.addWidget(c3)
            area_cards.append(c3)

        self._agent_kpi_cards = [clients_cards, contracts_cards, area_cards]

    def _update_clients_section(self):
        """Обновить секцию клиентов"""
        s = self._cache.get("summary", {})
        dynamics = self._cache.get("clients_dynamics", [])
        dist_agent = self._cache.get("dist_agent", [])

        # Мини-дашборд
        self._mini_clients["total"].set_value(str(s.get("total_clients", 0)))
        self._mini_clients["new"].set_value(str(s.get("new_clients", 0)))
        self._mini_clients["returning"].set_value(str(s.get("returning_clients", 0)))

        # Физлица и юрлица суммируем из динамики по месяцам
        total_ind = sum(d.get("individual", 0) or 0 for d in dynamics)
        total_legal = sum(d.get("legal", 0) or 0 for d in dynamics)
        self._mini_clients["individual"].set_value(str(total_ind))
        self._mini_clients["legal"].set_value(str(total_legal))

        # Клиенты от агентов (исключая прямые каналы)
        direct_names = {"Прямой", "ФЕСТИВАЛЬ", "Фестиваль", "прямой"}
        agent_clients = sum(
            a.get("count", 0) or 0
            for a in dist_agent
            if a.get("name", "") not in direct_names
        )
        self._mini_clients["from_agents"].set_value(str(agent_clients))

        # Графики
        if dynamics:
            month_labels = self._periods_to_labels([d.get("period", "") for d in dynamics])

            # Линейный график динамики
            self.chart_clients_dynamics.set_data([
                {
                    "label": "Новые",
                    "x": month_labels,
                    "y": [d.get("new_clients", 0) or 0 for d in dynamics],
                    "color": "#4CAF50"
                },
                {
                    "label": "Повторные",
                    "x": month_labels,
                    "y": [d.get("returning_clients", 0) or 0 for d in dynamics],
                    "color": "#9C27B0"
                },
            ])

            # Stacked bar новые vs повторные
            self.chart_clients_new_vs_returning.set_data(
                month_labels,
                [
                    {
                        "label": "Новые",
                        "values": [d.get("new_clients", 0) or 0 for d in dynamics],
                        "color": "#4CAF50"
                    },
                    {
                        "label": "Повторные",
                        "values": [d.get("returning_clients", 0) or 0 for d in dynamics],
                        "color": "#9C27B0"
                    },
                ],
                stacked=True
            )

        # Pie физлица / юрлица
        # Сигнатура: set_data(individual_count, template_count, supervision_count=0)
        # Переиспользуем слоты: физлица=individual, юрлица=template, supervision=0
        if total_ind or total_legal:
            self.chart_clients_types.set_data(total_ind, total_legal, 0)

        # Горизонтальный bar по агентам
        if dist_agent:
            labels = [a.get("name", "") for a in dist_agent]
            values = [a.get("count", 0) or 0 for a in dist_agent]
            self.chart_clients_by_agent.set_data(labels, values)

    def _update_contracts_section(self):
        """Обновить секцию договоров"""
        s = self._cache.get("summary", {})
        dynamics = self._cache.get("contracts_dynamics", [])
        dist_agent = self._cache.get("dist_agent", [])
        dist_city = self._cache.get("dist_city", [])

        # Мини-дашборд
        self._mini_contracts["total"].set_value(str(s.get("total_contracts", 0)))

        total_ind = sum(d.get("individual_count", 0) or 0 for d in dynamics)
        total_tmpl = sum(d.get("template_count", 0) or 0 for d in dynamics)
        self._mini_contracts["individual"].set_value(str(total_ind))
        self._mini_contracts["template"].set_value(str(total_tmpl))

        amount = s.get("total_amount", 0) or 0
        avg = s.get("avg_amount", 0) or 0
        self._mini_contracts["amount"].set_value(
            f"{amount:,.0f}\u00a0руб".replace(",", "\u00a0")
        )
        self._mini_contracts["avg"].set_value(
            f"{avg:,.0f}\u00a0руб".replace(",", "\u00a0")
        )

        # Графики
        if dynamics:
            month_labels = self._periods_to_labels([d.get("period", "") for d in dynamics])

            # Stacked bar кол-во договоров по месяцам
            self.chart_contracts_dynamics.set_data(
                month_labels,
                [
                    {
                        "label": "Индивид.",
                        "values": [d.get("individual_count", 0) or 0 for d in dynamics],
                        "color": "#F57C00"
                    },
                    {
                        "label": "Шаблон.",
                        "values": [d.get("template_count", 0) or 0 for d in dynamics],
                        "color": "#C62828"
                    },
                ],
                stacked=True
            )

            # Линейный стоимость по месяцам
            self.chart_contracts_amount.set_data([
                {
                    "label": "Стоимость",
                    "x": month_labels,
                    "y": [d.get("total_amount", 0) or 0 for d in dynamics],
                    "color": "#F57C00"
                },
            ])

        # Pie по типам: individual, template (без надзора)
        if total_ind or total_tmpl:
            self.chart_contracts_types.set_data(total_ind, total_tmpl, 0)

        # ТОП-10 городов
        if dist_city:
            top_cities = dist_city[:10]
            self.chart_contracts_cities.set_data(
                [c.get("name", "") for c in top_cities],
                [c.get("count", 0) or 0 for c in top_cities]
            )

        # Grouped bar договоры по агентам
        if dist_agent:
            agent_labels = [a.get("name", "") for a in dist_agent]
            agent_counts = [a.get("count", 0) or 0 for a in dist_agent]
            agent_amounts = [a.get("amount", 0) or 0 for a in dist_agent]

            self.chart_contracts_by_agent.set_data(
                agent_labels,
                [{"label": "Договоры", "values": agent_counts, "color": "#2196F3"}],
                stacked=False
            )
            self.chart_contracts_amount_by_agent.set_data(agent_labels, agent_amounts)

    def _update_crm_section(self):
        """Обновить CRM аналитику по типам проектов"""
        for cache_key, subtab in [
            ("crm_individual", self._crm_individual),
            ("crm_template", self._crm_template),
        ]:
            try:
                data = self._cache.get(cache_key) or {}
                logger.info(f"[Reports] _update_crm_section({cache_key}): "
                            f"data={bool(data)}, keys={list(data.keys()) if data else '[]'}")

                # Мини-KPI
                on_time = data.get("on_time_stats", {}) or {}
                subtab["mini_cards"]["on_time_pct"].set_value(
                    f"{on_time.get('projects_pct', 0) or 0:.0f}%"
                )
                subtab["mini_cards"]["stages_on_time_pct"].set_value(
                    f"{on_time.get('stages_pct', 0) or 0:.0f}%"
                )
                subtab["mini_cards"]["avg_deviation"].set_value(
                    f"{on_time.get('avg_deviation_days', 0) or 0:.1f}"
                )
                subtab["mini_cards"]["paused"].set_value(
                    str(data.get("paused_count", 0) or 0)
                )

                # Воронка: FunnelBarChart.set_data принимает dict {stage: count}
                funnel_list = data.get("funnel", []) or []
                if funnel_list:
                    funnel_dict = {
                        f.get("stage", "")[:35]: f.get("count", 0) or 0
                        for f in funnel_list
                    }
                    subtab["funnel"].set_data(funnel_dict)

                # Время стадий vs норматив: grouped bar
                durations = data.get("stage_durations", []) or []
                # Убрать "ДАТА НАЧАЛА РАЗРАБОТКИ" из диаграммы
                durations = [d for d in durations
                             if not d.get("stage", "").upper().startswith("ДАТА НАЧАЛА")]
                if durations:
                    stage_labels = [d.get("stage", "") for d in durations]
                    subtab["stage_duration"].set_data(
                        stage_labels,
                        [
                            {
                                "label": "Норматив",
                                "values": [d.get("norm_days", 0) or 0 for d in durations],
                                "color": "#4CAF50"
                            },
                            {
                                "label": "Факт (дни)",
                                "values": [d.get("avg_actual_days", 0) or 0 for d in durations],
                                "color": "#F57C00"
                            },
                        ],
                        stacked=False,
                        highlight_prefixes=["СТАДИЯ", "ЭТАП", "ДАТА"]
                    )
                    # Прокрутить скролл на середину графика
                    scroll = subtab.get("stage_scroll")
                    if scroll:
                        QTimer.singleShot(0, lambda s=scroll: s.horizontalScrollBar().setValue(
                            s.horizontalScrollBar().maximum() // 2))
            except Exception as e:
                logger.error(f"[Reports] Ошибка обновления CRM ({cache_key}): {e}", exc_info=True)

    def _update_supervision_section(self):
        """Обновить секцию авторского надзора"""
        sv = self._cache.get("supervision") or {}
        logger.info(f"[Reports] _update_supervision_section: "
                    f"data={bool(sv)}, keys={list(sv.keys()) if sv else '[]'}")

        # Фиксированные мини-карточки
        self._mini_supervision["total"].set_value(str(sv.get("total", 0) or 0))
        self._mini_supervision["active"].set_value(str(sv.get("active", 0) or 0))
        by_pt = sv.get("by_project_type", {}) or {}
        self._mini_supervision["individual"].set_value(str(by_pt.get("individual", 0) or 0))
        self._mini_supervision["template"].set_value(str(by_pt.get("template", 0) or 0))

        # Динамические мини-карточки по агентам
        # Удаляем старые (кроме первых 4 фиксированных виджетов)
        while self._supervision_mini_bar_layout.count() > 4:
            item = self._supervision_mini_bar_layout.takeAt(4)
            if item is not None:
                w = item.widget()
                if w is not None:
                    w.setParent(None)
                    w.deleteLater()

        for agent in sv.get("by_agent", []) or []:
            name = agent.get("agent_name", "")
            color = agent.get("agent_color") or "#607D8B"
            card = MiniKPICard(title=f"Надзоры — {name}", border_color=color)
            card.set_value(str(agent.get("count", 0) or 0))
            self._supervision_mini_bar_layout.addWidget(card)

        # Стадии закупок: stacked bar
        stages = sv.get("stages", []) or []
        if stages:
            stage_labels = [s.get("stage", "")[:30] for s in stages]
            self.chart_sv_stages.set_data(
                stage_labels,
                [
                    {
                        "label": "Активные",
                        "values": [s.get("active", 0) or 0 for s in stages],
                        "color": "#4CAF50"
                    },
                    {
                        "label": "Завершённые",
                        "values": [s.get("completed", 0) or 0 for s in stages],
                        "color": "#388E3C"
                    },
                ],
                stacked=True
            )

        # Бюджет план vs факт
        budget = sv.get("budget", {}) or {}
        if budget.get("total_planned"):
            self.chart_sv_budget.set_data(
                [""],
                [
                    {
                        "label": "План",
                        "values": [budget.get("total_planned", 0) or 0],
                        "color": "#2196F3"
                    },
                    {
                        "label": "Факт",
                        "values": [budget.get("total_actual", 0) or 0],
                        "color": "#F57C00"
                    },
                ],
                stacked=False
            )

        # По городам
        by_city = sv.get("by_city", []) or []
        if by_city:
            self.chart_sv_cities.set_data(
                [c.get("city", "") for c in by_city],
                [c.get("count", 0) or 0 for c in by_city]
            )

        # По агентам
        by_agent = sv.get("by_agent", []) or []
        if by_agent:
            self.chart_sv_agents.set_data(
                [a.get("agent_name", "") for a in by_agent],
                [a.get("count", 0) or 0 for a in by_agent]
            )

        # Pie по типам: individual, template, supervision=0
        ind_count = by_pt.get("individual", 0) or 0
        tmpl_count = by_pt.get("template", 0) or 0
        if ind_count or tmpl_count:
            self.chart_sv_project_types.set_data(ind_count, tmpl_count, 0)

        # Мини-KPI: экономия, дефекты, визиты
        budget = sv.get("budget", {}) or {}
        savings = budget.get("total_savings", 0) or 0
        savings_pct = budget.get("savings_pct", 0) or 0
        self._mini_sv_kpi["savings"].set_value(
            f"{savings:,.0f}\u00a0руб ({savings_pct:.0f}%)".replace(",", "\u00a0")
        )
        defects = sv.get("defects", {}) or {}
        self._mini_sv_kpi["defects"].set_value(
            f"{defects.get('found', 0) or 0}\u00a0/\u00a0{defects.get('resolved', 0) or 0}"
        )
        self._mini_sv_kpi["visits"].set_value(str(sv.get("site_visits", 0) or 0))

    # ===================================================================
    # ВСПОМОГАТЕЛЬНЫЕ МЕТОДЫ
    # ===================================================================

    def _periods_to_labels(self, periods):
        """Преобразовать периоды формата 'YYYY-MM' в короткие метки месяцев"""
        month_names = [
            "", "Янв", "Фев", "Мар", "Апр", "Май", "Июн",
            "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"
        ]
        labels = []
        for p in periods:
            parts = str(p).split("-")
            if len(parts) == 2:
                try:
                    labels.append(month_names[int(parts[1])])
                except (ValueError, IndexError):
                    labels.append(str(p))
            else:
                labels.append(str(p))
        return labels

    def _format_number(self, val, suffix=""):
        """Форматировать число с разделителями тысяч"""
        if val is None:
            return "0" + suffix
        try:
            return f"{float(val):,.0f}{suffix}".replace(",", " ")
        except (ValueError, TypeError):
            return str(val) + suffix

    # ===================================================================
    # PDF-ЭКСПОРТ (ReportLab Platypus)
    # ===================================================================

    def _chart_to_rl_image(self, chart, width_mm, height_mm=None,
                           max_height_mm=None, dpi=150):
        """Рендер matplotlib-графика в ReportLab Image через BytesIO.

        Если height_mm задан — figure ресайзится к целевым пропорциям,
        обеспечивая одинаковую высоту парных графиков.

        Args:
            chart: ChartBase виджет с matplotlib figure
            width_mm: желаемая ширина в мм
            height_mm: желаемая высота в мм (None = авто из пропорций figure)
            max_height_mm: максимальная высота в мм (ограничение сверху)
            dpi: разрешение PNG
        Returns:
            reportlab.platypus.Image или None
        """
        import io
        from reportlab.platypus import Image as RLImage
        from reportlab.lib.units import mm

        if not hasattr(chart, 'canvas') or not chart.canvas:
            return None
        if not hasattr(chart, 'figure') or not chart.figure.axes:
            return None

        buf = io.BytesIO()
        fig = chart.figure
        orig_size = fig.get_size_inches()
        orig_dpi = fig.get_dpi()

        try:
            # Целевые размеры в дюймах
            target_w = width_mm / 25.4
            if height_mm:
                target_h = height_mm / 25.4
            else:
                aspect = orig_size[1] / orig_size[0] if orig_size[0] > 0 else 0.6
                target_h = target_w * aspect

            # Ограничение максимальной высоты
            if max_height_mm:
                max_h = max_height_mm / 25.4
                if target_h > max_h:
                    target_h = max_h

            # Временно ресайзим figure для консистентного рендера
            fig.set_size_inches(target_w, target_h)
            try:
                fig.tight_layout(pad=0.8, h_pad=0.6, w_pad=0.6)
            except Exception:
                pass

            fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                        facecolor='white', edgecolor='none', pad_inches=0.04)
            buf.seek(0)

            w = width_mm * mm
            h_mm = height_mm if height_mm else width_mm * (target_h / target_w)
            if max_height_mm and h_mm > max_height_mm:
                h_mm = max_height_mm
            h = h_mm * mm

            return RLImage(buf, width=w, height=h)
        except Exception as e:
            logger.debug(f"Не удалось отрендерить график в PDF: {e}")
            return None
        finally:
            fig.set_size_inches(orig_size)
            fig.set_dpi(orig_dpi)
            try:
                fig.tight_layout(pad=1.2, h_pad=1.0, w_pad=1.0)
            except Exception:
                pass
            chart.canvas.draw()

    def _is_wide_chart(self, chart):
        """Определить нужен ли график на всю ширину.

        Широкие: FunnelBarChart + "Время стадий" (полная ширина в UI).
        Остальные (включая HorizontalBarWidget, StackedBar) — парные, как в UI grid.
        """
        if isinstance(chart, FunnelBarChart):
            return True
        # "Время стадий vs норматив" — отдельный ряд на всю ширину в программе
        if isinstance(chart, StackedBarChartWidget):
            if hasattr(chart, 'chart_title') and 'Время стадий' in (chart.chart_title or ''):
                return True
        return False

    def _pdf_chart_flowables(self, charts, page_w_mm):
        """Раскладка графиков: парные по 2 в строку, широкие на всю ширину.

        Стандарт размеров:
        - Парные графики: col_w x HALF_H мм (одинаковая высота для выравнивания осей)
        - Динамические графики (Funnel, HorizontalBar): авто-высота из пропорций
        - Широкие графики: page_w x авто-высота

        Args:
            charts: список ChartBase виджетов
            page_w_mm: доступная ширина страницы в мм
        Returns:
            list[Flowable] для добавления в elements
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle, Spacer
        from reportlab.lib.units import mm

        GAP_MM = 6
        col_w = (page_w_mm - GAP_MM) / 2
        HALF_H = int(col_w * 0.45)  # стандартная высота парных (~60мм для landscape)
        _TABLE_STYLE = RLTableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 0),
            ('RIGHTPADDING', (0, 0), (-1, -1), 0),
            ('TOPPADDING', (0, 0), (-1, -1), 0),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ])

        # Максимальная высота для широких графиков (не занимать всю страницу)
        WIDE_MAX_H = 90  # мм

        def _is_dynamic(c):
            """Динамическая высота зависит от количества данных"""
            return isinstance(c, (FunnelBarChart, HorizontalBarWidget))

        elements = []
        pending = None

        for chart in charts:
            is_wide = self._is_wide_chart(chart)

            if is_wide:
                if pending is not None:
                    row = RLTable([[pending, '']], colWidths=[col_w * mm, col_w * mm])
                    row.setStyle(_TABLE_STYLE)
                    elements.append(row)
                    elements.append(Spacer(1, 2 * mm))
                    pending = None

                # Широкие: авто-высота с ограничением сверху
                img = self._chart_to_rl_image(
                    chart, width_mm=page_w_mm - 4, max_height_mm=WIDE_MAX_H)
                if img:
                    elements.append(img)
                    elements.append(Spacer(1, 2 * mm))
            else:
                # Парные: фиксированная высота для обычных и Pie, авто для горизонтальных баров
                h = None if _is_dynamic(chart) else HALF_H
                img = self._chart_to_rl_image(chart, width_mm=col_w - 2, height_mm=h)
                if not img:
                    continue
                if pending is None:
                    pending = img
                else:
                    row = RLTable([[pending, img]], colWidths=[col_w * mm, col_w * mm])
                    row.setStyle(_TABLE_STYLE)
                    elements.append(row)
                    elements.append(Spacer(1, 2 * mm))
                    pending = None

        if pending is not None:
            row = RLTable([[pending, '']], colWidths=[col_w * mm, col_w * mm])
            row.setStyle(_TABLE_STYLE)
            elements.append(row)
            elements.append(Spacer(1, 2 * mm))

        return elements

    def _pdf_kpi_row(self, items, font_name, page_w_mm):
        """KPI-карточки с цветной левой рамкой через ReportLab Table.

        Args:
            items: list of (label, value, hex_color)
            font_name: зарегистрированный шрифт
            page_w_mm: доступная ширина страницы в мм
        Returns:
            Table flowable
        """
        from reportlab.platypus import Table as RLTable, TableStyle as RLTableStyle, Paragraph
        from reportlab.lib.styles import ParagraphStyle
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        label_style = ParagraphStyle(
            'KPILabel', fontName=font_name, fontSize=7,
            textColor=colors.HexColor('#888888'), leading=9,
        )
        value_style = ParagraphStyle(
            'KPIValue', fontName=font_name, fontSize=11,
            textColor=colors.HexColor('#333333'), leading=14,
        )

        n = len(items)
        card_w = page_w_mm / n * mm

        # Каждая ячейка — вложенная таблица [label, value]
        cells = []
        for label, value, _ in items:
            inner = RLTable(
                [[Paragraph(label, label_style)],
                 [Paragraph(f'<b>{value}</b>', value_style)]],
                colWidths=[card_w - 10 * mm],
            )
            inner.setStyle(RLTableStyle([
                ('LEFTPADDING', (0, 0), (-1, -1), 0),
                ('RIGHTPADDING', (0, 0), (-1, -1), 0),
                ('TOPPADDING', (0, 0), (-1, -1), 0),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
            ]))
            cells.append(inner)

        table = RLTable([cells], colWidths=[card_w] * n)

        style_cmds = [
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 4),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFAFA')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E0E0E0')),
        ]
        for i, (_, _, hex_color) in enumerate(items):
            style_cmds.append(
                ('LINEBEFORE', (i, 0), (i, 0), 3, colors.HexColor(hex_color))
            )
        table.setStyle(RLTableStyle(style_cmds))
        return table

    def _grab_crm_both_tabs(self, scale=3.0):
        """Захватить обе вкладки CRM — покомпонентно (mini cards, funnel, stage chart).
        Returns: list of (label, images_list) где images_list = [(buf, w_px, h_px), ...]
        """
        from PyQt5.QtWidgets import QApplication
        results = []
        saved_idx = self.crm_tabs.currentIndex()
        for idx, subtab in enumerate([self._crm_individual, self._crm_template]):
            self.crm_tabs.setCurrentIndex(idx)
            QApplication.processEvents()
            QApplication.processEvents()
            label = self.crm_tabs.tabText(idx)
            images = []

            # 1. Mini KPI cards
            mini_flow_w = subtab.get("mini_flow_w")
            if mini_flow_w and mini_flow_w.isVisible():
                data = grab_widget_png(mini_flow_w, scale)
                if data:
                    images.append(data)

            # 2. Funnel chart — через figure.savefig() (лучшее качество)
            funnel = subtab.get("funnel")
            if funnel and hasattr(funnel, 'figure') and funnel.figure.axes:
                chart_data = chart_to_png(funnel, dpi=300)
                if chart_data:
                    images.append(chart_data)

            # 3. Stage duration chart — через figure.savefig() (полный, без обрезки скроллом)
            stage_chart = subtab.get("stage_duration")
            if stage_chart and hasattr(stage_chart, 'figure') and stage_chart.figure.axes:
                chart_data = chart_to_png(stage_chart, dpi=300)
                if chart_data:
                    images.append(chart_data)

            if images:
                results.append((label, images))
        self.crm_tabs.setCurrentIndex(saved_idx)
        return results

    def export_to_pdf(self):
        """Экспорт отчёта в PDF — скриншоты секций (pixel-perfect как на экране)"""
        try:
            import os
            from datetime import datetime
            from reportlab.platypus import (
                SimpleDocTemplate, Paragraph, Spacer,
                Image as RLImage, CondPageBreak
            )
            from reportlab.lib.styles import ParagraphStyle
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib import colors
            from reportlab.lib.units import mm

            date_str = datetime.now().strftime('%d.%m.%Y')
            default_name = f"Отчеты и статистика от {date_str}"

            filename, _ = QFileDialog.getSaveFileName(
                self, "Сохранить отчёт", default_name, "PDF файлы (*.pdf)"
            )
            if not filename:
                return

            font_name, font_bold = register_fonts()

            # --- Landscape A4 ---
            page_size = landscape(A4)
            MARGIN_LR = 10 * mm
            MARGIN_TOP = 8 * mm
            MARGIN_BOT = 12 * mm
            PAGE_W_MM = (page_size[0] - 2 * MARGIN_LR) / mm
            PAGE_H_MM = (page_size[1] - MARGIN_TOP - MARGIN_BOT) / mm
            RENDER_SCALE = 3.0  # 3x для чёткого текста в PDF

            doc = SimpleDocTemplate(
                filename,
                pagesize=page_size,
                leftMargin=MARGIN_LR,
                rightMargin=MARGIN_LR,
                topMargin=MARGIN_TOP,
                bottomMargin=MARGIN_BOT,
            )

            style_title = ParagraphStyle(
                'RptTitle', fontName=font_bold, fontSize=16,
                textColor=colors.HexColor('#333333'),
                alignment=1, spaceAfter=2 * mm,
            )
            style_filter = ParagraphStyle(
                'RptFilter', fontName=font_name, fontSize=8,
                textColor=colors.HexColor('#666666'),
                alignment=1, spaceAfter=3 * mm,
                backColor=colors.HexColor('#F8F9FA'),
            )

            footer_cb = make_page_footer(page_size, font_name)

            elements = []

            # === ШАПКА ===
            logo_path = resource_path("resources/logo_pdf.png")
            if not os.path.exists(logo_path):
                logo_path = resource_path("resources/logo.png")
            if os.path.exists(logo_path):
                try:
                    logo = RLImage(logo_path, width=35 * mm, height=20 * mm,
                                   kind='proportional')
                    logo.hAlign = 'CENTER'
                    elements.append(logo)
                    elements.append(Spacer(1, 4 * mm))
                except Exception:
                    pass

            elements.append(Paragraph(
                'ОТЧЁТЫ И СТАТИСТИКА', style_title
            ))
            elements.append(Spacer(1, 3 * mm))

            filters_info = []
            for label, combo in [
                ("Год", self.filter_year), ("Квартал", self.filter_quarter),
                ("Месяц", self.filter_month), ("Тип агента", self.filter_agent),
                ("Город", self.filter_city), ("Тип проекта", self.filter_project_type),
            ]:
                val = combo.currentText()
                if val and val != "Все":
                    filters_info.append(f"<b>{label}:</b> {val}")
            filter_text = " | ".join(filters_info) if filters_info else "Все данные (без фильтров)"
            elements.append(Paragraph(
                f'<b>Фильтры:</b> {filter_text} | '
                f'<b>Дата:</b> {datetime.now().strftime("%d.%m.%Y %H:%M")}',
                style_filter
            ))
            elements.append(Spacer(1, 3 * mm))

            # === СЕКЦИИ — скриншоты виджетов (pixel-perfect) ===
            crm_section_idx = 3  # CRM — 4-я секция (0-indexed)
            logger.info(f"PDF: захват {len(self._pdf_sections)} секций")

            # Доступная высота на странице (с запасом на footer/spacers)
            safe_h_mm = PAGE_H_MM - 15

            for idx, section in enumerate(self._pdf_sections):
                if idx == crm_section_idx:
                    # CRM: заголовок + каждый таб отдельно
                    elements.append(CondPageBreak(40 * mm))
                    elements.append(pdf_section_header(
                        'CRM Аналитика', font_bold))
                    elements.append(Spacer(1, 3 * mm))
                    # CRM: mini cards (~15мм) + funnel (~55мм) + stage (~95мм) = ~170мм ≈ 1 стр
                    CRM_CARDS_H = 18   # мм — мини-карточки
                    CRM_FUNNEL_H = 55  # мм — воронка
                    CRM_STAGE_H = 95   # мм — время стадий
                    crm_heights = [CRM_CARDS_H, CRM_FUNNEL_H, CRM_STAGE_H]

                    for tab_label, images_list in self._grab_crm_both_tabs(RENDER_SCALE):
                        elements.append(CondPageBreak(120 * mm))
                        tab_style = ParagraphStyle(
                            'TabLabel', fontName=font_bold, fontSize=11,
                            textColor=colors.HexColor('#555555'),
                            spaceAfter=2 * mm,
                        )
                        elements.append(Paragraph(tab_label, tab_style))
                        for img_idx, (buf, w_px, h_px) in enumerate(images_list):
                            max_h = crm_heights[img_idx] if img_idx < len(crm_heights) else 80
                            img = fit_image(buf, w_px, h_px, PAGE_W_MM, max_h)
                            elements.append(img)
                            if img_idx < len(images_list) - 1:
                                elements.append(Spacer(1, 2 * mm))
                else:
                    elements.append(CondPageBreak(50 * mm))
                    data = grab_widget_png(section, RENDER_SCALE)
                    logger.info(f"PDF: секция [{idx}] {section.width()}x{section.height()} "
                                f"grab={'OK' if data else 'FAIL'}")
                    if data:
                        buf, w_px, h_px = data
                        img = fit_image(buf, w_px, h_px, PAGE_W_MM, safe_h_mm)
                        elements.append(img)
                        elements.append(Spacer(1, 4 * mm))

            # === СБОРКА ===
            doc.build(elements,
                      onFirstPage=footer_cb,
                      onLaterPages=footer_cb)
            logger.info(f"PDF отчёт сохранён: {filename}")
            open_file(filename)

        except Exception as e:
            logger.error(f"Ошибка экспорта PDF: {e}", exc_info=True)
            CustomMessageBox(self, "Ошибка экспорта",
                             f"Не удалось сохранить PDF:\n{e}").exec_()
