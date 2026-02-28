# Субагенты

> 21 агент Claude Code с 6-фазной оркестрацией через `/orkester`. Research → Design → Plan → Implement (+Gate Checks) → PR → CI.

## Обзор системы

```
Пользователь → /orkester <задача>
     │
     ▼
 ФАЗА 1: Research (sonnet) → research.md [если full/refactor]
     │
     ▼
 ФАЗА 2: Design (opus) → design.md [если full/refactor]
     │
     ▼
 ФАЗА 3: Planner (opus) → план + roadmap.md
     │
     ▼
 ФАЗА 4: Worker (opus) → код + Gate Checks 5/5 на каждую подзадачу
     │                     делегирование: Backend, Frontend, API Client, Database, Design Stylist
     ▼
 QA Monitor (sonnet) → запуск CRM + мониторинг крашей [если UI]
     │
     ▼
 Test-Runner (haiku) ⟷ Debugger (sonnet) [макс 3 цикла]
     │
     ▼
 ФАЗА 5: PR Creator (haiku) → feature branch + PR via gh
     │
     ▼
 ФАЗА 6: CI Verify → GitHub Actions на PR [макс 3 CI-Fix цикла]
     │
     ▼
 Reviewer (sonnet) → BLOCK/WARN/INFO
     │
     ▼
 Compatibility Checker (haiku) → OK/MISMATCH
     │
     ▼
 Security Auditor (sonnet) [если server/]
     │
     ▼
 Documenter (haiku) → docs + отчёт
     │
     ▼
 Senior Reviewer (opus) [если 3+ файлов] → Refactor (sonnet)?
     │
     ▼
 Deploy (opus) [только вручную]
```

---

## Матрица моделей (21 агент)

| # | Агент | Модель | Роль | Обоснование |
|---|-------|--------|------|-------------|
| 1 | **Research** | sonnet | Исследование | Анализ контекста, 3 направления |
| 2 | **Design** | opus | Проектирование | C4, DFD, ADR, тест-стратегия, API контракты |
| 3 | **Planner** | opus | Планирование | Анализ 109K строк, разбиение задач, roadmap.md |
| 4 | **Worker** | opus | Исполнение | Координация до 5 агентов параллельно |
| 5 | **Test-Runner** | haiku | Тестирование | Запуск pytest, парсинг stdout |
| 6 | **Debugger** | sonnet | Отладка | Анализ stacktrace, поиск root cause |
| 7 | **Reviewer** | sonnet | Ревью | Проверка по 12 правилам проекта |
| 8 | **Documenter** | haiku | Документация | Обновление markdown файлов |
| 9 | **Refactor** | sonnet | Рефакторинг | Структурные улучшения кода |
| 10 | **Security Auditor** | sonnet | Безопасность | Аудит по OWASP чеклисту |
| 11 | **Senior Reviewer** | opus | Архитектура | Долгосрочные последствия, масштабируемость |
| 12 | **Backend** | sonnet | Бэкенд | CRUD endpoints по шаблону |
| 13 | **Frontend** | sonnet | Фронтенд | PyQt5 виджеты, QSS стили |
| 14 | **API Client** | sonnet | REST клиент | Методы + offline fallback |
| 15 | **Database** | haiku | БД | Миграции SQLite по шаблону |
| 16 | **Compatibility** | haiku | Совместимость | Сравнение ключей server↔client |
| 17 | **Deploy** | opus | Деплой | Ошибка деплоя = downtime production |
| 18 | **Design Stylist** | sonnet | Дизайн | QSS стили по палитре |
| 19 | **QA Monitor** | sonnet | Ручное QA | Запуск CRM, инструкции, мониторинг крашей |
| 20 | **Gate Checker** | haiku | Контроль качества | 5 проверок на каждую фазу Implement |
| 21 | **PR Creator** | haiku | PR workflow | Feature branch, PR via gh, CI verify |

**Итого:** opus ×5, sonnet ×10, haiku ×6

---

## Инструменты по агентам

