"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime


# =========================
# АУТЕНТИФИКАЦИЯ
# =========================

class LoginRequest(BaseModel):
    login: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    employee_id: int
    full_name: str
    role: str


# =========================
# СОТРУДНИКИ
# =========================

class EmployeeBase(BaseModel):
    full_name: str
    phone: str
    email: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[str] = None
    position: str
    secondary_position: Optional[str] = None
    department: str
    role: Optional[str] = None
    status: str = "активный"


class EmployeeCreate(EmployeeBase):
    login: str
    password: str


class EmployeeUpdate(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[str] = None
    position: Optional[str] = None
    secondary_position: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None


class EmployeeResponse(EmployeeBase):
    id: int
    login: str
    is_online: bool
    last_login: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# КЛИЕНТЫ
# =========================

class ClientBase(BaseModel):
    client_type: str
    full_name: Optional[str] = None
    phone: str
    email: Optional[str] = None
    passport_series: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issued_by: Optional[str] = None
    passport_issued_date: Optional[str] = None
    registration_address: Optional[str] = None
    organization_type: Optional[str] = None
    organization_name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    account_details: Optional[str] = None
    responsible_person: Optional[str] = None


class ClientCreate(ClientBase):
    pass


class ClientUpdate(BaseModel):
    client_type: Optional[str] = None
    full_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    passport_series: Optional[str] = None
    passport_number: Optional[str] = None
    passport_issued_by: Optional[str] = None
    passport_issued_date: Optional[str] = None
    registration_address: Optional[str] = None
    organization_type: Optional[str] = None
    organization_name: Optional[str] = None
    inn: Optional[str] = None
    ogrn: Optional[str] = None
    account_details: Optional[str] = None
    responsible_person: Optional[str] = None


class ClientResponse(ClientBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# ДОГОВОРЫ
# =========================

class ContractBase(BaseModel):
    client_id: int
    project_type: str
    agent_type: Optional[str] = None
    city: Optional[str] = None
    contract_number: str
    contract_date: Optional[str] = None
    address: Optional[str] = None
    area: Optional[float] = None
    total_amount: Optional[float] = None
    advance_payment: Optional[float] = None
    additional_payment: Optional[float] = None
    third_payment: Optional[float] = None
    contract_period: Optional[int] = None
    comments: Optional[str] = None
    contract_file_link: Optional[str] = None
    tech_task_link: Optional[str] = None
    status: str = "Новый заказ"
    status_changed_date: Optional[str] = None
    termination_reason: Optional[str] = None
    yandex_folder_path: Optional[str] = None


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    client_id: Optional[int] = None
    project_type: Optional[str] = None
    agent_type: Optional[str] = None
    city: Optional[str] = None
    contract_number: Optional[str] = None
    contract_date: Optional[str] = None
    address: Optional[str] = None
    area: Optional[float] = None
    total_amount: Optional[float] = None
    advance_payment: Optional[float] = None
    additional_payment: Optional[float] = None
    third_payment: Optional[float] = None
    contract_period: Optional[int] = None
    comments: Optional[str] = None
    contract_file_link: Optional[str] = None
    tech_task_link: Optional[str] = None
    status: Optional[str] = None
    status_changed_date: Optional[str] = None
    termination_reason: Optional[str] = None
    yandex_folder_path: Optional[str] = None


class ContractResponse(ContractBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# УВЕДОМЛЕНИЯ
# =========================

class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# СИНХРОНИЗАЦИЯ
# =========================

class SyncRequest(BaseModel):
    """Запрос на получение обновлений"""
    last_sync_timestamp: datetime
    entity_types: List[str]  # ['clients', 'contracts', 'employees']


class SyncResponse(BaseModel):
    """Ответ с обновлениями"""
    timestamp: datetime
    clients: List[ClientResponse] = []
    contracts: List[ContractResponse] = []
    employees: List[EmployeeResponse] = []
    notifications: List[NotificationResponse] = []
