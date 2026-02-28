# Design: PDF-экспорт — Обновление всех модулей

> Агент: Design Agent
> Дата: 2026-02-28
> Slug: pdf-export-update
> Источники: research.md, github-search.md, docs/26-pdf-export.md

---

## 1. Обзор проблемы

В проекте 5 точек PDF-экспорта (кроме эталона `reports_tab.py`), каждая реализована по-своему:
- 2 модуля используют QPrinter + QTextDocument (устаревший подход, ~600 строк дублирующегося кода)
- 2 модуля используют API (серверную генерацию) — корректно, но без обработки ошибок и автооткрытия
- 1 модуль использует минималистичный PDFGenerator без фирменного оформления

**Цель:** привести все PDF-экспорты к единому стандарту (эталон: `reports_tab.py`), вынести общую логику в `utils/pdf_utils.py`, устранить дублирование и баги.

---

## 2. Архитектурное решение: `utils/pdf_utils.py`

### 2.1 Назначение

Общая утилита PDF-генерации, инкапсулирующая:
- Регистрацию шрифтов (Arial из Windows/Fonts, fallback Helvetica)
- Создание `SimpleDocTemplate` (A4 landscape, стандартные поля)
- Header (логотип + заголовок)
- Footer (footer.jpg + номер страницы)
- Захват виджетов и графиков для вставки в PDF
- Таблицы с фирменным стилем
- Автооткрытие файла
- Логирование через `logging`

### 2.2 Публичный API

