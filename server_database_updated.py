"""
База данных - SQLAlchemy модели
Многопользовательская структура + полная схема локальной БД
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

    # Дополнительные поля из локальной БД
    legal_status = Column(String)
    hire_date = Column(String)
    termination_date = Column(String)
    payment_details = Column(Text)

    # Зарплата
    salary_type = Column(String, default="fixed")
    base_salary = Column(Float, default=0.0)
    hourly_rate = Column(Float, default=0.0)
    commission_rate = Column(Float, default=0.0)

    # Заметки
    notes = Column(Text)

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

    permission_type = Column(String, nullable=False)
    target = Column(String, nullable=False)

    granted_by = Column(Integer, ForeignKey("employees.id"))
    granted_date = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    """Расширенный лог действий"""
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("user_sessions.id"))

    action_type = Column(String, nullable=False)
    entity_type = Column(String, nullable=False)
    entity_id = Column(Integer)

    old_values = Column(JSON)
    new_values = Column(JSON)

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
    expires_at = Column(DateTime)


class Notification(Base):
    """Уведомления для пользователей"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False)

    notification_type = Column(String, nullable=False)
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

    file_type = Column(String, nullable=False)
    file_name = Column(String, nullable=False)
    file_size = Column(Integer, nullable=False)
    mime_type = Column(String)

    storage_location = Column(String, nullable=False)
    server_path = Column(String)
    yandex_path = Column(String)

    public_url = Column(String)
    preview_cache_path = Column(String)

    is_synced_to_yandex = Column(Boolean, default=False)
    last_sync_date = Column(DateTime)

    uploaded_by = Column(Integer, ForeignKey("employees.id"), nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    last_accessed = Column(DateTime)
    access_count = Column(Integer, default=0)


# =========================
# ОСНОВНЫЕ ТАБЛИЦЫ
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
    manager_id = Column(Integer, ForeignKey("employees.id"))

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

    # Файлы договоров
    contract_file_link = Column(String)
    contract_file_name = Column(String)
    contract_file_yandex_path = Column(String)

    template_contract_file_link = Column(String)
    template_contract_file_name = Column(String)
    template_contract_file_yandex_path = Column(String)

    # Техзадания
    tech_task_link = Column(String)
    tech_task_file_name = Column(String)
    tech_task_yandex_path = Column(String)

    # Замеры
    measurement_image_link = Column(String)
    measurement_date = Column(String)
    measurement_file_name = Column(String)
    measurement_yandex_path = Column(String)

    # Прочие файлы
    references_yandex_path = Column(String)
    photo_documentation_yandex_path = Column(String)

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
