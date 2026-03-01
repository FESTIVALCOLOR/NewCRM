"""
Роутер для работы с клиентами.
Все CRUD-операции по модели Client.
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import func, or_
from typing import List, Optional

from database import (
    get_db, Client, ActivityLog, Employee,
    Contract, CRMCard, StageExecutor, Payment,
    SupervisionCard, SupervisionTimelineEntry,
    SupervisionProjectHistory, ProjectFile,
    ProjectTimelineEntry
)
from auth import get_current_user
from permissions import require_permission
from schemas import ClientResponse, ClientCreate, ClientUpdate, StatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["clients"])


@router.get("/", response_model=List[ClientResponse])
async def get_clients(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    search_type: str = "name",
    response: Response = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список клиентов с пагинацией и поиском.
    Заголовок X-Total-Count содержит общее количество записей.
    search — строка поиска, search_type — поле (name/phone/email/inn/all)."""
    query = db.query(Client)

    if search:
        term = f"%{search}%"
        if search_type == "all":
            query = query.filter(
                or_(
                    Client.full_name.ilike(term),
                    Client.organization_name.ilike(term),
                    Client.phone.ilike(term),
                    Client.email.ilike(term),
                    Client.inn.ilike(term),
                )
            )
        elif search_type == "phone":
            query = query.filter(Client.phone.ilike(term))
        elif search_type == "email":
            query = query.filter(Client.email.ilike(term))
        elif search_type == "inn":
            query = query.filter(Client.inn.ilike(term))
        else:
            query = query.filter(
                or_(
                    Client.full_name.ilike(term),
                    Client.organization_name.ilike(term),
                )
            )

    total = query.count()
    clients = query.order_by(Client.id.desc()).offset(skip).limit(limit).all()
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return clients


@router.get("/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить клиента по ID"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")
    return client


@router.post("/", response_model=ClientResponse)
async def create_client(
    client_data: ClientCreate,
    current_user: Employee = Depends(require_permission("clients.create")),
    db: Session = Depends(get_db)
):
    """Создать нового клиента"""
    client = Client(**client_data.model_dump())
    db.add(client)
    db.commit()
    db.refresh(client)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="create",
        entity_type="client",
        entity_id=client.id
    )
    db.add(log)
    db.commit()

    return client


@router.put("/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client_data: ClientUpdate,
    current_user: Employee = Depends(require_permission("clients.update")),
    db: Session = Depends(get_db)
):
    """Обновить клиента"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    # Обновление полей
    for field, value in client_data.model_dump(exclude_unset=True).items():
        setattr(client, field, value)

    client.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(client)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update",
        entity_type="client",
        entity_id=client.id
    )
    db.add(log)
    db.commit()

    return client


@router.delete("/{client_id}", response_model=StatusResponse)
async def delete_client(
    client_id: int,
    current_user: Employee = Depends(require_permission("clients.delete")),
    db: Session = Depends(get_db)
):
    """Удалить клиента и все связанные данные"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    try:
        # Сначала удаляем все связанные договоры (каскадно удалит карточки, платежи и т.д.)
        contracts = db.query(Contract).filter(Contract.client_id == client_id).all()
        for contract in contracts:
            # Удаляем timeline записи
            db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract.id).delete()
            # Удаляем CRM карточки и связанные данные
            crm_cards = db.query(CRMCard).filter(CRMCard.contract_id == contract.id).all()
            for card in crm_cards:
                db.query(StageExecutor).filter(StageExecutor.crm_card_id == card.id).delete()
                db.query(Payment).filter(Payment.crm_card_id == card.id).delete()
                db.delete(card)
            # Удаляем карточки надзора и связанные данные
            supervision_cards = db.query(SupervisionCard).filter(SupervisionCard.contract_id == contract.id).all()
            for card in supervision_cards:
                db.query(SupervisionTimelineEntry).filter(SupervisionTimelineEntry.supervision_card_id == card.id).delete()
                db.query(SupervisionProjectHistory).filter(SupervisionProjectHistory.supervision_card_id == card.id).delete()
                db.query(Payment).filter(Payment.supervision_card_id == card.id).delete()
                db.delete(card)
            # Удаляем оставшиеся платежи
            db.query(Payment).filter(Payment.contract_id == contract.id).delete()
            # Удаляем файлы
            db.query(ProjectFile).filter(ProjectFile.contract_id == contract.id).delete()
            # Удаляем сам договор
            db.delete(contract)

        # Лог перед удалением
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="delete",
            entity_type="client",
            entity_id=client_id
        )
        db.add(log)

        db.delete(client)
        db.commit()

        return {"status": "success", "message": "Клиент и все связанные данные удалены"}

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении клиента {client_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
