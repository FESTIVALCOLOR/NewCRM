"""
Роутер ежемесячных платежей клиента по авторскому надзору.
prefix="/api/v1/supervision-client-payments"
"""

from datetime import datetime
import logging

from auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import (
    Contract,
    Employee,
    SupervisionCard,
    SupervisionClientPayment,
    SupervisionPaymentNotifSettings,
    get_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["supervision-client-payments"])


def _get_or_create_settings(db: Session, card_id: int) -> SupervisionPaymentNotifSettings:
    s = db.query(SupervisionPaymentNotifSettings).filter_by(supervision_card_id=card_id).first()
    if not s:
        s = SupervisionPaymentNotifSettings(supervision_card_id=card_id, notification_enabled=True, notification_day=1)
        db.add(s)
        db.commit()
        db.refresh(s)
    return s


def _fmt(p: SupervisionClientPayment) -> dict:
    return {
        "id": p.id,
        "supervision_card_id": p.supervision_card_id,
        "contract_id": p.contract_id,
        "amount": p.amount,
        "payment_month": p.payment_month,
        "payment_date": p.payment_date,
        "receipt_path": p.receipt_path,
        "created_at": p.created_at.isoformat() if p.created_at else None,
    }


# --- ВАЖНО: статические пути перед динамическими ---


@router.get("/by-contract/{contract_id}")
async def list_by_contract(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Список платежей по contract_id (для страницы договора)"""
    payments = db.query(SupervisionClientPayment).filter(SupervisionClientPayment.contract_id == contract_id).order_by(SupervisionClientPayment.payment_month.asc()).all()
    return [_fmt(p) for p in payments]


@router.get("/{card_id}/settings")
async def get_settings(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_or_create_settings(db, card_id)
    return {"notification_enabled": s.notification_enabled, "notification_day": s.notification_day}


@router.patch("/{card_id}/settings")
async def update_settings(
    card_id: int,
    body: dict,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_or_create_settings(db, card_id)
    if "notification_enabled" in body:
        s.notification_enabled = bool(body["notification_enabled"])
    if "notification_day" in body:
        day = int(body["notification_day"])
        s.notification_day = max(1, min(28, day))
    db.commit()
    return {"notification_enabled": s.notification_enabled, "notification_day": s.notification_day}


@router.get("/{card_id}")
async def list_payments(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    payments = db.query(SupervisionClientPayment).filter(SupervisionClientPayment.supervision_card_id == card_id).order_by(SupervisionClientPayment.payment_month.asc()).all()
    settings = _get_or_create_settings(db, card_id)
    return {
        "payments": [_fmt(p) for p in payments],
        "settings": {"notification_enabled": settings.notification_enabled, "notification_day": settings.notification_day},
    }


class ClientPaymentCreate(BaseModel):
    supervision_card_id: int
    contract_id: int
    amount: float
    payment_month: str  # YYYY-MM


class ClientPaymentUpdate(BaseModel):
    amount: float | None = None
    payment_month: str | None = None
    payment_date: str | None = None
    receipt_path: str | None = None


@router.post("/")
async def create_payment(
    body: ClientPaymentCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = db.query(SupervisionCard).filter(SupervisionCard.id == body.supervision_card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

    # Устанавливаем день уведомления из первой записи если настройки ещё не менялись
    settings = _get_or_create_settings(db, body.supervision_card_id)
    existing_count = db.query(SupervisionClientPayment).filter_by(supervision_card_id=body.supervision_card_id).count()
    if existing_count == 0 and settings.notification_day == 1:
        # Оставляем 1-е число как дефолт, но можно расширить в будущем
        pass

    p = SupervisionClientPayment(
        supervision_card_id=body.supervision_card_id,
        contract_id=body.contract_id,
        amount=body.amount,
        payment_month=body.payment_month,
        created_at=datetime.utcnow(),
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    logger.info(f"Создан платёж клиента надзора: card={body.supervision_card_id}, month={body.payment_month}, amount={body.amount}")
    return _fmt(p)


@router.patch("/{payment_id}")
async def update_payment(
    payment_id: int,
    body: ClientPaymentUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(SupervisionClientPayment).filter(SupervisionClientPayment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    if body.amount is not None:
        p.amount = body.amount
    if body.payment_month is not None:
        p.payment_month = body.payment_month
    if body.payment_date is not None:
        p.payment_date = body.payment_date or None
    if body.receipt_path is not None:
        p.receipt_path = body.receipt_path or None

    db.commit()
    db.refresh(p)
    return _fmt(p)


@router.delete("/{payment_id}")
async def delete_payment(
    payment_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.query(SupervisionClientPayment).filter(SupervisionClientPayment.id == payment_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    db.delete(p)
    db.commit()
    return {"ok": True}
