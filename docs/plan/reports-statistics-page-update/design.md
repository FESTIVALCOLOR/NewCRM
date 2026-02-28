# Design: Обновление страницы "Отчёты и Статистика"

## 1. C4 Model

### Container Level
```
[PyQt5 Desktop Client]
  └── ReportsTab (обновлённый)
        ├── ReportsFilterBar → фильтры
        ├── KPIDashboard → карточки метрик
        ├── ClientsSection → графики клиентов
        ├── ContractsSection → графики договоров
        ├── CRMAnalyticsSection → аналитика CRM
        └── SupervisionSection → надзор
  └── DataAccess → API / LocalDB fallback
        └── ReportsDataProvider (новый) → кеш + агрегация

[FastAPI Server]
  └── ReportsRouter (новый) → /api/dashboard/reports/*
        └── ReportsService → SQL агрегации
```

### Component Level

**ReportsFilterBar**
- Ответственность: хранение состояния фильтров, уведомление всех секций об изменениях
- Испускает сигнал `filters_changed(dict)` при любом изменении
- Инициализируется из кеша DataAccess (годы, агенты, города)

**KPIDashboard**
- Ответственность: отображение сводных KPI-карточек (динамическое количество)
- Фиксированные карточки: клиенты (3), договоры (3), площадь (2) = 8 штук
- Динамические карточки: по каждому агенту из справочника `agents` — клиенты, договоры, площадь (3 × N агентов)
- Подписывается на `filters_changed`, перезагружает `/reports/summary`
- Показывает тренды vs прошлый аналогичный период
- При добавлении нового агента в админке — карточки появляются автоматически

**ClientsSection**
- Ответственность: динамика клиентов по месяцам, распределение физ/юр и по агентам
- Два графика в ряд: линейный и pie/bar
- Данные: `/reports/clients-dynamics` + `/reports/distribution?dimension=agent`

**ContractsSection**
- Ответственность: динамика договоров (кол-во + стоимость), распределения по городам и типам
- Четыре графика в сетке 2×2
- Данные: `/reports/contracts-dynamics` + `/reports/distribution?dimension=city` + `/reports/distribution?dimension=project_type`

**CRMAnalyticsSection**
- Ответственность: воронка стадий, соблюдение сроков, среднее время стадий
- Разделена на 2 подвкладки: "Индивидуальные" и "Шаблонные" (QTabWidget внутри секции)
- Каждая подвкладка — полный набор графиков для своего типа проекта
- Данные: `/reports/crm-analytics?project_type=Индивидуальный` и `?project_type=Шаблонный`

**SupervisionSection**
- Ответственность: стадии закупок, бюджет план/факт, дефекты, визиты + разбивка по агентам/городам/типам
- Мини-дашборд: всего, активных, по типам проектов, по каждому агенту (динамически)
- Графики: стадии, бюджет, по городам, по агентам, по типам проектов
- Данные: `/reports/supervision-analytics` + `/reports/distribution`

**ReportsDataProvider**
- Ответственность: кеш результатов запросов, инвалидация при смене фильтров
- Ключ кеша: md5 от набора параметров фильтра
- Параллельная загрузка всех секций через `QThreadPool`

---

## 2. Структура страницы (макет сверху вниз)

### Секция 0: Глобальные фильтры (ReportsFilterBar)
Sticky сверху. Содержит:
- Год (ComboBox), Квартал (ComboBox), Месяц (ComboBox)
- Тип агента (ComboBox), Город (ComboBox), Тип проекта (ComboBox)
- Кнопка "Сбросить", Кнопка "Экспорт PDF"
- При изменении любого фильтра — перезагрузка ВСЕХ секций

### Секция 1: KPI-карточки (динамическое количество, зависит от числа агентов)

Количество карточек **динамическое** — ряды "по агентам" генерируются из справочника `agents` (таблица БД).
При добавлении нового агента через админку — карточки появятся автоматически.

**Ряд 1 — Клиенты (фиксированный):**
1. Всего клиентов — иконка users.svg, цвет #2196F3, тренд vs прошлый период
2. Новых клиентов (за период) — цвет #4CAF50
3. Повторных клиентов (>1 договора) — цвет #9C27B0

**Ряд 2 — Клиенты по агентам (динамический из справочника agents):**
Для КАЖДОГО агента из таблицы `agents` генерируется карточка:
- Клиенты — {Агент.name} (кол-во) — цвет берётся из Agent.color

