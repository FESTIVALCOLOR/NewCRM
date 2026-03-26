# Research: Визуальный рефакторинг графиков (Charts Visual Overhaul)

## Контекст задачи

Пользователь недоволен визуальным стилем графиков в ReportsTab — "прошлый век", "столбцы как нога слона".
Референсы: профессиональные дашборды (РПЛ, Instagram Analytics) с тонкими столбцами, компактными donut charts,
чистыми линейными графиками с градиентами.

**Стек:** Python 3.14 клиент, matplotlib 3.10.8, PyQt5, FigureCanvasQTAgg, ReportLab 4.4.9.
**Ограничение:** только matplotlib, не plotly/bokeh.

---

## 1. Архитектура стилизации matplotlib

### 1.1 Текущее состояние ChartBase

Файл: `ui/chart_widget.py` (567 строк).

Проблемы текущей реализации:
- `Figure(figsize=(6, 3.5), dpi=100)` — стандартный размер, не адаптируется под тип графика
- Стили прописаны inline в каждом `set_data()` — нет единого источника истины
- `bar height=0.6` (horz), `bar width=0.5` (vert) — слишком жирные, "нога слона"
- Цвета FunnelBarChart: `#ffd93c`, `#F39C12` и т.д. — не согласованы с основной палитрой ProjectTypePieChart
- Grid: `linestyle='--', alpha=0.3, color='#DDD'` — нормально, но можно лучше
- Легенда: `framealpha=0.9` с рамкой — устаревший вид
- Pie chart в ProjectTypePieChart: не donut, `wedgeprops={'width': 0.65}` — уже полу-donut, но без внутреннего текста по центру

### 1.2 Рекомендуемая архитектура: ChartTheme (единый центр стилей)

Создать класс `ChartTheme` в `ui/chart_widget.py` (или отдельным модулем) со статическими константами и методом `apply(ax)`:

```python
class ChartTheme:
    """Единая система стилей для всех matplotlib-графиков проекта."""

    # Палитра — harmonized с основной палитрой (#ffd93c primary)
    # Muted professional colors: достаточно насыщены, но не кричащие
    PALETTE = [
        '#4C9BE8',   # синий   — основной
        '#E8854C',   # оранжевый
        '#4CBE7A',   # зелёный
        '#B07FE8',   # фиолетовый
        '#E84C6F',   # красный/малиновый
        '#4CCBCB',   # бирюзовый
        '#E8C84C',   # жёлтый (accent совпадает с #ffd93c)
        '#7F9BB0',   # стальной серый
    ]

    # Семантические цвета
    COLOR_INDIVIDUAL = '#4C9BE8'   # индивидуальные проекты
    COLOR_TEMPLATE   = '#E8854C'   # шаблонные
    COLOR_SUPERVISION = '#4CBE7A'  # надзор
    COLOR_SUCCESS    = '#4CBE7A'
    COLOR_WARNING    = '#F5A623'
    COLOR_DANGER     = '#E84C6F'
    COLOR_NEUTRAL    = '#9EA8B3'

    # Типография
    FONT_TITLE   = 10      # Заголовок графика (внутри matplotlib)
    FONT_LABEL   = 8       # Подписи осей
    FONT_TICK    = 7       # Тики
    FONT_VALUE   = 7.5     # Значения на барах
    FONT_LEGEND  = 7.5

    # Сетка
    GRID_COLOR     = '#EBEBEB'
    GRID_ALPHA     = 0.8
    GRID_LINEWIDTH = 0.5
    GRID_LINESTYLE = ':'   # пунктир — более современный вид, чем '--'

    # Spines
    SPINE_COLOR  = '#D8D8D8'
    SPINE_WIDTH  = 0.8

    # Бары
    BAR_WIDTH_VERT  = 0.38   # вертикальные (ранее 0.5 — слишком жирные)
    BAR_WIDTH_HORZ  = 0.55   # горизонтальные (ранее 0.6)
    BAR_RADIUS      = 3      # скругление углов (matplotlib 3.9+: bar(..., capstyle='round'))
    BAR_EDGE_COLOR  = 'none' # без обводки — современный стиль

    # Линейные графики
    LINE_WIDTH       = 2.0
    LINE_MARKER_SIZE = 5
    LINE_FILL_ALPHA  = 0.10  # заливка под линией

    @classmethod
    def apply(cls, ax, has_grid_x=False, has_grid_y=True):
        """Применить тему к axes."""
        # Фон
        ax.set_facecolor('white')

        # Spines
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(cls.SPINE_COLOR)
        ax.spines['left'].set_linewidth(cls.SPINE_WIDTH)
        ax.spines['bottom'].set_color(cls.SPINE_COLOR)
        ax.spines['bottom'].set_linewidth(cls.SPINE_WIDTH)

        # Ticks
        ax.tick_params(axis='both', labelsize=cls.FONT_TICK, length=3,
                       color=cls.SPINE_COLOR, pad=3)

        # Grid
        if has_grid_y:
            ax.grid(axis='y', linestyle=cls.GRID_LINESTYLE,
                    linewidth=cls.GRID_LINEWIDTH, color=cls.GRID_COLOR,
                    alpha=cls.GRID_ALPHA, zorder=0)
            ax.set_axisbelow(True)
        if has_grid_x:
            ax.grid(axis='x', linestyle=cls.GRID_LINESTYLE,
                    linewidth=cls.GRID_LINEWIDTH, color=cls.GRID_COLOR,
                    alpha=cls.GRID_ALPHA, zorder=0)
            ax.set_axisbelow(True)

    @classmethod
    def apply_legend(cls, ax, **kwargs):
        """Легенда без рамки, компактная."""
        handles, labels = ax.get_legend_handles_labels()
        if not handles:
            return
        default_kw = dict(
            fontsize=cls.FONT_LEGEND,
            frameon=False,         # без рамки — современный стиль
            loc='upper right',
            handlelength=1.2,
            handleheight=0.8,
            borderpad=0.4,
            labelspacing=0.35,
        )
        default_kw.update(kwargs)
        ax.legend(**default_kw)
```

