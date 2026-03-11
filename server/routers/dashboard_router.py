"""
Роутер для эндпоинтов дашборда.
Эндпоинты:
  GET /clients
  GET /contracts
  GET /crm
  GET /employees
  GET /salaries
  GET /salaries-by-type
  GET /salaries-all
  GET /salaries-individual
  GET /salaries-template
  GET /salaries-salary
  GET /salaries-supervision
  GET /agent-types
  GET /contract-years
  GET /reports/summary
  GET /reports/clients-dynamics
  GET /reports/contracts-dynamics
  GET /reports/crm-analytics
  GET /reports/supervision-analytics
  GET /reports/distribution

Подключение в main.py:
  app.include_router(dashboard_router, prefix="/api/dashboard")
"""
import logging
from collections import defaultdict
from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import (
    get_db,
    Client, Contract, Employee,
    CRMCard, SupervisionCard,
    Payment, Salary,
    Agent, StageExecutor, SupervisionTimelineEntry,
    ProjectTimelineEntry,
)

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


@router.get("/clients")
async def get_clients_dashboard(
    year: Optional[int] = None,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда страницы Клиенты"""
    try:
        # 1. Всего клиентов
        total_clients = db.query(Client).count()

        # 2. Всего физлиц
        total_individual = db.query(Client).filter(
            Client.client_type == 'Физическое лицо'
        ).count()

        # 3. Всего юрлиц
        total_legal = db.query(Client).filter(
            Client.client_type == 'Юридическое лицо'
        ).count()

        # 4. Клиенты за год
        # contract_date хранится как VARCHAR, используем LIKE для поиска года
        clients_by_year = 0
        if year:
            year_str = str(year)
            clients_by_year = db.query(Contract.client_id).filter(
                Contract.contract_date.like(f'{year_str}-%')
            ).distinct().count()

        # 5. Клиенты агента (всего)
        agent_clients_total = 0
        if agent_type:
            agent_clients_total = db.query(Contract.client_id).filter(
                Contract.agent_type == agent_type
            ).distinct().count()

        # 6. Клиенты агента за год
        agent_clients_by_year = 0
        if agent_type and year:
            year_str = str(year)
            agent_clients_by_year = db.query(Contract.client_id).filter(
                Contract.agent_type == agent_type,
                Contract.contract_date.like(f'{year_str}-%')
            ).distinct().count()

        return {
            'total_clients': total_clients,
            'total_individual': total_individual,
            'total_legal': total_legal,
            'clients_by_year': clients_by_year,
            'agent_clients_total': agent_clients_total,
            'agent_clients_by_year': agent_clients_by_year
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда клиентов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/contracts")
async def get_contracts_dashboard(
    year: Optional[int] = None,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда страницы Договора"""
    try:
        # 1-2. Индивидуальные заказы и площадь
        individual_query = db.query(
            func.count(Contract.id),
            func.coalesce(func.sum(Contract.area), 0)
        ).filter(Contract.project_type == 'Индивидуальный')
        individual_orders, individual_area = individual_query.first()

        # 3-4. Шаблонные заказы и площадь
        template_query = db.query(
            func.count(Contract.id),
            func.coalesce(func.sum(Contract.area), 0)
        ).filter(Contract.project_type == 'Шаблонный')
        template_orders, template_area = template_query.first()

        # 5. Заказы агента за год
        # contract_date хранится как VARCHAR, используем LIKE для поиска года
        agent_orders_by_year = 0
        if agent_type and year:
            year_str = str(year)
            agent_orders_by_year = db.query(Contract).filter(
                Contract.agent_type == agent_type,
                Contract.contract_date.like(f'{year_str}-%')
            ).count()

        # 6. Площадь агента за год
        agent_area_by_year = 0
        if agent_type and year:
            year_str = str(year)
            result = db.query(
                func.coalesce(func.sum(Contract.area), 0)
            ).filter(
                Contract.agent_type == agent_type,
                Contract.contract_date.like(f'{year_str}-%')
            ).scalar()
            agent_area_by_year = float(result) if result else 0

        return {
            'individual_orders': individual_orders,
            'individual_area': float(individual_area),
            'template_orders': template_orders,
            'template_area': float(template_area),
            'agent_orders_by_year': agent_orders_by_year,
            'agent_area_by_year': agent_area_by_year
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда договоров: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/crm")
async def get_crm_dashboard(
    project_type: str,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда СРМ (Индивидуальные/Шаблонные/Надзор)"""
    try:
        # Определяем таблицу CRM
        if project_type == 'Авторский надзор':
            crm_table = SupervisionCard
            contract_condition = Contract.status == 'АВТОРСКИЙ НАДЗОР'
        elif project_type == 'Индивидуальный':
            crm_table = CRMCard
            contract_condition = Contract.project_type == 'Индивидуальный'
        else:  # Шаблонный
            crm_table = CRMCard
            contract_condition = Contract.project_type == 'Шаблонный'

        # 1-2. Всего заказов и площадь (из договоров)
        total_query = db.query(
            func.count(Contract.id),
            func.coalesce(func.sum(Contract.area), 0)
        ).filter(contract_condition)
        total_orders, total_area = total_query.first()

        # 3-4. Активные и архивные заказы в СРМ
        archive_statuses = ['СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР']
        if project_type == 'Авторский надзор':
            # Для надзора: активные = контракт в статусе АВТОРСКИЙ НАДЗОР
            active_orders = db.query(crm_table).join(
                Contract, crm_table.contract_id == Contract.id
            ).filter(contract_condition).count()
            # Архивные = надзорные карточки с завершённым контрактом
            archive_orders = db.query(crm_table).join(
                Contract, crm_table.contract_id == Contract.id
            ).filter(
                Contract.status.in_(['СДАН', 'РАСТОРГНУТ'])
            ).count()
        else:
            active_orders = db.query(crm_table).join(
                Contract, crm_table.contract_id == Contract.id
            ).filter(
                contract_condition,
                ~Contract.status.in_(archive_statuses)
            ).count()
            archive_orders = db.query(crm_table).join(
                Contract, crm_table.contract_id == Contract.id
            ).filter(
                contract_condition,
                Contract.status.in_(archive_statuses)
            ).count()

        # 5. Активные заказы агента (без архивных)
        agent_active_orders = 0
        if agent_type:
            if project_type == 'Авторский надзор':
                agent_active_orders = db.query(crm_table).join(
                    Contract, crm_table.contract_id == Contract.id
                ).filter(contract_condition, Contract.agent_type == agent_type).count()
            else:
                agent_active_orders = db.query(crm_table).join(
                    Contract, crm_table.contract_id == Contract.id
                ).filter(
                    contract_condition,
                    Contract.agent_type == agent_type,
                    ~Contract.status.in_(archive_statuses)
                ).count()

        # 6. Архивные заказы агента
        agent_archive_orders = 0
        if agent_type:
            if project_type == 'Авторский надзор':
                agent_archive_orders = db.query(crm_table).join(
                    Contract, crm_table.contract_id == Contract.id
                ).filter(
                    Contract.status.in_(['СДАН', 'РАСТОРГНУТ']),
                    Contract.agent_type == agent_type
                ).count()
            else:
                agent_archive_orders = db.query(crm_table).join(
                    Contract, crm_table.contract_id == Contract.id
                ).filter(
                    contract_condition,
                    Contract.agent_type == agent_type,
                    Contract.status.in_(archive_statuses)
                ).count()

        return {
            'total_orders': total_orders,
            'total_area': float(total_area),
            'active_orders': active_orders,
            'archive_orders': archive_orders,
            'agent_active_orders': agent_active_orders,
            'agent_archive_orders': agent_archive_orders
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда CRM: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/employees")
async def get_employees_dashboard(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда страницы Сотрудники"""
    try:
        # Используем func.lower для регистронезависимого сравнения
        # Значения в БД: 'активный', 'уволен', 'в резерве'
        # Отделы: 'Административный отдел', 'Проектный отдел', 'Исполнительный отдел'

        # 1. Активные сотрудники
        active_employees = db.query(Employee).filter(
            func.lower(Employee.status) == 'активный'
        ).count()

        # 2. Резерв
        reserve_employees = db.query(Employee).filter(
            func.lower(Employee.status) == 'в резерве'
        ).count()

        # 3. Руководящий состав (по должностям, как во вкладках UI)
        admin_positions = ['Руководитель студии', 'Старший менеджер проектов', 'СДП', 'ГАП']
        active_management = db.query(Employee).filter(
            func.lower(Employee.status) == 'активный',
            Employee.position.in_(admin_positions)
        ).count()

        # 4. Проектный отдел (по должностям)
        project_positions = ['Дизайнер', 'Чертёжник']
        active_projects_dept = db.query(Employee).filter(
            func.lower(Employee.status) == 'активный',
            Employee.position.in_(project_positions)
        ).count()

        # 5. Исполнительный отдел (по должностям)
        exec_positions = ['Менеджер', 'ДАН', 'Замерщик']
        active_execution_dept = db.query(Employee).filter(
            func.lower(Employee.status) == 'активный',
            Employee.position.in_(exec_positions)
        ).count()

        # 6. Дни рождения (ближайшие 30 дней)
        today = datetime.now()
        upcoming_birthdays = 0
        nearest_birthday = None
        min_days = 366

        employees = db.query(Employee).filter(
            func.lower(Employee.status) == 'активный'
        ).all()
        from datetime import date as date_cls
        birthday_names = []
        for emp in employees:
            if emp.birth_date:
                try:
                    # birth_date хранится как строка 'yyyy-MM-dd'
                    if isinstance(emp.birth_date, str):
                        bd = datetime.strptime(emp.birth_date, '%Y-%m-%d').date()
                    else:
                        bd = emp.birth_date if isinstance(emp.birth_date, date_cls) else emp.birth_date.date()

                    birth_this_year = bd.replace(year=today.year)
                    if birth_this_year < today.date():
                        birth_this_year = bd.replace(year=today.year + 1)

                    days_until = (birth_this_year - today.date()).days
                    if 0 <= days_until <= 30:
                        upcoming_birthdays += 1

                    if days_until < min_days:
                        min_days = days_until
                        birthday_names = [emp.full_name]
                    elif days_until == min_days:
                        birthday_names.append(emp.full_name)
                except Exception:
                    continue

        nearest_birthday_text = ", ".join(birthday_names) if birthday_names else "Нет данных"

        return {
            'active_employees': active_employees,
            'reserve_employees': reserve_employees,
            'active_management': active_management,
            'active_admin': active_management,
            'active_projects_dept': active_projects_dept,
            'active_project': active_projects_dept,
            'active_execution_dept': active_execution_dept,
            'active_execution': active_execution_dept,
            'upcoming_birthdays': upcoming_birthdays,
            'nearest_birthday': nearest_birthday_text
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда сотрудников: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries")
async def get_salaries_dashboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда страницы Зарплаты"""
    try:
        # 1. Всего выплачено (все время)
        total_paid = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0)
        ).filter(Payment.payment_status == 'paid').scalar()

        # 2. Выплачено за год
        paid_by_year = 0
        if year:
            paid_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%')
            ).scalar()

        # 3. Выплачено за месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar()

        # 4. Индивидуальные за год
        individual_by_year = 0
        if year:
            individual_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.project_type == 'Индивидуальный'
            ).scalar()

        # 5. Шаблонные за год
        template_by_year = 0
        if year:
            template_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.project_type == 'Шаблонный'
            ).scalar()

        # 6. Надзор за год
        supervision_by_year = 0
        if year:
            supervision_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.status == 'АВТОРСКИЙ НАДЗОР'
            ).scalar()

        return {
            'total_paid': float(total_paid) if total_paid else 0,
            'paid_by_year': float(paid_by_year) if paid_by_year else 0,
            'paid_by_month': float(paid_by_month) if paid_by_month else 0,
            'individual_by_year': float(individual_by_year) if individual_by_year else 0,
            'template_by_year': float(template_by_year) if template_by_year else 0,
            'supervision_by_year': float(supervision_by_year) if supervision_by_year else 0
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда зарплат: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries-by-type")
async def get_salaries_by_type_dashboard(
    payment_type: str,
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить статистику для дашборда вкладок зарплат по типу выплат

    Args:
        payment_type: Тип вкладки ('all', 'individual', 'template', 'salary', 'supervision')
        year: Год для фильтра
        month: Месяц для фильтра
        agent_type: Тип агента для фильтра

    Returns:
        Dict с ключами: total_paid, paid_by_year, paid_by_month, payments_count, to_pay_amount, by_agent
    """
    try:
        # Базовый запрос
        if payment_type == 'salary':
            # Оклады - из таблицы salaries
            # ВАЖНО: таблица salaries не имеет поля status/payment_status
            # Оклады считаются всегда выплаченными

            # Всего выплачено (все оклады)
            total_paid = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).scalar()

            # За год
            paid_by_year = 0
            if year:
                paid_by_year = db.query(
                    func.coalesce(func.sum(Salary.amount), 0)
                ).filter(
                    Salary.report_month.like(f'{year}-%')
                ).scalar()

            # За месяц
            paid_by_month = 0
            if year and month:
                paid_by_month = db.query(
                    func.coalesce(func.sum(Salary.amount), 0)
                ).filter(
                    Salary.report_month == f'{year}-{month:02d}'
                ).scalar()

            # Количество выплат (все оклады)
            payments_count = db.query(func.count(Salary.id)).scalar()

            # К оплате - для окладов всегда 0 (нет статуса)
            to_pay_amount = 0

            # По агенту - для окладов не применимо
            by_agent = 0

        else:
            # Условие фильтрации по типу
            query_filter = []
            if payment_type == 'individual':
                query_filter.append(Contract.project_type == 'Индивидуальный')
            elif payment_type == 'template':
                query_filter.append(Contract.project_type == 'Шаблонный')
            elif payment_type == 'supervision':
                query_filter.append(Contract.status == 'АВТОРСКИЙ НАДЗОР')
            # 'all' - без дополнительного фильтра

            # Всего выплачено
            q = db.query(func.coalesce(func.sum(Payment.final_amount), 0))
            if query_filter:
                q = q.join(Contract)
                for f in query_filter:
                    q = q.filter(f)
            total_paid = q.filter(Payment.payment_status == 'paid').scalar()

            # За год
            paid_by_year = 0
            if year:
                q = db.query(func.coalesce(func.sum(Payment.final_amount), 0))
                if query_filter:
                    q = q.join(Contract)
                    for f in query_filter:
                        q = q.filter(f)
                paid_by_year = q.filter(
                    Payment.payment_status == 'paid',
                    Payment.report_month.like(f'{year}-%')
                ).scalar()

            # За месяц
            paid_by_month = 0
            if year and month:
                q = db.query(func.coalesce(func.sum(Payment.final_amount), 0))
                if query_filter:
                    q = q.join(Contract)
                    for f in query_filter:
                        q = q.filter(f)
                paid_by_month = q.filter(
                    Payment.payment_status == 'paid',
                    Payment.report_month == f'{year}-{month:02d}'
                ).scalar()

            # Количество выплат (paid)
            q = db.query(func.count(Payment.id))
            if query_filter:
                q = q.join(Contract)
                for f in query_filter:
                    q = q.filter(f)
            payments_count = q.filter(Payment.payment_status == 'paid').scalar()

            # К оплате
            q = db.query(func.coalesce(func.sum(Payment.final_amount), 0))
            if query_filter:
                q = q.join(Contract)
                for f in query_filter:
                    q = q.filter(f)
            to_pay_amount = q.filter(Payment.payment_status == 'to_pay').scalar()

            # По агенту
            by_agent = 0
            if agent_type:
                q = db.query(func.coalesce(func.sum(Payment.final_amount), 0)).join(Contract)
                if query_filter:
                    for f in query_filter:
                        q = q.filter(f)
                by_agent = q.filter(
                    Payment.payment_status == 'paid',
                    Contract.agent_type == agent_type
                ).scalar()

        return {
            'total_paid': float(total_paid) if total_paid else 0,
            'paid_by_year': float(paid_by_year) if paid_by_year else 0,
            'paid_by_month': float(paid_by_month) if paid_by_month else 0,
            'payments_count': int(payments_count) if payments_count else 0,
            'to_pay_amount': float(to_pay_amount) if to_pay_amount else 0,
            'by_agent': float(by_agent) if by_agent else 0
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда зарплат по типу: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries-all")
async def get_salaries_all_dashboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Дашборд 'Все выплаты': total_paid, paid_by_year, paid_by_month, individual/template/supervision_by_year
    Учитываются payments (CRM) + salaries (оклады)"""
    try:
        # Всего выплачено (payments + salaries)
        payments_total = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0)
        ).filter(Payment.payment_status == 'paid').scalar()
        salaries_total = db.query(
            func.coalesce(func.sum(Salary.amount), 0)
        ).filter(Salary.payment_status == 'paid').scalar()
        total_paid = float(payments_total or 0) + float(salaries_total or 0)

        # За год
        paid_by_year = 0
        individual_by_year = 0
        template_by_year = 0
        supervision_by_year = 0

        if year:
            # Payments за год
            payments_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%')
            ).scalar()
            # Salaries за год
            salaries_year = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%')
            ).scalar()
            paid_by_year = float(payments_year or 0) + float(salaries_year or 0)

            # Индивидуальные за год (payments + оклады с project_type='Индивидуальный' )
            ind_payments = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.project_type == 'Индивидуальный'
            ).scalar()
            ind_salaries = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%'),
                Salary.project_type == 'Индивидуальный'
            ).scalar()
            individual_by_year = float(ind_payments or 0) + float(ind_salaries or 0)

            # Шаблонные за год
            tmpl_payments = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.project_type == 'Шаблонный'
            ).scalar()
            tmpl_salaries = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%'),
                Salary.project_type == 'Шаблонный'
            ).scalar()
            template_by_year = float(tmpl_payments or 0) + float(tmpl_salaries or 0)

            # Авторский надзор за год
            sup_payments = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Payment.supervision_card_id.isnot(None)
            ).scalar()
            sup_salaries = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%'),
                Salary.project_type == 'Авторский надзор'
            ).scalar()
            supervision_by_year = float(sup_payments or 0) + float(sup_salaries or 0)

        # За месяц (payments + salaries)
        paid_by_month = 0
        if year and month:
            payments_month = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar()
            salaries_month = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month == f'{year}-{month:02d}'
            ).scalar()
            paid_by_month = float(payments_month or 0) + float(salaries_month or 0)

        return {
            'total_paid': total_paid,
            'paid_by_year': paid_by_year,
            'paid_by_month': paid_by_month,
            'individual_by_year': individual_by_year,
            'template_by_year': template_by_year,
            'supervision_by_year': supervision_by_year
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда всех зарплат: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries-individual")
async def get_salaries_individual_dashboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Дашборд 'Индивидуальные': total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
    Учитываются payments (CRM) + salaries (оклады с project_type='Индивидуальный' )"""
    try:
        # Всего выплачено и средний чек (payments)
        total_result = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0),
            func.coalesce(func.avg(Payment.final_amount), 0)
        ).join(Contract).filter(
            Payment.payment_status == 'paid',
            Contract.project_type == 'Индивидуальный'
        ).first()
        total_paid = float(total_result[0] or 0)
        avg_payment = total_result[1]
        # + оклады
        total_paid += float(db.query(
            func.coalesce(func.sum(Salary.amount), 0)
        ).filter(
            Salary.payment_status == 'paid',
            Salary.project_type == 'Индивидуальный'
        ).scalar() or 0)

        # За год и кол-во выплат
        paid_by_year = 0
        payments_count = 0
        if year:
            year_result = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0),
                func.count(Payment.id)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Индивидуальный',
                Payment.report_month.like(f'{year}-%')
            ).first()
            paid_by_year = float(year_result[0] or 0)
            payments_count = int(year_result[1] or 0)
            # + оклады за год
            sal_year = db.query(
                func.coalesce(func.sum(Salary.amount), 0),
                func.count(Salary.id)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%'),
                Salary.project_type == 'Индивидуальный'
            ).first()
            paid_by_year += float(sal_year[0] or 0)
            payments_count += int(sal_year[1] or 0)

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = float(db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Индивидуальный',
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar() or 0)
            # + оклады за месяц
            paid_by_month += float(db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month == f'{year}-{month:02d}',
                Salary.project_type == 'Индивидуальный'
            ).scalar() or 0)

        # По агенту (оклады не привязаны к агентам)
        by_agent = 0
        if agent_type:
            by_agent = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Индивидуальный',
                Contract.agent_type == agent_type
            ).scalar()

        result = {
            'total_paid': total_paid,
            'paid_by_year': paid_by_year,
            'paid_by_month': paid_by_month,
            'by_agent': float(by_agent) if by_agent else 0,
            'avg_payment': float(avg_payment) if avg_payment else 0,
            'payments_count': payments_count
        }
        logger.info(f"[DASHBOARD] salaries-individual: year={year}, month={month}, agent={agent_type} -> {result}")
        return result

    except Exception as e:
        logger.exception(f"Ошибка дашборда индивидуальных зарплат: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries-template")
