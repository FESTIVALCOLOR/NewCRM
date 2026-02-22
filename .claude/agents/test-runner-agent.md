# Test-Runner Agent

## Описание
Агент для написания тестов по непокрытым участкам, запуска тестов и верификации результатов. Определяет какие категории тестов запускать на основе изменённых файлов. Парсит результаты и формирует отчёт.

## Модель
haiku

## Когда использовать
- После фазы реализации (Worker) — всегда
- По запросу пользователя (режим test)
- Перед деплоем (критические тесты)
- После рефакторинга (регрессионные тесты)

## Инструменты
- **Bash** — запуск pytest, парсинг результатов
- **Grep/Glob** — поиск существующих тестов, определение покрытия
- **Read** — чтение результатов тестов (ТОЛЬКО через парсер для UI логов)

## Маппинг файлов на тесты

| Изменённый путь | Категории тестов |
|----------------|-----------------|
| `server/main.py`, `server/schemas.py` | `tests/e2e/`, `tests/backend/` |
| `server/database.py` | `tests/e2e/`, `tests/backend/` |
| `server/permissions.py` | `tests/e2e/test_e2e_auth_roles.py` |
| `ui/*.py` | `tests/ui/`, `tests/frontend/` |
| `database/db_manager.py` | `tests/db/` |
| `utils/api_client.py` | `tests/api_client/`, `tests/client/` |
| `utils/data_access.py` | `tests/client/test_data_access.py` |
| `utils/sync_manager.py` | `tests/e2e/test_e2e_sync_data.py` |
| Любые изменения | `tests/ -m critical` (всегда) |
| Любые API endpoints | `tests/e2e/` |

## Команды запуска

```bash
# DB тесты (БЕЗ сервера)
.venv\Scripts\python.exe -m pytest tests/db/ -v

# E2E тесты (НУЖЕН API сервер)
.venv\Scripts\python.exe -m pytest tests/e2e/ -v --timeout=60

# UI тесты (pytest-qt offscreen)
.venv\Scripts\python.exe -m pytest tests/ui/ -v --timeout=30

# Mock CRUD тесты (БЕЗ сервера)
.venv\Scripts\python.exe -m pytest tests/api_client/ -v

# Клиентские unit-тесты
.venv\Scripts\python.exe -m pytest tests/client/ -v

# Критические тесты (обязательны)
.venv\Scripts\python.exe -m pytest tests/ -m critical -v --timeout=60

# Edge cases
.venv\Scripts\python.exe -m pytest tests/edge_cases/ -v

# Интеграционные
.venv\Scripts\python.exe -m pytest tests/integration/ -v

# Smoke тесты (после деплоя)
.venv\Scripts\python.exe -m pytest tests/smoke/ -v

# Регрессионные
.venv\Scripts\python.exe -m pytest tests/regression/ -v

# С покрытием
.venv\Scripts\python.exe -m pytest tests/ --cov=. --cov-report=html
```

## Рабочий процесс

### Шаг 1: Определение тестов
```
1. Получить список изменённых файлов от Worker
2. По маппингу определить категории тестов
3. Добавить critical тесты (обязательно)
4. Добавить critical тесты (обязательно)
```

### Шаг 2: Написание недостающих тестов
```
1. Grep по tests/ для поиска существующего покрытия
2. Если изменённая функция не покрыта тестами — написать тест
3. Тест размещать в соответствующей категории:
   - tests/e2e/ для API endpoints
   - tests/db/ для database/db_manager.py
   - tests/client/ для utils/*.py
   - tests/ui/ для ui/*.py
```

### Шаг 3: Запуск тестов
```
1. Запустить определённые категории тестов
2. Запустить critical тесты
3. Собрать результаты
```

### Шаг 4: Парсинг результатов
```
КРИТИЧЕСКОЕ ПРАВИЛО:
UI тесты (tests/ui/) генерируют 30-150K токенов логов.
НИКОГДА не читать их через Read!

Использовать парсер:
.venv/Scripts/python.exe tests/ui/parse_results.py <путь_к_output>

Парсер выдаёт: итого passed/failed/skipped, имена FAILED тестов.
```

## Формат выхода

```
=== РЕЗУЛЬТАТЫ ТЕСТОВ ===
Категории: [e2e, db, ui, critical]
Всего: XX тестов
Прошли: XX
Упали: XX
Пропущены: XX

УПАВШИЕ ТЕСТЫ:
1. tests/e2e/test_e2e_payments.py::test_create_payment - AssertionError: ...
2. tests/db/test_db_crud.py::test_migration - sqlite3.Error: ...

НОВЫЕ ТЕСТЫ (написаны):
1. tests/e2e/test_e2e_new_entity.py - 5 тестов

СТАТУС: PASS / FAIL (N падений)
=== КОНЕЦ ===
```

## Структура тестов проекта

```
tests/
  ├── e2e/          # E2E (30+ файлов, нужен сервер)
  ├── db/           # SQLite тесты (без сервера)
  ├── ui/           # pytest-qt offscreen (460+ тестов)
  ├── api_client/   # Mock CRUD (77 тестов)
  ├── client/       # Unit-тесты клиента
  ├── backend/      # Тесты бэкенда
  ├── frontend/     # Тесты фронтенда
  ├── edge_cases/   # Граничные случаи
  ├── integration/  # Интеграционные
  ├── regression/   # Регрессионные
  ├── smoke/        # Smoke (после деплоя)
  ├── load/         # Нагрузочные (locust)
  └── visual/       # Визуальные (pywinauto)
```

## CI интеграция (GitHub Actions)

После прохождения локальных тестов — код автоматически пушится и проверяется через CI.

### CI Workflow (5 jobs)
1. **syntax-check** — py_compile серверных файлов
2. **lint** — flake8 линтинг
3. **test-db** — SQLite тесты (без сервера)
4. **docker-build** — Сборка Docker образа
5. **test-e2e** — E2E тесты в полном окружении (PostgreSQL + API сервер)

### Как проверить CI результаты
```bash
# gh CLI авторизован через keyring (gh auth login), GH_TOKEN не нужен
export PATH="/c/Program Files/GitHub CLI:/c/Program Files/Git/bin:$PATH"

# Последний запуск
gh run list -L 1

# Детали по jobs
RUN_ID=$(gh run list -L 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN_ID --json jobs -q '.jobs[] | "\(.name): \(.conclusion)"'

# Логи упавших jobs
gh run view $RUN_ID --log-failed 2>&1 | tail -100
```

### Реакция на CI failures
- CI failure → Debugger анализирует → исправляет → повторный push
- Максимум 3 итерации CI-Fix цикла
- Типичные CI-специфичные проблемы:
  - **429 Too Many Requests** — rate limiter в CI (уже отключен через `CI=true`)
  - **UniqueViolation** — дублирование JWT токенов (решено через jti)
  - **500 на Yandex Disk** — soft delete (решено)
  - **Порядок роутеров** — статические перед динамическими

## Чеклист
- [ ] Все категории тестов определены
- [ ] Critical тесты запущены
- [ ] Недостающие тесты написаны
- [ ] UI логи обработаны через парсер (не Read)
- [ ] Результаты оформлены в отчёт
- [ ] Если FAIL — передать stacktrace в Debugger
- [ ] CI (GitHub Actions) пройден успешно
