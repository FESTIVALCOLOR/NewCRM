# Исследование: Красивые графики matplotlib/PyQt5 — GitHub и документация

**Дата:** 2026-02-28
**Цель:** Собрать конкретные техники и примеры кода для редизайна графиков в ReportsTab

---

## 1. Найденные репозитории и ресурсы

### GitHub Topics
- **matplotlib-style-sheets:** https://github.com/topics/matplotlib-style-sheets
- **matplotlib-styles:** https://github.com/topics/matplotlib-styles
- **pyqt5-gui:** https://github.com/topics/pyqt5-gui

### Ключевые библиотеки и проекты

| Библиотека | Описание | Ссылка |
|---|---|---|
| **matplotx** | Минималистичные стили dufte, dufte_bar; Tableau/Dracula/Nord палитры | https://github.com/nschloe/matplotx |
| **mplcyberpunk** | Cyberpunk-стиль с neon glow-эффектами | https://github.com/dhaitz/mplcyberpunk |
| **opinionated** | Простые чистые стили для matplotlib/seaborn | https://github.com/MNoichl/opinionated |
| **dark-matplotlib-styles** | Коллекция тёмных стилей | https://github.com/akasharidas/dark-matplotlib-styles |
| **prettyplotlib** | Красивые matplotlib-графики по Tufte | https://github.com/olgabot/prettyplotlib |
| **PyQt5_Matplotlib** | Desktop app с PyQt5+matplotlib | https://github.com/idevloping/PyQt5_Matplotlib |

---

## 2. Ответы на ключевые вопросы

### 2.1 Скруглённые bar charts (FancyBboxPatch)

**Техника:** Заменить каждый `Rectangle` бара на `FancyBboxPatch` (скруглённый верх) + `Rectangle` (прямоугольный низ, чтобы скругление было только сверху).

**Источник:** https://discourse.matplotlib.org/t/new-to-matplotlib-how-to-round-the-edges-of-the-bars-in-a-bar-plot-in-matplotlib/24230

```python
import numpy as np
from matplotlib.patches import FancyBboxPatch, Rectangle
import matplotlib.pyplot as plt

values = [20, 5, 80, 30, 55]
labels = ['a', 'b', 'c', 'd', 'e']
max_val = max(values)

fig, ax = plt.subplots(figsize=(8, 5))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

# Параметры скругления
bar_width = 0.5
rounding_size = 0.2   # размер скругления в единицах данных
pad_factor = 0        # padding

bars = ax.bar(x=labels, height=values, color='#4F81E1', width=bar_width)

for bar in bars:
    h = bar.get_height()
    if h > rounding_size * max_val:
        # Скруглённый верх (FancyBboxPatch)
        round_top = FancyBboxPatch(
            xy=bar.get_xy(),
            width=bar.get_width(),
            height=h,
            color=bar.get_facecolor(),
            boxstyle=f"round,pad={pad_factor},rounding_size={rounding_size}",
            transform=ax.transData,
            mutation_scale=1.1,
            mutation_aspect=20,   # ВАЖНО: отношение высоты к ширине оси
        )
        # Прямоугольный низ (перекрывает нижнее скругление)
        square_bottom = Rectangle(
            xy=bar.get_xy(),
            width=bar.get_width(),
            height=h / 2,
            color=bar.get_facecolor(),
            transform=ax.transData,
        )
        bar.remove()
        ax.add_patch(round_top)
        ax.add_patch(square_bottom)

# Стиль осей
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#DDDDDD')
ax.tick_params(bottom=False, left=False)
ax.set_axisbelow(True)
ax.yaxis.grid(True, color='#EEEEEE')
ax.xaxis.grid(False)

plt.tight_layout()
plt.show()
```

**Важные замечания:**
- `mutation_aspect` — критический параметр: задаёт соотношение осей для правильного скругления (без него круг будет эллипсом)
- `rounding_size` задаётся в единицах данных оси Y
- Патч `square_bottom` нужен, чтобы скругление не было виндо внизу бара

---

### 2.2 Градиентные bar charts (gradient bars через imshow)

**Техника:** `ax.imshow()` с `extent` = размер бара + `cmap` + `aspect='auto'`.

**Источник:** https://matplotlib.org/stable/gallery/lines_bars_and_markers/gradient_bar.html

