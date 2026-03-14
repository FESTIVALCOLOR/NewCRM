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
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    matplotlib.use('Qt5Agg')
    matplotlib.rcParams.update({
        'figure.facecolor': '#FFFFFF',
        'axes.facecolor': '#FAFAFA',
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.spines.left': False,
        'axes.spines.bottom': False,
        'axes.grid': True,
        'axes.axisbelow': True,
        'grid.color': '#EEEEEE',
        'grid.linewidth': 0.8,
        'grid.alpha': 1.0,
        'grid.linestyle': '-',
        'font.family': 'sans-serif',
        'font.sans-serif': ['Segoe UI', 'Arial', 'DejaVu Sans'],
        'text.color': '#333333',
        'axes.labelcolor': '#666666',
        'xtick.color': '#888888',
        'ytick.color': '#888888',
        'xtick.major.size': 0,
        'ytick.major.size': 0,
        'xtick.labelsize': 9,
        'ytick.labelsize': 9,
    })
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


class _Theme:
    BAR_W_VERT = 0.55
    BAR_H_HORZ = 0.55
    MIN_HBAR_ITEMS = 3  # минимум элементов для ylim — эталон «Надзоры по агентам»
    MIN_VBAR_CATS = 3   # минимум категорий для xlim — единая ширина вертикальных баров
    TITLE_SIZE = 13
    LABEL_SIZE = 9
    TICK_SIZE = 9
    VALUE_SIZE = 10
    LEGEND_SIZE = 9
    PALETTE = [
        '#4A90D9', '#F5A623', '#7ED321', '#D0021B', '#9013FE',
        '#50E3C2', '#F8E71C', '#BD10E0', '#4A4A4A', '#B8E986',
    ]
    COLOR_INDIVIDUAL = '#F5A623'
    COLOR_TEMPLATE = '#D0021B'
    COLOR_SUPERVISION = '#7ED321'


