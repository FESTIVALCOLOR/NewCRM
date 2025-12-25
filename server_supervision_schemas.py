# -*- coding: utf-8 -*-
"""
Pydantic схемы для CRM Supervision - для добавления в server/schemas.py
"""

# ДОБАВИТЬ В server/schemas.py после CRM схем:

# =========================
# CRM SUPERVISION (Авторский надзор)
# =========================

class SupervisionCardBase(BaseModel):
    contract_id: int
    column_name: str = 'Новый заказ'
    deadline: Optional[str] = None
    tags: Optional[str] = None
    senior_manager_id: Optional[int] = None
    dan_id: Optional[int] = None
    dan_completed: bool = False
    is_paused: bool = False
    pause_reason: Optional[str] = None
    paused_at: Optional[datetime] = None


class SupervisionCardCreate(SupervisionCardBase):
    pass


class SupervisionCardUpdate(BaseModel):
    """Схема для частичного обновления карточки надзора"""
    column_name: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    senior_manager_id: Optional[int] = None
    dan_id: Optional[int] = None
    dan_completed: Optional[bool] = None
    is_paused: Optional[bool] = None
    pause_reason: Optional[str] = None
    paused_at: Optional[datetime] = None


class SupervisionCardResponse(SupervisionCardBase):
    """Полная информация о карточке надзора"""
    id: int
    created_at: datetime
    updated_at: datetime

    # Дополнительные поля из contract
    contract_number: Optional[str] = None
    address: Optional[str] = None
    area: Optional[float] = None
    city: Optional[str] = None
    agent_type: Optional[str] = None
    contract_status: Optional[str] = None

    # Имена менеджеров
    senior_manager_name: Optional[str] = None
    dan_name: Optional[str] = None

    class Config:
        from_attributes = True


class SupervisionColumnMoveRequest(BaseModel):
    """Запрос на перемещение карточки надзора"""
    column_name: str


class SupervisionPauseRequest(BaseModel):
    """Запрос на приостановку карточки надзора"""
    pause_reason: str
