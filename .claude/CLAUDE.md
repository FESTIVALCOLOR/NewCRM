# Interior Studio CRM

## Язык общения
**Всегда отвечать на русском языке**, включая после компактинга контекста. Все комментарии в коде и строки UI — тоже на русском.

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

### Ключевые компоненты

| Компонент | Файл | Строк |
|-----------|------|-------|
| CRM Kanban | ui/crm_tab.py | 17K+ |
| FastAPI сервер | server/main.py | 5800+ (144+ endpoints) |
| SQLite менеджер | database/db_manager.py | 4400+ (50+ миграций) |
| REST клиент | utils/api_client.py | 2300+ |
| Синхронизация БД | utils/db_sync.py | 1731 |
| Доступ к данным | utils/data_access.py | 915 |

## Полная документация

> **Вся детальная документация находится в папке [docs/](../docs/)**

**Содержание:** [docs/Index.md](../docs/Index.md)

| # | Документ | Путь |
|---|----------|------|
| 1 | Roadmap | [docs/01-roadmap.md](../docs/01-roadmap.md) |
| 2 | Правила проекта | [docs/02-project-rules.md](../docs/02-project-rules.md) |
| 3 | Авторизация | [docs/03-auth.md](../docs/03-auth.md) |
| 4 | Бекенд | [docs/04-backend.md](../docs/04-backend.md) |
| 5 | Фронтенд | [docs/05-frontend.md](../docs/05-frontend.md) |
| 6 | API и Endpoints | [docs/06-api-endpoints.md](../docs/06-api-endpoints.md) |
| 7 | Сервер и деплой | [docs/07-server.md](../docs/07-server.md) |
| 8 | Фичи и спеки | [docs/08-features-specs.md](../docs/08-features-specs.md) |
| 9 | Дизайн и стили | [docs/09-design-styles.md](../docs/09-design-styles.md) |
| 10 | UI и Utils | [docs/10-ui-utils.md](../docs/10-ui-utils.md) |
| 11 | Система оплат | [docs/11-payments.md](../docs/11-payments.md) |
| 12 | Система дедлайнов | [docs/12-deadlines.md](../docs/12-deadlines.md) |
| 13 | CRM интеграция | [docs/13-crm-integration.md](../docs/13-crm-integration.md) |
| 14 | CRM надзора | [docs/14-crm-supervision.md](../docs/14-crm-supervision.md) |
| 15 | Тестирование | [docs/15-testing.md](../docs/15-testing.md) |
| 16 | AI промпты | [docs/16-ai-prompts.md](../docs/16-ai-prompts.md) |
| 17 | Субагенты | [docs/17-subagents.md](../docs/17-subagents.md) |
| 18 | Agent Skills | [docs/18-agent-skills.md](../docs/18-agent-skills.md) |
| 19 | Логи и покрытие | [docs/19-logs-coverage.md](../docs/19-logs-coverage.md) |
| 20 | UI тесты (pywinauto) | [docs/20-ui-testing.md](../docs/20-ui-testing.md) |
| 21 | Безопасность | [docs/21-security.md](../docs/21-security.md) |
| 22 | Оптимизация (Roadmap) | [docs/22-optimization-roadmap.md](../docs/22-optimization-roadmap.md) |

## Критические правила (краткий справочник)

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

> Подробности: [docs/02-project-rules.md](../docs/02-project-rules.md)

## Сервер

- **IP:** 147.45.154.193 | **Домен:** crm.festivalcolor.ru
- **SSH:** `ssh timeweb` (порт 2222)
- **Путь:** /opt/interior_studio/
- **Docker:** postgres (внутренний), api (127.0.0.1:8000), nginx (80→443 SSL)
- **Учётка:** admin / admin123
- **Безопасность:** [docs/21-security.md](../docs/21-security.md) (~82%)

```bash
# Полная пересборка (применяет изменения)
ssh timeweb
cd /opt/interior_studio
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
```

## Клиент

```bash
# Запуск
.venv\Scripts\python.exe main.py

# Сборка exe
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm
```

## Тестирование

```bash
pytest tests/db/ -v                          # DB тесты (без сервера)
pytest tests/e2e/ -v --timeout=60            # E2E (нужен сервер)
pytest tests/ -m critical -v --timeout=60    # Критические
```

### Экономия контекста при чтении логов тестов

**ВАЖНО:** Логи UI тестов (pywinauto) содержат 30-150K токенов из-за verbose unicode-escaped строк.
НИКОГДА не читать их через Read. Всегда использовать парсер:

```bash
.venv/Scripts/python.exe tests/ui/parse_results.py <путь_к_output_файлу>
```

Парсер выдаёт только: итого passed/failed/skipped, имена FAILED тестов, причины XFAIL/SKIP.
Детальные логи конкретного теста читать через Grep только при необходимости отладки.

> Подробности: [docs/15-testing.md](../docs/15-testing.md)

## Оркестрация: /orkester

Скилл-оркестратор для запуска полного конвейера разработки из 16 агентов.

```
/orkester <описание задачи>
/orkester --mode=fix <описание бага>
/orkester --mode=test <что проверить>
/orkester --mode=deploy
```

6 режимов: full, fix, test, refactor, security, deploy.
Подробности: [docs/17-subagents.md](../docs/17-subagents.md)

## Агенты (16 шт.)

| # | Агент | Файл | Модель | Назначение |
|---|-------|------|--------|-----------|
| 1 | Planner | .claude/agents/planner-agent.md | opus | Планирование задач |
| 2 | Worker | .claude/agents/worker-agent.md | opus | Исполнение кода, координация |
| 3 | Test-Runner | .claude/agents/test-runner-agent.md | haiku | Запуск и написание тестов |
| 4 | Debugger | .claude/agents/debugger-agent.md | sonnet | Отладка, исправление падений |
| 5 | Reviewer | .claude/agents/reviewer-agent.md | sonnet | Code review по 12 правилам |
| 6 | Documenter | .claude/agents/documenter-agent.md | haiku | Документация, tech debt |
| 7 | Refactor | .claude/agents/refactor-agent.md | sonnet | Рефакторинг кода |
| 8 | Security Auditor | .claude/agents/security-auditor-agent.md | sonnet | Аудит безопасности |
| 9 | Senior Reviewer | .claude/agents/senior-reviewer-agent.md | opus | Архитектурный обзор |
| 10 | Backend | .claude/agents/backend-agent.md | sonnet | FastAPI, SQLAlchemy |
| 11 | Frontend | .claude/agents/frontend-agent.md | sonnet | PyQt5 UI |
| 12 | API Client | .claude/agents/api-client-agent.md | sonnet | REST, offline, sync |
| 13 | Database | .claude/agents/database-agent.md | haiku | SQLite, миграции |
| 14 | Compatibility | .claude/agents/compatibility-checker.md | haiku | Server-client проверка |
| 15 | Deploy | .claude/agents/deploy-agent.md | opus | Docker деплой |
| 16 | Design Stylist | .claude/agents/design-stylist-agent.md | sonnet | Стили, QSS, дизайн |

> Подробности: [docs/17-subagents.md](../docs/17-subagents.md)
