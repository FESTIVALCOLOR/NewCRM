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
    permissions = relationship("UserPermission", back_populates="employee")
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

    status = Column(String, default="Новый заказ")
    status_changed_date = Column(String)
    termination_reason = Column(Text)

    yandex_folder_path = Column(String)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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
