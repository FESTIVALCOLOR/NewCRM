# Дорожная карта: Тестовое покрытие 90-95%
Дата: 2026-02-26
Режим: full
Основа: [research.md](research.md) | [design.md](design.md)

---

## Оглавление

### Часть 1: Инфраструктура (фундамент)
- ✅ INFRA-01: Исправить корневой conftest.py (схема БД)
- ✅ INFRA-02: Добавить CI job `test-client`
- ✅ INFRA-03: Добавить CI job `test-backend`
- ✅ INFRA-04: Настроить pytest-cov в CI
- ✅ INFRA-05: Создать fixtures для contract тестов

### Часть 2: Этап 1 — Усиление существующих тестов
- ✅ E2E-DEEP-01: Углубить test_e2e_dashboard.py
- ✅ E2E-DEEP-02: Углубить test_e2e_statistics.py
- ✅ E2E-DEEP-03: Углубить test_e2e_reports.py
- ✅ E2E-DEEP-04: Углубить test_e2e_agents_crud.py
- ✅ E2E-DEEP-05: Углубить test_e2e_sync_data.py
- ✅ E2E-DEEP-06: Углубить test_e2e_notifications.py
- ✅ E2E-DEEP-07: Углубить test_e2e_heartbeat.py
- ✅ E2E-DEEP-08: Углубить test_e2e_project_templates.py
- ✅ REWRITE-01: Переписать фиктивные offline тесты

### Часть 3: Этап 2 — Закрытие пробелов
- ✅ E2E-NEW-01: E2E тесты для cities_router
- ✅ UTIL-01: Unit тесты для db_security.py
- ✅ UTIL-02: Unit тесты для pdf_generator.py
- ✅ UTIL-03: Unit тесты для calendar_helpers.py
- ✅ UTIL-04: Unit тесты для button_debounce.py
- ✅ UTIL-05: Unit тесты для db_sync.py
- ✅ UTIL-06: Unit тесты для update_manager.py
- ✅ UTIL-07: Unit тесты для остальных утилит (пакет)
- ✅ OFFLINE-01: Unit тесты для OfflineManager (реальные)
- ✅ CONTRACT-01: Contract тесты API-DB ключей
- ✅ INFRA-06: CI job test-contract
- ✅ UI-01: Тесты admin_dialog.py
- ✅ UI-02: Тесты agents_cities_widget.py
- ✅ UI-03: Тесты permissions_matrix_widget.py
- ✅ UI-04: Тесты supervision_timeline_widget.py
- ✅ UI-05: Тесты timeline_widget.py
- ✅ UI-06: Тесты для остальных 15 UI модулей (пакет)

### Часть 4: Этап 3 — Hardening
- ✅ MIGRATION-01: Тесты путей миграции БД
- ✅ PROPERTY-01: Property-based тесты валидаторов
- ✅ ROLES-01: Негативные ролевые E2E тесты
- ✅ DUAL-MODE-01: Тесты DataAccess двухрежимности
- ✅ UI-INTERACT-01: Расширенные UI тесты взаимодействий
- ✅ REGRESSION-01: Автоматизация regression suite

### Часть 5: Дополнительные этапы (путь к 90%)

#### Этап 4: Глубокие UI тесты
- ⬜ UI-DEEP-01: Глубокие тесты crm_tab.py (QTest взаимодействия, фильтры, CRUD)
- ⬜ UI-DEEP-02: Глубокие тесты salaries_tab.py (расчёт зарплат, фильтры, начисления)
- ⬜ UI-DEEP-03: Глубокие тесты employees_tab.py (CRUD, права, фильтры)
- ⬜ UI-DEEP-04: Глубокие тесты crm_card_edit_dialog.py (редактирование карточки CRM)
- ⬜ UI-DEEP-05: Глубокие тесты supervision_card_edit_dialog.py (карточка авторского надзора)

#### ✅ Этап 5: Полное покрытие data_access.py (реализовано)
- ✅ DA-01: Полное покрытие data_access.py (+169 тестов)

#### Этап 6: Расширенные E2E роутеров
- ✅ E2E-ROUTER-01: Углублённые E2E — clients, contracts, action_history, reports, messenger, supervision, crm_lifecycle (+86 тестов)
- ⬜ E2E-ROUTER-02: Углублённые E2E — dashboard_router (edge cases, пустые данные, фильтры)
- ⬜ E2E-ROUTER-03: Углублённые E2E — statistics_router (все виды статистик, фильтры по периодам)
- ⬜ E2E-ROUTER-04: Углублённые E2E — оставшиеся роутеры (agents, cities, payments, projects, templates)

#### Этап 7: Полное покрытие database/db_manager.py
- ⬜ DB-DEEP-01: Тесты CRUD операций db_manager.py (contracts, clients, agents)
- ⬜ DB-DEEP-02: Тесты миграций и индексов db_manager.py
- ⬜ DB-DEEP-03: Тесты offline-очереди и синхронизации db_manager.py

#### Этап 8: Полное покрытие UI диалогов
- ⬜ UI-DIALOG-01: Тесты contract_dialogs.py (все диалоги контрактов)
- ⬜ UI-DIALOG-02: Тесты crm_dialogs.py (все диалоги CRM)
- ⬜ UI-DIALOG-03: Тесты supervision_dialogs.py (диалоги авторского надзора)
- ⬜ UI-DIALOG-04: Тесты остальных диалогов (payments, employees, settings)

#### Этап 9: Покрытие мелких модулей + gaps
- ⬜ SMALL-01: Покрытие config.py, constants.py, icon_loader.py
- ⬜ SMALL-02: Покрытие api_client.py (все ветки, ошибки, retry)
- ⬜ SMALL-03: Gaps — покрытие пропущенных веток в уже покрытых модулях

### Часть 7: Целевые метрики
### Часть 8: Порядок реализации
### Приложение A: Сводная таблица задач
### Приложение B: Чеклист Planner Agent

---

## Исходное состояние

| Метрика | Значение |
|---------|----------|
| Line coverage (pytest-cov) | **7%** (2 910 / 44 043 statements) |
| Missed statements | 41 133 |
| Тестов в CI | 410 (test-db: 42, test-e2e: 368) |
| Тестов НЕ в CI | 1 622 |
| Категорий в CI | 2 из 12 |
| UI модулей без тестов | 21 из 43 (49%) |
| Утилит без тестов | 14 из 27 (52%) |
| Роутеров без E2E | 1 (cities_router) |
| Фиктивных тестов | ~32 (проверяют локальные переменные) |

---

## Часть 1: Инфраструктура (фундамент)

Задачи, которые нужно выполнить ДО написания тестов.

---

### INFRA-01: Исправить корневой conftest.py (схема БД)

- **Файлы изменения:** `tests/conftest.py`
- **Исходный код:** `database/db_manager.py` (эталон схемы)
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Оценка:** ~2 часа Claude
- **Прирост покрытия:** 0 п.п. (но корректирует все последующие тесты)

**Проблема (research.md секция 5.4):** Корневой `tests/conftest.py` создаёт таблицы вручную (строки 80-200), и схема отличается от реального `db_manager.py`:
- `payments` нет полей `supervision_card_id`, `is_manual`
- `employees` нет полей `phone`, `email`, `address`, `birth_date`, `status`, `secondary_position`
- `contracts` нет полей `city`, `agent_type`, `total_amount`, `advance_payment`, `additional_payment`, `third_payment`, `contract_period`, `termination_reason`

**Конкретные действия:**
1. Добавить в `employees` CREATE TABLE: `phone TEXT`, `email TEXT`, `address TEXT`, `birth_date TEXT`, `status TEXT DEFAULT 'active'`, `secondary_position TEXT`, `department TEXT`
2. Добавить в `contracts` CREATE TABLE: `city TEXT`, `agent_type TEXT`, `total_amount REAL`, `advance_payment REAL`, `additional_payment REAL`, `third_payment REAL`, `contract_period TEXT`, `termination_reason TEXT`
3. Добавить в `payments` CREATE TABLE: `supervision_card_id INTEGER`, `is_manual INTEGER DEFAULT 0`
4. Добавить таблицу `cities`: `id INTEGER PRIMARY KEY AUTOINCREMENT`, `name TEXT UNIQUE`, `status TEXT DEFAULT 'активный'`
5. Обновить фикстуры `sample_employee`, `sample_client`, `sample_contract`, `sample_payment` для соответствия новым полям
6. Запустить ВСЕ категории тестов локально для проверки что ничего не сломалось

**Тест верификации:**
```
test_conftest_schema_matches_db_manager — создать БД через conftest, создать через db_manager, сравнить колонки всех таблиц
```

---

### INFRA-02: Добавить CI job `test-client`

- **Файлы изменения:** `.github/workflows/ci.yml`
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Оценка:** ~1 час Claude
- **Прирост покрытия:** 0 п.п. (но 321 тест попадают в CI)

**Конкретные действия:**
Добавить в `.github/workflows/ci.yml` новый job:
```yaml
test-client:
  runs-on: ubuntu-latest
  needs: [syntax-check]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Установка зависимостей
      run: |
        pip install pytest pytest-timeout pytest-order requests urllib3 pydantic pydantic-settings
        pip install bcrypt PyJWT cryptography
    - name: Запуск Client тестов
      run: pytest tests/client/ tests/regression/ -v --timeout=30 -p no:qt
```

**Тесты в CI:** +321 (310 client + 11 regression)

---

### INFRA-03: Добавить CI job `test-backend`

- **Файлы изменения:** `.github/workflows/ci.yml`
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Оценка:** ~1 час Claude
- **Прирост покрытия:** 0 п.п. (но 757 тестов попадают в CI)

**Конкретные действия:**
```yaml
test-backend:
  runs-on: ubuntu-latest
  needs: [syntax-check]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Установка зависимостей
      run: |
        pip install pytest pytest-timeout pytest-order requests urllib3 pydantic pydantic-settings
        pip install bcrypt PyJWT cryptography
    - name: Запуск Backend тестов
      run: pytest tests/backend/ tests/api_client/ tests/integration/ tests/edge_cases/ -v --timeout=60 -p no:qt
```

**Тесты в CI:** +757 (120 backend + 173 api_client + 299 integration + 165 edge_cases)

---

### INFRA-04: Настроить pytest-cov в CI

