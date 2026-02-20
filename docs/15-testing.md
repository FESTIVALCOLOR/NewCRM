# Тестирование и стратегия

> Стратегия тестирования, покрытие, структура тестов, запуск.

## Структура тестов

```
tests/
├── e2e/                                    # E2E тесты (реальный API сервер)
│   ├── conftest.py                         # Авторизация, фабрика, 8 ролей, очистка
│   ├── test_e2e_auth_roles.py              # Авторизация + роли и доступы
│   ├── test_e2e_clients.py                 # CRUD клиентов
│   ├── test_e2e_contracts.py               # CRUD договоров
│   ├── test_e2e_crm_lifecycle.py           # Жизненный цикл CRM карточки
│   ├── test_e2e_crm_executors.py           # Назначение/переназначение исполнителей
│   ├── test_e2e_crm_deadlines.py           # Дедлайны карточек и исполнителей
│   ├── test_e2e_crm_approval.py            # Согласование
│   ├── test_e2e_supervision.py             # Авторский надзор
│   ├── test_e2e_supervision_timeline.py    # Таймлайн надзора (7 тестов)
│   ├── test_e2e_payments.py                # Платежи, расчёт
│   ├── test_e2e_files_db.py                # Файлы: CRUD + фильтрация
│   ├── test_e2e_files_yandex.py            # Файлы: Яндекс.Диск (21 тест)
│   ├── test_e2e_dashboard.py               # Дашборд и статистика
│   ├── test_e2e_statistics.py              # Расширенная статистика
│   ├── test_e2e_pdf_export.py              # PDF экспорт
│   ├── test_e2e_full_workflow.py           # Полный бизнес-цикл (16 шагов)
│   ├── test_e2e_employees.py               # CRUD сотрудников
│   ├── test_e2e_agents_crud.py             # CRUD агентов
│   ├── test_e2e_rates.py                   # Тарифы
│   ├── test_e2e_salaries.py                # Зарплаты
│   ├── test_e2e_reports.py                 # Отчёты
│   ├── test_e2e_locks.py                   # Блокировки записей (11 тестов)
│   ├── test_e2e_heartbeat.py              # Heartbeat + синхронизация (3 теста)
│   ├── test_e2e_notifications.py           # Уведомления
│   ├── test_e2e_project_templates.py       # Шаблоны проектов
│   ├── test_e2e_sync_data.py              # Синхронизация данных
│   ├── test_e2e_timeline.py               # Таблица сроков (15 тестов)
│   └── test_e2e_action_history.py          # История действий
├── api_client/                              # Mock CRUD тесты APIClient (77 тестов)
│   ├── __init__.py
│   └── test_api_crud.py                    # 13 классов: клиенты, договора, CRM, файлы и др.
├── db/                                      # DB тесты (temp SQLite)
│   ├── conftest.py                          # Временная БД
│   ├── test_db_migrations.py                # Миграции, таблицы, колонки
│   ├── test_db_file_queries.py              # Запросы файлов с фильтрами
│   └── test_db_crud.py                      # CRUD операции db_manager
├── ui/                                      # UI тесты (pytest-qt offscreen, 460 тестов)
│   ├── __init__.py
│   ├── conftest.py                          # Инфраструктура: QT_QPA_PLATFORM=offscreen, 11 ролей, автоочистка
│   ├── test_login.py                        # Авторизация (14 тестов)
│   ├── test_main_window.py                  # MainWindow: вкладки, навигация, lazy-loading (18 тестов)
│   ├── test_clients.py                      # Клиенты: CRUD, диалоги, валидация (36 тестов)
│   ├── test_contracts.py                    # Договора: CRUD, динамические поля (44 теста)
│   ├── test_employees.py                    # Сотрудники: CRUD, роли, фильтры (30 тестов)
│   ├── test_crm.py                          # CRM Kanban: карточки, workflow, перемещение (92 теста)
│   ├── test_crm_supervision.py              # CRM надзора: 12 стадий, timeline (40 тестов)
│   ├── test_salaries.py                     # Зарплаты: вкладки, фильтры, диалоги (34 теста)
│   ├── test_reports.py                      # Отчёты: 4 вкладки, фильтры (8 тестов)
│   ├── test_dashboard.py                    # Дашборд: карточки метрик, виджеты (14 тестов)
│   ├── test_roles.py                        # Ролевое тестирование: 9 должностей + 2 двойные (95 тестов)
│   ├── test_data_access.py                  # DataAccess: CRUD, mock DB (17 тестов)
│   └── test_edge_cases.py                   # Edge cases: пустые данные, экстремальные значения (18 тестов)
├── client/                                  # Клиентские тесты
│   ├── test_validators.py                   # Валидаторы (75+ тестов)
│   ├── test_cache_manager.py                # Кэширование (15 тестов)
│   └── test_unified_styles.py               # QSS стили (9 тестов)
├── load/                                    # Нагрузочные тесты (locust)
│   └── locustfile.py                        # CRMUser: 9 task-методов, JWT авторизация
├── test_db_api_sync_audit.py                # Аудит: self.db write без API
└── test_performance.py                      # Производительность
```

