"""
Роутер для тарифов (rates).
CRUD + расширенные операции (шаблонные, индивидуальные, надзор, замерщик).
ВАЖНО: статические пути (template, individual, supervision, surveyor) ПЕРЕД /{rate_id}.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db, Employee, Rate, Payment, Contract
from auth import get_current_user
from permissions import require_permission
from schemas import (
    RateCreate, RateUpdate, RateResponse,
    TemplateRateRequest, IndividualRateRequest,
    SupervisionRateRequest, SurveyorRateRequest,
    StatusResponse, DeleteCountResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["rates"])


def _recalc_zero_supervision_payments(db: Session, role: str, stage_name: str, rate_per_m2: float):
    """Пересчитать нулевые платежи надзора после создания/обновления тарифа."""
    zero_payments = db.query(Payment).filter(
        Payment.role == role,
        Payment.stage_name == stage_name,
        Payment.supervision_card_id.isnot(None),
        Payment.final_amount == 0,
    ).all()
    if not zero_payments:
        return 0
    count = 0
    for p in zero_payments:
        contract = db.query(Contract).filter(Contract.id == p.contract_id).first()
        area = float(contract.area) if contract and contract.area else 0
        if area > 0 and rate_per_m2 > 0:
            new_amount = area * rate_per_m2
            p.calculated_amount = new_amount
            p.final_amount = new_amount
            p.updated_at = datetime.utcnow()
            count += 1
            logger.info(f"Пересчитан платёж id={p.id}: 0 → {new_amount} (area={area}, rate={rate_per_m2})")
    return count


# --- Основные CRUD ---

@router.get("/", response_model=List[RateResponse])
async def get_rates(
    project_type: Optional[str] = None,
    role: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить тарифы"""
    query = db.query(Rate)
    if project_type:
        query = query.filter(Rate.project_type == project_type)
    if role:
        query = query.filter(Rate.role == role)
    return query.all()


# ВАЖНО: статические пути ПЕРЕД /{rate_id}

