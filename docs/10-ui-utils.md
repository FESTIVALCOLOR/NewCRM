# UI и Utils

> Все утилиты, хелперы, валидаторы, кэш-менеджер, загрузчики.

## Карта утилит

```
utils/
├── api_client.py           # REST клиент (2300+ строк)
├── data_access.py          # Унифицированный доступ к данным (915 строк)
├── offline_manager.py      # Offline режим и очередь (797 строк)
├── sync_manager.py         # Real-time синхронизация (484 строки)
├── db_sync.py              # Синхронизация БД при входе (1731 строка)
├── yandex_disk.py          # Яндекс.Диск интеграция (200+ строк)
├── unified_styles.py       # Единая система стилей
├── icon_loader.py          # SVG иконки (76 строк)
├── resource_path.py        # Пути к ресурсам (33 строки)
├── calendar_helpers.py     # Помощники календаря (153 строки)
├── cache_manager.py        # Кэш превью (137 строк)
├── validators.py           # Валидаторы (275 строк)
├── table_settings.py       # Настройки таблиц (471 строка)
├── pdf_generator.py        # Генератор PDF
├── preview_generator.py    # Генератор превью
├── tooltip_fix.py          # Исправление tooltip
├── logger.py               # Логирование
├── password_utils.py       # Работа с паролями
├── db_security.py          # Безопасность БД
├── constants.py            # Константы
├── date_utils.py           # Работа с датами
├── message_helper.py       # Помощник сообщений
├── tab_helpers.py          # Помощники вкладок
└── update_manager.py       # Менеджер обновлений
```

## APIClient ([utils/api_client.py](../utils/api_client.py))

**2300+ строк** — REST HTTP клиент с retry, timeout, fallback.

### Основные параметры

| Константа | Значение | Назначение |
|-----------|----------|-----------|
| `DEFAULT_TIMEOUT` | 10 сек | Чтение (GET) |
| `WRITE_TIMEOUT` | 15 сек | Запись (POST/PUT/PATCH/DELETE) |
| `FIRST_REQUEST_TIMEOUT` | 10 сек | TCP cold start |
| `MAX_RETRIES` | 2 | Количество попыток |
| `OFFLINE_CACHE_DURATION` | 10 сек | Кэш offline статуса |

### Ключевые методы

```python
class APIClient:
    # Базовые
    _request(method, path, **kwargs)    # универсальный запрос
    _is_recently_offline() -> bool       # проверка кэша offline
    _mark_offline()                      # пометка offline
    reset_offline_cache()                # сброс кэша
    force_online_check() -> bool         # принудительная проверка
    set_offline_mode(offline: bool)      # установка режима

    # Авторизация
    authenticate(login, password)        # вход
    get_current_user()                   # текущий пользователь

    # CRUD для каждой сущности
    get_clients() / create_client() / update_client() / delete_client()
    get_contracts() / create_contract() / update_contract() / delete_contract()
    # ... аналогично для всех сущностей
```

### Кастомные исключения

```python
APIError               # базовая ошибка
APITimeoutError        # таймаут
APIConnectionError     # нет соединения
APIAuthError           # 401/403
APIResponseError       # неожиданный ответ
```

## DataAccess ([utils/data_access.py](../utils/data_access.py))

**915 строк** — слой абстракции API/DB с fallback и offline очередью.

### Сигналы (PyQt5)

```python
connection_status_changed = pyqtSignal(bool)      # online/offline
operation_queued = pyqtSignal(str, str)            # entity_type, operation
pending_operations_changed = pyqtSignal(int)       # кол-во в очереди
```

### Паттерн использования

```python
# В табе
self.data = DataAccess(api_client=api_client)
clients = self.data.get_all_clients()              # API → fallback DB
self.data.update_crm_card(card_id, updates)        # API → fallback DB + queue

# Raw SQL (без API)
result = self.data.execute_raw_query("SELECT ...")
```

## OfflineManager ([utils/offline_manager.py](../utils/offline_manager.py))

**797 строк** — очередь операций, мониторинг соединения, синхронизация.

### Состояния

```python
class ConnectionStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    CONNECTING = "connecting"
    SYNCING = "syncing"
```

### Таблица БД: offline_operations_queue

```sql
id, operation_type, entity_type, entity_id, data (JSON),
status, created_at, synced_at, error_message, retry_count, server_entity_id
```

### Интервалы

