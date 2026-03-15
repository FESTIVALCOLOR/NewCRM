# Общие правила проекта — Interior Studio CRM

> Этот файл содержит общие правила для ВСЕХ агентов. НЕ дублировать в промптах агентов.

## 12 критических правил

1. **`__init__.py` обязательны** в database/, ui/, utils/
2. **Запрет emoji в UI** — только SVG через IconLoader
3. **`resource_path()`** для всех ресурсов (иконки, шрифты, логотипы)
4. **Рамки диалогов = 1px** (`border: 1px solid #E0E0E0; border-radius: 10px;`)
5. **Docker rebuild** после серверных изменений (не restart!). Команда: `ssh timeweb "cd /opt/interior_studio && git pull origin <branch> && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"`. Выполнять СРАЗУ после push с серверными изменениями. Проверить health check.
6. **Совместимость API/DB** ключей ответов (total_orders, position, source)
7. **Статические пути ПЕРЕД динамическими** в FastAPI
8. **Двухрежимная архитектура** (online API + offline SQLite)
9. **DataAccess** для всех CRUD в UI (не api_client/db напрямую)
10. **API-first с fallback** на локальную БД при записи
11. **PyQt Signal Safety** — emit из threading.Thread только через `QTimer.singleShot(0, ...)`
12. **Offline-очередь** — только сетевые ошибки, НЕ бизнес-ошибки (409/400)
13. **Параметризованные SQL** (не f-strings, не format)
14. **Именование:** snake_case переменные, PascalCase классы, UPPER_CASE константы

## Обязательная верификация после исправлений

1. **CI green** — все 5 jobs (lint, syntax-check, test-db, docker-build, test-e2e)
2. **Docker rebuild** — если изменены файлы в `server/`, СРАЗУ после push пересобрать Docker
3. **API проверка** — проверить исправленные endpoint-ы через curl с JWT: `ssh timeweb 'docker exec crm_api python3 -c "from auth import create_access_token; print(create_access_token({\"sub\": \"1\"}))"'`
4. **НЕ отмечать баг исправленным** без доказательства (curl ответ, лог, скриншот)

## Защита от регрессий — ОБЯЗАТЕЛЬНО при изменении UI файлов

> Повторяющиеся баги возникают когда при рефакторинге/исправлении одного бага
> агент непреднамеренно удаляет или перезаписывает уже работающие фичи.
> Нижеописанные правила ОБЯЗАТЕЛЬНЫ для всех агентов.

