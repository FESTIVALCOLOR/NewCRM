"""
JWT аутентификация
Создание и проверка токенов
"""
from datetime import datetime, timedelta
from typing import Optional
import secrets
from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from config import get_settings
from database import get_db, Employee

settings = get_settings()

# OAuth2 схема
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверка пароля (bcrypt напрямую, без passlib)"""
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8")
    )


def get_password_hash(password: str) -> str:
    """Хэширование пароля (bcrypt напрямую, без passlib)"""
    return bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt(rounds=12)
    ).decode("utf-8")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT access токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)

    to_encode.update({
        "exp": expire,
        "type": "access",
        "jti": secrets.token_hex(16),
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Создание JWT refresh токена"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.refresh_token_expire_days)

    # Добавляем уникальный идентификатор для возможности отзыва токена
    to_encode.update({
        "exp": expire,
        "type": "refresh",
        "jti": secrets.token_hex(16)  # Уникальный ID токена
    })
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Декодирование JWT токена"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


def verify_refresh_token(token: str) -> dict:
    """Проверка refresh токена"""
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Неверный тип токена",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный или истекший refresh токен",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> Employee:
    """Получить текущего пользователя из токена"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Не удалось проверить учетные данные",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_token(token)
    employee_id: int = payload.get("sub")
    if employee_id is None:
        raise credentials_exception

    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if employee is None:
        raise credentials_exception

    # Обновляем last_activity
    employee.last_activity = datetime.utcnow()
    db.commit()

    return employee


def check_permission(employee: Employee, permission_name: str, db: Session) -> bool:
    """Проверка прав доступа (делегирует в permissions модуль)"""
    from permissions import check_permission as _check
    return _check(employee, permission_name, db)
