# Research: Обновление страницы "Отчёты и Статистика"

## 1. Архитектура (текущее состояние)

### 1.1 Структура ReportsTab

Файл: `ui/reports_tab.py` (869 строк)

ReportsTab — QWidget, принимает `employee` и `api_client`. Создаёт `DatabaseManager` и `DataAccess` напрямую в конструкторе.

**Компоненты вкладки:**

```
ReportsTab
├── header_layout — заголовок + кнопка "Экспорт в PDF"
├── filters_group — QGroupBox (свёртываемые фильтры)
│   ├── toggle_filters_btn — кнопка развернуть/свернуть
│   ├── year_combo — ComboBox, годы 2020..2040
│   ├── quarter_combo — ComboBox, Все/Q1/Q2/Q3/Q4
│   ├── month_combo — ComboBox, Все/Январь..Декабрь
│   ├── agent_type_combo — ComboBox, из DataAccess.get_agent_types()
│   └── city_combo — ComboBox, из DataAccess.get_cities()
└── tabs — QTabWidget
    ├── Вкладка "Индивидуальные проекты" — create_statistics_tab('Индивидуальный')
    │   ├── Диаграмма: Распределение по городам (matplotlib pie)
    │   └── Диаграмма: Распределение по типам агентов (matplotlib pie)
    ├── Вкладка "Шаблонные проекты" — create_statistics_tab('Шаблонный')
    │   ├── Диаграмма: Распределение по городам (matplotlib pie)
    │   └── Диаграмма: Распределение по типам агентов (matplotlib pie)
    ├── Вкладка "Авторский надзор" — create_supervision_statistics_tab()
    │   ├── Диаграмма: Распределение по городам (matplotlib pie)
    │   └── Диаграмма: Распределение по типам агентов (matplotlib pie)
    └── Вкладка "Аналитика" — _create_analytics_tab()
        ├── ProjectTypePieChart — пирог: Индивидуальные/Шаблонные/Надзор
        ├── FunnelBarChart — горизонтальный бар: воронка по Kanban-колонкам
        └── ExecutorLoadChart — горизонтальный бар: нагрузка исполнителей
```

**Ленивая загрузка:** `ensure_data_loaded()` вызывается при первом показе вкладки, устанавливает `_data_loaded = True`, затем `load_all_statistics()`.

**Кэш аналитики:** `_analytics_data_hash` — md5 от строки параметров фильтрации. При повторном вызове с теми же параметрами перерисовка не происходит.

**Фильтры взаимоисключающие:** квартал и месяц — нельзя выбрать оба одновременно. При выборе квартала сбрасывается месяц, и наоборот.

**PDF-экспорт:**

- Открывает диалог выбора имени файла и папки
- Строит QTextDocument с логотипом, заголовком, таблицей 4×7
- Колонки таблицы: Тип, Всего, Площадь, Активные, Выполненные, Расторгнуто, Просрочки
- Три строки данных: Индивидуальные, Шаблонные, Авторский надзор

**Важное замечание:** В комментариях кода есть фраза "ТОЛЬКО ДИАГРАММЫ — карточки статистики показываются в дашборде main_window". То есть ReportsTab намеренно не содержит MetricCard-карточки — они размещены в `ReportsStatisticsDashboard` в шапке main_window.

### 1.2 Система дашбордов

Файл: `ui/dashboard_widget.py` (503 строки)

**DashboardWidget** — базовый QWidget для дашбордов:
- Фиксированная высота 105px (одна строка карточек)
- Использует QGridLayout для карточек
- Метод `add_metric_card(row, col, ...)` — добавляет MetricCard в grid
- Метод `update_metric(object_name, value)` — обновляет значение карточки
- Метод `refresh()` — вызывает `load_data()`
- Метод `get_years()` — динамический список годов через DataAccess.get_contract_years()

