"""
Роутер аналитики по сотрудникам.
Подключается: app.include_router(employee_analytics_router, prefix="/api/v1/employee-analytics")
"""
import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from database import (
    get_db, Employee, CRMCard, Contract, StageExecutor,
    SupervisionCard, Payment, EmployeeKpiSnapshot, ClientSurvey,
)
from auth import get_current_user
from constants import (
    POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER,
    STATUS_COMPLETED, STATUS_TERMINATED,
)
from services.kpi_calculator import (
    calculate_employee_kpi, get_concurrent_projects,
    get_recommended_max_load, get_total_salary, get_total_area,
    PROJECT_TYPE_MAP, _get_period_range,
)
from services.access_filter import (
    get_access_level, get_visible_employee_ids,
    get_available_roles, get_employees_by_role,
    ROLE_CODE_TO_POSITION,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["employee-analytics"])


@router.get("/dashboard")
async def get_analytics_dashboard(
    project_type: str = Query(..., regex="^(individual|template|supervision)$"),
    year: Optional[int] = Query(None, ge=2020, le=2035),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    month: Optional[int] = Query(None, ge=1, le=12),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Сводный дашборд KPI по сотрудникам."""
    try:
        if not year:
            year = date.today().year

        access_level = get_access_level(current_user)
        visible_ids = get_visible_employee_ids(db, current_user, project_type)
        available_roles = get_available_roles(project_type)
        period_start, period_end = _get_period_range(year, quarter, month)

        # Собираем KPI для всех видимых сотрудников, участвующих в проектах данного типа
        all_employees_kpi = []

        for role_code in available_roles:
            employees = get_employees_by_role(db, role_code, project_type, visible_ids)
            for emp in employees:
                # Не дублировать если уже посчитан (один человек может быть в нескольких ролях)
                if any(e['employee_id'] == emp.id for e in all_employees_kpi):
                    continue

                kpi_data = calculate_employee_kpi(
                    db, emp.id, emp.position, project_type, year, quarter, month
                )
                concurrent = get_concurrent_projects(db, emp.id, project_type, emp.position)

                all_employees_kpi.append({
                    'employee_id': emp.id,
                    'full_name': emp.full_name,
                    'position': emp.position,
                    'kpi_total': kpi_data['kpi_total'],
                    'k_deadline': kpi_data['k_deadline'],
                    'k_quality': kpi_data['k_quality'],
                    'k_speed': kpi_data['k_speed'],
                    'k_nps': kpi_data.get('k_nps'),
                    'stages_completed': kpi_data['stages_completed'],
                    'stages_on_time': kpi_data['stages_on_time'],
                    'stages_overdue': kpi_data['stages_overdue'],
                    'concurrent_projects': concurrent,
                    'trend': _calc_trend(db, emp.id, project_type, year, quarter, month),
                })

        # Сводные метрики
        kpi_values = [e['kpi_total'] for e in all_employees_kpi]
        on_time_values = [e['k_deadline'] for e in all_employees_kpi]
        concurrent_values = [e['concurrent_projects'] for e in all_employees_kpi]

        # Средний NPS из опросов
        avg_nps = _get_avg_nps(db, project_type, period_start, period_end, visible_ids)

        # Кол-во активных проектов
        active_projects = _count_active_projects(db, project_type, visible_ids)

        # Топ-5 лучших / проблемных
        sorted_by_kpi = sorted(all_employees_kpi, key=lambda x: x['kpi_total'], reverse=True)
        top_performers = sorted_by_kpi[:5] if access_level in ('full', 'team') else []
        underperformers = [e for e in sorted_by_kpi if e['kpi_total'] < 60 or e['stages_overdue'] > 3]
        underperformers = underperformers[:5] if access_level in ('full', 'team') else []

        # Тренд KPI за последние 6 месяцев
        kpi_trend = _get_kpi_trend(db, project_type, visible_ids)

        return {
            'access_level': access_level,
            'project_type': project_type,
            'summary': {
                'total_employees': len(all_employees_kpi),
                'avg_kpi': round(sum(kpi_values) / len(kpi_values), 1) if kpi_values else 0,
                'avg_on_time_rate': round(sum(on_time_values) / len(on_time_values), 1) if on_time_values else 0,
                'avg_concurrent_load': round(sum(concurrent_values) / len(concurrent_values), 1) if concurrent_values else 0,
                'avg_nps': avg_nps,
                'active_projects': active_projects,
            },
            'top_performers': top_performers,
            'underperformers': underperformers,
            'kpi_trend': kpi_trend,
            'available_roles': available_roles,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка дашборда аналитики: {e}")
        raise HTTPException(500, "Внутренняя ошибка сервера")


@router.get("/role/{role_code}")
async def get_role_analytics(
    role_code: str,
    project_type: str = Query(..., regex="^(individual|template|supervision)$"),
    year: Optional[int] = Query(None, ge=2020, le=2035),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    month: Optional[int] = Query(None, ge=1, le=12),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Сравнительная аналитика по роли."""
    try:
        if not year:
            year = date.today().year

        available_roles = get_available_roles(project_type)
        if role_code not in available_roles:
            raise HTTPException(400, f"Роль {role_code} не участвует в проектах типа {project_type}")

        visible_ids = get_visible_employee_ids(db, current_user, project_type)
        employees = get_employees_by_role(db, role_code, project_type, visible_ids)
        period_start, period_end = _get_period_range(year, quarter, month)

        position = ROLE_CODE_TO_POSITION.get(role_code, '')
        employees_data = []

        for emp in employees:
            kpi_data = calculate_employee_kpi(
                db, emp.id, emp.position, project_type, year, quarter, month
            )
            concurrent = get_concurrent_projects(db, emp.id, project_type, emp.position)
            salary = get_total_salary(db, emp.id, project_type, period_start, period_end)
            trend = _calc_trend(db, emp.id, project_type, year, quarter, month)

            entry = {
                'employee_id': emp.id,
                'full_name': emp.full_name,
                'position': emp.position,
                **kpi_data,
                'concurrent_projects': concurrent,
                'recommended_max': get_recommended_max_load(emp.position),
                'total_salary': round(salary, 2),
                'trend': trend,
            }

            # Специфичные метрики
            if project_type != 'supervision':
                project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')
                entry['total_area'] = round(
                    get_total_area(db, emp.id, project_type_db, period_start, period_end), 1
                )

            employees_data.append(entry)

        # Средние по роли
        kpi_values = [e['kpi_total'] for e in employees_data]
        role_avg = {
            'kpi_total': round(sum(kpi_values) / len(kpi_values), 1) if kpi_values else 0,
            'on_time_rate': round(
                sum(e['k_deadline'] for e in employees_data) / len(employees_data), 1
            ) if employees_data else 0,
        }

        # Помесячная динамика KPI
        kpi_monthly = _get_role_kpi_monthly(
            db, [emp.id for emp in employees], project_type
        )

        return {
            'role': position,
            'role_code': role_code,
            'employees': employees_data,
            'role_avg': role_avg,
            'kpi_monthly': kpi_monthly,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка аналитики роли: {e}")
        raise HTTPException(500, "Внутренняя ошибка сервера")


@router.get("/{employee_id}/detail")
async def get_employee_detail(
    employee_id: int,
    project_type: str = Query(..., regex="^(individual|template|supervision)$"),
    year: Optional[int] = Query(None, ge=2020, le=2035),
    quarter: Optional[int] = Query(None, ge=1, le=4),
    month: Optional[int] = Query(None, ge=1, le=12),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Детальная карточка сотрудника."""
    try:
        if not year:
            year = date.today().year

        # Проверка доступа
        visible_ids = get_visible_employee_ids(db, current_user, project_type)
        if visible_ids is not None and employee_id not in visible_ids:
            raise HTTPException(403, "Нет доступа к данным этого сотрудника")

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(404, "Сотрудник не найден")

        period_start, period_end = _get_period_range(year, quarter, month)

        # KPI
        kpi_data = calculate_employee_kpi(
            db, employee_id, employee.position, project_type, year, quarter, month
        )
        concurrent = get_concurrent_projects(db, employee_id, project_type, employee.position)
        salary = get_total_salary(db, employee_id, project_type, period_start, period_end)

        # Помесячный KPI (из снимков)
        kpi_monthly = db.query(EmployeeKpiSnapshot).filter(
            EmployeeKpiSnapshot.employee_id == employee_id,
            EmployeeKpiSnapshot.project_type == project_type,
        ).order_by(EmployeeKpiSnapshot.report_month.desc()).limit(12).all()

        kpi_monthly_data = [{
            'month': s.report_month,
            'kpi_total': s.kpi_total,
            'k_deadline': s.k_deadline,
            'k_quality': s.k_quality,
            'k_speed': s.k_speed,
            'k_nps': s.k_nps,
        } for s in reversed(kpi_monthly)]

        # Проекты сотрудника
        projects = _get_employee_projects(
            db, employee_id, project_type, period_start, period_end
        )

        # Отзывы клиентов
        reviews = _get_employee_reviews(db, employee_id, project_type)

        # Разбивка по стадиям
        stages_breakdown = _get_stages_breakdown(
            db, employee_id, project_type, period_start, period_end
        )

        # Нагрузка по месяцам (из снимков)
        load_monthly = [{
            'month': s.report_month,
            'concurrent': s.concurrent_projects or 0,
        } for s in reversed(kpi_monthly)]

        # Права на зарплату
        access_level = get_access_level(current_user)
        show_salary = access_level in ('full', 'team') or current_user.id == employee_id

        return {
            'employee': {
                'id': employee.id,
                'full_name': employee.full_name,
                'position': employee.position,
                'department': employee.department,
                'status': employee.status,
            },
            'kpi': {
                'total': kpi_data['kpi_total'],
                'k_deadline': kpi_data['k_deadline'],
                'k_quality': kpi_data['k_quality'],
                'k_speed': kpi_data['k_speed'],
                'k_nps': kpi_data.get('k_nps'),
            },
            'metrics': {
                **kpi_data,
                'concurrent_projects': concurrent,
                'recommended_max_load': get_recommended_max_load(employee.position),
                'total_salary': round(salary, 2) if show_salary else None,
            },
            'kpi_monthly': kpi_monthly_data,
            'stages_breakdown': stages_breakdown,
            'load_monthly': load_monthly,
            'projects': projects,
            'client_reviews': reviews,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка детальной карточки сотрудника: {e}")
        raise HTTPException(500, "Внутренняя ошибка сервера")


# ═══════════════════════════════════════════════════════════════════════
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ═══════════════════════════════════════════════════════════════════════

def _calc_trend(db: Session, employee_id: int, project_type: str,
                year: int, quarter=None, month=None) -> str:
    """Сравнивает KPI текущего и предыдущего периода → up/down/stable."""
    snapshots = db.query(EmployeeKpiSnapshot).filter(
        EmployeeKpiSnapshot.employee_id == employee_id,
        EmployeeKpiSnapshot.project_type == project_type,
    ).order_by(EmployeeKpiSnapshot.report_month.desc()).limit(2).all()

    if len(snapshots) < 2:
        return 'stable'

    current_kpi = snapshots[0].kpi_total or 0
    prev_kpi = snapshots[1].kpi_total or 0
    diff = current_kpi - prev_kpi

    if diff > 3:
        return 'up'
    elif diff < -3:
        return 'down'
    return 'stable'


def _get_avg_nps(db, project_type, period_start, period_end, visible_ids):
    """Средний NPS по опросам данного типа."""
    pt_code = project_type
    query = db.query(func.avg(ClientSurvey.nps_score)).filter(
        ClientSurvey.project_type == pt_code,
        ClientSurvey.status == 'completed',
        ClientSurvey.nps_score.isnot(None),
    )
    if visible_ids is not None:
        # Фильтрация NPS — только по контрактам видимых сотрудников
        if pt_code == 'supervision':
            visible_contract_ids = [c.contract_id for c in
                db.query(SupervisionCard.contract_id).filter(
                    or_(SupervisionCard.dan_id.in_(visible_ids),
                        SupervisionCard.senior_manager_id.in_(visible_ids))
                ).all()]
        else:
            visible_contract_ids = [s.contract_id for s in
                db.query(CRMCard.contract_id).join(
                    StageExecutor, StageExecutor.crm_card_id == CRMCard.id
                ).filter(StageExecutor.executor_id.in_(visible_ids)).all()]
        if visible_contract_ids:
            query = query.filter(ClientSurvey.contract_id.in_(visible_contract_ids))
        else:
            return None
    result = query.scalar()
    return round(result, 1) if result else None


def _count_active_projects(db, project_type, visible_ids):
    """Кол-во активных проектов данного типа."""
    active_statuses_exclude = [STATUS_COMPLETED, STATUS_TERMINATED, 'РАСТОРГНУТ']

    if project_type == 'supervision':
        return db.query(func.count(SupervisionCard.id)).filter(
            SupervisionCard.column_name.notin_(active_statuses_exclude),
        ).scalar() or 0
    else:
        project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')
        return db.query(func.count(CRMCard.id)).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type_db,
            CRMCard.column_name.notin_(active_statuses_exclude),
        ).scalar() or 0


def _get_kpi_trend(db, project_type, visible_ids):
    """Тренд среднего KPI за последние 6 месяцев."""
    query = db.query(
        EmployeeKpiSnapshot.report_month,
        func.avg(EmployeeKpiSnapshot.kpi_total).label('avg_kpi'),
        func.min(EmployeeKpiSnapshot.kpi_total).label('min_kpi'),
        func.max(EmployeeKpiSnapshot.kpi_total).label('max_kpi'),
    ).filter(
        EmployeeKpiSnapshot.project_type == project_type,
    )

    if visible_ids is not None:
        query = query.filter(EmployeeKpiSnapshot.employee_id.in_(visible_ids))

    results = query.group_by(
        EmployeeKpiSnapshot.report_month
    ).order_by(
        EmployeeKpiSnapshot.report_month.desc()
    ).limit(6).all()

    return [{
        'month': r.report_month,
        'avg_kpi': round(r.avg_kpi, 1) if r.avg_kpi else 0,
        'min_kpi': round(r.min_kpi, 1) if r.min_kpi else 0,
        'max_kpi': round(r.max_kpi, 1) if r.max_kpi else 0,
    } for r in reversed(results)]


def _get_role_kpi_monthly(db, employee_ids, project_type):
    """Помесячный KPI для списка сотрудников."""
    if not employee_ids:
        return []

    results = db.query(EmployeeKpiSnapshot).filter(
        EmployeeKpiSnapshot.employee_id.in_(employee_ids),
        EmployeeKpiSnapshot.project_type == project_type,
    ).order_by(EmployeeKpiSnapshot.report_month.desc()).all()

    months = {}
    for r in results:
        if r.report_month not in months:
            months[r.report_month] = {'month': r.report_month, 'employees': []}
        months[r.report_month]['employees'].append({
            'employee_id': r.employee_id,
            'kpi': r.kpi_total,
        })

    return sorted(months.values(), key=lambda x: x['month'])[-6:]


def _get_employee_projects(db, employee_id, project_type, period_start, period_end):
    """Список проектов сотрудника за период."""
    from datetime import datetime

    if project_type == 'supervision':
        cards = db.query(SupervisionCard).join(
            Contract, SupervisionCard.contract_id == Contract.id
        ).filter(
            or_(
                SupervisionCard.dan_id == employee_id,
                SupervisionCard.senior_manager_id == employee_id,
            ),
        ).limit(50).all()

        return [{
            'contract_id': c.contract_id,
            'contract_number': c.contract.contract_number if c.contract else '',
            'address': c.contract.address if c.contract else '',
            'status': c.column_name,
            'stage_name': 'Авторский надзор',
        } for c in cards]

    project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')

    stages = db.query(StageExecutor).join(
        CRMCard, StageExecutor.crm_card_id == CRMCard.id
    ).join(
        Contract, CRMCard.contract_id == Contract.id
    ).filter(
        Contract.project_type == project_type_db,
        StageExecutor.executor_id == employee_id,
        StageExecutor.assigned_date <= period_end,
        or_(StageExecutor.completed_date >= period_start, StageExecutor.completed_date.is_(None)),
    ).order_by(StageExecutor.assigned_date.desc()).limit(50).all()

    projects = []
    for s in stages:
        contract = s.crm_card.contract if s.crm_card else None
        dl = s.deadline
        cd = s.completed_date

        deviation = None
        if cd and dl:
            from services.kpi_calculator import _parse_date
            cd_d = _parse_date(cd)
            dl_d = _parse_date(dl)
            if cd_d and dl_d:
                deviation = (cd_d - dl_d).days

        # NPS по этому контракту
        nps = None
        if contract:
            survey = db.query(ClientSurvey).filter(
                ClientSurvey.contract_id == contract.id,
                ClientSurvey.status == 'completed',
            ).first()
            if survey:
                nps = survey.nps_score

        projects.append({
            'contract_id': contract.id if contract else None,
            'contract_number': contract.contract_number if contract else '',
            'address': contract.address if contract else '',
            'stage_name': s.stage_name,
            'assigned_date': s.assigned_date.isoformat() if s.assigned_date else None,
            'deadline': s.deadline,
            'completed_date': s.completed_date.isoformat() if s.completed_date else None,
            'deviation_days': deviation,
            'status': 'completed' if s.completed else ('overdue' if deviation and deviation > 0 else 'in_progress'),
            'nps_score': nps,
        })

    return projects


def _get_employee_reviews(db, employee_id, project_type):
    """Отзывы клиентов по проектам сотрудника."""
    pt_code = project_type

    if project_type == 'supervision':
        surveys = db.query(ClientSurvey).join(
            Contract, ClientSurvey.contract_id == Contract.id
        ).join(
            SupervisionCard, SupervisionCard.contract_id == Contract.id
        ).filter(
            ClientSurvey.project_type == pt_code,
            ClientSurvey.status == 'completed',
            or_(
                SupervisionCard.dan_id == employee_id,
                SupervisionCard.senior_manager_id == employee_id,
            ),
        ).order_by(ClientSurvey.completed_at.desc()).limit(10).all()
    else:
        # Через карточки
        surveys_direct = db.query(ClientSurvey).join(
            Contract, ClientSurvey.contract_id == Contract.id
        ).join(
            CRMCard, CRMCard.contract_id == Contract.id
        ).filter(
            ClientSurvey.project_type == pt_code,
            ClientSurvey.status == 'completed',
            or_(
                CRMCard.senior_manager_id == employee_id,
                CRMCard.sdp_id == employee_id,
                CRMCard.gap_id == employee_id,
                CRMCard.manager_id == employee_id,
                CRMCard.surveyor_id == employee_id,
            ),
        ).limit(10).all()

        # Через stage_executors
        surveys_exec = db.query(ClientSurvey).join(
            Contract, ClientSurvey.contract_id == Contract.id
        ).join(
            CRMCard, CRMCard.contract_id == Contract.id
        ).join(
            StageExecutor, StageExecutor.crm_card_id == CRMCard.id
        ).filter(
            ClientSurvey.project_type == pt_code,
            ClientSurvey.status == 'completed',
            StageExecutor.executor_id == employee_id,
        ).limit(10).all()

        seen = set()
        surveys = []
        for s in surveys_direct + surveys_exec:
            if s.id not in seen:
                seen.add(s.id)
                surveys.append(s)
        surveys = surveys[:10]

    return [{
        'survey_id': s.id,
        'contract_number': s.contract.contract_number if s.contract else '',
        'completed_at': s.completed_at.isoformat() if s.completed_at else None,
        'nps_score': s.nps_score,
        'csat_score': s.csat_score,
        'design_score': s.design_score,
        'deadline_score': s.deadline_score,
        'communication_score': s.communication_score,
        'expectations_score': s.expectations_score,
        'supervision_score': s.supervision_score,
        'comment': s.comment,
    } for s in surveys]


def _get_stages_breakdown(db, employee_id, project_type, period_start, period_end):
    """Разбивка по стадиям: кол-во в срок / с просрочкой."""
    if project_type == 'supervision':
        return []  # Для надзора другая структура

    from services.kpi_calculator import _parse_date, _get_completed_stages
    from datetime import datetime

    project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')
    stages = _get_completed_stages(db, employee_id, project_type_db, period_start, period_end)

    breakdown = {}
    for s in stages:
        name = s.stage_name or 'Без названия'
        if name not in breakdown:
            breakdown[name] = {'stage_name': name, 'total': 0, 'on_time': 0, 'overdue': 0}

        breakdown[name]['total'] += 1

        dl = _parse_date(s.deadline)
        cd = _parse_date(s.completed_date)
        if dl and cd:
            if cd <= dl:
                breakdown[name]['on_time'] += 1
            else:
                breakdown[name]['overdue'] += 1

    return list(breakdown.values())
