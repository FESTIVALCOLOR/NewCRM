"""
Роутер анкет технического задания (ТЗ).

Эндпоинты:
  - GET/PUT /api/v1/tz-templates/{project_type}      — управление шаблоном (только admin)
  - POST    /api/v1/technical-surveys/{contract_id}  — создать/отправить анкету
  - GET     /api/v1/technical-surveys/contract/{id}  — получить анкету по договору
  - GET     /api/v1/technical-surveys/{id}           — получить анкету по id
  - PATCH   /api/v1/technical-surveys/{id}           — редактировать ответы (менеджер)
  - GET     /api/v1/technical-surveys/{id}/pdf       — скачать PDF
  - GET     /api/v1/surveys/fill/{token}             — публичный: получить анкету (клиент)
  - POST    /api/v1/surveys/fill/{token}             — публичный: отправить ответы (клиент)
"""

from datetime import datetime
import logging
import secrets
from typing import Any
from urllib.parse import quote

from auth import get_current_user as get_current_employee
from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from services.tz_initial_template import INITIAL_TEMPLATES
from services.tz_pdf_generator import generate_tz_pdf
from sqlalchemy.orm import Session

from database import (
    Contract,
    CRMCard,
    TechnicalSurvey,
    TZSurveyTemplate,
    get_db,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["technical-surveys"])


# ── Схемы ───────────────────────────────────────────────────────────────────


class TZTemplateUpdate(BaseModel):
    template_data: dict


class SurveyCreateRequest(BaseModel):
    send_link: bool = True


class SurveyAnswersSubmit(BaseModel):
    answers: dict


class SurveyAnswersPatch(BaseModel):
    answers: dict


# ── Вспомогательные ─────────────────────────────────────────────────────────


def _get_or_create_template(db: Session, project_type: str) -> dict:
    """Возвращает шаблон из БД, или начальный шаблон если ещё не сохранялся."""
    tpl = db.query(TZSurveyTemplate).filter(TZSurveyTemplate.project_type == project_type).first()
    if tpl:
        return tpl.template_data
    # Возвращаем начальный шаблон без сохранения в БД (lazy init)
    return INITIAL_TEMPLATES.get(project_type, INITIAL_TEMPLATES.get("Индивидуальный"))


def _get_agent_logo_url(db: Session, agent_type: str | None) -> str | None:
    """Возвращает публичную ссылку на логотип агента с ЯД (или None)."""
    if not agent_type:
        return None
    try:
        from yandex_disk_service import YandexDiskService

        from database import CompanyRequisite

        req_type = f"logo_{agent_type.strip().lower()}"
        req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == req_type).first()
        if not req or not req.file_path:
            return None
        yd = YandexDiskService()
        # Если файл уже опубликован — берём ссылку без блокирующих sleep
        try:
            info = yd.get_file_info(req.file_path)
            if info.get("public_url"):
                return info["public_url"]
        except Exception:
            pass
        return yd.get_public_link(req.file_path)
    except Exception as e:
        logger.warning(f"Не удалось получить лого агента {agent_type}: {e}")
        return None


def _save_pdf_to_yd(db: Session, survey: TechnicalSurvey, contract: Contract, pdf_bytes: bytes) -> None:
    """Сохраняет PDF в подпапку {договор}/Анкета/ на ЯД. Имя: анкета-{адрес}-{дата}.pdf"""
    try:
        from datetime import date as _date

        from yandex_disk_service import YandexDiskService

        folder = (contract.yandex_folder_path or "").removeprefix("disk:").rstrip("/")
        if not folder:
            return
        # Подпапка «Анкета» (с заглавной буквы — папка уже создаётся при создании договора)
        subfolder = f"{folder}/Анкета"
        yd = YandexDiskService()
        try:
            yd.create_folder(subfolder)
        except Exception:
            pass  # Папка может уже существовать
        # Имя файла: анкета-{адрес}-{дата}.pdf
        addr = (contract.address or "").strip()
        addr_slug = "".join(c if c.isalnum() or c in " _-" else "-" for c in addr)[:40].strip("-")
        date_str = _date.today().strftime("%d.%m.%Y")
        pdf_name = f"анкета-{addr_slug}-{date_str}.pdf" if addr_slug else f"анкета-{date_str}.pdf"
        pdf_path = f"{subfolder}/{pdf_name}"
        yd.upload_file_from_bytes(pdf_bytes, pdf_path)
        survey.pdf_yandex_path = f"disk:{pdf_path}"
        db.commit()
        logger.info(f"PDF анкеты сохранён на ЯД: disk:{pdf_path}")
    except Exception as e:
        logger.warning(f"Не удалось сохранить PDF на ЯД: {e}")


