# -*- coding: utf-8 -*-
"""
Виджеты графиков для дашборда аналитики.
Используют matplotlib для отрисовки внутри PyQt5.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QColor

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib
    matplotlib.use('Qt5Agg')
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class ChartBase(QWidget):
    """Базовый класс для графиков"""

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.chart_title = title
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self.setLayout(self._layout)

        if not MATPLOTLIB_AVAILABLE:
            lbl = QLabel("matplotlib не установлен")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #999; font-size: 12px;")
            self._layout.addWidget(lbl)
            self.canvas = None
            return

        self.figure = Figure(figsize=(5, 3.2), dpi=100)
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addWidget(self.canvas)

        # Рамка вокруг графика
        self.setStyleSheet("""
            ChartBase, LineChartWidget, StackedBarChartWidget, HorizontalBarWidget,
            FunnelBarChart, ProjectTypePieChart, ExecutorLoadChart {
                background: white;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
        """)

    def _finalize(self):
        """Финализация отрисовки"""
        if self.canvas:
            try:
                self.figure.tight_layout(pad=2.0, h_pad=1.5, w_pad=1.5)
            except Exception:
                pass
            self.canvas.draw()

    @staticmethod
    def _truncate(text, max_len=20):
        """Обрезать длинный текст"""
        if len(text) > max_len:
            return text[:max_len - 1] + "..."
        return text


class FunnelBarChart(ChartBase):
    """Горизонтальная столбчатая диаграмма — воронка проектов по колонкам Kanban"""

    def __init__(self, parent=None):
        super().__init__("Воронка проектов", parent)

    def set_data(self, funnel_dict):
        """funnel_dict: {column_name: count, ...}"""
        if not self.canvas or not funnel_dict:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        # Сортируем по количеству (убывание сверху вниз)
        sorted_items = sorted(funnel_dict.items(), key=lambda x: x[1])
        labels = [self._truncate(item[0], 25) for item in sorted_items]
        values = [item[1] for item in sorted_items]

        colors = ['#ffd93c', '#F39C12', '#27AE60', '#3498DB', '#9B59B6',
                  '#E74C3C', '#1ABC9C', '#34495E', '#95A5A6', '#D35400']
        bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

        bars = ax.barh(labels, values, color=bar_colors, height=0.6, edgecolor='white')

        # Значения на столбцах
        max_val = max(values) if values else 1
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.03, bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=9, fontweight='bold', color='#333')

        ax.set_title(self.chart_title, fontsize=11, fontweight='bold', color='#333', pad=8)
        ax.set_xlabel('Количество проектов', fontsize=8, color='#888')
        ax.tick_params(axis='y', labelsize=7, pad=2)
        ax.tick_params(axis='x', labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#E0E0E0')

        self._finalize()


class ExecutorLoadChart(ChartBase):
    """Горизонтальная столбчатая диаграмма — нагрузка на исполнителей"""

    def __init__(self, parent=None):
        super().__init__("Нагрузка исполнителей", parent)

    def set_data(self, executor_list):
        """executor_list: [{"name": ..., "active_stages": ...}, ...]"""
        if not self.canvas or not executor_list:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        sorted_data = sorted(executor_list, key=lambda x: x.get("active_stages", 0))
        names = [self._truncate(d["name"], 18) for d in sorted_data]
        stages = [d.get("active_stages", 0) for d in sorted_data]

        def bar_color(val):
            if val >= 8:
                return '#E74C3C'
            elif val >= 5:
                return '#F39C12'
            else:
                return '#27AE60'

        colors = [bar_color(s) for s in stages]
        bars = ax.barh(names, stages, color=colors, height=0.6, edgecolor='white')

        max_val = max(stages) if stages else 1
        for bar, val in zip(bars, stages):
            ax.text(bar.get_width() + max_val * 0.03, bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=8, fontweight='bold', color='#333')

        ax.set_title(self.chart_title, fontsize=11, fontweight='bold', color='#333', pad=8)
        ax.set_xlabel('Активные стадии', fontsize=8, color='#888')
        ax.tick_params(axis='y', labelsize=7, pad=2)
        ax.tick_params(axis='x', labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#E0E0E0')

        self._finalize()


class ProjectTypePieChart(ChartBase):
    """Круговая диаграмма — распределение по типам проектов"""

    def __init__(self, parent=None):
        super().__init__("Типы проектов", parent)

    def set_data(self, individual_count, template_count, supervision_count=0):
        """Установить данные для пирога"""
        if not self.canvas:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        labels = []
        sizes = []
        colors = []

        if individual_count > 0:
            labels.append(f'Индив. ({individual_count})')
            sizes.append(individual_count)
            colors.append('#F57C00')
        if template_count > 0:
            labels.append(f'Шаблон. ({template_count})')
            sizes.append(template_count)
            colors.append('#C62828')
        if supervision_count > 0:
            labels.append(f'Надзор ({supervision_count})')
            sizes.append(supervision_count)
            colors.append('#388E3C')

        if not sizes:
            ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                    fontsize=11, color='#999', transform=ax.transAxes)
            self._finalize()
            return

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct='%1.0f%%',
            startangle=90, textprops={'fontsize': 8},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2, 'width': 0.65},
            pctdistance=0.7
        )
        for t in autotexts:
            t.set_fontweight('bold')
            t.set_color('#333')
            t.set_fontsize(9)

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=11, fontweight='bold',
                         color='#333', pad=8)

        self._finalize()


class SectionWidget(QFrame):
    """Контейнер секции с заголовком для страницы отчётов"""

    def __init__(self, title, description="", parent=None):
        """
        Args:
            title: Заголовок секции
            description: Описание (скрыт если пустой)
            parent: Родительский виджет
        """
        super().__init__(parent)

        self.setStyleSheet("""
            SectionWidget {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)

        # Тень
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(shadow)

        # Основной layout секции
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(16, 14, 16, 14)
        outer_layout.setSpacing(10)

        # Заголовок секции
        title_label = QLabel(title, self)
        title_font = QFont("Segoe UI", 12, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #222; background-color: transparent;")
        outer_layout.addWidget(title_label)

        # Описание (скрыто если пустое)
        if description:
            desc_label = QLabel(description, self)
            desc_label.setStyleSheet("font-size: 11px; color: #888; background-color: transparent;")
            desc_label.setWordWrap(True)
            outer_layout.addWidget(desc_label)

        # Контент-область
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addLayout(self.content_layout)

        self.setLayout(outer_layout)

    def add_widget(self, widget):
        """Добавить виджет в контент-область секции"""
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        """Добавить layout в контент-область секции"""
        self.content_layout.addLayout(layout)


class LineChartWidget(ChartBase):
    """Линейный график с поддержкой нескольких серий"""

    DEFAULT_COLORS = ['#F57C00', '#C62828', '#388E3C', '#2196F3', '#9C27B0', '#00BCD4']

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(260)

    def set_data(self, series: list):
        """
        Args:
            series: Список серий. Каждая серия — dict:
                {"label": str, "x": list, "y": list, "color": str}
        """
        if not self.canvas or not series:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        for i, s in enumerate(series):
            color = s.get("color") or self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
            x_data = s.get("x", [])
            y_data = s.get("y", [])
            label = s.get("label", "")
            if not x_data or not y_data:
                continue
            ax.plot(x_data, y_data, color=color, linewidth=2.5, marker='o',
                    markersize=4, label=label, zorder=3)
            ax.fill_between(range(len(x_data)), y_data, alpha=0.12, color=color)

        if series and series[0].get("x"):
            x_labels = series[0]["x"]
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, fontsize=7, rotation=0, ha='center')

        ax.tick_params(axis='y', labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#E0E0E0')
        ax.grid(axis='y', linestyle='--', alpha=0.3, color='#DDD')

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=11, fontweight='bold',
                         color='#333', pad=8)

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc='upper left', fontsize=7, framealpha=0.9,
                      edgecolor='#E0E0E0', fancybox=True)

        self._finalize()