- **Файлы изменения:** `.github/workflows/ci.yml`, `pytest.ini` или `pyproject.toml`
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-02, INFRA-03
- **Оценка:** ~1 час Claude
- **Прирост покрытия:** 0 п.п. (метрика, не покрытие)

**Конкретные действия:**
1. Добавить `pytest-cov` в зависимости CI:
   ```
   pip install pytest-cov
   ```
2. Добавить флаги coverage в каждый test-* job:
   ```
   pytest tests/client/ --cov=utils --cov=database --cov-report=xml --cov-report=term-missing
   ```
3. Добавить upload coverage artifact (xml) в каждый job
4. Добавить step `coverage combine` + summary в отдельный job, зависящий от всех test-* jobs

---

### INFRA-05: Создать fixtures для contract тестов

- **Файлы создания:** `tests/contract/__init__.py`, `tests/contract/conftest.py`
- **Исходный код:** `server/schemas.py`, `database/db_manager.py`, `utils/data_access.py`
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Оценка:** ~2 часа Claude
- **Прирост покрытия:** 0 п.п. (подготовка)

**Конкретные действия:**
1. Создать `tests/contract/conftest.py` с фикстурами:
   - `schema_fields` -- парсит Pydantic Response-модели из `server/schemas.py`, возвращает `{model_name: set(field_names)}`
   - `db_method_keys` -- вызывает методы `db_manager` с тестовыми данными, собирает ключи возвращаемых словарей
   - `api_response_samples` -- загружает JSON файлы из `tests/contract/fixtures/` с образцами реальных API ответов
2. Создать `tests/contract/fixtures/` с JSON образцами ответов каждого endpoint (собрать через curl)

---

## Часть 2: Этап 1 -- Усиление существующих тестов (3-4 дня Claude)

Переписать 8 поверхностных E2E тестов, добавить data assertions. Заменить фиктивные offline тесты.

---

### E2E-DEEP-01: Углубить test_e2e_dashboard.py

- **Файл тестов:** `tests/e2e/test_e2e_dashboard.py` (модификация)
- **Исходный код:** `server/routers/dashboard_router.py` (1028 строк)
- **Новых тестовых функций:** 0 (модификация 8 существующих)
- **Новых assert:** +22
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Прирост покрытия:** +0.8 п.п. (dashboard_router ~350 executable строк, покрытие вырастет с ~30% до ~65%)
- **Оценка:** ~1.5 часа Claude
- **Привязка к багу:** research.md секция 5.3 -- dashboard включал архивные статусы в active_orders; test_e2e_regression_qa_audit.py поймал, но основной тест нет

**Конкретные тесты и проверки:**

| Тест | Добавить assert | Что проверяется |
|------|----------------|-----------------|
| `test_clients_dashboard_stats` | `assert "total_clients" in data`, `assert "total_individual" in data`, `assert "total_legal" in data`, `assert isinstance(data["total_clients"], int)`, `assert data["total_clients"] >= 0` | Ключи и типы ответа clients dashboard |
| `test_contracts_dashboard_stats` | `assert "individual_orders" in data`, `assert "template_orders" in data`, `assert isinstance(data["individual_orders"], (int, dict))` | Ключи contracts dashboard, структура по годам |
| `test_crm_dashboard_stats` | `assert "total_orders" in data`, `assert "active_orders" in data`, `assert "archive_orders" in data`, `assert data["active_orders"] >= 0` | Бизнес-инвариант: active + archive <= total |
| `test_employees_dashboard_stats` | `assert "active_employees" in data`, `assert "reserve_employees" in data`, `assert isinstance(data["active_employees"], int)` | Ключи employees dashboard |
| `test_salaries_dashboard_stats` | `data = resp.json()`, `assert isinstance(data, dict)`, `assert "total_paid" in data`, `assert isinstance(data["total_paid"], (int, float))` | Ключи и типы salaries |
| `test_supervision_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))` | Базовая структура supervision stats |
| `test_contracts_by_period` | `data = resp.json()`, `assert isinstance(data, (dict, list))` | Структура contracts-by-period |
| `test_general_statistics` | `data = resp.json()`, `assert isinstance(data, dict)`, `assert "total_contracts" in data or "total" in data` | Ключи general statistics |

---

### E2E-DEEP-02: Углубить test_e2e_statistics.py

- **Файл тестов:** `tests/e2e/test_e2e_statistics.py` (модификация)
- **Исходный код:** `server/routers/statistics_router.py` (891 строка)
- **Новых тестовых функций:** 0 (модификация 9 существующих)
- **Новых assert:** +27
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Прирост покрытия:** +0.7 п.п. (statistics_router ~600 executable строк, покрытие вырастет с ~20% до ~50%)
- **Оценка:** ~1.5 часа Claude

**Конкретные тесты и проверки:**

| Тест | Добавить assert |
|------|----------------|
| `test_dashboard_statistics` | `assert "total_contracts" in data or len(data) > 0`, `assert isinstance(data.get("total_contracts", 0), (int, float))` |
| `test_employees_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))`, проверка наличия employee_id или employee_name в элементах |
| `test_agent_types_statistics` | `for item in data: assert isinstance(item, str)` -- проверка что каждый элемент строка |
| `test_cities_statistics` | `for item in data: assert isinstance(item, (str, dict))` -- проверка структуры |
| `test_projects_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))`, проверка ключей |
| `test_supervision_filtered_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))` |
| `test_crm_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))`, проверка полей crm |
| `test_crm_filtered_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))`, проверка что фильтрация работает |
| `test_approvals_statistics` | `data = resp.json()`, `assert isinstance(data, (dict, list))` |

---

### E2E-DEEP-03: Углубить test_e2e_reports.py

- **Файл тестов:** `tests/e2e/test_e2e_reports.py` (модификация)
- **Исходный код:** `server/routers/reports_router.py` (328 строк)
- **Новых тестовых функций:** +3 (новые кейсы)
- **Новых assert:** +12
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Прирост покрытия:** +0.3 п.п.
- **Оценка:** ~1 час Claude

**Конкретные тесты и проверки:**

Модификация существующих:
| Тест | Добавить assert |
|------|----------------|
| `test_employee_report_data` | `data = resp.json()`, проверка наличия ключей `employee_id` или `employee_name`, `stages`, `payments` |
| `test_employee_report_by_type` | `data = resp.json()`, `assert isinstance(data, (dict, list))`, проверка structure |
| `test_employee_report_missing_params` | Заменить `assert resp.status_code in (200, 422)` на конкретный ожидаемый статус + проверка тела ответа |

Новые тесты:
| Тест | Что проверяет |
|------|---------------|
| `test_employee_report_data_has_stages` | GET /api/reports/employee с конкретным employee_id -- проверить что stages список, каждый элемент имеет stage_name |
| `test_employee_report_by_type_returns_list` | GET /api/reports/employee-report -- проверить что ответ содержит список сотрудников с полями |
| `test_employee_report_nonexistent_employee` | GET /api/reports/employee?employee_id=999999 -- проверить 200 с пустыми данными или 404 |

---

### E2E-DEEP-04: Углубить test_e2e_agents_crud.py

- **Файл тестов:** `tests/e2e/test_e2e_agents_crud.py` (модификация)
- **Исходный код:** `server/routers/agents_router.py` (136 строк)
- **Новых тестовых функций:** +2
- **Новых assert:** +8
- **Приоритет:** P1 -- важно
- **Зависимости:** нет
- **Прирост покрытия:** +0.1 п.п.
- **Оценка:** ~45 мин Claude

Модификация: каждый существующий тест проверяет `id`, `name`, `agent_type`, `is_active` в ответе.

Новые:
| Тест | Что проверяет |
|------|---------------|
| `test_update_agent_name` | PATCH /api/agents/{id} -- обновить имя, GET проверить изменение |
| `test_create_duplicate_agent` | POST /api/agents/ с существующим именем -- проверить 400 или 409 |

---

### E2E-DEEP-05: Углубить test_e2e_sync_data.py

- **Файл тестов:** `tests/e2e/test_e2e_sync_data.py` (модификация)
- **Исходный код:** `server/routers/sync_router.py` (143 строки)
- **Новых тестовых функций:** +2
- **Новых assert:** +12
- **Приоритет:** P1 -- важно
- **Зависимости:** нет
- **Прирост покрытия:** +0.2 п.п.
- **Оценка:** ~45 мин Claude

Модификация существующих -- для каждого `isinstance(data, list)` добавить:
```python
if data:  # если есть данные
    item = data[0]
    assert "id" in item
    # + специфичные поля для каждого endpoint
```

| Тест | Добавить проверку полей |
|------|------------------------|
| `test_sync_stage_executors` | `crm_card_id`, `stage_name`, `executor_id`, `role` |
| `test_sync_approval_deadlines` | `crm_card_id`, `deadline` |
| `test_sync_action_history` | `entity_type`, `entity_id`, `action_type`, `created_at` |
| `test_sync_supervision_history` | `supervision_card_id`, `action_type` |

Новые:
| Тест | Что проверяет |
|------|---------------|
| `test_sync_stage_executors_after_assignment` | Создать CRM карточку + назначить исполнителя -> GET sync -> проверить что executor присутствует |
| `test_sync_action_history_after_move` | Переместить CRM карточку -> GET sync/action-history -> проверить что запись существует |

---

### E2E-DEEP-06: Углубить test_e2e_notifications.py

- **Файл тестов:** `tests/e2e/test_e2e_notifications.py` (модификация)
- **Исходный код:** `server/routers/` (notifications в crm_router.py)
- **Новых тестовых функций:** +2
- **Новых assert:** +10
- **Приоритет:** P1 -- важно
- **Зависимости:** нет
- **Прирост покрытия:** +0.1 п.п.
- **Оценка:** ~45 мин Claude

Модификация:
| Тест | Добавить assert |
|------|----------------|
| `test_get_notifications` | `if data: item = data[0]; assert "id" in item; assert "message" in item; assert "is_read" in item; assert "created_at" in item` |
| `test_get_notifications_unread_only` | `for item in data: assert item.get("is_read") is False` (если есть данные) |
| `test_notifications_role_isolation` | Проверить что уведомления текущего пользователя, а не чужого |

Новые:
| Тест | Что проверяет |
|------|---------------|
| `test_create_and_read_notification` | Создать уведомление через действие -> GET -> проверить что оно появилось |
| `test_mark_notification_read` | Создать уведомление -> PUT mark read -> GET проверить is_read=True |

