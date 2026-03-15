"""
Фоновая задача для ежедневного снимка KPI сотрудников.

Запускается через asyncio.create_task(kpi_snapshot_loop()) в startup_event.
Раз в сутки (02:00 UTC) рассчитывает KPI всех активных сотрудников
и сохраняет снимки в таблицу employee_kpi_snapshots.
"""
import asyncio
import logging
from datetime import datetime, date

from database import SessionLocal, Employee, EmployeeKpiSnapshot
from services.kpi_calculator import (
    calculate_employee_kpi,
    get_concurrent_projects, get_total_salary, get_total_area,
    PROJECT_TYPE_MAP,
)
from services.access_filter import ROLES_BY_PROJECT_TYPE, ROLE_CODE_TO_POSITION

logger = logging.getLogger(__name__)

# Интервал проверки — раз в час (сам расчёт запускается 1 раз в сутки)
CHECK_INTERVAL = 3600  # секунд
SNAPSHOT_HOUR_UTC = 2  # Час запуска в UTC (05:00 МСК)


async def kpi_snapshot_loop():
    """Бесконечный цикл для ежедневного снимка KPI."""
    logger.info("KPI snapshot loop запущен (расчёт в 02:00 UTC)")
    last_run_date = None

    while True:
        try:
            now = datetime.utcnow()
            today = now.date()

            # Запускаем расчёт один раз в сутки после SNAPSHOT_HOUR_UTC
            if now.hour >= SNAPSHOT_HOUR_UTC and last_run_date != today:
                logger.info(f"Запуск ежедневного расчёта KPI за {today}")
                await _run_snapshot(today)
                last_run_date = today
                logger.info(f"Расчёт KPI завершён за {today}")

        except Exception as e:
            logger.error(f"kpi_snapshot_loop: {e}", exc_info=True)

        await asyncio.sleep(CHECK_INTERVAL)


async def _run_snapshot(today: date):
    """Рассчитывает KPI всех активных сотрудников и сохраняет снимки."""
    db = SessionLocal()
    try:
        year = today.year
        month = today.month
        report_month = f"{year}-{month:02d}"

        # Все активные сотрудники
        employees = db.query(Employee).filter(
            Employee.status == 'активный',
        ).all()

        count = 0

        for emp in employees:
            position = emp.position or ''

            # Определяем в каких типах проектов участвует данная позиция
            project_types = _get_project_types_for_position(position)

            for pt in project_types:
                try:
                    _save_snapshot(db, emp, pt, year, month, report_month)
                    count += 1
                except Exception as e:
                    logger.warning(
                        f"KPI snapshot ошибка: emp={emp.id} ({emp.full_name}), "
                        f"type={pt}: {e}"
                    )
                    db.rollback()

        logger.info(f"KPI snapshots сохранено: {count} записей")

    finally:
        db.close()


def _get_project_types_for_position(position: str) -> list:
    """Определяет типы проектов, в которых участвует данная позиция."""
    types = []
    for pt, roles in ROLES_BY_PROJECT_TYPE.items():
        for _code, pos in roles:
            if pos == position:
                types.append(pt)
                break
    return types if types else ['individual']  # fallback


def _save_snapshot(db, emp: Employee, project_type: str,
                   year: int, month: int, report_month: str):
    """Рассчитывает и сохраняет один снимок KPI."""
    from datetime import timedelta

    # Период — текущий месяц
    period_start = date(year, month, 1)
    if month == 12:
        period_end = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        period_end = date(year, month + 1, 1) - timedelta(days=1)

    # Расчёт KPI
    kpi_data = calculate_employee_kpi(
        db, emp.id, emp.position or '', project_type, year, month=month
    )

    # Текущая нагрузка и метрики
    concurrent = get_concurrent_projects(db, emp.id, project_type, emp.position or '')
    salary = get_total_salary(db, emp.id, project_type, period_start, period_end)
    project_type_db = PROJECT_TYPE_MAP.get(project_type, 'Индивидуальный')
    area = get_total_area(db, emp.id, project_type_db, period_start, period_end)

    # Upsert: обновляем если уже есть, создаём если нет
    existing = db.query(EmployeeKpiSnapshot).filter(
        EmployeeKpiSnapshot.employee_id == emp.id,
        EmployeeKpiSnapshot.report_month == report_month,
        EmployeeKpiSnapshot.project_type == project_type,
    ).first()

    if existing:
        snapshot = existing
    else:
        snapshot = EmployeeKpiSnapshot(
            employee_id=emp.id,
            report_month=report_month,
            project_type=project_type,
        )
        db.add(snapshot)

    # Заполняем данные
    snapshot.k_deadline = kpi_data.get('k_deadline')
    snapshot.k_quality = kpi_data.get('k_quality')
    snapshot.k_speed = kpi_data.get('k_speed')
    snapshot.k_nps = kpi_data.get('k_nps')
    snapshot.kpi_total = kpi_data.get('kpi_total')

    snapshot.stages_completed = kpi_data.get('stages_completed', 0)
    snapshot.stages_on_time = kpi_data.get('stages_on_time', 0)
    snapshot.stages_overdue = kpi_data.get('stages_overdue', 0)
    snapshot.avg_overdue_days = kpi_data.get('avg_overdue_days', 0)

    snapshot.concurrent_projects = concurrent
    snapshot.total_area = area
    snapshot.total_salary = salary
    snapshot.revision_count = kpi_data.get('revision_count', 0)

    # Метрики надзора
    if project_type == 'supervision':
        snapshot.defects_found = kpi_data.get('defects_found', 0)
        snapshot.defects_resolved = kpi_data.get('defects_resolved', 0)
        snapshot.site_visits = kpi_data.get('site_visits', 0)
        snapshot.budget_savings = kpi_data.get('budget_savings', 0)

    snapshot.calculated_at = datetime.utcnow()

    db.commit()
