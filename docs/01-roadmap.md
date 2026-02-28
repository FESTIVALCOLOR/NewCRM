# Roadmap — Дорожная карта Interior Studio CRM

> Последнее обновление: 2026-02-23

## Текущая версия

- **Клиент:** PyQt5 Desktop (Python 3.14.0)
- **Сервер:** FastAPI (Python 3.11) + PostgreSQL
- **Инфраструктура:** Docker на VPS (Timeweb)

## Выполненные фичи

### Ядро (Core)
- [x] Двухрежимная архитектура (Автономный SQLite + Сетевой REST API)
- [x] JWT авторизация с ролями и правами доступа
- [x] Offline-first с очередью синхронизации
- [x] Real-time синхронизация между клиентами (QTimer 30 сек)
- [x] Heartbeat и онлайн-статус пользователей
- [x] Блокировка записей (concurrent editing prevention)
- [x] Синхронизация БД при входе (14 этапов)

### CRM Kanban ([ui/crm_tab.py](../ui/crm_tab.py))
- [x] Kanban доска с Drag & Drop
- [x] Индивидуальные проекты (6 колонок) и Шаблонные (5 колонок)
- [x] Стадии согласования (approval stages)
- [x] Назначение исполнителей на стадии
- [x] Workflow: Сдать работу → Проверка → Принять/На исправление
- [x] Workflow: Клиенту на согласование → Клиент согласовал
- [x] Рассчёт дедлайнов исполнителей (рабочие дни)

### Авторский надзор ([ui/crm_supervision_tab.py](../ui/crm_supervision_tab.py))
- [x] Отдельная Kanban доска для надзора
- [x] Таблица закупок (12 стадий)
- [x] Бюджет план/факт, экономия, комиссия поставщика
- [x] Пауза/возобновление карточки надзора

### Платежи ([ui/salaries_tab.py](../ui/salaries_tab.py))
- [x] Расчёт платежей по тарифам
- [x] Переназначение платежей при смене исполнителя
- [x] Зарплатные отчёты по месяцам
- [x] Статус "В работе" (report_month = NULL)

### Таблица сроков ([ui/timeline_widget.py](../ui/timeline_widget.py))
- [x] 7-колоночная таблица для проектов (Дата, Дни, Норма, Статус, Исполнитель, ФИО)
- [x] 11-колоночная таблица для надзора (Бюджет, Поставщик, Комиссия)
- [x] Авто-расчёт START = max(contract_date, survey_date, tech_task_date)
- [x] Пропорциональное распределение norm_days по contract_term
- [x] Дедлайн исполнителя от предыдущей actual_date (не от today)
- [x] Планируемые даты цепочкой (prev_date + norm_days) с tooltip
- [x] Каскадный пересчёт planned_date при ручном изменении даты (автоматический)
- [x] Сценарии по типам проектов: 3 подтипа Индивидуальных + 4 подтипа Шаблонных
- [x] Кастомные нормо-дни по агентам (NormDaysTemplate с приоритетами)
- [x] Автосинхронизация norm_days из admin шаблона в карточки (односторонняя, пропускает custom)
- [x] Заблокированные ячейки дат + кнопка-карандаш для редактирования
- [x] Экспорт в Excel и PDF
- [x] Дедлайны исполнителей → read-only QLabel + диалог с причиной (Фаза 8.0)
- [x] Дедлайн проекта → авто-расчёт START + contract_term (pyqtSignal)
- [x] workflow_reject/client_ok → запись actual_date в timeline (Фаза 8.1)
- [x] custom_norm_days: зачёркнутая стандартная + красная кастомная (Фаза 8.2)
- [x] Пропуск промежуточных подэтапов при отправке клиенту (Фаза 8.3)
- [x] Кнопка "Клиент согласовал" по workflow state (Фаза 8.4)
- [x] Гибкий маппинг stage_group через regex (Фаза 8.5)

### Файлы и интеграции
- [x] Интеграция с Яндекс.Диском (загрузка/скачивание/публикация)
- [x] Автоматическое создание папок при создании договора
- [x] Галерея файлов с превью
- [x] Галерея вариаций

### Поиск и аналитика
- [x] Глобальный полнотекстовый поиск (клиенты, договора, проекты)
- [x] Дашборд: круговая диаграмма типов проектов
- [x] Дашборд: воронка проектов по колонкам Kanban
- [x] Дашборд: нагрузка исполнителей (активные стадии)
- [x] Менеджер обновлений клиента (auto-update)
- [x] Экспорт PDF (таймлайн, надзор)

