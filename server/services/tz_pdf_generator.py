"""
PDF генератор анкеты технического задания в фирменном стиле Festival Color.
Использует ReportLab (уже установлен в проекте).
"""

from datetime import datetime
import io
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import (
        HRFlowable,
        Image,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False
    logger.warning("reportlab не установлен — генерация PDF анкеты недоступна")


# ── Цвета бренда ─────────────────────────────────────────────────────────────
BRAND_PURPLE = colors.HexColor("#6B4FA0")
BRAND_LIGHT_PURPLE = colors.HexColor("#EDE8F5")
SECTION_HEADER_BG = colors.HexColor("#F0EDF8")
TABLE_BORDER = colors.HexColor("#CCCCCC")
LABEL_COLOR = colors.HexColor("#555555")
TEXT_BLACK = colors.HexColor("#222222")
GRAY_LIGHT = colors.HexColor("#F5F5F5")
WHITE = colors.white

# ── Пути ресурсов ─────────────────────────────────────────────────────────────
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOGO_PATH = os.path.join(_BASE_DIR, "..", "resources", "logo_pdf.png")
LOGO_PATH = os.path.normpath(LOGO_PATH)

# ── Символы чекбоксов ─────────────────────────────────────────────────────────
CHECKBOX_EMPTY = "□"
CHECKBOX_CHECKED = "☑"


def _register_fonts() -> str:
    """Регистрирует шрифт с поддержкой кириллицы. Возвращает имя шрифта."""
    # Порядок поиска: DejaVu (Linux), Arial (Windows), Helvetica (fallback)
    candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
        ("/usr/share/fonts/dejavu/DejaVuSans.ttf", "DejaVuSans"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "LiberationSans"),
        ("C:/Windows/Fonts/arial.ttf", "Arial"),
        ("C:/Windows/Fonts/calibri.ttf", "Calibri"),
    ]
    bold_candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold"),
        ("/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold"),
        ("/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "LiberationSans-Bold"),
        ("C:/Windows/Fonts/arialbd.ttf", "Arial-Bold"),
        ("C:/Windows/Fonts/calibrib.ttf", "Calibri-Bold"),
    ]
    italic_candidates = [
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf", "DejaVuSans-Italic"),
        ("/usr/share/fonts/dejavu/DejaVuSans-Oblique.ttf", "DejaVuSans-Italic"),
        ("C:/Windows/Fonts/ariali.ttf", "Arial-Italic"),
    ]

    font_name = "Helvetica"
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                font_name = name
                # Bold
                for bp, bn in bold_candidates:
                    if os.path.exists(bp):
                        try:
                            pdfmetrics.registerFont(TTFont(bn, bp))
                        except Exception:
                            pass
                        break
                # Italic
                for ip, in_ in italic_candidates:
                    if os.path.exists(ip):
                        try:
                            pdfmetrics.registerFont(TTFont(in_, ip))
                        except Exception:
                            pass
                        break
                break
            except Exception:
                continue
    return font_name


