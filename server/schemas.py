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


# =========================
# CRM КАРТОЧКИ
# =========================

class CRMCardBase(BaseModel):
    contract_id: int
    column_name: str = "Новый заказ"
    deadline: Optional[str] = None
    tags: Optional[str] = None
    is_approved: bool = False
    approval_deadline: Optional[str] = None
    approval_stages: Optional[str] = None
    project_data_link: Optional[str] = None
    tech_task_file: Optional[str] = None
    tech_task_date: Optional[str] = None
    survey_date: Optional[str] = None
    senior_manager_id: Optional[int] = None
    sdp_id: Optional[int] = None
    gap_id: Optional[int] = None
    manager_id: Optional[int] = None
    surveyor_id: Optional[int] = None
    order_position: int = 0


class CRMCardCreate(CRMCardBase):
    pass


class CRMCardUpdate(BaseModel):
    column_name: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    is_approved: Optional[bool] = None
    approval_deadline: Optional[str] = None
    approval_stages: Optional[str] = None
    project_data_link: Optional[str] = None
    tech_task_file: Optional[str] = None
    tech_task_date: Optional[str] = None
    survey_date: Optional[str] = None
    senior_manager_id: Optional[int] = None
    sdp_id: Optional[int] = None
    gap_id: Optional[int] = None
    manager_id: Optional[int] = None
    surveyor_id: Optional[int] = None
    order_position: Optional[int] = None