### Правило 1: ЧИТАЙ ПЕРЕД ПРАВКОЙ
Перед изменением любого UI файла (ui/*.py) — **прочитай весь файл** через Grep/Read.
Если файл >500 строк — прочитай минимум:
- Все `def __init__` (инициализация виджетов)
- Все `def eventFilter` (обработка событий)
- Все `_setup_*` методы (настройка виджетов)
- Все `getOpenFileName` (фильтры файлов)

### Правило 2: ТОЧЕЧНЫЕ ПРАВКИ вместо перезаписи
**ЗАПРЕЩЕНО** переписывать большие блоки кода целиком (>20 строк).
Используй Edit tool с точечными заменами. Если нужна крупная правка —
разбей на несколько мелких Edit операций.

### Правило 3: ПРОВЕРЬ ЧТО НЕ СЛОМАЛ
После каждого изменения UI файла — запусти:
```bash
pytest tests/anti_pattern/test_ui_regression_guards.py tests/ui/test_widget_config_regression.py -v --timeout=30
```
Эти тесты ловят потерю:
- searchable combo (editable, completer, eventFilter, _searchable)
- PNG в фильтрах файлов
- substring match в адресных фильтрах
- хардкод значений в фильтрах
- CRM карточка при создании договора
- truncate_filename max_length

### Правило 4: ЗАПРЕЩЁННЫЕ ПАТТЕРНЫ в UI
- `addItem('Фестиваль')` / `addItem('Петрович')` — хардкод типов агентов
- `payment.get('address') != f_address` — exact match вместо substring
- `getOpenFileName(... "*.pdf *.jpg" ...)` без `*.png` — потеря PNG
- `truncate_filename(..., max_length=30)` — слишком длинный max_length (макс 25)
- Удаление `def eventFilter` — потеря clear-on-click
- Удаление `_setup_searchable_combo` — потеря поиска в комбобоксах

## Архитектура проекта

```
UI (PyQt5)              DataAccess           API Client           Server (FastAPI)
ui/*.py            →  utils/data_access.py → utils/api_client.py → server/main.py
                                  ↓ fallback                        server/database.py
                          database/db_manager.py                    server/schemas.py
```

**Ключевые компоненты:**

| Компонент | Файл | Строк |
|-----------|------|-------|
| CRM Kanban | ui/crm_tab.py | 3 368 |
| FastAPI сервер | server/main.py | 424 (22 роутера, 214 endpoints) |
| SQLite менеджер | database/db_manager.py | 5 203 |
| REST клиент | utils/api_client.py | 2 300+ |
| Доступ к данным | utils/data_access.py | 2 038 |
| Offline менеджер | utils/offline_manager.py | 450+ |

## Экономия токенов при работе с файлами

- **docs/** файлы: ВСЕГДА сначала Grep по нужной теме, затем Read с offset/limit
- Файлы **>500 строк**: Grep + Read с offset/limit, НЕ Read целиком
- **UI тест логи**: ТОЛЬКО через парсер: `.venv/Scripts/python.exe tests/ui/parse_results.py <файл>`
- **НИКОГДА** не Read целиком: crm_card_edit_dialog.py (8542), db_manager.py (5739), crm_tab.py (3368), api_client.py (2300+), data_access.py (2038)

## Команды тестирования

```bash
.venv\Scripts\python.exe -m pytest tests/db/ -v               # DB (без сервера)
.venv\Scripts\python.exe -m pytest tests/e2e/ -v --timeout=60  # E2E (нужен сервер)
.venv\Scripts\python.exe -m pytest tests/ui/ -v --timeout=30   # UI (offscreen)
.venv\Scripts\python.exe -m pytest tests/api_client/ -v        # Mock CRUD
.venv\Scripts\python.exe -m pytest tests/client/ -v            # Unit-тесты
.venv\Scripts\python.exe -m pytest tests/ -m critical -v       # Критические (обязательны)
```

## CI / GitHub Actions

5 jobs: syntax-check, lint, test-db, docker-build, test-e2e (360+ тестов).
`gh` CLI авторизован через keyring (`gh auth login`).

```bash
export PATH="/c/Program Files/GitHub CLI:/c/Program Files/Git/bin:$PATH"

gh run list -L 1                                                                    # Последний CI
RUN_ID=$(gh run list -L 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN_ID --json jobs -q '.jobs[] | "\(.name): \(.conclusion)"'           # Jobs
gh run view $RUN_ID --log-failed 2>&1 | tail -100                                  # Логи ошибок
```

### PR Workflow (вместо прямого push в main)
1. `git checkout -b {тип}/{slug}` — создать feature branch
2. `git add <файлы>` → `git commit` (HEREDOC формат)
3. `git push -u origin {branch}` — push feature branch
4. `gh pr create --title "..." --body "..."` — создать PR
5. Polling `gh run list` для PR branch (макс 10 мин)
6. CI passed → PR готов к merge
7. CI failed → Debugger → push в тот же branch → ожидание (макс 3 итерации)
8. **НИКОГДА** не merge PR автоматически — только ручное

### Branch naming
- `feat/{slug}` — новая функциональность (режим full)
- `fix/{slug}` — исправление (режим fix)
- `refactor/{slug}` — рефакторинг
- `security/{slug}` — безопасность
- `test/{slug}` — тесты
- Slug: kebab-case, латиница, до 50 символов

### Gate Checks (5 обязательных проверок)
После каждого субагента в фазе Implement:
1. **Билд:** `py_compile` изменённых файлов
2. **Тесты:** `pytest` соответствующих категорий + critical
3. **Линтер:** `flake8` с CI-идентичными настройками
4. **Дизайн:** сверка с `docs/plan/{task-slug}/design.md`
5. **Безопасность:** grep на f-string SQL, hardcoded credentials, sensitive logs

Подробности: `.claude/agents/gate-checker-agent.md`

## Сервер

- **Домен:** crm.festivalcolor.ru | **SSH:** `ssh timeweb`
- **Путь:** /opt/interior_studio/
- **Docker rebuild:** `ssh timeweb "cd /opt/interior_studio && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"`

## Шаблоны кода

### DataAccess паттерн (API-first)
```python
def get_all_entities(self):
    if self.api_client:
        try:
            return self.api_client.get_entities()
        except Exception as e:
            print(f"[WARN] API error: {e}")
            return self.db.get_entities()
    return self.db.get_entities()
```

### Frameless диалог
```python
border_frame.setStyleSheet("QFrame#borderFrame { border: 1px solid #E0E0E0; border-radius: 10px; background: white; }")
```

## Правила форматирования отчётов субагентов

> **ОБЯЗАТЕЛЬНО** для каждого субагента: возвращать отчёт в стандартном формате с emoji-иконками и таблицами.
> Примечание: emoji разрешены ТОЛЬКО в отчётах агентов (текстовый вывод), **ЗАПРЕЩЕНЫ в UI-коде** (PyQt5 виджеты).

### Emoji-словарь для статусов

| Emoji | Значение | Когда использовать |
|-------|----------|--------------------|
| ✅ | Успех, пройдено | Тест/проверка пройдена, задача выполнена |
| ❌ | Ошибка, не пройдено | Тест упал, проверка провалена |
| ⚠️ | Предупреждение | WARN замечания, требует внимания |
| ℹ️ | Информация | INFO замечания, tech debt |
| 🔄 | В процессе | Итерация цикла, повторная попытка |
| ⏭️ | Пропущено | Фаза не требуется для данного режима |
| 🚫 | Блокировка | BLOCK замечание, CRITICAL security |
| 🔍 | Исследование | Research, анализ |
| 🏗️ | Реализация | Worker, построение |
| 🧪 | Тестирование | Test-Runner, тесты |
| 🐛 | Отладка | Debugger, фикс бага |
| 📋 | Планирование | Planner, план |
| 🎨 | Дизайн | Design, стилизация |
| 🔐 | Безопасность | Security Auditor |
| 📝 | Документация | Documenter |
| 🚀 | Деплой | Deploy Agent |
| 📦 | PR/CI | PR Creator, GitHub Actions |
| 👁️ | Ревью | Reviewer, Senior Reviewer |
| 🔗 | Совместимость | Compatibility Checker |
| 🖥️ | QA | QA Monitor, ручное тестирование |
| 🐳 | Docker | Docker Monitor |
| 🛡️ | Gate Check | Gate Checker |

### Стандартный формат отчёта субагента

Каждый субагент **ОБЯЗАН** вернуть отчёт в следующей структуре:

```
{EMOJI} ОТЧЁТ: {ИМЯ АГЕНТА}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 Сводка
| Метрика | Значение |
|---------|----------|
| Статус  | ✅ Успех / ❌ Ошибка / ⚠️ С предупреждениями |
| Время   | ~{N} сек |
| Файлов затронуто | {N} |
| {спец. метрика} | {значение} |

📁 Затронутые файлы
| Файл | Действие | Строк |
|------|----------|-------|
| path/to/file.py | ✅ Изменён (+{N}/-{M}) | {total} |
| path/to/file2.py | ✅ Создан | {total} |

{СЕКЦИЯ СПЕЦИФИЧНАЯ ДЛЯ АГЕНТА — формат описан ниже}

{EMOJI} Итог: {краткое резюме одной строкой}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Специфичные секции по типам агентов

#### Research Agent (🔍)
```
🔍 Направления исследования
| # | Направление | Статус | Ключевые находки |
|---|-------------|--------|------------------|
| 1 | Архитектура | ✅ | {кратко} |
| 2 | Паттерны | ✅ | {кратко} |
| 3 | Интеграции | ✅ | {кратко} |

📎 Артефакт: docs/plan/{slug}/research.md
```

#### Design Agent (🎨)
```
🎨 Разделы дизайна
| # | Раздел | Статус | Детали |
|---|--------|--------|--------|
| 1 | C4 Model | ✅ | Container + Component |
| 2 | DFD | ✅ | {N} потоков данных |
| 3 | ADR | ✅/⏭️ | {описание или "не требуется"} |
| 4 | Тест-стратегия | ✅ | {N} тест-кейсов |
| 5 | API контракты | ✅/⏭️ | {N} endpoints |

📎 Артефакт: docs/plan/{slug}/design.md
```

#### Planner Agent (📋)
```
📋 План реализации
| # | Подзадача | Агент | Файлы | Зависит от | Параллельно |
|---|-----------|-------|-------|------------|-------------|
| 1 | {описание} | Backend | {файлы} | — | с #2 |
| 2 | {описание} | API Client | {файлы} | — | с #1 |
| 3 | {описание} | Frontend | {файлы} | #1, #2 | — |

🧪 Тесты: {категории через запятую}

📎 Артефакт: docs/plan/{slug}/roadmap.md
```

#### Worker Agent (🏗️)
```
🏗️ Выполнение подзадач
| # | Подзадача | Агент | Статус | Gate Check |
|---|-----------|-------|--------|------------|
| 1 | {описание} | Backend | ✅ Выполнено | ✅ 5/5 |
| 2 | {описание} | Worker (сам) | ✅ Выполнено | ✅ 5/5 |
| 3 | {описание} | Frontend | ⚠️ Fix #1 | ✅ 5/5 |

🔗 Контракты проверены: ✅ API ↔ DB ключи совпадают
```

#### Gate Checker Agent (🛡️)
```
🛡️ Результаты Gate Check
| # | Проверка | Статус | Детали |
|---|----------|--------|--------|
| 1 | Билд (py_compile) | ✅ PASS | {N} файлов скомпилировано |
| 2 | Тесты (pytest) | ✅ PASS | {N} passed, 0 failed |
| 3 | Линтер (flake8) | ✅ PASS | 0 ошибок |
| 4 | Дизайн | ✅ PASS | Соответствует design.md |
| 5 | Безопасность | ✅ PASS | 0 нарушений |

🛡️ Итог: {PASS ✅ / FAIL ❌} — {N}/5 проверок пройдено
```

#### Test-Runner Agent (🧪)
```
🧪 Результаты тестов
| Категория | Всего | ✅ Passed | ❌ Failed | ⏭️ Skipped |
|-----------|-------|-----------|-----------|------------|
| e2e | {N} | {N} | {N} | {N} |
| db | {N} | {N} | {N} | {N} |
| critical | {N} | {N} | {N} | {N} |
| **Итого** | **{N}** | **{N}** | **{N}** | **{N}** |

{Если есть упавшие:}
❌ Упавшие тесты
| Тест | Файл | Ошибка |
|------|------|--------|
| test_name | tests/path.py:42 | {краткое описание} |
```

#### Debugger Agent (🐛)
```
🐛 Итерации отладки
| # | Проблема | Гипотеза | Исправление | Результат |
|---|----------|----------|-------------|-----------|
| 1 | {описание} | {root cause} | {что сделано} | ✅/❌ |

📁 Исправленные файлы
| Файл | Изменение | Строки |
|------|-----------|--------|
| path/to/file.py | {описание} | +{N}/-{M} |
```

#### Reviewer Agent (👁️)
```
👁️ Результаты ревью (12 правил)
| # | Правило | Статус | Детали |
|---|---------|--------|--------|
| 1 | Нет emoji в UI | ✅ OK | — |
| 2 | resource_path() | ✅ OK | — |
| 3 | 1px border | ✅ OK | — |
| 4 | DataAccess для CRUD | ✅ OK | — |
| 5 | Параметризованные SQL | ✅ OK | — |
| 6 | __init__.py | ✅ OK | — |
| 7 | Статические перед динамическими | ✅ OK | — |
| 8 | API-first + fallback | ⚠️ WARN | {описание} |
| 9 | Двухрежимность | ✅ OK | — |
| 10 | Совместимость ключей | ✅ OK | — |
| 11 | Именование | ✅ OK | — |
| 12 | Дублирование кода | ℹ️ INFO | {описание} |

📊 Итого: 🚫 BLOCK: {N} | ⚠️ WARN: {N} | ℹ️ INFO: {N}
```

#### Compatibility Checker (🔗)
```
🔗 Проверки совместимости
| # | Проверка | Статус | Детали |
|---|----------|--------|--------|
| 1 | Endpoint → Method | ✅ OK | {N} endpoints |
| 2 | Response fields | ✅ OK | {N} полей |
| 3 | Method signatures | ✅ OK | {N} методов |
| 4 | Pydantic ↔ SQLAlchemy | ✅ OK | {N} моделей |
| 5 | DB fallback format | ✅ OK | {N} пар |
| 6 | DataAccess обёртки | ✅ OK | {N} методов |
```

#### Security Auditor (🔐)
```
🔐 Аудит безопасности
| # | Проверка | Уровень | Статус | Детали |
|---|----------|---------|--------|--------|
| 1 | SQL injection | CRITICAL | ✅ Чисто | Параметризованные запросы |
| 2 | Hardcoded credentials | CRITICAL | ✅ Чисто | — |
| 3 | JWT expiration | HIGH | ⚠️ Найдено | {описание} |
| 4 | CORS policy | MEDIUM | ✅ Чисто | — |

📊 Итого: 🚫 CRITICAL: {N} | ❌ HIGH: {N} | ⚠️ MEDIUM: {N} | ℹ️ LOW: {N}
```

#### Senior Reviewer (👁️)
```
👁️ Архитектурный обзор
| # | Проверка | Статус | Рекомендация |
|---|----------|--------|--------------|
| 1 | Двухрежимная архитектура | ✅ OK | — |
| 2 | Масштабируемость | ✅ OK | — |
| 3 | Дублирование кода | ⚠️ Внимание | {описание} |
| 4 | DataAccess целостность | ✅ OK | — |
| 5 | Производительность | ✅ OK | — |
| 6 | Совместимость | ✅ OK | — |

🔧 Решение: ✅ Рефакторинг не нужен / ⚠️ Рекомендуется / 🚫 Обязателен
```

#### QA Monitor (🖥️)
```
🖥️ Ручное тестирование
| # | Сценарий | Действие | Ожидание | Результат |
|---|----------|----------|----------|-----------|
| 1 | {описание} | {что сделать} | {что должно быть} | ✅/❌ |

📊 CRM статус: ✅ Стабилен / ❌ Крашнулся ({N} ошибок в логах)
🔄 QA-Debug итераций: {N}/3
```

#### PR Creator (📦)
```
📦 Pull Request
| Параметр | Значение |
|----------|----------|
| Branch | {тип}/{slug} |
| PR | #{N} |
| Коммитов | {N} |
| Файлов | {N} (+{add}/-{del} строк) |

📊 CI статус: ✅ 5/5 jobs passed / ❌ {N}/5 failed
🔄 CI-Fix итераций: {N}/3
```

#### Documenter (📝)
```
📝 Обновлённая документация
| Файл | Действие | Что изменено |
|------|----------|--------------|
| docs/{file}.md | ✅ Обновлён | {описание} |
| docs/01-roadmap.md | ✅ Отмечено | {пункты} |

📋 Tech debt записан: {N} пунктов
```

#### Deploy Agent (🚀)
```
🚀 Деплой
| # | Фаза | Статус | Детали |
|---|------|--------|--------|
| 1 | Pre-checks | ✅ | Синтаксис, совместимость, безопасность |
| 2 | Backup | ✅ | DB + код |
| 3 | Deploy | ✅ | docker rebuild |
| 4 | Verify | ✅ | ps + logs + curl |
| 5 | Smoke test | ✅ | {N} endpoints OK |
```

#### Docker Monitor (🐳)
```
🐳 Docker мониторинг
| Контейнер | Статус | CPU | RAM | Uptime |
|-----------|--------|-----|-----|--------|
| crm_api | ✅ healthy | {N}% | {N}MB | {time} |
| crm_postgres | ✅ healthy | {N}% | {N}MB | {time} |
| crm_nginx | ✅ running | {N}% | {N}MB | {time} |
```

### Правила использования emoji в отчётах

1. **Только из словаря** — не использовать произвольные emoji
2. **Консистентность** — одинаковые статусы = одинаковые emoji во всех агентах
3. **Таблицы обязательны** — каждая группа данных должна быть в таблице
4. **Разделители** — `━━━` для начала и конца отчёта
5. **Заголовок** — всегда начинается с emoji агента + `ОТЧЁТ: {ИМЯ}`
6. **Итог** — всегда заканчивается строкой с emoji + `Итог: {резюме}`
7. **Ни один отчёт без таблицы** — даже если одна строка данных
