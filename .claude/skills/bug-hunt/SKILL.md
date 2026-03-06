---
name: bug-hunt
description: Проактивный поиск багов по кодовой базе
user_invocable: true
---

# Bug Hunt — Проактивный поиск и исправление багов

Аргумент: `[файл или директория]` — цель аудита (по умолчанию: `ui/`)

## Обязательная последовательность

### Фаза 1: Автоматическое сканирование

Запустить скрипт сканера паттернов:

```bash
.venv/Scripts/python.exe scripts/bug_scanner.py [аргумент]
```

Скрипт выведет список потенциальных багов с серьёзностью и контекстом.

### Фаза 2: Субагентный аудит (параллельно)

Для каждого крупного файла (>500 строк) — запустить субагент `.claude/agents/bug-hunter-agent.md` через Task tool:

```
Задание: Аудит файла [путь]
Прочитай .claude/agents/shared-rules.md, затем файл.
Выполни все 6 фаз поиска паттернов.
```

Параллелизация: до 3 субагентов одновременно для разных файлов.

### Фаза 3: Верификация

Для каждого найденного бага (скрипт + субагенты):
1. Прочитать контекст ±20 строк
2. Классифицировать: реальный баг / ложное срабатывание / tech debt
3. Если баг — определить минимальное исправление

### Фаза 4: Исправление

Порядок: CRITICAL → HIGH → MEDIUM → LOW

Для каждого бага:
1. Применить исправление через Edit
2. Запустить тесты затронутого модуля
3. Если тесты обновились из-за исправления — обновить тесты
4. Коммит пакетом (все баги одного файла = один коммит)

### Фаза 5: Отчёт

Вывести сводную таблицу:

```
| Файл | Багов | CRITICAL | HIGH | MEDIUM | LOW | Исправлено |
|------|-------|----------|------|--------|-----|------------|
```

## Категории паттернов

| Категория | Серьёзность | Grep-запрос |
|-----------|------------|-------------|
| Прямой SQL | CRITICAL | `cursor\.execute\|execute_raw_query\|execute_raw_update` |
| f-string SQL | CRITICAL | `f['"](.*?(UPDATE\|INSERT).*?\{)` |
| DatabaseManager | CRITICAL | `DatabaseManager\(\)` |
| NoneType | HIGH | `for \w+ in self\.data\.` без `or []` |
| Offline queue | HIGH | `def (create\|update\|delete)_` без `_queue_operation` |
| Question box | MEDIUM | `CustomMessageBox.*question\|QMessageBox\.Yes` |
| Signal leak | MEDIUM | `.connect(` в `showEvent` без guard |
| prefer_local | MEDIUM | `prefer_local\s*=\s*True` |

## Известные ложные срабатывания

- `execute_raw_query` для `supervision_project_history` — нет API endpoint
- `prefer_local = True` в `_first_load()` — допустимо для первой загрузки
- Lambda захват `cur=text` — default argument, не closure bug
- DAN role и `archive_widget` — DAN не имеет доступа к вкладке Архив
