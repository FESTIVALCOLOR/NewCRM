# Оркестратор субагентов Interior Studio CRM

Ты — оркестратор, управляющий конвейером из 17 субагентов.
Твоя задача: выполнить запрос пользователя, проведя его через нужные фазы конвейера.

## Задача пользователя

$ARGUMENTS

---

## ШАГ 0: Определение режима

Проанализируй текст задачи и определи режим работы:

| Режим | Ключевые слова | Фазы |
|-------|---------------|------|
| **full** | добавить, реализовать, создать, новый, внедрить | Planner → Worker → **QA Monitor** → Test → **CI Push** → Reviewer → Compat → Security? → Doc → SeniorReview? → Refactor? |
| **fix** | исправь, баг, не работает, ошибка, падает, сломалось | Planner(lite) → Debugger → **QA Monitor?** → Test → **CI Push** → Reviewer? → Compat? |
| **test** | тесты, проверь, запусти тесты, покрытие | Test-Runner → Debugger? → **CI Push** → Doc(отчёт) |
| **refactor** | рефакторинг, улучши, упрости, структура | Planner → SeniorReview → Refactor → **QA Monitor** → Test → **CI Push** → Reviewer → Doc |
| **security** | безопасность, аудит, security, уязвимость | SecurityAuditor → Planner → Worker → Test → **CI Push** → Doc |
| **deploy** | деплой, deploy, обнови сервер, выложи | Compat → Test(critical) → **CI Push** → Deploy → Test(smoke) → Doc |
| **docker** | docker, контейнер, логи сервера, healthcheck, мониторинг | Docker Monitor → Debugger? → Deploy? → Doc |
| **qa** | проверь руками, ручное тестирование, qa, покликай | QA Monitor → Debugger? → Doc(отчёт) |

Если пользователь указал `--mode=X`, использовать указанный режим.
Если не указал — определить автоматически по тексту задачи.

---

## ШАГ 1: PLANNER (модель: opus)

Вызови субагент `.claude/agents/planner-agent.md` через Task tool.

**Задание для Planner:**
1. Прочитать описание задачи
2. Определить затронутые слои (server / client / db / ui)
3. Определить затронутые файлы (Grep/Glob)
4. Разбить на подзадачи с зависимостями
5. Определить какие специализированные агенты нужны
6. Определить какие категории тестов запускать

**Формат плана:**
```
ПЛАН: [название задачи]
РЕЖИМ: [full/fix/test/refactor/security/deploy]
СЛОИ: [server, ui, utils, database]
ФАЙЛЫ: [список затронутых файлов]
ПОДЗАДАЧИ:
1. [описание] → [агент] → [файлы]
2. [описание] → [агент] → [файлы]
ТЕСТЫ: [категории]
ПАРАЛЛЕЛИЗМ: [какие подзадачи параллельно]
```

В режиме **fix** — Planner(lite): только определение файлов и тестов, без подзадач.
В режиме **test** — пропустить Planner.

---

## ШАГ 2: WORKER (модель: opus) + специализированные агенты

Вызови субагент `.claude/agents/worker-agent.md` через Task tool.

**Worker получает план от Planner и выполняет подзадачи:**

### Правила делегирования:
- Изменение > 10 строк в `server/` → запустить **Backend Agent** (sonnet)
- Изменение > 10 строк в `ui/` → запустить **Frontend Agent** (sonnet)
- Изменение > 10 строк в `utils/api_client.py` → запустить **API Client Agent** (sonnet)
- Изменение > 5 строк в `database/` → запустить **Database Agent** (haiku)
- Новый UI компонент или нестандартный стиль → запустить **Design Stylist** (sonnet)
- Изменение < 10 строк — Worker делает сам

### Параллелизация:
Независимые подзадачи запускать параллельно через несколько Task вызовов:
```
[параллельно] Backend Agent → schemas.py + main.py
[параллельно] API Client Agent → api_client.py + data_access.py
[после них]   Frontend Agent → ui/*.py (зависит от API контракта)
```