def _build_styles(font: str, font_bold: str, font_italic: str):
    """Создаёт словарь стилей Paragraph."""
    base = {"fontName": font, "leading": 14, "wordWrap": "CJK"}
    return {
        "title": ParagraphStyle(
            "TZTitle",
            fontName=font_bold,
            fontSize=14,
            leading=18,
            alignment=1,
            textColor=TEXT_BLACK,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "TZSubtitle",
            fontName=font,
            fontSize=10,
            leading=14,
            alignment=1,
            textColor=LABEL_COLOR,
            underline=1,
            spaceAfter=10,
        ),
        "section_header": ParagraphStyle(
            "TZSection",
            fontName=font_bold,
            fontSize=11,
            leading=16,
            alignment=1,
            textColor=TEXT_BLACK,
            spaceBefore=4,
            spaceAfter=4,
        ),
        "room_header": ParagraphStyle(
            "TZRoom",
            fontName=font_bold,
            fontSize=10,
            leading=15,
            alignment=1,
            textColor=BRAND_PURPLE,
            spaceBefore=4,
            spaceAfter=2,
        ),
        "room_subheader": ParagraphStyle(
            "TZRoomSub",
            fontName=font_italic,
            fontSize=8,
            leading=12,
            alignment=1,
            textColor=LABEL_COLOR,
            spaceAfter=4,
        ),
        "label": ParagraphStyle(
            "TZLabel",
            fontName=font_italic,
            fontSize=9,
            leading=13,
            textColor=LABEL_COLOR,
            **{k: v for k, v in base.items() if k not in ("fontName", "leading")},
        ),
        "value": ParagraphStyle(
            "TZValue",
            fontName=font,
            fontSize=9,
            leading=13,
            textColor=TEXT_BLACK,
            **{k: v for k, v in base.items() if k not in ("fontName", "leading")},
        ),
        "value_bold": ParagraphStyle(
            "TZValueBold",
            fontName=font_bold,
            fontSize=9,
            leading=13,
            textColor=TEXT_BLACK,
        ),
        "checkbox": ParagraphStyle(
            "TZCheckbox",
            fontName=font,
            fontSize=9,
            leading=14,
            textColor=TEXT_BLACK,
            leftIndent=0,
        ),
        "checkbox_checked": ParagraphStyle(
            "TZCheckboxChecked",
            fontName=font_bold,
            fontSize=9,
            leading=14,
            textColor=BRAND_PURPLE,
            leftIndent=0,
        ),
        "checkbox_italic": ParagraphStyle(
            "TZCheckboxItalic",
            fontName=font_italic,
            fontSize=9,
            leading=14,
            textColor=LABEL_COLOR,
            leftIndent=12,
        ),
        "checkbox_child": ParagraphStyle(
            "TZCheckboxChild",
            fontName=font_italic,
            fontSize=8,
            leading=12,
            textColor=LABEL_COLOR,
            leftIndent=20,
        ),
        "checkbox_child_checked": ParagraphStyle(
            "TZCheckboxChildChecked",
            fontName=font_bold,
            fontSize=8,
            leading=12,
            textColor=BRAND_PURPLE,
            leftIndent=20,
        ),
        "contract_ref": ParagraphStyle(
            "TZContractRef",
            fontName=font_italic,
            fontSize=9,
            leading=12,
            alignment=2,
            textColor=LABEL_COLOR,
        ),
        "footer": ParagraphStyle(
            "TZFooter",
            fontName=font,
            fontSize=8,
            leading=11,
            textColor=LABEL_COLOR,
        ),
        "footer_bold": ParagraphStyle(
            "TZFooterBold",
            fontName=font_bold,
            fontSize=8,
            leading=11,
            textColor=LABEL_COLOR,
        ),
    }