### MCP серверы
- **SequentialThinking** — пошаговый структурированный анализ (`mcp__sequentialthinking`)
- **Context7** — актуальная документация библиотек (`mcp__context7`)

### Матрица инструментов

| Агент | Bash | Grep/Glob | Read | Edit/Write | Context7 | SeqThinking | WebSearch |
|-------|:----:|:---------:|:----:|:----------:|:--------:|:-----------:|:---------:|
| Research | — | + | + | + | — | **+** | + |
| Design | — | + | + | + | — | **+** | — |
| Planner | — | + | + | + | — | **+** | — |
| Worker | + | + | + | + | + | **+** | — |
| Test-Runner | + | + | + | — | — | — | — |
| Debugger | + | + | + | + | + | **+** | — |
| QA Monitor | + | + | + | — | — | **+** | — |
| Reviewer | — | + | + | — | — | **+** | — |
| Documenter | — | + | + | + | — | — | — |
| Refactor | + | + | + | + | + | — | — |
| Security Auditor | — | + | + | — | — | **+** | — |
| Senior Reviewer | — | + | + | — | — | **+** | — |
| Backend | + | + | + | + | + | — | — |
| Frontend | + | + | + | + | + | — | — |
| API Client | + | + | + | + | — | — | — |
| Database | + | + | + | + | — | — | — |
| Compatibility | — | + | + | — | — | — | — |
| Deploy | + | — | + | — | — | — | — |
| Design Stylist | + | + | + | + | + | — | + |
| Gate Checker | + | + | + | — | — | — | — |
| PR Creator | + | — | — | — | — | — | — |

### Когда использовать SequentialThinking

| Агент | Применение |
|-------|-----------|
| Research | Каждое из 3 направлений = отдельный thought (архитектура → паттерны → интеграции) |
| Design | Каждый раздел дизайна = отдельный thought (C4 → DFD → ADR → тесты → API контракты) |
| Planner | Декомпозиция задачи: каждый шаг = отдельный thought (слои → файлы → подзадачи → параллелизм) |
| Worker | Планирование делегирования и интеграции результатов от спец. агентов |
| Debugger | Анализ root cause: разбор ошибки → гипотеза → проверка → ревизия при новых данных |
| Reviewer | Систематическая проверка: каждое из 12 правил = thought с результатом OK/BLOCK/WARN/INFO |
| Security Auditor | Систематический аудит: CRITICAL → HIGH → MEDIUM → LOW, отсеивание false positives |
| Senior Reviewer | 6 архитектурных проверок, итоговое решение о рефакторинге с обоснованием |

---

## Агенты: подробное описание

### 1. Planner Agent ([.claude/agents/planner-agent.md](../.claude/agents/planner-agent.md))

**Модель:** opus | **Роль:** Планирование задач

**Вход:** Описание задачи от пользователя
**Выход:** Структурированный план (подзадачи, агенты, тесты, параллелизм)

**Инструменты:** Grep, Glob, Read (только анализ, НЕ редактирование)

**Workflow:**
1. Прочитать задачу → определить затронутые слои/файлы
2. Разбить на подзадачи с зависимостями
3. Назначить агентов каждой подзадаче
4. Определить тесты для проверки
5. Спланировать параллелизацию

---

### 2. Worker Agent ([.claude/agents/worker-agent.md](../.claude/agents/worker-agent.md))

**Модель:** opus | **Роль:** Центральный исполнитель

**Вход:** План от Planner
**Выход:** Изменённые файлы + контракты изменений

**Правила делегирования:**

| Затронутый путь | Спец. агент | Worker сам если |
|----------------|-------------|-----------------|
| `server/*.py` | Backend Agent | < 10 строк |
| `ui/*.py` | Frontend Agent | < 10 строк |
| `utils/api_client.py`, `utils/data_access.py` | API Client Agent | < 10 строк |
| `database/db_manager.py` | Database Agent | < 5 строк |
| QSS стили | Design Stylist | стиль уже есть в unified_styles.py |

