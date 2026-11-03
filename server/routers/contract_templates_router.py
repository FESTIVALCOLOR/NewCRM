"""
Роутер для управления шаблонами договоров и реквизитами компании.

Файлы хранятся на Яндекс.Диске:
  Реквизиты : disk:/CRM/Системные/Реквизиты/{type}.{ext}
  Шаблоны   : disk:/CRM/Системные/Шаблоны/{project_type}_{doc_type}.docx

Endpoints:
  GET    /api/v1/contract-templates/requisites                — список реквизитов
  POST   /api/v1/contract-templates/requisites/{type}         — загрузить реквизит (image)
  DELETE /api/v1/contract-templates/requisites/{type}         — удалить реквизит

  GET    /api/v1/contract-templates/templates                 — все шаблоны
  POST   /api/v1/contract-templates/templates/{project_type}/{doc_type}  — загрузить шаблон
  DELETE /api/v1/contract-templates/templates/{project_type}/{doc_type}  — удалить шаблон

  POST   /api/v1/contract-templates/generate                  — сгенерировать документ
"""

from datetime import datetime

from auth import get_current_user as get_current_active_user
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from permissions import check_permission
from schemas import (
    CompanyRequisiteResponse,
    ContractTemplateResponse,
    GenerateContractRequest,
    GenerateContractResponse,
)
from services.docx_generator import generate_document
from sqlalchemy.orm import Session
from yandex_disk_service import YandexDiskService

from database import CompanyRequisite, ContractTemplate, Employee, get_db

router = APIRouter(prefix="/api/v1/contract-templates", tags=["contract-templates"])

ALLOWED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
ALLOWED_DOC_TYPES = {
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/msword",
    "application/octet-stream",
}
VALID_REQUISITE_TYPES = {"signature", "signature_name", "seal"}
# Логотипы агентов — динамические типы вида logo_<agent_name>


def _is_valid_requisite_type(req_type: str) -> bool:
    return req_type in VALID_REQUISITE_TYPES or req_type.startswith("logo_")


VALID_PROJECT_TYPES = {"Индивидуальный", "Шаблонный", "Авторский надзор"}
VALID_DOC_TYPES = {"contract", "act_pr", "act_kd", "act_info", "act_final"}

# Папки на ЯД (без «disk:» префикса — YandexDiskService принимает без него)
YD_REQUISITES_FOLDER = "/CRM/Системные/Реквизиты"
YD_TEMPLATES_FOLDER = "/CRM/Системные/Шаблоны"


def _require_admin(current_user: Employee = Depends(get_current_active_user)):
    if current_user.role not in ("admin", "director") and current_user.position not in (
        "Руководитель студии",
        "Старший менеджер проектов",
    ):
        raise HTTPException(status_code=403, detail="Доступ запрещён")
    return current_user


# ─── Реквизиты ───────────────────────────────────────────────────────────────


@router.get("/requisites", response_model=list[CompanyRequisiteResponse])
def get_requisites(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_active_user),
):
    return db.query(CompanyRequisite).all()


@router.post("/requisites/{requisite_type}", response_model=CompanyRequisiteResponse)
async def upload_requisite(
    requisite_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(_require_admin),
):
    if not _is_valid_requisite_type(requisite_type):
        raise HTTPException(status_code=400, detail=f"Неверный тип реквизита: {requisite_type}")
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=400, detail="Разрешены только изображения (JPEG/PNG/WebP)")

    import os

    ext = os.path.splitext(file.filename or "")[1] or ".png"
    yd_path = f"{YD_REQUISITES_FOLDER}/{requisite_type}{ext}"

    content = await file.read()
    yd = YandexDiskService()
    try:
        yd.upload_file_from_bytes(content, yd_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки на ЯД: {e}")

    existing = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == requisite_type).first()
    if existing:
        existing.file_name = file.filename or f"{requisite_type}{ext}"
        existing.file_path = yd_path
        existing.updated_at = datetime.utcnow()
        existing.updated_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    req = CompanyRequisite(
        requisite_type=requisite_type,
        file_name=file.filename or f"{requisite_type}{ext}",
        file_path=yd_path,
        updated_by=current_user.id,
    )
    db.add(req)
    db.commit()
    db.refresh(req)
    return req