---

### E2E-DEEP-07: Углубить test_e2e_heartbeat.py

- **Файл тестов:** `tests/e2e/test_e2e_heartbeat.py` (модификация)
- **Исходный код:** `server/routers/heartbeat_router.py` (58 строк)
- **Новых тестовых функций:** +1
- **Новых assert:** +5
- **Приоритет:** P2 -- нормально
- **Зависимости:** нет
- **Прирост покрытия:** +0.05 п.п.
- **Оценка:** ~30 мин Claude

Модификация:
| Тест | Добавить assert |
|------|----------------|
| `test_heartbeat_returns_online_users` | Если `isinstance(data, list)`: проверить структуру элементов `{"employee_id": int, "last_seen": str}`. Если dict: проверить `"online_users" in data` |
| `test_heartbeat_with_employee_id` | `data = resp.json()`, проверить что текущий employee_id присутствует в ответе |

Новый:
| Тест | Что проверяет |
|------|---------------|
| `test_heartbeat_multiple_users_tracked` | POST heartbeat от двух разных ролей -> проверить что оба видны в ответе |

---

### E2E-DEEP-08: Углубить test_e2e_project_templates.py

- **Файл тестов:** `tests/e2e/test_e2e_project_templates.py` (модификация)
- **Исходный код:** `server/routers/project_templates_router.py` (91 строка)
- **Новых тестовых функций:** +1
- **Новых assert:** +6
- **Приоритет:** P2 -- нормально
- **Зависимости:** нет
- **Прирост покрытия:** +0.05 п.п.
- **Оценка:** ~30 мин Claude

Модификация:
| Тест | Добавить assert |
|------|----------------|
| `test_add_project_template` | `assert data["id"] > 0`, проверить `template_url` или `contract_id` в ответе |
| `test_get_project_templates` | `assert isinstance(data[0], dict)`, `assert "id" in data[0]`, `assert "template_url" in data[0] or "contract_id" in data[0]` |
| `test_get_templates_nonexistent_contract` | Конкретизировать: `if resp.status_code == 200: assert data == [] or isinstance(data, list)` |

Новый:
| Тест | Что проверяет |
|------|---------------|
| `test_template_linked_to_correct_contract` | Создать шаблон -> GET -> проверить `contract_id == self.contract["id"]` |

---

### REWRITE-01: Переписать фиктивные offline тесты

- **Файлы изменения:** `tests/edge_cases/test_offline_online.py`, `tests/api_client/test_offline.py`
- **Исходный код:** `utils/offline_manager.py` (1159 строк), `utils/api_client/base.py`
- **Новых тестовых функций:** 0 (переписать ~32 существующих)
- **Приоритет:** P0 -- критично
- **Зависимости:** нет
- **Прирост покрытия:** +1.2 п.п. (~500 строк offline_manager.py начнут покрываться)
- **Оценка:** ~3 часа Claude
- **Привязка к багу:** research.md секция 5.1 -- тесты проверяют локальные переменные, не реальный код

**Конкретные действия для `tests/edge_cases/test_offline_online.py`:**

Заменить ВСЕ тесты класса `TestOfflineCacheExpiration` на реальные:

| Старый тест (фиктивный) | Новый тест (реальный) | Что проверяет |
|--------------------------|----------------------|---------------|
| `test_offline_cache_duration_not_too_long` | `test_offline_cache_duration_from_real_code` | `from utils.api_client.base import APIClient; assert APIClient.OFFLINE_CACHE_DURATION <= 10` |
| `test_cache_allows_retry_after_expiration` | `test_api_client_retries_after_cache_expires` | Создать APIClient с mock, вызвать метод (fail) -> подождать -> вызвать снова -> проверить что HTTP запрос отправлен повторно |
| `test_cache_prevents_hammering` | `test_api_client_skips_within_cache_window` | Создать APIClient, вызвать метод (fail) -> сразу вызвать снова -> проверить что HTTP запрос НЕ отправлен |
| `test_force_check_bypasses_cache` | `test_api_client_force_online_bypasses_cache` | Создать APIClient, force_online=True -> проверить что HTTP запрос отправлен несмотря на кэш |

Аналогично для `TestOfflineManagerCoordination` и других классов -- каждый тест ОБЯЗАН делать `from utils...import` реального класса.

**Конкретные действия для `tests/api_client/test_offline.py`:**

Заменить все тесты на импорт реальных констант и методов:
```python
from utils.api_client.base import APIClient
# Вместо локальных переменных -- тестировать реальные атрибуты класса
```

---

### Итого Этап 1

| Показатель | До | После |
|------------|-----|-------|
| Content assert ratio в E2E | ~30% | ~70% |
| Фиктивных тестов | ~32 | 0 |
| Тестов в CI | 410 | 1 488 |
| CI categories | 2 | 4 (test-db, test-e2e, test-client, test-backend) |
| Line coverage (оценка) | 7% | ~11% (+4 п.п.) |
| Время | -- | 3-4 дня Claude |

---

## Часть 3: Этап 2 -- Закрытие пробелов (8-10 дней Claude)

Новые тесты для непокрытых модулей.

---

### E2E-NEW-01: E2E тесты для cities_router

- **Файл тестов (создать):** `tests/e2e/test_e2e_cities.py`
- **Исходный код:** `server/routers/cities_router.py` (93 строки)
- **Новых тестовых функций:** 8
- **Приоритет:** P0 -- критично
- **Зависимости:** INFRA-01 (таблица cities в conftest)
- **Прирост покрытия:** +0.2 п.п. (~93 строки, ~65 executable -> ~60 покрыты)
- **Оценка:** ~1.5 часа Claude
- **Привязка к пробелу:** research.md секция 4.1 -- cities_router БЕЗ ПРЯМОГО E2E ТЕСТА

**Конкретные тесты:**

| # | Тест | Endpoint | Метод | Проверки |
|---|------|----------|-------|----------|
| 1 | `test_get_cities_list` | `/api/cities/` | GET | 200, isinstance(list), каждый элемент: `{"id": int, "name": str, "status": str}` |
| 2 | `test_create_city` | `/api/cities/` | POST | 200, `data["status"] == "success"`, `data["id"] > 0`, `data["name"] == "ТестГород__TEST__"` |
| 3 | `test_create_duplicate_city` | `/api/cities/` | POST | 400, `"уже существует" in resp.json()["detail"]` |
| 4 | `test_delete_city` | `/api/cities/{id}` | DELETE | 200, `data["status"] == "success"` |
| 5 | `test_delete_nonexistent_city` | `/api/cities/999999` | DELETE | 404, `"не найден" in resp.json()["detail"]` |
| 6 | `test_delete_city_with_active_contracts` | `/api/cities/{id}` | DELETE | 409, `"активных договоров" in resp.json()["detail"]` |
| 7 | `test_restore_deleted_city` | `/api/cities/` | POST | Создать -> удалить -> создать снова: 200, проверить что id тот же (восстановление) |
| 8 | `test_get_cities_include_deleted` | `/api/cities/?include_deleted=true` | GET | 200, проверить что удалённый город присутствует в списке |

---

### UTIL-01: Unit тесты для db_security.py

- **Файл тестов (создать):** `tests/client/test_db_security.py`
- **Исходный код:** `utils/db_security.py` (201 строка, 57 statements с 0% покрытия)
- **Новых тестовых функций:** 12
- **Приоритет:** P0 -- критично (безопасность)
- **Зависимости:** нет
- **Прирост покрытия:** +0.13 п.п. (~57 строк)
- **Оценка:** ~1 час Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_validate_update_data_filters_malicious_fields` | `validate_update_data('clients', {'full_name': 'X', 'DROP TABLE': 'Y'})` -> только full_name |
| 2 | `test_validate_update_data_accepts_all_allowed` | Все поля из ALLOWED_FIELDS['clients'] проходят |
| 3 | `test_validate_update_data_unknown_table_raises` | `validate_update_data('nonexistent', {})` -> ValueError |
| 4 | `test_build_update_query_correct_sql` | Проверить что SQL содержит `UPDATE clients SET full_name = ?` |
| 5 | `test_build_update_query_empty_after_filter` | Все поля отфильтрованы -> ValueError |
| 6 | `test_build_insert_query_correct_sql` | Проверить `INSERT INTO clients (full_name, phone) VALUES (?, ?)` |
| 7 | `test_build_insert_query_filters_malicious` | Вредоносные поля не попадают в INSERT |
| 8 | `test_sanitize_table_name_valid` | `sanitize_table_name('clients')` -> 'clients' |
| 9 | `test_sanitize_table_name_sql_injection` | `sanitize_table_name('clients; DROP TABLE')` -> ValueError |
| 10 | `test_sanitize_table_name_not_in_whitelist` | `sanitize_table_name('valid_syntax_but_unknown')` -> ValueError |
| 11 | `test_build_update_query_custom_where` | `where_clause="login = ?"` -> проверить SQL |
| 12 | `test_allowed_fields_covers_all_tables` | Проверить что ALLOWED_FIELDS содержит ключи для employees, clients, contracts, crm_cards, supervision_cards, salaries |

---

### UTIL-02: Unit тесты для pdf_generator.py

- **Файл тестов (создать):** `tests/client/test_pdf_generator.py`
- **Исходный код:** `utils/pdf_generator.py` (324 строки, 107 statements с 0% покрытия)
- **Новых тестовых функций:** 10
- **Приоритет:** P1 -- важно
- **Зависимости:** нет
- **Прирост покрытия:** +0.18 п.п. (~80 из 107 строк)
- **Оценка:** ~1.5 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_format_report_value_none` | `format_report_value(None) == ''` |
| 2 | `test_format_report_value_currency` | `format_report_value(1500000, 'currency')` содержит "руб." |
| 3 | `test_format_report_value_area` | `format_report_value(125.5, 'area')` содержит "м2" |
| 4 | `test_format_report_value_date` | `format_report_value('2026-01-15', 'date') == '15.01.2026'` |
| 5 | `test_format_report_value_invalid_currency` | `format_report_value('abc', 'currency') == 'abc'` |
| 6 | `test_pdf_style_constants` | `PDF_STYLE['header_bg'] == '#2C3E50'`, все ключи присутствуют |
| 7 | `test_pdf_generator_init` | `PDFGenerator()` не падает (если reportlab есть) |
| 8 | `test_pdf_generator_generate_contract_report` | Mock данные -> generate -> проверить что файл создан |
| 9 | `test_pdf_generator_cyrillic_text` | Генерация PDF с кириллицей -- файл создан, размер > 0 |
| 10 | `test_pdf_generator_empty_data` | Пустые данные -> generate -> не падает, файл создан |

