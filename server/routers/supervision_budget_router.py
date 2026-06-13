"""
Роутер бюджета надзора: строительные работы и черновые материалы
"""

import json

from auth import get_current_user
from fastapi import APIRouter, Depends, HTTPException
from schemas import BudgetExtraUpdate
from sqlalchemy.orm import Session

from database import Employee, SupervisionBudgetExtra, SupervisionCard, get_db

router = APIRouter(tags=["supervision-budget"])


def _parse_json(text):
    if not text:
        return []
    try:
        return json.loads(text)
    except Exception:
        return []


def _format(record):
    return {
        "id": record.id,
        "supervision_card_id": record.supervision_card_id,
        "construction_planned": record.construction_planned,
        "construction_contractor": record.construction_contractor,
        "construction_notes": record.construction_notes,
        "construction_payments": _parse_json(record.construction_payments),
        "materials_planned": record.materials_planned,
        "materials_supplier": record.materials_supplier,
        "materials_notes": record.materials_notes,
        "materials_payments": _parse_json(record.materials_payments),
    }


_EMPTY = {
    "id": None,
    "construction_planned": None,
    "construction_contractor": None,
    "construction_notes": None,
    "construction_payments": [],
    "materials_planned": None,
    "materials_supplier": None,
    "materials_notes": None,
    "materials_payments": [],
}


@router.get("/{card_id}")
async def get_budget_extra(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    record = db.query(SupervisionBudgetExtra).filter(SupervisionBudgetExtra.supervision_card_id == card_id).first()
    if not record:
        return {**_EMPTY, "supervision_card_id": card_id}
    return _format(record)


@router.put("/{card_id}")
async def update_budget_extra(
    card_id: int,
    data: BudgetExtraUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    card = db.query(SupervisionCard).filter(SupervisionCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка надзора не найдена")

    record = db.query(SupervisionBudgetExtra).filter(SupervisionBudgetExtra.supervision_card_id == card_id).first()
    if not record:
        record = SupervisionBudgetExtra(supervision_card_id=card_id)
        db.add(record)

    if data.construction_planned is not None:
        record.construction_planned = data.construction_planned
    if data.construction_contractor is not None:
        record.construction_contractor = data.construction_contractor
    if data.construction_notes is not None:
        record.construction_notes = data.construction_notes
    if data.construction_payments is not None:
        record.construction_payments = json.dumps(data.construction_payments, ensure_ascii=False)

    if data.materials_planned is not None:
        record.materials_planned = data.materials_planned
    if data.materials_supplier is not None:
        record.materials_supplier = data.materials_supplier
    if data.materials_notes is not None:
        record.materials_notes = data.materials_notes
    if data.materials_payments is not None:
        record.materials_payments = json.dumps(data.materials_payments, ensure_ascii=False)

    db.commit()
    db.refresh(record)
    return _format(record)