### 1.3 rcParams — глобальные настройки

Применять один раз при старте приложения (в `main.py` до создания QApplication или в `chart_widget.py` на уровне модуля):

```python
import matplotlib as mpl

mpl.rcParams.update({
    # Шрифты — системный Segoe UI (Windows) или sans-serif
    'font.family':        'sans-serif',
    'font.sans-serif':    ['Segoe UI', 'Arial', 'Helvetica', 'DejaVu Sans'],
    'font.size':          8,
    'axes.titlesize':     10,
    'axes.titleweight':   'bold',
    'axes.titlepad':      8,
    'axes.labelsize':     8,
    'axes.labelcolor':    '#555555',

    # Spines глобально
    'axes.spines.top':    False,
    'axes.spines.right':  False,
    'axes.edgecolor':     '#D8D8D8',
    'axes.linewidth':     0.8,
    'axes.facecolor':     'white',
    'figure.facecolor':   'white',

    # Grid — выключен по умолчанию, включаем в apply()
    'axes.grid':          False,

    # Ticks
    'xtick.major.size':   3,
    'xtick.major.width':  0.7,
    'ytick.major.size':   3,
    'ytick.major.width':  0.7,
    'xtick.color':        '#888888',
    'ytick.color':        '#888888',
    'xtick.labelsize':    7,
    'ytick.labelsize':    7,

    # Линии
    'lines.linewidth':    2.0,
    'patch.linewidth':    0.5,

    # Легенда
    'legend.frameon':     False,
    'legend.fontsize':    7.5,
    'legend.borderpad':   0.4,
    'legend.handlelength': 1.2,
})
```

**Важно для PyQt5:** rcParams применять **после** `matplotlib.use('Qt5Agg')` и **до** первого создания Figure. В текущем `chart_widget.py` — вынести в блок `try: MATPLOTLIB_AVAILABLE = True` перед классами.

---

## 2. Паттерны визуализации по типам графиков

