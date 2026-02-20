# Сервер проекта

> Docker, деплой, инфраструктура, мониторинг, резервное копирование.

## Инфраструктура

```
┌────────────────────────── VPS (Timeweb) ──────────────────────────┐
│ IP: 147.45.154.193                                                │
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

## Управление сервером

### SSH подключение

```bash
ssh timeweb                    # алиас из ~/.ssh/config
cd /opt/interior_studio
```

### Статус

```bash
docker-compose ps              # статус контейнеров
docker-compose logs -f api     # логи API в реальном времени
docker-compose logs --tail=50 api  # последние 50 строк
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
scp -r server/ root@147.45.154.193:/opt/interior_studio/server/

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
curl -s http://147.45.154.193:8000/
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

### Ручной мониторинг

```bash
# Логи в реальном времени
docker-compose logs -f api

# Использование ресурсов
docker stats

# Свободное место
df -h
```

### Автоматический мониторинг (рекомендуется)

На текущий момент автоматический мониторинг не настроен. Рекомендации:
- Добавить Docker health checks
- Настроить Prometheus + Grafana
- Добавить alerting при падении контейнера