---

### UTIL-03: Unit тесты для calendar_helpers.py

- **Файл тестов (создать):** `tests/client/test_calendar_helpers.py`
- **Исходный код:** `utils/calendar_helpers.py` (218 строк, ~87 statements с 0% покрытия)
- **Новых тестовых функций:** 10
- **Приоритет:** P1 -- важно
- **Зависимости:** нет
- **Прирост покрытия:** +0.1 п.п. (~45 из 87 строк -- чистые функции без Qt)
- **Оценка:** ~1 час Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_add_working_days_normal` | `add_working_days('2026-01-05', 5)` -- результат пропускает выходные |
| 2 | `test_add_working_days_over_weekend` | `add_working_days('2026-01-09', 1)` (пятница +1) -> '2026-01-12' (понедельник) |
| 3 | `test_add_working_days_zero` | `add_working_days('2026-01-05', 0) == '2026-01-05'` |
| 4 | `test_add_working_days_empty_date` | `add_working_days('', 5) == ''` |
| 5 | `test_add_working_days_invalid_date` | `add_working_days('invalid', 5) == 'invalid'` |
| 6 | `test_add_working_days_negative` | `add_working_days('2026-01-05', -1) == '2026-01-05'` |
| 7 | `test_working_days_between_same_week` | `working_days_between('2026-01-05', '2026-01-09')` == 4 (Пн-Пт) |
| 8 | `test_working_days_between_over_weekend` | `working_days_between('2026-01-09', '2026-01-12')` == 1 (Пт-Пн) |
| 9 | `test_working_days_between_empty` | `working_days_between('', '2026-01-09') == 0` |
| 10 | `test_working_days_between_end_before_start` | `working_days_between('2026-01-09', '2026-01-05') == 0` |

---

### UTIL-04: Unit тесты для button_debounce.py

- **Файл тестов (создать):** `tests/client/test_button_debounce.py`
- **Исходный код:** `utils/button_debounce.py` (43 строки, ~20 statements)
- **Новых тестовых функций:** 6
- **Приоритет:** P2 -- нормально
- **Зависимости:** нет
- **Прирост покрытия:** +0.05 п.п.
- **Оценка:** ~30 мин Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_debounce_first_call_executes` | Первый вызов декорированной функции выполняется |
| 2 | `test_debounce_rapid_calls_blocked` | Второй вызов через 0.1с блокируется (return None) |
| 3 | `test_debounce_after_delay_executes` | Вызов через delay_ms+0.1с выполняется |
| 4 | `test_debounce_custom_delay` | `@debounce_click(delay_ms=2000)` -- блокирует в течение 2с |
| 5 | `test_debounce_strips_qt_bool_arg` | Вызов с `(self, True)` -> функция получает только `(self,)` |
| 6 | `test_debounce_without_parentheses` | `@debounce_click` (без скобок) -- работает с default delay |

---

### UTIL-05: Unit тесты для db_sync.py

- **Файл тестов (создать):** `tests/client/test_db_sync.py`
- **Исходный код:** `utils/db_sync.py` (1730 строк, 583 statements с 0% покрытия)
- **Новых тестовых функций:** 12
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.5 п.п. (~220 из 583 строк)
- **Оценка:** ~2.5 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_db_sync_init` | Инициализация DbSync с SQLite :memory: |
| 2 | `test_sync_employees_from_api` | Mock API -> sync -> проверить что сотрудники в SQLite |
| 3 | `test_sync_clients_from_api` | Mock API -> sync -> клиенты в SQLite |
| 4 | `test_sync_contracts_from_api` | Mock API -> sync -> договоры в SQLite |
| 5 | `test_sync_handles_api_error` | Mock API raises -> sync не падает, данные не потеряны |
| 6 | `test_sync_updates_existing_records` | Sync с обновлёнными данными -> старые записи обновлены |
| 7 | `test_sync_preserves_local_only_data` | Данные только в SQLite -> после sync не удалены |
| 8 | `test_sync_conflict_resolution` | Данные в SQLite и API различаются -> API побеждает |
| 9 | `test_sync_empty_api_response` | API возвращает [] -> SQLite не трогается |
| 10 | `test_sync_crm_cards` | Mock API -> sync CRM карточек |
| 11 | `test_sync_payments` | Mock API -> sync платежей |
| 12 | `test_full_sync_cycle` | Полный цикл: employees -> clients -> contracts -> crm -> payments |

---

### UTIL-06: Unit тесты для update_manager.py

- **Файл тестов (создать):** `tests/client/test_update_manager.py`
- **Исходный код:** `utils/update_manager.py` (360 строк, 178 statements с 0% покрытия)
- **Новых тестовых функций:** 8
- **Приоритет:** P2 -- нормально
- **Зависимости:** нет
- **Прирост покрытия:** +0.2 п.п. (~90 из 178 строк)
- **Оценка:** ~1.5 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_version_comparison_newer` | `compare_versions('2.0.0', '1.9.0') == 1` |
| 2 | `test_version_comparison_same` | `compare_versions('1.0.0', '1.0.0') == 0` |
| 3 | `test_version_comparison_older` | `compare_versions('1.0.0', '2.0.0') == -1` |
| 4 | `test_check_update_available` | Mock HTTP -> ответ с новой версией -> update_available == True |
| 5 | `test_check_update_not_available` | Mock HTTP -> ответ с текущей версией -> update_available == False |
| 6 | `test_check_update_network_error` | Mock HTTP raises -> не падает, возвращает False |
| 7 | `test_download_update` | Mock HTTP -> скачивание файла -> файл существует |
| 8 | `test_update_manager_current_version` | Проверить что current_version читается из config/version |

---

### UTIL-07: Unit тесты для остальных утилит (пакет)

- **Файлы тестов (создать):** `tests/client/test_misc_utils.py`
- **Исходный код:** `utils/message_helper.py` (55 строк), `utils/tooltip_fix.py` (18 строк), `utils/dialog_helpers.py` (126 строк), `utils/tab_helpers.py` (57 строк), `utils/table_settings.py` (470 строк), `utils/add_indexes.py` (201 строк), `utils/migrate_passwords.py` (173 строк), `utils/preview_generator.py` (223 строк)
- **Новых тестовых функций:** 22
- **Приоритет:** P2 -- нормально
- **Зависимости:** нет
- **Прирост покрытия:** +0.6 п.п. (~260 строк)
- **Оценка:** ~3 часа Claude

**utils/table_settings.py (5 тестов):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_save_column_widths` | Сохранить ширины колонок -> загрузить -> совпадают |
| 2 | `test_load_column_widths_no_file` | Файла нет -> возвращает defaults |
| 3 | `test_save_sort_order` | Сохранить сортировку -> загрузить -> совпадает |
| 4 | `test_save_hidden_columns` | Сохранить скрытые колонки -> загрузить -> совпадают |
| 5 | `test_settings_file_path` | Проверить что путь файла в correct directory |

**utils/add_indexes.py (3 теста):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 6 | `test_create_indexes_on_empty_db` | Создать индексы на пустой SQLite -> не падает |
| 7 | `test_create_indexes_idempotent` | Создать индексы дважды -> не падает (IF NOT EXISTS) |
| 8 | `test_indexes_exist_after_creation` | Проверить что индексы реально существуют в sqlite_master |

**utils/migrate_passwords.py (3 теста):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 9 | `test_migrate_plaintext_to_bcrypt` | Пароль в plaintext -> миграция -> password_hash начинается с $2b$ |
| 10 | `test_already_migrated_skipped` | Пароль уже bcrypt -> миграция -> не изменён |
| 11 | `test_migrate_empty_password` | Пустой пароль -> миграция -> не падает |

**utils/preview_generator.py (3 теста):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 12 | `test_generate_preview_image` | PNG файл -> генерация превью -> файл создан, размер меньше |
| 13 | `test_generate_preview_unsupported_format` | .xyz файл -> генерация -> возвращает None/default |
| 14 | `test_generate_preview_nonexistent_file` | Несуществующий файл -> не падает |

**utils/message_helper.py (4 теста):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 15 | `test_show_warning_creates_dialog` | Mock CustomMessageBox -> show_warning -> exec_ вызван с 'warning' |
| 16 | `test_show_error_creates_dialog` | Mock CustomMessageBox -> show_error -> exec_ вызван с 'error' |
| 17 | `test_show_success_creates_dialog` | Mock CustomMessageBox -> show_success -> exec_ вызван с 'success' |
| 18 | `test_show_info_creates_dialog` | Mock CustomMessageBox -> show_info -> exec_ вызван с 'info' |

**utils/dialog_helpers.py (2 теста):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 19 | `test_dialog_helper_creates_widget` | Вызов helper -> виджет создан |
| 20 | `test_dialog_helper_applies_styles` | Вызов helper -> стили применены |

**utils/tab_helpers.py (2 теста):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 21 | `test_tab_helper_switch` | Переключение вкладки -> индекс изменился |
| 22 | `test_tab_helper_count` | Проверить количество вкладок |

---

### OFFLINE-01: Unit тесты для OfflineManager (реальные)

- **Файл тестов (создать):** `tests/client/test_offline_manager.py`
- **Исходный код:** `utils/offline_manager.py` (1159 строк, 688 statements с 13% покрытия)
- **Новых тестовых функций:** 15
- **Приоритет:** P1 -- важно
- **Зависимости:** REWRITE-01
- **Прирост покрытия:** +0.8 п.п. (~350 из 688 строк)
- **Оценка:** ~3 часа Claude
- **Привязка к пробелу:** research.md секция 6.3 -- реальный offline_manager тестируется только косвенно

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_offline_manager_init` | OfflineManager с SQLite :memory: + mock api_client -> не падает |
| 2 | `test_add_to_queue` | add_to_queue('create_client', {...}) -> pending_count == 1 |
| 3 | `test_get_pending_count` | Добавить 3 операции -> pending_count == 3 |
| 4 | `test_process_queue_success` | Добавить операцию + mock api success -> pending_count == 0 |
| 5 | `test_process_queue_api_error` | Добавить операцию + mock api fail -> pending_count == 1 (не удалена) |
| 6 | `test_clear_synced_operations` | Добавить + sync + clear -> pending_count == 0 |
| 7 | `test_operation_signature_hmac` | _sign_operation -> _verify_operation_signature -> True |
| 8 | `test_tampered_operation_rejected` | Изменить операцию после подписи -> verify -> False |
| 9 | `test_queue_ordering_fifo` | Добавить A, B, C -> process -> порядок A, B, C |
| 10 | `test_queue_with_dependencies` | Создать client -> создать contract (depends on client) -> process в правильном порядке |
| 11 | `test_is_online_property` | Mock api_client.is_online -> OfflineManager.is_online отражает |
| 12 | `test_go_offline_signal` | Установить offline -> сигнал connection_changed emitted |
| 13 | `test_go_online_triggers_sync` | Переход online -> process_queue вызван |
| 14 | `test_max_retry_count` | Операция fails N раз -> помечена как failed, не retried |
| 15 | `test_queue_persistence_across_restart` | Добавить в :memory: -> перечитать -> операции сохранены |

