# Бекенд проекта

> FastAPI сервер, SQLAlchemy модели, Pydantic схемы, PostgreSQL.
> Последнее обновление: 2026-03-29

## Архитектура бекенда

```
┌───────────────────────────────────────────────────────┐
│                 Docker Container: api                 │
│                                                       │
│  ┌──────────┐  ┌────────────┐  ┌────────────────────┐ │
│  │ FastAPI   │  │ SQLAlchemy │  │ Pydantic           │ │
│  │ main.py   │→ │ database   │→ │ schemas.py         │ │
│  │           │  │ .py        │  │ 30+ схем           │ │
│  └──────────┘  └────────────┘  └────────────────────┘ │
│       │              │                                │
│       ▼              ▼                                │
│  ┌──────────┐  ┌─────────────────────────────────┐   │
│  │ auth.py   │  │ services/                       │   │
│  │ JWT/bcrypt│  │ notification_service            │   │
│  └──────────┘  │ timeline_service, kpi_calculator │   │
│                │ deadline_checker, access_filter  │   │
│                └─────────────────────────────────┘   │
└───────────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────┐
│  PostgreSQL 15   │
│  (Docker: 5432)  │
│  interior_studio │
│  _crm            │
└──────────────────┘
```

## Файлы бекенда

| Файл | Назначение |
|------|-----------|
| [server/main.py](../server/main.py) | FastAPI приложение, регистрация роутеров, middleware |
| [server/database.py](../server/database.py) | SQLAlchemy модели (27+ таблиц) |
| [server/schemas.py](../server/schemas.py) | Pydantic DTO (30+ схем) |
| [server/auth.py](../server/auth.py) | JWT + bcrypt авторизация |
| [server/permissions.py](../server/permissions.py) | Проверка прав по ролям |
| [server/constants.py](../server/constants.py) | Системные константы (роли, статусы) |
| [server/rate_limit.py](../server/rate_limit.py) | Rate limiting (slowapi) |
| [server/yandex_disk_service.py](../server/yandex_disk_service.py) | Интеграция Яндекс.Диск |
| [server/telegram_service.py](../server/telegram_service.py) | Telegram Bot API (aiogram) |
| [server/email_service.py](../server/email_service.py) | SMTP invite-письма |
| [server/pdf_helper.py](../server/pdf_helper.py) | Генерация PDF (reportlab) |
| [server/Dockerfile](../server/Dockerfile) | Docker образ Python 3.11 |
| [server/requirements.txt](../server/requirements.txt) | Зависимости сервера |

## Роутеры (server/routers/)

28 роутеров — все подключаются в `main.py` через `app.include_router()`:

| Роутер | Prefix | Назначение |
|--------|--------|-----------|
| auth_router | /api/auth | Вход, refresh, logout, me |
| employees_router | /api/employees | CRUD сотрудников |
| clients_router | /api/clients | CRUD клиентов |
| contracts_router | /api/contracts | CRUD договоров, акты |
| crm_router | /api/crm | Карточки, стадии, workflow, исполнители |
| supervision_router | /api/supervision | Карточки надзора, пауза/возобновление |
| **supervision_visits_router** | /api/supervision | Выезды, дефекты, итого, экспорт PDF/Excel |
| supervision_timeline_router | /api/supervision-timeline | Таблица закупок надзора |
| payments_router | /api/payments | CRUD платежей, расчёт, пометка оплаченным |
| salaries_router | /api/salaries | Зарплатные записи |
| rates_router | /api/rates | Тарифы и прайс-листы |
| timeline_router | /api/timeline | Таблица сроков проекта |
| files_router | /api/files | Upload/download, ЯД интеграция |
| notifications_router | /api/notifications | Уведомления, Web Push (VAPID), подписки |
| messenger_router | /api/messenger | Чаты, сообщения, Telegram интеграция |
| dashboard_router | /api/dashboard | KPI срезы данных |
| statistics_router | /api/statistics | Отчёты, аналитика |
| reports_router | /api/reports | Генерация отчётов, экспорт Excel |
| employee_analytics_router | /api/employee-analytics | Аналитика сотрудников |
| action_history_router | /api/action-history | Аудит всех операций |
| project_templates_router | /api/project-templates | Шаблоны проектов |
| norm_days_router | /api/norm-days | Рабочие дни, производственный календарь |
| locks_router | /api/locks | Блокировки для совместного редактирования |
| sync_router | /api/sync | Синхронизация desktop → server |
| websocket_router | /ws | WebSocket real-time подписки |
| heartbeat_router | /api/heartbeat | Проверка здоровья и активности сессии |
| agents_router | /api/agents | Справочник агентов (ФЕСТИВАЛЬ, ПЕТРОВИЧ) |
| cities_router | /api/cities | Справочник городов |
| **survey_router** | /api/surveys | Опросы клиентов (Яндекс Формы интеграция) |

