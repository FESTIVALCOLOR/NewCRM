# Interior Studio CRM — Расширенный контекст

> Этот файл НЕ загружается автоматически. Читать через Read при необходимости.

## Сервер

- **Домен:** crm.festivalcolor.ru
- **SSH:** `ssh timeweb` (порт 2222)
- **Путь:** /opt/interior_studio/
- **Docker:** postgres (внутренний), api (127.0.0.1:8000), nginx (80→443 SSL)
- **Docker CLI:** `C:\Docker\docker.exe` (v27.5.1), контекст `interior-studio-server` через SSH
- **Учётка:** см. `.env` файл (ADMIN_USER / ADMIN_PASSWORD)
- **Безопасность:** [docs/21-security.md](../docs/21-security.md)

```bash
# Docker CLI (локальный доступ к серверу, без ssh timeweb)
docker ps                              # Статус контейнеров
docker logs crm_api --tail 50         # Логи API
docker stats --no-stream               # Ресурсы (CPU/RAM)
docker inspect crm_api                 # Детали контейнера

# Полная пересборка (через SSH, для правильных путей)
ssh timeweb "cd /opt/interior_studio && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"
```

## CI / GitHub Actions

**Автоматическая проверка кода при каждом push в main.**
5 jobs: syntax-check, lint, test-db, docker-build, test-e2e (360+ тестов).

### gh CLI авторизация
`gh` CLI авторизован через keyring (`gh auth login`).
- **Аккаунт:** FESTIVALCOLOR
- **Scopes:** gist, read:org, repo
- **Метод:** `gh auth login --git-protocol ssh --web` → токен в keyring

**Обновление токена** (если 401):
1. `gh auth login --git-protocol ssh --web`
2. Перейти по URL, ввести код
3. `gh auth status`

### CI команды
```bash
export PATH="/c/Program Files/GitHub CLI:/c/Program Files/Git/bin:$PATH"

gh run list -L 1                                                                    # Последний запуск
RUN_ID=$(gh run list -L 1 --json databaseId -q '.[0].databaseId')
gh run view $RUN_ID --json jobs -q '.jobs[] | "\(.name): \(.conclusion)"'           # Детали по jobs
gh run view $RUN_ID --log-failed 2>&1 | tail -100                                  # Логи упавших
```

### Автопуш и ожидание CI
1. `git add <файлы>` → `git commit` → `git push origin main`
2. `sleep 30` → polling `gh run list` каждые 30 сек (макс 10 мин)
3. CI passed → сообщить результат
4. CI failed → Debugger исправляет → повторный push (макс 3 итерации)

## Оркестрация: /orkester

Скилл-оркестратор для запуска полного конвейера разработки из 17 агентов.

```
/orkester <описание задачи>
/orkester --mode=fix <описание бага>
/orkester --mode=test <что проверить>
/orkester --mode=qa <что проверить руками>
/orkester --mode=deploy
/orkester --mode=docker <что проверить>
```

8 режимов: full, fix, test, refactor, security, deploy, docker, qa.
Подробности: [docs/17-subagents.md](../docs/17-subagents.md)

## Агенты (17 шт.)

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
| 15 | Deploy | .claude/agents/deploy-agent.md | opus | Docker деплой + мониторинг |
| 16 | Design Stylist | .claude/agents/design-stylist-agent.md | sonnet | Стили, QSS, дизайн |
| 17 | QA Monitor | .claude/agents/qa-monitor-agent.md | sonnet | Ручное QA, мониторинг крашей |

> Подробности: [docs/17-subagents.md](../docs/17-subagents.md)