**Ряд 3 — Договоры (фиксированный):**
4. Всего договоров — цвет #FF9800
5. Общая стоимость (руб) — цвет #F57C00, формат "1 234 567 руб"
6. Средний чек (руб) — цвет #E91E63

**Ряд 4 — Договоры по агентам (динамический):**
Для КАЖДОГО агента: кол-во договоров + сумма — цвет из Agent.color

**Ряд 5 — Площадь (фиксированный):**
7. Общая площадь (м²) — цвет #00BCD4
8. Средняя площадь (м²) — цвет #607D8B

**Ряд 6 — Площадь по агентам (динамический):**
Для КАЖДОГО агента: площадь (м²) — цвет из Agent.color

Каждая KPI-карточка: иконка, заголовок, значение, тренд (↑12% или ↓5% текстом, зелёный/красный)

### Секция 2: Клиенты

**Мини-дашборд сверху (6 карточек):**
1. Всего клиентов — цвет #2196F3
2. Физлица — цвет #4CAF50
3. Юрлица — цвет #FF9800
4. Новых за период — цвет #9C27B0
5. Повторных (>1 договора) — цвет #E91E63
6. От агентов (не прямые/Фестиваль) — цвет #00BCD4

**Графики (2x2):**
- [0,0] Line chart — динамика новых клиентов по месяцам текущего года (с возможностью наложить прошлый год)
- [0,1] Pie chart — физлица vs юрлица
- [1,0] Bar chart — клиенты по КАЖДОМУ агенту (динамически из справочника agents)
- [1,1] Stacked bar — новые vs повторные клиенты по месяцам

### Секция 3: Договоры

**Мини-дашборд сверху (6 карточек):**
1. Всего договоров — цвет #FF9800
2. Индивидуальных — цвет #F57C00
3. Шаблонных — цвет #C62828
4. Авторский надзор — цвет #388E3C
5. Общая стоимость — цвет #F57C00
6. Средний чек — цвет #E91E63

**Графики (3x2):**
- [0,0] Stacked bar: кол-во договоров по месяцам (инд/шабл/надзор стэком)
- [0,1] Line chart: стоимость договоров по месяцам (руб)
- [1,0] Pie chart: распределение по типам проектов (кол-во + стоимость)
- [1,1] Horizontal bar: ТОП города по количеству договоров
- [2,0] Grouped bar: договоры по КАЖДОМУ агенту (кол-во) — динамически из agents
- [2,1] Horizontal bar: стоимость по КАЖДОМУ агенту (руб) — динамически из agents

### Секция 4: CRM Аналитика — РАЗДЕЛЬНО Индивидуальные и Шаблонные

Внутри секции **2 подвкладки** (QTabWidget): "Индивидуальные проекты" и "Шаблонные проекты".
Каждая подвкладка содержит ОДИНАКОВЫЙ набор графиков, но для своего типа проекта.

**Для каждой подвкладки:**
- Горизонтальный bar: воронка по стадиям (свои стадии для каждого типа)
- Grouped bar chart: среднее время стадий vs норматив
- 4 KPI-мини-карточки:
  1. % проектов завершённых в срок
  2. % стадий завершённых в срок
  3. Среднее отклонение от дедлайна (дни)
  4. Проектов на паузе

**Стадии Индивидуальных:** Новый заказ → В ожидании → Стадия 1 (планировочные) → Стадия 2 (концепция) → Стадия 3 (чертежи) → Выполненный
**Стадии Шаблонных:** Новый заказ → В ожидании → Стадия 1 (планировочные) → Стадия 2 (чертежи) → Стадия 3 (3D визуализация) → Выполненный

### Секция 5: Авторский надзор — расширенная

**Мини-дашборд сверху (6 карточек):**
1. Всего надзоров — цвет #388E3C
2. Активных сейчас — цвет #4CAF50
3. По индивидуальным проектам — цвет #F57C00
4. По шаблонным проектам — цвет #C62828
5. Надзоры — {Агент 1} (динамически из agents) — цвет Agent.color
6. Надзоры — {Агент N} (динамически из agents) — цвет Agent.color

**Графики (3x2):**
- [0,0] Stacked bar: 12 стадий закупок (активные/завершённые)
- [0,1] Grouped bar: бюджет план vs факт по стадиям
- [1,0] Horizontal bar: надзоры по городам (динамически)
- [1,1] Bar chart: надзоры по КАЖДОМУ агенту (динамически из agents)
- [2,0] Pie chart: надзоры по типам проектов (индивидуальные vs шаблонные)

**Мини-KPI карточки:**
1. Экономия бюджета (руб + %)
2. Дефекты: найдено / устранено
3. Визиты на объект

