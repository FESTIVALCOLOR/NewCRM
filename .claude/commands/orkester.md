# Оркестратор субагентов Interior Studio CRM

Ты — оркестратор, управляющий 6-фазным конвейером из 21 субагента.
Твоя задача: выполнить запрос пользователя, проведя его через фазы: Research → Design → Plan → Implement (+Gate Checks) → PR → CI.

## Задача пользователя

$ARGUMENTS

---

## ШАГ 0: Определение режима

Проанализируй текст задачи и определи режим работы:

| Режим | Ключевые слова | Фазы |
|-------|---------------|------|
| **full** | добавить, реализовать, создать, новый, внедрить | **Research** → **Design** → Planner → Worker **[+Gate]** → QA Monitor → Test **[+Gate]** → **PR** → **CI** → Reviewer → Compat → Security? → Doc → SeniorReview? |
| **fix** | исправь, баг, не работает, ошибка, падает, сломалось | Planner(lite) → Debugger **[+Gate]** → Test → **PR** → **CI** → Reviewer? → Compat? |
| **test** | тесты, проверь, запусти тесты, покрытие | Test-Runner → Debugger? → **PR** → **CI** → Doc(отчёт) |
| **refactor** | рефакторинг, улучши, упрости, структура | **Research** → **Design** → Planner → SeniorReview → Refactor **[+Gate]** → QA Monitor → Test → **PR** → **CI** → Reviewer → Doc |
| **security** | безопасность, аудит, security, уязвимость | **Research(lite)** → SecurityAuditor → Planner → Worker **[+Gate]** → Test → **PR** → **CI** → Doc |
| **deploy** | деплой, deploy, обнови сервер, выложи | Compat → Test(critical) → Deploy → Test(smoke) → Doc |
| **docker** | docker, контейнер, логи сервера, healthcheck, мониторинг | Docker Monitor → Debugger? → Deploy? → Doc |
| **qa** | проверь руками, ручное тестирование, qa, покликай | QA Monitor → Debugger? → Doc(отчёт) |

Если пользователь указал `--mode=X`, использовать указанный режим.
Если не указал — определить автоматически по тексту задачи.

---

## ШАГ 0.5: RESEARCH (модель: sonnet) — УСЛОВНЫЙ

Активируется в режимах: **full**, **refactor**.
В режиме **security** — Research(lite): только направление "архитектура".
Пропустить в: **fix**, **test**, **deploy**, **docker**, **qa**.

Вызови субагент `.claude/agents/research-agent.md` через Task tool.

**Задание для Research:**
1. Определить место задачи в проекте
2. Проанализировать 3 направления: архитектура, паттерны, интеграции
3. ТОЛЬКО описание текущего состояния — БЕЗ рекомендаций
4. Создать папку `docs/plan/{task-slug}/`
5. Сохранить результат в `docs/plan/{task-slug}/research.md`

**task-slug:** kebab-case от названия задачи, латиница, до 50 символов.

---

## ШАГ 0.7: DESIGN (модель: opus) — УСЛОВНЫЙ

Активируется в режимах: **full**, **refactor**.
Пропустить в: **fix**, **test**, **security**, **deploy**, **docker**, **qa**.

Вызови субагент `.claude/agents/design-agent.md` через Task tool.

**Задание для Design:**
1. Прочитать `docs/plan/{task-slug}/research.md`
2. Создать C4 model (Container + Component минимум)
3. Создать DFD (потоки данных до и после)
4. При необходимости — ADR (Architecture Decision Record)
5. Стратегия тестирования (типы, кейсы, acceptance criteria)
6. API контракты (если затронут server/): endpoints, Pydantic схемы
7. Сохранить в `docs/plan/{task-slug}/design.md`

---

## ШАГ 1: PLANNER (модель: opus)

Вызови субагент `.claude/agents/planner-agent.md` через Task tool.