class StackedBarChartWidget(ChartBase):
    """Stacked/Grouped bar chart"""

    DEFAULT_COLORS = ['#F57C00', '#C62828', '#388E3C', '#2196F3', '#9C27B0', '#00BCD4']

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(260)

    def set_data(self, categories: list, series: list, stacked=True):
        """
        Args:
            categories: Подписи по оси X
            series: [{"label": ..., "values": [...], "color": ...}, ...]
            stacked: True — стопкой, False — grouped
        """
        if not self.canvas or not categories or not series:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        # Обрезка длинных категорий
        short_categories = [self._truncate(c, 12) for c in categories]
        n_categories = len(short_categories)
        x = range(n_categories)

        # Определяем нужен ли поворот меток
        need_rotation = n_categories > 6 or any(len(c) > 6 for c in short_categories)
        rotation = 45 if need_rotation else 0
        ha = 'right' if need_rotation else 'center'

        if stacked:
            bottoms = [0.0] * n_categories
            for i, s in enumerate(series):
                color = s.get("color") or self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
                values = s.get("values", [0] * n_categories)
                bars = ax.bar(x, values, bottom=bottoms, color=color,
                              label=s.get("label", ""), edgecolor='white',
                              linewidth=0.5, width=0.7)
                for bar, val, bot in zip(bars, values, bottoms):
                    if val > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                bot + val / 2, str(int(val)),
                                ha='center', va='center', fontsize=7,
                                fontweight='bold', color='white')
                bottoms = [b + v for b, v in zip(bottoms, values)]
        else:
            n_series = len(series)
            bar_width = 0.7 / n_series
            for i, s in enumerate(series):
                color = s.get("color") or self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
                values = s.get("values", [0] * n_categories)
                offset = (i - n_series / 2 + 0.5) * bar_width
                positions = [xi + offset for xi in x]
                bars = ax.bar(positions, values, width=bar_width * 0.9,
                              color=color, label=s.get("label", ""),
                              edgecolor='white', linewidth=0.5)
                for bar, val in zip(bars, values):
                    if val > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                bar.get_height() * 1.02 + 0.1, str(int(val)),
                                ha='center', va='bottom', fontsize=6,
                                fontweight='bold', color='#555')

        ax.set_xticks(list(x))
        ax.set_xticklabels(short_categories, fontsize=7, rotation=rotation, ha=ha)
        ax.tick_params(axis='y', labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#E0E0E0')
        ax.grid(axis='y', linestyle='--', alpha=0.3, color='#DDD')

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=11, fontweight='bold',
                         color='#333', pad=8)

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc='upper right', fontsize=7, framealpha=0.9,
                      edgecolor='#E0E0E0', fancybox=True)

        self._finalize()