---

## 3. DFD (Data Flow Diagram)

### Загрузка данных
```
Открытие ReportsTab
  → ReportsFilterBar инициализируется (загрузка годов, агентов, городов из кеша DataAccess)
  → load_all_statistics() — ПАРАЛЛЕЛЬНО:
      → GET /api/dashboard/reports/summary → KPI карточки
      → GET /api/dashboard/reports/clients-dynamics → Секция 2
      → GET /api/dashboard/reports/contracts-dynamics → Секция 3
      → GET /api/dashboard/reports/crm-analytics?project_type=Индивидуальный → Секция 4
      → GET /api/dashboard/reports/crm-analytics?project_type=Шаблонный → Секция 4
      → GET /api/dashboard/reports/supervision-analytics → Секция 5
      → GET /api/dashboard/reports/distribution?dimension=city → Секция 3
      → GET /api/dashboard/reports/distribution?dimension=agent → Секция 2,3

Изменение фильтра
  → Все запросы повторяются с новыми параметрами
  → Кеш инвалидируется для данного набора фильтров
```

### Offline fallback
Все endpoints имеют fallback в DataAccess → локальная SQLite → те же агрегации SQL.

---

## 4. API контракты (НОВЫЕ endpoints)

### 4.1 GET /api/dashboard/reports/summary
```python
@router.get("/reports/summary")
async def get_reports_summary(
    year: int = None,
    quarter: int = None,
    month: int = None,
    agent_type: str = None,
    city: str = None,
    project_type: str = None,
    user = Depends(get_current_user)
):
    # Response
    {
        "total_clients": int,
        "new_clients": int,          # за выбранный период
        "returning_clients": int,    # клиенты с >1 договором
        "total_contracts": int,
        "total_amount": float,       # сумма total_amount всех договоров
        "avg_amount": float,         # средний чек
        "total_area": float,         # сумма площадей
        "avg_area": float,           # средняя площадь
        "contracts_on_time_pct": float,  # % проектов завершённых в срок
        "stages_on_time_pct": float,     # % стадий завершённых в срок
        "trend_clients": float,     # % изменения vs прошлый период
        "trend_contracts": float,
        "trend_amount": float,
        # Разбивка по агентам (динамически из справочника agents)
        "by_agent": [
            {
                "agent_name": str,       # имя агента (Фестиваль, Петрович, ...)
                "agent_color": str,      # цвет агента (#FFFFFF)
                "clients": int,          # клиентов этого агента
                "contracts": int,        # договоров этого агента
                "amount": float,         # стоимость договоров агента
                "area": float            # площадь договоров агента
            }
        ]
    }
```

### 4.2 GET /api/dashboard/reports/clients-dynamics
```python
@router.get("/reports/clients-dynamics")
async def get_clients_dynamics(
    year: int = None,        # если не указан — текущий
    granularity: str = "month",  # month | quarter
    user = Depends(get_current_user)
):
    # Response
    [
        {
            "period": "2026-01",     # или "2026-Q1"
            "new_clients": int,
            "returning_clients": int,
            "individual": int,       # физлица
            "legal": int,            # юрлица
            "total": int
        }
    ]
```

### 4.3 GET /api/dashboard/reports/contracts-dynamics
```python
@router.get("/reports/contracts-dynamics")
async def get_contracts_dynamics(
    year: int = None,
    granularity: str = "month",
    agent_type: str = None,
    city: str = None,
    user = Depends(get_current_user)
):
    # Response
    [
        {
            "period": "2026-01",
            "individual_count": int,
            "template_count": int,
            "supervision_count": int,
            "total_count": int,
            "individual_amount": float,
            "template_amount": float,
            "supervision_amount": float,
            "total_amount": float
        }
    ]
```

### 4.4 GET /api/dashboard/reports/crm-analytics
```python
@router.get("/reports/crm-analytics")
async def get_crm_analytics(
    project_type: str = "Индивидуальный",
    year: int = None,
    quarter: int = None,
    month: int = None,
    user = Depends(get_current_user)
):
    # Response
    {
        "funnel": [
            {"stage": "Новый заказ", "count": int, "avg_days": float},
            {"stage": "Стадия 1: планировочные решения", "count": int, "avg_days": float},
            ...
        ],
        "on_time_stats": {
            "projects_on_time": int,
            "projects_overdue": int,
            "projects_total": int,
            "projects_pct": float,
            "stages_on_time": int,
            "stages_overdue": int,
            "stages_total": int,
            "stages_pct": float,
            "avg_deviation_days": float
        },
        "stage_durations": [
            {"stage": str, "avg_actual_days": float, "norm_days": float, "on_time_pct": float}
        ],
        "paused_count": int,
        "active_count": int,
        "archived_count": int
    }
```

