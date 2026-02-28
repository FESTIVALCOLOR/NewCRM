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

6-фазный конвейер из 21 агента: Research → Design → Plan → Implement (+Gate Checks) → PR → CI.

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

## Агенты (21 шт.)

| # | Агент | Файл | Модель | Назначение |
|---|-------|------|--------|-----------|
| 1 | Research | .claude/agents/research-agent.md | sonnet | Исследование контекста, 3 направления |
| 2 | Design | .claude/agents/design-agent.md | opus | C4, DFD, ADR, тест-стратегия |
| 3 | Planner | .claude/agents/planner-agent.md | opus | Планирование задач, roadmap.md |
| 4 | Worker | .claude/agents/worker-agent.md | opus | Исполнение кода, координация |
| 5 | Test-Runner | .claude/agents/test-runner-agent.md | haiku | Запуск и написание тестов |
| 6 | Debugger | .claude/agents/debugger-agent.md | sonnet | Отладка, исправление падений |
| 7 | Reviewer | .claude/agents/reviewer-agent.md | sonnet | Code review по 12 правилам |
| 8 | Documenter | .claude/agents/documenter-agent.md | haiku | Документация, tech debt |
| 9 | Refactor | .claude/agents/refactor-agent.md | sonnet | Рефакторинг кода |
| 10 | Security Auditor | .claude/agents/security-auditor-agent.md | sonnet | Аудит безопасности |
| 11 | Senior Reviewer | .claude/agents/senior-reviewer-agent.md | opus | Архитектурный обзор |
| 12 | Backend | .claude/agents/backend-agent.md | sonnet | FastAPI, SQLAlchemy |
| 13 | Frontend | .claude/agents/frontend-agent.md | sonnet | PyQt5 UI |
| 14 | API Client | .claude/agents/api-client-agent.md | sonnet | REST, offline, sync |
| 15 | Database | .claude/agents/database-agent.md | haiku | SQLite, миграции |
| 16 | Compatibility | .claude/agents/compatibility-checker.md | haiku | Server-client проверка |
| 17 | Deploy | .claude/agents/deploy-agent.md | opus | Docker деплой + мониторинг |
| 18 | Design Stylist | .claude/agents/design-stylist-agent.md | sonnet | Стили, QSS, дизайн |
| 19 | QA Monitor | .claude/agents/qa-monitor-agent.md | sonnet | Ручное QA, мониторинг крашей |
| 20 | Gate Checker | .claude/agents/gate-checker-agent.md | haiku | 5 проверок на каждую фазу |
| 21 | PR Creator | .claude/agents/pr-creator-agent.md | haiku | Feature branch, PR via gh |

**Итого:** opus x5, sonnet x10, haiku x6

> Подробности: [docs/17-subagents.md](../docs/17-subagents.md)
