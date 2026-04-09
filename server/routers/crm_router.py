"""
Роутер CRM-карточек и Workflow.
Подключается в main.py через app.include_router(crm_router, prefix="/api/crm").
"""

import asyncio
from datetime import datetime, timedelta
import json
import logging
from typing import List, Optional

from auth import get_current_user
from constants import (
    ARCHIVE_STATUSES,
    FREE_MOVE_ROLES,
    POSITION_DAN,
    POSITION_DESIGNER,
    POSITION_DRAFTSMAN,
    POSITION_GAP,
    POSITION_MANAGER,
    POSITION_MEASURER,
    POSITION_SDP,
    POSITION_SENIOR_MANAGER,
    POSITION_STUDIO_DIRECTOR,
    REVIEWER_ROLES,
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from permissions import require_permission
from routers.payments_router import auto_create_employee_payment
from schemas import (
    ActionHistoryResponse,
    ColumnMoveRequest,
    CompleteApprovalStageRequest,
    CompleteStageExecutorRequest,
    CRMCardCreate,
    CRMCardResponse,
    CRMCardUpdate,
    ManagerAcceptanceRequest,
    StageExecutorCreate,
    StageExecutorDeadlineRequest,
    StageExecutorResponse,
    StageExecutorUpdate,
    SupervisionHistoryResponse,
)
from services.notification_dispatcher import dispatch_notification
from services.notification_service import send_survey_to_chat, trigger_messenger_notification
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import (
    ActionHistory,
    ActivityLog,
    ApprovalStageDeadline,
    Client,
    Contract,
    CRMCard,
    Employee,
    MessengerChat,
    Payment,
    ProjectFile,
    ProjectTimelineEntry,
    SessionLocal,
    StageExecutor,
    StageWorkflowState,
    SupervisionCard,
    get_db,
)


def _get_project_type_key(project_type: str) -> str:
    """Преобразовать тип проекта БД в ключ для dispatch_notification."""
    if not project_type:
        return "individual"
    pt = project_type.lower()
    if "шабл" in pt:
        return "template"
    if "надзор" in pt:
        return "supervision"
    return "individual"


def _find_executor_id(db: Session, card_id: int, stage_name: str) -> Optional[int]:
    """Найти ID исполнителя стадии через StageExecutor."""
    executor = (
        db.query(StageExecutor)
        .filter(
            StageExecutor.crm_card_id == card_id,
            StageExecutor.stage_name == stage_name,
        )
        .first()
    )
    return executor.executor_id if executor else None


def _extract_stage_number(stage_name: str) -> str:
    """Извлечь номер стадии из названия колонки.
    'Стадия 2: концепция дизайна' → '2'
    """
    import re

    m = re.search(r"[Сс]тадия\s*(\d+)", stage_name)
    return m.group(1) if m else ""


def _get_substage_concept(current_subgroup: str) -> str:
    """Определить концепцию подэтапа Стадии 2 инд.
    Подэтап 2.2/2.3/2.4 → 'мудборд'
    Подэтап 2.5/2.6/2.7 → 'визуализация'
    """
    if current_subgroup in ("Подэтап 2.2", "Подэтап 2.3", "Подэтап 2.4"):
        return "мудборд"
    elif current_subgroup in ("Подэтап 2.5", "Подэтап 2.6", "Подэтап 2.7"):
        return "визуализация"
    return ""


# Маппинг номеров стадий к коротким названиям (для уведомлений исполнителям)
_STAGE_TITLE_MAP = {
    "1": "Планировочное решение",
    "2": "Концепция дизайна",
    "3": "Рабочая документация",
}

# Последние круги (бесплатные правки исчерпаны)
_LAST_VIZ_SUBGROUPS = {"Подэтап 2.7"}


async def _dispatch_crm_notifications(
    card_id: int,
    event_type: str,
    recipients: list,
    title: str,
    project_type_key: str = "",
):
    """Отправить личные уведомления нескольким получателям (фоновая задача).

    Создаёт собственную сессию БД, т.к. вызывается через asyncio.create_task()
    и переданная из endpoint'а сессия может быть уже закрыта.

    Args:
        card_id: ID CRM-карточки
        recipients: список кортежей (employee_id, message_text)
    """
    own_db = SessionLocal()
    try:
        for emp_id, message in recipients:
            if emp_id:
                try:
                    await dispatch_notification(
                        db=own_db,
                        employee_id=emp_id,
                        event_type=event_type,
                        title=title,
                        message=message,
                        related_entity_type="crm_card",
                        related_entity_id=card_id,
                        project_type=project_type_key,
                        card_id=card_id,
                    )
                except Exception as e:
                    logger.warning(f"Ошибка dispatch_notification для employee {emp_id}: {e}")
    finally:
        own_db.close()


def _add_business_days(start_date, days: int):
    """Добавить рабочие дни (пн-пт + праздники РФ) к дате."""
    if not start_date:
        return datetime.utcnow()
    if isinstance(start_date, str):
        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
        except (ValueError, TypeError):
            return datetime.utcnow()
    current = start_date
    added = 0
    while added < days:
        current += timedelta(days=1)
        if _is_working_day(current):
            added += 1
    return current


RUSSIAN_HOLIDAYS = [
    (1, 1),
    (1, 2),
    (1, 3),
    (1, 4),
    (1, 5),
    (1, 6),
    (1, 7),
    (1, 8),
    (2, 23),
    (3, 8),
    (5, 1),
    (5, 9),
    (6, 12),
    (11, 4),
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
        current = datetime.strptime(start_date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return start_date_str
    added = 0
    while added < working_days:
        current += timedelta(days=1)
        if _is_working_day(current):
            added += 1
    return current.strftime("%Y-%m-%d")


logger = logging.getLogger(__name__)
router = APIRouter(tags=["crm"])


def _calc_current_step_deadline(entries) -> str:
    """Рассчитать плановую дату ТЕКУЩЕЙ АКТИВНОЙ фазы — первой незавершённой записи timeline.
    Это то, что в десктопе выделяется зелёной рамкой: stage_code == current_substep_code AND not actual_date.
    entries: список ProjectTimelineEntry, отсортированных по sort_order.
    Возвращает строку 'YYYY-MM-DD' или ''.
    """
    prev_date = ""
    for entry in entries:
        if (entry.executor_role or "") == "header":
            continue
        code = entry.stage_code or ""
        if code == "START":
            prev_date = entry.actual_date or ""
            continue
        # Пропускаем записи вне договора
        if not entry.is_in_contract_scope:
            if entry.actual_date:
                prev_date = entry.actual_date
            continue
        # Пропускаем явно пропущенные шаги
        if (entry.status or "") == "skipped":
            if entry.actual_date:
                prev_date = entry.actual_date
            continue
        norm = int(entry.custom_norm_days or 0) if (entry.custom_norm_days and entry.custom_norm_days > 0) else int(entry.norm_days or 0)
        actual = entry.actual_date or ""
        if prev_date and norm > 0:
            planned = _add_working_days_to_date(prev_date, norm)
        elif prev_date:
            planned = prev_date
        else:
            planned = ""
        # Первый шаг без фактической даты — текущая активная фаза
        if not actual:
            return planned
        prev_date = actual
    return ""


# =========================
# CRM КАРТОЧКИ
# =========================


@router.get("/cards")
async def get_crm_cards(project_type: Optional[str] = None, archived: bool = False, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список CRM карточек по типу проекта

    Args:
        project_type: Тип проекта (Индивидуальный/Шаблонный). Если не указан — все типы.
        archived: Если True - возвращает архивные карточки (СДАН, РАСТОРГНУТ, АВТОРСКИЙ НАДЗОР)
    """
    try:
        query = db.query(CRMCard, Client.full_name.label("client_name")).join(Contract, CRMCard.contract_id == Contract.id).outerjoin(Client, Contract.client_id == Client.id)
        if project_type:
            query = query.filter(Contract.project_type == project_type)

        if archived:
            # Архивные карточки - статус СДАН, РАСТОРГНУТ или АВТОРСКИЙ НАДЗОР
            query = query.filter(Contract.status.in_(ARCHIVE_STATUSES))
        else:
            # Активные карточки - статус НЕ в архивных
            query = query.filter(or_(Contract.status.is_(None), Contract.status == "", ~Contract.status.in_(ARCHIVE_STATUSES)))

        rows = query.order_by(CRMCard.order_position.nullslast(), CRMCard.id).all()

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

        # Batch-load workflow states для отображения текущего подэтапа
        all_wf_states = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id.in_(card_ids)).all() if card_ids else []
        wf_states_by_card = {}
        for wf in all_wf_states:
            wf_states_by_card[(wf.crm_card_id, wf.stage_name)] = wf

        # Batch-load substep names из ProjectTimelineEntry
        substep_codes = [wf.current_substep_code for wf in all_wf_states if wf.current_substep_code]
        substep_name_map = {}
        if substep_codes:
            substep_entries = db.query(ProjectTimelineEntry.stage_code, ProjectTimelineEntry.stage_name).filter(ProjectTimelineEntry.stage_code.in_(substep_codes)).all()
            substep_name_map = {e.stage_code: e.stage_name for e in substep_entries}

        # Batch-load timeline entries для расчёта дедлайна текущего подэтапа
        contract_ids = list(set(card.contract_id for card in cards))
        all_timeline_entries = (
            db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id.in_(contract_ids)).order_by(ProjectTimelineEntry.contract_id, ProjectTimelineEntry.sort_order).all()
            if contract_ids
            else []
        )
        timeline_by_contract = {}
        for te in all_timeline_entries:
            timeline_by_contract.setdefault(te.contract_id, []).append(te)

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
            designer_candidates = [e for e in card_executors if "концепция" in (e.stage_name or "").lower() or "визуализация" in (e.stage_name or "").lower()]
            designer_executor = max(designer_candidates, key=lambda e: e.id) if designer_candidates else None

            # Find draftsman executor: stage_name contains 'чертежи' or 'планировочные', latest by id
            draftsman_candidates = [e for e in card_executors if "чертежи" in (e.stage_name or "").lower() or "планировочные" in (e.stage_name or "").lower()]
            draftsman_executor = max(draftsman_candidates, key=lambda e: e.id) if draftsman_candidates else None

            # Get executor names from batch-loaded employees map
            designer_employee = executor_employees_map.get(designer_executor.executor_id) if designer_executor else None
            draftsman_employee = executor_employees_map.get(draftsman_executor.executor_id) if draftsman_executor else None

            card_data = {
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
                "senior_manager_name": senior_manager_name,
                "sdp_name": sdp_name,
                "gap_name": gap_name,
                "manager_name": manager_name,
                "surveyor_name": surveyor_name,
                "contract_number": contract.contract_number,
                "address": contract.address,
                "area": contract.area,
                "city": contract.city,
                "agent_type": contract.agent_type,
                "project_type": contract.project_type,
                "project_subtype": contract.project_subtype if hasattr(contract, "project_subtype") else None,
                "floors": contract.floors if hasattr(contract, "floors") else 1,
                "contract_period": contract.contract_period,
                "contract_status": contract.status,
                # Поля ТЗ и замера из contracts
                "tech_task_link": contract.tech_task_link,
                "tech_task_file_name": contract.tech_task_file_name,
                "tech_task_yandex_path": contract.tech_task_yandex_path,
                "measurement_image_link": contract.measurement_image_link,
                "measurement_file_name": contract.measurement_file_name,
                "measurement_yandex_path": contract.measurement_yandex_path,
                "measurement_date": str(contract.measurement_date) if contract.measurement_date else None,
                "designer_name": designer_employee.full_name if designer_employee else None,
                "designer_completed": designer_executor.completed if designer_executor else False,
                "designer_deadline": str(designer_executor.deadline) if designer_executor and designer_executor.deadline else None,
                "draftsman_name": draftsman_employee.full_name if draftsman_employee else None,
                "draftsman_completed": draftsman_executor.completed if draftsman_executor else False,
                "draftsman_deadline": str(draftsman_executor.deadline) if draftsman_executor and draftsman_executor.deadline else None,
                "order_position": card.order_position,
                "client_name": client_names.get(card.id),
                "created_at": card.created_at.isoformat() if card.created_at else None,
                "updated_at": card.updated_at.isoformat() if card.updated_at else None,
                # Текущий подэтап из StageWorkflowState
                "current_substep_code": (lambda wf: wf.current_substep_code if wf else None)(wf_states_by_card.get((card.id, card.column_name))),
                "current_substep_name": (lambda wf: substep_name_map.get(wf.current_substep_code) if wf and wf.current_substep_code else None)(wf_states_by_card.get((card.id, card.column_name))),
                "workflow_status": (lambda wf: wf.status if wf else None)(wf_states_by_card.get((card.id, card.column_name))),
                "revision_count": (lambda wf: wf.revision_count if wf else 0)(wf_states_by_card.get((card.id, card.column_name))),
                # Дедлайн текущего подэтапа (плановая дата из timeline)
                "current_substep_deadline": None,  # заполняется ниже
            }
            # Вычислить дедлайн текущей активной фазы (первая запись без actual_date)
            if card.contract_id in timeline_by_contract:
                _planned = _calc_current_step_deadline(timeline_by_contract[card.contract_id])
                card_data["current_substep_deadline"] = _planned or None
            result.append(card_data)

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении CRM карточек: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}")
async def get_crm_card(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
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

        stage_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).all()

        executor_data = []
        for se in stage_executors:
            executor_data.append(
                {
                    "id": se.id,
                    "stage_name": se.stage_name,
                    "executor_id": se.executor_id,
                    "executor_name": se.executor.full_name if se.executor else None,
                    "assigned_by": se.assigned_by,
                    "assigned_date": se.assigned_date.isoformat() if se.assigned_date else None,
                    "deadline": str(se.deadline) if se.deadline else None,
                    "submitted_date": se.submitted_date.isoformat() if se.submitted_date else None,
                    "completed": se.completed,
                    "completed_date": se.completed_date.isoformat() if se.completed_date else None,
                }
            )

        result = {
            "id": card.id,
            "contract_id": card.contract_id,
            "column_name": card.column_name,
            "deadline": str(card.deadline) if card.deadline else None,
            "tags": card.tags,
            "is_approved": card.is_approved,
            "senior_manager_id": card.senior_manager_id,
            "sdp_id": card.sdp_id,
            "gap_id": card.gap_id,
            "manager_id": card.manager_id,
            "surveyor_id": card.surveyor_id,
            "senior_manager_name": _emp_name(card.senior_manager_id),
            "sdp_name": _emp_name(card.sdp_id),
            "gap_name": _emp_name(card.gap_id),
            "manager_name": _emp_name(card.manager_id),
            "surveyor_name": _emp_name(card.surveyor_id),
            "approval_deadline": str(card.approval_deadline) if card.approval_deadline else None,
            "approval_stages": json.loads(card.approval_stages) if card.approval_stages else None,
            "project_data_link": card.project_data_link,
            "tech_task_file": card.tech_task_file,
            "tech_task_date": str(card.tech_task_date) if card.tech_task_date else None,
            "survey_date": str(card.survey_date) if card.survey_date else None,
            "order_position": card.order_position,
            "stage_executors": executor_data,
        }

        # Текущий подэтап из StageWorkflowState
        wf = (
            db.query(StageWorkflowState)
            .filter(
                StageWorkflowState.crm_card_id == card_id,
                StageWorkflowState.stage_name == card.column_name,
            )
            .first()
        )
        if wf:
            substep_name = None
            if wf.current_substep_code:
                tle = db.query(ProjectTimelineEntry.stage_name).filter(ProjectTimelineEntry.stage_code == wf.current_substep_code).first()
                substep_name = tle.stage_name if tle else None
            result["current_substep_code"] = wf.current_substep_code
            result["current_substep_name"] = substep_name
            result["workflow_status"] = wf.status
            result["revision_count"] = wf.revision_count
        else:
            result["current_substep_code"] = None
            result["current_substep_name"] = None
            result["workflow_status"] = None
            result["revision_count"] = 0

        # Поля из контракта
        if contract:
            # Имя клиента
            client = db.query(Client).filter(Client.id == contract.client_id).first() if contract.client_id else None
            result.update(
                {
                    "contract_number": contract.contract_number,
                    "address": contract.address,
                    "area": contract.area,
                    "city": contract.city,
                    "agent_type": contract.agent_type,
                    "project_type": contract.project_type,
                    "project_subtype": contract.project_subtype if hasattr(contract, "project_subtype") else None,
                    "floors": contract.floors if hasattr(contract, "floors") else 1,
                    "contract_period": contract.contract_period,
                    "contract_status": contract.status,
                    "client_name": client.full_name if client else None,
                    "client_id": contract.client_id,
                }
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при получении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards", response_model=CRMCardResponse)
async def create_crm_card(card_data: CRMCardCreate, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Создать новую CRM карточку"""
    try:
        # Защита от дублей: проверяем что CRM-карточка для этого договора ещё не существует
        if card_data.contract_id:
            existing_card = db.query(CRMCard).filter(CRMCard.contract_id == card_data.contract_id).first()
            if existing_card:
                raise HTTPException(status_code=409, detail="CRM-карточка для этого договора уже существует")

        card = CRMCard(**card_data.model_dump())
        db.add(card)
        db.commit()
        db.refresh(card)

        log = ActivityLog(employee_id=current_user.id, action_type="create", entity_type="crm_card", entity_id=card.id)
        db.add(log)
        db.commit()

        # Личное уведомление: создание карточки
        try:
            contract = db.query(Contract).filter(Contract.id == card.contract_id).first() if card.contract_id else None
            address = contract.address if contract else ""
            client_name = ""
            if contract and contract.client_id:
                cl = db.query(Client).filter(Client.id == contract.client_id).first()
                client_name = cl.full_name if cl else ""
            pt_key = _get_project_type_key(contract.project_type if contract else "")

            # Определяем получателя уведомления о создании карточки
            # Руководство §2/§3:
            # - Инд.: всегда уведомить СМ (если не он создал)
            # - Шабл.: если создал СМ → уведомить Менеджера; если создал другой → уведомить СМ
            sm_id = card.senior_manager_id
            # Текст по руководству: инд. — со списком специалистов, шабл. — без
            if pt_key == "template":
                _new_order_text = f"Новый заказ (шаблонный): {address}, {client_name}. Назначьте сотрудников."
            else:
                _new_order_text = f"Новый заказ: {address}, {client_name}. Назначьте сотрудников (СДП, дизайнера, чертёжника, замерщика)."

            if pt_key == "template" and sm_id and sm_id == current_user.id:
                # Шаблонные: СМ создал → уведомить Менеджера
                _mgr_id = card.manager_id
                if _mgr_id and _mgr_id != current_user.id:
                    asyncio.create_task(
                        _dispatch_crm_notifications(
                            card.id,
                            "assigned",
                            [(_mgr_id, _new_order_text)],
                            f"Новый заказ: {address}",
                            pt_key,
                        )
                    )
            elif sm_id and sm_id != current_user.id:
                asyncio.create_task(
                    _dispatch_crm_notifications(
                        card.id,
                        "assigned",
                        [(sm_id, _new_order_text)],
                        f"Новый заказ: {address}",
                        pt_key,
                    )
                )
            elif not sm_id:
                # Если ст.менеджер не назначен — ищем по роли
                sm = (
                    db.query(Employee)
                    .filter(
                        Employee.position == POSITION_SENIOR_MANAGER,
                        Employee.status == "активный",
                    )
                    .first()
                )
                if sm and sm.id != current_user.id:
                    asyncio.create_task(
                        _dispatch_crm_notifications(
                            card.id,
                            "assigned",
                            [(sm.id, _new_order_text)],
                            f"Новый заказ: {address}",
                            pt_key,
                        )
                    )
        except Exception as e:
            logger.warning(f"Ошибка уведомления при создании карточки: {e}")

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
            "updated_at": card.updated_at.isoformat() if card.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}")
async def update_crm_card(card_id: int, updates: CRMCardUpdate, current_user: Employee = Depends(require_permission("crm_cards.update")), db: Session = Depends(get_db)):
    """Обновить CRM карточку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        update_data = updates.model_dump(exclude_unset=True)

        # Проверяем существование сотрудников перед обновлением FK полей
        employee_fields = ["senior_manager_id", "sdp_id", "gap_id", "manager_id", "surveyor_id"]
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
            new_values=json.dumps({k: str(v) if v is not None else None for k, v in update_data.items()}, ensure_ascii=False),
        )
        db.add(activity)

        # Автосоздание оплат при назначении сотрудника на роль
        role_field_map = {
            "senior_manager_id": "Старший менеджер проектов",
            "sdp_id": "СДП",
            "gap_id": "ГАП",
            "manager_id": "Менеджер",
            "surveyor_id": "Замерщик",
        }
        for field, role in role_field_map.items():
            if field in update_data:
                new_emp = update_data[field]
                old_emp = old_values.get(field)
                if new_emp and new_emp != old_emp and card.contract_id:
                    try:
                        auto_create_employee_payment(db, card.contract_id, card.id, new_emp, role)
                    except Exception as e:
                        logger.warning(f"[AUTO_PAY] Ошибка для {role}: {e}")

        db.commit()
        db.refresh(card)

        # R-11 FIX: Унифицированный формат ответа (как в create)
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
            "updated_at": card.updated_at.isoformat() if card.updated_at else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/column")
async def move_crm_card_to_column(card_id: int, move_request: ColumnMoveRequest, current_user: Employee = Depends(require_permission("crm_cards.move")), db: Session = Depends(get_db)):
    """Переместить CRM карточку в другую колонку"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # S-01: Определяем тип проекта для выбора допустимых колонок
        contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
        project_type = contract.project_type if contract else "Индивидуальный"

        INDIVIDUAL_COLUMNS = ["Новый заказ", "В ожидании", "Стадия 1: планировочные решения", "Стадия 2: концепция дизайна", "Стадия 3: рабочие чертежи", "Выполненный проект"]
        TEMPLATE_COLUMNS = ["Новый заказ", "В ожидании", "Стадия 1: планировочные решения", "Стадия 2: рабочие чертежи", "Стадия 3: 3д визуализация (Дополнительная)", "Выполненный проект"]
        VALID_CRM_COLUMNS = TEMPLATE_COLUMNS if project_type == "Шаблонный" else INDIVIDUAL_COLUMNS

        if move_request.column_name not in VALID_CRM_COLUMNS:
            raise HTTPException(status_code=422, detail=f"Недопустимая колонка: {move_request.column_name}")

        old_column = card.column_name
        new_column = move_request.column_name

        # Ограничение для Планировочного проекта: только определённые колонки
        project_subtype = contract.project_subtype if contract else None
        if project_subtype and "Планировочный" in project_subtype:
            if "Стадия 2" in new_column or "Стадия 3" in new_column:
                raise HTTPException(status_code=400, detail="Планировочный проект не может перейти в эту стадию")

        # === ПРАВИЛО: Нельзя вернуться в "Новый заказ" ===
        if new_column == "Новый заказ" and old_column != "Новый заказ":
            raise HTTPException(status_code=422, detail='Нельзя вернуть карточку в "Новый заказ". Используйте столбец "В ожидании".')

        # === ПРАВИЛО: Из "В ожидании" — только в previous_column или "Выполненный проект" ===
        # Если previous_column == "Новый заказ" — разрешаем любой столбец (кроме "Новый заказ", что уже блокировано выше)
        if old_column == "В ожидании" and new_column != "В ожидании":
            allowed_return = card.previous_column or "Новый заказ"
            if allowed_return != "Новый заказ" and new_column not in [allowed_return, "Выполненный проект"]:
                raise HTTPException(status_code=422, detail=f'Из "В ожидании" можно вернуть только в "{allowed_return}" или "Выполненный проект".')

        # === ПРАВИЛО: При переходе в "В ожидании" — сохраняем previous_column + ставим на паузу ===
        if new_column == "В ожидании" and old_column != "В ожидании":
            card.previous_column = old_column
            # K1: Запоминаем время постановки на паузу для пересчёта дедлайна
            card.paused_at = datetime.utcnow()

        # === ПРАВИЛО: При возврате из "В ожидании" — пересчитываем дедлайн ===
        if old_column == "В ожидании" and new_column != "В ожидании":
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
                executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).all()
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
        free_move_roles = FREE_MOVE_ROLES
        if current_user.role not in free_move_roles:
            # S-01: Порядок колонок зависит от типа проекта
            if project_type == "Шаблонный":
                CRM_COLUMN_ORDER = ["Новый заказ", "Стадия 1: планировочные решения", "Стадия 2: рабочие чертежи", "Стадия 3: 3д визуализация (Дополнительная)", "Выполненный проект"]
            else:
                CRM_COLUMN_ORDER = ["Новый заказ", "Стадия 1: планировочные решения", "Стадия 2: концепция дизайна", "Стадия 3: рабочие чертежи", "Выполненный проект"]
            # "В ожидании" — специальная колонка, можно перемещать туда и обратно
            if old_column != "В ожидании" and new_column != "В ожидании":
                old_idx = CRM_COLUMN_ORDER.index(old_column) if old_column in CRM_COLUMN_ORDER else -1
                new_idx = CRM_COLUMN_ORDER.index(new_column) if new_column in CRM_COLUMN_ORDER else -1
                if old_idx >= 0 and new_idx >= 0:
                    if new_idx < old_idx:
                        # FIX Баг 3: Запрет перемещения назад для обычных пользователей
                        raise HTTPException(status_code=422, detail=f"Нельзя переместить карточку назад: {old_column} → {new_column}. Используйте 'В ожидании'.")
                    if new_idx - old_idx > 1:
                        raise HTTPException(status_code=422, detail=f"Нельзя перескакивать стадии: {old_column} → {new_column}")

        card.column_name = new_column

        # FIX Баг 6: Синхронизация статуса договора с колонкой CRM-карточки
        # Статус договора должен отражать текущую стадию для корректной статистики
        if contract and old_column != new_column:
            if new_column == "Выполненный проект":
                contract.status = "Выполненный проект"
                contract.status_changed_date = datetime.utcnow().strftime("%Y-%m-%d")
            elif new_column == "В ожидании":
                contract.status = "В ожидании"
                contract.status_changed_date = datetime.utcnow().strftime("%Y-%m-%d")
            elif old_column == "Новый заказ" and "Стадия" in new_column:
                contract.status = "В работе"
                contract.status_changed_date = datetime.utcnow().strftime("%Y-%m-%d")
            elif old_column == "В ожидании" and new_column != "Новый заказ":
                # Возврат из паузы — возвращаем "В работе"
                contract.status = "В работе"
                contract.status_changed_date = datetime.utcnow().strftime("%Y-%m-%d")

        # При перемещении вперёд: помечаем незаполненные подэтапы предыдущей стадии как skipped
        if old_column != new_column and new_column != "В ожидании" and old_column != "В ожидании":
            old_stage_group = _resolve_stage_group(old_column)
            if old_stage_group and contract:
                unfilled = (
                    db.query(ProjectTimelineEntry)
                    .filter(
                        ProjectTimelineEntry.contract_id == contract.id,
                        ProjectTimelineEntry.stage_group == old_stage_group,
                        ProjectTimelineEntry.executor_role != "header",
                        ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
                        ProjectTimelineEntry.status != "skipped",
                    )
                    .all()
                )
                for uf in unfilled:
                    uf.status = "skipped"
                    uf.updated_at = datetime.utcnow()
                if unfilled:
                    logger.info(f"Card {card_id} move: {len(unfilled)} entries marked skipped in {old_stage_group}")

            # Помечаем StageExecutors предыдущей стадии как completed (чтобы не слать уведомления о просрочке)
            if "Стадия" in old_column:
                old_stage_execs = (
                    db.query(StageExecutor)
                    .filter(
                        StageExecutor.crm_card_id == card_id,
                        StageExecutor.stage_name == old_column,
                        StageExecutor.completed == False,
                    )
                    .all()
                )
                for ex in old_stage_execs:
                    ex.completed = True
                    if not ex.completed_date:
                        ex.completed_date = datetime.utcnow()
                if old_stage_execs:
                    logger.info(f"Card {card_id} move: {len(old_stage_execs)} stage executors completed for {old_column}")

        # Автосоздание workflow state при перемещении на рабочую стадию
        if old_column != new_column and "Стадия" in new_column and contract:
            new_stage_group = _resolve_stage_group(new_column)
            if new_stage_group:
                existing_wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == new_column).first()
                if not existing_wf:
                    next_entry = _resolve_next_active_substep(db, contract.id, new_stage_group)
                    if next_entry:
                        new_wf = StageWorkflowState(
                            crm_card_id=card_id,
                            stage_name=new_column,
                            status="in_progress",
                            current_substep_code=next_entry.stage_code,
                            current_substage_group=next_entry.substage_group,
                        )
                        db.add(new_wf)
                        logger.info(f"Card {card_id} move: workflow state created for {new_column}, substep={next_entry.stage_code}")

        # K11: Запись перемещения в историю проекта
        if old_column != new_column:
            if new_column == "В ожидании":
                action_type = "card_paused"
                desc = f'Карточка приостановлена (из "{old_column}")'
            elif old_column == "В ожидании":
                action_type = "card_resumed"
                desc = f'Карточка возобновлена (в "{new_column}")'
            else:
                action_type = "card_moved"
                desc = f'Карточка перемещена: "{old_column}" → "{new_column}"'
            history = ActionHistory(user_id=current_user.id, action_type=action_type, entity_type="crm_card", entity_id=card_id, description=desc)
            db.add(history)

        db.commit()
        db.refresh(card)

        # Хук: автоуведомление в чат при перемещении карточки
        if old_column != new_column:
            if new_column == "Выполненный проект":
                # Завершающий скрипт (project_end) НЕ отправляется автоматически —
                # менеджер отправляет его вручную через кнопку в карточке.
                # Автоматически отправляется только опрос (Яндекс Формы).
                asyncio.create_task(send_survey_to_chat(card.id))
            elif "Стадия" in new_column:
                asyncio.create_task(trigger_messenger_notification(card.id, "stage_complete", stage_name=old_column, sender_id=current_user.id))

        # Личные уведомления при перемещении в новую стадию / выполненный проект
        if old_column != new_column and new_column != "В ожидании" and old_column != "В ожидании":
            try:
                address = contract.address if contract else ""
                pt_key = _get_project_type_key(contract.project_type if contract else "")
                notif_recipients = []

                if "Стадия" in new_column:
                    # Определяем исполнителя и reviewer для стадии
                    sl = new_column.lower()
                    if "концепция" in sl or "визуализац" in sl or "3д" in sl:
                        exec_id = _find_executor_id(db, card.id, new_column)
                        exec_role = "Дизайнер"
                    else:
                        exec_id = _find_executor_id(db, card.id, new_column)
                        exec_role = "Чертёжник"
                    # Reviewer зависит от стадии и типа проекта
                    if "рабочие чертежи" in sl or ("рабочая документация" in sl):
                        reviewer_id = card.gap_id
                        reviewer_role = POSITION_GAP
                    elif pt_key == "template" and ("планировочн" in sl or "3д" in sl or "визуализац" in sl):
                        reviewer_id = card.manager_id
                        reviewer_role = POSITION_MANAGER
                    else:
                        reviewer_id = card.sdp_id
                        reviewer_role = POSITION_SDP

                    if exec_id:
                        notif_recipients.append((exec_id, f'Проект {address} перешёл в "{new_column}". Приступайте к работе.'))
                    if reviewer_id:
                        notif_recipients.append((reviewer_id, f'Проект {address} перешёл в "{new_column}". Вы — проверяющий.'))

                elif new_column == "Выполненный проект":
                    # Руководство §2/§3: получатели зависят от типа проекта
                    sent_ids = set()
                    if pt_key == "template":
                        # Шаблонные: Менеджер + Ст.менеджер + Исполнитель (с "Спасибо за работу!")
                        for eid in [card.manager_id, card.senior_manager_id]:
                            if eid and eid not in sent_ids:
                                notif_recipients.append((eid, f"Проект {address} завершён."))
                                sent_ids.add(eid)
                        # Найти исполнителей (чертёжник/дизайнер) последней стадии
                        _exec_ids = (
                            db.query(StageExecutor.executor_id)
                            .filter(
                                StageExecutor.crm_card_id == card.id,
                            )
                            .distinct()
                            .all()
                        )
                        for (eid,) in _exec_ids:
                            if eid and eid not in sent_ids:
                                notif_recipients.append((eid, f"Проект {address} завершён. Спасибо за работу!"))
                                sent_ids.add(eid)
                    else:
                        # Индивидуальные: Менеджер + Ст.менеджер + СДП + ГАП
                        for eid in [card.manager_id, card.senior_manager_id, card.sdp_id, card.gap_id]:
                            if eid and eid not in sent_ids:
                                notif_recipients.append((eid, f"Проект {address} завершён."))
                                sent_ids.add(eid)

                if notif_recipients:
                    asyncio.create_task(
                        _dispatch_crm_notifications(
                            card.id,
                            "crm_stage_change",
                            notif_recipients,
                            f"Смена стадии: {address}",
                            pt_key,
                        )
                    )
            except Exception as e:
                logger.warning(f"Ошибка уведомления при перемещении карточки: {e}")

        return {
            "id": card.id,
            "contract_id": card.contract_id,
            "column_name": card.column_name,
            "old_column_name": old_column,
            "previous_column": card.previous_column,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при перемещении CRM карточки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/stage-executor")
async def assign_stage_executor(card_id: int, executor_data: StageExecutorCreate, current_user: Employee = Depends(require_permission("crm_cards.assign_executor")), db: Session = Depends(get_db)):
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
            if contract.project_type == "Шаблонный":
                allowed_stages = [
                    "Стадия 1: планировочные решения",
                    "Стадия 2: рабочие чертежи",
                    "Стадия 3: 3д визуализация (Дополнительная)",
                ]
            elif contract.project_type == "Индивидуальный":
                allowed_stages = [
                    "Стадия 1: планировочные решения",
                    "Стадия 2: концепция дизайна",
                    "Стадия 3: рабочие чертежи",
                ]
            else:
                allowed_stages = None

            if allowed_stages and executor_data.stage_name not in allowed_stages:
                raise HTTPException(status_code=400, detail=f"Недопустимая стадия '{executor_data.stage_name}' для типа проекта '{contract.project_type}'")

        # Upsert: если запись для этой стадии уже существует — обновить, иначе создать
        existing = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == executor_data.stage_name).order_by(StageExecutor.id.desc()).first()

        if existing:
            if existing.executor_id == executor_data.executor_id:
                # Тот же исполнитель — обновляем только дедлайн
                if executor_data.deadline:
                    existing.deadline = executor_data.deadline
                stage_executor = existing
            else:
                # Другой исполнитель — обновляем запись (переназначение)
                existing.executor_id = executor_data.executor_id
                existing.deadline = executor_data.deadline
                existing.assigned_by = current_user.id
                existing.assigned_date = datetime.utcnow()
                existing.completed = False
                existing.completed_date = None
                stage_executor = existing
        else:
            # Новая запись
            stage_executor = StageExecutor(
                crm_card_id=card_id,
                stage_name=executor_data.stage_name,
                executor_id=executor_data.executor_id,
                assigned_by=current_user.id,
                deadline=executor_data.deadline,
                assigned_date=datetime.utcnow(),
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
        db.add(
            ActionHistory(
                user_id=current_user.id,
                action_type="executor_assigned",
                entity_type="crm_card",
                entity_id=card_id,
                description=f"Назначен исполнитель: {executor.full_name} на стадию «{executor_data.stage_name}»" + (f", дедлайн: {executor_data.deadline}" if executor_data.deadline else ""),
            )
        )

        db.commit()
        db.refresh(stage_executor)

        # N1: Уведомление о назначении исполнителя
        # Согласно руководству §2: текст зависит от роли (позиции) исполнителя
        try:
            address = contract.address if contract else ""
            pt_key = _get_project_type_key(contract.project_type if contract else "")
            # Получить имя клиента для текста уведомления
            client_name = ""
            if contract and contract.client_id:
                _client = db.query(Client).filter(Client.id == contract.client_id).first()
                if _client:
                    client_name = _client.full_name or ""
            # Маппинг позиции → текст роли (из руководства по уведомлениям §2)
            _role_text_map = {
                POSITION_DRAFTSMAN: "чертёжником по проекту",
                POSITION_DESIGNER: "дизайнером по проекту",
                POSITION_SDP: "старшим дизайнером-проектировщиком по проекту",
                POSITION_GAP: "главным архитектором проекта",
                POSITION_MANAGER: "менеджером по проекту",
                POSITION_MEASURER: "замерщиком по проекту",
                POSITION_DAN: "дизайнером авторского надзора по объекту",
            }
            role_text = _role_text_map.get(executor.position, f"{(executor.position or 'исполнителем').lower()} по проекту")
            client_suffix = f" ({client_name})" if client_name else ""
            notif_recipients = [(executor.id, f"Вы назначены {role_text} {address}{client_suffix}.")]
            # Уведомление старшему менеджеру (информационный дубль)
            if card.senior_manager_id and card.senior_manager_id != executor.id:
                notif_recipients.append((card.senior_manager_id, f"Проект {address}: назначен исполнитель {executor.full_name} на стадию «{executor_data.stage_name}»."))
            asyncio.create_task(
                _dispatch_crm_notifications(
                    card.id,
                    "assigned",
                    notif_recipients,
                    f"Назначение: {address}",
                    pt_key,
                )
            )
        except Exception as e:
            logger.warning(f"Ошибка уведомления assign: {e}")

        return {
            "id": stage_executor.id,
            "crm_card_id": stage_executor.crm_card_id,
            "stage_name": stage_executor.stage_name,
            "executor_id": stage_executor.executor_id,
            "executor_name": executor.full_name,
            "assigned_by": stage_executor.assigned_by,
            "assigned_date": stage_executor.assigned_date.isoformat() if stage_executor.assigned_date else None,
            "deadline": str(stage_executor.deadline) if stage_executor.deadline else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при назначении исполнителя стадии: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/stage-executor/{stage_name}")
async def complete_stage(card_id: int, stage_name: str, update_data: StageExecutorUpdate, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Обновить статус выполнения стадии"""
    try:
        # Проверка прав: только назначенные на карточку сотрудники, исполнители стадий или суперпользователи
        from permissions import SUPERUSER_ROLES

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        is_card_member = current_user.id in [card.senior_manager_id, card.sdp_id, card.gap_id, card.manager_id]
        is_stage_executor = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.executor_id == current_user.id).first() is not None
        is_superuser = current_user.role in SUPERUSER_ROLES

        if not (is_card_member or is_stage_executor or is_superuser):
            raise HTTPException(status_code=403, detail="Недостаточно прав для завершения стадии")

        stage_executor = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name).order_by(StageExecutor.id.desc()).first()

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
            executor_name = executor_emp.full_name if executor_emp else f"ID {stage_executor.executor_id}"
            db.add(
                ActionHistory(
                    user_id=current_user.id, action_type="stage_completed", entity_type="crm_card", entity_id=card_id, description=f"Стадия завершена: «{stage_name}», исполнитель: {executor_name}"
                )
            )

        db.commit()
        db.refresh(stage_executor)

        return {
            "id": stage_executor.id,
            "crm_card_id": stage_executor.crm_card_id,
            "stage_name": stage_executor.stage_name,
            "executor_id": stage_executor.executor_id,
            "completed": stage_executor.completed,
            "completed_date": stage_executor.completed_date.isoformat() if stage_executor.completed_date else None,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении стадии CRM: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/cards/{card_id}")
async def delete_crm_card(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.delete")), db: Session = Depends(get_db)):
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
        db.query(ApprovalStageDeadline).filter(ApprovalStageDeadline.crm_card_id == card_id).delete()

        # Удаляем записи timeline проекта (по contract_id карточки)
        if card.contract_id:
            db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == card.contract_id).delete()

        # Удаляем историю действий
        db.query(ActionHistory).filter(ActionHistory.entity_type.in_(["crm_card", "stage", "stage_executor"]), ActionHistory.entity_id == card_id).delete(synchronize_session="fetch")

        # Удаляем привязанные чаты мессенджера
        db.query(MessengerChat).filter(MessengerChat.crm_card_id == card_id).delete()

        # Лог перед удалением
        log = ActivityLog(employee_id=current_user.id, action_type="delete", entity_type="crm_card", entity_id=card_id)
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
async def delete_stage_executor(executor_id: int, current_user: Employee = Depends(require_permission("crm_cards.delete_executor")), db: Session = Depends(get_db)):
    """Удалить назначение исполнителя на стадию"""
    try:
        executor = db.query(StageExecutor).filter(StageExecutor.id == executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Назначение не найдено")

        # Лог перед удалением
        log = ActivityLog(employee_id=current_user.id, action_type="delete", entity_type="stage_executor", entity_id=executor_id)
        db.add(log)

        # Бизнес-история удаления исполнителя
        executor_emp = db.query(Employee).filter(Employee.id == executor.executor_id).first()
        executor_name = executor_emp.full_name if executor_emp else f"ID {executor.executor_id}"
        db.add(
            ActionHistory(
                user_id=current_user.id,
                action_type="executor_deleted",
                entity_type="crm_card",
                entity_id=executor.crm_card_id,
                description=f"Удалён исполнитель: {executor_name} со стадии «{executor.stage_name}»",
            )
        )

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
async def reset_crm_card_stages(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.reset_stages")), db: Session = Depends(get_db)):
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
        db.add(ActionHistory(user_id=current_user.id, action_type="stages_reset", entity_type="crm_card", entity_id=card_id, description=f"Сброшены все стадии ({len(stage_executors)} исполнителей)"))

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
    stage_names: list[str] = Query(..., description="Имена стадий (column_name) для каскадного сброса"),
    current_user: Employee = Depends(require_permission("crm_cards.reset_stages")),
    db: Session = Depends(get_db),
):
    """Каскадный сброс стадий карточки — сбрасывает все указанные стадии (от выбранной и далее)"""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Сбрасываем StageExecutor для всех указанных стадий
        stage_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name.in_(stage_names)).all()

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
        db.add(
            ActionHistory(
                user_id=current_user.id,
                action_type="stages_reset",
                entity_type="crm_card",
                entity_id=card_id,
                description=f"Каскадный сброс стадий: {', '.join(stage_names)} ({reset_count} исполнителей)",
            )
        )

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
async def reset_crm_card_approval(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.reset_approval")), db: Session = Depends(get_db)):
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
        db.add(ActionHistory(user_id=current_user.id, action_type="approval_reset", entity_type="crm_card", entity_id=card_id, description="Сброшены все стадии согласования"))

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
async def get_submitted_stages(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить отправленные стадии карточки"""
    stages = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.submitted_date.isnot(None)).all()

    return [
        {
            "id": s.id,
            "stage_name": s.stage_name,
            "executor_id": s.executor_id,
            "executor_name": s.executor.full_name if s.executor else None,
            "submitted_date": s.submitted_date.isoformat() if s.submitted_date else None,
            "completed": s.completed,
            "completed_date": s.completed_date.isoformat() if s.completed_date else None,
        }
        for s in stages
    ]


@router.get("/cards/{card_id}/stage-history")
async def get_stage_history(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить историю стадий карточки (stage executors с именами сотрудников)"""
    executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).order_by(StageExecutor.assigned_date.asc()).all()

    result = []
    for se in executors:
        executor_name = "Не назначен"
        if se.executor:
            executor_name = se.executor.full_name or "Не назначен"

        assigned_by_name = None
        if se.assigned_by:
            assigner = db.query(Employee).filter(Employee.id == se.assigned_by).first()
            assigned_by_name = assigner.full_name if assigner else None

        result.append(
            {
                "stage_name": se.stage_name,
                "executor_name": executor_name,
                "assigned_by_name": assigned_by_name,
                "assigned_date": se.assigned_date.isoformat() if se.assigned_date else None,
                "deadline": se.deadline,
                "submitted_date": se.submitted_date.isoformat() if se.submitted_date else None,
                "completed": se.completed,
                "completed_date": se.completed_date.isoformat() if se.completed_date else None,
            }
        )

    return result


@router.get("/cards/{card_id}/action-history")
async def get_crm_card_action_history(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить историю действий карточки CRM"""
    history = db.query(ActionHistory).filter(ActionHistory.entity_type == "crm_card", ActionHistory.entity_id == card_id).order_by(ActionHistory.action_date.desc()).all()

    result = []
    for item in history:
        employee = db.query(Employee).filter(Employee.id == item.user_id).first()
        result.append(
            {
                "id": item.id,
                "user_id": item.user_id,
                "user_name": employee.full_name if employee else "Неизвестно",
                "action_type": item.action_type,
                "entity_type": item.entity_type,
                "entity_id": item.entity_id,
                "description": item.description,
                "action_date": item.action_date.strftime("%Y-%m-%d %H:%M:%S") if item.action_date else None,
            }
        )
    return result


# =========================
# WORKFLOW ENDPOINTS (CRM)
# =========================


def _server_recalculate_actual_days(db, contract_id: int):
    """Пересчёт actual_days (рабочие дни между последовательными actual_date) на сервере.
    Аналог _recalculate_days() из timeline_widget.py, но серверный."""
    from services.date_helpers import networkdays as _nwd

    entries = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id, ProjectTimelineEntry.executor_role != "header").order_by(ProjectTimelineEntry.sort_order).all()

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


def _resolve_next_active_substep(db, contract_id: int, stage_group: str, after_sort_order: int = 0):
    """Единый резолвер следующего активного подэтапа.

    Находит первую незаполненную, не-пропущенную, не-header строку
    таймлайна после заданной позиции. Используется всеми workflow
    endpoint-ами для определения 'куда карточке дальше'.
    """
    return (
        db.query(ProjectTimelineEntry)
        .filter(
            ProjectTimelineEntry.contract_id == contract_id,
            ProjectTimelineEntry.stage_group == stage_group,
            ProjectTimelineEntry.executor_role != "header",
            ProjectTimelineEntry.sort_order > after_sort_order,
            or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
            or_(ProjectTimelineEntry.status.is_(None), ProjectTimelineEntry.status != "skipped"),
        )
        .order_by(ProjectTimelineEntry.sort_order)
        .first()
    )


def _sync_workflow_substep(db, card_id: int, stage_name: str, contract_id: int):
    """Синхронизировать current_substep_code/current_substage_group с реальным состоянием таймлайна.

    Вызывается ПОСЛЕ каждого workflow-действия как safety-net перед commit.
    Гарантирует что карточка всегда знает 'где она сейчас'.

    НЕ меняет статус (status) — только позицию (substep_code + substage_group).
    Пропускает защищённые статусы (pending_decision, act_signing, stage_completed),
    где позиция управляется специальной логикой.
    """
    stage_group = _resolve_stage_group(stage_name)
    if not stage_group or not contract_id:
        return

    wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
    if not wf:
        return

    # Статусы с нестандартной логикой позиционирования — не трогать.
    # pending_review/revision: substep указывает на последнюю сданную работу (для reject)
    # client_approval: substep указывает на клиентскую строку
    # pending_decision/act_signing/stage_completed: финальные позиции
    PROTECTED_STATUSES = {
        "pending_review",
        "revision",
        "client_approval",
        "pending_decision",
        "act_signing",
        "stage_completed",
    }
    if wf.status in PROTECTED_STATUSES:
        return

    next_entry = _resolve_next_active_substep(db, contract_id, stage_group)
    if next_entry:
        old_code = wf.current_substep_code
        if old_code != next_entry.stage_code:
            logger.info(f"[WorkflowSync] card={card_id}: substep {old_code} → {next_entry.stage_code} ({next_entry.stage_name}), substage: {next_entry.substage_group}")
            wf.current_substep_code = next_entry.stage_code
            wf.current_substage_group = next_entry.substage_group


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
    next_entry = (
        db.query(ProjectTimelineEntry)
        .filter(
            ProjectTimelineEntry.contract_id == contract_id,
            ProjectTimelineEntry.stage_group == stage_group,
            ProjectTimelineEntry.executor_role != "header",
            (ProjectTimelineEntry.actual_date.is_(None)) | (ProjectTimelineEntry.actual_date == ""),
            ProjectTimelineEntry.status != "skipped",
            ProjectTimelineEntry.norm_days > 0,
        )
        .order_by(ProjectTimelineEntry.sort_order)
        .first()
    )

    if not next_entry:
        # Все подэтапы стадии заполнены — стадия завершена, дедлайн не нужен
        logger.debug(f"[Deadline] Нет незаполненных подэтапов для card={card_id}, стадия={stage_name}")
        return

    # is_in_contract_scope влияет только на расчёт срока договора (итоги),
    # а НЕ на дедлайн текущего подэтапа на канбане. Дедлайн всегда обновляется,
    # чтобы карточка отражала норму дней для текущего шага.

    # norm_days с учётом custom_norm_days (если менеджер изменил)
    norm = next_entry.norm_days or 0
    if next_entry.custom_norm_days and next_entry.custom_norm_days > 0:
        norm = next_entry.custom_norm_days
    if norm <= 0:
        logger.warning(f"[Deadline] norm_days=0 для подэтапа «{next_entry.stage_name}» card={card_id} — дедлайн не обновлён")
        return

    # База для расчёта: последняя actual_date перед этим подэтапом (сквозная)
    prev_filled = (
        db.query(ProjectTimelineEntry)
        .filter(
            ProjectTimelineEntry.contract_id == contract_id,
            ProjectTimelineEntry.executor_role != "header",
            ProjectTimelineEntry.sort_order < next_entry.sort_order,
            ProjectTimelineEntry.actual_date.isnot(None),
            ProjectTimelineEntry.actual_date != "",
        )
        .order_by(ProjectTimelineEntry.sort_order.desc())
        .first()
    )

    base_date_str = prev_filled.actual_date if prev_filled else datetime.utcnow().strftime("%Y-%m-%d")

    # Рассчитываем новый дедлайн через _add_business_days (серверная, без PyQt5)
    new_deadline_dt = _add_business_days(base_date_str, norm)
    new_deadline = new_deadline_dt.strftime("%Y-%m-%d")

    # Обновляем StageExecutor.deadline
    stage_executor = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name).order_by(StageExecutor.id.desc()).first()

    if stage_executor and stage_executor.deadline != new_deadline:
        old_deadline = stage_executor.deadline or "не установлен"
        stage_executor.deadline = new_deadline
        logger.info(f"[Deadline] Обновлён: card={card_id}, стадия={stage_name}, подэтап=«{next_entry.stage_name}», {old_deadline} → {new_deadline} (norm={norm} раб.дн.)")


def _resolve_stage_group(column_name: str) -> str:
    """Определить stage_group по имени колонки канбана.
    Маппинг гибкий: ищет паттерны 'стадия N' в названии колонки.
    """
    col = column_name.lower()
    # Универсальный маппинг: 'стадия N' → STAGEN
    import re

    m = re.search(r"стадия\s*(\d+)", col)
    if m:
        return f"STAGE{m.group(1)}"
    # Альтернативные маппинги для нестандартных названий колонок
    if "планировочн" in col:
        return "STAGE1"
    elif "концепция" in col or "дизайн" in col:
        return "STAGE2"
    elif "рабоч" in col or "чертеж" in col or "чертёж" in col or "документац" in col:
        # Для шаблонных "Стадия 2: рабочие чертежи" regex уже выдаёт STAGE2
        # Этот fallback — для случаев без "Стадия N:" в названии
        return "STAGE3"
    elif "визуализац" in col or "3д" in col or "3d" in col:
        return "STAGE3"
    return ""


@router.get("/cards/{card_id}/workflow/state")
async def get_workflow_state(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить текущее состояние рабочего процесса карточки"""
    states = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id).all()
    return [{c.name: getattr(s, c.name) for c in s.__table__.columns} for s in states]


@router.post("/cards/{card_id}/workflow/repair")
async def workflow_repair(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.move")), db: Session = Depends(get_db)):
    """Восстановить застрявшую карточку: пересчитать substep из таймлайна.

    Если карточка застряла в pending_decision (диалог был закрыт) или
    current_substep_code указывает на неправильную строку — этот endpoint
    принудительно синхронизирует позицию с реальным состоянием таймлайна.
    Доступен для ст.менеджера и директора.
    """
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    stage_name = card.column_name
    contract_id = card.contract_id
    stage_group = _resolve_stage_group(stage_name)
    if not stage_group or not contract_id:
        raise HTTPException(status_code=400, detail="Невозможно определить стадию")

    wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
    if not wf:
        # Создаём workflow state если его нет (шаблонные проекты и др.)
        next_entry = _resolve_next_active_substep(db, contract_id, stage_group)
        wf = StageWorkflowState(
            crm_card_id=card_id,
            stage_name=stage_name,
            status="in_progress",
            current_substep_code=next_entry.stage_code if next_entry else None,
            current_substage_group=next_entry.substage_group if next_entry else None,
        )
        db.add(wf)
        logger.info(f"[WorkflowRepair] Создан workflow state для card={card_id}, stage={stage_name}")

    old_status = wf.status
    old_substep = wf.current_substep_code
    old_substage = wf.current_substage_group

    # Принудительная синхронизация (игнорируем protected statuses)
    next_entry = None

    if wf.status == "revision" and wf.current_substep_code:
        # При revision — ищем подэтап правки (исполнитель после текущего reviewer)
        current_entry = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id, ProjectTimelineEntry.stage_code == wf.current_substep_code).first()
        if current_entry:
            current_substage = current_entry.substage_group
            corr_q = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role.notin_(["header", "Клиент", POSITION_SDP, POSITION_MANAGER, POSITION_GAP]),
                ProjectTimelineEntry.sort_order > current_entry.sort_order,
                (ProjectTimelineEntry.actual_date.is_(None)) | (ProjectTimelineEntry.actual_date == ""),
            )
            if current_substage and current_substage.strip():
                corr_q = corr_q.filter(ProjectTimelineEntry.substage_group == current_substage)
            next_entry = corr_q.order_by(ProjectTimelineEntry.sort_order).first()

        # Также очищаем ошибочно заполненные даты после текущего подэтапа
        if current_entry:
            future_entries = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.sort_order > current_entry.sort_order,
                    ProjectTimelineEntry.actual_date.isnot(None),
                    ProjectTimelineEntry.actual_date != "",
                )
                .all()
            )
            for fe in future_entries:
                logger.info(f"[WorkflowRepair] Очистка даты у {fe.stage_code} ({fe.stage_name})")
                fe.actual_date = None
                fe.actual_days = None

    if not next_entry:
        next_entry = _resolve_next_active_substep(db, contract_id, stage_group)

    if next_entry:
        wf.current_substep_code = next_entry.stage_code
        wf.current_substage_group = next_entry.substage_group
        # Определяем правильный status по роли подэтапа
        reviewer_roles = {POSITION_SDP, POSITION_MANAGER, POSITION_GAP}
        executor_roles = {POSITION_DRAFTSMAN, POSITION_DESIGNER}
        if next_entry.executor_role in reviewer_roles:
            wf.status = "pending_review"
        elif next_entry.executor_role in executor_roles:
            wf.status = "in_progress"
        elif next_entry.executor_role == "Клиент":
            wf.status = "client_approval"
        elif wf.status == "pending_decision":
            wf.status = "in_progress"
        wf.updated_at = datetime.utcnow()
        logger.info(f"[WorkflowRepair] status={wf.status}, substep={next_entry.stage_code} ({next_entry.executor_role})")
    else:
        # Все строки заполнены — стадия завершена, можно перевести в act_signing
        if wf.status not in ("act_signing", "stage_completed"):
            wf.status = "act_signing"
            wf.updated_at = datetime.utcnow()

    # Пересчёт дедлайна
    _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

    # Сбросить executor state при ремонте (если status изменился на рабочий)
    if wf.status in ("in_progress", "revision"):
        executors = (
            db.query(StageExecutor)
            .filter(
                StageExecutor.crm_card_id == card_id,
                StageExecutor.stage_name == stage_name,
                StageExecutor.completed == True,
            )
            .all()
        )
        for ex in executors:
            ex.completed = False
            ex.completed_date = None
            logger.info(f"[WorkflowRepair] Сброс completed для {ex.executor_name}")

    db.add(
        ActionHistory(
            user_id=current_user.id,
            action_type="workflow_repair",
            entity_type="crm_card",
            entity_id=card_id,
            description=(f"Восстановление карточки: {old_status} → {wf.status}, {old_substep} → {wf.current_substep_code}"),
        )
    )

    db.commit()

    logger.info(f"[WorkflowRepair] card={card_id}: status {old_status} → {wf.status}, substep {old_substep} → {wf.current_substep_code}, substage {old_substage} → {wf.current_substage_group}")

    return {
        "status": "repaired",
        "old_status": old_status,
        "new_status": wf.status,
        "old_substep": old_substep,
        "new_substep": wf.current_substep_code,
        "old_substage": old_substage,
        "new_substage": wf.current_substage_group,
    }


@router.post("/cards/{card_id}/workflow/submit")
async def workflow_submit_work(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
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
        executor_roles = [POSITION_DRAFTSMAN, POSITION_DESIGNER]

        # Проверяем workflow state — если revision, обновляем тот же подэтап (не следующий)
        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()

        entry = None
        if wf and wf.status == "revision" and wf.current_substep_code:
            # После исправления — НЕ ищем следующий подэтап, обновляем текущий
            entry = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id, ProjectTimelineEntry.stage_code == wf.current_substep_code).first()
        else:
            # Обычная сдача — ищем первый незаполненный подэтап
            entry = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.executor_role.in_(executor_roles),
                    ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
                )
                .order_by(ProjectTimelineEntry.sort_order)
                .first()
            )

        if entry:
            entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
            entry.updated_at = datetime.utcnow()
            _server_recalculate_actual_days(db, contract_id)

        # Обновляем workflow state
        if not wf:
            wf = StageWorkflowState(
                crm_card_id=card_id,
                stage_name=stage_name,
                current_substep_code=entry.stage_code if entry else None,
                current_substage_group=entry.substage_group if entry else None,
                status="pending_review",
            )
            db.add(wf)
        wf.current_substep_code = entry.stage_code if entry else wf.current_substep_code
        wf.current_substage_group = entry.substage_group if entry else wf.current_substage_group
        wf.status = "pending_review"
        wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(
            ActionHistory(
                user_id=current_user.id, action_type="work_submitted", entity_type="crm_card", entity_id=card_id, description=f"Сдача работы: {stage_name} ({entry.stage_name if entry else ''})"
            )
        )

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        db.commit()

        # Хук: уведомление в чат о сдаче работы
        asyncio.create_task(trigger_messenger_notification(card_id, "stage_complete", stage_name=stage_name))

        # Личное уведомление: "Исполнитель сдал работу" → reviewer
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            address = contract.address if contract else ""
            pt_key = _get_project_type_key(contract.project_type if contract else "")
            sl = stage_name.lower()
            # Определяем роль исполнителя
            if "концепция" in sl or "визуализац" in sl or "3д" in sl:
                executor_name = "Дизайнер"
            else:
                executor_name = "Чертёжник"
            # Определяем reviewer
            if "рабочие чертежи" in sl or "рабочая документация" in sl:
                reviewer_id = card.gap_id
            elif pt_key == "template" and ("планировочн" in sl or "3д" in sl or "визуализац" in sl):
                reviewer_id = card.manager_id
            else:
                reviewer_id = card.sdp_id
            if reviewer_id:
                # Текст зависит от типа проекта (§2-§3 notifications-guide):
                # Инд: стадия "Планировочное решение" (короткое имя)
                # Шабл: без стадии
                if pt_key == "individual":
                    _sn = _extract_stage_number(stage_name)
                    _short = _STAGE_TITLE_MAP.get(_sn, stage_name)
                    _submit_txt = f'{executor_name} сдал работу по проекту {address}, стадия "{_short}". Проверьте.'
                else:
                    _submit_txt = f"{executor_name} сдал работу по проекту {address}. Проверьте."
                asyncio.create_task(
                    _dispatch_crm_notifications(
                        card.id,
                        "crm_stage_change",
                        [(reviewer_id, _submit_txt)],
                        f"Сдача работы: {address}",
                        pt_key,
                    )
                )
        except Exception as e:
            logger.warning(f"Ошибка уведомления submit: {e}")

        return {"status": "submitted", "substep": entry.stage_code if entry else None}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/submit: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/accept")
async def workflow_accept_work(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.move")), db: Session = Depends(get_db)):
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
        reviewer_roles = REVIEWER_ROLES

        if stage_group:
            entry = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.executor_role.in_(reviewer_roles),
                    ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
                )
                .order_by(ProjectTimelineEntry.sort_order)
                .first()
            )

            if entry:
                entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
                entry.updated_at = datetime.utcnow()
                _server_recalculate_actual_days(db, contract_id)

        # Устанавливаем submitted_date у завершённых исполнителей текущей стадии
        stage_executors = (
            db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name, StageExecutor.completed == True, StageExecutor.submitted_date.is_(None)).all()
        )
        for se in stage_executors:
            se.submitted_date = datetime.utcnow()

        # Обновляем workflow state
        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
        if wf:
            wf.status = "in_progress"
            wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(user_id=current_user.id, action_type="work_accepted", entity_type="crm_card", entity_id=card_id, description=f"Работа принята: {stage_name}"))

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        # Safety-net: синхронизировать substep с реальным состоянием таймлайна
        _sync_workflow_substep(db, card_id, stage_name, contract_id)

        db.commit()
        return {"status": "accepted"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/accept: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/reject")
async def workflow_reject_work(card_id: int, request: Request, current_user: Employee = Depends(require_permission("crm_cards.move")), db: Session = Depends(get_db)):
    """Отправить на исправление — обновляет workflow state и сбрасывает completed.
    Записывает дату проверки reviewer в таймлайн (отклонение — тоже факт проверки).
    Продвигает current_substep_code на строку "Правка" (исполнитель).
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
        revision_file_path = body.get("revision_file_path", "")

        # Сбрасываем completed у исполнителя текущей стадии
        # чтобы он увидел кнопку "Сдать работу" снова
        executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.completed == True).all()
        for ex in executors:
            # С2: Точное совпадение stage_name (вместо нечёткого ILIKE-подобного)
            if ex.stage_name and ex.stage_name == stage_name:
                ex.completed = False
                ex.completed_date = None

        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
        if not wf:
            wf = StageWorkflowState(
                crm_card_id=card_id,
                stage_name=stage_name,
                status="revision",
                revision_count=1,
                revision_file_path=revision_file_path or None,
            )
            db.add(wf)
        else:
            wf.status = "revision"
            wf.revision_count = (wf.revision_count or 0) + 1
            if revision_file_path:
                wf.revision_file_path = revision_file_path
            # П5: сохраняем историю ревизий (не перезатираем предыдущие)
            import json as _json

            history = []
            if wf.revision_history:
                try:
                    history = _json.loads(wf.revision_history)
                except (ValueError, TypeError):
                    history = []
            reason = body.get("reason", "")
            history.append(
                {
                    "num": wf.revision_count,
                    "file_path": revision_file_path or "",
                    "reason": reason,
                    "date": datetime.utcnow().strftime("%Y-%m-%d %H:%M"),
                }
            )
            wf.revision_history = _json.dumps(history, ensure_ascii=False)
            wf.updated_at = datetime.utcnow()

        # Записываем дату проверки reviewer (отклонение тоже фиксируется в таймлайне)
        # и продвигаем current_substep_code на строку "Правка" (исполнитель)
        stage_group = _resolve_stage_group(stage_name)
        if contract_id and wf.current_substep_code and stage_group:
            current_entry = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id, ProjectTimelineEntry.stage_code == wf.current_substep_code).first()
            if current_entry:
                # Дата проверки reviewer (отклонение = факт проверки)
                reviewer_roles = REVIEWER_ROLES
                current_substage = current_entry.substage_group
                reviewer_entry = None

                # Если текущий подэтап УЖЕ reviewer — ставим дату НА НЕГО
                if current_entry.executor_role in reviewer_roles:
                    if not current_entry.actual_date:
                        reviewer_entry = current_entry
                    elif wf.revision_count > 1:
                        # Повторный reject — перезаписываем текущую дату
                        reviewer_entry = current_entry
                else:
                    # Текущий = исполнитель — ищем первый reviewer ПОСЛЕ него
                    reviewer_base = db.query(ProjectTimelineEntry).filter(
                        ProjectTimelineEntry.contract_id == contract_id,
                        ProjectTimelineEntry.stage_group == stage_group,
                        ProjectTimelineEntry.executor_role.in_(reviewer_roles),
                        ProjectTimelineEntry.sort_order > current_entry.sort_order,
                    )
                    if current_substage and current_substage.strip():
                        reviewer_base = reviewer_base.filter(ProjectTimelineEntry.substage_group == current_substage)
                    reviewer_entry = (
                        reviewer_base.filter(
                            (ProjectTimelineEntry.actual_date.is_(None)) | (ProjectTimelineEntry.actual_date == ""),
                        )
                        .order_by(ProjectTimelineEntry.sort_order)
                        .first()
                    )
                    if not reviewer_entry and wf.revision_count > 1:
                        reviewer_entry = (
                            reviewer_base.filter(
                                ProjectTimelineEntry.actual_date.isnot(None),
                                ProjectTimelineEntry.actual_date != "",
                            )
                            .order_by(ProjectTimelineEntry.sort_order.desc())
                            .first()
                        )

                if reviewer_entry:
                    reviewer_entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
                    reviewer_entry.updated_at = datetime.utcnow()
                    logger.info(f"reject: дата проверки записана в {reviewer_entry.stage_code} ({reviewer_entry.stage_name})")

                # Продвигаем current_substep_code на строку "Правка" (исполнитель)
                # Для плоских стадий (STAGE3 инд., STAGE2/3 шабл.) substage_group может быть None или ''
                current_substage = current_entry.substage_group
                correction_query = db.query(ProjectTimelineEntry).filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.executor_role.notin_(["header", "Клиент", POSITION_SDP, POSITION_MANAGER, POSITION_GAP]),
                    ProjectTimelineEntry.sort_order > current_entry.sort_order,
                    (ProjectTimelineEntry.actual_date.is_(None)) | (ProjectTimelineEntry.actual_date == ""),
                )
                if current_substage and current_substage.strip():
                    # Иерархическая стадия — ищем в рамках подэтапа
                    correction_query = correction_query.filter(ProjectTimelineEntry.substage_group == current_substage)
                else:
                    # Плоская стадия — ищем в рамках всего stage_group (substage_group пуст/None)
                    correction_query = correction_query.filter(or_(ProjectTimelineEntry.substage_group.is_(None), ProjectTimelineEntry.substage_group == ""))
                correction_entry = correction_query.order_by(ProjectTimelineEntry.sort_order).first()
                if correction_entry:
                    wf.current_substep_code = correction_entry.stage_code
                    logger.info(f"reject: substep продвинут на {correction_entry.stage_code} ({correction_entry.stage_name})")

                _server_recalculate_actual_days(db, contract_id)

        # K11: Запись в историю
        db.add(
            ActionHistory(
                user_id=current_user.id, action_type="work_rejected", entity_type="crm_card", entity_id=card_id, description=f"Отправлено на правки: {stage_name} (итерация {wf.revision_count})"
            )
        )

        # Пересчитываем дедлайн — правки сдвигают timeline
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        db.commit()

        # Личные уведомления: "На исправление" → исполнитель + ст.менеджер (правило 3)
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            address = contract.address if contract else ""
            pt_key = _get_project_type_key(contract.project_type if contract else "")
            rev_count = wf.revision_count or 1
            # Определяем исполнителя
            sl = stage_name.lower()
            if "концепция" in sl or "визуализац" in sl or "3д" in sl:
                exec_id = _find_executor_id(db, card.id, stage_name)
            else:
                exec_id = _find_executor_id(db, card.id, stage_name)
            notif_recipients = []
            if exec_id:
                notif_recipients.append((exec_id, f"Работа по проекту {address} возвращена на исправление (правка #{rev_count})."))
            # Правило 3: дубль ст.менеджеру (с указанием роли исполнителя)
            if card.senior_manager_id:
                # Руководство §2: "работа возвращена чертёжнику/дизайнеру"
                _sl = stage_name.lower()
                executor_role_dat = "дизайнеру" if ("концепция" in _sl or "визуализац" in _sl or "3д" in _sl) else "чертёжнику"
                notif_recipients.append((card.senior_manager_id, f"Проект {address}: работа возвращена {executor_role_dat} на исправление (правка #{rev_count})."))
            if notif_recipients:
                asyncio.create_task(
                    _dispatch_crm_notifications(
                        card.id,
                        "crm_stage_change",
                        notif_recipients,
                        f"На исправление: {address}",
                        pt_key,
                    )
                )
        except Exception as e:
            logger.warning(f"Ошибка уведомления reject: {e}")

        return {"status": "rejected", "revision_count": wf.revision_count, "revision_file_path": wf.revision_file_path}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/reject: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/client-send")