```python
# utils/pdf_utils.py

import os
import io
import sys
import logging
import subprocess
from datetime import datetime

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage, CondPageBreak
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from utils.resource_path import resource_path

logger = logging.getLogger(__name__)


# =====================================================================
# 1. Регистрация шрифтов
# =====================================================================

_fonts_registered = False

def register_fonts():
    """
    Регистрирует шрифты для PDF (Arial из C:/Windows/Fonts, fallback Helvetica).
    Вызывается один раз (идемпотентно).
    Возвращает (font_name, font_bold).
    """
    global _fonts_registered
    font_name = 'Helvetica'
    font_bold = 'Helvetica-Bold'

    if _fonts_registered:
        # Проверяем какие шрифты были зарегистрированы ранее
        try:
            pdfmetrics.getFont('Arial')
            font_name = 'Arial'
        except KeyError:
            pass
        try:
            pdfmetrics.getFont('ArialBold')
            font_bold = 'ArialBold'
        except KeyError:
            pass
        return font_name, font_bold

    try:
        font_path = 'C:/Windows/Fonts/arial.ttf'
        bold_path = 'C:/Windows/Fonts/arialbd.ttf'
        if os.path.exists(font_path):
            try:
                pdfmetrics.getFont('Arial')
            except KeyError:
                pdfmetrics.registerFont(TTFont('Arial', font_path))
            font_name = 'Arial'
        if os.path.exists(bold_path):
            try:
                pdfmetrics.getFont('ArialBold')
            except KeyError:
                pdfmetrics.registerFont(TTFont('ArialBold', bold_path))
            font_bold = 'ArialBold'
    except Exception as e:
        logger.warning(f"Не удалось зарегистрировать шрифты: {e}")

    _fonts_registered = True
    return font_name, font_bold


# =====================================================================
# 2. Стили
# =====================================================================

# Цвета таблиц (единый фирменный стиль)
HEADER_BG = colors.HexColor('#2C3E50')
HEADER_FG = colors.white
ROW_ODD = colors.white
ROW_EVEN = colors.HexColor('#F8F9FA')
BORDER_COLOR = colors.HexColor('#DEE2E6')

# Стиль таблицы по умолчанию (для data tables)
def get_default_table_style(font_name='Arial', font_bold='ArialBold'):
    """Возвращает стандартный TableStyle для фирменных таблиц."""
    return TableStyle([
        # Заголовок
        ('BACKGROUND',      (0, 0), (-1, 0),  HEADER_BG),
        ('TEXTCOLOR',       (0, 0), (-1, 0),  HEADER_FG),
        ('FONTNAME',        (0, 0), (-1, 0),  font_bold),
        ('FONTSIZE',        (0, 0), (-1, 0),  9),
        ('ALIGN',           (0, 0), (-1, 0),  'CENTER'),
        ('TOPPADDING',      (0, 0), (-1, 0),  6),
        ('BOTTOMPADDING',   (0, 0), (-1, 0),  6),
        # Данные
        ('ROWBACKGROUNDS',  (0, 1), (-1, -1), [ROW_ODD, ROW_EVEN]),
        ('FONTNAME',        (0, 1), (-1, -1), font_name),
        ('FONTSIZE',        (0, 1), (-1, -1), 8),
        ('ALIGN',           (0, 1), (-1, -1), 'LEFT'),
        ('TOPPADDING',      (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING',   (0, 1), (-1, -1), 4),
        ('VALIGN',          (0, 0), (-1, -1), 'MIDDLE'),
        # Границы
        ('GRID',            (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ('LINEBELOW',       (0, 0), (-1, 0),  1.0,  colors.HexColor('#1A252F')),
        ('BOX',             (0, 0), (-1, -1), 0.5,  BORDER_COLOR),
        ('NOSPLIT',         (0, 0), (-1, 0)),
    ])


# =====================================================================
# 3. Footer callback
# =====================================================================

def make_page_footer(page_size, font_name='Arial'):
    """
    Возвращает callback для onFirstPage/onLaterPages,
    рисующий footer.jpg полосу + номер страницы.
    """
    def _draw_footer(canvas_obj, doc_obj):
        canvas_obj.saveState()
        # Подложка-полоса внизу (footer.jpg)
        footer_path = resource_path("resources/footer.jpg")
        if os.path.exists(footer_path):
            try:
                canvas_obj.drawImage(
                    footer_path, 0, 0,
                    width=page_size[0], height=12 * mm,
                    preserveAspectRatio=False, mask='auto')
            except Exception:
                pass
        # Текст поверх полосы
        canvas_obj.setFont(font_name, 7)
        canvas_obj.setFillColor(colors.HexColor('#999999'))
        canvas_obj.drawCentredString(
            page_size[0] / 2, 4 * mm,
            f"Interior Studio CRM  --  стр. {doc_obj.page}"
        )
        canvas_obj.restoreState()
    return _draw_footer


# =====================================================================
# 4. Секционные элементы
# =====================================================================

def pdf_section_header(text, font_bold='ArialBold'):
    """Заголовок секции с желтой полоской слева."""
    style = ParagraphStyle(
        'SectionH', fontName=font_bold, fontSize=13,
        textColor=colors.HexColor('#333333'), leading=16,
    )
    t = Table(
        [['', Paragraph(f'<b>{text}</b>', style)]],
        colWidths=[4, None],
    )
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#FFD93C')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    return t


def pdf_hr(page_w_mm):
    """Горизонтальная желтая разделительная линия."""
    hr = Table([['']],  colWidths=[page_w_mm * mm], rowHeights=[2])
    hr.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), colors.HexColor('#FFD93C')),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('TOPPADDING', (0, 0), (0, 0), 0),
        ('BOTTOMPADDING', (0, 0), (0, 0), 0),
    ]))
    return hr


# =====================================================================
# 5. Захват виджетов
# =====================================================================

def grab_widget_png(widget, scale=3.0):
    """
    Захватить QWidget как PNG-байты с повышенным разрешением.

    Args:
        widget: QWidget для захвата
        scale: множитель разрешения (3.0 = 300 DPI для печати)
    Returns:
        (BytesIO buf, width_px, height_px) или None
    """
    from PyQt5.QtGui import QPixmap, QPainter, QColor
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QApplication

    if not widget or not widget.isVisible():
        return None
    w, h = widget.width(), widget.height()
    if w <= 0 or h <= 0:
        return None

    # Принудительно перерисовать matplotlib canvases
    try:
        from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
        for canvas in widget.findChildren(FigureCanvasQTAgg):
            try:
                canvas.draw()
            except Exception:
                pass
    except ImportError:
        pass

    QApplication.processEvents()

    # Временно убрать QGraphicsDropShadowEffect
    has_shadow = widget.graphicsEffect() is not None
    if has_shadow:
        widget.setGraphicsEffect(None)
        QApplication.processEvents()

    # Рендер в Nx pixmap
    pixmap = QPixmap(int(w * scale), int(h * scale))
    pixmap.setDevicePixelRatio(scale)
    pixmap.fill(Qt.white)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.TextAntialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    widget.render(painter)
    painter.end()

    # Вернуть shadow effect
    if has_shadow:
        from PyQt5.QtWidgets import QGraphicsDropShadowEffect
        new_shadow = QGraphicsDropShadowEffect(widget)
        new_shadow.setBlurRadius(16)
        new_shadow.setOffset(0, 2)
        new_shadow.setColor(QColor(0, 0, 0, 25))
        widget.setGraphicsEffect(new_shadow)

    if pixmap.isNull():
        return None

    buf = io.BytesIO()
    from PyQt5.QtCore import QBuffer, QIODevice
    qbuf = QBuffer()
    qbuf.open(QIODevice.WriteOnly)
    pixmap.save(qbuf, 'PNG', quality=95)
    buf.write(qbuf.data().data())
    buf.seek(0)
    return buf, pixmap.width(), pixmap.height()


def chart_to_png(chart_widget, dpi=300):
    """
    Получить PNG из matplotlib chart через figure.savefig().

    Returns: (BytesIO buf, width_px, height_px) или None
    """
    if not chart_widget or not hasattr(chart_widget, 'figure'):
        return None
    fig = chart_widget.figure
    if not fig.axes:
        return None
    buf = io.BytesIO()
    try:
        fig.savefig(buf, format='png', dpi=dpi, bbox_inches='tight',
                    facecolor='white', edgecolor='none', pad_inches=0.08)
        buf.seek(0)
        try:
            from PIL import Image as PILImage
            img = PILImage.open(buf)
            w_px, h_px = img.size
            buf.seek(0)
            return buf, w_px, h_px
        except ImportError:
            buf.seek(0)
            size_in = fig.get_size_inches()
            w_px = int(size_in[0] * dpi)
            h_px = int(size_in[1] * dpi)
            return buf, w_px, h_px
    except Exception as e:
        logger.warning(f"chart_to_png error: {e}")
        return None


# =====================================================================
# 6. Вспомогательные функции
# =====================================================================

def fit_image(buf, w_px, h_px, max_w_mm, max_h_mm):
    """
    Создать RLImage, вписанную в max_w x max_h мм
    с сохранением пропорций.
    """
    aspect = h_px / w_px if w_px > 0 else 0.5
    img_w_mm = max_w_mm
    img_h_mm = max_w_mm * aspect
    if img_h_mm > max_h_mm:
        img_h_mm = max_h_mm
        img_w_mm = max_h_mm / aspect
    return RLImage(buf, width=img_w_mm * mm, height=img_h_mm * mm)


def open_file(filepath):
    """
    Автооткрытие файла в системном приложении.
    Windows: os.startfile(), Linux/Mac: xdg-open/open.
    """
    try:
        if sys.platform == 'win32':
            os.startfile(os.path.normpath(filepath))
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', filepath])
        else:
            subprocess.Popen(['xdg-open', filepath])
    except Exception as e:
        logger.warning(f"Не удалось открыть файл: {e}")


# =====================================================================
# 7. Высокоуровневый генератор табличных PDF
# =====================================================================

def build_table_pdf(
    output_path: str,
    title: str,
    headers: list,
    rows: list,
    subtitle: str = None,
    summary_items: list = None,
    status_column: int = None,
    status_colors: dict = None,
    col_widths: list = None,
    orientation: str = 'landscape',
    auto_open: bool = True,
):
    """
    Генерация табличного PDF-отчета с фирменным оформлением.

    Args:
        output_path: Путь сохранения PDF
        title: Заголовок документа
        headers: Список заголовков колонок
        rows: Список строк [['val1', 'val2', ...], ...]
        subtitle: Подзаголовок (необязательно)
        summary_items: Краткая сводка [('Метка', 'значение'), ...]
        status_column: Индекс колонки со статусом для цветной подсветки
        status_colors: {'Текст статуса': '#HexColor', ...}
        col_widths: Ширины колонок в mm (None = авто)
        orientation: 'landscape' или 'portrait'
        auto_open: Открыть файл после генерации
    """
    font_name, font_bold = register_fonts()

    page_size = landscape(A4) if orientation == 'landscape' else A4
    MARGIN_LR = 10 * mm
    MARGIN_TOP = 8 * mm
    MARGIN_BOT = 12 * mm
    PAGE_W_MM = (page_size[0] - 2 * MARGIN_LR) / mm

    doc = SimpleDocTemplate(
        output_path,
        pagesize=page_size,
        leftMargin=MARGIN_LR,
        rightMargin=MARGIN_LR,
        topMargin=MARGIN_TOP,
        bottomMargin=MARGIN_BOT,
    )

    footer_cb = make_page_footer(page_size, font_name)
    elements = []

    # --- ШАПКА ---
    logo_path = resource_path("resources/logo.png")
    if os.path.exists(logo_path):
        try:
            logo = RLImage(logo_path, width=18 * mm, height=18 * mm)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 2 * mm))
        except Exception:
            pass

    style_title = ParagraphStyle(
        'RptTitle', fontName=font_bold, fontSize=16,
        textColor=colors.HexColor('#333333'),
        alignment=1, spaceAfter=2 * mm,
    )
    elements.append(Paragraph(title, style_title))
    elements.append(pdf_hr(PAGE_W_MM))
    elements.append(Spacer(1, 2 * mm))

    # Подзаголовок / дата
    style_sub = ParagraphStyle(
        'RptSub', fontName=font_name, fontSize=8,
        textColor=colors.HexColor('#666666'),
        alignment=1, spaceAfter=3 * mm,
        backColor=colors.HexColor('#F8F9FA'),
    )
    date_str = datetime.now().strftime('%d.%m.%Y %H:%M')
    sub_text = f'<b>Дата:</b> {date_str}'
    if subtitle:
        sub_text = f'{subtitle} | {sub_text}'
    elements.append(Paragraph(sub_text, style_sub))
    elements.append(Spacer(1, 3 * mm))

    # --- СВОДКА ---
    if summary_items:
        elements.append(pdf_section_header('Краткая сводка', font_bold))
        elements.append(Spacer(1, 2 * mm))
        style_body = ParagraphStyle(
            'SummaryBody', fontName=font_name, fontSize=9,
            textColor=colors.HexColor('#333333'),
            spaceAfter=1 * mm,
        )
        for label, value in summary_items:
            elements.append(Paragraph(
                f'&bull; {label}: <b>{value}</b>', style_body
            ))
        elements.append(Spacer(1, 4 * mm))

    # --- ТАБЛИЦА ---
    if rows:
        elements.append(pdf_section_header('Детальная статистика', font_bold))
        elements.append(Spacer(1, 2 * mm))

        # Подготовка данных: применяем Paragraph для длинных текстов и статусов
        cell_style = ParagraphStyle(
            'Cell', fontName=font_name, fontSize=8,
            textColor=colors.HexColor('#333333'), leading=10,
        )

        table_data = [headers]
        for row in rows:
            processed_row = []
            for col_idx, cell_val in enumerate(row):
                if status_column is not None and col_idx == status_column and status_colors:
                    color = status_colors.get(cell_val)
                    if color:
                        processed_row.append(Paragraph(
                            f'<b><font color="{color}">{cell_val}</font></b>',
                            cell_style
                        ))
                    else:
                        processed_row.append(cell_val)
                else:
                    processed_row.append(cell_val)
            table_data.append(processed_row)

        # Ширины колонок
        if col_widths:
            cw = [w * mm for w in col_widths]
        else:
            # Равномерное распределение
            available_w = PAGE_W_MM * mm
            cw = [available_w / len(headers)] * len(headers)

        table = Table(table_data, colWidths=cw, repeatRows=1)
        table.setStyle(get_default_table_style(font_name, font_bold))
        elements.append(table)
    else:
        style_no_data = ParagraphStyle(
            'NoData', fontName=font_name, fontSize=10,
            textColor=colors.HexColor('#999999'),
            alignment=1, spaceBefore=20 * mm,
        )
        elements.append(Paragraph('Нет данных для отображения', style_no_data))

    # --- СБОРКА ---
    doc.build(elements, onFirstPage=footer_cb, onLaterPages=footer_cb)
    logger.info(f"PDF отчет сохранен: {output_path}")

    if auto_open:
        open_file(output_path)
```