---

### CONTRACT-01: Contract тесты API-DB ключей

- **Файл тестов (создать):** `tests/contract/test_schema_contracts.py`, `tests/contract/test_key_sync.py`, `tests/contract/test_data_access_coverage.py`
- **Исходный код:** `server/schemas.py`, `database/db_manager.py`, `utils/data_access.py`
- **Новых тестовых функций:** 25
- **Приоритет:** P0 -- критично
- **Зависимости:** INFRA-05
- **Прирост покрытия:** +0.3 п.п. (статический анализ + runtime checks)
- **Оценка:** ~3 часа Claude
- **Привязка к пробелу:** research.md секция 6.4 -- нет тестов совместимости ключей

**test_schema_contracts.py (10 тестов):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_client_response_fields_complete` | Все поля ClientResponse существуют в реальном API ответе |
| 2 | `test_contract_response_fields_complete` | Все поля ContractResponse |
| 3 | `test_employee_response_fields_complete` | Все поля EmployeeResponse |
| 4 | `test_crm_card_response_fields_complete` | Все поля CRMCardResponse |
| 5 | `test_supervision_card_response_fields_complete` | Все поля SupervisionCardResponse |
| 6 | `test_stage_executor_response_fields_complete` | Все поля StageExecutorResponse |
| 7 | `test_payment_response_fields_complete` | Все поля PaymentResponse |
| 8 | `test_notification_response_fields_complete` | Все поля NotificationResponse |
| 9 | `test_rate_response_fields_complete` | Все поля RateResponse |
| 10 | `test_salary_response_fields_complete` | Все поля SalaryResponse |

**test_key_sync.py (8 тестов):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 11 | `test_db_client_keys_superset_of_schema` | set(db.get_client().keys()) >= set(ClientResponse.model_fields.keys()) |
| 12 | `test_db_contract_keys_superset_of_schema` | Аналогично для contracts |
| 13 | `test_db_employee_keys_superset_of_schema` | Аналогично для employees |
| 14 | `test_db_crm_card_keys_match_schema` | Аналогично для crm_cards |
| 15 | `test_db_supervision_card_keys_match_schema` | Аналогично для supervision_cards |
| 16 | `test_db_payment_keys_match_schema` | Аналогично для payments |
| 17 | `test_api_response_keys_match_schema` | JSON fixture vs Pydantic model fields |
| 18 | `test_no_snake_camel_mismatch` | Проверить что нет total_paid vs totalPaid расхождений |

**test_data_access_coverage.py (7 тестов):**
| # | Тест | Что проверяет |
|---|------|---------------|
| 19 | `test_data_access_wraps_all_api_methods` | Каждый публичный метод APIClient имеет обёртку в DataAccess |
| 20 | `test_data_access_get_clients_calls_api_first` | DataAccess.get_all_clients -> api_client.get_clients вызван первым |
| 21 | `test_data_access_fallback_on_connection_error` | APIConnectionError -> db метод вызван |
| 22 | `test_data_access_no_fallback_on_business_error` | 409/400 -> НЕ вызывает db fallback |
| 23 | `test_data_access_create_methods_have_offline_queue` | create_client raises APIConnectionError -> offline_queue пополнена |
| 24 | `test_data_access_methods_count` | Проверить что публичных методов DataAccess >= N (protection against method deletion) |
| 25 | `test_data_access_returns_consistent_format` | get_all_clients API vs DB -> одинаковый формат ответа |

---

### INFRA-06: CI job test-contract

- **Файлы изменения:** `.github/workflows/ci.yml`
- **Приоритет:** P1 -- важно
- **Зависимости:** CONTRACT-01
- **Оценка:** ~30 мин Claude
- **Прирост покрытия:** 0 п.п. (тесты попадают в CI)

```yaml
test-contract:
  runs-on: ubuntu-latest
  needs: [syntax-check]
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with:
        python-version: '3.11'
    - name: Установка зависимостей
      run: |
        pip install pytest pytest-timeout pydantic pydantic-settings
    - name: Запуск Contract тестов
      run: pytest tests/contract/ -v --timeout=30 -p no:qt
```

---

### UI-01: Тесты admin_dialog.py

- **Файл тестов (создать):** `tests/ui/test_admin_dialog.py`
- **Исходный код:** `ui/admin_dialog.py` (302 строки)
- **Новых тестовых функций:** 8
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.3 п.п.
- **Оценка:** ~1.5 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_admin_dialog_init` | AdminDialog создаётся без ошибок с mock DataAccess |
| 2 | `test_admin_dialog_has_tabs` | Диалог содержит TabWidget с вкладками |
| 3 | `test_admin_dialog_agents_tab_present` | Вкладка "Агенты" присутствует |
| 4 | `test_admin_dialog_cities_tab_present` | Вкладка "Города" присутствует |
| 5 | `test_admin_dialog_permissions_tab_present` | Вкладка "Права" или "Роли" присутствует |
| 6 | `test_admin_dialog_load_data_calls_da` | load_data -> mock_data_access.get_all_agents вызван |
| 7 | `test_admin_dialog_save_calls_da` | Заполнить данные -> save -> mock_data_access.update_* вызван |
| 8 | `test_admin_dialog_close_without_crash` | Открыть -> закрыть -> QApplication живо |

---

### UI-02: Тесты agents_cities_widget.py

- **Файл тестов (создать):** `tests/ui/test_agents_cities_widget.py`
- **Исходный код:** `ui/agents_cities_widget.py` (375 строк)
- **Новых тестовых функций:** 10
- **Приоритет:** P0 -- критично (бизнес-критичный модуль)
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.35 п.п.
- **Оценка:** ~2 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_widget_init` | AgentsCitiesWidget создаётся с mock DataAccess |
| 2 | `test_load_agents` | load_agents -> mock_data_access.get_all_agents вызван, таблица заполнена |
| 3 | `test_load_cities` | load_cities -> mock_data_access.get_all_cities вызван, список заполнен |
| 4 | `test_add_agent` | Нажать "Добавить агента" -> mock_data_access.create_agent вызван |
| 5 | `test_delete_agent` | Выбрать агента -> удалить -> mock_data_access.delete_agent вызван |
| 6 | `test_add_city` | Ввести город -> добавить -> mock_data_access.create_city вызван с именем |
| 7 | `test_delete_city` | Выбрать город -> удалить -> mock_data_access.delete_city вызван |
| 8 | `test_empty_city_name_rejected` | Ввести пустое имя -> добавить -> create_city НЕ вызван |
| 9 | `test_agent_table_columns` | Таблица агентов имеет колонки: имя, тип, статус |
| 10 | `test_city_list_populated` | После load_cities -> список содержит элементы |

---

### UI-03: Тесты permissions_matrix_widget.py

- **Файл тестов (создать):** `tests/ui/test_permissions_matrix.py`
- **Исходный код:** `ui/permissions_matrix_widget.py` (477 строк, 176 statements с 0% покрытия)
- **Новых тестовых функций:** 8
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.25 п.п.
- **Оценка:** ~1.5 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_matrix_init` | PermissionsMatrixWidget создаётся с mock DataAccess |
| 2 | `test_matrix_shows_roles` | Матрица отображает роли в строках/столбцах |
| 3 | `test_matrix_shows_permissions` | Матрица отображает разрешения (checkboxes) |
| 4 | `test_toggle_permission` | Кликнуть checkbox -> mock_data_access.update_permission вызван |
| 5 | `test_load_permissions` | load -> mock_data_access.get_permissions вызван |
| 6 | `test_save_permissions` | save -> mock_data_access.save_permissions вызван |
| 7 | `test_admin_role_all_checked` | Роль admin -> все checkboxes checked |
| 8 | `test_readonly_for_non_admin` | Если текущий пользователь не admin -> checkboxes disabled |

---

### UI-04: Тесты supervision_timeline_widget.py

- **Файл тестов (создать):** `tests/ui/test_supervision_timeline.py`
- **Исходный код:** `ui/supervision_timeline_widget.py` (872 строки, 491 statements с 0% покрытия)
- **Новых тестовых функций:** 8
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.4 п.п.
- **Оценка:** ~2 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_timeline_init` | SupervisionTimelineWidget создаётся |
| 2 | `test_timeline_set_data` | set_data(mock_entries) -> виджет отображает записи |
| 3 | `test_timeline_empty_data` | set_data([]) -> виджет показывает "Нет данных" |
| 4 | `test_timeline_pause_display` | Запись с is_paused=True -> отображается с паузой |
| 5 | `test_timeline_date_range` | Запись с start/end -> корректный диапазон дат |
| 6 | `test_timeline_stage_colors` | Разные стадии -> разные цвета |
| 7 | `test_timeline_resize` | Изменение размера -> не падает |
| 8 | `test_timeline_scroll` | Много записей -> скролл работает |

---

### UI-05: Тесты timeline_widget.py

- **Файл тестов (создать):** `tests/ui/test_timeline_widget.py`
- **Исходный код:** `ui/timeline_widget.py` (1023 строки, 614 statements с 0% покрытия)
- **Новых тестовых функций:** 8
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.4 п.п.
- **Оценка:** ~2 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_timeline_widget_init` | TimelineWidget создаётся |
| 2 | `test_timeline_set_planned_dates` | set_planned_dates(data) -> даты отображаются |
| 3 | `test_timeline_empty_dates` | Пустые даты -> виджет показывает placeholder |
| 4 | `test_timeline_milestone_markers` | Даты milestone -> маркеры отображаются |
| 5 | `test_timeline_overdue_highlight` | Просроченная дата -> подсветка красным |
| 6 | `test_timeline_today_marker` | Текущая дата отмечена на timeline |
| 7 | `test_timeline_zoom_in_out` | Zoom -> масштаб меняется, не падает |
| 8 | `test_timeline_date_format` | Даты отображаются в формате DD.MM.YYYY |

