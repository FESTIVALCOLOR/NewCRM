# Исследование: Аудит тестового покрытия (test-coverage-90)
Дата: 2026-02-25
Режим: full

---

## 1. Текущее состояние (метрики)

| Метрика | Значение |
|---------|----------|
| Всего тест-файлов | 93 |
| Всего тестов | 2 032 |
| Всего строк в тестах | ~36 000 |
| Категорий тестов | 12 |
| Роутеров сервера | 24 |
| UI-модулей | 43 |
| Утилит | 27 |
| **pytest-cov line coverage** | **7%** (44 043 statements, 41 133 missed) |
| Файлов с 0% покрытия | 24 (ui: 15, utils: 9) |
| Файлов с 5-15% покрытия | 12 (крупнейшие модули UI) |

### Распределение по категориям

| Категория | Тестов | Файлов | Примечание |
|-----------|--------|--------|------------|
| `tests/e2e/` | 368 | 32 | Реальный HTTP к API серверу |
| `tests/ui/` | 443 | 13 | PyQt5 headless (offscreen) |
| `tests/client/` | 310 | 11 | Unit/mock клиентского кода |
| `tests/integration/` | 299 | 9 | Mock API + реальная SQLite |
| `tests/api_client/` | 173 | 4 | Mock тесты API client |
| `tests/edge_cases/` | 165 | 10 | Граничные случаи offline/sync |
| `tests/backend/` | 120 | 4 | Mock бэкенд модели/схемы |
| `tests/frontend/` | 66 | 2 | Mock PyQt5 виджеты |
| `tests/db/` | 42 | 4 | SQLite + миграции |
| `tests/smoke/` | 16 | 1 | Быстрая проверка API health |
| `tests/regression/` | 11 | 1 | Критические баги |
| `tests/load/` | 0 | 1 | locustfile (не pytest) |
| `testsprite_tests/` | ~99 | 99 | Внешний генератор (отдельно) |

---

## 2. Архитектура тестов

### 2.1 Структура директорий

```
tests/
├── conftest.py               # Корневые фикстуры: temp_db, mock_api_client, sample_* данные
├── e2e/
│   ├── conftest.py           # TestDataFactory, admin_token, test_employees (8 ролей), role_tokens
│   └── test_e2e_*.py         # 32 файла, реальные HTTP запросы
├── db/
│   ├── conftest.py           # db (DatabaseManager + все миграции), db_with_data
│   └── test_db_*.py          # 4 файла
├── client/
│   ├── conftest.py           # mock_db, mock_api_client, mock_data_access
│   └── test_*.py             # 11 файлов
├── ui/
│   ├── conftest.py           # _block_real_db, _block_real_api (autouse), test_db fixture
│   └── test_*.py             # 13 файлов
├── integration/              # 9 файлов, SQLite + mock API
├── edge_cases/               # 10 файлов
├── api_client/               # 4 файла
├── backend/                  # 4 файла
├── frontend/                 # 2 файла
├── regression/               # 1 файл
├── smoke/                    # 1 файл
├── load/                     # locustfile.py (не pytest)
├── visual/                   # 6 файлов (скрипты запуска, не pytest)
├── test_db_api_sync_audit.py # 1 статический анализ API-first паттерна
└── test_performance.py       # 0 тестов
```

### 2.2 Conftest фикстуры

**Корневой `tests/conftest.py`:**
- `temp_db` / `temp_db_path` — SQLite в tmpdir
- `db_with_data` — SQLite с тестовыми данными (4 сотрудника, 2 клиента, 2 договора)
- `mock_api_response` / `mock_api_client` / `api_client_offline` — фабрика mock HTTP
- `sample_employee/client/contract/crm_card/payment` — готовые словари данных
- `qapp` — QApplication для PyQt5 тестов

**E2E `tests/e2e/conftest.py`:**
- `admin_token` / `admin_headers` (scope=session) — реальная авторизация admin:admin123
- `test_employees` (scope=session) — создание 8 тестовых сотрудников (sdp, gap, designer, draftsman, manager, dan, senior_manager, surveyor) с __TEST__ префиксом
- `role_tokens` (scope=session) — Bearer токены для каждой роли
- `factory` (scope=session) / `module_factory` (scope=module) — `TestDataFactory` с tracked cleanup
- `TestDataFactory` — методы: `create_client`, `create_contract`, `create_crm_card`, `create_supervision_card`, `create_payment`, `create_file_record`, `create_rate`, `create_salary`
- Вспомогательные функции: `api_get`, `api_post`, `api_patch`, `api_put`, `api_delete`