### 4.5 GET /api/dashboard/reports/supervision-analytics
```python
@router.get("/reports/supervision-analytics")
async def get_supervision_analytics(
    year: int = None,
    quarter: int = None,
    month: int = None,
    user = Depends(get_current_user)
):
    # Response
    {
        "total": int,                # всего надзоров
        "active": int,               # активных сейчас
        "by_project_type": {         # по типам проектов
            "individual": int,       # по индивидуальным
            "template": int          # по шаблонным
        },
        "by_agent": [                # по КАЖДОМУ агенту (динамически из agents)
            {"agent_name": str, "agent_color": str, "count": int}
        ],
        "by_city": [                 # по городам
            {"city": str, "count": int}
        ],
        "stages": [
            {"stage": "Стадия 1: Закупка керамогранита", "active": int, "completed": int}
        ],
        "budget": {
            "total_planned": float,
            "total_actual": float,
            "total_savings": float,
            "savings_pct": float
        },
        "defects": {"found": int, "resolved": int, "resolution_pct": float},
        "site_visits": int
    }
```

### 4.6 GET /api/dashboard/reports/distribution
```python
@router.get("/reports/distribution")
async def get_distribution(
    dimension: str,     # city | agent | project_type | subtype
    year: int = None,
    quarter: int = None,
    month: int = None,
    user = Depends(get_current_user)
):
    # Response
    [
        {"name": str, "count": int, "amount": float, "area": float}
    ]
```

---

## 5. Новые компоненты (PyQt5 виджеты)

### 5.1 KPICard
- Наследует QFrame
- Иконка (SVG, 32px), заголовок (10px), значение (24px bold), тренд (12px, ↑/↓ + %)
- Фон: белый, граница: 2px solid {цвет}, border-radius: 12px
- Hover: тень или утолщение границы

### 5.2 SectionWidget
- Контейнер секции: заголовок + описание + содержимое
- Заголовок: 14px bold, #333
- Фон: #FAFAFA, граница: 1px solid #E0E0E0, border-radius: 8px

### 5.3 LineChartWidget (matplotlib)
- Линейный/area график
- Поддержка нескольких серий с легендой
- Адаптивный размер

### 5.4 StackedBarChartWidget (matplotlib)
- Stacked или grouped bar chart
- Цветовая кодировка по типам проектов

### 5.5 HorizontalBarWidget (matplotlib)
- Горизонтальный bar chart для ТОП-N

### 5.6 MiniKPICard
- Компактная версия KPICard для вложения в секции
- Высота: 60px, меньшие шрифты

### 5.7 ReportsFilterBar
- Горизонтальная панель фильтров
- 6 ComboBox + 2 кнопки
- Sticky поведение при скролле (QScrollArea)

---

## 6. Стратегия тестирования

### Unit тесты (tests/e2e/)
- test_reports_summary — проверка /reports/summary с разными фильтрами
- test_reports_clients_dynamics — проверка динамики клиентов
- test_reports_contracts_dynamics — проверка динамики договоров
- test_reports_crm_analytics — проверка CRM аналитики (on_time, funnel)
- test_reports_supervision — проверка аналитики надзора
- test_reports_distribution — проверка распределений

### UI тесты (tests/ui/)
- test_reports_tab_init — создание вкладки, все секции видимы
- test_reports_filters — изменение фильтров, перезагрузка данных
- test_reports_kpi_cards — корректные значения KPI
- test_reports_charts — графики рисуются без ошибок

### Acceptance Criteria
1. Все KPI-карточки показывают корректные значения (фиксированные + динамические по агентам)
2. Добавление нового агента в админке — автоматически появляются карточки по нему
3. Фильтры работают — данные обновляются при изменении во всех секциях
4. Секция 2: мини-дашборд клиентов + 4 графика корректны
5. Секция 3: мини-дашборд договоров + 6 графиков (вкл. разбивку по агентам)
6. Секция 4: отдельные подвкладки для индивидуальных и шаблонных, все графики по каждому типу
7. Секция 5: мини-дашборд надзоров + графики по агентам/городам/типам
8. Просрочки считаются правильно (deadline vs actual_date)
9. Тренды считаются правильно (текущий vs прошлый период)
10. Offline режим — все данные доступны из локальной БД
11. Экспорт PDF работает со всеми секциями