async def workflow_client_send(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.move")), db: Session = Depends(get_db)):
    """Отправить на согласование клиенту — объединяет accept + client-send.
    1. Записывает дату проверки reviewer (СДП/Менеджер/ГАП) в таймлайн
    2. Устанавливает submitted_date у StageExecutor
    3. Обновляет report_month у Payment
    4. Сбрасывает completed у исполнителя
    5. Помечает промежуточные пустые строки как skipped
    6. Приостанавливает дедлайн"""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    stage_name = card.column_name
    contract_id = card.contract_id
    stage_group = _resolve_stage_group(stage_name)

    deadline_str = ""
    if stage_group and contract_id:
        # === 1. Находим первую незаполненную клиентскую строку ===
        client_entry = (
            db.query(ProjectTimelineEntry)
            .filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role == "Клиент",
                ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
            )
            .order_by(ProjectTimelineEntry.sort_order)
            .first()
        )

        # === 2. Записываем дату проверки reviewer (только ДО клиентской строки) ===
        reviewer_roles = REVIEWER_ROLES
        reviewer_query = db.query(ProjectTimelineEntry).filter(
            ProjectTimelineEntry.contract_id == contract_id,
            ProjectTimelineEntry.stage_group == stage_group,
            ProjectTimelineEntry.executor_role.in_(reviewer_roles),
            ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
        )
        if client_entry:
            # Не записывать в строки ПОСЛЕ клиентской (например "Сбор правок")
            reviewer_query = reviewer_query.filter(ProjectTimelineEntry.sort_order < client_entry.sort_order)
        reviewer_entry = reviewer_query.order_by(ProjectTimelineEntry.sort_order).first()
        if reviewer_entry:
            reviewer_entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
            reviewer_entry.updated_at = datetime.utcnow()

        if client_entry:
            # Помечаем незаполненные строки как пропущенные:
            # Только строки ПОСЛЕ reviewer_entry и ДО client_entry
            # (строки правок/повторных проверок между reviewer и client)
            # Строки ДО reviewer_entry НЕ трогаем — они могут быть ещё не пройдены
            skip_after = reviewer_entry.sort_order if reviewer_entry else 0
            skipped_entries = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.executor_role.notin_(["header", "Клиент"]),
                    ProjectTimelineEntry.sort_order > skip_after,
                    ProjectTimelineEntry.sort_order < client_entry.sort_order,
                    ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
                )
                .all()
            )
            for se in skipped_entries:
                se.status = "skipped"
                se.updated_at = datetime.utcnow()

            # Считаем дедлайн согласования для уведомления
            norm_days = client_entry.norm_days or 3
            prev_entry = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.sort_order < client_entry.sort_order,
                    ProjectTimelineEntry.actual_date.isnot(None),
                    ProjectTimelineEntry.actual_date != "",
                )
                .order_by(ProjectTimelineEntry.sort_order.desc())
                .first()
            )

            if prev_entry and prev_entry.actual_date:
                try:
                    deadline_date = _add_business_days(prev_entry.actual_date, norm_days)
                    deadline_str = deadline_date.strftime("%d.%m.%Y")
                except Exception:
                    pass

        _server_recalculate_actual_days(db, contract_id)

    # === 3. Устанавливаем submitted_date у завершённых исполнителей ===
    stage_executors = (
        db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name, StageExecutor.completed == True, StageExecutor.submitted_date.is_(None)).all()
    )
    for se in stage_executors:
        se.submitted_date = datetime.utcnow()

    # === 4. Обновляем report_month у Payment ===
    try:
        current_month = datetime.utcnow().strftime("%Y-%m")
        from database import Contract
        from database import Payment as PaymentModel

        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if contract:
            # Определяем роль исполнителя по колонке
            sl = stage_name.lower()
            if "концепция" in sl or "дизайн" in sl or "визуализац" in sl:
                executor_role_name = "Дизайнер"
            else:
                executor_role_name = "Чертёжник"

            # Находим ID исполнителя через StageExecutor
            executor = (
                db.query(StageExecutor)
                .filter(
                    StageExecutor.crm_card_id == card_id,
                    StageExecutor.stage_name == stage_name,
                )
                .first()
            )
            executor_id = executor.executor_id if executor else None

            if executor_id:
                if contract.project_type == "Индивидуальный":
                    # Обновляем report_month для Доплаты
                    payments = (
                        db.query(PaymentModel)
                        .filter(PaymentModel.contract_id == contract_id, PaymentModel.employee_id == executor_id, PaymentModel.stage_name == stage_name, PaymentModel.payment_type == "Доплата")
                        .all()
                    )
                    for p in payments:
                        p.report_month = current_month
                        logger.info(f"[client-send] report_month Доплата → {current_month}, payment={p.id}")

                elif contract.project_type == "Шаблонный":
                    can_set_month = True
                    # Для чертежника — проверяем количество принятых стадий
                    if executor_role_name == "Чертёжник":
                        accepted_count = (
                            db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.executor_id == executor_id, StageExecutor.submitted_date.isnot(None)).count()
                        )
                        if accepted_count < 2:
                            can_set_month = False
                            logger.info(f"[client-send] Чертёжник первая стадия — report_month НЕ установлен")

                    if can_set_month:
                        payments = (
                            db.query(PaymentModel)
                            .filter(
                                PaymentModel.contract_id == contract_id, PaymentModel.employee_id == executor_id, PaymentModel.stage_name == stage_name, PaymentModel.payment_type == "Полная оплата"
                            )
                            .all()
                        )
                        for p in payments:
                            p.report_month = current_month
                            logger.info(f"[client-send] report_month Полная оплата → {current_month}, payment={p.id}")
    except Exception as e:
        logger.warning(f"[client-send] Ошибка обновления report_month: {e}")

    # === 5. НЕ сбрасываем completed — работа исполнителя принята ===
    # (ранее здесь был сброс completed=False, что приводило к повторному
    # появлению кнопки "Сдать работу" у исполнителя)

    # === 6. Обновляем workflow state ===
    # Определяем stage_code клиентской строки для current_substep_code
    client_substep_code = None
    if stage_group and contract_id:
        _client_entry = (
            db.query(ProjectTimelineEntry)
            .filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.executor_role == "Клиент",
                ProjectTimelineEntry.actual_date.is_(None) | (ProjectTimelineEntry.actual_date == ""),
            )
            .order_by(ProjectTimelineEntry.sort_order)
            .first()
        )
        if _client_entry:
            client_substep_code = _client_entry.stage_code

    wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
    if not wf:
        wf = StageWorkflowState(crm_card_id=card_id, stage_name=stage_name, status="client_approval", client_approval_started_at=datetime.utcnow(), client_approval_deadline_paused=True)
        if client_substep_code:
            wf.current_substep_code = client_substep_code
        db.add(wf)
    else:
        wf.status = "client_approval"
        wf.client_approval_started_at = datetime.utcnow()
        wf.client_approval_deadline_paused = True
        wf.updated_at = datetime.utcnow()
        if client_substep_code:
            wf.current_substep_code = client_substep_code

    # === 7. Обновляем дедлайн исполнителя ===
    if stage_group and contract_id:
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

    # K11: Запись в историю
    db.add(ActionHistory(user_id=current_user.id, action_type="client_send", entity_type="crm_card", entity_id=card_id, description=f"Отправлено клиенту: {stage_name}"))

    db.commit()

    # Хук: уведомление в чат об отправке клиенту (с дедлайном)
    asyncio.create_task(trigger_messenger_notification(card_id, "stage_complete", stage_name=f"{stage_name} (отправлено клиенту)", extra_context={"deadline": deadline_str} if deadline_str else None))

    # Личные уведомления: "Отправлено клиенту" → ст.менеджер + исполнитель (для Стадии 2 инд.)
    # Руководство §2/§3: тексты зависят от подэтапа и типа проекта
    try:
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        address = contract.address if contract else ""
        pt_key = _get_project_type_key(contract.project_type if contract else "")
        stage_num = _extract_stage_number(stage_name)
        notif_recipients = []

        # Определяем концепцию подэтапа для Стадии 2 инд.
        _cur_sub_cs = wf.current_substage_group if wf else ""
        concept_cs = ""
        if stage_num == "2" and pt_key == "individual":
            concept_cs = _get_substage_concept(_cur_sub_cs or "")
        _is_last_viz_cs = _cur_sub_cs in _LAST_VIZ_SUBGROUPS

        # Текст для СМ
        if card.senior_manager_id:
            if concept_cs == "мудборд":
                _sm_cs_txt = f"Проект {address}: мудборды отправлены клиенту на согласование."
            elif concept_cs == "визуализация":
                if _is_last_viz_cs:
                    _sm_cs_txt = f"Проект {address}: визуализации всех помещений отправлены клиенту."
                else:
                    _sm_cs_txt = f"Проект {address}: визуализация 1 помещения отправлена клиенту."
            else:
                _sm_cs_txt = f"Проект {address} отправлен клиенту на согласование (Стадия {stage_num})."
            notif_recipients.append((card.senior_manager_id, _sm_cs_txt))

        # Руководство §2: Стадия 2 (концепция дизайна) — также уведомить исполнителя (дизайнера)
        _sl_cs = stage_name.lower()
        if "концепция" in _sl_cs or ("визуализац" in _sl_cs and pt_key == "individual"):
            exec_id = _find_executor_id(db, card.id, stage_name)
            if exec_id:
                # Исполнитель получает тот же текст что и СМ для Стадии 2
                if concept_cs == "мудборд":
                    _ex_cs_txt = f"Проект {address}: мудборды отправлены клиенту на согласование."
                elif concept_cs == "визуализация":
                    if _is_last_viz_cs:
                        _ex_cs_txt = f"Проект {address}: визуализации всех помещений отправлены клиенту."
                    else:
                        _ex_cs_txt = f"Проект {address}: визуализация 1 помещения отправлена клиенту."
                else:
                    _ex_cs_txt = f"Проект {address} отправлен клиенту на согласование (Стадия {stage_num})."
                notif_recipients.append((exec_id, _ex_cs_txt))

        if notif_recipients:
            asyncio.create_task(
                _dispatch_crm_notifications(
                    card.id,
                    "crm_stage_change",
                    notif_recipients,
                    f"Отправлено клиенту: {address}",
                    pt_key,
                )
            )
    except Exception as e:
        logger.warning(f"Ошибка уведомления client-send: {e}")

    return {"status": "sent_to_client"}


