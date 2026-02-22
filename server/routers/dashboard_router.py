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

Подключение в main.py:
  app.include_router(dashboard_router, prefix="/api/dashboard")
"""
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import get_current_user
from database import (
    get_db,
    Client, Contract, Employee,
    CRMCard, SupervisionCard,
    Payment, Salary,
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

        # 3. Активные заказы в СРМ
        active_orders = db.query(crm_table).count()

        # 4. Архивные заказы (считаем из истории или архивной таблицы)
        # Для упрощения считаем как разницу между всеми договорами и активными
        archive_orders = total_orders - active_orders if total_orders > active_orders else 0

        # 5. Активные заказы агента
        agent_active_orders = 0
        if agent_type:
            agent_active_orders = db.query(crm_table).join(
                Contract, crm_table.contract_id == Contract.id
            ).filter(Contract.agent_type == agent_type).count()

        # 6. Архивные заказы агента
        agent_archive_orders = 0
        if agent_type:
            agent_total = db.query(Contract).filter(
                contract_condition,
                Contract.agent_type == agent_type
            ).count()
            agent_archive_orders = agent_total - agent_active_orders if agent_total > agent_active_orders else 0

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
    """Дашборд 'Все выплаты': total_paid, paid_by_year, paid_by_month, individual/template/supervision_by_year"""
    try:
        # Всего выплачено
        total_paid = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0)
        ).filter(Payment.payment_status == 'paid').scalar()

        # За год
        paid_by_year = 0
        individual_by_year = 0
        template_by_year = 0
        supervision_by_year = 0

        if year:
            paid_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%')
            ).scalar()

            # Индивидуальные за год
            individual_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.project_type == 'Индивидуальный'
            ).scalar()

            # Шаблонные за год
            template_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Contract.project_type == 'Шаблонный'
            ).scalar()

            # Авторский надзор за год - платежи с supervision_card_id
            supervision_by_year = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month.like(f'{year}-%'),
                Payment.supervision_card_id.isnot(None)
            ).scalar()

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.report_month == f'{year}-{month:02d}'
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
    """Дашборд 'Индивидуальные': total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count"""
    try:
        base_q = db.query(Payment).join(Contract).filter(
            Payment.payment_status == 'paid',
            Contract.project_type == 'Индивидуальный'
        )

        # Всего выплачено и средний чек
        total_result = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0),
            func.coalesce(func.avg(Payment.final_amount), 0)
        ).join(Contract).filter(
            Payment.payment_status == 'paid',
            Contract.project_type == 'Индивидуальный'
        ).first()
        total_paid = total_result[0]
        avg_payment = total_result[1]

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
            paid_by_year = year_result[0]
            payments_count = year_result[1]

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Индивидуальный',
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar()

        # По агенту
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
            'total_paid': float(total_paid) if total_paid else 0,
            'paid_by_year': float(paid_by_year) if paid_by_year else 0,
            'paid_by_month': float(paid_by_month) if paid_by_month else 0,
            'by_agent': float(by_agent) if by_agent else 0,
            'avg_payment': float(avg_payment) if avg_payment else 0,
            'payments_count': int(payments_count) if payments_count else 0
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
    """Дашборд 'Шаблонные': total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count"""
    try:
        # Всего выплачено и средний чек
        total_result = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0),
            func.coalesce(func.avg(Payment.final_amount), 0)
        ).join(Contract).filter(
            Payment.payment_status == 'paid',
            Contract.project_type == 'Шаблонный'
        ).first()
        total_paid = total_result[0]
        avg_payment = total_result[1]

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
            paid_by_year = year_result[0]
            payments_count = year_result[1]

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).join(Contract).filter(
                Payment.payment_status == 'paid',
                Contract.project_type == 'Шаблонный',
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar()

        # По агенту
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
            'total_paid': float(total_paid) if total_paid else 0,
            'paid_by_year': float(paid_by_year) if paid_by_year else 0,
            'paid_by_month': float(paid_by_month) if paid_by_month else 0,
            'by_agent': float(by_agent) if by_agent else 0,
            'avg_payment': float(avg_payment) if avg_payment else 0,
            'payments_count': int(payments_count) if payments_count else 0
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
    """Дашборд 'Авторский надзор': total_paid, paid_by_year, paid_by_month, by_agent, avg_payment, payments_count"""
    try:
        # Всего выплачено и средний чек (надзорные = supervision_card_id IS NOT NULL)
        total_result = db.query(
            func.coalesce(func.sum(Payment.final_amount), 0),
            func.coalesce(func.avg(Payment.final_amount), 0)
        ).filter(
            Payment.payment_status == 'paid',
            Payment.supervision_card_id.isnot(None)
        ).first()
        total_paid = total_result[0]
        avg_payment = total_result[1]

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
            paid_by_year = year_result[0]
            payments_count = year_result[1]

        # За месяц
        paid_by_month = 0
        if year and month:
            paid_by_month = db.query(
                func.coalesce(func.sum(Payment.final_amount), 0)
            ).filter(
                Payment.payment_status == 'paid',
                Payment.supervision_card_id.isnot(None),
                Payment.report_month == f'{year}-{month:02d}'
            ).scalar()

        # По агенту (нужен JOIN через supervision_cards -> contracts)
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
            'total_paid': float(total_paid) if total_paid else 0,
            'paid_by_year': float(paid_by_year) if paid_by_year else 0,
            'paid_by_month': float(paid_by_month) if paid_by_month else 0,
            'by_agent': float(by_agent) if by_agent else 0,
            'avg_payment': float(avg_payment) if avg_payment else 0,
            'payments_count': int(payments_count) if payments_count else 0
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
