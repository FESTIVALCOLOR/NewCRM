# AI промпты и правила

> Базовые промпты, context compression, правила использования AI в проекте.

## Конфигурация Claude Code

### Файл настроек ([.claude/settings.local.json](../.claude/settings.local.json))

```json
{
  "model": "opus",
  "thinkingBudget": "ultratank"
}
```

### Context Compression (System Prompt)

При сжатии контекста применяются следующие правила:

```
1. ЯЗЫК: Всегда отвечай на русском языке. Все комментарии, объяснения, вопросы — только на русском.
2. НЕ ВЫДУМЫВАЙ: Если не знаешь ответа — честно скажи. Никогда не генерируй ложные ответы.
3. ДОКУМЕНТАЦИЯ: После завершения задачи автоматически запускай /init для обновления CLAUDE.md.
4. ПЛАН: Когда пользователь просит план — автоматически входи в plan mode.
```

### Permissions (Разрешения)

```json
"allow": [
    "Bash(*)",
    "WebFetch(*)",
    "mcp__playwright__browser_*(*)",
    "mcp__context7__resolve-library-id(*)",
    "mcp__context7__query-docs(*)"
]
```

## Hooks (Автоматические проверки)

### PostToolUse: Edit

**Триггер:** После каждого `Edit` в файле
**Модель:** claude-haiku-4-5-20251001
**Таймаут:** 15 сек

Проверяет:
1. **ui/ файлы:** Наличие emoji (Unicode U+2600+) — ЗАПРЕЩЕНЫ
2. **server/ файлы:** Напоминание `[DEPLOY] Docker rebuild required`
3. **Ресурсы:** Использование `resource_path()` для QPixmap/QIcon
4. **Frameless:** Рамка `border: 1px` для FramelessWindowHint

### PostToolUse: Write

**Триггер:** После каждого `Write` в файл
**Модель:** claude-haiku-4-5-20251001
**Таймаут:** 15 сек

Проверяет те же правила что и Edit.

### PreToolUse: Bash

**Триггер:** Перед выполнением Bash команды
**Модель:** claude-haiku-4-5-20251001
**Таймаут:** 10 сек

Проверяет:
1. Если git commit → нет emoji в сообщении
2. Напоминание py_compile для .py файлов

### Stop Hook

**Триггер:** При завершении работы агента
**Модель:** claude-haiku-4-5-20251001
**Таймаут:** 30 сек

Проверяет совместимость сервер-клиент.

## Промпты для типовых задач

### 1. Добавление нового endpoint

```
Добавь новый API endpoint:
1. Endpoint: [метод] /api/[путь]
2. Pydantic схема в server/schemas.py
3. Метод в utils/api_client.py
4. Вызов в UI с try/except и fallback на db_manager
5. Тест в tests/e2e/
6. Инструкция по Docker rebuild
```

### 2. Исправление бага

```
Баг: [описание]
1. Найди root cause
2. Проверь затронутые файлы (server + client + DB)
3. Исправь с минимальным изменением
4. Добавь регрессионный тест
5. Проверь совместимость API/DB форматов
```

### 3. Добавление UI компонента

```
Добавь UI компонент:
1. Следуй стилям из utils/unified_styles.py
2. Используй IconLoader для иконок (НЕ emoji)
3. resource_path() для ресурсов
4. 1px border для frameless диалогов
5. DataAccess для данных (НЕ прямой api_client/db)
6. Оба режима: online + offline
```

### 4. Деплой на сервер

```
Деплой изменения на сервер:
1. py_compile всех изменённых файлов
2. Бэкап БД и кода
3. scp файлов на сервер
4. docker-compose down && build --no-cache && up -d
5. Проверка логов и smoke test
```

## Промпты для автоматизации (рекомендуемые)

### Pre-commit проверка

```
Перед коммитом автоматически:
1. py_compile всех изменённых .py файлов
2. Запустить pytest tests/ -m critical
3. Проверить отсутствие emoji в UI файлах
4. Проверить наличие __init__.py
5. Проверить resource_path() для ресурсов
```

### Post-deploy верификация

```
После деплоя автоматически:
1. Проверить docker-compose ps (все контейнеры running)
2. Curl smoke test на /
3. Проверить логи на ошибки
4. Запустить E2E critical тесты
```

### Автоматический code review

```
При изменении файла автоматически:
1. Проверить соответствие стилям unified_styles.py
2. Проверить API-first паттерн для DB операций
3. Проверить совместимость server-client форматов
4. Предложить тесты для нового кода
```

## MCP Серверы

### Context7

Поиск документации библиотек:
```
mcp__context7__resolve-library-id  — найти ID библиотеки
mcp__context7__query-docs           — запрос документации
```

### Playwright

Автоматизация браузера для тестирования:
```
mcp__playwright__browser_navigate   — навигация
mcp__playwright__browser_snapshot   — accessibility snapshot
mcp__playwright__browser_click      — клик
mcp__playwright__browser_type       — ввод текста
mcp__playwright__browser_take_screenshot — скриншот
mcp__playwright__browser_console_messages — логи консоли
mcp__playwright__browser_evaluate   — выполнение JS
```
