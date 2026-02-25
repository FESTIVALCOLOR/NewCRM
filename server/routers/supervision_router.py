"""
Роутер авторского надзора (supervision).
Подключается в main.py через app.include_router(supervision_router, prefix="/api/supervision").
"""
import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import (
    get_db, Employee, Contract, ActivityLog,
    SupervisionCard, SupervisionProjectHistory, StageExecutor,
    Payment, SupervisionTimelineEntry,
)
from auth import get_current_user
from permissions import require_permission
from schemas import (
    SupervisionCardCreate, SupervisionCardUpdate, SupervisionCardResponse,
    SupervisionColumnMoveRequest, SupervisionPauseRequest,
    SupervisionHistoryCreate, SupervisionHistoryResponse,
)
from services.notification_service import trigger_supervision_notification

# Маппинг column_name → stage_code для таблицы сроков надзора
_SUPERVISION_COLUMN_TO_STAGE = {
    'Стадия 1: Закупка керамогранита': 'STAGE_1_CERAMIC',
    'Стадия 2: Закупка сантехники': 'STAGE_2_PLUMBING',
    'Стадия 3: Закупка оборудования': 'STAGE_3_EQUIPMENT',
    'Стадия 4: Закупка дверей и окон': 'STAGE_4_DOORS',
    'Стадия 5: Закупка настенных материалов': 'STAGE_5_WALL',
    'Стадия 6: Закупка напольных материалов': 'STAGE_6_FLOOR',
    'Стадия 7: Лепной декор': 'STAGE_7_STUCCO',
    'Стадия 8: Освещение': 'STAGE_8_LIGHTING',
    'Стадия 9: Бытовая техника': 'STAGE_9_APPLIANCES',
    'Стадия 10: Закупка заказной мебели': 'STAGE_10_CUSTOM_FURNITURE',
    'Стадия 11: Закупка фабричной мебели': 'STAGE_11_FACTORY_FURNITURE',
    'Стадия 12: Закупка декора': 'STAGE_12_DECOR',
}

logger = logging.getLogger(__name__)


def _count_business_days(start_date, end_date):
    """Подсчёт рабочих дней между двумя датами (пн-пт)"""
    days = 0
    current = start_date
    while current < end_date:
        if current.weekday() < 5:  # пн=0, пт=4
            days += 1
        current += timedelta(days=1)
    return days


router = APIRouter(tags=["supervision"])


# --- ВАЖНО: Статические пути ПЕРЕД динамическими ---