---

### UI-06: Тесты для остальных 15 UI модулей (пакет)

- **Файлы тестов (создать):** По 1 файлу на 2-3 модуля
- **Исходный код:** 15 модулей (суммарно ~7200 строк)
- **Новых тестовых функций:** ~75 (по 5 тестов на модуль)
- **Приоритет:** P2 -- нормально
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +2.5 п.п.
- **Оценка:** ~6 часов Claude

**Разбивка по файлам:**

| Файл тестов | Модули | Тестов | Ключевые проверки |
|-------------|--------|--------|-------------------|
| `tests/ui/test_file_widgets.py` | file_gallery_widget (191), file_list_widget (271), file_preview_widget (172) | 12 | init, load_files, display, thumbnail, empty_state |
| `tests/ui/test_messenger_widgets.py` | messenger_admin_dialog (1526), messenger_select_dialog (654) | 10 | init, load_chats, send_message, select_recipient, search |
| `tests/ui/test_norm_days_widget.py` | norm_days_settings_widget (1017) | 8 | init, load_settings, save, calendar_days, validation |
| `tests/ui/test_supervision_dialogs.py` | supervision_dialogs (2430) | 10 | init, create_card, edit_card, validate_fields, save |
| `tests/ui/test_update_dialogs.py` | update_dialogs (498) | 5 | init, check_update, download_progress, install_button |
| `tests/ui/test_chart_widget.py` | chart_widget (184) | 5 | init, set_data, empty_data, resize, labels |
| `tests/ui/test_variation_gallery.py` | variation_gallery_widget (291) | 5 | init, load_variations, display, navigate |
| `tests/ui/test_small_widgets.py` | flow_layout (96), custom_combobox (40), custom_dateedit (28), bubble_tooltip (199), crm_archive (1465) | 12 | init per widget, layout_items, popup, tooltip_text, archive_load |
| `tests/ui/test_global_search.py` | global_search_widget (240) | 8 | init, search_text, results_display, select_result, empty_query |

---

### Итого Этап 2

| Показатель | До (после Этапа 1) | После Этапа 2 |
|------------|---------------------|---------------|
| Новых тестов | 0 | +237 |
| Тестов в CI | 1 488 | ~1 560 (+72 contract + утилиты) |
| CI categories | 4 | 5 (+test-contract) |
| UI модулей без тестов | 21 | 0 |
| Утилит без тестов | 14 | 0 |
| Роутеров без E2E | 1 | 0 |
| Line coverage (оценка) | ~11% | ~19% (+8 п.п.) |
| Время | -- | 8-10 дней Claude |

---

## Часть 4: Этап 3 -- Hardening (6-8 дней Claude)

Продвинутые тесты для достижения целевого покрытия.

---

### MIGRATION-01: Тесты путей миграции БД

- **Файл тестов (создать):** `tests/db/test_migration_paths.py`
- **Исходный код:** `database/db_manager.py`
- **Новых тестовых функций:** 10
- **Приоритет:** P1 -- важно
- **Зависимости:** INFRA-01
- **Прирост покрытия:** +0.3 п.п.
- **Оценка:** ~2 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_migration_adds_crm_card_id_to_payments` | Создать БД без миграции -> migrate -> проверить колонку |
| 2 | `test_migration_adds_supervision_card_id_to_payments` | Аналогично |
| 3 | `test_migration_adds_phone_to_employees` | Аналогично |
| 4 | `test_migration_adds_city_to_contracts` | Аналогично |
| 5 | `test_migration_preserves_existing_data` | INSERT данные -> migrate -> данные сохранены |
| 6 | `test_migration_default_values_correct` | Новые колонки имеют правильные DEFAULT |
| 7 | `test_full_migration_chain` | Все миграции последовательно -> финальная схема корректна |
| 8 | `test_conftest_schema_matches_db_manager` | Схема conftest == схема db_manager (после миграций) |
| 9 | `test_migration_creates_cities_table` | После миграции таблица cities существует |
| 10 | `test_migration_creates_indexes` | После миграции индексы созданы |

---

### PROPERTY-01: Property-based тесты валидаторов

- **Файл тестов (создать):** `tests/client/test_validators_property.py`
- **Исходный код:** `utils/validators.py` (207 строк)
- **Новых тестовых функций:** 12
- **Приоритет:** P2 -- нормально
- **Зависимости:** hypothesis (pip install)
- **Прирост покрытия:** +0.2 п.п. (глубина, не ширина)
- **Оценка:** ~2 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_phone_valid_format_accepted` | `@given(st.from_regex(r'\+7 \d{3} \d{3} \d{4}'))` -> validate_phone == True |
| 2 | `test_phone_random_text_rejected` | `@given(st.text())` -> если не формат, validate_phone == False |
| 3 | `test_email_valid_format_accepted` | `@given(st.emails())` -> validate_email == True |
| 4 | `test_email_no_at_rejected` | `@given(st.text().filter(lambda x: '@' not in x))` -> False |
| 5 | `test_contract_number_format` | `@given(valid_contract_numbers)` -> validate_contract_number == True |
| 6 | `test_name_valid_cyrillic` | `@given(cyrillic_names)` -> validate_name == True |
| 7 | `test_inn_10_digits` | `@given(st.from_regex(r'\d{10}'))` -> validate_inn == True |
| 8 | `test_inn_wrong_length_rejected` | `@given(st.from_regex(r'\d{1,9}'))` -> validate_inn == False |
| 9 | `test_area_positive_float` | `@given(st.floats(min_value=0.1, max_value=10000))` -> validate_area == True |
| 10 | `test_area_negative_rejected` | `@given(st.floats(max_value=-0.01))` -> validate_area == False |
| 11 | `test_amount_boundary_values` | `@given(st.floats(min_value=0, max_value=1e12))` -> validate_amount |
| 12 | `test_date_format_valid` | `@given(st.dates())` -> format to string -> validate_date == True |

---

### ROLES-01: Негативные ролевые E2E тесты

- **Файл тестов (создать):** `tests/e2e/test_e2e_role_restrictions.py`
- **Исходный код:** `server/routers/` (permissions), `server/auth.py`
- **Новых тестовых функций:** 20
- **Приоритет:** P1 -- важно
- **Зависимости:** E2E-DEEP-01..08
- **Прирост покрытия:** +0.5 п.п. (auth + permissions ветки)
- **Оценка:** ~3 часа Claude

| # | Тест | Роль | Endpoint | Ожидание |
|---|------|------|----------|----------|
| 1 | `test_designer_cannot_create_city` | designer | POST /api/cities/ | 403 |
| 2 | `test_draftsman_cannot_create_city` | draftsman | POST /api/cities/ | 403 |
| 3 | `test_designer_cannot_delete_employee` | designer | DELETE /api/employees/{id} | 403 |
| 4 | `test_manager_cannot_view_salaries` | manager | GET /api/salaries/ | 403 |
| 5 | `test_designer_cannot_create_rate` | designer | POST /api/rates/ | 403 |
| 6 | `test_gap_cannot_delete_contract` | gap | DELETE /api/contracts/{id} | 403 |
| 7 | `test_surveyor_cannot_modify_permissions` | surveyor | PUT /api/admin/permissions | 403 |
| 8 | `test_dan_cannot_modify_crm_card` | dan | PATCH /api/crm/{id} | 403 (если нет прав) |
| 9 | `test_no_token_all_endpoints_401` | (none) | GET /api/clients/ | 401 |
| 10 | `test_expired_token_all_endpoints_401` | expired | GET /api/clients/ | 401 |
| 11 | `test_sdp_can_view_own_stages` | sdp | GET /api/crm/ | 200 |
| 12 | `test_admin_can_access_everything` | admin | ALL endpoints | 200 |
| 13 | `test_senior_manager_can_create_contract` | senior_manager | POST /api/contracts/ | 200 |
| 14 | `test_designer_can_view_crm` | designer | GET /api/crm/ | 200 |
| 15 | `test_manager_can_view_reports` | manager | GET /api/reports/employee | 200 |
| 16 | `test_dan_can_view_supervision` | dan | GET /api/supervision/ | 200 |
| 17 | `test_gap_can_view_dashboard` | gap | GET /api/dashboard/crm | 200 |
| 18 | `test_invalid_permission_returns_403` | user_without_perm | endpoint requiring perm | 403 |
| 19 | `test_rate_view_requires_rates_view_perm` | role_without_rates | GET /api/rates/ | 403 |
| 20 | `test_salary_create_requires_salaries_create_perm` | role_without_salaries | POST /api/salaries/ | 403 |

---

### DUAL-MODE-01: Тесты DataAccess двухрежимности

- **Файл тестов (создать):** `tests/client/test_data_access_dual_mode.py`
- **Исходный код:** `utils/data_access.py` (3144 строки, 2192 statements с 20% покрытия)
- **Новых тестовых функций:** 15
- **Приоритет:** P1 -- важно
- **Зависимости:** OFFLINE-01
- **Прирост покрытия:** +1.5 п.п. (~660 из 2192 строк -> ~880)
- **Оценка:** ~3 часа Claude