### Ключевые правила роутеров

- **Статические endpoints ПЕРЕД динамическими** — `GET /summary` до `GET /{id}`
- `require_permission()` — декоратор проверки прав доступа
- `get_current_user` через `Depends` — JWT верификация

## Сервисы (server/services/)

| Сервис | Файл | Назначение |
|--------|------|-----------|
| NotificationService | notification_service.py | Отправка email/push/Telegram уведомлений |
| NotificationDispatcher | notification_dispatcher.py | Маршрутизация уведомлений по типам и ролям |
| TimelineService | timeline_service.py | Построение и синхронизация таблицы сроков |
| KPICalculator | kpi_calculator.py | Расчёт KPI (выполнение, просрочки) |
| KPISnapshot | kpi_snapshot.py | Снимки KPI для отчётов |
| DeadlineChecker | deadline_checker.py | Проверка просроченных дедлайнов |
| AccessFilter | access_filter.py | Фильтрация данных по ролям |
| DateHelpers | date_helpers.py | Рабочие дни, праздники РФ, расчёты дат |

## SQLAlchemy модели (server/database.py)

### Основные бизнес-модели

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

#### SupervisionVisit (Выезд надзора) — новая модель
```python
class SupervisionVisit(Base):
    __tablename__ = 'supervision_visits'
    id = Column(Integer, primary_key=True)
    supervision_card_id = Column(Integer, ForeignKey('supervision_cards.id', ondelete='CASCADE'))
    stage_name = Column(String(255))           # Название стадии (выпадающий список)
    visit_date = Column(Date)
    executor_name = Column(String(255))        # ФИО исполнителя
    notes = Column(Text)
    defects_found = Column(Integer, default=0)
    defects_resolved = Column(Integer, default=0)
    yandex_folder_path = Column(String(512))   # Папка на ЯД для файлов выезда
    voice_url = Column(String(512))            # Путь голосовой заметки на ЯД
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

#### ClientSurvey (Опрос клиента) — новая модель
```python
class ClientSurvey(Base):
    __tablename__ = 'client_surveys'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id'))
    survey_token = Column(String(64), unique=True)  # уникальная ссылка
    sent_at = Column(DateTime)
    completed_at = Column(DateTime)
    responses = Column(Text)                   # JSON ответы из Яндекс Форм
    overall_score = Column(Float)              # Средняя оценка
    created_at = Column(DateTime, default=func.now())
```

### Таблицы таймлайнов

#### ProjectTimelineEntry
```python
class ProjectTimelineEntry(Base):
    __tablename__ = 'project_timeline_entries'
    id = Column(Integer, primary_key=True)
    contract_id = Column(Integer, ForeignKey('contracts.id', ondelete='CASCADE'))
    stage_code = Column(String(20))
    stage_name = Column(String(255))
    stage_group = Column(String(20))           # STAGE1/STAGE2/STAGE3/START
    substage_group = Column(String(20))
    actual_date = Column(String)               # yyyy-MM-dd
    actual_days = Column(Integer)
    norm_days = Column(Integer)
    status = Column(String(20))
    executor_role = Column(String(50))
    is_in_contract_scope = Column(Boolean)
    sort_order = Column(Integer)
    raw_norm_days = Column(Float)
    cumulative_days = Column(Float)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())
```

#### SupervisionTimelineEntry (Таблица закупок)
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
    # status: 'in_progress' | 'revision' | 'client_approval' | 'completed'
    id, crm_card_id (FK CASCADE), stage_name, current_substep_code,
    status, revision_count, revision_file_path,
    client_approval_started_at, client_approval_deadline_paused,
    created_at, updated_at
```

#### StageExecutor
```python
class StageExecutor(Base):
    __tablename__ = 'stage_executors'
    id, crm_card_id (FK), stage_name, executor_id (FK),
    assigned_date, assigned_by (FK), deadline (String),
    submitted_date, completed (Boolean), completed_date
```

