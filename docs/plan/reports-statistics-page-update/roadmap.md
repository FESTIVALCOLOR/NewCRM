# Roadmap: Обновление страницы "Отчёты и Статистика"

## Оглавление

- ⬜ **Этап 1**: Backend — новые API endpoints для отчётов
  - ⬜ 1.1: Endpoint /reports/summary (KPI метрики)
  - ⬜ 1.2: Endpoint /reports/clients-dynamics (динамика клиентов)
  - ⬜ 1.3: Endpoint /reports/contracts-dynamics (динамика договоров)
  - ⬜ 1.4: Endpoint /reports/crm-analytics (CRM аналитика + просрочки)
  - ⬜ 1.5: Endpoint /reports/supervision-analytics (надзор)
  - ⬜ 1.6: Endpoint /reports/distribution (распределения)
- ⬜ **Этап 2**: API Client + DataAccess — клиентская интеграция
  - ⬜ 2.1: Методы в api_client для новых endpoints
  - ⬜ 2.2: Методы в DataAccess (API-first + offline fallback)
  - ⬜ 2.3: Fallback SQL в db_manager для offline
- ⬜ **Этап 3**: UI компоненты — новые виджеты
  - ⬜ 3.1: KPICard — карточка метрики с трендом
  - ⬜ 3.2: MiniKPICard — компактная карточка
  - ⬜ 3.3: SectionWidget — контейнер секции
  - ⬜ 3.4: ReportsFilterBar — панель фильтров
  - ⬜ 3.5: LineChartWidget — линейный график
  - ⬜ 3.6: StackedBarChartWidget — стопочный bar chart
  - ⬜ 3.7: HorizontalBarWidget — горизонтальный bar chart
- ⬜ **Этап 4**: ReportsTab — сборка страницы
  - ⬜ 4.1: Секция 0 — глобальные фильтры
  - ⬜ 4.2: Секция 1 — KPI-карточки (динамические, с разбивкой по агентам)
  - ⬜ 4.3: Секция 2 — клиенты (мини-дашборд + 4 графика + разбивка по агентам)
  - ⬜ 4.4: Секция 3 — договоры (мини-дашборд + 6 графиков + разбивка по агентам)
  - ⬜ 4.5: Секция 4 — CRM аналитика (раздельно индивидуальные и шаблонные)
  - ⬜ 4.6: Секция 5 — авторский надзор (мини-дашборд + по агентам/городам/типам)
  - ⬜ 4.7: Интеграция фильтров с секциями
  - ⬜ 4.8: Экспорт PDF (обновлённый)
- ⬜ **Этап 5**: Тестирование
  - ⬜ 5.1: E2E тесты для 6 API endpoints
  - ⬜ 5.2: UI тесты для новых виджетов
  - ⬜ 5.3: Client unit тесты для DataAccess
- ⬜ **Этап 6**: Docker rebuild + верификация
  - ⬜ 6.1: Docker rebuild на сервере
  - ⬜ 6.2: Curl верификация endpoints
  - ⬜ 6.3: Smoke-тест клиента

---

## ПЛАН: Обновление страницы "Отчёты и Статистика"

**РЕЖИМ:** full
**СЛОИ:** server, ui, utils, database

## Затронутые файлы

### Server (изменения)
| Файл | Действие | Строк | Описание |
|------|----------|-------|----------|
| `server/routers/dashboard_router.py` (1028 строк) | Изменить | +420 | +6 новых endpoints `/reports/*` под prefix `/api/v1/dashboard` |
| `server/database.py` | Читать | — | Модели Contract, Client, CRMCard, StageExecutor, SupervisionCard, SupervisionTimelineEntry, Payment для SQL запросов |
| `server/main.py` | Без изменений | — | dashboard_router уже подключён (`prefix="/api/v1/dashboard"`), новые endpoints подхватятся автоматически |

**Примечание:** `server/routers/reports_router.py` (329 строк) уже существует с prefix `/api/v1/reports`, но содержит только employee-related endpoints (`/employee`, `/employee-report`). Новые endpoints добавляются в `dashboard_router.py` согласно design.md — под path `/reports/*`, итоговые URL: `/api/v1/dashboard/reports/summary`, `/api/v1/dashboard/reports/clients-dynamics` и т.д.

