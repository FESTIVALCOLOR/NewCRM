"""
База данных - SQLAlchemy модели
Многопользовательская структура
"""
from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, Float, Text, ForeignKey, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import get_settings

settings = get_settings()

# Создание engine
engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
    pool_pre_ping=True
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# =========================
# МНОГОПОЛЬЗОВАТЕЛЬСКИЕ ТАБЛИЦЫ
# =========================

class Employee(Base):
    """Сотрудники (пользователи системы)"""
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String, nullable=False)
    phone = Column(String, nullable=False)
    email = Column(String)
    address = Column(String)
    birth_date = Column(String)

    # Аутентификация
    login = Column(String, unique=True, index=True)
    password_hash = Column(String, nullable=False)

    # Роль и должность
    position = Column(String, nullable=False)
    secondary_position = Column(String)
    department = Column(String, nullable=False)
    role = Column(String)

    # Статус
    status = Column(String, default="активный")

    # Многопользовательские поля
    last_login = Column(DateTime)
    is_online = Column(Boolean, default=False)
    last_activity = Column(DateTime)
    current_session_token = Column(String)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    sessions = relationship("UserSession", back_populates="employee")
    permissions = relationship("UserPermission", back_populates="employee", foreign_keys="[UserPermission.employee_id]")
    notifications = relationship("Notification", back_populates="employee")


class UserSession(Base):
    """Сессии пользователей"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    session_token = Column(String, unique=True, nullable=False, index=True)
    refresh_token = Column(String, unique=True)

    ip_address = Column(String)
    user_agent = Column(String)
    computer_name = Column(String)

    login_time = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    logout_time = Column(DateTime)

    is_active = Column(Boolean, default=True)

    # Связи
    employee = relationship("Employee", back_populates="sessions")


class UserPermission(Base):
    """Детальные права доступа"""
    __tablename__ = "user_permissions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    permission_type = Column(String, nullable=False)  # 'tab_access', 'entity_edit', 'entity_delete', 'entity_create'
    target = Column(String, nullable=False)  # название вкладки или таблицы

    granted_by = Column(Integer, ForeignKey("employees.id"))
    granted_date = Column(DateTime, default=datetime.utcnow)

    # Связи
    employee = relationship("Employee", back_populates="permissions", foreign_keys=[employee_id])


class ActivityLog(Base):
    """Расширенный лог действий"""
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("user_sessions.id"))

    action_type = Column(String, nullable=False)  # 'login', 'logout', 'create', 'update', 'delete', 'view'
    entity_type = Column(String, nullable=False)  # 'client', 'contract', 'crm_card', etc.
    entity_id = Column(Integer)

    old_values = Column(JSON)  # JSON с прежними значениями
    new_values = Column(JSON)  # JSON с новыми значениями

    ip_address = Column(String)
    action_date = Column(DateTime, default=datetime.utcnow, index=True)


class ConcurrentEdit(Base):
    """Блокировка записей при редактировании"""
    __tablename__ = "concurrent_edits"

    id = Column(Integer, primary_key=True, index=True)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False)

    locked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Автоматическая разблокировка через 30 минут


class Notification(Base):
    """Уведомления для пользователей"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    notification_type = Column(String, nullable=False)  # 'task_assigned', 'deadline_warning', etc.
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)

    related_entity_type = Column(String)
    related_entity_id = Column(Integer)

    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    read_at = Column(DateTime)

    # Связи
    employee = relationship("Employee", back_populates="notifications")


class FileStorage(Base):
    """Хранилище файлов"""
    __tablename__ = "file_storage"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, nullable=False)

    file_type = Column(String, nullable=False)  # 'contract', 'tech_task', 'measurement', 'stage_file'
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String)

    # Местоположение
    storage_location = Column(String, nullable=False)  # 'server' или 'yandex'
    server_path = Column(String)
    yandex_path = Column(String)

    # Доступ
    public_url = Column(String)
    preview_cache_path = Column(String)

    # Синхронизация
    is_synced_to_yandex = Column(Boolean, default=False)
    last_sync_date = Column(DateTime)

    # Метаданные
    uploaded_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)


# =========================
# ОСНОВНЫЕ ТАБЛИЦЫ (из текущей системы)
# =========================