### 2.3 Что НЕ входит в `pdf_utils.py`

- **Логика извлечения данных из QTableWidget** — остается в UI-модулях
- **CRM-специфичный захват вкладок** (`_grab_crm_both_tabs`) — остается в `reports_tab.py`
- **API-вызовы** для серверной генерации — остаются в timeline-виджетах
- **Диалоги выбора файла** — остаются в UI-модулях (`QFileDialog`)

### 2.4 Судьба `utils/pdf_generator.py`

`utils/pdf_generator.py` (текущий файл, 324 строки) **будет заменен** на `utils/pdf_utils.py`:

- `PDFGenerator.generate_report()` заменяется на `build_table_pdf()`
- `PDFGenerator.generate_general_report()` заменяется на `build_table_pdf()` с `summary_items`
- `format_report_value()` и `PDF_STYLE` **переносятся** в `pdf_utils.py` (обратная совместимость)
- Файл `pdf_generator.py` остается как тонкая обертка-алиас с deprecation warning:
  ```python
  # utils/pdf_generator.py — DEPRECATED, использовать utils/pdf_utils
  import warnings
  warnings.warn("pdf_generator устарел, используйте pdf_utils", DeprecationWarning)
  from utils.pdf_utils import format_report_value, PDF_STYLE, build_table_pdf
  # ... обертка для обратной совместимости ...
  ```

### 2.5 Рефакторинг `reports_tab.py`

Эталон `reports_tab.py` **сохраняет свою реализацию**, но переносит общие методы в `pdf_utils.py`:

