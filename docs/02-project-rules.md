# Правила проекта Interior Studio CRM

> Критические правила, нарушение которых приводит к багам. Обязательны к соблюдению.

## 1. `__init__.py` обязательны

Файлы `database/__init__.py`, `ui/__init__.py`, `utils/__init__.py` **ДОЛЖНЫ существовать**. Без них PyInstaller не найдёт модули при сборке exe.

```
database/
  __init__.py    # обязателен
  db_manager.py
ui/
  __init__.py    # обязателен
  ...
utils/
  __init__.py    # обязателен
  ...
```

## 2. Запрет emoji в UI

**НИКОГДА** не использовать emoji/Unicode символы (U+2600+) в `QLabel`, `QPushButton` и любых UI строках. Вместо emoji использовать SVG иконки через [IconLoader](../utils/icon_loader.py).

```python
# ЗАПРЕЩЕНО
label = QLabel("Успех! ✅")
btn = QPushButton("📁 Открыть")

# ПРАВИЛЬНО
from utils.icon_loader import IconLoader
icon = IconLoader.load('check.svg', size=18)
label = QLabel("Успех!")
btn = IconLoader.create_icon_button('folder', text='Открыть')
```

**Валидация:** Hook в [.claude/settings.local.json](../.claude/settings.local.json) автоматически проверяет код на emoji при каждом Edit/Write.

## 3. `resource_path()` для всех ресурсов

**ВСЕ** обращения к файлам ресурсов (иконки, логотип, шрифты) ДОЛЖНЫ использовать [resource_path()](../utils/resource_path.py). Без этого ресурсы не найдутся в exe (PyInstaller упаковывает в `sys._MEIPASS`).

```python
from utils.resource_path import resource_path

# ПРАВИЛЬНО
logo = QPixmap(resource_path('resources/logo.png'))
icon = QIcon(resource_path('resources/icons/edit.svg'))

# ЗАПРЕЩЕНО — не найдётся в exe
logo = QPixmap('resources/logo.png')
```

## 4. Рамки диалогов = 1px

Все диалоги с `FramelessWindowHint` ОБЯЗАНЫ иметь `border: 1px solid #E0E0E0;` — строго **1px**, не 2px, не 0px.

```python
border_frame.setStyleSheet("""
    QFrame#borderFrame {
        border: 1px solid #E0E0E0;    /* строго 1px! */
        border-radius: 10px;
        background: white;
    }
""")
```

## 5. Docker пересборка после изменений сервера

**`docker-compose restart api` НЕ РАБОТАЕТ** для применения изменений Python-кода. Нужна полная пересборка:

```bash
ssh timeweb
cd /opt/interior_studio
docker-compose down && docker-compose build --no-cache api && docker-compose up -d
```

## 6. Совместимость форматов API и клиента

API **ОБЯЗАН** возвращать те же ключи, что и [db_manager.py](../database/db_manager.py). Частые ошибки:

| Правильно | Неправильно |
|-----------|-------------|
| `total_orders` | `total_count` |
| `position` | отсутствует |
| `source` | отсутствует |
| `amount` | `final_amount` |

## 7. Порядок endpoints в FastAPI

Статические пути **ПЕРЕД** динамическими. Иначе FastAPI поймает динамический путь первым и вернёт 422.

```python
# ПРАВИЛЬНО
@app.get("/api/rates/template")      # статический — ПЕРВЫЙ
@app.get("/api/rates/{rate_id}")     # динамический — ВТОРОЙ

# НЕПРАВИЛЬНО — 422 ошибка
@app.get("/api/rates/{rate_id}")     # ловит "template" как rate_id
@app.get("/api/rates/template")      # никогда не срабатывает
```

## 8. Двухрежимная архитектура

**ВСЕ** функции ОБЯЗАНЫ работать в обоих режимах:
- **Автономный** (`MULTI_USER_MODE=False`): локальная SQLite БД
- **Сетевой** (`MULTI_USER_MODE=True`): клиент-сервер через REST API

## 9. Доступ к данным через DataAccess

Все CRUD операции в UI **ТОЛЬКО** через `self.data` ([DataAccess](../utils/data_access.py)), **НЕ** через `self.api_client`/`self.db` напрямую.

```python
# Инициализация в __init__ таба:
from utils.data_access import DataAccess
self.data = DataAccess(api_client=api_client)
self.db = self.data.db  # обратная совместимость для raw SQL

# ПРАВИЛЬНО — DataAccess сам делает API → fallback DB
clients = self.data.get_all_clients()
self.data.update_crm_card(card_id, updates)

# ЗАПРЕЩЕНО — прямой вызов
clients = self.api_client.get_clients()  # нет fallback!
```

**Исключение:** `self.db` допустим ТОЛЬКО для raw SQL запросов, у которых нет API-эквивалента.

## 10. Соглашения об именах

| Тип | Стиль | Примеры |
|-----|-------|---------|
| Переменные, функции | `snake_case` | `get_all_clients`, `contract_id` |
| Классы | `PascalCase` | `CRMTab`, `DraggableListWidget` |
| Константы | `UPPER_CASE` | `DATABASE_PATH`, `PROJECT_TYPES` |
| Кодировка | UTF-8 | `# -*- coding: utf-8 -*-` в начале файла |
| Строки UI | Русский | `"Новый заказ"`, `"Сохранить"` |

## 11. Кодировка

Каждый `.py` файл ОБЯЗАН начинаться с:
```python
# -*- coding: utf-8 -*-
```

## 12. Паттерн API-first с fallback

При добавлении нового `self.db.<write>()` в UI — **ВСЕГДА** оборачивать в API-first паттерн:

```python
if self.api_client:
    try:
        self.api_client.method(...)
    except Exception:
        self.db.method(...)  # fallback
else:
    self.db.method(...)  # offline
```

**Автоматический аудит:** [tests/test_db_api_sync_audit.py](../tests/test_db_api_sync_audit.py) проверяет все UI файлы на соответствие этому правилу.