@router.delete("/requisites/{requisite_type}", status_code=204)
def delete_requisite(
    requisite_type: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(_require_admin),
):
    req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == requisite_type).first()
    if not req:
        raise HTTPException(status_code=404, detail="Реквизит не найден")
    yd = YandexDiskService()
    try:
        yd.delete_file(req.file_path)
    except Exception:
        pass  # файл мог быть удалён вручную, не блокируем удаление записи
    db.delete(req)
    db.commit()


# ─── Шаблоны договоров ───────────────────────────────────────────────────────


@router.get("/templates", response_model=list[ContractTemplateResponse])
def get_templates(
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_active_user),
):
    return db.query(ContractTemplate).all()


@router.post("/templates/{project_type}/{doc_type}", response_model=ContractTemplateResponse)
async def upload_template(
    project_type: str,
    doc_type: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Employee = Depends(_require_admin),
):
    if project_type not in VALID_PROJECT_TYPES:
        raise HTTPException(status_code=400, detail=f"Неверный тип проекта: {project_type}")
    if doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Неверный тип документа: {doc_type}")

    import os

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in (".docx", ".dotx", ".doc"):
        raise HTTPException(status_code=400, detail="Разрешены только DOCX/DOC/DOTX файлы")

    safe_type = project_type.replace(" ", "_")
    file_name = f"{safe_type}_{doc_type}{ext}"
    yd_path = f"{YD_TEMPLATES_FOLDER}/{file_name}"

    content = await file.read()
    yd = YandexDiskService()
    try:
        yd.upload_file_from_bytes(content, yd_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка загрузки на ЯД: {e}")

    existing = (
        db.query(ContractTemplate)
        .filter(
            ContractTemplate.project_type == project_type,
            ContractTemplate.doc_type == doc_type,
        )
        .first()
    )
    if existing:
        existing.file_name = file.filename or file_name
        existing.file_path = yd_path
        existing.uploaded_at = datetime.utcnow()
        existing.uploaded_by = current_user.id
        db.commit()
        db.refresh(existing)
        return existing

    tmpl = ContractTemplate(
        project_type=project_type,
        doc_type=doc_type,
        file_name=file.filename or file_name,
        file_path=yd_path,
        uploaded_by=current_user.id,
    )
    db.add(tmpl)
    db.commit()
    db.refresh(tmpl)
    return tmpl


@router.delete("/templates/{project_type}/{doc_type}", status_code=204)
def delete_template(
    project_type: str,
    doc_type: str,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(_require_admin),
):
    tmpl = (
        db.query(ContractTemplate)
        .filter(
            ContractTemplate.project_type == project_type,
            ContractTemplate.doc_type == doc_type,
        )
        .first()
    )
    if not tmpl:
        raise HTTPException(status_code=404, detail="Шаблон не найден")
    yd = YandexDiskService()
    try:
        yd.delete_file(tmpl.file_path)
    except Exception:
        pass
    db.delete(tmpl)
    db.commit()


# ─── Генерация ────────────────────────────────────────────────────────────────


@router.post("/generate", response_model=GenerateContractResponse)
def generate(
    request: GenerateContractRequest,
    db: Session = Depends(get_db),
    current_user: Employee = Depends(get_current_active_user),
):
    if request.doc_type not in VALID_DOC_TYPES:
        raise HTTPException(status_code=400, detail=f"Неверный тип документа: {request.doc_type}")
    # Проверка прав: договор vs акты
    if request.doc_type == "contract":
        required_perm = "contracts.generate_contract"
    else:
        required_perm = "contracts.generate_acts"
    if not check_permission(current_user, required_perm, db):
        raise HTTPException(status_code=403, detail="Недостаточно прав для формирования документа")
    yd_service = YandexDiskService()
    result = generate_document(db, request.contract_id, request.doc_type, yd_service)
    return GenerateContractResponse(**result)
