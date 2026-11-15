"""
Гостевой просмотр CRM-карточки по секретной ссылке (без входа).

GET /api/v1/public/crm-card/{token}

Отдаёт только рабочие данные для исполнителей: адрес, стадию, сроки, команду, таблицу сроков
и файлы рабочих разделов. Не отдаёт: данные клиента, суммы и оплаты, договор и акты, чаты.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from rate_limit import limiter
from services.project_deadline import compute_project_metrics
from sqlalchemy.orm import Session

from database import Contract, CRMCard, Employee, ProjectFile, ProjectTimelineEntry, StageExecutor, get_db

router = APIRouter(tags=["public-card"])

# Разделы файлов, нужные исполнителям; договор, акты, письма и надзор не показываем
GUEST_FILE_STAGES = {
    "tech_task": "Техническое задание",
    "questionnaire": "Анкета",
    "measurement": "Замер",
    "photo_documentation": "Фотофиксация",
    "references": "Референсы",
    "stage1": "Стадия 1: планировочное решение",
    "stage2_concept": "Стадия 2: концепция / коллажи",
    "stage2_3d": "Стадия 2: 3D визуализация",
    "stage3": "Стадия 3: чертёжный проект",
}

TEAM_ROLES = (
    ("senior_manager", "Старший менеджер проектов"),
    ("sdp", "СДП"),
    ("gap", "ГАП"),
    ("manager", "Менеджер"),
    ("surveyor", "Замерщик"),
)


def _team(db, card):
    team = [{"role": role, "name": getattr(card, attr).full_name} for attr, role in TEAM_ROLES if getattr(card, attr, None)]
    executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card.id).order_by(StageExecutor.id).all()
    names = {e.id: e.full_name for e in db.query(Employee).filter(Employee.id.in_([x.executor_id for x in executors if x.executor_id])).all()} if executors else {}
    latest = {}
    for ex in executors:
        latest[ex.stage_name] = ex
    for stage_name, ex in latest.items():
        if ex.executor_id in names:
            team.append({"role": f"Исполнитель — {stage_name}", "name": names[ex.executor_id], "deadline": str(ex.deadline) if ex.deadline else None, "completed": bool(ex.completed)})
    return team


def _timeline_rows(entries):
    rows = []
    for e in sorted(entries, key=lambda x: x.sort_order or 0):
        if e.executor_role == "header":
            rows.append({"kind": "group", "stage": e.stage_name})
        elif (e.stage_code or "").endswith("_HDR"):
            rows.append({"kind": "sub", "stage": e.stage_name})
        else:
            rows.append(
                {
                    "kind": "row",
                    "stage": e.stage_name,
                    "role": e.executor_role or "",
                    "norm": e.custom_norm_days or e.norm_days or None,
                    "fact": e.actual_days or None,
                    "date": str(e.actual_date) if e.actual_date else None,
                    "skipped": e.status == "skipped",
                    "out_of_scope": e.is_in_contract_scope is False,
                }
            )
    return rows


def _files(db, contract):
    files = (
        db.query(ProjectFile)
        .filter(ProjectFile.contract_id == contract.id, ProjectFile.stage.in_(list(GUEST_FILE_STAGES)), ProjectFile.public_link.isnot(None), ProjectFile.public_link != "")
        .order_by(ProjectFile.stage, ProjectFile.file_order)
        .all()
    )
    groups = {}
    for f in files:
        groups.setdefault(f.stage, []).append({"name": f.file_name, "link": f.public_link, "variation": f.variation})
    folders = {
        "measurement": contract.measurement_image_link,
        "photo_documentation": contract.photo_documentation_yandex_path,
        "references": contract.references_yandex_path,
        "tech_task": contract.tech_task_link,
    }
    result = []
    for stage, title in GUEST_FILE_STAGES.items():
        folder = folders.get(stage)
        folder = folder if folder and str(folder).startswith("http") else None
        if groups.get(stage) or folder:
            result.append({"stage": stage, "title": title, "folder_link": folder, "files": groups.get(stage, [])})
    return result


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
    return {
        "card_id": card.id,
        "contract_number": contract.contract_number,
        "address": contract.address,
        "city": contract.city,
        "area": contract.area,
        "project_type": contract.project_type,
        "project_subtype": getattr(contract, "project_subtype", None),
        "agent_type": contract.agent_type,
        "column_name": card.column_name,
        "metrics": compute_project_metrics(card, contract, entries),
        "team": _team(db, card),
        "timeline": _timeline_rows(entries),
        "files": _files(db, contract),
    }
