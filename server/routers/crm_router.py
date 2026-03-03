"""
Роутер CRM-карточек и Workflow.
Подключается в main.py через app.include_router(crm_router, prefix="/api/crm").
"""
import asyncio
import json
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import List, Optional

from database import (
    get_db, Employee, Client, Contract, ActivityLog,
    CRMCard, StageExecutor, SupervisionCard,
    ApprovalStageDeadline, ProjectTimelineEntry,
    StageWorkflowState, Payment, ActionHistory,
    MessengerChat,
)
from auth import get_current_user
from permissions import require_permission
from schemas import (
    CRMCardCreate, CRMCardUpdate, CRMCardResponse,
    ColumnMoveRequest, StageExecutorCreate, StageExecutorUpdate, StageExecutorResponse,
    ActionHistoryResponse, SupervisionHistoryResponse,
    CompleteApprovalStageRequest, StageExecutorDeadlineRequest,
    CompleteStageExecutorRequest, ManagerAcceptanceRequest,
)
from services.notification_service import trigger_messenger_notification


def _add_business_days(start_date, days: int):
    """Добавить рабочие дни (пн-пт) к дате."""
    if isinstance(start_date, str):
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if current.weekday() < 5:
            added += 1
    return current


RUSSIAN_HOLIDAYS = [
    (1, 1), (1, 2), (1, 3), (1, 4), (1, 5), (1, 6), (1, 7), (1, 8),
    (2, 23), (3, 8), (5, 1), (5, 9), (6, 12), (11, 4),
]


def _is_working_day(d):
    """Рабочий ли день (учитывает выходные + праздники)"""
    if d.weekday() in [5, 6]:
        return False
    if (d.month, d.day) in RUSSIAN_HOLIDAYS:
        return False
    return True


def _count_business_days(start_date, end_date):
    """Подсчёт рабочих дней между двумя датами (с учётом праздников)"""
    days = 0
    current = start_date
    while current < end_date:
        if _is_working_day(current):
            days += 1
        current += timedelta(days=1)
    return days


def _add_working_days_to_date(start_date_str, working_days):
    """Добавить рабочие дни к дате (строка YYYY-MM-DD → строка YYYY-MM-DD)"""
    try:
        current = datetime.strptime(start_date_str, '%Y-%m-%d')
    except (ValueError, TypeError):
        return start_date_str
    added = 0
    while added < working_days:
        current += timedelta(days=1)
        if _is_working_day(current):
            added += 1
    return current.strftime('%Y-%m-%d')


logger = logging.getLogger(__name__)
router = APIRouter(tags=["crm"])


# =========================
# CRM КАРТОЧКИ
# =========================

