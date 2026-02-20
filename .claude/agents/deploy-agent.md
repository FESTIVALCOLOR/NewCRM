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

## Чеклист
- [ ] Pre-checks пройдены (синтаксис, совместимость, безопасность)
- [ ] Backup создан
- [ ] Деплой выполнен
- [ ] Docker rebuild (не restart)
- [ ] Верификация пройдена
- [ ] Smoke test пройден