| Метод в `reports_tab.py` | Переносится в `pdf_utils.py` как |
|---|---|
| `_grab_widget_png(widget, scale)` | `grab_widget_png(widget, scale)` |
| `_chart_to_png(chart_widget, dpi)` | `chart_to_png(chart_widget, dpi)` |
| `_fit_image(buf, w, h, max_w, max_h)` | `fit_image(buf, w, h, max_w, max_h)` |
| `_pdf_section_header(text, font)` | `pdf_section_header(text, font)` |
| `_pdf_hr(page_w_mm)` | `pdf_hr(page_w_mm)` |
| Регистрация шрифтов (inline) | `register_fonts()` |
| Footer callback (inline) | `make_page_footer(page_size, font)` |
| `os.startfile()` (inline) | `open_file(filepath)` |

`reports_tab.py` импортирует эти функции из `pdf_utils` и вызывает напрямую. Специфичная логика (`_grab_crm_both_tabs`, секции по виджетам) остается в `reports_tab.py`.

---

## 3. Миграция каждого модуля

### 3.1 CRM Статистика — `ui/crm_dialogs.py`

**Текущее состояние:**
- 2 метода: `export_to_pdf()` (стр. 1814) + `perform_pdf_export_with_params()` (стр. 2058)
- ~500 строк дублирующегося QPrinter-кода
- `ExportPDFDialog` (frameless, стр. 2380) и `PDFExportSuccessDialog` (стр. 2563)
- Баг: двойной диалог успеха в `perform_pdf_export_with_params`

**Что дает миграция:**
- Удаление ~500 строк QPrinter-кода
- Устранение дублирования (2 метода -> 1)
- Устранение бага двойного диалога
- Фирменное оформление (footer.jpg, номер страницы)
- Автооткрытие PDF вместо "Открыть папку"

**Изменения:**

```
УДАЛИТЬ:
  - export_to_pdf() — 235 строк QPrinter-кода (стр. 1814-2055)
  - perform_pdf_export_with_params() — 295 строк (стр. 2058-2352)
  - ExportPDFDialog — 181 строка (стр. 2380-2561)
  - PDFExportSuccessDialog — 140 строк (стр. 2563-2703)

ДОБАВИТЬ:
  - export_to_pdf() — 40-50 строк:
    1. QFileDialog.getSaveFileName() — стандартный диалог (как в эталоне)
    2. Извлечение данных из self.stats_table (заголовки, строки, сводка)
    3. Вызов pdf_utils.build_table_pdf(...)
    4. Обработка ошибок через CustomMessageBox + logger
```

**Данные для передачи:**
```python
# Заголовки: из self.stats_table.horizontalHeaderItem(col).text()
headers = [self.stats_table.horizontalHeaderItem(col).text()
           for col in range(self.stats_table.columnCount())]

# Строки: из self.stats_table.item(row, col).text()
rows = [[self.stats_table.item(row, col).text() if self.stats_table.item(row, col) else ''
         for col in range(self.stats_table.columnCount())]
        for row in range(self.stats_table.rowCount())]

# Сводка: подсчет по колонке 5 (статус)
summary_items = [
    ('Всего записей', str(total)),
    ('Выполнено', str(completed)),
    ('В работе', str(in_work)),
    ('Просрочено', str(overdue)),
]

# Цвета статусов (колонка 5)
status_colors = {
    'Просрочено': '#E74C3C',
    'Завершено': '#27AE60',
}
```

**Реализация нового `export_to_pdf()`:**
```python
def export_to_pdf(self):
    """Экспорт в PDF"""
    from utils.pdf_utils import build_table_pdf

    default_name = f'Отчет CRM {self.project_type} {QDate.currentDate().toString("yyyy-MM-dd")}'
    filename, _ = QFileDialog.getSaveFileName(
        self, 'Сохранить PDF', default_name, 'PDF файлы (*.pdf)'
    )
    if not filename:
        return

    try:
        # Извлечение данных из таблицы
        headers = [self.stats_table.horizontalHeaderItem(col).text()
                   for col in range(self.stats_table.columnCount())]
        rows = []
        total = self.stats_table.rowCount()
        completed = in_work = overdue = 0

        for row in range(total):
            row_data = []
            for col in range(self.stats_table.columnCount()):
                item = self.stats_table.item(row, col)
                row_data.append(item.text() if item else '')
            rows.append(row_data)

            status_item = self.stats_table.item(row, 5)
            if status_item:
                st = status_item.text()
                if 'Завершено' in st:
                    completed += 1
                elif 'Просрочено' in st:
                    overdue += 1
                else:
                    in_work += 1

        build_table_pdf(
            output_path=filename,
            title=f'Статистика CRM: {self.project_type} проекты',
            headers=headers,
            rows=rows,
            summary_items=[
                ('Всего записей', str(total)),
                ('Выполнено', str(completed)),
                ('В работе', str(in_work)),
                ('Просрочено', str(overdue)),
            ],
            status_column=5,
            status_colors={
                'Просрочено': '#E74C3C',
                'Завершено': '#27AE60',
            },
        )
    except Exception as e:
        logger.error(f"Ошибка экспорта PDF: {e}", exc_info=True)
        CustomMessageBox(self, 'Ошибка', f'Не удалось создать PDF:\n{e}', 'error').exec_()
```

---

### 3.2 Статистика надзора — `ui/supervision_dialogs.py`

**Текущее состояние:**
- `export_to_pdf()` (стр. 580) — inline QDialog (не frameless)
- `perform_pdf_export()` (стр. 656) — ~240 строк QPrinter-кода
- Inline success_dialog (не frameless, не CustomMessageBox)
- `QMessageBox.critical` вместо `CustomMessageBox`

**Что дает миграция:**
- Удаление ~320 строк (inline QDialog + QPrinter-код + inline success)
- Единое фирменное оформление
- Frameless-совместимость (через стандартный QFileDialog)

**Изменения:**

