# -*- coding: utf-8 -*-
"""
Виджеты графиков для дашборда аналитики.
Используют matplotlib для отрисовки внутри PyQt5.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QFrame, QHBoxLayout
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

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

        self.figure = Figure(figsize=(4, 3), dpi=100)
        self.figure.patch.set_facecolor('#F8F9FA')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._layout.addWidget(self.canvas)

    def _finalize(self):
        """Финализация отрисовки"""
        if self.canvas:
            self.figure.tight_layout(pad=1.5)
            self.canvas.draw()


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

        # Сортируем по количеству (убывание сверху вниз)
        sorted_items = sorted(funnel_dict.items(), key=lambda x: x[1])
        labels = [item[0] for item in sorted_items]
        values = [item[1] for item in sorted_items]

        colors = ['#ffd93c', '#F39C12', '#27AE60', '#3498DB', '#9B59B6',
                  '#E74C3C', '#1ABC9C', '#34495E', '#95A5A6', '#D35400']
        bar_colors = [colors[i % len(colors)] for i in range(len(labels))]

        bars = ax.barh(labels, values, color=bar_colors, height=0.6, edgecolor='white')

        # Значения на столбцах
        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=9, fontweight='bold', color='#333')

        ax.set_title(self.chart_title, fontsize=12, fontweight='bold', color='#2C3E50', pad=10)
        ax.set_xlabel('Количество проектов', fontsize=9, color='#666')
        ax.tick_params(axis='y', labelsize=8)
        ax.tick_params(axis='x', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

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

        # Сортируем по нагрузке (меньше внизу, больше вверху)
        sorted_data = sorted(executor_list, key=lambda x: x.get("active_stages", 0))
        names = [d["name"] for d in sorted_data]
        stages = [d.get("active_stages", 0) for d in sorted_data]

        # Цвет в зависимости от нагрузки
        def bar_color(val):
            if val >= 8:
                return '#E74C3C'  # красный — перегрузка
            elif val >= 5:
                return '#F39C12'  # оранжевый — средняя
            else:
                return '#27AE60'  # зелёный — норма

        colors = [bar_color(s) for s in stages]
        bars = ax.barh(names, stages, color=colors, height=0.6, edgecolor='white')

        for bar, val in zip(bars, stages):
            ax.text(bar.get_width() + 0.2, bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=9, fontweight='bold', color='#333')

        ax.set_title(self.chart_title, fontsize=12, fontweight='bold', color='#2C3E50', pad=10)
        ax.set_xlabel('Активные стадии', fontsize=9, color='#666')
        ax.tick_params(axis='y', labelsize=8)
        ax.tick_params(axis='x', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)

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

        labels = []
        sizes = []
        colors = []

        if individual_count > 0:
            labels.append(f'Индивидуальные ({individual_count})')
            sizes.append(individual_count)
            colors.append('#ffd93c')
        if template_count > 0:
            labels.append(f'Шаблонные ({template_count})')
            sizes.append(template_count)
            colors.append('#F39C12')
        if supervision_count > 0:
            labels.append(f'Надзор ({supervision_count})')
            sizes.append(supervision_count)
            colors.append('#27AE60')

        if not sizes:
            ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                    fontsize=12, color='#999', transform=ax.transAxes)
            self._finalize()
            return

        wedges, texts, autotexts = ax.pie(
            sizes, labels=labels, colors=colors, autopct='%1.0f%%',
            startangle=90, textprops={'fontsize': 9},
            wedgeprops={'edgecolor': 'white', 'linewidth': 2}
        )
        for t in autotexts:
            t.set_fontweight('bold')
            t.set_color('#333')

        ax.set_title(self.chart_title, fontsize=12, fontweight='bold', color='#2C3E50', pad=10)

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
                background-color: #FAFAFA;
                border: 1px solid #E0E0E0;
                border-radius: 8px;
            }
        """)

        # Основной layout секции
        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(12, 12, 12, 12)
        outer_layout.setSpacing(8)

        # Заголовок секции
        title_label = QLabel(title, self)
        title_font = QFont()
        title_font.setPointSize(11)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #333333; background-color: transparent;")
        outer_layout.addWidget(title_label)

        # Описание (скрыто если пустое)
        if description:
            desc_label = QLabel(description, self)
            desc_label.setStyleSheet("font-size: 11px; color: #666666; background-color: transparent;")
            desc_label.setWordWrap(True)
            outer_layout.addWidget(desc_label)

        # Контент-область
        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(8)
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

    # Цветовая палитра проекта
    DEFAULT_COLORS = ['#F57C00', '#C62828', '#388E3C', '#2196F3', '#9C27B0', '#00BCD4']

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(280)
        # Устанавливаем фон графика
        if self.canvas:
            self.figure.patch.set_facecolor('#FAFAFA')

    def set_data(self, series: list):
        """
        Установить данные для отрисовки.

        Args:
            series: Список серий. Каждая серия — dict:
                {
                    "label": str,       # подпись в легенде
                    "x": list,          # метки по оси X
                    "y": list,          # значения по оси Y
                    "color": str        # цвет линии (опционально)
                }
        """
        if not self.canvas or not series:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#FAFAFA')

        for i, s in enumerate(series):
            color = s.get("color") or self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
            x_data = s.get("x", [])
            y_data = s.get("y", [])
            label = s.get("label", "")

            if not x_data or not y_data:
                continue

            # Рисуем линию с маркерами
            ax.plot(x_data, y_data, color=color, linewidth=2, marker='o',
                    markersize=5, label=label, zorder=3)

            # Area fill с прозрачностью
            ax.fill_between(range(len(x_data)), y_data, alpha=0.15, color=color)

        # Подписи оси X
        if series and series[0].get("x"):
            x_labels = series[0]["x"]
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, fontsize=8, rotation=30, ha='right')

        ax.tick_params(axis='y', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.4, color='#CCCCCC')

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=12, fontweight='bold',
                         color='#2C3E50', pad=10)

        # Легенда (если несколько серий)
        handles, labels = ax.get_legend_handles_labels()
        if len(handles) > 1:
            ax.legend(loc='upper left', fontsize=8, framealpha=0.8,
                      edgecolor='#E0E0E0')
        elif len(handles) == 1 and labels[0]:
            ax.legend(loc='upper left', fontsize=8, framealpha=0.8,
                      edgecolor='#E0E0E0')

        self._finalize()


