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

from datetime import datetime
import io
import logging
import os
import re
import subprocess
import tempfile

from docx import Document
from docx.shared import Inches
from num2words import num2words
from sqlalchemy.orm import Session
from yandex_disk_service import YandexDiskService

from database import Client, CompanyRequisite, Contract, ContractTemplate, ProjectFile

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
        "db_stage": "act_kd",
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
IMAGE_PLACEHOLDERS = {"{{ПОДПИСЬ}}", "{{ПЕЧАТЬ}}", "{{ПОДПИСЬ_РАСШ}}"}
REQUISITE_TYPE_MAP = {
    "{{ПОДПИСЬ}}": "signature",
    "{{ПЕЧАТЬ}}": "seal",
    "{{ПОДПИСЬ_РАСШ}}": "signature_name",
}


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


def _get_image_bytes(db: Session, placeholder: str, yd_service: YandexDiskService) -> bytes | None:
    """Скачивает байты изображения реквизита с ЯД или возвращает None."""
    req_type = REQUISITE_TYPE_MAP.get(placeholder)
    if not req_type:
        return None
    req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == req_type).first()
    if not req:
        return None
    try:
        return yd_service.download_file_to_bytes(req.file_path)
    except Exception as e:
        logger.warning(f"Не удалось скачать реквизит с ЯД ({req.file_path}): {e}")
        return None


def _replace_text_in_runs(runs, ctx: dict, db: Session, yd_service: YandexDiskService) -> None:
    """Заменяет плейсхолдеры {{КЛЮЧ}} и изображения в runs параграфа.

    Проход 1: каждый run отдельно — сохраняет bold/italic/size.
              Если run целиком содержит плейсхолдер изображения — вставляет картинку.
    Проход 2: кросс-run плейсхолдеры (Word разбил {{КЛЮЧ}} на несколько runs).
    """
    if not runs:
        return

    # Проход 1: замена внутри каждого run
    for r in runs:
        stripped = r.text.strip()
        if stripped in IMAGE_PLACEHOLDERS:
            # Весь run = плейсхолдер картинки
            img_bytes = _get_image_bytes(db, stripped, yd_service)
            r.text = ""
            if img_bytes:
                try:
                    r.add_picture(io.BytesIO(img_bytes), width=Inches(1.5))
                    logger.info(f"Изображение {stripped} вставлено ({len(img_bytes)} байт)")
                except Exception as e:
                    logger.error(f"Ошибка вставки {stripped}: {e}")
            else:
                logger.warning(f"Изображение {stripped} не найдено — плейсхолдер очищен")
        elif "{{" in r.text:
            for key, value in ctx.items():
                r.text = r.text.replace("{{" + key + "}}", value)

    # Проход 2: кросс-run текстовые плейсхолдеры (Word разбил {{КЛЮЧ}} на несколько runs)
    full_text = "".join(r.text for r in runs)
    if "{{" not in full_text:
        return
    replaced = full_text
    for key, value in ctx.items():
        replaced = replaced.replace("{{" + key + "}}", value)
    if replaced == full_text:
        return
    runs[0].text = replaced
    for r in runs[1:]:
        r.text = ""


def _process_table(table, ctx: dict, db: Session, yd_service: YandexDiskService) -> None:
    """Рекурсивно обходит таблицу (включая вложенные таблицы).

    Без seen-dedup: id(cell._tc) ненадёжен (lxml переиспользует адреса памяти),
    ложные дубликаты приводили к пропуску ячеек с плейсхолдерами.
    Повторная обработка безопасна — замены идемпотентны.
    """
    for row in table.rows:
        for cell in row.cells:
            for para in cell.paragraphs:
                _replace_text_in_runs(para.runs, ctx, db, yd_service)
            for nested in cell.tables:
                _process_table(nested, ctx, db, yd_service)


def _fill_docx(doc: Document, ctx: dict, db: Session, yd_service: YandexDiskService) -> None:
    """Заполняет все плейсхолдеры в документе (параграфы + таблицы рекурсивно)."""
    for para in doc.paragraphs:
        _replace_text_in_runs(para.runs, ctx, db, yd_service)
    for table in doc.tables:
        _process_table(table, ctx, db, yd_service)


def _convert_to_pdf(docx_path: str) -> bytes:
    """Конвертирует DOCX в PDF через LibreOffice headless."""
    out_dir = os.path.dirname(docx_path)
    result = subprocess.run(
        [
            "libreoffice",
            "--headless",
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

    template = (
        db.query(ContractTemplate)
        .filter(
            ContractTemplate.project_type == contract.project_type,
            ContractTemplate.doc_type == doc_type,
        )
        .first()
    )
    if not template:
        return {"success": False, "message": f"Шаблон не найден для {contract.project_type} / {doc_type}"}

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
        ctx = _build_context(contract, client, doc_type)
        _fill_docx(doc, ctx, db, yd_service)

        with tempfile.TemporaryDirectory() as tmpdir:
            # Имя файла: «Договор-Фестиваль-Иванов ИА.pdf»
            agent = _agent_short(contract.agent_type)
            client_name = _client_short_name(client.full_name if client else None)
            name_parts = [p for p in [meta["label"], agent, client_name] if p]
            # Убираем символы, запрещённые в именах файлов ЯД
            base_name = re.sub(r'[<>:"/\\|?*]', "", "-".join(name_parts))
            if not base_name:
                base_name = f"{meta['label']}_{contract_id}"

            docx_path = os.path.join(tmpdir, base_name + ".docx")
            doc.save(docx_path)

            pdf_bytes = _convert_to_pdf(docx_path)

            pdf_name = base_name + ".pdf"

            # Путь на ЯД: папка проекта / подпапка (Документы или Документы/Акты)
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
                file_id = existing.id
            else:
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
                file_id = pf.id

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
