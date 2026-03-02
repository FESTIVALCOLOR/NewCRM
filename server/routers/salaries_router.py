"""
Роутер для зарплат (salaries).
CRUD + отчет по зарплатам.
ВАЖНО: /report ПЕРЕД /{salary_id} (статический перед динамическим).
"""
import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db, Employee, Salary, ActivityLog
from auth import get_current_user
from permissions import require_permission
from schemas import SalaryCreate, SalaryUpdate, SalaryResponse, StatusResponse

logger = logging.getLogger(__name__)
router = APIRouter(tags=["salaries"])


@router.get("/", response_model=List[SalaryResponse])
async def get_salaries(
    report_month: Optional[str] = None,
    employee_id: Optional[int] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить зарплаты"""
    query = db.query(Salary)
    if report_month:
        query = query.filter(Salary.report_month == report_month)
    if employee_id:
        query = query.filter(Salary.employee_id == employee_id)
    return query.all()


# Статический путь ПЕРЕД /{salary_id}
@router.get("/report")
async def get_salary_report(
    report_month: Optional[str] = None,
    employee_id: Optional[int] = None,
    payment_type: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить отчет по зарплатам"""
    try:
        query = db.query(Salary)

        if report_month:
            query = query.filter(Salary.report_month == report_month)
        if employee_id:
            query = query.filter(Salary.employee_id == employee_id)
        if payment_type:
            query = query.filter(Salary.payment_type == payment_type)

        salaries = query.all()

        # Группировка по сотрудникам
        employee_totals = {}
        for s in salaries:
            emp_id = s.employee_id
            if emp_id not in employee_totals:
                emp = db.query(Employee).filter(Employee.id == emp_id).first()
                employee_totals[emp_id] = {
                    'employee_id': emp_id,
                    'employee_name': s.employee_name or (emp.full_name if emp else 'Неизвестный'),
                    'position': emp.position if emp else '',
                    'total_amount': 0,
                    'advance_payment': 0,
                    'records': []
                }

            employee_totals[emp_id]['total_amount'] += s.amount or 0
            employee_totals[emp_id]['advance_payment'] += s.advance_payment or 0
            employee_totals[emp_id]['records'].append({
                'id': s.id,
                'payment_type': s.payment_type,
                'stage_name': s.stage_name,
                'amount': s.amount,
                'report_month': s.report_month,
                'payment_status': s.payment_status
            })

        return {
            'report_month': report_month,
            'total_amount': sum(e['total_amount'] for e in employee_totals.values()),
            'employees': list(employee_totals.values())
        }

    except Exception as e:
        logger.exception(f"Ошибка при получении отчета по зарплатам: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# Динамические пути ПОСЛЕ статических

@router.get("/{salary_id}", response_model=SalaryResponse)
async def get_salary(
    salary_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить зарплату по ID"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Запись о зарплате не найдена")
    return salary


@router.post("/", response_model=SalaryResponse)
async def create_salary(
    salary_data: SalaryCreate,
    current_user: Employee = Depends(require_permission("salaries.create")),
    db: Session = Depends(get_db)
):
    """Создать запись о зарплате"""
    data = salary_data.model_dump()
    # Денормализация: сохраняем имя сотрудника для истории
    if data.get('employee_id') and not data.get('employee_name'):
        emp = db.query(Employee).filter(Employee.id == data['employee_id']).first()
        if emp:
            data['employee_name'] = emp.full_name
    salary = Salary(**data)
    db.add(salary)
    db.commit()
    db.refresh(salary)
    return salary


@router.put("/{salary_id}", response_model=SalaryResponse)
async def update_salary(
    salary_id: int,
    salary_data: SalaryUpdate,
    current_user: Employee = Depends(require_permission("salaries.update")),
    db: Session = Depends(get_db)
):
    """Обновить запись о зарплате"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Запись о зарплате не найдена")

    for field, value in salary_data.model_dump(exclude_unset=True).items():
        setattr(salary, field, value)

    db.commit()
    db.refresh(salary)

    return salary


@router.delete("/{salary_id}", response_model=StatusResponse)
async def delete_salary(
    salary_id: int,
    current_user: Employee = Depends(require_permission("salaries.delete")),
    db: Session = Depends(get_db)
):
    """Удалить запись о зарплате"""
    salary = db.query(Salary).filter(Salary.id == salary_id).first()
    if not salary:
        raise HTTPException(status_code=404, detail="Запись о зарплате не найдена")

    log = ActivityLog(
        employee_id=current_user.id,
        action_type="delete",
        entity_type="salary",
        entity_id=salary_id
    )
    db.add(log)

    db.delete(salary)
    db.commit()

    return {"status": "success", "message": "Запись о зарплате удалена"}
