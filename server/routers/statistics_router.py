"""
Роутер для endpoint'ов статистики и отчётов.
Подключается в main.py через app.include_router(statistics_router, prefix="/api/statistics").
"""
import logging
import json
from collections import defaultdict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import extract, func, cast, Date, case
from sqlalchemy.orm import Session
from typing import Optional

from database import (
    get_db,
    Employee, Contract, CRMCard, StageExecutor, SupervisionCard,
    Payment, Salary
)
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["statistics"])


def _apply_quarter_filter(query, date_field, quarter: int, year: int = None):
    """Применить фильтр по кварталу к SQLAlchemy-запросу"""
    start_month = (quarter - 1) * 3 + 1
    end_month = quarter * 3
    query = query.filter(extract('month', date_field).between(start_month, end_month))
    if year:
        query = query.filter(extract('year', date_field) == year)
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
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда"""
    try:
        # Базовый запрос договоров
        query = db.query(Contract)

        # Фильтры
        if year:
            query = query.filter(extract('year', Contract.created_at) == year)
        if month:
            query = query.filter(extract('month', Contract.created_at) == month)
        if quarter:
            query = _apply_quarter_filter(query, Contract.created_at, quarter)
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)

        contracts = query.all()

        # Подсчет статистики
        total_contracts = len(contracts)
        total_amount = sum(c.total_amount or 0 for c in contracts)
        total_area = sum(c.area or 0 for c in contracts)

        # По типам проектов
        individual_count = len([c for c in contracts if c.project_type == 'Индивидуальный'])
        template_count = len([c for c in contracts if c.project_type == 'Шаблонный'])

        # По статусам
        status_counts = {}
        for c in contracts:
            status = c.status or 'Новый заказ'
            status_counts[status] = status_counts.get(status, 0) + 1

        # По городам
        city_counts = {}
        for c in contracts:
            c_city = c.city or 'Не указан'
            city_counts[c_city] = city_counts.get(c_city, 0) + 1

        # По месяцам (для графиков)
        monthly_data = {}
        for c in contracts:
            if c.created_at:
                month_key = c.created_at.strftime('%Y-%m')
                if month_key not in monthly_data:
                    monthly_data[month_key] = {'count': 0, 'amount': 0}
                monthly_data[month_key]['count'] += 1
                monthly_data[month_key]['amount'] += c.total_amount or 0

        # Активные CRM карточки
        active_cards = db.query(CRMCard).join(Contract).filter(
            ~Contract.status.in_(['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР'])
        ).count()

        # Карточки надзора
        supervision_cards = db.query(SupervisionCard).join(Contract).filter(
            Contract.status == 'АВТОРСКИЙ НАДЗОР'
        ).count()

        return {
            'total_contracts': total_contracts,
            'total_amount': total_amount,
            'total_area': total_area,
            'individual_count': individual_count,
            'template_count': template_count,
            'status_counts': status_counts,
            'city_counts': city_counts,
            'monthly_data': monthly_data,
            'active_crm_cards': active_cards,
            'supervision_cards': supervision_cards
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики дашборда: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/employees")
async def get_employee_statistics(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику по сотрудникам"""
    try:
        employees = db.query(Employee).filter(Employee.status == 'активный').all()
        emp_ids = [emp.id for emp in employees]

        if not emp_ids:
            return []

        # Batch-load stage executor counts to avoid N+1 queries
        stage_query = db.query(
            StageExecutor.executor_id,
            func.count(StageExecutor.id).label('total'),
            func.count(case((StageExecutor.completed == True, 1))).label('completed')
        ).filter(StageExecutor.executor_id.in_(emp_ids))

        if year:
            stage_query = stage_query.filter(extract('year', StageExecutor.assigned_date) == year)
        if month:
            stage_query = stage_query.filter(extract('month', StageExecutor.assigned_date) == month)

        stage_counts = stage_query.group_by(StageExecutor.executor_id).all()
        stage_map = {sc[0]: {'total': sc[1], 'completed': sc[2]} for sc in stage_counts}

        # Batch-load salary totals to avoid N+1 queries
        salary_query = db.query(
            Salary.employee_id,
            func.sum(Salary.amount).label('total')
        ).filter(Salary.employee_id.in_(emp_ids))

        if year and month:
            report_month_str = f"{year}-{month:02d}"
            salary_query = salary_query.filter(Salary.report_month == report_month_str)

        salary_totals = salary_query.group_by(Salary.employee_id).all()
        salary_map = {st[0]: float(st[1]) if st[1] else 0 for st in salary_totals}

        result = []
        for emp in employees:
            stage_data = stage_map.get(emp.id, {'total': 0, 'completed': 0})
            total_stages = stage_data['total']
            completed_stages = stage_data['completed']
            total_salary = salary_map.get(emp.id, 0)

            result.append({
                'id': emp.id,
                'full_name': emp.full_name,
                'position': emp.position,
                'total_stages': total_stages,
                'completed_stages': completed_stages,
                'completion_rate': (completed_stages / total_stages * 100) if total_stages > 0 else 0,
                'total_salary': total_salary
            })

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
    db: Session = Depends(get_db)
):
    """Получить договоры сгруппированные по периоду"""
    try:
        query = db.query(Contract).filter(extract('year', Contract.created_at) == year)

        if project_type and project_type != 'Все':
            query = query.filter(Contract.project_type == project_type)

        contracts = query.all()

        if group_by == "month":
            result = {i: {'count': 0, 'amount': 0} for i in range(1, 13)}
            for c in contracts:
                if c.created_at:
                    m = c.created_at.month
                    result[m]['count'] += 1
                    result[m]['amount'] += c.total_amount or 0

        elif group_by == "quarter":
            result = {i: {'count': 0, 'amount': 0} for i in range(1, 5)}
            for c in contracts:
                if c.created_at:
                    q = (c.created_at.month - 1) // 3 + 1
                    result[q]['count'] += 1
                    result[q]['amount'] += c.total_amount or 0

        elif group_by == "status":
            result = {}
            for c in contracts:
                status = c.status or 'Новый заказ'
                if status not in result:
                    result[status] = {'count': 0, 'amount': 0}
                result[status]['count'] += 1
                result[status]['amount'] += c.total_amount or 0

        else:
            result = {}

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении договоров по периодам: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/agent-types")
async def get_agent_types(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список типов агентов"""
    try:
        result = db.query(Contract.agent_type).distinct().filter(
            Contract.agent_type != None,
            Contract.agent_type != ''
        ).all()
        return ['Все'] + [r[0] for r in result if r[0]]
    except Exception as e:
        logger.exception(f"Ошибка при получении типов агентов (статистика): {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/cities")
async def get_cities(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список городов"""
    try:
        result = db.query(Contract.city).distinct().filter(
            Contract.city != None,
            Contract.city != ''
        ).all()
        return ['Все'] + [r[0] for r in result if r[0]]
    except Exception as e:
        logger.exception(f"Ошибка при получении городов (статистика): {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/projects")
async def get_project_statistics(
    project_type: str,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику проектов (формат совместим с db_manager)"""
    try:
        # Базовый запрос
        query = db.query(Contract).filter(Contract.project_type == project_type)

        # Фильтр по дате договора (contract_date хранится как строка YYYY-MM-DD)
        # Используем CAST к DATE для PostgreSQL или работу со строками
        if year or month or quarter:
            # Фильтруем только договоры с валидными датами
            query = query.filter(
                Contract.contract_date.isnot(None),
                Contract.contract_date != ''
            )

        if year:
            # Приводим contract_date к DATE и извлекаем год
            query = query.filter(
                func.extract('year', cast(Contract.contract_date, Date)) == year
            )
        if month:
            query = query.filter(
                func.extract('month', cast(Contract.contract_date, Date)) == month
            )
        if quarter:
            query = _apply_quarter_filter(query, cast(Contract.contract_date, Date), quarter, year)
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)

        contracts = query.all()

        # Подсчёт статистики
        total_orders = len(contracts)
        total_area = sum(c.area or 0 for c in contracts)

        # Активные (не сданы и не расторгнуты)
        active = len([c for c in contracts if c.status not in ['СДАН', 'АВТОРСКИЙ НАДЗОР', 'РАСТОРГНУТ'] or c.status is None or c.status == ''])

        # Выполненные (СДАН или АВТОРСКИЙ НАДЗОР)
        completed = len([c for c in contracts if c.status in ['СДАН', 'АВТОРСКИЙ НАДЗОР']])

        # Расторгнуты
        cancelled = len([c for c in contracts if c.status == 'РАСТОРГНУТ'])

        # Просрочки - считаем договоры с незавершёнными просроченными этапами
        overdue = 0
        try:
            from datetime import date as date_today
            overdue_query = db.query(func.count(func.distinct(Contract.id))).join(
                CRMCard, CRMCard.contract_id == Contract.id
            ).join(
                StageExecutor, StageExecutor.crm_card_id == CRMCard.id
            ).filter(
                Contract.project_type == project_type,
                StageExecutor.completed == False,
                StageExecutor.deadline.isnot(None),
                StageExecutor.deadline != '',
                cast(StageExecutor.deadline, Date) < date_today.today()
            )
            # Применяем те же фильтры
            if year or month or quarter:
                # Фильтруем только договоры с валидными датами
                overdue_query = overdue_query.filter(
                    Contract.contract_date.isnot(None),
                    Contract.contract_date != ''
                )

            if year:
                overdue_query = overdue_query.filter(
                    func.extract('year', cast(Contract.contract_date, Date)) == year
                )
            if month:
                overdue_query = overdue_query.filter(
                    func.extract('month', cast(Contract.contract_date, Date)) == month
                )
            if quarter:
                overdue_query = _apply_quarter_filter(overdue_query, cast(Contract.contract_date, Date), quarter, year)
            if agent_type and agent_type != 'Все':
                overdue_query = overdue_query.filter(Contract.agent_type == agent_type)
            if city and city != 'Все':
                overdue_query = overdue_query.filter(Contract.city == city)

            overdue = overdue_query.scalar() or 0
        except Exception:
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
            stage_rows = db.query(
                CRMCard.column_name,
                func.count(CRMCard.id).label("count")
            ).filter(
                CRMCard.contract_id.in_(contract_ids)
            ).group_by(CRMCard.column_name).all()
            by_stages = {row.column_name: row.count for row in stage_rows}

        return {
            'total_orders': total_orders,
            'total_area': float(total_area),
            'active': active,
            'completed': completed,
            'cancelled': cancelled,
            'overdue': overdue,
            'by_cities': by_cities,
            'by_agents': by_agents,
            'by_stages': by_stages,
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
    db: Session = Depends(get_db)
):
    """Получить отфильтрованную статистику надзора"""
    try:
        query = db.query(SupervisionCard).join(Contract)

        if year:
            query = query.filter(extract('year', SupervisionCard.created_at) == year)
        if month:
            query = query.filter(extract('month', SupervisionCard.created_at) == month)
        if quarter:
            query = _apply_quarter_filter(query, SupervisionCard.created_at, quarter)
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)
        if address:
            query = query.filter(Contract.address.ilike(f'%{address}%'))
        if executor_id:
            query = query.filter(SupervisionCard.dan_id == executor_id)
        if manager_id:
            query = query.filter(SupervisionCard.senior_manager_id == manager_id)
        if status:
            if status == 'Приостановлено':
                query = query.filter(SupervisionCard.is_paused == True)
            elif status == 'Работа сдана':
                query = query.filter(SupervisionCard.dan_completed == True)
            elif status == 'В работе':
                query = query.filter(SupervisionCard.is_paused == False, SupervisionCard.dan_completed == False)

        cards = query.all()

        total_count = len(cards)
        total_area = sum(c.contract.area or 0 for c in cards)

        return {
            'total_count': total_count,
            'total_area': total_area,
            'cards': [{
                'id': c.id,
                'contract_number': c.contract.contract_number,
                'address': c.contract.address,
                'area': c.contract.area,
                'status': c.contract.status
            } for c in cards]
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
    db: Session = Depends(get_db)
):
    """Получить статистику авторского надзора (формат совместим с db_manager)"""
    try:
        from datetime import date as date_type

        # Базовый запрос
        query = db.query(SupervisionCard).join(Contract, SupervisionCard.contract_id == Contract.id)

        # Фильтры по дате договора (contract_date хранится как строка YYYY-MM-DD)
        if year or month or quarter:
            # Фильтруем только договоры с валидными датами
            query = query.filter(
                Contract.contract_date.isnot(None),
                Contract.contract_date != ''
            )

        if year:
            query = query.filter(
                func.extract('year', cast(Contract.contract_date, Date)) == year
            )
        if month:
            query = query.filter(
                func.extract('month', cast(Contract.contract_date, Date)) == month
            )
        if quarter:
            query = _apply_quarter_filter(query, cast(Contract.contract_date, Date), quarter, year)
        if agent_type and agent_type != 'Все':
            query = query.filter(Contract.agent_type == agent_type)
        if city and city != 'Все':
            query = query.filter(Contract.city == city)

        cards = query.all()

        # Подсчёт статистики
        total_orders = len(cards)
        total_area = sum(c.contract.area or 0 for c in cards)

        # Активные (статус АВТОРСКИЙ НАДЗОР)
        active = len([c for c in cards if c.contract.status == 'АВТОРСКИЙ НАДЗОР'])

        # Выполненные (статус СДАН)
        completed = len([c for c in cards if c.contract.status == 'СДАН'])

        # Расторгнуты
        cancelled = len([c for c in cards if c.contract.status == 'РАСТОРГНУТ'])

        # Просрочки (дедлайн прошел, статус АВТОРСКИЙ НАДЗОР)
        today = date_type.today()
        def _is_overdue(card):
            if not card.deadline or card.contract.status != 'АВТОРСКИЙ НАДЗОР':
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
            stage = c.column_name or 'Не указана'
            by_stages[stage] = by_stages.get(stage, 0) + 1

        return {
            'total_orders': total_orders,
            'total_area': float(total_area),
            'active': active,
            'completed': completed,
            'cancelled': cancelled,
            'overdue': overdue,
            'by_cities': by_cities,
            'by_agents': by_agents,
            'by_stages': by_stages,
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
    db: Session = Depends(get_db)
):
    """Получить статистику CRM с фильтрами"""
    try:
        query = db.query(CRMCard).join(Contract).filter(
            Contract.project_type == project_type
        )

        if period == 'За год':
            query = query.filter(extract('year', CRMCard.created_at) == year)
        elif period == 'За квартал' and quarter:
            query = _apply_quarter_filter(query, CRMCard.created_at, quarter, year)
        elif period == 'За месяц' and month:
            query = query.filter(
                extract('year', CRMCard.created_at) == year,
                extract('month', CRMCard.created_at) == month
            )

        if project_id:
            query = query.filter(CRMCard.contract_id == project_id)

        if status_filter:
            query = query.filter(CRMCard.column_name == status_filter)

        cards = query.all()

        # Фильтрация по исполнителю или стадии (batch-load вместо N+1)
        if executor_id or stage_name:
            card_ids = [c.id for c in cards]
            if card_ids:
                all_executors = db.query(StageExecutor).filter(
                    StageExecutor.crm_card_id.in_(card_ids)
                ).all()
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
                        if any(stage_name in (e.stage_name or '') for e in card_executors):
                            filtered_cards.append(card)
                cards = filtered_cards

        result = []
        for card in cards:
            result.append({
                'id': card.id,
                'contract_id': card.contract_id,
                'column_name': card.column_name,
                'contract_number': card.contract.contract_number,
                'address': card.contract.address,
                'area': float(card.contract.area) if card.contract.area else 0,
                'is_approved': card.is_approved
            })

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
    db: Session = Depends(get_db)
):
    """Получить статистику CRM"""
    try:
        if year is None:
            year = datetime.utcnow().year

        query = db.query(CRMCard).join(Contract).filter(
            Contract.project_type == project_type
        )

        if period == 'За год':
            query = query.filter(extract('year', CRMCard.created_at) == year)
        elif period == 'За месяц' and month:
            query = query.filter(
                extract('year', CRMCard.created_at) == year,
                extract('month', CRMCard.created_at) == month
            )

        cards = query.all()

        result = []
        for card in cards:
            result.append({
                'id': card.id,
                'contract_id': card.contract_id,
                'column_name': card.column_name,
                'contract_number': card.contract.contract_number,
                'address': card.contract.address,
                'area': float(card.contract.area) if card.contract.area else 0
            })

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
    db: Session = Depends(get_db)
):
    """Получить статистику согласований"""
    try:
        query = db.query(CRMCard).join(Contract).filter(
            Contract.project_type == project_type,
            CRMCard.is_approved == True
        )

        if period == 'За год':
            query = query.filter(extract('year', CRMCard.created_at) == year)
        elif period == 'За квартал' and quarter:
            query = _apply_quarter_filter(query, CRMCard.created_at, quarter, year)
        elif period == 'За месяц' and month:
            query = query.filter(
                extract('year', CRMCard.created_at) == year,
                extract('month', CRMCard.created_at) == month
            )

        if project_id:
            query = query.filter(CRMCard.contract_id == project_id)

        cards = query.all()

        result = []
        for card in cards:
            result.append({
                'id': card.id,
                'contract_id': card.contract_id,
                'contract_number': card.contract.contract_number,
                'address': card.contract.address,
                'is_approved': card.is_approved,
                'approval_deadline': str(card.approval_deadline) if card.approval_deadline else None,
                'approval_stages': json.loads(card.approval_stages) if card.approval_stages else None
            })

        return result

    except Exception as e:
        logger.exception(f"Ошибка при получении статистики согласований: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/general")
async def get_general_statistics(
    year: int,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить общую статистику"""
    try:
        # Базовый запрос договоров
        query = db.query(Contract).filter(extract('year', Contract.created_at) == year)

        if quarter:
            query = _apply_quarter_filter(query, Contract.created_at, quarter)
        if month:
            query = query.filter(extract('month', Contract.created_at) == month)

        contracts = query.all()

        total_orders = len(contracts)
        total_area = sum(c.area or 0 for c in contracts)
        total_amount = sum(c.total_amount or 0 for c in contracts)

        individual_count = len([c for c in contracts if c.project_type == 'Индивидуальный'])
        template_count = len([c for c in contracts if c.project_type == 'Шаблонный'])

        active_count = len([c for c in contracts if c.status not in ['СДАН', 'РАСТОРГНУТ']])
        completed_count = len([c for c in contracts if c.status == 'СДАН'])
        cancelled_count = len([c for c in contracts if c.status == 'РАСТОРГНУТ'])

        # Сотрудники
        active_employees = db.query(Employee).filter(Employee.status == 'активный').count()

        # Платежи
        payments_query = db.query(Payment).filter(extract('year', Payment.created_at) == year)
        if quarter:
            payments_query = _apply_quarter_filter(payments_query, Payment.created_at, quarter)
        if month:
            payments_query = payments_query.filter(extract('month', Payment.created_at) == month)

        payments = payments_query.all()
        total_payments = sum(p.final_amount or 0 for p in payments)
        paid_payments = sum(p.final_amount or 0 for p in payments if p.is_paid)

        return {
            'total_orders': total_orders,
            'active': active_count,
            'completed': completed_count,
            'cancelled': cancelled_count,
            'individual_count': individual_count,
            'template_count': template_count,
            'total_area': total_area,
            'total_amount': total_amount,
            'active_employees': active_employees,
            'total_payments': total_payments,
            'paid_payments': paid_payments,
            'pending_payments': total_payments - paid_payments
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении общей статистики: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/funnel")
async def get_funnel_statistics(
    year: Optional[int] = None,
    project_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Воронка проектов: количество CRM-карточек по колонкам Kanban"""
    try:
        query = db.query(
            CRMCard.column_name,
            func.count(CRMCard.id).label("count")
        ).join(Contract, CRMCard.contract_id == Contract.id)

        if year:
            query = query.filter(extract('year', Contract.created_at) == year)
        if project_type:
            query = query.filter(Contract.project_type == project_type)

        rows = query.group_by(CRMCard.column_name).all()

        funnel = {row.column_name: row.count for row in rows}
        return {"funnel": funnel, "total": sum(funnel.values())}

    except Exception as e:
        logger.exception(f"Ошибка при получении воронки статистики: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/executor-load")
async def get_executor_load(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Нагрузка на исполнителей: количество активных стадий на каждого"""
    try:
        query = db.query(
            Employee.full_name,
            func.count(StageExecutor.id).label("active_stages")
        ).join(
            StageExecutor, StageExecutor.executor_id == Employee.id
        ).join(
            CRMCard, CRMCard.id == StageExecutor.crm_card_id
        ).filter(
            CRMCard.column_name.notin_(['СДАН', 'РАСТОРГНУТ'])
        )

        if year or month:
            query = query.join(Contract, CRMCard.contract_id == Contract.id)
            if year:
                query = query.filter(extract('year', Contract.created_at) == year)
            if month:
                query = query.filter(extract('month', Contract.created_at) == month)

        rows = query.group_by(Employee.full_name).order_by(
            func.count(StageExecutor.id).desc()
        ).limit(15).all()

        return [{"name": row.full_name, "active_stages": row.active_stages} for row in rows]

    except Exception as e:
        logger.exception(f"Ошибка при получении нагрузки исполнителей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
