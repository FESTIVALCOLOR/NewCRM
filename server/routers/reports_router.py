"""
Роутер отчётов (reports).
Подключается в main.py через app.include_router(reports_router, prefix="/api/reports").
"""
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional

from database import (
    get_db, Employee, Contract, Payment, CRMCard, SupervisionCard,
    StageExecutor, Salary,
)
from auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(tags=["reports"])


@router.get("/employee")
async def get_employee_report_data(
    employee_id: int,
    year: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить данные для отчета сотрудника"""
    try:
        from sqlalchemy import extract

        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            raise HTTPException(status_code=404, detail="Сотрудник не найден")

        # Получаем назначения на стадии
        stage_query = db.query(StageExecutor).filter(StageExecutor.executor_id == employee_id)
        if year:
            stage_query = stage_query.filter(extract('year', StageExecutor.assigned_date) == year)
        if month:
            stage_query = stage_query.filter(extract('month', StageExecutor.assigned_date) == month)

        stages = stage_query.all()

        # Получаем платежи
        payment_query = db.query(Payment).filter(Payment.employee_id == employee_id)
        if year and month:
            report_month = f"{year}-{month:02d}"
            payment_query = payment_query.filter(Payment.report_month == report_month)

        payments = payment_query.all()

        total_stages = len(stages)
        completed_stages = len([s for s in stages if s.completed])
        total_payments = sum(p.final_amount or 0 for p in payments)

        return {
            'employee_id': employee_id,
            'employee_name': employee.full_name,
            'position': employee.position,
            'total_stages': total_stages,
            'completed_stages': completed_stages,
            'completion_rate': (completed_stages / total_stages * 100) if total_stages > 0 else 0,
            'total_payments': total_payments,
            'stages': [{
                'id': s.id,
                'stage_name': s.stage_name,
                'completed': s.completed,
                'assigned_date': s.assigned_date.isoformat() if s.assigned_date else None,
                'completed_date': s.completed_date.isoformat() if s.completed_date else None,
            } for s in stages],
            'payments': [{
                'id': p.id,
                'payment_type': p.payment_type,
                'amount': float(p.final_amount) if p.final_amount else 0,
                'report_month': p.report_month,
                'is_paid': p.is_paid
            } for p in payments]
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при получении отчета: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/employee-report")
async def get_employee_report_by_type(
    project_type: str,
    period: str,
    year: int,
    quarter: Optional[int] = None,
    month: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Получить данные для отчета по сотрудникам

    Сигнатура совпадает с database/db_manager.py:get_employee_report_data()

    Args:
        project_type: Тип проекта ('Индивидуальный' или 'Шаблонный')
        period: Период ('За год', 'За квартал', 'За месяц')
        year: Год
        quarter: Квартал (1-4)
        month: Месяц (1-12)

    Returns:
        completed: Список выполненных заказов по сотрудникам
        area: Список площадей по сотрудникам
        deadlines: Список просрочек
        salaries: Список зарплат
    """
    try:
        from sqlalchemy import extract, func, and_

        # Строим условие по периоду
        def build_period_condition(date_column):
            """Строит условие фильтрации по периоду"""
            conditions = [extract('year', date_column) == year]

            if period == 'За квартал' and quarter:
                start_month = (quarter - 1) * 3 + 1
                end_month = quarter * 3
                conditions.append(extract('month', date_column).between(start_month, end_month))
            elif period == 'За месяц' and month:
                conditions.append(extract('month', date_column) == month)

            return and_(*conditions) if len(conditions) > 1 else conditions[0]

        # 1. Выполненные заказы - группировка по сотрудникам
        completed_query = db.query(
            Employee.full_name.label('employee_name'),
            Employee.position,
            func.count(StageExecutor.id).label('count')
        ).join(
            StageExecutor, StageExecutor.executor_id == Employee.id
        ).join(
            CRMCard, StageExecutor.crm_card_id == CRMCard.id
        ).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type,
            StageExecutor.completed == True
        )

        # Добавляем фильтр по периоду для completed_date
        if period == 'За квартал' and quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            completed_query = completed_query.filter(
                extract('year', StageExecutor.completed_date) == year,
                extract('month', StageExecutor.completed_date).between(start_month, end_month)
            )
        elif period == 'За месяц' and month:
            completed_query = completed_query.filter(
                extract('year', StageExecutor.completed_date) == year,
                extract('month', StageExecutor.completed_date) == month
            )
        else:  # За год
            completed_query = completed_query.filter(
                extract('year', StageExecutor.completed_date) == year
            )

        completed_data = completed_query.group_by(
            StageExecutor.executor_id,
            Employee.full_name,
            Employee.position
        ).order_by(func.count(StageExecutor.id).desc()).all()

        completed = [
            {'employee_name': row.employee_name, 'position': row.position, 'count': row.count}
            for row in completed_data
        ]

        # 2. Площадь по сотрудникам
        area_query = db.query(
            Employee.full_name.label('employee_name'),
            Employee.position,
            func.sum(Contract.area).label('total_area')
        ).join(
            StageExecutor, StageExecutor.executor_id == Employee.id
        ).join(
            CRMCard, StageExecutor.crm_card_id == CRMCard.id
        ).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type,
            StageExecutor.completed == True
        )

        # Добавляем фильтр по периоду
        if period == 'За квартал' and quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            area_query = area_query.filter(
                extract('year', StageExecutor.completed_date) == year,
                extract('month', StageExecutor.completed_date).between(start_month, end_month)
            )
        elif period == 'За месяц' and month:
            area_query = area_query.filter(
                extract('year', StageExecutor.completed_date) == year,
                extract('month', StageExecutor.completed_date) == month
            )
        else:  # За год
            area_query = area_query.filter(
                extract('year', StageExecutor.completed_date) == year
            )

        area_data = area_query.group_by(
            StageExecutor.executor_id,
            Employee.full_name,
            Employee.position
        ).order_by(func.sum(Contract.area).desc()).all()

        area = [
            {'employee_name': row.employee_name, 'position': row.position, 'total_area': float(row.total_area or 0)}
            for row in area_data
        ]

        # 3. Просрочки дедлайнов (PostgreSQL-совместимый вариант)
        # Используем EXTRACT(EPOCH FROM ...) / 86400 для получения дней
        deadlines_query = db.query(
            Employee.full_name.label('employee_name'),
            func.count().label('overdue_count'),
            func.avg(
                func.extract('epoch', StageExecutor.completed_date - StageExecutor.deadline) / 86400.0
            ).label('avg_overdue_days')
        ).join(
            StageExecutor, StageExecutor.executor_id == Employee.id
        ).join(
            CRMCard, StageExecutor.crm_card_id == CRMCard.id
        ).join(
            Contract, CRMCard.contract_id == Contract.id
        ).filter(
            Contract.project_type == project_type,
            StageExecutor.completed == True,
            StageExecutor.completed_date > StageExecutor.deadline
        )

        # Добавляем фильтр по периоду
        if period == 'За квартал' and quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            deadlines_query = deadlines_query.filter(
                extract('year', StageExecutor.completed_date) == year,
                extract('month', StageExecutor.completed_date).between(start_month, end_month)
            )
        elif period == 'За месяц' and month:
            deadlines_query = deadlines_query.filter(
                extract('year', StageExecutor.completed_date) == year,
                extract('month', StageExecutor.completed_date) == month
            )
        else:  # За год
            deadlines_query = deadlines_query.filter(
                extract('year', StageExecutor.completed_date) == year
            )

        deadlines_data = deadlines_query.group_by(
            StageExecutor.executor_id,
            Employee.full_name
        ).order_by(func.count().desc()).all()

        deadlines = [
            {
                'employee_name': row.employee_name,
                'overdue_count': row.overdue_count,
                'avg_overdue_days': float(row.avg_overdue_days or 0)
            }
            for row in deadlines_data
        ]

        # 4. Зарплаты по сотрудникам
        salaries_query = db.query(
            Employee.full_name.label('employee_name'),
            Employee.position,
            func.sum(Salary.amount).label('total_salary')
        ).join(
            Salary, Salary.employee_id == Employee.id
        ).filter(
            Salary.payment_type.ilike(f'%{project_type}%')
        )

        # Фильтр по report_month
        if period == 'За квартал' and quarter:
            start_month = (quarter - 1) * 3 + 1
            end_month = quarter * 3
            months_pattern = '|'.join([f'{year}-{m:02d}' for m in range(start_month, end_month + 1)])
            salaries_query = salaries_query.filter(
                Salary.report_month.op('~')(months_pattern)
            )
        elif period == 'За месяц' and month:
            salaries_query = salaries_query.filter(
                Salary.report_month == f'{year}-{month:02d}'
            )
        else:  # За год
            salaries_query = salaries_query.filter(
                Salary.report_month.like(f'{year}-%')
            )

        salaries_data = salaries_query.group_by(
            Salary.employee_id,
            Employee.full_name,
            Employee.position
        ).order_by(func.sum(Salary.amount).desc()).all()

        salaries = [
            {'employee_name': row.employee_name, 'position': row.position, 'total_salary': float(row.total_salary or 0)}
            for row in salaries_data
        ]

        return {
            'completed': completed,
            'area': area,
            'deadlines': deadlines,
            'salaries': salaries
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при получении отчета по сотрудникам: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