class ChartBase(QWidget):
    """Базовый класс для графиков"""

    _AXIS_LEFT = 0.15
    _AXIS_RIGHT = 0.96

    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.chart_title = title
        self._layout = QVBoxLayout()
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self.setLayout(self._layout)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        if not MATPLOTLIB_AVAILABLE:
            lbl = QLabel("matplotlib не установлен")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #999; font-size: 12px;")
            self._layout.addWidget(lbl)
            self.canvas = None
            return

        self.figure = Figure(figsize=(6, 3.5), dpi=100)
        self.figure.patch.set_facecolor('white')
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(260)
        self._layout.addWidget(self.canvas)

        self.setStyleSheet("""
            ChartBase, LineChartWidget, StackedBarChartWidget, HorizontalBarWidget,
            FunnelBarChart, ProjectTypePieChart, ExecutorLoadChart, ContractTypePieChart {
                background: white;
                border: 1px solid #E8E8E8;
                border-radius: 8px;
            }
        """)

    def _finalize(self, *, legend_above=False, bottom=None, left=None, right=None):
        if self.canvas:
            try:
                self.figure.tight_layout(pad=1.2, h_pad=1.0, w_pad=1.0)
            except Exception:
                pass
            kwargs = {}
            if left is not None:
                kwargs['left'] = left
            elif self._AXIS_LEFT is not None:
                kwargs['left'] = self._AXIS_LEFT
            if right is not None:
                kwargs['right'] = right
            elif self._AXIS_LEFT is not None:
                kwargs['right'] = self._AXIS_RIGHT
            if legend_above:
                kwargs['top'] = 0.82
            if bottom is not None:
                kwargs['bottom'] = bottom
            if kwargs and self.figure.axes:
                self.figure.subplots_adjust(**kwargs)
            self.canvas.draw()

    def _add_legend_row(self, ax):
        """Размещает легенду НАД графиком в одну строку. Возвращает True если легенда добавлена."""
        handles, labels = ax.get_legend_handles_labels()
        if not handles:
            return False
        ax.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 1.0),
                  ncol=len(handles), fontsize=_Theme.LEGEND_SIZE, frameon=False,
                  columnspacing=1.5, handlelength=1.5)
        return True

    @staticmethod
    def _apply_bar_gradient(ax, bars):
        """Лёгкий градиент (подсветка сверху) на столбцах — работает для bar и barh"""
        import numpy as np
        xlim, ylim = ax.get_xlim(), ax.get_ylim()
        for bar in bars:
            x0, y0 = bar.get_xy()
            w, h = bar.get_width(), bar.get_height()
            if abs(w) < 1e-10 or abs(h) < 1e-10:
                continue
            grad = np.zeros((100, 1, 4))
            grad[:, 0, :3] = 1.0
            grad[:, 0, 3] = np.linspace(0.28, 0.0, 100)
            ax.imshow(grad, extent=[x0, x0 + w, y0, y0 + h],
                      aspect='auto', zorder=bar.get_zorder() + 1,
                      interpolation='bilinear')
        ax.set_xlim(xlim)
        ax.set_ylim(ylim)

    def to_base64_png(self, width_px=700, dpi=150):
        if not self.canvas or not self.figure.axes:
            return ""
        import io
        import base64
        orig_size = self.figure.get_size_inches()
        orig_dpi = self.figure.get_dpi()
        try:
            render_dpi = max(72, width_px / orig_size[0]) if orig_size[0] > 0 else dpi
            try:
                self.figure.tight_layout(pad=1.0, h_pad=0.8, w_pad=0.8)
            except Exception:
                pass
            buf = io.BytesIO()
            self.figure.savefig(buf, format='png', dpi=render_dpi, bbox_inches='tight',
                                facecolor='white', edgecolor='none', pad_inches=0.08)
            buf.seek(0)
            return base64.b64encode(buf.read()).decode('utf-8')
        finally:
            self.figure.set_dpi(orig_dpi)
            try:
                self.figure.tight_layout(pad=1.2, h_pad=1.0, w_pad=1.0)
            except Exception:
                pass
            self.canvas.draw()

    @staticmethod
    def _truncate(text, max_len=20):
        if len(text) > max_len:
            return text[:max_len - 1] + "..."
        return text

    @staticmethod
    def _wrap_label(text, max_line=18):
        """Перенос на 2 строки по границе слова (вместо усечения '...')"""
        if len(text) <= max_line:
            return text
        mid = len(text) // 2
        best = -1
        for i, ch in enumerate(text):
            if ch == ' ':
                if best == -1 or abs(i - mid) < abs(best - mid):
                    best = i
        if best > 0:
            return text[:best] + '\n' + text[best + 1:]
        return text[:max_line] + '\n' + text[max_line:]

    @staticmethod
    def _setup_hbar_axes(ax, n_items=None):
        """Настройка осей для горизонтальных баров — сетка по X, без Y.
        Если n_items задан — нормализует ylim для единой визуальной толщины баров."""
        ax.xaxis.grid(True)
        ax.yaxis.grid(False)
        if n_items is not None and n_items < _Theme.MIN_HBAR_ITEMS:
            extra = (_Theme.MIN_HBAR_ITEMS - n_items) / 2
            ax.set_ylim(-0.5 - extra, n_items - 0.5 + extra)

    @staticmethod
    def _setup_vbar_axes(ax, n_cats=None):
        """Настройка осей для вертикальных баров — сетка по Y, без X.
        Если n_cats задан — нормализует xlim для единой визуальной ширины баров."""
        ax.yaxis.grid(True)
        ax.xaxis.grid(False)
        if n_cats is not None and n_cats < _Theme.MIN_VBAR_CATS:
            extra = (_Theme.MIN_VBAR_CATS - n_cats) / 2
            ax.set_xlim(-0.5 - extra, n_cats - 0.5 + extra)