### Инфраструктура
- [x] Docker-compose (PostgreSQL + FastAPI + Nginx) с health checks
- [x] PyInstaller сборка в exe
- [x] Кастомный CustomTitleBar (Frameless окна)
- [x] Единая система стилей (unified_styles.py)
- [x] SVG иконки через IconLoader
- [x] 17 субагентов Claude Code (оркестратор + 16 специализированных)
- [x] Hooks для валидации кода
- [x] GitHub Actions CI/CD (lint, test-db, docker-build, e2e)
- [x] `.env.example` шаблон переменных окружения
- [x] Секреты вынесены в переменные окружения
- [x] faulthandler для crash-диагностики (Python traceback при segfault)
- [x] Thread-safe PyQt signals (QTimer.singleShot для фоновых потоков)
- [x] Фильтрация offline-очереди (только сетевые ошибки)

---

## Аудит: Полный анализ 17 систем (2026-02-23)

> Комплексный анализ всех 17 подсистем CRM + глубокий анализ runtime-крашей.
> Тестирование после фиксов: **879 passed**, 0 failed, 3 skipped.
> Исправлено: **23 бага** (11 runtime R-01..R-11 + 12 системных S-01..S-15).
> Общая оценка качества: ~~6.4/10~~ → **8.1/10** (после фиксов).

### Результаты по системам

| # | Система | Статус | Было | Исправлено | Осталось | Фиксы |
|---|---------|--------|------|------------|----------|-------|
| 1 | ~~Бизнес-процессы (общее)~~ | **РАБОТАЕТ** | 5 | 3 | 2 | R-01, S-01, S-05 |
| 2 | Клиенты | РАБОТАЕТ | 5 | 0 | **5** | — |
| 3 | ~~Договоры~~ | **РАБОТАЕТ** | 5 | 3 | 2 | S-02, R-10, R-01 |
| 4 | ~~CRM (канбан, карточки)~~ | **РАБОТАЕТ** | 7 | 5 | 2 | S-01, S-05, R-01, R-02, R-04 |
| 5 | ~~CRM Надзора~~ | **РАБОТАЕТ** | 5 | 1 | **4** | S-14 |
| 6 | ~~Назначение сотрудников~~ | **РАБОТАЕТ** | 4 | 2 | 2 | S-05, R-05 |
| 7 | Дедлайны | ЧАСТИЧНО | 7 | 0 | **7** | — |
| 8 | ~~Файлы и Яндекс Диск~~ | ЧАСТИЧНО | 7 | 2 | **5** | S-03, R-02 |
| 9 | ~~Платежи и зарплаты~~ | **РАБОТАЕТ** | 6 | 3 | 3 | S-07, S-08, R-08 |
| 10 | ~~История проекта~~ | ЧАСТИЧНО | 5 | 1 | **4** | R-11 |
| 11 | ~~Учёт сотрудников~~ | **РАБОТАЕТ** | 5 | 2 | 3 | S-07, S-11(fp) |
| 12 | Аналитика проектов | ЧАСТИЧНО | 7 | 0 | **7** | — |
| 13 | ~~Аналитика сотрудников~~ | **РАБОТАЕТ** | 6 | 3 | 3 | S-04, S-09, S-15 |
| 14 | ~~Администрирование~~ | **РАБОТАЕТ** | 5 | 2 | 3 | S-12, S-06(fp) |
| 15 | ~~Фильтрация~~ | ЧАСТИЧНО | 5 | 1 | **4** | S-14 |
| 16 | ~~Отчётность PDF/Excel~~ | ЧАСТИЧНО | 7 | 2 | **5** | S-10, S-13 |
| 17 | ~~Кнопки действий~~ | **РАБОТАЕТ** | 6 | 2 | 4 | R-01, R-03 |

**Было:** 97 проблем. **Исправлено:** 32 (включая сопутствующие). **Осталось:** **65**.

#### Нерешённые проблемы (требуют внимания)

