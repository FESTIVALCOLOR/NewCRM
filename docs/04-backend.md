# Бекенд проекта

> FastAPI сервер, SQLAlchemy модели, Pydantic схемы, PostgreSQL.

## Архитектура бекенда

```
┌───────────────────────────────────────────────┐
│              Docker Container: api            │
│                                               │
│  ┌──────────┐  ┌──────────┐  ┌────────────┐  │
│  │ FastAPI   │  │ SQLAlchemy│  │ Pydantic   │  │
│  │ main.py   │→ │ database  │→ │ schemas.py │  │
│  │ 5800+ LOC │  │ .py       │  │            │  │
│  │ 144+ EP   │  │           │  │            │  │
│  └──────────┘  └──────────┘  └────────────┘  │
│       │              │                        │
│       ▼              ▼                        │
│  ┌──────────┐  ┌──────────────┐              │
│  │ auth.py   │  │ yandex_disk  │              │
│  │ JWT/bcrypt│  │ _service.py  │              │
│  └──────────┘  └──────────────┘              │
└───────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  PostgreSQL      │
│  (Docker: 5432)  │
│  interior_studio │
│  _crm            │
└──────────────────┘
```

## Файлы бекенда

| Файл | Строк | Назначение |
|------|-------|-----------|
| [server/main.py](../server/main.py) | 5800+ | FastAPI приложение, 144+ endpoints |
| [server/database.py](../server/database.py) | ~500 | SQLAlchemy модели (15+ таблиц) |
| [server/schemas.py](../server/schemas.py) | ~400 | Pydantic валидация (30+ схем) |
| [server/auth.py](../server/auth.py) | ~100 | JWT + bcrypt авторизация |
| [server/yandex_disk_service.py](../server/yandex_disk_service.py) | ~200 | Серверный Яндекс.Диск |
| [server/Dockerfile](../server/Dockerfile) | ~20 | Docker образ Python 3.11 |
| [server/requirements.txt](../server/requirements.txt) | ~15 | Зависимости сервера |

## SQLAlchemy модели ([server/database.py](../server/database.py))

### Основные таблицы

#### Employee (Сотрудник)
```python
class Employee(Base):
    __tablename__ = 'employees'
    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    email = Column(String(255))
    address = Column(Text)
    birth_date = Column(Date)
    status = Column(String(20), default='active')
    position = Column(String(100))
    secondary_position = Column(String(100))
    department = Column(String(100))
    login = Column(String(100), unique=True)
    password = Column(String(255))
    role = Column(String(100))
    created_at = Column(DateTime, default=func.now())
```

#### Client (Клиент)
```python
class Client(Base):
    __tablename__ = 'clients'
    id = Column(Integer, primary_key=True)
    client_type = Column(String(50))          # 'Физическое лицо' / 'Юридическое лицо'
    full_name = Column(String(255), nullable=False)
    phone = Column(String(50))
    email = Column(String(255))
    passport_series = Column(String(10))
    passport_number = Column(String(20))
    registration_address = Column(Text)
    organization_name = Column(String(255))
    inn = Column(String(20))
    ogrn = Column(String(20))
    created_at = Column(DateTime, default=func.now())
```

#### Contract (Договор)
```python
class Contract(Base):
    __tablename__ = 'contracts'
    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey('clients.id'))
    project_type = Column(String(50))         # 'Индивидуальный' / 'Шаблонный'
    agent_type = Column(String(50))           # 'ФЕСТИВАЛЬ' / 'ПЕТРОВИЧ'
    city = Column(String(50))                 # 'СПБ' / 'МСК' / 'ВН'
    contract_number = Column(String(50))
    contract_date = Column(Date)
    address = Column(Text)
    area = Column(Float)
    total_amount = Column(Float)
    advance_payment = Column(Float)
    additional_payment = Column(Float)
    third_payment = Column(Float)
    contract_period = Column(Integer)          # дни
    status = Column(String(50), default='active')
    termination_reason = Column(Text)
    created_at = Column(DateTime, default=func.now())
```

