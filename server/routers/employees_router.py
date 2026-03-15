"""
Роутер для эндпоинтов сотрудников и прав доступа.
Эндпоинты:
  GET/POST   /employees
  GET/PUT/DELETE /employees/{employee_id}
  GET        /permissions/definitions
  GET/PUT    /permissions/role-matrix
  GET/PUT    /permissions/{employee_id}
  POST       /permissions/{employee_id}/reset-to-defaults
"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from database import (
    get_db, Employee, ActivityLog, UserSession, ConcurrentEdit,
    StageExecutor, Payment, Salary, ActionHistory, CRMCard, SupervisionCard,
    UserPermission, RoleDefaultPermission
)
from auth import get_current_user, get_password_hash
from constants import POSITION_STUDIO_DIRECTOR, POSITION_SENIOR_MANAGER, ROLE_ADMIN, ROLE_DIRECTOR
from permissions import (
    require_permission, check_permission as perm_check,
    get_employee_permissions, set_employee_permissions, reset_to_defaults,
    load_role_matrix, save_role_matrix, load_permissions,
    PERMISSION_NAMES, DEFAULT_ROLE_PERMISSIONS, SUPERUSER_ROLES,
    NON_MATRIX_PERMISSIONS,
    invalidate_cache as invalidate_perm_cache,
)
from schemas import (
    EmployeeResponse, EmployeeCreate, EmployeeUpdate,
    PermissionSetRequest, PermissionResponse, PermissionDefinition,
    RoleMatrixResponse, RoleMatrixUpdateRequest, StatusResponse,
)
from datetime import datetime

logger = logging.getLogger(__name__)
router = APIRouter(tags=["employees"])


# =========================
# СОТРУДНИКИ
# =========================

@router.get("/employees", response_model=List[EmployeeResponse])
async def get_employees(
    skip: int = 0,
    limit: int = 100,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список сотрудников"""
    employees = db.query(Employee).offset(skip).limit(limit).all()
    return employees


@router.get("/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить сотрудника по ID"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")
    return employee


@router.post("/employees", response_model=EmployeeResponse, status_code=201)
async def create_employee(
    employee_data: EmployeeCreate,
    current_user: Employee = Depends(require_permission("employees.create")),
    db: Session = Depends(get_db)
):
    """Создать нового сотрудника"""

    # Проверка уникальности логина
    existing = db.query(Employee).filter(Employee.login == employee_data.login).first()
    if existing:
        raise HTTPException(status_code=400, detail="Логин уже занят")

    # Создание
    employee = Employee(
        **employee_data.model_dump(exclude={'password'}),
        password_hash=get_password_hash(employee_data.password),
        invite_temp_password=employee_data.password,
    )
    db.add(employee)
    db.commit()
    db.refresh(employee)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="create",
        entity_type="employee",
        entity_id=employee.id
    )
    db.add(log)
    db.commit()

    return employee


@router.put("/employees/{employee_id}", response_model=EmployeeResponse)
async def update_employee(
    employee_id: int,
    employee_data: EmployeeUpdate,
    current_user: Employee = Depends(require_permission("employees.update")),
    db: Session = Depends(get_db)
):
    """Обновить сотрудника"""

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # IDOR защита: Старший менеджер не может менять руководителей и других старших менеджеров
    protected_roles = [POSITION_STUDIO_DIRECTOR, ROLE_ADMIN, ROLE_DIRECTOR]
    if current_user.role == POSITION_SENIOR_MANAGER:
        if employee.role in protected_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав для изменения этого сотрудника")
        # Запрет повышения роли до руководителя
        update_data_check = employee_data.model_dump(exclude_unset=True)
        if 'role' in update_data_check and update_data_check['role'] in protected_roles:
            raise HTTPException(status_code=403, detail="Недостаточно прав для назначения этой роли")

    # Обновление полей
    update_data = employee_data.model_dump(exclude_unset=True)

    # Если обновляется пароль
    if 'password' in update_data:
        plain = update_data.pop('password')
        update_data['password_hash'] = get_password_hash(plain)
        update_data['invite_temp_password'] = plain  # для invite-письма

    for field, value in update_data.items():
        setattr(employee, field, value)

    employee.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(employee)

    # Cache invalidation при смене роли или должности
    if 'role' in update_data or 'position' in update_data or 'secondary_position' in update_data:
        invalidate_perm_cache(employee_id)

    # Лог
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="update",
        entity_type="employee",
        entity_id=employee.id
    )
    db.add(log)
    db.commit()

    return employee