class _TZPageTemplate:
    """Callback для рисования шапки и подвала на каждой странице."""

    def __init__(self, font: str, font_italic: str, contract_number: str, logo_bytes: bytes | None = None, logo_path: str | None = None):
        self.font = font
        self.font_italic = font_italic
        self.contract_number = contract_number
        self.logo_bytes = logo_bytes
        self.logo_path = logo_path or LOGO_PATH
        self._page_count = 0

    def on_page(self, canvas, doc):
        canvas.saveState()
        w, h = A4

        # ── Верхняя шапка ──────────────────────────────────────────────────
        # Логотип: приоритет — байты из БД (агент), fallback — файл
        logo_drawn = False
        if self.logo_bytes:
            try:
                from reportlab.lib.utils import ImageReader

                img_reader = ImageReader(io.BytesIO(self.logo_bytes))
                canvas.drawImage(
                    img_reader,
                    15 * mm,
                    h - 28 * mm,
                    width=45 * mm,
                    height=22 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
                logo_drawn = True
            except Exception:
                pass
        if not logo_drawn and os.path.exists(self.logo_path):
            try:
                canvas.drawImage(
                    self.logo_path,
                    15 * mm,
                    h - 28 * mm,
                    width=45 * mm,
                    height=22 * mm,
                    preserveAspectRatio=True,
                    mask="auto",
                )
            except Exception:
                pass

        # Текст "www.festivalcolor.ru"
        canvas.setFont(self.font_italic, 7)
        canvas.setFillColor(LABEL_COLOR)
        canvas.drawRightString(w - 15 * mm, h - 29 * mm, "www.festivalcolor.ru")

        # Горизонтальная линия под шапкой
        canvas.setStrokeColor(BRAND_PURPLE)
        canvas.setLineWidth(1)
        canvas.line(15 * mm, h - 32 * mm, w - 15 * mm, h - 32 * mm)

        # Номер договора (справа под линией)
        if self.contract_number:
            canvas.setFont(self.font_italic, 8)
            canvas.setFillColor(LABEL_COLOR)
            canvas.drawRightString(w - 15 * mm, h - 38 * mm, f"Приложение к Договору № {self.contract_number}")

        # ── Нижний подвал ──────────────────────────────────────────────────
        footer_y = 12 * mm
        canvas.setStrokeColor(TABLE_BORDER)
        canvas.setLineWidth(0.5)
        canvas.line(15 * mm, footer_y + 6 * mm, w - 15 * mm, footer_y + 6 * mm)

        # Подпись заказчика
        canvas.setFont(self.font, 8)
        canvas.setFillColor(LABEL_COLOR)
        canvas.drawString(15 * mm, footer_y + 2 * mm, "Заказчик: ____________________ / ____________________ / Дата: ___________")

        # Текст под линиями
        canvas.setFont(self.font_italic, 7)
        canvas.drawString(23 * mm, footer_y - 1 * mm, "ФИО")
        canvas.drawString(62 * mm, footer_y - 1 * mm, "подпись")
        canvas.drawString(107 * mm, footer_y - 1 * mm, "число")

        # Номер страницы
        page_num = doc.page
        canvas.setFont(self.font_italic, 8)
        canvas.setFillColor(LABEL_COLOR)
        canvas.drawRightString(w - 15 * mm, footer_y + 2 * mm, f"С т р а н и ц а  {page_num}")

        canvas.restoreState()


def _yn_html(text: str) -> str:
    """Возвращает цветной HTML-текст для Да/Нет ответов (используется в Paragraph)."""
    if text == "Да":
        return '<font color="#6B4FA0"><b> Да </b></font>'
    elif text == "Нет":
        return '<font color="#C62828"><b> Нет </b></font>'
    return text or "—"


def _checkbox_opt_line(opt: dict, is_checked: bool, q_id: str, answers: dict) -> str:
    """Строит HTML-строку для одного чекбокса checkbox_group."""
    mark = CHECKBOX_CHECKED if is_checked else CHECKBOX_EMPTY
    label = opt.get("label", "")
    if is_checked:
        line = f'<b><font color="#6B4FA0">{mark}  {label}</font></b>'
    else:
        line = f"{mark}  {label}"
    if opt.get("has_text_input") and is_checked:
        extra = answers.get(q_id + "_text_" + opt["value"], "")
        if extra:
            tl = opt.get("text_input_label", "")
            line += f'  <font color="#6B4FA0">{tl + ": " if tl else ""}{extra}</font>'
    if opt.get("has_select"):
        sel_val = answers.get(q_id + "_text_" + opt["value"] + "_sel", "")
        if sel_val:
            sl = opt.get("select_label", "")
            line += f'  <font color="#6B4FA0">({sl + ": " if sl else ""}{sel_val})</font>'
    return line


def _render_checkbox_group(q_id: str, question: dict, answer, answers: dict, styles: dict) -> list:
    """Возвращает список Paragraph для checkbox_group вопроса."""
    options = question.get("options", [])
    selected = answer if isinstance(answer, list) else ([answer] if answer else [])
    value_lines = []
    for opt in options:
        opt_type = opt.get("type", "")
        if opt_type == "separator":
            value_lines.append(Paragraph(f"── {opt.get('label', '')} ──", styles["checkbox_italic"]))
        elif opt_type == "yes_no_inline":
            yn_val = answers.get(q_id + "_text_" + opt["value"], "")
            value_lines.append(Paragraph(f"{opt.get('label', '')}:  {_yn_html(yn_val)}", styles["checkbox"]))
        elif opt_type == "text_field":
            text_val = answers.get(q_id + "_text_" + opt["value"], "")
            val_html = f'<font color="#6B4FA0">{text_val}</font>' if text_val else "—"
            value_lines.append(Paragraph(f"{opt.get('label', '')}: {val_html}", styles["label"]))
        else:
            is_checked = opt.get("value", "") in selected
            line = _checkbox_opt_line(opt, is_checked, q_id, answers)
            if is_checked:
                style_key = "checkbox_checked"
            elif opt.get("italic"):
                style_key = "checkbox_italic"
            else:
                style_key = "checkbox"
            value_lines.append(Paragraph(line, styles[style_key]))
            if is_checked and opt.get("children"):
                children_ans = answers.get(q_id + "_sub_" + opt["value"], [])
                children_sel = children_ans if isinstance(children_ans, list) else []
                for child in opt["children"]:
                    c_val = child.get("value", "")
                    child_checked = c_val in children_sel
                    c_mark = CHECKBOX_CHECKED if child_checked else CHECKBOX_EMPTY
                    child_label = child.get("label", "")
                    if child_checked:
                        c_line = f'<b><font color="#6B4FA0">{c_mark}  {child_label}</font></b>'
                        value_lines.append(Paragraph(c_line, styles["checkbox_child_checked"]))
                    else:
                        value_lines.append(Paragraph(f"   {c_mark}  {child_label}", styles["checkbox_child"]))
    return value_lines


def _electro_opt_line(opt: dict, is_checked: bool, answer_obj: dict) -> str:
    """Строит HTML-строку для одного чекбокса electro_block."""
    mark = CHECKBOX_CHECKED if is_checked else CHECKBOX_EMPTY
    label = opt.get("label", "")
    if is_checked:
        line = f'<b><font color="#6B4FA0">{mark}  {label}</font></b>'
    else:
        line = f"{mark}  {label}"
    if opt.get("has_text_input") and is_checked:
        extra = answer_obj.get(opt["value"] + "_text", "")
        if extra:
            tl = opt.get("text_input_label", "Количество")
            line += f'  <font color="#6B4FA0">{tl}: {extra}</font>'
    if opt.get("has_select"):
        sel_val = answer_obj.get(opt["value"] + "_select", "")
        if sel_val:
            sl = opt.get("select_label", "")
            line += f'  <font color="#6B4FA0">({sl + ": " if sl else ""}{sel_val})</font>'
    return line


def _render_electro_block(question: dict, answer_obj: dict, styles: dict) -> list:
    """Возвращает список Paragraph для electro_block вопроса."""
    value_lines = []
    for sf in question.get("subfields", []):
        sf_val = answer_obj.get(sf.get("key", ""), "")
        if sf.get("type") == "yes_no":
            value_lines.append(Paragraph(f"{sf.get('label', '')}:  {_yn_html(sf_val)}", styles["checkbox"]))
        else:
            val_html = f'<font color="#6B4FA0">{sf_val}</font>' if sf_val else "—"
            value_lines.append(Paragraph(f"{sf.get('label', '')}: {val_html}", styles["label"]))
    checked_list = answer_obj.get("_checked", [])
    if not isinstance(checked_list, list):
        checked_list = []
    for opt in question.get("checkboxes", []):
        is_checked = opt.get("value", "") in checked_list
        line = _electro_opt_line(opt, is_checked, answer_obj)
        value_lines.append(Paragraph(line, styles["checkbox"]))
    if question.get("has_comment"):
        comment = answer_obj.get("_comment", "")
        if comment:
            cl = question.get("comment_label", "Пожелания")
            value_lines.append(Paragraph(f'<i>{cl}: <font color="#6B4FA0">{comment}</font></i>', styles["value"]))
    return value_lines


def _render_question_rows(question: dict, answers: dict, styles: dict) -> list:
    """Рендерит один вопрос как список строк для таблицы [(label_para, value_para)]."""
    rows = []
    q_id = question.get("id", "")
    q_type = question.get("type", "text")
    label = question.get("label", "")
    answer = answers.get(q_id, "") if answers else ""
    label_para = Paragraph(label, styles["label"])

    if q_type in ("text", "textarea"):
        rows.append((label_para, Paragraph(str(answer) if answer else "", styles["value_bold"])))
    elif q_type == "contacts":
        answer_dict = answer if isinstance(answer, dict) else {}
        sub_lines = [f"{sf['label']}: {answer_dict.get(sf['key'], '')}" for sf in question.get("subfields", [])]
        rows.append((label_para, Paragraph("<br/>".join(sub_lines), styles["value"])))
    elif q_type == "checkbox_group":
        value_lines = _render_checkbox_group(q_id, question, answer, answers, styles)
        for i, line in enumerate(value_lines):
            lbl = label_para if i == 0 else Paragraph("", styles["label"])
            rows.append((lbl, line))
    elif q_type == "electro_block":
        answer_obj = answer if isinstance(answer, dict) else {}
        value_lines = _render_electro_block(question, answer_obj, styles)
        for i, line in enumerate(value_lines):
            lbl = label_para if i == 0 else Paragraph("", styles["label"])
            rows.append((lbl, line))

    return rows or [(label_para, Paragraph("", styles["value"]))]


def _build_section_table(section: dict, answers: dict, styles: dict, page_width: float) -> list:
    """Возвращает список Flowable для одной секции."""
    flowables = []
    title = section.get("title", "")

    # Заголовок секции (полная ширина, серый фон)
    header_data = [[Paragraph(title, styles["section_header"])]]
    header_table = Table(header_data, colWidths=[page_width])
    header_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SECTION_HEADER_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    flowables.append(header_table)

    # Строки вопросов
    questions = section.get("questions", [])
    col_label = page_width * 0.35
    col_value = page_width * 0.65
    rows_data = []

    for q in questions:
        q_rows = _render_question_rows(q, answers or {}, styles)
        rows_data.extend(q_rows)

    if rows_data:
        tbl = Table(rows_data, colWidths=[col_label, col_value], repeatRows=0)
        style_cmds = [
            ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
        ]
        tbl.setStyle(TableStyle(style_cmds))
        flowables.append(tbl)

    return flowables


def _build_room_flowables(room_instance: dict, room_template: dict, styles: dict, page_width: float) -> list:
    """Возвращает список Flowable для одного помещения."""
    flowables = []
    room_name = room_instance.get("room_name", room_template.get("name", "Помещение"))
    room_answers = room_instance.get("answers", {})

    # Заголовок комнаты
    hdr_data = [
        [Paragraph(room_name, styles["room_header"])],
        [Paragraph("(Название комнаты)", styles["room_subheader"])],
    ]
    hdr_tbl = Table(hdr_data, colWidths=[page_width])
    hdr_tbl.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), SECTION_HEADER_BG),
                ("BOX", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
                ("TOPPADDING", (0, 0), (-1, 0), 6),
                ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ]
        )
    )
    flowables.append(hdr_tbl)

    # Вопросы комнаты
    questions = room_template.get("questions", [])
    col_label = page_width * 0.35
    col_value = page_width * 0.65
    rows_data = []
    for q in questions:
        q_rows = _render_question_rows(q, room_answers, styles)
        rows_data.extend(q_rows)

    if rows_data:
        tbl = Table(rows_data, colWidths=[col_label, col_value])
        tbl.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.5, TABLE_BORDER),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("BACKGROUND", (0, 0), (0, -1), GRAY_LIGHT),
                ]
            )
        )
        flowables.append(tbl)

    return flowables