### Client UI (изменения)
| Файл | Действие | Строк текущих | Строк ~(+/-) | Описание |
|------|----------|---------------|-------------|----------|
| `ui/reports_tab.py` | Переписать | 868 | ~800 (rewrite) | Полная переработка — 6 секций вместо 4 вкладок QTabWidget |
| `ui/chart_widget.py` | Изменить | 184 | +260 | +3 новых типа графиков (LineChartWidget, StackedBarChartWidget, HorizontalBarWidget) + SectionWidget |
| `ui/dashboards.py` | Изменить | 1829 | +50 | Обновить ReportsStatisticsDashboard (строки 1462–1624) — KPI-карточки с трендами |
| `ui/dashboard_widget.py` | Изменить | 503 | +130 | Добавить KPICard (с трендом) и MiniKPICard |

### Utils (изменения)
| Файл | Действие | Строк текущих | Строк ~(+) | Описание |
|------|----------|---------------|------------|----------|
| `utils/data_access.py` | Изменить | 3280 | +100 | +6 новых методов для reports endpoints (API-first + fallback) |
| `utils/api_client/statistics_mixin.py` | Изменить | 520 | +60 | +6 API методов GET для reports endpoints |

### Database (изменения)
| Файл | Действие | Строк текущих | Строк ~(+) | Описание |
|------|----------|---------------|------------|----------|
| `database/db_manager.py` | Изменить | 6038 | +200 | +6 fallback SQL методов для offline режима |

### Тесты (новые)
| Файл | Действие | Описание |
|------|----------|----------|
| `tests/e2e/test_e2e_reports_analytics.py` | Создать | E2E тесты для 6 новых endpoints (naming convention: `test_e2e_*.py`) |
| `tests/ui/test_reports_tab_updated.py` | Создать | UI тесты виджетов (KPICard, фильтры, графики) |
| `tests/client/test_reports_data_access.py` | Создать | Unit тесты DataAccess mock методов |

---

## Подзадачи с зависимостями

### Этап 1: Backend (ПАРАЛЛЕЛЬНО с Этапом 3)
**Агент:** Backend Agent (sonnet)
**Зависимости:** нет
**Файл:** `server/routers/dashboard_router.py`

| # | Подзадача | Строк ~(+) | Описание |
|---|-----------|------------|----------|
| 1.1 | `/reports/summary` | +120 | Агрегация: клиенты (всего, новые, повторные), договоры, стоимость (total + avg), площадь (total + avg), % в срок (проекты + стадии), тренды vs прошлый период. **+ разбивка по КАЖДОМУ агенту** (by_agent: [{agent_name, clients, contracts, amount, area}]). Использует модели: Contract, Client, CRMCard, StageExecutor, Agent |
| 1.2 | `/reports/clients-dynamics` | +60 | GROUP BY month/quarter с подсчётом новых/повторных/физ/юр. Параметр `granularity` (month\|quarter). Повторный клиент = `client_id` с >1 договором за всё время |
| 1.3 | `/reports/contracts-dynamics` | +60 | GROUP BY month/quarter, разбивка по типам проектов (инд/шабл/надзор), суммы `total_amount` по каждому типу |
| 1.4 | `/reports/crm-analytics` | +100 | Воронка по стадиям (CRMCard.column_name + count + avg_days), on_time stats (StageExecutor.deadline vs completed_date), stage_durations (avg actual vs norm), paused/active/archived counts |
| 1.5 | `/reports/supervision-analytics` | +100 | Стадии закупок (SupervisionCard.column_name → active/completed), бюджет план/факт (SupervisionTimelineEntry), дефекты (defects_found/resolved), визиты (site_visits). **+ разбивка**: by_agent (динамически), by_city, by_project_type (инд/шабл). Использует: SupervisionCard, Contract, Agent, City |
| 1.6 | `/reports/distribution` | +50 | GROUP BY dimension (city\|agent\|project_type\|subtype), возвращает count + amount + area по каждой группе |

**Итого ~470 строк серверного кода**

**Важно:** Все endpoints под `router = APIRouter(tags=["dashboard"])`, автоматически попадают под prefix `/api/v1/dashboard`. Защита: `Depends(get_current_user)`. Все фильтры: `year?, quarter?, month?, agent_type?, city?, project_type?` — опциональны.

### Этап 2: API Client + DataAccess (ПОСЛЕ Этапа 1)
**Агент:** API Client Agent (sonnet)
**Зависимости:** Этап 1

