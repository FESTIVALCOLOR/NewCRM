"""
Роутер для endpoint'ов статистики и отчётов.
Подключается в main.py через app.include_router(statistics_router, prefix="/api/statistics").
"""

from collections import defaultdict
from datetime import datetime
import json
import logging
from typing import Optional

from auth import get_current_user
from constants import (
    ARCHIVE_STATUSES,
    INACTIVE_STATUSES,
    STATUS_COMPLETED,
    STATUS_SUPERVISION,
    STATUS_TERMINATED,
)
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Date, and_, case, cast, extract, func
from sqlalchemy.orm import Session

from database import ClientSurvey, Contract, CRMCard, Employee, Payment, Salary, StageExecutor, SupervisionCard, SupervisionVisit, get_db

logger = logging.getLogger(__name__)
router = APIRouter(tags=["statistics"])


def _apply_quarter_filter(query, date_field, quarter: int, year: int = None):
    """Применить фильтр по кварталу к SQLAlchemy-запросу"""
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    query = query.filter(extract("month", date_field).between(start_month, end_month))
    if year:
        query = query.filter(extract("year", date_field) == year)
    return query


# =========================
# СТАТИСТИКА И ОТЧЕТЫ
# =========================


@router.get("/dashboard")
async def get_dashboard_statistics(
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику для дашборда"""
    try:
        # Базовый запрос договоров
        query = db.query(Contract)

        # Фильтры
        if year:
            query = query.filter(extract("year", Contract.created_at) == year)
        if month:
            query = query.filter(extract("month", Contract.created_at) == month)
        if quarter:
            query = _apply_quarter_filter(query, Contract.created_at, quarter)
        if agent_type and agent_type != "Все":
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != "Все":
            query = query.filter(Contract.city == city)

        contracts = query.all()

        # Подсчет статистики
        total_contracts = len(contracts)
        total_amount = sum(c.total_amount or 0 for c in contracts)
        total_area = sum(c.area or 0 for c in contracts)

        # По типам проектов
        individual_count = len([c for c in contracts if c.project_type == "Индивидуальный"])
        template_count = len([c for c in contracts if c.project_type == "Шаблонный"])

        # По статусам
        status_counts = {}
        for c in contracts:
            status = c.status or "Новый заказ"
            status_counts[status] = status_counts.get(status, 0) + 1

        # По городам
        city_counts = {}
        for c in contracts:
            c_city = c.city or "Не указан"
            city_counts[c_city] = city_counts.get(c_city, 0) + 1

        # По месяцам (для графиков)
        monthly_data = {}
        for c in contracts:
            if c.created_at:
                month_key = c.created_at.strftime("%Y-%m")
                if month_key not in monthly_data:
                    monthly_data[month_key] = {"count": 0, "amount": 0}
                monthly_data[month_key]["count"] += 1
                monthly_data[month_key]["amount"] += c.total_amount or 0

        # Активные CRM карточки
        active_cards = db.query(CRMCard).join(Contract).filter(~Contract.status.in_(ARCHIVE_STATUSES)).count()

        # Карточки надзора
        supervision_cards = db.query(SupervisionCard).join(Contract).filter(Contract.status == STATUS_SUPERVISION).count()

        return {
            "total_contracts": total_contracts,
            "total_amount": total_amount,
            "total_area": total_area,
            "individual_count": individual_count,
            "template_count": template_count,
            "status_counts": status_counts,
            "city_counts": city_counts,
            "monthly_data": monthly_data,
            "active_crm_cards": active_cards,
            "supervision_cards": supervision_cards,
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики дашборда: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/employees")
async def get_employee_statistics(
    year: Optional[int] = None,
    month: Optional[int] = None,
    quarter: Optional[int] = None,
    project_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику по сотрудникам. project_type: individual | template | supervision"""
    try:
        employees = db.query(Employee).filter(Employee.status == "активный").all()
        emp_ids = [emp.id for emp in employees]

        if not emp_ids:
            return []

        # project_type param: 'individual' | 'template' | 'supervision' | None (all)
        _CRM_PT = {"individual": "Индивидуальный", "template": "Шаблонный"}

        # Batch-load stage executor counts to avoid N+1 queries
        # Для supervision StageExecutor не используется → нули
        if project_type == "supervision":
            stage_map: dict = {}
        else:
            stage_query = db.query(
                StageExecutor.executor_id,
                func.count(StageExecutor.id).label("total"),
                func.count(case((StageExecutor.completed == True, 1))).label("completed"),
            ).filter(StageExecutor.executor_id.in_(emp_ids))

            # Фильтр по типу проекта — JOIN с Contract
            if project_type in _CRM_PT:
                stage_query = (
                    stage_query.join(CRMCard, StageExecutor.crm_card_id == CRMCard.id).join(Contract, CRMCard.contract_id == Contract.id).filter(Contract.project_type == _CRM_PT[project_type])
                )

            if year:
                stage_query = stage_query.filter(extract("year", StageExecutor.assigned_date) == year)
            if quarter:
                _q_start = (quarter - 1) * 3 + 1
                _q_end = quarter * 3
                stage_query = stage_query.filter(extract("month", StageExecutor.assigned_date).between(_q_start, _q_end))
            if month:
                stage_query = stage_query.filter(extract("month", StageExecutor.assigned_date) == month)

            stage_counts = stage_query.group_by(StageExecutor.executor_id).all()
            stage_map = {sc[0]: {"total": sc[1], "completed": sc[2]} for sc in stage_counts}

        # Batch-load salary totals to avoid N+1 queries
        salary_query = db.query(Salary.employee_id, func.sum(Salary.amount).label("total")).filter(Salary.employee_id.in_(emp_ids))

        if year and month:
            report_month_str = f"{year}-{month:02d}"
            salary_query = salary_query.filter(Salary.report_month == report_month_str)

        salary_totals = salary_query.group_by(Salary.employee_id).all()
        salary_map = {st[0]: float(st[1]) if st[1] else 0 for st in salary_totals}

        def _r(v):
            return round(float(v), 1) if v is not None else None

        # CRM survey scores (StageExecutor → CRMCard → Contract → ClientSurvey)
        # Skipped when viewing supervision tab — those surveys come via dan_id path
        if project_type != "supervision":
            _crm_filters = [StageExecutor.executor_id.in_(emp_ids), ClientSurvey.status == "completed"]
            if project_type in _CRM_PT:
                _crm_filters.append(Contract.project_type == _CRM_PT[project_type])
            crm_survey_subq = (
                db.query(
                    StageExecutor.executor_id,
                    ClientSurvey.nps_score,
                    ClientSurvey.csat_score,
                    ClientSurvey.design_score,
                    ClientSurvey.deadline_score,
                    ClientSurvey.communication_score,
                    ClientSurvey.expectations_score,
                )
                .join(CRMCard, StageExecutor.crm_card_id == CRMCard.id)
                .join(Contract, CRMCard.contract_id == Contract.id)
                .join(ClientSurvey, ClientSurvey.contract_id == Contract.id)
                .filter(*_crm_filters)
                .distinct()
                .subquery()
            )
            crm_survey_rows = (
                db.query(
                    crm_survey_subq.c.executor_id,
                    func.avg(crm_survey_subq.c.nps_score).label("avg_nps"),
                    func.avg(crm_survey_subq.c.csat_score).label("avg_csat"),
                    func.avg(crm_survey_subq.c.design_score).label("avg_design"),
                    func.avg(crm_survey_subq.c.deadline_score).label("avg_deadline"),
                    func.avg(crm_survey_subq.c.communication_score).label("avg_communication"),
                    func.avg(crm_survey_subq.c.expectations_score).label("avg_expectations"),
                )
                .group_by(crm_survey_subq.c.executor_id)
                .all()
            )
        else:
            crm_survey_rows = []

        survey_map = {
            row[0]: {
                "avg_nps": _r(row[1]),
                "avg_csat": _r(row[2]),
                "avg_design": _r(row[3]),
                "avg_deadline": _r(row[4]),
                "avg_communication": _r(row[5]),
                "avg_expectations": _r(row[6]),
                "avg_supervision": None,
            }
            for row in crm_survey_rows
        }

        # Supervision survey scores (SupervisionCard.dan_id → Contract → ClientSurvey)
        # Only relevant for supervision tab or general view (no project_type filter)
        if project_type in (None, "supervision"):
            sup_survey_subq = (
                db.query(
                    SupervisionCard.dan_id.label("executor_id"),
                    ClientSurvey.nps_score,
                    ClientSurvey.csat_score,
                    ClientSurvey.design_score,
                    ClientSurvey.deadline_score,
                    ClientSurvey.expectations_score,
                    ClientSurvey.supervision_score,
                )
                .join(Contract, SupervisionCard.contract_id == Contract.id)
                .join(ClientSurvey, ClientSurvey.contract_id == Contract.id)
                .filter(
                    SupervisionCard.dan_id.in_(emp_ids),
                    ClientSurvey.status == "completed",
                    ClientSurvey.project_type == "supervision",
                )
                .distinct()
                .subquery()
            )
            sup_survey_rows = (
                db.query(
                    sup_survey_subq.c.executor_id,
                    func.avg(sup_survey_subq.c.nps_score).label("avg_nps"),
                    func.avg(sup_survey_subq.c.csat_score).label("avg_csat"),
                    func.avg(sup_survey_subq.c.design_score).label("avg_design"),
                    func.avg(sup_survey_subq.c.deadline_score).label("avg_deadline"),
                    func.avg(sup_survey_subq.c.expectations_score).label("avg_expectations"),
                    func.avg(sup_survey_subq.c.supervision_score).label("avg_supervision"),
                )
                .group_by(sup_survey_subq.c.executor_id)
                .all()
            )
            for row in sup_survey_rows:
                eid = row[0]
                sup_data = {
                    "avg_nps": _r(row[1]),
                    "avg_csat": _r(row[2]),
                    "avg_design": _r(row[3]),
                    "avg_deadline": _r(row[4]),
                    "avg_communication": None,
                    "avg_expectations": _r(row[5]),
                    "avg_supervision": _r(row[6]),
                }
                if eid in survey_map:
                    for key, val in sup_data.items():
                        if val is not None:
                            survey_map[eid][key] = val
                else:
                    survey_map[eid] = sup_data

        # Visit stats (matched by executor_name string) — only for supervision view
        if project_type in (None, "supervision"):
            today_str = datetime.utcnow().date().isoformat()
            visit_rows = (
                db.query(
                    SupervisionVisit.executor_name,
                    SupervisionVisit.visit_type,
                    func.count(SupervisionVisit.id).label("cnt"),
                    func.sum(
                        case(
                            (and_(SupervisionVisit.actual_date.is_(None), SupervisionVisit.visit_date < today_str), 1),
                            else_=0,
                        )
                    ).label("overdue"),
                )
                .filter(SupervisionVisit.executor_name.isnot(None))
                .group_by(SupervisionVisit.executor_name, SupervisionVisit.visit_type)
                .all()
            )
            visit_raw: dict = defaultdict(lambda: {"total": 0, "object": 0, "supplier": 0, "overdue": 0})
            for name, vtype, cnt, overdue in visit_rows:
                if name:
                    visit_raw[name]["total"] += cnt
                    visit_raw[name]["overdue"] += overdue or 0
                    if vtype == "К поставщику":
                        visit_raw[name]["supplier"] += cnt
                    else:
                        visit_raw[name]["object"] += cnt
            visit_map = {emp.id: dict(visit_raw[emp.full_name]) for emp in employees if emp.full_name and emp.full_name in visit_raw}
        else:
            visit_map = {}

        # Подсчёт карточек для управленческих ролей (ГАП, СДП, Менеджер, Старший менеджер).
        # Эти роли хранятся как FK-поля на CRMCard, а не в StageExecutor.
        # Факт выполнения = карточка в "Выполненный проект" или договор в архивном статусе.
        # Период НЕ применяется — управленческие роли назначаются на весь срок проекта.
        emp_id_set = set(emp_ids)
        card_role_map: dict = {}

        if project_type in (None, "individual", "template"):
            card_q = db.query(
                CRMCard.gap_id,
                CRMCard.sdp_id,
                CRMCard.manager_id,
                CRMCard.senior_manager_id,
                Contract.status.label("contract_status"),
                CRMCard.column_name,
            ).join(Contract, CRMCard.contract_id == Contract.id)

            if project_type in _CRM_PT:
                card_q = card_q.filter(Contract.project_type == _CRM_PT[project_type])

            for row in card_q.all():
                is_done = row.column_name == "Выполненный проект" or (row.contract_status and row.contract_status in ARCHIVE_STATUSES)
                for role_id in (row.gap_id, row.sdp_id, row.manager_id, row.senior_manager_id):
                    if role_id and role_id in emp_id_set:
                        entry = card_role_map.setdefault(role_id, {"total": 0, "completed": 0})
                        entry["total"] += 1
                        if is_done:
                            entry["completed"] += 1

        # Supervision: ДАН и Старший менеджер через поля SupervisionCard
        if project_type in (None, "supervision"):
            sup_q = db.query(
                SupervisionCard.dan_id,
                SupervisionCard.senior_manager_id,
                SupervisionCard.dan_completed,
            ).join(Contract, SupervisionCard.contract_id == Contract.id)

            for row in sup_q.all():
                is_done = bool(row.dan_completed)
                for role_id in (row.dan_id, row.senior_manager_id):
                    if role_id and role_id in emp_id_set:
                        entry = card_role_map.setdefault(role_id, {"total": 0, "completed": 0})
                        entry["total"] += 1
                        if is_done:
                            entry["completed"] += 1

        result = []
        for emp in employees:
            stage_data = stage_map.get(emp.id, {"total": 0, "completed": 0})
            card_data = card_role_map.get(emp.id, {"total": 0, "completed": 0})
            # Управленческие роли не имеют StageExecutor-записей, а исполнители — card-level полей,
            # поэтому сумма даёт корректный результат для обоих типов без двойного счёта.
            total_stages = stage_data["total"] + card_data["total"]
            completed_stages = stage_data["completed"] + card_data["completed"]
            total_salary = salary_map.get(emp.id, 0)

            result.append(
                {
                    "id": emp.id,
                    "full_name": emp.full_name,
                    "position": emp.position,
                    "total_stages": total_stages,
                    "completed_stages": completed_stages,
                    "completion_rate": (completed_stages / total_stages * 100) if total_stages > 0 else 0,
                    "total_salary": total_salary,
                    **survey_map.get(
                        emp.id, {"avg_nps": None, "avg_csat": None, "avg_design": None, "avg_deadline": None, "avg_communication": None, "avg_expectations": None, "avg_supervision": None}
                    ),
                    **{f"visits_{k}": v for k, v in visit_map.get(emp.id, {"total": 0, "object": 0, "supplier": 0, "overdue": 0}).items()},
                }
            )

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики сотрудников: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/contracts-by-period")
async def get_contracts_by_period(
    year: int,
    group_by: str = "month",  # month, quarter, status
    project_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить договоры сгруппированные по периоду"""
    try:
        query = db.query(Contract).filter(extract("year", Contract.created_at) == year)

        if project_type and project_type != "Все":
            query = query.filter(Contract.project_type == project_type)

        contracts = query.all()

        if group_by == "month":
            result = {i: {"count": 0, "amount": 0, "template_count": 0, "template_amount": 0, "individual_count": 0, "individual_amount": 0} for i in range(1, 13)}
            for c in contracts:
                if c.created_at:
                    m = c.created_at.month
                    result[m]["count"] += 1
                    result[m]["amount"] += c.total_amount or 0
                    if c.project_type == "Шаблонный":
                        result[m]["template_count"] += 1
                        result[m]["template_amount"] += c.total_amount or 0
                    else:
                        result[m]["individual_count"] += 1
                        result[m]["individual_amount"] += c.total_amount or 0

        elif group_by == "quarter":
            result = {i: {"count": 0, "amount": 0, "template_count": 0, "template_amount": 0, "individual_count": 0, "individual_amount": 0} for i in range(1, 5)}
            for c in contracts:
                if c.created_at:
                    q = (c.created_at.month - 1) // 3 + 1
                    result[q]["count"] += 1
                    result[q]["amount"] += c.total_amount or 0
                    if c.project_type == "Шаблонный":
                        result[q]["template_count"] += 1
                        result[q]["template_amount"] += c.total_amount or 0
                    else:
                        result[q]["individual_count"] += 1
                        result[q]["individual_amount"] += c.total_amount or 0

        elif group_by == "status":
            result = {}
            for c in contracts:
                status = c.status or "Новый заказ"
                if status not in result:
                    result[status] = {"count": 0, "amount": 0}
                result[status]["count"] += 1
                result[status]["amount"] += c.total_amount or 0

        else:
            result = {}

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении договоров по периодам: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/agent-types")
async def get_agent_types(current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список типов агентов"""
    try:
        result = db.query(Contract.agent_type).distinct().filter(Contract.agent_type.isnot(None), Contract.agent_type != "").all()
        return ["Все"] + [r[0] for r in result if r[0]]
    except Exception as e:
        logger.exception(f"Ошибка при получении типов агентов (статистика): {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cities")
async def get_cities(current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить список городов"""
    try:
        result = db.query(Contract.city).distinct().filter(Contract.city.isnot(None), Contract.city != "").all()
        return ["Все"] + [r[0] for r in result if r[0]]
    except Exception as e:
        logger.exception(f"Ошибка при получении городов (статистика): {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/projects")
async def get_project_statistics(
    project_type: str = "Индивидуальный",
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику проектов (формат совместим с db_manager)"""
    try:
        # Базовый запрос
        query = db.query(Contract).filter(Contract.project_type == project_type)

        # Фильтр по дате договора (contract_date хранится как строка YYYY-MM-DD)
        # Используем CAST к DATE для PostgreSQL или работу со строками
        if year or month or quarter:
            # Фильтруем только договоры с валидными датами
            query = query.filter(Contract.contract_date.isnot(None), Contract.contract_date != "")

        if year:
            # Приводим contract_date к DATE и извлекаем год
            query = query.filter(func.extract("year", cast(Contract.contract_date, Date)) == year)
        if month:
            query = query.filter(func.extract("month", cast(Contract.contract_date, Date)) == month)
        if quarter:
            query = _apply_quarter_filter(query, cast(Contract.contract_date, Date), quarter, year)
        if agent_type and agent_type != "Все":
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != "Все":
            query = query.filter(Contract.city == city)

        contracts = query.all()

        # Подсчёт статистики
        total_orders = len(contracts)
        total_area = sum(c.area or 0 for c in contracts)

        # Активные (не сданы и не расторгнуты; None и '' считаются активными)
        _inactive_statuses = INACTIVE_STATUSES
        active = len([c for c in contracts if c.status is None or c.status == "" or c.status not in _inactive_statuses])

        # Выполненные (СДАН или АВТОРСКИЙ НАДЗОР)
        completed = len([c for c in contracts if c.status in [STATUS_COMPLETED, STATUS_SUPERVISION]])

        # Расторгнуты
        cancelled = len([c for c in contracts if c.status == STATUS_TERMINATED])

        # Просрочки - считаем договоры с незавершёнными просроченными этапами
        overdue = 0
        try:
            from datetime import date as date_today

            overdue_query = (
                db.query(func.count(func.distinct(Contract.id)))
                .join(CRMCard, CRMCard.contract_id == Contract.id)
                .join(StageExecutor, StageExecutor.crm_card_id == CRMCard.id)
                .filter(
                    Contract.project_type == project_type,
                    StageExecutor.completed == False,
                    and_(StageExecutor.deadline.isnot(None), StageExecutor.deadline != "", func.length(StageExecutor.deadline) >= 10),
                    cast(StageExecutor.deadline, Date) < date_today.today(),
                )
            )
            # Применяем те же фильтры
            if year or month or quarter:
                # Фильтруем только договоры с валидными датами
                overdue_query = overdue_query.filter(Contract.contract_date.isnot(None), Contract.contract_date != "")

            if year:
                overdue_query = overdue_query.filter(func.extract("year", cast(Contract.contract_date, Date)) == year)
            if month:
                overdue_query = overdue_query.filter(func.extract("month", cast(Contract.contract_date, Date)) == month)
            if quarter:
                overdue_query = _apply_quarter_filter(overdue_query, cast(Contract.contract_date, Date), quarter, year)
            if agent_type and agent_type != "Все":
                overdue_query = overdue_query.filter(Contract.agent_type == agent_type)
            if city and city != "Все":
                overdue_query = overdue_query.filter(Contract.city == city)

            overdue = overdue_query.scalar() or 0
        except Exception:
            db.rollback()
            overdue = 0

        # По городам
        by_cities = {}
        for c in contracts:
            if c.city:
                by_cities[c.city] = by_cities.get(c.city, 0) + 1

        # По агентам
        by_agents = {}
        for c in contracts:
            if c.agent_type:
                by_agents[c.agent_type] = by_agents.get(c.agent_type, 0) + 1

        # По стадиям (column_name CRM-карточек)
        by_stages = {}
        contract_ids = [c.id for c in contracts]
        if contract_ids:
            stage_rows = db.query(CRMCard.column_name, func.count(CRMCard.id).label("count")).filter(CRMCard.contract_id.in_(contract_ids)).group_by(CRMCard.column_name).all()
            by_stages = {row.column_name: row.count for row in stage_rows}

        return {
            "total_orders": total_orders,
            "total_area": float(total_area),
            "active": active,
            "completed": completed,
            "cancelled": cancelled,
            "overdue": overdue,
            "by_cities": by_cities,
            "by_agents": by_agents,
            "by_stages": by_stages,
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики проектов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/supervision/filtered")
async def get_supervision_statistics_filtered(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    address: Optional[str] = None,
    executor_id: Optional[int] = None,
    manager_id: Optional[int] = None,
    status: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить отфильтрованную статистику надзора"""
    try:
        query = db.query(SupervisionCard).join(Contract)

        if year:
            query = query.filter(extract("year", SupervisionCard.created_at) == year)
        if month:
            query = query.filter(extract("month", SupervisionCard.created_at) == month)
        if quarter:
            query = _apply_quarter_filter(query, SupervisionCard.created_at, quarter)
        if agent_type and agent_type != "Все":
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != "Все":
            query = query.filter(Contract.city == city)
        if address:
            query = query.filter(Contract.address.ilike(f"%{address}%"))
        if executor_id:
            query = query.filter(SupervisionCard.dan_id == executor_id)
        if manager_id:
            query = query.filter(SupervisionCard.senior_manager_id == manager_id)
        if status:
            if status == "Приостановлено":
                query = query.filter(SupervisionCard.is_paused == True)
            elif status == "Работа сдана":
                query = query.filter(SupervisionCard.dan_completed == True)
            elif status == "В работе":
                query = query.filter(SupervisionCard.is_paused == False, SupervisionCard.dan_completed == False)

        cards = query.all()

        total_count = len(cards)
        total_area = sum(c.contract.area or 0 for c in cards)

        return {
            "total_count": total_count,
            "total_area": total_area,
            "cards": [{"id": c.id, "contract_number": c.contract.contract_number, "address": c.contract.address, "area": c.contract.area, "status": c.contract.status} for c in cards],
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении отфильтрованной статистики надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/supervision")
async def get_supervision_statistics(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику авторского надзора (формат совместим с db_manager)"""
    try:
        from datetime import date as date_type

        # Показываем все активные надзоры без фильтра по периоду
        # (периодный фильтр не применяется к карточкам, т.к. надзор — длительный процесс)
        query = db.query(SupervisionCard).join(Contract, SupervisionCard.contract_id == Contract.id)
        if agent_type and agent_type != "Все":
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != "Все":
            query = query.filter(Contract.city == city)

        cards = query.all()

        # Подсчёт статистики
        total_orders = len(cards)
        total_area = sum(c.contract.area or 0 for c in cards)

        # Активные (статус АВТОРСКИЙ НАДЗОР)
        active = len([c for c in cards if c.contract.status == STATUS_SUPERVISION])

        # Выполненные (статус СДАН)
        completed = len([c for c in cards if c.contract.status == STATUS_COMPLETED])

        # Расторгнуты
        cancelled = len([c for c in cards if c.contract.status == STATUS_TERMINATED])

        # Просрочки (дедлайн прошел, статус АВТОРСКИЙ НАДЗОР)
        today = date_type.today()

        def _is_overdue(card):
            if not card.deadline or card.contract.status != STATUS_SUPERVISION:
                return False
            try:
                dl = date_type.fromisoformat(card.deadline) if isinstance(card.deadline, str) else card.deadline
                return dl < today
            except (ValueError, TypeError):
                return False

        overdue = len([c for c in cards if _is_overdue(c)])

        # По городам
        by_cities = {}
        for c in cards:
            if c.contract.city:
                by_cities[c.contract.city] = by_cities.get(c.contract.city, 0) + 1

        # По агентам
        by_agents = {}
        for c in cards:
            if c.contract.agent_type:
                by_agents[c.contract.agent_type] = by_agents.get(c.contract.agent_type, 0) + 1

        # По стадиям (column_name карточек надзора)
        by_stages = {}
        for c in cards:
            stage = c.column_name or "Не указана"
            by_stages[stage] = by_stages.get(stage, 0) + 1

        # По типу проекта (Индивидуальный / Шаблонный)
        by_individual = len([c for c in cards if c.contract.project_type == "Индивидуальный"])
        by_template = len([c for c in cards if c.contract.project_type == "Шаблонный"])

        return {
            "total_orders": total_orders,
            "total_area": float(total_area),
            "active": active,
            "completed": completed,
            "cancelled": cancelled,
            "overdue": overdue,
            "by_individual": by_individual,
            "by_template": by_template,
            "by_cities": by_cities,
            "by_agents": by_agents,
            "by_stages": by_stages,
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики надзора: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/crm/filtered")
async def get_crm_statistics_filtered(
    project_type: str,
    period: str,
    year: int,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    project_id: Optional[int] = None,
    executor_id: Optional[int] = None,
    stage_name: Optional[str] = None,
    status_filter: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику CRM с фильтрами"""
    try:
        query = db.query(CRMCard).join(Contract).filter(Contract.project_type == project_type)

        if period == "За год":
            query = query.filter(extract("year", CRMCard.created_at) == year)
        elif period == "За квартал" and quarter:
            query = _apply_quarter_filter(query, CRMCard.created_at, quarter, year)
        elif period == "За месяц" and month:
            query = query.filter(extract("year", CRMCard.created_at) == year, extract("month", CRMCard.created_at) == month)

        if project_id:
            query = query.filter(CRMCard.contract_id == project_id)

        if status_filter:
            query = query.filter(CRMCard.column_name == status_filter)

        cards = query.all()

        # Фильтрация по исполнителю или стадии (batch-load вместо N+1)
        if executor_id or stage_name:
            card_ids = [c.id for c in cards]
            if card_ids:
                all_executors = db.query(StageExecutor).filter(StageExecutor.crm_card_id.in_(card_ids)).all()
                executor_map = defaultdict(list)
                for e in all_executors:
                    executor_map[e.crm_card_id].append(e)

                filtered_cards = []
                for card in cards:
                    card_executors = executor_map.get(card.id, [])
                    if executor_id:
                        if any(e.executor_id == executor_id for e in card_executors):
                            filtered_cards.append(card)
                    elif stage_name:
                        if any(stage_name in (e.stage_name or "") for e in card_executors):
                            filtered_cards.append(card)
                cards = filtered_cards

        result = []
        for card in cards:
            result.append(
                {
                    "id": card.id,
                    "contract_id": card.contract_id,
                    "column_name": card.column_name,
                    "contract_number": card.contract.contract_number if card.contract else None,
                    "address": card.contract.address if card.contract else None,
                    "area": float(card.contract.area) if card.contract and card.contract.area else 0,
                    "is_approved": card.is_approved,
                }
            )

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении отфильтрованной статистики CRM: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/crm")
async def get_crm_statistics(
    project_type: str = "Индивидуальный",
    period: str = "all",
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику CRM"""
    try:
        if year is None:
            year = datetime.utcnow().year

        query = db.query(CRMCard).join(Contract).filter(Contract.project_type == project_type)

        if period == "За год":
            query = query.filter(extract("year", CRMCard.created_at) == year)
        elif period == "За месяц" and month:
            query = query.filter(extract("year", CRMCard.created_at) == year, extract("month", CRMCard.created_at) == month)

        cards = query.all()

        result = []
        for card in cards:
            result.append(
                {
                    "id": card.id,
                    "contract_id": card.contract_id,
                    "column_name": card.column_name,
                    "contract_number": card.contract.contract_number if card.contract else None,
                    "address": card.contract.address if card.contract else None,
                    "area": float(card.contract.area) if card.contract and card.contract.area else 0,
                }
            )

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики CRM: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/approvals")
async def get_approval_statistics(
    project_type: str,
    period: str,
    year: int,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    project_id: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Получить статистику согласований"""
    try:
        query = db.query(CRMCard).join(Contract).filter(Contract.project_type == project_type, CRMCard.is_approved == True)

        if period == "За год":
            query = query.filter(extract("year", CRMCard.created_at) == year)
        elif period == "За квартал" and quarter:
            query = _apply_quarter_filter(query, CRMCard.created_at, quarter, year)
        elif period == "За месяц" and month:
            query = query.filter(extract("year", CRMCard.created_at) == year, extract("month", CRMCard.created_at) == month)

        if project_id:
            query = query.filter(CRMCard.contract_id == project_id)

        cards = query.all()

        result = []
        for card in cards:
            result.append(
                {
                    "id": card.id,
                    "contract_id": card.contract_id,
                    "contract_number": card.contract.contract_number if card.contract else None,
                    "address": card.contract.address if card.contract else None,
                    "is_approved": card.is_approved,
                    "approval_deadline": str(card.approval_deadline) if card.approval_deadline else None,
                    "approval_stages": json.loads(card.approval_stages) if card.approval_stages else None,
                }
            )

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики согласований: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/general")
async def get_general_statistics(year: int, quarter: Optional[int] = None, month: Optional[int] = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить общую статистику"""
    try:
        # Базовый запрос договоров
        query = db.query(Contract).filter(extract("year", Contract.created_at) == year)

        if quarter:
            query = _apply_quarter_filter(query, Contract.created_at, quarter)
        if month:
            query = query.filter(extract("month", Contract.created_at) == month)

        contracts = query.all()

        total_orders = len(contracts)
        total_area = sum(c.area or 0 for c in contracts)
        total_amount = sum(c.total_amount or 0 for c in contracts)

        individual_count = len([c for c in contracts if c.project_type == "Индивидуальный"])
        template_count = len([c for c in contracts if c.project_type == "Шаблонный"])

        active_count = len([c for c in contracts if c.status not in [STATUS_COMPLETED, STATUS_TERMINATED]])
        completed_count = len([c for c in contracts if c.status == STATUS_COMPLETED])
        cancelled_count = len([c for c in contracts if c.status == STATUS_TERMINATED])

        # Сотрудники
        active_employees = db.query(Employee).filter(Employee.status == "активный").count()

        # Платежи
        payments_query = db.query(Payment).filter(extract("year", Payment.created_at) == year)
        if quarter:
            payments_query = _apply_quarter_filter(payments_query, Payment.created_at, quarter)
        if month:
            payments_query = payments_query.filter(extract("month", Payment.created_at) == month)

        payments = payments_query.all()
        total_payments = sum(p.final_amount or 0 for p in payments)
        paid_payments = sum(p.final_amount or 0 for p in payments if p.is_paid)

        return {
            "total_orders": total_orders,
            "active": active_count,
            "completed": completed_count,
            "cancelled": cancelled_count,
            "individual_count": individual_count,
            "template_count": template_count,
            "total_area": total_area,
            "total_amount": total_amount,
            "active_employees": active_employees,
            "total_payments": total_payments,
            "paid_payments": paid_payments,
            "pending_payments": total_payments - paid_payments,
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении общей статистики: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/funnel")
async def get_funnel_statistics(year: Optional[int] = None, project_type: Optional[str] = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Воронка проектов: количество CRM-карточек по колонкам Kanban"""
    try:
        query = db.query(CRMCard.column_name, func.count(CRMCard.id).label("count")).join(Contract, CRMCard.contract_id == Contract.id)

        if year:
            query = query.filter(extract("year", Contract.created_at) == year)
        if project_type:
            query = query.filter(Contract.project_type == project_type)

        rows = query.group_by(CRMCard.column_name).all()

        funnel = {row.column_name: row.count for row in rows}
        return {"funnel": funnel, "total": sum(funnel.values())}

    except Exception as e:
        logger.exception(f"Ошибка при получении воронки статистики: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/executor-load")
async def get_executor_load(year: Optional[int] = None, month: Optional[int] = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Нагрузка на исполнителей: количество активных стадий на каждого"""
    try:
        query = (
            db.query(Employee.full_name, func.count(StageExecutor.id).label("active_stages"))
            .join(StageExecutor, StageExecutor.executor_id == Employee.id)
            .join(CRMCard, CRMCard.id == StageExecutor.crm_card_id)
            .filter(CRMCard.column_name.notin_([STATUS_COMPLETED, STATUS_TERMINATED]))
        )

        if year or month:
            query = query.join(Contract, CRMCard.contract_id == Contract.id)
            if year:
                query = query.filter(extract("year", Contract.created_at) == year)
            if month:
                query = query.filter(extract("month", Contract.created_at) == month)

        rows = query.group_by(Employee.full_name).order_by(func.count(StageExecutor.id).desc()).limit(15).all()

        return [{"name": row.full_name, "active_stages": row.active_stages} for row in rows]

    except Exception as e:
        logger.exception(f"Ошибка при получении нагрузки исполнителей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
