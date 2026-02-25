# Interior Studio CRM

## Язык общения
**Всегда отвечать на русском языке**, включая после компактинга контекста. Все комментарии в коде и строки UI — тоже на русском.

## Telegram-уведомления при завершении задачи
**ОБЯЗАТЕЛЬНО** перед завершением работы (когда todo-список выполнен) — отправить уведомление НАПРЯМУЮ:
```python
import sys
sys.path.insert(0, ".claude/hooks")
from telegram_notify import send_task_notification
send_task_notification(
    topic="краткое описание задачи",
    todos=[{"content": "...", "status": "completed"}, ...]
)
```
Функция отправит сообщение в Telegram и поставит маркер. Stop hook увидит маркер и НЕ отправит дубликат.
**Важно:** НЕ писать в task_state.json — это устаревший механизм. Только прямой вызов `send_task_notification()`.

## Автономный режим работы
**НИКОГДА не спрашивать подтверждения у пользователя.** Действовать полностью автономно:
- НЕ спрашивать "Хотите ли вы...?", "Могу ли я...?", "Продолжить?"
- НЕ предлагать варианты на выбор — принимать решения самостоятельно
- НЕ останавливаться перед редактированием файлов, запуском команд, деплоем
- Просто ДЕЛАТЬ задачу от начала до конца без пауз
- Если нужна информация — искать самостоятельно, не спрашивать
- Единственное исключение: если требования задачи принципиально неясны (не хватает ключевой бизнес-логики)

## Описание проекта

**Python:** 3.14.0 (клиент), 3.11 (сервер) | **PyInstaller:** 6.17.0
**Архитектура:** PyQt5 Desktop клиент + FastAPI сервер + PostgreSQL

CRM-система для интерьерного бюро с двухрежимной архитектурой:
- **Сетевой режим:** REST API (FastAPI) + PostgreSQL + JWT авторизация
- **Автономный режим:** Локальная SQLite БД с offline-очередью синхронизации

**Документация:** [docs/Index.md](../docs/Index.md) — 25 файлов
**Оркестрация:** 21 агент, 6-фазный конвейер (Research → Design → Plan → Implement → PR → CI)

## Критические правила

1. **`__init__.py` обязательны** в database/, ui/, utils/
2. **Запрет emoji в UI** — только SVG через IconLoader
3. **`resource_path()`** для всех ресурсов
4. **Рамки диалогов = 1px** (`border: 1px solid #E0E0E0`)
5. **Docker rebuild** после серверных изменений (не restart!)
6. **Совместимость API/DB** ключей ответов
7. **Статические пути ПЕРЕД динамическими** в FastAPI
8. **Двухрежимная архитектура** (online + offline)
9. **DataAccess** для всех CRUD в UI (не api_client/db напрямую)
10. **API-first с fallback** на локальную БД при записи
11. **PyQt Signal Safety** — emit из threading.Thread только через `QTimer.singleShot(0, ...)`
12. **Offline-очередь** — только сетевые ошибки (APIConnectionError/APITimeoutError), НЕ бизнес-ошибки (409/400)

> Подробности: [docs/02-project-rules.md](../docs/02-project-rules.md)

## Docker rebuild — ОБЯЗАТЕЛЬНАЯ процедура

**После ЛЮБЫХ изменений в `server/`** — ОБЯЗАТЕЛЬНО пересобрать Docker на production:
```bash
ssh timeweb "cd /opt/interior_studio && git pull origin <branch> && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"
```
**Когда:** после каждого push, содержащего изменения в `server/` (роутеры, модели, схемы, миграции).
**Проверка:** после rebuild выполнить `ssh timeweb 'curl -s http://localhost:8000/health'` — должен вернуть `{"status":"healthy"}`.
**НЕЛЬЗЯ:** использовать `docker-compose restart` — это НЕ подхватывает новый код.

## Верификация после исправлений

**ОБЯЗАТЕЛЬНО** после каждого цикла исправлений:
1. CI green (все 5 jobs)
2. Если есть серверные изменения → Docker rebuild → health check
3. Проверка исправленных endpoint-ов через `curl` с JWT токеном
4. НЕ отмечать баг как исправленный, если нет доказательства работоспособности

## Контекстное окно 1M токенов

**Модель:** `opus[1m]` — включён расширенный контекст 1 миллион токенов (beta `context-1m-2025-08-07`).

- **Чат (без оркестра):** 1M включён по умолчанию через `settings.local.json` → `"model": "opus[1m]"`
- **Оркестр (субагенты):** Task tool поддерживает только `"sonnet"`, `"opus"`, `"haiku"` без `[1m]` суффикса. Субагенты работают со стандартным контекстом (~200K). Это нормально — каждый субагент решает узкую задачу.
- **Ценообразование:** до 200K токенов — стандартная цена. Свыше 200K — 2x input, 1.5x output.
- **Отключение:** переменная окружения `CLAUDE_CODE_DISABLE_1M_CONTEXT=1` или `/model opus` (без суффикса).

## Экономия токенов

- **docs/**: Использовать Grep для поиска нужных секций, НЕ Read целиком
- **Крупные файлы** (>2000 строк): Grep + Read с offset/limit
- **UI тест логи**: ТОЛЬКО через парсер: `.venv/Scripts/python.exe tests/ui/parse_results.py <файл>`

## Клиент

```bash
.venv\Scripts\python.exe main.py                                        # Запуск
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm   # Сборка
```

## Тестирование

```bash
pytest tests/db/ -v                          # DB (без сервера)
pytest tests/e2e/ -v --timeout=60            # E2E (нужен сервер)
pytest tests/ -m critical -v --timeout=60    # Критические
```

## Стратегия тестирования и предотвращения ошибок

### 3 уровня проверки (обязательны после каждого цикла исправлений)

**Уровень 1: Автотесты (CI)**
- Все 5 CI jobs должны быть green перед любым деплоем
- При добавлении нового endpoint — писать E2E тест в `tests/e2e/`
- При исправлении бага — писать regression тест, воспроизводящий баг

**Уровень 2: API верификация (curl)**
- После Docker rebuild проверить ВСЕ изменённые endpoint-ы через curl
- Генерация JWT: `ssh timeweb 'docker exec crm_api python3 -c "from auth import create_access_token; print(create_access_token({\"sub\": \"1\"}))"'`
- Проверка: `ssh timeweb "curl -sL -H 'Authorization: Bearer TOKEN' 'URL'" | python3 -c "import sys,json; print(json.dumps(json.load(sys.stdin), indent=2))"`

**Уровень 3: Smoke-тест клиента**
- Запустить `.venv\Scripts\python.exe main.py` и проверить каждый исправленный модуль
- Для невозможности запуска (headless) — проверить логи на ошибки

### Правило новых тестов
При каждом баге, который не был пойман существующими тестами:
1. Определить какой тест мог бы поймать баг
2. Написать этот тест в соответствующую директорию (tests/e2e/, tests/client/, tests/db/)
3. Убедиться что тест FAIL на старом коде и PASS на новом

## Расширенный контекст

Читать через Read при необходимости:
- **Сервер, Docker, CI, агенты:** `.claude/CLAUDE-extended.md`
- **Общие правила агентов:** `.claude/agents/shared-rules.md`
- **Оркестрация:** `/orkester` (skill) | [docs/17-subagents.md](../docs/17-subagents.md)