| # | Подзадача | Файл | Строк ~(+) | Описание |
|---|-----------|------|------------|----------|
| 2.1 | API client методы | `utils/api_client/statistics_mixin.py` | +60 | 6 методов: `get_reports_summary()`, `get_reports_clients_dynamics()`, `get_reports_contracts_dynamics()`, `get_reports_crm_analytics()`, `get_reports_supervision_analytics()`, `get_reports_distribution()`. Все — GET запросы, возвращают dict/list. Учесть, что StatisticsMixin уже содержит 20+ методов (520 строк) |
| 2.2 | DataAccess методы | `utils/data_access.py` | +100 | 6 методов с паттерном API-first + fallback: `get_reports_summary(**kwargs)`, `get_reports_clients_dynamics(**kwargs)`, `get_reports_contracts_dynamics(**kwargs)`, `get_reports_crm_analytics(**kwargs)`, `get_reports_supervision_analytics(**kwargs)`, `get_reports_distribution(**kwargs)`. Кеш через md5 хеш параметров (как `_analytics_data_hash` в текущем ReportsTab) |
| 2.3 | DB fallback SQL | `database/db_manager.py` | +200 | 6 SQL агрегаций для offline режима — повторить логику серверных SQL запросов на SQLite. Учесть различия SQLite vs PostgreSQL: `strftime` вместо `EXTRACT`, отсутствие `EPOCH FROM` |

**Итого ~360 строк**

### Этап 3: UI компоненты (ПАРАЛЛЕЛЬНО с Этапом 1)
**Агент:** Design Stylist (sonnet) + Frontend Agent (sonnet)
**Зависимости:** нет

| # | Подзадача | Файл | Строк ~(+) | Описание |
|---|-----------|------|------------|----------|
| 3.1 | KPICard | `ui/dashboard_widget.py` | +80 | QFrame: иконка SVG (32px) + заголовок (10px) + значение (24px bold) + тренд текст (12px, зелёный/красный). Border: 2px solid {цвет}, border-radius: 12px. Отличие от MetricCard: тренд вместо FilterButton, другой border-radius |
| 3.2 | MiniKPICard | `ui/dashboard_widget.py` | +50 | Компактная версия KPICard (высота 60px, шрифты меньше). Для встраивания в секции CRM и Надзор |
| 3.3 | SectionWidget | `ui/chart_widget.py` | +40 | QFrame контейнер секции: заголовок 14px bold #333 + описание + content area. Фон #FAFAFA, border: 1px solid #E0E0E0, border-radius: 8px |
| 3.4 | ReportsFilterBar | `ui/reports_tab.py` | +100 | QWidget горизонтальная панель: 6 CustomComboBox (Год, Квартал, Месяц, Тип агента, Город, Тип проекта) + кнопка "Сбросить" + кнопка "Экспорт PDF". Signal `filters_changed(dict)`. Sticky поведение через QScrollArea |
| 3.5 | LineChartWidget | `ui/chart_widget.py` | +80 | Наследует ChartBase. Линейный/area matplotlib. Поддержка нескольких серий с легендой. Метод `set_data(series: list[dict])` где каждый dict содержит `label`, `x`, `y`, `color` |
| 3.6 | StackedBarChartWidget | `ui/chart_widget.py` | +80 | Наследует ChartBase. Stacked bars matplotlib. Метод `set_data(categories, series: list[dict])`. Цветовая кодировка по типам проектов: #ffd93c (инд), #F39C12 (шабл), #27AE60 (надзор) |
| 3.7 | HorizontalBarWidget | `ui/chart_widget.py` | +60 | Наследует ChartBase. Расширение/рефакторинг существующего FunnelBarChart. Метод `set_data(labels, values, colors=None)`. ТОП-N с автоматической сортировкой |

**Итого ~490 строк**

### Этап 4: ReportsTab сборка (ПОСЛЕ Этапов 2 и 3)
**Агент:** Frontend Agent (sonnet)
**Зависимости:** Этапы 2, 3
**Файл:** `ui/reports_tab.py` — полный rewrite (868 строк → ~800 строк)

