"""
Роутер для endpoint'ов синхронизации данных (sync data).
Подключается в main.py через app.include_router(sync_router, prefix="/api/sync").
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from typing import List

from database import (
    get_db, Employee,
    StageExecutor, ApprovalStageDeadline,
    ActionHistory, SupervisionProjectHistory
)
from auth import get_current_user
from schemas import (
    StageExecutorResponse, ApprovalDeadlineResponse,
    ActionHistoryResponse, SupervisionHistoryResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["sync"])


# =========================
# SYNC DATA ENDPOINTS
# =========================

@router.get("/stage-executors", response_model=List[StageExecutorResponse])
async def get_all_stage_executors(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить всех исполнителей стадий для синхронизации"""
    try:
        executors = db.query(StageExecutor).all()

        return [{
            'id': e.id,
            'crm_card_id': e.crm_card_id,
            'stage_name': e.stage_name,
            'executor_id': e.executor_id,
            'assigned_date': e.assigned_date.isoformat() if e.assigned_date else None,
            'assigned_by': e.assigned_by,
            'deadline': e.deadline.isoformat() if e.deadline else (e.deadline if isinstance(e.deadline, str) else None),
            'completed': e.completed,
            'completed_date': e.completed_date.isoformat() if e.completed_date else None,
            'submitted_date': e.submitted_date.isoformat() if e.submitted_date else None
        } for e in executors]

    except Exception as e:
        logger.exception(f"Ошибка синхронизации исполнителей стадий: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/approval-deadlines", response_model=List[ApprovalDeadlineResponse])
async def get_all_approval_deadlines(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все дедлайны согласования для синхронизации"""
    try:
        deadlines = db.query(ApprovalStageDeadline).all()

        return [{
            'id': d.id,
            'crm_card_id': d.crm_card_id,
            'stage_name': d.stage_name,
            'deadline': d.deadline if isinstance(d.deadline, str) else (d.deadline.isoformat() if d.deadline else None),
            'is_completed': d.is_completed,
            'completed_date': d.completed_date.isoformat() if d.completed_date else None,
            'created_at': d.created_at.isoformat() if d.created_at else None
        } for d in deadlines]

    except Exception as e:
        logger.exception(f"Ошибка синхронизации дедлайнов согласования: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/action-history", response_model=List[ActionHistoryResponse])
async def get_all_action_history(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить всю историю действий для синхронизации"""
    try:
        history = db.query(ActionHistory).all()

        return [{
            'id': h.id,
            'user_id': h.user_id,
            'action_type': h.action_type,
            'entity_type': h.entity_type,
            'entity_id': h.entity_id,
            'description': h.description,
            'action_date': h.action_date.isoformat() if h.action_date else None
        } for h in history]

    except Exception as e:
        logger.exception(f"Ошибка синхронизации истории действий: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/supervision-history", response_model=List[SupervisionHistoryResponse])
async def get_all_supervision_history(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить всю историю проектов надзора для синхронизации"""
    try:
        history = db.query(SupervisionProjectHistory).all()

        return [{
            'id': h.id,
            'supervision_card_id': h.supervision_card_id,
            'entry_type': h.entry_type,
            'message': h.message,
            'created_by': h.created_by,
            'created_at': h.created_at.isoformat() if h.created_at else None
        } for h in history]

    except Exception as e:
        logger.exception(f"Ошибка синхронизации истории надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
