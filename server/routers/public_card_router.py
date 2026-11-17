"""
Гостевой просмотр CRM-карточки по секретной ссылке (без входа).

GET /api/v1/public/crm-card/{token}

Отдаёт только рабочие данные для исполнителей: шапку карточки, сроки, команду, папки и файлы
рабочих разделов, анкету ТЗ без контактов. Не отдаёт: данные клиента, суммы и оплаты,
договор и акты, чаты, ключ анкеты.
"""

import copy

from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limit import limiter
from services.project_deadline import compute_project_metrics
from sqlalchemy.orm import Session

from database import Agent, Contract, CRMCard, Employee, ProjectFile, ProjectTimelineEntry, StageExecutor, TechnicalSurvey, get_db

router = APIRouter(tags=["public-card"])

# Разделы файлов, нужные исполнителям; договор, акты, письма и надзор не показываем
GUEST_FILE_STAGES = ("tech_task", "questionnaire", "measurement", "photo_documentation", "references", "stage1", "stage2_concept", "stage2_3d", "stage3")

TEAM_ROLES = (
    ("senior_manager", "Ст. менеджер"),
    ("sdp", "СДП"),
    ("gap", "ГАП"),
    ("manager", "Менеджер"),
    ("surveyor", "Замерщик"),
)


def _executor_role(stage_name):
    name = (stage_name or "").lower()
    return "Дизайнер" if "концепц" in name or "визуализ" in name else "Чертёжник"


def _team(db, card):
    team = [{"role": role, "name": getattr(card, attr).full_name} for attr, role in TEAM_ROLES if getattr(card, attr, None)]
    executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card.id).order_by(StageExecutor.id).all()
    ids = [x.executor_id for x in executors if x.executor_id]
    names = {e.id: e.full_name for e in db.query(Employee).filter(Employee.id.in_(ids)).all()} if ids else {}
    latest = {}
    for ex in executors:
        latest[ex.stage_name] = ex
    for stage_name, ex in latest.items():
        if ex.executor_id in names:
            team.append({"role": f"{_executor_role(stage_name)} — {stage_name}", "name": names[ex.executor_id]})
    return team


def _http(link):
    return link if link and str(link).startswith("http") else None


def _norm_path(path):
    return (path or "").removeprefix("disk:").strip()


def _files(db, contract):
    # PDF анкеты не показываем — анкета открывается через «Просмотр анкеты»
    survey = db.query(TechnicalSurvey.pdf_yandex_path).filter(TechnicalSurvey.contract_id == contract.id).first()
    survey_pdf = _norm_path(survey.pdf_yandex_path) if survey else ""
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.contract_id == contract.id, ProjectFile.stage.in_(GUEST_FILE_STAGES), ProjectFile.public_link.isnot(None), ProjectFile.public_link != "")
        .order_by(ProjectFile.stage, ProjectFile.file_order)
        .all()
    )
    return [{"stage": f.stage, "name": f.file_name, "link": f.public_link, "variation": f.variation or 1} for f in files if _http(f.public_link) and not _is_survey_pdf(f, survey_pdf)]


def _is_survey_pdf(f, survey_pdf):
    if survey_pdf and _norm_path(f.yandex_path) == survey_pdf:
        return True
    # Прежние версии PDF анкеты, которые CRM сохраняла под именем «анкета-…pdf»
    name = (f.file_name or "").lower()
    return f.stage == "questionnaire" and name.startswith("анкета") and name.endswith(".pdf")


def _collect_contact_ids(node, ids):
    if isinstance(node, dict):
        if node.get("type") == "contacts" and node.get("id"):
            ids.add(node["id"])
        for value in node.values():
            _collect_contact_ids(value, ids)
    elif isinstance(node, list):
        for value in node:
            _collect_contact_ids(value, ids)
    return ids


def _strip_keys(node, keys):
    if isinstance(node, dict):
        return {k: _strip_keys(v, keys) for k, v in node.items() if k not in keys}
    if isinstance(node, list):
        return [_strip_keys(v, keys) for v in node]
    return node


def _survey(db, contract):
    """Анкета ТЗ для просмотра: без ключа доступа и без ответов на вопросы-контакты."""
    from routers.tz_router import _get_agent_logo_url, _get_or_create_template

    survey = db.query(TechnicalSurvey).filter(TechnicalSurvey.contract_id == contract.id).first()
    if not survey or not survey.answers:
        return None
    project_type = contract.project_type or "Индивидуальный"
    template = _get_or_create_template(db, project_type)
    # Личные данные клиента: вопросы-контакты и ФИО заказчика
    contact_ids = _collect_contact_ids(template, {"client_name"})
    return {
        "status": survey.status,
        "template_data": template,
        "answers": _strip_keys(copy.deepcopy(survey.answers), contact_ids),
        "project_type": project_type,
        "contract_number": contract.contract_number or "",
        "agent_logo_url": _get_agent_logo_url(db, contract.agent_type),
    }


def _folders(card, contract):
    return {
        "tech_task": _http(contract.tech_task_link),
        "measurement": _http(contract.measurement_image_link) or _http(contract.measurement_folder_public_link),
        "photo_documentation": _http(contract.photo_folder_public_link) or _http(contract.photo_documentation_yandex_path),
        "references": _http(contract.references_yandex_path),
    }


@router.get("/public/crm-card/{token}")
@limiter.limit("60/minute")
def get_public_crm_card(request: Request, token: str, db: Session = Depends(get_db)):
    if not token or len(token) < 16:
        raise HTTPException(status_code=404, detail="Ссылка недействительна")
    card = db.query(CRMCard).filter(CRMCard.share_token == token).first()
    contract = db.query(Contract).filter(Contract.id == card.contract_id).first() if card else None
    if not card or not contract:
        raise HTTPException(status_code=404, detail="Ссылка недействительна")

    entries = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract.id).all()
    agent = db.query(Agent).filter(Agent.name == contract.agent_type).first() if contract.agent_type else None
    return {
        "card_id": card.id,
        "contract_number": contract.contract_number,
        "address": contract.address,
        "city": contract.city,
        "area": contract.area,
        "project_type": contract.project_type,
        "project_subtype": getattr(contract, "project_subtype", None),
        "contract_period": contract.contract_period,
        "agent_type": contract.agent_type,
        "agent_color": agent.color if agent else None,
        "column_name": card.column_name,
        "tags": card.tags,
        "tech_task_date": str(card.tech_task_date) if card.tech_task_date else None,
        "measurement_date": str(contract.measurement_date) if contract.measurement_date else None,
        "metrics": compute_project_metrics(card, contract, entries),
        "team": _team(db, card),
        "folders": _folders(card, contract),
        "files": _files(db, contract),
        "survey": _survey(db, contract),
    }