```python
import matplotlib.pyplot as plt
import numpy as np

def gradient_image(ax, direction=0.3, cmap_range=(0, 1), **kwargs):
    """
    Рисует градиентный прямоугольник через imshow.
    direction=0 → вертикальный, direction=1 → горизонтальный
    """
    phi = direction * np.pi / 2
    v = np.array([np.cos(phi), np.sin(phi)])
    X = np.array([[v @ [1, 0], v @ [1, 1]],
                  [v @ [0, 0], v @ [0, 1]]])
    a, b = cmap_range
    X = a + (b - a) / X.max() * X
    im = ax.imshow(
        X,
        interpolation='bicubic',
        clim=(0, 1),
        aspect='auto',
        **kwargs
    )
    return im

def gradient_bar(ax, x, y, width=0.5, bottom=0, cmap=None):
    """Рисует бары с градиентной заливкой."""
    if cmap is None:
        cmap = plt.cm.Blues_r
    for left, top in zip(x, y):
        right = left + width
        gradient_image(
            ax,
            extent=(left, right, bottom, top),
            cmap=cmap,
            cmap_range=(0, 0.8)
        )

# Пример использования
fig, ax = plt.subplots(figsize=(10, 5))
ax.set_facecolor('white')
fig.patch.set_facecolor('white')

N = 6
x = np.arange(N) + 0.15
y = np.array([45, 72, 38, 91, 56, 63]) / 100

gradient_bar(ax, x, y, width=0.7, cmap=plt.cm.Blues)

ax.set_xlim(0, N)
ax.set_ylim(0, 1.1)
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

plt.tight_layout()
plt.show()
```

**Вариант с одним цветом (solid с лёгким градиентом сверху вниз):**
```python
# Создать двухцветную colormap: от светлого оттенка к основному
from matplotlib.colors import LinearSegmentedColormap

def make_bar_cmap(base_color_hex, light_factor=0.7):
    """Создаёт colormap от светлого варианта цвета к основному."""
    import matplotlib.colors as mcolors
    r, g, b = mcolors.to_rgb(base_color_hex)
    light = (1 - (1 - r) * light_factor,
             1 - (1 - g) * light_factor,
             1 - (1 - b) * light_factor)
    return LinearSegmentedColormap.from_list(
        'bar_grad', [light, base_color_hex]
    )

# Использование:
cmap = make_bar_cmap('#4F81E1')  # синий с градиентом от светло-синего
gradient_bar(ax, x, y, width=0.7, cmap=cmap)
```

---

### 2.3 Donut charts с текстом по центру

**Техника:** `ax.pie()` с `wedgeprops={'width': 0.4}` + `plt.Circle((0,0), 0.6)` + `ax.text()`.

**Источники:**
- https://gist.github.com/andymcdgeo/11e2e90dc08b7d2d2d9fcf2c872ab26b
- https://plainenglish.io/blog/how-to-make-a-beautiful-donut-chart-and-nested-donut-chart-in-matplotlib-92040c8bbeea

```python
import matplotlib.pyplot as plt

def draw_donut_chart(ax, values, labels, colors, center_text_main, center_text_sub,
                     bg_color='white'):
    """
    Рисует donut chart с текстом по центру.

    ax: matplotlib Axes
    values: список чисел [45, 35, 20]
    labels: список строк
    colors: список HEX ['#4F81E1', '#34C578', '#F5A623']
    center_text_main: главный текст в центре (например '85%')
    center_text_sub: подпись (например 'Завершено')
    """
    wedges, texts = ax.pie(
        values,
        labels=None,
        colors=colors,
        startangle=90,
        counterclock=False,
        wedgeprops={'width': 0.4, 'edgecolor': bg_color, 'linewidth': 2}
    )

    # Белый круг в центре
    centre_circle = plt.Circle(
        (0, 0), 0.6,
        fc=bg_color,
        linewidth=0
    )
    ax.add_artist(centre_circle)

    # Текст в центре
    ax.text(
        0, 0.08,
        center_text_main,
        ha='center', va='center',
        fontsize=22, fontweight='bold',
        color='#1A1A2E'
    )
    ax.text(
        0, -0.15,
        center_text_sub,
        ha='center', va='center',
        fontsize=11,
        color='#888888'
    )

    ax.set_aspect('equal')
    ax.axis('off')

# Пример
fig, ax = plt.subplots(figsize=(5, 5))
fig.patch.set_facecolor('white')

draw_donut_chart(
    ax=ax,
    values=[68, 32],
    labels=['Завершено', 'В работе'],
    colors=['#4F81E1', '#E8EEFF'],
    center_text_main='68%',
    center_text_sub='Завершено'
)
plt.tight_layout()
plt.show()
```