```
УДАЛИТЬ:
  - export_to_pdf() — inline QDialog 75 строк (стр. 580-654)
  - perform_pdf_export() — 240 строк QPrinter-кода (стр. 656-897)
  - inline success_dialog — 65 строк (стр. 901-965)

ДОБАВИТЬ:
  - export_to_pdf() — 40-50 строк (аналогично CRM):
    1. QFileDialog.getSaveFileName()
    2. Извлечение из self.stats_table
    3. build_table_pdf(...)
    4. Обработка ошибок
```

**Данные для передачи:**
```python
# Статусная колонка: 6 (не 5 как в CRM)
status_column = 6
status_colors = {
    'Приостановлено': '#F39C12',
    'Работа сдана': '#27AE60',
}
summary_items = [
    ('Всего проектов', str(total)),
    ('В работе', str(in_work)),
    ('Работа сдана', str(completed_work)),
    ('Приостановлено', str(paused)),
]
```

---

### 3.3 Таймлайн договора — `ui/timeline_widget.py`

**Текущее состояние:**
- API-вызов `self.data.export_timeline_pdf(contract_id)` — серверная генерация
- `QFileDialog.getSaveFileName()` + запись файла
- Только `print()` для ошибок, нет UI-уведомления
- Нет автооткрытия

**Что дает миграция:**
- Замена `print()` на `logger`
- Автооткрытие PDF после сохранения
- UI-уведомление об ошибках через `CustomMessageBox`
- Уведомление если сервер вернул пустой ответ

**Механизм генерации НЕ МЕНЯЕТСЯ** — остается API.

**Изменения:**

```python
def _export_pdf(self):
    """Экспорт в PDF через API"""
    if not self.contract_id:
        return
    try:
        file_bytes = self.data.export_timeline_pdf(self.contract_id)
        if not file_bytes:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(
                self, 'Предупреждение',
                'Сервер не вернул данные для PDF', 'warning'
            ).exec_()
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 'Сохранить PDF', f'timeline_{self.contract_id}.pdf',
            'PDF (*.pdf)'
        )
        if path:
            with open(path, 'wb') as f:
                f.write(file_bytes)
            logger.info(f"PDF таймлайна сохранен: {path}")
            from utils.pdf_utils import open_file
            open_file(path)
    except Exception as e:
        logger.error(f"Ошибка экспорта PDF таймлайна: {e}", exc_info=True)
        from ui.custom_message_box import CustomMessageBox
        CustomMessageBox(
            self, 'Ошибка', f'Не удалось экспортировать PDF:\n{e}', 'error'
        ).exec_()
```

**Добавить в начало файла:**
```python
import logging
logger = logging.getLogger(__name__)
```

---

### 3.4 Таймлайн надзора — `ui/supervision_timeline_widget.py`

**Идентичная миграция** как у `timeline_widget.py`:
- Замена `print()` на `logger`
- Автооткрытие через `open_file()`
- `CustomMessageBox` для ошибок
- Проверка `file_bytes` с UI-сообщением

```python
def _export_pdf(self):
    """Экспорт в PDF (без бюджетов)"""
    if not self.card_id:
        return
    try:
        file_bytes = self.data.export_supervision_timeline_pdf(self.card_id)
        if not file_bytes:
            from ui.custom_message_box import CustomMessageBox
            CustomMessageBox(
                self, 'Предупреждение',
                'Сервер не вернул данные для PDF', 'warning'
            ).exec_()
            return

        path, _ = QFileDialog.getSaveFileName(
            self, 'Сохранить PDF', f'supervision_timeline_{self.card_id}.pdf',
            'PDF (*.pdf)'
        )
        if path:
            with open(path, 'wb') as f:
                f.write(file_bytes)
            logger.info(f"PDF таймлайна надзора сохранен: {path}")
            from utils.pdf_utils import open_file
            open_file(path)
    except Exception as e:
        logger.error(f"Ошибка экспорта PDF таймлайна надзора: {e}", exc_info=True)
        from ui.custom_message_box import CustomMessageBox
        CustomMessageBox(
            self, 'Ошибка', f'Не удалось экспортировать PDF:\n{e}', 'error'
        ).exec_()
```

---

### 3.5 Отчеты сотрудников — `ui/employee_reports_tab.py`

**Текущее состояние:**
- `PDFGenerator.generate_report()` — минималистичный ReportLab без фирменного оформления
- `QMessageBox.information/critical` вместо `CustomMessageBox`
- Нет логотипа, нет footer, нет автооткрытия
- Нет logger (print + traceback)

**Что дает миграция:**
- Фирменное оформление (логотип, footer.jpg, нумерация)
- CustomMessageBox вместо QMessageBox
- Автооткрытие PDF
- Логирование

**Изменения:**

```
УДАЛИТЬ:
  - import: from utils.pdf_generator import PDFGenerator (стр. 10)
  - __init__: self.pdf_gen = PDFGenerator()
  - QMessageBox.information / QMessageBox.critical (стр. 464, 467)

ЗАМЕНИТЬ export_report() на:
```

```python
def export_report(self, project_type, report_type):
    """Экспорт отчета в PDF"""
    try:
        # ... (извлечение tab_widget, параметров периода — без изменений) ...

        filename, _ = QFileDialog.getSaveFileName(
            self, 'Сохранить отчет',
            f'Отчет_сотрудники_{report_type}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
            'PDF Files (*.pdf)'
        )
        if not filename:
            return

        # Получаем данные через DataAccess (без изменений)
        try:
            report_data = self.data_access.get_employee_report_data(...)
        except Exception as e:
            logger.warning(f"DataAccess ошибка get_employee_report_data: {e}")
            report_data = {'completed': [], 'salaries': []}

        # Подготовка данных
        if report_type == 'completed':
            data = report_data.get('completed', [])
            headers = ['Исполнитель', 'Должность', 'Количество проектов']
            title = f'Выполненные заказы - {project_type}'
            pdf_data = [[item.get('employee_name', ''),
                        item.get('position', ''),
                        str(item.get('count', 0))] for item in data]
        else:
            data = report_data.get('salaries', [])
            headers = ['Исполнитель', 'Должность', 'Сумма (руб.)']
            title = f'Зарплаты - {project_type}'
            pdf_data = [[item.get('employee_name', ''),
                        item.get('position', ''),
                        f"{item.get('total_salary', 0):,.2f}"] for item in data]

        from utils.pdf_utils import build_table_pdf
        build_table_pdf(
            output_path=filename,
            title=title,
            headers=headers,
            rows=pdf_data,
            subtitle=f'Тип проекта: {project_type}',
        )
    except Exception as e:
        logger.error(f"Ошибка экспорта отчета: {e}", exc_info=True)
        from ui.custom_message_box import CustomMessageBox
        CustomMessageBox(self, 'Ошибка', f'Ошибка экспорта отчета:\n{e}', 'error').exec_()
```

