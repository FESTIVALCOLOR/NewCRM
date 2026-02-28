"""
Серверная утилита генерации PDF для таблиц сроков.

Стилистика единая с клиентом: фирменные цвета #2C3E50,
лого, инфо-блок о проекте, футер с рамкой.
"""

import io
import os
import logging
from datetime import date

from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Image as RLImage,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

logger = logging.getLogger(__name__)

# ── Цвета (единые с клиентом) ────────────────────────────
HEADER_BG = colors.HexColor('#2C3E50')
HEADER_FG = colors.white
ROW_ODD = colors.white
ROW_EVEN = colors.HexColor('#F8F9FA')
BORDER_COLOR = colors.HexColor('#DEE2E6')
ACCENT = colors.HexColor('#FFD93C')

# ── Базовый путь ресурсов ─────────────────────────────────
# Docker: pdf_helper.py в /app/ → resources в /app/resources/
# Локально: pdf_helper.py в server/ → resources в ../resources/
_HERE = os.path.dirname(os.path.abspath(__file__))
_BASE = _HERE if os.path.isdir(os.path.join(_HERE, 'resources')) else os.path.dirname(_HERE)
LOGO_PATH = os.path.join(_BASE, 'resources', 'logo_pdf.png')
FOOTER_IMG = os.path.join(_BASE, 'resources', 'footer.jpg')

# ── Шрифты ────────────────────────────────────────────────
_fonts_ok = False


def _register_fonts():
    """Регистрация DejaVuSans (Docker) один раз."""
    global _fonts_ok
    if _fonts_ok:
        return
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/TTF/DejaVuSans.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans.ttf",
    ]
    bold_candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSans", p))
            except Exception:
                pass
            break
    for p in bold_candidates:
        if os.path.exists(p):
            try:
                pdfmetrics.registerFont(TTFont("DejaVuSansBold", p))
            except Exception:
                pass
            break
    _fonts_ok = True


def _font():
    _register_fonts()
    try:
        pdfmetrics.getFont("DejaVuSans")
        return "DejaVuSans"
    except KeyError:
        return "Helvetica"


def _font_bold():
    _register_fonts()
    try:
        pdfmetrics.getFont("DejaVuSansBold")
        return "DejaVuSansBold"
    except KeyError:
        return "Helvetica-Bold"


# ── Футер ─────────────────────────────────────────────────

def _draw_footer(canvas_obj, doc_obj):
    """Футер: градиентная полоска footer.jpg + белый блок с рамкой + текст."""
    canvas_obj.saveState()
    pw, ph = doc_obj.pagesize if hasattr(doc_obj, 'pagesize') else landscape(A4)

    # Градиентная полоска по всей ширине (как в клиентских PDF)
    if os.path.exists(FOOTER_IMG):
        try:
            canvas_obj.drawImage(
                FOOTER_IMG, 0, 0,
                width=pw, height=12 * mm,
                preserveAspectRatio=False, mask='auto')
        except Exception:
            pass

    # Белый блок с текстом поверх полоски
    block_w = 200
    block_h = 28
    x = (pw - block_w) / 2
    y = 2 * mm

    canvas_obj.setStrokeColor(colors.HexColor('#CCCCCC'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.roundRect(x, y, block_w, block_h, 4, fill=1, stroke=1)

    # Текст
    fn = _font()
    canvas_obj.setFont(fn, 7)
    canvas_obj.setFillColor(colors.HexColor('#666666'))
    canvas_obj.drawCentredString(pw / 2, y + 16, "\u0418\u043d\u0442\u0435\u0440\u044c\u0435\u0440\u043d\u043e\u0435 \u0431\u044e\u0440\u043e FESTIVAL COLOR")
    canvas_obj.drawCentredString(pw / 2, y + 6, f"\u0441\u0442\u0440. {doc_obj.page}")

    canvas_obj.restoreState()


# ── Стили ─────────────────────────────────────────────────

def _table_style():
    fn = _font()
    fb = _font_bold()
    return TableStyle([
        ('BACKGROUND',    (0, 0), (-1, 0),  HEADER_BG),
        ('TEXTCOLOR',     (0, 0), (-1, 0),  HEADER_FG),
        ('FONTNAME',      (0, 0), (-1, 0),  fb),
        ('FONTSIZE',      (0, 0), (-1, 0),  9),
        ('ALIGN',         (0, 0), (-1, 0),  'CENTER'),
        ('TOPPADDING',    (0, 0), (-1, 0),  6),
        ('BOTTOMPADDING', (0, 0), (-1, 0),  6),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [ROW_ODD, ROW_EVEN]),
        ('FONTNAME',      (0, 1), (-1, -1), fn),
        ('FONTSIZE',      (0, 1), (-1, -1), 8),
        ('ALIGN',         (0, 1), (-1, -1), 'LEFT'),
        ('TOPPADDING',    (0, 1), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 4),
        ('VALIGN',        (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID',          (0, 0), (-1, -1), 0.25, BORDER_COLOR),
        ('LINEBELOW',     (0, 0), (-1, 0),  1.0, colors.HexColor('#1A252F')),
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ])


# ── Инфо-блок ────────────────────────────────────────────

def _project_info_block(contract, fn, fb, available_w):
    """Возвращает элементы: лого, заголовок, блок с инфо о проекте."""
    elements = []

    # Лого (по центру)
    if os.path.exists(LOGO_PATH):
        try:
            logo = RLImage(LOGO_PATH, width=40 * mm, height=18 * mm)
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 4 * mm))
        except Exception:
            pass

    # Информация о проекте — компактная таблица на всю ширину
    info_rows = []
    address = getattr(contract, 'address', None) or '-'
    area = getattr(contract, 'area', None) or 0
    ptype = getattr(contract, 'project_type', None) or '-'
    psubtype = getattr(contract, 'project_subtype', None) or ''
    agent = getattr(contract, 'agent_type', None) or '-'
    city = getattr(contract, 'city', None) or '-'

    label_style = ParagraphStyle('InfoLabel', fontName=fb, fontSize=8,
                                  textColor=colors.HexColor('#666666'))
    value_style = ParagraphStyle('InfoValue', fontName=fn, fontSize=9,
                                  textColor=colors.HexColor('#333333'))

    info_rows.append([
        Paragraph('Адрес:', label_style),
        Paragraph(address, value_style),
        Paragraph('Площадь:', label_style),
        Paragraph(f'{area} м\u00b2', value_style),
    ])
    type_text = f'{ptype}'
    if psubtype:
        type_text += f' / {psubtype}'
    info_rows.append([
        Paragraph('Тип проекта:', label_style),
        Paragraph(type_text, value_style),
        Paragraph('Агент:', label_style),
        Paragraph(agent, value_style),
    ])
    info_rows.append([
        Paragraph('Город:', label_style),
        Paragraph(city, value_style),
        Paragraph('Дата:', label_style),
        Paragraph(date.today().strftime('%d.%m.%Y'), value_style),
    ])

    # Ширины: label1=80, value1=заполняет, label2=72, value2=остаток
    lbl1, lbl2, val2 = 80, 72, available_w * 0.25
    val1 = available_w - lbl1 - lbl2 - val2
    info_table = Table(info_rows, colWidths=[lbl1, val1, lbl2, val2])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, -1), (-1, -1), 0.5, BORDER_COLOR),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 5 * mm))

    return elements