**DB `tests/db/conftest.py`:**
- `db` (scope=function) — `DatabaseManager` + все миграции последовательно
- `db_with_data` — db с 1 клиентом, 1 договором, 1 сотрудником

**UI `tests/ui/conftest.py`:**
- `_block_real_db` (autouse) — блокирует production БД, разрешает только tmp/memory
- `_block_real_api` (autouse) — блокирует реальные HTTP запросы (monkeypatch requests)

### 2.3 CI Pipeline

Файл: `.github/workflows/ci.yml`

| Job | Что запускает | Зависимости |
|-----|---------------|-------------|
| `syntax-check` | py_compile server/*.py | — |
| `lint` | flake8 server/ (с 11 игнорами) | — |
| `test-db` | `pytest tests/db/` | syntax-check |
| `docker-build` | docker build ./server | syntax-check |
| `test-e2e` | `pytest tests/e2e/` | docker-build |

**Не запускаются в CI:**
- `tests/ui/` — требует PyQt5
- `tests/client/` — не подключены
- `tests/integration/` — не подключены
- `tests/edge_cases/` — не подключены
- `tests/backend/` — не подключены
- `tests/regression/` — не подключены
- `tests/smoke/` — не подключены
- `testsprite_tests/` — отдельный запуск

### 2.4 Соотношение типов тестов

| Тип | Количество | % |
|-----|-----------|---|
| E2E (реальный HTTP) | 368 | 18% |
| Unit/Mock (не требуют сервера) | 1 297 | 64% |
| Integration (SQLite + mock API) | 299 | 15% |
| DB (SQLite миграции) | 42 | 2% |
| Smoke | 16 | 1% |

---

## 3. Анализ качества E2E тестов

### 3.1 "Поверхностные" E2E тесты (по заданию)

| Файл | Тестов | assert всего | assert content (не status/isinstance) | Глубина | Вердикт |
|------|--------|-------------|--------------------------------------|---------|---------|
| `test_e2e_dashboard.py` | 8 | 12 | 0 | Только 200 + isinstance(dict) | SHALLOW |
| `test_e2e_statistics.py` | 9 | 12 | 0 | Только 200 + isinstance(list/dict) | SHALLOW |
| `test_e2e_reports.py` | 4 | 6 | 0 | Только 200, 1 негативный тест | SHALLOW |
| `test_e2e_agents_crud.py` | 5 | 7 | 1 | Один assert по имени агента | SHALLOW |
| `test_e2e_heartbeat.py` | 3 | 4 | 0 | Только 200 + isinstance(list/dict) | SHALLOW |
| `test_e2e_sync_data.py` | 5 | 9 | 0 | Только 200 + isinstance(list) | SHALLOW |
| `test_e2e_notifications.py` | 5 | 6 | 0 | Только 200 + isinstance(list) | SHALLOW |
| `test_e2e_project_templates.py` | 5 | 7 | 2 | "id" in data, len >= 1 | SHALLOW |

**Характеристика "поверхностных" тестов:**
- Паттерн: `assert resp.status_code == 200` + `assert isinstance(data, dict/list)` — ЕДИНСТВЕННЫЕ проверки
- Нет проверки ключей ответа (например: `total_paid`, `active_orders`, `by_role`)
- Нет проверки типов значений, диапазонов, бизнес-инвариантов
- Нет проверки что данные реально созданы/изменены в БД после операции

### 3.2 "Глубокие" E2E тесты (по заданию)

| Файл | Тестов | assert всего | assert content | Глубина | Вердикт |
|------|--------|-------------|----------------|---------|---------|
| `test_e2e_payments.py` | 22 | 45 | 21 | Поля summary, бизнес-инварианты | DEEP |
| `test_e2e_employees.py` | 20 | 60 | 30+ | Поля сотрудника, права, отчёты | DEEP |
| `test_e2e_rates.py` | 25 | 106 | 60+ | Типы тарифов, фильтры, CRUD полей | DEEP |
| `test_e2e_crm_lifecycle.py` | 18 | 33 | 13 | column_name, contract_id, executor_id | MEDIUM |
| `test_e2e_supervision.py` | 12 | 22 | 10 | dan_id, is_paused, column_name | MEDIUM |

**Паттерны эффективных тестов:**
1. **TestDataFactory** — данные создаются через factory с tracked cleanup, нет "мусора" после тестов
2. **Проверка конкретных полей** — `assert payment["contract_id"] == contract["id"]`, не просто `isinstance`
3. **Бизнес-инварианты** — `total_paid + total_pending == total` (с epsilon)
4. **Негативные тесты** — 404 для несуществующих ID, 400 для дублей, 401 без токена
5. **Каскадные действия** — создать → обновить → проверить изменение через GET
6. **Ролевое тестирование** — `role_tokens` для проверки прав разных ролей
7. **Setup/teardown через autouse fixture** — изоляция данных между тестами

---

## 4. Карта пробелов

### 4.1 Роутеры без прямых E2E тестов

| Роутер | Endpoints | Статус |
|--------|-----------|--------|
| `cities_router.py` | GET /, POST /, DELETE /{name} | БЕЗ ПРЯМОГО E2E ТЕСТА |

Примечание: `cities_router` косвенно упоминается в `test_e2e_contracts.py` (test_contract_with_all_cities) и `test_e2e_statistics.py` (test_cities_statistics), но CRUD города (добавление/удаление) не тестируется.

**Все остальные 23 роутера имеют прямые E2E тесты.**

### 4.2 UI модули без тестов

| Категория | Модули без тестов |
|-----------|------------------|
| Диалоги | `admin_dialog`, `supervision_dialogs`, `update_dialogs`, `messenger_admin_dialog`, `messenger_select_dialog` |
| Виджеты | `agents_cities_widget`, `chart_widget`, `supervision_timeline_widget`, `timeline_widget`, `variation_gallery_widget`, `file_gallery_widget`, `file_list_widget`, `file_preview_widget`, `global_search_widget` |
| Кастомные компоненты | `custom_combobox`, `custom_dateedit`, `bubble_tooltip`, `flow_layout`, `norm_days_settings_widget`, `permissions_matrix_widget` |
| Служебное | `crm_archive` |

Итого: **21 из 43 UI-модулей (49%)** не имеют тестов.

### 4.3 Утилиты без тестов

| Утилита | Что делает |
|---------|-----------|
| `add_indexes.py` | Создание индексов БД |
| `button_debounce.py` | Дебаунс кнопок UI |
| `calendar_helpers.py` | Вспомогательные функции для дат |
| `db_security.py` | Безопасность БД |
| `db_sync.py` | Синхронизация БД |
| `dialog_helpers.py` | Помощники диалогов |
| `message_helper.py` | Форматирование сообщений |
| `migrate_passwords.py` | Миграция паролей |
| `pdf_generator.py` | Генерация PDF |
| `preview_generator.py` | Генерация превью |
| `tab_helpers.py` | Вспомогательные функции для вкладок |
| `table_settings.py` | Настройки таблиц |
| `tooltip_fix.py` | Фикс тулttpov |
| `update_manager.py` | Управление обновлениями |

Итого: **14 из 27 утилит (52%)** не имеют тестов.

### 4.4 Тесты client/ — детально

| Файл | Тестов | Что покрывает |
|------|--------|---------------|
| `test_validators.py` | 64 | `utils/validators.py` — полное покрытие |
| `test_data_access.py` | 55 | `utils/data_access.py` — API-first fallback логика |
| `test_date_utils.py` | 43 | `utils/date_utils.py` — форматирование дат |
| `test_validation_bugs.py` | 28 | Регрессии: имена методов, DataAccess.delete_file_record |
| `test_api_client.py` | 31 | `utils/api_client/base.py` — offline/online переходы |
| `test_supervision_upload.py` | 21 | Загрузка файлов надзора |
| `test_planned_dates.py` | 15 | `utils/timeline_calc.calc_planned_dates()` |
| `test_login_widget.py` | 15 | `ui/login_window.py` |
| `test_password_utils.py` | 17 | `utils/password_utils.py` |
| `test_cache_manager.py` | 12 | `utils/cache_manager.py` |
| `test_unified_styles.py` | 9 | `utils/unified_styles.py` |

---

## 5. Антипаттерны и проблемы

### 5.1 Тесты проверяют переменные, не код

**Файлы:** `tests/edge_cases/test_offline_online.py`, `tests/api_client/test_offline.py`

Тесты в этих файлах **не импортируют реальный код** проекта. Они создают локальные переменные (например `OFFLINE_CACHE_DURATION = 5`) и проверяют их значение. Изменение в `utils/offline_manager.py` или `utils/api_client/base.py` НЕ вызовет провала этих тестов.

Пример:
```python
# test_offline_online.py строка 24-33
def test_offline_cache_duration_not_too_long(self):
    OFFLINE_CACHE_DURATION = 5  # Локальная переменная!
    assert OFFLINE_CACHE_DURATION <= 10  # Всегда True, не связано с кодом
```

Аналогично в `TestOfflineManagerCoordination`:
```python
offline_manager_should_ping = True  # Hardcoded boolean
assert should_ping is True          # Trivially true
```

### 5.2 CI запускает только 2 из 12 категорий тестов

CI pipeline (`ci.yml`) запускает только:
- `tests/db/` — 42 теста
- `tests/e2e/` — 368 тестов

**НЕ запускаются в CI:** `ui`, `client`, `integration`, `api_client`, `edge_cases`, `backend`, `regression`, `smoke` — суммарно 1 622 теста остаются без автоматической проверки в PR.

### 5.3 Поверхностные тесты не ловят контентные баги

Тесты `test_e2e_dashboard.py` / `test_e2e_statistics.py` только проверяют `200` и `isinstance(dict)`. Если API вернёт пустой словарь `{}` вместо `{"active_orders": 5, "total_orders": 10}`, тест пройдёт. Найденный в PR feat/admin-agents-cities-qa-audit баг (dashboard включал архивные статусы в active_orders) был покрыт отдельным `test_e2e_regression_qa_audit.py`.

### 5.4 Несоответствие схем в conftest

В `tests/conftest.py` (корневой) схема SQLite отличается от реальной `database/db_manager.py`:
- `payments` в корневом conftest не имеет полей `crm_card_id`, `supervision_card_id`, `is_manual`, `reassigned` (добавлены миграциями)
- `employees` не имеет полей `phone`, `department`, `status`, `birth_date` и др.
- Это означает что фикстуры из корневого conftest создают данные несовместимые с реальной схемой

### 5.5 Отсутствие тестов городов (cities) как CRUD

`cities_router.py` предоставляет GET (список), POST (добавить), DELETE (удалить с восстановлением удалённых). Ни один E2E тест не вызывает `POST /api/cities` или `DELETE /api/cities/{name}`. Тесты в `test_e2e_admin.py` (36 тестов) не охватывают управление городами.

### 5.6 Тесты visual/ — не pytest

`tests/visual/` содержит 6 скриптов (`auto_test.py`, `full_ui_test.py`, `qt_auto_login.py`, `run_and_capture.py`, `run_with_autologin.py`, `visual_tester.py`) — это скрипты запуска с захватом скриншотов, не pytest-тесты. В CI не интегрированы.

### 5.7 pdf_generator без тестов при PDF экспорте в E2E

`test_e2e_pdf_export.py` (4 теста) проверяет PDF endpoint через API, но `utils/pdf_generator.py` не имеет unit-тестов. Логика генерации PDF не проверяется изолированно.

---

## 6. Направление 3: Пробелы интеграции

### 6.1 Цепочка API → DataAccess → UI

- **DataAccess (utils/data_access.py)** тестируется в `tests/client/test_data_access.py` (55 тестов) — API-first с fallback логика через mock API client и mock DB.
- **Полная цепочка API → DataAccess → UI** в интеграционных тестах (`tests/integration/`) тестируется с: реальная SQLite DB + mock API client + mock PyQt5 виджеты. НЕ используется реальный API сервер.
- **Реальной сквозной цепочки** (реальный сервер + реальный DataAccess + реальный UI виджет) в автоматических тестах нет.

### 6.2 Тесты миграций БД

- `tests/db/test_db_migrations.py` (20 тестов) — проверяет существование таблиц и колонок в SQLite после применения всех миграций.
- `tests/db/test_schema_sync.py` — сравнение схем SQLite vs PostgreSQL с whitelist известных расхождений.
- Алгоритм миграций (`database/db_manager.py`) тестируется через `tests/db/conftest.py` — все миграции применяются последовательно к каждому тесту.
- **Нет тестов:** обновления с конкретных версий схемы (migration path tests), rollback миграций.

### 6.3 Тесты offline режима

| Тест | Реально тестирует | Реальный код? |
|------|-------------------|---------------|
| `tests/edge_cases/test_offline_online.py` | Числовые константы и переменные | НЕТ |
| `tests/api_client/test_offline.py` | Числовые константы и переменные | НЕТ |
| `tests/integration/test_offline_edge_cases.py` | Mock OfflineManager + SQLite | ЧАСТИЧНО |
| `tests/client/test_data_access.py` | DataAccess.offline fallback через mock | ДА |
| `tests/edge_cases/test_offline_queue_integrity.py` | Queue логика через mock | ЧАСТИЧНО |

Реальный `utils/offline_manager.py` тестируется только косвенно через `tests/integration/test_contracts_clients_api_integration.py` (импорт `OperationType`).

### 6.4 Тесты совместимости API/DB ключей

- `tests/test_db_api_sync_audit.py` — **статический анализ кода**: ищет вызовы `self.db.<write_method>()` без API-first паттерна. 1 тест.
- `tests/db/test_schema_sync.py` — сравнение колонок SQLite vs PostgreSQL.
- `utils/api_client/compat_mixin.py` — нет прямых тестов на совместимость ключей API ответов.
- Нет тестов которые проверяют что ключи в ответе сервера совпадают с тем что ожидает клиентский код.

---

## 7. Сырые данные для Design фазы

### 7.1 Детальная карта покрытия по модулям

| Модуль | Тип | Покрытие | Приоритет |
|--------|-----|----------|-----------|
| `server/routers/cities_router.py` | E2E | НЕТ ПРЯМОГО | ВЫСОКИЙ |
| `utils/pdf_generator.py` | Unit | НЕТ | ВЫСОКИЙ |
| `utils/calendar_helpers.py` | Unit | НЕТ | СРЕДНИЙ |
| `utils/button_debounce.py` | Unit | НЕТ | НИЗКИЙ |
| `utils/db_security.py` | Unit | НЕТ | ВЫСОКИЙ |
| `utils/db_sync.py` | Unit | НЕТ | СРЕДНИЙ |
| `utils/update_manager.py` | Unit | НЕТ | СРЕДНИЙ |
| `ui/admin_dialog.py` | UI | НЕТ | ВЫСОКИЙ |
| `ui/agents_cities_widget.py` | UI | НЕТ | ВЫСОКИЙ |
| `ui/supervision_timeline_widget.py` | UI | НЕТ | СРЕДНИЙ |
| `ui/timeline_widget.py` | UI | НЕТ | СРЕДНИЙ |
| `ui/permissions_matrix_widget.py` | UI | НЕТ | СРЕДНИЙ |
| `ui/norm_days_settings_widget.py` | UI | НЕТ | СРЕДНИЙ |
| `tests/e2e/test_e2e_dashboard.py` | E2E | ПОВЕРХНОСТНО | ВЫСОКИЙ |
| `tests/e2e/test_e2e_statistics.py` | E2E | ПОВЕРХНОСТНО | ВЫСОКИЙ |
| `tests/e2e/test_e2e_reports.py` | E2E | ПОВЕРХНОСТНО | ВЫСОКИЙ |
| `tests/e2e/test_e2e_heartbeat.py` | E2E | ПОВЕРХНОСТНО | НИЗКИЙ |
| `tests/e2e/test_e2e_sync_data.py` | E2E | ПОВЕРХНОСТНО | СРЕДНИЙ |
| `tests/e2e/test_e2e_notifications.py` | E2E | ПОВЕРХНОСТНО | СРЕДНИЙ |
| `tests/edge_cases/test_offline_online.py` | Unit | ФИКТИВНЫЙ | ВЫСОКИЙ |
| `tests/api_client/test_offline.py` | Unit | ФИКТИВНЫЙ | ВЫСОКИЙ |

### 7.2 CI Gap — категории не запускаемые в CI

Тесты не в CI pipeline (1 622 теста):
- `tests/ui/` — 443 теста (headless PyQt5, требует QT_QPA_PLATFORM=offscreen)
- `tests/client/` — 310 тестов
- `tests/integration/` — 299 тестов
- `tests/api_client/` — 173 теста
- `tests/edge_cases/` — 165 тестов
- `tests/backend/` — 120 тестов
- `tests/frontend/` — 66 тестов
- `tests/smoke/` — 16 тестов
- `tests/regression/` — 11 тестов

### 7.3 Ключевые антипаттерны с примерами кода

**Антипаттерн 1: Тест проверяет только статус-код без проверки данных**
```python
# tests/e2e/test_e2e_dashboard.py:51
def test_salaries_dashboard_stats(self, api_base, admin_headers):
    resp = api_get(api_base, "/api/dashboard/salaries", admin_headers)
    assert resp.status_code == 200  # ← ЕДИНСТВЕННАЯ проверка
```

**Антипаттерн 2: Тест проверяет только локальную переменную**
```python
# tests/edge_cases/test_offline_online.py:23-33
def test_offline_cache_duration_not_too_long(self):
    OFFLINE_CACHE_DURATION = 5  # ← Hardcoded, не из кода
    assert OFFLINE_CACHE_DURATION <= 10  # ← Trivially true
```

**Антипаттерн 3: Тест допускает оба варианта 200/422 без разбора**
```python
# tests/e2e/test_e2e_reports.py:41-42
def test_employee_report_missing_params(self, api_base, admin_headers):
    resp = api_get(api_base, "/api/reports/employee", admin_headers)
    assert resp.status_code in (200, 422)  # ← Не проверяет бизнес-логику
```

**Антипаттерн 4: Несовпадение схем в корневом conftest**
Файл `tests/conftest.py` строки 161-176: таблица `payments` создаётся без полей `crm_card_id`, `supervision_card_id`, `is_manual` которые добавляются миграциями в `database/db_manager.py`.

### 7.4 Эффективные паттерны для Design фазы

**Паттерн 1: TestDataFactory с tracked cleanup** (`tests/e2e/conftest.py:304-634`)
- Все созданные сущности отслеживаются в списках `_created_*`
- `cleanup_all()` удаляет в правильном порядке (salaries → rates → files → payments → supervision → crm → contracts → clients)
- `_force_cleanup_all_test_data()` подчищает через поиск по __TEST__ префиксу

**Паттерн 2: Проверка бизнес-инвариантов** (`tests/e2e/test_e2e_payments.py:365`)
```python
assert abs((total_paid + total_pending) - total) < 0.01
```

**Паттерн 3: Проверка конкретных полей с типами** (`tests/e2e/test_e2e_rates.py:43-47`)
```python
assert rate["id"] > 0
assert rate["project_type"] == "Индивидуальный"
assert rate["role"] == "Дизайнер"
assert rate["rate_per_m2"] == 100.0
```

**Паттерн 4: Conftest autouse блокировка production** (`tests/ui/conftest.py:24-60`)
- Блокирует DatabaseManager с production путями
- Блокирует реальные HTTP запросы через monkeypatch

**Паттерн 5: Ролевое тестирование** (`tests/e2e/conftest.py:269-297`)
- `role_tokens` — 8 ролей с Bearer токенами
- Используется в тестах прав доступа через `for role_key, headers in role_tokens.items()`

### 7.5 Метрики по "поверхностным" тестам для улучшения

| Файл | Тестов | Потенциальных content assert | Примерные проверки |
|------|--------|------------------------------|-------------------|
| `test_e2e_dashboard.py` | 8 | ~20 | active_orders, total_orders, archive_orders, статус полей |
| `test_e2e_statistics.py` | 9 | ~25 | поля general, employees, crm статистики |
| `test_e2e_reports.py` | 4 | ~8 | employee_id, employee_name, stages, payments |
| `test_e2e_sync_data.py` | 5 | ~10 | поля stage_executors, action_history, supervision_history |
| `test_e2e_notifications.py` | 5 | ~8 | id, message, is_read, created_at |
| `test_e2e_heartbeat.py` | 3 | ~4 | online_users структура |
