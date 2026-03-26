# PDF Export — Исследование лучших практик

**Дата:** 2026-02-28
**Цель:** Найти лучшие практики и готовые решения для PDF-экспорта в PyQt5 + ReportLab приложениях

---

## 1. Подходы к PDF-генерации в Python desktop apps

### 1.1 Обзор библиотек

| Библиотека | Подходит для | Сложность |
|---|---|---|
| **ReportLab** (open source) | Data-heavy документы, CRM, точная вёрстка | Высокая |
| **WeasyPrint** | HTML→PDF, статичный контент | Средняя |
| **QPrinter + QTextDocument** | Простой текст/HTML в PyQt5 | Низкая |
| **QPrinter + widget.render()** | Скриншот виджета в PDF | Низкая |

**Вывод для Interior Studio CRM:** ReportLab — лучший выбор для профессиональных отчётов с таблицами, заголовками, логотипом и нумерацией страниц. WeasyPrint подходит только если есть шаблоны HTML.

### 1.2 ReportLab 4.0+ и совместимость

- ReportLab 4.0 перешёл на **чистый Python** (убраны C-расширения `rl_accel`)
- Поддерживает **Python 3.9–3.14** (актуально для нашего клиента Python 3.14.0)
- Полная обратная совместимость с ReportLab 3.x API
- Рендеринг через PyCairo вместо устаревшего libart