class FunnelBarChart(ChartBase):
    """Горизонтальная столбчатая диаграмма — воронка проектов"""

    _AXIS_LEFT = 0.22

    def __init__(self, parent=None):
        super().__init__("Воронка проектов", parent)
        self.setFixedHeight(260)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

    def set_data(self, funnel_dict):
        if not self.canvas or not funnel_dict:
            return

        n_items = len(funnel_dict)
        fig_h = max(3.5, n_items * 0.40 + 0.8)
        self.figure.set_size_inches(6, fig_h)
        pixel_h = max(260, int(fig_h * 100))
        self.setMinimumHeight(pixel_h)
        self.setFixedHeight(pixel_h)

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        sorted_items = sorted(funnel_dict.items(), key=lambda x: x[1])
        labels = [self._truncate(item[0], 25) for item in sorted_items]
        values = [item[1] for item in sorted_items]
        max_val = max(values) if values else 1

        bar_colors = [_Theme.PALETTE[i % len(_Theme.PALETTE)] for i in range(len(labels))]

        bars = ax.barh(labels, values, color=bar_colors,
                       height=_Theme.BAR_H_HORZ, edgecolor='none')
        self._apply_bar_gradient(ax, bars)

        for bar, val in zip(bars, values):
            ax.text(bar.get_width() + max_val * 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=_Theme.VALUE_SIZE,
                    fontweight='bold', color='#333')

        ax.set_xlim(right=max_val * 1.18)
        self._setup_hbar_axes(ax, n_items)
        # suptitle центрируется по всей фигуре (а не по осям)
        self.figure.suptitle(self.chart_title, fontsize=_Theme.TITLE_SIZE,
                             fontweight='bold', color='#333', x=0.5, y=0.95)

        self.figure.subplots_adjust(top=0.85, bottom=0.10)
        self._finalize()


class ExecutorLoadChart(ChartBase):
    """Горизонтальная столбчатая диаграмма — нагрузка на исполнителей"""

    _AXIS_LEFT = 0.22

    def __init__(self, parent=None):
        super().__init__("Нагрузка исполнителей", parent)

    def set_data(self, executor_list):
        if not self.canvas or not executor_list:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        sorted_data = sorted(executor_list, key=lambda x: x.get("active_stages", 0))
        names = [self._truncate(d["name"], 18) for d in sorted_data]
        stages = [d.get("active_stages", 0) for d in sorted_data]
        max_val = max(stages) if stages else 1

        def bar_color(val):
            if val >= 8:
                return '#E74C3C'
            elif val >= 5:
                return '#F5A623'
            return '#7ED321'

        colors = [bar_color(s) for s in stages]
        bars = ax.barh(names, stages, color=colors,
                       height=_Theme.BAR_H_HORZ, edgecolor='none')
        self._apply_bar_gradient(ax, bars)

        for bar, val in zip(bars, stages):
            ax.text(bar.get_width() + max_val * 0.03,
                    bar.get_y() + bar.get_height() / 2,
                    str(val), va='center', fontsize=_Theme.VALUE_SIZE,
                    fontweight='bold', color='#333')

        ax.set_xlim(right=max_val * 1.18)
        self._setup_hbar_axes(ax, len(sorted_data))
        ax.set_title(self.chart_title, fontsize=_Theme.TITLE_SIZE,
                     fontweight='bold', color='#333', pad=12)
        self._finalize()