class CRMCardResponse(CRMCardBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ColumnMoveRequest(BaseModel):
    column_name: str


class StageExecutorCreate(BaseModel):
    stage_name: str
    executor_id: int
    deadline: Optional[str] = None


class StageExecutorUpdate(BaseModel):
    completed: Optional[bool] = None
    completed_date: Optional[datetime] = None
    submitted_date: Optional[datetime] = None


class StageExecutorResponse(BaseModel):
    id: int
    crm_card_id: int
    stage_name: str
    executor_id: int
    assigned_date: Optional[datetime] = None
    assigned_by: int
    deadline: Optional[str] = None
    submitted_date: Optional[datetime] = None
    completed: bool
    completed_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# =========================
# SUPERVISION (Авторский надзор)
# =========================

class SupervisionCardBase(BaseModel):
    contract_id: int
    column_name: str = "Новый заказ"
    deadline: Optional[str] = None
    tags: Optional[str] = None
    senior_manager_id: Optional[int] = None
    dan_id: Optional[int] = None
    dan_completed: bool = False


class SupervisionCardCreate(SupervisionCardBase):
    pass


class SupervisionCardUpdate(BaseModel):
    column_name: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    senior_manager_id: Optional[int] = None
    dan_id: Optional[int] = None
    dan_completed: Optional[bool] = None


class SupervisionCardResponse(SupervisionCardBase):
    id: int
    is_paused: bool
    pause_reason: Optional[str] = None
    paused_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SupervisionColumnMoveRequest(BaseModel):
    column_name: str


class SupervisionPauseRequest(BaseModel):
    pause_reason: str


class SupervisionHistoryResponse(BaseModel):
    id: int
    supervision_card_id: int
    entry_type: str
    message: str
    created_by: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# ПЛАТЕЖИ
# =========================

class PaymentBase(BaseModel):
    contract_id: int
    crm_card_id: Optional[int] = None
    supervision_card_id: Optional[int] = None
    employee_id: int
    role: str
    stage_name: Optional[str] = None
    calculated_amount: float
    manual_amount: Optional[float] = None
    final_amount: float
    is_manual: bool = False
    payment_type: Optional[str] = None
    report_month: Optional[str] = None
    payment_status: Optional[str] = None


class PaymentCreate(PaymentBase):
    pass


class PaymentUpdate(BaseModel):
    manual_amount: Optional[float] = None
    final_amount: Optional[float] = None
    is_manual: Optional[bool] = None
    payment_type: Optional[str] = None
    report_month: Optional[str] = None
    payment_status: Optional[str] = None
    is_paid: Optional[bool] = None
    paid_date: Optional[datetime] = None
    paid_by: Optional[int] = None


class PaymentResponse(PaymentBase):
    id: int
    is_paid: bool
    paid_date: Optional[datetime] = None
    paid_by: Optional[int] = None
    reassigned: bool
    old_employee_id: Optional[int] = None
    employee_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# ТАРИФЫ
# =========================

class RateBase(BaseModel):
    project_type: Optional[str] = None
    role: Optional[str] = None
    stage_name: Optional[str] = None
    rate_per_m2: Optional[float] = None
    area_from: Optional[float] = None
    area_to: Optional[float] = None
    fixed_price: Optional[float] = None
    price: Optional[float] = None
    executor_rate: Optional[float] = None
    manager_rate: Optional[float] = None
    city: Optional[str] = None
    surveyor_price: Optional[float] = None


class RateCreate(RateBase):
    pass


class RateUpdate(BaseModel):
    project_type: Optional[str] = None
    role: Optional[str] = None
    stage_name: Optional[str] = None
    rate_per_m2: Optional[float] = None
    area_from: Optional[float] = None
    area_to: Optional[float] = None
    fixed_price: Optional[float] = None
    price: Optional[float] = None
    executor_rate: Optional[float] = None
    manager_rate: Optional[float] = None
    city: Optional[str] = None
    surveyor_price: Optional[float] = None


class RateResponse(RateBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# =========================
# ЗАРПЛАТЫ
# =========================

class SalaryBase(BaseModel):
    contract_id: Optional[int] = None
    employee_id: int
    payment_type: str
    stage_name: Optional[str] = None
    amount: float
    advance_payment: Optional[float] = None
    report_month: str
    project_type: Optional[str] = None
    payment_status: Optional[str] = None
    comments: Optional[str] = None


class SalaryCreate(SalaryBase):
    pass


class SalaryUpdate(BaseModel):
    payment_type: Optional[str] = None
    stage_name: Optional[str] = None
    amount: Optional[float] = None
    advance_payment: Optional[float] = None
    report_month: Optional[str] = None
    project_type: Optional[str] = None
    payment_status: Optional[str] = None
    comments: Optional[str] = None


class SalaryResponse(SalaryBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


# =========================
# ФАЙЛЫ ПРОЕКТА
# =========================

class ProjectFileBase(BaseModel):
    contract_id: int
    stage: str
    file_type: str
    public_link: Optional[str] = None
    yandex_path: str
    file_name: str
    file_order: int = 0
    variation: int = 1


class ProjectFileCreate(ProjectFileBase):
    pass


class ProjectFileResponse(ProjectFileBase):
    id: int
    upload_date: datetime
    preview_cache_path: Optional[str] = None

    class Config:
        from_attributes = True


# =========================
# ИСТОРИЯ ДЕЙСТВИЙ
# =========================

class ActionHistoryCreate(BaseModel):
    action_type: str
    entity_type: str
    entity_id: int
    description: Optional[str] = None


class ActionHistoryResponse(BaseModel):
    id: int
    user_id: int
    action_type: str
    entity_type: str
    entity_id: int
    description: Optional[str] = None
    action_date: datetime

    class Config:
        from_attributes = True


# =========================
# EXTENDED REQUEST SCHEMAS
# =========================

class PaymentManualUpdateRequest(BaseModel):
    """Схема для ручного обновления платежа"""
    amount: float
    report_month: str


class TemplateRateRequest(BaseModel):
    """Схема для сохранения шаблонного тарифа"""
    role: str
    area_from: float
    area_to: float
    price: float


class IndividualRateRequest(BaseModel):
    """Схема для сохранения индивидуального тарифа"""
    role: str
    rate_per_m2: float
    stage_name: Optional[str] = None


class SupervisionRateRequest(BaseModel):
    """Схема для сохранения тарифа надзора"""
    stage_name: str
    executor_rate: float
    manager_rate: float


class SurveyorRateRequest(BaseModel):
    """Схема для сохранения тарифа замерщика"""
    city: str
    price: float