class Client(Base):
    """Клиенты"""
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    client_type = Column(String, nullable=False)
    full_name = Column(String)
    phone = Column(String, nullable=False)
    email = Column(String)

    # Паспортные данные
    passport_series = Column(String)
    passport_number = Column(String)
    passport_issued_by = Column(String)
    passport_issued_date = Column(String)
    registration_address = Column(String)

    # Для организаций
    organization_type = Column(String)
    organization_name = Column(String)
    inn = Column(String)
    ogrn = Column(String)
    account_details = Column(Text)
    responsible_person = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Contract(Base):
    """Договоры"""
    __tablename__ = "contracts"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)

    project_type = Column(String, nullable=False)
    agent_type = Column(String)
    city = Column(String)

    contract_number = Column(String, unique=True, nullable=False)
    contract_date = Column(String)

    address = Column(String)
    area = Column(Float)

    total_amount = Column(Float)
    advance_payment = Column(Float)
    additional_payment = Column(Float)
    third_payment = Column(Float)

    contract_period = Column(Integer)
    comments = Column(Text)

    contract_file_link = Column(String)
    tech_task_link = Column(String)
    tech_task_yandex_path = Column(String)
    tech_task_file_name = Column(String)

    # Поля для файлов замера
    measurement_image_link = Column(String)
    measurement_file_name = Column(String)
    measurement_yandex_path = Column(String)
    measurement_date = Column(String)

    status = Column(String, default="Новый заказ")
    status_changed_date = Column(String)
    termination_reason = Column(Text)

    yandex_folder_path = Column(String)

    # Поля для референсов и фотофиксации (25.01.2026)
    references_yandex_path = Column(String)
    photo_documentation_yandex_path = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    crm_cards = relationship("CRMCard", back_populates="contract")
    supervision_cards = relationship("SupervisionCard", back_populates="contract")


# =========================
# CRM КАРТОЧКИ
# =========================

class CRMCard(Base):
    """CRM карточки проектов"""
    __tablename__ = "crm_cards"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    column_name = Column(String, nullable=False, default="Новый заказ")
    deadline = Column(String)
    tags = Column(String)

    is_approved = Column(Boolean, default=False)
    approval_deadline = Column(String)
    approval_stages = Column(Text)  # JSON строка

    project_data_link = Column(String)
    tech_task_file = Column(String)
    tech_task_date = Column(String)
    survey_date = Column(String)

    # Менеджеры
    senior_manager_id = Column(Integer, ForeignKey("employees.id"))
    sdp_id = Column(Integer, ForeignKey("employees.id"))  # Старший дизайнер-проектировщик
    gap_id = Column(Integer, ForeignKey("employees.id"))  # Главный архитектор-проектировщик
    manager_id = Column(Integer, ForeignKey("employees.id"))
    surveyor_id = Column(Integer, ForeignKey("employees.id"))

    order_position = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    contract = relationship("Contract", back_populates="crm_cards")
    senior_manager = relationship("Employee", foreign_keys=[senior_manager_id])
    sdp = relationship("Employee", foreign_keys=[sdp_id])
    gap = relationship("Employee", foreign_keys=[gap_id])
    manager = relationship("Employee", foreign_keys=[manager_id])
    surveyor = relationship("Employee", foreign_keys=[surveyor_id])
    stage_executors = relationship("StageExecutor", back_populates="crm_card")


class StageExecutor(Base):
    """Исполнители по стадиям"""
    __tablename__ = "stage_executors"

    id = Column(Integer, primary_key=True, index=True)
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id"), nullable=False)

    stage_name = Column(String, nullable=False)
    executor_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    assigned_date = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("employees.id"), nullable=False)

    deadline = Column(String)
    submitted_date = Column(DateTime)

    completed = Column(Boolean, default=False)
    completed_date = Column(DateTime)

    # Связи
    crm_card = relationship("CRMCard", back_populates="stage_executors")
    executor = relationship("Employee", foreign_keys=[executor_id])


# =========================
# SUPERVISION (Авторский надзор)
# =========================

class SupervisionCard(Base):
    """Карточки авторского надзора"""
    __tablename__ = "supervision_cards"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    column_name = Column(String, nullable=False, default="Новый заказ")
    deadline = Column(String)
    tags = Column(String)

    senior_manager_id = Column(Integer, ForeignKey("employees.id"))
    dan_id = Column(Integer, ForeignKey("employees.id"))  # Дежурный по авторскому надзору
    dan_completed = Column(Boolean, default=False)

    is_paused = Column(Boolean, default=False)
    pause_reason = Column(Text)
    paused_at = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    contract = relationship("Contract", back_populates="supervision_cards")
    senior_manager = relationship("Employee", foreign_keys=[senior_manager_id])
    dan = relationship("Employee", foreign_keys=[dan_id])
    history = relationship("SupervisionProjectHistory", back_populates="supervision_card")


