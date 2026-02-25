import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from database import get_db, City, Contract, Employee
from auth import get_current_user
from permissions import require_permission


class CityCreate(BaseModel):
    name: str


logger = logging.getLogger(__name__)
router = APIRouter(tags=["cities"])


@router.get("/")
async def get_all_cities(
    include_deleted: bool = False,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить список всех городов"""
    query = db.query(City).order_by(City.name)
    if not include_deleted:
        query = query.filter(City.status == 'активный')
    cities = query.all()
    return [{"id": c.id, "name": c.name, "status": c.status} for c in cities]


@router.post("/")
async def add_city(
    data: CityCreate,
    current_user: Employee = Depends(require_permission("cities.create")),
    db: Session = Depends(get_db)
):
    """Добавить новый город"""
    try:
        # Проверить удалённый город — восстановить
        existing = db.query(City).filter(City.name == data.name).first()
        if existing:
            if existing.status == 'удалён':
                existing.status = 'активный'
                db.commit()
                return {"status": "success", "id": existing.id, "name": existing.name}
            raise HTTPException(status_code=400, detail="Город с таким названием уже существует")

        city = City(name=data.name)
        db.add(city)
        db.commit()
        db.refresh(city)
        return {"status": "success", "id": city.id, "name": data.name}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при добавлении города: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.delete("/{city_id}")
async def delete_city(
    city_id: int,
    current_user: Employee = Depends(require_permission("cities.delete")),
    db: Session = Depends(get_db)
):
    """Мягкое удаление города"""
    try:
        city = db.query(City).filter(City.id == city_id).first()
        if not city:
            raise HTTPException(status_code=404, detail="Город не найден")

        # Проверить активные договоры
        active_contracts = db.query(Contract).filter(
            Contract.city == city.name,
            Contract.status.notin_(['СДАН', 'РАСТОРГНУТ'])
        ).count()
        if active_contracts > 0:
            raise HTTPException(
                status_code=409,
                detail=f"Невозможно удалить город: {active_contracts} активных договоров"
            )

        city.status = 'удалён'
        db.commit()
        return {"status": "success", "message": f"Город '{city.name}' удалён"}
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.exception(f"Ошибка при удалении города: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