#### CRMCard (Карточка Kanban)
```python
class CRMCard(Base):
    __tablename__ = 'crm_cards'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    column_name = Column(String(100))          # Kanban колонка
    deadline = Column(Date)
    tags = Column(Text)                        # JSON массив тегов
    is_approved = Column(Boolean, default=False)
    approval_stages = Column(Text)             # JSON
    approval_deadline = Column(Date)
    senior_manager_id = Column(Integer, ForeignKey('employees.id'))
    sdp_id = Column(Integer, ForeignKey('employees.id'))
    gap_id = Column(Integer, ForeignKey('employees.id'))
    manager_id = Column(Integer, ForeignKey('employees.id'))
    surveyor_id = Column(Integer, ForeignKey('employees.id'))
    order_position = Column(Integer)
    created_at = Column(DateTime, default=func.now())
```

#### SupervisionCard (Карточка надзора)
```python
class SupervisionCard(Base):
    __tablename__ = 'supervision_cards'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    column_name = Column(String(100))
    deadline = Column(Date)
    tags = Column(Text)
    senior_manager_id = Column(Integer, ForeignKey('employees.id'))
    dan_id = Column(Integer, ForeignKey('employees.id'))
    dan_completed = Column(Boolean, default=False)
    is_paused = Column(Boolean, default=False)
    pause_reason = Column(Text)
    paused_at = Column(DateTime)
    created_at = Column(DateTime, default=func.now())
```

#### Payment (Зарплата)
```python
class Payment(Base):
    __tablename__ = 'salaries'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    employee_id = Column(Integer, ForeignKey('employees.id'))
    payment_type = Column(String(50))
    stage_name = Column(String(255))
    amount = Column(Float)
    advance_payment = Column(Float)
    report_month = Column(String(20))          # NULL = "В работе"
    reassigned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
```

### Таблицы таймлайнов

#### ProjectTimelineEntry
```python
class ProjectTimelineEntry(Base):
    __tablename__ = 'project_timeline_entries'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id', ondelete='CASCADE'))
    stage_code = Column(String(20))            # Уникальный + contract_id
    stage_name = Column(String(255))
    stage_group = Column(String(20))           # STAGE1/STAGE2/STAGE3/START
    substage_group = Column(String(20))
    actual_date = Column(String)               # yyyy-MM-dd
    actual_days = Column(Integer)
    norm_days = Column(Integer)
    status = Column(String(20))
    executor_role = Column(String(50))         # Чертежник/Дизайнер/СДП/ГАП/Менеджер/Клиент/header
    is_in_contract_scope = Column(Boolean)
    sort_order = Column(Integer)
    raw_norm_days = Column(Float)
    cumulative_days = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

#### SupervisionTimelineEntry
```python
class SupervisionTimelineEntry(Base):
    __tablename__ = 'supervision_timeline_entries'
    id = Column(Integer, primary_key=True)
    supervision_card_id = Column(Integer, ForeignKey('supervision_cards.id', ondelete='CASCADE'))
    stage_code = Column(String(30))
    stage_name = Column(String(255))
    sort_order = Column(Integer)
    plan_date = Column(String)
    actual_date = Column(String)
    actual_days = Column(Integer)
    budget_planned = Column(Float)
    budget_actual = Column(Float)
    budget_savings = Column(Float)
    supplier = Column(String(255))
    commission = Column(Float)
    status = Column(String(20))                # Не начато/В работе/Закуплено/Доставлено/Просрочено
    notes = Column(Text)
    executor = Column(String(100))
    defects_found = Column(Integer)
    defects_resolved = Column(Integer)
    site_visits = Column(Integer)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

### Таблицы Workflow

#### StageWorkflowState
```python
class StageWorkflowState(Base):
    __tablename__ = 'stage_workflow_states'
    id = Column(Integer, primary_key=True)
    crm_card_id = Column(Integer, ForeignKey('crm_cards.id', ondelete='CASCADE'))
    stage_name = Column(String(255))
    current_substep_code = Column(String(30))
    status = Column(String(20))                # in_progress/revision/client_approval/completed
    revision_count = Column(Integer, default=0)
    revision_file_path = Column(Text)
    client_approval_started_at = Column(DateTime)
    client_approval_deadline_paused = Column(Boolean, default=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

#### StageExecutor
```python
class StageExecutor(Base):
    __tablename__ = 'stage_executors'
    id = Column(Integer, primary_key=True)
    crm_card_id = Column(Integer, ForeignKey('crm_cards.id'))
    stage_name = Column(String, nullable=False)
    executor_id = Column(Integer, ForeignKey('employees.id'), nullable=False)
    assigned_date = Column(DateTime)
    assigned_by = Column(Integer, ForeignKey('employees.id'), nullable=False)
    deadline = Column(String)
    submitted_date = Column(DateTime)
    completed = Column(Boolean, default=False)
    completed_date = Column(DateTime)