### 2.1 Вертикальные Bar Charts (StackedBarChartWidget)

**Текущая проблема:** `width=0.5` — жирно. При stacked — каждая секция не читается.

**Рекомендации:**

```python
# Ширина столбца
BAR_WIDTH = 0.38  # для >= 6 категорий
BAR_WIDTH = 0.45  # для < 6 категорий

# Для stacked — убрать edgecolor (разделение секций через небольшой зазор)
# Между секциями — linewidth=0.8, color='white'

# При grouped — ширина каждого столбца в группе:
bar_width = 0.38 / n_series  # НЕ делить на n_series от 0.5!

# Скругление верхних углов (matplotlib 3.9+ через bar_label или patches):
# Использовать FancyBboxPatch для современного вида:
from matplotlib.patches import FancyBboxPatch
# Или проще — оставить без скругления, но уменьшить ширину
```

**Оптимальная ширина (исследование):**
- `0.3` — очень тонкие, "Instagram story stats" стиль
- `0.35–0.40` — современный аналитический дашборд (РПЛ, Google Analytics)
- `0.50–0.60` — стандартный matplotlib (устаревший вид)
- `0.70–0.80` — "нога слона"

**Рекомендуемое значение для проекта: `0.38`** для вертикальных, `0.55` для горизонтальных.

### 2.2 Горизонтальные Bar Charts (FunnelBarChart, HorizontalBarWidget, ExecutorLoadChart)

**Текущая проблема:** `height=0.6` слишком толстые для горизонтальных.

```python
# Высота горизонтального бара
BAR_HEIGHT = 0.55   # было 0.6 — небольшое уменьшение

# Закруглённые концы через capstyle (не поддерживается в barh напрямую)
# Альтернатива — добавить маленький scatter на конце:
ax.scatter(values, range(n), s=100, color=bar_colors,
           zorder=5, marker='|')  # не лучший вариант

# Лучший способ для скруглённых концов — FancyBboxPatch:
for i, (val, clr) in enumerate(zip(values, colors)):
    bar = FancyBboxPatch(
        (0, i - 0.25), val, 0.5,
        boxstyle="round,pad=0,rounding_size=0.12",
        facecolor=clr, edgecolor='none'
    )
    ax.add_patch(bar)
```

**Значения на барах:** размещать внутри бара при val > 20% max, снаружи при малых значениях.

### 2.3 Donut Chart (ProjectTypePieChart)

**Текущее состояние:** уже есть `wedgeprops={'width': 0.65}` — почти donut. Проблемы:
1. Autopct на внешних сегментах — читается плохо
2. Нет легенды снаружи (легенда встроена в labels=labels)
3. Нет числа в центре доната (total)

**Рекомендуемая реализация donut:**

```python
def set_data(self, individual_count, template_count, supervision_count=0):
    """Modern donut chart с легендой снаружи и числом в центре."""
    self.figure.clear()
    ax = self.figure.add_subplot(111)
    ax.set_facecolor('white')

    # Данные
    data   = [x for x in [individual_count, template_count, supervision_count] if x > 0]
    labels = [lbl for lbl, x in [
        ('Индивид.', individual_count),
        ('Шаблон.',  template_count),
        ('Надзор',   supervision_count)
    ] if x > 0]
    colors = [
        ChartTheme.COLOR_INDIVIDUAL,
        ChartTheme.COLOR_TEMPLATE,
        ChartTheme.COLOR_SUPERVISION,
    ][:len(data)]

    total = sum(data)
    if not data:
        ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center',
                fontsize=10, color='#999', transform=ax.transAxes)
        self._finalize()
        return

    wedges, _, autotexts = ax.pie(
        data,
        colors=colors,
        autopct='%1.0f%%',
        startangle=90,
        pctdistance=0.75,      # проценты внутри кольца
        wedgeprops={
            'width': 0.52,     # толщина кольца — компактный donut
            'edgecolor': 'white',
            'linewidth': 2.5,  # белый зазор между секциями
        },
        textprops={'fontsize': 0},  # скрыть labels (заменяем легендой)
    )

    # Стилизация текста процентов
    for at in autotexts:
        at.set_fontsize(7.5)
        at.set_fontweight('bold')
        at.set_color('white')

    # Число в центре
    ax.text(0, 0, str(total), ha='center', va='center',
            fontsize=14, fontweight='bold', color='#333')
    ax.text(0, -0.18, 'всего', ha='center', va='center',
            fontsize=7, color='#888')

    # Легенда снаружи — справа, без рамки
    ax.legend(
        wedges,
        [f'{lbl} ({cnt})' for lbl, cnt in zip(labels, data)],
        loc='center left',
        bbox_to_anchor=(0.95, 0, 0.5, 1.0),
        frameon=False,
        fontsize=7.5,
        labelspacing=0.6,
    )

    self._finalize()
```