**Параллелизация (кросс-слойная задача):**
```
Worker: "Добавить CRUD для сущности X"
    ├─ [параллельно] Backend → schemas.py + main.py
    ├─ [параллельно] API Client → api_client.py + data_access.py
    └─ [после них] Frontend → ui/x_tab.py
         └─ [после] Design Stylist → стили
```

---

### 3. Test-Runner Agent ([.claude/agents/test-runner-agent.md](../.claude/agents/test-runner-agent.md))

**Модель:** haiku | **Роль:** Запуск и написание тестов

**Маппинг файлов → тестов:**

| Изменённый файл | Тесты |
|-----------------|-------|
| `server/` | `tests/e2e/`, `tests/backend/` |
| `ui/` | `tests/ui/` |
| `database/` | `tests/db/` |
| `utils/api_client.py` | `tests/api_client/`, `tests/client/` |
| Всегда | `tests/ -m critical` |

**ВАЖНО:** UI логи НЕ читать через Read! Использовать `tests/ui/parse_results.py`.

---

### 4. Debugger Agent ([.claude/agents/debugger-agent.md](../.claude/agents/debugger-agent.md))

**Модель:** sonnet | **Роль:** Исправление падений тестов

**Вход:** Stacktrace упавших тестов
**Выход:** Минимальное исправление
**Макс итераций:** 3 (потом эскалация пользователю)

**Частые баги:**
- 422 ошибка → проверить порядок endpoints (статические перед динамическими)
- Ключи API/DB → сравнить ответы server/main.py и db_manager.py
- `resource_path()` → пути к ресурсам через обёртку
- Offline fallback → проверить двухрежимность
- Docker → rebuild, не restart

---

### 4.5. QA Monitor Agent ([.claude/agents/qa-monitor-agent.md](../.claude/agents/qa-monitor-agent.md))

**Модель:** sonnet | **Роль:** Интерактивный контроль качества

**Вход:** Список изменённых файлов от Worker
**Выход:** Результат ручного тестирования (OK / ошибки найдены)

**Workflow:**
1. Определить тест-сценарии по изменённым файлам (ui/ → что открыть/нажать)
2. Запустить CRM клиент с перехватом логов в файл
3. Выдать пользователю пошаговые инструкции по тестированию
4. Мониторить логи на traceback/error/crash
5. Если краш — передать traceback в Debugger для автоисправления
6. Цикл QA-Debug: макс 3 итерации (запуск → краш → fix → перезапуск)

**Активируется:** Если изменены `ui/` или `utils/data_access.py`. Обязателен в full/refactor (при UI), qa.

---

### 5. Reviewer Agent ([.claude/agents/reviewer-agent.md](../.claude/agents/reviewer-agent.md))

**Модель:** sonnet | **Роль:** Code review по 12 правилам

**Категории замечаний:**

| Тип | Действие | Примеры |
|-----|----------|---------|
| **BLOCK** | Обязательное исправление | Emoji в UI, нет resource_path(), SQL injection |
| **WARN** | Рекомендуемое | Нет snake_case, нет UTF-8 |
| **INFO** | Записать в tech_debt | Дублирование кода |

**Цикл:** Reviewer → Worker исправляет → Reviewer перепроверяет (макс 2 раза)

---

### 6. Documenter Agent ([.claude/agents/documenter-agent.md](../.claude/agents/documenter-agent.md))

**Модель:** haiku | **Роль:** Документация и tech debt

**Обязанности:**
- Обновить затронутые docs/ файлы (22 документа)
- Обновить docs/01-roadmap.md (отметить выполненное)
- Записать INFO замечания в tech_debt
- Сформировать итоговый отчёт

---

### 7. Refactor Agent ([.claude/agents/refactor-agent.md](../.claude/agents/refactor-agent.md))

**Модель:** sonnet | **Роль:** Рефакторинг кода

**Активируется:** По решению Senior Reviewer

**Правила:**
- НИКОГДА не менять публичные интерфейсы
- Сохранять поведение
- Обязательный повторный прогон тестов

---