### Многопользовательские модели

| Модель | Таблица | Назначение |
|--------|---------|-----------|
| UserSession | user_sessions | Сессии, refresh токены, IP, компьютер |
| ConcurrentEdit | concurrent_edits | Блокировки (авторазблокировка 30 мин) |
| Notification | notifications | In-app уведомления |
| ActionHistory | action_history | Аудит всех операций |
| ApprovalStageDeadline | approval_stage_deadlines | Дедлайны стадий согласования |
| SupervisionProjectHistory | supervision_project_history | История проекта надзора |

### Полная статистика моделей

| Категория | Кол-во |
|-----------|--------|
| Основной бизнес (employees, clients, contracts) | 3 |
| CRM Kanban (cards, executors, workflow states) | 3 |
| Авторский надзор (cards, visits, history) | 3 |
| Таблицы сроков (project, supervision) | 2 |
| Платежи и тарифы (payments, rates, salaries) | 3 |
| Файлы (project_files, file_storage) | 2 |
| Многопользовательские (sessions, locks, notifications, history) | 4 |
| Дополнительные (approval_deadlines, surveys, project_templates) | 3 |
| **Итого** | **~27** |

## Схема связей

```
employees ──┬── crm_cards (senior_manager_id, sdp_id, gap_id, manager_id, surveyor_id)
            ├── supervision_cards (senior_manager_id, dan_id)
            ├── payments (employee_id)
            ├── stage_executors (executor_id, assigned_by)
            ├── user_sessions (employee_id)
            ├── concurrent_edits (employee_id)
            ├── notifications (employee_id)
            └── action_history (user_id)

clients ──── contracts ──┬── crm_cards (contract_id)
                         ├── supervision_cards (contract_id)
                         ├── payments (contract_id)
                         ├── project_timeline_entries (contract_id, CASCADE)
                         ├── project_files (contract_id)
                         └── client_surveys (contract_id)

crm_cards ──┬── stage_executors (crm_card_id)
            ├── stage_workflow_states (crm_card_id, CASCADE)
            └── approval_stage_deadlines (crm_card_id)

supervision_cards ──┬── supervision_timeline_entries (supervision_card_id, CASCADE)
                    ├── supervision_visits (supervision_card_id, CASCADE)
                    └── supervision_project_history (supervision_card_id)
```

## Миграции (Alembic)

13 миграций в `server/alembic/versions/`:

| Версия | Изменение |
|--------|-----------|
| 9b43f... | Baseline: полная начальная схема |
| add_agent_type_to_norm_days | Поле agent_type в norm_days |
| add_supervision_visits | Таблица supervision_visits |
| add_studio_director_id | studio_director_id в employees |
| add_employee_name_to_payments | employee_name в payments |
| add_notifications_system | Таблица notifications |
| add_workflow_substage_group | substage_group в timeline entries |
| add_notification_project_type_filters | Фильтры типов проектов в уведомлениях |
| add_employee_payment_fields | Дополнительные поля payments |
| add_additional_agreement_fields | Поля доп. соглашений в contracts |
| add_script_name_field | script_name в messenger chats |
| reseed_scripts_with_names | Обновление данных скриптов |
| add_revision_history | Таблица revision_history |

## Pydantic схемы (server/schemas.py)

Основные группы схем:
- `EmployeeBase/Create/Response` — сотрудники
- `ClientBase/Create/Response` — клиенты
- `ContractBase/Create/Response` — договоры
- `CRMCardBase/Create/Update/Response` — CRM карточки
- `SupervisionCardBase/Create/Update/Response` — карточки надзора
- `SupervisionVisitCreate/Update/Response` — выезды надзора (новые)
- `PaymentBase/Create/Response` — платежи
- `RateBase/Create/Response` — тарифы
- `TimelineEntryUpdate` — обновление записи таймлайна
- `ProjectFileBase/Create/Response` — файлы проектов
- `StageExecutorCreate/Update` — исполнители стадий

## Зависимости сервера (server/requirements.txt)

```
fastapi
uvicorn[standard]
sqlalchemy
psycopg2-binary
pydantic
python-jose[cryptography]
bcrypt==4.2.1
python-multipart
requests
openpyxl
reportlab
pywebpush          # Web Push уведомления
aiogram            # Telegram Bot
```