| # | Тест | Что проверяет |
|---|------|---------------|
| 1 | `test_get_clients_api_mode` | API доступен -> возвращает данные из API |
| 2 | `test_get_clients_offline_fallback` | API недоступен -> возвращает данные из SQLite |
| 3 | `test_create_client_api_mode` | API доступен -> create_client через API |
| 4 | `test_create_client_offline_queued` | API недоступен -> операция в offline_queue |
| 5 | `test_update_client_api_mode` | API доступен -> update через API |
| 6 | `test_update_client_offline_queued` | API недоступен -> операция в offline_queue |
| 7 | `test_delete_client_api_mode` | API доступен -> delete через API |
| 8 | `test_business_error_not_queued` | API 409 -> операция НЕ попадает в offline_queue |
| 9 | `test_prefer_local_false_uses_api` | prefer_local=False -> API вызван |
| 10 | `test_prefer_local_true_uses_db` | prefer_local=True -> DB вызван |
| 11 | `test_api_data_cached_locally` | API ответ -> сохранён в локальную SQLite |
| 12 | `test_sync_after_reconnect` | Offline -> Online -> pending_queue обработана |
| 13 | `test_get_contracts_dual_mode` | Аналогично clients для contracts |
| 14 | `test_get_employees_dual_mode` | Аналогично для employees |
| 15 | `test_get_crm_cards_dual_mode` | Аналогично для crm_cards |

---

### UI-INTERACT-01: Расширенные UI тесты взаимодействий

- **Файлы тестов (изменение):** Существующие UI тест файлы из Этапа 2
- **Исходный код:** Крупные UI модули (crm_tab.py, salaries_tab.py, etc.)
- **Новых тестовых функций:** 30
- **Приоритет:** P2 -- нормально
- **Зависимости:** UI-01..06
- **Прирост покрытия:** +2.0 п.п.
- **Оценка:** ~4 часа Claude

**Фокусные модули (наибольший объём кода с минимальным покрытием):**

| Модуль | Строки | Текущее покрытие | Тестов | Ключевые взаимодействия |
|--------|--------|-----------------|--------|------------------------|
| `crm_tab.py` | 3210 | 6% | 6 | drag_card, filter_by_column, search, context_menu, sort |
| `salaries_tab.py` | 1645 | 5% | 5 | load_salaries, filter_by_month, calculate_total, export |
| `crm_card_edit_dialog.py` | 2038 | 5% | 5 | open_card, edit_field, assign_executor, save |
| `supervision_card_edit_dialog.py` | 1719 | 5% | 5 | open_card, edit_dan, set_pause, save |
| `employees_tab.py` | 865 | 7% | 5 | load_employees, search, filter_by_role, edit |
| `main_window.py` | 948 | 7% | 4 | init_tabs, switch_tab, handle_sync, logout |

---

### REGRESSION-01: Автоматизация regression suite

- **Файл тестов (изменение):** `tests/regression/test_regression.py`
- **Исходный код:** Все модули с known bugs из MEMORY.md
- **Новых тестовых функций:** 10
- **Приоритет:** P2 -- нормально
- **Зависимости:** все предыдущие этапы
- **Прирост покрытия:** +0.3 п.п.
- **Оценка:** ~2 часа Claude

| # | Тест | Баг | Привязка к MEMORY.md |
|---|------|-----|---------------------|
| 1 | `test_archive_always_uses_api` | prefer_local=True для архива -> пустой результат | "prefer_local = True для архивных карточек" |
| 2 | `test_stage_executor_deadline_is_date` | StageExecutor.deadline String, не Date | "StageExecutor.deadline -- String, не Date" |
| 3 | `test_dashboard_excludes_archive_from_active` | Dashboard agent_active включает архивные | "Dashboard agent_active/archive" |
| 4 | `test_custom_question_box_for_confirmations` | CustomMessageBox вместо CustomQuestionBox для подтверждений | "CustomMessageBox vs CustomQuestionBox" |
| 5 | `test_svg_icons_exist` | Иконки SVG не найдены | "Иконки SVG должны существовать" |
| 6 | `test_data_access_exception_not_propagated` | DataAccess проксирует API, исключения не проброшены | "api_client методы ловят исключения" |
| 7 | `test_offline_queue_only_network_errors` | Offline-очередь принимает бизнес-ошибки | "Offline-очередь -- только сетевые ошибки" |
| 8 | `test_qt_signal_from_thread` | emit из threading.Thread без QTimer | "PyQt Signal Safety" |
| 9 | `test_resource_path_used_for_resources` | Прямой путь вместо resource_path() | "resource_path() для всех ресурсов" |
| 10 | `test_static_routes_before_dynamic` | Динамический маршрут перехватывает статический | "Статические пути ПЕРЕД динамическими" |

---

### Итого Этап 3

| Показатель | До (после Этапа 2) | После Этапа 3 |
|------------|---------------------|---------------|
| Новых тестов | +237 | +334 (всего +571) |
| Тестов в CI | ~1 560 | ~1 640 |
| CI categories | 5 | 5 |
| Line coverage (оценка) | ~19% | ~24% (+5 п.п.) |
| Время | -- | 6-8 дней Claude |

---

## Часть 5: Целевые метрики

### Прогноз line coverage по этапам

**Базовые расчёты:**
- Всего statements: 44 043 (из pytest-cov)
- Всего missed: 41 133
- Текущее покрытие: 2 910 / 44 043 = 6.6%

**Важное уточнение:** Line coverage 90% означает покрытие ~39 639 statements. Для этого нужно покрыть дополнительно ~36 729 строк. Основная масса непокрытого кода -- крупные UI модули (crm_card_edit_dialog: 2038 строк, crm_tab: 3210, salaries_tab: 1645, supervision_card_edit_dialog: 1719, contract_dialogs: 5580 и т.д.), которые требуют либо глубокого mock-тестирования, либо интеграционных UI тестов.

| Этап | Новых statements покрыто | Cumulative coverage | Cumulative % |
|------|-------------------------|--------------------|----|
| **Текущее** | -- | 2 910 | **7%** |
| **Инфраструктура** | 0 | 2 910 | 7% |
| **Этап 1: Усиление** | +1 700 | 4 610 | **10.5%** |
| **Этап 2: Пробелы** | +3 500 | 8 110 | **18.4%** |
| **Этап 3: Hardening** | +2 800 | 10 910 | **24.8%** |

### Разрыв до 90% и стратегия преодоления

Покрытие 90% требует ~39 639 покрытых statements. После Этапов 1-3 покрыто ~10 910. Разрыв: ~28 729 statements.

**Основные источники непокрытого кода (оставшиеся ~29K строк):**

| Категория | Statements | % от разрыва | Стратегия |
|-----------|-----------|---|-----------|
| Крупные UI диалоги и вкладки | ~18 000 | 63% | Глубокие UI mock-тесты с QTest.keyClick, QTest.mouseClick |
| data_access.py (2192 stmts, 80% непокрыто) | ~1 750 | 6% | Системные mock тесты каждого метода |
| server/routers/ (непокрытые ветки) | ~3 000 | 10% | E2E тесты с edge case параметрами |
| database/db_manager.py | ~2 000 | 7% | DB тесты с каждым методом |
| utils/ (большие модули) | ~3 000 | 10% | Unit + Integration тесты |
| Прочее | ~979 | 4% | По мере необходимости |

### Дополнительные этапы для 90% (оценка)

| Этап | Описание | Statements | Дни Claude |
|------|----------|-----------|------------|
| **Этап 4** | Глубокие UI тесты: crm_tab, salaries_tab, employees_tab, crm_card_edit_dialog, supervision_card_edit_dialog (QTest взаимодействия) | +6 000 | 10-12 |
| **Этап 5** | Полное покрытие data_access.py (каждый метод, online+offline) | +1 750 | 4-5 |
| **Этап 6** | Полное покрытие server/routers/ (все ветки, edge cases) | +3 000 | 6-8 |
| **Этап 7** | Полное покрытие database/db_manager.py | +2 000 | 4-5 |
| **Этап 8** | Полное покрытие UI диалогов (contract_dialogs, crm_dialogs, supervision_dialogs) | +8 000 | 12-15 |
| **Этап 9** | Покрытие мелких модулей + gaps | +3 000 | 4-6 |
| **ИТОГО до 90%** | | +23 750 | 40-51 |

### Суммарная таблица

| Milestone | Coverage | Statements покрыто | Cumulative Claude-дни |
|-----------|---------|-------------------|-----------------------|
| Текущее | 7% | 2 910 | 0 |
| После Этапа 1 | 10.5% | 4 610 | 3-4 |
| После Этапа 2 | 18.4% | 8 110 | 11-14 |
| После Этапа 3 | 24.8% | 10 910 | 17-22 |
| После Этапа 4 | 38% | 16 910 | 27-34 |
| После Этапа 5 | 42% | 18 660 | 31-39 |
| После Этапа 6 | 49% | 21 660 | 37-47 |
| После Этапа 7 | 54% | 23 660 | 41-52 |
| После Этапа 8 | 72% | 31 660 | 53-67 |
| После Этапа 9 | **79%** | 34 660 | 57-73 |

**Реалистичная цель:** Достижение **80% line coverage** за 57-73 Claude-дня. Для 90% потребуется ещё ~10-15 Claude-дней на покрытие оставшихся edge-cases и UI ветвлений (итого ~70-90 Claude-дней).

### Альтернативная метрика: "Способность ловить баги"

Line coverage -- не единственная метрика. "Способность ловить баги" (mutation score) может быть 90% при 50% line coverage, если тесты проверяют бизнес-инварианты, а не просто вызывают код.

| Метрика | Текущее | После Этапа 3 | Цель |
|---------|---------|---------------|------|
| Line coverage | 7% | 25% | 80-90% |
| Content assert ratio (E2E) | 30% | 85% | >90% |
| Mutation score (top-10 модулей) | не измерялось | ~60% | >80% |
| CI test count | 410 | ~1 640 | ~2 600 |
| Модулей с хотя бы 1 тестом | ~55% | ~95% | 100% |

---

## Часть 6: Порядок реализации

### Gantt-подобная диаграмма

