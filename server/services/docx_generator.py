"""
Генерация документов (договор, акты) из DOCX-шаблонов.

Алгоритм:
1. Загрузить шаблон DOCX из БД
2. Заполнить плейсхолдеры {{КЛЮЧ}} данными договора
3. Вставить изображения ({{ПОДПИСЬ}}, {{ПЕЧАТЬ}}, {{ПОДПИСЬ_РАСШ}})
4. Конвертировать в PDF через LibreOffice headless
5. Загрузить PDF на Яндекс.Диск
6. Сохранить запись ProjectFile в БД

Плейсхолдеры в шаблоне пишутся в двойных фигурных скобках: {{КЛЮЧ}}
Изображения: вся строка должна содержать ТОЛЬКО плейсхолдер изображения.
"""

import copy
from datetime import datetime
import io
import logging
import os
import re
import subprocess
import tempfile
import threading

from docx import Document
from docx.oxml.ns import qn
from docx.shared import Inches
from lxml import etree
from num2words import num2words
from sqlalchemy.orm import Session
from yandex_disk_service import YandexDiskService

from database import Client, CompanyRequisite, CompositionTemplate, Contract, ContractTemplate, ProjectFile

logger = logging.getLogger(__name__)

# Маппинг doc_type → метаданные документа
# yd_subfolder — подпапка внутри папки проекта на ЯД
# db_stage    — значение ProjectFile.stage (совпадает с ContractDetailPage.vue)
DOC_TYPE_META = {
    "contract": {
        "label": "Договор",
        "yd_subfolder": "Документы",
        "db_stage": "documents",
    },
    "act_pr": {
        "label": "Акт ПР",
        "yd_subfolder": "Документы/Акты",
        "db_stage": "act_pr",
    },
    "act_kd": {
        "label": "Акт КД",
        "yd_subfolder": "Документы/Акты",
        "db_stage": "act_kd",
    },
    "act_info": {
        "label": "Инф. письмо",
        "yd_subfolder": "Документы/Акты",
        "db_stage": "act_info",
    },
    "act_final": {
        "label": "Акт РЧ",
        "yd_subfolder": "Документы/Акты",
        "db_stage": "act_rch",
    },
}

# Сокращения агентов для имени файла
_AGENT_SHORT: dict[str, str] = {
    "ФЕСТИВАЛЬ": "Фестиваль",
    "ПЕТРОВИЧ": "Петрович",
}


def _agent_short(agent_type: str | None) -> str:
    """ФЕСТИВАЛЬ → Фестиваль"""
    if not agent_type:
        return ""
    return _AGENT_SHORT.get(agent_type.strip().upper(), agent_type.strip().capitalize())


def _client_short_name(full_name: str | None) -> str:
    """Иванов Иван Андреевич → Иванов ИА"""
    if not full_name:
        return ""
    parts = full_name.strip().split()
    if not parts:
        return ""
    last = parts[0]
    initials = "".join(p[0].upper() for p in parts[1:] if p)
    return f"{last} {initials}" if initials else last


# Имена плейсхолдеров изображений
IMAGE_PLACEHOLDERS = {"{{ПОДПИСЬ}}", "{{ПЕЧАТЬ}}", "{{ПОДПИСЬ_РАСШ}}", "{{ЛОГО_АГЕНТА}}"}
REQUISITE_TYPE_MAP = {
    "{{ПОДПИСЬ}}": "signature",
    "{{ПЕЧАТЬ}}": "seal",
    "{{ПОДПИСЬ_РАСШ}}": "signature_name",
    "{{ЛОГО_АГЕНТА}}": None,  # динамически — зависит от агента договора
}


def _agent_logo_req_type(agent_type: str | None) -> str | None:
    """Возвращает requisite_type логотипа агента: logo_<agent_type_lower>.
    Динамически — не требует хардкода при добавлении новых агентов.
    """
    if not agent_type or not agent_type.strip():
        return None
    return f"logo_{agent_type.strip().lower()}"


def _amount_in_words(amount: float) -> str:
    """Сумма прописью: «Двести тысяч рублей 00 коп.»"""
    try:
        rubles = int(amount)
        kopecks = round((amount - rubles) * 100)
        # to="cardinal" — количественное числительное, не делит на 100 как to="currency"
        words = num2words(rubles, lang="ru", to="cardinal")
        return f"{words.capitalize()} рублей {kopecks:02d} коп."
    except Exception:
        return ""