**Системы с наибольшим остатком:**
- **7. Дедлайны (7)** — не затронуты текущими фиксами; каскадный пересчёт, таймзоны, edge cases
- **12. Аналитика проектов (7)** — дублирование логики дашбордов, отсутствие drill-down
- **8. Файлы и Яндекс Диск (5)** — превью, обработка ошибок загрузки, оффлайн-доступ
- **16. Отчётность PDF/Excel (5)** — отсутствие единого стиля, нет xlsx, шаблоны
- **2. Клиенты (5)** — нет серверного поиска, фильтрация, пагинация
- **5. CRM Надзора (4)** — фильтрация, архивные статусы, кнопки
- **10. История проекта (4)** — хронология, группировка, фильтрация
- **15. Фильтрация (4)** — несогласованность фильтров между вкладками

### Аудит: Runtime-краши (скрытые, не ловятся тестами)

| # | Баг | Категория | Файл | Severity | Статус |
|---|-----|-----------|------|----------|--------|
| R-01 | `@debounce_click` передаёт Qt bool в bound-метод — TypeError на 8 методах | TypeError | `utils/button_debounce.py:35` | **P0** | **DONE** |
| R-02 | `progress.wasCanceled()` из threading.Thread → SEGFAULT при закрытии диалога | SEGFAULT | `ui/crm_card_edit_dialog.py`, `ui/contract_dialogs.py` | **P0** | **DONE** — `threading.Event` |
| R-03 | `emit()` сигнала из threading.Thread без QTimer → SEGFAULT | SEGFAULT | `ui/crm_card_edit_dialog.py:5515` | **P0** | **DONE** — `QTimer.singleShot(0, ...)` |
| R-04 | `PreviewLoaderThread.callback` на удалённый объект → SEGFAULT | SEGFAULT | `ui/crm_tab.py:3278` | **P0** | **DONE** — `_stopped` flag + safe callback |
| R-05 | `self.employee['id']` когда employee=None → TypeError | TypeError | `ui/crm_card_edit_dialog.py:1329` | **P1** | **DONE** — None-check |
| R-06 | `_is_online` в APIClientBase без lock → race condition | Race | `utils/api_client/base.py:84` | **P1** | **DONE** — `threading.RLock` |
| R-07 | `self.data` из threading.Thread без защиты → AttributeError | Race | `ui/crm_card_edit_dialog.py:5477` | **P1** | **DONE** — кэширование `is_online` перед потоком |
| R-08 | `datetime` без `.isoformat()` в create CRM card | Serialization | `server/routers/crm_router.py:343` | **P1** | **DONE** — `.isoformat()` |
| R-09 | SQLite без потокобезопасности в OfflineManager | Corruption | `utils/offline_manager.py:127` | **P1** | **DONE** — `threading.RLock` |
| R-10 | `contract_data['key']` без `.get()` в fill_data → KeyError | KeyError | `ui/contract_dialogs.py:1911-1941` | **P2** | **DONE** — `.get()` |
| R-11 | Разные поля в ответе create vs update CRM card | API mismatch | `server/routers/crm_router.py:324 vs 384` | **P2** | **DONE** — унифицированный формат |
| R-12 | Дублирование ключей в dashboard API | Logic | `server/routers/dashboard_router.py:310` | **P2** | Алиасы для обратной совместимости |

### ТОП-15 системных багов (из анализа 17 систем)

| # | Баг | Файл | Severity | Статус |
|---|-----|------|----------|--------|
| S-01 | VALID_CRM_COLUMNS не включает колонки шаблонных проектов → HTTP 422 при drag-n-drop | `server/routers/crm_router.py` | P0 | DONE |
| S-02 | `project_subtype` отсутствует в SQLite INSERT → данные теряются | `database/db_manager.py`, `database/migrations.py` | P0 | DONE |
| S-03 | Несовместимость upload API: клиент JSON base64, сервер multipart → 422 | `utils/api_client/files_mixin.py` | P0 | DONE |
| S-04 | Несоответствие периодов UI↔API: 'Месяц' vs 'За месяц' | `ui/employee_reports_tab.py` | P0 | DONE |
| S-05 | Прямые SQL в UI обходят DataAccess → не синхронизируются | `ui/crm_tab.py`, `database/db_manager.py`, `utils/data_access.py` | P1 | DONE |
| S-06 | Кэш прав не инвалидируется при сохранении матрицы | — | P1 | FALSE POSITIVE |
| S-07 | Удаление сотрудника каскадно удаляет платежи и историю | `server/routers/employees_router.py`, `server/database.py` | P1 | DONE |
| S-08 | `recalculate` перезаписывает ручную корректировку (is_manual) | `server/routers/payments_router.py` | P1 | DONE |
| S-09 | PostgreSQL regex `op('~')` ломает SQLite offline | `server/routers/reports_router.py` | P1 | DONE |
| S-10 | PDFGenerator игнорирует self.font → кириллица ломается | `utils/pdf_generator.py` | P1 | DONE |
| S-11 | Уволенный сотрудник может войти в систему | — | P1 | FALSE POSITIVE |
| S-12 | Расхождение матриц прав UI↔сервер | `ui/permissions_matrix_widget.py` | P1 | DONE |
| S-13 | "Экспорт в Excel" на самом деле CSV — переименована кнопка | `ui/crm_dialogs.py` | P2 | DONE |
| S-14 | Фильтр архива надзора — поле не возвращается API | `server/routers/supervision_router.py` | P2 | DONE |
| S-15 | quarter передаётся как 'Q1', а API ожидает int → ValueError | `ui/employee_reports_tab.py`, `database/db_manager.py` | P2 | DONE |

