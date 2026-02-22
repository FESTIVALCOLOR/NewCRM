"""
Pydantic схемы для валидации данных
"""
from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator
from typing import Optional, List, Dict
from datetime import datetime, date
import re


# =========================
# ОБЩИЕ ОТВЕТЫ
# =========================

class StatusResponse(BaseModel):
    """Ответ со статусом операции"""
    status: str
    message: str


class MessageResponse(BaseModel):
    """Ответ с сообщением"""
    message: str


class DeleteCountResponse(BaseModel):
    """Ответ с количеством удалённых записей"""
    status: str
    deleted_count: int


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


class LoginResponse(BaseModel):
    """Полный ответ при успешном входе"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    employee_id: int
    full_name: str
    role: str
    position: str
    secondary_position: str
    department: str


class RefreshTokenResponse(BaseModel):
    """Ответ при обновлении access_token"""
    access_token: str
    token_type: str = "bearer"
    employee_id: int
    full_name: str


# =========================
# СОТРУДНИКИ
# =========================

class EmployeeBase(BaseModel):
    full_name: str
    phone: Optional[str] = ""
    email: Optional[str] = None
    address: Optional[str] = None
    birth_date: Optional[str] = None
    position: str
    secondary_position: Optional[str] = None
    department: Optional[str] = ""
    role: Optional[str] = None
    status: str = "активный"


def _validate_password(v: str) -> str:
    """Общая валидация пароля (используется в EmployeeCreate и EmployeeUpdate)"""
    if len(v) < 6:
        raise ValueError('Пароль должен содержать минимум 6 символов')
    if not any(c.isdigit() for c in v):
        raise ValueError('Пароль должен содержать хотя бы одну цифру')
    if not any(c.isalpha() for c in v):
        raise ValueError('Пароль должен содержать хотя бы одну букву')
    return v


class EmployeeCreate(EmployeeBase):
    model_config = {"extra": "ignore"}

    login: Optional[str] = Field(None, min_length=3, max_length=50)
    password: str = Field(..., min_length=6, max_length=128)

    @model_validator(mode='before')
    @classmethod
    def handle_username_alias(cls, data):
        """Принимает username как алиас для login"""
        if isinstance(data, dict):
            if 'username' in data and not data.get('login'):
                data['login'] = data['username']
        return data

    @model_validator(mode='after')
    def ensure_login(self):
        """Проверяем что login задан"""
        if not self.login:
            raise ValueError('login обязателен')
        return self

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        return _validate_password(v)


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
    login: Optional[str] = None
    password: Optional[str] = None

    @field_validator('password')
    @classmethod
    def validate_password_strength(cls, v):
        if v is None:
            return v
        return _validate_password(v)


class EmployeeResponse(EmployeeBase):
    id: int
    login: Optional[str] = None
    is_online: bool
    last_login: Optional[datetime] = None
    agent_color: Optional[str] = None
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
    project_subtype: Optional[str] = None
    floors: Optional[int] = 1
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
    contract_file_yandex_path: Optional[str] = None
    contract_file_name: Optional[str] = None
    template_contract_file_link: Optional[str] = None
    template_contract_file_yandex_path: Optional[str] = None
    template_contract_file_name: Optional[str] = None
    tech_task_link: Optional[str] = None
    tech_task_yandex_path: Optional[str] = None
    tech_task_file_name: Optional[str] = None
    # Поля для файлов замера
    measurement_image_link: Optional[str] = None
    measurement_file_name: Optional[str] = None
    measurement_yandex_path: Optional[str] = None
    measurement_date: Optional[str] = None
    status: str = "Новый заказ"
    status_changed_date: Optional[str] = None
    termination_reason: Optional[str] = None
    yandex_folder_path: Optional[str] = None
    # Поля для референсов и фотофиксации (25.01.2026)
    references_yandex_path: Optional[str] = None
    photo_documentation_yandex_path: Optional[str] = None
    # Поля для актов и информационного письма
    act_planning_link: Optional[str] = None
    act_planning_yandex_path: Optional[str] = None
    act_planning_file_name: Optional[str] = None
    act_concept_link: Optional[str] = None
    act_concept_yandex_path: Optional[str] = None
    act_concept_file_name: Optional[str] = None
    info_letter_link: Optional[str] = None
    info_letter_yandex_path: Optional[str] = None
    info_letter_file_name: Optional[str] = None
    act_final_link: Optional[str] = None
    act_final_yandex_path: Optional[str] = None
    act_final_file_name: Optional[str] = None
    # Подписанные акты
    act_planning_signed_link: Optional[str] = None
    act_planning_signed_yandex_path: Optional[str] = None
    act_planning_signed_file_name: Optional[str] = None
    act_concept_signed_link: Optional[str] = None
    act_concept_signed_yandex_path: Optional[str] = None
    act_concept_signed_file_name: Optional[str] = None
    info_letter_signed_link: Optional[str] = None
    info_letter_signed_yandex_path: Optional[str] = None
    info_letter_signed_file_name: Optional[str] = None
    act_final_signed_link: Optional[str] = None
    act_final_signed_yandex_path: Optional[str] = None
    act_final_signed_file_name: Optional[str] = None
    # Отслеживание платежей
    advance_payment_paid_date: Optional[str] = None
    additional_payment_paid_date: Optional[str] = None
    third_payment_paid_date: Optional[str] = None
    advance_receipt_link: Optional[str] = None
    advance_receipt_yandex_path: Optional[str] = None
    advance_receipt_file_name: Optional[str] = None
    additional_receipt_link: Optional[str] = None
    additional_receipt_yandex_path: Optional[str] = None
    additional_receipt_file_name: Optional[str] = None
    third_receipt_link: Optional[str] = None
    third_receipt_yandex_path: Optional[str] = None
    third_receipt_file_name: Optional[str] = None

    @field_validator('area', mode='before')
    @classmethod
    def validate_area_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Площадь должна быть больше 0')
        return v


class ContractCreate(ContractBase):
    pass


class ContractUpdate(BaseModel):
    client_id: Optional[int] = None
    project_type: Optional[str] = None
    project_subtype: Optional[str] = None
    floors: Optional[int] = None
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
    contract_file_yandex_path: Optional[str] = None
    contract_file_name: Optional[str] = None
    template_contract_file_link: Optional[str] = None
    template_contract_file_yandex_path: Optional[str] = None
    template_contract_file_name: Optional[str] = None
    tech_task_link: Optional[str] = None
    tech_task_yandex_path: Optional[str] = None
    tech_task_file_name: Optional[str] = None
    # Поля для файлов замера
    measurement_image_link: Optional[str] = None
    measurement_file_name: Optional[str] = None
    measurement_yandex_path: Optional[str] = None
    measurement_date: Optional[str] = None
    status: Optional[str] = None
    status_changed_date: Optional[str] = None
    termination_reason: Optional[str] = None
    yandex_folder_path: Optional[str] = None
    # Поля для референсов и фотофиксации (25.01.2026)
    references_yandex_path: Optional[str] = None
    photo_documentation_yandex_path: Optional[str] = None
    # Поля для актов и информационного письма
    act_planning_link: Optional[str] = None
    act_planning_yandex_path: Optional[str] = None
    act_planning_file_name: Optional[str] = None
    act_concept_link: Optional[str] = None
    act_concept_yandex_path: Optional[str] = None
    act_concept_file_name: Optional[str] = None
    info_letter_link: Optional[str] = None
    info_letter_yandex_path: Optional[str] = None
    info_letter_file_name: Optional[str] = None
    act_final_link: Optional[str] = None
    act_final_yandex_path: Optional[str] = None
    act_final_file_name: Optional[str] = None
    # Подписанные акты
    act_planning_signed_link: Optional[str] = None
    act_planning_signed_yandex_path: Optional[str] = None
    act_planning_signed_file_name: Optional[str] = None
    act_concept_signed_link: Optional[str] = None
    act_concept_signed_yandex_path: Optional[str] = None
    act_concept_signed_file_name: Optional[str] = None
    info_letter_signed_link: Optional[str] = None
    info_letter_signed_yandex_path: Optional[str] = None
    info_letter_signed_file_name: Optional[str] = None
    act_final_signed_link: Optional[str] = None
    act_final_signed_yandex_path: Optional[str] = None
    act_final_signed_file_name: Optional[str] = None
    # Отслеживание платежей
    advance_payment_paid_date: Optional[str] = None
    additional_payment_paid_date: Optional[str] = None
    third_payment_paid_date: Optional[str] = None
    advance_receipt_link: Optional[str] = None
    advance_receipt_yandex_path: Optional[str] = None
    advance_receipt_file_name: Optional[str] = None
    additional_receipt_link: Optional[str] = None
    additional_receipt_yandex_path: Optional[str] = None
    additional_receipt_file_name: Optional[str] = None
    third_receipt_link: Optional[str] = None
    third_receipt_yandex_path: Optional[str] = None
    third_receipt_file_name: Optional[str] = None

    @field_validator('area', mode='before')
    @classmethod
    def validate_area_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError('Площадь должна быть больше 0')
        return v


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

    @field_validator('deadline', mode='before')
    @classmethod
    def validate_deadline_not_in_past(cls, v):
        if v is not None and v != '':
            try:
                deadline_date = datetime.strptime(str(v), '%Y-%m-%d').date()
                if deadline_date < date.today():
                    raise ValueError('Дедлайн не может быть в прошлом')
            except ValueError as e:
                if 'Дедлайн' in str(e):
                    raise
        return v


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

    @field_validator('deadline', mode='before')
    @classmethod
    def validate_deadline_not_in_past(cls, v):
        if v is not None and v != '':
            try:
                deadline_date = datetime.strptime(str(v), '%Y-%m-%d').date()
                if deadline_date < date.today():
                    raise ValueError('Дедлайн не может быть в прошлом')
            except ValueError as e:
                if 'Дедлайн' in str(e):
                    raise
        return v


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

    @field_validator('deadline', mode='before')
    @classmethod
    def validate_deadline_not_in_past(cls, v):
        if v is not None and v != '':
            try:
                deadline_date = datetime.strptime(str(v), '%Y-%m-%d').date()
                if deadline_date < date.today():
                    raise ValueError('Дедлайн не может быть в прошлом')
            except ValueError as e:
                if 'Дедлайн' in str(e):
                    raise
        return v


class StageExecutorUpdate(BaseModel):
    executor_id: Optional[int] = None
    deadline: Optional[str] = None
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
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    senior_manager_id: Optional[int] = None
    dan_id: Optional[int] = None
    dan_completed: bool = False

    @field_validator('deadline', mode='before')
    @classmethod
    def validate_deadline_not_in_past(cls, v):
        if v is not None and v != '':
            try:
                deadline_date = datetime.strptime(str(v), '%Y-%m-%d').date()
                if deadline_date < date.today():
                    raise ValueError('Дедлайн не может быть в прошлом')
            except ValueError as e:
                if 'Дедлайн' in str(e):
                    raise
        return v


class SupervisionCardCreate(SupervisionCardBase):
    pass


class SupervisionCardUpdate(BaseModel):
    column_name: Optional[str] = None
    start_date: Optional[str] = None
    deadline: Optional[str] = None
    tags: Optional[str] = None
    senior_manager_id: Optional[int] = None
    dan_id: Optional[int] = None
    dan_completed: Optional[bool] = None

    @field_validator('deadline', mode='before')
    @classmethod
    def validate_deadline_not_in_past(cls, v):
        if v is not None and v != '':
            try:
                deadline_date = datetime.strptime(str(v), '%Y-%m-%d').date()
                if deadline_date < date.today():
                    raise ValueError('Дедлайн не может быть в прошлом')
            except ValueError as e:
                if 'Дедлайн' in str(e):
                    raise
        return v


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


# ИСПРАВЛЕНИЕ 06.02.2026: Добавлена схема для создания записи истории (#22)
class SupervisionHistoryCreate(BaseModel):
    entry_type: str
    message: str
    created_by: Optional[int] = None


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
# CRM: Запросы согласования и исполнителей
# =========================

class CompleteApprovalStageRequest(BaseModel):
    stage_name: str


class StageExecutorDeadlineRequest(BaseModel):
    stage_name: str
    deadline: Optional[str] = None


class CompleteStageExecutorRequest(BaseModel):
    executor_id: int


class ManagerAcceptanceRequest(BaseModel):
    stage_name: str
    executor_name: str
    manager_id: int


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
    calculated_amount: Optional[float] = 0.0
    manual_amount: Optional[float] = None
    final_amount: Optional[float] = 0.0
    is_manual: bool = False
    payment_type: Optional[str] = None
    report_month: Optional[str] = None
    payment_status: Optional[str] = None
    reassigned: Optional[bool] = False  # ДОБАВЛЕНО 28.01.2026: Флаг переназначения
    old_employee_id: Optional[int] = None  # ДОБАВЛЕНО 28.01.2026: ID старого исполнителя

    @field_validator('calculated_amount', 'manual_amount', 'final_amount', mode='before')
    @classmethod
    def validate_amount_non_negative(cls, v):
        """Суммы не могут быть отрицательными"""
        if v is not None and v < 0:
            raise ValueError('Сумма не может быть отрицательной')
        return v

    @field_validator('report_month', mode='before')
    @classmethod
    def validate_report_month_format(cls, v):
        """Формат отчётного месяца: YYYY-MM"""
        if v is not None and v != '' and not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', str(v)):
            raise ValueError('Формат отчётного месяца должен быть YYYY-MM (например, 2026-01)')
        return v


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
    reassigned: Optional[bool] = None  # ДОБАВЛЕНО 28.01.2026: Флаг переназначения
    old_employee_id: Optional[int] = None  # ДОБАВЛЕНО 28.01.2026: ID старого исполнителя

    @field_validator('manual_amount', 'final_amount', mode='before')
    @classmethod
    def validate_amount_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Сумма не может быть отрицательной')
        return v

    @field_validator('report_month', mode='before')
    @classmethod
    def validate_report_month_format(cls, v):
        if v is not None and v != '' and not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', str(v)):
            raise ValueError('Формат отчётного месяца должен быть YYYY-MM')
        return v


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
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

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

    @field_validator('amount', 'advance_payment', mode='before')
    @classmethod
    def validate_amount_non_negative(cls, v):
        if v is not None and v < 0:
            raise ValueError('Сумма не может быть отрицательной')
        return v

    @field_validator('report_month', mode='before')
    @classmethod
    def validate_report_month_format(cls, v):
        if v is not None and v != '' and not re.match(r'^\d{4}-(0[1-9]|1[0-2])$', str(v)):
            raise ValueError('Формат отчётного месяца должен быть YYYY-MM')
        return v


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
# ДЕДЛАЙНЫ СОГЛАСОВАНИЯ
# =========================

class ApprovalDeadlineResponse(BaseModel):
    """Ответ с дедлайном согласования"""
    id: int
    crm_card_id: int
    stage_name: str
    deadline: Optional[str] = None
    is_completed: bool
    completed_date: Optional[datetime] = None
    created_at: Optional[datetime] = None

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


class ContractFilesUpdate(BaseModel):
    """Схема для обновления файлов договора (замер, референсы, фотофиксация, акты)"""
    measurement_image_link: Optional[str] = None
    measurement_file_name: Optional[str] = None
    measurement_yandex_path: Optional[str] = None
    measurement_date: Optional[str] = None
    contract_file_link: Optional[str] = None
    contract_file_yandex_path: Optional[str] = None
    contract_file_name: Optional[str] = None
    template_contract_file_link: Optional[str] = None
    template_contract_file_yandex_path: Optional[str] = None
    template_contract_file_name: Optional[str] = None
    tech_task_link: Optional[str] = None
    # Поля для актов и информационного письма
    act_planning_link: Optional[str] = None
    act_planning_yandex_path: Optional[str] = None
    act_planning_file_name: Optional[str] = None
    act_concept_link: Optional[str] = None
    act_concept_yandex_path: Optional[str] = None
    act_concept_file_name: Optional[str] = None
    info_letter_link: Optional[str] = None
    info_letter_yandex_path: Optional[str] = None
    info_letter_file_name: Optional[str] = None
    act_final_link: Optional[str] = None
    act_final_yandex_path: Optional[str] = None
    act_final_file_name: Optional[str] = None
    # Подписанные акты
    act_planning_signed_link: Optional[str] = None
    act_planning_signed_yandex_path: Optional[str] = None
    act_planning_signed_file_name: Optional[str] = None
    act_concept_signed_link: Optional[str] = None
    act_concept_signed_yandex_path: Optional[str] = None
    act_concept_signed_file_name: Optional[str] = None
    info_letter_signed_link: Optional[str] = None
    info_letter_signed_yandex_path: Optional[str] = None
    info_letter_signed_file_name: Optional[str] = None
    act_final_signed_link: Optional[str] = None
    act_final_signed_yandex_path: Optional[str] = None
    act_final_signed_file_name: Optional[str] = None
    # Чеки платежей
    advance_receipt_link: Optional[str] = None
    advance_receipt_yandex_path: Optional[str] = None
    advance_receipt_file_name: Optional[str] = None
    additional_receipt_link: Optional[str] = None
    additional_receipt_yandex_path: Optional[str] = None
    additional_receipt_file_name: Optional[str] = None
    third_receipt_link: Optional[str] = None
    third_receipt_yandex_path: Optional[str] = None
    third_receipt_file_name: Optional[str] = None


# =========================
# ТАБЛИЦА СРОКОВ ПРОЕКТА
# =========================

class TimelineEntryBase(BaseModel):
    stage_code: str
    stage_name: str
    stage_group: str
    substage_group: Optional[str] = None
    actual_date: Optional[str] = None
    actual_days: int = 0
    norm_days: int = 0
    status: str = ''
    executor_role: str
    is_in_contract_scope: bool = True
    sort_order: int
    custom_norm_days: Optional[int] = None
    raw_norm_days: float = 0
    cumulative_days: float = 0

class TimelineEntryCreate(TimelineEntryBase):
    pass

class TimelineEntryUpdate(BaseModel):
    actual_date: Optional[str] = None
    actual_days: Optional[int] = None
    norm_days: Optional[int] = None
    custom_norm_days: Optional[int] = None
    status: Optional[str] = None

class TimelineEntryResponse(TimelineEntryBase):
    id: int
    contract_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True

class TimelineInitRequest(BaseModel):
    project_type: str
    project_subtype: Optional[str] = None
    area: float
    floors: Optional[int] = 1
    force: Optional[bool] = False  # K10: Принудительный reinit (удаляет actual_date)


# =========================
# ТАБЛИЦА СРОКОВ НАДЗОРА
# =========================

class SupervisionTimelineBase(BaseModel):
    stage_code: str
    stage_name: str
    sort_order: int
    plan_date: Optional[str] = None
    actual_date: Optional[str] = None
    actual_days: int = 0
    budget_planned: float = 0
    budget_actual: float = 0
    budget_savings: float = 0
    supplier: Optional[str] = None
    commission: float = 0
    status: str = 'Не начато'
    notes: Optional[str] = None
    executor: Optional[str] = None
    defects_found: int = 0
    defects_resolved: int = 0
    site_visits: int = 0

class SupervisionTimelineCreate(SupervisionTimelineBase):
    pass

class SupervisionTimelineUpdate(BaseModel):
    plan_date: Optional[str] = None
    actual_date: Optional[str] = None
    actual_days: Optional[int] = None
    budget_planned: Optional[float] = None
    budget_actual: Optional[float] = None
    budget_savings: Optional[float] = None
    supplier: Optional[str] = None
    commission: Optional[float] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    executor: Optional[str] = None
    defects_found: Optional[int] = None
    defects_resolved: Optional[int] = None
    site_visits: Optional[int] = None

class SupervisionTimelineResponse(SupervisionTimelineBase):
    id: int
    supervision_card_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    class Config:
        from_attributes = True


# =========================
# ГЛОБАЛЬНЫЙ ПОИСК
# =========================

class SearchResult(BaseModel):
    type: str  # "client", "contract", "crm_card"
    id: int
    title: str
    subtitle: Optional[str] = None

class SearchResponse(BaseModel):
    results: List[SearchResult]
    total: int
    query: str


# =========================
# ПРАВА ДОСТУПА (PERMISSIONS)
# =========================

class PermissionSetRequest(BaseModel):
    """Установить набор прав сотрудника"""
    permissions: List[str]


class PermissionDefinition(BaseModel):
    """Определение одного права"""
    name: str
    description: str


class PermissionResponse(BaseModel):
    """Ответ с правами сотрудника"""
    employee_id: int
    permissions: List[str]
    is_superuser: bool = False


class RoleMatrixResponse(BaseModel):
    """Ответ с матрицей прав по ролям"""
    roles: Dict[str, List[str]]


class RoleMatrixUpdateRequest(BaseModel):
    """Запрос на обновление матрицы прав по ролям"""
    roles: Dict[str, List[str]]
    apply_to_employees: bool = False


# =========================
# НОРМО-ДНИ (ШАБЛОНЫ)
# =========================

class NormDaysTemplateEntry(BaseModel):
    """Одна запись шаблона нормо-дней"""
    stage_code: str = Field(..., min_length=1, max_length=50)
    stage_name: str = Field(..., min_length=1, max_length=200)
    stage_group: str = Field(..., min_length=1, max_length=50)
    substage_group: Optional[str] = None
    base_norm_days: float = Field(..., ge=0)
    k_multiplier: float = Field(default=0, ge=0)
    executor_role: str = Field(..., min_length=1, max_length=50)
    is_in_contract_scope: bool = True
    sort_order: int = Field(..., ge=0)


class NormDaysTemplateRequest(BaseModel):
    """Запрос на сохранение шаблона нормо-дней"""
    project_type: str = Field(..., min_length=1, max_length=50)
    project_subtype: str = Field(..., min_length=1, max_length=100)
    agent_type: str = Field(default='Все агенты', max_length=100)
    entries: List[NormDaysTemplateEntry] = Field(..., min_length=1)


class NormDaysTemplateResponse(BaseModel):
    """Ответ с шаблоном нормо-дней"""
    project_type: str
    project_subtype: str
    agent_type: str = 'Все агенты'
    entries: List[NormDaysTemplateEntry]
    is_custom: bool = False  # True если из БД, False если из формул


class NormDaysPreviewRequest(BaseModel):
    """Запрос на предпросмотр расчёта нормо-дней"""
    project_type: str = Field(..., min_length=1, max_length=50)
    project_subtype: str = Field(..., min_length=1, max_length=100)
    agent_type: str = Field(default='Все агенты', max_length=100)
    area: float = Field(..., gt=0, le=2000)


# =========================
# БЛОКИРОВКИ
# =========================

class LockRequest(BaseModel):
    """Запрос на создание блокировки"""
    entity_type: str
    entity_id: int
    employee_id: Optional[int] = None
