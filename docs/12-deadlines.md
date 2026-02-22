# Система дедлайнов

> Дедлайны проектов, таймлайны, рабочие дни, workflow исполнителей.

## Типы дедлайнов

### 1. Дедлайн карточки CRM

```sql
crm_cards.deadline — общий дедлайн проекта
```

Устанавливается менеджером, отображается на Kanban карточке.

### 2. Дедлайн согласования

```sql
crm_cards.approval_deadline — дедлайн согласования с клиентом
```

### 3. Дедлайн исполнителя

```sql
stage_executors.deadline — персональный дедлайн исполнителя на стадию
```

Рассчитывается автоматически:
```python
# База: actual_date предыдущего подэтапа (если есть), иначе today
base_date = prev_actual_date or today
deadline = base_date + norm_days (рабочие дни, Пн-Пт)
```

### 5. Планируемые даты (planned dates)

```python
# Рассчитываются цепочкой в TimelineWidget._calc_planned_dates()
planned[START] = START.actual_date
planned[N] = prev_date + norm_days[N]
# prev_date = actual_date (если заполнена) или planned_date предыдущего
```

Отображаются как tooltip на date_edit виджетах: "Планируемая дата: dd.MM.yyyy"

### 4. Даты в таймлайне

```sql
project_timeline_entries.actual_date — фактическая дата завершения этапа
```

## Расчёт рабочих дней ([utils/calendar_helpers.py](../utils/calendar_helpers.py))

```python
def add_working_days(start_date_str, working_days):
    """Добавляет N рабочих дней (Пн-Пт) к дате.

    Args:
        start_date_str: дата в формате 'yyyy-MM-dd'
        working_days: количество рабочих дней
    Returns:
        дата в формате 'yyyy-MM-dd'
    """
    # Пропускает субботы (5) и воскресенья (6)
    # Не учитывает государственные праздники
```

## Project Timeline — детально

### Файлы

| Файл | Назначение |
|------|-----------|
| [ui/timeline_widget.py](../ui/timeline_widget.py) | UI виджет (7 колонок) |
| [server/main.py](../server/main.py) | `build_project_timeline_template()`, `build_template_project_timeline()` |
| [server/database.py](../server/database.py) | `ProjectTimelineEntry` модель |

### Формулы расчёта

#### Коэффициент площади
```python
K = max(0, int((area - 1) // 100))
# area=50  → K=0
# area=120 → K=1
# area=250 → K=2
```

#### Базовые дни (raw_norm_days)
Каждый этап имеет базовое количество дней, зависящее от K.

#### Нормативные дни (norm_days)
```python
# Пропорциональное распределение по сроку договора
norm_days = contract_term * (raw_norm_days / sum(in_scope_raw_norm_days))

# contract_term — срок договора (все рабочие дни)
# in_scope — только этапы, входящие в scope подтипа
```

#### Фактические дни (actual_days)
```python
actual_days = networkdays(prev_date, current_date)
# Рабочие дни между последовательными actual_dates
```

### Авто-расчёт даты начала (START)

```python
START = max(contract_date, survey_date, tech_task_date)
# contract_date — дата подписания договора
# survey_date — дата замера
# tech_task_date — дата технического задания
```

### Этапы индивидуальных проектов

```
START           → ДАТА НАЧАЛА РАЗРАБОТКИ

STAGE1          → ЭТАП 1: ПЛАНИРОВОЧНОЕ РЕШЕНИЕ
  Подэтап 1.1  → Разработка 3 вар. планировок → Проверка СДП → Правка → Клиент
  Подэтап 1.2  → Финальное план. решение (1 круг правок)
  Подэтап 1.3  → Финальное план. решение (2 круг правок)

STAGE2          → ЭТАП 2: КОНЦЕПЦИЯ ДИЗАЙНА (Полный + Эскизный)
  Подэтап 2.1  → Мудборды
  Подэтап 2.2  → Визуализация 1 помещения (только Полный)
  Подэтап 2.3-2.4 → Правки визуализации (1, 2 круг)
  Подэтап 2.5  → Визуализация остальных помещений
  Подэтап 2.6-2.7 → Правки всех визуализаций (1, 2 круг)

STAGE3          → ЭТАП 3: РАБОЧАЯ ДОКУМЕНТАЦИЯ (Полный + Эскизный)
  12 шагов     → Подготовка → Разработка РД → Проверки ГАП → Клиент → Закрытие
```

