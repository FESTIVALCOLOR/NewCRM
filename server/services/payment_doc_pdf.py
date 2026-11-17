"""
PDF «Документ, подтверждающий расчёт» (ИП на ПСН без ККТ, п. 2.1 ст. 2 54-ФЗ).

Реквизиты (ст. 4.7 54-ФЗ, абз. 4–12 п. 1): наименование и порядковый номер документа, дата, время и место расчёта,
ФИО и ИНН ИП, система налогообложения, признак расчёта, наименование услуги, цена и сумма (без НДС),
форма расчёта, должность и фамилия лица, осуществившего расчёт.
Логотип — всегда студии «Фестиваль» (по центру сверху), независимо от агента в договоре.
"""

import io
import logging
import os

from pdf_helper import _BASE, _font, _font_bold
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Image as RLImage
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

logger = logging.getLogger(__name__)

FALLBACK_LOGO = os.path.join(_BASE, "resources", "festival_logo.png")
BORDER = colors.HexColor("#DEE2E6")
LABEL_BG = colors.HexColor("#F8F9FA")


def _esc(value):
    """Текст для Paragraph: reportlab разбирает разметку, поэтому экранируем & < >."""
    from xml.sax.saxutils import escape

    return escape(str(value or ""))


def _money(value):
    return f"{float(value or 0):,.2f}".replace(",", " ").replace(".", ",") + " ₽"


def festival_logo_bytes(db=None):
    """Логотип «Фестиваль»: загруженный в админке (реквизит logo_фестиваль на ЯД), иначе файл из resources."""
    if db is not None:
        try:
            from yandex_disk_service import YandexDiskService

            from database import CompanyRequisite

            req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == "logo_фестиваль").first()
            if req and req.file_path:
                return YandexDiskService().download_file_to_bytes(req.file_path)
        except Exception as e:
            logger.warning(f"Документ об оплате: лого с ЯД недоступно, берём локальное ({e})")
    try:
        with open(FALLBACK_LOGO, "rb") as f:
            return f.read()
    except OSError:
        return None


def _logo_flowable(logo_bytes):
    if not logo_bytes:
        return None
    try:
        from reportlab.lib.utils import ImageReader

        reader = ImageReader(io.BytesIO(logo_bytes))
        width, height = reader.getSize()
        target_h = 22 * mm
        target_w = min(70 * mm, target_h * width / height)
        target_h = target_w * height / width
        image = RLImage(io.BytesIO(logo_bytes), width=target_w, height=target_h)
        image.hAlign = "CENTER"
        return image
    except Exception as e:
        logger.warning(f"Документ об оплате: не удалось вставить лого ({e})")
        return None


