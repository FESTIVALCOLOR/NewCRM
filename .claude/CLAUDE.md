# Interior Studio CRM

**Python:** 3.14.0 (клиент), 3.11 (сервер) | **PyInstaller:** 6.17.0
**Архитектура:** PyQt5 Desktop клиент + FastAPI сервер + PostgreSQL

## Структура проекта

```
main.py                    # Точка входа клиента
config.py                  # API_BASE_URL, APP_VERSION, ROLES, POSITIONS
InteriorStudio.spec        # PyInstaller конфигурация
database/
  db_manager.py            # Локальная SQLite БД (fallback), 4400+ строк, 50+ миграций
ui/                        # PyQt5 модули
  main_window.py           # Главное окно с табами
  login_window.py          # Окно входа (API + локальный режим)
  crm_tab.py               # CRM Kanban доска (17K+ строк)
  crm_supervision_tab.py   # Авторский надзор
  clients_tab.py           # Клиенты
  contracts_tab.py         # Договоры
  salaries_tab.py          # Зарплаты
  employees_tab.py         # Сотрудники
  employee_reports_tab.py  # Отчеты сотрудников
  dashboard_widget.py      # Дашборд
  dashboards.py            # Виджеты дашборда
  rates_dialog.py          # Диалог тарифов
  custom_title_bar.py      # Кастомный заголовок окна
  custom_combobox.py       # Кастомный ComboBox
  custom_dateedit.py       # Кастомный DateEdit
  custom_message_box.py    # Кастомное MessageBox
  file_gallery_widget.py   # Галерея файлов
  file_list_widget.py      # Список файлов
  file_preview_widget.py   # Предпросмотр файлов
  variation_gallery_widget.py # Галерея вариаций
  flow_layout.py           # Flow Layout
utils/
  api_client.py            # HTTP клиент для API (2300+ строк)
  offline_manager.py       # Offline режим и очередь синхронизации
  sync_manager.py          # Real-time синхронизация (QTimer 5 сек)
  resource_path.py         # Пути к ресурсам для exe
  unified_styles.py        # Единая система стилей
  icon_loader.py           # Загрузчик SVG иконок
  validators.py            # Валидаторы
  table_settings.py        # Настройки таблиц
  yandex_disk.py           # Интеграция с Яндекс.Диском
  calendar_helpers.py      # Помощники календаря
  data_access.py           # Слой доступа к данным
  db_sync.py               # Синхронизация БД
  pdf_generator.py         # Генератор PDF
  preview_generator.py     # Генератор превью
  tooltip_fix.py           # Исправление tooltip
  logger.py                # Логирование
  password_utils.py        # Работа с паролями
  db_security.py           # Безопасность БД
  cache_manager.py         # Менеджер кэша
  constants.py             # Константы
  date_utils.py            # Работа с датами
  message_helper.py        # Помощник сообщений
  tab_helpers.py           # Помощники вкладок
  update_manager.py        # Менеджер обновлений
server/                    # FastAPI (НЕ входит в exe)
  main.py                  # 5800+ строк, 144 endpoints
  database.py              # SQLAlchemy модели
  schemas.py               # Pydantic схемы
  auth.py                  # JWT (bcrypt==3.2.2)
resources/
  icons/                   # 50+ SVG иконок
  logo.png                 # Логотип
  icon.ico                 # Иконка приложения
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

### 8. Двухрежимная архитектура
Все функции должны работать в обоих режимах:
- **Автономный** (`MULTI_USER_MODE=False`): локальная SQLite БД
- **Сетевой** (`MULTI_USER_MODE=True`): клиент-сервер через REST API

```python
# Паттерн offline в UI
if self.api_client:
    try:
        data = self.api_client.get_something()
    except Exception as e:
        data = self.db.get_something()  # fallback
else:
    data = self.db.get_something()
```

## Двухрежимная архитектура

### Сетевой режим (Data Flow)
```
LoginWindow -> APIClient.authenticate() -> (токен + сотрудник)
    -> MainWindow + SyncManager (QTimer каждые 5 сек)
    -> Табы работают через APIClient (+ локальный кэш)
    -> При изменении: PUT/POST в API, обновление кэша, emit сигнала