@router.get("/cards")
async def get_crm_cards(
    project_type: str,
    archived: bool = False,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список CRM карточек по типу проекта

    Args:
        project_type: Тип проекта (Индивидуальный/Шаблонный)
        archived: Если True - возвращает архивные карточки (СДАН, РАСТОРГНУТ, АВТОРСКИЙ НАДЗОР)
    """
    try:
        query = db.query(CRMCard, Client.full_name.label('client_name')).join(
            Contract, CRMCard.contract_id == Contract.id
        ).outerjoin(
            Client, Contract.client_id == Client.id
        ).filter(
            Contract.project_type == project_type
        )

        if archived:
            # Архивные карточки - статус СДАН, РАСТОРГНУТ или АВТОРСКИЙ НАДЗОР
            query = query.filter(
                Contract.status.in_(['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
            )
        else:
            # Активные карточки - статус НЕ в архивных
            query = query.filter(
                or_(
                    Contract.status == None,
                    Contract.status == '',
                    ~Contract.status.in_(['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
                )
            )

        rows = query.order_by(
            CRMCard.order_position.nullslast(),
            CRMCard.id
        ).all()

        # Распаковываем (CRMCard, client_name) из результата
        cards = [row[0] for row in rows]
        client_names = {row[0].id: row[1] for row in rows}

        # Batch-load all stage executors for all cards to avoid N+1 queries
        card_ids = [card.id for card in cards]
        all_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id.in_(card_ids)).all() if card_ids else []
        executors_by_card = {}
        for se in all_executors:
            if se.crm_card_id not in executors_by_card:
                executors_by_card[se.crm_card_id] = []
            executors_by_card[se.crm_card_id].append(se)

        # Batch-load executor Employee objects for all stage executors
        executor_employee_ids = list(set(se.executor_id for se in all_executors if se.executor_id))
        executor_employees_map = {e.id: e for e in db.query(Employee).filter(Employee.id.in_(executor_employee_ids)).all()} if executor_employee_ids else {}

        result = []
        for card in cards:
            contract = card.contract
            senior_manager_name = card.senior_manager.full_name if card.senior_manager else None
            sdp_name = card.sdp.full_name if card.sdp else None
            gap_name = card.gap.full_name if card.gap else None
            manager_name = card.manager.full_name if card.manager else None
            surveyor_name = card.surveyor.full_name if card.surveyor else None

            # ИСПРАВЛЕНИЕ 06.02.2026: Добавлен поиск по '3д визуализация' для шаблонных проектов (#10)
            # Use batch-loaded executors instead of per-card queries
            card_executors = executors_by_card.get(card.id, [])

            # Find designer executor: stage_name contains 'концепция' or 'визуализация', latest by id
            designer_candidates = [
                e for e in card_executors
                if 'концепция' in (e.stage_name or '').lower() or 'визуализация' in (e.stage_name or '').lower()
            ]
            designer_executor = max(designer_candidates, key=lambda e: e.id) if designer_candidates else None

            # Find draftsman executor: stage_name contains 'чертежи' or 'планировочные', latest by id
            draftsman_candidates = [
                e for e in card_executors
                if 'чертежи' in (e.stage_name or '').lower() or 'планировочные' in (e.stage_name or '').lower()
            ]
            draftsman_executor = max(draftsman_candidates, key=lambda e: e.id) if draftsman_candidates else None

            # Get executor names from batch-loaded employees map
            designer_employee = executor_employees_map.get(designer_executor.executor_id) if designer_executor else None
            draftsman_employee = executor_employees_map.get(draftsman_executor.executor_id) if draftsman_executor else None

            card_data = {
                'id': card.id,
                'contract_id': card.contract_id,
                'column_name': card.column_name,
                'deadline': str(card.deadline) if card.deadline else None,
                'tags': card.tags,
                'is_approved': card.is_approved,
                'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
                'approval_stages': json.loads(card.approval_stages) if card.approval_stages else None,
                'project_data_link': card.project_data_link,
                'tech_task_file': card.tech_task_file,
                'tech_task_date': str(card.tech_task_date) if card.tech_task_date else None,
                'survey_date': str(card.survey_date) if card.survey_date else None,
                'senior_manager_id': card.senior_manager_id,
                'sdp_id': card.sdp_id,
                'gap_id': card.gap_id,
                'manager_id': card.manager_id,
                'surveyor_id': card.surveyor_id,
                'senior_manager_name': senior_manager_name,
                'sdp_name': sdp_name,
                'gap_name': gap_name,
                'manager_name': manager_name,
                'surveyor_name': surveyor_name,
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'project_type': contract.project_type,
                'project_subtype': contract.project_subtype if hasattr(contract, 'project_subtype') else None,
                'floors': contract.floors if hasattr(contract, 'floors') else 1,
                'contract_period': contract.contract_period,
                'contract_status': contract.status,
                # Поля ТЗ и замера из contracts
                'tech_task_link': contract.tech_task_link,
                'tech_task_file_name': contract.tech_task_file_name,
                'tech_task_yandex_path': contract.tech_task_yandex_path,
                'measurement_image_link': contract.measurement_image_link,
                'measurement_file_name': contract.measurement_file_name,
                'measurement_yandex_path': contract.measurement_yandex_path,
                'measurement_date': str(contract.measurement_date) if contract.measurement_date else None,
                'designer_name': designer_employee.full_name if designer_employee else None,
                'designer_completed': designer_executor.completed if designer_executor else False,
                'designer_deadline': str(designer_executor.deadline) if designer_executor and designer_executor.deadline else None,
                'draftsman_name': draftsman_employee.full_name if draftsman_employee else None,
                'draftsman_completed': draftsman_executor.completed if draftsman_executor else False,
                'draftsman_deadline': str(draftsman_executor.deadline) if draftsman_executor and draftsman_executor.deadline else None,
                'order_position': card.order_position,
                'client_name': client_names.get(card.id),
                'created_at': card.created_at.isoformat() if card.created_at else None,
                'updated_at': card.updated_at.isoformat() if card.updated_at else None,
            }
            result.append(card_data)

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении CRM карточек: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}")
async def get_crm_card(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить одну CRM карточку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Контракт — для полей project_subtype, agent_type, address и т.д.
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first() if card.contract_id else None

        # Имена сотрудников
        def _emp_name(emp_id):
            if not emp_id:
                return None
            emp = db.query(Employee).filter(Employee.id == emp_id).first()
            return emp.full_name if emp else None

        stage_executors = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id
        ).all()

        executor_data = []
        for se in stage_executors:
            executor_data.append({
                'id': se.id,
                'stage_name': se.stage_name,
                'executor_id': se.executor_id,
                'executor_name': se.executor.full_name,
                'assigned_by': se.assigned_by,
                'assigned_date': se.assigned_date.isoformat() if se.assigned_date else None,
                'deadline': str(se.deadline) if se.deadline else None,
                'submitted_date': se.submitted_date.isoformat() if se.submitted_date else None,
                'completed': se.completed,
                'completed_date': se.completed_date.isoformat() if se.completed_date else None,
            })

        result = {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'is_approved': card.is_approved,
            'senior_manager_id': card.senior_manager_id,
            'sdp_id': card.sdp_id,
            'gap_id': card.gap_id,
            'manager_id': card.manager_id,
            'surveyor_id': card.surveyor_id,
            'senior_manager_name': _emp_name(card.senior_manager_id),
            'sdp_name': _emp_name(card.sdp_id),
            'gap_name': _emp_name(card.gap_id),
            'manager_name': _emp_name(card.manager_id),
            'surveyor_name': _emp_name(card.surveyor_id),
            'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
            'approval_stages': json.loads(card.approval_stages) if card.approval_stages else None,
            'project_data_link': card.project_data_link,
            'tech_task_file': card.tech_task_file,
            'tech_task_date': str(card.tech_task_date) if card.tech_task_date else None,
            'survey_date': str(card.survey_date) if card.survey_date else None,
            'order_position': card.order_position,
            'stage_executors': executor_data,
        }

        # Поля из контракта
        if contract:
            # Имя клиента
            client = db.query(Client).filter(Client.id == contract.client_id).first() if contract.client_id else None
            result.update({
                'contract_number': contract.contract_number,
                'address': contract.address,
                'area': contract.area,
                'city': contract.city,
                'agent_type': contract.agent_type,
                'project_type': contract.project_type,
                'project_subtype': contract.project_subtype if hasattr(contract, 'project_subtype') else None,
                'floors': contract.floors if hasattr(contract, 'floors') else 1,
                'contract_period': contract.contract_period,
                'contract_status': contract.status,
                'client_name': client.full_name if client else None,
            })

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при получении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards", response_model=CRMCardResponse)
async def create_crm_card(
    card_data: CRMCardCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать новую CRM карточку"""
    try:
        # Защита от дублей: проверяем что CRM-карточка для этого договора ещё не существует
        if card_data.contract_id:
            existing_card = db.query(CRMCard).filter(
                CRMCard.contract_id == card_data.contract_id
            ).first()
            if existing_card:
                raise HTTPException(
                    status_code=409,
                    detail="CRM-карточка для этого договора уже существует"
                )

        card = CRMCard(**card_data.model_dump())
        db.add(card)
        db.commit()
        db.refresh(card)

        log = ActivityLog(
            employee_id=current_user.id,
            action_type="create",
            entity_type="crm_card",
            entity_id=card.id
        )
        db.add(log)
        db.commit()

        # Явная сериализация для корректного ответа
        return {
            "id": card.id,
            "contract_id": card.contract_id,
            "column_name": card.column_name,
            "deadline": str(card.deadline) if card.deadline else None,
            "tags": card.tags,
            "is_approved": card.is_approved,
            "approval_deadline": str(card.approval_deadline) if card.approval_deadline else None,
            "approval_stages": json.loads(card.approval_stages) if card.approval_stages else None,
            "project_data_link": card.project_data_link,
            "tech_task_file": card.tech_task_file,
            "tech_task_date": str(card.tech_task_date) if card.tech_task_date else None,
            "survey_date": str(card.survey_date) if card.survey_date else None,
            "senior_manager_id": card.senior_manager_id,
            "sdp_id": card.sdp_id,
            "gap_id": card.gap_id,
            "manager_id": card.manager_id,
            "surveyor_id": card.surveyor_id,
            "order_position": card.order_position,
            "created_at": card.created_at.isoformat() if card.created_at else None,
            "updated_at": card.updated_at.isoformat() if card.updated_at else None
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}")
async def update_crm_card(
    card_id: int,
    updates: CRMCardUpdate,
    current_user: Employee = Depends(require_permission("crm_cards.update")),
    db: Session = Depends(get_db)
):
    """Обновить CRM карточку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        update_data = updates.model_dump(exclude_unset=True)

        # Проверяем существование сотрудников перед обновлением FK полей
        employee_fields = ['senior_manager_id', 'sdp_id', 'gap_id', 'manager_id', 'surveyor_id']
        for field in employee_fields:
            if field in update_data and update_data[field] is not None:
                employee_exists = db.query(Employee).filter(Employee.id == update_data[field]).first()
                if not employee_exists:
                    # Удаляем несуществующий ID из обновлений (игнорируем)
                    logger.warning(f"Employee ID {update_data[field]} not found for field {field}, skipping")
                    del update_data[field]

        # Сохраняем старые значения для аудита
        old_values = {field: getattr(card, field, None) for field in update_data}
        old_values_str = {k: str(v) if v is not None else None for k, v in old_values.items()}

        for field, value in update_data.items():
            setattr(card, field, value)

        # Аудит-лог изменений
        activity = ActivityLog(
            employee_id=current_user.id,
            action_type="update",
            entity_type="crm_card",
            entity_id=card_id,
            old_values=json.dumps(old_values_str, ensure_ascii=False) if old_values_str else None,
            new_values=json.dumps({k: str(v) if v is not None else None for k, v in update_data.items()}, ensure_ascii=False)
        )
        db.add(activity)

        db.commit()
        db.refresh(card)

        # R-11 FIX: Унифицированный формат ответа (как в create)
        return {
            'id': card.id,
            'contract_id': card.contract_id,
            'column_name': card.column_name,
            'deadline': str(card.deadline) if card.deadline else None,
            'tags': card.tags,
            'is_approved': card.is_approved,
            'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
            'approval_stages': json.loads(card.approval_stages) if card.approval_stages else None,
            'project_data_link': card.project_data_link,
            'tech_task_file': card.tech_task_file,
            'tech_task_date': str(card.tech_task_date) if card.tech_task_date else None,
            'survey_date': str(card.survey_date) if card.survey_date else None,
            'senior_manager_id': card.senior_manager_id,
            'sdp_id': card.sdp_id,
            'gap_id': card.gap_id,
            'manager_id': card.manager_id,
            'surveyor_id': card.surveyor_id,
            'order_position': card.order_position,
            'created_at': card.created_at.isoformat() if card.created_at else None,
            'updated_at': card.updated_at.isoformat() if card.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/column")
async def move_crm_card_to_column(
    card_id: int,
    move_request: ColumnMoveRequest,
    current_user: Employee = Depends(require_permission("crm_cards.move")),
    db: Session = Depends(get_db)
):
    """Переместить CRM карточку в другую колонку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # S-01: Определяем тип проекта для выбора допустимых колонок
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        project_type = contract.project_type if contract else 'Индивидуальный'

        INDIVIDUAL_COLUMNS = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: планировочные решения', 'Стадия 2: концепция дизайна',
            'Стадия 3: рабочие чертежи',
            'Выполненный проект'
        ]
        TEMPLATE_COLUMNS = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: планировочные решения', 'Стадия 2: рабочие чертежи',
            'Стадия 3: 3д визуализация (Дополнительная)',
            'Выполненный проект'
        ]
        VALID_CRM_COLUMNS = TEMPLATE_COLUMNS if project_type == 'Шаблонный' else INDIVIDUAL_COLUMNS

        if move_request.column_name not in VALID_CRM_COLUMNS:
            raise HTTPException(status_code=422, detail=f"Недопустимая колонка: {move_request.column_name}")

        old_column = card.column_name
        new_column = move_request.column_name

        # Ограничение для Планировочного проекта: только определённые колонки
        project_subtype = contract.project_subtype if contract else None
        if project_subtype and 'Планировочный' in project_subtype:
            if 'Стадия 2' in new_column or 'Стадия 3' in new_column:
                raise HTTPException(
                    status_code=400,
                    detail="Планировочный проект не может перейти в эту стадию"
                )

        # === ПРАВИЛО: Нельзя вернуться в "Новый заказ" ===
        if new_column == 'Новый заказ' and old_column != 'Новый заказ':
            raise HTTPException(
                status_code=422,
                detail='Нельзя вернуть карточку в "Новый заказ". Используйте столбец "В ожидании".'
            )

        # === ПРАВИЛО: Из "В ожидании" — только в previous_column или "Выполненный проект" ===
        # Если previous_column == "Новый заказ" — разрешаем любой столбец (кроме "Новый заказ", что уже блокировано выше)
        if old_column == 'В ожидании' and new_column != 'В ожидании':
            allowed_return = card.previous_column or 'Новый заказ'
            if allowed_return != 'Новый заказ' and new_column not in [allowed_return, 'Выполненный проект']:
                raise HTTPException(
                    status_code=422,
                    detail=f'Из "В ожидании" можно вернуть только в "{allowed_return}" или "Выполненный проект".'
                )

        # === ПРАВИЛО: При переходе в "В ожидании" — сохраняем previous_column + ставим на паузу ===
        if new_column == 'В ожидании' and old_column != 'В ожидании':
            card.previous_column = old_column
            # K1: Запоминаем время постановки на паузу для пересчёта дедлайна
            card.paused_at = datetime.utcnow()

        # === ПРАВИЛО: При возврате из "В ожидании" — пересчитываем дедлайн ===
        if old_column == 'В ожидании' and new_column != 'В ожидании':
            # K1: Считаем дни паузы и сдвигаем дедлайн
            if card.paused_at:
                pause_days = _count_business_days(card.paused_at, datetime.utcnow())
                card.total_pause_days = (card.total_pause_days or 0) + pause_days
                # Сдвигаем дедлайн карточки
                if card.deadline:
                    try:
                        card.deadline = _add_working_days_to_date(card.deadline, pause_days)
                    except (ValueError, TypeError):
                        pass
                # Сдвигаем дедлайны исполнителей стадий
                executors = db.query(StageExecutor).filter(
                    StageExecutor.crm_card_id == card_id
                ).all()
                for ex in executors:
                    if ex.deadline:
                        try:
                            ex.deadline = _add_working_days_to_date(str(ex.deadline), pause_days)
                        except (ValueError, TypeError):
                            pass
                logger.info(f"K1: CRM card {card_id} resumed, pause_days={pause_days}, total={card.total_pause_days}")
            card.paused_at = None
            card.previous_column = None

        # Валидация последовательности переходов (руководство может перемещать свободно)
        free_move_roles = ['admin', 'director', 'Руководитель студии', 'Старший менеджер проектов']
        if current_user.role not in free_move_roles:
            # S-01: Порядок колонок зависит от типа проекта
            if project_type == 'Шаблонный':
                CRM_COLUMN_ORDER = [
                    'Новый заказ',
                    'Стадия 1: планировочные решения', 'Стадия 2: рабочие чертежи',
                    'Стадия 3: 3д визуализация (Дополнительная)',
                    'Выполненный проект'
                ]
            else:
                CRM_COLUMN_ORDER = [
                    'Новый заказ',
                    'Стадия 1: планировочные решения', 'Стадия 2: концепция дизайна',
                    'Стадия 3: рабочие чертежи',
                    'Выполненный проект'
                ]
            # "В ожидании" — специальная колонка, можно перемещать туда и обратно
            if old_column != 'В ожидании' and new_column != 'В ожидании':
                old_idx = CRM_COLUMN_ORDER.index(old_column) if old_column in CRM_COLUMN_ORDER else -1
                new_idx = CRM_COLUMN_ORDER.index(new_column) if new_column in CRM_COLUMN_ORDER else -1
                if old_idx >= 0 and new_idx >= 0 and abs(new_idx - old_idx) > 1:
                    raise HTTPException(
                        status_code=422,
                        detail=f"Нельзя перескакивать стадии: {old_column} → {new_column}"
                    )

        card.column_name = new_column

        # При перемещении вперёд: помечаем незаполненные подэтапы предыдущей стадии как skipped
        if old_column != new_column and new_column != 'В ожидании' and old_column != 'В ожидании':
            old_stage_group = _resolve_stage_group(old_column)
            if old_stage_group and contract:
                unfilled = db.query(ProjectTimelineEntry).filter(
                    ProjectTimelineEntry.contract_id == contract.id,
                    ProjectTimelineEntry.stage_group == old_stage_group,
                    ProjectTimelineEntry.executor_role != 'header',
                    ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ''),
                    ProjectTimelineEntry.status != 'skipped'
                ).all()
                for uf in unfilled:
                    uf.status = 'skipped'
                    uf.updated_at = datetime.utcnow()
                if unfilled:
                    logger.info(f"Card {card_id} move: {len(unfilled)} entries marked skipped in {old_stage_group}")

        # K11: Запись перемещения в историю проекта
        if old_column != new_column:
            if new_column == 'В ожидании':
                action_type = 'card_paused'
                desc = f'Карточка приостановлена (из "{old_column}")'
            elif old_column == 'В ожидании':
                action_type = 'card_resumed'
                desc = f'Карточка возобновлена (в "{new_column}")'
            else:
                action_type = 'card_moved'
                desc = f'Карточка перемещена: "{old_column}" → "{new_column}"'
            history = ActionHistory(
                user_id=current_user.id,
                action_type=action_type,
                entity_type='crm_card',
                entity_id=card_id,
                description=desc
            )
            db.add(history)

        db.commit()
        db.refresh(card)

        # Хук: автоуведомление в чат при перемещении карточки
        if old_column != new_column:
            if new_column == 'Выполненный проект':
                asyncio.create_task(trigger_messenger_notification(
                    db, card.id, 'project_end', stage_name=new_column
                ))
            elif 'Стадия' in new_column:
                asyncio.create_task(trigger_messenger_notification(
                    db, card.id, 'stage_complete', stage_name=old_column
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
        logger.exception(f"Ошибка при перемещении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/stage-executor")
async def assign_stage_executor(
    card_id: int,
    executor_data: StageExecutorCreate,
    current_user: Employee = Depends(require_permission("crm_cards.assign_executor")),
    db: Session = Depends(get_db)
):
    """Назначить исполнителя на стадию"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        executor = db.query(Employee).filter(Employee.id == executor_data.executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Исполнитель не найден")

        # Валидация stage_name по типу проекта
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        if contract:
            if contract.project_type == 'Шаблонный':
                allowed_stages = [
                    'Стадия 1: планировочные решения',
                    'Стадия 2: рабочие чертежи',
                    'Стадия 3: 3д визуализация (Дополнительная)',
                ]
            elif contract.project_type == 'Индивидуальный':
                allowed_stages = [
                    'Стадия 1: планировочные решения',
                    'Стадия 2: концепция дизайна',
                    'Стадия 3: рабочие чертежи',
                ]
            else:
                allowed_stages = None

            if allowed_stages and executor_data.stage_name not in allowed_stages:
                raise HTTPException(
                    status_code=400,
                    detail=f"Недопустимая стадия '{executor_data.stage_name}' для типа проекта '{contract.project_type}'"
                )

        # Проверка дубликата: тот же исполнитель на ту же стадию
        existing = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == executor_data.stage_name,
            StageExecutor.executor_id == executor_data.executor_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Исполнитель {executor.full_name} уже назначен на стадию '{executor_data.stage_name}'"
            )

        stage_executor = StageExecutor(
            crm_card_id=card_id,
            stage_name=executor_data.stage_name,
            executor_id=executor_data.executor_id,
            assigned_by=current_user.id,
            deadline=executor_data.deadline,
            assigned_date=datetime.utcnow()
        )

        db.add(stage_executor)

        # Аудит-лог назначения исполнителя
        activity = ActivityLog(
            employee_id=current_user.id,
            action_type="assign_executor",
            entity_type="crm_card",
            entity_id=card_id,
        )
        db.add(activity)

        # Бизнес-история назначения исполнителя
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='executor_assigned',
            entity_type='crm_card',
            entity_id=card_id,
            description=f'Назначен исполнитель: {executor.full_name} на стадию «{executor_data.stage_name}»'
            + (f', дедлайн: {executor_data.deadline}' if executor_data.deadline else '')
        ))

        db.commit()
        db.refresh(stage_executor)

        return {
            'id': stage_executor.id,
            'crm_card_id': stage_executor.crm_card_id,
            'stage_name': stage_executor.stage_name,
            'executor_id': stage_executor.executor_id,
            'executor_name': executor.full_name,
            'assigned_by': stage_executor.assigned_by,
            'assigned_date': stage_executor.assigned_date.isoformat(),
            'deadline': str(stage_executor.deadline) if stage_executor.deadline else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при назначении исполнителя стадии: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/stage-executor/{stage_name}")
async def complete_stage(
    card_id: int,
    stage_name: str,
    update_data: StageExecutorUpdate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить статус выполнения стадии"""
    try:
        # Проверка прав: только назначенные на карточку сотрудники, исполнители стадий или суперпользователи
        from permissions import SUPERUSER_ROLES
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        is_card_member = current_user.id in [
            card.senior_manager_id, card.sdp_id, card.gap_id, card.manager_id
        ]
        is_stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.executor_id == current_user.id
        ).first() is not None
        is_superuser = current_user.role in SUPERUSER_ROLES

        if not (is_card_member or is_stage_executor or is_superuser):
            raise HTTPException(
                status_code=403,
                detail="Недостаточно прав для завершения стадии"
            )

        stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name
        ).order_by(StageExecutor.id.desc()).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail=f"Назначение стадии не найдено: card_id={card_id}, stage_name={stage_name}")

        update_dict = update_data.model_dump(exclude_unset=True)

        # Простое обновление всех полей
        for field, value in update_dict.items():
            setattr(stage_executor, field, value)

        if update_data.completed and not update_data.completed_date:
            stage_executor.completed_date = datetime.utcnow()

        # Бизнес-история изменения стадии
        if update_data.completed:
            executor_emp = db.query(Employee).filter(Employee.id == stage_executor.executor_id).first()
            executor_name = executor_emp.full_name if executor_emp else f'ID {stage_executor.executor_id}'
            db.add(ActionHistory(
                user_id=current_user.id,
                action_type='stage_completed',
                entity_type='crm_card',
                entity_id=card_id,
                description=f'Стадия завершена: «{stage_name}», исполнитель: {executor_name}'
            ))

        db.commit()
        db.refresh(stage_executor)

        return {
            'id': stage_executor.id,
            'crm_card_id': stage_executor.crm_card_id,
            'stage_name': stage_executor.stage_name,
            'executor_id': stage_executor.executor_id,
            'completed': stage_executor.completed,
            'completed_date': stage_executor.completed_date.isoformat() if stage_executor.completed_date else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении стадии CRM: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/cards/{card_id}")
async def delete_crm_card(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.delete")),
    db: Session = Depends(get_db)
):
    """Удалить CRM карточку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Удаляем связанные stage_executors
        db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).delete()

        # Удаляем связанные платежи
        db.query(Payment).filter(Payment.crm_card_id == card_id).delete()

        # Удаляем дедлайны стадий согласования
        db.query(ApprovalStageDeadline).filter(
            ApprovalStageDeadline.crm_card_id == card_id
        ).delete()

        # Удаляем записи timeline проекта (по contract_id карточки)
        if card.contract_id:
            db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == card.contract_id
            ).delete()

        # Удаляем историю действий
        db.query(ActionHistory).filter(
            ActionHistory.entity_type.in_(['crm_card', 'stage', 'stage_executor']),
            ActionHistory.entity_id == card_id
        ).delete(synchronize_session='fetch')

        # Удаляем привязанные чаты мессенджера
        db.query(MessengerChat).filter(
            MessengerChat.crm_card_id == card_id
        ).delete()

        # Лог перед удалением
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="delete",
            entity_type="crm_card",
            entity_id=card_id
        )
        db.add(log)

        db.delete(card)
        db.commit()

        return {"status": "success", "message": "CRM карточка удалена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/stage-executors/{executor_id}")
async def delete_stage_executor(
    executor_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.delete_executor")),
    db: Session = Depends(get_db)
):
    """Удалить назначение исполнителя на стадию"""
    try:
        executor = db.query(StageExecutor).filter(StageExecutor.id == executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Назначение не найдено")

        # Лог перед удалением
        log = ActivityLog(
            employee_id=current_user.id,
            action_type="delete",
            entity_type="stage_executor",
            entity_id=executor_id
        )
        db.add(log)

        # Бизнес-история удаления исполнителя
        executor_emp = db.query(Employee).filter(Employee.id == executor.executor_id).first()
        executor_name = executor_emp.full_name if executor_emp else f'ID {executor.executor_id}'
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='executor_deleted',
            entity_type='crm_card',
            entity_id=executor.crm_card_id,
            description=f'Удалён исполнитель: {executor_name} со стадии «{executor.stage_name}»'
        ))

        db.delete(executor)
        db.commit()

        return {"status": "success", "message": "Назначение исполнителя удалено"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении назначения исполнителя: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =========================
# CRM RESET ENDPOINTS
# =========================

@router.post("/cards/{card_id}/reset-stages")
async def reset_crm_card_stages(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.reset_stages")),
    db: Session = Depends(get_db)
):
    """Сбросить выполнение стадий карточки"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Сбрасываем все stage_executors
        stage_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).all()
        for se in stage_executors:
            se.completed = False
            se.completed_date = None
            se.submitted_date = None

        # Бизнес-история сброса стадий
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='stages_reset',
            entity_type='crm_card',
            entity_id=card_id,
            description=f'Сброшены все стадии ({len(stage_executors)} исполнителей)'
        ))

        db.commit()

        return {"status": "success", "message": "Стадии сброшены", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе стадий CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/reset-stage-by-name")
async def reset_crm_card_stage_by_name(
    card_id: int,
    stage_names: List[str] = Query(..., description="Имена стадий (column_name) для каскадного сброса"),
    current_user: Employee = Depends(require_permission("crm_cards.reset_stages")),
    db: Session = Depends(get_db)
):
    """Каскадный сброс стадий карточки — сбрасывает все указанные стадии (от выбранной и далее)"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Сбрасываем StageExecutor для всех указанных стадий
        stage_executors = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name.in_(stage_names)
        ).all()

        reset_count = 0
        for se in stage_executors:
            se.completed = False
            se.completed_date = None
            se.submitted_date = None
            reset_count += 1

        # Сбрасываем согласование (если возвращаем на стадию — согласование неактуально)
        card.is_approved = False
        card.approval_stages = None
        card.approval_deadline = None

        # Бизнес-история каскадного сброса стадий
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='stages_reset',
            entity_type='crm_card',
            entity_id=card_id,
            description=f'Каскадный сброс стадий: {", ".join(stage_names)} ({reset_count} исполнителей)'
        ))

        db.commit()

        return {
            "status": "success",
            "message": f"Сброшено {len(stage_names)} стадий ({reset_count} исполнителей)",
            "card_id": card_id,
            "stage_names": stage_names,
            "reset_count": reset_count,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при каскадном сбросе стадий CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/reset-approval")
async def reset_crm_card_approval(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.reset_approval")),
    db: Session = Depends(get_db)
):
    """Сбросить стадии согласования карточки"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Сбрасываем согласования
        card.is_approved = False
        card.approval_stages = None
        card.approval_deadline = None

        # Бизнес-история сброса согласований
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='approval_reset',
            entity_type='crm_card',
            entity_id=card_id,
            description='Сброшены все стадии согласования'
        ))

        db.commit()

        return {"status": "success", "message": "Согласования сброшены", "card_id": card_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе согласований CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =========================
# CRM SUBMITTED/HISTORY
# =========================

@router.get("/cards/{card_id}/submitted-stages")
async def get_submitted_stages(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить отправленные стадии карточки"""
    stages = db.query(StageExecutor).filter(
        StageExecutor.crm_card_id == card_id,
        StageExecutor.submitted_date != None
    ).all()

    return [{
        'id': s.id,
        'stage_name': s.stage_name,
        'executor_id': s.executor_id,
        'executor_name': s.executor.full_name if s.executor else None,
        'submitted_date': s.submitted_date.isoformat() if s.submitted_date else None,
        'completed': s.completed,
        'completed_date': s.completed_date.isoformat() if s.completed_date else None,
    } for s in stages]


@router.get("/cards/{card_id}/stage-history")
async def get_stage_history(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить историю стадий карточки (stage executors с именами сотрудников)"""
    executors = db.query(StageExecutor).filter(
        StageExecutor.crm_card_id == card_id
    ).order_by(StageExecutor.assigned_date.asc()).all()

    result = []
    for se in executors:
        executor_name = 'Не назначен'
        if se.executor:
            executor_name = se.executor.full_name or 'Не назначен'

        assigned_by_name = None
        if se.assigned_by:
            assigner = db.query(Employee).filter(Employee.id == se.assigned_by).first()
            assigned_by_name = assigner.full_name if assigner else None

        result.append({
            'stage_name': se.stage_name,
            'executor_name': executor_name,
            'assigned_by_name': assigned_by_name,
            'assigned_date': se.assigned_date.isoformat() if se.assigned_date else None,
            'deadline': se.deadline,
            'submitted_date': se.submitted_date.isoformat() if se.submitted_date else None,
            'completed': se.completed,
            'completed_date': se.completed_date.isoformat() if se.completed_date else None,
        })

    return result


# =========================
# WORKFLOW ENDPOINTS (CRM)
# =========================

def _server_recalculate_actual_days(db, contract_id: int):
    """Пересчёт actual_days (рабочие дни между последовательными actual_date) на сервере.
    Аналог _recalculate_days() из timeline_widget.py, но серверный."""
    from utils.date_utils import networkdays as _nwd
    entries = db.query(ProjectTimelineEntry).filter(
        ProjectTimelineEntry.contract_id == contract_id,
        ProjectTimelineEntry.executor_role != 'header'
    ).order_by(ProjectTimelineEntry.sort_order).all()

    prev_date = None
    for entry in entries:
        actual_date = entry.actual_date
        if actual_date and prev_date:
            try:
                days = _nwd(prev_date, actual_date)
                entry.actual_days = max(days, 0)
            except Exception:
                entry.actual_days = 0
        else:
            if not actual_date:
                entry.actual_days = 0
        if actual_date:
            prev_date = actual_date


def _update_executor_deadline_for_next_substep(db, card_id: int, stage_name: str, contract_id: int):
    """Обновить дедлайн исполнителя стадии по norm_days следующего незаполненного подэтапа.

    Вызывается после каждого workflow-действия (submit/accept/reject/client-ok),
    чтобы дедлайн на карточке канбана всегда отражал текущий подэтап.
    Пример: подэтап «Чертёж» 4 дня → сдал → подэтап «Проверка СДП» 2 дня → дедлайн = today+2.
    """
    stage_group = _resolve_stage_group(stage_name)
    if not stage_group or not contract_id:
        return

    # Первый незаполненный подэтап с norm_days > 0 (не skipped, не header)
    next_entry = db.query(ProjectTimelineEntry).filter(
        ProjectTimelineEntry.contract_id == contract_id,
        ProjectTimelineEntry.stage_group == stage_group,
        ProjectTimelineEntry.executor_role != 'header',
        (ProjectTimelineEntry.actual_date.is_(None)) | (ProjectTimelineEntry.actual_date == ''),
        ProjectTimelineEntry.status != 'skipped',
        ProjectTimelineEntry.norm_days > 0
    ).order_by(ProjectTimelineEntry.sort_order).first()

    if not next_entry:
        # Все подэтапы стадии заполнены — стадия завершена, дедлайн не нужен
        return

    # Фаза 4: Если следующий подэтап вне расчёта срока (is_in_contract_scope=False),
    # дедлайн приостанавливается (клиентские этапы, сбор правок и т.п.)
    if not getattr(next_entry, 'is_in_contract_scope', True):
        logger.info(
            f"[Deadline] Пауза: card={card_id}, подэтап «{next_entry.stage_name}» "
            f"вне расчёта срока — дедлайн не обновляется"
        )
        return

    # norm_days с учётом custom_norm_days (если менеджер изменил)
    norm = next_entry.norm_days or 0
    if next_entry.custom_norm_days and next_entry.custom_norm_days > 0:
        norm = next_entry.custom_norm_days
    if norm <= 0:
        return

    # База для расчёта: последняя actual_date перед этим подэтапом (сквозная)
    prev_filled = db.query(ProjectTimelineEntry).filter(
        ProjectTimelineEntry.contract_id == contract_id,
        ProjectTimelineEntry.executor_role != 'header',
        ProjectTimelineEntry.sort_order < next_entry.sort_order,
        ProjectTimelineEntry.actual_date.isnot(None),
        ProjectTimelineEntry.actual_date != ''
    ).order_by(ProjectTimelineEntry.sort_order.desc()).first()

    base_date_str = prev_filled.actual_date if prev_filled else datetime.utcnow().strftime('%Y-%m-%d')

    # Рассчитываем новый дедлайн через _add_business_days (серверная, без PyQt5)
    new_deadline_dt = _add_business_days(base_date_str, norm)
    new_deadline = new_deadline_dt.strftime('%Y-%m-%d')

    # Обновляем StageExecutor.deadline
    stage_executor = db.query(StageExecutor).filter(
        StageExecutor.crm_card_id == card_id,
        StageExecutor.stage_name == stage_name
    ).order_by(StageExecutor.id.desc()).first()

    if stage_executor and stage_executor.deadline != new_deadline:
        old_deadline = stage_executor.deadline or 'не установлен'
        stage_executor.deadline = new_deadline
        logger.info(
            f"[Deadline] Обновлён: card={card_id}, стадия={stage_name}, "
            f"подэтап=«{next_entry.stage_name}», {old_deadline} → {new_deadline} "
            f"(norm={norm} раб.дн.)"
        )


def _resolve_stage_group(column_name: str) -> str:
    """Определить stage_group по имени колонки канбана.
    Маппинг гибкий: ищет паттерны 'стадия N' в названии колонки.
    """
    col = column_name.lower()
    # Универсальный маппинг: 'стадия N' → STAGEN
    import re
    m = re.search(r'стадия\s*(\d+)', col)
    if m:
        return f'STAGE{m.group(1)}'
    # Альтернативные маппинги для других названий колонок
    if 'планировочн' in col:
        return 'STAGE1'
    elif 'концепция' in col or 'дизайн' in col:
        return 'STAGE2'
    elif 'чертеж' in col or 'чертёж' in col:
        return 'STAGE3'
    return ''


@router.get("/cards/{card_id}/workflow/state")
async def get_workflow_state(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить текущее состояние рабочего процесса карточки"""
    states = db.query(StageWorkflowState).filter(
        StageWorkflowState.crm_card_id == card_id
    ).all()
    return [
        {c.name: getattr(s, c.name) for c in s.__table__.columns}
        for s in states
    ]


@router.post("/cards/{card_id}/workflow/submit")
async def workflow_submit_work(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сдача работы исполнителем — записывает дату в timeline.
    Ищет строку по executor_role (Чертежник/Дизайнер/ГАП), а не просто первую пустую."""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка не найдена")

        contract_id = card.contract_id
        stage_name = card.column_name

        stage_group = _resolve_stage_group(stage_name)
        if not stage_group:
            return {"status": "no_stage_group"}

        # Роли исполнителей (те, кто нажимает "Сдать работу")
        executor_roles = ['Чертежник', 'Дизайнер', 'ГАП']

        entry = db.query(ProjectTimelineEntry).filter(
            ProjectTimelineEntry.contract_id == contract_id,
            ProjectTimelineEntry.stage_group == stage_group,
            ProjectTimelineEntry.executor_role.in_(executor_roles),
            ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
        ).order_by(ProjectTimelineEntry.sort_order).first()

        if entry:
            entry.actual_date = datetime.utcnow().strftime('%Y-%m-%d')
            entry.updated_at = datetime.utcnow()
            _server_recalculate_actual_days(db, contract_id)

        # Обновляем workflow state
        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == card_id,
            StageWorkflowState.stage_name == stage_name
        ).first()
        if not wf:
            wf = StageWorkflowState(
                crm_card_id=card_id,
                stage_name=stage_name,
                current_substep_code=entry.stage_code if entry else None,
                status='in_progress'
            )
            db.add(wf)
        wf.current_substep_code = entry.stage_code if entry else wf.current_substep_code
        wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(
            user_id=current_user.id, action_type='work_submitted',
            entity_type='crm_card', entity_id=card_id,
            description=f'Сдача работы: {stage_name} ({entry.stage_name if entry else ""})'
        ))

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        db.commit()

        # Хук: уведомление в чат о сдаче работы
        asyncio.create_task(trigger_messenger_notification(
            db, card_id, 'stage_complete', stage_name=stage_name
        ))

        return {"status": "submitted", "substep": entry.stage_code if entry else None}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/submit: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/accept")
async def workflow_accept_work(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.move")),
    db: Session = Depends(get_db)
):
    """Приемка работы — записывает дату проверки в timeline.
    Ищет строку по executor_role (СДП/Менеджер), а не просто первую пустую."""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка не найдена")

        contract_id = card.contract_id
        stage_name = card.column_name
        stage_group = _resolve_stage_group(stage_name)

        # Роли проверяющих (те, кто нажимает "Принять работу")
        reviewer_roles = ['СДП', 'Менеджер']

        if stage_group:
            entry = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role.in_(reviewer_roles),
                ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
            ).order_by(ProjectTimelineEntry.sort_order).first()

            if entry:
                entry.actual_date = datetime.utcnow().strftime('%Y-%m-%d')
                entry.updated_at = datetime.utcnow()
                _server_recalculate_actual_days(db, contract_id)

        # Устанавливаем submitted_date у завершённых исполнителей текущей стадии
        stage_executors = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name,
            StageExecutor.completed == True,
            StageExecutor.submitted_date.is_(None)
        ).all()
        for se in stage_executors:
            se.submitted_date = datetime.utcnow()

        # Обновляем workflow state
        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == card_id,
            StageWorkflowState.stage_name == stage_name
        ).first()
        if wf:
            wf.status = 'in_progress'
            wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(
            user_id=current_user.id, action_type='work_accepted',
            entity_type='crm_card', entity_id=card_id,
            description=f'Работа принята: {stage_name}'
        ))

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        db.commit()
        return {"status": "accepted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/accept: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/reject")