class ProjectTypePieChart(ChartBase):
    """Donut-диаграмма с числом по центру — типы проектов"""

    _AXIS_LEFT = None

    def __init__(self, parent=None):
        super().__init__("Типы проектов", parent)

    def set_data(self, individual_count, template_count, supervision_count=0):
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
            colors.append(_Theme.COLOR_INDIVIDUAL)
        if template_count > 0:
            labels.append(f'Шаблонные ({template_count})')
            sizes.append(template_count)
            colors.append(_Theme.COLOR_TEMPLATE)
        if supervision_count > 0:
            labels.append(f'Надзор ({supervision_count})')
            sizes.append(supervision_count)
            colors.append(_Theme.COLOR_SUPERVISION)

        if not sizes:
            ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                    fontsize=_Theme.TITLE_SIZE, color='#999',
                    transform=ax.transAxes)
            ax.axis('off')
            self._finalize()
            return

        total = sum(sizes)
        import math

        wedges, _ = ax.pie(
            sizes, labels=None, colors=colors,
            startangle=90, counterclock=False,
            wedgeprops={'width': 0.35, 'edgecolor': 'white', 'linewidth': 3},
        )

        # Проценты на сегментах
        for wedge, val in zip(wedges, sizes):
            ang = (wedge.theta2 + wedge.theta1) / 2
            x = 0.82 * math.cos(math.radians(ang))
            y = 0.82 * math.sin(math.radians(ang))
            pct = val / total * 100
            ax.text(x, y, f'{pct:.0f}%', ha='center', va='center',
                    fontsize=10, fontweight='bold', color='white')

        # Белый круг в центре
        centre = plt.Circle((0, 0), 0.65, fc='white', linewidth=0)
        ax.add_artist(centre)

        # Число по центру
        ax.text(0, 0.06, str(total), ha='center', va='center',
                fontsize=28, fontweight='bold', color='#333')
        ax.text(0, -0.18, 'Всего', ha='center', va='center',
                fontsize=11, color='#999')

        # Легенда с правильными цветами
        legend_handles = [mpatches.Patch(facecolor=c, edgecolor='none', label=l)
                          for c, l in zip(colors, labels)]
        ax.legend(handles=legend_handles, loc='center left', bbox_to_anchor=(0.92, 0.5),
                  fontsize=_Theme.LEGEND_SIZE, frameon=False,
                  handlelength=1.2, handleheight=1.2)

        ax.set_aspect('equal')
        ax.set_title(self.chart_title, fontsize=_Theme.TITLE_SIZE,
                     fontweight='bold', color='#333', pad=12)
        self._finalize()