**Ключевые параметры donut:**
| Параметр | Рекомендуемое | Описание |
|---|---|---|
| `wedgeprops width` | `0.52` | Компактное кольцо (0.45 = тонкое, 0.65 = толстое) |
| `pctdistance` | `0.75` | Проценты на 3/4 пути к краю (внутри кольца) |
| `linewidth` (edge) | `2.5` | Белый зазор между секциями |
| `startangle` | `90` | Начало с 12 часов |
| Центральный текст | total + подпись | Добавляет информативность |
| Легенда `bbox_to_anchor` | `(0.95, 0, 0.5, 1.0)` | Справа от donut |

### 2.4 Линейный График с Градиентной Заливкой (LineChartWidget)

**Текущее состояние:** `fill_between` с `alpha=0.12` — почти нормально, но градиент отсутствует.

**Градиентная заливка через imshow + clip_path:**

```python
# Метод 1: Простой — несколько fill_between с убывающей alpha
def _add_gradient_fill(ax, x_numeric, y_data, color, n_steps=8):
    """Градиентная заливка под линией через стек полупрозрачных слоёв."""
    y_min = min(0, min(y_data) * 0.9)
    for i in range(n_steps):
        alpha = 0.08 * (1 - i / n_steps)
        y_threshold = y_min + (max(y_data) - y_min) * (i / n_steps)
        ax.fill_between(x_numeric, y_threshold, y_data,
                        where=[y > y_threshold for y in y_data],
                        color=color, alpha=alpha, zorder=1)

# Метод 2: Через imshow (настоящий градиент) — сложнее, но красивее
import numpy as np
from matplotlib.colors import to_rgba

def _add_true_gradient_fill(ax, x_numeric, y_data, color, alpha_top=0.25, alpha_bottom=0.0):
    """Настоящий вертикальный градиент под линией через imshow."""
    from matplotlib.patches import PathPatch
    from matplotlib.path import Path

    # Создаём маску пути
    verts = list(zip(x_numeric, y_data))
    verts.append((x_numeric[-1], 0))
    verts.append((x_numeric[0], 0))
    verts.append((x_numeric[0], y_data[0]))
    codes = [Path.MOVETO] + [Path.LINETO] * (len(verts) - 1)
    path = Path(verts, codes)
    patch = PathPatch(path, facecolor='none', edgecolor='none')
    ax.add_patch(patch)

    # Градиентный imshow
    rgba_top    = to_rgba(color, alpha=alpha_top)
    rgba_bottom = to_rgba(color, alpha=alpha_bottom)
    grad = np.array([[rgba_top], [rgba_bottom]])
    ax.imshow(grad, aspect='auto', extent=[x_numeric[0], x_numeric[-1],
              min(0, min(y_data)), max(y_data)],
              origin='upper', clip_path=patch, clip_on=True, zorder=1)
```

**Рекомендация для проекта:** Метод 1 (простой fill_between) достаточен и нет проблем с совместимостью. Параметры:
- `alpha` для fill: `0.12–0.15` (не больше — отвлекает от линий)
- `linewidth`: `2.0–2.2` (немного тоньше текущего `2.5`)
- Маркеры: `markersize=4`, `markerfacecolor='white'`, `markeredgewidth=1.5` — "полые" маркеры