async def workflow_reject_work(
    card_id: int,
    request: Request,
    current_user: Employee = Depends(require_permission("crm_cards.move")),
    db: Session = Depends(get_db)
):
    """Отправить на исправление — обновляет workflow state и сбрасывает completed.
    Записывает дату проверки СДП в timeline (первый незаполненный подэтап).
    Опционально принимает revision_file_path (путь к папке правок на ЯД)."""
    try:
        body = {}
        try:
            body = await request.json()
        except Exception:
            pass
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка не найдена")

        stage_name = card.column_name
        contract_id = card.contract_id
        revision_file_path = body.get('revision_file_path', '')

        # Записываем дату проверки СДП в timeline (ищем по роли СДП/Менеджер)
        stage_group = _resolve_stage_group(stage_name)
        reviewer_roles = ['СДП', 'Менеджер']
        if stage_group and contract_id:
            entry = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role.in_(reviewer_roles),
                ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
            ).order_by(ProjectTimelineEntry.sort_order).first()
            if entry:
                entry.actual_date = datetime.utcnow().strftime('%Y-%m-%d')
                entry.updated_at = datetime.utcnow()
                _server_recalculate_actual_days(db, contract_id)

        # Сбрасываем completed у исполнителя текущей стадии
        # чтобы он увидел кнопку "Сдать работу" снова
        executors = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.completed == True
        ).all()
        for ex in executors:
            # С2: Точное совпадение stage_name (вместо нечёткого ILIKE-подобного)
            if ex.stage_name and ex.stage_name == stage_name:
                ex.completed = False
                ex.completed_date = None

        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == card_id,
            StageWorkflowState.stage_name == stage_name
        ).first()
        if not wf:
            wf = StageWorkflowState(
                crm_card_id=card_id,
                stage_name=stage_name,
                status='revision',
                revision_count=1,
                revision_file_path=revision_file_path or None
            )
            db.add(wf)
        else:
            wf.status = 'revision'
            wf.revision_count = (wf.revision_count or 0) + 1
            if revision_file_path:
                wf.revision_file_path = revision_file_path
            wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(
            user_id=current_user.id, action_type='work_rejected',
            entity_type='crm_card', entity_id=card_id,
            description=f'Отправлено на правки: {stage_name} (итерация {wf.revision_count})'
        ))

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа (переделка)
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        db.commit()
        return {"status": "rejected", "revision_count": wf.revision_count, "revision_file_path": wf.revision_file_path}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/reject: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/client-send")