def _format_date(date_str: str | None) -> str:
    """Форматирует дату из строки в читаемый вид «01 января 2025 г.»."""
    if not date_str:
        return ""
    months_ru = [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ]
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return f"{dt.day:02d} {months_ru[dt.month - 1]} {dt.year} г."
        except ValueError:
            continue
    return date_str


def _build_context(contract: Contract, client: Client, doc_type: str) -> dict:
    """Собирает словарь замен плейсхолдеров из данных договора и клиента."""
    amount = contract.total_amount or 0.0
    advance = contract.advance_payment or 0.0
    additional = contract.additional_payment or 0.0
    third = contract.third_payment or 0.0
    period = int(contract.contract_period or 0)

    ctx = {
        "НОМЕР_ДОГОВОРА": contract.contract_number or "",
        "ДАТА_ДОГОВОРА": _format_date(contract.contract_date),
        "АДРЕС": contract.address or "",
        "ПЛОЩАДЬ": str(contract.area or ""),
        "СРОК": str(period),
        "СУММА": f"{amount:,.0f}".replace(",", " "),
        "СУММА_ПРОПИСЬЮ": _amount_in_words(amount),
        "ТИП_ПРОЕКТА": contract.project_type or "",
        "ПОДТИП_ПРОЕКТА": contract.project_subtype or "",
        "ТИП_ОРГАНИЗАЦИИ": (client.organization_type or "") if client else "",
        "СЕГОДНЯ": _format_date(datetime.now().strftime("%Y-%m-%d")),
        "АВАНС": f"{advance:,.0f}".replace(",", " "),
        "АВАНС_ПРОПИСЬЮ": _amount_in_words(advance),
        "ДОПЛАТА": f"{additional:,.0f}".replace(",", " "),
        "ДОПЛАТА_ПРОПИСЬЮ": _amount_in_words(additional),
        "ТРЕТИЙ_ПЛАТЕЖ": f"{third:,.0f}".replace(",", " "),
        "ТРЕТИЙ_ПЛАТЕЖ_ПРОПИСЬЮ": _amount_in_words(third),
    }

    # Этапы: стоимость и срок (целое число, округление)
    # Проценты зависят от типа проекта
    if contract.project_type == "Шаблонный":
        _stage_pct = [
            ("ПР", 0.30, 0.24),  # планировочные решения
            ("КД", 0.00, 0.00),  # не используется в шаблонном
            ("РЧ", 0.70, 0.76),  # комплект чертежей
            ("СМ", 0.00, 0.00),  # не используется в шаблонном
        ]
    else:
        # Индивидуальный и Авторский надзор
        _stage_pct = [
            ("ПР", 0.20, 0.16),  # планировочные решения
            ("КД", 0.50, 0.50),  # концепция дизайна
            ("РЧ", 0.25, 0.24),  # комплект чертежей (рабочие чертежи)
            ("СМ", 0.05, 0.10),  # ведомость / смета
        ]
    for code, cost_pct, days_pct in _stage_pct:
        stage_cost = amount * cost_pct
        stage_days = round(period * days_pct)
        ctx[f"ЭТАП_{code}_СТОИМОСТЬ"] = f"{stage_cost:,.0f}".replace(",", " ") if cost_pct else ""
        ctx[f"ЭТАП_{code}_СРОК"] = str(stage_days) if days_pct else ""
    if client:
        ctx.update(
            {
                "КЛИЕНТ": client.full_name or "",
                "ТЕЛЕФОН": client.phone or "",
                "EMAIL": client.email or "",
                "ПАСПОРТ_СЕРИЯ": client.passport_series or "",
                "ПАСПОРТ_НОМЕР": client.passport_number or "",
                "ПАСПОРТ_КЕМ_ВЫДАН": client.passport_issued_by or "",
                "ПАСПОРТ_ДАТА": _format_date(client.passport_issued_date),
                "АДРЕС_РЕГИСТРАЦИИ": client.registration_address or "",
                "ИНН": client.inn or "",
                "ОГРН": client.ogrn or "",
                "ОРГАНИЗАЦИЯ": client.organization_name or "",
                "РЕКВИЗИТЫ": client.account_details or "",
                "ОТВЕТСТВЕННЫЙ": client.responsible_person or "",
            }
        )
    return ctx


