# Сервер проекта

> Docker, деплой, инфраструктура, мониторинг, резервное копирование.

## Инфраструктура

```
┌────────────────────────── VPS (Timeweb) ──────────────────────────┐
│ IP: crm.festivalcolor.ru                                                │
│ SSH: ssh timeweb (алиас в ~/.ssh/config, ключ ed25519)            │
│ Путь: /opt/interior_studio/                                       │
│                                                                    │
│ ┌──────────┐   ┌──────────┐   ┌──────────┐                       │
│ │  nginx   │   │   api    │   │ postgres │                        │
│ │ :80/:443 │ → │  :8000   │ → │  :5432   │                        │
│ │          │   │ FastAPI   │   │ PostgreSQL│                       │
│ └──────────┘   └──────────┘   └──────────┘                        │
│                                                                    │
│ Docker Compose orchestration                                       │
└────────────────────────────────────────────────────────────────────┘
```

## Docker Compose ([docker-compose.yml](../docker-compose.yml))

### Сервисы

| Сервис | Образ | Порт | Назначение |
|--------|-------|------|-----------|
| postgres | postgres:15 | 5432 | PostgreSQL база данных |
| api | ./server/Dockerfile | 8000 | FastAPI приложение |
| nginx | nginx:alpine | 80, 443 | Reverse proxy |

### Переменные окружения

```yaml
postgres:
  POSTGRES_DB: interior_studio_crm
  POSTGRES_USER: crm_user
  POSTGRES_PASSWORD: <секрет>

api:
  DATABASE_URL: postgresql://crm_user:<password>@postgres:5432/interior_studio_crm
  SECRET_KEY: <jwt_secret>
  YANDEX_DISK_TOKEN: <token>
```

## Dockerfile ([server/Dockerfile](../server/Dockerfile))

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Docker CLI (локальный доступ)

Docker CLI v27.5.1 установлен в `C:\Docker\docker.exe` с контекстом `interior-studio-server`, подключённым к серверу через SSH (порт 2222). Все docker-команды выполняются **локально без ssh timeweb**.

```bash
# Статус контейнеров
docker ps

# Логи
docker logs crm_api --tail 50
docker logs crm_nginx --tail 50
docker logs crm_postgres --tail 50

# Ресурсы (CPU/RAM/NET)
docker stats --no-stream

# Healthcheck
docker inspect crm_api --format='{{json .State.Health.Status}}'

# Выполнить команду внутри контейнера
docker exec crm_postgres psql -U crm_user -d interior_studio_crm -c "SELECT count(*) FROM contracts"

# Образы
docker images
```

**Примечание:** `docker-compose` команды (build, up, down) требуют выполнения через SSH для корректных путей к build context:
```bash
ssh timeweb "cd /opt/interior_studio && docker-compose down && docker-compose build --no-cache api && docker-compose up -d"
```

### VS Code Container Tools

Расширение `ms-azuretools.vscode-containers` настроено на работу с Docker CLI. Настройки в `settings.json`:
```json
{
    "containers.containerCommand": "C:\\Docker\\docker.exe",
    "containers.composeCommand": "C:\\Docker\\docker.exe compose",
    "containers.environment": {
        "DOCKER_HOST": "ssh://root@crm.festivalcolor.ru:2222",
        "DOCKER_CONTEXT": "interior-studio-server"
    }
}
```

## Управление сервером

### SSH подключение

```bash
ssh timeweb                    # алиас из ~/.ssh/config
cd /opt/interior_studio
```

### Статус

```bash
docker ps                              # через Docker CLI (предпочтительно)
docker-compose ps                      # через SSH
docker-compose logs -f api             # логи API в реальном времени
docker-compose logs --tail=50 api      # последние 50 строк
```

### Перезапуск (НЕ применяет изменения!)

```bash
docker-compose restart api     # только перезапуск процесса
```

### Полная пересборка (применяет изменения)

```bash
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
```

> **КРИТИЧЕСКОЕ ПРАВИЛО:** `restart` НЕ перезагружает Python-модули. Для применения изменений кода — только полная пересборка!

### Подключение к БД

```bash
docker-compose exec postgres psql -U crm_user -d interior_studio_crm
```

## Деплой (пошагово)

### 1. Подготовка (локально)

```bash
# Проверка синтаксиса
python -m py_compile server/main.py
python -m py_compile server/database.py
python -m py_compile server/schemas.py

# Коммит
git add server/
git commit -m "описание изменений"
git push
```

### 2. Бэкап (на сервере)

```bash
ssh timeweb
cd /opt/interior_studio

# Бэкап БД
docker exec crm_postgres pg_dump -U crm_user interior_studio_crm > backup_$(date +%Y%m%d_%H%M%S).sql

# Бэкап кода
tar -czf backup_server_$(date +%Y%m%d_%H%M%S).tar.gz server/
```

### 3. Деплой (на сервере)

```bash
# Копировать файлы
scp -r server/ root@crm.festivalcolor.ru:/opt/interior_studio/server/

# Пересборка
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
```

### 4. Проверка

```bash
# Статус
docker-compose ps

# Логи (подождать 5 сек)
sleep 5 && docker-compose logs --tail=30 api

# Smoke test
curl -s http://localhost:8000/
```

### 5. Smoke test (с клиента)

```bash
curl -s http://crm.festivalcolor.ru:8000/
# Ожидается: {"message": "Interior Studio CRM API", ...}
```

## Откат (Rollback)

```bash
ssh timeweb
cd /opt/interior_studio

# Восстановить код
tar -xzf backup_server_TIMESTAMP.tar.gz

# Восстановить БД (если нужно)
cat backup_TIMESTAMP.sql | docker exec -i crm_postgres psql -U crm_user -d interior_studio_crm

# Пересобрать
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
```

## Сборка клиента (PyInstaller)

### Pre-Build чеклист

1. Проверить `API_BASE_URL` в [config.py](../config.py) → production URL
2. Проверить наличие `__init__.py` в database/, ui/, utils/
3. Проверить `hiddenimports` в [InteriorStudio.spec](../InteriorStudio.spec)

### Сборка

```bash
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm
```

### Проверка

```bash
dir dist\InteriorStudio.exe
# Ожидаемый размер: 50-100 MB
```

## Мониторинг

### Docker CLI мониторинг (предпочтительно)

```bash
# Статус и здоровье контейнеров
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

# Ресурсы (CPU/RAM/NET/IO)
docker stats --no-stream --format "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"

# Healthcheck детали
docker inspect crm_api --format='{{json .State.Health}}'

# Поиск ошибок в логах API
docker logs crm_api --tail 200 2>&1 | grep -i "error\|traceback\|500\|critical"

# Логи nginx (4xx/5xx)
docker logs crm_nginx --tail 200 2>&1 | grep -E " (4|5)[0-9]{2} "
```

### Через SSH

```bash
ssh timeweb "cd /opt/interior_studio && docker-compose logs -f api"
ssh timeweb "docker stats --no-stream"
ssh timeweb "df -h"
```

### Оркестратор

```
/orkester --mode=docker проверить здоровье контейнеров
/orkester --mode=docker анализ логов API за последний час
```

### Docker Health Checks

Все контейнеры имеют healthcheck:
- **postgres:** `pg_isready -U crm_user` (каждые 10с)
- **api:** `python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"` (каждые 30с)
- **nginx:** нет (зависит от api)
