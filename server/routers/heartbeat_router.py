from datetime import datetime, timedelta
import logging
import shutil

from auth import get_current_user
from constants import ADMIN_POSITIONS, SUPERUSER_ROLES
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import Employee, get_db

logger = logging.getLogger(__name__)

router = APIRouter(tags=["heartbeat"])


# =========================
# HEARTBEAT (ONLINE STATUS)
# =========================


@router.post("/heartbeat")
async def send_heartbeat(employee_id: int = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Отправить heartbeat для поддержания онлайн-статуса.
    Возвращает список онлайн пользователей.
    """
    try:
        # Обновляем last_activity и last_login текущего пользователя
        current_user.last_activity = datetime.utcnow()
        current_user.last_login = datetime.utcnow()
        current_user.is_online = True
        db.commit()

        # Определяем порог активности (2 минуты — heartbeat каждые 60с, 2 пропуска = offline)
        activity_threshold = datetime.utcnow() - timedelta(minutes=2)

        # Получаем список онлайн пользователей
        online_employees = db.query(Employee).filter(Employee.last_activity > activity_threshold, Employee.is_online == True, Employee.status == "активный").all()

        online_users = [{"id": emp.id, "full_name": emp.full_name, "position": emp.position, "last_activity": emp.last_activity.isoformat() if emp.last_activity else None} for emp in online_employees]

        return {"status": "ok", "online_users": online_users, "online_count": len(online_users)}

    except Exception as e:
        logger.exception(f"Ошибка heartbeat: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


# =========================
# DISK / RAM STATUS (ADMIN)
# =========================


@router.get("/admin/disk-status")
async def get_disk_status(current_user: Employee = Depends(get_current_user)):
    """Состояние диска и RAM сервера — только для администраторов."""
    is_admin = current_user.position in ADMIN_POSITIONS or current_user.role in SUPERUSER_ROLES
    if not is_admin:
        raise HTTPException(status_code=403, detail="Нет прав")

    # Диск
    u = shutil.disk_usage("/")
    disk_percent = round(u.used / u.total * 100, 1)

    # RAM из /proc/meminfo (работает внутри Docker на Linux)
    ram_total_bytes = ram_used_bytes = 0
    try:
        with open("/proc/meminfo") as f:
            lines = {}
            for line in f:
                if ":" in line:
                    k, v = line.split(":", 1)
                    lines[k.strip()] = v.strip()
        ram_total_bytes = int(lines["MemTotal"].split()[0]) * 1024
        ram_avail_bytes = int(lines["MemAvailable"].split()[0]) * 1024
        ram_used_bytes = ram_total_bytes - ram_avail_bytes
    except Exception:
        pass

    ram_percent = round(ram_used_bytes / ram_total_bytes * 100, 1) if ram_total_bytes else 0

    return {
        "disk_percent": disk_percent,
        "disk_used_gb": round(u.used / 1024**3, 1),
        "disk_total_gb": round(u.total / 1024**3, 1),
        "disk_free_gb": round(u.free / 1024**3, 1),
        "disk_warning": disk_percent >= 90,
        "disk_critical": disk_percent >= 95,
        "ram_percent": ram_percent,
        "ram_used_gb": round(ram_used_bytes / 1024**3, 1),
        "ram_total_gb": round(ram_total_bytes / 1024**3, 1),
    }