## Команды запуска

```bash
# Установка зависимостей
pip install -r requirements-dev.txt

# DB тесты (не нужен сервер)
pytest tests/db/ -v

# E2E тесты (нужен API сервер!)
pytest tests/e2e/ -v --timeout=60

# Критические тесты
pytest tests/ -m critical -v --timeout=60

# Полный прогон
pytest tests/e2e/ tests/db/ -v --timeout=60

# UI тесты (pytest-qt offscreen, не нужен рабочий стол)
pytest tests/ui/ -v --timeout=30

# Mock CRUD тесты api_client.py (без сервера)
pytest tests/api_client/ -v

# Клиентские unit-тесты (без сервера)
pytest tests/client/ -v

# С покрытием (optional)
pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

# Нагрузочные тесты (отдельно, нужен locust + сервер)
locust -f tests/load/locustfile.py --host http://147.45.154.193:8000
locust -f tests/load/locustfile.py --host http://147.45.154.193:8000 --headless -u 10 -r 2 -t 30s
```

## Тестовые данные

### Префикс

Все тестовые данные создаются с префиксом `__TEST__`:
```python
client_name = "__TEST__Тестовый клиент"
contract_number = "__TEST__01/2026"
```

### 8 тестовых сотрудников

| Роль | Должность |
|------|-----------|
| СДП | СДП |
| ГАП | ГАП |
| Дизайнер | Дизайнер |
| Чертёжник | Чертёжник |
| Менеджер | Менеджер |
| ДАН | ДАН |
| Старший менеджер | Старший менеджер проектов |
| Замерщик | Замерщик |

### Очистка

Session-scoped fixtures автоматически удаляют все `__TEST__` данные после завершения тестов.

### Яндекс.Диск

Все файловые операции в тестах — в папке `__TEST__/`, которая удаляется после тестов.

## Маркеры pytest ([pytest.ini](../pytest.ini))

```ini
markers =
    backend: Backend tests
    frontend: Frontend tests
    api_client: API Client tests
    integration: Integration tests
    edge_cases: Edge cases tests
    slow: Slow tests (skip: -m "not slow")
    critical: Critical tests
    e2e: End-to-end tests
    db: Database tests
    order: Test execution order
    ui: Qt widget tests (pytest-qt offscreen)
```

## Матрица покрытия

### Покрытые модули

| Модуль | E2E тесты | DB тесты | Уровень |
|--------|-----------|----------|---------|
| Авторизация | test_e2e_auth_roles | — | Высокий |
| Клиенты | test_e2e_clients | test_db_crud | Высокий |
| Договоры | test_e2e_contracts | test_db_crud | Высокий |
| CRM карточки | test_e2e_crm_lifecycle | — | Высокий |
| Исполнители | test_e2e_crm_executors | — | Средний |
| Дедлайны | test_e2e_crm_deadlines | — | Средний |
| Согласование | test_e2e_crm_approval | — | Средний |
| Надзор | test_e2e_supervision | — | Средний |
| Платежи | test_e2e_payments | — | Высокий |
| Файлы (DB) | test_e2e_files_db | test_db_file_queries | Высокий |
| Файлы (Я.Диск) | test_e2e_files_yandex (21) | — | Высокий |
| Дашборд | test_e2e_dashboard | — | Средний |
| PDF экспорт | test_e2e_pdf_export | — | Низкий |
| Миграции | — | test_db_migrations | Высокий |
| Полный workflow | test_e2e_full_workflow | — | Высокий |
| Таблица сроков | test_e2e_timeline (15) | — | Высокий |
| Heartbeat | test_e2e_heartbeat (3) | — | Средний |
| Блокировки | test_e2e_locks (11) | — | Высокий |
| Таймлайн надзора | test_e2e_supervision_timeline (7) | — | Средний |
| APIClient CRUD | test_api_crud (77) | — | Высокий |
| Валидаторы | — | test_validators (75+) | Высокий |
| Кэширование | — | test_cache_manager (15) | Средний |
| QSS стили | — | test_unified_styles (9) | Низкий |

### UI тесты (pytest-qt offscreen) — 460 тестов

> Подробная документация: [20-ui-testing.md](20-ui-testing.md)

| Файл | Тестов | Покрытие |
|------|:------:|----------|
| test_login.py | 14 | Окно логина, поля ввода, валидация, frameless window |
| test_main_window.py | 18 | Вкладки по ролям, навигация, lazy-loading, статус-бар |
| test_clients.py | 36 | Полный CRUD (физ.+юр.), диалоги, валидация, поиск |
| test_contracts.py | 44 | CRUD, динамические поля по типу, подтипы, валидация |
| test_employees.py | 30 | CRUD, диалоги, фильтры, должности, двойные роли |
| test_crm.py | 92 | Kanban, перемещение карточек, workflow, дедлайны, исполнители |
| test_crm_supervision.py | 40 | 12 стадий, timeline, карточки, архив, фильтры |
| test_salaries.py | 34 | 5 вкладок, фильтры, PaymentDialog, роли |
| test_reports.py | 8 | 4 вкладки статистики, фильтры, lazy-loading |
| test_dashboard.py | 14 | 6 карточек метрик, DashboardWidget, MetricCard |
| test_roles.py | 95 | 9 должностей + 2 двойные роли, видимость вкладок, CRM permissions |
| test_data_access.py | 17 | DataAccess CRUD, mock DB, изоляция данных |
| test_edge_cases.py | 18 | Пустые данные, экстремальные значения, offline, rapid interactions |