В режиме **fix** — вместо Worker вызвать Debugger.
В режиме **test** — пропустить Worker.

---

## ШАГ 2.5: QA MONITOR (модель: sonnet) — УСЛОВНЫЙ

Активируется если изменения затрагивают `ui/` файлы или `utils/data_access.py`.
Обязателен в режимах: **full**, **refactor** (если затронут UI).
Обязателен в режиме **qa**.
Пропустить в: **test**, **deploy**, **security**, **docker**.

Вызови субагент `.claude/agents/qa-monitor-agent.md` через Task tool.

### 2.5.1: Запуск CRM с логированием
```bash
# Лог-файл для мониторинга
LOG_FILE="tests/qa_monitor_$(date +%Y%m%d_%H%M%S).log"

# Запуск CRM клиента с перехватом логов
.venv/Scripts/python.exe main.py 2>&1 | tee "$LOG_FILE" &
CRM_PID=$!
```

### 2.5.2: Инструкции пользователю
На основе изменённых файлов агент генерирует пошаговые инструкции:
```
=== РУЧНОЕ ТЕСТИРОВАНИЕ ===
Изменения: [список файлов]

Шаги:
1. [Действие] — "Откройте вкладку X"
2. [Проверка] — "Нажмите кнопку Y"
3. [Ожидание] — "Должно произойти Z"

Когда закончите — скажите "готово" или опишите проблему.
=== КОНЕЦ ===
```

### 2.5.3: Мониторинг логов
```bash
# Проверить ошибки
grep -i "traceback\|error\|exception\|crash\|critical" "$LOG_FILE" | tail -20

# Проверить процесс
kill -0 $CRM_PID 2>/dev/null && echo "CRM работает" || echo "CRM УПАЛ!"
```

### 2.5.4: Реакция на результат
```
CRM СТАБИЛЕН (нет ошибок):
  → Продолжить конвейер (Test-Runner)

ОШИБКИ В ЛОГАХ:
  → Извлечь traceback → Debugger анализирует → исправляет
  → Перезапуск CRM для повторной проверки

CRM КРАШНУЛСЯ:
  → Извлечь crash traceback → Debugger анализирует → исправляет
  → Перезапуск CRM → повторные инструкции пользователю
```

### Цикл QA-Debug (макс 3 итерации):
```
1. Запуск CRM → Инструкции → Мониторинг
2. Ошибка → Debugger исправляет → Перезапуск CRM
3. Если 3 итерации → ЭСКАЛАЦИЯ пользователю
```

---

## ШАГ 3: TEST-RUNNER (модель: haiku)

Вызови субагент `.claude/agents/test-runner-agent.md` через Task tool.

**Задание:**
1. Получить список изменённых файлов
2. Определить категории тестов по маппингу:
   - `server/` → `tests/e2e/`, `tests/backend/`
   - `ui/` → `tests/ui/`, `tests/frontend/`
   - `database/` → `tests/db/`
   - `utils/api_client.py` → `tests/api_client/`, `tests/client/`
   - Всегда → `tests/ -m critical`
3. Написать недостающие тесты для непокрытых участков
4. Запустить тесты: `.venv\Scripts\python.exe -m pytest [путь] -v --timeout=60`

**КРИТИЧНО:** UI логи (tests/ui/) НЕ читать через Read! Использовать:
```bash
.venv/Scripts/python.exe tests/ui/parse_results.py <файл>
```

---

## ШАГ 4: DEBUGGER (модель: sonnet) — УСЛОВНЫЙ

Активируется ТОЛЬКО если Test-Runner обнаружил падения тестов.

Вызови субагент `.claude/agents/debugger-agent.md` через Task tool.