@router.delete("/employees/{employee_id}", response_model=StatusResponse)
async def delete_employee(
    employee_id: int,
    current_user: Employee = Depends(require_permission("employees.delete")),
    db: Session = Depends(get_db)
):
    """Удалить сотрудника"""

    # Нельзя удалить самого себя
    if employee_id == current_user.id:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # Каскадное удаление связанных записей
    session_ids = [s.id for s in db.query(UserSession).filter(UserSession.employee_id == employee_id).all()]
    if session_ids:
        db.query(ConcurrentEdit).filter(ConcurrentEdit.session_id.in_(session_ids)).delete(synchronize_session=False)
    db.query(ConcurrentEdit).filter(ConcurrentEdit.employee_id == employee_id).delete(synchronize_session=False)
    db.query(ActivityLog).filter(ActivityLog.employee_id == employee_id).delete(synchronize_session=False)
    if session_ids:
        db.query(ActivityLog).filter(ActivityLog.session_id.in_(session_ids)).delete(synchronize_session=False)

    # S-07: SET NULL вместо hard delete — сохраняем историю платежей и зарплат
    db.query(StageExecutor).filter(StageExecutor.executor_id == employee_id).update(
        {"executor_id": None}, synchronize_session=False)
    db.query(StageExecutor).filter(StageExecutor.assigned_by == employee_id).update(
        {"assigned_by": None}, synchronize_session=False)
    db.query(Payment).filter(Payment.employee_id == employee_id).update(
        {"employee_id": None}, synchronize_session=False)
    db.query(Payment).filter(Payment.paid_by == employee_id).update(
        {"paid_by": None}, synchronize_session=False)
    db.query(Salary).filter(Salary.employee_id == employee_id).update(
        {"employee_id": None}, synchronize_session=False)
    db.query(ActionHistory).filter(ActionHistory.user_id == employee_id).delete(synchronize_session=False)

    # Обнуляем FK ссылки в crm_cards и supervision_cards
    for col in ['senior_manager_id', 'sdp_id', 'gap_id', 'manager_id', 'surveyor_id']:
        db.query(CRMCard).filter(getattr(CRMCard, col) == employee_id).update({col: None}, synchronize_session=False)
    for col in ['senior_manager_id', 'dan_id']:
        db.query(SupervisionCard).filter(getattr(SupervisionCard, col) == employee_id).update({col: None}, synchronize_session=False)

    # ORM cascade удалит: user_sessions, user_permissions, notifications
    db.delete(employee)
    db.commit()

    return {"status": "success", "message": "Сотрудник удален"}


# =========================
# ПРАВА ДОСТУПА (PERMISSIONS)
# =========================

@router.get("/permissions/definitions", response_model=List[PermissionDefinition])
async def get_permission_definitions(
    current_user: Employee = Depends(get_current_user),
):
    """Получить список всех доступных прав с описаниями"""
    return [
        {"name": name, "description": desc}
        for name, desc in PERMISSION_NAMES.items()
    ]