---

### 3.6 Рефакторинг `reports_tab.py` (эталон)

**Сохраняет свою сложную логику**, но переносит общие методы в `pdf_utils`:

```python
# БЫЛО (inline в reports_tab.py):
def _grab_widget_png(self, widget, scale=3.0): ...
def _chart_to_png(self, chart_widget, dpi=300): ...
def _fit_image(buf, w_px, h_px, max_w_mm, max_h_mm): ...
def _pdf_section_header(self, text, font_name): ...
def _pdf_hr(self, page_w_mm): ...
# + inline регистрация шрифтов
# + inline footer callback
# + inline os.startfile()

# СТАНЕТ:
from utils.pdf_utils import (
    register_fonts, make_page_footer, pdf_section_header, pdf_hr,
    grab_widget_png, chart_to_png, fit_image, open_file,
)

def export_to_pdf(self):
    font_name, font_bold = register_fonts()
    page_size = landscape(A4)
    # ... (остальная специфичная логика без изменений) ...
    footer_cb = make_page_footer(page_size, font_name)
    # ...
    elements.append(pdf_section_header('CRM Аналитика', font_bold))
    elements.append(pdf_hr(PAGE_W_MM))
    # ...
    data = grab_widget_png(section, RENDER_SCALE)
    img = fit_image(buf, w_px, h_px, PAGE_W_MM, safe_h_mm)
    # ...
    doc.build(elements, onFirstPage=footer_cb, onLaterPages=footer_cb)
    open_file(filename)
```

**Методы, остающиеся в `reports_tab.py`:**
- `_grab_crm_both_tabs()` — специфичная логика CRM-секций (mini cards + funnel + stage)
- Логика обхода секций (`self._pdf_sections`)
- Формирование `filters_info` из конкретных комбобоксов

---

## 4. Диаграмма зависимостей после миграции

```
utils/pdf_utils.py          <-- НОВЫЙ (общая утилита)
  |
  +-- utils/resource_path.py (resource_path)
  |
  +-- reportlab (SimpleDocTemplate, Table, ...)
  |
  +-- PyQt5 (QPixmap, QPainter) -- только в grab_widget_png/chart_to_png

utils/pdf_generator.py      <-- DEPRECATED (тонкая обертка)
  |
  +-- utils/pdf_utils.py

ui/reports_tab.py            (эталон, импортирует из pdf_utils)
  |
  +-- utils/pdf_utils.py (register_fonts, make_page_footer, grab_widget_png,
  |                        chart_to_png, fit_image, pdf_section_header,
  |                        pdf_hr, open_file)
  +-- Собственная логика: _grab_crm_both_tabs, секции, фильтры

ui/crm_dialogs.py            (статистика CRM)
  |
  +-- utils/pdf_utils.py (build_table_pdf)

ui/supervision_dialogs.py    (статистика надзора)
  |
  +-- utils/pdf_utils.py (build_table_pdf)

ui/timeline_widget.py        (таймлайн — API based)
  |
  +-- utils/pdf_utils.py (open_file)
  +-- DataAccess API (серверная генерация)

ui/supervision_timeline_widget.py  (таймлайн надзора — API based)
  |
  +-- utils/pdf_utils.py (open_file)
  +-- DataAccess API (серверная генерация)

ui/employee_reports_tab.py   (отчеты сотрудников)
  |
  +-- utils/pdf_utils.py (build_table_pdf)
```

---

## 5. Удаляемый код (summary)

| Файл | Удаляемый код | Строк |
|---|---|---|
| `ui/crm_dialogs.py` | `export_to_pdf()` QPrinter (стр. 1814-2055) | ~240 |
| `ui/crm_dialogs.py` | `perform_pdf_export_with_params()` (стр. 2058-2352) | ~295 |
| `ui/crm_dialogs.py` | `ExportPDFDialog` (стр. 2380-2561) | ~181 |
| `ui/crm_dialogs.py` | `PDFExportSuccessDialog` (стр. 2563-2703) | ~140 |
| `ui/supervision_dialogs.py` | `export_to_pdf()` inline QDialog (стр. 580-654) | ~75 |
| `ui/supervision_dialogs.py` | `perform_pdf_export()` QPrinter (стр. 656-897) | ~240 |
| `ui/supervision_dialogs.py` | Inline success_dialog (стр. 901-965) | ~65 |
| `ui/reports_tab.py` | Inline методы (перенос, не удаление) | ~200 |
| **Итого удалено** | | **~1236** |
| **Итого добавлено** (`pdf_utils.py`) | | **~350** |
| **Чистая экономия** | | **~886 строк** |

---

## 6. Тест-стратегия

### 6.1 Unit-тесты для `utils/pdf_utils.py`

Файл: `tests/client/test_pdf_utils.py`