| # | Подзадача | Строк ~(+) | Описание |
|---|-----------|------------|----------|
| 4.1 | Фильтры | +60 | Инициализация ReportsFilterBar, подключение signal `filters_changed` к `reload_all_sections()`. Источники данных: `DataAccess.get_contract_years()`, `DataAccess.get_agent_types()`, `DataAccess.get_cities()` |
| 4.2 | KPI секция | +120 | Динамическое число KPICard (QFlowLayout/QGridLayout). 8 фиксированных + N×3 по агентам. Данные из `/reports/summary` (вкл. by_agent). Карточки: клиенты (3) + по агентам + договоры (3) + по агентам + площадь (2) + по агентам |
| 4.3 | Клиенты | +80 | SectionWidget: мини-дашборд (6 карточек) + 4 графика (2x2): LineChart (динамика), Pie (физ/юр), Bar по КАЖДОМУ агенту (динамически из agents), StackedBar (новые vs повторные). Данные: `/reports/clients-dynamics` + `/reports/distribution?dimension=agent` |
| 4.4 | Договоры | +100 | SectionWidget: мини-дашборд (6 карточек) + 6 графиков (3x2): StackedBar (по месяцам), Line (стоимость), Pie (по типам), HorizontalBar (ТОП города), GroupedBar (договоры по КАЖДОМУ агенту), HorizontalBar (стоимость по КАЖДОМУ агенту). Данные: `/reports/contracts-dynamics` + `/reports/distribution` |
| 4.5 | CRM | +120 | SectionWidget с QTabWidget (2 подвкладки: Индивидуальные / Шаблонные). Каждая подвкладка: FunnelBarChart (воронка), GroupedBar (время vs норматив), 4 MiniKPICard. Данные: `/reports/crm-analytics?project_type=...` |
| 4.6 | Надзор | +100 | SectionWidget: мини-дашборд (всего, активных, по типам, по КАЖДОМУ агенту — динамически) + 5 графиков: стадии, бюджет, по городам, по агентам, pie по типам + 3 MiniKPICard. Данные: `/reports/supervision-analytics` |
| 4.7 | Интеграция | +40 | Связь фильтров с секциями: при `filters_changed` — параллельная загрузка через QThreadPool (как в текущем `_load_analytics_charts`). Кеш через md5 хеш параметров. Ленивая загрузка (как `ensure_data_loaded()`) |
| 4.8 | PDF экспорт | +60 | Обновлённый `export_to_pdf()`: QTextDocument с логотипом, KPI таблица, описание секций. Кнопка экспорта в ReportsFilterBar |

**Итого ~680 строк (переписанный reports_tab.py ~1000 строк)**

**Важное архитектурное решение:** Замена QTabWidget (4 вкладки) на QScrollArea с последовательными SectionWidget. Комментарий из текущего кода "ТОЛЬКО ДИАГРАММЫ — карточки статистики показываются в дашборде main_window" больше не актуален — KPI-карточки теперь интегрируются в саму страницу ReportsTab.

### Этап 5: Тестирование (ПОСЛЕ Этапа 4)
**Агент:** Test-Runner (haiku)
**Зависимости:** Этап 4

| # | Подзадача | Файл | Строк ~(+) | Описание |
|---|-----------|------|------------|----------|
| 5.1 | E2E тесты | `tests/e2e/test_e2e_reports_analytics.py` | +200 | 6 endpoints x 3-4 кейса: без фильтров, с годом, с кварталом, с городом. Naming convention: `test_e2e_*.py` (как `test_e2e_dashboard.py`, `test_e2e_statistics.py`). Conftest: `tests/e2e/conftest.py` |
| 5.2 | UI тесты | `tests/ui/test_reports_tab_updated.py` | +150 | Инициализация ReportsTab, проверка секций, фильтры, mock DataAccess, проверка KPICard значений |
| 5.3 | Client тесты | `tests/client/test_reports_data_access.py` | +100 | DataAccess mock тесты: API-first path, fallback path, кеширование, преобразование данных |

**Итого ~450 строк тестов**

### Этап 6: Деплой и верификация (ПОСЛЕ Этапа 5)
**Агент:** Deploy (opus) — только по запросу
**Зависимости:** Этап 5 (все тесты green)

| # | Подзадача | Описание |
|---|-----------|----------|
| 6.1 | Docker rebuild | `ssh timeweb "cd /opt/interior_studio && git pull origin <branch> && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"` |
| 6.2 | Curl верификация | Проверить все 6 endpoints через curl с JWT. Генерация JWT: `docker exec crm_api python3 -c "from auth import create_access_token; print(create_access_token({\"sub\": \"1\"}))"` |
| 6.3 | Smoke-тест клиента | `.venv\Scripts\python.exe main.py` — проверить вкладку "Отчёты и Статистика", все 6 секций, фильтры, экспорт PDF |

---

## Граф зависимостей

```
Этап 1 (Backend) ─────┐
                       ├──→ Этап 2 (API Client) ─┐
Этап 3 (UI виджеты) ──┘                          ├──→ Этап 4 (Сборка) ──→ Этап 5 (Тесты) ──→ Этап 6 (Деплой)
                                                   │
                                                   └──→ Gate Check
```