# ── Публичная функция ─────────────────────────────────────

def build_timeline_pdf(
    title: str,
    contract,
    headers: list[str],
    rows: list[list],
    col_widths: list[int],
    row_styles: list[dict] | None = None,
) -> bytes:
    """
    Генерирует PDF для таблицы сроков (timeline / supervision).

    Args:
        title: Заголовок документа
        contract: ORM-объект Contract
        headers: Заголовки столбцов
        rows: Список строк (каждая строка — список Paragraph)
        col_widths: Ширины столбцов
        row_styles: Доп. стили для строк [{row_idx, bg, fg}, ...]

    Returns:
        bytes — содержимое PDF
    """
    _register_fonts()
    fn = _font()
    fb = _font_bold()

    MARGIN_LR = 15 * mm
    page = landscape(A4)
    available_w = page[0] - 2 * MARGIN_LR

    output = io.BytesIO()
    doc = SimpleDocTemplate(
        output,
        pagesize=page,
        leftMargin=MARGIN_LR, rightMargin=MARGIN_LR,
        topMargin=15 * mm, bottomMargin=20 * mm,
    )

    elements = []

    # Инфо-блок
    elements.extend(_project_info_block(contract, fn, fb, available_w))

    # Заголовок таблицы — жёлтая полоска
    title_style = ParagraphStyle('TitleH', fontName=fb, fontSize=13,
                                  textColor=colors.HexColor('#333333'), leading=16)
    title_tbl = Table(
        [['', Paragraph(f'<b>{title}</b>', title_style)]],
        colWidths=[4, None],
    )
    title_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, 0), ACCENT),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (0, 0), 0),
        ('RIGHTPADDING', (0, 0), (0, 0), 0),
        ('LEFTPADDING', (1, 0), (1, 0), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(title_tbl)
    elements.append(Spacer(1, 3 * mm))

    # Auto-scale col_widths на всю доступную ширину
    total_w = sum(col_widths)
    if total_w < available_w:
        scale = available_w / total_w
        col_widths = [w * scale for w in col_widths]

    # Основная таблица
    header_style = ParagraphStyle('H', fontName=fb, fontSize=9,
                                    leading=11, textColor=colors.white,
                                    alignment=TA_CENTER)
    header_row = [Paragraph(h, header_style) for h in headers]
    table_data = [header_row] + rows
    table = Table(table_data, colWidths=col_widths, repeatRows=1)

    style_cmds = list(_table_style().getCommands())

    # Доп. стили строк (заголовки этапов, просрочки и т.д.)
    if row_styles:
        for rs in row_styles:
            idx = rs['row_idx']
            if 'bg' in rs:
                style_cmds.append(('BACKGROUND', (0, idx), (-1, idx),
                                   colors.HexColor(rs['bg'])))
            if 'fg' in rs:
                style_cmds.append(('TEXTCOLOR', (0, idx), (-1, idx),
                                   colors.HexColor(rs['fg'])))

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    output.seek(0)
    return output.read()
