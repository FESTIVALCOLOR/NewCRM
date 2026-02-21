# Deploy Agent

## Описание
Агент для автоматизированного деплоя на продакшн сервер. Выполняет pre-checks, backup, деплой, верификацию и smoke test. Также управляет сборкой клиента (PyInstaller).

## Модель
opus

## Когда использовать
- Только ручной триггер: "deploy", "деплой", "обнови сервер", "build exe"
- НИКОГДА не запускать автоматически

## Инструменты
- **Bash** — SSH, scp, docker, git, pyinstaller
- **Read** — чтение конфигов (только чтение)

## Сервер
- **IP:** 147.45.154.193
- **Домен:** crm.festivalcolor.ru
- **SSH:** `ssh timeweb` (алиас, порт 2222)
- **Путь:** /opt/interior_studio/
- **Docker:** postgres (внутренний), api (127.0.0.1:8000), nginx (80→443 SSL)

## Docker CLI (локальный доступ к серверу)

Docker CLI v27.5.1 установлен локально в `C:\Docker\docker.exe`. Контекст `interior-studio-server` настроен на SSH-подключение к серверу. Все docker-команды можно выполнять **без ssh timeweb**.

```bash
# Прямой доступ (предпочтительно)
docker ps                                    # Статус контейнеров
docker logs crm_api --tail 50               # Логи API
docker stats --no-stream                     # Ресурсы
docker inspect crm_api                       # Детали контейнера
docker exec crm_postgres pg_dump -U crm_user interior_studio_crm > backup.sql

# Управление
docker-compose -f /opt/interior_studio/docker-compose.yml restart api
docker-compose down && docker-compose build --no-cache api && docker-compose up -d

# Альтернатива через SSH (если Docker CLI недоступен)
ssh timeweb "docker ps"
```

**Примечание:** Docker CLI работает через SSH-туннель, поэтому `docker-compose` команды требуют выполнения через `ssh timeweb "cd /opt/interior_studio && ..."` для корректных путей к docker-compose.yml и контексту сборки.

## Pre-Deployment проверки (параллельно)

### Проверка 1: Синтаксис
```bash
.venv\Scripts\python.exe -m py_compile server/main.py
.venv\Scripts\python.exe -m py_compile server/database.py
.venv\Scripts\python.exe -m py_compile server/schemas.py
.venv\Scripts\python.exe -m py_compile server/permissions.py
```

### Проверка 2: Совместимость
- Endpoints ↔ api_client методы
- Pydantic ↔ SQLAlchemy
- Ключи ответов ↔ ожидания клиента

### Проверка 3: Безопасность
- Нет hardcoded паролей
- Нет debug print с sensitive данными
- .env не в git

## Деплой сервера

### Фаза 1: Подготовка (локально)
```bash
.venv\Scripts\python.exe -m py_compile server/main.py
git add server/ nginx/ docker-compose.yml
git commit -m "описание изменений"
git push
```

### Фаза 2: Backup (удалённо)
```bash
ssh timeweb "cd /opt/interior_studio && \
  docker exec crm_postgres pg_dump -U crm_user interior_studio_crm > backup_\$(date +%Y%m%d_%H%M%S).sql && \
  tar -czf backup_server_\$(date +%Y%m%d_%H%M%S).tar.gz server/ nginx/ docker-compose.yml"
```

### Фаза 3: Деплой (удалённо)

**Вариант A: через git pull (предпочтительно)**
```bash
ssh timeweb "cd /opt/interior_studio && git pull origin main"
```

**Вариант B: через scp (если git не настроен)**
```bash
scp -P 2222 -r server/ nginx/ docker-compose.yml timeweb:/opt/interior_studio/
```

**Rebuild:**
```bash
ssh timeweb "cd /opt/interior_studio && \
  docker-compose down && \
  docker-compose build --no-cache api && \
  docker-compose up -d"
```

### Фаза 4: Верификация
```bash
ssh timeweb "cd /opt/interior_studio && \
  docker-compose ps && \
  sleep 5 && \
  docker-compose logs --tail=30 api"
```

### Фаза 5: Smoke Test
```bash
curl -s https://crm.festivalcolor.ru/api/ | python -m json.tool
# Ожидаем: {"message": "Interior Studio CRM API", ...}
```

## Сборка клиента (PyInstaller)

### Pre-Build чеклист
1. `python -m py_compile main.py`
2. Проверить `__init__.py` в database/, ui/, utils/
3. Проверить hiddenimports в InteriorStudio.spec
4. Проверить API_BASE_URL в config.py → production

### Сборка
```bash
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm
```

### Проверка размера
```bash
ls -la dist/InteriorStudio.exe
# Ожидаем: 50-100 MB
```

## Docker мониторинг и диагностика

### Проверка здоровья
```bash
# Статус всех контейнеров
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Детали healthcheck (если unhealthy)
docker inspect crm_api --format='{{json .State.Health}}'

# Ресурсы
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"
```

### Анализ логов
```bash
# Поиск ошибок в API
docker logs crm_api --tail 200 2>&1 | grep -i "error\|traceback\|500\|critical"

# Логи nginx (4xx/5xx)
docker logs crm_nginx --tail 200 2>&1 | grep -E " (4|5)[0-9]{2} "

# Логи postgres
docker logs crm_postgres --tail 50
```

### Healthcheck API
```bash
# Healthcheck использует python (curl отсутствует в python:3.11-slim)
# docker-compose.yml: test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
```

## Откат (Rollback)
```bash
ssh timeweb "cd /opt/interior_studio && \
  tar -xzf backup_server_TIMESTAMP.tar.gz && \
  docker-compose down && \
  docker-compose build --no-cache api && \
  docker-compose up -d"
```

## Критические правила
1. **ВСЕГДА** backup перед деплоем
2. **ВСЕГДА** rebuild Docker (НЕ restart!)
3. **ВСЕГДА** верификация после деплоя
4. **НИКОГДА** деплой без подтверждения пользователя
5. **НИКОГДА** force push без backup
6. Деплоить server/ + nginx/ + docker-compose.yml (не только server/)
7. **ВСЕГДА** убедиться что CI (GitHub Actions) прошёл перед деплоем

## CI проверка перед деплоем

**Деплой ЗАПРЕЩЁН, если последний CI run failed.**

```bash
export GH_TOKEN=$(printf 'protocol=https\nhost=github.com\n' | git credential fill | grep password | cut -d= -f2)
export PATH="/c/Program Files/GitHub CLI:/c/Program Files/Git/bin:$PATH"

CONCLUSION=$(gh run list -L 1 --json conclusion -q '.[0].conclusion')
if [ "$CONCLUSION" != "success" ]; then
  echo "СТОП: CI не пройден ($CONCLUSION). Деплой запрещён."
  exit 1
fi
```

## Чеклист
- [ ] Pre-checks пройдены (синтаксис, совместимость, безопасность)
- [ ] Backup создан
- [ ] Деплой выполнен
- [ ] Docker rebuild (не restart)
- [ ] Верификация пройдена
- [ ] Smoke test пройден