**Источники:**
- [Release Notes 4.0 — ReportLab Docs](https://docs.reportlab.com/releases/notes/whats-new-40/)
- [reportlab — PyPI](https://pypi.org/project/reportlab/)
- [Top 10 Python PDF generator libraries 2025](https://www.nutrient.io/blog/top-10-ways-to-generate-pdfs-in-python/)

---

## 2. ReportLab Platypus: SimpleDocTemplate + Header/Footer

### 2.1 Базовая структура с шапкой и нижним колонтитулом

```python
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

def build_header_footer(canvas, doc):
    """Вызывается для КАЖДОЙ страницы — рисует шапку и футер."""
    canvas.saveState()

    # --- Шапка ---
    canvas.setFont('DejaVuSerif-Bold', 10)
    canvas.drawString(20*mm, A4[1] - 15*mm, "Interior Studio CRM")

    # Логотип (если есть)
    # canvas.drawImage(logo_path, 20*mm, A4[1] - 18*mm, width=30*mm, height=10*mm)

    # Горизонтальная линия под шапкой
    canvas.setLineWidth(0.5)
    canvas.line(20*mm, A4[1] - 20*mm, A4[0] - 20*mm, A4[1] - 20*mm)

    # --- Футер ---
    canvas.setFont('DejaVuSerif', 8)
    canvas.drawString(20*mm, 12*mm, f"Дата: {doc.report_date}")

    # Нумерация страниц — "Страница N"
    page_num = canvas.getPageNumber()
    canvas.drawRightString(A4[0] - 20*mm, 12*mm, f"Стр. {page_num}")

    canvas.restoreState()


def generate_report(output_path, data, report_date):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=30*mm,      # место под шапку
        bottomMargin=25*mm,   # место под футер
    )
    doc.report_date = report_date  # передаём через атрибут doc

    styles = getSampleStyleSheet()
    story = []

    # ... наполнение story элементами ...

    doc.build(
        story,
        onFirstPage=build_header_footer,
        onLaterPages=build_header_footer,
    )
```

**Источники:**
- [Chapter 5: Platypus — ReportLab Docs](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
- [Automated Document Layout with ReportLab Platypus — woteq](https://woteq.com/using-reportlab-platypus-for-automated-document-layout-in-python/)
- [ReportLab and Django – Part 2 – Headers and Footers with Page Numbers](https://ericsaupe.netlify.app/reportlab-and-django-%E2%80%93-part-2-%E2%80%93-headers-and-footers-with-page-numbers/)

### 2.2 Нумерация страниц "Страница N из M"

Когда нужно показать "Стр. 3 из 10", используется кастомный Canvas-класс:

```python
from reportlab.pdfgen import canvas as pdf_canvas

class NumberedCanvas(pdf_canvas.Canvas):
    """Canvas с нумерацией 'N из M' — вычисляется после сборки всех страниц."""

    def __init__(self, *args, **kwargs):
        pdf_canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(num_pages)
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)

    def _draw_page_number(self, page_count):
        self.setFont('DejaVuSerif', 8)
        self.drawRightString(
            A4[0] - 20*mm, 12*mm,
            f"Стр. {self.getPageNumber()} из {page_count}"
        )

# Использование:
doc.build(story, canvasmaker=NumberedCanvas, onFirstPage=draw_header, onLaterPages=draw_header)
```

**Источник:**
- [Reportlab: How to Add Page Numbers — Mouse Vs Python](https://www.blog.pythonlibrary.org/2013/08/12/reportlab-how-to-add-page-numbers/)

---

## 3. Экспорт QWidget в изображение для PDF

### 3.1 QWidget.grab() → QPixmap → временный файл → ReportLab Image

Это самый надёжный способ вставить диаграмму (chart_widget) в PDF:

```python
import io
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from reportlab.platypus import Image as RLImage

def widget_to_reportlab_image(widget, max_width_mm=170, max_height_mm=100):
    """
    Захватывает QWidget как QPixmap, конвертирует в bytes,
    возвращает reportlab Image, масштабированный по заданным размерам.
    """
    # Захват виджета
    pixmap = widget.grab()

    # Конвертация в bytes (PNG в памяти)
    buffer = io.BytesIO()
    pixmap.save(buffer, format='PNG')
    buffer.seek(0)

    # Создание ReportLab Image с сохранением пропорций
    from reportlab.lib.units import mm
    max_w = max_width_mm * mm
    max_h = max_height_mm * mm

    img = RLImage(buffer)
    # Масштабирование с сохранением aspect ratio
    scale = min(max_w / img.imageWidth, max_h / img.imageHeight)
    img.drawWidth = img.imageWidth * scale
    img.drawHeight = img.imageHeight * scale

    return img
```

### 3.2 QPrinter + widget.render() — для простых случаев

```python
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtGui import QPainter
from PyQt5.QtWidgets import QFileDialog
from PyQt5.Qt import QFileInfo

def export_widget_to_pdf(widget, filename):
    """Рендерит виджет напрямую в PDF через QPrinter."""
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(filename)

    painter = QPainter(printer)
    # Масштаб: вписываем виджет в страницу
    xscale = printer.pageRect().width() / widget.width()
    yscale = printer.pageRect().height() / widget.height()
    scale = min(xscale, yscale)

    # Позиционирование в верхнем левом углу
    painter.translate(printer.pageRect().width() / 2, 0)
    painter.scale(scale, scale)
    painter.translate(-widget.width() / 2, 0)
    widget.render(painter)
    painter.end()
```

**Ограничение QPrinter:** нельзя смешивать с другими элементами (таблицами, текстом) — только скриншот виджета. Для полноценных отчётов лучше ReportLab.

**Источники:**
- [Exporting widgets and setting the position — Python GUIs](https://www.pythonguis.com/faq/exporting-widgets-and-setting-the-position-of-to-the-top-of-the-paper-in-pyqt5/)
- [How To Export File As PDF In PyQt5 — Codeloop](https://codeloop.org/how-to-export-file-as-pdf-in-pyqt5/)
- [Export QTableView to PDF — Qt Forum](https://forum.qt.io/topic/91015/export-qtableview-to-pdf)

### 3.3 Экспорт в отдельном потоке (QRunnable)

Генерация PDF может занять 1-5 секунд — важно не блокировать UI:

```python
from PyQt5.QtCore import QRunnable, QThreadPool, pyqtSignal, QObject

class PDFWorkerSignals(QObject):
    finished = pyqtSignal(str)   # путь к файлу
    error = pyqtSignal(str)      # сообщение об ошибке

class PDFGeneratorWorker(QRunnable):
    def __init__(self, output_path, data):
        super().__init__()
        self.output_path = output_path
        self.data = data
        self.signals = PDFWorkerSignals()

    def run(self):
        try:
            generate_report(self.output_path, self.data)
            self.signals.finished.emit(self.output_path)
        except Exception as e:
            self.signals.error.emit(str(e))

# Запуск:
worker = PDFGeneratorWorker(output_path, data)
worker.signals.finished.connect(self.on_pdf_done)
worker.signals.error.connect(self.on_pdf_error)
QThreadPool.globalInstance().start(worker)
```

**Источник:**
- [Generate customizable PDF reports with Python — Python GUIs](https://www.pythonguis.com/examples/python-pdf-report-generator/)

---

## 4. Профессиональные таблицы в ReportLab

### 4.1 TableStyle — полный набор команд

```python
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors

# Данные: первая строка — заголовки
data = [
    ['Клиент', 'Проект', 'Сумма', 'Статус'],
    ['ООО Дизайн', 'Квартира', '250 000 ₽', 'В работе'],
    ['Иванов А.В.', 'Офис', '800 000 ₽', 'Завершён'],
]

# Ширина столбцов (в пунктах, 1mm ≈ 2.83pt)
col_widths = [55*mm, 50*mm, 35*mm, 30*mm]

table = Table(data, colWidths=col_widths, repeatRows=1)  # repeatRows: заголовок на каждой странице

style = TableStyle([
    # --- Заголовок ---
    ('BACKGROUND',   (0, 0), (-1, 0),  colors.HexColor('#2C3E50')),
    ('TEXTCOLOR',    (0, 0), (-1, 0),  colors.white),
    ('FONTNAME',     (0, 0), (-1, 0),  'DejaVuSerif-Bold'),
    ('FONTSIZE',     (0, 0), (-1, 0),  9),
    ('ALIGN',        (0, 0), (-1, 0),  'CENTER'),
    ('TOPPADDING',   (0, 0), (-1, 0),  6),
    ('BOTTOMPADDING',(0, 0), (-1, 0),  6),

    # --- Данные: чередующийся фон ---
    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7F9FC')]),
    ('FONTNAME',     (0, 1), (-1, -1),  'DejaVuSerif'),
    ('FONTSIZE',     (0, 1), (-1, -1),  8),
    ('ALIGN',        (0, 1), (-1, -1),  'LEFT'),
    ('ALIGN',        (2, 1), (2, -1),   'RIGHT'),  # суммы — по правому краю
    ('TOPPADDING',   (0, 1), (-1, -1),  4),
    ('BOTTOMPADDING',(0, 1), (-1, -1),  4),

    # --- Границы ---
    ('GRID',         (0, 0), (-1, -1),  0.25, colors.HexColor('#DEE2E6')),
    ('LINEBELOW',    (0, 0), (-1, 0),   1.5,  colors.HexColor('#2C3E50')),  # жирная линия под заголовком
    ('BOX',          (0, 0), (-1, -1),  0.5,  colors.HexColor('#ADB5BD')),

    # --- Запрет разрыва заголовка ---
    ('NOSPLIT',      (0, 0), (-1, 0)),
])
table.setStyle(style)
```

### 4.2 Ключевые команды TableStyle

| Команда | Назначение | Пример |
|---|---|---|
| `BACKGROUND` | Фон ячеек | `('BACKGROUND', (0,0), (-1,0), colors.grey)` |
| `ROWBACKGROUNDS` | Чередующийся фон строк | `('ROWBACKGROUNDS', (0,1), (-1,-1), [white, lightgrey])` |
| `GRID` | Сетка всех границ | `('GRID', (0,0), (-1,-1), 0.5, colors.black)` |
| `BOX` | Внешняя рамка | `('BOX', (0,0), (-1,-1), 1, colors.black)` |
| `INNERGRID` | Только внутренние линии | `('INNERGRID', (0,0), (-1,-1), 0.25, colors.grey)` |
| `LINEBELOW` | Линия под строкой | `('LINEBELOW', (0,0), (-1,0), 2, colors.black)` |
| `SPAN` | Объединение ячеек | `('SPAN', (0,0), (2,0))` |
| `NOSPLIT` | Запрет разрыва строк | `('NOSPLIT', (0,0), (-1,0))` |
| `ALIGN` | Выравнивание текста | `('ALIGN', (0,0), (-1,-1), 'CENTER')` |
| `VALIGN` | Вертикальное выравнивание | `('VALIGN', (0,0), (-1,-1), 'MIDDLE')` |
| `FONTNAME` | Шрифт | `('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold')` |
| `FONTSIZE` | Размер шрифта | `('FONTSIZE', (0,0), (-1,-1), 9)` |

**Источники:**
- [Chapter 7: Tables — ReportLab Docs](https://docs.reportlab.com/reportlab/userguide/ch7_tables/)
- [Chapter 13: Using tables — ReportLab Docs](https://docs.reportlab.com/rml/userguide/Chapter_13_Using_tables/)
- [How to create table in PDF using ReportLab — woteq](https://woteq.com/how-to-create-table-in-pdf-using-reportlab/)

---

## 5. Кириллица / Русский текст в ReportLab

### 5.1 Регистрация шрифта с поддержкой Unicode

ReportLab 4.0+ принимает UTF-8 по умолчанию, но встроенные шрифты (Helvetica, Times) **не поддерживают кириллицу**. Нужен TTF-шрифт.

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

# Регистрация шрифтов DejaVu (поддерживает кириллицу)
pdfmetrics.registerFont(TTFont('DejaVuSerif', 'DejaVuSerif.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSerif-Bold', 'DejaVuSerif-Bold.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans', 'DejaVuSans.ttf'))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold', 'DejaVuSans-Bold.ttf'))

# Назначение шрифтов в стилях
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

styles = getSampleStyleSheet()

# Переопределяем все стандартные стили
styles['Normal'].fontName = 'DejaVuSans'
styles['Normal'].fontSize = 9
styles['Heading1'].fontName = 'DejaVuSans-Bold'
styles['Heading1'].fontSize = 14

# Создаём кастомные стили
title_style = ParagraphStyle(
    'ReportTitle',
    fontName='DejaVuSans-Bold',
    fontSize=16,
    alignment=TA_CENTER,
    spaceAfter=6,
)
```

### 5.2 Где взять шрифты DejaVu

- Скачать с https://dejavu-fonts.github.io/ или из пакета `fonts-dejavu`
- Разместить рядом с приложением или использовать `resource_path()`:

```python
from utils.helpers import resource_path  # наш resource_path

FONT_DIR = resource_path('resources/fonts')

pdfmetrics.registerFont(TTFont('DejaVuSans',
    os.path.join(FONT_DIR, 'DejaVuSans.ttf')))
pdfmetrics.registerFont(TTFont('DejaVuSans-Bold',
    os.path.join(FONT_DIR, 'DejaVuSans-Bold.ttf')))
```

**Источники:**
- [Chapter 3: Fonts — ReportLab Docs](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/)
- [How to use Cyrillic fonts in ReportLab — ActiveState Code](https://code.activestate.com/recipes/438817-how-to-use-cyrillic-fonts-in-reportlab-pdf-library/)
- [Russian text in ReportLab — GitHub Gist](https://gist.github.com/nngogol/6e19b97ce3f6e06b21a1add1a196ce3b)

---

## 6. Многостраничные PDF с таблицами

### 6.1 Автоматический разрыв страниц в Platypus

Platypus автоматически разбивает `story` на страницы. Для таблиц:

```python
from reportlab.platypus import Table, Spacer, PageBreak

# Table с repeatRows=1 повторяет заголовок на каждой новой странице
table = Table(data, colWidths=col_widths, repeatRows=1)

# Явный разрыв страницы (если нужен)
story.append(PageBreak())

# Отступы
story.append(Spacer(1, 6*mm))
```

### 6.2 Объединение статичного контента с таблицами

```python
story = []
# Титульный блок
story.append(Paragraph("Отчёт по проектам", title_style))
story.append(Paragraph(f"За период: {start_date} — {end_date}", subtitle_style))
story.append(Spacer(1, 5*mm))

# Сводная таблица
story.append(Paragraph("Сводка", section_style))
story.append(summary_table)
story.append(Spacer(1, 8*mm))

# Детальная таблица (может занимать несколько страниц)
story.append(Paragraph("Детали по проектам", section_style))
story.append(detail_table)
```

**Источник:**
- [Reportlab: Combine Static Content and Multipage Tables — Mouse Vs Python](https://www.blog.pythonlibrary.org/2013/08/09/reportlab-how-to-combine-static-content-and-multipage-tables/)

---

## 7. Сравнение подходов для Interior Studio CRM

### Сценарий 1: Отчёт с таблицами (основной случай)
**Рекомендация: ReportLab Platypus**
- `SimpleDocTemplate` + `onFirstPage`/`onLaterPages` для шапки/футера
- `Table` с `repeatRows=1` для многостраничных таблиц
- `NumberedCanvas` для нумерации "Стр. N из M"
- Шрифты DejaVu через `pdfmetrics.registerFont`

### Сценарий 2: Диаграммы в PDF
**Рекомендация: QWidget.grab() → ReportLab Image**
- `widget.grab()` возвращает `QPixmap`
- Конвертация через `io.BytesIO` в PNG
- Вставка через `reportlab.platypus.Image`
- Масштабирование с сохранением aspect ratio

### Сценарий 3: Простой текстовый отчёт
**Рекомендация: QPrinter + QTextDocument**
- Генерация HTML-строки с данными
- `QTextDocument.setHtml(html_string)`
- `doc.print_(printer)` с `printer.setOutputFormat(QPrinter.PdfFormat)`

### Вердикт для нашего проекта

```
ReportLab Platypus = основной инструмент для всех отчётов
QWidget.grab()     = для вставки диаграмм в PDF
QPrinter           = только для самых простых случаев (один виджет → PDF)
WeasyPrint         = НЕ нужен (нет HTML-шаблонов, сложная установка)
```

---

## 8. Готовый шаблон PDF-репорта для Interior Studio CRM

```python
"""
Шаблон PDF-экспорта для Interior Studio CRM.
Поддерживает: шапка с логотипом, нумерация страниц, кириллица.
"""
import os
import io
from datetime import date
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, PageBreak
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT
from reportlab.lib import colors
from reportlab.pdfgen import canvas as pdf_canvas


# ─── Регистрация шрифтов (вызвать один раз при старте) ───────────────────────

def register_fonts(font_dir: str):
    """Регистрирует шрифты DejaVu с поддержкой кириллицы."""
    fonts = {
        'DejaVuSans':       'DejaVuSans.ttf',
        'DejaVuSans-Bold':  'DejaVuSans-Bold.ttf',
    }
    for name, filename in fonts.items():
        path = os.path.join(font_dir, filename)
        if os.path.exists(path):
            pdfmetrics.registerFont(TTFont(name, path))


# ─── Canvas с нумерацией "Страница N из M" ───────────────────────────────────

class NumberedCanvas(pdf_canvas.Canvas):
    def __init__(self, *args, **kwargs):
        pdf_canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self._draw_page_number(num_pages)
            pdf_canvas.Canvas.showPage(self)
        pdf_canvas.Canvas.save(self)

    def _draw_page_number(self, page_count: int):
        self.setFont('DejaVuSans', 7)
        self.setFillColor(colors.HexColor('#6C757D'))
        self.drawRightString(
            A4[0] - 20*mm, 10*mm,
            f"Стр. {self.getPageNumber()} из {page_count}"
        )


# ─── Шапка и футер ────────────────────────────────────────────────────────────

def _make_header_footer(logo_path=None, company_name="Interior Studio"):
    def draw(canvas, doc):
        canvas.saveState()
        w, h = A4

        # Шапка
        if logo_path and os.path.exists(logo_path):
            canvas.drawImage(logo_path, 20*mm, h - 18*mm,
                             width=25*mm, height=8*mm, preserveAspectRatio=True)
        canvas.setFont('DejaVuSans-Bold', 10)
        canvas.setFillColor(colors.HexColor('#2C3E50'))
        canvas.drawString(50*mm, h - 14*mm, company_name)

        # Линия под шапкой
        canvas.setStrokeColor(colors.HexColor('#DEE2E6'))
        canvas.setLineWidth(0.5)
        canvas.line(20*mm, h - 20*mm, w - 20*mm, h - 20*mm)

        # Дата в футере
        canvas.setFont('DejaVuSans', 7)
        canvas.setFillColor(colors.HexColor('#6C757D'))
        report_date = getattr(doc, 'report_date', date.today().strftime('%d.%m.%Y'))
        canvas.drawString(20*mm, 10*mm, f"Сформировано: {report_date}")

        # Линия над футером
        canvas.line(20*mm, 15*mm, w - 20*mm, 15*mm)

        canvas.restoreState()
    return draw


# ─── Стили текста ──────────────────────────────────────────────────────────────

def get_styles():
    base = getSampleStyleSheet()
    return {
        'title': ParagraphStyle('title',
            fontName='DejaVuSans-Bold', fontSize=16,
            alignment=TA_CENTER, spaceAfter=4*mm,
            textColor=colors.HexColor('#2C3E50')),
        'subtitle': ParagraphStyle('subtitle',
            fontName='DejaVuSans', fontSize=10,
            alignment=TA_CENTER, spaceAfter=6*mm,
            textColor=colors.HexColor('#6C757D')),
        'section': ParagraphStyle('section',
            fontName='DejaVuSans-Bold', fontSize=11,
            spaceBefore=4*mm, spaceAfter=2*mm,
            textColor=colors.HexColor('#2C3E50')),
        'body': ParagraphStyle('body',
            fontName='DejaVuSans', fontSize=9,
            spaceAfter=2*mm,
            textColor=colors.HexColor('#212529')),
    }


# ─── Стиль таблицы ────────────────────────────────────────────────────────────

HEADER_BG   = colors.HexColor('#2C3E50')
ROW_BG_ODD  = colors.white
ROW_BG_EVEN = colors.HexColor('#F8F9FA')
BORDER_CLR  = colors.HexColor('#DEE2E6')

DEFAULT_TABLE_STYLE = TableStyle([
    ('BACKGROUND',      (0, 0), (-1, 0),  HEADER_BG),
    ('TEXTCOLOR',       (0, 0), (-1, 0),  colors.white),
    ('FONTNAME',        (0, 0), (-1, 0),  'DejaVuSans-Bold'),
    ('FONTSIZE',        (0, 0), (-1, 0),  8),
    ('ALIGN',           (0, 0), (-1, 0),  'CENTER'),
    ('TOPPADDING',      (0, 0), (-1, 0),  5),
    ('BOTTOMPADDING',   (0, 0), (-1, 0),  5),
    ('ROWBACKGROUNDS',  (0, 1), (-1, -1), [ROW_BG_ODD, ROW_BG_EVEN]),
    ('FONTNAME',        (0, 1), (-1, -1), 'DejaVuSans'),
    ('FONTSIZE',        (0, 1), (-1, -1), 8),
    ('ALIGN',           (0, 1), (-1, -1), 'LEFT'),
    ('TOPPADDING',      (0, 1), (-1, -1), 3),
    ('BOTTOMPADDING',   (0, 1), (-1, -1), 3),
    ('GRID',            (0, 0), (-1, -1), 0.25, BORDER_CLR),
    ('LINEBELOW',       (0, 0), (-1, 0),  1.0,  colors.HexColor('#1A252F')),
    ('BOX',             (0, 0), (-1, -1), 0.5,  BORDER_CLR),
    ('NOSPLIT',         (0, 0), (-1, 0)),
])


# ─── Вставка виджета PyQt в PDF ───────────────────────────────────────────────

def pyqt_widget_to_rl_image(widget, max_width_mm=170.0, max_height_mm=120.0):
    """Захватывает QWidget и возвращает reportlab Image."""
    pixmap = widget.grab()
    buf = io.BytesIO()
    pixmap.save(buf, format='PNG')
    buf.seek(0)

    img = RLImage(buf)
    scale = min(
        (max_width_mm * mm) / img.imageWidth,
        (max_height_mm * mm) / img.imageHeight,
        1.0,  # не увеличивать, только уменьшать
    )
    img.drawWidth  = img.imageWidth  * scale
    img.drawHeight = img.imageHeight * scale
    return img


# ─── Главная функция генерации ────────────────────────────────────────────────

def generate_pdf_report(
    output_path: str,
    title: str,
    subtitle: str,
    sections: list,   # [(section_title, table_data, col_widths), ...]
    logo_path: str = None,
    report_date: str = None,
):
    """
    sections = [
        {
            "title": "Активные проекты",
            "headers": ["Клиент", "Проект", "Сумма"],
            "rows": [["ООО Дизайн", "Квартира", "250 000 ₽"], ...],
            "col_widths": [60*mm, 60*mm, 50*mm],
        },
        ...
    ]
    """
    if report_date is None:
        report_date = date.today().strftime('%d.%m.%Y')

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=20*mm, leftMargin=20*mm,
        topMargin=28*mm, bottomMargin=22*mm,
    )
    doc.report_date = report_date

    styles = get_styles()
    draw_page = _make_header_footer(logo_path=logo_path)
    story = []

    # Заголовок отчёта
    story.append(Paragraph(title, styles['title']))
    if subtitle:
        story.append(Paragraph(subtitle, styles['subtitle']))
    story.append(Spacer(1, 4*mm))

    # Секции с таблицами
    for section in sections:
        story.append(Paragraph(section['title'], styles['section']))
        data = [section['headers']] + section['rows']
        table = Table(data, colWidths=section.get('col_widths'), repeatRows=1)
        table.setStyle(DEFAULT_TABLE_STYLE)
        story.append(table)
        story.append(Spacer(1, 6*mm))

    doc.build(story, onFirstPage=draw_page, onLaterPages=draw_page,
              canvasmaker=NumberedCanvas)
```

---

## 9. Ссылки и источники

### Официальная документация
- [ReportLab Docs — Platypus](https://docs.reportlab.com/reportlab/userguide/ch5_platypus/)
- [ReportLab Docs — Tables](https://docs.reportlab.com/reportlab/userguide/ch7_tables/)
- [ReportLab Docs — Fonts](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/)
- [ReportLab Docs — Graphics & Canvas](https://docs.reportlab.com/reportlab/userguide/ch2_graphics/)
- [ReportLab Release Notes 4.0](https://docs.reportlab.com/releases/notes/whats-new-40/)

### Туториалы и примеры
- [Generate customizable PDF reports with Python — Python GUIs](https://www.pythonguis.com/examples/python-pdf-report-generator/)
- [How To Export File As PDF In PyQt5 — Codeloop](https://codeloop.org/how-to-export-file-as-pdf-in-pyqt5/)
- [Exporting widgets to PDF — Python GUIs FAQ](https://www.pythonguis.com/faq/exporting-widgets-and-setting-the-position-of-to-the-top-of-the-paper-in-pyqt5/)
- [Reportlab: How to Add Page Numbers — Mouse Vs Python](https://www.blog.pythonlibrary.org/2013/08/12/reportlab-how-to-add-page-numbers/)
- [Reportlab: Combine Static Content and Multipage Tables](https://www.blog.pythonlibrary.org/2013/08/09/reportlab-how-to-combine-static-content-and-multipage-tables/)
- [Mastering PDF Report Generation — Medium](https://medium.com/@parveengoyal198/mastering-pdf-report-generation-with-reportlab-a-comprehensive-tutorial-part-2-c970ccd15fb6)

### Кириллица
- [Chapter 3: Fonts — ReportLab Docs](https://docs.reportlab.com/reportlab/userguide/ch3_fonts/)
- [Russian text in ReportLab — GitHub Gist (DejaVuSerif)](https://gist.github.com/nngogol/6e19b97ce3f6e06b21a1add1a196ce3b)
- [Cyrillic fonts in ReportLab — ActiveState](https://code.activestate.com/recipes/438817-how-to-use-cyrillic-fonts-in-reportlab-pdf-library/)

### Сравнение библиотек
- [WeasyPrint vs ReportLab — DEV Community](https://dev.to/claudeprime/generate-pdfs-in-python-weasyprint-vs-reportlab-ifi)
- [Top 10 Python PDF generator libraries 2025 — Nutrient](https://www.nutrient.io/blog/top-10-ways-to-generate-pdfs-in-python/)
- [Generating PDF in Python (2025) — Rost Glukhov](https://www.glukhov.org/post/2025/05/generating-pdf-in-python/)

### Qt / PyQt5
- [Exporting a document to PDF — Qt Wiki](https://wiki.qt.io/Exporting_a_document_to_PDF)
- [Handling PDF — Qt Wiki](https://wiki.qt.io/Handling_PDF)
- [Export QTableView to PDF — Qt Forum](https://forum.qt.io/topic/91015/export-qtableview-to-pdf)
- [Mastering Printing and PDF Exporting in PyQt — IT trip](https://en.ittrip.xyz/python/pyqt-pdf-print-control)