def _get_image_bytes(db: Session, placeholder: str, yd_service: YandexDiskService, req_type: str | None = None) -> bytes | None:
    """Скачивает байты изображения реквизита с ЯД или возвращает None."""
    effective_req = req_type or REQUISITE_TYPE_MAP.get(placeholder)
    if not effective_req:
        return None
    req_type = effective_req
    req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == req_type).first()
    if not req:
        return None
    try:
        return yd_service.download_file_to_bytes(req.file_path)
    except Exception as e:
        logger.warning(f"Не удалось скачать реквизит с ЯД ({req.file_path}): {e}")
        return None


_WP = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
_A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"

# Параметры вставки для каждого типа реквизита:
#   width_inches — ширина изображения
#   pos_h_emu    — смещение по горизонтали от позиции символа (EMU; 914400 = 1 дюйм)
#   pos_v_emu    — смещение по вертикали от строки (EMU; отрицательное = вверх)
_IMAGE_FLOAT_PARAMS: dict[str, dict] = {
    "{{ПОДПИСЬ}}": {"width": 1.5, "pos_h": -342900, "pos_v": -160800},  # 0.375" влево, 4мм ниже
    "{{ПОДПИСЬ_РАСШ}}": {"width": 1.5, "pos_h": 1208700, "pos_v": -232800},  # +5мм вправо, -1мм вниз
    "{{ПЕЧАТЬ}}": {"width": 2.2, "pos_h": -457200, "pos_v": -1371600},  # без изменений
    "{{ЛОГО_АГЕНТА}}": {"width": 3.0, "pos_h": 0, "pos_v": 0, "inline": True},  # inline, без floating
}
_IMAGE_FLOAT_DEFAULT = {"width": 1.5, "pos_h": 0, "pos_v": 0}

# Переопределения по типу документа (перекрывают _IMAGE_FLOAT_PARAMS)
_IMAGE_FLOAT_OVERRIDES: dict[str, dict[str, dict]] = {
    "act_info": {
        "{{ПЕЧАТЬ}}": {"width": 2.2, "pos_h": -1463040, "pos_v": -1371600},  # влево на 0.5 ширины
    },
}


def _get_image_params(doc_type: str) -> dict[str, dict]:
    """Возвращает словарь параметров вставки с учётом переопределений для doc_type."""
    params = dict(_IMAGE_FLOAT_PARAMS)
    if doc_type in _IMAGE_FLOAT_OVERRIDES:
        params.update(_IMAGE_FLOAT_OVERRIDES[doc_type])
    return params


def _make_picture_floating(run, pos_h_emu: int = 0, pos_v_emu: int = 0) -> None:
    """Конвертирует inline картинку в run во floating поверх текста (wp:anchor + wrapNone)."""
    r_elem = run._r
    drawing = r_elem.find(qn("w:drawing"))
    if drawing is None:
        return
    inline = drawing.find(qn("wp:inline"))
    if inline is None:
        return

    extent = inline.find(qn("wp:extent"))
    docPr = inline.find(qn("wp:docPr"))
    cNvGFP = inline.find(qn("wp:cNvGraphicFramePr"))
    graphic = inline.find(f"{{{_A_NS}}}graphic")

    cx = extent.get("cx", "1371600") if extent is not None else "1371600"
    cy = extent.get("cy", "571500") if extent is not None else "571500"
    doc_id = docPr.get("id", "1") if docPr is not None else "1"
    doc_name = docPr.get("name", "image") if docPr is not None else "image"

    anchor = etree.Element(
        f"{{{_WP}}}anchor",
        {
            "distT": "0",
            "distB": "0",
            "distL": "114300",
            "distR": "114300",
            "simplePos": "0",
            "relativeHeight": "251659264",
            "behindDoc": "0",
            "locked": "0",
            "layoutInCell": "1",
            "allowOverlap": "1",
        },
    )
    etree.SubElement(anchor, f"{{{_WP}}}simplePos", x="0", y="0")
    posH = etree.SubElement(anchor, f"{{{_WP}}}positionH", relativeFrom="character")
    etree.SubElement(posH, f"{{{_WP}}}posOffset").text = str(pos_h_emu)
    posV = etree.SubElement(anchor, f"{{{_WP}}}positionV", relativeFrom="line")
    etree.SubElement(posV, f"{{{_WP}}}posOffset").text = str(pos_v_emu)
    etree.SubElement(anchor, f"{{{_WP}}}extent", cx=cx, cy=cy)
    etree.SubElement(anchor, f"{{{_WP}}}effectExtent", l="0", t="0", r="0", b="0")
    etree.SubElement(anchor, f"{{{_WP}}}wrapNone")
    etree.SubElement(anchor, f"{{{_WP}}}docPr", id=doc_id, name=doc_name)
    if cNvGFP is not None:
        anchor.append(copy.deepcopy(cNvGFP))
    else:
        etree.SubElement(anchor, f"{{{_WP}}}cNvGraphicFramePr")
    if graphic is not None:
        anchor.append(copy.deepcopy(graphic))

    drawing.remove(inline)
    drawing.append(anchor)