def _survey_to_dict(survey: TechnicalSurvey, include_answers: bool = True) -> dict:
    result = {
        "id": survey.id,
        "contract_id": survey.contract_id,
        "access_token": survey.access_token,
        "status": survey.status,
        "pdf_yandex_path": survey.pdf_yandex_path,
        "created_at": survey.created_at.isoformat() if survey.created_at else None,
        "sent_at": survey.sent_at.isoformat() if survey.sent_at else None,
        "completed_at": survey.completed_at.isoformat() if survey.completed_at else None,
        "last_edited_at": survey.last_edited_at.isoformat() if survey.last_edited_at else None,
    }
    if include_answers:
        result["answers"] = survey.answers
    return result


def _get_agent_logo_url(db: Session, agent_type: str | None) -> str | None:
    """Возвращает URL логотипа агента если есть."""
    if not agent_type:
        return None
    from database import CompanyRequisite

    slug = agent_type.strip().lower()
    req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == f"logo_{slug}").first()
    if req and req.file_path:
        return f"/api/v1/surveys/agent-logo/{slug}"
    return None


# ── Шаблоны (только admin/director) ─────────────────────────────────────────


@router.get("/tz-templates/{project_type}")
def get_tz_template(
    project_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Получить шаблон анкеты по типу проекта."""
    template_data = _get_or_create_template(db, project_type)
    return {"project_type": project_type, "template_data": template_data}


@router.put("/tz-templates/{project_type}")
def update_tz_template(
    project_type: str,
    body: TZTemplateUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Обновить шаблон анкеты (только администраторы)."""
    from constants import ADMIN_POSITIONS

    if current_user.position not in ADMIN_POSITIONS and current_user.role not in ("admin", "director"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    tpl = db.query(TZSurveyTemplate).filter(TZSurveyTemplate.project_type == project_type).first()
    if tpl:
        tpl.template_data = body.template_data
        tpl.updated_at = datetime.utcnow()
        tpl.updated_by = current_user.id
    else:
        tpl = TZSurveyTemplate(
            project_type=project_type,
            template_data=body.template_data,
            updated_by=current_user.id,
        )
        db.add(tpl)
    db.commit()
    return {"ok": True, "project_type": project_type}


@router.post("/tz-templates/{project_type}/reset")
def reset_tz_template(
    project_type: str,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Сбросить шаблон до начального."""
    from constants import ADMIN_POSITIONS

    if current_user.position not in ADMIN_POSITIONS and current_user.role not in ("admin", "director"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    initial = INITIAL_TEMPLATES.get(project_type)
    if not initial:
        raise HTTPException(status_code=404, detail="Начальный шаблон для данного типа не найден")

    tpl = db.query(TZSurveyTemplate).filter(TZSurveyTemplate.project_type == project_type).first()
    if tpl:
        tpl.template_data = initial
        tpl.updated_at = datetime.utcnow()
        tpl.updated_by = current_user.id
        db.commit()
    return {"ok": True, "project_type": project_type, "template_data": initial}


# ── Анкеты (сотрудники) ──────────────────────────────────────────────────────


@router.post("/technical-surveys/{contract_id}")
def create_survey(
    contract_id: int,
    body: SurveyCreateRequest,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Создать анкету для договора (если ещё нет) и вернуть ссылку."""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    existing = db.query(TechnicalSurvey).filter(TechnicalSurvey.contract_id == contract_id).first()
    if existing:
        return _survey_to_dict(existing)

    survey = TechnicalSurvey(
        contract_id=contract_id,
        access_token=secrets.token_urlsafe(32),
        status="pending",
        created_by=current_user.id,
    )
    if body.send_link:
        survey.sent_at = datetime.utcnow()
        survey.status = "sent"

    db.add(survey)
    db.commit()
    db.refresh(survey)
    return _survey_to_dict(survey)


@router.get("/technical-surveys/contract/{contract_id}")
def get_survey_by_contract(
    contract_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Получить анкету по id договора."""
    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.contract_id == contract_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена")

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    project_type = contract.project_type if contract else "Индивидуальный"
    template_data = _get_or_create_template(db, project_type)

    result = _survey_to_dict(survey)
    result["template_data"] = template_data
    result["project_type"] = project_type
    result["contract_number"] = contract.contract_number if contract else ""
    result["agent_logo_url"] = _get_agent_logo_url(db, getattr(contract, "agent_type", None))
    return result


@router.get("/technical-surveys/{survey_id}")
def get_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Получить анкету по id."""
    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена")

    contract = db.query(Contract).filter(Contract.id == survey.contract_id).first()
    project_type = contract.project_type if contract else "Индивидуальный"
    template_data = _get_or_create_template(db, project_type)

    result = _survey_to_dict(survey)
    result["template_data"] = template_data
    result["project_type"] = project_type
    result["contract_number"] = contract.contract_number if contract else ""
    result["agent_logo_url"] = _get_agent_logo_url(db, getattr(contract, "agent_type", None))
    return result


@router.patch("/technical-surveys/{survey_id}")
def edit_survey_answers(
    survey_id: int,
    body: SurveyAnswersPatch,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Редактировать ответы менеджером после заполнения клиентом."""
    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена")

    survey.answers = body.answers
    survey.status = "edited"
    survey.last_edited_at = datetime.utcnow()
    survey.last_edited_by = current_user.id
    db.commit()
    db.refresh(survey)
    return _survey_to_dict(survey)


@router.delete("/technical-surveys/{survey_id}")
def delete_survey(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Удалить анкету (только admin)."""
    from constants import ADMIN_POSITIONS

    if current_user.position not in ADMIN_POSITIONS and current_user.role not in ("admin", "director"):
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена")

    db.delete(survey)
    db.commit()
    return {"ok": True}


@router.get("/technical-surveys/{survey_id}/pdf")
def get_survey_pdf(
    survey_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_current_employee),
):
    """Генерировать и скачать PDF анкеты."""
    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.id == survey_id).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена")
    if not survey.answers:
        raise HTTPException(status_code=400, detail="Анкета ещё не заполнена")

    contract = db.query(Contract).filter(Contract.id == survey.contract_id).first()
    project_type = contract.project_type if contract else "Индивидуальный"
    agent_type = contract.agent_type if contract else None
    contract_number = contract.contract_number if contract else ""

    template_data = _get_or_create_template(db, project_type)

    pdf_bytes = generate_tz_pdf(
        template_data=template_data,
        answers=survey.answers,
        contract_number=contract_number,
        project_type=project_type,
        agent_type=agent_type,
        db=db,
    )
    if not pdf_bytes:
        raise HTTPException(status_code=500, detail="Ошибка генерации PDF")

    # Сохраняем на ЯД если ещё не сохранён
    if contract and not survey.pdf_yandex_path:
        _save_pdf_to_yd(db, survey, contract, pdf_bytes)

    # Имя файла при скачивании: анкета-{адрес}-{дата}.pdf
    from datetime import date as _date

    addr = (contract.address if contract else "") or ""
    addr_slug = "".join(c if c.isalnum() or c in " _-" else "-" for c in addr)[:40].strip("-")
    date_str = _date.today().strftime("%d.%m.%Y")
    filename = f"анкета-{addr_slug}-{date_str}.pdf" if addr_slug else f"анкета-{date_str}.pdf"
    encoded = quote(filename.encode("utf-8"))
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=\"anketa.pdf\"; filename*=UTF-8''{encoded}"},
    )


# ── Публичные эндпоинты (клиент заполняет по токену) ─────────────────────────


@router.get("/surveys/agent-logo/{agent_type_slug}")
def get_agent_logo_image(
    agent_type_slug: str,
    db: Session = Depends(get_db),
):
    """Публичный: логотип агента как изображение (для страницы анкеты)."""
    try:
        from yandex_disk_service import YandexDiskService

        from database import CompanyRequisite

        req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == f"logo_{agent_type_slug}").first()
        if not req or not req.file_path:
            raise HTTPException(status_code=404, detail="Логотип не найден")
        yd = YandexDiskService()
        logo_bytes = yd.download_file_to_bytes(req.file_path)
        ext = req.file_path.rsplit(".", 1)[-1].lower() if "." in req.file_path else "png"
        content_type = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg", "svg": "image/svg+xml"}.get(ext, "image/png")
        return Response(
            content=logo_bytes,
            media_type=content_type,
            headers={"Cache-Control": "public, max-age=3600"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Не удалось отдать лого агента {agent_type_slug}: {e}")
        raise HTTPException(status_code=404, detail="Логотип не найден")


@router.get("/surveys/fill/{token}")
def get_survey_for_client(
    token: str,
    db: Session = Depends(get_db),
):
    """
    Публичный: клиент открывает анкету по токену.
    Если анкета уже заполнена (completed/edited) — возвращает readonly=True.
    """
    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.access_token == token).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена или ссылка недействительна")

    contract = db.query(Contract).filter(Contract.id == survey.contract_id).first()
    project_type = contract.project_type if contract else "Индивидуальный"
    contract_number = contract.contract_number if contract else ""
    agent_type = contract.agent_type if contract else None

    template_data = _get_or_create_template(db, project_type)

    # Лого агента — возвращаем URL к прокси-эндпоинту (не YD public link)
    agent_logo_url = None
    if agent_type:
        from database import CompanyRequisite

        slug = agent_type.strip().lower()
        req = db.query(CompanyRequisite).filter(CompanyRequisite.requisite_type == f"logo_{slug}").first()
        if req and req.file_path:
            agent_logo_url = f"/api/v1/surveys/agent-logo/{slug}"

    # После заполнения клиент видит только просмотр
    readonly = survey.status in ("completed", "edited")

    return {
        "survey_id": survey.id,
        "status": survey.status,
        "readonly": readonly,
        "project_type": project_type,
        "contract_number": contract_number,
        "agent_type": agent_type,
        "agent_logo_url": agent_logo_url,
        "template_data": template_data,
        "answers": survey.answers if readonly else None,
    }


@router.post("/surveys/fill/{token}")
def submit_survey_by_client(
    token: str,
    body: SurveyAnswersSubmit,
    db: Session = Depends(get_db),
):
    """
    Публичный: клиент отправляет заполненную анкету.
    После отправки анкета становится read-only для клиента.
    """
    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.access_token == token).first()
    if not survey:
        raise HTTPException(status_code=404, detail="Анкета не найдена или ссылка недействительна")

    # Запрет повторной отправки клиентом
    if survey.status in ("completed", "edited"):
        raise HTTPException(
            status_code=409,
            detail="Анкета уже была заполнена. Обратитесь к менеджеру для внесения изменений.",
        )

    survey.answers = body.answers
    survey.status = "completed"
    survey.completed_at = datetime.utcnow()

    # Автоматически ставим survey_date и tech_task_date в CRM карточке, если ещё не установлены
    crm_card = db.query(CRMCard).filter(CRMCard.contract_id == survey.contract_id).first()
    today = datetime.utcnow().strftime("%Y-%m-%d")
    if crm_card and not crm_card.survey_date:
        crm_card.survey_date = today
    if crm_card and not crm_card.tech_task_date:
        crm_card.tech_task_date = today

    db.commit()

    # Генерируем PDF в фоне (не блокируем ответ)
    try:
        contract = db.query(Contract).filter(Contract.id == survey.contract_id).first()
        project_type = contract.project_type if contract else "Индивидуальный"
        template_data = _get_or_create_template(db, project_type)
        pdf_bytes = generate_tz_pdf(
            template_data=template_data,
            answers=body.answers,
            contract_number=contract.contract_number if contract else "",
            project_type=project_type,
            agent_type=contract.agent_type if contract else None,
            db=db,
        )
        if pdf_bytes and contract:
            _save_pdf_to_yd(db, survey, contract, pdf_bytes)
    except Exception as e:
        logger.error(f"Ошибка генерации PDF после заполнения анкеты: {e}")

    return {"ok": True, "status": "completed", "readonly": True}