@router.get("/cards")
async def get_supervision_cards(
    status: str = "active",
    skip: int = 0,
    limit: int = 200,
    address: Optional[str] = None,
    city: Optional[str] = None,
    agent_type: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список карточек авторского надзора с фильтрацией"""
    try:
        base_query = db.query(SupervisionCard).join(
            Contract, SupervisionCard.contract_id == Contract.id
        )

        if status == "active":
            base_query = base_query.filter(Contract.status == 'АВТОРСКИЙ НАДЗОР')
        else:
            base_query = base_query.filter(Contract.status.in_(['СДАН', 'РАСТОРГНУТ']))

        # Серверная фильтрация
        if address:
            base_query = base_query.filter(Contract.address.ilike(f"%{address}%"))
        if city:
            base_query = base_query.filter(Contract.city == city)
        if agent_type:
            base_query = base_query.filter(Contract.agent_type == agent_type)
        if date_from:
            base_query = base_query.filter(Contract.contract_date >= date_from)
        if date_to:
            base_query = base_query.filter(Contract.contract_date <= date_to)

        cards = base_query.order_by(SupervisionCard.id.desc()).offset(skip).limit(limit).all()

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
                'total_pause_days': card.total_pause_days or 0,
                'senior_manager_name': senior_manager_name,
                'dan_name': dan_name,
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'contract_status': contract.status,
                'termination_reason': contract.termination_reason if status == "archived" else None,
                # S-14: Добавлено status_changed_date для фильтрации в архиве
                'status_changed_date': contract.status_changed_date.isoformat() if hasattr(contract, 'status_changed_date') and contract.status_changed_date else None,
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
            'total_pause_days': card.total_pause_days or 0,
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
            "total_pause_days": card.total_pause_days or 0,
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
            'total_pause_days': card.total_pause_days or 0,
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
            'Стадия 7: Лепной декор', 'Стадия 8: Освещение',
            'Стадия 9: Бытовая техника', 'Стадия 10: Закупка заказной мебели',
            'Стадия 11: Закупка фабричной мебели', 'Стадия 12: Закупка декора',
            'Выполненный проект'
        ]
        if move_request.column_name not in VALID_SUPERVISION_COLUMNS:
            raise HTTPException(status_code=422, detail=f"Недопустимая колонка надзора: {move_request.column_name}")

        card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

        old_column = card.column_name
        new_column = move_request.column_name

        # С4: Блокируем перемещение приостановленной карточки
        # Исключение: выход из "В ожидании" разрешён (это и есть возобновление)
        if card.is_paused and new_column != old_column and old_column != 'В ожидании':
            raise HTTPException(
                status_code=422,
                detail='Карточка приостановлена. Сначала возобновите проект.'
            )

        # === ПРАВИЛО: Нельзя вернуться в "Новый заказ" ===
        if new_column == 'Новый заказ' and old_column != 'Новый заказ':
            raise HTTPException(
                status_code=422,
                detail='Нельзя вернуть карточку в "Новый заказ". Используйте столбец "В ожидании".'
            )

        # === ПРАВИЛО: Из "В ожидании" — только в previous_column или "Выполненный проект" ===
        if old_column == 'В ожидании' and new_column != 'В ожидании':
            allowed_return = card.previous_column or 'Новый заказ'
            if allowed_return != 'Новый заказ' and new_column not in [allowed_return, 'Выполненный проект']:
                raise HTTPException(
                    status_code=422,
                    detail=f'Из "В ожидании" можно вернуть только в "{allowed_return}" или "Выполненный проект".'
                )

        # === ПРАВИЛО: При переходе в "В ожидании" — сохраняем previous_column ===
        if new_column == 'В ожидании' and old_column != 'В ожидании':
            card.previous_column = old_column

        # === ПРАВИЛО: При возврате из "В ожидании" — автоматически возобновляем ===
        if old_column == 'В ожидании' and new_column != 'В ожидании':
            # Авто-resume: снимаем is_paused и пересчитываем дедлайны
            if card.is_paused:
                pause_days = 0
                if card.paused_at:
                    pause_days = _count_business_days(card.paused_at, datetime.utcnow())
                card.is_paused = False
                card.pause_reason = None
                card.paused_at = None
                card.total_pause_days = (card.total_pause_days or 0) + pause_days
                # Сдвигаем plan_dates в timeline на дни паузы
                if pause_days > 0:
                    timeline_entries = db.query(SupervisionTimelineEntry).filter(
                        SupervisionTimelineEntry.supervision_card_id == card_id,
                        SupervisionTimelineEntry.actual_date.is_(None)
                    ).all()
                    for te in timeline_entries:
                        if te.plan_date:
                            try:
                                plan_dt = datetime.strptime(te.plan_date, '%Y-%m-%d')
                                plan_dt += timedelta(days=pause_days)
                                te.plan_date = plan_dt.strftime('%Y-%m-%d')
                            except (ValueError, TypeError):
                                pass
                    logger.info(f"Supervision card {card_id} auto-resumed from 'В ожидании', pause_days={pause_days}")

                # Сдвигаем deadline карточки
                if card.deadline:
                    try:
                        dl = datetime.strptime(card.deadline, '%Y-%m-%d')
                        dl += timedelta(days=pause_days)
                        card.deadline = dl.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass

            card.previous_column = None

        card.column_name = new_column

        # K11: Запись перемещения в историю
        if old_column != new_column:
            history = SupervisionProjectHistory(
                supervision_card_id=card_id,
                entry_type="card_moved",
                message=f'Карточка перемещена: "{old_column}" → "{new_column}"',
                created_by=current_user.id
            )
            db.add(history)

        # === Установка actual_date в timeline при УХОДЕ из стадии ===
        if old_column != new_column and old_column not in ['Новый заказ', 'В ожидании', 'Выполненный проект']:
            stage_code = _SUPERVISION_COLUMN_TO_STAGE.get(old_column)
            if stage_code:
                timeline_entry = db.query(SupervisionTimelineEntry).filter(
                    SupervisionTimelineEntry.supervision_card_id == card_id,
                    SupervisionTimelineEntry.stage_code == stage_code
                ).first()
                if timeline_entry and not timeline_entry.actual_date:
                    today_str = datetime.utcnow().strftime('%Y-%m-%d')
                    timeline_entry.actual_date = today_str
                    timeline_entry.status = 'Закуплено'
                    # Рассчитываем дней (план → факт)
                    if timeline_entry.plan_date:
                        try:
                            plan_dt = datetime.strptime(timeline_entry.plan_date, '%Y-%m-%d')
                            actual_dt = datetime.strptime(today_str, '%Y-%m-%d')
                            timeline_entry.actual_days = max(0, (actual_dt - plan_dt).days)
                        except (ValueError, TypeError):
                            pass
                    logger.info(f"Timeline actual_date: card={card_id}, stage={stage_code}, date={today_str}")

        db.commit()
        db.refresh(card)

        # Хук: уведомление в чат надзора при перемещении
        if old_column != new_column:
            asyncio.create_task(trigger_supervision_notification(
                db, card_id, 'supervision_move', stage_name=new_column
            ))

        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'old_column_name': old_column,
            'previous_column': card.previous_column,
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

        # С5: Проверка — уже приостановлена?
        if card.is_paused:
            raise HTTPException(status_code=422, detail="Карточка уже приостановлена")

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

        # С5: Проверка — не приостановлена?
        if not card.is_paused:
            raise HTTPException(status_code=422, detail="Карточка не приостановлена")

        # K2: Считаем дни паузы и сдвигаем plan_dates в timeline
        pause_days = 0
        if card.paused_at:
            pause_days = _count_business_days(card.paused_at, datetime.utcnow())

        card.is_paused = False
        card.pause_reason = None
        card.paused_at = None
        card.total_pause_days = (card.total_pause_days or 0) + pause_days

        # K2: Сдвигаем все plan_date в timeline на pause_days
        if pause_days > 0:
            timeline_entries = db.query(SupervisionTimelineEntry).filter(
                SupervisionTimelineEntry.supervision_card_id == card_id,
                SupervisionTimelineEntry.actual_date.is_(None)
            ).all()
            for te in timeline_entries:
                if te.plan_date:
                    try:
                        plan_dt = datetime.strptime(te.plan_date, '%Y-%m-%d')
                        plan_dt += timedelta(days=pause_days)
                        te.plan_date = plan_dt.strftime('%Y-%m-%d')
                    except (ValueError, TypeError):
                        pass
            logger.info(f"K2: Supervision card {card_id} resumed, pause_days={pause_days}, shifted {len(timeline_entries)} entries")

        # Сдвигаем deadline карточки
        if pause_days > 0 and card.deadline:
            try:
                dl = datetime.strptime(card.deadline, '%Y-%m-%d')
                dl += timedelta(days=pause_days)
                card.deadline = dl.strftime('%Y-%m-%d')
            except (ValueError, TypeError):
                pass

        # Добавляем запись в историю
        history = SupervisionProjectHistory(
            supervision_card_id=card_id,
            entry_type="resume",
            message=f"Возобновлено (пауза: {pause_days} дн.)" if pause_days > 0 else "Возобновлено",
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

        # Удаляем записи timeline
        db.query(SupervisionTimelineEntry).filter(
            SupervisionTimelineEntry.supervision_card_id == supervision_card_id
        ).delete()

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