def generate_tz_pdf(
    template_data: dict,
    answers: dict,
    contract_number: str = "",
    project_type: str = "",
    agent_type: str | None = None,
    db=None,
) -> bytes | None:
    """
    Генерирует PDF анкеты ТЗ.

    Args:
        template_data: шаблон анкеты (sections + room_templates)
        answers: ответы клиента {general_answers: {...}, rooms: [...]}
        contract_number: номер договора для заголовка
        project_type: тип проекта

    Returns:
        bytes PDF-документа или None при ошибке
    """
    if not REPORTLAB_AVAILABLE:
        logger.error("reportlab не установлен")
        return None

    try:
        font = _register_fonts()
        # Определяем bold и italic варианты
        bold_map = {
            "DejaVuSans": "DejaVuSans-Bold",
            "LiberationSans": "LiberationSans-Bold",
            "Arial": "Arial-Bold",
            "Calibri": "Calibri-Bold",
        }
        italic_map = {
            "DejaVuSans": "DejaVuSans-Italic",
            "Arial": "Arial-Italic",
        }
        font_bold = bold_map.get(font, font)
        font_italic = italic_map.get(font, font)

        # Проверяем реально зарегистрированные шрифты
        registered = pdfmetrics.getRegisteredFontNames()
        if font_bold not in registered:
            font_bold = font
        if font_italic not in registered:
            font_italic = font

        styles = _build_styles(font, font_bold, font_italic)

        buf = io.BytesIO()
        margin_top = 42 * mm  # под шапку
        margin_bottom = 25 * mm  # над подвалом
        margin_lr = 15 * mm

        doc = SimpleDocTemplate(
            buf,
            pagesize=A4,
            topMargin=margin_top,
            bottomMargin=margin_bottom,
            leftMargin=margin_lr,
            rightMargin=margin_lr,
        )

        page_w = A4[0] - 2 * margin_lr

        # Загружаем лого агента из БД если передан db + agent_type
        logo_bytes = None
        if db is not None and agent_type:
            try:
                from database import CompanyRequisite

                req_type = f"logo_{agent_type.strip().lower()}"
                req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == req_type).first()
                if req and req.file_path:
                    from yandex_disk_service import YandexDiskService

                    yd = YandexDiskService()
                    logo_bytes = yd.download_file_to_bytes(req.file_path)
            except Exception as e:
                logger.warning(f"Не удалось загрузить лого агента {agent_type}: {e}")

        page_template = _TZPageTemplate(font, font_italic, contract_number, logo_bytes=logo_bytes)

        story = []

        # ── Титульная часть ──────────────────────────────────────────────────
        pt = "дизайн-проекта интерьера"
        if project_type == "Шаблонный":
            pt = "шаблонного дизайн-проекта интерьера"
        story.append(Paragraph("ТЕХНИЧЕСКОЕ ЗАДАНИЕ", styles["title"]))
        story.append(Paragraph(f"на разработку {pt}", styles["subtitle"]))
        story.append(Spacer(1, 6 * mm))

        general_answers = answers.get("general_answers", {}) if answers else {}
        rooms_data = answers.get("rooms", []) if answers else []

        # ── Статические секции до комнат ────────────────────────────────────
        # Поддержка нового формата (sections_before_rooms) и старого (sections)
        sections_before = template_data.get("sections_before_rooms") or template_data.get("sections", [])
        for section in sections_before:
            flowables = _build_section_table(section, general_answers, styles, page_w)
            story.extend(flowables)
            story.append(Spacer(1, 4 * mm))

        # ── Раздел по комнатам ──────────────────────────────────────────────
        room_templates_map = {rt["id"]: rt for rt in template_data.get("room_templates", [])}

        if rooms_data:
            story.append(Spacer(1, 4 * mm))
            # Заголовок раздела
            rooms_hdr = [[Paragraph("Информация по помещениям", styles["section_header"])]]
            rooms_hdr_tbl = Table(rooms_hdr, colWidths=[page_w])
            rooms_hdr_tbl.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, -1), BRAND_LIGHT_PURPLE),
                        ("BOX", (0, 0), (-1, -1), 1, BRAND_PURPLE),
                        ("TOPPADDING", (0, 0), (-1, -1), 8),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                        ("LEFTPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            story.append(rooms_hdr_tbl)
            story.append(Spacer(1, 4 * mm))

            for room_instance in rooms_data:
                rt_id = room_instance.get("room_template_id", "")
                rt = room_templates_map.get(rt_id, {})
                if not rt:
                    # Если шаблон комнаты не найден — показываем просто имя
                    rt = {"name": room_instance.get("room_name", ""), "questions": []}
                room_flowables = _build_room_flowables(room_instance, rt, styles, page_w)
                story.extend(room_flowables)
                story.append(Spacer(1, 4 * mm))

        # ── Статические секции после комнат ─────────────────────────────────
        sections_after = template_data.get("sections_after_rooms", [])
        if sections_after:
            story.append(Spacer(1, 4 * mm))
            for section in sections_after:
                flowables = _build_section_table(section, general_answers, styles, page_w)
                story.extend(flowables)
                story.append(Spacer(1, 4 * mm))

        doc.build(
            story,
            onFirstPage=page_template.on_page,
            onLaterPages=page_template.on_page,
        )

        return buf.getvalue()

    except Exception as e:
        logger.exception(f"Ошибка генерации PDF анкеты: {e}")
        return None
