# Система оплат

> Платежи, тарифы, расчёт сумм, переназначение, зарплатные отчёты.

## Архитектура платежей

```
┌──────────────┐     calculate_payment     ┌──────────────┐
│  SalariesTab │ ─────────────────────── → │ server/main  │
│  (PyQt5)     │ ← ─────────────────────── │ .py          │
│              │     amount, breakdown      │              │
└──────────────┘                            └──────────────┘
       │                                           │
       ▼                                           ▼
  DataAccess                                   PostgreSQL
  (API → DB)                                   salaries table
                                               rates table
```

### Файлы

| Файл | Назначение |
|------|-----------|
| [ui/salaries_tab.py](../ui/salaries_tab.py) | UI управления платежами |
| [server/main.py](../server/main.py) | Endpoints платежей и расчёта |
| [ui/rates_dialog.py](../ui/rates_dialog.py) | Диалог управления тарифами |
| [database/db_manager.py](../database/db_manager.py) | Локальные CRUD операции |

## Ключевые правила

### 1. CRM vs Надзор

| Тип | Поле | Описание |
|-----|------|----------|
| CRM платёж | `crm_card_id` | Привязка к CRM карточке |
| Платёж надзора | `supervision_card_id` | Привязка к карточке надзора |

### 2. Статус "В работе"

```python
# report_month = NULL означает "В работе" (не закрыт в отчёте)
# report_month = "2026-02" означает платёж закрыт в феврале 2026
```

### 3. Переназначение

При переназначении исполнителя на другого:
1. Старый платёж получает `reassigned = True`
2. Создаётся **новый** платёж для нового исполнителя
3. При поиске старых платежей — проверять флаг `reassigned`

### 4. Расчёт суммы

Расчёт **ВСЕГДА** через серверный endpoint `POST /api/payments/calculate`:

```python
# Клиент отправляет:
{
    "contract_id": 42,
    "employee_id": 5,
    "stage_name": "Стадия 1: планировочные решения",
    "payment_type": "Основной платеж"
}

# Сервер возвращает:
{
    "amount": 15000.0,
    "breakdown": {
        "rate": 500,
        "area": 120,
        "coefficient": 1.0
    }
}
```

## Схема таблицы salaries

```sql
CREATE TABLE salaries (
    id SERIAL PRIMARY KEY,
    contract_id INTEGER REFERENCES contracts(id),
    employee_id INTEGER REFERENCES employees(id),
    payment_type VARCHAR(50),          -- Аванс / Основной платеж / Оплата согласования
    stage_name VARCHAR(255),           -- название стадии
    amount FLOAT,                      -- сумма платежа
    advance_payment FLOAT,             -- сумма аванса
    report_month VARCHAR(20),          -- NULL = "В работе", "2026-02" = закрыт
    reassigned BOOLEAN DEFAULT FALSE,  -- переназначен ли
    crm_card_id INTEGER,               -- привязка к CRM карточке
    supervision_card_id INTEGER,       -- привязка к карточке надзора
    created_at TIMESTAMP DEFAULT NOW()
);
```

## Тарифы (Rates)

### Тарифы CRM

```python
# Тарифы CRM зависят от:
# - Роли исполнителя (executor_rate / manager_rate)
# - Типа проекта (Индивидуальный / Шаблонный)
# - Стадии (Стадия 1, 2, 3)
# - Площади объекта (area)
```

### Тарифы надзора

```python
# Тарифы надзора:
# - role + rate_per_m2
# - НЕ executor_rate / manager_rate
```

## API Endpoints

| Метод | Путь | Описание |
|-------|------|----------|
| GET | `/api/payments` | Все платежи |
| GET | `/api/payments/{id}` | Платёж по ID |
| POST | `/api/payments` | Создать платёж |
| PUT | `/api/payments/{id}` | Обновить |
| DELETE | `/api/payments/{id}` | Удалить |
| GET | `/api/payments/contract/{id}` | Платежи по договору |
| GET | `/api/payments/employee/{id}` | Платежи сотрудника |
| POST | `/api/payments/calculate` | Расчёт суммы |
| GET | `/api/payments/report` | Зарплатный отчёт |

## Зарплатный отчёт

Отчёт группирует платежи по `report_month`:
- `report_month = NULL` → раздел "В работе"
- `report_month = "2026-02"` → раздел "Февраль 2026"

### Фильтры

- По сотруднику
- По отчётному месяцу
- По типу платежа
- По договору

## Типы платежей

```python
PAYMENT_TYPES = [
    'Аванс',                    # предоплата
    'Основной платеж',          # основная сумма
    'Оплата согласования',      # за этап согласования
]
```