class HorizontalBarWidget(ChartBase):
    """Горизонтальный bar chart для ТОП-N или распределений"""

    # Цветовая палитра проекта
    DEFAULT_COLORS = ['#F57C00', '#C62828', '#388E3C', '#2196F3', '#9C27B0',
                      '#00BCD4', '#FF9800', '#607D8B', '#E91E63', '#795548']

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(250)

    def set_data(self, labels: list, values: list, colors: list = None):
        """
        Установить данные для отрисовки.

        Args:
            labels: Подписи категорий
            values: Значения (автоматически сортируются по убыванию)
            colors: Цвета баров (опционально)
        """
        if not self.canvas or not labels or not values:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('white')

        # Сортируем по убыванию значений
        paired = sorted(zip(values, labels), key=lambda x: x[0])
        sorted_values = [p[0] for p in paired]
        sorted_labels = [self._truncate(p[1], 20) for p in paired]

        if colors:
            label_to_color = {lbl: colors[i % len(colors)] for i, lbl in enumerate(labels)}
            bar_colors = [label_to_color.get(lbl, self.DEFAULT_COLORS[0]) for lbl in sorted_labels]
        else:
            bar_colors = [self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
                          for i in range(len(sorted_labels))]

        bars = ax.barh(sorted_labels, sorted_values, color=bar_colors,
                       height=0.6, edgecolor='white')

        # Значения на барах (справа)
        max_val = max(sorted_values) if sorted_values else 1
        for bar, val in zip(bars, sorted_values):
            ax.text(bar.get_width() + max_val * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    str(int(val)) if isinstance(val, float) and val == int(val) else str(val),
                    va='center', fontsize=8, fontweight='bold', color='#333')

        ax.tick_params(axis='y', labelsize=7, pad=2)
        ax.tick_params(axis='x', labelsize=7)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#E0E0E0')
        ax.spines['bottom'].set_color('#E0E0E0')
        ax.grid(axis='x', linestyle='--', alpha=0.3, color='#DDD')

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=11, fontweight='bold',
                         color='#333', pad=8)

        self._finalize()