**Вариант с тонким кольцом (как в Tableau):**
```python
# Очень тонкое кольцо = width маленькое
wedgeprops={'width': 0.15, 'edgecolor': 'white', 'linewidth': 2}
# + большой круг в центре:
centre_circle = plt.Circle((0, 0), 0.85, fc='white')
```

---

### 2.4 Градиентная заливка под линейным графиком (area gradient)

**Техника:** `imshow()` с colormap + `Polygon` из данных кривой как `clip_path`.

**Источник:** https://www.pythontutorials.net/blog/is-it-possible-to-get-color-gradients-under-a-curve/

```python
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.colors import LinearSegmentedColormap

def draw_area_gradient(ax, x, y, color_top='#4F81E1', color_bottom='#FFFFFF',
                       alpha=0.6, line_color=None, line_width=2):
    """
    Рисует линейный график с градиентной заливкой под ним.

    Градиент: от color_top у линии до color_bottom у нуля.
    """
    y_min = 0
    y_max = max(y) * 1.05

    # Создаём colormap: снизу прозрачный/белый → сверху цвет
    cmap = LinearSegmentedColormap.from_list(
        'area_grad',
        [color_bottom, color_top]
    )

    # Полигон области под кривой
    verts = ([(x[0], y_min)]
             + list(zip(x, y))
             + [(x[-1], y_min)])
    poly = Polygon(verts, facecolor='none', edgecolor='none')
    ax.add_patch(poly)

    # Градиентный прямоугольник через imshow
    # Z = Y → вертикальный градиент (снизу светло, сверху темно)
    X_grid, Y_grid = np.meshgrid(
        np.linspace(x.min(), x.max(), 300),
        np.linspace(y_min, y_max, 300)
    )
    Z = Y_grid  # интенсивность = высота

    im = ax.imshow(
        Z,
        extent=[x.min(), x.max(), y_min, y_max],
        origin='lower',
        cmap=cmap,
        aspect='auto',
        alpha=alpha
    )
    im.set_clip_path(poly)

    # Линия поверх
    line_c = line_color or color_top
    ax.plot(x, y, color=line_c, linewidth=line_width, zorder=5)

    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(y_min, y_max)

# Пример использования
fig, ax = plt.subplots(figsize=(10, 4))
fig.patch.set_facecolor('white')
ax.set_facecolor('white')

x = np.linspace(0, 12, 100)
y = np.array([5, 8, 12, 7, 15, 22, 18, 25, 30, 28, 35, 32, 40])[
    np.round(np.linspace(0, 12, 100)).astype(int)
]

draw_area_gradient(ax, x, y, color_top='#4F81E1', color_bottom='#FFFFFF', alpha=0.5)

# Стиль
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_color('#EEEEEE')
ax.spines['bottom'].set_color('#EEEEEE')
ax.tick_params(colors='#888888', labelsize=9)
ax.yaxis.grid(True, color='#F5F5F5', linewidth=0.8)
ax.set_axisbelow(True)

plt.tight_layout()
plt.show()
```

**Упрощённый вариант через `fill_between` с alpha (без imshow):**
```python
# Быстрый способ — менее красиво, но надёжно:
ax.plot(x, y, color='#4F81E1', linewidth=2)
ax.fill_between(x, y, alpha=0.15, color='#4F81E1')

# Или многослойная заливка для имитации градиента:
for alpha, frac in zip([0.05, 0.07, 0.10, 0.12], [0.9, 0.7, 0.5, 0.3]):
    ax.fill_between(x, y * frac, y, alpha=alpha, color='#4F81E1')
```

---

### 2.5 Тонкие элегантные бары как в Tableau/Power BI

**Ключевые параметры:**

