"""VPN управление — проксирует команды к vpn-control-api на хосте."""

import logging

from auth import get_current_user
from constants import ADMIN_POSITIONS
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
import requests as http_requests
from sqlalchemy.orm import Session

from database import Employee, get_db

router = APIRouter()
logger = logging.getLogger(__name__)

VPN_CONTROL_URL = "http://host.docker.internal:8081"
TIMEOUT = 60


def _require_admin(current_user: Employee = Depends(get_current_user)):
    if current_user.position not in ADMIN_POSITIONS and current_user.role not in ("admin", "director"):
        raise HTTPException(status_code=403, detail="Только администратор")
    return current_user


def _call(method: str, path: str, **kwargs):
    try:
        resp = getattr(http_requests, method)(f"{VPN_CONTROL_URL}{path}", timeout=TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp.json()
    except http_requests.exceptions.ConnectionError:
        raise HTTPException(status_code=503, detail="VPN Control API недоступен (сервис vpn-control-api не запущен)")
    except http_requests.exceptions.Timeout:
        raise HTTPException(status_code=504, detail="VPN Control API не ответил вовремя")
    except Exception as e:
        logger.error(f"[VPN] Ошибка запроса к control API: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vpn/status")
async def vpn_status(current_user: Employee = Depends(_require_admin), db: Session = Depends(get_db)):
    """Статус VPN сервисов и текущий пароль."""
    return _call("get", "/status")


@router.post("/vpn/auto-update")
async def vpn_auto_update(current_user: Employee = Depends(_require_admin), db: Session = Depends(get_db)):
    """Автоматически получить новый пароль с vpnbook.com и перезапустить сервисы."""
    logger.info(f"[VPN] auto-update запущен пользователем {current_user.full_name}")
    return _call("post", "/auto-update")


class SetPasswordRequest(BaseModel):
    password: str


@router.post("/vpn/set-password")
async def vpn_set_password(
    body: SetPasswordRequest,
    current_user: Employee = Depends(_require_admin),
    db: Session = Depends(get_db),
):
    """Установить пароль VPNBook вручную и перезапустить сервисы."""
    if not body.password.strip():
        raise HTTPException(status_code=400, detail="Пароль не может быть пустым")
    logger.info(f"[VPN] set-password запущен пользователем {current_user.full_name}")
    return _call("post", "/set-password", json={"password": body.password.strip()})


@router.post("/vpn/restart")
async def vpn_restart(current_user: Employee = Depends(_require_admin), db: Session = Depends(get_db)):
    """Перезапустить VPN сервисы без смены пароля."""
    logger.info(f"[VPN] restart запущен пользователем {current_user.full_name}")
    return _call("post", "/restart")
