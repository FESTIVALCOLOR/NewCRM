# 26. PDF-экспорт — Архитектура и реализация

> Система экспорта данных в PDF из всех модулей Interior Studio CRM.
> Версия: 1.0 | Дата: 2026-02-28

## Содержание

1. [Обзор](#обзор)
2. [Реализованные экспорты](#реализованные-экспорты)
3. [Архитектура PDF-экспорта в Отчётах](#архитектура-pdf-экспорта-в-отчётах)
4. [Технические решения](#технические-решения)
5. [Шаблон для новых экспортов](#шаблон-для-новых-экспортов)
6. [Потенциальные экспорты](#потенциальные-экспорты)

---

## Обзор

В приложении используются **3 механизма** PDF-генерации:

| Механизм | Библиотека | Где используется | Качество |
|----------|-----------|------------------|----------|
| **ReportLab Platypus** | `reportlab` | Отчёты и статистика, серверный таймлайн | Высокое (векторный текст + растровые скриншоты) |
| **QPrinter + QTextDocument** | `PyQt5.QtPrintSupport` | CRM статистика, надзор статистика | Среднее (HTML-таблицы) |
| **API (серверная генерация)** | `reportlab` на сервере | Таймлайн договора, таймлайн надзора | Высокое (серверный рендер) |

### Зависимости

```
reportlab>=4.0        # PDF-генерация (Platypus flowables)
Pillow>=10.0          # Определение размеров изображений
matplotlib>=3.7       # Графики (figure.savefig для экспорта)
PyQt5>=5.15           # QPrinter, QTextDocument, widget.render()
```

---

## Реализованные экспорты

### 1. Отчёты и статистика (`ui/reports_tab.py`)

**Кнопка:** "Экспорт PDF" (жёлтая, в панели фильтров)
**Метод:** `ReportsTab.export_to_pdf()` (строка ~1700)
**Формат:** A4 landscape, ReportLab Platypus

**Что экспортирует:**
- Шапка: логотип, название, дата, активные фильтры
- 5 секций: KPI, Клиенты, Договоры, CRM Аналитика, Авторский надзор
- CRM: mini KPI cards + воронка + время стадий (по 2 таба)

**Ключевые методы:**
| Метод | Описание |
|-------|----------|
| `_grab_widget_png(widget, scale=3.0)` | Рендер QWidget в PNG через QPainter (3x для чёткости) |
| `_chart_to_png(chart, dpi=300)` | Экспорт matplotlib figure через `savefig()` |
| `_grab_crm_both_tabs(scale)` | Покомпонентный захват CRM-вкладок |
| `_fit_image(buf, w_px, h_px, max_w, max_h)` | Вписать изображение в рамки страницы |
| `_pdf_section_header(text, font)` | Заголовок секции с жёлтой полоской |
| `_pdf_hr(page_w_mm)` | Горизонтальная разделительная линия |

**Технические особенности:**
- `QGraphicsDropShadowEffect` временно снимается перед `render()` и пересоздаётся после
- Все matplotlib canvases принудительно перерисовываются (`canvas.draw()`) перед захватом
- CRM stage charts экспортируются через `figure.savefig(dpi=300)` для полного графика без обрезки скроллом
- Высоты CRM-компонентов ограничены: cards=18мм, funnel=55мм, stage=95мм
- Автозапуск PDF после сохранения (`os.startfile` на Windows)

---

### 2. CRM Статистика (`ui/crm_dialogs.py`)

**Кнопка:** "Экспорт в PDF" (красная, в CRMStatisticsDialog)
**Метод:** `CRMStatisticsDialog._export_pdf()` (строка ~1814)
**Формат:** QPrinter → PDF через QTextDocument (HTML-таблицы)

**Что экспортирует:**
- Логотип + название компании
- Статистика по проектам (таблица)
- Детальные данные по стадиям

**Вспомогательные диалоги:**
- `ExportPDFDialog` — выбор имени файла и папки
- `PDFExportSuccessDialog` — подтверждение успеха

---

### 3. Статистика надзора (`ui/supervision_dialogs.py`)

**Кнопка:** "Экспорт в PDF" (красная, в SupervisionStatisticsDialog)
**Метод:** `SupervisionStatisticsDialog.perform_pdf_export()` (строка ~656)
**Формат:** QPrinter → PDF через QTextDocument

**Что экспортирует:**
- Статистика надзорных проектов
- Таблица с данными по закупкам

---

### 4. Таймлайн договора (`ui/timeline_widget.py`)

**Кнопка:** "Экспорт в PDF" (красная, 32px)
**Метод:** `TimelineWidget._export_pdf()` (строка ~1008)
**Формат:** API-вызов → серверная генерация ReportLab → бинарные данные

**Что экспортирует:**
- Таблица таймлайна проекта (стадии, даты, статусы)
- Генерируется на сервере: `GET /api/timeline/{contract_id}/export-pdf`

---

### 5. Таймлайн надзора (`ui/supervision_timeline_widget.py`)

**Кнопка:** "Экспорт в PDF (без бюджетов)" (красная, 32px)
**Метод:** `SupervisionTimelineWidget._export_pdf()` (строка ~1043)
**Формат:** API-вызов → серверная генерация

**Что экспортирует:**
- Таблица таймлайна надзора (без финансовых данных)
- Генерируется на сервере: `GET /api/supervision-timeline/{card_id}/export-pdf`

---

### 6. Отчёты сотрудников (`ui/employee_reports_tab.py`)

**Кнопки:** 2 кнопки экспорта с SVG-иконками
- "Экспорт: Выполненные заказы"
- "Экспорт: Зарплаты"

**Метод:** `EmployeeReportsTab._export_pdf()` (строка ~396)
**Формат:** Файловый диалог → PDF

---

## Архитектура PDF-экспорта в Отчётах

### Процесс генерации (pixel-perfect подход)

```
┌────────────────────────────────────────────────┐
│  1. Пользователь нажимает "Экспорт PDF"        │
│  2. QFileDialog → выбор имени файла             │
│  3. Регистрация шрифтов (Arial из C:/Windows/)  │
│  4. Создание SimpleDocTemplate (A4 landscape)   │
├────────────────────────────────────────────────┤
│  5. ШАПКА: логотип + заголовок + фильтры        │
├────────────────────────────────────────────────┤
│  6. Для каждой секции (кроме CRM):              │
│     a) Снять QGraphicsDropShadowEffect          │
│     b) canvas.draw() на всех matplotlib charts   │
│     c) QPixmap(w*3, h*3) + setDevicePixelRatio  │
│     d) widget.render(painter) → PNG буфер        │
│     e) Вернуть shadow effect                     │
│     f) _fit_image() → вписать в страницу         │
├────────────────────────────────────────────────┤
│  7. CRM секция (покомпонентно):                 │
│     a) Mini KPI cards → _grab_widget_png()      │
│     b) Воронка → figure.savefig(dpi=300)        │
│     c) Время стадий → figure.savefig(dpi=300)   │
│     d) Ограничение высот: 18+55+95 мм          │
├────────────────────────────────────────────────┤
│  8. doc.build() с footer на каждой странице     │
│  9. os.startfile() → автозапуск PDF             │
└────────────────────────────────────────────────┘
```

### Настройки PDF

```python
# Страница
page_size = landscape(A4)          # 297×210 мм
MARGIN_LR = 10 * mm               # Боковые поля
MARGIN_TOP = 8 * mm               # Верхнее поле
MARGIN_BOT = 12 * mm              # Нижнее поле (footer)
RENDER_SCALE = 3.0                 # 3x разрешение для виджетов
CHART_DPI = 300                    # DPI для matplotlib charts

# Доступная область
PAGE_W_MM ≈ 277 мм                # Ширина контента
PAGE_H_MM ≈ 190 мм                # Высота контента
safe_h_mm ≈ 175 мм                # С запасом на footer

# CRM-секция (компоненты на одну страницу)
CRM_CARDS_H = 18 мм               # Mini KPI cards
CRM_FUNNEL_H = 55 мм              # Воронка проектов
CRM_STAGE_H = 95 мм               # Время стадий vs норматив
```

---

## Технические решения

### Проблема: QGraphicsDropShadowEffect блокирует render()

`SectionWidget` имеет тень (`QGraphicsDropShadowEffect`). При вызове `widget.render(painter)` Qt рендерит через proxy эффекта, что даёт пустой результат.

**Решение:** временно снять эффект, отрендерить, пересоздать:
```python
has_shadow = widget.graphicsEffect() is not None
if has_shadow:
    widget.setGraphicsEffect(None)  # Qt уничтожает old effect
    QApplication.processEvents()

# ... render ...

if has_shadow:
    new_shadow = QGraphicsDropShadowEffect(widget)
    new_shadow.setBlurRadius(16)
    new_shadow.setOffset(0, 2)
    new_shadow.setColor(QColor(0, 0, 0, 25))
    widget.setGraphicsEffect(new_shadow)
```

### Проблема: Matplotlib canvases пустые при render()

FigureCanvasQTAgg имеет внутренний bitmap-кэш. Если canvas не был отрисован на экране, кэш пуст.

**Решение:** принудительный `canvas.draw()` перед захватом:
```python
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
for canvas in widget.findChildren(FigureCanvasQTAgg):
    canvas.draw()
```

### Проблема: Графики в QScrollArea обрезаны

`StackedBarChartWidget` для "Время стадий" имеет `setFixedSize()` и находится в QScrollArea. `render()` захватывает только видимую часть viewport.

**Решение:** экспорт через `figure.savefig()` напрямую:
```python
def _chart_to_png(self, chart_widget, dpi=300):
    fig = chart_widget.figure
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                facecolor='white', edgecolor='none', pad_inches=0.08)
    buf.seek(0)
    return buf, w_px, h_px
```

### Проблема: Изображение не помещается на страницу (LayoutError)

ReportLab бросает `LayoutError: Flowable too large` если flowable больше frame.

**Решение:** `_fit_image()` масштабирует пропорционально:
```python
def _fit_image(buf, w_px, h_px, max_w_mm, max_h_mm):
    aspect = h_px / w_px
    img_w_mm = max_w_mm
    img_h_mm = max_w_mm * aspect
    if img_h_mm > max_h_mm:
        img_h_mm = max_h_mm
        img_w_mm = max_h_mm / aspect
    return RLImage(buf, width=img_w_mm * mm, height=img_h_mm * mm)
```

### Проблема: Краш при закрытии (matplotlib + PyQt5)

"Fatal Python error: Illegal instruction" при выходе — GC уничтожает matplotlib objects после cleanup PyQt5.

**Решение:** явно закрыть все фигуры перед выходом (`ui/main_window.py`):
```python
def closeEvent(self, event):
    # ... stop managers ...
    import matplotlib.pyplot as plt
    plt.close('all')
    event.accept()
```

---

## Шаблон для новых экспортов

### Вариант A: Скриншот виджета (pixel-perfect)

Подходит для: таблицы, карточки, смешанный контент.

```python
def export_to_pdf(self):
    from reportlab.platypus import SimpleDocTemplate, Image as RLImage, Spacer
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm

    filename, _ = QFileDialog.getSaveFileName(self, "Сохранить", "report", "PDF (*.pdf)")
    if not filename:
        return

    page_size = landscape(A4)
    doc = SimpleDocTemplate(filename, pagesize=page_size,
                            leftMargin=10*mm, rightMargin=10*mm,
                            topMargin=8*mm, bottomMargin=12*mm)

    elements = []
    # Захват виджета
    data = self._grab_widget_png(target_widget, scale=3.0)
    if data:
        buf, w_px, h_px = data
        img = _fit_image(buf, w_px, h_px, max_w_mm=277, max_h_mm=175)
        elements.append(img)

    doc.build(elements)
    os.startfile(os.path.normpath(filename))  # Windows
```

### Вариант B: Matplotlib chart через savefig

Подходит для: графики, диаграммы.

```python
def _export_chart_pdf(self, chart_widget):
    buf = io.BytesIO()
    chart_widget.figure.savefig(buf, format='png', dpi=300,
                                 bbox_inches='tight', facecolor='white')
    buf.seek(0)
    # Далее — в ReportLab как RLImage
```

### Вариант C: HTML-таблицы через QPrinter

Подходит для: табличные данные без графиков.

```python
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QTextDocument

printer = QPrinter(QPrinter.HighResolution)
printer.setOutputFormat(QPrinter.PdfFormat)
printer.setOutputFileName(filename)
printer.setPageOrientation(QPageLayout.Landscape)

doc = QTextDocument()
doc.setHtml(html_content)
doc.print_(printer)
```

---

## Потенциальные экспорты

Модули, где PDF-экспорт может быть добавлен:

| Модуль | Файл | Что экспортировать | Рекомендуемый механизм |
|--------|------|-------------------|----------------------|
| **Клиенты** | `ui/clients_tab.py` | Список клиентов (таблица) | QPrinter + QTextDocument |
| **Договоры** | `ui/contracts_tab.py` | Реестр договоров (таблица) | QPrinter + QTextDocument |
| **Сотрудники** | `ui/employees_tab.py` | Справочник сотрудников | QPrinter + QTextDocument |
| **Зарплаты** | `ui/salaries_tab.py` | Расчётные ведомости | ReportLab (сложная вёрстка) |
| **CRM Kanban** | `ui/crm_tab.py` | Список проектов по стадиям | ReportLab (карточки) |
| **Надзор Kanban** | `ui/crm_supervision_tab.py` | Список надзорных проектов | ReportLab (карточки) |
| **Дашборд** | `ui/dashboard_tab.py` | Снимок дашборда (KPI + графики) | Screenshot (как в Отчётах) |

### Приоритеты реализации

1. **Высокий:** Клиенты, Договоры — основные реестры, часто нужен бумажный вид
2. **Средний:** Зарплаты — финансовая отчётность
3. **Низкий:** Kanban, Дашборд — редко экспортируют