### Mock CRUD тесты APIClient — 77 тестов

| Класс | Тестов | Покрытие |
|-------|:------:|----------|
| TestClientsCRUD | 6 | get_clients, get_client, create, update, delete |
| TestContractsCRUD | 7 | get_contracts, get_contract, create, update, delete, check_number |
| TestEmployeesCRUD | 6 | get_employees, get_by_position, get, create, update, delete |
| TestCRMCardsCRUD | 7 | get_cards, get_card, create, update, move, delete |
| TestSupervisionCRUD | 6 | get_cards, create, update, move, pause, resume |
| TestPaymentsCRUD | 6 | get_for_contract, create, get, update, delete, mark_paid |
| TestRatesCRUD | 5 | get_rates, get_rate, create, update, delete |
| TestSalariesCRUD | 5 | get_salaries, get, create, update, delete |
| TestFilesCRUD | 3 | get_contract_files, create_record, delete_record |
| TestYandexDiskMethods | 5 | upload, create_folder, public_link, list, delete |
| TestTimelineMethods | 7 | get, init, reinit, update_entry, summary, export_excel/pdf |
| TestErrorHandling | 6 | 401, 403, 404, 500, timeout, connection_error |
| TestOfflineCache | 8 | is_recently_offline, mark_offline, reset, force_check |

### Клиентские unit-тесты

| Файл | Тестов | Покрытие |
|------|:------:|----------|
| test_validators.py | 75+ | Валидаторы: поля, форматы, длины |
| test_cache_manager.py | 15 | Кэширование: get, set, expire, clear |
| test_unified_styles.py | 9 | QSS: селекторы, цвета, balanced braces |

### Ранее непокрытые — теперь покрыты

| Модуль / Endpoint | Тестовый файл | Статус |
|-------------------|---------------|--------|
| api_client.py CRUD | test_api_crud.py (77 тестов) | Покрыт |
| unified_styles.py | test_unified_styles.py (9 тестов) | Покрыт |
| cache_manager.py | test_cache_manager.py (15 тестов) | Покрыт |
| validators.py | test_validators.py (75+ тестов) | Покрыт |
| icon_loader.py | test_widgets.py (3 теста) | Покрыт |
| Timeline init/reinit/export | test_e2e_timeline.py (15 тестов) | Покрыт |
| Supervision timeline | test_e2e_supervision_timeline.py (7 тестов) | Покрыт |
| Sync heartbeat | test_e2e_heartbeat.py (3 теста) | Покрыт |
| Sync lock/unlock | test_e2e_locks.py (11 тестов) | Покрыт |
| Yandex Disk API | test_e2e_files_yandex.py (21 тест) | Покрыт |

## Аудит синхронизации ([tests/test_db_api_sync_audit.py](../tests/test_db_api_sync_audit.py))

Автоматический статический анализ:
- Сканирует 10 UI файлов на `self.db.<write_method>()`
- Проверяет наличие API-first обёртки
- Распознаёт 5 паттернов: API-first+fallback, offline else, local-first+sync, offline queue, `_locally()` хелперы
- `KNOWN_EXCEPTIONS` — осознанно локальные методы
- Не требует запущенного сервера

```bash
python tests/test_db_api_sync_audit.py
pytest tests/test_db_api_sync_audit.py -v
```

## Нагрузочные тесты (locust)

```
tests/load/
├── __init__.py
└── locustfile.py    # CRMUser с 9 task-методами, JWT авторизация
```

**Task-методы:** get_clients (×5), get_contracts (×5), get_crm_cards (×3), get_supervision (×3), get_employees (×2), get_dashboard (×2), get_payments (×1), get_rates (×1), health_check (×1).

```bash
# Web UI (локальный дашборд)
locust -f tests/load/locustfile.py --host http://147.45.154.193:8000

# Headless (CI/CD)
locust -f tests/load/locustfile.py --host http://147.45.154.193:8000 --headless -u 10 -r 2 -t 30s
```

Зависимость: `locust>=2.29.0` в `requirements-dev.txt`.

## Рекомендации по расширению тестов (выполнено)

1. ~~**Mock-тесты для api_client.py**~~ — test_api_crud.py, 77 тестов
2. ~~**Unit-тесты для validators.py**~~ — test_validators.py, 75+ тестов
3. ~~**Расширение UI тестов**~~ — test_edge_cases.py, 18 тестов (пустые данные, экстремальные значения, offline)
4. ~~**Нагрузочные тесты**~~ — locustfile.py, 9 task-методов