```

### Автономный режим (Data Flow)
```
LoginWindow -> DatabaseManager.verify_credentials() (SQLite)
    -> MainWindow (без SyncManager)
    -> Табы работают напрямую с DatabaseManager
```

### Ключевые компоненты

| Компонент | Файл | Строк | Назначение |
|-----------|------|-------|-----------|
| API Client | utils/api_client.py | 2300+ | REST клиент, retry/timeout/fallback, JWT |
| Sync Manager | utils/sync_manager.py | - | QTimer синхронизация (5 сек), сигналы для UI |
| CRM Kanban | ui/crm_tab.py | 17K+ | Drag & drop доски, этапы согласования |
| DB Manager | database/db_manager.py | 4400+ | SQLite + 50+ миграций on-the-fly |
| Server API | server/main.py | 5800+ | 144 endpoints FastAPI |

## Сервер

- **IP:** 147.45.154.193 | **API порт:** 8000
- **Путь:** /opt/interior_studio/
- **Docker:** postgres (5432), api (8000), nginx (80/443)
- **БД:** PostgreSQL, user=crm_user, db=interior_studio_crm
- **Учетная запись:** admin / admin123

### Управление сервером
```bash
ssh root@147.45.154.193
cd /opt/interior_studio

# Логи API
docker-compose logs -f api

# Перезапуск (НЕ применяет изменения кода!)
docker-compose restart api

# Полная пересборка (применяет изменения кода)
docker-compose down && docker-compose build --no-cache api && docker-compose up -d

# Статус
docker-compose ps

# Подключение к БД
docker-compose exec postgres psql -U crm_user -d interior_studio_crm
```

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

## Платежи -- ключевые правила

1. CRM платежи имеют `crm_card_id`, надзора -- `supervision_card_id`
2. `report_month = NULL` = "В работе"
3. При переназначении: старый платеж `reassigned=True`, создается новый
4. Расчет суммы всегда через `calculate_payment_amount()` endpoint
5. При поиске старых платежей проверять `reassigned` флаг
6. Тарифы надзора: `role` + `rate_per_m2` (не executor_rate/manager_rate)

## Схема базы данных

### employees -- Сотрудники
```sql
id, full_name, phone, email, address, birth_date, status,
position, secondary_position, department, login, password,
role, created_at
```

### clients -- Клиенты
```sql
id, client_type, full_name, phone, email,
passport_series, passport_number, registration_address,
organization_name, inn, ogrn, created_at
```

### contracts -- Договоры
```sql
id, client_id, project_type, agent_type, city,
contract_number, contract_date, address, area,
total_amount, advance_payment, additional_payment, third_payment,
contract_period, status, termination_reason, created_at
```

### crm_cards -- Проекты в Kanban
```sql
id, contract_id, column_name, deadline, tags,
is_approved, approval_stages, approval_deadline,
senior_manager_id, sdp_id, gap_id, manager_id, surveyor_id,
order_position, created_at
```

### supervision_cards -- Авторский надзор
```sql
id, contract_id, column_name, deadline, tags,
senior_manager_id, dan_id, dan_completed,
is_paused, pause_reason, paused_at, created_at
```

### salaries -- Зарплаты
```sql
id, contract_id, employee_id, payment_type, stage_name,
amount, advance_payment, report_month, created_at
```

## Kanban статусы

### Индивидуальные проекты (6 колонок)
1. Новый заказ
2. В ожидании
3. Стадия 1: планировочные решения
4. Стадия 2: концепция дизайна
5. Стадия 3: рабочие чертежи
6. Выполненный проект

### Шаблонные проекты (5 колонок)
1. Новый заказ
2. В ожидании
3. Стадия 1: планировочные решения
4. Стадия 2: рабочие чертежи
5. Выполненный проект

## Роли и права доступа

| Роль | Табы | Может редактировать |
|------|------|---------------------|
| Руководитель студии | Все | Да |
| Старший менеджер проектов | Все | Да |
| СДП / ГАП | СРМ, Статистика, Сотрудники | Да |
| Дизайнер / Чертежник / Замерщик | СРМ (просмотр) | Нет |
| ДАН | СРМ надзора | Нет |

### Должности и отделы
- **Административный:** Руководитель студии, Старший менеджер проектов, СДП, ГАП
- **Проектный:** Дизайнер, Чертежник
- **Исполнительный:** Менеджер, ДАН, Замерщик

### Константы (config.py)
```python
PROJECT_TYPES = ['Индивидуальный', 'Шаблонный']
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
CITIES = ['СПБ', 'МСК', 'ВН']
PAYMENT_TYPES = ['Аванс', 'Основной платеж', 'Оплата согласования']
```

## Паттерны UI

### CustomTitleBar
```python
from ui.custom_title_bar import CustomTitleBar
title_bar = CustomTitleBar(self, "Заголовок", simple_mode=False)
# simple_mode=True для диалогов, False для основных окон
```

### Кастомные диалоги
```python
from ui.custom_message_box import CustomMessageBox
CustomMessageBox.info(self, "Успех", "Данные сохранены")
```

### SVG иконки
```python
from utils.icon_loader import IconLoader
icon = IconLoader.load('search.svg', size=24)
btn = IconLoader.create_icon_button('save', text='Сохранить', icon_size=20)
```

### Frameless окна
Все окна используют `Qt.FramelessWindowHint` + `CustomTitleBar`.

## Интеграция с Яндекс.Диском

### Структура папок
```
АРХИВ ПРОЕКТОВ/
  ФЕСТИВАЛЬ/
    Индивидуальные/ (СПБ/, МСК/, ВН/)
    Шаблонные/ (СПБ/, МСК/, ВН/)
    Авторские надзоры/ (СПБ/, МСК/, ВН/)
  ПЕТРОВИЧ/
    (аналогично)