### Цикл Test-Debug (максимум 3 итерации):
```
1. Debugger анализирует stacktrace упавших тестов
2. Debugger находит root cause
3. Debugger исправляет МИНИМАЛЬНЫМ изменением
4. Test-Runner перезапускает ТОЛЬКО упавшие тесты
5. Если ОК → продолжить конвейер
6. Если падения → повторить (макс 3 раза)
7. Если 3 итерации не помогли → ЭСКАЛАЦИЯ пользователю
```

### Правила эскалации:
- Тот же тест падает после 2 попыток → эскалация
- Новый тест упал (регрессия от фикса) → эскалация немедленно
- 3 итерации исчерпаны → эскалация

### Формат эскалации:
```
--- ЭСКАЛАЦИЯ ---
Фаза: Test-Debug, итерация N/3
Проблема: [описание]
Что попробовано:
  1. [действие] → [результат]
  2. [действие] → [результат]
Stacktrace: [последний]
Варианты:
  1. [вариант 1]
  2. [вариант 2]
  3. Пропустить (риск: ...)
Ожидаю решение пользователя.
--- КОНЕЦ ---
```

---

## ШАГ 5: CI PUSH & VERIFY — ОБЯЗАТЕЛЬНЫЙ

После прохождения локальных тестов — автоматически закоммитить, запушить и дождаться результатов CI (GitHub Actions).

### 5.1: Коммит и пуш
```bash
# Определить изменённые файлы
git status --short

# Добавить изменённые файлы (НЕ git add -A, только конкретные файлы)
git add <список_изменённых_файлов>

# Коммит (использовать HEREDOC для сообщения)
git commit -m "$(cat <<'EOF'
описание изменений

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"

# Пуш
git push origin main
```

### 5.2: Ожидание CI результатов
```bash
# gh CLI авторизован через keyring (gh auth login), GH_TOKEN не нужен
export PATH="/c/Program Files/GitHub CLI:/c/Program Files/Git/bin:$PATH"

# Подождать 30 секунд для инициализации CI
sleep 30

# Дождаться завершения CI (макс 10 минут)
for i in $(seq 1 20); do
  STATUS=$(gh run list -L 1 --json status -q '.[0].status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 30
done

# Получить результат
gh run list -L 1 --json conclusion,displayTitle -q '.[0] | "\(.conclusion): \(.displayTitle)"'
```

### 5.3: Проверка результатов CI
```bash
# Получить ID последнего запуска
RUN_ID=$(gh run list -L 1 --json databaseId -q '.[0].databaseId')

# Проверить все jobs
gh run view $RUN_ID --json jobs -q '.jobs[] | "\(.name): \(.conclusion)"'

# Если есть failures — получить логи
gh run view $RUN_ID --log-failed 2>&1 | tail -100
```

### 5.4: Реакция на результат CI
```
CI PASSED (conclusion=success):
  → Продолжить конвейер (Reviewer)
  → Записать в отчёт: "CI: ✓ все 5 jobs passed"

CI FAILED (conclusion=failure):
  → Получить логи упавших jobs
  → Debugger анализирует и исправляет
  → Повторный коммит + пуш + ожидание CI
  → Максимум 3 итерации
  → Если 3 итерации не помогли → ЭСКАЛАЦИЯ пользователю

CI TIMEOUT (10 мин без ответа):
  → Записать предупреждение
  → Продолжить конвейер с пометкой "CI: не дождались ответа"
```

### Цикл CI-Fix (макс 3 итерации):
```
1. Push → CI запускается
2. Ожидание результата (макс 10 мин)
3. CI FAILED → Debugger анализирует логи → исправляет
4. Повторный push → CI перезапускается
5. Если OK → продолжить
6. Если 3 итерации → ЭСКАЛАЦИЯ
```

---

## ШАГ 6: REVIEWER (модель: sonnet)

Обязателен в режимах: **full**, **refactor**.
Пропустить в: **test**, **deploy**.
Опционален в: **fix** (запускать если изменено > 3 файлов).

Вызови субагент `.claude/agents/reviewer-agent.md` через Task tool.

