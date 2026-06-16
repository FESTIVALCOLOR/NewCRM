"""
Роутер для endpoint'ов договоров (contracts).
Подключается в main.py через app.include_router(contracts_router, prefix="/api/contracts").
"""

from datetime import datetime
import logging
from typing import List, Optional

from auth import get_current_user
from constants import ARCHIVE_STATUSES
from fastapi import APIRouter, Depends, HTTPException, Response, status
from permissions import require_permission
from schemas import ContractCreate, ContractFilesUpdate, ContractResponse, ContractUpdate, StatusResponse
from sqlalchemy import func, nullslast, or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import (
    ActivityLog,
    ApprovalStageDeadline,
    Client,
    Contract,
    CRMCard,
    DeletedContract,
    Employee,
    FileStorage,
    InternalChat,
    MessengerChat,
    Notification,
    Payment,
    ProjectFile,
    ProjectTimelineEntry,
    Salary,
    StageExecutor,
    StageWorkflowState,
    SupervisionCard,
    SupervisionProjectHistory,
    SupervisionTimelineEntry,
    SupervisionVisit,
    get_db,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["contracts"])


# =========================
# ДОГОВОРЫ
# =========================


@router.get("/", response_model=list[ContractResponse])
async def get_contracts(skip: int = 0, limit: int = 100, response: Response = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список договоров с пагинацией.
    Заголовок X-Total-Count содержит общее количество записей."""
    # Считаем общее количество записей для пагинации
    total = db.query(func.count(Contract.id)).scalar()
    contracts = db.query(Contract).order_by(nullslast(Contract.contract_date.desc())).offset(skip).limit(limit).all()
    # Устанавливаем заголовок с общим количеством записей
    if response is not None:
        response.headers["X-Total-Count"] = str(total)
    return contracts


@router.get("/count")
async def get_contracts_count(
    status: Optional[str] = None, project_type: Optional[str] = None, year: Optional[int] = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)
):
    """Получить количество договоров с фильтрацией (без загрузки всех записей)"""
    query = db.query(func.count(Contract.id))
    if status:
        query = query.filter(Contract.status == status)
    if project_type:
        query = query.filter(Contract.project_type == project_type)
    if year:
        from sqlalchemy import extract

        query = query.filter(extract("year", Contract.contract_date) == year)
    count = query.scalar()
    return {"count": count}


@router.get("/{contract_id}")
async def get_contract(contract_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить договор по ID"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")
    # Обогащаем ответ данными CRM карточки (total_pause_days)
    crm_card = db.query(CRMCard).filter(CRMCard.contract_id == contract_id).order_by(CRMCard.id.desc()).first()
    data = ContractResponse.model_validate(contract).model_dump()
    data["crm_card_total_pause_days"] = crm_card.total_pause_days if crm_card else 0
    return data


@router.post("/", response_model=ContractResponse)
async def create_contract(contract_data: ContractCreate, current_user: Employee = Depends(require_permission("contracts.create")), db: Session = Depends(get_db)):
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
        if contract.project_type != "Авторский надзор":
            # Назначаем создателя в соответствующее поле по должности
            crm_card_kwargs = {
                "contract_id": contract.id,
                "column_name": "Новый заказ",
            }
            if current_user.position in ("Руководитель студии", "Старший менеджер"):
                crm_card_kwargs["senior_manager_id"] = current_user.id
            elif current_user.position == "Менеджер":
                crm_card_kwargs["manager_id"] = current_user.id
            else:
                # Для остальных должностей — в manager_id как fallback
                crm_card_kwargs["manager_id"] = current_user.id

            crm_card = CRMCard(**crm_card_kwargs)
            db.add(crm_card)
            logger.info(f"Создана CRM карточка для договора {contract.id}, создатель: {current_user.full_name} ({current_user.position})")

        # Лог
        log = ActivityLog(employee_id=current_user.id, action_type="create", entity_type="contract", entity_id=contract.id)
        db.add(log)

        # Единый коммит: договор + карточка + лог — атомарно
        db.commit()
        db.refresh(contract)

        # Авто-инициализация таймлайна (только если есть площадь)
        if contract.project_type != "Авторский надзор" and (contract.area or 0) > 0:
            try:
                from services.timeline_service import (
                    build_project_timeline_template,
                    build_template_project_timeline,
                    refresh_timeline_start_date,
                )

                _existing = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract.id).count()
                if _existing == 0:
                    _agent = contract.agent_type or "Все агенты"
                    if contract.project_type == "Шаблонный":
                        _entries, _, _ = build_template_project_timeline(contract.project_subtype or "Стандарт", contract.area, floors=1, agent_type=_agent)
                    else:
                        _entries, _, _ = build_project_timeline_template(contract.project_type or "Индивидуальный", contract.area, contract.project_subtype, agent_type=_agent)
                    for e in _entries:
                        db.add(
                            ProjectTimelineEntry(
                                contract_id=contract.id,
                                stage_code=e["stage_code"],
                                stage_name=e["stage_name"],
                                stage_group=e["stage_group"],
                                substage_group=e.get("substage_group", ""),
                                executor_role=e["executor_role"],
                                is_in_contract_scope=e["is_in_contract_scope"],
                                sort_order=e["sort_order"],
                                raw_norm_days=e.get("raw_norm_days", 0),
                                cumulative_days=e.get("cumulative_days", 0),
                                norm_days=e.get("norm_days", 0),
                            )
                        )
                    db.commit()
                    refresh_timeline_start_date(db, contract.id)
            except Exception as _te:
                logger.warning(f"Авто-инициализация таймлайна для договора {contract.id}: {_te}")

        return contract

    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Договор с таким номером уже существует")
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании договора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.put("/{contract_id}", response_model=ContractResponse)
async def update_contract(contract_id: int, contract_data: ContractUpdate, current_user: Employee = Depends(require_permission("contracts.update")), db: Session = Depends(get_db)):
    """Обновить договор"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Проверяем, изменяется ли статус на "АВТОРСКИЙ НАДЗОР"
    old_status = contract.status
    update_data = contract_data.model_dump(exclude_unset=True)
    old_area = contract.area
    new_status = update_data.get("status")
    need_supervision_card = new_status == "АВТОРСКИЙ НАДЗОР" and old_status != "АВТОРСКИЙ НАДЗОР"

    # П4: ретроактивная проверка — нельзя менять подтип на Планировочный,
    # если CRM-карточка уже на Стадии 2 или 3
    new_subtype = update_data.get("project_subtype")
    if new_subtype and "Планировочный" in new_subtype:
        crm_card = db.query(CRMCard).filter(CRMCard.contract_id == contract_id).first()
        if crm_card and crm_card.column_name and ("Стадия 2" in crm_card.column_name or "Стадия 3" in crm_card.column_name):
            raise HTTPException(status_code=400, detail=f"Нельзя сменить подтип на Планировочный: карточка уже на «{crm_card.column_name}». Сначала верните карточку на Стадию 1.")

    # Обновление полей
    for field, value in update_data.items():
        setattr(contract, field, value)

    # Auto-fill status_changed_date при смене статуса
    if new_status and new_status != old_status:
        contract.status_changed_date = datetime.utcnow().strftime("%Y-%m-%d")

    contract.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(contract)

    # BUG #2 FIX: Автоматическое создание карточки надзора при смене статуса
    if need_supervision_card:
        existing_supervision = db.query(SupervisionCard).filter(SupervisionCard.contract_id == contract_id).first()
        if not existing_supervision:
            supervision_card = SupervisionCard(contract_id=contract_id, column_name="Новый заказ", created_at=datetime.utcnow())
            db.add(supervision_card)
            db.commit()
            logger.info(f"Автоматически создана карточка надзора для договора {contract_id}")

    # Пересчёт оплат при изменении площади
    new_area = update_data.get("area")
    if new_area is not None and float(new_area or 0) != float(old_area or 0):
        from routers.payments_router import _recalculate_payments_for_contract

        recalc_count = _recalculate_payments_for_contract(db, contract_id)
        if recalc_count:
            logger.info(f"Договор {contract_id}: площадь изменена, пересчитано оплат: {recalc_count}")

    # Обновить дату START таймлайна и дедлайн при изменении дат-триггеров или срока
    if any(f in update_data for f in ("contract_date", "advance_payment_paid_date", "contract_period")):
        from services.timeline_service import refresh_timeline_start_date

        refresh_timeline_start_date(db, contract_id)

    # Лог
    log = ActivityLog(employee_id=current_user.id, action_type="update", entity_type="contract", entity_id=contract.id)
    db.add(log)
    db.commit()

    return contract


@router.patch("/{contract_id}/files")
async def update_contract_files(contract_id: int, files_data: ContractFilesUpdate, current_user: Employee = Depends(require_permission("contracts.update")), db: Session = Depends(get_db)):
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
    log = ActivityLog(employee_id=current_user.id, action_type="update_files", entity_type="contract", entity_id=contract.id)
    db.add(log)
    db.commit()

    return {
        "id": contract.id,
        "measurement_image_link": contract.measurement_image_link,
        "measurement_file_name": contract.measurement_file_name,
        "measurement_yandex_path": contract.measurement_yandex_path,
        "measurement_date": contract.measurement_date,
        "contract_file_link": contract.contract_file_link,
        "tech_task_link": contract.tech_task_link,
        "updated_at": contract.updated_at.isoformat() if contract.updated_at else None,
    }


@router.post("/fix-all-folders")
async def fix_all_contract_folders(current_user: Employee = Depends(require_permission("contracts.update")), db: Session = Depends(get_db)):
    """Массовая починка папок ЯД: создаёт папки которых нет на диске,
    генерирует путь для договоров без yandex_folder_path."""
    import re

    # Берём ВСЕ активные договоры (не только без пути)
    contracts = db.query(Contract).all()

    import os

    import requests as req
    from yandex_disk_service import YandexDiskService

    yd = YandexDiskService()
    token = os.environ.get("YANDEX_DISK_TOKEN", "")
    fixed = 0
    already_ok = 0
    errors = []

    for contract in contracts:
        try:
            # Генерируем путь если нет
            folder_path = contract.yandex_folder_path
            if not folder_path:
                agent = contract.agent_type or "ФЕСТИВАЛЬ"
                ptype = contract.project_type or "Индивидуальный"
                city = contract.city or "Москва"
                address = contract.address or "Без адреса"
                area = contract.area or 0
                type_folder = "Индивидуальные" if "ндивид" in ptype else "Шаблонные"
                folder_name = f"{city}-{address}-{area}м2"
                folder_name = re.sub(r'[<>:"|?*]', "", folder_name)
                folder_path = f"disk:/CRM/Проекты/{agent}/{type_folder}/{city}/{folder_name}"

            # Проверяем существование папки на ЯД
            check = req.get("https://cloud-api.yandex.net/v1/disk/resources", params={"path": folder_path}, headers={"Authorization": f"OAuth {token}"}, timeout=10)
            if check.status_code == 200:
                # Папка существует
                if not contract.yandex_folder_path:
                    contract.yandex_folder_path = folder_path
                    fixed += 1
                else:
                    already_ok += 1
            else:
                # Папка НЕ существует — создаём
                yd.create_folder(folder_path)
                contract.yandex_folder_path = folder_path
                fixed += 1
                logger.info(f"Папка создана для договора {contract.id}: {folder_path}")
        except Exception as e:
            errors.append(f"ID {contract.id}: {str(e)[:100]}")

    db.commit()
    return {
        "status": "success",
        "message": f"Починено {fixed}, уже ОК {already_ok}, ошибки {len(errors)} из {len(contracts)} договоров",
        "fixed": fixed,
        "already_ok": already_ok,
        "errors": errors[:10],
    }


@router.post("/{contract_id}/fix-folder", response_model=StatusResponse)
async def fix_contract_folder(contract_id: int, current_user: Employee = Depends(require_permission("contracts.update")), db: Session = Depends(get_db)):
    """Диагностика и починка папки на Яндекс.Диске для договора.
    Создаёт папку если не существует, обновляет yandex_folder_path в БД.
    """
    import re

    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    try:
        from yandex_disk_service import YandexDiskService

        yd = YandexDiskService()

        # Генерируем путь
        agent = contract.agent_type or "ФЕСТИВАЛЬ"
        ptype = contract.project_type or "Индивидуальный"
        city = contract.city or "Москва"
        address = contract.address or "Без адреса"
        area = contract.area or 0
        type_folder = "Индивидуальные" if "ндивид" in ptype else "Шаблонные"
        folder_name = f"{city}-{address}-{area}м2"
        folder_name = re.sub(r'[<>:"|?*]', "", folder_name)
        folder_path = f"disk:/CRM/Проекты/{agent}/{type_folder}/{city}/{folder_name}"

        # Создаём папку рекурсивно
        result = yd.create_folder(folder_path)
        if result or (isinstance(result, dict)):
            # Обновляем в БД
            contract.yandex_folder_path = folder_path
            db.commit()
            logger.info(f"Папка починена для договора {contract_id}: {folder_path}")
            return {"status": "success", "message": f"Папка создана: {folder_path}"}
        else:
            return {"status": "error", "message": "Не удалось создать папку на Яндекс.Диске"}
    except Exception as e:
        logger.exception(f"Ошибка починки папки для договора {contract_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{contract_id}", response_model=StatusResponse)
async def delete_contract(contract_id: int, current_user: Employee = Depends(require_permission("contracts.delete")), db: Session = Depends(get_db)):
    """Удалить договор и все связанные данные"""
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    # Запрет удаления активного договора
    if contract.status not in ARCHIVE_STATUSES:
        raise HTTPException(status_code=409, detail=f"Нельзя удалить активный договор (статус: {contract.status}). Сначала переведите в архивный статус.")

    try:
        # === Собираем снимок данных до удаления ===
        client_obj = db.query(Client).filter(Client.id == contract.client_id).first()
        client_name = client_obj.full_name if client_obj else ""

        def _row_to_dict(obj):
            d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
            for k, v in d.items():
                if hasattr(v, "isoformat"):
                    d[k] = v.isoformat()
            return d

        snap_crm_cards = []
        for card in db.query(CRMCard).filter(CRMCard.contract_id == contract_id).all():
            snap_crm_cards.append(
                {
                    "card": _row_to_dict(card),
                    "stage_executors": [_row_to_dict(r) for r in db.query(StageExecutor).filter(StageExecutor.crm_card_id == card.id).all()],
                    "workflow_states": [_row_to_dict(r) for r in db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card.id).all()],
                    "approval_deadlines": [_row_to_dict(r) for r in db.query(ApprovalStageDeadline).filter(ApprovalStageDeadline.crm_card_id == card.id).all()],
                    "payments": [_row_to_dict(r) for r in db.query(Payment).filter(Payment.crm_card_id == card.id).all()],
                    "messenger_chats": [_row_to_dict(r) for r in db.query(MessengerChat).filter(MessengerChat.crm_card_id == card.id).all()],
                    "internal_chats": [_row_to_dict(r) for r in db.query(InternalChat).filter(InternalChat.crm_card_id == card.id).all()],
                }
            )

        snap_sup_cards = []
        for card in db.query(SupervisionCard).filter(SupervisionCard.contract_id == contract_id).all():
            snap_sup_cards.append(
                {
                    "card": _row_to_dict(card),
                    "timeline_entries": [_row_to_dict(r) for r in db.query(SupervisionTimelineEntry).filter(SupervisionTimelineEntry.supervision_card_id == card.id).all()],
                    "visits": [_row_to_dict(r) for r in db.query(SupervisionVisit).filter(SupervisionVisit.supervision_card_id == card.id).all()],
                    "history": [_row_to_dict(r) for r in db.query(SupervisionProjectHistory).filter(SupervisionProjectHistory.supervision_card_id == card.id).all()],
                    "payments": [_row_to_dict(r) for r in db.query(Payment).filter(Payment.supervision_card_id == card.id).all()],
                }
            )

        snapshot_data = {
            "contract": _row_to_dict(contract),
            "crm_cards": snap_crm_cards,
            "supervision_cards": snap_sup_cards,
            "payments": [_row_to_dict(r) for r in db.query(Payment).filter(Payment.contract_id == contract_id).all()],
            "salaries": [_row_to_dict(r) for r in db.query(Salary).filter(Salary.contract_id == contract_id).all()],
            "project_files": [_row_to_dict(r) for r in db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).all()],
            "timeline_entries": [_row_to_dict(r) for r in db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id).all()],
            "messenger_chats": [_row_to_dict(r) for r in db.query(MessengerChat).filter(MessengerChat.contract_id == contract_id).all()],
            "internal_chats": [_row_to_dict(r) for r in db.query(InternalChat).filter(InternalChat.contract_id == contract_id).all()],
            "file_storage": [_row_to_dict(r) for r in db.query(FileStorage).filter(FileStorage.contract_id == contract_id).all()],
        }

        deleted_record = DeletedContract(
            original_contract_id=contract_id,
            contract_number=contract.contract_number,
            client_name=client_name,
            address=contract.address,
            project_type=contract.project_type,
            project_subtype=contract.project_subtype,
            yandex_folder_path=contract.yandex_folder_path,
            snapshot=snapshot_data,
            deleted_by_id=current_user.id,
        )
        db.add(deleted_record)
        db.flush()
        # ==========================================

        # Удаляем папки на Яндекс.Диске (до удаления записей в БД)
        try:
            from yandex_disk_service import get_yandex_disk_service

            yd = get_yandex_disk_service()
            if yd and yd.token:
                # Папки чатов сотрудников/клиентов (InternalChat) — удаляем до CASCADE-удаления
                chats = (
                    db.query(InternalChat)
                    .filter((InternalChat.contract_id == contract_id) | (InternalChat.crm_card_id.in_(db.query(CRMCard.id).filter(CRMCard.contract_id == contract_id).scalar_subquery())))
                    .all()
                )
                for chat in chats:
                    if chat.yandex_folder_path:
                        try:
                            yd.delete_file(chat.yandex_folder_path.replace("disk:", ""), permanently=False)
                        except Exception:
                            pass

                # Главная папка договора на ЯД
                if contract.yandex_folder_path:
                    try:
                        yd.delete_file(contract.yandex_folder_path.replace("disk:", ""), permanently=False)
                        logger.info(f"Папка ЯД удалена: {contract.yandex_folder_path}")
                    except Exception as e:
                        logger.warning(f"Не удалось удалить папку ЯД {contract.yandex_folder_path}: {e}")
        except Exception as e:
            logger.warning(f"Ошибка при удалении данных с Яндекс.Диска: {e}")

        # Удаляем timeline записи проекта
        db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id).delete()

        # Удаляем связанные CRM карточки
        crm_cards = db.query(CRMCard).filter(CRMCard.contract_id == contract_id).all()
        for card in crm_cards:
            # Удаляем уведомления привязанные к карточке
            db.query(Notification).filter(Notification.related_entity_type == "crm_card", Notification.related_entity_id == card.id).delete()
            # Удаляем чаты мессенджера
            db.query(MessengerChat).filter(MessengerChat.crm_card_id == card.id).delete()
            # Удаляем workflow state
            db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card.id).delete()
            # Удаляем дедлайны согласования
            db.query(ApprovalStageDeadline).filter(ApprovalStageDeadline.crm_card_id == card.id).delete()
            # Удаляем связанные stage_executors
            db.query(StageExecutor).filter(StageExecutor.crm_card_id == card.id).delete()
            # Удаляем платежи привязанные к карточке
            db.query(Payment).filter(Payment.crm_card_id == card.id).delete()
            # Удаляем саму карточку
            db.delete(card)

        # Удаляем связанные SupervisionCard
        supervision_cards = db.query(SupervisionCard).filter(SupervisionCard.contract_id == contract_id).all()
        for card in supervision_cards:
            # Удаляем уведомления привязанные к карточке надзора
            db.query(Notification).filter(Notification.related_entity_type == "supervision_card", Notification.related_entity_id == card.id).delete()
            # Удаляем timeline записи надзора
            db.query(SupervisionTimelineEntry).filter(SupervisionTimelineEntry.supervision_card_id == card.id).delete()
            # Удаляем выезды надзора
            db.query(SupervisionVisit).filter(SupervisionVisit.supervision_card_id == card.id).delete()
            # Удаляем связанную историю
            db.query(SupervisionProjectHistory).filter(SupervisionProjectHistory.supervision_card_id == card.id).delete()
            # Удаляем платежи привязанные к карточке надзора
            db.query(Payment).filter(Payment.supervision_card_id == card.id).delete()
            db.delete(card)

        # Удаляем оставшиеся чаты по договору
        db.query(MessengerChat).filter(MessengerChat.contract_id == contract_id).delete()

        # Удаляем оставшиеся платежи по договору
        db.query(Payment).filter(Payment.contract_id == contract_id).delete()

        # Удаляем связанные файлы проекта
        db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).delete()

        # Удаляем зарплаты привязанные к договору
        db.query(Salary).filter(Salary.contract_id == contract_id).delete()

        # Удаляем записи файлового хранилища
        db.query(FileStorage).filter(FileStorage.contract_id == contract_id).delete()

        # Лог перед удалением
        log = ActivityLog(employee_id=current_user.id, action_type="delete", entity_type="contract", entity_id=contract_id)
        db.add(log)

        db.delete(contract)
        db.commit()

        return {"status": "success", "message": "Договор и все связанные данные удалены"}

    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении договора {contract_id}: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