def build_payment_doc_pdf(data, logo_bytes=None, annulled=False):
    """data — «замороженные» реквизиты документа (ClientPaymentDoc.data)."""
    fn, fb = _font(), _font_bold()
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=f"Документ, подтверждающий расчёт № {data.get('number', '')}",
    )
    width = A4[0] - 36 * mm

    title_style = ParagraphStyle("T", fontName=fb, fontSize=13, leading=17, alignment=TA_CENTER)
    sub_style = ParagraphStyle("S", fontName=fn, fontSize=8, leading=11, alignment=TA_CENTER, textColor=colors.HexColor("#666666"))
    label_style = ParagraphStyle("L", fontName=fb, fontSize=8.5, leading=11, textColor=colors.HexColor("#444444"))
    value_style = ParagraphStyle("V", fontName=fn, fontSize=9.5, leading=12)
    cell_style = ParagraphStyle("C", fontName=fn, fontSize=9, leading=12)
    cell_bold = ParagraphStyle("CB", fontName=fb, fontSize=9, leading=12)
    right_style = ParagraphStyle("R", fontName=fn, fontSize=9, leading=12, alignment=TA_RIGHT)
    right_bold = ParagraphStyle("RB", fontName=fb, fontSize=10.5, leading=14, alignment=TA_RIGHT)
    annul_style = ParagraphStyle("A", fontName=fb, fontSize=12, leading=16, alignment=TA_CENTER, textColor=colors.HexColor("#C62828"))

    elements = []
    logo = _logo_flowable(logo_bytes)
    if logo:
        elements += [logo, Spacer(1, 5 * mm)]

    elements.append(Paragraph(f"ДОКУМЕНТ, ПОДТВЕРЖДАЮЩИЙ РАСЧЁТ № {data.get('number', '')}", title_style))
    elements.append(Spacer(1, 1.5 * mm))
    elements.append(Paragraph("выдан без применения контрольно-кассовой техники на основании п. 2.1 ст. 2 Федерального закона от 22.05.2003 № 54-ФЗ", sub_style))
    if annulled:
        elements += [Spacer(1, 3 * mm), Paragraph("ДОКУМЕНТ АННУЛИРОВАН", annul_style)]
    elements.append(Spacer(1, 6 * mm))

    rows = [
        ("Дата и время расчёта", f"{data.get('date_text', '')} {data.get('time', '')} (МСК)"),
        ("Место расчёта", data.get("place", "")),
        ("Исполнитель", data.get("seller_name", "")),
        ("ИНН", data.get("seller_inn", "")),
    ]
    if data.get("seller_ogrnip"):
        rows.append(("ОГРНИП", data["seller_ogrnip"]))
    rows += [
        ("Система налогообложения", data.get("tax_system", "")),
        ("Признак расчёта", data.get("calc_sign", "")),
    ]
    if data.get("client_name"):
        rows.append(("Клиент", data["client_name"]))
    if data.get("basis"):
        rows.append(("Основание", data["basis"]))

    info = Table([[Paragraph(k, label_style), Paragraph(_esc(v) or "—", value_style)] for k, v in rows], colWidths=[52 * mm, width - 52 * mm])
    info.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (0, -1), LABEL_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements += [info, Spacer(1, 6 * mm)]

    amount = _money(data.get("amount"))
    head = [Paragraph(t, cell_bold) for t in ("№", "Наименование услуги", "Кол.", "Цена", "Сумма")]
    item = [Paragraph("1", cell_style), Paragraph(_esc(data.get("service")), cell_style), Paragraph("1", cell_style), Paragraph(amount, right_style), Paragraph(amount, right_style)]
    items = Table([head, item], colWidths=[9 * mm, width - 9 * mm - 16 * mm - 60 * mm, 16 * mm, 30 * mm, 30 * mm])
    items.setStyle(
        TableStyle(
            [
                ("GRID", (0, 0), (-1, -1), 0.5, BORDER),
                ("BACKGROUND", (0, 0), (-1, 0), LABEL_BG),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    elements += [items, Spacer(1, 4 * mm)]

    totals = Table(
        [
            [Paragraph("ИТОГО:", right_bold), Paragraph(amount, right_bold)],
            [Paragraph("НДС:", right_style), Paragraph("без НДС", right_style)],
            [Paragraph(f"Форма расчёта: {_esc(data.get('method_text'))}", right_style), Paragraph(amount, right_style)],
        ],
        colWidths=[width - 40 * mm, 40 * mm],
    )
    totals.setStyle(TableStyle([("TOPPADDING", (0, 0), (-1, -1), 1), ("BOTTOMPADDING", (0, 0), (-1, -1), 1)]))
    elements += [totals, Spacer(1, 8 * mm)]

    # Без тегов <b>: семейство DejaVu не зарегистрировано как bold-пара, используем отдельный шрифт
    elements.append(Paragraph(f"Расчёт осуществил: {_esc(data.get('cashier'))}", ParagraphStyle("CS", fontName=fb, fontSize=9.5, leading=12)))
    if data.get("public_url"):
        elements += [Spacer(1, 6 * mm), Paragraph(f"Электронная копия документа: {_esc(data['public_url'])}", sub_style)]

    doc.build(elements)
    return buffer.getvalue()


def qr_svg(text, size=220):
    """QR-код (SVG) средствами reportlab — для СБП-ссылки в окне «Сформировать оплату»."""
    from reportlab.graphics import renderSVG
    from reportlab.graphics.barcode.qr import QrCodeWidget
    from reportlab.graphics.shapes import Drawing

    widget = QrCodeWidget(text)
    x1, y1, x2, y2 = widget.getBounds()
    drawing = Drawing(size, size, transform=[size / (x2 - x1), 0, 0, size / (y2 - y1), 0, 0])
    drawing.add(widget)
    svg = renderSVG.drawToString(drawing)
    return svg[svg.find("<svg") :] if "<svg" in svg else svg
