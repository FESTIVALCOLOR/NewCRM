# CRM надзора

> Авторский надзор, закупки, бюджет, пауза/возобновление.

## Архитектура надзора

```
┌───────────────────────────────────────────────┐
│         CRMSupervisionTab                     │
│  ┌────────┐ ┌────────┐ ┌────────┐            │
│  │Колонка1│ │Колонка2│ │Колонка3│ ...         │
│  │        │ │        │ │        │             │
│  │ [Card] │ │ [Card] │ │ [Card] │             │
│  └────────┘ └────────┘ └────────┘             │
│                                               │
│  SupervisionTimelineWidget (11 колонок)       │
│  ┌─────────────────────────────────────────┐  │
│  │ Стадия | План | Факт | Дней | Бюджет...│  │
│  └─────────────────────────────────────────┘  │
└───────────────────────────────────────────────┘
```

### Файлы

| Файл | Назначение |
|------|-----------|
| [ui/crm_supervision_tab.py](../ui/crm_supervision_tab.py) | Kanban доска надзора |
| [ui/supervision_timeline_widget.py](../ui/supervision_timeline_widget.py) | Таблица закупок |
| [server/main.py](../server/main.py) | Supervision endpoints |
| [server/database.py](../server/database.py) | SupervisionCard, SupervisionTimelineEntry |

## Карточка надзора (SupervisionCard)

### Поля

```sql
id                   -- уникальный ID
contract_id          -- связь с договором
column_name          -- Kanban колонка
deadline             -- дедлайн
tags                 -- JSON теги
senior_manager_id    -- старший менеджер
dan_id               -- ДАН (дизайнер авторского надзора)
dan_completed        -- ДАН завершил работу
is_paused            -- на паузе
pause_reason         -- причина паузы
paused_at            -- дата паузы
created_at           -- дата создания
```

### Связи

```
SupervisionCard
  ├── Contract (contract_id) → Client
  ├── Employee (senior_manager_id)
  ├── Employee (dan_id)
  ├── Payments (supervision_card_id)
  └── SupervisionTimelineEntries (supervision_card_id, CASCADE)
```

## Пауза/Возобновление

### Пауза карточки

```python
# PATCH /api/supervision/cards/{id}/pause
{
    "pause_reason": "Ожидание поставки материалов"
}
# → is_paused = True, pause_reason = "...", paused_at = now()
```

### Возобновление

```python
# PATCH /api/supervision/cards/{id}/resume
# → is_paused = False, pause_reason = None, paused_at = None
```

## Таблица закупок (Supervision Timeline)

### 11 колонок

| # | Колонка | Тип данных | Описание |
|---|---------|-----------|----------|
| 1 | Стадия | String | Название стадии закупки |
| 2 | План. дата | Date | Планируемая дата |
| 3 | Факт. дата | Date | Фактическая дата |
| 4 | Дней | Integer | Фактических дней |
| 5 | Бюджет план | Float | Плановый бюджет (руб) |
| 6 | Бюджет факт | Float | Фактический бюджет (руб) |
| 7 | Экономия | Float | plan - fact (авто-расчёт) |
| 8 | Поставщик | String | Название поставщика |
| 9 | Комиссия | Float | Комиссия поставщика (%) |
| 10 | Статус | Enum | Не начато/В работе/Закуплено/Доставлено/Просрочено |
| 11 | Примечания | Text | Комментарии |

### 12 стадий закупок (автоматическая инициализация)

При создании карточки надзора автоматически создаются 12 стадий закупок для типовых этапов строительства.

### Статусы стадий

| Статус | Цвет | Описание |
|--------|------|----------|
| Не начато | Серый | Стадия ещё не началась |
| В работе | Жёлтый | Идёт процесс закупки |
| Закуплено | Синий | Товар закуплен, ожидание доставки |
| Доставлено | Зелёный | Товар доставлен |
| Просрочено | Красный | Превышен плановый срок |

### Расчёт экономии

```python
budget_savings = budget_planned - budget_actual
# > 0 → экономия (зелёный)
# < 0 → перерасход (красный)
# = 0 → точно в бюджете
```

## Дополнительные поля SupervisionTimelineEntry

```sql
executor             -- ответственный
defects_found        -- количество найденных дефектов
defects_resolved     -- количество исправленных дефектов
site_visits          -- количество визитов на объект
```

## Роли в надзоре

| Роль | Доступ |
|------|--------|
| Руководитель студии | Полный доступ |
| Старший менеджер | Полный доступ |
| ДАН | Просмотр + отметка завершения |

## API Endpoints

### Карточки надзора

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/supervision/cards` | Все карточки |
| GET | `/api/supervision/cards/{id}` | По ID |
| POST | `/api/supervision/cards` | Создать |
| PUT | `/api/supervision/cards/{id}` | Обновить |
| PATCH | `/api/supervision/cards/{id}` | Частично |
| DELETE | `/api/supervision/cards/{id}` | Удалить |
| PATCH | `/api/supervision/cards/{id}/pause` | Приостановить |
| PATCH | `/api/supervision/cards/{id}/resume` | Возобновить |

### Таблица сроков надзора

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/supervision-timeline/{card_id}` | Записи |
| POST | `/api/supervision-timeline/{card_id}/init` | Инициализировать |
| PUT | `/api/supervision-timeline/{card_id}/entry/{stage_code}` | Обновить |
| GET | `/api/supervision-timeline/{card_id}/summary` | Сводка |
| GET | `/api/supervision-timeline/{card_id}/export/excel` | Excel |
| GET | `/api/supervision-timeline/{card_id}/export/pdf` | PDF |