@router.post("/cards/{card_id}/workflow/client-ok")
async def workflow_client_approved(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.complete_approval")), db: Session = Depends(get_db)):
    """Клиент согласовал — записывает дату в клиентскую строку Отправка/Согласование.
    Также записывает дату в следующую строку «Сбор правок» (роль СДП/Менеджер).
    Идемпотентен: если карточка уже в pending_decision, возвращает кэшированный результат."""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    try:
        stage_name = card.column_name
        contract_id = card.contract_id

        # ── ИДЕМПОТЕНТНОСТЬ + блокировка от race condition (П10) ──
        wf_check = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).with_for_update().first()
        if wf_check and wf_check.status == "pending_decision":
            # Карточка уже ожидает решения (повторный вызов после краша/retry)
            current_subgroup = wf_check.current_substage_group
            ROUND_PAIRS_IDEM = {
                "Подэтап 1.1": "Подэтап 1.2",
                "Подэтап 1.2": "Подэтап 1.3",
                "Подэтап 2.1": "Подэтап 2.2",
                "Подэтап 2.2": "Подэтап 2.3",
                "Подэтап 2.3": "Подэтап 2.4",
                "Подэтап 2.4": "Подэтап 2.5",
                "Подэтап 2.5": "Подэтап 2.6",
                "Подэтап 2.6": "Подэтап 2.7",
            }
            LAST_ROUNDS_IDEM = {"Подэтап 1.3", "Подэтап 2.7"}
            next_round_name = ROUND_PAIRS_IDEM.get(current_subgroup)
            stage_group_idem = _resolve_stage_group(stage_name)
            has_next = False
            if next_round_name and contract_id and stage_group_idem:
                has_next = (
                    db.query(ProjectTimelineEntry)
                    .filter(
                        ProjectTimelineEntry.contract_id == contract_id,
                        ProjectTimelineEntry.stage_group == stage_group_idem,
                        ProjectTimelineEntry.substage_group == next_round_name,
                    )
                    .first()
                    is not None
                )
            is_last = current_subgroup in LAST_ROUNDS_IDEM
            if not current_subgroup or not current_subgroup.strip():
                is_last = True
            project_type = ""
            if contract_id:
                c = db.query(Contract).filter(Contract.id == contract_id).first()
                if c:
                    project_type = c.project_type or ""
            logger.info(f"client-ok: идемпотентный повторный вызов для карточки {card_id} (pending_decision)")
            return {
                "status": "client_approved",
                "has_next_round": has_next,
                "next_round_name": next_round_name,
                "is_last_round": is_last,
                "has_remaining_client": False,
                "project_type": project_type,
            }

        stage_group = _resolve_stage_group(stage_name)
        client_entry = None
        is_last_round = False
        if stage_group and contract_id:
            # Записываем дату в клиентскую строку "Отправка клиенту / Согласование"
            client_entry = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.executor_role == "Клиент",
                    or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                )
                .order_by(ProjectTimelineEntry.sort_order)
                .first()
            )
            if client_entry:
                client_entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
                client_entry.updated_at = datetime.utcnow()

                # Дата "Сбор правок" НЕ записывается при client-ok
                # Она записывается позже — при advance-round или close-stage

            _server_recalculate_actual_days(db, contract_id)

        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
        if wf:
            # K7: Пересчёт дедлайна — считаем РАБОЧИЕ дни паузы на согласовании клиента
            if wf.client_approval_deadline_paused and wf.client_approval_started_at:
                approval_pause_days = _count_business_days(wf.client_approval_started_at, datetime.utcnow())
                if approval_pause_days > 0 and card.deadline:
                    try:
                        card.deadline = _add_working_days_to_date(card.deadline, approval_pause_days)
                        card.total_pause_days = (card.total_pause_days or 0) + approval_pause_days
                        logger.info(f"K7: Client approval pause {approval_pause_days} business days, card {card_id}")
                    except (ValueError, TypeError):
                        pass

                # Сдвигаем дедлайны исполнителей стадий
                if approval_pause_days > 0:
                    executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).all()
                    for ex in executors:
                        if ex.deadline:
                            try:
                                ex.deadline = _add_working_days_to_date(str(ex.deadline), approval_pause_days)
                            except (ValueError, TypeError):
                                pass

            # Определяем, есть ли следующий "круг" (substage_group)
            # Полная таблица переходов из docs/workflow-guide.md
            ROUND_PAIRS = {
                "Подэтап 1.1": "Подэтап 1.2",
                "Подэтап 1.2": "Подэтап 1.3",
                "Подэтап 2.1": "Подэтап 2.2",
                "Подэтап 2.2": "Подэтап 2.3",
                "Подэтап 2.3": "Подэтап 2.4",
                "Подэтап 2.4": "Подэтап 2.5",
                "Подэтап 2.5": "Подэтап 2.6",
                "Подэтап 2.6": "Подэтап 2.7",
            }
            current_subgroup = wf.current_substage_group if wf else None
            next_round_name = ROUND_PAIRS.get(current_subgroup)
            has_next_round = False
            if next_round_name and contract_id and stage_group:
                # Проверяем что следующий круг реально существует в таймлайне
                next_round_exists = (
                    db.query(ProjectTimelineEntry)
                    .filter(
                        ProjectTimelineEntry.contract_id == contract_id,
                        ProjectTimelineEntry.stage_group == stage_group,
                        ProjectTimelineEntry.substage_group == next_round_name,
                    )
                    .first()
                )
                has_next_round = next_round_exists is not None
                if not has_next_round:
                    logger.warning(f"client-ok: ROUND_PAIRS указывает на '{next_round_name}', но в таймлайне его нет (contract_id={contract_id}, stage_group={stage_group})")

            # Подэтап 2.1 (Мудборды): проверяем есть ли ещё незаполненные клиентские строки
            # Если есть — это первое согласование, нужно предложить "Продолжить правки / Закрыть"
            has_remaining_client = False
            if client_entry and contract_id and stage_group and current_subgroup:
                remaining_client = (
                    db.query(ProjectTimelineEntry)
                    .filter(
                        ProjectTimelineEntry.contract_id == contract_id,
                        ProjectTimelineEntry.stage_group == stage_group,
                        ProjectTimelineEntry.substage_group == current_subgroup,
                        ProjectTimelineEntry.executor_role == "Клиент",
                        ProjectTimelineEntry.sort_order > client_entry.sort_order,
                        or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                        or_(ProjectTimelineEntry.status.is_(None), ProjectTimelineEntry.status != "skipped"),
                    )
                    .first()
                )
                has_remaining_client = remaining_client is not None

            # Статус зависит от наличия оставшихся клиентских строк в том же подэтапе
            if has_remaining_client:
                # Внутри подэтапа с несколькими клиентскими кругами (2.1 Мудборды)
                # Исполнитель продолжает работу — не нужен pending_decision
                wf.status = "in_progress"
            else:
                # UI покажет диалог выбора: круг 2 / закрыть / платный круг
                wf.status = "pending_decision"

            if not has_next_round:
                # Нет следующего круга — продвигаем current_substep_code
                last_recorded = client_entry if stage_group else None
                if last_recorded and stage_group and contract_id:
                    next_substep = (
                        db.query(ProjectTimelineEntry)
                        .filter(
                            ProjectTimelineEntry.contract_id == contract_id,
                            ProjectTimelineEntry.stage_group == stage_group,
                            ProjectTimelineEntry.executor_role.notin_(["header"]),
                            ProjectTimelineEntry.sort_order > last_recorded.sort_order,
                            or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                            or_(ProjectTimelineEntry.status.is_(None), ProjectTimelineEntry.status != "skipped"),
                        )
                        .order_by(ProjectTimelineEntry.sort_order)
                        .first()
                    )
                    if next_substep:
                        wf.current_substep_code = next_substep.stage_code
                        wf.current_substage_group = next_substep.substage_group
                        logger.info(f"client-ok: переход к {next_substep.stage_code} ({next_substep.stage_name}), подэтап: {next_substep.substage_group}")

            # Определяем is_last_round
            # Последний круг: нет следующего ROUND_PAIRS для текущего подэтапа
            LAST_ROUNDS = {"Подэтап 1.3", "Подэтап 2.7"}
            is_last_round = current_subgroup in LAST_ROUNDS
            # Для плоских стадий (stage3 инд., stage2/3 шабл.) — считать как последний круг
            if not current_subgroup or not current_subgroup.strip():
                is_last_round = True

            wf.client_approval_deadline_paused = False
            wf.revision_count = 0  # сбрасываем счётчик правок для нового подэтапа
            wf.updated_at = datetime.utcnow()

        # Определяем тип проекта (для решения о платных кругах)
        project_type = ""
        if contract_id:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            if contract:
                project_type = contract.project_type or ""

        # K11: Запись в историю
        db.add(ActionHistory(user_id=current_user.id, action_type="client_approved", entity_type="crm_card", entity_id=card_id, description=f"Клиент согласовал: {stage_name}"))

        # Обновляем дедлайн исполнителя по norm_days следующего подэтапа
        if not (wf and hasattr(wf, "status") and wf.status == "pending_decision"):
            _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        # Safety-net: синхронизировать substep с реальным состоянием таймлайна
        _sync_workflow_substep(db, card_id, stage_name, contract_id)

        db.commit()

        # Хук: уведомление в чат о согласовании клиентом
        try:
            asyncio.create_task(trigger_messenger_notification(card_id, "stage_complete", stage_name=f"{stage_name} (клиент согласовал)"))
        except Exception:
            logger.warning(f"Не удалось отправить уведомление для карточки {card_id}")

        # Личные уведомления: "Клиент согласовал" → ст.менеджер + исполнитель
        # Руководство §2/§3: тексты зависят от подэтапа и типа проекта
        try:
            contract_obj = db.query(Contract).filter(Contract.id == contract_id).first()
            address = contract_obj.address if contract_obj else ""
            pt_key = _get_project_type_key(contract_obj.project_type if contract_obj else "")
            stage_num = _extract_stage_number(stage_name)
            notif_recipients = []

            # Определяем концепцию подэтапа для Стадии 2 инд.
            _cur_sub = wf.current_substage_group if wf else ""
            concept = ""
            if stage_num == "2" and pt_key == "individual":
                concept = _get_substage_concept(_cur_sub or "")
            _is_last_viz = _cur_sub in _LAST_VIZ_SUBGROUPS

            # Текст для СМ
            if card.senior_manager_id:
                if concept == "мудборд":
                    _sm_txt = f"Клиент согласовал мудборды по проекту {address}."
                elif concept == "визуализация":
                    if _is_last_viz:
                        _sm_txt = f"Клиент согласовал Стадию 2 по проекту {address}."
                    else:
                        _sm_txt = f"Клиент согласовал визуализацию 1 помещения по проекту {address}."
                else:
                    _sm_txt = f"Клиент согласовал Стадию {stage_num} по проекту {address}."
                notif_recipients.append((card.senior_manager_id, _sm_txt))

            # Текст для исполнителя
            exec_id = _find_executor_id(db, card.id, stage_name)
            if exec_id:
                if concept == "мудборд":
                    _ex_txt = f"Клиент согласовал мудборды по проекту {address}."
                elif concept == "визуализация":
                    if _is_last_viz:
                        _ex_txt = f"Клиент согласовал визуализации всех помещений по проекту {address}."
                    else:
                        _ex_txt = f"Клиент согласовал визуализацию 1 помещения по проекту {address}."
                elif stage_num in _STAGE_TITLE_MAP and pt_key == "individual":
                    _ex_txt = f'Клиент согласовал работу по проекту {address}, стадия "{_STAGE_TITLE_MAP[stage_num]}".'
                else:
                    _ex_txt = f"Клиент согласовал Стадию {stage_num} по проекту {address}."
                notif_recipients.append((exec_id, _ex_txt))

            if notif_recipients:
                asyncio.create_task(
                    _dispatch_crm_notifications(
                        card.id,
                        "crm_stage_change",
                        notif_recipients,
                        f"Клиент согласовал: {address}",
                        pt_key,
                    )
                )
        except Exception as e:
            logger.warning(f"Ошибка уведомления client-ok: {e}")

        has_next = has_next_round if wf else False
        next_name = next_round_name if wf else None
        is_last = is_last_round if wf else False
        remaining_client = has_remaining_client if wf else False
        return {
            "status": "client_approved",
            "has_next_round": has_next,
            "next_round_name": next_name,
            "is_last_round": is_last,
            "has_remaining_client": remaining_client,
            "project_type": project_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при согласовании клиентом карточки {card_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка при согласовании: {str(e)}")


# =========================
# WORKFLOW: ADVANCE ROUND / CLOSE STAGE / ADD EXTRA ROUND
# =========================

# Пары кругов: подэтап → следующий (полная таблица из docs/workflow-guide.md)
_ROUND_PAIRS = {
    "Подэтап 1.1": "Подэтап 1.2",
    "Подэтап 1.2": "Подэтап 1.3",
    "Подэтап 2.1": "Подэтап 2.2",
    "Подэтап 2.2": "Подэтап 2.3",
    "Подэтап 2.3": "Подэтап 2.4",
    "Подэтап 2.4": "Подэтап 2.5",
    "Подэтап 2.5": "Подэтап 2.6",
    "Подэтап 2.6": "Подэтап 2.7",
}


@router.post("/cards/{card_id}/workflow/advance-round")
async def workflow_advance_round(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.complete_approval")), db: Session = Depends(get_db)):
    """Перейти к следующему кругу (например, с Подэтапа 1.2 к Подэтапу 1.3)."""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    try:
        stage_name = card.column_name
        contract_id = card.contract_id
        stage_group = _resolve_stage_group(stage_name)

        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
        if not wf:
            raise HTTPException(status_code=400, detail="Нет workflow state для этой карточки")

        current_subgroup = wf.current_substage_group
        next_subgroup = _ROUND_PAIRS.get(current_subgroup)
        if not next_subgroup:
            raise HTTPException(status_code=400, detail=f"Нет следующего круга для {current_subgroup}")

        # Записываем дату в строку "Сбор правок" текущего подэтапа
        if contract_id and stage_group and current_subgroup:
            reviewer_roles = REVIEWER_ROLES
            collection_entries = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.substage_group == current_subgroup,
                    ProjectTimelineEntry.executor_role.in_(reviewer_roles),
                    or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                )
                .order_by(ProjectTimelineEntry.sort_order)
                .all()
            )
            for entry in collection_entries:
                if "сбор правок" in (entry.stage_name or "").lower():
                    entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
                    entry.updated_at = datetime.utcnow()
                    logger.info(f"advance-round: дата 'Сбор правок' записана в {entry.stage_code} ({entry.stage_name})")
                    break

        # Находим первый подэтап следующего круга (исполнитель)
        executor_roles = [POSITION_DRAFTSMAN, POSITION_DESIGNER]
        next_entry = (
            db.query(ProjectTimelineEntry)
            .filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
                ProjectTimelineEntry.substage_group == next_subgroup,
                ProjectTimelineEntry.executor_role.in_(executor_roles),
            )
            .order_by(ProjectTimelineEntry.sort_order)
            .first()
        )

        if next_entry:
            wf.current_substep_code = next_entry.stage_code
            wf.current_substage_group = next_subgroup
        wf.status = "in_progress"
        wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(user_id=current_user.id, action_type="advance_round", entity_type="crm_card", entity_id=card_id, description=f"Переход к кругу 2: {stage_name} → {next_subgroup}"))

        # Обновляем дедлайн
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        # Safety-net: синхронизировать substep с реальным состоянием таймлайна
        _sync_workflow_substep(db, card_id, stage_name, contract_id)

        db.commit()
        return {"status": "advanced", "next_round": next_subgroup}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в advance-round: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/close-stage")
