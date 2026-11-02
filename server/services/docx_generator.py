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

# Маппинг doc_type → название файла и stage для ProjectFile
DOC_TYPE_META = {
    "contract": {
        "label": "Договор",
        "file_suffix": "Договор",
        "stage": "Договор",
    },
    "act_pr": {
        "label": "Акт планировочных решений",
        "file_suffix": "Акт_ПР",
        "stage": "Акт ПР",
    },
    "act_kd": {
        "label": "Акт концепции дизайна",
        "file_suffix": "Акт_КД",
        "stage": "Акт КД",
    },
    "act_info": {
        "label": "Информационное письмо о готовности",
        "file_suffix": "Инф_письмо",
        "stage": "Акт КД",
    },
    "act_final": {
        "label": "Акт финальной стадии",
        "file_suffix": "Акт_финал",
        "stage": "Акт РЧ",
    },
}

# Имена плейсхолдеров изображений
IMAGE_PLACEHOLDERS = {"{{ПОДПИСЬ}}", "{{ПЕЧАТЬ}}", "{{ПОДПИСЬ_РАСШ}}"}
REQUISITE_TYPE_MAP = {
    "{{ПОДПИСЬ}}": "signature",
    "{{ПЕЧАТЬ}}": "seal",
    "{{ПОДПИСЬ_РАСШ}}": "signature_name",
}


def _amount_in_words(amount: float) -> str:
    """Сумма прописью на русском (рубли)."""
    try:
        rubles = int(amount)
        kopecks = round((amount - rubles) * 100)
        words = num2words(rubles, lang="ru", to="currency").capitalize()
        if kopecks:
            return f"{words} {kopecks:02d} коп."
        return words
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
    ctx = {
        "НОМЕР_ДОГОВОРА": contract.contract_number or "",
        "ДАТА_ДОГОВОРА": _format_date(contract.contract_date),
        "АДРЕС": contract.address or "",
        "ПЛОЩАДЬ": str(contract.area or ""),
        "СРОК": str(contract.contract_period or ""),
        "СУММА": f"{amount:,.2f}".replace(",", " "),
        "СУММА_ПРОПИСЬЮ": _amount_in_words(amount),
        "ТИП_ПРОЕКТА": contract.project_type or "",
        "ПОДТИП_ПРОЕКТА": contract.project_subtype or "",
        "СЕГОДНЯ": _format_date(datetime.now().strftime("%Y-%m-%d")),
        "АВАНС": f"{contract.advance_payment or 0:,.2f}".replace(",", " "),
        "ДОПЛАТА": f"{contract.additional_payment or 0:,.2f}".replace(",", " "),
        "ТРЕТИЙ_ПЛАТЕЖ": f"{contract.third_payment or 0:,.2f}".replace(",", " "),
    }
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


def _replace_text_in_runs(runs, ctx: dict) -> None:
    """Заменяет плейсхолдеры {{КЛЮЧ}} в runs параграфа."""
    full_text = "".join(r.text for r in runs)
    replaced = full_text
    for key, value in ctx.items():
        replaced = replaced.replace("{{" + key + "}}", value)
    if replaced == full_text:
        return
    # Записываем результат в первый run, очищаем остальные
    if runs:
        runs[0].text = replaced
        for r in runs[1:]:
            r.text = ""


def _get_image_bytes(db: Session, placeholder: str) -> bytes | None:
    """Возвращает байты изображения реквизита или None."""
    req_type = REQUISITE_TYPE_MAP.get(placeholder)
    if not req_type:
        return None
    req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == req_type).first()
    if not req:
        return None
    path = os.path.join("uploads", "requisites", req.file_path)
    if not os.path.exists(path):
        logger.warning(f"Файл реквизита не найден: {path}")
        return None
    with open(path, "rb") as f:
        return f.read()


def _paragraph_is_image_placeholder(para) -> str | None:
    """Если весь параграф — плейсхолдер изображения, вернуть его имя."""
    text = "".join(r.text for r in para.runs).strip()
    if text in IMAGE_PLACEHOLDERS:
        return text
    return None


def _replace_image_in_paragraph(doc: Document, para, db: Session, placeholder: str) -> None:
    """Заменяет параграф-плейсхолдер изображением из реквизитов."""
    img_bytes = _get_image_bytes(db, placeholder)
    if not img_bytes:
        # Если изображение не найдено — просто очищаем плейсхолдер
        for r in para.runs:
            r.text = ""
        return

    # Очищаем все runs параграфа
    for r in para.runs:
        r.text = ""

    # Вставляем изображение в первый run (или создаём новый)
    run = para.runs[0] if para.runs else para.add_run()
    stream = io.BytesIO(img_bytes)
    run.add_picture(stream, width=Inches(1.5))


def _fill_docx(doc: Document, ctx: dict, db: Session) -> None:
    """Заполняет все плейсхолдеры в документе (параграфы + таблицы)."""
    for para in doc.paragraphs:
        img_ph = _paragraph_is_image_placeholder(para)
        if img_ph:
            _replace_image_in_paragraph(doc, para, db, img_ph)
        else:
            _replace_text_in_runs(para.runs, ctx)

    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    img_ph = _paragraph_is_image_placeholder(para)
                    if img_ph:
                        _replace_image_in_paragraph(doc, para, db, img_ph)
                    else:
                        _replace_text_in_runs(para.runs, ctx)


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

    template_path = os.path.join("uploads", "contract_templates", template.file_path)
    if not os.path.exists(template_path):
        return {"success": False, "message": "Файл шаблона не найден на диске"}

    meta = DOC_TYPE_META.get(doc_type, {"label": doc_type, "file_suffix": doc_type, "stage": doc_type})

    try:
        doc = Document(template_path)
        ctx = _build_context(contract, client, doc_type)
        _fill_docx(doc, ctx, db)

        with tempfile.TemporaryDirectory() as tmpdir:
            safe_num = re.sub(r"[^\w\-]", "_", contract.contract_number or str(contract_id))
            base_name = f"{meta['file_suffix']}_{safe_num}"
            docx_path = os.path.join(tmpdir, base_name + ".docx")
            doc.save(docx_path)

            pdf_bytes = _convert_to_pdf(docx_path)

            pdf_name = base_name + ".pdf"
            yd_folder = (contract.yandex_folder_path or "").lstrip("disk:")
            if not yd_folder:
                yd_folder = f"/CRM/Проекты/{contract.contract_number}"
            yd_path = f"{yd_folder}/{pdf_name}"

            yd_service.upload_file_from_bytes(pdf_bytes, yd_path)

            file_info = yd_service.get_file_info(yd_path)
            public_url = file_info.get("public_url") or file_info.get("href") or ""

            existing = (
                db.query(ProjectFile)
                .filter(
                    ProjectFile.contract_id == contract_id,
                    ProjectFile.stage == meta["stage"],
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
                    stage=meta["stage"],
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
