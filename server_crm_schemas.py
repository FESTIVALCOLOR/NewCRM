# -*- coding: utf-8 -*-
"""
Pydantic схемы для CRM - для добавления в server/schemas.py
"""

# ДОБАВИТЬ В server/schemas.py:

# =========================
# CRM КАРТОЧКИ
# =========================

class CRMCardBase(BaseModel):
    contract_id: int
    column_name: str
    deadline: Optional[str] = None
    tags: Optional[str] = None
    is_approved: bool = False
    senior_manager_id: Optional[int] = None
    sdp_id: Optional[int] = None
    gap_id: Optional[int] = None
    manager_id: Optional[int] = None
    surveyor_id: Optional[int] = None
    approval_deadline: Optional[str] = None
    approval_stages: Optional[str] = None  # JSON строка
    project_data_link: Optional[str] = None
    tech_task_file: Optional[str] = None
    tech_task_date: Optional[str] = None
    survey_date: Optional[str] = None
    order_position: int = 0


class CRMCardCreate(CRMCardBase):
    pass


class CRMCardUpdate(BaseModel):
    """Схема для частичного обновления карточки"""
    column_name: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    is_approved: Optional[bool] = None
    senior_manager_id: Optional[int] = None
    sdp_id: Optional[int] = None
    gap_id: Optional[int] = None
    manager_id: Optional[int] = None
    surveyor_id: Optional[int] = None
    approval_deadline: Optional[str] = None
    approval_stages: Optional[str] = None
    project_data_link: Optional[str] = None
    tech_task_file: Optional[str] = None
    tech_task_date: Optional[str] = None
    survey_date: Optional[str] = None
    order_position: Optional[int] = None


class StageExecutorInfo(BaseModel):
    """Информация об исполнителе стадии для вложения в ответ"""
    id: int
    stage_name: str
    executor_id: int
    executor_name: str
    assigned_by: int
    assigned_date: datetime
    deadline: Optional[str] = None
    submitted_date: Optional[datetime] = None
    completed: bool
    completed_date: Optional[datetime] = None

    class Config:
        from_attributes = True


class CRMCardResponse(CRMCardBase):
    """Полная информация о карточке с joins"""
    id: int
    created_at: datetime
    updated_at: datetime

    # Дополнительные поля из contract
    contract_number: Optional[str] = None
    client_name: Optional[str] = None
    contract_amount: Optional[float] = None
    project_type: Optional[str] = None

    # Имена менеджеров
    senior_manager_name: Optional[str] = None
    sdp_name: Optional[str] = None
    gap_name: Optional[str] = None
    manager_name: Optional[str] = None
    surveyor_name: Optional[str] = None

    # Исполнители стадий
    stage_executors: List[StageExecutorInfo] = []

    class Config:
        from_attributes = True


class ColumnMoveRequest(BaseModel):
    """Запрос на перемещение карточки в другую колонку"""
    column_name: str


# =========================
# ИСПОЛНИТЕЛИ СТАДИЙ
# =========================

class StageExecutorCreate(BaseModel):
    stage_name: str
    executor_id: int
    deadline: Optional[str] = None


class StageExecutorUpdate(BaseModel):
    deadline: Optional[str] = None
    submitted_date: Optional[datetime] = None
    completed: Optional[bool] = None
    completed_date: Optional[datetime] = None


class StageExecutorResponse(BaseModel):
    id: int
    crm_card_id: int
    stage_name: str
    executor_id: int
    assigned_by: int
    assigned_date: datetime
    deadline: Optional[str] = None
    submitted_date: Optional[datetime] = None
    completed: bool
    completed_date: Optional[datetime] = None

    class Config:
        from_attributes = True
