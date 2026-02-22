# Общие правила проекта — Interior Studio CRM

> Этот файл содержит общие правила для ВСЕХ агентов. НЕ дублировать в промптах агентов.

## 12 критических правил

1. **`__init__.py` обязательны** в database/, ui/, utils/
2. **Запрет emoji в UI** — только SVG через IconLoader
3. **`resource_path()`** для всех ресурсов (иконки, шрифты, логотипы)
4. **Рамки диалогов = 1px** (`border: 1px solid #E0E0E0; border-radius: 10px;`)
5. **Docker rebuild** после серверных изменений (не restart!)
6. **Совместимость API/DB** ключей ответов (total_orders, position, source)
7. **Статические пути ПЕРЕД динамическими** в FastAPI
8. **Двухрежимная архитектура** (online API + offline SQLite)
9. **DataAccess** для всех CRUD в UI (не api_client/db напрямую)
10. **API-first с fallback** на локальную БД при записи
11. **PyQt Signal Safety** — emit из threading.Thread только через `QTimer.singleShot(0, ...)`
12. **Offline-очередь** — только сетевые ошибки, НЕ бизнес-ошибки (409/400)
13. **Параметризованные SQL** (не f-strings, не format)
14. **Именование:** snake_case переменные, PascalCase классы, UPPER_CASE константы

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

### Автопуш и ожидание CI
1. `git add <файлы>` → `git commit` → `git push origin main`
2. `sleep 30` → polling `gh run list` каждые 30 сек (макс 10 мин)
3. CI passed → продолжить
4. CI failed → Debugger → повторный push (макс 3 итерации)

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