### Предложения по новым фичам (15)

| # | Фича | Приоритет |
|---|------|-----------|
| F-01 | Серверный endpoint `/api/contracts/check-number` | HIGH |
| F-02 | Единый CorporateReportBuilder (reportlab) | HIGH |
| F-03 | Планировщик дедлайнов (APScheduler) — автоуведомления | HIGH |
| F-04 | Мягкое удаление (soft delete) сотрудников, платежей | HIGH |
| F-05 | Серверный поиск `/api/clients?search=` | MEDIUM |
| F-06 | Справочник российских праздников | MEDIUM |
| F-07 | Диаграмма Ганта (план/факт) | MEDIUM |
| F-08 | Кнопка "Вернуть из архива" | MEDIUM |
| F-09 | Drill-down карточек дашборда | MEDIUM |
| F-10 | История назначений/переназначений | MEDIUM |
| F-11 | Push-уведомление при назначении | MEDIUM |
| F-12 | Сохранение фильтров в QSettings | LOW |
| F-13 | Индикатор загруженности в списке выбора | LOW |
| F-14 | Версионирование файлов на Яндекс.Диске | LOW |
| F-15 | Настоящий xlsx через openpyxl вместо CSV | LOW |
| F-16 | Управление агентами и городами через админку (перенос из договоров) | HIGH | DONE |
| F-17 | Soft delete для агентов и городов (status='удалён') | HIGH | DONE |

### QA-аудит: найденные проблемы (33 шт.)

Подробные отчёты:
- Права доступа: `docs/plan/crm-admin-agents-qa-audit/qa-permissions-report.md` (10 проблем)
- Основной CRM: `docs/plan/crm-admin-agents-qa-audit/qa-crm-main-report.md` (11 проблем)
- Надзорный CRM: `docs/plan/crm-admin-agents-qa-audit/qa-supervision-report.md` (12 проблем)

| # | Проблема | Severity | Статус |
|---|----------|----------|--------|
| QA-01 | `crm.update` → `crm_cards.update` — права не работали | P0 | **DONE** |
| QA-02 | `contracts.update` отсутствовал в системе прав | P0 | **DONE** |
| QA-03 | agents.delete, cities.* не в матрице прав UI | P1 | **DONE** |
| QA-04 | `contracts.update` не enforce на server endpoints | P1 | — |
| QA-05 | Messenger endpoints без require_permission | P1 | — |
| QA-06 | `agents.update` не в DEFAULT_ROLE_PERMISSIONS | P2 | — |
| QA-07 | Dashboard `active_orders` без фильтра project_type | P1 | — |
| QA-08 | Шаблонные карты без визуализации могут перейти в "3D визуализация" | P1 | — |
| QA-09 | supervision.status_changed_date не заполняется | P2 | — |
| QA-10 | commission не редактируется через API | P2 | — |

---

## Планируемые улучшения

### Приоритет 1 (Высокий)
- [x] Расширение покрытия тестами (E2E + Mock + UI) — 23/23 групп (100%), 600+ тестов
- [x] Автоматический деплой через CI/CD (GitHub Actions) — `.github/workflows/ci.yml`
- [ ] Push-уведомления между клиентами (WebSocket вместо polling)
- [x] Менеджер обновлений клиента (auto-update exe) — `utils/update_manager.py`

### Приоритет 2 (Средний)
- [x] Экспорт отчётов в PDF (все табы) — `utils/pdf_export.py`
- [x] Расширенная аналитика дашборда — графики: воронка, нагрузка, типы проектов
- [x] Полнотекстовый поиск по проектам — `GET /api/search` + `ui/global_search_widget.py`
- [ ] Мобильный веб-клиент (React/Vue)

