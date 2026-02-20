# Субагенты

> 16 агентов Claude Code с оркестрацией через `/orkester`. Модели, инструменты, цепочка вызовов, циклы обратной связи.

## Обзор системы

```
Пользователь → /orkester <задача>
     │
     ▼
 Planner (opus) → план + подзадачи
     │
     ▼
 Worker (opus) → код + делегирование спец. агентам
     │
     ▼
 Test-Runner (haiku) ⟷ Debugger (sonnet) [макс 3 цикла]
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

## Матрица моделей (16 агентов)

| # | Агент | Модель | Роль | Обоснование |
|---|-------|--------|------|-------------|
| 1 | **Planner** | opus | Планирование | Анализ 109K строк, разбиение задач |
| 2 | **Worker** | opus | Исполнение | Координация до 5 агентов параллельно |
| 3 | **Test-Runner** | haiku | Тестирование | Запуск pytest, парсинг stdout |
| 4 | **Debugger** | sonnet | Отладка | Анализ stacktrace, поиск root cause |
| 5 | **Reviewer** | sonnet | Ревью | Проверка по 12 правилам проекта |
| 6 | **Documenter** | haiku | Документация | Обновление markdown файлов |
| 7 | **Refactor** | sonnet | Рефакторинг | Структурные улучшения кода |
| 8 | **Security Auditor** | sonnet | Безопасность | Аудит по OWASP чеклисту |
| 9 | **Senior Reviewer** | opus | Архитектура | Долгосрочные последствия, масштабируемость |
| 10 | **Backend** | sonnet | Бэкенд | CRUD endpoints по шаблону |
| 11 | **Frontend** | sonnet | Фронтенд | PyQt5 виджеты, QSS стили |
| 12 | **API Client** | sonnet | REST клиент | Методы + offline fallback |
| 13 | **Database** | haiku | БД | Миграции SQLite по шаблону |
| 14 | **Compatibility** | haiku | Совместимость | Сравнение ключей server↔client |
| 15 | **Deploy** | opus | Деплой | Ошибка деплоя = downtime production |
| 16 | **Design Stylist** | sonnet | Дизайн | QSS стили по палитре |

**Итого:** opus ×4, sonnet ×8, haiku ×4

---

## Инструменты по агентам

### MCP серверы
- **SequentialThinking** — пошаговый структурированный анализ (`mcp__sequentialthinking`)
- **Context7** — актуальная документация библиотек (`mcp__context7`)

### Матрица инструментов

| Агент | Bash | Grep/Glob | Read | Edit/Write | Context7 | SeqThinking | WebSearch |
|-------|:----:|:---------:|:----:|:----------:|:--------:|:-----------:|:---------:|
| Planner | — | + | + | — | — | **+** | — |
| Worker | + | + | + | + | + | **+** | — |
| Test-Runner | + | + | + | — | — | — | — |
| Debugger | + | + | + | + | + | **+** | — |
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

### Когда использовать SequentialThinking

| Агент | Применение |
|-------|-----------|
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

**Модель:** opus | **Роль:** Автоматизированный деплой

**Триггер:** Только ручной (`deploy`, `деплой`, `обнови сервер`, `build exe`)

**Фазы:**
1. Pre-checks (синтаксис, совместимость, безопасность)
2. Backup (DB + код)
3. Deploy (git pull или scp + docker rebuild)
4. Верификация (ps + logs)
5. Smoke test (curl)

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

---

## 6 режимов оркестрации

| Режим | Ключевые слова | Фазы |
|-------|---------------|------|
| **full** | добавить, реализовать, создать, новый | Planner→Worker→Test→Review→Compat→Security?→Doc→SeniorReview? |
| **fix** | исправь, баг, не работает, ошибка | Planner(lite)→Debugger→Test→Review?→Compat? |
| **test** | тесты, проверь, запусти, покрытие | Test-Runner→Debugger?→Doc(отчёт) |
| **refactor** | рефакторинг, улучши, упрости | Planner→SeniorReview→Refactor→Test→Review→Doc |
| **security** | безопасность, аудит, уязвимость | SecurityAuditor→Planner→Worker→Test→Doc |
| **deploy** | деплой, deploy, обнови сервер | Compat→Test(critical)→Deploy→Test(smoke)→Doc |

**Вызов:** `/orkester <описание задачи>` или `/orkester --mode=fix <описание бага>`

---

## Использование

### Через оркестратор (рекомендуется)
```
/orkester Добавить CRUD для проектных шаблонов
/orkester --mode=fix Не работает загрузка клиентов в offline
/orkester --mode=test Проверить модуль платежей
/orkester --mode=deploy Обновить сервер
```

### Напрямую (для отдельных задач)
Агенты можно вызывать напрямую через Task tool, указывая `subagent_type` и промпт. Это полезно для изолированных задач, не требующих полного конвейера.