async def workflow_close_stage(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.complete_approval")), db: Session = Depends(get_db)):
    """Закрыть этап — пропустить оставшиеся круги.
    Все незаполненные подэтапы текущего stage_group помечаются как skipped."""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    try:
        stage_name = card.column_name
        contract_id = card.contract_id
        stage_group = _resolve_stage_group(stage_name)

        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()

        if stage_group and contract_id:
            # Записываем дату в строку "Сбор правок" текущего подэтапа (если есть)
            if wf and wf.current_substage_group:
                reviewer_roles = REVIEWER_ROLES
                collection_entries = (
                    db.query(ProjectTimelineEntry)
                    .filter(
                        ProjectTimelineEntry.contract_id == contract_id,
                        ProjectTimelineEntry.stage_group == stage_group,
                        ProjectTimelineEntry.substage_group == wf.current_substage_group,
                        ProjectTimelineEntry.executor_role.in_(reviewer_roles),
                        or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                    )
                    .order_by(ProjectTimelineEntry.sort_order)
                    .all()
                )
                for entry in collection_entries:
                    if "сбор правок" in (entry.stage_name or "").lower():
                        entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
                        entry.updated_at = datetime.utcnow()
                        logger.info(f"close-stage: дата 'Сбор правок' записана в {entry.stage_code} ({entry.stage_name})")
                        break

            # Помечаем все незаполненные подэтапы текущего stage_group как skipped
            unfilled = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    ProjectTimelineEntry.executor_role != "header",
                    or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                )
                .all()
            )
            for entry in unfilled:
                entry.status = "skipped"
                entry.updated_at = datetime.utcnow()

            _server_recalculate_actual_days(db, contract_id)

        if wf:
            wf.status = "act_signing"
            wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(user_id=current_user.id, action_type="close_stage", entity_type="crm_card", entity_id=card_id, description=f"Этап закрыт: {stage_name} (пропуск оставшихся кругов)"))

        # Устанавливаем дедлайн 1 рабочий день для подписания акта
        try:
            act_deadline = _add_business_days(datetime.utcnow().strftime("%Y-%m-%d"), 1)
            act_deadline_str = act_deadline.strftime("%Y-%m-%d")
            stage_execs = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name).all()
            for se in stage_execs:
                se.deadline = act_deadline_str
                logger.info(f"[close-stage] act_signing deadline → {act_deadline_str} для executor {se.executor_id}")
        except Exception as e:
            logger.warning(f"Ошибка установки дедлайна act_signing: {e}")

        db.commit()
        return {"status": "stage_closed"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в close-stage: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/sign-act")
async def workflow_sign_act(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.complete_approval")), db: Session = Depends(get_db)):
    """Подписание акта — финальный шаг стадии.
    Записывает дату в строку 'Акт' в таймлайне.
    Статус → stage_completed."""
    try:
        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="Карточка не найдена")

        stage_name = card.column_name
        contract_id = card.contract_id
        stage_group = _resolve_stage_group(stage_name)

        # Проверяем статус workflow
        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
        if not wf:
            raise HTTPException(status_code=400, detail="Workflow-состояние стадии не найдено")
        if wf.status != "act_signing":
            raise HTTPException(status_code=400, detail="Акт можно подписать только в статусе act_signing")

        # Записываем дату в строку "Акт" / "Акт подписан" / "Закрытие"
        if contract_id and stage_group:
            act_entry = (
                db.query(ProjectTimelineEntry)
                .filter(
                    ProjectTimelineEntry.contract_id == contract_id,
                    ProjectTimelineEntry.stage_group == stage_group,
                    or_(
                        ProjectTimelineEntry.stage_name.ilike("%акт%"),
                        ProjectTimelineEntry.stage_name.ilike("%закрытие%"),
                        ProjectTimelineEntry.stage_name.ilike("%принятие%"),
                    ),
                    or_(ProjectTimelineEntry.actual_date.is_(None), ProjectTimelineEntry.actual_date == ""),
                )
                .order_by(ProjectTimelineEntry.sort_order.desc())
                .first()
            )

            if act_entry:
                act_entry.actual_date = datetime.utcnow().strftime("%Y-%m-%d")
                act_entry.updated_at = datetime.utcnow()
                logger.info(f"sign-act: дата акта записана в {act_entry.stage_code} ({act_entry.stage_name})")

            _server_recalculate_actual_days(db, contract_id)

        # Обновляем workflow state
        if wf:
            wf.status = "stage_completed"
            wf.updated_at = datetime.utcnow()

        # K11: Запись в историю
        db.add(ActionHistory(user_id=current_user.id, action_type="sign_act", entity_type="crm_card", entity_id=card_id, description=f"Акт подписан: {stage_name}"))

        # Обновляем дедлайн для следующего этапа
        _update_executor_deadline_for_next_substep(db, card_id, stage_name, contract_id)

        # === Обновляем report_month у Доплаты при завершении стадии ===
        try:
            current_month = datetime.utcnow().strftime("%Y-%m")
            from database import Contract
            from database import Payment as PaymentModel

            contract_for_pm = db.query(Contract).filter(Contract.id == contract_id).first()
            if contract_for_pm:
                # Находим исполнителя стадии
                executor = (
                    db.query(StageExecutor)
                    .filter(
                        StageExecutor.crm_card_id == card_id,
                        StageExecutor.stage_name == stage_name,
                    )
                    .first()
                )
                executor_id = executor.executor_id if executor else None

                if executor_id:
                    if contract_for_pm.project_type == "Индивидуальный":
                        # Доплата исполнителя — report_month = месяц подписания акта
                        payments = (
                            db.query(PaymentModel)
                            .filter(PaymentModel.contract_id == contract_id, PaymentModel.employee_id == executor_id, PaymentModel.stage_name == stage_name, PaymentModel.payment_type == "Доплата")
                            .all()
                        )
                        for p in payments:
                            p.report_month = current_month
                            logger.info(f"[sign-act] report_month Доплата → {current_month}, payment={p.id}")

                    elif contract_for_pm.project_type == "Шаблонный":
                        # Для шаблонных — Полная оплата
                        sl = stage_name.lower()
                        if "концепция" in sl or "дизайн" in sl or "визуализац" in sl:
                            executor_role_name = "Дизайнер"
                        else:
                            executor_role_name = "Чертёжник"

                        can_set_month = True
                        if executor_role_name == "Чертёжник":
                            accepted_count = (
                                db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.executor_id == executor_id, StageExecutor.submitted_date.isnot(None)).count()
                            )
                            if accepted_count < 2:
                                can_set_month = False

                        if can_set_month:
                            payments = (
                                db.query(PaymentModel)
                                .filter(
                                    PaymentModel.contract_id == contract_id,
                                    PaymentModel.employee_id == executor_id,
                                    PaymentModel.stage_name == stage_name,
                                    PaymentModel.payment_type == "Полная оплата",
                                )
                                .all()
                            )
                            for p in payments:
                                p.report_month = current_month
                                logger.info(f"[sign-act] report_month Полная оплата → {current_month}, payment={p.id}")
        except Exception as e:
            logger.warning(f"[sign-act] Ошибка обновления report_month: {e}")

        db.commit()

        # Хук: уведомление в чат о подписании акта
        try:
            asyncio.create_task(trigger_messenger_notification(card_id, "stage_complete", stage_name=f"{stage_name} (акт подписан)"))
        except Exception:
            logger.warning(f"Не удалось отправить уведомление sign-act для карточки {card_id}")

        # Личные уведомления: "Акт подписан" → reviewer + SM (для шаблонных)
        # Руководство §2/§3: тексты зависят от типа проекта и стадии
        try:
            contract = db.query(Contract).filter(Contract.id == contract_id).first()
            address = contract.address if contract else ""
            pt_key = _get_project_type_key(contract.project_type if contract else "")
            sl = stage_name.lower()
            if "рабочие чертежи" in sl or "рабочая документация" in sl:
                reviewer_id = card.gap_id
            elif pt_key == "template" and ("планировочн" in sl or "3д" in sl or "визуализац" in sl):
                reviewer_id = card.manager_id
            else:
                reviewer_id = card.sdp_id
            notif_recipients = []
            sent_ids = set()
            _act_stage_num = _extract_stage_number(stage_name)
            # Определить текст по руководству
            if pt_key == "template" and ("3д" in sl or "визуализац" in sl):
                # Шаблонные Стадия 3: "Стадия 3 проекта {address} завершена."
                act_text = f"Стадия 3 проекта {address} завершена."
            elif _act_stage_num == "3":
                # Инд. Стадия 3: "Акт по Стадии 3 подписан. Проект завершён."
                act_text = f"Акт по Стадии {_act_stage_num} проекта {address} подписан. Проект завершён."
            else:
                act_text = f"Акт по Стадии {_act_stage_num} проекта {address} подписан."
            if reviewer_id:
                notif_recipients.append((reviewer_id, act_text))
                sent_ids.add(reviewer_id)
            # Шаблонные: SM тоже получает уведомление (руководство §3)
            if pt_key == "template" and card.senior_manager_id and card.senior_manager_id not in sent_ids:
                notif_recipients.append((card.senior_manager_id, act_text))
                sent_ids.add(card.senior_manager_id)
            if notif_recipients:
                asyncio.create_task(
                    _dispatch_crm_notifications(
                        card.id,
                        "crm_stage_change",
                        notif_recipients,
                        f"Акт подписан: {address}",
                        pt_key,
                    )
                )
        except Exception as e:
            logger.warning(f"Ошибка уведомления sign-act: {e}")

        return {"status": "act_signed", "stage_completed": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в workflow/sign-act: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/workflow/add-extra-round")
async def workflow_add_extra_round(card_id: int, request: Request, current_user: Employee = Depends(require_permission("crm_cards.complete_approval")), db: Session = Depends(get_db)):
    """Добавить дополнительный платный круг правок в таймлайн.
    Вставляет новые подэтапы: работа исполнителя + проверка reviewer + отправка клиенту."""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    try:
        body = await request.json()
    except Exception:
        body = {}

    stage_name = body.get("stage_name", card.column_name)
    executor_role = body.get("executor_role", POSITION_DRAFTSMAN)
    reviewer_role = body.get("reviewer_role", POSITION_SDP)
    norm_days_work = body.get("norm_days_work", 3)
    norm_days_review = body.get("norm_days_review", 1)

    try:
        contract_id = card.contract_id
        stage_group = _resolve_stage_group(stage_name)
        if not stage_group or not contract_id:
            raise HTTPException(status_code=400, detail="Не удалось определить stage_group")

        # Находим последнюю запись в текущем stage_group
        last_entry = (
            db.query(ProjectTimelineEntry)
            .filter(
                ProjectTimelineEntry.contract_id == contract_id,
                ProjectTimelineEntry.stage_group == stage_group,
            )
            .order_by(ProjectTimelineEntry.sort_order.desc())
            .first()
        )

        if not last_entry:
            raise HTTPException(status_code=400, detail="Нет записей в таймлайне для этого этапа")

        base_sort = last_entry.sort_order
        stage_num = stage_group.replace("STAGE", "")

        # Считаем количество существующих доп. кругов
        ext_count = (
            db.query(ProjectTimelineEntry)
            .filter(ProjectTimelineEntry.contract_id == contract_id, ProjectTimelineEntry.stage_group == stage_group, ProjectTimelineEntry.stage_code.like(f"%_EXT_%"))
            .count()
        )
        ext_num = ext_count + 1

        # Сдвигаем sort_order всех записей ПОСЛЕ текущего stage_group
        entries_after = db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id, ProjectTimelineEntry.sort_order > base_sort).all()
        for ea in entries_after:
            ea.sort_order += 6  # W2: 6 строк вместо 4

        # Prefix для stage_code (S для индивидуальных, T для шаблонных)
        prefix = last_entry.stage_code[0] if last_entry.stage_code else "S"

        # W2: Вставляем 6 новых записей (header + работа + проверка + правка + повторная проверка + согласование)
        new_entries = [
            ProjectTimelineEntry(
                contract_id=contract_id,
                stage_code=f"{prefix}{stage_num}_EXT{ext_num}_HDR",
                stage_name=f"Доп. круг {ext_num} (платный)",
                stage_group=stage_group,
                substage_group=f"Доп. круг {ext_num}",
                norm_days=0,
                executor_role="header",
                is_in_contract_scope=False,
                sort_order=base_sort + 1,
            ),
            ProjectTimelineEntry(
                contract_id=contract_id,
                stage_code=f"{prefix}{stage_num}_EXT{ext_num}_01",
                stage_name=f"Работа ({executor_role.lower()})",
                stage_group=stage_group,
                substage_group=f"Доп. круг {ext_num}",
                norm_days=norm_days_work,
                executor_role=executor_role,
                is_in_contract_scope=False,
                sort_order=base_sort + 2,
            ),
            ProjectTimelineEntry(
                contract_id=contract_id,
                stage_code=f"{prefix}{stage_num}_EXT{ext_num}_02",
                stage_name=f"Проверка ({reviewer_role})",
                stage_group=stage_group,
                substage_group=f"Доп. круг {ext_num}",
                norm_days=norm_days_review,
                executor_role=reviewer_role,
                is_in_contract_scope=False,
                sort_order=base_sort + 3,
            ),
            ProjectTimelineEntry(
                contract_id=contract_id,
                stage_code=f"{prefix}{stage_num}_EXT{ext_num}_03",
                stage_name=f"Правка ({executor_role.lower()})",
                stage_group=stage_group,
                substage_group=f"Доп. круг {ext_num}",
                norm_days=norm_days_work,
                executor_role=executor_role,
                is_in_contract_scope=False,
                sort_order=base_sort + 4,
            ),
            ProjectTimelineEntry(
                contract_id=contract_id,
                stage_code=f"{prefix}{stage_num}_EXT{ext_num}_04",
                stage_name=f"Проверка повторная ({reviewer_role})",
                stage_group=stage_group,
                substage_group=f"Доп. круг {ext_num}",
                norm_days=norm_days_review,
                executor_role=reviewer_role,
                is_in_contract_scope=False,
                sort_order=base_sort + 5,
            ),
            ProjectTimelineEntry(
                contract_id=contract_id,
                stage_code=f"{prefix}{stage_num}_EXT{ext_num}_05",
                stage_name="Отправка клиенту / Согласование",
                stage_group=stage_group,
                substage_group=f"Доп. круг {ext_num}",
                norm_days=3,
                executor_role="Клиент",
                is_in_contract_scope=False,
                sort_order=base_sort + 6,
            ),
        ]
        for ne in new_entries:
            db.add(ne)

        # Обновить wf.status и current_substep_code (руководство §8)
        # После создания платного круга исполнитель должен начать работу
        wf = db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id, StageWorkflowState.stage_name == stage_name).first()
        if wf:
            wf.status = "in_progress"
            wf.current_substep_code = f"{prefix}{stage_num}_EXT{ext_num}_01"
            wf.current_substage_group = f"Доп. круг {ext_num}"
            wf.updated_at = datetime.utcnow()
        else:
            wf = StageWorkflowState(
                crm_card_id=card_id,
                stage_name=stage_name,
                status="in_progress",
                current_substep_code=f"{prefix}{stage_num}_EXT{ext_num}_01",
                current_substage_group=f"Доп. круг {ext_num}",
            )
            db.add(wf)

        # K11: Запись в историю
        db.add(ActionHistory(user_id=current_user.id, action_type="add_extra_round", entity_type="crm_card", entity_id=card_id, description=f"Добавлен доп. круг {ext_num}: {stage_name}"))

        # Flush для того чтобы новые entries были видны в sync
        db.flush()

        # Safety-net: синхронизировать substep с реальным состоянием таймлайна
        _sync_workflow_substep(db, card_id, stage_name, contract_id)

        db.commit()
        return {"status": "extra_round_added", "round_number": ext_num}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка в add-extra-round: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =========================