| Параметр | Значение |
|----------|----------|
| CHECK_INTERVAL | 60 сек |
| PING_TIMEOUT | 2 сек |
| SYNC_TIMEOUT | 10 сек |
| MAX_SYNC_ERRORS | 3 |

## SyncManager ([utils/sync_manager.py](../utils/sync_manager.py))

**484 строки** — real-time синхронизация, блокировки, heartbeat.

### Сигналы

```python
data_updated = pyqtSignal(str, list)          # тип сущности, данные
clients_updated = pyqtSignal(list)             # клиенты обновлены
contracts_updated = pyqtSignal(list)           # договоры обновлены
record_locked = pyqtSignal(str, int, str)      # тип, id, кем заблокировано
record_unlocked = pyqtSignal(str, int)         # тип, id
online_users_updated = pyqtSignal(list)        # онлайн-пользователи
```

### Блокировки записей

```python
# Контекстный менеджер
with sync_manager.lock_record('contract', contract_id):
    # редактирование — запись заблокирована для других
    pass
# блокировка автоматически снята

# Проверка блокировки
if sync_manager.is_record_locked('contract', 42):
    show_warning("Запись редактируется другим пользователем")
```

## DatabaseSynchronizer ([utils/db_sync.py](../utils/db_sync.py))

**1731 строка** — полная синхронизация при входе (14 этапов).

### Использование

```python
from utils.db_sync import sync_on_login, verify_data_integrity

# При входе
sync_on_login(api_client, db_manager, progress_callback)

# Проверка целостности
verify_data_integrity(api_client, db_manager)
```

## Вспомогательные утилиты

### CacheManager ([utils/cache_manager.py](../utils/cache_manager.py))

```python
CacheManager.get_cache_dir()                # путь к кэшу
CacheManager.clear_cache()                  # очистить весь кэш
CacheManager.clear_contract_cache(id)       # кэш договора
CacheManager.get_cache_size_mb()            # размер в МБ
CacheManager.get_cache_files_count()        # кол-во файлов
```

### Validators ([utils/validators.py](../utils/validators.py))

```python
validate_phone(phone)          # +7 (XXX) XXX-XX-XX
validate_email(email)          # стандартный email
validate_date(date_str)        # формат даты
validate_required(value, name) # не пустое
validate_inn(inn)              # 10 или 12 цифр
validate_passport(passport)    # XXXX XXXXXX
validate_contract_number(num)  # XX/XXXX
sanitize_string(value)         # удаление HTML, экранирование SQL
format_phone(phone)            # форматирование номера
```

### CalendarHelpers ([utils/calendar_helpers.py](../utils/calendar_helpers.py))

```python
add_working_days(start_date_str, working_days)  # +N рабочих дней
add_today_button_to_dateedit(date_edit)          # кнопка "Сегодня"
```

### TableSettings ([utils/table_settings.py](../utils/table_settings.py))

```python
# Пропорциональная таблица
table = ProportionalResizeTable()
table.setup_proportional_resize(
    column_ratios={0: 3, 1: 2, 2: 1},
    fixed_columns={3: 80},
    min_width=50
)

# Сохранение/загрузка сортировки
TableSettings.save_sort_order('contracts', column=2, order=Qt.AscendingOrder)
TableSettings.get_sort_order('contracts')  # → (2, Qt.AscendingOrder)

# Коллапс колонок Kanban
TableSettings.save_column_collapsed_state('individual', 'Новый заказ', True)
```

### ResourcePath ([utils/resource_path.py](../utils/resource_path.py))

```python
from utils.resource_path import resource_path

# Для PyInstaller: sys._MEIPASS + relative_path
# Для разработки: os.path.abspath(relative_path)
path = resource_path('resources/icons/edit.svg')
```

## Схема зависимостей утилит

```
DataAccess
  ├── APIClient (optional, для сетевого режима)
  ├── DatabaseManager (always, для fallback)
  └── OfflineManager (lazy import)

OfflineManager
  ├── APIClient (set_api_client)
  ├── YandexDiskManager (для папок)
  └── config.YANDEX_DISK_TOKEN

SyncManager
  ├── APIClient (sync + heartbeat)
  └── DatabaseManager (save locally)

DatabaseSynchronizer
  ├── DatabaseManager
  ├── APIClient
  └── logger

YandexDiskManager (singleton)
  └── requests + urllib3
```