```python
# Тонкие бары: width=0.4 вместо дефолтного 0.8
bars = ax.bar(x, y, width=0.35, color='#4F81E1', zorder=3)

# Стиль Tableau: убрать рамки, только нижняя сетка
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
ax.spines['left'].set_visible(False)
ax.spines['bottom'].set_color('#DDDDDD')
ax.tick_params(bottom=False, left=False, labelcolor='#666666', labelsize=9)
ax.set_axisbelow(True)
ax.yaxis.grid(True, color='#EEEEEE', linewidth=0.8)
ax.xaxis.grid(False)

# Аннотации значений над барами
for bar in bars:
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        f'{bar.get_height():.0f}',
        ha='center', va='bottom',
        fontsize=9, color='#444444', fontweight='bold'
    )
```

---

## 3. Библиотеки стилей: сравнение

### matplotx (рекомендуется для чистого делового стиля)
```python
import matplotx
import matplotlib.pyplot as plt

# Минималистичный стиль dufte
plt.style.use(matplotx.styles.dufte)

# Для bar charts
plt.style.use(matplotx.styles.dufte_bar)

# Вывести значения над барами
matplotx.show_bar_values(format="{:.0f}")

# Метки на конце линий вместо легенды
matplotx.line_labels()

# Встроенные цветовые палитры
plt.style.use(matplotx.styles.tableau)  # как Tableau
plt.style.use(matplotx.styles.dracula)  # тёмная тема
plt.style.use(matplotx.styles.nord)     # Nord тема
```

**Установка:** `pip install matplotx[all]`

### mplcyberpunk (для тёмной/футуристичной темы)
```python
import mplcyberpunk
plt.style.use("cyberpunk")

# Добавить glow-эффект к линиям
mplcyberpunk.add_glow_effects()

# Только для баров (градиент внутри бара снизу вверх)
mplcyberpunk.add_bar_gradient(bars=bars)
```

### seaborn (для академического/корпоративного стиля)
```python
import seaborn as sns

# Базовые стили
sns.set_style("whitegrid")        # белый + серая сетка
sns.set_style("ticks")            # минималистичный
sns.set_style("darkgrid")         # тёмный с сеткой

# Контекст (размер шрифтов)
sns.set_context("talk")           # для презентаций
sns.set_context("paper")          # для документов

# Убрать рамки
sns.despine()
sns.despine(left=True)            # убрать левую ось

# Цветовые палитры
palette = sns.color_palette("Blues_d", n_colors=6)
palette = sns.color_palette("husl", n_colors=8)
```

---

## 4. Профессиональный базовый стиль (rcParams)

```python
import matplotlib.pyplot as plt
import matplotlib as mpl

# Глобальный стиль для всех графиков в дашборде
DASHBOARD_STYLE = {
    # Фон
    'figure.facecolor': '#FFFFFF',
    'axes.facecolor': '#FAFAFA',
    'axes.edgecolor': '#E0E0E0',

    # Сетка
    'axes.grid': True,
    'axes.axisbelow': True,
    'grid.color': '#EEEEEE',
    'grid.linewidth': 0.8,
    'grid.alpha': 1.0,

    # Рамки
    'axes.spines.top': False,
    'axes.spines.right': False,
    'axes.spines.left': False,
    'axes.spines.bottom': True,

    # Шрифт
    'font.family': 'sans-serif',
    'font.sans-serif': ['Segoe UI', 'Arial', 'DejaVu Sans'],
    'font.size': 10,
    'axes.labelsize': 10,
    'axes.titlesize': 13,
    'xtick.labelsize': 9,
    'ytick.labelsize': 9,

    # Цвета текста
    'text.color': '#333333',
    'axes.labelcolor': '#555555',
    'xtick.color': '#666666',
    'ytick.color': '#666666',

    # Цветовой цикл (синий-зелёный-оранжевый-фиолетовый)
    'axes.prop_cycle': mpl.cycler(
        color=['#4F81E1', '#34C578', '#F5A623', '#9B59B6',
               '#E74C3C', '#1ABC9C', '#F39C12', '#3498DB']
    ),

    # Линии
    'lines.linewidth': 2.0,
    'lines.markersize': 6,

    # Тики
    'xtick.bottom': False,
    'ytick.left': False,
}

# Применить
mpl.rcParams.update(DASHBOARD_STYLE)
```

---

## 5. KPI-карточки в matplotlib (встроенный в PyQt5)

**Подход:** Создать `Figure` с нулевыми margins, отключить все оси, использовать только `ax.text()`.

