import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, Employee
from auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(tags=["heartbeat"])


# =========================
# HEARTBEAT (ONLINE STATUS)
# =========================

@router.post("/heartbeat")
async def send_heartbeat(
    employee_id: int = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Отправить heartbeat для поддержания онлайн-статуса.
    Возвращает список онлайн пользователей.
    """
    try:
        # Обновляем last_activity текущего пользователя
        current_user.last_activity = datetime.utcnow()
        current_user.is_online = True
        db.commit()

        # Определяем порог активности (5 минут)
        activity_threshold = datetime.utcnow() - timedelta(minutes=5)

        # Получаем список онлайн пользователей
        online_employees = db.query(Employee).filter(
            Employee.last_activity > activity_threshold,
            Employee.is_online == True,
            Employee.status == 'активный'
        ).all()

        online_users = [
            {
                'id': emp.id,
                'full_name': emp.full_name,
                'position': emp.position,
                'last_activity': emp.last_activity.isoformat() if emp.last_activity else None
            }
            for emp in online_employees
        ]

        return {
            'status': 'ok',
            'online_users': online_users,
            'online_count': len(online_users)
        }

    except Exception as e:
        logger.exception(f"Ошибка heartbeat: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