# CRM EXTENDED ENDPOINTS (Designer/Draftsman Reset)
# =========================


@router.post("/cards/{card_id}/reset-designer")
async def reset_designer_completion(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.reset_designer")), db: Session = Depends(get_db)):
    """Сбросить отметку о завершении дизайнером"""
    try:
        # ИСПРАВЛЕНИЕ 06.02.2026: Добавлен поиск по '3д визуализация' для шаблонных проектов (#10)
        designer_executor = (
            db.query(StageExecutor)
            .filter(StageExecutor.crm_card_id == card_id, or_(StageExecutor.stage_name.ilike("%концепция%"), StageExecutor.stage_name.ilike("%визуализация%")))
            .order_by(StageExecutor.id.desc())
            .first()
        )

        if designer_executor:
            designer_executor.completed = False
            designer_executor.completed_date = None

            # Бизнес-история сброса дизайнера
            executor_emp = db.query(Employee).filter(Employee.id == designer_executor.executor_id).first()
            executor_name = executor_emp.full_name if executor_emp else f"ID {designer_executor.executor_id}"
            db.add(
                ActionHistory(
                    user_id=current_user.id,
                    action_type="designer_reset",
                    entity_type="crm_card",
                    entity_id=card_id,
                    description=f"Сброшена отметка дизайнера: {executor_name}, стадия «{designer_executor.stage_name}»",
                )
            )

            db.commit()

        return {"status": "success", "message": "Отметка дизайнера сброшена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе отметки дизайнера: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/reset-draftsman")
async def reset_draftsman_completion(card_id: int, current_user: Employee = Depends(require_permission("crm_cards.reset_draftsman")), db: Session = Depends(get_db)):
    """Сбросить отметку о завершении чертежником"""
    try:
        # Находим назначение чертежника
        draftsman_executor = (
            db.query(StageExecutor)
            .filter(StageExecutor.crm_card_id == card_id, or_(StageExecutor.stage_name.ilike("%чертежи%"), StageExecutor.stage_name.ilike("%планировочные%")))
            .order_by(StageExecutor.id.desc())
            .first()
        )

        if draftsman_executor:
            draftsman_executor.completed = False
            draftsman_executor.completed_date = None

            # Бизнес-история сброса чертёжника
            executor_emp = db.query(Employee).filter(Employee.id == draftsman_executor.executor_id).first()
            executor_name = executor_emp.full_name if executor_emp else f"ID {draftsman_executor.executor_id}"
            db.add(
                ActionHistory(
                    user_id=current_user.id,
                    action_type="draftsman_reset",
                    entity_type="crm_card",
                    entity_id=card_id,
                    description=f"Сброшена отметка чертёжника: {executor_name}, стадия «{draftsman_executor.stage_name}»",
                )
            )

            db.commit()

        return {"status": "success", "message": "Отметка чертежника сброшена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при сбросе отметки чертежника: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/approval-deadlines")
async def get_approval_stage_deadlines(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить дедлайны стадий согласования"""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM карточка не найдена")

    # Возвращаем данные о согласовании
    return {
        "card_id": card_id,
        "is_approved": card.is_approved,
        "approval_deadline": str(card.approval_deadline) if card.approval_deadline else None,
        "approval_stages": json.loads(card.approval_stages) if card.approval_stages else None,
    }


@router.post("/cards/{card_id}/complete-approval-stage")
async def complete_approval_stage(card_id: int, body: CompleteApprovalStageRequest, current_user: Employee = Depends(require_permission("crm_cards.complete_approval")), db: Session = Depends(get_db)):
    """Завершить стадию согласования"""
    try:
        stage_name = body.stage_name

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")

        # Обновляем approval_stages (JSON)
        current_stages = json.loads(card.approval_stages) if card.approval_stages else {}
        current_stages[stage_name] = {"completed": True, "completed_date": datetime.utcnow().isoformat(), "completed_by": current_user.id}
        card.approval_stages = json.dumps(current_stages)

        # Авто-установка is_approved когда текущая стадия согласована
        if stage_name == card.column_name:
            card.is_approved = True

        # Бизнес-история завершения согласования
        db.add(
            ActionHistory(
                user_id=current_user.id,
                action_type="approval_completed",
                entity_type="crm_card",
                entity_id=card_id,
                description=f"Завершена стадия согласования: «{stage_name}»" + (" (карточка согласована)" if card.is_approved else ""),
            )
        )

        db.commit()

        return {"status": "success", "stage_name": stage_name, "completed": True, "is_approved": card.is_approved}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при завершении стадии согласования: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/stage-executor-deadline")
async def update_stage_executor_deadline(card_id: int, body: StageExecutorDeadlineRequest, current_user: Employee = Depends(require_permission("crm_cards.deadlines")), db: Session = Depends(get_db)):
    """Обновить дедлайн исполнителя стадии"""
    try:
        stage_name = body.stage_name
        deadline = body.deadline

        # С1: Точное совпадение stage_name вместо ILIKE
        stage_executor = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name).order_by(StageExecutor.id.desc()).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail="Назначение стадии не найдено")

        from datetime import datetime as dt

        old_deadline = str(stage_executor.deadline) if stage_executor.deadline else "не установлен"
        stage_executor.deadline = dt.fromisoformat(deadline).strftime("%Y-%m-%d") if deadline else None
        new_deadline = deadline if deadline else "снят"

        # Бизнес-история изменения дедлайна
        executor_emp = db.query(Employee).filter(Employee.id == stage_executor.executor_id).first()
        executor_name = executor_emp.full_name if executor_emp else f"ID {stage_executor.executor_id}"
        db.add(
            ActionHistory(
                user_id=current_user.id,
                action_type="deadline_changed",
                entity_type="crm_card",
                entity_id=card_id,
                description=f"Изменён дедлайн: «{stage_name}», исполнитель: {executor_name}, {old_deadline} → {new_deadline}",
            )
        )

        db.commit()

        return {"status": "success", "stage_name": stage_executor.stage_name, "deadline": deadline}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении дедлайна исполнителя стадии: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/cards/{card_id}/stage-executor/{stage_name}/complete")
async def complete_stage_for_executor(card_id: int, stage_name: str, body: CompleteStageExecutorRequest, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Отметить стадию как выполненную для исполнителя"""
    try:
        executor_id = body.executor_id

        # Проверка прав: назначенный на карточку, исполнитель стадии или суперпользователь
        from permissions import SUPERUSER_ROLES

        card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
        if not card:
            raise HTTPException(status_code=404, detail="CRM карточка не найдена")
        is_card_member = current_user.id in [card.senior_manager_id, card.sdp_id, card.gap_id, card.manager_id]
        is_stage_executor = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.executor_id == current_user.id).first() is not None
        is_superuser = current_user.role in SUPERUSER_ROLES
        if not (is_card_member or is_stage_executor or is_superuser):
            raise HTTPException(status_code=403, detail="Недостаточно прав для завершения стадии")

        stage_executor = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id, StageExecutor.stage_name == stage_name, StageExecutor.executor_id == executor_id).first()

        if not stage_executor:
            raise HTTPException(status_code=404, detail=f"Назначение стадии не найдено: card_id={card_id}, stage_name={stage_name}, executor_id={executor_id}")

        stage_executor.completed = True
        stage_executor.completed_date = datetime.utcnow()

        # Бизнес-история завершения стадии исполнителем
        executor_emp = db.query(Employee).filter(Employee.id == executor_id).first()
        executor_name = executor_emp.full_name if executor_emp else f"ID {executor_id}"
        db.add(
            ActionHistory(
                user_id=current_user.id, action_type="executor_completed", entity_type="crm_card", entity_id=card_id, description=f"Исполнитель завершил стадию: {executor_name}, «{stage_name}»"
            )
        )

        db.commit()

        return {"status": "success", "stage_name": stage_name, "completed": True}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при завершении стадии исполнителем: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cards/{card_id}/previous-executor")