class SupervisionProjectHistory(Base):
    """История проектов надзора"""
    __tablename__ = "supervision_project_history"

    id = Column(Integer, primary_key=True, index=True)
    supervision_card_id = Column(Integer, ForeignKey("supervision_cards.id"), nullable=False)

    entry_type = Column(String, nullable=False)  # pause, resume, etc.
    message = Column(Text, nullable=False)

    created_by = Column(Integer, ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    supervision_card = relationship("SupervisionCard", back_populates="history")


# =========================
# ПЛАТЕЖИ И ТАРИФЫ
# =========================

class Payment(Base):
    """Платежи/выплаты"""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id"))
    supervision_card_id = Column(Integer, ForeignKey("supervision_cards.id"))

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    role = Column(String, nullable=False)
    stage_name = Column(String)

    calculated_amount = Column(Float, nullable=False)
    manual_amount = Column(Float)
    final_amount = Column(Float, nullable=False)

    is_manual = Column(Boolean, default=False)
    payment_type = Column(String)  # Полная оплата, Аванс, Доплата, Оклад
    report_month = Column(String)
    payment_status = Column(String)

    is_paid = Column(Boolean, default=False)
    paid_date = Column(DateTime)
    paid_by = Column(Integer, ForeignKey("employees.id"))

    reassigned = Column(Boolean, default=False)
    old_employee_id = Column(Integer)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    employee = relationship("Employee", foreign_keys=[employee_id])


class Rate(Base):
    """Тарифы"""
    __tablename__ = "rates"

    id = Column(Integer, primary_key=True, index=True)
    project_type = Column(String)  # Индивидуальный, Шаблонный, Авторский надзор
    role = Column(String)
    stage_name = Column(String)

    rate_per_m2 = Column(Float)
    area_from = Column(Float)
    area_to = Column(Float)
    fixed_price = Column(Float)
    price = Column(Float)  # Цена (для шаблонных)

    # Для авторского надзора
    executor_rate = Column(Float)
    manager_rate = Column(Float)

    city = Column(String)
    surveyor_price = Column(Float)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Salary(Base):
    """Зарплаты/оклады"""
    __tablename__ = "salaries"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"))
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    payment_type = Column(String, nullable=False)
    stage_name = Column(String)

    amount = Column(Float, nullable=False)
    advance_payment = Column(Float)

    report_month = Column(String, nullable=False)
    project_type = Column(String)
    payment_status = Column(String)
    comments = Column(Text)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Связи
    employee = relationship("Employee", foreign_keys=[employee_id])


# =========================
# ФАЙЛЫ ПРОЕКТА
# =========================

class ProjectFile(Base):
    """Файлы проекта"""
    __tablename__ = "project_files"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False)

    stage = Column(String, nullable=False)
    file_type = Column(String, nullable=False)  # image, pdf, excel

    public_link = Column(String)
    yandex_path = Column(String, nullable=False)
    file_name = Column(String, nullable=False)

    upload_date = Column(DateTime, default=datetime.utcnow)
    preview_cache_path = Column(String)
    file_order = Column(Integer, default=0)
    variation = Column(Integer, default=1)


# =========================
# ИСТОРИЯ ДЕЙСТВИЙ
# =========================

class ActionHistory(Base):
    """История действий (для локальной совместимости)"""
    __tablename__ = "action_history"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    action_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer, nullable=False)

    description = Column(Text)
    action_date = Column(DateTime, default=datetime.utcnow)


class ApprovalStageDeadline(Base):
    """Дедлайны стадий согласования"""
    __tablename__ = "approval_stage_deadlines"

    id = Column(Integer, primary_key=True, index=True)
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id"), nullable=False)

    stage_name = Column(String, nullable=False)
    deadline = Column(String, nullable=False)  # DATE as string for compatibility

    is_completed = Column(Boolean, default=False)
    completed_date = Column(DateTime)

    created_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    """Инициализация базы данных"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """Получить сессию БД для dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