def _split_run_with_images(r, db: Session, yd_service: YandexDiskService, ctx: dict, image_params: dict | None = None) -> None:
    """Разбивает run, содержащий IMAGE_PLACEHOLDER среди текста, вставляет картинки.

    Пример: "{{ПОДПИСЬ}} ( {{ПОДПИСЬ_РАСШ}} )"
    → пустой оригинальный run, затем run{img}, run{" ( "}, run{img}, run{" )"}
    """
    from docx.oxml import OxmlElement
    from docx.text.run import Run as DocxRun

    pattern = "|".join(re.escape(ph) for ph in sorted(IMAGE_PLACEHOLDERS, key=len, reverse=True))
    parts = re.split(f"({pattern})", r.text)
    if len(parts) <= 1:
        return

    r_elem = r._r
    rPr = r_elem.find(qn("w:rPr"))

    # Очищаем оригинальный run
    for t_el in r_elem.findall(qn("w:t")):
        r_elem.remove(t_el)

    insert_after = r_elem

    for part in parts:
        if not part:
            continue

        new_r_elem = OxmlElement("w:r")
        if rPr is not None:
            new_r_elem.append(copy.deepcopy(rPr))

        if part in IMAGE_PLACEHOLDERS:
            _iparams = image_params if image_params is not None else _IMAGE_FLOAT_PARAMS
            params = _iparams.get(part, _IMAGE_FLOAT_DEFAULT)
            img_bytes = _get_image_bytes(db, part, yd_service, params.get("logo_req"))
            if img_bytes:
                insert_after.addnext(new_r_elem)
                insert_after = new_r_elem
                new_run = DocxRun(new_r_elem, r._parent)
                try:
                    new_run.add_picture(io.BytesIO(img_bytes), width=Inches(params["width"]))
                    if not params.get("inline", False):
                        _make_picture_floating(new_run, params["pos_h"], params["pos_v"])
                    logger.info(f"Изображение {part} вставлено (split, {len(img_bytes)} байт)")
                except Exception as exc:
                    logger.error(f"Ошибка вставки {part} (split): {exc}")
        else:
            # Заменяем текстовые плейсхолдеры прямо здесь
            for key, value in ctx.items():
                part = part.replace("{{" + key + "}}", value)
            t_elem = OxmlElement("w:t")
            t_elem.text = part
            if part != part.strip():
                t_elem.set("{http://www.w3.org/XML/1998/namespace}space", "preserve")
            new_r_elem.append(t_elem)
            insert_after.addnext(new_r_elem)
            insert_after = new_r_elem


def _replace_cross_run_images(runs, ctx: dict, db: Session, yd_service: YandexDiskService, image_params: dict | None = None) -> None:
    """Проход 2.5: кросс-run IMAGE_PLACEHOLDERS.

    Word разбивает {{ПОДПИСЬ_РАСШ}} или {{ПЕЧАТЬ}} по нескольким runs.
    Нормализует плейсхолдер в один run и вставляет картинку.
    """
    for placeholder in IMAGE_PLACEHOLDERS:
        texts = [r.text for r in runs]
        full = "".join(texts)
        if placeholder not in full:
            continue
        ph_start = full.index(placeholder)
        ph_end = ph_start + len(placeholder)
        pos = 0
        start_run = end_run = None
        start_off = end_off = 0
        for i, t in enumerate(texts):
            rend = pos + len(t)
            if start_run is None and pos <= ph_start < rend:
                start_run = i
                start_off = ph_start - pos
            if end_run is None and pos < ph_end <= rend:
                end_run = i
                end_off = ph_end - pos
                break
            pos = rend
        if start_run is None or end_run is None or start_run == end_run:
            continue  # Уже обработано в Проходе 1
        runs[start_run].text = texts[start_run][:start_off] + placeholder
        for i in range(start_run + 1, end_run):
            runs[i].text = ""
        runs[end_run].text = texts[end_run][end_off:]
        r = runs[start_run]
        if r.text.strip() == placeholder:
            _iparams = image_params if image_params is not None else _IMAGE_FLOAT_PARAMS
            params = _iparams.get(placeholder, _IMAGE_FLOAT_DEFAULT)
            img_bytes = _get_image_bytes(db, placeholder, yd_service, params.get("logo_req"))
            r.text = ""
            if img_bytes:
                try:
                    r.add_picture(io.BytesIO(img_bytes), width=Inches(params["width"]))
                    if not params.get("inline", False):
                        _make_picture_floating(r, params["pos_h"], params["pos_v"])
                    logger.info(f"Изображение {placeholder} вставлено (cross-run, {len(img_bytes)} байт)")
                except Exception as e:
                    logger.error(f"Ошибка вставки {placeholder} (cross-run): {e}")
            else:
                logger.warning(f"Изображение {placeholder} не найдено (cross-run)")
        elif any(ph in r.text for ph in IMAGE_PLACEHOLDERS):
            _split_run_with_images(r, db, yd_service, ctx, image_params)