@router.get("/template", response_model=List[RateResponse])
async def get_template_rates_early(
    role: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить шаблонные тарифы"""
    query = db.query(Rate).filter(Rate.project_type == 'Шаблонный')
    if role:
        query = query.filter(Rate.role == role)
    return query.all()


@router.post("/template", response_model=RateResponse)
async def save_template_rate(
    data: TemplateRateRequest,
    current_user: Employee = Depends(require_permission("rates.create")),
    db: Session = Depends(get_db)
):
    """Сохранить шаблонный тариф"""
    try:
        existing = db.query(Rate).filter(
            Rate.project_type == 'Шаблонный',
            Rate.role == data.role,
            Rate.area_from == data.area_from,
            Rate.area_to == data.area_to
        ).first()

        if existing:
            existing.fixed_price = data.price
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                project_type='Шаблонный',
                role=data.role,
                area_from=data.area_from,
                area_to=data.area_to,
                fixed_price=data.price
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сохранении шаблонного тарифа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/individual", response_model=RateResponse)
async def save_individual_rate(
    data: IndividualRateRequest,
    current_user: Employee = Depends(require_permission("rates.create")),
    db: Session = Depends(get_db)
):
    """Сохранить индивидуальный тариф"""
    try:
        query = db.query(Rate).filter(
            Rate.project_type == 'Индивидуальный',
            Rate.role == data.role
        )
        if data.stage_name:
            query = query.filter(Rate.stage_name == data.stage_name)
        else:
            query = query.filter(Rate.stage_name.is_(None))

        existing = query.first()

        if existing:
            existing.rate_per_m2 = data.rate_per_m2
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                project_type='Индивидуальный',
                role=data.role,
                rate_per_m2=data.rate_per_m2,
                stage_name=data.stage_name
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сохранении индивидуального тарифа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/individual", response_model=DeleteCountResponse)
async def delete_individual_rate(
    role: str,
    stage_name: Optional[str] = None,
    current_user: Employee = Depends(require_permission("rates.delete")),
    db: Session = Depends(get_db)
):
    """Удалить индивидуальный тариф"""
    try:
        query = db.query(Rate).filter(
            Rate.project_type == 'Индивидуальный',
            Rate.role == role
        )
        if stage_name:
            query = query.filter(Rate.stage_name == stage_name)

        deleted = query.delete()
        db.commit()

        return {"status": "success", "deleted_count": deleted}

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении индивидуального тарифа: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/supervision")
async def save_supervision_rate(
    data: SupervisionRateRequest,
    current_user: Employee = Depends(require_permission("rates.create")),
    db: Session = Depends(get_db)
):
    """Сохранить тариф надзора"""
    try:
        results = []

        # Тариф для ДАН (исполнитель)
        if data.executor_rate is not None:
            existing_dan = db.query(Rate).filter(
                Rate.project_type == 'Авторский надзор',
                Rate.role == 'ДАН',
                Rate.stage_name == data.stage_name
            ).first()

            if existing_dan:
                existing_dan.rate_per_m2 = data.executor_rate
                existing_dan.updated_at = datetime.utcnow()
            else:
                rate_dan = Rate(
                    project_type='Авторский надзор',
                    role='ДАН',
                    stage_name=data.stage_name,
                    rate_per_m2=data.executor_rate
                )
                db.add(rate_dan)
            results.append({'role': 'ДАН', 'rate': data.executor_rate})

        # Тариф для Старшего менеджера
        if data.manager_rate is not None:
            existing_manager = db.query(Rate).filter(
                Rate.project_type == 'Авторский надзор',
                Rate.role == 'Старший менеджер проектов',
                Rate.stage_name == data.stage_name
            ).first()

            if existing_manager:
                existing_manager.rate_per_m2 = data.manager_rate
                existing_manager.updated_at = datetime.utcnow()
            else:
                rate_manager = Rate(
                    project_type='Авторский надзор',
                    role='Старший менеджер проектов',
                    stage_name=data.stage_name,
                    rate_per_m2=data.manager_rate
                )
                db.add(rate_manager)
            results.append({'role': 'Старший менеджер проектов', 'rate': data.manager_rate})

        db.commit()

        # Пересчитать нулевые платежи для обновлённых тарифов
        recalc_count = 0
        if data.executor_rate is not None:
            recalc_count += _recalc_zero_supervision_payments(
                db, 'ДАН', data.stage_name, data.executor_rate)
        if data.manager_rate is not None:
            recalc_count += _recalc_zero_supervision_payments(
                db, 'Старший менеджер проектов', data.stage_name, data.manager_rate)
        if recalc_count > 0:
            db.commit()
            logger.info(f"Пересчитано {recalc_count} нулевых платежей после обновления тарифа")

        return {'status': 'success', 'stage_name': data.stage_name, 'rates': results}

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сохранении тарифа надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/surveyor", response_model=RateResponse)
async def save_surveyor_rate(
    data: SurveyorRateRequest,
    current_user: Employee = Depends(require_permission("rates.create")),
    db: Session = Depends(get_db)
):
    """Сохранить тариф замерщика"""
    try:
        existing = db.query(Rate).filter(
            Rate.role == 'Замерщик',
            Rate.city == data.city
        ).first()

        if existing:
            existing.surveyor_price = data.price
            existing.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(existing)
            return existing
        else:
            rate = Rate(
                role='Замерщик',
                city=data.city,
                surveyor_price=data.price
            )
            db.add(rate)
            db.commit()
            db.refresh(rate)
            return rate

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сохранении тарифа замерщика: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# --- Динамические пути ПОСЛЕ статических ---

@router.get("/{rate_id}", response_model=RateResponse)
async def get_rate(
    rate_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить тариф по ID"""
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Тариф не найден")
    return rate


@router.post("/", response_model=RateResponse)
async def create_rate(
    rate_data: RateCreate,
    current_user: Employee = Depends(require_permission("rates.create")),
    db: Session = Depends(get_db)
):
    """Создать тариф"""
    try:
        rate = Rate(**rate_data.model_dump())
        db.add(rate)
        db.commit()
        db.refresh(rate)
        return rate
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании тарифа: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при создании тарифа: {str(e)}")


@router.put("/{rate_id}", response_model=RateResponse)
async def update_rate(
    rate_id: int,
    rate_data: RateUpdate,
    current_user: Employee = Depends(require_permission("rates.create")),
    db: Session = Depends(get_db)
):
    """Обновить тариф"""
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Тариф не найден")

    for field, value in rate_data.model_dump(exclude_unset=True).items():
        setattr(rate, field, value)

    rate.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rate)

    return rate


@router.delete("/{rate_id}", response_model=StatusResponse)
async def delete_rate(
    rate_id: int,
    current_user: Employee = Depends(require_permission("rates.delete")),
    db: Session = Depends(get_db)
):
    """Удалить тариф"""
    rate = db.query(Rate).filter(Rate.id == rate_id).first()
    if not rate:
        raise HTTPException(status_code=404, detail="Тариф не найден")

    db.delete(rate)
    db.commit()

    return {"status": "success", "message": "Тариф удален"}