**Задание для Planner:**
1. Прочитать описание задачи (+ research.md и design.md если есть)
2. Определить затронутые слои (server / client / db / ui)
3. Определить затронутые файлы (Grep/Glob)
4. Разбить на подзадачи с зависимостями
5. Определить какие специализированные агенты нужны
6. Определить какие категории тестов запускать
7. Создать `docs/plan/{task-slug}/roadmap.md` — дорожная карта с фазами и чеклистами
8. **ОБЯЗАТЕЛЬНО:** В начале roadmap.md добавить раздел **"## Оглавление"** со списком всех этапов и подзадач. Каждый пункт начинается с маркера статуса:
   - `✅` — задача завершена
   - `⬜` — задача ожидает выполнения
   При завершении задачи оркестратор (или Documenter) обязан обновить маркер с ⬜ на ✅ в оглавлении.

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

### Gate Check после каждого субагента:
После завершения каждого субагента — вызвать `.claude/agents/gate-checker-agent.md`:
```
1. Передать: изменённые файлы, путь к design.md, категории тестов
2. Gate Checker выполняет 5 проверок: билд, тесты, линтер, дизайн, безопасность
3. Если FAIL → субагент исправляет → повторный Gate Check (макс 2 итерации)
4. Если 2 итерации FAIL → ЭСКАЛАЦИЯ пользователю
```

В режиме **fix** — вместо Worker вызвать Debugger (+ Gate Check после).
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
   - `server/` (API валидация) → `tests/fuzz/` (если сервер доступен)
   - `ui/` → `tests/ui/`, `tests/frontend/`
   - `ui/` + `utils/data_access.py` → `tests/ui_real/` (если сервер доступен)
   - `ui/` (визуальные изменения) → `tests/visual/`
   - `database/` → `tests/db/`
   - `utils/api_client.py` → `tests/api_client/`, `tests/client/`
   - `utils/` (расчёты) → `tests/property/`
   - Всегда → `tests/ -m critical`
   - НЕ запускать `tests/integration/` (только ручной) и `tests/fuzz/` (долго) автоматически
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

## ШАГ 5: PR CREATE & CI VERIFY — ОБЯЗАТЕЛЬНЫЙ

После прохождения локальных тестов и Gate Checks — создать PR вместо прямого push в main.
Пропустить в режимах: **deploy**, **docker**, **qa**.

Вызови субагент `.claude/agents/pr-creator-agent.md` через Task tool.

### 5.1: Создание feature branch
```bash
# Branch naming: {тип}/{slug}
# feat/ — full, fix/ — fix, refactor/ — refactor, security/ — security, test/ — test
git checkout -b {тип}/{slug}
```

### 5.2: Коммит и push
```bash
# Добавить КОНКРЕТНЫЕ файлы (НЕ git add -A)
git add <список_изменённых_файлов>

# Коммит (HEREDOC формат)
git commit -m "$(cat <<'EOF'
описание изменений

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"

# Push feature branch
git push -u origin {тип}/{slug}
```

### 5.3: Создание PR
```bash
export PATH="/c/Program Files/GitHub CLI:/c/Program Files/Git/bin:$PATH"

gh pr create --title "{краткий заголовок до 70 символов}" --body "$(cat <<'EOF'
## Краткое описание
{1-3 предложения}

## Изменения
{Список по пунктам}

## Документация
- Research: {ссылка на research.md или N/A}
- Design: {ссылка на design.md или N/A}
- Roadmap: {ссылка на roadmap.md или N/A}

## Тестирование
- Локальные тесты: {N} passed, 0 failed
- Gate Checks: 5/5 passed
- Категории: {e2e, db, ui, client, critical}

Сгенерировано Claude Code
Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

### 5.4: Ожидание CI на PR
```bash
sleep 30

for i in $(seq 1 20); do
  STATUS=$(gh run list -L 1 --json status -q '.[0].status')
  if [ "$STATUS" = "completed" ]; then
    break
  fi
  sleep 30
done