### 2.5 Stacked Bar Chart — альтернативный подход

Для stacked bar рекомендуется убрать числовые подписи внутри секций если секции малы.
Порог: отображать подпись только если `val / total > 0.08` (8% и более).

---

## 3. Пропорции figsize и layout в embedded matplotlib

### 3.1 Проблема tight_layout vs subplots_adjust в PyQt5

**Конфликт:** `tight_layout()` пересчитывает отступы автоматически и перезаписывает `subplots_adjust()` если вызван после. Текущий `_finalize()` делает это правильно: сначала `tight_layout`, потом `subplots_adjust`. Но это хрупкое решение.

**Рекомендация — использовать `constrained_layout`:**

```python
# В ChartBase.__init__:
self.figure = Figure(figsize=(6, 3.5), dpi=100, constrained_layout=True)
# constrained_layout заменяет tight_layout и работает лучше
# НО: несовместим с subplots_adjust() — нужно выбрать одно
```

**Для проекта:** оставить текущий подход (`tight_layout` + `subplots_adjust`) — он проверен. Добавить `try/except` вокруг обоих вызовов (уже есть). Уточнить `pad`:
- `tight_layout(pad=1.0)` вместо `1.2` — чуть меньше отступов
- `subplots_adjust(left=0.13, right=0.97, top=0.92, bottom=0.12)` — для большинства графиков

### 3.2 Оптимальные figsize для embedded графиков

| Тип графика | figsize (w, h) | Обоснование |
|---|---|---|
| Горизонтальный bar (до 8 элем.) | `(6, 3.5)` | Текущий — ок |
| Горизонтальный bar (авто) | `(6, n * 0.35 + 0.6)` | Текущий — ок |
| Вертикальный bar / stacked | `(6, 3.2)` | Чуть ниже — бары выглядят пропорциональнее |
| Линейный график | `(6, 3.0)` | Широкий и невысокий — как в аналитике |
| Donut / Pie | `(5, 3.5)` | Квадратнее для pie |
| Воронка (funnel) | `(6, авто)` | Текущий — ок |

**DPI:** `100` для экрана нормально. Не повышать до `150` — QWidget растянет canvas и пиксели будут некрасивы. DPI `150` только для `savefig` (PDF-экспорт).

### 3.3 Видимость подписей (clip_on, xlim, ylim padding)

**Проблема:** подписи значений на барах обрезаются при маленьком xlim/ylim.

```python
# Для горизонтальных баров — обязательный padding справа:
max_val = max(values)
ax.set_xlim(right=max_val * 1.18)  # 18% запаса (текущее 1.15 — минимум)

# Для вертикальных баров — padding сверху:
ax.set_ylim(top=max_val * 1.20)

# clip_on=False для текстовых аннотаций:
ax.text(..., clip_on=False)

# Проверка что anotation не вылезает за figure:
# После draw() можно проверить через fig.get_window_extent()
# На практике: достаточно увеличить right/top margin
```

### 3.4 Legend — позиционирование

```python
# Современные паттерны:

# 1. Внутри графика, без рамки (для bar/line с местом)
ax.legend(frameon=False, loc='upper right', fontsize=7.5)

# 2. Снаружи справа (для donut, для графиков с плотными данными)
ax.legend(
    loc='center left',
    bbox_to_anchor=(1.02, 0.5),
    frameon=False,
    fontsize=7.5,
    borderaxespad=0,
)
# ВАЖНО: при bbox_to_anchor за пределами axes нужно:
fig.subplots_adjust(right=0.75)  # освободить место справа

# 3. Снизу (для stacked bar с 3+ сериями)
ax.legend(
    loc='upper center',
    bbox_to_anchor=(0.5, -0.15),
    frameon=False,
    ncol=3,
    fontsize=7.5,
)
# ВАЖНО: subplots_adjust(bottom=0.20) для места под легендой
```

### 3.5 Grid — современный стиль