class StackedBarChartWidget(ChartBase):
    """Stacked/Grouped bar chart"""

    # Цветовая палитра проекта
    DEFAULT_COLORS = ['#F57C00', '#C62828', '#388E3C', '#2196F3', '#9C27B0', '#00BCD4']

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(280)
        if self.canvas:
            self.figure.patch.set_facecolor('#FAFAFA')

    def set_data(self, categories: list, series: list, stacked=True):
        """
        Установить данные для отрисовки.

        Args:
            categories: Подписи по оси X (напр. ["Янв", "Фев", ...])
            series: Список серий:
                [
                    {"label": "Инд.", "values": [10, 20, ...], "color": "#F57C00"},
                    ...
                ]
            stacked: True — стопкой, False — grouped (рядом)
        """
        if not self.canvas or not categories or not series:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_facecolor('#FAFAFA')

        n_categories = len(categories)
        x = range(n_categories)

        if stacked:
            # Stacked bar
            bottoms = [0.0] * n_categories
            for i, s in enumerate(series):
                color = s.get("color") or self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
                values = s.get("values", [0] * n_categories)
                bars = ax.bar(x, values, bottom=bottoms, color=color,
                              label=s.get("label", ""), edgecolor='white', linewidth=0.5)
                # Подписи на барах (только для достаточно больших значений)
                for bar, val, bot in zip(bars, values, bottoms):
                    if val > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                bot + val / 2, str(int(val)),
                                ha='center', va='center', fontsize=7,
                                fontweight='bold', color='white')
                bottoms = [b + v for b, v in zip(bottoms, values)]
        else:
            # Grouped bar
            n_series = len(series)
            bar_width = 0.8 / n_series
            for i, s in enumerate(series):
                color = s.get("color") or self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
                values = s.get("values", [0] * n_categories)
                offset = (i - n_series / 2 + 0.5) * bar_width
                positions = [xi + offset for xi in x]
                bars = ax.bar(positions, values, width=bar_width * 0.9,
                              color=color, label=s.get("label", ""),
                              edgecolor='white', linewidth=0.5)
                # Подписи на барах
                for bar, val in zip(bars, values):
                    if val > 0:
                        ax.text(bar.get_x() + bar.get_width() / 2,
                                bar.get_height() + 0.3, str(int(val)),
                                ha='center', va='bottom', fontsize=7,
                                fontweight='bold', color='#333')

        ax.set_xticks(list(x))
        ax.set_xticklabels(categories, fontsize=8, rotation=30, ha='right')
        ax.tick_params(axis='y', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='y', linestyle='--', alpha=0.4, color='#CCCCCC')

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=12, fontweight='bold',
                         color='#2C3E50', pad=10)

        handles, labels = ax.get_legend_handles_labels()
        if handles:
            ax.legend(loc='upper right', fontsize=8, framealpha=0.8,
                      edgecolor='#E0E0E0')

        self._finalize()


class HorizontalBarWidget(ChartBase):
    """Горизонтальный bar chart для ТОП-N или распределений"""

    # Цветовая палитра проекта
    DEFAULT_COLORS = ['#F57C00', '#C62828', '#388E3C', '#2196F3', '#9C27B0',
                      '#00BCD4', '#FF9800', '#607D8B', '#E91E63', '#795548']

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)
        self.setMinimumHeight(250)
        if self.canvas:
            self.figure.patch.set_facecolor('#FAFAFA')

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
        ax.set_facecolor('#FAFAFA')

        # Сортируем по убыванию значений
        paired = sorted(zip(values, labels), key=lambda x: x[0])
        sorted_values = [p[0] for p in paired]
        sorted_labels = [p[1] for p in paired]

        if colors:
            # Переставляем цвета в соответствии с сортировкой
            label_to_color = {lbl: colors[i % len(colors)] for i, lbl in enumerate(labels)}
            bar_colors = [label_to_color.get(lbl, self.DEFAULT_COLORS[0]) for lbl in sorted_labels]
        else:
            bar_colors = [self.DEFAULT_COLORS[i % len(self.DEFAULT_COLORS)]
                          for i in range(len(sorted_labels))]

        bars = ax.barh(sorted_labels, sorted_values, color=bar_colors,
                       height=0.6, edgecolor='white')

        # Значения на барах (справа)
        for bar, val in zip(bars, sorted_values):
            ax.text(bar.get_width() + max(sorted_values) * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    str(int(val)) if isinstance(val, float) and val == int(val) else str(val),
                    va='center', fontsize=9, fontweight='bold', color='#333')

        ax.tick_params(axis='y', labelsize=8)
        ax.tick_params(axis='x', labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.grid(axis='x', linestyle='--', alpha=0.4, color='#CCCCCC')

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=12, fontweight='bold',
                         color='#2C3E50', pad=10)

        self._finalize()