### Приоритет 3 (Низкий)
- [ ] Мультиязычность (i18n)
- [ ] Тёмная тема
- [ ] Интеграция с 1С
- [ ] API для внешних интеграций

## Технический долг

| Область | Проблема | Приоритет | Статус |
|---------|----------|-----------|--------|
| ~~[ui/crm_tab.py](../ui/crm_tab.py)~~ | ~~17K+ строк — нужна декомпозиция~~ | ~~Высокий~~ | **DONE Phase 4** (3 368 строк, −81%) |
| ~~[server/main.py](../server/main.py)~~ | ~~8700+ строк — выделить routers~~ | ~~Высокий~~ | **DONE Phase 2+3** (424 строки, 22 роутера) |
| ~~[ui/contracts_tab.py](../ui/contracts_tab.py)~~ | ~~5K строк — нужна декомпозиция~~ | ~~Низкий~~ | **DONE Phase 5** (693 строки, contract_dialogs.py) |
| [ui/base_kanban_tab.py](../ui/base_kanban_tab.py) | Базовый класс KanbanTab — заготовка, требует полной интеграции | Средний | Заготовка в Phase 5 |
| Тесты | Нет unit-тестов для UI виджетов | Средний | — |
| Тесты | Нет нагрузочного тестирования | Низкий | — |
| Sync | QTimer polling → WebSocket | Средний | — |
| ~~Docker~~ | ~~Нет health checks~~ — **Реализовано** в `docker-compose.yml` | ~~Средний~~ | **DONE** |
| ~~Безопасность~~ | ~~Хардкод admin/admin123~~ — **Секреты вынесены в env** | ~~Высокий~~ | **DONE** |
| ~~Offline~~ | ~~Write-операции без offline-fallback~~ — **Все 34 write-метода: local-first + offline queue, 18 entity types** | ~~Высокий~~ | **DONE Phase 6.3** |
| ~~Offline~~ | ~~Бизнес-ошибки (409/400) попадают в offline-очередь~~ — **Фильтрация по sys.exc_info(): только сетевые ошибки** | ~~Высокий~~ | **DONE Phase 7.5** |
| ~~Стабильность~~ | ~~Segfault при drag-and-drop карточек CRM~~ — **CopyAction + deferred dialog + thread-safe signals** | ~~Критический~~ | **DONE Phase 7.5** |
| ~~Стабильность~~ | ~~Stale signal connections DataAccess→OfflineManager~~ — **Удалены мёртвые подключения** | ~~Высокий~~ | **DONE Phase 7.5** |
| ~~Авторизация~~ | ~~401 loop при длительной работе~~ — **Token 24h + auto-relogin + redirect header fix** | ~~Высокий~~ | **DONE Phase 7.5** |
| ~~Производительность~~ | ~~N+1 в statistics, нет пагинации, нет кэша~~ | ~~Высокий~~ | **DONE Phase 5** |
| Стиль | border-color без токена (#E0E0E0 вместо переменной) | Низкий | WARN Phase 5 |
| ~~Стиль~~ | ~~Неиспользуемый импорт в messenger_router.py~~ | ~~Низкий~~ | **DONE Phase 5.1** |
| ~~БД~~ | ~~f-string WHERE в db_manager.py (не whitelist)~~ — **_validate_columns + _build_set_clause** | ~~Средний~~ | **DONE Phase 5.1** |
| ~~Тесты~~ | ~~Дублирование в conftest.py~~ — **_factory_teardown helper** | ~~Низкий~~ | **DONE Phase 5.1** |
| ~~DataAccess~~ | ~~19 расхождений параметров DataAccess↔API↔DB~~ | ~~Высокий~~ | **DONE Phase 6.1** |
| ~~DataAccess~~ | ~~34 write-метода без local-first / offline queue~~ | ~~Высокий~~ | **DONE Phase 6.3** |
| ~~Timeline~~ | ~~`_calc_planned_dates` копируется в тест~~ — **Вынесена в `utils/timeline_calc.py`** | ~~Низкий~~ | **DONE** |
| ~~Timeline~~ | ~~Дублирование `_load_data` / `_load_data_background`~~ — **`_fetch_entries()` DRY** | ~~Низкий~~ | **DONE** |