### 8. Security Auditor Agent ([.claude/agents/security-auditor-agent.md](../.claude/agents/security-auditor-agent.md))

**Модель:** sonnet | **Роль:** Аудит безопасности

**Активируется:** Условно, если затронут `server/`

**Категории:**

| Уровень | Действие | Примеры |
|---------|----------|---------|
| **CRITICAL** | СТОП + эскалация | SQL injection, hardcoded пароли, .env в git |
| **HIGH** | Worker исправляет | JWT без expiration, CORS wildcard, IDOR |
| **MEDIUM** | Worker исправляет | Sensitive логи, нет rate limiting |
| **LOW** | Записать | Устаревшие зависимости |

---

### 9. Senior Reviewer Agent ([.claude/agents/senior-reviewer-agent.md](../.claude/agents/senior-reviewer-agent.md))

**Модель:** opus | **Роль:** Архитектурный обзор

**Активируется:** Условно, если изменено 3+ файлов

**6 проверок:**
1. Соответствие двухрежимной архитектуре
2. Масштабируемость
3. Дублирование кода
4. Целостность DataAccess layer
5. Производительность
6. Совместимость

**Выход:** Решение о рефакторинге (не нужен / рекомендуется / обязателен)

---

### 10. Backend Agent ([.claude/agents/backend-agent.md](../.claude/agents/backend-agent.md))

**Модель:** sonnet | **Роль:** FastAPI, SQLAlchemy, Pydantic

**Триггеры:** `server/main.py`, `server/schemas.py`, `server/database.py`, `server/permissions.py`

**Чеклист:** endpoints, schemas, Docker rebuild, тесты, статические пути перед динамическими

---

### 11. Frontend Agent ([.claude/agents/frontend-agent.md](../.claude/agents/frontend-agent.md))

**Модель:** sonnet | **Роль:** PyQt5 UI

**Триггеры:** `ui/*.py`, `resources/*`

**Правила:** Нет emoji, resource_path(), 1px border, DataAccess обязателен, lazy loading, UnifiedStyles

---

### 12. API Client Agent ([.claude/agents/api-client-agent.md](../.claude/agents/api-client-agent.md))

**Модель:** sonnet | **Роль:** REST клиент, offline, синхронизация

**Триггеры:** `utils/api_client.py`, `utils/data_access.py`, `utils/sync_manager.py`, `utils/db_sync.py`

**Критические правила:**
- Таймауты: READ=10s, WRITE=15s, offline кэш=5s
- DataAccess паттерн API-first
- Формат API = формат DB

---

### 13. Database Agent ([.claude/agents/database-agent.md](../.claude/agents/database-agent.md))

**Модель:** haiku | **Роль:** SQLite, миграции

**Триггер:** `database/db_manager.py`

**Правила:** Параметризованные запросы, идемпотентные миграции (PRAGMA table_info), ключи совпадают с API

---

### 14. Compatibility Checker ([.claude/agents/compatibility-checker.md](../.claude/agents/compatibility-checker.md))

**Модель:** haiku | **Роль:** Проверка совместимости server↔client

**6 проверок:**
1. Endpoint → Method маппинг
2. Ключи ответов совпадают
3. Сигнатуры методов совпадают
4. Pydantic ↔ SQLAlchemy совместимы
5. DB fallback формат идентичен API (11 пар методов)
6. DataAccess обёртки существуют

---

### 15. Deploy Agent ([.claude/agents/deploy-agent.md](../.claude/agents/deploy-agent.md))

**Модель:** opus | **Роль:** Автоматизированный деплой + Docker мониторинг

**Триггер:** Ручной (`deploy`, `деплой`, `обнови сервер`, `build exe`) или режим `docker`

**Docker CLI:** Установлен локально (`C:\Docker\docker.exe`), контекст `interior-studio-server` через SSH. Все docker-команды выполняются без `ssh timeweb` — прямой доступ к контейнерам сервера.

**Фазы деплоя:**
1. Pre-checks (синтаксис, совместимость, безопасность)
2. Backup (DB + код)
3. Deploy (git pull или scp + docker rebuild)
4. Верификация (ps + logs)
5. Smoke test

