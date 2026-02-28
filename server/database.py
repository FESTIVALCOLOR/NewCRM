"""
База данных - SQLAlchemy модели
Многопользовательская структура
"""
from sqlalchemy import create_engine, Column, Integer, BigInteger, String, Boolean, DateTime, Float, Text, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
from config import get_settings

settings = get_settings()

# Создание engine
_is_sqlite = "sqlite" in settings.database_url

_engine_kwargs = {
    "pool_pre_ping": True,
}

if _is_sqlite:
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    # PostgreSQL: настройка connection pool
    _engine_kwargs.update({
        "pool_size": 10,          # Постоянных соединений на worker
        "max_overflow": 20,       # Дополнительных при пиковой нагрузке
        "pool_timeout": 30,       # Ожидание свободного соединения (сек)
        "pool_recycle": 1800,     # Пересоздание соединений каждые 30 мин
    })

engine = create_engine(settings.database_url, **_engine_kwargs)

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

    # Цвет агента (для сотрудников с position='Агент')
    agent_color = Column(String)

    # Даты
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Связи
    sessions = relationship("UserSession", back_populates="employee", cascade="all, delete-orphan")
    permissions = relationship("UserPermission", back_populates="employee", foreign_keys="[UserPermission.employee_id]", cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="employee", cascade="all, delete-orphan")


class UserSession(Base):
    """Сессии пользователей"""
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

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
    """Именованные права доступа (granular permissions)"""
    __tablename__ = "user_permissions"
    __table_args__ = (
        UniqueConstraint('employee_id', 'permission_name', name='uq_employee_permission'),
    )

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    permission_name = Column(String, nullable=False)  # 'crm_cards.update', 'employees.create', ...

    granted_by = Column(Integer, ForeignKey("employees.id"), index=True)
    granted_date = Column(DateTime, default=datetime.utcnow)

    # Связи
    employee = relationship("Employee", back_populates="permissions", foreign_keys=[employee_id])


class RoleDefaultPermission(Base):
    """Дефолтные права по ролям (настраиваемая матрица)"""
    __tablename__ = "role_default_permissions"
    __table_args__ = (
        UniqueConstraint('role', 'permission_name', name='uq_role_perm'),
    )

    id = Column(Integer, primary_key=True, index=True)
    role = Column(String, nullable=False, index=True)
    permission_name = Column(String, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)


class NormDaysTemplate(Base):
    """Шаблоны нормо-дней по типам проектов"""
    __tablename__ = "norm_days_templates"

    id = Column(Integer, primary_key=True, index=True)
    project_type = Column(String, nullable=False)       # 'Индивидуальный' / 'Шаблонный'
    project_subtype = Column(String, nullable=False)     # 'Полный', 'Эскизный', etc.
    stage_code = Column(String, nullable=False)          # S1_1_01, T1_1_01
    stage_name = Column(String, nullable=False)
    stage_group = Column(String, nullable=False)         # STAGE1, STAGE2, STAGE3
    substage_group = Column(String, nullable=True)
    base_norm_days = Column(Float, nullable=False)       # базовое значение
    k_multiplier = Column(Float, default=0)              # множитель K (площади)
    executor_role = Column(String, nullable=False)
    is_in_contract_scope = Column(Boolean, default=True)
    sort_order = Column(Integer, nullable=False)
    agent_type = Column(String, default='Все агенты')  # 'Все агенты' / имя агента
    updated_at = Column(DateTime, default=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    __table_args__ = (
        UniqueConstraint('project_type', 'project_subtype', 'stage_code', 'agent_type', name='uq_norm_template'),
    )


class Agent(Base):
    """Агенты (типы агентов: ПЕТРОВИЧ, ФЕСТИВАЛЬ и т.д.)"""
    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    color = Column(String, nullable=False, default='#FFFFFF')
    status = Column(String, default='активный')
    created_at = Column(DateTime, default=datetime.utcnow)


class City(Base):
    """Города"""
    __tablename__ = "cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False)
    status = Column(String, default='активный')
    created_at = Column(DateTime, default=datetime.utcnow)


class ActivityLog(Base):
    """Расширенный лог действий"""
    __tablename__ = "activity_log"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), index=True)

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

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False, index=True)

    locked_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # Автоматическая разблокировка через 30 минут


