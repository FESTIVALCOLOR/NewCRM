"""
Роутер для endpoint'ов договоров (contracts).
Подключается в main.py через app.include_router(contracts_router, prefix="/api/contracts").
"""
import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Response
from sqlalchemy.orm import Session
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from typing import List, Optional

from database import (
    get_db, Contract, CRMCard, SupervisionCard, ProjectFile,
    ActivityLog, Employee, StageExecutor,
    Client, Payment, ProjectTimelineEntry,
    SupervisionTimelineEntry, SupervisionProjectHistory
)
from auth import get_current_user
from permissions import require_permission
from schemas import ContractResponse, ContractCreate, ContractUpdate, ContractFilesUpdate, StatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["contracts"])


# =========================
# ДОГОВОРЫ
# =========================

@router.get("/", response_model=List[ContractResponse])
async def get_contracts(
    skip: int = 0,
    limit: int = 100,
    response: Response = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список договоров с пагинацией.
    Заголовок X-Total-Count содержит общее количество записей."""
    # Считаем общее количество записей для пагинации
    total = db.query(func.count(Contract.id)).scalar()
    contracts = db.query(Contract).offset(skip).limit(limit).all()
    # Устанавливаем заголовок с общим количеством записей
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return contracts


@router.get("/count")
async def get_contracts_count(
    status: Optional[str] = None,
    project_type: Optional[str] = None,
    year: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить количество договоров с фильтрацией (без загрузки всех записей)"""
    query = db.query(func.count(Contract.id))
    if status:
        query = query.filter(Contract.status == status)
    if project_type:
        query = query.filter(Contract.project_type == project_type)
    if year:
        from sqlalchemy import extract
        query = query.filter(extract('year', Contract.contract_date) == year)
    count = query.scalar()
    return {"count": count}


@router.get("/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить договор по ID"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    return contract


@router.post("/", response_model=ContractResponse)
async def create_contract(
    contract_data: ContractCreate,
    current_user: Employee = Depends(require_permission("contracts.create")),
    db: Session = Depends(get_db)
):
    """Создать новый договор"""
    # Проверяем существование клиента
    client = db.query(Client).filter(Client.id == contract_data.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    try:
        contract = Contract(**contract_data.model_dump())
        db.add(contract)
        db.flush()  # Получаем ID без коммита — единая транзакция

        # Автоматически создаём CRM карточку для нового договора
        # (кроме Авторского надзора — для него создаётся SupervisionCard)
        if contract.project_type != 'Авторский надзор':
            crm_card = CRMCard(
                contract_id=contract.id,
                column_name='Новый заказ',
                manager_id=current_user.id
            )
            db.add(crm_card)
            logger.info(f"Создана CRM карточка для договора {contract.id}")

        # Лог
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="create",
            entity_type="contract",
            entity_id=contract.id
        )
        db.add(log)

        # Единый коммит: договор + карточка + лог — атомарно
        db.commit()
        db.refresh(contract)

        return contract

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Договор с таким номером уже существует")
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании договора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdate,
    current_user: Employee = Depends(require_permission("contracts.update")),
    db: Session = Depends(get_db)
):
    """Обновить договор"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Проверяем, изменяется ли статус на "АВТОРСКИЙ НАДЗОР"
    old_status = contract.status
    update_data = contract_data.model_dump(exclude_unset=True)
    new_status = update_data.get('status')
    need_supervision_card = (
        new_status == 'АВТОРСКИЙ НАДЗОР' and
        old_status != 'АВТОРСКИЙ НАДЗОР'
    )

    # Обновление полей
    for field, value in update_data.items():
        setattr(contract, field, value)

    # Auto-fill status_changed_date при смене статуса
    if new_status and new_status != old_status:
        contract.status_changed_date = datetime.utcnow().strftime('%Y-%m-%d')

    contract.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contract)

    # BUG #2 FIX: Автоматическое создание карточки надзора при смене статуса
    if need_supervision_card:
        existing_supervision = db.query(SupervisionCard).filter(
            SupervisionCard.contract_id == contract_id
        ).first()
        if not existing_supervision:
            supervision_card = SupervisionCard(
                contract_id=contract_id,
                column_name='Новый заказ',
                created_at=datetime.utcnow()
            )
            db.add(supervision_card)
            db.commit()
            logger.info(f"Автоматически создана карточка надзора для договора {contract_id}")

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update",
        entity_type="contract",
        entity_id=contract.id
    )
    db.add(log)
    db.commit()

    return contract


@router.patch("/{contract_id}/files")
async def update_contract_files(
    contract_id: int,
    files_data: ContractFilesUpdate,
    current_user: Employee = Depends(require_permission("contracts.update")),
    db: Session = Depends(get_db)
):
    """
    Обновить файлы договора (замер, референсы, фотофиксация)

    Этот endpoint используется для обновления:
    - measurement_image_link - ссылка на изображение замера
    - measurement_file_name - имя файла замера
    - measurement_yandex_path - путь к файлу на Яндекс.Диске
    - measurement_date - дата замера
    - contract_file_link - ссылка на договор
    - tech_task_link - ссылка на техническое задание
    """
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Обновляем только переданные поля
    for field, value in files_data.model_dump(exclude_unset=True).items():
        setattr(contract, field, value)

    contract.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contract)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update_files",
        entity_type="contract",
        entity_id=contract.id
    )
    db.add(log)
    db.commit()

    return {
        'id': contract.id,
        'measurement_image_link': contract.measurement_image_link,
        'measurement_file_name': contract.measurement_file_name,
        'measurement_yandex_path': contract.measurement_yandex_path,
        'measurement_date': contract.measurement_date,
        'contract_file_link': contract.contract_file_link,
        'tech_task_link': contract.tech_task_link,
        'updated_at': contract.updated_at.isoformat() if contract.updated_at else None
    }


@router.delete("/{contract_id}", response_model=StatusResponse)
async def delete_contract(
    contract_id: int,
    current_user: Employee = Depends(require_permission("contracts.delete")),
    db: Session = Depends(get_db)
):
    """Удалить договор и все связанные данные"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    try:
        # Удаляем timeline записи проекта
        db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id).delete()

        # Удаляем связанные CRM карточки
        crm_cards = db.query(CRMCard).filter(CRMCard.contract_id == contract_id).all()
        for card in crm_cards:
            # Удаляем связанные stage_executors
            db.query(StageExecutor).filter(StageExecutor.crm_card_id == card.id).delete()
            # Удаляем платежи привязанные к карточке
            db.query(Payment).filter(Payment.crm_card_id == card.id).delete()
            # Удаляем саму карточку
            db.delete(card)

        # Удаляем связанные SupervisionCard
        supervision_cards = db.query(SupervisionCard).filter(SupervisionCard.contract_id == contract_id).all()
        for card in supervision_cards:
            # Удаляем timeline записи надзора
            db.query(SupervisionTimelineEntry).filter(SupervisionTimelineEntry.supervision_card_id == card.id).delete()
            # Удаляем связанную историю
            db.query(SupervisionProjectHistory).filter(SupervisionProjectHistory.supervision_card_id == card.id).delete()
            # Удаляем платежи привязанные к карточке надзора
            db.query(Payment).filter(Payment.supervision_card_id == card.id).delete()
            db.delete(card)

        # Удаляем оставшиеся платежи по договору
        db.query(Payment).filter(Payment.contract_id == contract_id).delete()

        # Удаляем связанные файлы проекта
        db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).delete()

        # Лог перед удалением
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="delete",
            entity_type="contract",
            entity_id=contract_id
        )
        db.add(log)

        db.delete(contract)
        db.commit()

        return {"status": "success", "message": "Договор и все связанные данные удалены"}

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении договора {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
