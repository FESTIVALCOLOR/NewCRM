"""
Granular Permissions — именованные права доступа в БД
Заменяет хардкод allowed_roles в endpoints
"""
import time
import logging
from typing import Optional, List, Dict, Set
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db, Employee, UserPermission, RoleDefaultPermission

logger = logging.getLogger(__name__)

# =========================
# ОПРЕДЕЛЕНИЯ ПРАВ (26 штук)
# =========================

PERMISSION_NAMES: Dict[str, str] = {
    # Сотрудники
    "employees.create": "Создание сотрудников",
    "employees.update": "Редактирование сотрудников",
    "employees.delete": "Удаление сотрудников",
    # Клиенты
    "clients.delete": "Удаление клиентов",
    # Договоры
    "contracts.delete": "Удаление договоров",
    # CRM
    "crm_cards.update": "Редактирование CRM карточек",
    "crm_cards.move": "Перемещение CRM карточек",
    "crm_cards.delete": "Удаление CRM карточек",
    "crm_cards.assign_executor": "Назначение исполнителей",
    "crm_cards.delete_executor": "Удаление исполнителей",
    "crm_cards.reset_stages": "Сброс стадий CRM",
    "crm_cards.reset_approval": "Сброс согласования",
    "crm_cards.complete_approval": "Завершение согласования",
    "crm_cards.reset_designer": "Сброс отметки дизайнера",
    "crm_cards.reset_draftsman": "Сброс отметки чертежника",
    # Надзор
    "supervision.update": "Редактирование карточек надзора",
    "supervision.move": "Перемещение карточек надзора",
    "supervision.pause_resume": "Приостановка/возобновление надзора",
    "supervision.reset_stages": "Сброс стадий надзора",
    "supervision.complete_stage": "Завершение стадии надзора",
    "supervision.delete_order": "Удаление заказа надзора",
    # Платежи
    "payments.create": "Создание платежей",
    "payments.update": "Редактирование платежей",
    "payments.delete": "Удаление платежей",
    # Зарплаты
    "salaries.create": "Создание зарплат",
    "salaries.update": "Редактирование зарплат",
    "salaries.delete": "Удаление зарплат",
    # Ставки
    "rates.create": "Создание/редактирование ставок",
    "rates.delete": "Удаление ставок",
    # Агенты
    "agents.create": "Создание агентов",
    "agents.update": "Редактирование агентов",
    # Мессенджер
    "messenger.create_chat": "Создание чатов",
    "messenger.delete_chat": "Удаление чатов",
    "messenger.view_chat": "Просмотр/открытие чатов",
}

# =========================
# ДЕФОЛТНЫЕ ПРАВА ПО РОЛЯМ
# =========================
# Воспроизводят текущее поведение хардкод-проверок

# Базовый набор: Руководитель + Старший менеджер
_BASE_MANAGER = {
    "clients.delete",
    "contracts.delete",
    "crm_cards.update",
    "crm_cards.move",
    "crm_cards.delete",
    "crm_cards.assign_executor",
    "crm_cards.delete_executor",
    "crm_cards.reset_stages",
    "crm_cards.reset_approval",
    "crm_cards.complete_approval",
    "supervision.update",
    "supervision.move",
    "supervision.pause_resume",
    "supervision.reset_stages",
    "supervision.complete_stage",
    "supervision.delete_order",
    "payments.create",
    "payments.update",
    "payments.delete",
    "salaries.create",
    "salaries.update",
    "rates.create",
    "rates.delete",
    "agents.create",
    "agents.update",
    "messenger.create_chat",
    "messenger.delete_chat",
    "messenger.view_chat",
}

DEFAULT_ROLE_PERMISSIONS: Dict[str, Set[str]] = {
    "Руководитель студии": _BASE_MANAGER | {
        "employees.create",
        "employees.update",
        "employees.delete",
        "crm_cards.reset_designer",
        "crm_cards.reset_draftsman",
        "salaries.delete",
    },
    "Старший менеджер проектов": _BASE_MANAGER | {
        "employees.update",
        "crm_cards.reset_designer",
        "crm_cards.reset_draftsman",
    },
    # Роли с ограниченным доступом к reset_designer/draftsman
    "СДП": {"crm_cards.reset_designer", "crm_cards.reset_draftsman", "messenger.view_chat"},
    "ГАП": {"crm_cards.reset_designer", "crm_cards.reset_draftsman", "messenger.view_chat"},
    "Менеджер": {"crm_cards.reset_designer", "crm_cards.reset_draftsman"},
    # ДАН: завершение стадии надзора + просмотр чатов
    "ДАН": {"supervision.complete_stage", "messenger.view_chat"},
}