### Этапы шаблонных проектов

```
START   → ДАТА НАЧАЛА РАЗРАБОТКИ

T1      → СТАДИЯ 1: ПЛАНИРОВОЧНЫЕ РЕШЕНИЯ
  T1_1  → Разработка 3 вар. → проверка Менеджером → клиент
  T1_2  → Финальное план. решение

T2      → СТАДИЯ 2: РАБОЧИЕ ЧЕРТЕЖИ
  12 шагов → Подготовка → Разработка → ГАП → Клиент → Закрытие

T3      → СТАДИЯ 3: 3Д ВИЗУАЛИЗАЦИЯ (только если подтип с визуализацией)
  6 шагов → Разработка виз → проверка Менеджером → клиент → закрытие
```

## Supervision Timeline — детально

### Файлы

| Файл | Назначение |
|------|-----------|
| [ui/supervision_timeline_widget.py](../ui/supervision_timeline_widget.py) | UI виджет (11 колонок) |
| [server/database.py](../server/database.py) | `SupervisionTimelineEntry` модель |

### Статусы стадий

| Статус | Описание |
|--------|----------|
| Не начато | Стадия ещё не началась |
| В работе | Идёт закупка |
| Закуплено | Товар закуплен |
| Доставлено | Товар доставлен |
| Просрочено | Превышен срок |

### Расчёт экономии

```python
budget_savings = budget_planned - budget_actual
# Положительное значение = экономия
# Отрицательное = перерасход
```

## API Endpoints

### Timeline

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/timeline/{contract_id}` | Записи |
| POST | `/api/timeline/{contract_id}/init` | Инициализация |
| POST | `/api/timeline/{contract_id}/reinit` | Пересоздание |
| PUT | `/api/timeline/{contract_id}/entry/{stage_code}` | Обновление |
| GET | `/api/timeline/{contract_id}/summary` | Сводка |
| GET | `/api/timeline/{contract_id}/export/excel` | Экспорт Excel |
| GET | `/api/timeline/{contract_id}/export/pdf` | Экспорт PDF |

### Supervision Timeline

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/supervision-timeline/{card_id}` | Записи |
| POST | `/api/supervision-timeline/{card_id}/init` | Инициализация |
| PUT | `/api/supervision-timeline/{card_id}/entry/{stage_code}` | Обновление |
| GET | `/api/supervision-timeline/{card_id}/summary` | Сводка |

## Ключевые методы UI

### ProjectTimelineWidget

```python
_load_data()              # загрузка entries, auto-init если пусто
populate_table()          # построение строк с заголовками, подытогами
_calc_planned_dates()     # расчёт планируемых дат цепочкой (prev + norm_days)
_recalculate_days()       # пересчёт actual_days между датами
_auto_set_start_date()    # авто-расчёт START
_on_date_changed()        # обработка QDateEdit, обновление сервера
```

### ExecutorSelectionDialog

```python
# Загружает norm_days из timeline для первого незавершённого подэтапа
# Маппинг: stage_name → stage_group (STAGE1, STAGE2, STAGE3)
# _load_timeline_norm_days():
#   - Сортирует entries по sort_order
#   - Находит prev_actual_date — actual_date предыдущего подэтапа
#   - prev_date сквозной по всем стадиям (стадии последовательны)
# Авто-расчёт: deadline = prev_actual_date + norm_days рабочих дней
#   (если prev_actual_date нет — используется today)
# Фильтрует исполнителей по должности для стадии
```