async def get_salaries_template_dashboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Дашборд 'Шаблонные': total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
    Учитываются payments (CRM) + salaries (оклады с project_type='Шаблонный' )"""
    try:
        # Всего выплачено и средний чек (payments)
        total_result = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0),
            func.coalesce(func.avg(Payment.final_amount), 0)
        ).join(Contract).filter(
            Payment.payment_status == 'paid',
            Contract.project_type == 'Шаблонный'
        ).first()
        total_paid_payments = float(total_result[0] or 0)
        avg_payment = total_result[1]
        # + оклады
        total_paid_salaries = float(db.query(
            func.coalesce(func.sum(Salary.amount), 0)
        ).filter(
            Salary.payment_status == 'paid',
            Salary.project_type == 'Шаблонный'
        ).scalar() or 0)
        total_paid = total_paid_payments + total_paid_salaries

        # За год и кол-во выплат
        paid_by_year = 0
        payments_count = 0
        if year:
            year_result = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0),
                func.count(Payment.id)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Шаблонный',
                Payment.report_month.like(f'{year}-%')
            ).first()
            paid_by_year = float(year_result[0] or 0)
            payments_count = int(year_result[1] or 0)
            # + оклады за год
            sal_year = db.query(
                func.coalesce(func.sum(Salary.amount), 0),
                func.count(Salary.id)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%'),
                Salary.project_type == 'Шаблонный'
            ).first()
            paid_by_year += float(sal_year[0] or 0)
            payments_count += int(sal_year[1] or 0)

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = float(db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Шаблонный',
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar() or 0)
            # + оклады за месяц
            paid_by_month += float(db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month == f'{year}-{month:02d}',
                Salary.project_type == 'Шаблонный'
            ).scalar() or 0)

        # По агенту (оклады не привязаны к агентам — только payments)
        by_agent = 0
        if agent_type:
            by_agent = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Шаблонный',
                Contract.agent_type == agent_type
            ).scalar()

        return {
            'total_paid': total_paid,
            'paid_by_year': paid_by_year,
            'paid_by_month': paid_by_month,
            'by_agent': float(by_agent) if by_agent else 0,
            'avg_payment': float(avg_payment) if avg_payment else 0,
            'payments_count': payments_count
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда шаблонных зарплат: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries-salary")
async def get_salaries_salary_dashboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    project_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Дашборд 'Оклады': total_paid, paid_by_year, paid_by_month, by_project_type, avg_salary, employees_count"""
    try:
        # Всего выплачено и средний оклад (только оплаченные)
        total_result = db.query(
            func.coalesce(func.sum(Salary.amount), 0),
            func.coalesce(func.avg(Salary.amount), 0)
        ).filter(
            Salary.payment_status == 'paid'
        ).first()
        total_paid = total_result[0]
        avg_salary = total_result[1]

        # За год и кол-во уникальных сотрудников (только оплаченные)
        paid_by_year = 0
        employees_count = 0
        if year:
            year_result = db.query(
                func.coalesce(func.sum(Salary.amount), 0),
                func.count(func.distinct(Salary.employee_id))
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%')
            ).first()
            paid_by_year = year_result[0]
            employees_count = year_result[1]

        # За месяц (только оплаченные)
        paid_by_month = 0
        if year and month:
            paid_by_month = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month == f'{year}-{month:02d}'
            ).scalar()

        # По типу проекта (только оплаченные)
        by_project_type = 0
        if project_type:
            by_project_type = db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.project_type == project_type
            ).scalar()

        return {
            'total_paid': float(total_paid) if total_paid else 0,
            'paid_by_year': float(paid_by_year) if paid_by_year else 0,
            'paid_by_month': float(paid_by_month) if paid_by_month else 0,
            'by_project_type': float(by_project_type) if by_project_type else 0,
            'avg_salary': float(avg_salary) if avg_salary else 0,
            'employees_count': int(employees_count) if employees_count else 0
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда окладов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/salaries-supervision")
async def get_salaries_supervision_dashboard(
    year: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Дашборд 'Авторский надзор': total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count
    Учитываются payments (supervision) + salaries (оклады с project_type='Авторский надзор' )"""
    try:
        # Всего выплачено и средний чек (payments)
        total_result = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0),
            func.coalesce(func.avg(Payment.final_amount), 0)
        ).filter(
            Payment.payment_status == 'paid',
            Payment.supervision_card_id.isnot(None)
        ).first()
        total_paid = float(total_result[0] or 0)
        avg_payment = total_result[1]
        # + оклады
        total_paid += float(db.query(
            func.coalesce(func.sum(Salary.amount), 0)
        ).filter(
            Salary.payment_status == 'paid',
            Salary.project_type == 'Авторский надзор'
        ).scalar() or 0)

        # За год и кол-во выплат
        paid_by_year = 0
        payments_count = 0
        if year:
            year_result = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0),
                func.count(Payment.id)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.supervision_card_id.isnot(None),
                Payment.report_month.like(f'{year}-%')
            ).first()
            paid_by_year = float(year_result[0] or 0)
            payments_count = int(year_result[1] or 0)
            # + оклады за год
            sal_year = db.query(
                func.coalesce(func.sum(Salary.amount), 0),
                func.count(Salary.id)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month.like(f'{year}-%'),
                Salary.project_type == 'Авторский надзор'
            ).first()
            paid_by_year += float(sal_year[0] or 0)
            payments_count += int(sal_year[1] or 0)

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = float(db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.supervision_card_id.isnot(None),
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar() or 0)
            # + оклады за месяц
            paid_by_month += float(db.query(
                func.coalesce(func.sum(Salary.amount), 0)
            ).filter(
                Salary.payment_status == 'paid',
                Salary.report_month == f'{year}-{month:02d}',
                Salary.project_type == 'Авторский надзор'
            ).scalar() or 0)

        # По агенту (оклады не привязаны к агентам)
        by_agent = 0
        if agent_type:
            by_agent = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(SupervisionCard, Payment.supervision_card_id == SupervisionCard.id
            ).join(Contract, SupervisionCard.contract_id == Contract.id
            ).filter(
                Payment.payment_status == 'paid',
                Payment.supervision_card_id.isnot(None),
                Contract.agent_type == agent_type
            ).scalar()

        return {
            'total_paid': total_paid,
            'paid_by_year': paid_by_year,
            'paid_by_month': paid_by_month,
            'by_agent': float(by_agent) if by_agent else 0,
            'avg_payment': float(avg_payment) if avg_payment else 0,
            'payments_count': payments_count
        }

    except Exception as e:
        logger.exception(f"Ошибка дашборда надзорных зарплат: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/agent-types")
async def get_agent_types(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех типов агентов"""
    try:
        agents = db.query(Contract.agent_type).filter(
            Contract.agent_type.isnot(None),
            Contract.agent_type != ''
        ).distinct().order_by(Contract.agent_type).all()

        return [agent[0] for agent in agents]

    except Exception as e:
        logger.exception(f"Ошибка получения типов агентов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/contract-years")
async def get_contract_years(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех годов из договоров (для фильтров дашборда)

    Возвращает список годов в обратном порядке (от нового к старому),
    включая текущий год и следующий год.
    """
    try:
        from datetime import datetime
        from sqlalchemy import func

        # Получаем все уникальные годы из дат договоров (contract_date — VARCHAR формата YYYY-MM-DD)
        years_query = db.query(
            func.substr(Contract.contract_date, 1, 4).label('year')
        ).filter(
            Contract.contract_date.isnot(None),
            Contract.contract_date != ''
        ).distinct().all()

        db_years = set()
        for row in years_query:
            if row.year:
                try:
                    db_years.add(int(row.year))
                except (ValueError, TypeError):
                    pass

        # Добавляем текущий год и следующий год
        current_year = datetime.now().year
        next_year = current_year + 1

        db_years.add(current_year)
        db_years.add(next_year)

        # Сортируем в обратном порядке (от нового к старому)
        years_list = sorted(db_years, reverse=True)

        return years_list

    except Exception as e:
        logger.error(f"Contract years error: {e}")
        # Возвращаем fallback
        from datetime import datetime
        current_year = datetime.now().year
        return list(range(current_year + 1, current_year - 10, -1))


# =============================================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ОТЧЁТОВ
# =============================================================================

def _parse_contract_date(date_str: str):
    """Разбирает дату договора из форматов ДД.ММ.ГГГГ или YYYY-MM-DD.
    Возвращает объект datetime или None."""
    if not date_str:
        return None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d'):
        try:
            return datetime.strptime(date_str.strip(), fmt)
        except ValueError:
            pass
    return None


def _get_period_key(dt: datetime, granularity: str) -> str:
    """Возвращает ключ периода: '2026-01' или '2026-Q1'."""
    if granularity == 'quarter':
        q = (dt.month - 1) // 3 + 1
        return f"{dt.year}-Q{q}"
    return f"{dt.year}-{dt.month:02d}"


def _apply_period_filter(contracts: list, year: Optional[int], quarter: Optional[int], month: Optional[int]) -> list:
    """Фильтрует список контрактов по году/кварталу/месяцу в Python (дата — VARCHAR)."""
    if not year and not quarter and not month:
        return contracts
    result = []
    for c in contracts:
        dt = _parse_contract_date(c.contract_date)
        if dt is None:
            continue
        if year and dt.year != year:
            continue
        if quarter and (dt.month - 1) // 3 + 1 != quarter:
            continue
        if month and dt.month != month:
            continue
        result.append(c)
    return result


def _get_prev_period_filter(year: Optional[int], quarter: Optional[int], month: Optional[int]):
    """Возвращает параметры (year, quarter, month) для аналогичного прошлого периода."""
    if year:
        return year - 1, quarter, month
    # Если год не задан — нет смысла считать тренд
    return None, None, None


# =============================================================================
# ENDPOINT 1: GET /reports/summary
# =============================================================================

@router.get("/reports/summary")
async def get_reports_summary(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    project_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Агрегация KPI-метрик с разбивкой по агентам для страницы Отчёты."""
    try:
        # --- Загрузить все договоры одним запросом, потом фильтровать в Python ---
        # Исключаем Авторский надзор — для него отдельная секция
        query = db.query(Contract).filter(
            Contract.project_type != 'Авторский надзор'
        )
        if agent_type:
            query = query.filter(Contract.agent_type == agent_type)
        if city:
            query = query.filter(Contract.city == city)
        if project_type:
            query = query.filter(Contract.project_type == project_type)

        all_contracts = query.all()

        # Применяем фильтр по периоду в Python (дата хранится как VARCHAR)
        filtered = _apply_period_filter(all_contracts, year, quarter, month)

        # --- KPI метрики ---
        filtered_client_ids = {c.client_id for c in filtered}
        total_clients = len(filtered_client_ids)
        total_contracts = len(filtered)
        total_amount = sum(c.total_amount or 0 for c in filtered)
        avg_amount = total_amount / total_contracts if total_contracts else 0.0
        total_area = sum(c.area or 0 for c in filtered)
        avg_area = total_area / total_contracts if total_contracts else 0.0

        # Новые клиенты: клиенты, у которых ПЕРВЫЙ договор (за всё время) попадает в период
        # Для этого берём все договоры без фильтра по периоду, но с теми же прочими фильтрами
        client_ids_in_period = filtered_client_ids
        # Первые даты договора для каждого клиента (по всем договорам с теми же прочими фильтрами)
        client_first_date: dict = {}
        for c in all_contracts:
            dt = _parse_contract_date(c.contract_date)
            if dt is None:
                continue
            cid = c.client_id
            if cid not in client_first_date or dt < client_first_date[cid]:
                client_first_date[cid] = dt

        new_clients = 0
        for cid in client_ids_in_period:
            dt = client_first_date.get(cid)
            if dt is None:
                continue
            # Проверяем, попадает ли первый договор в период
            check = _apply_period_filter(
                [type('C', (), {'contract_date': dt.strftime('%Y-%m-%d'), 'client_id': cid})()],
                year, quarter, month
            )
            if check:
                new_clients += 1

        # Повторные клиенты: клиенты с >1 договором (за всё время), имеющие договор в периоде
        client_contract_count: dict = defaultdict(int)
        for c in all_contracts:
            client_contract_count[c.client_id] += 1
        returning_clients = sum(
            1 for cid in client_ids_in_period if client_contract_count.get(cid, 0) > 1
        )

        # % завершённых проектов в срок (column_name='Выполненный проект')
        # Берём только договоры из отфильтрованного списка
        filtered_contract_ids = {c.id for c in filtered}
        contracts_on_time_pct = 0.0
        if filtered_contract_ids:
            completed_cards = db.query(CRMCard).filter(
                CRMCard.contract_id.in_(filtered_contract_ids),
                CRMCard.column_name == 'Выполненный проект'
            ).all()
            if completed_cards:
                on_time_count = 0
                for card in completed_cards:
                    if card.deadline and card.updated_at:
                        try:
                            deadline_dt = datetime.strptime(card.deadline.strip(), '%Y-%m-%d')
                            if card.updated_at <= deadline_dt:
                                on_time_count += 1
                        except ValueError:
                            pass
                contracts_on_time_pct = round(on_time_count / len(completed_cards) * 100, 1)

        # % стадий выполненных в срок (через StageExecutor)
        stages_on_time_pct = 0.0
        if filtered_contract_ids:
            # Получаем crm_card_ids для отфильтрованных договоров
            crm_card_ids = [
                row[0] for row in db.query(CRMCard.id).filter(
                    CRMCard.contract_id.in_(filtered_contract_ids)
                ).all()
            ]
            if crm_card_ids:
                completed_stages = db.query(StageExecutor).filter(
                    StageExecutor.crm_card_id.in_(crm_card_ids),
                    StageExecutor.completed == True
                ).all()
                if completed_stages:
                    on_time_stages = 0
                    for stage in completed_stages:
                        if stage.deadline and stage.completed_date:
                            try:
                                deadline_dt = datetime.strptime(stage.deadline.strip(), '%Y-%m-%d')
                                if stage.completed_date <= deadline_dt:
                                    on_time_stages += 1
                            except ValueError:
                                pass
                    stages_on_time_pct = round(on_time_stages / len(completed_stages) * 100, 1)

        # --- Тренды: сравнение с аналогичным прошлым периодом ---
        prev_year, prev_quarter, prev_month = _get_prev_period_filter(year, quarter, month)
        trend_clients = 0.0
        trend_contracts = 0.0
        trend_amount = 0.0

        if prev_year is not None:
            prev_filtered = _apply_period_filter(all_contracts, prev_year, prev_quarter, prev_month)
            prev_clients = len({c.client_id for c in prev_filtered})
            prev_contracts = len(prev_filtered)
            prev_amount = sum(c.total_amount or 0 for c in prev_filtered)

            if prev_clients > 0:
                trend_clients = round((total_clients - prev_clients) / prev_clients * 100, 1)
            if prev_contracts > 0:
                trend_contracts = round((total_contracts - prev_contracts) / prev_contracts * 100, 1)
            if prev_amount > 0:
                trend_amount = round((total_amount - prev_amount) / prev_amount * 100, 1)

        # --- Разбивка по агентам (из справочника Agent) ---
        agents_list = db.query(Agent).filter(Agent.status == 'активный').order_by(Agent.name).all()
        agent_color_map = {a.name: a.color for a in agents_list}

        # Группировка отфильтрованных договоров по agent_type
        agent_data: dict = defaultdict(lambda: {'clients': set(), 'contracts': 0, 'amount': 0.0, 'area': 0.0})
        for c in filtered:
            key = c.agent_type or 'Не указан'
            agent_data[key]['clients'].add(c.client_id)
            agent_data[key]['contracts'] += 1
            agent_data[key]['amount'] += c.total_amount or 0
            agent_data[key]['area'] += c.area or 0

        by_agent = []
        for a in agents_list:
            data = agent_data.get(a.name, {'clients': set(), 'contracts': 0, 'amount': 0.0, 'area': 0.0})
            by_agent.append({
                'agent_name': a.name,
                'agent_color': a.color,
                'clients': len(data['clients']),
                'contracts': data['contracts'],
                'amount': round(data['amount'], 2),
                'area': round(data['area'], 2),
            })

        return {
            'total_clients': total_clients,
            'new_clients': new_clients,
            'returning_clients': returning_clients,
            'total_contracts': total_contracts,
            'total_amount': round(total_amount, 2),
            'avg_amount': round(avg_amount, 2),
            'total_area': round(total_area, 2),
            'avg_area': round(avg_area, 2),
            'contracts_on_time_pct': contracts_on_time_pct,
            'stages_on_time_pct': stages_on_time_pct,
            'trend_clients': trend_clients,
            'trend_contracts': trend_contracts,
            'trend_amount': trend_amount,
            'by_agent': by_agent,
        }

    except Exception as e:
        logger.exception(f"Ошибка отчёта summary: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =============================================================================
# ENDPOINT 2: GET /reports/clients-dynamics
# =============================================================================

@router.get("/reports/clients-dynamics")
async def get_clients_dynamics(
    year: Optional[int] = None,
    granularity: Optional[str] = "month",
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Динамика клиентов по месяцам/кварталам за указанный год."""
    try:
        target_year = year or datetime.now().year

        # Загружаем все договоры за нужный год (фильтрация в Python)
        # Исключаем Авторский надзор — для него отдельная секция
        all_contracts = db.query(Contract).filter(
            Contract.project_type != 'Авторский надзор'
        ).all()
        year_contracts = _apply_period_filter(all_contracts, target_year, None, None)

        # Загружаем типы клиентов
        client_type_map: dict = {}
        all_clients = db.query(Client.id, Client.client_type).all()
        for cid, ctype in all_clients:
            client_type_map[cid] = ctype or ''

        # Первый договор каждого клиента (по всем договорам)
        client_first_date: dict = {}
        for c in all_contracts:
            dt = _parse_contract_date(c.contract_date)
            if dt is None:
                continue
            cid = c.client_id
            if cid not in client_first_date or dt < client_first_date[cid]:
                client_first_date[cid] = dt

        # Кол-во договоров у каждого клиента (за всё время)
        client_contract_count: dict = defaultdict(int)
        for c in all_contracts:
            client_contract_count[c.client_id] += 1

        # Группировка по периодам
        period_data: dict = defaultdict(lambda: {
            'new_set': set(), 'returning_set': set(),
            'individual_set': set(), 'legal_set': set(), 'all_set': set()
        })

        for c in year_contracts:
            dt = _parse_contract_date(c.contract_date)
            if dt is None:
                continue
            period = _get_period_key(dt, granularity)
            cid = c.client_id
            period_data[period]['all_set'].add(cid)

            # Новый: первый договор в этом периоде (совпадает с первым договором вообще)
            first = client_first_date.get(cid)
            if first and _get_period_key(first, granularity) == period:
                period_data[period]['new_set'].add(cid)

            # Повторный: >1 договор за всё время + есть договор в периоде
            if client_contract_count.get(cid, 0) > 1:
                period_data[period]['returning_set'].add(cid)

            # Тип клиента
            ctype = client_type_map.get(cid, '')
            if 'Физическое' in ctype:
                period_data[period]['individual_set'].add(cid)
            elif 'Юридическое' in ctype:
                period_data[period]['legal_set'].add(cid)

        # Формируем упорядоченный список периодов
        if granularity == 'quarter':
            all_periods = [f"{target_year}-Q{q}" for q in range(1, 5)]
        else:
            all_periods = [f"{target_year}-{m:02d}" for m in range(1, 13)]

        result = []
        for period in all_periods:
            data = period_data.get(period, {})
            result.append({
                'period': period,
                'new_clients': len(data.get('new_set', set())),
                'returning_clients': len(data.get('returning_set', set())),
                'individual': len(data.get('individual_set', set())),
                'legal': len(data.get('legal_set', set())),
                'total': len(data.get('all_set', set())),
            })

        return result

    except Exception as e:
        logger.exception(f"Ошибка clients-dynamics: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =============================================================================
# ENDPOINT 3: GET /reports/contracts-dynamics
# =============================================================================

@router.get("/reports/contracts-dynamics")
async def get_contracts_dynamics(
    year: Optional[int] = None,
    granularity: Optional[str] = "month",
    agent_type: Optional[str] = None,
    city: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Динамика договоров по месяцам/кварталам (кол-во + стоимость по типам)."""
    try:
        target_year = year or datetime.now().year

        # Исключаем Авторский надзор — для него отдельная секция
        query = db.query(Contract).filter(
            Contract.project_type != 'Авторский надзор'
        )
        if agent_type:
            query = query.filter(Contract.agent_type == agent_type)
        if city:
            query = query.filter(Contract.city == city)

        all_contracts = query.all()
        year_contracts = _apply_period_filter(all_contracts, target_year, None, None)

        # Группировка по периодам (только Индивидуальный и Шаблонный)
        period_data: dict = defaultdict(lambda: {
            'individual_count': 0, 'template_count': 0,
            'individual_amount': 0.0, 'template_amount': 0.0,
        })

        for c in year_contracts:
            dt = _parse_contract_date(c.contract_date)
            if dt is None:
                continue
            period = _get_period_key(dt, granularity)
            amount = c.total_amount or 0.0
            ptype = c.project_type or ''

            if ptype == 'Шаблонный':
                period_data[period]['template_count'] += 1
                period_data[period]['template_amount'] += amount
            else:
                # Индивидуальный и прочие
                period_data[period]['individual_count'] += 1
                period_data[period]['individual_amount'] += amount

        # Формируем упорядоченный список периодов
        if granularity == 'quarter':
            all_periods = [f"{target_year}-Q{q}" for q in range(1, 5)]
        else:
            all_periods = [f"{target_year}-{m:02d}" for m in range(1, 13)]

        result = []
        for period in all_periods:
            d = period_data.get(period, {})
            ind_c = d.get('individual_count', 0)
            tmpl_c = d.get('template_count', 0)
            ind_a = d.get('individual_amount', 0.0)
            tmpl_a = d.get('template_amount', 0.0)
            result.append({
                'period': period,
                'individual_count': ind_c,
                'template_count': tmpl_c,
                'supervision_count': 0,
                'total_count': ind_c + tmpl_c,
                'individual_amount': round(ind_a, 2),
                'template_amount': round(tmpl_a, 2),
                'supervision_amount': 0.0,
                'total_amount': round(ind_a + tmpl_a, 2),
            })

        return result

    except Exception as e:
        logger.exception(f"Ошибка contracts-dynamics: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =============================================================================
# ENDPOINT 4: GET /reports/crm-analytics
# =============================================================================

@router.get("/reports/crm-analytics")
async def get_crm_analytics(
    project_type: Optional[str] = "Индивидуальный",
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """CRM аналитика: воронка стадий, соблюдение сроков, длительность стадий."""
    try:
        # CRM аналитика работает только для Индивидуальный и Шаблонный.
        # Авторский надзор обрабатывается в отдельном endpoint /reports/supervision-analytics
        use_supervision = False

        all_contracts = db.query(Contract).filter(
            Contract.project_type == project_type
        ).all()

        # Фильтр по периоду
        filtered_contracts = _apply_period_filter(all_contracts, year, quarter, month)
        filtered_ids = {c.id for c in filtered_contracts}

        if not filtered_ids:
            # Возвращаем пустую структуру
            return {
                'funnel': [],
                'on_time_stats': {
                    'projects_on_time': 0, 'projects_overdue': 0, 'projects_total': 0,
                    'projects_pct': 0.0, 'stages_on_time': 0, 'stages_overdue': 0,
                    'stages_total': 0, 'stages_pct': 0.0, 'avg_deviation_days': 0.0,
                },
                'stage_durations': [],
                'paused_count': 0,
                'active_count': 0,
                'archived_count': 0,
            }

        if use_supervision:
            crm_cards = db.query(SupervisionCard).filter(
                SupervisionCard.contract_id.in_(filtered_ids)
            ).all()
        else:
            crm_cards = db.query(CRMCard).filter(
                CRMCard.contract_id.in_(filtered_ids)
            ).all()

        # --- Воронка: GROUP BY column_name ---
        funnel_counter: dict = defaultdict(int)
        for card in crm_cards:
            funnel_counter[card.column_name] += 1

        # Порядок стадий воронки
        if project_type == 'Шаблонный':
            stage_order = [
                'Новый заказ', 'В ожидании',
                'Стадия 1: планировочные решения',
                'Стадия 2: чертежи',
                'Стадия 3: 3D визуализация',
                'Выполненный проект',
            ]
        elif use_supervision:
            stage_order = [
                'Новый заказ', 'В ожидании',
                'Стадия 1: Закупка керамогранита',
                'Стадия 2: Закупка плитки',
                'Стадия 3: Закупка паркета',
                'Стадия 4: Закупка сантехники',
                'Стадия 5: Закупка мебели кухни',
                'Стадия 6: Закупка дверей',
                'Стадия 7: Закупка электрики',
                'Стадия 8: Закупка освещения',
                'Стадия 9: Закупка сантехники и аксессуаров',
                'Стадия 10: Закупка мебели',
                'Стадия 11: Закупка текстиля',
                'Стадия 12: Закупка декора',
                'Выполненный проект',
            ]
        else:
            # Индивидуальный
            stage_order = [
                'Новый заказ', 'В ожидании',
                'Стадия 1: планировочные решения',
                'Стадия 2: концепция',
                'Стадия 3: чертежи',
                'Выполненный проект',
            ]

        # Собираем воронку в нужном порядке + все прочие стадии
        seen = set()
        funnel = []
        for stage in stage_order:
            funnel.append({'stage': stage, 'count': funnel_counter.get(stage, 0), 'avg_days': 0.0})
            seen.add(stage)
        for stage, cnt in funnel_counter.items():
            if stage not in seen:
                funnel.append({'stage': stage, 'count': cnt, 'avg_days': 0.0})

        # Средняя длительность стадий — из ProjectTimelineEntry (только для CRMCard)
        if not use_supervision and filtered_ids:
            timeline_entries = db.query(ProjectTimelineEntry).filter(
                ProjectTimelineEntry.contract_id.in_(filtered_ids)
            ).all()
            stage_actual_days: dict = defaultdict(list)
            for e in timeline_entries:
                if e.actual_days and e.actual_days > 0:
                    stage_actual_days[e.stage_name].append(e.actual_days)
            for item in funnel:
                days_list = stage_actual_days.get(item['stage'], [])
                item['avg_days'] = round(sum(days_list) / len(days_list), 1) if days_list else 0.0

        # --- On-time статистика ---
        # Проекты: column_name='Выполненный проект', сравниваем deadline с updated_at
        completed_cards = [c for c in crm_cards if c.column_name == 'Выполненный проект']
        projects_on_time = 0
        projects_overdue = 0
        deviation_days: list = []

        for card in completed_cards:
            if card.deadline and card.updated_at:
                try:
                    deadline_dt = datetime.strptime(card.deadline.strip(), '%Y-%m-%d')
                    delta = (card.updated_at - deadline_dt).days
                    deviation_days.append(delta)
                    if card.updated_at <= deadline_dt:
                        projects_on_time += 1
                    else:
                        projects_overdue += 1
                except ValueError:
                    pass

        projects_total = projects_on_time + projects_overdue
        projects_pct = round(projects_on_time / projects_total * 100, 1) if projects_total else 0.0
        avg_deviation = round(sum(deviation_days) / len(deviation_days), 1) if deviation_days else 0.0

        # Стадии (StageExecutor, только для CRM карточек)
        stages_on_time = 0
        stages_overdue = 0
        if not use_supervision and crm_cards:
            crm_card_ids = [c.id for c in crm_cards]
            completed_stages = db.query(StageExecutor).filter(
                StageExecutor.crm_card_id.in_(crm_card_ids),
                StageExecutor.completed == True
            ).all()
            for stage in completed_stages:
                if stage.deadline and stage.completed_date:
                    try:
                        deadline_dt = datetime.strptime(stage.deadline.strip(), '%Y-%m-%d')
                        if stage.completed_date <= deadline_dt:
                            stages_on_time += 1
                        else:
                            stages_overdue += 1
                    except ValueError:
                        pass

        stages_total = stages_on_time + stages_overdue
        stages_pct = round(stages_on_time / stages_total * 100, 1) if stages_total else 0.0

        on_time_stats = {
            'projects_on_time': projects_on_time,
            'projects_overdue': projects_overdue,
            'projects_total': projects_total,
            'projects_pct': projects_pct,
            'stages_on_time': stages_on_time,
            'stages_overdue': stages_overdue,
            'stages_total': stages_total,
            'stages_pct': stages_pct,
            'avg_deviation_days': avg_deviation,
        }

        # --- Длительность стадий (avg actual vs norm) ---
        stage_durations = []
        if not use_supervision and filtered_ids:
            # Группируем timeline entries по stage_name
            stage_actual: dict = defaultdict(list)
            stage_norm: dict = {}
            for e in timeline_entries:
                stage_actual[e.stage_name].append(e.actual_days or 0)
                stage_norm[e.stage_name] = e.norm_days or 0

            for sname, days_list in stage_actual.items():
                avg_actual = round(sum(days_list) / len(days_list), 1) if days_list else 0.0
                norm = stage_norm.get(sname, 0)
                on_time_pct_s = 0.0
                if days_list and norm > 0:
                    on_time_count_s = sum(1 for d in days_list if d <= norm)
                    on_time_pct_s = round(on_time_count_s / len(days_list) * 100, 1)
                stage_durations.append({
                    'stage': sname,
                    'avg_actual_days': avg_actual,
                    'norm_days': float(norm),
                    'on_time_pct': on_time_pct_s,
                })

        # --- Счётчики статусов ---
        paused_count = sum(1 for c in crm_cards if c.column_name == 'В ожидании')
        archived_statuses = {'Выполненный проект', 'СДАН', 'РАСТОРГНУТ'}
        active_count = sum(
            1 for c in crm_cards
            if c.column_name not in archived_statuses and c.column_name != 'В ожидании'
        )
        archived_count = sum(1 for c in crm_cards if c.column_name in archived_statuses)

        return {
            'funnel': funnel,
            'on_time_stats': on_time_stats,
            'stage_durations': stage_durations,
            'paused_count': paused_count,
            'active_count': active_count,
            'archived_count': archived_count,
        }

    except Exception as e:
        logger.exception(f"Ошибка crm-analytics: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =============================================================================
# ENDPOINT 5: GET /reports/supervision-analytics
# =============================================================================

@router.get("/reports/supervision-analytics")
async def get_supervision_analytics(
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Аналитика авторского надзора: стадии, бюджет, дефекты, визиты."""
    try:
        # Загружаем все надзорные карточки с договорами
        supervision_cards = db.query(SupervisionCard).all()
        supervision_card_ids_all = [c.id for c in supervision_cards]

        # Словарь contract_id → SupervisionCard
        sc_by_id = {c.id: c for c in supervision_cards}

        # Договоры для надзоров
        contract_ids_for_sup = [c.contract_id for c in supervision_cards]
        contracts_map: dict = {}
        if contract_ids_for_sup:
            for cont in db.query(Contract).filter(Contract.id.in_(contract_ids_for_sup)).all():
                contracts_map[cont.id] = cont

        # Фильтрация по периоду: через contract_date договора
        if year or quarter or month:
            filtered_sc = []
            for sc in supervision_cards:
                cont = contracts_map.get(sc.contract_id)
                if cont is None:
                    continue
                check = _apply_period_filter([cont], year, quarter, month)
                if check:
                    filtered_sc.append(sc)
        else:
            filtered_sc = supervision_cards

        filtered_sc_ids = {sc.id for sc in filtered_sc}

        # --- Итоговые счётчики ---
        total = len(filtered_sc)
        # Активные: не в архивных стадиях
        archived_stages = {'Выполненный проект', 'СДАН', 'РАСТОРГНУТ'}
        active = sum(1 for sc in filtered_sc if sc.column_name not in archived_stages)

        # --- По типу проекта (через договор) ---
        individual_count = 0
        template_count = 0
        for sc in filtered_sc:
            cont = contracts_map.get(sc.contract_id)
            if cont is None:
                continue
            ptype = cont.project_type or ''
            if ptype == 'Индивидуальный':
                individual_count += 1
            elif ptype == 'Шаблонный':
                template_count += 1

        # --- По агентам (из справочника Agent + договоры) ---
        agents_list = db.query(Agent).filter(Agent.status == 'активный').order_by(Agent.name).all()
        agent_counter: dict = defaultdict(int)
        for sc in filtered_sc:
            cont = contracts_map.get(sc.contract_id)
            if cont is None:
                continue
            agent_counter[cont.agent_type or 'Не указан'] += 1

        by_agent = []
        for a in agents_list:
            by_agent.append({
                'agent_name': a.name,
                'agent_color': a.color,
                'count': agent_counter.get(a.name, 0),
            })

        # --- По городам ---
        city_counter: dict = defaultdict(int)
        for sc in filtered_sc:
            cont = contracts_map.get(sc.contract_id)
            if cont is None:
                continue
            city_counter[cont.city or 'Не указан'] += 1

        by_city = [
            {'city': city, 'count': cnt}
            for city, cnt in sorted(city_counter.items(), key=lambda x: -x[1])
        ]

        # --- Стадии надзора (GROUP BY column_name) ---
        supervision_stage_names = [
            'Стадия 1: Закупка керамогранита',
            'Стадия 2: Закупка плитки',
            'Стадия 3: Закупка паркета',
            'Стадия 4: Закупка сантехники',
            'Стадия 5: Закупка мебели кухни',
            'Стадия 6: Закупка дверей',
            'Стадия 7: Закупка электрики',
            'Стадия 8: Закупка освещения',
            'Стадия 9: Закупка сантехники и аксессуаров',
            'Стадия 10: Закупка мебели',
            'Стадия 11: Закупка текстиля',
            'Стадия 12: Закупка декора',
        ]
        # Подсчёт через SupervisionTimelineEntry (stage_code → status)
        stages_result = []
        if filtered_sc_ids:
            timeline_entries = db.query(SupervisionTimelineEntry).filter(
                SupervisionTimelineEntry.supervision_card_id.in_(filtered_sc_ids)
            ).all()

            # Группировка по stage_name (используем stage_name)
            stage_active: dict = defaultdict(int)
            stage_completed: dict = defaultdict(int)
            for entry in timeline_entries:
                sname = entry.stage_name
                if entry.status in ('Завершено', 'Выполнено', 'completed'):
                    stage_completed[sname] += 1
                else:
                    stage_active[sname] += 1

            for sname in supervision_stage_names:
                stages_result.append({
                    'stage': sname,
                    'active': stage_active.get(sname, 0),
                    'completed': stage_completed.get(sname, 0),
                })
        else:
            stages_result = [{'stage': s, 'active': 0, 'completed': 0} for s in supervision_stage_names]

        # --- Бюджет и дефекты из SupervisionTimelineEntry ---
        total_planned = 0.0
        total_actual = 0.0
        total_savings = 0.0
        defects_found = 0
        defects_resolved = 0
        site_visits_total = 0

        if filtered_sc_ids:
            for entry in timeline_entries:
                total_planned += entry.budget_planned or 0.0
                total_actual += entry.budget_actual or 0.0
                total_savings += entry.budget_savings or 0.0
                defects_found += entry.defects_found or 0
                defects_resolved += entry.defects_resolved or 0
                site_visits_total += entry.site_visits or 0

        savings_pct = round(total_savings / total_planned * 100, 1) if total_planned > 0 else 0.0
        resolution_pct = round(defects_resolved / defects_found * 100, 1) if defects_found > 0 else 0.0

        return {
            'total': total,
            'active': active,
            'by_project_type': {
                'individual': individual_count,
                'template': template_count,
            },
            'by_agent': by_agent,
            'by_city': by_city,
            'stages': stages_result,
            'budget': {
                'total_planned': round(total_planned, 2),
                'total_actual': round(total_actual, 2),
                'total_savings': round(total_savings, 2),
                'savings_pct': savings_pct,
            },
            'defects': {
                'found': defects_found,
                'resolved': defects_resolved,
                'resolution_pct': resolution_pct,
            },
            'site_visits': site_visits_total,
        }

    except Exception as e:
        logger.exception(f"Ошибка supervision-analytics: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =============================================================================
# ENDPOINT 6: GET /reports/distribution
# =============================================================================

@router.get("/reports/distribution")
async def get_distribution(
    dimension: str,
    year: Optional[int] = None,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Универсальное распределение договоров по измерению (city|agent|project_type|subtype)."""
    try:
        # Загружаем все договоры (исключаем Авторский надзор — для него отдельная секция)
        all_contracts = db.query(Contract).filter(
            Contract.project_type != 'Авторский надзор'
        ).all()
        filtered = _apply_period_filter(all_contracts, year, quarter, month)

        # Функция извлечения значения измерения
        def get_dim_value(c: Contract) -> str:
            if dimension == 'city':
                return c.city or 'Не указан'
            elif dimension == 'agent':
                return c.agent_type or 'Не указан'
            elif dimension == 'project_type':
                return c.project_type or 'Не указан'
            elif dimension == 'subtype':
                return c.project_subtype or 'Не указан'
            else:
                return 'Неизвестно'

        # Группировка
        dim_data: dict = defaultdict(lambda: {'count': 0, 'amount': 0.0, 'area': 0.0})
        for c in filtered:
            key = get_dim_value(c)
            dim_data[key]['count'] += 1
            dim_data[key]['amount'] += c.total_amount or 0.0
            dim_data[key]['area'] += c.area or 0.0

        # Результат, сортировка по убыванию count
        result = [
            {
                'name': name,
                'count': data['count'],
                'amount': round(data['amount'], 2),
                'area': round(data['area'], 2),
            }
            for name, data in sorted(dim_data.items(), key=lambda x: -x[1]['count'])
        ]

        return result

    except Exception as e:
        logger.exception(f"Ошибка distribution (dimension={dimension}): {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
