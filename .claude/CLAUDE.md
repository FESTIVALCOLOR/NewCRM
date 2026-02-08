# Interior Studio CRM

**Python:** 3.14.0 (клиент), 3.11 (сервер) | **PyInstaller:** 6.17.0
**Архитектура:** PyQt5 Desktop клиент + FastAPI сервер + PostgreSQL

## Структура

```
main.py                    # Точка входа клиента
config.py                  # API_BASE_URL, APP_VERSION
InteriorStudio.spec        # PyInstaller конфигурация
database/db_manager.py     # Локальная SQLite БД (fallback)
ui/                        # PyQt5 модули (crm_tab.py 17K+ строк)
utils/api_client.py        # HTTP клиент для API
utils/offline_manager.py   # Offline режим и очередь синхронизации
utils/resource_path.py     # Пути к ресурсам для exe
server/                    # FastAPI (НЕ входит в exe)
  main.py                  # 5800+ строк, 144 endpoints
  database.py              # SQLAlchemy модели
  schemas.py               # Pydantic схемы
  auth.py                  # JWT (bcrypt==3.2.2)
```

## Критические правила

### 1. __init__.py обязательны
`database/__init__.py`, `ui/__init__.py`, `utils/__init__.py` -- без них PyInstaller не найдет модули.

### 2. Запрет emoji в UI
Никогда не использовать emoji в QLabel, QPushButton и любых UI строках. Использовать SVG иконки через IconLoader.

### 3. resource_path() для всех ресурсов
```python
from utils.resource_path import resource_path
logo = QPixmap(resource_path('resources/logo.png'))
```
Без resource_path() ресурсы не найдутся в exe.

### 4. Рамки диалогов = 1px
Все диалоги с FramelessWindowHint: `border: 1px solid #E0E0E0;` -- строго 1px.

### 5. Docker пересборка после изменений сервера
```bash
ssh root@147.45.154.193
cd /opt/interior_studio
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
```
Простой restart НЕ перезагружает Python модули.

### 6. Совместимость форматов API и клиента
API должен возвращать те же ключи, что и db_manager.py. Проверять: `total_orders` (не `total_count`), `position`, `source`, `amount`.

### 7. Порядок endpoints в FastAPI
Статические пути ПЕРЕД динамическими: `/api/rates/template` ПЕРЕД `/api/rates/{rate_id}`.

## Сервер

- **IP:** 147.45.154.193 | **API порт:** 8000 (рекомендуется)
- **Путь:** /opt/interior_studio/
- **Docker:** postgres (5432), api (8000), nginx (80/443)
- **БД:** PostgreSQL, user=crm_user, db=interior_studio_crm

## Клиент

- **API:** `API_BASE_URL = "http://147.45.154.193:8000"` (config.py)
- **Запуск:** `.venv\Scripts\python.exe main.py`
- **Сборка:** `.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm`

## Таймауты (utils/api_client.py)

| Константа | Значение | Назначение |
|-----------|----------|------------|
| DEFAULT_TIMEOUT | 10 сек | Чтение |
| WRITE_TIMEOUT | 15 сек | Запись |
| OFFLINE_CACHE_DURATION | 3 сек | Кеш offline статуса |
| SYNC_TIMEOUT | 10 сек | Синхронизация offline очереди |

## Offline режим

1. Приложение пытается API -> при ошибке fallback на локальную SQLite БД
2. Изменения в offline добавляются в очередь (offline_manager.py)
3. При восстановлении соединения очередь синхронизируется
4. Поддерживаются: client, contract, crm_card, supervision_card, employee, payment, yandex_folder

### Паттерн offline в UI
```python
if self.api_client:
    try:
        data = self.api_client.get_something()
    except Exception as e:
        data = self.db.get_something()  # fallback
else:
    data = self.db.get_something()
```

## Платежи -- ключевые правила

1. CRM платежи имеют `crm_card_id`, надзора -- `supervision_card_id`
2. `report_month = NULL` = "В работе"
3. При переназначении: старый платеж `reassigned=True`, создается новый
4. Расчет суммы всегда через `calculate_payment_amount()` endpoint
5. При поиске старых платежей проверять `reassigned` флаг
6. Тарифы надзора: `role` + `rate_per_m2` (не executor_rate/manager_rate)

## Добавление нового endpoint -- чеклист

1. Добавить endpoint в server/main.py (статические пути ПЕРЕД динамическими)
2. Добавить Pydantic схему в server/schemas.py
3. Добавить метод в utils/api_client.py (сигнатура = как вызывается в UI)
4. Добавить вызов в UI с try/except и fallback на db_manager
5. Пересобрать Docker на сервере