def _replace_text_in_runs(runs, ctx: dict, db: Session, yd_service: YandexDiskService, image_params: dict | None = None) -> None:
    """Заменяет плейсхолдеры {{КЛЮЧ}} и изображения в runs параграфа.

    Проход 1: каждый run отдельно — сохраняет bold/italic/size.
              Если run целиком содержит IMAGE_PLACEHOLDER — вставляет картинку (floating).
              Если IMAGE_PLACEHOLDER смешан с текстом — разбивает run (_split_run_with_images).
    Проход 2.5: кросс-run IMAGE_PLACEHOLDERS (_replace_cross_run_images).
    Проход 2: кросс-run текстовые плейсхолдеры (Word разбил {{КЛЮЧ}} на несколько runs).
    """
    if not runs:
        return

    _iparams = image_params if image_params is not None else _IMAGE_FLOAT_PARAMS

    # Проход 1: замена внутри каждого run
    for r in runs:
        stripped = r.text.strip()
        if stripped in IMAGE_PLACEHOLDERS:
            # Весь run = один плейсхолдер картинки
            params = _iparams.get(stripped, _IMAGE_FLOAT_DEFAULT)
            img_bytes = _get_image_bytes(db, stripped, yd_service, params.get("logo_req"))
            r.text = ""
            if img_bytes:
                try:
                    r.add_picture(io.BytesIO(img_bytes), width=Inches(params["width"]))
                    if not params.get("inline", False):
                        _make_picture_floating(r, params["pos_h"], params["pos_v"])
                    logger.info(f"Изображение {stripped} вставлено ({len(img_bytes)} байт)")
                except Exception as e:
                    logger.error(f"Ошибка вставки {stripped}: {e}")
            else:
                logger.warning(f"Изображение {stripped} не найдено — плейсхолдер очищен")
        elif any(ph in r.text for ph in IMAGE_PLACEHOLDERS):
            # IMAGE_PLACEHOLDER смешан с текстом — разбиваем run
            _split_run_with_images(r, db, yd_service, ctx, image_params)
        elif "{{" in r.text:
            for key, value in ctx.items():
                r.text = r.text.replace("{{" + key + "}}", value)

    # Проход 2.5: кросс-run IMAGE_PLACEHOLDERS
    _replace_cross_run_images(runs, ctx, db, yd_service, image_params)

    # Проход 2: кросс-run текстовые плейсхолдеры (Word разбил {{КЛЮЧ}} на несколько runs)
    # Заменяем каждый плейсхолдер точечно — только затронутые runs, сохраняя форматирование.
    for key, value in ctx.items():
        ph = "{{" + key + "}}"
        texts = [r.text for r in runs]
        full = "".join(texts)
        if ph not in full:
            continue
        ph_start = full.index(ph)
        ph_end = ph_start + len(ph)
        # Найти run-ы, на которые попадает плейсхолдер
        pos = 0
        start_run = end_run = None
        start_off = end_off = 0
        for i, t in enumerate(texts):
            rend = pos + len(t)
            if start_run is None and pos <= ph_start < rend:
                start_run = i
                start_off = ph_start - pos
            if end_run is None and pos < ph_end <= rend:
                end_run = i
                end_off = ph_end - pos
                break
            pos = rend
        if start_run is None or end_run is None:
            continue
        if start_run == end_run:
            # Плейсхолдер целиком в одном run — должно было поймано в Проходе 1
            t = texts[start_run]
            runs[start_run].text = t[:start_off] + value + t[end_off:]
        else:
            # Плейсхолдер распределён по runs: prefix в start_run, value туда же,
            # средние runs очищаются, suffix остаётся в end_run
            runs[start_run].text = texts[start_run][:start_off] + value
            for i in range(start_run + 1, end_run):
                runs[i].text = ""
            runs[end_run].text = texts[end_run][end_off:]