```python
# Современный: очень тонкие пунктирные (':') или штрих-пунктирные ('-.')
ax.grid(axis='y', linestyle=':', linewidth=0.5, color='#E0E0E0', alpha=1.0, zorder=0)
ax.set_axisbelow(True)  # grid под данными (не поверх баров)

# НЕ рекомендуется: '--' (длинный дефис) — слишком заметный
# НЕ рекомендуется: alpha=0.3 с плотным цветом — еле видно, цели не достигает
```

### 3.6 Spines — что убирать, что оставлять

**Минималистичный современный подход:**
- `top` — всегда `visible=False`
- `right` — всегда `visible=False`
- `left` — оставить, цвет `#D8D8D8` (очень светлый)
- `bottom` — оставить, цвет `#D8D8D8`

**Для горизонтальных bar charts:**
- Можно убрать и `left` spine (у Y-оси нет смысла если метки читаются без неё)
- Оставить только `bottom` с цветом `#D8D8D8`

---

## 4. Цветовые палитры — modern muted vs яркие

### 4.1 Анализ текущей палитры

Текущая палитра в проекте (FunnelBarChart):
```python
['#ffd93c', '#F39C12', '#27AE60', '#3498DB', '#9B59B6',
 '#E74C3C', '#1ABC9C', '#34495E', '#95A5A6', '#D35400']
```

Проблемы:
1. `#ffd93c` (жёлтый) — основной цвет приложения, использован как категориальный цвет
2. `#34495E` (тёмно-серый) — очень тёмный, выбивается из ряда
3. Контрастность неравномерна — некоторые цвета "кричат"

### 4.2 Рекомендуемая палитра: Professional Muted

Вдохновение: Tableau 10 + Instagram Analytics muted + RPL Dashboard.

```python
# Основная палитра (8 цветов, muted, хорошо читаются на белом фоне)
PALETTE_MAIN = [
    '#5B9BD5',  # синий      (как Tableau tab:blue, но чуть светлее)
    '#ED7D31',  # оранжевый  (Tableau tab:orange, muted)
    '#70AD47',  # зелёный    (Tableau tab:green, muted)
    '#A569BD',  # фиолетовый (muted purple)
    '#F1948A',  # розово-красный (salmon, мягкий)
    '#45B9C6',  # тeal       (бирюзовый, современный)
    '#F5C842',  # жёлтый     (чуть темнее #ffd93c — для категорий)
    '#839192',  # серый      (нейтральный)
]

# Семантические цвета для ExecutorLoadChart (нагрузка)
COLOR_LOW      = '#70AD47'   # нормальная (<5)
COLOR_MEDIUM   = '#F5C842'   # средняя (5–7)
COLOR_HIGH     = '#ED7D31'   # высокая (8–10)
COLOR_CRITICAL = '#E84C6F'   # критическая (>10)

# Фиксированные цвета типов проектов
COLOR_INDIVIDUAL  = '#5B9BD5'  # Индивидуальные — синий
COLOR_TEMPLATE    = '#ED7D31'  # Шаблонные — оранжевый
COLOR_SUPERVISION = '#70AD47'  # Надзор — зелёный
```

**Принципы выбора muted palettes:**
- Насыщенность (S в HSL): 40–60% (не 80-100% как яркие)
- Светлота (L в HSL): 45–65%
- Цвета должны быть различимы при малом размере (учёт для bar width=0.38)
- Проверить на colorblindness (не ставить красный рядом с зелёным без текстовой метки)

---

## 5. PDF Экспорт matplotlib → ReportLab

### 5.1 Текущая реализация `_chart_to_rl_image`

Анализ кода `reports_tab.py:1241–1314`:

**Что работает правильно:**
- Временный ресайз figure под целевые мм
- Восстановление оригинального размера в `finally`
- `bbox_inches='tight'` + `pad_inches=0.04` — компактный рендер
- `facecolor='white'` — белый фон (не прозрачный)

**Что можно улучшить:**