**Docker мониторинг (режим docker):**
1. Диагностика: `docker ps`, healthcheck, `docker stats`
2. Анализ логов: `docker logs` с фильтрацией ошибок
3. Реакция: перезапуск / пересборка / эскалация (curl)

---

### 16. Design Stylist Agent ([.claude/agents/design-stylist-agent.md](../.claude/agents/design-stylist-agent.md))

**Модель:** sonnet | **Роль:** Дизайн, стили, QSS

**Автотриггер:** Ключевые слова: дизайн, стиль, цвет, QSS, шрифт

**Палитра:**
```
Primary: #ffd93c | Hover: #ffc800 | Pressed: #e6b400
Background: #FFFFFF | Surface: #F8F9FA | Border: #E0E0E0
Text: #333333 | Success: #4CAF50 | Error: #F44336
```

---

## Циклы обратной связи

### Цикл A: Test → Debugger (макс 3 итерации)
```
Тесты упали → Debugger анализирует → исправляет →
Test-Runner перезапускает ТОЛЬКО упавшие →
  ├─ OK → продолжить конвейер
  └─ Падения → повторить (макс 3) → ЭСКАЛАЦИЯ пользователю
```

### Цикл B: Reviewer → Worker (макс 2 итерации)
```
BLOCK замечания → Worker исправляет → Reviewer перепроверяет →
  ├─ OK → продолжить
  └─ BLOCK → повторить (макс 2) → ЭСКАЛАЦИЯ
```

### Цикл C: Compatibility → Worker (макс 2 итерации)
```
MISMATCH → Worker исправляет → Checker перепроверяет →
  ├─ OK → продолжить
  └─ MISMATCH → повторить (макс 2) → ЭСКАЛАЦИЯ
```

### Цикл D: Security → Worker (макс 1 итерация)
```
CRITICAL → СТОП + ЭСКАЛАЦИЯ (никогда не автофикс)
HIGH/MEDIUM → Worker исправляет → Security перепроверяет →
  ├─ OK → продолжить
  └─ Проблемы → ЭСКАЛАЦИЯ
```

### Цикл E.5: QA Monitor → Debugger (макс 3 итерации)
```
Запуск CRM → Инструкции пользователю → Мониторинг логов →
  ├─ OK (нет ошибок) → продолжить конвейер (Test-Runner)
  └─ Краш/ошибка → Debugger исправляет → Перезапуск CRM
       ├─ OK → продолжить
       └─ Ошибка → повторить (макс 3) → ЭСКАЛАЦИЯ
```

### Цикл F: PR & CI Verify (макс 3 итерации)
```
PR Creator → feature branch + gh pr create → CI запускается на PR →
  ├─ CI PASSED → продолжить конвейер
  └─ CI FAILED → Debugger анализирует логи CI → исправляет → push в тот же branch
       ├─ OK → продолжить
       └─ FAIL → повторить (макс 3) → ЭСКАЛАЦИЯ

CI включает 5 jobs: syntax-check, lint, test-db, docker-build, test-e2e
НИКОГДА не merge PR автоматически — только ручное решение пользователя
```

### Цикл G: Gate Check → Субагент (макс 2 итерации)
```
Gate Checker (5 проверок: билд, тесты, линтер, дизайн, безопасность) →
  ├─ PASS → продолжить конвейер
  └─ FAIL → Субагент исправляет → Gate Check повторно
       ├─ PASS → продолжить
       └─ FAIL → повторить (макс 2) → ЭСКАЛАЦИЯ
```

---

## 8 режимов оркестрации

