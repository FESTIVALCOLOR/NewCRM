"""
Роутер нормо-дней (norm-days) — шаблоны подэтапов с нормами.
Подключается в main.py через app.include_router(norm_days_router, prefix="/api/norm-days").
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from database import get_db, Employee, NormDaysTemplate
from auth import get_current_user
from permissions import require_permission
from schemas import NormDaysTemplateRequest, NormDaysPreviewRequest
from services.timeline_service import (
    build_project_timeline_template,
    build_template_project_timeline,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["norm-days"])


@router.get("/templates")
async def get_norm_days_template(
    project_type: str,
    project_subtype: str,
    agent_type: str = 'Все агенты',
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить шаблон нормо-дней. Приоритет: конкретный агент > 'Все агенты' > формулы."""
    # Приоритет: сначала ищем для конкретного агента, потом для "Все агенты"
    custom = None
    effective_agent = agent_type
    if agent_type and agent_type != 'Все агенты':
        custom = db.query(NormDaysTemplate).filter(
            NormDaysTemplate.project_type == project_type,
            NormDaysTemplate.project_subtype == project_subtype,
            NormDaysTemplate.agent_type == agent_type,
        ).order_by(NormDaysTemplate.sort_order).all()

    if not custom:
        # Fallback на "Все агенты"
        effective_agent = 'Все агенты'
        custom = db.query(NormDaysTemplate).filter(
            NormDaysTemplate.project_type == project_type,
            NormDaysTemplate.project_subtype == project_subtype,
            NormDaysTemplate.agent_type.in_(['Все агенты', None]),
        ).order_by(NormDaysTemplate.sort_order).all()

    if custom:
        entries = []
        for c in custom:
            entries.append({
                "stage_code": c.stage_code,
                "stage_name": c.stage_name,
                "stage_group": c.stage_group,
                "substage_group": c.substage_group,
                "base_norm_days": c.base_norm_days,
                "k_multiplier": c.k_multiplier,
                "executor_role": c.executor_role,
                "is_in_contract_scope": c.is_in_contract_scope,
                "sort_order": c.sort_order,
            })
        return {
            "project_type": project_type,
            "project_subtype": project_subtype,
            "agent_type": effective_agent,
            "entries": entries,
            "is_custom": True,
        }

    # Генерируем из формул (area=100 для дефолтных значений)
    if project_type == 'Шаблонный':
        raw_entries, contract_term, K = build_template_project_timeline(project_subtype, 100)
    else:
        raw_entries, contract_term, K = build_project_timeline_template(project_type, 100, project_subtype)
    effective_agent = 'Все агенты'

    entries = []
    for e in raw_entries:
        if e['executor_role'] == 'header':
            continue
        entries.append({
            "stage_code": e['stage_code'],
            "stage_name": e['stage_name'],
            "stage_group": e['stage_group'],
            "substage_group": e.get('substage_group', ''),
            "base_norm_days": e.get('raw_norm_days', 0),
            "k_multiplier": 0,
            "executor_role": e['executor_role'],
            "is_in_contract_scope": e.get('is_in_contract_scope', True),
            "sort_order": e.get('sort_order', 0),
        })
    return {
        "project_type": project_type,
        "project_subtype": project_subtype,
        "agent_type": effective_agent,
        "entries": entries,
        "is_custom": False,
    }


@router.put("/templates")
async def save_norm_days_template(
    request: NormDaysTemplateRequest,
    current_user: Employee = Depends(require_permission("employees.update")),
    db: Session = Depends(get_db)
):
    """Сохранить кастомный шаблон нормо-дней в БД."""
    if not request.entries:
        raise HTTPException(status_code=400, detail="Список entries не может быть пустым")

    try:
        # Удаляем старый шаблон для этого типа/подтипа/агента
        db.query(NormDaysTemplate).filter(
            NormDaysTemplate.project_type == request.project_type,
            NormDaysTemplate.project_subtype == request.project_subtype,
            NormDaysTemplate.agent_type == request.agent_type,
        ).delete()
        db.flush()

        # Создаём новые записи
        for entry in request.entries:
            record = NormDaysTemplate(
                project_type=request.project_type,
                project_subtype=request.project_subtype,
                stage_code=entry.stage_code,
                stage_name=entry.stage_name,
                stage_group=entry.stage_group,
                substage_group=entry.substage_group,
                base_norm_days=entry.base_norm_days,
                k_multiplier=entry.k_multiplier,
                executor_role=entry.executor_role,
                is_in_contract_scope=entry.is_in_contract_scope,
                sort_order=entry.sort_order,
                agent_type=request.agent_type,
                updated_at=datetime.utcnow(),
                updated_by=current_user.id,
            )
            db.add(record)

        db.commit()
        logger.info(f"Шаблон нормо-дней сохранен: {request.project_type}/{request.project_subtype}"
                     f"/{request.agent_type}, {len(request.entries)} записей (user={current_user.id})")
        return {"status": "saved", "count": len(request.entries)}
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка сохранения шаблона нормо-дней: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/templates/preview")
async def preview_norm_days_template(
    request: NormDaysPreviewRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Предпросмотр расчёта нормо-дней для указанной площади.
    Если есть кастомный шаблон — используем base_norm_days + K * k_multiplier,
    иначе генерируем из формул.
    """
    area = request.area
    if area <= 0:
        raise HTTPException(status_code=400, detail="Площадь должна быть положительной")

    try:
        if request.project_type == 'Шаблонный':
            raw_entries, contract_term, K = build_template_project_timeline(
                request.project_subtype, area, agent_type=request.agent_type)
        else:
            raw_entries, contract_term, K = build_project_timeline_template(
                request.project_type, area, request.project_subtype, agent_type=request.agent_type)

        entries = []
        for e in raw_entries:
            entries.append({
                "stage_code": e['stage_code'],
                "stage_name": e['stage_name'],
                "stage_group": e['stage_group'],
                "substage_group": e.get('substage_group', ''),
                "raw_norm_days": e.get('raw_norm_days', 0),
                "norm_days": e.get('norm_days', 0),
                "executor_role": e['executor_role'],
                "is_in_contract_scope": e.get('is_in_contract_scope', True),
                "sort_order": e.get('sort_order', 0),
            })

        return {
            "entries": entries,
            "contract_term": contract_term,
            "k_coefficient": K if isinstance(K, int) else int(K),
        }
    except Exception as e:
        logger.error(f"Ошибка preview нормо-дней: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка расчёта: {str(e)}")


@router.post("/templates/reset")
async def reset_norm_days_template(
    request: Request,
    current_user: Employee = Depends(require_permission("employees.update")),
    db: Session = Depends(get_db)
):
    """Удалить кастомный шаблон нормо-дней (возврат к формулам)."""
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Некорректный JSON")

    project_type = body.get("project_type", "")
    project_subtype = body.get("project_subtype", "")
    agent_type = body.get("agent_type", "Все агенты")

    if not project_type or not project_subtype:
        raise HTTPException(status_code=400, detail="Необходимо указать project_type и project_subtype")

    try:
        deleted = db.query(NormDaysTemplate).filter(
            NormDaysTemplate.project_type == project_type,
            NormDaysTemplate.project_subtype == project_subtype,
            NormDaysTemplate.agent_type == agent_type,
        ).delete()
        db.commit()
        logger.info(f"Шаблон нормо-дней сброшен: {project_type}/{project_subtype}/{agent_type}, "
                     f"удалено {deleted} записей (user={current_user.id})")
        return {"status": "reset", "deleted": deleted}
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка сброса шаблона нормо-дней: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