## Параллелизм
- **Этап 1 + Этап 3** — запускаются ПАРАЛЛЕЛЬНО (Backend + UI виджеты, независимы друг от друга)
- **Этап 2** — последовательно ПОСЛЕ Этапа 1 (зависит от API контрактов серверных endpoints)
- **Этап 4** — последовательно ПОСЛЕ Этапов 2 и 3 (зависит от обоих: API client методы + UI виджеты)
- **Этап 5** — последовательно ПОСЛЕ Этапа 4
- Gate Checks — после каждого субагента

## Оценка объёма
- **Серверный код:** ~470 строк (dashboard_router.py)
- **Клиентский код:** ~1170 строк (UI виджеты 490 + сборка 680)
- **Утилиты:** ~400 строк (API client 60 + DataAccess 120 + DB fallback 220)
- **Тесты:** ~500 строк (E2E 220 + UI 170 + Client 110)
- **ИТОГО:** ~2540 строк кода

## Субагенты задействованные
1. **Backend Agent** (sonnet) — Этап 1: 6 серверных endpoints
2. **API Client Agent** (sonnet) — Этап 2: statistics_mixin + data_access + db_manager
3. **Design Stylist** (sonnet) — Этап 3: стили KPICard, MiniKPICard, SectionWidget
4. **Frontend Agent** (sonnet) — Этапы 3, 4: UI виджеты + сборка ReportsTab
5. **Gate Checker** (haiku) — после каждого этапа: проверка импортов, совместимости, стилей
6. **Test-Runner** (haiku) — Этап 5: запуск тестов, проверка покрытия
7. **Debugger** (sonnet) — если тесты упали: анализ, исправление, повторный запуск
8. **Reviewer** (sonnet) — финальный ревью всех изменений перед merge
9. **Compatibility Checker** (haiku) — проверка API/DB ключей ответов, offline fallback
10. **Documenter** (haiku) — обновление docs (roadmap статусы, changelog)

## Риски и митигации

| Риск | Вероятность | Митигация |
|------|-------------|-----------|
| SQLite vs PostgreSQL различия в SQL (EXTRACT, EPOCH) | Высокая | Этап 2.3: отдельные SQL для SQLite в db_manager с `strftime` |
| Переписание reports_tab.py ломает PDF экспорт | Средняя | Этап 4.8: обновить PDF сразу при rewrite, покрыть тестом |
| ReportsStatisticsDashboard в main_window конфликтует с KPI в ReportsTab | Низкая | Обновить дашборд в Этапе 3: убрать дублирующие карточки или оставить как "быстрый обзор" |
| Медленные SQL агрегации на больших данных | Средняя | Серверные endpoints с LIMIT/кешированием, клиент — QThreadPool для параллельной загрузки |
| Matplotlib TkAgg conflict с PyQt5 | Низкая | Уже решено в проекте — использовать FigureCanvasQTAgg (как ChartBase) |

## Контракты API (сводка из design.md)

| Endpoint | URL | Параметры | Ключи ответа |
|----------|-----|-----------|--------------|
| Summary | `GET /api/v1/dashboard/reports/summary` | year?, quarter?, month?, agent_type?, city?, project_type? | total_clients, new_clients, returning_clients, total_contracts, total_amount, avg_amount, total_area, avg_area, contracts_on_time_pct, stages_on_time_pct, trend_clients, trend_contracts, trend_amount, **by_agent**: [{agent_name, agent_color, clients, contracts, amount, area}] |
| Clients Dynamics | `GET /api/v1/dashboard/reports/clients-dynamics` | year?, granularity? (month\|quarter) | [{period, new_clients, returning_clients, individual, legal, total}] |
| Contracts Dynamics | `GET /api/v1/dashboard/reports/contracts-dynamics` | year?, granularity?, agent_type?, city? | [{period, individual_count, template_count, supervision_count, total_count, individual_amount, template_amount, supervision_amount, total_amount}] |
| CRM Analytics | `GET /api/v1/dashboard/reports/crm-analytics` | project_type?, year?, quarter?, month? | {funnel: [{stage, count, avg_days}], on_time_stats: {...}, stage_durations: [{stage, avg_actual_days, norm_days, on_time_pct}], paused_count, active_count, archived_count} |
| Supervision Analytics | `GET /api/v1/dashboard/reports/supervision-analytics` | year?, quarter?, month? | {total, active, **by_project_type**: {individual, template}, **by_agent**: [{agent_name, agent_color, count}], **by_city**: [{city, count}], stages: [{stage, active, completed}], budget: {total_planned, total_actual, total_savings, savings_pct}, defects: {found, resolved, resolution_pct}, site_visits} |
| Distribution | `GET /api/v1/dashboard/reports/distribution` | dimension (city\|agent\|project_type\|subtype), year?, quarter?, month? | [{name, count, amount, area}] |
