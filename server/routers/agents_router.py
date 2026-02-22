import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db, Agent, Employee
from auth import get_current_user
from permissions import require_permission


class AgentCreate(BaseModel):
    name: str
    color: str = "#FFFFFF"


class AgentColorUpdate(BaseModel):
    color: str


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
    agents = db.query(Agent).order_by(Agent.name).all()
    return [{
        "id": a.id,
        "name": a.name,
        "full_name": a.name,
        "color": a.color or "#FFFFFF",
        "status": a.status or "активный"
    } for a in agents]


@router.post("/")
async def add_agent(
    data: AgentCreate,
    current_user: Employee = Depends(require_permission("agents.create")),
    db: Session = Depends(get_db)
):
    """Добавить нового агента"""
    try:
        existing = db.query(Agent).filter(Agent.name == data.name).first()
        if existing:
            raise HTTPException(status_code=400, detail="Агент с таким именем уже существует")

        agent = Agent(name=data.name, color=data.color)
        db.add(agent)
        db.commit()
        db.refresh(agent)

        return {"status": "success", "id": agent.id, "name": data.name, "color": data.color}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при добавлении агента: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.patch("/{name}/color")
async def update_agent_color(
    name: str,
    data: AgentColorUpdate,
    current_user: Employee = Depends(require_permission("agents.update")),
    db: Session = Depends(get_db)
):
    """Обновить цвет агента"""
    try:
        agent = db.query(Agent).filter(Agent.name == name).first()

        if not agent:
            raise HTTPException(status_code=404, detail="Агент не найден")

        agent.color = data.color
        db.commit()

        return {"status": "success", "name": name, "color": data.color}

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при обновлении цвета агента: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
