# CRM интеграция

> Kanban доска, карточки, стадии, исполнители, Drag & Drop, workflow.

## Архитектура CRM

```
┌──────────────────────────────────────────────────┐
│                CRMTab (17K+ строк)               │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │
│  │ Новый  │ │В ожида-│ │Стадия 1│ │Стадия 2│ ...│
│  │ заказ  │ │нии     │ │        │ │        │    │
│  │        │ │        │ │        │ │        │    │
│  │ [Card] │ │ [Card] │ │ [Card] │ │ [Card] │    │
│  │ [Card] │ │        │ │ [Card] │ │        │    │
│  └────────┘ └────────┘ └────────┘ └────────┘    │
│  DraggableListWidget (Drag & Drop)               │
└──────────────────────────────────────────────────┘
       │                        │
       ▼                        ▼
   DataAccess              SyncManager
   (API → DB)           (обновления 30с)
```

### Файлы

| Файл | Строк | Назначение |
|------|-------|-----------|
| [ui/crm_tab.py](../ui/crm_tab.py) | 17K+ | Kanban доска, все диалоги |
| [server/main.py](../server/main.py) | — | CRM endpoints |
| [utils/data_access.py](../utils/data_access.py) | — | CRUD операции |

## Kanban колонки

### Индивидуальные проекты (6 колонок)

| # | Колонка | Описание |
|---|---------|----------|
| 1 | Новый заказ | Только что созданные проекты |
| 2 | В ожидании | Ожидание начала работы |
| 3 | Стадия 1: планировочные решения | Активная работа |
| 4 | Стадия 2: концепция дизайна | Активная работа |
| 5 | Стадия 3: рабочие чертежи | Активная работа |
| 6 | Выполненный проект | Завершённые проекты |

### Шаблонные проекты (5 колонок)

| # | Колонка | Описание |
|---|---------|----------|
| 1 | Новый заказ | Только что созданные |
| 2 | В ожидании | Ожидание начала |
| 3 | Стадия 1: планировочные решения | Активная работа |
| 4 | Стадия 2: рабочие чертежи | Активная работа |
| 5 | Выполненный проект | Завершённые |

## CRM карточка (CRMCard)

### Поля

```sql
id, contract_id, column_name, deadline, tags,
is_approved, approval_stages, approval_deadline,
senior_manager_id, sdp_id, gap_id, manager_id, surveyor_id,
order_position, created_at
```

### Связанные сущности

```
CRMCard
  ├── Contract (contract_id) → Client
  ├── Employees (senior_manager, sdp, gap, manager, surveyor)
  ├── StageExecutors (назначенные исполнители)
  ├── StageWorkflowStates (состояния workflow)
  ├── Payments (crm_card_id)
  ├── ProjectFiles (через contract_id)
  └── ProjectTimelineEntries (через contract_id)
```

## Drag & Drop

### Механизм

```python
class DraggableListWidget(QListWidget):
    # Поддерживает перетаскивание карточек между колонками
    # При drop:
    #   1. Определяет целевую колонку
    #   2. Обновляет column_name через API
    #   3. Пересчитывает order_position
    #   4. Обновляет UI
```

### Ограничения перемещения

- Не все колонки доступны для перемещения (зависит от роли)
- "Выполненный проект" — только для завершённых
- Обратное перемещение из "Выполненный" — с подтверждением

## Исполнители стадий (Stage Executors)

### Назначение

```python
# ExecutorSelectionDialog
1. Выбор стадии (Stage 1, 2, 3)
2. Выбор исполнителя (фильтр по должности)
3. Авто-расчёт дедлайна: assigned_date + norm_days рабочих дней
4. API: POST /api/crm/cards/{card_id}/stage-executor
```

### Маппинг ролей на стадии

| Стадия | Роли исполнителей |
|--------|------------------|
| Стадия 1 | Дизайнер, СДП |
| Стадия 2 | Дизайнер |
| Стадия 3 | Чертёжник, ГАП |

### StageExecutor модель

```sql
id, crm_card_id, stage_name, executor_id,
assigned_date, assigned_by, deadline,
submitted_date, completed, completed_date
```

## Workflow (Рабочий процесс)

### Полный цикл

```
НАЗНАЧЕНИЕ → РАБОТА → СДАЧА → ПРОВЕРКА → ПРИНЯТИЕ/ИСПРАВЛЕНИЕ → КЛИЕНТ
```

### Состояния StageWorkflowState

| Статус | Описание |
|--------|----------|
| `in_progress` | Идёт работа |
| `revision` | На исправлении |
| `client_approval` | На согласовании у клиента |
| `completed` | Завершено |

### Кнопки и видимость

| Кнопка | Роль | Условие |
|--------|------|---------|
| "Сдать работу" | Дизайнер/Чертёжник | `completed == False` |
| "Ожидайте проверку" | Дизайнер/Чертёжник | `completed == True` (disabled) |
| "Принять работу" | Менеджеры | `completed == True` |
| "На исправление" | Менеджеры | `completed == True` |
| "Клиенту на согласование" | Менеджеры | После принятия |
| "Клиент согласовал" | Менеджеры | После отправки клиенту |

## Согласование (Approval)

### approval_stages

JSON массив стадий согласования:

```json
[
    {"stage": "Планировочное решение", "status": "approved", "date": "2026-01-15"},
    {"stage": "Концепция дизайна", "status": "pending", "date": null},
    {"stage": "Рабочие чертежи", "status": "not_started", "date": null}
]
```

### Процесс согласования

1. Менеджер отправляет стадию на согласование клиенту
2. `client_approval_started_at` фиксирует время
3. Клиент одобряет → `is_approved = True` для стадии
4. Дедлайн карточки может быть приостановлен (`client_approval_deadline_paused`)

## API Endpoints

### CRM карточки

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/crm/cards` | Все карточки |
| GET | `/api/crm/cards/{id}` | По ID |
| POST | `/api/crm/cards` | Создать |
| PUT | `/api/crm/cards/{id}` | Обновить |
| PATCH | `/api/crm/cards/{id}` | Частично |
| DELETE | `/api/crm/cards/{id}` | Удалить |
| GET | `/api/crm/cards/by-type/{type}` | По типу |
| PATCH | `/api/crm/cards/{id}/column` | Переместить |
| PATCH | `/api/crm/cards/{id}/order` | Порядок |

### Workflow

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/crm/cards/{id}/workflow/submit` | Сдать работу |
| POST | `/api/crm/cards/{id}/workflow/accept` | Принять |
| POST | `/api/crm/cards/{id}/workflow/reject` | На исправление |
| POST | `/api/crm/cards/{id}/workflow/client-send` | Клиенту |
| POST | `/api/crm/cards/{id}/workflow/client-ok` | Клиент OK |
| GET | `/api/crm/cards/{id}/workflow/state` | Состояние |

### Исполнители

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/crm/cards/{id}/stage-executor` | Назначить |
| PATCH | `/api/crm/cards/{id}/stage-executor/{stage}` | Обновить |
| PATCH | `/api/crm/cards/{id}/stage-executor/{stage}/complete` | Завершить |
| DELETE | `/api/crm/stage-executors/{id}` | Удалить |