**MetricCard** — QGroupBox, высота 95px:
- SVG-иконка слева (ColoredSvgWidget, 36px, цвет из border_color)
- Заголовок (10px, цвет border_color)
- Значение (22px, bold, цвет border_color)
- Метка выбранного фильтра (9px, italic, скрыта по умолчанию)
- Опциональные FilterButton-кнопки справа (24×24px, вертикально)

**FilterButton** — QPushButton с QMenu:
- Типы фильтров: `agent`, `year`, `month`, `project_type`
- Иконки: user.svg / calendar.svg / clock.svg / briefcase.svg
- Эмитирует `filter_changed(str)` при выборе
- Метод `connect_filter(filter_type, callback)` для подключения обработчиков

**DashboardWidget** поддерживает двухстрочный layout через параметры `row` и `col` в `add_metric_card`.

**ReportsStatisticsDashboard** (в `ui/dashboards.py`, строки 1462–1624):

Строка 0 (6 карточек):
- `total_clients` — Всего клиентов (#2196F3)
- `total_individual_clients` — Физические лица (#4CAF50)
- `total_legal_clients` — Юридические лица (#FF9800)
- `individual_orders` — Индивидуальные заказы (#F57C00)
- `template_orders` — Шаблонные заказы (#C62828)
- `supervision_orders` — Надзоры (#388E3C)

Строка 1 (6 карточек):
- `crm_individual_active` — СРМ Индивидуальные (активные) (#F57C00)
- `crm_template_active` — СРМ Шаблонные (активные) (#C62828)
- `crm_supervision_active` — СРМ Надзор (активные) (#388E3C)
- `crm_individual_archive` — СРМ Индивидуальные (архив) (#9E9E9E)
- `crm_template_archive` — СРМ Шаблонные (архив) (#9E9E9E)
- `crm_supervision_archive` — СРМ Надзор (архив) (#9E9E9E)

`load_data()` вызывает:
- `data_access.get_clients_dashboard_stats()` — для клиентских метрик
- `data_access.get_contracts_dashboard_stats()` — для счётчиков договоров
- `data_access.get_crm_dashboard_stats(project_type=...)` — 3 раза (Инд/Шаб/Надзор)

**Фильтры в ReportsStatisticsDashboard отсутствуют** — все карточки без FilterButton. Нет ни года, ни агента, ни города.

### 1.3 Система графиков

Файл: `ui/chart_widget.py` (184 строки)

**ChartBase** — базовый QWidget:
- Использует matplotlib FigureCanvasQTAgg
- `Figure(figsize=(4,3), dpi=100)`, фон `#F8F9FA`
- Метод `_finalize()`: `figure.tight_layout(pad=1.5)` + `canvas.draw()`

**FunnelBarChart(ChartBase):**
- `set_data(funnel_dict)` — `{column_name: count, ...}`
- Горизонтальные столбцы, отсортированные по возрастанию
- Цвета: ротируются из массива 10 цветов
- Значения отображаются правее столбца

**ExecutorLoadChart(ChartBase):**
- `set_data(executor_list)` — `[{"name": ..., "active_stages": ...}, ...]`
- Горизонтальные столбцы, цвет зависит от нагрузки:
  - ≥8 стадий → красный `#E74C3C` (перегрузка)
  - ≥5 стадий → оранжевый `#F39C12`
  - <5 стадий → зелёный `#27AE60`

**ProjectTypePieChart(ChartBase):**
- `set_data(individual_count, template_count, supervision_count=0)`
- Цвета: `#ffd93c` (инд), `#F39C12` (шаб), `#27AE60` (надзор)
- Подписи включают количество в скобках

**Круговые диаграммы в ReportsTab** — создаются через `create_chart()`:
- Используют `plt.Figure` напрямую (не ChartBase)
- Метод `update_pie_chart(chart_name, data)` — перерисовывает по данным `{name: count}`
- Ищет canvas через `findChild(FigureCanvas, 'canvas')`

### 1.4 Система фильтрации

ReportsTab имеет **глобальные фильтры** в шапке, влияющие на все 4 вкладки сразу:

| Фильтр | Виджет | Источник данных | Логика |
|---|---|---|---|
| Год | CustomComboBox | 2020–2040 хардкод | `contract_date` starts with `YYYY` |
| Квартал | CustomComboBox | Все/Q1/Q2/Q3/Q4 | Месяцы 1–3 / 4–6 / 7–9 / 10–12 |
| Месяц | CustomComboBox | Все / Янв..Дек | `contract_date[5:7]` == MM |
| Тип агента | CustomComboBox | `DataAccess.get_agent_types()` | `agent_type` поле договора |
| Город | CustomComboBox | `DataAccess.get_cities()` | `city` поле договора |

Квартал и месяц взаимоисключающие (при выборе одного сбрасывается другой через `blockSignals`).

Метод `reset_filters()` сбрасывает всё в "Все" (год — текущий).

Данные в ReportsStatisticsDashboard (в шапке main_window) НЕ реагируют на фильтры ReportsTab. Дашборд обновляется только при вызове `refresh()` при переключении на вкладку.

---

## 2. Паттерны

### 2.1 Загрузка данных

**DataAccess** — универсальный фасад (`utils/data_access.py`, 3280 строк):
- Конструктор: `DataAccess(api_client=None, db=None)`
- `_should_use_api()` → `True` если `api_client` не None и `is_online`
- Паттерн: API-first с fallback на локальную SQLite БД
- Для чистых read-операций: сначала `api_client.method()`, при ошибке — `db.method()`
- Для write-операций: сначала локально, затем API (или в offline-очередь)

Методы, непосредственно используемые в ReportsTab/ReportsStatisticsDashboard:

| Метод | Куда идёт | Что возвращает |
|---|---|---|
| `get_clients_dashboard_stats(**kwargs)` | `GET /api/dashboard/clients` | `{total_clients, total_individual, total_legal, clients_by_year, agent_clients_total, agent_clients_by_year}` |
| `get_contracts_dashboard_stats(**kwargs)` | `GET /api/dashboard/contracts` | `{individual_orders, individual_area, template_orders, template_area, agent_orders_by_year, agent_area_by_year}` |
| `get_crm_dashboard_stats(**kwargs)` | `GET /api/dashboard/crm?project_type=...` | `{total_orders, total_area, active_orders, archive_orders, agent_active_orders, agent_archive_orders}` |
| `get_project_statistics(**kwargs)` | `GET /api/statistics/projects?project_type=...` | `{total_orders, total_area, active, completed, cancelled, overdue, by_cities, by_agents, by_stages}` |
| `get_supervision_statistics_report(**kwargs)` | `GET /api/statistics/supervision` | `{total_orders, total_area, active, completed, cancelled, overdue, by_cities, by_agents, by_stages}` |
| `get_funnel_statistics(year, project_type)` | `GET /api/statistics/funnel` | `{funnel: {column_name: count}, total: int}` |
| `get_executor_load(year, month)` | `GET /api/statistics/executor-load` | `[{name, active_stages}, ...]` |
| `get_agent_types()` | `GET /api/dashboard/agent-types` | `[str, ...]` |
| `get_cities()` | `GET /api/statistics/cities` | `[str, ...]` |
| `get_all_contracts()` | `GET /api/contracts` (с пагинацией) | `[{contract_dict}, ...]` |

### 2.2 Существующие метрики

**Клиенты:**
- Всего клиентов (физ + юр)
- Физические лица (`client_type == 'Физическое лицо'`)
- Юридические лица (`client_type == 'Юридическое лицо'`)
- Клиенты за год (distinct client_id по contract_date)
- Клиенты агента всего / за год

**Договора (из `/api/dashboard/contracts`):**
- Всего индивидуальных заказов
- Площадь индивидуальных
- Всего шаблонных заказов
- Площадь шаблонных
- Заказы агента за год
- Площадь агента за год

**CRM карточки (из `/api/dashboard/crm`):**
- Всего заказов и площадь (из contracts)
- Активные в СРМ (не СДАН/РАСТОРГНУТ/АВТ.НАДЗОР)
- Архивные (СДАН/РАСТОРГНУТ/АВТ.НАДЗОР)
- Активные агента
- Архивные агента

**Статистика проектов (из `/api/statistics/projects`):**
- total_orders — всего заказов
- total_area — суммарная площадь
- active — активные (не СДАН/РАСТОРГНУТ/АВТ.НАДЗОР)
- completed — выполненные (СДАН/АВТ.НАДЗОР)
- cancelled — расторгнуты (РАСТОРГНУТ)
- overdue — просрочки (StageExecutor: completed=False, deadline < today)
- by_cities — `{city: count}`
- by_agents — `{agent_type: count}`
- by_stages — `{column_name (CRMCard): count}`

**Надзор (из `/api/statistics/supervision`):**
- Аналогичная структура: total_orders, total_area, active, completed, cancelled, overdue, by_cities, by_agents, by_stages
- overdue для надзора: `SupervisionCard.deadline < today` при статусе АВТОРСКИЙ НАДЗОР
- by_stages для надзора: `SupervisionCard.column_name`

**Аналитические графики:**
- Воронка (funnel): `{column_name: count}` по CRM-карточкам Kanban
- Нагрузка исполнителей: топ-15, `{name, active_stages}` — активные StageExecutor не в [СДАН, РАСТОРГНУТ]
- Пирог по типам проектов: Инд/Шаб/Надзор (считается на клиенте из списка contracts)

**Общая статистика (из `/api/statistics/general`):**
- total_orders, active, completed, cancelled
- individual_count, template_count
- total_area, total_amount (сумма total_amount по договорам)
- active_employees
- total_payments, paid_payments, pending_payments

### 2.3 Паттерны UI

**Стиль вкладок QTabWidget:**
- Фон: `#F5F5F5`, выбранная — белая
- Padding: `10px 100px` (широкие вкладки)
- Font-size: 13px, bold

**Стиль фильтров-группы:**
- QGroupBox с `border: 1px solid #E0E0E0`
- По умолчанию свёрнута (filters_content.hide())
- Кнопка сворачивания: SVG-иконка arrow-down-circle/arrow-up-circle

**Стиль MetricCard:**
- `border: 2px solid {border_color}`, border-radius: 8px
- Hover: `border: 3px solid {border_color}`
- Высота фиксирована: 95px

**Создание графиков в вкладках:**
- `QGroupBox` → `QVBoxLayout` → `FigureCanvas` с именем 'canvas'
- Поиск: `findChild(QGroupBox, chart_name)` затем `findChild(FigureCanvas, 'canvas')`
- При нет данных: `ax.text(0.5, 0.5, 'Нет данных', ...)`

---

## 3. Интеграции

### 3.1 API endpoints для дашбордов

**Dashboard Router** (`/api/dashboard/`):

| Endpoint | Параметры | Возвращает |
|---|---|---|
| `GET /api/dashboard/clients` | `year?, agent_type?` | `{total_clients, total_individual, total_legal, clients_by_year, agent_clients_total, agent_clients_by_year}` |
| `GET /api/dashboard/contracts` | `year?, agent_type?` | `{individual_orders, individual_area, template_orders, template_area, agent_orders_by_year, agent_area_by_year}` |
| `GET /api/dashboard/crm` | `project_type, agent_type?` | `{total_orders, total_area, active_orders, archive_orders, agent_active_orders, agent_archive_orders}` |
| `GET /api/dashboard/employees` | — | `{active_employees, reserve_employees, active_management, active_projects_dept, active_execution_dept, upcoming_birthdays}` |
| `GET /api/dashboard/salaries` | `year?, month?` | Статистика зарплат |
| `GET /api/dashboard/agent-types` | — | `[str, ...]` |
| `GET /api/dashboard/contract-years` | — | `[int, ...]` |

**Statistics Router** (`/api/statistics/`):

| Endpoint | Параметры | Возвращает |
|---|---|---|
| `GET /api/statistics/dashboard` | `year?, month?, quarter?, agent_type?, city?` | `{total_contracts, total_amount, total_area, individual_count, template_count, status_counts, city_counts, monthly_data, active_crm_cards, supervision_cards}` |
| `GET /api/statistics/projects` | `project_type, year?, quarter?, month?, agent_type?, city?` | `{total_orders, total_area, active, completed, cancelled, overdue, by_cities, by_agents, by_stages}` |
| `GET /api/statistics/supervision` | `year?, quarter?, month?, agent_type?, city?` | `{total_orders, total_area, active, completed, cancelled, overdue, by_cities, by_agents, by_stages}` |
| `GET /api/statistics/supervision/filtered` | `year?, quarter?, month?, agent_type?, city?, address?, executor_id?, manager_id?, status?` | `{total_count, total_area, cards: [...]}` |
| `GET /api/statistics/crm/filtered` | `project_type, period, year, quarter?, month?, project_id?, executor_id?, stage_name?, status_filter?` | `[{id, contract_id, column_name, contract_number, address, area, is_approved}]` |
| `GET /api/statistics/general` | `year, quarter?, month?` | `{total_orders, active, completed, cancelled, individual_count, template_count, total_area, total_amount, active_employees, total_payments, paid_payments, pending_payments}` |
| `GET /api/statistics/funnel` | `year?, project_type?` | `{funnel: {column_name: count}, total: int}` |
| `GET /api/statistics/executor-load` | `year?, month?` | `[{name, active_stages}]` |
| `GET /api/statistics/contracts-by-period` | `year, group_by (month/quarter/status), project_type?` | По группе: `{count, amount}` |
| `GET /api/statistics/agent-types` | — | `[str, ...]` |
| `GET /api/statistics/cities` | — | `[str, ...]` |

### 3.2 Доступные данные для новых метрик

**Из модели Contract:**
- `total_amount` — стоимость договора (Float)
- `advance_payment`, `additional_payment`, `third_payment` — три платежа
- `advance_payment_paid_date`, `additional_payment_paid_date`, `third_payment_paid_date` — даты оплат
- `contract_date` — дата договора (String YYYY-MM-DD)
- `contract_period` — период договора в днях
- `status` — статус: Новый заказ / СДАН / РАСТОРГНУТ / АВТОРСКИЙ НАДЗОР
- `project_type` — Индивидуальный / Шаблонный
- `project_subtype` — подтип
- `area`, `city`, `agent_type`

**Повторные обращения клиентов:**
- Источник: `contracts.client_id` — одному клиенту может принадлежать несколько договоров
- Запрос: `GROUP BY client_id HAVING COUNT(*) > 1`
- Текущий endpoint: не реализован
- Возможен через `/api/dashboard/clients` с дополнительным параметром или новый endpoint

**Просрочки (StageExecutor):**
- Поля: `deadline` (String), `completed` (Boolean), `completed_date`
- Просроченная стадия: `completed=False AND deadline < today`
- Уже вычисляется в `/api/statistics/projects` для поля `overdue` (count distinct Contract.id)
- Не возвращается деталей (какие стадии, по каким договорам)

**Просрочки (ProjectTimelineEntry):**
- Поля: `actual_date` (String) — факт. дата выполнения, `stage_code`, `contract_id`
- Нет поля deadline в этой таблице (дедлайны в StageExecutor)

**Просрочки (SupervisionCard):**
- Поля: `deadline` (String), `dan_completed` (Boolean), `is_paused`
- Уже вычисляется в `/api/statistics/supervision` для поля `overdue`

**Стоимость (total_amount):**
- Уже суммируется в `/api/statistics/dashboard` → `total_amount`
- В `/api/statistics/general` → `total_amount`
- Не суммируется в `/api/statistics/projects` (только count и area)
- Не передаётся в `/api/dashboard/contracts`

**Статусы CRM карточек по стадиям:**
- `CRMCard.column_name` — текущая Kanban-колонка
- Уже вычисляется в `/api/statistics/projects` → `by_stages: {column_name: count}`
- Уже вычисляется в `/api/statistics/funnel` → `{column_name: count}`

**Оплаченность (Payment):**
- `final_amount`, `is_paid`, `payment_type`
- Суммируется в `/api/statistics/general`: `total_payments`, `paid_payments`, `pending_payments`
- Связаны с `contract_id`

### 3.3 Что нужно добавить

**Данные, которых нет в существующих endpoint-ах:**

1. **Сумма договоров по типу проекта** — `/api/statistics/projects` возвращает count и area, но не `total_amount`. Нужно добавить `total_amount` к ответу.

2. **Повторные обращения клиентов** — количество клиентов с 2+ договорами. Отсутствует в любом endpoint. Можно вычислить: `SELECT client_id, COUNT(*) FROM contracts GROUP BY client_id HAVING COUNT(*) > 1`.

3. **Динамика по месяцам для типа проекта** — `/api/statistics/contracts-by-period` поддерживает `project_type`, но клиент это не использует. ReportsTab не загружает динамику.

4. **Конверсия по стадиям** — сколько договоров доходит до СДАН vs РАСТОРГНУТ (процент). Нет отдельного endpoint.

5. **Средняя площадь договора** — вычислима из `total_area / total_orders`. Клиентская сторона это не считает.

6. **Средняя стоимость договора** — `total_amount / total_orders`. Нет.

7. **Стоимость надзора** — `/api/statistics/supervision` не возвращает `total_amount`.

8. **Разбивка CRM по статусам с фильтром** — `/api/statistics/projects` возвращает `by_stages`, но без фильтрации по году/кварталу для распределения по стадиям (только общий count).

**Текущие DataAccess-методы, не использующиеся в ReportsTab:**
- `get_clients_dashboard_stats` — используется только в ReportsStatisticsDashboard
- `get_contracts_dashboard_stats` — то же
- `get_crm_dashboard_stats` — то же
- `get_all_contracts()` — используется в `_load_analytics_charts` для пирога типов

**Методы DataAccess, которых нет, но можно добавить:**
- `get_reports_stats(year, quarter, month, agent_type, city)` — агрегированный метод для страницы Отчётов, возвращающий всё нужное за один вызов

---

## Приложение: Сводная таблица полей моделей

| Модель | Поля, релевантные для статистики |
|---|---|
| `Client` | `client_type` (Физ/Юр), `created_at` |
| `Contract` | `project_type`, `project_subtype`, `agent_type`, `city`, `contract_date`, `area`, `total_amount`, `status`, `client_id`, `contract_period` |
| `CRMCard` | `column_name` (Kanban), `is_approved`, `deadline`, `contract_id`, `created_at` |
| `StageExecutor` | `deadline`, `completed`, `completed_date`, `executor_id`, `crm_card_id` |
| `SupervisionCard` | `column_name`, `deadline`, `dan_completed`, `is_paused`, `contract_id`, `created_at` |
| `ProjectTimelineEntry` | `actual_date`, `actual_days`, `norm_days`, `stage_code`, `contract_id` |
| `SupervisionTimelineEntry` | `actual_date`, `budget_planned`, `budget_actual`, `defects_found`, `site_visits`, `supervision_card_id` |
| `Payment` | `final_amount`, `is_paid`, `payment_type`, `contract_id` |