```python
class TestRegisterFonts:
    """Тесты регистрации шрифтов."""

    def test_register_fonts_returns_tuple(self):
        """register_fonts() возвращает (font_name, font_bold)."""
        result = register_fonts()
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_register_fonts_idempotent(self):
        """Повторный вызов возвращает те же шрифты."""
        r1 = register_fonts()
        r2 = register_fonts()
        assert r1 == r2

    def test_register_fonts_fallback_no_arial(self, monkeypatch):
        """Без arial.ttf — fallback на Helvetica."""
        monkeypatch.setattr(os.path, 'exists', lambda p: False)
        # Сбросить _fonts_registered для теста
        import utils.pdf_utils
        utils.pdf_utils._fonts_registered = False
        result = register_fonts()
        assert result == ('Helvetica', 'Helvetica-Bold')


class TestGetDefaultTableStyle:
    """Тесты стиля таблицы."""

    def test_returns_table_style(self):
        """Возвращает объект TableStyle."""
        style = get_default_table_style()
        assert isinstance(style, TableStyle)


class TestMakePageFooter:
    """Тесты footer callback."""

    def test_returns_callable(self):
        """make_page_footer() возвращает callable."""
        cb = make_page_footer(landscape(A4))
        assert callable(cb)

    def test_footer_draws_page_number(self, mock_canvas, mock_doc):
        """Footer рисует номер страницы."""
        cb = make_page_footer(landscape(A4))
        cb(mock_canvas, mock_doc)
        mock_canvas.drawCentredString.assert_called_once()


class TestPdfSectionHeader:
    """Тесты заголовка секции."""

    def test_returns_table(self):
        """pdf_section_header() возвращает Table."""
        result = pdf_section_header('Тест')
        assert isinstance(result, Table)


class TestPdfHr:
    """Тесты горизонтальной линии."""

    def test_returns_table(self):
        """pdf_hr() возвращает Table."""
        result = pdf_hr(277)
        assert isinstance(result, Table)


class TestFitImage:
    """Тесты масштабирования изображения."""

    def test_fit_landscape_image(self):
        """Ландшафтное изображение вписывается по ширине."""
        img = fit_image(io.BytesIO(PNG_1X1), 1000, 500, 277, 190)
        assert isinstance(img, RLImage)

    def test_fit_portrait_image(self):
        """Портретное изображение ограничивается по высоте."""
        img = fit_image(io.BytesIO(PNG_1X1), 500, 1000, 277, 190)
        assert isinstance(img, RLImage)


class TestOpenFile:
    """Тесты автооткрытия файла."""

    def test_open_file_windows(self, monkeypatch):
        """На Windows вызывает os.startfile."""
        monkeypatch.setattr(sys, 'platform', 'win32')
        mock_startfile = MagicMock()
        monkeypatch.setattr(os, 'startfile', mock_startfile)
        open_file('/tmp/test.pdf')
        mock_startfile.assert_called_once()

    def test_open_file_exception_no_crash(self, monkeypatch):
        """Ошибка открытия не крашит приложение."""
        monkeypatch.setattr(sys, 'platform', 'win32')
        monkeypatch.setattr(os, 'startfile', MagicMock(side_effect=OSError))
        open_file('/tmp/test.pdf')  # Не должен бросить исключение


class TestBuildTablePdf:
    """Тесты генерации табличного PDF."""

    def test_generates_file(self, tmp_path):
        """build_table_pdf() создает файл."""
        path = str(tmp_path / 'test.pdf')
        build_table_pdf(
            output_path=path,
            title='Тестовый отчет',
            headers=['Колонка 1', 'Колонка 2'],
            rows=[['Значение 1', 'Значение 2']],
            auto_open=False,
        )
        assert os.path.exists(path)
        assert os.path.getsize(path) > 0

    def test_generates_with_summary(self, tmp_path):
        """PDF с краткой сводкой генерируется без ошибок."""
        path = str(tmp_path / 'test_summary.pdf')
        build_table_pdf(
            output_path=path,
            title='Отчет со сводкой',
            headers=['A', 'B'],
            rows=[['1', '2']],
            summary_items=[('Всего', '1')],
            auto_open=False,
        )
        assert os.path.exists(path)

    def test_generates_empty_data(self, tmp_path):
        """PDF без данных показывает 'Нет данных'."""
        path = str(tmp_path / 'test_empty.pdf')
        build_table_pdf(
            output_path=path,
            title='Пустой отчет',
            headers=['A'],
            rows=[],
            auto_open=False,
        )
        assert os.path.exists(path)

    def test_status_column_colors(self, tmp_path):
        """PDF с цветными статусами генерируется без ошибок."""
        path = str(tmp_path / 'test_status.pdf')
        build_table_pdf(
            output_path=path,
            title='Отчет со статусами',
            headers=['Проект', 'Статус'],
            rows=[['Проект 1', 'Завершено'], ['Проект 2', 'Просрочено']],
            status_column=1,
            status_colors={'Завершено': '#27AE60', 'Просрочено': '#E74C3C'},
            auto_open=False,
        )
        assert os.path.exists(path)

    def test_portrait_orientation(self, tmp_path):
        """PDF в портретной ориентации."""
        path = str(tmp_path / 'test_portrait.pdf')
        build_table_pdf(
            output_path=path,
            title='Портретный отчет',
            headers=['A', 'B'],
            rows=[['1', '2']],
            orientation='portrait',
            auto_open=False,
        )
        assert os.path.exists(path)

    def test_cyrillic_content(self, tmp_path):
        """PDF с кириллическим контентом генерируется корректно."""
        path = str(tmp_path / 'test_cyrillic.pdf')
        build_table_pdf(
            output_path=path,
            title='Кириллический заголовок',
            headers=['Имя', 'Должность', 'Зарплата'],
            rows=[['Иванов И.И.', 'Дизайнер', '150 000 руб.']],
            subtitle='Период: Январь 2026',
            auto_open=False,
        )
        assert os.path.exists(path)
```

### 6.2 Обновление существующих тестов

Файл `tests/client/test_pdf_generator.py` — обновить импорты:
```python
# Проверить что обертка pdf_generator все еще работает
from utils.pdf_generator import format_report_value, PDF_STYLE
# Добавить тест обратной совместимости:
def test_deprecated_import_still_works():
    from utils.pdf_generator import PDFGenerator
    gen = PDFGenerator()
    assert gen is not None
```

### 6.3 Проверка миграции модулей

Файл: `tests/client/test_pdf_export_migration.py`

