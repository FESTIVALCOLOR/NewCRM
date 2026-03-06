"""
Общая утилита PDF-генерации для Interior Studio CRM.

Инкапсулирует: регистрацию шрифтов, header/footer, захват виджетов,
фирменные таблицы, автооткрытие файлов.

Используется: reports_tab.py, crm_dialogs.py, supervision_dialogs.py,
              employee_reports_tab.py, timeline_widget.py и др.
"""

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
# 2. Стили таблиц
# =====================================================================

HEADER_BG = colors.HexColor('#2C3E50')
HEADER_FG = colors.white
ROW_ODD = colors.white
ROW_EVEN = colors.HexColor('#F8F9FA')
BORDER_COLOR = colors.HexColor('#DEE2E6')


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
        footer_path = resource_path("resources/footer.jpg")
        if os.path.exists(footer_path):
            try:
                canvas_obj.drawImage(
                    footer_path, 0, 0,
                    width=page_size[0], height=12 * mm,
                    preserveAspectRatio=False, mask='auto')
            except Exception:
                pass
        canvas_obj.setFont(font_name, 7)
        canvas_obj.setFillColor(colors.HexColor('#999999'))
        canvas_obj.drawCentredString(
            page_size[0] / 2, 4 * mm,
            f"Interior Studio CRM \u2014 \u0441\u0442\u0440. {doc_obj.page}"
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
    output_path,
    title,
    headers,
    rows,
    subtitle=None,
    summary_items=None,
    status_column=None,
    status_colors=None,
    col_widths=None,
    orientation='landscape',
    auto_open=True,
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
    sub_text = f'<b>\u0414\u0430\u0442\u0430:</b> {date_str}'
    if subtitle:
        sub_text = f'{subtitle} | {sub_text}'
    elements.append(Paragraph(sub_text, style_sub))
    elements.append(Spacer(1, 3 * mm))

    # --- СВОДКА ---
    if summary_items:
        elements.append(pdf_section_header('\u041a\u0440\u0430\u0442\u043a\u0430\u044f \u0441\u0432\u043e\u0434\u043a\u0430', font_bold))
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
        elements.append(pdf_section_header('\u0414\u0435\u0442\u0430\u043b\u044c\u043d\u0430\u044f \u0441\u0442\u0430\u0442\u0438\u0441\u0442\u0438\u043a\u0430', font_bold))
        elements.append(Spacer(1, 2 * mm))

        cell_style = ParagraphStyle(
            'Cell', fontName=font_name, fontSize=8,
            textColor=colors.HexColor('#333333'), leading=10,
        )

        table_data = [headers]
        for row in rows:
            processed_row = []
            for col_idx, cell_val in enumerate(row):
                if status_column is not None and col_idx == status_column and status_colors:
                    color = status_colors.get(str(cell_val))
                    if color:
                        processed_row.append(Paragraph(
                            f'<b><font color="{color}">{cell_val}</font></b>',
                            cell_style
                        ))
                    else:
                        processed_row.append(str(cell_val) if cell_val else '')
                else:
                    processed_row.append(str(cell_val) if cell_val else '')
            table_data.append(processed_row)

        # Ширины колонок
        if col_widths:
            cw = [w * mm for w in col_widths]
        else:
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
        elements.append(Paragraph('\u041d\u0435\u0442 \u0434\u0430\u043d\u043d\u044b\u0445 \u0434\u043b\u044f \u043e\u0442\u043e\u0431\u0440\u0430\u0436\u0435\u043d\u0438\u044f', style_no_data))

    # --- СБОРКА ---
    doc.build(elements, onFirstPage=footer_cb, onLaterPages=footer_cb)
    logger.info(f"PDF \u043e\u0442\u0447\u0435\u0442 \u0441\u043e\u0445\u0440\u0430\u043d\u0435\u043d: {output_path}")

    if auto_open:
        open_file(output_path)