class SectionWidget(QFrame):
    """Контейнер секции с заголовком для страницы отчётов"""

    def __init__(self, title, description="", parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            SectionWidget {
                background-color: #FFFFFF;
                border: 1px solid #E8E8E8;
                border-radius: 12px;
            }
        """)

        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(16)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 25))
        self.setGraphicsEffect(shadow)

        outer_layout = QVBoxLayout()
        outer_layout.setContentsMargins(16, 14, 16, 14)
        outer_layout.setSpacing(10)

        title_label = QLabel(title, self)
        title_font = QFont("Segoe UI", 12, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #222; background-color: transparent;")
        outer_layout.addWidget(title_label)

        if description:
            desc_label = QLabel(description, self)
            desc_label.setStyleSheet("font-size: 11px; color: #888; background-color: transparent;")
            desc_label.setWordWrap(True)
            outer_layout.addWidget(desc_label)

        self.content_layout = QVBoxLayout()
        self.content_layout.setSpacing(10)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addLayout(self.content_layout)
        self.setLayout(outer_layout)

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)


class LineChartWidget(ChartBase):
    """Линейный график с градиентной заливкой и полыми маркерами"""

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)

    def set_data(self, series: list):
        if not self.canvas or not series:
            return

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        for i, s in enumerate(series):
            color = s.get("color") or _Theme.PALETTE[i % len(_Theme.PALETTE)]
            x_data = s.get("x", [])
            y_data = s.get("y", [])
            label = s.get("label", "")
            if not x_data or not y_data:
                continue

            x_idx = list(range(len(x_data)))
            ax.plot(x_idx, y_data, color=color, linewidth=2.5,
                    marker='o', markersize=7, markerfacecolor='white',
                    markeredgewidth=2, markeredgecolor=color,
                    label=label, zorder=5)

            # Градиентная заливка (4 слоя)
            for alpha, frac in [(0.03, 1.0), (0.05, 0.75), (0.07, 0.5), (0.06, 0.25)]:
                y_lower = [v * frac for v in y_data]
                ax.fill_between(x_idx, y_lower, y_data, alpha=alpha,
                                color=color, linewidth=0)

        if series and series[0].get("x"):
            x_labels = series[0]["x"]
            ax.set_xticks(range(len(x_labels)))
            ax.set_xticklabels(x_labels, fontsize=_Theme.TICK_SIZE)

        ax.yaxis.grid(True)
        ax.xaxis.grid(False)

        has_legend = self._add_legend_row(ax)

        if self.chart_title:
            pad = 26 if has_legend else 12
            ax.set_title(self.chart_title, fontsize=_Theme.TITLE_SIZE,
                         fontweight='bold', color='#333', pad=pad)

        self._finalize(legend_above=has_legend)


class StackedBarChartWidget(ChartBase):
    """Stacked/Grouped bar chart"""

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)

    def set_data(self, categories: list, series: list, stacked=True,
                 highlight_prefixes=None):
        if not self.canvas or not categories or not series:
            return

        n_cat = len(categories)

        # Размеры фигуры: шире для "Время стадий" с горизонтальными метками
        if highlight_prefixes and n_cat > 8:
            fig_w = max(6, n_cat * 0.43)
            fig_h = 4.2
        elif n_cat > 10:
            fig_w = 6
            fig_h = max(3.5, 3.5 + (n_cat - 10) * 0.12)
        else:
            fig_w = 6
            fig_h = 3.5
        self.figure.set_size_inches(fig_w, fig_h)
        self.setMinimumHeight(max(280, int(fig_h * 100)))

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        # Подготовка меток
        if highlight_prefixes:
            # "Время стадий": вертикальный текст в 2 строки (перенос вместо усечения)
            short_categories = [self._wrap_label(c, 18) for c in categories]
            rotation, ha = 90, 'right'
            tick_fontsize = 7.5
        else:
            max_orig_len = max((len(c) for c in categories), default=0)
            if max_orig_len > 5:
                rotation, ha, max_trunc = 90, 'right', 18
            else:
                rotation, ha, max_trunc = 0, 'center', 12
            short_categories = [self._truncate(c, max_trunc) for c in categories]
            tick_fontsize = _Theme.TICK_SIZE

        n_categories = len(short_categories)
        x = list(range(n_categories))

        all_bars = []

        if stacked:
            bottoms = [0.0] * n_categories
            for i, s in enumerate(series):
                color = s.get("color") or _Theme.PALETTE[i % len(_Theme.PALETTE)]
                values = s.get("values", [0] * n_categories)
                bars = ax.bar(x, values, bottom=bottoms, color=color,
                              label=s.get("label", ""), edgecolor='none',
                              width=_Theme.BAR_W_VERT, zorder=3)
                all_bars.extend(bars)
                for xi, val, bot in zip(x, values, bottoms):
                    if val > 0:
                        ax.text(xi, bot + val / 2, str(int(val)),
                                ha='center', va='center',
                                fontsize=_Theme.VALUE_SIZE - 1,
                                fontweight='bold', color='white', zorder=6)
                bottoms = [b + v for b, v in zip(bottoms, values)]
        else:
            n_series = len(series)
            total_w = min(_Theme.BAR_W_VERT * 1.6, 0.9)
            bar_width = total_w / n_series
            actual_w = bar_width * 0.75
            if highlight_prefixes and n_series == 2:
                # Узкие бары (÷1.5) прижаты друг к другу с зазором ~1px
                actual_w = actual_w / 1.5
                gap = 0.02  # ~1px в координатах данных
            for i, s in enumerate(series):
                color = s.get("color") or _Theme.PALETTE[i % len(_Theme.PALETTE)]
                values = s.get("values", [0] * n_categories)
                if highlight_prefixes and n_series == 2:
                    half = actual_w / 2 + gap / 2
                    if i == 0:
                        positions = [xi - half for xi in x]
                    else:
                        positions = [xi + half for xi in x]
                else:
                    offset = (i - n_series / 2 + 0.5) * bar_width
                    positions = [xi + offset for xi in x]
                bars = ax.bar(positions, values, width=actual_w,
                              color=color, label=s.get("label", ""),
                              edgecolor='none', zorder=3)
                all_bars.extend(bars)
                for pos, val in zip(positions, values):
                    if val > 0:
                        ax.text(pos, val + max(values) * 0.02, str(int(val)),
                                ha='center', va='bottom',
                                fontsize=_Theme.VALUE_SIZE - 1,
                                fontweight='bold', color='#555', zorder=6)

        self._apply_bar_gradient(ax, all_bars)

        ax.set_xticks(x)
        ax.set_xticklabels(short_categories, fontsize=tick_fontsize,
                           rotation=rotation, ha=ha)

        # Разделители и стили меток для "Время стадий"
        if highlight_prefixes:
            upper_prefixes = [p.upper() for p in highlight_prefixes]
            # Серые вертикальные разделители между группами стадий
            for i, cat in enumerate(categories):
                if i > 0 and any(cat.upper().startswith(p) for p in upper_prefixes):
                    ax.axvline(x=i - 0.5, color='#CCCCCC', linewidth=1.0,
                               linestyle='-', zorder=2)
            # Стили: стадии жирным+синим, подэтапы жирным+серым
            for label in ax.get_xticklabels():
                text_clean = label.get_text().replace('\n', ' ').upper()
                label.set_fontweight('bold')
                if any(text_clean.startswith(p) for p in upper_prefixes):
                    label.set_color('#2F5496')
                else:
                    label.set_color('#555')

        self._setup_vbar_axes(ax, n_categories)

        if stacked and bottoms and max(bottoms) > 0:
            ax.set_ylim(0, max(bottoms) * 1.15)

        has_legend = self._add_legend_row(ax)

        if self.chart_title:
            pad = 26 if has_legend else 12
            ax.set_title(self.chart_title, fontsize=_Theme.TITLE_SIZE,
                         fontweight='bold', color='#333', pad=pad)

        if highlight_prefixes:
            # Фиксированная ширина = ширине фигуры в пикселях.
            # Бары и подписи синхронизированы при постоянном размере фигуры.
            # Scroll area обеспечит прокрутку / центрирование.
            dpi = self.figure.get_dpi()
            chart_px_w = max(600, int(fig_w * dpi))
            chart_px_h = max(480, int(fig_h * dpi) + 60)
            self.setFixedSize(chart_px_w, chart_px_h)
            self._finalize(legend_above=has_legend,
                           bottom=0.25, left=0.04, right=0.99)
        else:
            self._finalize(legend_above=has_legend)


class HorizontalBarWidget(ChartBase):
    """Горизонтальный bar chart для ТОП-N или распределений"""

    _AXIS_LEFT = 0.22
    _AXIS_RIGHT = 0.92

    def __init__(self, title="", parent=None):
        super().__init__(title, parent)

    def set_data(self, labels: list, values: list, colors: list = None):
        if not self.canvas or not labels or not values:
            return

        n = len(labels)
        fig_h = max(3.5, n * 0.40 + 0.8)
        self.figure.set_size_inches(6, fig_h)
        self.setMinimumHeight(max(260, int(fig_h * 100)))

        self.figure.clear()
        ax = self.figure.add_subplot(111)

        paired = sorted(zip(values, labels), key=lambda x: x[0])
        sorted_values = [p[0] for p in paired]
        sorted_labels = [self._truncate(p[1], 18) for p in paired]
        max_val = max(sorted_values) if sorted_values else 1

        if colors:
            label_to_color = {lbl: colors[i % len(colors)] for i, lbl in enumerate(labels)}
            bar_colors = [label_to_color.get(lbl, _Theme.PALETTE[0]) for lbl in sorted_labels]
        else:
            bar_colors = [_Theme.PALETTE[i % len(_Theme.PALETTE)]
                          for i in range(len(sorted_labels))]

        bars = ax.barh(sorted_labels, sorted_values, color=bar_colors,
                       height=_Theme.BAR_H_HORZ, edgecolor='none')
        self._apply_bar_gradient(ax, bars)

        for bar, val in zip(bars, sorted_values):
            display = str(int(val)) if isinstance(val, float) and val == int(val) else str(val)
            ax.text(bar.get_width() + max_val * 0.02,
                    bar.get_y() + bar.get_height() / 2,
                    display, va='center', fontsize=_Theme.VALUE_SIZE,
                    fontweight='bold', color='#333')

        ax.set_xlim(right=max_val * 1.18)
        self._setup_hbar_axes(ax, n)

        if self.chart_title:
            ax.set_title(self.chart_title, fontsize=_Theme.TITLE_SIZE,
                         fontweight='bold', color='#333', pad=12)
        self._finalize()