```python
class TestPdfExportMigration:
    """Проверка что все экспорты используют общую утилиту."""

    def test_crm_dialogs_no_qprinter(self):
        """crm_dialogs.py не использует QPrinter для PDF."""
        import inspect
        from ui.crm_dialogs import CRMStatisticsDialog
        source = inspect.getsource(CRMStatisticsDialog.export_to_pdf)
        assert 'QPrinter' not in source
        assert 'build_table_pdf' in source or 'pdf_utils' in source

    def test_supervision_dialogs_no_qprinter(self):
        """supervision_dialogs.py не использует QPrinter для PDF."""
        import inspect
        from ui.supervision_dialogs import SupervisionStatisticsDialog
        source = inspect.getsource(SupervisionStatisticsDialog.export_to_pdf)
        assert 'QPrinter' not in source

    def test_timeline_uses_logger(self):
        """timeline_widget.py использует logger, не print."""
        import inspect
        from ui.timeline_widget import TimelineWidget
        source = inspect.getsource(TimelineWidget._export_pdf)
        assert 'logger' in source
        assert 'print(' not in source

    def test_supervision_timeline_uses_logger(self):
        """supervision_timeline_widget.py использует logger, не print."""
        import inspect
        from ui.supervision_timeline_widget import SupervisionTimelineWidget
        source = inspect.getsource(SupervisionTimelineWidget._export_pdf)
        assert 'logger' in source
        assert 'print(' not in source

    def test_employee_reports_uses_build_table_pdf(self):
        """employee_reports_tab.py использует build_table_pdf, не PDFGenerator."""
        import inspect
        from ui.employee_reports_tab import EmployeeReportsTab
        source = inspect.getsource(EmployeeReportsTab.export_report)
        assert 'PDFGenerator' not in source
        assert 'QMessageBox' not in source

    def test_reports_tab_imports_from_pdf_utils(self):
        """reports_tab.py импортирует общие методы из pdf_utils."""
        import inspect
        from ui.reports_tab import ReportsTab
        source = inspect.getsource(ReportsTab)
        assert 'pdf_utils' in source
```

---

## 7. Порядок реализации

### Фаза 1: Создание `utils/pdf_utils.py`
1. Создать файл `utils/pdf_utils.py` с полным API (секция 2.2)
2. Перенести `format_report_value()` и `PDF_STYLE` из `pdf_generator.py`
3. Написать unit-тесты `tests/client/test_pdf_utils.py`
4. Запустить тесты, убедиться что все зеленые

### Фаза 2: Рефакторинг `reports_tab.py`
5. Импортировать общие функции из `pdf_utils`
6. Удалить дублирующийся inline-код (шрифты, footer, grab, fit, hr, section_header)
7. Запустить тесты + ручной smoke-тест PDF-экспорта

### Фаза 3: Миграция `crm_dialogs.py`
8. Удалить `export_to_pdf()` QPrinter-версию
9. Удалить `perform_pdf_export_with_params()`
10. Удалить `ExportPDFDialog`, `PDFExportSuccessDialog`
11. Написать новый `export_to_pdf()` через `build_table_pdf`
12. Добавить `import logging; logger = logging.getLogger(__name__)`
13. Тест

### Фаза 4: Миграция `supervision_dialogs.py`
14. Удалить `export_to_pdf()` inline QDialog
15. Удалить `perform_pdf_export()` QPrinter-версию
16. Удалить inline success_dialog
17. Написать новый `export_to_pdf()` через `build_table_pdf`
18. Тест

### Фаза 5: Миграция timeline-виджетов
19. `timeline_widget.py`: заменить `_export_pdf()` (добавить logger, open_file, CustomMessageBox)
20. `supervision_timeline_widget.py`: аналогично
21. Тест

### Фаза 6: Миграция `employee_reports_tab.py`
22. Заменить `export_report()` на версию с `build_table_pdf`
23. Удалить `self.pdf_gen = PDFGenerator()`
24. Удалить импорт `from utils.pdf_generator import PDFGenerator`
25. Тест

### Фаза 7: Deprecation `pdf_generator.py`
26. Заменить содержимое на тонкую обертку с deprecation warning
27. Проверить обратную совместимость

### Фаза 8: Тесты миграции
28. Создать `tests/client/test_pdf_export_migration.py`
29. Обновить `tests/client/test_pdf_generator.py`
30. Запустить полный CI

---

## 8. Риски и митигация

| Риск | Вероятность | Митигация |
|---|---|---|
| Шрифт Arial не найден (Linux/Mac) | Средняя | Fallback на Helvetica уже реализован |
| footer.jpg / logo.png отсутствуют | Низкая | Проверка `os.path.exists()` + graceful skip |
| Большие таблицы (>1000 строк) | Средняя | `repeatRows=1` + автоматический page break в Platypus |
| `os.startfile` недоступен (non-Windows) | Низкая | `open_file()` с platform check и try/except |
| Внешний вызов `perform_pdf_export_with_params` | Средняя | Grep по проекту, проверить все caller-ы перед удалением |
| Обратная совместимость PDFGenerator | Низкая | Обертка в `pdf_generator.py` |

---

## 9. Результирующая таблица

| Модуль | До | После |
|---|---|---|
| `ui/crm_dialogs.py` | QPrinter, 500 строк, дубли, баг двойного диалога | `build_table_pdf()`, ~50 строк, без багов |
| `ui/supervision_dialogs.py` | QPrinter, 320 строк, inline QDialog | `build_table_pdf()`, ~50 строк |
| `ui/timeline_widget.py` | API, print(), нет UI ошибок | API, logger, CustomMessageBox, open_file |
| `ui/supervision_timeline_widget.py` | API, print(), нет UI ошибок | API, logger, CustomMessageBox, open_file |
| `ui/employee_reports_tab.py` | PDFGenerator, QMessageBox, нет footer | `build_table_pdf()`, CustomMessageBox, footer |
| `ui/reports_tab.py` | Inline методы | Импорт из pdf_utils |
| `utils/pdf_generator.py` | 324 строки | Deprecated обертка |
| `utils/pdf_utils.py` | Не существует | ~350 строк (общая утилита) |

---

> Design Agent: спроектировано обновление PDF-экспорта.
> Затрагиваемые файлы: 8. Удаляемый код: ~1236 строк. Добавляемый: ~350 строк.
> Чистая экономия: ~886 строк. Устраняемые баги: 7.
