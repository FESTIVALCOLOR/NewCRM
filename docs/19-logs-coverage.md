# Логи и покрытие

> Логирование, мониторинг, отладка, покрытие кода.

## Система логирования

### Файл: [utils/logger.py](../utils/logger.py)

Централизованная система логирования приложения.

### Логгеры

| Логгер | Назначение |
|--------|-----------|
| `app_logger` | Основной логгер приложения |
| `log_database_operation()` | Логирование DB операций |
| `log_api_request()` | Логирование API запросов |
| `log_sync_operation()` | Логирование синхронизации |

### Уровни логирования

| Уровень | Использование |
|---------|--------------|
| DEBUG | Детальная отладка (не в production) |
| INFO | Нормальные операции (вход, загрузка данных) |
| WARNING | Ожидаемые проблемы (fallback на DB, retry) |
| ERROR | Ошибки (API недоступен, ошибка сохранения) |
| CRITICAL | Критические сбои (не удалось запустить приложение) |

### Формат логов (pytest.ini)

```
%(asctime)s [%(levelname)s] %(message)s
2026-02-14 15:30:45 [INFO] Loading CRM cards...
2026-02-14 15:30:46 [WARN] API timeout, fallback to local DB
2026-02-14 15:30:47 [ERROR] Failed to save payment: Connection refused
```

## Логи сервера (Docker)

### Просмотр в реальном времени

```bash
ssh timeweb
cd /opt/interior_studio
docker-compose logs -f api          # все логи API
docker-compose logs --tail=50 api   # последние 50 строк
docker-compose logs -f postgres     # логи PostgreSQL
```

### Формат логов сервера

```
INFO:     147.45.154.193:0 - "GET /api/clients HTTP/1.1" 200 OK
WARNING:  Payment calculation failed for contract 42
ERROR:    Database connection lost, reconnecting...
```

## Логи клиента

### Консольные логи

При запуске через `.venv\Scripts\python.exe main.py` логи выводятся в консоль.

### Паттерны логирования в коде

```python
# API запросы
print(f"[API] GET /api/clients → {len(result)} records")
print(f"[API] Error: {e}, fallback to local DB")

# Offline
print(f"[OFFLINE] Operation queued: {operation_type} {entity_type}")
print(f"[SYNC] Syncing {count} pending operations...")

# UI
print(f"[UI] Loading tab: {tab_name}")
print(f"[UI] Card moved from {from_col} to {to_col}")
```

## Логи тестов

### pytest вывод

```bash
pytest tests/ -v --tb=short --log-cli-level=INFO
```

### Формат

```
2026-02-14 15:30:45 [INFO] === Test session started ===
PASSED tests/e2e/test_e2e_clients.py::test_create_client
FAILED tests/e2e/test_e2e_payments.py::test_calculate_payment - AssertionError
2026-02-14 15:31:20 [INFO] === 24 passed, 1 failed ===
```

## Покрытие кода

### Текущий статус покрытия

#### Покрытие по файлам

| Файл | E2E | DB | Unit | Статус |
|------|-----|-----|------|--------|
| server/main.py (144 EP) | ~80% EP | — | — | Средний |
| server/database.py | Косвенно | Да | — | Средний |
| server/schemas.py | Косвенно | — | — | Низкий |
| server/auth.py | Да | — | — | Высокий |
| database/db_manager.py | — | Да | — | Средний |
| utils/api_client.py | Косвенно | — | — | Низкий |
| utils/data_access.py | Косвенно | — | — | Низкий |
| utils/offline_manager.py | — | — | — | НЕТ |
| utils/sync_manager.py | — | — | — | НЕТ |
| utils/db_sync.py | Косвенно | — | — | Низкий |
| utils/validators.py | Высокий | test_validators.py | 75+ тестов | Высокий |
| utils/yandex_disk.py | Средний | test_e2e_files_yandex.py | 21 тест | Средний |
| ui/crm_tab.py | Высокий | test_crm.py (pytest-qt) | 92 теста | Высокий |
| ui/contracts_tab.py | Высокий | test_contracts.py (pytest-qt) | 44 теста | Высокий |
| ui/salaries_tab.py | Высокий | test_salaries.py (pytest-qt) | 34 теста | Высокий |

#### Покрытие по функциональности