```python
# Оптимальный DPI для PDF:
# - 150 DPI — хороший баланс качество/размер файла
# - 200 DPI — для большой площади (A3)
# - 100 DPI — слишком мало для печати
# Рекомендация: оставить 150, это верно

# Для парных графиков — гарантировать одинаковую высоту:
# Текущий HALF_H = int(col_w * 0.45) — корректно
# Но передавать height_mm явно в _chart_to_rl_image:
img1 = self._chart_to_rl_image(chart1, col_w, height_mm=HALF_H)
img2 = self._chart_to_rl_image(chart2, col_w, height_mm=HALF_H)
# Это уже реализовано — правильно

# Проблема: если figure содержит легенду снаружи (bbox_to_anchor),
# tight_layout внутри _chart_to_rl_image может её обрезать.
# Решение: использовать bbox_inches='tight' БЕЗ tight_layout перед savefig,
# или передавать bbox_extra_artists=[legend_handle]:
fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
            bbox_extra_artists=ax.get_legend() and [ax.get_legend()] or [],
            facecolor='white', edgecolor='none', pad_inches=0.06)
```

### 5.2 KeepTogether и CondPageBreak с графиками

```python
from reportlab.platypus import KeepTogether, CondPageBreak, Spacer

# KeepTogether — хранит набор flowables вместе (не разрывает по странице)
# Ограничение: работает только если весь блок помещается на одну страницу.
# Если содержимое > высоты страницы — ReportLab игнорирует KeepTogether.

# Правильный паттерн для секции с графиком:
elements.append(CondPageBreak(inch * 4))  # перенос если < 4" на текущей странице
elements.append(KeepTogether([
    header_flowable,
    Spacer(1, 6 * mm),
    chart_table,          # Table с парой графиков
    Spacer(1, 4 * mm),
]))

# CondPageBreak(height) — переносит страницу если осталось < height
# Оптимальные значения:
# - Для пары графиков 60мм высотой: CondPageBreak(75 * mm)
# - Для KPI-строки: CondPageBreak(30 * mm)
# - Для заголовка секции: CondPageBreak(20 * mm)
```

### 5.3 Одинаковая высота парных графиков

**Проблема:** при авто-высоте из пропорций figure два соседних графика имеют разную высоту.

**Текущее решение:** `HALF_H = int(col_w * 0.45)` — фиксированная высота для всех парных. Это правильно.

**Но:** для `FunnelBarChart` и `HorizontalBarWidget` с авто-высотой (много элементов) это не работает — их нельзя ставить в пару с фиксированной высотой.

```python
# Алгоритм правильной раскладки:
def _pdf_chart_flowables(self, charts, page_w_mm):
    GAP_MM = 6
    col_w  = (page_w_mm - GAP_MM) / 2
    PAIR_H = col_w * 0.45   # ~60мм для landscape A4

    pairs = []
    single = None

    for chart in charts:
        if self._is_wide_chart(chart):
            # Широкий — рендерим отдельно, авто-высота
            img = self._chart_to_rl_image(chart, page_w_mm)
            pairs.append([img])
        elif single is None:
            single = chart   # ждём пару
        else:
            # Есть пара — рендерим с одинаковой высотой
            img1 = self._chart_to_rl_image(single, col_w, height_mm=PAIR_H)
            img2 = self._chart_to_rl_image(chart,  col_w, height_mm=PAIR_H)
            pairs.append([img1, img2])
            single = None

    if single:
        # Непарный — рендерим на пол-ширины или на полную
        img = self._chart_to_rl_image(single, col_w, height_mm=PAIR_H)
        pairs.append([img, None])

    # Сборка в ReportLab Table
    ...
```

### 5.4 Корректный рендер русского текста в matplotlib → PDF

При экспорте в PNG через `savefig` кириллица рендерится через шрифт matplotlib (DejaVu), который поддерживает кириллицу — проблем нет. Но если `font.family = 'Segoe UI'` (Windows), нужно убедиться что Segoe UI есть в системе. Fallback на DejaVu гарантирован через `font.sans-serif`.

---

## 6. Применение к конкретным классам ChartBase

### 6.1 Матрица изменений

