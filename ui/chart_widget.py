# -*- coding: utf-8 -*-
"""
Виджеты графиков для дашборда аналитики.
Используют matplotlib для отрисовки внутри PyQt5.
"""
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy
from PyQt5.QtCore import Qt

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
