import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_

from database import get_db, Employee
from auth import get_current_user
from permissions import require_permission

logger = logging.getLogger(__name__)

router = APIRouter(tags=["agents"])


# =========================
# AGENTS ENDPOINTS
# =========================

@router.get("/")
async def get_all_agents(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех агентов"""
    agents = db.query(Employee).filter(
        or_(
            Employee.position == 'Агент',
            Employee.secondary_position == 'Агент'
        )
    ).all()
    return [{
        "id": a.id,
        "name": a.full_name,
        "full_name": a.full_name,
        "color": a.agent_color or "#FFFFFF",
        "status": a.status
    } for a in agents]


@router.post("/")
async def add_agent(
    name: str,
    color: str = "#FFFFFF",
    current_user: Employee = Depends(require_permission("agents.create")),
    db: Session = Depends(get_db)
):
    """Добавить нового агента"""
    try:
        # Проверяем, не существует ли уже агент с таким именем
        existing = db.query(Employee).filter(
            Employee.full_name == name,
            Employee.position == 'Агент'
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="Агент с таким именем уже существует")

        # Создаём агента как сотрудника с обязательными полями
        agent = Employee(
            full_name=name,
            login=f"agent_{name.lower().replace(' ', '_')}",
            position='Агент',
            department='Агенты',
            phone='',
            password_hash='',
            agent_color=color,
            status='активный'
        )
        db.add(agent)
        db.commit()
        db.refresh(agent)

        return {"status": "success", "id": agent.id, "name": name, "color": color}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при добавлении агента: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/{name}/color")
async def update_agent_color(
    name: str,
    color: str,
    current_user: Employee = Depends(require_permission("agents.update")),
    db: Session = Depends(get_db)
):
    """Обновить цвет агента"""
    try:
        agent = db.query(Employee).filter(
            Employee.full_name == name,
            or_(Employee.position == 'Агент', Employee.secondary_position == 'Агент')
        ).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Агент не найден")

        agent.agent_color = color
        db.commit()

        return {"status": "success", "name": name, "color": color}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении цвета агента: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
