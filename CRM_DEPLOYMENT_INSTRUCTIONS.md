# Инструкции по развертыванию CRM интеграции на сервере

## Шаг 1: Создание таблиц в PostgreSQL

Подключиться к серверу и выполнить SQL миграцию:

```bash
ssh root@147.45.154.193

# Войти в контейнер PostgreSQL
docker exec -it interior_studio-db-1 psql -U interior_admin -d interior_studio_db

# Выполнить SQL из файла server_crm_migration.sql
# (Скопировать содержимое и вставить в psql)

# Проверить создание таблиц:
\d crm_cards
\d stage_executors

# Выйти
\q
exit
```

## Шаг 2: Добавить модели в server/database.py

Файл находится на сервере: `/opt/interior_studio/server/database.py`

### 2.1 Добавить импорты в начало файла (если не хватает):
```python
from sqlalchemy.orm import relationship
```

### 2.2 Добавить модели CRMCard и StageExecutor

Вставить содержимое файла `server_crm_models.py` в конец файла database.py, ПОСЛЕ модели Contract.

### 2.3 Обновить модель Contract

Добавить relationship в модель Contract:
```python
class Contract(Base):
    # ... existing fields ...

    # Добавить в конец:
    crm_card = relationship("CRMCard", back_populates="contract", uselist=False)
```

## Шаг 3: Добавить схемы в server/schemas.py

Файл находится на сервере: `/opt/interior_studio/server/schemas.py`

Вставить содержимое файла `server_crm_schemas.py` В КОНЕЦ файла schemas.py.

## Шаг 4: Добавить роуты в server/main.py

Файл находится на сервере: `/opt/interior_studio/server/main.py`

### 4.1 Добавить импорты в начало файла (после существующих импортов):
```python
from database import CRMCard, StageExecutor
from schemas import (
    CRMCardResponse, CRMCardUpdate, ColumnMoveRequest,
    StageExecutorCreate, StageExecutorUpdate
)
```

### 4.2 Вставить роуты

Вставить содержимое файла `server_crm_routes.py` в конец файла main.py, ПОСЛЕ всех существующих роутов.

## Шаг 5: Пересобрать и перезапустить Docker контейнер

```bash
ssh root@147.45.154.193

cd /opt/interior_studio

# Пересобрать образ API
docker-compose build api

# Перезапустить контейнеры
docker-compose down
docker-compose up -d

# Проверить логи
docker-compose logs -f api

# Проверить, что API работает
curl -k https://147.45.154.193
```

## Шаг 6: Тестирование API

### 6.1 Тест через curl (на сервере или локально):

```bash
# Логин
TOKEN=$(curl -k -X POST https://147.45.154.193/api/auth/login \
  -d "username=admin&password=admin123" \
  | jq -r '.access_token')

# Получить CRM карточки
curl -k -H "Authorization: Bearer $TOKEN" \
  "https://147.45.154.193/api/crm/cards?project_type=Индивидуальный"
```

### 6.2 Тест через Python клиент (локально):

```bash
cd "d:\New CRM\interior_studio"

.venv\Scripts\python.exe -c "
from utils.api_client import APIClient
client = APIClient('https://147.45.154.193')
result = client.login('admin', 'admin123')
print('[OK] Login successful')

# Тест получения карточек
cards = client.get_crm_cards('Индивидуальный')
print(f'[OK] Got {len(cards)} CRM cards')
"
```

## Шаг 7: Миграция данных (опционально)

Если нужно перенести существующие CRM карточки из локальной БД на сервер:

```bash
# Создать скрипт миграции (аналогично migrate_to_server.py)
.venv\Scripts\python.exe migrate_crm_to_server.py
```

## Файлы для копирования на сервер

1. `server_crm_migration.sql` - SQL миграция
2. `server_crm_models.py` - Модели SQLAlchemy (добавить в database.py)
3. `server_crm_schemas.py` - Pydantic схемы (добавить в schemas.py)
4. `server_crm_routes.py` - API роуты (добавить в main.py)

## Способы копирования файлов на сервер

### Вариант 1: Через scp (если доступен)
```bash
scp server_crm_migration.sql root@147.45.154.193:/tmp/
```

### Вариант 2: Через редактирование на сервере
```bash
ssh root@147.45.154.193
nano /opt/interior_studio/server/database.py
# Вставить содержимое вручную
```

### Вариант 3: Через git (рекомендуется)
```bash
# На локальной машине
git add server/database.py server/schemas.py server/main.py
git commit -m "Add CRM API integration"
git push

# На сервере
ssh root@147.45.154.193
cd /opt/interior_studio
git pull
docker-compose build api
docker-compose up -d
```

## Проверка успешности развертывания

✅ Таблицы crm_cards и stage_executors созданы в PostgreSQL
✅ Модели добавлены в database.py
✅ Схемы добавлены в schemas.py
✅ Роуты добавлены в main.py
✅ Docker контейнер пересобран и перезапущен
✅ API отвечает на GET /api/crm/cards
✅ Python клиент может получить карточки

## Troubleshooting

### Ошибка: "no module named 'CRMCard'"
- Проверьте, что модели добавлены в database.py
- Проверьте, что импорты обновлены в main.py

### Ошибка: "table crm_cards does not exist"
- Выполните SQL миграцию в PostgreSQL

### Ошибка: HTTP 500 при запросе
- Проверьте логи: `docker-compose logs -f api`
- Возможно, нужно добавить недостающие импорты

### Docker не пересобирается
- Используйте `docker-compose build --no-cache api`
- Или удалите образ: `docker rmi interior_studio-api`

---

**Следующий шаг:** После успешного развертывания на сервере, интегрировать UI (ui/crm_tab.py)