def _process_table(table, ctx: dict, db: Session, yd_service: YandexDiskService, image_params: dict | None = None) -> None:
    """Рекурсивно обходит таблицу (включая вложенные таблицы).

    Без seen-dedup: id(cell._tc) ненадёжен (lxml переиспользует адреса памяти),
    ложные дубликаты приводили к пропуску ячеек с плейсхолдерами.
    Повторная обработка безопасна — замены идемпотентны.
    """
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                _replace_text_in_runs(para.runs, ctx, db, yd_service, image_params)
            for nested in cell.tables:
                _process_table(nested, ctx, db, yd_service, image_params)


def _fill_docx(doc: Document, ctx: dict, db: Session, yd_service: YandexDiskService, image_params: dict | None = None) -> None:
    """Заполняет все плейсхолдеры в документе (параграфы + таблицы + колонтитулы)."""
    for para in doc.paragraphs:
        _replace_text_in_runs(para.runs, ctx, db, yd_service, image_params)
    for table in doc.tables:
        _process_table(table, ctx, db, yd_service, image_params)
    # Верхние и нижние колонтитулы (все варианты: default, first_page, even_page)
    for section in doc.sections:
        for hf in (
            section.header,
            section.footer,
            section.first_page_header,
            section.first_page_footer,
            section.even_page_header,
            section.even_page_footer,
        ):
            if hf is None or hf.is_linked_to_previous:
                continue
            for para in hf.paragraphs:
                _replace_text_in_runs(para.runs, ctx, db, yd_service, image_params)
            for table in hf.tables:
                _process_table(table, ctx, db, yd_service, image_params)


_lo_lock = threading.Lock()

_WNS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def _insert_composition_block(doc: Document, comp_doc: Document) -> bool:
    """Находит параграф с {{СОСТАВ_ПРОЕКТА}} и заменяет его блоками из comp_doc.

    Возвращает True если placeholder найден и заменён, False — если не найден.
    Плейсхолдер может быть разбит по нескольким runs — ищем по полному тексту параграфа.
    """
    body = doc.element.body
    target_idx = None
    target_elem = None

    for i, child in enumerate(body):
        if child.tag != f"{{{_WNS}}}p":
            continue
        # Собираем полный текст параграфа из всех runs
        text = "".join(t.text or "" for t in child.iter(f"{{{_WNS}}}t"))
        if "{{СОСТАВ_ПРОЕКТА}}" in text:
            target_idx = i
            target_elem = child
            break

    if target_elem is None:
        logger.warning("Плейсхолдер {{СОСТАВ_ПРОЕКТА}} не найден в шаблоне договора")
        return False

    # Проверяем, есть ли разрыв страницы перед плейсхолдером
    W = f"{{{_WNS}}}"
    has_page_break = False
    pPr = target_elem.find(f"{W}pPr")
    if pPr is not None and pPr.find(f"{W}pageBreakBefore") is not None:
        has_page_break = True
    if not has_page_break:
        for r in target_elem.findall(f"{W}r"):
            for br in r.findall(f"{W}br"):
                if br.get(f"{W}type") == "page":
                    has_page_break = True

    # Собираем элементы из тела comp_doc (всё кроме sectPr — настроек раздела)
    comp_body = comp_doc.element.body
    comp_elements = []
    for child in comp_body:
        if child.tag == f"{W}sectPr":
            continue
        comp_elements.append(copy.deepcopy(child))

    if not comp_elements:
        logger.warning("Шаблон состава пуст — плейсхолдер удалён без замены")
        body.remove(target_elem)
        return True

    # Если плейсхолдер был с новой страницы — добавляем явный разрыв перед составом
    if has_page_break:
        from lxml import etree as _etree

        pb_para = _etree.Element(f"{W}p")
        pb_run = _etree.SubElement(pb_para, f"{W}r")
        pb_br = _etree.SubElement(pb_run, f"{W}br")
        pb_br.set(f"{W}type", "page")
        comp_elements.insert(0, pb_para)

    # Удаляем параграф-плейсхолдер и вставляем на его место блоки состава
    body.remove(target_elem)
    for offset, elem in enumerate(comp_elements):
        body.insert(target_idx + offset, elem)

    logger.info(f"Состав проекта вставлен: {len(comp_elements)} элементов")
    return True