```

### Функции
- При создании договора -- автоматически создается папка
- При изменении типа/города/адреса -- папка перемещается
- При удалении договора -- папка удаляется

### Получение OAuth токена
1. https://oauth.yandex.ru/ -> Зарегистрировать приложение
2. Права: Яндекс.Диск REST API (Запись + Чтение)
3. Redirect URI: `https://oauth.yandex.ru/verification_code`
4. Перейти: `https://oauth.yandex.ru/authorize?response_type=token&client_id=YOUR_CLIENT_ID`
5. Скопировать токен из URL после `#access_token=`
6. Установить: `setx YANDEX_DISK_TOKEN "токен"` или в config.py

## Паттерны Database

### Миграции (on-the-fly в __init__)
```python
cursor.execute("PRAGMA table_info(table_name)")
columns = [col[1] for col in cursor.fetchall()]
if 'new_column' not in columns:
    cursor.execute('ALTER TABLE table_name ADD COLUMN new_column TYPE DEFAULT value')
```

### JSON в SQLite
```python
import json
stages = json.loads(db_data['approval_stages'])  # чтение
json_str = json.dumps(stages)                     # запись
```

## Добавление нового endpoint -- чеклист

1. Добавить endpoint в server/main.py (статические пути ПЕРЕД динамическими)
2. Добавить Pydantic схему в server/schemas.py
3. Добавить метод в utils/api_client.py (сигнатура = как вызывается в UI)
4. Добавить вызов в UI с try/except и fallback на db_manager
5. Пересобрать Docker на сервере

## Добавление нового UI модуля

1. Создать файл `ui/new_module.py`
2. Добавить `from utils.resource_path import resource_path`
3. Поддержать оба режима (MULTI_USER_MODE True/False)
4. Добавить в `InteriorStudio.spec` -> `hiddenimports`
5. Зарегистрировать в `config.ROLES` для нужных ролей

## Добавление новой таблицы БД

1. Создать миграцию в `database/db_manager.py` (CREATE TABLE IF NOT EXISTS)
2. Вызвать миграцию в `__init__()` DatabaseManager
3. Создать CRUD методы в DatabaseManager
4. Если нужен API: добавить endpoints в server/main.py

## Соглашения об именах

- **Переменные БД/Python:** `snake_case`
- **Классы PyQt:** `PascalCase` (CRMTab, DraggableListWidget)
- **Константы:** `UPPER_CASE` (DATABASE_PATH, PROJECT_TYPES)
- **Кодировка:** `# -*- coding: utf-8 -*-` в начале каждого файла
- **Все строки UI на русском языке**

## GitHub

- **Репозиторий:** git@github.com:FESTIVALCOLOR/NewCRM.git
- **Ветка:** main