async def workflow_client_send(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.move")),
    db: Session = Depends(get_db)
):
    """Отправить на согласование клиенту — приостанавливает дедлайн.
    НЕ записывает дату в клиентскую строку — дата записывается при client-ok (согласовано).
    Помечает промежуточные пустые строки как skipped."""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    stage_name = card.column_name
    contract_id = card.contract_id
    stage_group = _resolve_stage_group(stage_name)

    deadline_str = ''
    if stage_group:
        # Находим первую незаполненную клиентскую строку
        client_entry = db.query(ProjectTimelineEntry).filter(
            ProjectTimelineEntry.contract_id == contract_id,
            ProjectTimelineEntry.stage_group == stage_group,
            ProjectTimelineEntry.executor_role == 'Клиент',
            ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
        ).order_by(ProjectTimelineEntry.sort_order).first()

        if client_entry:
            # Помечаем незаполненные НЕ-клиентские подэтапы до клиентского как пропущенные
            skipped_entries = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role.notin_(['header', 'Клиент']),
                ProjectTimelineEntry.sort_order < client_entry.sort_order,
                ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == '')
            ).all()
            for se in skipped_entries:
                se.status = 'skipped'
                se.updated_at = datetime.utcnow()

            # НЕ записываем дату — она запишется при client-ok (согласовано)
            # Считаем дедлайн согласования для уведомления
            norm_days = client_entry.norm_days or 3
            prev_entry = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.sort_order < client_entry.sort_order,
                ProjectTimelineEntry.actual_date.isnot(None),
                ProjectTimelineEntry.actual_date != ''
            ).order_by(ProjectTimelineEntry.sort_order.desc()).first()

            if prev_entry and prev_entry.actual_date:
                try:
                    deadline_date = _add_business_days(prev_entry.actual_date, norm_days)
                    deadline_str = deadline_date.strftime('%d.%m.%Y')
                except Exception:
                    pass

    wf = db.query(StageWorkflowState).filter(
        StageWorkflowState.crm_card_id == card_id,
        StageWorkflowState.stage_name == stage_name
    ).first()
    if not wf:
        wf = StageWorkflowState(
            crm_card_id=card_id,
            stage_name=stage_name,
            status='client_approval',
            client_approval_started_at=datetime.utcnow(),
            client_approval_deadline_paused=True
        )
        db.add(wf)
    else:
        wf.status = 'client_approval'
        wf.client_approval_started_at = datetime.utcnow()
        wf.client_approval_deadline_paused = True
        wf.updated_at = datetime.utcnow()

    # K11: Запись в историю
    db.add(ActionHistory(
        user_id=current_user.id, action_type='client_send',
        entity_type='crm_card', entity_id=card_id,
        description=f'Отправлено клиенту: {stage_name}'
    ))

    db.commit()

    # Хук: уведомление в чат об отправке клиенту (с дедлайном)
    asyncio.create_task(trigger_messenger_notification(
        db, card_id, 'stage_complete', stage_name=f"{stage_name} (отправлено клиенту)",
        extra_context={'deadline': deadline_str} if deadline_str else None
    ))

    return {"status": "sent_to_client"}