```python
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
import matplotlib.patches as mpatches

class KPICard(FigureCanvasQTAgg):
    """Виджет KPI-карточки на основе matplotlib."""

    def __init__(self, title, value, subtitle='', color='#4F81E1',
                 width=200, height=100):
        dpi = 100
        fig = Figure(figsize=(width/dpi, height/dpi), dpi=dpi)
        fig.patch.set_facecolor('white')
        super().__init__(fig)

        ax = fig.add_axes([0, 0, 1, 1])  # занять весь Figure
        ax.set_facecolor('white')
        ax.axis('off')

        # Цветная полоска слева
        rect = mpatches.FancyBboxPatch(
            (0.02, 0.15), 0.04, 0.7,
            boxstyle='round,pad=0.01',
            facecolor=color,
            edgecolor='none',
            transform=ax.transAxes
        )
        ax.add_patch(rect)

        # Значение
        ax.text(0.15, 0.6, value,
                transform=ax.transAxes,
                fontsize=24, fontweight='bold',
                color='#1A1A2E', va='center')

        # Заголовок
        ax.text(0.15, 0.82, title,
                transform=ax.transAxes,
                fontsize=10, color='#888888', va='center')

        # Подпись
        if subtitle:
            ax.text(0.15, 0.25, subtitle,
                    transform=ax.transAxes,
                    fontsize=9, color=color, va='center')

        fig.tight_layout(pad=0)
```

---

## 6. Gradient Patches (продвинутый — любой полигон с градиентом)

**Источник:** https://gist.github.com/rgerum/a729b68dbaac71ca45707b636a1d1fa0

Функция `add_gradient_patch()` позволяет добавить градиент к произвольному полигону (не только прямоугольнику), поддерживает:
- Направление градиента (угол)
- Несколько color stops
- Произвольные формы через `clip_path`

**Использование:**
```python
# Добавить градиентный патч к кривой
polygon_points = list(zip(x, y)) + [(x[-1], 0), (x[0], 0)]
add_gradient_patch(
    polygon=polygon_points,
    start=(x[0], 0),
    end=(x[0], max(y)),
    color1='white',
    color2='#4F81E1',
    ax=ax
)
```

---

## 7. Рекомендуемые подходы для Interior Studio ReportsTab

| График | Рекомендуемая техника | Сложность |
|---|---|---|
| Бары по стадиям | FancyBboxPatch (скруглённые верхи) | Средняя |
| Бары по менеджерам | Тонкие бары width=0.4 + аннотации | Простая |
| Donut (статус проектов) | pie() + Circle + text() по центру | Простая |
| Линейный (тренд) | imshow gradient + Polygon clip_path | Средняя |
| Линейный (быстрый) | fill_between alpha=0.15 | Простая |
| KPI цифры | matplotlib Figure без осей + text() | Средняя |
| Фоновый стиль | rcParams DASHBOARD_STYLE | Простая |

**Для быстрого внедрения** — использовать:
1. `matplotx.styles.dufte` / `dufte_bar` как базовый стиль
2. `fill_between(alpha=0.15)` для area charts
3. `FancyBboxPatch` для скруглённых баров
4. `pie() + Circle` для donut

---

## 8. Ссылки

- Matplotlib gradient bar: https://matplotlib.org/stable/gallery/lines_bars_and_markers/gradient_bar.html
- Rounded bars discourse: https://discourse.matplotlib.org/t/new-to-matplotlib-how-to-round-the-edges-of-the-bars-in-a-bar-plot-in-matplotlib/24230
- Beautiful bar charts: https://www.pythoncharts.com/matplotlib/beautiful-bar-charts-matplotlib/
- Donut with center text (gist): https://gist.github.com/andymcdgeo/11e2e90dc08b7d2d2d9fcf2c872ab26b
- Donut nested chart: https://plainenglish.io/blog/how-to-make-a-beautiful-donut-chart-and-nested-donut-chart-in-matplotlib-92040c8bbeea
- Gradient under curve: https://www.pythontutorials.net/blog/is-it-possible-to-get-color-gradients-under-a-curve/
- Gradient patches gist: https://gist.github.com/rgerum/a729b68dbaac71ca45707b636a1d1fa0
- matplotx GitHub: https://github.com/nschloe/matplotx
- mplcyberpunk GitHub: https://github.com/dhaitz/mplcyberpunk
- matplotlib topics: https://github.com/topics/matplotlib-style-sheets