class Notification(Base):
    """Уведомления для пользователей"""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

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
    uploaded_by = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
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
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False, index=True)

    project_type = Column(String, nullable=False)
    project_subtype = Column(String)  # Полный/Эскизный/Планировочный / Стандарт/...
    floors = Column(Integer, default=1)  # Кол-во этажей (для шаблонных)
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
    contract_file_yandex_path = Column(String)
    contract_file_name = Column(String)
    template_contract_file_link = Column(String)
    template_contract_file_yandex_path = Column(String)
    template_contract_file_name = Column(String)
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

    # Поля для актов и информационного письма
    act_planning_link = Column(String)
    act_planning_yandex_path = Column(String)
    act_planning_file_name = Column(String)
    act_concept_link = Column(String)
    act_concept_yandex_path = Column(String)
    act_concept_file_name = Column(String)
    info_letter_link = Column(String)
    info_letter_yandex_path = Column(String)
    info_letter_file_name = Column(String)
    act_final_link = Column(String)
    act_final_yandex_path = Column(String)
    act_final_file_name = Column(String)

    # Подписанные акты
    act_planning_signed_link = Column(String)
    act_planning_signed_yandex_path = Column(String)
    act_planning_signed_file_name = Column(String)
    act_concept_signed_link = Column(String)
    act_concept_signed_yandex_path = Column(String)
    act_concept_signed_file_name = Column(String)
    info_letter_signed_link = Column(String)
    info_letter_signed_yandex_path = Column(String)
    info_letter_signed_file_name = Column(String)
    act_final_signed_link = Column(String)
    act_final_signed_yandex_path = Column(String)
    act_final_signed_file_name = Column(String)

    # Отслеживание платежей (даты оплат + чеки)
    advance_payment_paid_date = Column(String)
    additional_payment_paid_date = Column(String)
    third_payment_paid_date = Column(String)
    advance_receipt_link = Column(String)
    advance_receipt_yandex_path = Column(String)
    advance_receipt_file_name = Column(String)
    additional_receipt_link = Column(String)
    additional_receipt_yandex_path = Column(String)
    additional_receipt_file_name = Column(String)
    third_receipt_link = Column(String)
    third_receipt_yandex_path = Column(String)
    third_receipt_file_name = Column(String)

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
    contract_id = Column(Integer, ForeignKey("contracts.id"), nullable=False, index=True)

    column_name = Column(String, nullable=False, default="Новый заказ")
    previous_column = Column(String)  # Предыдущий столбец (для возврата из "В ожидании")
    deadline = Column(String)
    paused_at = Column(DateTime)  # K1: Время постановки на паузу (для пересчёта дедлайна)
    total_pause_days = Column(Integer, default=0)  # K1: Суммарные дни паузы
    tags = Column(String)

    is_approved = Column(Boolean, default=False)
    approval_deadline = Column(String)
    approval_stages = Column(Text)  # JSON строка

    project_data_link = Column(String)
    tech_task_file = Column(String)
    tech_task_date = Column(String)
    survey_date = Column(String)

    # Менеджеры
    senior_manager_id = Column(Integer, ForeignKey("employees.id"), index=True)
    sdp_id = Column(Integer, ForeignKey("employees.id"), index=True)  # Старший дизайнер-проектировщик
    gap_id = Column(Integer, ForeignKey("employees.id"), index=True)  # Главный архитектор-проектировщик
    manager_id = Column(Integer, ForeignKey("employees.id"), index=True)
    surveyor_id = Column(Integer, ForeignKey("employees.id"), index=True)

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
    # S-07: nullable для SET NULL при удалении сотрудника
    executor_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

    assigned_date = Column(DateTime, default=datetime.utcnow)
    assigned_by = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

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
    previous_column = Column(String)  # Предыдущий столбец (для возврата из "В ожидании")
    start_date = Column(String)  # Дата начала надзора
    deadline = Column(String)
    tags = Column(String)

    senior_manager_id = Column(Integer, ForeignKey("employees.id"))
    dan_id = Column(Integer, ForeignKey("employees.id"))  # Дежурный по авторскому надзору
    dan_completed = Column(Boolean, default=False)

    is_paused = Column(Boolean, default=False)
    pause_reason = Column(Text)
    paused_at = Column(DateTime)
    total_pause_days = Column(Integer, default=0)

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
# ТАБЛИЦЫ СРОКОВ (TIMELINE)
# =========================