# Системные роли с полным доступом (не настраиваются)
SUPERUSER_ROLES = {"admin", "director"}

# =========================
# КЭШ ПРАВ
# =========================

_CACHE_TTL = 300  # 5 минут
_permissions_cache: Dict[int, tuple] = {}  # {employee_id: (permissions_set, timestamp)}


def invalidate_cache(employee_id: Optional[int] = None):
    """Сброс кэша прав"""
    if employee_id is not None:
        _permissions_cache.pop(employee_id, None)
    else:
        _permissions_cache.clear()


def _get_cached(employee_id: int) -> Optional[Set[str]]:
    """Получить права из кэша если актуальны"""
    entry = _permissions_cache.get(employee_id)
    if entry and (time.time() - entry[1]) < _CACHE_TTL:
        return entry[0]
    return None


def _set_cached(employee_id: int, perms: Set[str]):
    """Сохранить права в кэш"""
    _permissions_cache[employee_id] = (perms, time.time())


# =========================
# ЗАГРУЗКА И ПРОВЕРКА ПРАВ
# =========================

def load_permissions(employee_id: int, db: Session) -> Set[str]:
    """
    Загрузить права сотрудника.
    Если в БД есть записи — берём из БД.
    Если записей нет — используем дефолтные по роли.
    """
    cached = _get_cached(employee_id)
    if cached is not None:
        return cached

    # Запрос из БД
    db_perms = db.query(UserPermission).filter(
        UserPermission.employee_id == employee_id
    ).all()

    if db_perms:
        # Есть записи в БД — используем их
        perms = {p.permission_name for p in db_perms}
    else:
        # Нет записей — дефолтные по роли
        employee = db.query(Employee).filter(Employee.id == employee_id).first()
        if not employee:
            perms = set()
        else:
            perms = _get_default_permissions(employee)

    _set_cached(employee_id, perms)
    return perms


def _get_default_permissions(employee: Employee) -> Set[str]:
    """Получить дефолтные права по роли и должности сотрудника"""
    perms = set()

    # По роли
    role_perms = DEFAULT_ROLE_PERMISSIONS.get(employee.role, set())
    perms |= role_perms

    # По основной должности (для reset_designer/draftsman)
    pos_perms = DEFAULT_ROLE_PERMISSIONS.get(employee.position, set())
    perms |= pos_perms

    # По совмещённой должности
    if employee.secondary_position:
        sec_perms = DEFAULT_ROLE_PERMISSIONS.get(employee.secondary_position, set())
        perms |= sec_perms

    return perms


def check_permission(employee: Employee, permission_name: str, db: Session) -> bool:
    """
    Проверить конкретное право у сотрудника.
    admin/director имеют полный доступ всегда.
    """
    if employee.role in SUPERUSER_ROLES:
        return True

    perms = load_permissions(employee.id, db)
    return permission_name in perms


# =========================
# FASTAPI DEPENDENCY
# =========================

def require_permission(permission_name: str):
    """
    FastAPI dependency factory.
    Использование: Depends(require_permission("crm_cards.update"))
    """
    from auth import get_current_user

    async def _check(
        current_user: Employee = Depends(get_current_user),
        db: Session = Depends(get_db)
    ):
        if not check_permission(current_user, permission_name, db):
            raise HTTPException(status_code=403, detail="Недостаточно прав")
        return current_user

    return _check


# =========================
# SEED: Заполнение дефолтных прав
# =========================

