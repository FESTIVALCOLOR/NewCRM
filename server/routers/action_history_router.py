"""
Роутер истории действий (action-history).
Подключается в main.py через app.include_router(action_history_router, prefix="/api/action-history").
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db, Employee, ActionHistory
from auth import get_current_user
from schemas import ActionHistoryCreate, ActionHistoryResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["action-history"])


# --- ВАЖНО: Статический GET / ПЕРЕД динамическим GET /{entity_type}/{entity_id} ---

@router.get("/", response_model=List[ActionHistoryResponse])
async def get_all_action_history(
    entity_type: Optional[str] = None,
    user_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 100,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить всю историю действий"""
    query = db.query(ActionHistory)
    if entity_type:
        query = query.filter(ActionHistory.entity_type == entity_type)
    if user_id:
        query = query.filter(ActionHistory.user_id == user_id)
    return query.order_by(ActionHistory.action_date.desc()).offset(skip).limit(limit).all()


@router.get("/{entity_type}/{entity_id}")
async def get_action_history(
    entity_type: str,
    entity_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю действий по сущности"""
    history = db.query(ActionHistory).filter(
        ActionHistory.entity_type == entity_type,
        ActionHistory.entity_id == entity_id
    ).order_by(ActionHistory.action_date.desc()).all()

    # Добавляем user_name к каждой записи
    result = []
    for item in history:
        employee = db.query(Employee).filter(Employee.id == item.user_id).first()
        result.append({
            'id': item.id,
            'user_id': item.user_id,
            'user_name': employee.full_name if employee else 'Неизвестно',
            'action_type': item.action_type,
            'entity_type': item.entity_type,
            'entity_id': item.entity_id,
            'description': item.description,
            'old_value': item.old_value,
            'new_value': item.new_value,
            'action_date': item.action_date.strftime('%Y-%m-%d %H:%M:%S') if item.action_date else None
        })
    return result


@router.post("/", response_model=ActionHistoryResponse)
async def create_action_history(
    history_data: ActionHistoryCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать запись в истории действий"""
    history = ActionHistory(
        user_id=current_user.id,
        **history_data.model_dump()
    )
    db.add(history)
    db.commit()
    db.refresh(history)
    return history
