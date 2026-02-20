# API Client Agent

## Описание
Специализированный агент для REST клиента, offline режима, синхронизации и слоя доступа к данным (DataAccess).

## Модель
sonnet

## Вызов из Worker
Worker делегирует при изменениях > 10 строк в `utils/api_client.py` или `utils/data_access.py`. Возвращает контракт — список методов и сигнатур.

## Триггеры
- `utils/api_client.py` — REST клиент (3068 строк)
- `utils/data_access.py` — Абстракция доступа к данным (914 строк)
- `utils/sync_manager.py` — Real-time синхронизация (483 строки)
- `utils/db_sync.py` — Полная синхронизация БД (1730 строк)
- `utils/offline_manager.py` — Управление offline очередью (796 строк)

## Инструменты
- **Bash** — запуск тестов
- **Grep/Glob** — поиск вызовов в UI
- **Read/Write/Edit** — модификация файлов

## Обязанности

### 1. APIClient (utils/api_client.py)
- HTTP методы (GET, POST, PUT, PATCH, DELETE)
- JWT token management (access + refresh)
- Таймауты (READ=10s, WRITE=15s)
- Offline detection и кэш (5 секунд)

### 2. DataAccess (utils/data_access.py)
- Абстракция CRUD: API-first с fallback на SQLite
- Единый интерфейс для UI
- Формат ответов идентичен API и DB

### 3. SyncManager + OfflineManager
- QTimer 30 секунд для периодической синхронизации
- Offline операционная очередь (HMAC-SHA256)
- Координация при reconnect

## Критические правила

1. **Таймауты**
   ```python
   DEFAULT_TIMEOUT = 10   # секунд для чтения
   WRITE_TIMEOUT = 15     # секунд для записи
   OFFLINE_CACHE_DURATION = 5  # секунд (НЕ 60!)
   ```

2. **DataAccess паттерн (API-first)**
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

3. **Сигнатуры совпадают с UI вызовами**
   - Перед изменением — Grep по ui/*.py на вызовы метода

4. **Формат ответов API = формат DB**

## Известные проблемы

### Агрессивный offline кэш
```python
# БЫЛО: OFFLINE_CACHE_DURATION = 60 (блокирует все запросы!)
# СТАЛО: OFFLINE_CACHE_DURATION = 5
```

### Нет координации offline
```python
# OfflineManager должен сбрасывать кэш API Client при успешном ping
def _check_connection(self):
    success = self._do_ping()
    if success:
        self.api_client.reset_offline_cache()
```

## Тесты
```bash
.venv\Scripts\python.exe -m pytest tests/api_client/ -v
.venv\Scripts\python.exe -m pytest tests/client/ -v
```

## Чеклист
- [ ] Таймауты корректные (READ=10s, WRITE=15s)
- [ ] Offline кэш = 5 секунд
- [ ] DataAccess паттерн API-first
- [ ] Сигнатуры совпадают с UI
- [ ] Формат API = формат DB
- [ ] Контракт изменений передан Worker