def seed_permissions(db: Session):
    """
    Заполнить/дополнить дефолтные права для сотрудников.
    Вызывается при старте сервера.
    Использует advisory lock для предотвращения deadlock между workers.
    """
    from sqlalchemy import text

    try:
        # PostgreSQL advisory lock — только один worker выполняет seed
        db.execute(text("SELECT pg_advisory_lock(42)"))

        employees = db.query(Employee).all()
        total_added = 0

        for emp in employees:
            if emp.role in SUPERUSER_ROLES and emp.role not in DEFAULT_ROLE_PERMISSIONS:
                continue

            default_perms = _get_default_permissions(emp)
            if not default_perms:
                continue

            # Получаем существующие права
            existing = {
                r[0] for r in db.execute(
                    text("SELECT permission_name FROM user_permissions WHERE employee_id = :eid"),
                    {"eid": emp.id}
                ).fetchall()
            }

            missing = default_perms - existing
            for perm_name in missing:
                db.execute(
                    text("""
                        INSERT INTO user_permissions (employee_id, permission_name)
                        VALUES (:emp_id, :perm)
                        ON CONFLICT (employee_id, permission_name) DO NOTHING
                    """),
                    {"emp_id": emp.id, "perm": perm_name}
                )
                total_added += 1

        db.commit()
        if total_added > 0:
            logger.info(f"Seeded {total_added} missing permissions")
    except Exception as e:
        db.rollback()
        logger.warning(f"seed_permissions error (non-fatal): {e}")
    finally:
        try:
            db.execute(text("SELECT pg_advisory_unlock(42)"))
            db.commit()
        except Exception:
            pass


# =========================
# УПРАВЛЕНИЕ ПРАВАМИ
# =========================

def get_employee_permissions(employee_id: int, db: Session) -> List[str]:
    """Получить список прав сотрудника"""
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        return []

    if employee.role in SUPERUSER_ROLES:
        return sorted(PERMISSION_NAMES.keys())

    perms = load_permissions(employee_id, db)
    return sorted(perms)


def set_employee_permissions(employee_id: int, permissions: List[str], granted_by: int, db: Session):
    """Установить права сотрудника (полная замена)"""
    # Удаляем старые
    db.query(UserPermission).filter(
        UserPermission.employee_id == employee_id
    ).delete(synchronize_session=False)

    # Создаём новые
    for perm_name in permissions:
        if perm_name in PERMISSION_NAMES:
            db.add(UserPermission(
                employee_id=employee_id,
                permission_name=perm_name,
                granted_by=granted_by,
            ))

    db.commit()
    invalidate_cache(employee_id)


def reset_to_defaults(employee_id: int, db: Session):
    """Сбросить права сотрудника до дефолтных по роли"""
    # Удаляем все записи — load_permissions вернёт дефолтные
    db.query(UserPermission).filter(
        UserPermission.employee_id == employee_id
    ).delete(synchronize_session=False)
    db.commit()
    invalidate_cache(employee_id)


# =========================
# МАТРИЦА РОЛЕЙ
# =========================

def load_role_matrix(db: Session) -> Dict[str, List[str]]:
    """
    Загрузить матрицу прав по ролям из БД.
    Если таблица пуста — возвращает DEFAULT_ROLE_PERMISSIONS.
    """
    from datetime import datetime
    rows = db.query(RoleDefaultPermission).all()
    if not rows:
        # Таблица пуста — возвращаем хардкод-дефолты
        return {
            role: sorted(perms)
            for role, perms in DEFAULT_ROLE_PERMISSIONS.items()
        }

    # Группируем по ролям
    matrix: Dict[str, List[str]] = {}
    for row in rows:
        matrix.setdefault(row.role, []).append(row.permission_name)

    # Сортируем права внутри каждой роли
    for role in matrix:
        matrix[role] = sorted(matrix[role])

    return matrix


def save_role_matrix(matrix: Dict[str, List[str]], updated_by: int, db: Session):
    """
    Сохранить матрицу прав по ролям в БД.
    Полная замена: удаляет старые записи, создаёт новые.
    """
    from datetime import datetime

    # Удаляем все старые записи
    db.query(RoleDefaultPermission).delete(synchronize_session=False)

    # Создаём новые записи
    now = datetime.utcnow()
    for role, permissions in matrix.items():
        for perm_name in permissions:
            if perm_name in PERMISSION_NAMES:
                db.add(RoleDefaultPermission(
                    role=role,
                    permission_name=perm_name,
                    updated_at=now,
                    updated_by=updated_by,
                ))

    db.commit()
    logger.info(f"Матрица ролей обновлена пользователем {updated_by}: {len(matrix)} ролей")
