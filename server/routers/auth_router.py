"""
Роутер аутентификации — auth endpoints:
  POST /login   — вход в систему
  POST /refresh — обновление access_token
  POST /logout  — выход из системы
  GET  /me      — информация о текущем пользователе

Подключается в main.py через:
    app.include_router(auth_router, prefix="/api/auth")
"""
import logging
from collections import defaultdict
from datetime import datetime, timedelta

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    verify_password,
    verify_refresh_token,
)
from config import get_settings
from rate_limit import limiter
from database import ActivityLog, Employee, UserSession, get_db
from schemas import EmployeeResponse, LoginResponse, RefreshTokenResponse, MessageResponse

logger = logging.getLogger(__name__)

router = APIRouter(tags=["auth"])

# ---------------------------------------------------------------------------
# Brute-force защита логина: in-memory счётчик + персистентная проверка в БД
# ---------------------------------------------------------------------------
_login_attempts: dict = defaultdict(list)
_LOGIN_MAX_ATTEMPTS: int = 5
_LOGIN_BLOCK_MINUTES: int = 15


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Вход в систему — возвращает access_token и refresh_token"""
    # Получаем реальный IP клиента (за Nginx/Docker прокси)
    client_ip = (
        request.headers.get("X-Real-IP")
        or request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        or (request.client.host if request.client else "unknown")
    )
    now = datetime.utcnow()
    cutoff = now - timedelta(minutes=_LOGIN_BLOCK_MINUTES)

    # In-memory счётчик (быстрый)
    _login_attempts[client_ip] = [
        t for t in _login_attempts[client_ip] if t > cutoff
    ]

    # Дополнительно проверяем в БД (персистентно, переживает рестарт)
    # Фильтруем по конкретному IP, а не по всем попыткам
    db_failed_count = (
        db.query(ActivityLog)
        .filter(
            ActivityLog.action_type == "login_failed",
            ActivityLog.entity_type == "auth",
            ActivityLog.action_date > cutoff,
            ActivityLog.ip_address == client_ip,
        )
        .count()
    )

    total_attempts = max(len(_login_attempts[client_ip]), db_failed_count)
    if total_attempts >= _LOGIN_MAX_ATTEMPTS:
        logger.warning(
            f"Brute-force заблокирован: IP={client_ip}, попыток={total_attempts}"
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Слишком много попыток входа. Повторите через {_LOGIN_BLOCK_MINUTES} минут",
        )

    # Поиск сотрудника
    employee = db.query(Employee).filter(Employee.login == form_data.username).first()
    if not employee:
        _login_attempts[client_ip].append(now)
        failed_log = ActivityLog(
            employee_id=0,
            action_type="login_failed",
            entity_type="auth",
            entity_id=0,
            ip_address=client_ip,
        )
        db.add(failed_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(form_data.password, employee.password_hash):
        _login_attempts[client_ip].append(now)
        failed_log = ActivityLog(
            employee_id=employee.id,
            action_type="login_failed",
            entity_type="auth",
            entity_id=0,
            ip_address=client_ip,
        )
        db.add(failed_log)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный логин или пароль",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверка: уволенный / неактивный сотрудник не может войти
    if employee.status != "активный":
        _login_attempts[client_ip].append(now)
        failed_log = ActivityLog(
            employee_id=employee.id,
            action_type="login_denied_inactive",
            entity_type="auth",
            entity_id=0,
        )
        db.add(failed_log)
        db.commit()
        status_label = employee.status or "неизвестен"
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Вход запрещён. Статус сотрудника: {status_label}",
        )

    # Успешный вход — очищаем счётчик
    _login_attempts.pop(client_ip, None)

    # Лимит одновременных сессий: деактивируем самые старые
    settings = get_settings()
    max_sessions = settings.max_sessions_per_user
    active_sessions = (
        db.query(UserSession)
        .filter(
            UserSession.employee_id == employee.id,
            UserSession.is_active == True,
        )
        .order_by(UserSession.login_time.asc())
        .all()
    )
    if len(active_sessions) >= max_sessions:
        sessions_to_close = active_sessions[: len(active_sessions) - max_sessions + 1]
        for old_session in sessions_to_close:
            old_session.is_active = False
            old_session.logout_time = datetime.utcnow()
        logger.info(
            f"Лимит сессий: закрыто {len(sessions_to_close)} старых "
            f"сессий для employee_id={employee.id} (макс={max_sessions})"
        )

    # Создание токенов
    access_token = create_access_token(data={"sub": str(employee.id)})
    refresh_token = create_refresh_token(data={"sub": str(employee.id)})

    # Обновление статуса сотрудника
    employee.last_login = datetime.utcnow()
    employee.is_online = True
    employee.current_session_token = access_token

    # Создание сессии с refresh_token
    session = UserSession(
        employee_id=employee.id,
        session_token=access_token,
        refresh_token=refresh_token,
        login_time=datetime.utcnow(),
    )
    db.add(session)

    # Лог активности
    log = ActivityLog(
        employee_id=employee.id,
        session_id=session.id,
        action_type="login",
        entity_type="auth",
        entity_id=employee.id,
    )
    db.add(log)

    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "employee_id": employee.id,
        "full_name": employee.full_name,
        "role": employee.role or "",
        "position": employee.position or "",
        "secondary_position": employee.secondary_position or "",
        "department": employee.department or "",
    }


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------

@router.post("/refresh", response_model=RefreshTokenResponse)
@limiter.limit("10/minute")
async def refresh_token(
    request: Request,
    refresh_token: str = Body(..., embed=True),
    db: Session = Depends(get_db),
):
    """Обновление access_token с помощью refresh_token (в теле запроса)"""
    # Проверяем refresh_token
    payload = verify_refresh_token(refresh_token)
    employee_id = payload.get("sub")

    if not employee_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный refresh токен",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Проверяем, что сессия с этим refresh_token существует и активна
    session = (
        db.query(UserSession)
        .filter(
            UserSession.refresh_token == refresh_token,
            UserSession.is_active == True,
        )
        .first()
    )

    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Сессия не найдена или истекла",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Получаем сотрудника
    employee = db.query(Employee).filter(Employee.id == int(employee_id)).first()
    if not employee:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Пользователь не найден",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Создаём новый access_token
    new_access_token = create_access_token(data={"sub": str(employee.id)})

    # Обновляем сессию
    session.session_token = new_access_token
    employee.current_session_token = new_access_token
    employee.last_activity = datetime.utcnow()

    db.commit()

    return {
        "access_token": new_access_token,
        "token_type": "bearer",
        "employee_id": employee.id,
        "full_name": employee.full_name,
    }


# ---------------------------------------------------------------------------
# POST /logout
# ---------------------------------------------------------------------------

@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Выход из системы"""
    current_user.is_online = False
    current_user.current_session_token = None

    # Закрываем активную сессию
    session = (
        db.query(UserSession)
        .filter(
            UserSession.employee_id == current_user.id,
            UserSession.is_active == True,
        )
        .first()
    )
    if session:
        session.is_active = False
        session.logout_time = datetime.utcnow()

    # Лог активности
    log = ActivityLog(
        employee_id=current_user.id,
        action_type="logout",
        entity_type="auth",
        entity_id=current_user.id,
    )
    db.add(log)

    db.commit()

    return {"message": "Успешный выход"}


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------

@router.get("/me", response_model=EmployeeResponse)
async def get_me(current_user: Employee = Depends(get_current_user)):
    """Получить информацию о текущем пользователе"""
    return current_user