| Функциональность | Покрытие | Тест |
|-----------------|----------|------|
| Авторизация | Высокий | test_e2e_auth_roles |
| CRUD клиентов | Высокий | test_e2e_clients + test_db_crud |
| CRUD договоров | Высокий | test_e2e_contracts + test_db_crud |
| CRM lifecycle | Высокий | test_e2e_crm_lifecycle |
| Исполнители | Средний | test_e2e_crm_executors |
| Дедлайны | Средний | test_e2e_crm_deadlines |
| Согласование | Средний | test_e2e_crm_approval |
| Надзор | Средний | test_e2e_supervision |
| Платежи | Высокий | test_e2e_payments |
| Файлы DB | Высокий | test_e2e_files_db |
| Файлы Я.Диск | Высокий | test_e2e_files_yandex (21 тест) |
| Дашборд | Средний | test_e2e_dashboard |
| PDF экспорт | Низкий | test_e2e_pdf_export |
| Миграции | Высокий | test_db_migrations |
| Полный workflow | Высокий | test_e2e_full_workflow |
| Offline режим | Средний | test_edge_cases.py (4 теста), test_offline.py |
| Синхронизация | Средний | test_e2e_heartbeat (3), test_e2e_sync_data, test_e2e_locks (11) |
| UI виджеты | Высокий | 460 pytest-qt тестов (13 файлов) |
| Timeline | Высокий | test_e2e_timeline (15), test_e2e_supervision_timeline (7) |
| APIClient CRUD | Высокий | test_api_crud.py (77 тестов) |
| QSS стили | Низкий | test_unified_styles.py (9 тестов) |
| Кэширование | Средний | test_cache_manager.py (15 тестов) |

### Рекомендации по увеличению покрытия (выполнено)

#### Приоритет 1 (Критические) — выполнено

1. ~~**utils/offline_manager.py**~~ — test_offline.py + test_edge_cases.py (offline UI)
2. ~~**utils/api_client.py**~~ — test_api_crud.py, 77 mock CRUD тестов
3. ~~**utils/validators.py**~~ — test_validators.py, 75+ unit-тестов

#### Приоритет 2 (Важные) — выполнено

4. ~~**Timeline endpoints**~~ — test_e2e_timeline.py, 15 E2E тестов
5. ~~**Supervision timeline**~~ — test_e2e_supervision_timeline.py, 7 E2E тестов
6. **utils/sync_manager.py** — частично (test_e2e_heartbeat, test_e2e_sync_data, test_e2e_locks)

#### Приоритет 3 (Желательные) — выполнено

7. ~~**UI виджеты**~~ — 460 pytest-qt тестов (13 файлов, offscreen)
8. ~~**Нагрузочное**~~ — locustfile.py, 9 task-методов
9. **server/schemas.py** — test_schemas.py (tests/backend/)

## Покрытие хуками

### Текущие хуки ([.claude/settings.local.json](../.claude/settings.local.json))

| Хук | Триггер | Что проверяет |
|-----|---------|--------------|
| PostToolUse: Edit | Каждый Edit | Emoji, resource_path, border, deploy |
| PostToolUse: Write | Каждый Write | Emoji, resource_path, __init__.py |
| PreToolUse: Bash | Каждый Bash | Git commit emoji, py_compile |
| Stop | Завершение | Совместимость server-client |

### Что НЕ покрыто хуками

| Действие | Рекомендуемый хук | Приоритет |
|---------|-------------------|-----------|
| Изменение API response формата | PostToolUse: Edit (server/main.py) → проверка совместимости с api_client | Высокий |
| Удаление __init__.py | PostToolUse: Edit/Write → проверка наличия | Средний |
| Hardcoded credentials | PreToolUse: Bash (git commit) → поиск паролей | Высокий |
| Создание нового файла без UTF-8 header | PostToolUse: Write → проверка кодировки | Низкий |
| Изменение config.py (API URL) | PostToolUse: Edit → предупреждение | Средний |
| Тесты перед коммитом | PreToolUse: Bash (git commit) → pytest -m critical | Высокий |

### Рекомендуемые дополнительные хуки

#### 1. Pre-commit тесты

```json
{
    "matcher": "Bash",
    "hooks": [{
        "type": "prompt",
        "prompt": "If this is a git commit: remind to run 'pytest tests/ -m critical' first. Output '[PRE-COMMIT] Run critical tests before committing'",
        "model": "claude-haiku-4-5-20251001"
    }]
}
```

#### 2. Security check

```json
{
    "matcher": "Write",
    "hooks": [{
        "type": "prompt",
        "prompt": "Check if the written file contains hardcoded passwords, API keys, or tokens. Flag as '[SECURITY] Hardcoded credentials detected'",
        "model": "claude-haiku-4-5-20251001"
    }]
}
```

#### 3. API compatibility check

```json
{
    "matcher": "Edit",
    "hooks": [{
        "type": "prompt",
        "prompt": "If editing server/main.py or server/schemas.py: remind to check utils/api_client.py for compatibility. Output '[COMPAT] Check api_client.py for matching methods'",
        "model": "claude-haiku-4-5-20251001"
    }]
}
```