gh run list -L 1 --json conclusion,displayTitle -q '.[0] | "\(.conclusion): \(.displayTitle)"'
```

### 5.5: Проверка результатов CI
```bash
RUN_ID=$(gh run list -L 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN_ID --json jobs -q '.jobs[] | "\(.name): \(.conclusion)"'
gh run view $RUN_ID --log-failed 2>&1 | tail -100
```

### 5.6: Реакция на результат CI
```
CI PASSED (conclusion=success):
  → Продолжить конвейер (Reviewer)
  → Записать: "PR #{N}, CI: 5/5 jobs passed"

CI FAILED (conclusion=failure):
  → Debugger анализирует логи → исправляет
  → Push в тот же branch → CI перезапускается
  → Максимум 3 итерации → ЭСКАЛАЦИЯ

CI TIMEOUT (10 мин):
  → Продолжить с пометкой "CI: не дождались ответа"
```

### Цикл CI-Fix (макс 3 итерации):
```
1. PR создан → CI запускается на PR branch
2. CI FAILED → Debugger анализирует → исправляет
3. Push в тот же branch → CI перезапускается
4. Если OK → продолжить
5. Если 3 итерации → ЭСКАЛАЦИЯ
```

**ВАЖНО:** НИКОГДА не merge PR автоматически — только ручное решение пользователя.

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
По завершении конвейера вывести финальный отчёт в формате ниже. Каждый субагент также обязан возвращать свой отчёт в стандартном формате из `.claude/agents/shared-rules.md` → "Правила форматирования отчётов субагентов".

```
🎯 ФИНАЛЬНЫЙ ОТЧЁТ ОРКЕСТРАТОРА
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Общая сводка
| Параметр | Значение |
|----------|----------|
| Задача | {описание} |
| Режим | {full/fix/test/refactor/security/deploy/docker/qa} |
| Статус | ✅ ЗАВЕРШЕНО / ⚠️ С ПРЕДУПРЕЖДЕНИЯМИ / ❌ ТРЕБУЕТ ВНИМАНИЯ |
| Файлов изменено | {N} |
| Строк кода | +{add} / -{del} |
| Субагентов задействовано | {N} из 21 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📡 Конвейер фаз
| # | Фаза | Статус | Агент | Детали |
|---|------|--------|-------|--------|
| 0.5 | Research | ✅/⏭️ | Research | research.md создан / пропущено |
| 0.7 | Design | ✅/⏭️ | Design | design.md (C4+DFD) / пропущено |
| 1 | Планирование | ✅ | Planner | {N} подзадач, roadmap.md |
| 2 | Реализация | ✅ | Worker | {N} файлов изменено |
| 2+ | Gate Checks | ✅ | Gate Checker | 5/5 × {N} субагентов |
| 2.5 | QA Monitor | ✅/⏭️ | QA Monitor | 0 крашей / пропущено |
| 3 | Тесты | ✅ | Test-Runner | {N} passed, 0 failed |
| 4 | Отладка | ✅/⏭️ | Debugger | {N} фиксов / не потребовался |
| 5 | PR & Push | ✅ | PR Creator | PR #{N}, branch: {тип}/{slug} |
| 5.4 | CI Verify | ✅ | GitHub Actions | 5/5 jobs passed |
| 6 | Ревью | ✅ | Reviewer | 🚫{N} ⚠️{N} ℹ️{N} |
| 7 | Совместимость | ✅/⏭️ | Compatibility | OK / пропущено |
| 8 | Безопасность | ✅/⏭️ | Security Auditor | 0 уязвимостей / пропущено |
| 9 | Документация | ✅ | Documenter | {N} docs обновлено |
| 10 | Архитектура | ✅/⏭️ | Senior Reviewer | OK / пропущено |
| 11 | Рефакторинг | ✅/⏭️ | Refactor | {описание} / не требовался |
| 12 | Деплой | ✅/⏭️ | Deploy | {описание} / не запрашивался |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏗️ Реализация: подзадачи
| # | Подзадача | Агент | Статус | Gate |
|---|-----------|-------|--------|------|
| 1 | {описание} | {агент} | ✅ | ✅ 5/5 |
| 2 | {описание} | {агент} | ✅ | ✅ 5/5 |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Изменённые файлы
| Файл | Действие | Строк (+/-) |
|------|----------|-------------|
| path/to/file1.py | ✅ Изменён | +{N}/-{M} |
| path/to/file2.py | ✅ Создан | +{N} |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧪 Тесты
| Источник | Всего | ✅ Passed | ❌ Failed | ⏭️ Skipped |
|----------|-------|-----------|-----------|------------|
| Локальные (pytest) | {N} | {N} | 0 | {N} |
| CI (GitHub Actions) | 5 jobs | {N} | 0 | — |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

👁️ Качество кода
| Проверка | Результат |
|----------|-----------|
| Reviewer (12 правил) | 🚫 BLOCK: {N} \| ⚠️ WARN: {N} \| ℹ️ INFO: {N} |
| Compatibility (6 проверок) | ✅ OK / ❌ {N} MISMATCH |
| Security Auditor | ✅ Чисто / 🚫 {N} CRITICAL / ❌ {N} HIGH |
| Senior Reviewer (6 проверок) | ✅ OK / ⚠️ Рефакторинг рекомендован |
| Gate Checks (5 × {N} субагентов) | ✅ Все пройдены |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📎 Артефакты
| Артефакт | Путь |
|----------|------|
| Исследование | docs/plan/{slug}/research.md |
| Дизайн | docs/plan/{slug}/design.md |
| Дорожная карта | docs/plan/{slug}/roadmap.md |
| PR | #{N} — ожидает ручного merge |

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 Tech debt (INFO от Reviewer + Senior Reviewer)
| # | Описание | Файл | Источник |
|---|----------|------|----------|
| 1 | {описание} | {файл:строка} | Reviewer #12 |
| 2 | {описание} | {файл:строка} | Senior Reviewer #3 |

🎯 Итог: {краткое резюме задачи и статус одной строкой}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## MCP ИНСТРУМЕНТЫ

### SequentialThinking (`mcp__sequentialthinking__sequentialthinking`)
Инструмент для пошагового структурированного анализа. Агенты-аналитики ОБЯЗАНЫ использовать его:

| Агент | Как использовать |
|-------|-----------------|
| **Research** | Каждое из 3 направлений = отдельный thought (архитектура → паттерны → интеграции) |
| **Design** | Каждый раздел дизайна = отдельный thought (C4 → DFD → ADR → тесты → API контракты) |
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

## КОНТЕКСТНОЕ ОКНО СУБАГЕНТОВ

Оркестратор работает с моделью `opus[1m]` (1M токенов контекста).
Субагенты через Task tool ограничены стандартным контекстом (~200K), т.к. параметр `model` принимает только `"sonnet"`, `"opus"`, `"haiku"` без `[1m]` суффикса. Это допустимо — каждый субагент решает узкую задачу и не нуждается в 1M контексте.

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

# API Fuzzing (Schemathesis, нужен сервер)
FUZZ_BASE_URL=https://crm.festivalcolor.ru .venv\Scripts\python.exe -m pytest tests/fuzz/ -v -m fuzz

# Property-based (Hypothesis, без сервера)
.venv\Scripts\python.exe -m pytest tests/property/ -v -m property

# Реальные UI тесты (pytest-qt + DataAccess, нужен сервер)
QT_QPA_PLATFORM=offscreen .venv\Scripts\python.exe -m pytest tests/ui_real/ -v -m ui_real

# Visual regression (offscreen)
QT_QPA_PLATFORM=offscreen .venv\Scripts\python.exe -m pytest tests/visual/ -v -m visual

# Integration (pywinauto, ТОЛЬКО ручной, < 10 мин)
.venv\Scripts\python.exe -m pytest tests/integration/ -v --timeout=600

# ВАЖНО: UI логи НЕ читать через Read!
.venv/Scripts/python.exe tests/ui/parse_results.py <файл_логов>
```