class ProjectTimelineEntry(Base):
    """Записи таблицы сроков проекта"""
    __tablename__ = "project_timeline_entries"
    __table_args__ = (
        UniqueConstraint('contract_id', 'stage_code', name='uq_timeline_contract_stage'),
    )

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_code = Column(String(20), nullable=False)
    stage_name = Column(String(255), nullable=False)
    stage_group = Column(String(100), nullable=False)
    substage_group = Column(String(100))
    actual_date = Column(String)
    actual_days = Column(Integer, default=0)
    norm_days = Column(Integer, default=0)
    custom_norm_days = Column(Integer, nullable=True)  # Кастомная норма (если СДП изменил)
    status = Column(String(20), default='')
    executor_role = Column(String(50), nullable=False)
    is_in_contract_scope = Column(Boolean, default=True)
    sort_order = Column(Integer, nullable=False)
    raw_norm_days = Column(Float, default=0)
    cumulative_days = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupervisionTimelineEntry(Base):
    """Записи таблицы сроков надзора"""
    __tablename__ = "supervision_timeline_entries"
    __table_args__ = (
        UniqueConstraint('supervision_card_id', 'stage_code', name='uq_sv_timeline_card_stage'),
    )

    id = Column(Integer, primary_key=True, index=True)
    supervision_card_id = Column(Integer, ForeignKey("supervision_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_code = Column(String(30), nullable=False)
    stage_name = Column(String(255), nullable=False)
    sort_order = Column(Integer, nullable=False)
    plan_date = Column(String)
    actual_date = Column(String)
    actual_days = Column(Integer, default=0)
    budget_planned = Column(Float, default=0)
    budget_actual = Column(Float, default=0)
    budget_savings = Column(Float, default=0)
    supplier = Column(String(255))
    commission = Column(Float, default=0)
    status = Column(String(20), default='Не начато')
    notes = Column(Text)
    executor = Column(String(100))
    defects_found = Column(Integer, default=0)
    defects_resolved = Column(Integer, default=0)
    site_visits = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SupervisionVisit(Base):
    """Записи выездов на объект авторского надзора"""
    __tablename__ = "supervision_visits"

    id = Column(Integer, primary_key=True, index=True)
    supervision_card_id = Column(Integer, ForeignKey("supervision_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_code = Column(String(30), nullable=False)
    stage_name = Column(String(255), nullable=False)
    visit_date = Column(String, nullable=False)  # YYYY-MM-DD
    executor_name = Column(String(255))  # ФИО исполнителя (ДАН)
    notes = Column(Text)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    supervision_card = relationship("SupervisionCard", backref="visits")


# =========================
# РАБОЧИЙ ПРОЦЕСС (WORKFLOW)
# =========================

class StageWorkflowState(Base):
    """Состояние рабочего процесса стадии CRM карточки"""
    __tablename__ = "stage_workflow_state"

    id = Column(Integer, primary_key=True, index=True)
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id", ondelete="CASCADE"), nullable=False, index=True)
    stage_name = Column(String(255), nullable=False)
    current_substep_code = Column(String(30))
    status = Column(String(30), default='in_progress')  # in_progress, revision, client_approval, completed
    revision_count = Column(Integer, default=0)
    revision_file_path = Column(Text)
    client_approval_started_at = Column(DateTime)
    client_approval_deadline_paused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


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

    # S-07: nullable чтобы сохранять платежи при удалении сотрудника (SET NULL)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)
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
    # S-07: nullable чтобы сохранять зарплаты при удалении сотрудника (SET NULL)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="SET NULL"), nullable=True)

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


# =========================
# МЕССЕНДЖЕР-ЧАТЫ
# =========================

class MessengerChat(Base):
    """Чаты проектов в мессенджерах"""
    __tablename__ = "messenger_chats"

    id = Column(Integer, primary_key=True, index=True)
    contract_id = Column(Integer, ForeignKey("contracts.id"))
    crm_card_id = Column(Integer, ForeignKey("crm_cards.id"))
    supervision_card_id = Column(Integer, nullable=True)

    messenger_type = Column(String, nullable=False, default="telegram")
    telegram_chat_id = Column(BigInteger, nullable=True)
    chat_title = Column(String, nullable=True)
    invite_link = Column(String, nullable=True)
    avatar_type = Column(String, nullable=True)  # 'festival' / 'petrovich'
    creation_method = Column(String, nullable=False, default="manual")  # 'auto' / 'manual'

    created_by = Column(Integer, ForeignKey("employees.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)


class MessengerChatMember(Base):
    """Участники чата"""
    __tablename__ = "messenger_chat_members"

    id = Column(Integer, primary_key=True, index=True)
    messenger_chat_id = Column(Integer, ForeignKey("messenger_chats.id", ondelete="CASCADE"), nullable=False)

    member_type = Column(String, nullable=False)  # 'employee' / 'client'
    member_id = Column(Integer, nullable=False)
    role_in_project = Column(String, nullable=True)
    is_mandatory = Column(Boolean, default=False)

    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    telegram_user_id = Column(BigInteger, nullable=True)

    invite_status = Column(String, default="pending")  # pending/sent/joined/email_sent
    invited_at = Column(DateTime, nullable=True)
    joined_at = Column(DateTime, nullable=True)


class MessengerScript(Base):
    """Скрипты автоматических сообщений"""
    __tablename__ = "messenger_scripts"

    id = Column(Integer, primary_key=True, index=True)
    script_type = Column(String, nullable=False)  # project_start/stage_complete/project_end
    project_type = Column(String, nullable=True)  # Индивидуальный/Шаблонный/Авторский надзор/NULL
    stage_name = Column(String, nullable=True)

    message_template = Column(Text, nullable=False)
    memo_file_path = Column(String, nullable=True)  # Путь к PDF-памятке на Яндекс.Диске
    use_auto_deadline = Column(Boolean, default=True)
    is_enabled = Column(Boolean, default=True)
    sort_order = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class MessengerSetting(Base):
    """Настройки мессенджера"""
    __tablename__ = "messenger_settings"

    id = Column(Integer, primary_key=True, index=True)
    setting_key = Column(String, unique=True, nullable=False)
    setting_value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)


class MessengerMessageLog(Base):
    """Лог отправленных сообщений"""
    __tablename__ = "messenger_message_log"

    id = Column(Integer, primary_key=True, index=True)
    messenger_chat_id = Column(Integer, ForeignKey("messenger_chats.id", ondelete="CASCADE"))

    message_type = Column(String, nullable=True)  # auto_stage/auto_start/auto_end/file/manual
    message_text = Column(Text, nullable=True)
    file_links = Column(Text, nullable=True)  # JSON

    sent_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    sent_at = Column(DateTime, default=datetime.utcnow)
    telegram_message_id = Column(BigInteger, nullable=True)
    delivery_status = Column(String, default="sent")  # sent/failed/pending


def _auto_migrate_columns():
    """Автоматически добавляет недостающие столбцы в существующие таблицы.

    create_all() НЕ добавляет новые столбцы к уже существующим таблицам.
    Эта функция сравнивает модель с БД и выполняет ALTER TABLE ADD COLUMN.
    """
    import logging
    from sqlalchemy import inspect, text
    logger = logging.getLogger(__name__)
    try:
        inspector = inspect(engine)
        existing_tables = inspector.get_table_names()

        for table in Base.metadata.sorted_tables:
            if table.name not in existing_tables:
                continue  # create_all() создаст таблицу целиком

            db_columns = {col['name'] for col in inspector.get_columns(table.name)}
            for col in table.columns:
                if col.name not in db_columns:
                    col_type = col.type.compile(engine.dialect)
                    nullable = "NULL" if col.nullable else "NOT NULL"
                    default = ""
                    if col.default is not None:
                        default = f" DEFAULT {col.default.arg!r}"
                    sql = f'ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type} {nullable}{default}'
                    with engine.begin() as conn:
                        conn.execute(text(sql))
                    logger.info(f"auto-migrate: добавлен столбец {table.name}.{col.name} ({col_type})")
    except Exception as e:
        logger.warning(f"auto-migrate warning: {e}")


def init_db():
    """Инициализация базы данных"""
    try:
        Base.metadata.create_all(bind=engine)
        _auto_migrate_columns()
    except Exception as e:
        # Race condition при 2+ workers: один уже создал таблицы
        import logging
        logging.getLogger(__name__).warning(f"init_db warning (likely race condition): {e}")


def get_db():
    """Получить сессию БД для dependency injection"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
