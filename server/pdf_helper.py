"""
Серверная утилита генерации PDF для таблиц сроков.

Стилистика: тёмно-серые заголовки таблиц, лого logo_pdf.png,
инфо-блок в рамке, статусы как в программе, итоги этапов.
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

# ── Цвета ─────────────────────────────────────────────────
HEADER_BG = colors.HexColor('#444444')       # тёмно-серый заголовок
HEADER_FG = colors.white
ROW_ODD = colors.white
ROW_EVEN = colors.HexColor('#F8F9FA')
BORDER_COLOR = colors.HexColor('#DEE2E6')

# Цвета строк как в программе
COLOR_HEADER_ROW = '#2F5496'        # заголовок этапа (синий)
COLOR_SUBHEADER_ROW = '#D6E4F0'     # заголовок подэтапа
COLOR_OK = '#E8F5E9'                # в срок (зелёный)
COLOR_OVERDUE = '#FFEBEE'           # просрочен (красный)
COLOR_SKIPPED = '#F5F5F5'           # пропущен
COLOR_OUT_SCOPE = '#E0E0E0'         # вне расчёта
COLOR_SUBTOTAL = '#E3F2FD'          # итого этапа (голубой)
COLOR_GRANDTOTAL = '#FFF8E1'        # итого общий (жёлтый)

# ── Базовый путь ресурсов ─────────────────────────────────
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
    """Градиентная полоска footer.jpg (8mm) + текст бюро + год.
    Номер страницы — над футером."""
    canvas_obj.saveState()
    pw = doc_obj.pagesize[0] if hasattr(doc_obj, 'pagesize') else landscape(A4)[0]

    strip_h = 8 * mm

    # Градиентная полоска
    if os.path.exists(FOOTER_IMG):
        try:
            canvas_obj.drawImage(
                FOOTER_IMG, 0, 0,
                width=pw, height=strip_h,
                preserveAspectRatio=False, mask='auto')
        except Exception:
            pass

    # Белый блок с текстом поверх полоски (компактный)
    block_w = 220
    block_h = 14
    x = (pw - block_w) / 2
    y = 1 * mm

    canvas_obj.setStrokeColor(colors.HexColor('#CCCCCC'))
    canvas_obj.setLineWidth(0.5)
    canvas_obj.setFillColor(colors.white)
    canvas_obj.roundRect(x, y, block_w, block_h, 3, fill=1, stroke=1)

    fn = _font()
    canvas_obj.setFont(fn, 6)
    canvas_obj.setFillColor(colors.HexColor('#666666'))
    year = date.today().year
    canvas_obj.drawCentredString(
        pw / 2, y + 4,
        f"\u0418\u043d\u0442\u0435\u0440\u044c\u0435\u0440\u043d\u043e\u0435 \u0431\u044e\u0440\u043e FESTIVAL COLOR \u2014 {year}"
    )

    # Номер страницы — над полоской
    canvas_obj.setFont(fn, 7)
    canvas_obj.setFillColor(colors.HexColor('#999999'))
    canvas_obj.drawCentredString(pw / 2, strip_h + 2 * mm, f"\u0441\u0442\u0440. {doc_obj.page}")

    canvas_obj.restoreState()


# ── Стиль таблицы ─────────────────────────────────────────

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
        ('LINEBELOW',     (0, 0), (-1, 0),  1.0, colors.HexColor('#333333')),
        ('BOX',           (0, 0), (-1, -1), 0.5, BORDER_COLOR),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
    ])


# ── Инфо-блок ────────────────────────────────────────────

def _project_info_block(contract, fn, fb, available_w):
    """Лого по центру + инфо о проекте в рамке с радиусами."""
    elements = []

    # Лого по центру (пропорции из файла)
    if os.path.exists(LOGO_PATH):
        try:
            logo = RLImage(LOGO_PATH, width=35 * mm, height=20 * mm,
                           kind='proportional')
            logo.hAlign = 'CENTER'
            elements.append(logo)
            elements.append(Spacer(1, 4 * mm))
        except Exception:
            pass

    # Информация о проекте
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
        Paragraph('\u0410\u0434\u0440\u0435\u0441:', label_style),
        Paragraph(address, value_style),
        Paragraph('\u041f\u043b\u043e\u0449\u0430\u0434\u044c:', label_style),
        Paragraph(f'{area} \u043c\u00b2', value_style),
    ])
    type_text = ptype
    if psubtype:
        type_text += f' / {psubtype}'
    info_rows.append([
        Paragraph('\u0422\u0438\u043f \u043f\u0440\u043e\u0435\u043a\u0442\u0430:', label_style),
        Paragraph(type_text, value_style),
        Paragraph('\u0410\u0433\u0435\u043d\u0442:', label_style),
        Paragraph(agent, value_style),
    ])
    info_rows.append([
        Paragraph('\u0413\u043e\u0440\u043e\u0434:', label_style),
        Paragraph(city, value_style),
        Paragraph('\u0414\u0430\u0442\u0430:', label_style),
        Paragraph(date.today().strftime('%d.%m.%Y'), value_style),
    ])

    lbl1, lbl2, val2 = 80, 72, available_w * 0.25
    val1 = available_w - lbl1 - lbl2 - val2
    info_table = Table(info_rows, colWidths=[lbl1, val1, lbl2, val2])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
        # Рамка с радиусами вокруг всего блока
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#CCCCCC')),
        ('ROUNDEDCORNERS', [4, 4, 4, 4]),
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
        title: Заголовок документа (будет в верхнем регистре)
        contract: ORM-объект Contract
        headers: Заголовки столбцов
        rows: Список строк (каждая строка — список Paragraph)
        col_widths: Ширины столбцов (пропорциональные, будут масштабированы)
        row_styles: Доп. стили для строк [{row_idx, bg, fg, bold}, ...]

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
        topMargin=15 * mm, bottomMargin=18 * mm,
    )

    elements = []

    # Инфо-блок (лого + инфо)
    elements.extend(_project_info_block(contract, fn, fb, available_w))

    # Заголовок — по центру, заглавные буквы, без жёлтой полоски
    title_style = ParagraphStyle(
        'TitleH', fontName=fb, fontSize=13,
        textColor=colors.HexColor('#333333'),
        leading=16, alignment=TA_CENTER,
        spaceBefore=0, spaceAfter=3 * mm,
    )
    elements.append(Paragraph(title.upper(), title_style))

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

    # Доп. стили строк (заголовки этапов, статусы, итоги)
    if row_styles:
        for rs in row_styles:
            idx = rs['row_idx']
            if 'bg' in rs:
                style_cmds.append(('BACKGROUND', (0, idx), (-1, idx),
                                   colors.HexColor(rs['bg'])))
            if 'fg' in rs:
                style_cmds.append(('TEXTCOLOR', (0, idx), (-1, idx),
                                   colors.HexColor(rs['fg'])))
            if rs.get('bold'):
                style_cmds.append(('FONTNAME', (0, idx), (-1, idx), fb))

    table.setStyle(TableStyle(style_cmds))
    elements.append(table)

    doc.build(elements, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    output.seek(0)
    return output.read()