async def get_previous_executor_by_position(card_id: int, position: str, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить предыдущего исполнителя по должности"""
    try:
        # Находим назначение для этой должности
        stage_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).order_by(StageExecutor.id.desc()).all()

        for se in stage_executors:
            employee = db.query(Employee).filter(Employee.id == se.executor_id).first()
            if employee and employee.position == position:
                return {"executor_id": se.executor_id, "executor_name": employee.full_name}

        return {"executor_id": None}

    except Exception as e:
        logger.exception(f"Ошибка при получении предыдущего исполнителя по должности: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/cards/{card_id}/manager-acceptance")
async def save_manager_acceptance(card_id: int, body: ManagerAcceptanceRequest, current_user: Employee = Depends(require_permission("crm_cards.move")), db: Session = Depends(get_db)):
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
        history = ActionHistory(user_id=manager_id, action_type="acceptance", entity_type="stage", entity_id=card_id, description=f"Принятие работы: {stage_name} от {executor_name}")
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
async def get_accepted_stages(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список принятых стадий"""
    history = db.query(ActionHistory).filter(ActionHistory.entity_type == "stage", ActionHistory.entity_id == card_id, ActionHistory.action_type == "acceptance").all()

    return [{"id": h.id, "stage_name": h.description, "accepted_by": h.user_id, "accepted_date": h.action_date.isoformat() if h.action_date else None} for h in history]


@router.post("/cards/{card_id}/invite-client")
async def invite_client_to_chat(card_id: int, current_user: Employee = Depends(require_permission("messenger.create_chat")), db: Session = Depends(get_db)):
    """Отправить клиенту email-приглашение в проектный Telegram-чат"""
    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="CRM карточка не найдена")

    contract = db.query(Contract).filter(Contract.id == card.contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    client = db.query(Client).filter(Client.id == contract.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Клиент не найден")

    if not client.email:
        raise HTTPException(status_code=422, detail="Email клиента не заполнен")

    # Найти чат проекта
    chat = db.query(MessengerChat).filter(MessengerChat.crm_card_id == card_id, MessengerChat.is_active == True).first()
    if not chat:
        raise HTTPException(status_code=422, detail="Чат проекта не создан")

    if not chat.invite_link:
        raise HTTPException(status_code=422, detail="Ссылка-приглашение для чата не сформирована")

    # Отправить письмо
    try:
        from email_service import get_email_service

        email_svc = get_email_service()
        manager_name = current_user.full_name
        project_type = getattr(contract, "project_type", "Интерьерный проект")
        project_address = getattr(contract, "address", card.address or "")
        sent = await email_svc.send_client_chat_invite(
            to_email=client.email,
            client_name=client.full_name or client.email,
            project_address=project_address,
            project_type=project_type or "Интерьерный проект",
            manager_name=manager_name,
            invite_link=chat.invite_link,
        )
        if sent:
            return {"ok": True, "message": f"Приглашение отправлено на {client.email}"}
        else:
            raise HTTPException(status_code=503, detail="Email-сервис недоступен")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"invite_client_to_chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ========== СБРОС КАРТОЧКИ ДО НАЧАЛЬНОГО СОСТОЯНИЯ ==========


@router.post("/{card_id}/reset")
async def reset_crm_card(card_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Сброс карточки CRM до начального состояния (только для руководителей)"""

    # Проверка прав — только руководитель студии
    if current_user.position != "Руководитель студии":
        raise HTTPException(status_code=403, detail="Сброс доступен только руководителю студии")

    card = db.query(CRMCard).filter(CRMCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="Карточка не найдена")

    contract_id = card.contract_id

    try:
        # 1. Удаляем всех исполнителей стадий
        db.query(StageExecutor).filter(StageExecutor.crm_card_id == card_id).delete()

        # 2. Удаляем все оплаты
        db.query(Payment).filter(Payment.crm_card_id == card_id).delete()

        # 3. Удаляем файлы проекта (из БД, Yandex Disk очистка — опционально)
        files = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).all()
        # Попытка удалить файлы с Яндекс.Диска
        try:
            from yandex_disk_service import get_yandex_disk_service

            yd = get_yandex_disk_service()
            for f in files:
                if f.yandex_path:
                    try:
                        yd.delete_file(f.yandex_path, permanently=False)
                    except Exception:
                        pass  # Файл мог быть уже удален
        except Exception:
            pass  # Yandex Disk недоступен
        db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).delete()

        # 4. Удаляем workflow состояния
        db.query(StageWorkflowState).filter(StageWorkflowState.crm_card_id == card_id).delete()

        # 5. Удаляем дедлайны согласования
        db.query(ApprovalStageDeadline).filter(ApprovalStageDeadline.crm_card_id == card_id).delete()

        # 6. Сбрасываем таблицу сроков (actual_date → NULL)
        db.query(ProjectTimelineEntry).filter(ProjectTimelineEntry.contract_id == contract_id).update({ProjectTimelineEntry.actual_date: None, ProjectTimelineEntry.status: "pending"})

        # 7. Удаляем всю историю действий
        db.query(ActionHistory).filter(ActionHistory.entity_type == "crm_card", ActionHistory.entity_id == card_id).delete()

        # 8. Сбрасываем поля карточки
        card.column_name = "Новый заказ"
        card.previous_column = None
        card.survey_date = None
        card.surveyor_id = None
        card.tech_task_file = None
        card.tech_task_date = None
        card.project_data_link = None
        card.deadline = None
        card.paused_at = None
        card.total_pause_days = 0
        card.tags = None
        # Сбрасываем назначенных сотрудников
        card.manager_id = None
        card.senior_manager_id = None
        card.designer_id = None
        card.draftsman_id = None
        card.sdp_id = None
        card.gap_id = None

        # 9. Сбрасываем поля замера в договоре
        contract = db.query(Contract).filter(Contract.id == contract_id).first()
        if contract:
            contract.measurement_date = None
            contract.measurement_image_link = None
            contract.measurement_file_name = None
            contract.measurement_yandex_path = None

        # 10. Записываем единственную запись в историю — "Сброс карточки"
        db.add(
            ActionHistory(
                user_id=current_user.id,
                action_type="card_reset",
                entity_type="crm_card",
                entity_id=card_id,
                description=f"Карточка сброшена до начального состояния пользователем {current_user.full_name}",
            )
        )

        db.commit()

        logger.info(f"CRM card {card_id} reset by {current_user.full_name}")
        return {"ok": True, "message": "Карточка успешно сброшена"}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"reset_crm_card error: {e}")
        raise HTTPException(status_code=500, detail=f"Ошибка сброса: {str(e)}")