@router.get("/permissions/role-matrix", response_model=RoleMatrixResponse)
async def get_role_matrix(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить текущую матрицу прав по ролям"""
    matrix = load_role_matrix(db)
    return RoleMatrixResponse(roles=matrix)


@router.put("/permissions/role-matrix", response_model=RoleMatrixResponse)
async def update_role_matrix(
    request: RoleMatrixUpdateRequest,
    current_user: Employee = Depends(require_permission("employees.update")),
    db: Session = Depends(get_db)
):
    """Обновить матрицу прав по ролям"""
    # Валидация имён прав
    all_invalid = []
    for role, perms in request.roles.items():
        invalid = [p for p in perms if p not in PERMISSION_NAMES]
        all_invalid.extend(invalid)
    if all_invalid:
        raise HTTPException(
            status_code=400,
            detail=f"Неизвестные права: {', '.join(set(all_invalid))}"
        )

    # Сохраняем матрицу в БД
    save_role_matrix(request.roles, current_user.id, db)

    # Если запрошено — обновляем права всех сотрудников по ролям
    if request.apply_to_employees:
        employees = db.query(Employee).filter(
            Employee.role.notin_(SUPERUSER_ROLES)
        ).all()
        updated_count = 0
        for emp in employees:
            # Определяем новые права по роли из матрицы
            role_perms = set(request.roles.get(emp.role, []))
            # Добавляем права по должности
            if emp.position and emp.position in request.roles:
                role_perms |= set(request.roles[emp.position])
            # Добавляем права по совмещённой должности
            if emp.secondary_position and emp.secondary_position in request.roles:
                role_perms |= set(request.roles[emp.secondary_position])

            # Сохраняем не-матричные права (agents.*, cities.*, и др.)
            # которые не управляются через UI и не должны теряться при сохранении
            existing_perms = load_permissions(emp.id, db)
            preserved_perms = existing_perms & NON_MATRIX_PERMISSIONS
            merged_perms = role_perms | preserved_perms

            if merged_perms:
                set_employee_permissions(emp.id, sorted(merged_perms), current_user.id, db)
                updated_count += 1

        logger.info(f"Обновлены права {updated_count} сотрудников по новой матрице ролей")

    # Возвращаем актуальную матрицу
    matrix = load_role_matrix(db)
    return RoleMatrixResponse(roles=matrix)


@router.get("/permissions/{employee_id}", response_model=PermissionResponse)
async def get_permissions(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить права сотрудника"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    perms = get_employee_permissions(employee_id, db)
    is_superuser = employee.role in SUPERUSER_ROLES
    return PermissionResponse(employee_id=employee_id, permissions=perms, is_superuser=is_superuser)


@router.put("/permissions/{employee_id}", response_model=PermissionResponse)
async def update_permissions(
    employee_id: int,
    request: PermissionSetRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Установить права сотрудника (полная замена)"""
    # Только Руководитель / admin / director могут менять права
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    # Нельзя менять права superuser
    if employee.role in SUPERUSER_ROLES:
        raise HTTPException(status_code=400, detail="Нельзя менять права системного пользователя")

    # IDOR: Старший менеджер не может менять Руководителя (но мы уже ограничили до Руководителя)

    # Валидация имён прав
    invalid = [p for p in request.permissions if p not in PERMISSION_NAMES]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Неизвестные права: {', '.join(invalid)}")

    set_employee_permissions(employee_id, request.permissions, current_user.id, db)
    perms = get_employee_permissions(employee_id, db)
    return PermissionResponse(employee_id=employee_id, permissions=perms)


@router.post("/permissions/{employee_id}/reset-to-defaults", response_model=PermissionResponse)
async def reset_permissions_to_defaults(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Сбросить права до дефолтных по роли"""
    if current_user.role not in SUPERUSER_ROLES:
        raise HTTPException(status_code=403, detail="Недостаточно прав")

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="Сотрудник не найден")

    if employee.role in SUPERUSER_ROLES:
        raise HTTPException(status_code=400, detail="Нельзя сбросить права системного пользователя")

    reset_to_defaults(employee_id, db)
    perms = get_employee_permissions(employee_id, db)
    return PermissionResponse(employee_id=employee_id, permissions=perms)