```
ДЕНЬ    1    2    3    4    5    6    7    8    9   10   11   12   13   14   15   16   17   18   19   20   21   22
        |====ИНФРА====|============ЭТАП 1============|=================ЭТАП 2=================|=======ЭТАП 3========|
        |              |                              |                                        |                     |

ИНФРА (параллельно):
INFRA-01  [====]                                              conftest fix
INFRA-02  [==]                                                CI test-client
INFRA-03  [==]                                                CI test-backend
INFRA-04       [==]                                           pytest-cov в CI
INFRA-05       [====]                                         contract fixtures

ЭТАП 1 (параллельные группы):
Группа A (E2E deep):
E2E-DEEP-01      [===]                                       dashboard deep
E2E-DEEP-02      [===]                                       statistics deep
E2E-DEEP-03       [==]                                       reports deep
E2E-DEEP-04       [=]                                        agents deep
E2E-DEEP-05        [=]                                       sync deep
E2E-DEEP-06        [=]                                       notifications deep
E2E-DEEP-07        [=]                                       heartbeat deep
E2E-DEEP-08        [=]                                       templates deep

Группа B (параллельно с A):
REWRITE-01       [=====]                                     offline rewrite

ЭТАП 2 (параллельные группы):
Группа C (без зависимостей):
E2E-NEW-01            [===]                                  cities E2E
UTIL-01               [==]                                   db_security
UTIL-02               [===]                                  pdf_generator
UTIL-03                [==]                                  calendar_helpers
UTIL-04                [=]                                   button_debounce

Группа D (зависит от INFRA-01):
UI-01                  [===]                                 admin_dialog
UI-02                  [====]                                agents_cities
UI-03                   [===]                                permissions
UI-04                   [====]                               supervision_timeline
UI-05                    [====]                              timeline_widget

Группа E (зависит от contract fixtures):
CONTRACT-01                [=====]                           contract tests
INFRA-06                        [=]                          CI test-contract

Группа F (зависит от REWRITE-01):
OFFLINE-01                 [=====]                           offline manager

Группа G (параллельно):
UTIL-05                    [=====]                           db_sync
UTIL-06                     [===]                            update_manager
UTIL-07                     [=====]                          misc utils
UI-06                       [===========]                    15 UI modules

ЭТАП 3 (параллельные группы):
Группа H:
MIGRATION-01                            [====]              migration paths
PROPERTY-01                             [====]              property-based
ROLES-01                                [=====]             role restrictions

Группа I (зависит от этапа 2):
DUAL-MODE-01                                 [=====]        dual mode
UI-INTERACT-01                               [========]     UI interactions
REGRESSION-01                                     [====]    regression suite
```

### Параллелизм

| Этап | Параллельные задачи | Последовательные зависимости |
|------|---------------------|------------------------------|
| Инфра | INFRA-01, INFRA-02, INFRA-03 -- все параллельно | INFRA-04 после 02+03. INFRA-05 после 01 |
| Этап 1 | E2E-DEEP-01..08 все параллельно. REWRITE-01 параллельно с ними | -- |
| Этап 2 | UTIL-01..07 параллельно. UI-01..06 параллельно (после INFRA-01). CONTRACT-01 параллельно (после INFRA-05) | OFFLINE-01 после REWRITE-01. INFRA-06 после CONTRACT-01 |
| Этап 3 | MIGRATION-01, PROPERTY-01, ROLES-01 параллельно | DUAL-MODE-01 после OFFLINE-01. UI-INTERACT-01 после UI-01..06. REGRESSION-01 после всех |

### Критический путь

```
INFRA-01 -> UI-01..06 -> UI-INTERACT-01 -> REGRESSION-01
     |
     +-> INFRA-05 -> CONTRACT-01 -> INFRA-06

REWRITE-01 -> OFFLINE-01 -> DUAL-MODE-01

E2E-DEEP-01..08 (независимый, начинается сразу)
```

Критический путь: **INFRA-01 -> UI модули -> UI взаимодействия -> Regression** = ~18 дней.
Параллельная работа сокращает до ~17-22 дней (Этапы 1-3).

---

## Приложение A: Сводная таблица задач

| ID | Задача | Файл(ы) тестов | Файл(ы) кода | Тестов | Приоритет | Зависит от | Прирост п.п. | Часы Claude |
|----|--------|---------------|-------------|--------|-----------|------------|------------|-------------|
| INFRA-01 | Исправить conftest | tests/conftest.py | database/db_manager.py | 0 | P0 | -- | 0 | 2 |
| INFRA-02 | CI test-client | .github/workflows/ci.yml | -- | 0 | P0 | -- | 0 | 1 |
| INFRA-03 | CI test-backend | .github/workflows/ci.yml | -- | 0 | P0 | -- | 0 | 1 |
| INFRA-04 | pytest-cov в CI | ci.yml, pyproject.toml | -- | 0 | P1 | 02,03 | 0 | 1 |
| INFRA-05 | Contract fixtures | tests/contract/ | schemas.py, db_manager.py | 0 | P1 | 01 | 0 | 2 |
| E2E-DEEP-01 | Dashboard deep | test_e2e_dashboard.py | dashboard_router.py | +0 | P0 | -- | +0.8 | 1.5 |
| E2E-DEEP-02 | Statistics deep | test_e2e_statistics.py | statistics_router.py | +0 | P0 | -- | +0.7 | 1.5 |
| E2E-DEEP-03 | Reports deep | test_e2e_reports.py | reports_router.py | +3 | P0 | -- | +0.3 | 1 |
| E2E-DEEP-04 | Agents deep | test_e2e_agents_crud.py | agents_router.py | +2 | P1 | -- | +0.1 | 0.75 |
| E2E-DEEP-05 | Sync deep | test_e2e_sync_data.py | sync_router.py | +2 | P1 | -- | +0.2 | 0.75 |
| E2E-DEEP-06 | Notifications deep | test_e2e_notifications.py | crm_router.py | +2 | P1 | -- | +0.1 | 0.75 |
| E2E-DEEP-07 | Heartbeat deep | test_e2e_heartbeat.py | heartbeat_router.py | +1 | P2 | -- | +0.05 | 0.5 |
| E2E-DEEP-08 | Templates deep | test_e2e_project_templates.py | project_templates_router.py | +1 | P2 | -- | +0.05 | 0.5 |
| REWRITE-01 | Offline rewrite | test_offline_online.py, test_offline.py | offline_manager.py, base.py | +0 | P0 | -- | +1.2 | 3 |
| E2E-NEW-01 | Cities E2E | test_e2e_cities.py (new) | cities_router.py | +8 | P0 | 01 | +0.2 | 1.5 |
| UTIL-01 | db_security | test_db_security.py (new) | db_security.py | +12 | P0 | -- | +0.13 | 1 |
| UTIL-02 | pdf_generator | test_pdf_generator.py (new) | pdf_generator.py | +10 | P1 | -- | +0.18 | 1.5 |
| UTIL-03 | calendar_helpers | test_calendar_helpers.py (new) | calendar_helpers.py | +10 | P1 | -- | +0.1 | 1 |
| UTIL-04 | button_debounce | test_button_debounce.py (new) | button_debounce.py | +6 | P2 | -- | +0.05 | 0.5 |
| UTIL-05 | db_sync | test_db_sync.py (new) | db_sync.py | +12 | P1 | 01 | +0.5 | 2.5 |
| UTIL-06 | update_manager | test_update_manager.py (new) | update_manager.py | +8 | P2 | -- | +0.2 | 1.5 |
| UTIL-07 | Остальные утилиты | test_misc_utils.py (new) | 8 файлов | +22 | P2 | -- | +0.6 | 3 |
| OFFLINE-01 | OfflineManager unit | test_offline_manager.py (new) | offline_manager.py | +15 | P1 | RW-01 | +0.8 | 3 |
| CONTRACT-01 | Contract tests | tests/contract/ (new) | schemas.py, db_manager.py, data_access.py | +25 | P0 | 05 | +0.3 | 3 |
| INFRA-06 | CI test-contract | ci.yml | -- | 0 | P1 | CT-01 | 0 | 0.5 |
| UI-01 | admin_dialog | test_admin_dialog.py (new) | admin_dialog.py | +8 | P1 | 01 | +0.3 | 1.5 |
| UI-02 | agents_cities | test_agents_cities_widget.py (new) | agents_cities_widget.py | +10 | P0 | 01 | +0.35 | 2 |
| UI-03 | permissions_matrix | test_permissions_matrix.py (new) | permissions_matrix_widget.py | +8 | P1 | 01 | +0.25 | 1.5 |
| UI-04 | supervision_timeline | test_supervision_timeline.py (new) | supervision_timeline_widget.py | +8 | P1 | 01 | +0.4 | 2 |
| UI-05 | timeline_widget | test_timeline_widget.py (new) | timeline_widget.py | +8 | P1 | 01 | +0.4 | 2 |
| UI-06 | 15 UI modules | 9 new files | 15 modules | +75 | P2 | 01 | +2.5 | 6 |
| MIGRATION-01 | Migration paths | test_migration_paths.py (new) | db_manager.py | +10 | P1 | 01 | +0.3 | 2 |
| PROPERTY-01 | Property-based | test_validators_property.py (new) | validators.py | +12 | P2 | -- | +0.2 | 2 |
| ROLES-01 | Role restrictions | test_e2e_role_restrictions.py (new) | auth.py, permissions.py | +20 | P1 | E2E-* | +0.5 | 3 |
| DUAL-MODE-01 | Dual mode | test_data_access_dual_mode.py (new) | data_access.py | +15 | P1 | OFF-01 | +1.5 | 3 |
| UI-INTERACT-01 | UI interactions | existing UI test files | crm_tab, salaries_tab, etc. | +30 | P2 | UI-* | +2.0 | 4 |
| REGRESSION-01 | Regression suite | test_regression.py | all modules | +10 | P2 | all | +0.3 | 2 |

**Итого задач:** 36
**Итого новых тестов:** +371
**Итого прирост line coverage:** +17.8 п.п. (с 7% до ~25%)
**Итого Claude-часов:** ~68 (~8.5 Claude-дней по 8 часов)
**Общее время с параллелизмом:** 17-22 Claude-дня

---

## Приложение B: Чеклист Planner Agent

- [x] Все затронутые слои определены (server, ui, utils, database, CI)
- [x] Все затронутые файлы найдены (93 тестовых + 84 исходных)
- [x] Подзадачи имеют чёткие зависимости
- [x] Категории тестов определены (e2e, db, client, contract, ui, regression)
- [x] Параллелизм максимизирован (до 6 параллельных групп)
- [x] Режим конвейера соответствует задаче (full)
- [x] roadmap.md создан в docs/plan/test-coverage-90/
- [x] Фазы с ревью определены в roadmap
- [x] Конкретные тестовые кейсы с именами и проверками
- [x] Реалистичные оценки времени
- [x] Прирост покрытия рассчитан для каждой задачи