@router.post("/cards/{card_id}/workflow/client-ok")
async def workflow_client_approved(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.complete_approval")),
    db: Session = Depends(get_db)
):
    """Клиент согласовал — записывает дату в клиентскую строку Отправка/Согласование.
    Также записывает дату в следующую строку «Сбор правок» (роль СДП/Менеджер)."""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    try:
        stage_name = card.column_name
        contract_id = card.contract_id

        stage_group = _resolve_stage_group(stage_name)
        if stage_group and contract_id:
            # Записываем дату в клиентскую строку "Отправка клиенту / Согласование"
            client_entry = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role == 'Клиент',
                or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == '')
            ).order_by(ProjectTimelineEntry.sort_order).first()
            if client_entry:
                client_entry.actual_date = datetime.utcnow().strftime('%Y-%m-%d')
                client_entry.updated_at = datetime.utcnow()
            _server_recalculate_actual_days(db, contract_id)

        wf = db.query(StageWorkflowState).filter(
            StageWorkflowState.crm_card_id == card_id,
            StageWorkflowState.stage_name == stage_name
        ).first()
        if wf:
            # K7: Пересчёт дедлайна — считаем дни паузы на согласовании клиента
            if wf.client_approval_deadline_paused and wf.client_approval_started_at:
                approval_pause_days = (datetime.utcnow() - wf.client_approval_started_at).days
                if approval_pause_days > 0 and card.deadline:
                    try:
                        dl = datetime.strptime(card.deadline, '%Y-%m-%d')
                        dl += timedelta(days=approval_pause_days)
                        card.deadline = dl.strftime('%Y-%m-%d')
                        card.total_pause_days = (card.total_pause_days or 0) + approval_pause_days
                        logger.info(f"K7: Client approval pause {approval_pause_days} days, card {card_id}")
                    except (ValueError, TypeError):
                        pass

                # Сдвигаем дедлайны исполнителей стадий
                if approval_pause_days > 0:
                    executors = db.query(StageExecutor).filter(
                        StageExecutor.crm_card_id == card_id
                    ).all()
                    for ex in executors:
                        if ex.deadline:
                            try:
                                ex_dl = datetime.strptime(str(ex.deadline), '%Y-%m-%d')
                                ex_dl += timedelta(days=approval_pause_days)
                                ex.deadline = ex_dl.strftime('%Y-%m-%d')
                            except (ValueError, TypeError):
                                pass

            wf.status = 'in_progress'
            wf.client_approval_deadline_paused = False
            wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(
            user_id=current_user.id, action_type='client_approved',
            entity_type='crm_card', entity_id=card_id,
            description=f'Клиент согласовал: {stage_name}'
        ))

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        db.commit()

        # Хук: уведомление в чат о согласовании клиентом
        try:
            asyncio.create_task(trigger_messenger_notification(
                db, card_id, 'stage_complete', stage_name=f"{stage_name} (клиент согласовал)"
            ))
        except Exception:
            logger.warning(f"Не удалось отправить уведомление для карточки {card_id}")

        return {"status": "client_approved"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при согласовании клиентом карточки {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при согласовании: {str(e)}")


# =========================
# CRM EXTENDED ENDPOINTS (Designer/Draftsman Reset)
# =========================

@router.post("/cards/{card_id}/reset-designer")
async def reset_designer_completion(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.reset_designer")),
    db: Session = Depends(get_db)
):
    """Сбросить отметку о завершении дизайнером"""
    try:
        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлен поиск по '3д визуализация' для шаблонных проектов (#10)
        designer_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            or_(
                StageExecutor.stage_name.ilike('%концепция%'),
                StageExecutor.stage_name.ilike('%визуализация%')
            )
        ).order_by(StageExecutor.id.desc()).first()

        if designer_executor:
            designer_executor.completed = False
            designer_executor.completed_date = None

            # Бизнес-история сброса дизайнера
            executor_emp = db.query(Employee).filter(Employee.id == designer_executor.executor_id).first()
            executor_name = executor_emp.full_name if executor_emp else f'ID {designer_executor.executor_id}'
            db.add(ActionHistory(
                user_id=current_user.id,
                action_type='designer_reset',
                entity_type='crm_card',
                entity_id=card_id,
                description=f'Сброшена отметка дизайнера: {executor_name}, стадия «{designer_executor.stage_name}»'
            ))

            db.commit()

        return {"status": "success", "message": "Отметка дизайнера сброшена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе отметки дизайнера: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/reset-draftsman")
async def reset_draftsman_completion(
    card_id: int,
    current_user: Employee = Depends(require_permission("crm_cards.reset_draftsman")),
    db: Session = Depends(get_db)
):
    """Сбросить отметку о завершении чертежником"""
    try:

        # Находим назначение чертежника
        draftsman_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            or_(
                StageExecutor.stage_name.ilike('%чертежи%'),
                StageExecutor.stage_name.ilike('%планировочные%')
            )
        ).order_by(StageExecutor.id.desc()).first()

        if draftsman_executor:
            draftsman_executor.completed = False
            draftsman_executor.completed_date = None

            # Бизнес-история сброса чертёжника
            executor_emp = db.query(Employee).filter(Employee.id == draftsman_executor.executor_id).first()
            executor_name = executor_emp.full_name if executor_emp else f'ID {draftsman_executor.executor_id}'
            db.add(ActionHistory(
                user_id=current_user.id,
                action_type='draftsman_reset',
                entity_type='crm_card',
                entity_id=card_id,
                description=f'Сброшена отметка чертёжника: {executor_name}, стадия «{draftsman_executor.stage_name}»'
            ))

            db.commit()

        return {"status": "success", "message": "Отметка чертежника сброшена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе отметки чертежника: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/approval-deadlines")
async def get_approval_stage_deadlines(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить дедлайны стадий согласования"""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM карточка не найдена")

    # Возвращаем данные о согласовании
    return {
        'card_id': card_id,
        'is_approved': card.is_approved,
        'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
        'approval_stages': json.loads(card.approval_stages) if card.approval_stages else None
    }


@router.post("/cards/{card_id}/complete-approval-stage")
async def complete_approval_stage(
    card_id: int,
    body: CompleteApprovalStageRequest,
    current_user: Employee = Depends(require_permission("crm_cards.complete_approval")),
    db: Session = Depends(get_db)
):
    """Завершить стадию согласования"""
    try:
        stage_name = body.stage_name

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Обновляем approval_stages (JSON)
        current_stages = json.loads(card.approval_stages) if card.approval_stages else {}
        current_stages[stage_name] = {
            'completed': True,
            'completed_date': datetime.utcnow().isoformat(),
            'completed_by': current_user.id
        }
        card.approval_stages = json.dumps(current_stages)

        # Авто-установка is_approved когда текущая стадия согласована
        if stage_name == card.column_name:
            card.is_approved = True

        # Бизнес-история завершения согласования
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='approval_completed',
            entity_type='crm_card',
            entity_id=card_id,
            description=f'Завершена стадия согласования: «{stage_name}»'
            + (' (карточка согласована)' if card.is_approved else '')
        ))

        db.commit()

        return {
            "status": "success",
            "stage_name": stage_name,
            "completed": True,
            "is_approved": card.is_approved
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при завершении стадии согласования: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/stage-executor-deadline")
async def update_stage_executor_deadline(
    card_id: int,
    body: StageExecutorDeadlineRequest,
    current_user: Employee = Depends(require_permission("crm_cards.deadlines")),
    db: Session = Depends(get_db)
):
    """Обновить дедлайн исполнителя стадии"""
    try:
        stage_name = body.stage_name
        deadline = body.deadline

        # С1: Точное совпадение stage_name вместо ILIKE
        stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name
        ).order_by(StageExecutor.id.desc()).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail="Назначение стадии не найдено")

        from datetime import datetime as dt
        old_deadline = str(stage_executor.deadline) if stage_executor.deadline else 'не установлен'
        stage_executor.deadline = dt.fromisoformat(deadline).date() if deadline else None
        new_deadline = deadline if deadline else 'снят'

        # Бизнес-история изменения дедлайна
        executor_emp = db.query(Employee).filter(Employee.id == stage_executor.executor_id).first()
        executor_name = executor_emp.full_name if executor_emp else f'ID {stage_executor.executor_id}'
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='deadline_changed',
            entity_type='crm_card',
            entity_id=card_id,
            description=f'Изменён дедлайн: «{stage_name}», исполнитель: {executor_name}, {old_deadline} → {new_deadline}'
        ))

        db.commit()

        return {"status": "success", "stage_name": stage_executor.stage_name, "deadline": deadline}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении дедлайна исполнителя стадии: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/stage-executor/{stage_name}/complete")
async def complete_stage_for_executor(
    card_id: int,
    stage_name: str,
    body: CompleteStageExecutorRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Отметить стадию как выполненную для исполнителя"""
    try:
        executor_id = body.executor_id

        # Проверка прав: назначенный на карточку, исполнитель стадии или суперпользователь
        from permissions import SUPERUSER_ROLES
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")
        is_card_member = current_user.id in [
            card.senior_manager_id, card.sdp_id, card.gap_id, card.manager_id
        ]
        is_stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.executor_id == current_user.id
        ).first() is not None
        is_superuser = current_user.role in SUPERUSER_ROLES
        if not (is_card_member or is_stage_executor or is_superuser):
            raise HTTPException(status_code=403, detail="Недостаточно прав для завершения стадии")

        stage_executor = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name,
            StageExecutor.executor_id == executor_id
        ).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail=f"Назначение стадии не найдено: card_id={card_id}, stage_name={stage_name}, executor_id={executor_id}")

        stage_executor.completed = True
        stage_executor.completed_date = datetime.utcnow()

        # Бизнес-история завершения стадии исполнителем
        executor_emp = db.query(Employee).filter(Employee.id == executor_id).first()
        executor_name = executor_emp.full_name if executor_emp else f'ID {executor_id}'
        db.add(ActionHistory(
            user_id=current_user.id,
            action_type='executor_completed',
            entity_type='crm_card',
            entity_id=card_id,
            description=f'Исполнитель завершил стадию: {executor_name}, «{stage_name}»'
        ))

        db.commit()

        return {"status": "success", "stage_name": stage_name, "completed": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при завершении стадии исполнителем: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/previous-executor")
async def get_previous_executor_by_position(
    card_id: int,
    position: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить предыдущего исполнителя по должности"""
    try:
        # Находим назначение для этой должности
        stage_executors = db.query(StageExecutor).filter(
            StageExecutor.crm_card_id == card_id
        ).order_by(StageExecutor.id.desc()).all()

        for se in stage_executors:
            employee = db.query(Employee).filter(Employee.id == se.executor_id).first()
            if employee and employee.position == position:
                return {'executor_id': se.executor_id, 'executor_name': employee.full_name}

        return {'executor_id': None}

    except Exception as e:
        logger.exception(f"Ошибка при получении предыдущего исполнителя по должности: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/manager-acceptance")
async def save_manager_acceptance(
    card_id: int,
    body: ManagerAcceptanceRequest,
    current_user: Employee = Depends(require_permission("crm_cards.move")),
    db: Session = Depends(get_db)
):
    """Сохранить принятие работы менеджером.
    K3: Фасадный endpoint — только записывает ActionHistory.
    Обновление StageExecutor.completed и ProjectTimelineEntry.actual_date
    выполняется на стороне UI (crm_tab.py)."""
    try:
        stage_name = body.stage_name
        executor_name = body.executor_name
        # Используем current_user.id вместо body.manager_id для безопасности
        manager_id = current_user.id

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Добавляем запись в историю действий
        history = ActionHistory(
            user_id=manager_id,
            action_type='acceptance',
            entity_type='stage',
            entity_id=card_id,
            description=f'Принятие работы: {stage_name} от {executor_name}'
        )
        db.add(history)
        db.commit()

        return {"status": "success", "stage_name": stage_name, "accepted_by": manager_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сохранении приемки менеджера: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/accepted-stages")
async def get_accepted_stages(
    card_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список принятых стадий"""
    history = db.query(ActionHistory).filter(
        ActionHistory.entity_type == 'stage',
        ActionHistory.entity_id == card_id,
        ActionHistory.action_type == 'acceptance'
    ).all()

    return [{
        'id': h.id,
        'stage_name': h.description,
        'accepted_by': h.user_id,
        'accepted_date': h.action_date.isoformat() if h.action_date else None
    } for h in history]
