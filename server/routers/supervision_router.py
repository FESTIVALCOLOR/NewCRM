"""
Роутер авторского надзора (supervision).
Подключается в main.py через app.include_router(supervision_router, prefix="/api/supervision").
"""
import asyncio
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import (
    get_db, Employee, Contract, ActivityLog,
    SupervisionCard, SupervisionProjectHistory, StageExecutor,
    Payment,
)
from auth import get_current_user
from permissions import require_permission
from schemas import (
    SupervisionCardCreate, SupervisionCardUpdate, SupervisionCardResponse,
    SupervisionColumnMoveRequest, SupervisionPauseRequest,
    SupervisionHistoryCreate, SupervisionHistoryResponse,
)
from services.notification_service import trigger_supervision_notification

logger = logging.getLogger(__name__)
router = APIRouter(tags=["supervision"])


# --- ВАЖНО: Статические пути ПЕРЕД динамическими ---

@router.get("/cards")
async def get_supervision_cards(
    status: str = "active",
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список карточек авторского надзора"""
    try:
        if status == "active":
            cards = db.query(SupervisionCard).join(
                Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Contract.status == 'АВТОРСКИЙ НАДЗОР'
            ).order_by(
                SupervisionCard.id.desc()
            ).all()
        else:
            cards = db.query(SupervisionCard).join(
                Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Contract.status.in_(['СДАН', 'РАСТОРГНУТ'])
            ).order_by(
                SupervisionCard.id.desc()
            ).all()

        result = []
        for card in cards:
            contract = card.contract
            senior_manager_name = card.senior_manager.full_name if card.senior_manager else None
            dan_name = card.dan.full_name if card.dan else None

            card_data = {
                'id': card.id,
                'contract_id': card.contract_id,
                'column_name': card.column_name,
                'deadline': str(card.deadline) if card.deadline else None,
                'tags': card.tags,
                'senior_manager_id': card.senior_manager_id,
                'dan_id': card.dan_id,
                'dan_completed': card.dan_completed,
                'is_paused': card.is_paused,
                'pause_reason': card.pause_reason,
                'paused_at': card.paused_at.isoformat() if card.paused_at else None,
                'senior_manager_name': senior_manager_name,
                'dan_name': dan_name,
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'contract_status': contract.status,
                'termination_reason': contract.termination_reason if status == "archived" else None,
                'created_at': card.created_at.isoformat() if card.created_at else None,
                'updated_at': card.updated_at.isoformat() if card.updated_at else None,
            }
            result.append(card_data)

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении карточек надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/addresses")
async def get_supervision_addresses(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить адреса надзора"""
    try:
        result = db.query(Contract.address).join(
            SupervisionCard, SupervisionCard.contract_id == Contract.id
        ).distinct().filter(
            Contract.address != None,
            Contract.address != ''
        ).all()
        return [r[0] for r in result if r[0]]
    except Exception as e:
        logger.exception(f"Ошибка при получении адресов надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}")
async def get_supervision_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить одну карточку надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'senior_manager_id': card.senior_manager_id,
            'dan_id': card.dan_id,
            'dan_completed': card.dan_completed,
            'is_paused': card.is_paused,
            'pause_reason': card.pause_reason,
            'paused_at': card.paused_at.isoformat() if card.paused_at else None,
            'created_at': card.created_at.isoformat() if card.created_at else None,
            'updated_at': card.updated_at.isoformat() if card.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при получении карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards")
async def create_supervision_card(
    card_data: SupervisionCardCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать карточку надзора"""
    try:
        card = SupervisionCard(**card_data.model_dump())
        db.add(card)
        db.commit()
        db.refresh(card)

        log = ActivityLog(
            employee_id=current_user.id,
            action_type="create",
            entity_type="supervision_card",
            entity_id=card.id
        )
        db.add(log)
        db.commit()

        return {
            "id": card.id,
            "contract_id": card.contract_id,
            "column_name": card.column_name,
            "deadline": str(card.deadline) if card.deadline else None,
            "tags": card.tags,
            "senior_manager_id": card.senior_manager_id,
            "dan_id": card.dan_id,
            "dan_completed": card.dan_completed,
            "is_paused": card.is_paused,
            "pause_reason": card.pause_reason,
            "paused_at": card.paused_at.isoformat() if card.paused_at else None,
            "created_at": card.created_at.isoformat() if card.created_at else None,
        }

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}")
async def update_supervision_card(
    card_id: int,
    updates: SupervisionCardUpdate,
    current_user: Employee = Depends(require_permission("supervision.update")),
    db: Session = Depends(get_db)
):
    """Обновить карточку надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        update_data = updates.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(card, field, value)

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'senior_manager_id': card.senior_manager_id,
            'dan_id': card.dan_id,
            'dan_completed': card.dan_completed,
            'is_paused': card.is_paused,
            'pause_reason': card.pause_reason,
            'paused_at': card.paused_at.isoformat() if card.paused_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/column")
async def move_supervision_card_to_column(
    card_id: int,
    move_request: SupervisionColumnMoveRequest,
    current_user: Employee = Depends(require_permission("supervision.move")),
    db: Session = Depends(get_db)
):
    """Переместить карточку надзора в другую колонку"""
    try:
        VALID_SUPERVISION_COLUMNS = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники',
            'Стадия 3: Закупка оборудования', 'Стадия 4: Закупка дверей и окон',
            'Стадия 5: Закупка настенных материалов', 'Стадия 6: Закупка напольных материалов',
            'Стадия 7: Лепного декора', 'Стадия 8: Освещения',
            'Стадия 9: бытовой техники', 'Стадия 10: Закупка заказной мебели',
            'Стадия 11: Закупка фабричной мебели', 'Стадия 12: Закупка декора',
            'Выполненный проект'
        ]
        if move_request.column_name not in VALID_SUPERVISION_COLUMNS:
            raise HTTPException(status_code=422, detail=f"Недопустимая колонка надзора: {move_request.column_name}")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        old_column = card.column_name
        card.column_name = move_request.column_name

        db.commit()
        db.refresh(card)

        # Хук: уведомление в чат надзора при перемещении
        if old_column != move_request.column_name:
            asyncio.create_task(trigger_supervision_notification(
                db, card_id, 'supervision_move', stage_name=move_request.column_name
            ))

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'old_column_name': old_column,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при перемещении карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/pause")
async def pause_supervision_card(
    card_id: int,
    pause_request: SupervisionPauseRequest,
    current_user: Employee = Depends(require_permission("supervision.pause_resume")),
    db: Session = Depends(get_db)
):
    """Приостановить карточку надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.is_paused = True
        card.pause_reason = pause_request.pause_reason
        card.paused_at = datetime.utcnow()

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="pause",
            message=f"Приостановлено: {pause_request.pause_reason}",
            created_by=current_user.id
        )
        db.add(history)

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'is_paused': card.is_paused,
            'pause_reason': card.pause_reason,
            'paused_at': card.paused_at.isoformat(),
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при приостановке карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/resume")
async def resume_supervision_card(
    card_id: int,
    current_user: Employee = Depends(require_permission("supervision.pause_resume")),
    db: Session = Depends(get_db)
):
    """Возобновить карточку надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.is_paused = False
        card.pause_reason = None
        card.paused_at = None

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="resume",
            message="Возобновлено",
            created_by=current_user.id
        )
        db.add(history)

        db.commit()
        db.refresh(card)

        return {
            'id': card.id,
            'is_paused': card.is_paused,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при возобновлении карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/history", response_model=List[SupervisionHistoryResponse])
async def get_supervision_card_history(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю карточки надзора"""
    try:
        history = db.query(SupervisionProjectHistory).filter(
            SupervisionProjectHistory.supervision_card_id == card_id
        ).order_by(SupervisionProjectHistory.created_at.desc()).all()

        return history

    except Exception as e:
        logger.exception(f"Ошибка при получении истории карточки надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/reset-stages")
async def reset_supervision_card_stages(
    card_id: int,
    current_user: Employee = Depends(require_permission("supervision.reset_stages")),
    db: Session = Depends(get_db)
):
    """Сбросить выполнение стадий надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        # Сбрасываем dan_completed
        card.dan_completed = False

        db.commit()

        return {"status": "success", "message": "Стадии надзора сброшены", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе стадий надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/complete-stage")
async def complete_supervision_stage(
    card_id: int,
    current_user: Employee = Depends(require_permission("supervision.complete_stage")),
    db: Session = Depends(get_db)
):
    """Завершить стадию надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        card.dan_completed = True

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="stage_completed",
            message="Стадия завершена",
            created_by=current_user.id
        )
        db.add(history)

        db.commit()

        return {"status": "success", "message": "Стадия завершена", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при завершении стадии надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/history")
async def add_supervision_history(
    card_id: int,
    data: SupervisionHistoryCreate,  # ИСПРАВЛЕНИЕ 06.02.2026: Принимаем body вместо query (#22)
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Добавить запись в историю надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type=data.entry_type,
            message=data.message,
            created_by=data.created_by or current_user.id
        )
        db.add(history)
        db.commit()
        db.refresh(history)

        return {
            'id': history.id,
            'supervision_card_id': history.supervision_card_id,
            'entry_type': history.entry_type,
            'message': history.message,
            'created_at': history.created_at.isoformat() if history.created_at else None,
            'created_by': history.created_by
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при добавлении истории надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/contract")
async def get_contract_id_by_supervision_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить ID договора по ID карточки надзора"""
    card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка надзора не найдена")
    return {"contract_id": card.contract_id}


@router.delete("/orders/{supervision_card_id}")
async def delete_supervision_order(
    supervision_card_id: int,
    contract_id: int,
    current_user: Employee = Depends(require_permission("supervision.delete_order")),
    db: Session = Depends(get_db)
):
    """Удалить заказ надзора"""
    try:
        card = db.query(SupervisionCard).filter(SupervisionCard.id == supervision_card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        # Удаляем историю
        db.query(SupervisionProjectHistory).filter(
            SupervisionProjectHistory.supervision_card_id == supervision_card_id
        ).delete()

        # Удаляем связанные платежи
        db.query(Payment).filter(Payment.supervision_card_id == supervision_card_id).delete()

        # Удаляем карточку
        db.delete(card)
        db.commit()

        return {"status": "success", "message": "Заказ надзора удален"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении заказа надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