```

### Дополнительные модели (многопользовательские)

#### UserSession (user_sessions)
```python
class UserSession(Base):
    __tablename__ = 'user_sessions'
    id, employee_id (FK), session_token (UNIQUE), refresh_token (UNIQUE),
    ip_address, user_agent, computer_name, login_time, last_activity,
    logout_time, is_active (default=True)
```

#### ConcurrentEdit (concurrent_edits)
```python
class ConcurrentEdit(Base):
    __tablename__ = 'concurrent_edits'
    id, entity_type, entity_id, employee_id (FK), session_id (FK),
    locked_at (default=now), expires_at  # Авторазблокировка через 30 мин
```

#### Notification (notifications)
```python
class Notification(Base):
    __tablename__ = 'notifications'
    id, employee_id (FK), notification_type, title, message,
    related_entity_type, related_entity_id, is_read (default=False),
    created_at, read_at
```

#### ActionHistory (action_history)
```python
class ActionHistory(Base):
    __tablename__ = 'action_history'
    id, user_id (FK), action_type, entity_type, entity_id,
    description, action_date
```

#### ApprovalStageDeadline (approval_stage_deadlines)
```python
class ApprovalStageDeadline(Base):
    __tablename__ = 'approval_stage_deadlines'
    id, crm_card_id (FK), stage_name, deadline,
    is_completed (default=False), completed_date, created_at
```

#### SupervisionProjectHistory (supervision_project_history)
```python
class SupervisionProjectHistory(Base):
    __tablename__ = 'supervision_project_history'
    id, supervision_card_id (FK), entry_type, message,
    created_by (FK), created_at
```

## Полная статистика моделей

| Категория | Кол-во моделей |
|-----------|---------------|
| Многопользовательские (сессии, блокировки, уведомления) | 6 |
| Основной бизнес (clients, contracts, employees) | 3 |
| CRM Kanban (cards, executors, workflow) | 3 |
| Авторский надзор (cards, history) | 2 |
| Таблицы сроков (project, supervision) | 2 |
| Платежи и тарифы (payments, rates, salaries) | 3 |
| Файлы (project_files, file_storage) | 2 |
| История (action_history, approval_deadlines) | 2 |
| **Итого** | **~25** |

## Схема связей

```
employees ──┬── crm_cards (senior_manager_id, sdp_id, gap_id, manager_id, surveyor_id)
            ├── supervision_cards (senior_manager_id, dan_id)
            ├── payments (employee_id)
            ├── salaries (employee_id)
            ├── stage_executors (executor_id, assigned_by)
            ├── user_sessions (employee_id)
            ├── concurrent_edits (employee_id)
            ├── notifications (employee_id)
            └── action_history (user_id)

clients ──── contracts ──┬── crm_cards (contract_id)
                         ├── supervision_cards (contract_id)
                         ├── payments (contract_id)
                         ├── salaries (contract_id)
                         ├── project_timeline_entries (contract_id, CASCADE)
                         └── project_files (contract_id)

crm_cards ──┬── stage_executors (crm_card_id)
            ├── stage_workflow_states (crm_card_id, CASCADE)
            ├── payments (crm_card_id)
            └── approval_stage_deadlines (crm_card_id)

supervision_cards ──┬── supervision_timeline_entries (supervision_card_id, CASCADE)
                    ├── payments (supervision_card_id)
                    └── supervision_project_history (supervision_card_id)
```

## Pydantic схемы ([server/schemas.py](../server/schemas.py))

Основные группы схем:
- `EmployeeBase/Create/Response` — сотрудники
- `ClientBase/Create/Response` — клиенты
- `ContractBase/Create/Response` — договоры
- `CRMCardBase/Create/Update/Response` — CRM карточки
- `SupervisionCardBase/Create/Update/Response` — карточки надзора
- `PaymentBase/Create/Response` — платежи/зарплаты
- `RateBase/Create/Response` — тарифы
- `TimelineEntryUpdate` — обновление записи таймлайна
- `ProjectFileBase/Create/Response` — файлы проектов
- `StageExecutorCreate/Update` — исполнители стадий

## Зависимости сервера ([server/requirements.txt](../server/requirements.txt))

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
pydantic
python-jose[cryptography]
passlib[bcrypt]
bcrypt==3.2.2
python-multipart
requests
openpyxl
reportlab
```