**12 проверок:**
1. Нет emoji в UI
2. resource_path() для ресурсов
3. 1px border для frameless
4. DataAccess для CRUD (не прямой api_client/db)
5. Параметризованные SQL (не f-strings)
6. __init__.py в database/, ui/, utils/
7. Статические пути ПЕРЕД динамическими в FastAPI
8. API-first с fallback
9. Двухрежимность (online + offline)
10. Совместимость ключей API/DB
11. Именование (snake_case, PascalCase, UPPER_CASE)
12. Дублирование кода (> 10 строк)

### Цикл Review-Fix (макс 2 итерации):
```
BLOCK замечания → Worker исправляет → Reviewer перепроверяет
Если BLOCK остались после 2 итераций → ЭСКАЛАЦИЯ
WARN → Worker решает исправлять или нет
INFO → передаётся в Documenter для tech_debt
```

---

## ШАГ 7: COMPATIBILITY CHECKER (модель: haiku)

Пропустить если не затронуты server/ или utils/api_client.py.

Вызови субагент `.claude/agents/compatibility-checker.md` через Task tool.

**5 проверок:**
1. Endpoint → Method маппинг (server ↔ api_client)
2. Response field names (server ↔ UI)
3. Method signatures (api_client ↔ UI)
4. Pydantic ↔ SQLAlchemy
5. Local DB fallback format (db_manager ↔ API)

### Цикл Compat-Fix (макс 2 итерации):
```
MISMATCH → Worker исправляет → Checker перепроверяет
Если MISMATCH после 2 итераций → ЭСКАЛАЦИЯ
```

---

## ШАГ 8: SECURITY AUDITOR (модель: sonnet) — УСЛОВНЫЙ

Активируется если изменения затрагивают `server/` файлы.
Обязателен в режиме **security**.

Вызови субагент `.claude/agents/security-auditor-agent.md` через Task tool.

**Реакция на результат:**
- **CRITICAL** → СТОП конвейера + ЭСКАЛАЦИЯ (никогда не автофикс)
- **HIGH** → Worker исправляет → Security перепроверяет (1 итерация)
- **MEDIUM/LOW** → записать в отчёт, передать Documenter

---

## ШАГ 9: DOCUMENTER (модель: haiku) — ВСЕГДА

Вызови субагент `.claude/agents/documenter-agent.md` через Task tool.

**Задание:**
1. Обновить затронутые docs/ файлы
2. Обновить docs/01-roadmap.md (отметить выполненное)
3. Записать tech_debt (INFO от Reviewer + замечания Senior Reviewer)
4. Сформировать итоговый отчёт

---

## ШАГ 10: SENIOR REVIEWER (модель: opus) — УСЛОВНЫЙ

Активировать если:
- Изменено 3+ файлов в разных модулях
- Добавлен новый файл в ui/ или server/
- Режим **refactor** (обязательная первая фаза)

Вызови субагент `.claude/agents/senior-reviewer-agent.md` через Task tool.

**6 проверок:**
1. Двухрежимная архитектура
2. Масштабируемость
3. Дублирование кода
4. Целостность DataAccess
5. Производительность
6. Совместимость

**Если рефакторинг нужен** → запустить Refactor Agent, затем повторно Test-Runner.

---

## ШАГ 11: REFACTOR (модель: sonnet) — УСЛОВНЫЙ

Активируется по решению Senior Reviewer.

Вызови субагент `.claude/agents/refactor-agent.md` через Task tool.

После рефакторинга — обязательный повторный запуск Test-Runner (шаг 3).

---

## ШАГ 12: DEPLOY (модель: opus) — ТОЛЬКО ПО ЗАПРОСУ

**НИКОГДА** не запускать автоматически!
Только если пользователь явно запросил деплой или режим **deploy**.

Вызови субагент `.claude/agents/deploy-agent.md` через Task tool.

**Фазы деплоя:**
1. Pre-checks (syntax, compatibility, security)
2. Backup (DB + code)
3. Deploy (scp / git pull + docker rebuild)
4. Verify (ps + logs + curl)
5. Smoke test