def _convert_to_pdf(docx_path: str) -> bytes:
    """Конвертирует DOCX в PDF через LibreOffice headless.

    Использует глобальный lock и уникальный профиль LO на вызов,
    чтобы параллельные запросы не конфликтовали по ~/.config/libreoffice.
    """
    out_dir = os.path.dirname(docx_path)
    profile_dir = os.path.join(out_dir, "lo_profile")
    os.makedirs(profile_dir, exist_ok=True)
    profile_url = f"file://{profile_dir}"

    with _lo_lock:
        result = subprocess.run(
            [
                "libreoffice",
                "--headless",
                "--norestore",
                f"-env:UserInstallation={profile_url}",
                "--convert-to",
                "pdf",
                "--outdir",
                out_dir,
                docx_path,
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
    if result.returncode != 0:
        raise RuntimeError(f"LibreOffice ошибка: {result.stderr}")
    pdf_path = os.path.splitext(docx_path)[0] + ".pdf"
    if not os.path.exists(pdf_path):
        raise RuntimeError("LibreOffice не создал PDF файл")
    with open(pdf_path, "rb") as f:
        return f.read()


def _apply_composition_block(
    db: Session,
    doc: Document,
    contract,
    client_type: str,
    yd_service,
) -> None:
    comp_tmpl = (
        db.query(CompositionTemplate)
        .filter(
            CompositionTemplate.project_type == contract.project_type,
            CompositionTemplate.project_subtype == contract.project_subtype,
            CompositionTemplate.client_type == client_type,
        )
        .first()
    )
    if not comp_tmpl and client_type == "юр":
        comp_tmpl = (
            db.query(CompositionTemplate)
            .filter(
                CompositionTemplate.project_type == contract.project_type,
                CompositionTemplate.project_subtype == contract.project_subtype,
                CompositionTemplate.client_type == "физ",
            )
            .first()
        )
    if comp_tmpl:
        try:
            comp_bytes = yd_service.download_file_to_bytes(comp_tmpl.file_path)
            comp_doc = Document(io.BytesIO(comp_bytes))
            _insert_composition_block(doc, comp_doc)
        except Exception as e:
            logger.warning(f"Не удалось вставить состав проекта ({comp_tmpl.file_path}): {e}")
    else:
        logger.info(f"Шаблон состава не найден для {contract.project_type} / {contract.project_subtype} — {{{{СОСТАВ_ПРОЕКТА}}}} останется как есть")


def _render_to_pdf(doc: Document, tmpdir: str, meta: dict, contract, contract_id: int, client) -> tuple:
    agent = _agent_short(contract.agent_type)
    client_name = _client_short_name(client.full_name if client else None)
    name_parts = [p for p in [meta["label"], agent, client_name] if p]
    base_name = re.sub(r'[<>:"/\\|?*]', "", "-".join(name_parts))
    if not base_name:
        base_name = f"{meta['label']}_{contract_id}"
    docx_path = os.path.join(tmpdir, base_name + ".docx")
    doc.save(docx_path)
    pdf_bytes = _convert_to_pdf(docx_path)
    return pdf_bytes, base_name + ".pdf"


def _upload_and_persist(
    db: Session,
    yd_service,
    pdf_bytes: bytes,
    pdf_name: str,
    contract,
    contract_id: int,
    meta: dict,
) -> tuple:
    yd_project = (contract.yandex_folder_path or "").lstrip("disk:").rstrip("/")
    if not yd_project:
        yd_project = f"/CRM/Проекты/{contract.contract_number}"
    yd_path = f"{yd_project}/{meta['yd_subfolder']}/{pdf_name}"
    yd_service.upload_file_from_bytes(pdf_bytes, yd_path)
    file_info = yd_service.get_file_info(yd_path)
    public_url = file_info.get("public_url") or file_info.get("href") or ""
    db_stage = meta["db_stage"]
    existing = (
        db.query(ProjectFile)
        .filter(
            ProjectFile.contract_id == contract_id,
            ProjectFile.stage == db_stage,
            ProjectFile.file_name == pdf_name,
        )
        .first()
    )
    if existing:
        existing.public_link = public_url
        existing.yandex_path = yd_path
        existing.upload_date = datetime.utcnow()
        db.flush()
        return existing.id, public_url
    pf = ProjectFile(
        contract_id=contract_id,
        stage=db_stage,
        file_type="pdf",
        public_link=public_url,
        yandex_path=yd_path,
        file_name=pdf_name,
    )
    db.add(pf)
    db.flush()
    return pf.id, public_url


def generate_document(
    db: Session,
    contract_id: int,
    doc_type: str,
    yd_service: YandexDiskService,
) -> dict:
    """
    Генерирует документ из шаблона и загружает на Яндекс.Диск.

    Returns:
        dict с ключами: success, file_id, file_name, public_url, message
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        return {"success": False, "message": "Договор не найден"}

    client = db.query(Client).filter(Client.id == contract.client_id).first()

    # Определяем тип клиента: юр. лицо если явно указано OR у клиента заполнен organization_type
    explicit = getattr(contract, "client_type", None) or "физ"
    if explicit == "юр" or (client and getattr(client, "organization_type", None)):
        client_type = "юр"
    else:
        client_type = "физ"

    template = (
        db.query(ContractTemplate)
        .filter(
            ContractTemplate.project_type == contract.project_type,
            ContractTemplate.doc_type == doc_type,
            ContractTemplate.client_type == client_type,
        )
        .first()
    )
    if not template:
        # Фолбэк: если юр-шаблон не загружен — пробуем физ
        if client_type == "юр":
            template = (
                db.query(ContractTemplate)
                .filter(
                    ContractTemplate.project_type == contract.project_type,
                    ContractTemplate.doc_type == doc_type,
                    ContractTemplate.client_type == "физ",
                )
                .first()
            )
        if not template:
            return {
                "success": False,
                "message": f"Шаблон не найден для {contract.project_type} / {doc_type} / {client_type}",
            }

    meta = DOC_TYPE_META.get(
        doc_type,
        {"label": doc_type, "yd_subfolder": "Документы", "db_stage": doc_type},
    )

    try:
        # Скачиваем шаблон с ЯД во временный файл
        try:
            template_bytes = yd_service.download_file_to_bytes(template.file_path)
        except Exception as e:
            return {"success": False, "message": f"Не удалось скачать шаблон с ЯД: {e}"}

        doc = Document(io.BytesIO(template_bytes))

        # Вставка состава проекта (только для договора, если есть подтип и шаблон состава)
        if doc_type == "contract" and contract.project_subtype:
            _apply_composition_block(db, doc, contract, client_type, yd_service)

        ctx = _build_context(contract, client, doc_type)
        image_params = _get_image_params(doc_type)
        logo_req = _agent_logo_req_type(contract.agent_type)
        if logo_req:
            # Ширина лого = вся текстовая область (page_width - margins), в дюймах
            sec = doc.sections[0] if doc.sections else None
            text_area_w = (
                (sec.page_width - sec.left_margin - sec.right_margin) / 914400 if sec and sec.page_width else 6.3  # fallback: A4 типичная ширина текста
            )
            # Индивидуальный (все типы) и Шаблонный договор — уменьшить в 2 раза
            # Шаблонный акты — полный 0.75
            if contract.project_type == "Шаблонный" and doc_type != "contract":
                logo_scale = 0.75
            else:
                logo_scale = 0.1875
            logo_width = text_area_w * logo_scale
            image_params["{{ЛОГО_АГЕНТА}}"] = {
                **image_params["{{ЛОГО_АГЕНТА}}"],
                "logo_req": logo_req,
                "width": logo_width,
            }
        _fill_docx(doc, ctx, db, yd_service, image_params)

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_bytes, pdf_name = _render_to_pdf(doc, tmpdir, meta, contract, contract_id, client)
            file_id, public_url = _upload_and_persist(db, yd_service, pdf_bytes, pdf_name, contract, contract_id, meta)
            db.commit()
            return {
                "success": True,
                "file_id": file_id,
                "file_name": pdf_name,
                "public_url": public_url,
                "message": f"{meta['label']} сформирован успешно",
            }

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка генерации документа contract={contract_id} doc_type={doc_type}: {e}")
        return {"success": False, "message": f"Ошибка генерации: {e}"}