| Класс | Текущая проблема | Изменение |
|---|---|---|
| `FunnelBarChart` | `height=0.6`, пёстрая палитра | `height=0.52`, PALETTE_MAIN |
| `ExecutorLoadChart` | `height=0.6`, нет деления "средняя" | `height=0.52`, 4 уровня цвета |
| `ProjectTypePieChart` | Pie, не donut, labels на секторах | Full donut rewrite |
| `LineChartWidget` | `fill_between alpha=0.12` ok, маркеры | Hollow markers, тоньше линия |
| `StackedBarChartWidget` | `width=0.5`, числа в узких секциях | `width=0.38`, порог отображения |
| `HorizontalBarWidget` | `height=0.6`, мультицвет | `height=0.52`, PALETTE_MAIN |

### 6.2 Единый вызов ChartTheme.apply()

После рефакторинга каждый `set_data()` начинается с:
```python
self.figure.clear()
ax = self.figure.add_subplot(111)
ChartTheme.apply(ax, has_grid_y=True)  # или has_grid_x=True для горизонтальных
```

И заканчивается:
```python
if self.chart_title:
    ax.set_title(self.chart_title, fontsize=ChartTheme.FONT_TITLE,
                 fontweight='bold', color='#2C2C2C', pad=8)
ChartTheme.apply_legend(ax)
self._finalize()
```

---

## 7. Сводка рекомендаций

### Приоритет 1 (визуальный эффект максимальный)
1. **Тонкие бары:** `width 0.5→0.38` (vert), `height 0.6→0.52` (horz) — сразу бросается в глаза
2. **Donut вместо pie:** `ProjectTypePieChart` — центральная цифра + легенда снаружи
3. **Новая палитра:** PALETTE_MAIN (muted professional) вместо текущей пёстрой

### Приоритет 2 (polish)
4. **Grid:** `linestyle=':'`, `linewidth=0.5` + `set_axisbelow(True)`
5. **Легенда без рамки:** `frameon=False` везде
6. **rcParams** один раз при старте — унифицирует шрифты

### Приоритет 3 (архитектура)
7. **ChartTheme класс** — единый источник констант стиля
8. **Gradient fill** в LineChartWidget — опционально

### Что НЕ менять
- `tight_layout + subplots_adjust` паттерн — работает, не трогать
- `FigureCanvasQTAgg` backend — стандарт для PyQt5
- DPI=100 для экрана, DPI=150 для PDF — правильно
- `_chart_to_rl_image` логика с ресайзом figure — верная
- `figsize=(6, 3.5)` как базовый — нормально, по нему canvas масштабируется

---

## Источники

- [Matplotlib Style Sheets — официальная документация](https://matplotlib.org/stable/users/explain/customizing.html)
- [Pie and Donut Labels — Matplotlib Gallery](https://matplotlib.org/stable/gallery/pie_and_polar_charts/pie_and_donut_labels.html)
- [Fill Between Alpha — Matplotlib Gallery](https://matplotlib.org/stable/gallery/lines_bars_and_markers/fill_between_alpha.html)
- [Bar Chart Width — Statology](https://www.statology.org/matplotlib-bar-width/)
- [Bar Chart Spacing — Saturn Cloud](https://saturncloud.io/blog/matplotlib-bar-chart-spacing-out-bars-for-better-data-visualization/)
- [Matplotlib in PyQt5 — pythonguis.com](https://www.pythonguis.com/tutorials/plotting-matplotlib/)
- [Tight Layout Guide — Matplotlib](https://matplotlib.org/stable/users/explain/axes/tight_layout_guide.html)
- [Constrained Layout Guide — Matplotlib](https://matplotlib.org/stable/users/explain/axes/constrainedlayout_guide.html)
- [Seaborn Color Palettes](https://seaborn.pydata.org/tutorial/color_palettes.html)
- [ReportLab Userguide PDF](https://www.reportlab.com/docs/reportlab-userguide.pdf)
- [Donut Chart — how2matplotlib.com](https://how2matplotlib.com/donut-chart-using-matplotlib-in-python)