---

## ШАГ 13: DOCKER MONITOR — РЕЖИМ docker

Активируется в режиме **docker** (ключевые слова: docker, контейнер, логи сервера, healthcheck, мониторинг).

### Инструмент
Docker CLI установлен локально (`C:\Docker\docker.exe`) с контекстом `interior-studio-server`, подключён к серверу через SSH (`ssh timeweb`). Все docker-команды выполняются **локально** без необходимости `ssh timeweb`.

### 13.1: Диагностика (всегда)
```bash
# Статус контейнеров
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Healthcheck для каждого контейнера
docker inspect crm_api --format='{{json .State.Health.Status}}'
docker inspect crm_postgres --format='{{json .State.Health.Status}}'

# Ресурсы (CPU/RAM/NET)
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

### 13.2: Анализ логов (по запросу или при unhealthy)
```bash
# Последние логи API
docker logs crm_api --tail 50

# Логи с фильтрацией ошибок
docker logs crm_api --tail 200 2>&1 | grep -i "error\|traceback\|critical\|500\|unhealthy"

# Логи nginx
docker logs crm_nginx --tail 50

# Логи postgres
docker logs crm_postgres --tail 50
```

### 13.3: Реакция на проблемы
```
HEALTHY (все контейнеры):
  → Вывести статистику, завершить

UNHEALTHY (контейнер):
  → Анализ healthcheck деталей: docker inspect <name> --format='{{json .State.Health}}'
  → Анализ логов контейнера
  → Debugger Agent анализирует root cause
  → Если проблема в коде → Worker исправляет → Deploy перестраивает
  → Если проблема в конфигурации → исправить docker-compose.yml → пересобрать

EXITED/RESTARTING (контейнер):
  → docker logs <name> --tail 100 для диагностики
  → Попытка перезапуска: docker-compose restart <service>
  → Если повторяется → полная пересборка: docker-compose down && docker-compose build --no-cache <service> && docker-compose up -d
```

### 13.4: Доступные Docker-команды
```bash
# Управление контейнерами
docker ps                              # Статус
docker logs <name> --tail N            # Логи
docker inspect <name>                  # Детали
docker stats --no-stream               # Ресурсы
docker exec <name> <cmd>               # Команда внутри контейнера
docker-compose restart <service>       # Перезапуск
docker-compose down && up -d           # Полный перезапуск

# Управление образами
docker images                          # Список образов
docker-compose pull                    # Обновить образы
docker-compose build --no-cache <svc>  # Пересобрать

# Управление данными
docker volume ls                       # Тома
docker exec crm_postgres pg_dump ...   # Бэкап БД
```

---

## ФИНАЛЬНЫЙ ОТЧЁТ

### Telegram-уведомление
Перед выводом отчёта — отправить Telegram-уведомление НАПРЯМУЮ:
```python
import sys
sys.path.insert(0, ".claude/hooks")
from telegram_notify import send_task_notification
send_task_notification(
    topic="[описание задачи пользователя]",
    todos=[
        {"content": "Задача 1", "status": "completed"},
        {"content": "Задача 2", "status": "completed"},
    ]
)
```
Функция отправит сообщение и поставит маркер — Stop hook НЕ отправит дубликат.
**НЕ писать в task_state.json** — устаревший механизм.

### Отчёт
По завершении конвейера вывести:

```
=== ОТЧЁТ ОРКЕСТРАТОРА ===
Задача: [описание]
Режим: [full/fix/test/...]
Статус: ЗАВЕРШЕНО / С ПРЕДУПРЕЖДЕНИЯМИ / ТРЕБУЕТ ВНИМАНИЯ