| Режим | Ключевые слова | Фазы |
|-------|---------------|------|
| **full** | добавить, реализовать, создать, новый | **Research**→**Design**→Planner→Worker **[+Gate]**→QA Monitor→Test **[+Gate]**→**PR**→**CI**→Review→Compat→Security?→Doc→SeniorReview? |
| **fix** | исправь, баг, не работает, ошибка | Planner(lite)→Debugger **[+Gate]**→Test→**PR**→**CI**→Review?→Compat? |
| **test** | тесты, проверь, запусти, покрытие | Test-Runner→Debugger?→**PR**→**CI**→Doc(отчёт) |
| **refactor** | рефакторинг, улучши, упрости | **Research**→**Design**→Planner→SeniorReview→Refactor **[+Gate]**→QA Monitor→Test→**PR**→**CI**→Review→Doc |
| **security** | безопасность, аудит, уязвимость | **Research(lite)**→SecurityAuditor→Planner→Worker **[+Gate]**→Test→**PR**→**CI**→Doc |
| **deploy** | деплой, deploy, обнови сервер | Compat→Test(critical)→Deploy→Test(smoke)→Doc |
| **docker** | docker, контейнер, логи сервера, healthcheck | Docker Monitor→Debugger?→Deploy?→Doc |
| **qa** | проверь руками, ручное тестирование | QA Monitor→Debugger?→Doc(отчёт) |

**Вызов:** `/orkester <описание задачи>` или `/orkester --mode=fix <описание бага>` или `/orkester --mode=qa`

---

## Использование

### Через оркестратор (рекомендуется)
```
/orkester Добавить CRUD для проектных шаблонов
/orkester --mode=fix Не работает загрузка клиентов в offline
/orkester --mode=test Проверить модуль платежей
/orkester --mode=qa Проверить вкладку Клиенты после изменений
/orkester --mode=deploy Обновить сервер
```

### Напрямую (для отдельных задач)
Агенты можно вызывать напрямую через Task tool, указывая `subagent_type` и промпт. Это полезно для изолированных задач, не требующих полного конвейера.

---

## Система отчётности

Все агенты **обязаны** возвращать отчёты в стандартном формате с emoji-иконками и таблицами. Правила описаны в `.claude/agents/shared-rules.md` → "Правила форматирования отчётов субагентов".

### Emoji-словарь (ключевые)

| Emoji | Значение | | Emoji | Значение |
|-------|----------|--|-------|----------|
| ✅ | Успех | | ❌ | Ошибка |
| ⚠️ | Предупреждение | | ℹ️ | Информация |
| 🚫 | Блокировка | | ⏭️ | Пропущено |
| 🔄 | В процессе | | | |

### Emoji агентов

| Emoji | Агент | | Emoji | Агент |
|-------|-------|--|-------|-------|
| 🔍 | Research | | 🎨 | Design |
| 📋 | Planner | | 🏗️ | Worker |
| 🛡️ | Gate Checker | | 🧪 | Test-Runner |
| 🐛 | Debugger | | 👁️ | Reviewer / Senior |
| 🔗 | Compatibility | | 🔐 | Security |
| 📝 | Documenter | | 📦 | PR Creator |
| 🖥️ | QA Monitor | | 🚀 | Deploy |
| 🐳 | Docker Monitor | | | |

### Стандартная структура отчёта

```
{EMOJI} ОТЧЁТ: {ИМЯ АГЕНТА}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Сводка (таблица метрик)
📁 Затронутые файлы (таблица)
{Специфичная секция агента} (таблица)

{EMOJI} Итог: {резюме одной строкой}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Финальный отчёт оркестратора

Содержит 7 секций-таблиц:
1. **📊 Общая сводка** — задача, режим, статус, метрики
2. **📡 Конвейер фаз** — все 17 фаз с emoji-статусами
3. **🏗️ Подзадачи** — детали реализации + Gate Checks
4. **📁 Файлы** — все изменённые файлы с +/- строк
5. **🧪 Тесты** — локальные + CI результаты
6. **👁️ Качество** — Reviewer, Compatibility, Security, Senior
7. **📋 Tech debt** — INFO замечания для будущей работы

> **Важно:** emoji разрешены ТОЛЬКО в отчётах (текстовый вывод). В UI-коде (PyQt5 виджеты) emoji **ЗАПРЕЩЕНЫ** — только SVG через IconLoader.
