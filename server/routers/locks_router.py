import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Employee, ConcurrentEdit, UserSession
from auth import get_current_user
from schemas import LockRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/locks", tags=["locks"])


# =========================
# CONCURRENT EDITING LOCKS
# =========================

@router.post("/")
async def create_lock(
    lock_data: LockRequest,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Создать блокировку записи для редактирования.
    Принимает JSON body: {entity_type, entity_id, employee_id (опционально)}.
    Возвращает 409 если запись уже заблокирована другим пользователем.
    """
    entity_type = lock_data.entity_type
    entity_id = lock_data.entity_id
    employee_id = lock_data.employee_id or current_user.id
    try:
        # Проверяем существующую блокировку
        existing_lock = db.query(ConcurrentEdit).filter(
            ConcurrentEdit.entity_type == entity_type,
            ConcurrentEdit.entity_id == entity_id
        ).first()

        if existing_lock:
            # Проверяем, не истекла ли блокировка (2 минуты)
            if existing_lock.expires_at and existing_lock.expires_at < datetime.utcnow():
                # Блокировка истекла, удаляем её
                db.delete(existing_lock)
                db.commit()
            elif existing_lock.employee_id != employee_id:
                # Запись заблокирована другим пользователем
                locked_by = db.query(Employee).filter(
                    Employee.id == existing_lock.employee_id
                ).first()

                locked_by_name = locked_by.full_name if locked_by else 'другим пользователем'

                raise HTTPException(
                    status_code=409,
                    detail={
                        'message': 'Запись заблокирована',
                        'locked_by': locked_by_name,
                        'locked_at': existing_lock.locked_at.isoformat()
                    }
                )
            else:
                # Обновляем время блокировки
                existing_lock.locked_at = datetime.utcnow()
                existing_lock.expires_at = datetime.utcnow() + timedelta(minutes=2)
                db.commit()
                return {'status': 'renewed', 'entity_type': entity_type, 'entity_id': entity_id}

        # Получаем реальную сессию текущего пользователя
        user_session = db.query(UserSession).filter(
            UserSession.employee_id == current_user.id
        ).order_by(UserSession.last_activity.desc()).first()

        if not user_session:
            # Создаём сессию если нет
            user_session = UserSession(
                employee_id=current_user.id,
                session_token="lock-session",
                ip_address="0.0.0.0",
                last_activity=datetime.utcnow(),
                is_active=True
            )
            db.add(user_session)
            db.flush()

        # Создаём новую блокировку
        new_lock = ConcurrentEdit(
            entity_type=entity_type,
            entity_id=entity_id,
            employee_id=employee_id,
            session_id=user_session.id,
            locked_at=datetime.utcnow(),
            expires_at=datetime.utcnow() + timedelta(minutes=2)
        )
        db.add(new_lock)
        db.commit()

        return {'status': 'created', 'entity_type': entity_type, 'entity_id': entity_id}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при создании блокировки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/{entity_type}/{entity_id}")
async def check_lock(
    entity_type: str,
    entity_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Проверить блокировку записи"""
    try:
        lock = db.query(ConcurrentEdit).filter(
            ConcurrentEdit.entity_type == entity_type,
            ConcurrentEdit.entity_id == entity_id
        ).first()

        if not lock:
            return {'is_locked': False, 'locked_by': None}

        # Проверяем, не истекла ли блокировка
        if lock.expires_at and lock.expires_at < datetime.utcnow():
            db.delete(lock)
            db.commit()
            return {'is_locked': False, 'locked_by': None}

        # Получаем имя пользователя, заблокировавшего запись
        locked_by = db.query(Employee).filter(
            Employee.id == lock.employee_id
        ).first()

        return {
            'is_locked': True,
            'locked_by': locked_by.full_name if locked_by else 'неизвестный пользователь',
            'locked_at': lock.locked_at.isoformat(),
            'expires_at': lock.expires_at.isoformat() if lock.expires_at else None,
            'is_own_lock': lock.employee_id == current_user.id
        }

    except Exception as e:
        logger.exception(f"Ошибка при проверке блокировки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# ВАЖНО: статический маршрут /user/{employee_id} ПЕРЕД динамическим /{entity_type}/{entity_id}
@router.delete("/user/{employee_id}")
async def release_user_locks(
    employee_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Снять все блокировки пользователя"""
    try:
        # Только сам пользователь или админ может снять блокировки
        if employee_id != current_user.id and current_user.position not in ['Руководитель студии', 'Старший менеджер проектов']:
            raise HTTPException(status_code=403, detail="Нет прав")

        locks = db.query(ConcurrentEdit).filter(
            ConcurrentEdit.employee_id == employee_id
        ).all()

        count = len(locks)
        for lock in locks:
            db.delete(lock)

        db.commit()

        return {'status': 'released', 'count': count}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при снятии блокировок пользователя: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/{entity_type}/{entity_id}")
async def release_lock(
    entity_type: str,
    entity_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Снять блокировку записи"""
    try:
        lock = db.query(ConcurrentEdit).filter(
            ConcurrentEdit.entity_type == entity_type,
            ConcurrentEdit.entity_id == entity_id
        ).first()

        if lock:
            # Только владелец или админ может снять блокировку
            if lock.employee_id == current_user.id or current_user.position in ['Руководитель студии', 'Старший менеджер проектов']:
                db.delete(lock)
                db.commit()
                return {'status': 'released'}
            else:
                raise HTTPException(status_code=403, detail="Нельзя снять чужую блокировку")

        return {'status': 'not_found'}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при снятии блокировки: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