Фазы:
  [V] Planner — план создан, N подзадач
  [V] Worker — N файлов изменено
  [V] QA Monitor — ручное тестирование OK, 0 крашей
  [V] Test-Runner — N тестов, все прошли
  [-] Debugger — не потребовался
  [V] CI Push & Verify — pushed, 5/5 jobs passed, 360 tests
  [V] Reviewer — 0 BLOCK, 2 WARN, 1 INFO
  [V] Compatibility — OK
  [-] Security — не затронуто
  [V] Documenter — обновлено N docs
  [-] Senior Reviewer — не требовался
  [-] Refactor — не требовался
  [-] Deploy — не запрашивался
  [-] Docker Monitor — не запрашивался

Изменённые файлы:
  - path/to/file1.py (+N строк)
  - path/to/file2.py (+M строк)

Тесты (локальные): XX passed, 0 failed, YY skipped
CI (GitHub Actions): 5/5 jobs passed, XX e2e tests
Tech debt: [список INFO замечаний]
=== КОНЕЦ ОТЧЁТА ===
```

---

## MCP ИНСТРУМЕНТЫ

### SequentialThinking (`mcp__sequentialthinking__sequentialthinking`)
Инструмент для пошагового структурированного анализа. Агенты-аналитики ОБЯЗАНЫ использовать его:

| Агент | Как использовать |
|-------|-----------------|
| **Planner** | Каждый шаг декомпозиции = отдельный thought (определение слоёв → подзадачи → зависимости → параллелизм) |
| **Worker** | Планирование порядка делегирования и интеграции результатов |
| **QA Monitor** | Анализ crash-логов, построение тест-сценариев по изменённым файлам |
| **Debugger** | Анализ stacktrace: разбор ошибки → гипотеза → проверка → исправление. Ревизия при новых данных |
| **Reviewer** | Каждое из 12 правил = отдельный thought с результатом OK/BLOCK/WARN/INFO |
| **Security Auditor** | Каждая проверка CRITICAL→HIGH→MEDIUM→LOW = отдельный thought |
| **Senior Reviewer** | Каждая из 6 архитектурных проверок = thought. Итог — решение о рефакторинге |

### Context7 (`mcp__context7__resolve-library-id` + `mcp__context7__query-docs`)
Для получения актуальной документации библиотек. Используют: Worker, Debugger, Backend, Frontend, Refactor, Design Stylist.

---

## ГЛОБАЛЬНЫЕ ПРАВИЛА (для всех фаз)

Эти правила действуют для КАЖДОГО агента в конвейере:

1. **Язык** — всегда русский (комментарии, UI строки, общение)
2. **Нет emoji** в UI — только SVG через IconLoader
3. **resource_path()** для всех ресурсов
4. **1px border** для frameless диалогов (`border: 1px solid #E0E0E0`)
5. **Docker rebuild** (не restart) после серверных изменений
6. **Совместимость** ключей API/DB ответов
7. **Статические пути ПЕРЕД динамическими** в FastAPI
8. **Двухрежимность** (online API + offline SQLite)
9. **DataAccess** для CRUD в UI (не api_client/db напрямую)
10. **API-first с fallback** на локальную БД
11. **__init__.py** обязательны в database/, ui/, utils/
12. **Параметризованные SQL** (не f-strings)

## КОМАНДЫ ТЕСТИРОВАНИЯ

```bash
# DB тесты (без сервера)
.venv\Scripts\python.exe -m pytest tests/db/ -v

# E2E тесты (нужен сервер)
.venv\Scripts\python.exe -m pytest tests/e2e/ -v --timeout=60

# UI тесты (offscreen)
.venv\Scripts\python.exe -m pytest tests/ui/ -v --timeout=30

# Mock CRUD
.venv\Scripts\python.exe -m pytest tests/api_client/ -v

# Критические (обязательны)
.venv\Scripts\python.exe -m pytest tests/ -m critical -v --timeout=60

# Клиентские unit-тесты
.venv\Scripts\python.exe -m pytest tests/client/ -v

# ВАЖНО: UI логи НЕ читать через Read!
.venv/Scripts/python.exe tests/ui/parse_results.py <файл_логов>
```