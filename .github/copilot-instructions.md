# Инструкции для AI-агентов: Interior Studio CRM

⚠️ **КРИТИЧЕСКОЕ ПОНИМАНИЕ**: Этот проект поддерживает ДВУХРЕЖИМНУЮ АРХИТЕКТУРУ. Все функции должны работать как в локальном режиме (SQLite), так и в API режиме (клиент-сервер). Всегда проверяйте оба режима при изменении функциональности!

## Обзор проекта

**Interior Studio** — многопользовательская CRM система на PyQt5 + FastAPI, управляющая интерьерной студией. **КРИТИЧНО**: проект работает в двух режимах:
- **Автономный** (`MULTI_USER_MODE=False`): локальная SQLite БД
- **Сетевой** (`MULTI_USER_MODE=True`): клиент-серверное взаимодействие через REST API

### Основные модули
- **`ui/`** — PyQt5 GUI (10+ табов, frameless окна, SVG иконки)
- **`database/`** — SQLite менеджер + миграции on-the-fly (4398 строк db_manager.py)
- **`utils/`** — APIClient, SyncManager (real-time синхронизация), PDF, Yandex Disk
- **`server/`** — FastAPI сервер (не включается в exe) для многопользовательского режима
- **`config.py`** — переключатель режимов, роли, позиции, API URL

## Критическая архитектура

### Двухрежимная работа
```python
# config.py
MULTI_USER_MODE = True  # False = локальная БД, True = API сервер
API_BASE_URL = "http://147.45.154.193:8000"  # Продакшн сервер
SYNC_INTERVAL = 5  # Секунды между проверками изменений
```

### Data Flow в сетевом режиме
```
LoginWindow → APIClient.authenticate() → (успех: токен + сотрудник)
           ↓
MainWindow + SyncManager (QTimer каждые 5 сек)
           ↓
Табы работают через APIClient (+ локальный кэш в utils/cache_manager.py)
           ↓
При изменении: PUT/POST в API, обновление кэша, emit сигнала в MainWindow
```

### Data Flow в локальном режиме
```
LoginWindow → DatabaseManager.verify_credentials() (прямая SQLite проверка)
           ↓
MainWindow (без SyncManager)
           ↓
Табы работают напрямую с DatabaseManager (SQL-запросы)
```

### Ключевые компоненты

| Компонент | Файл | Назначение |
|-----------|------|-----------|
| **API Client** | `utils/api_client.py` (2320 строк) | REST клиент с retry/timeout/fallback логикой + JWT токены |
| **Sync Manager** | `utils/sync_manager.py` | QTimer-based синхронизация (5 сек), сигналы для UI обновлений |
| **CRM Kanban** | `ui/crm_tab.py` | Drag & drop доски, drag → APIClient.update_card() → сигнал → UI |
| **DB Manager** | `database/db_manager.py` (4398 строк) | SQLite + 50+ миграций on-the-fly, нижний уровень доступа |
| **Отчеты** | `ui/reports_tab.py` | PDF экспорт, экспорт на Yandex Disk |

## Разработка

### Критические правила PyInstaller
⚠️ **ВСЕ папки с Python-модулями должны содержать `__init__.py`:**
- `database/__init__.py` (даже пустой!)
- `ui/__init__.py`
- `utils/__init__.py`

Без этих файлов PyInstaller НЕ найдет модули при сборке exe!

### Критические ограничения UI
- ⚠️ **НИКОГДА не используйте emoji в интерфейсе**: ❌ `QLabel('⚠️ ВНИМАНИЕ')` — используйте Unicode символы или иконки из SVG
- ✅ **Frameless окна везде**: `self.setWindowFlags(Qt.FramelessWindowHint)` обязателен
- ✅ **CustomTitleBar обязателен**: вместо стандартной рамки окна
- ✅ **UTF-8 кодировка**: `# -*- coding: utf-8 -*-` в начале каждого файла

### Двухрежимная разработка

**Локальный режим** (разработка):
```python
# config.py: MULTI_USER_MODE = False
# Работает с SQLite напрямую
db = DatabaseManager()
employees = db.get_employees()
```

**API режим** (с сервером):
```python
# config.py: MULTI_USER_MODE = True
# LoginWindow → APIClient.authenticate() + токен
# Табы используют api_client.get_employees() через SyncManager
```

**КРИТИЧЕСКИ ВАЖНО**: При разработке нового таба ВСЕГДА проверяйте оба режима!

### Роли пользователей (`config.ROLES`)
- **Руководитель студии** — полный доступ
- **СДП / ГАП** — СРМ + статистика + сотрудники
- **Дизайнер / Чертежник / Замерщик** — СРМ только просмотр
- **ДАН** — только авторский надзор

Каждой роли соответствуют:
- `tabs[]` — список доступных табов
- `can_assign[]` — кому может назначать задачи
- `can_edit` — может ли редактировать данные

### Паттерны UI

#### 1. Кастомный Title Bar
```python
from ui.custom_title_bar import CustomTitleBar
title_bar = CustomTitleBar(self, "Заголовок", simple_mode=False)
layout.addWidget(title_bar)
```
- `simple_mode=True` для диалогов (только закрытие)
- `simple_mode=False` для основных окон (минимизация, развертывание и т.д.)

#### 2. Кастомные диалоги
```python
from ui.custom_message_box import CustomMessageBox, CustomQuestionBox
CustomMessageBox.info(self, "Успех", "Данные сохранены")
```
- Заменяют стандартные QMessageBox
- Поддерживают кастомные стили (см. `resources/styles.qss`)

#### 3. Drag & Drop в CRM Tab
```python
# Класс DraggableListWidget с сигналом:
item_dropped.emit(card_id, source_column, target_column)
# При перемещении между колонками обновляется status в БД
```

#### 4. SVG иконки
```python
from utils.icon_loader import IconLoader
icon = IconLoader.load('search.svg', size=24)
btn = IconLoader.create_icon_button('save', text='Сохранить', icon_size=20)
```
- Иконки хранятся в `resources/icons/`
- Поддерживает авто-добавление расширения `.svg`

### Паттерны Database

#### Миграции
DatabaseManager выполняет миграции при инициализации:
```python
# database/db_manager.py
def __init__(self):
    self.run_migrations()  # Авто-применение всех миграций
    self.create_supervision_table_migration()
    self.add_approval_deadline_field()
    # и т.д.
```
**Важно**: При добавлении колонок проверяйте наличие через `PRAGMA table_info()`:
```python
cursor.execute("PRAGMA table_info(table_name)")
columns = [col[1] for col in cursor.fetchall()]
if 'new_column' not in columns:
    cursor.execute('ALTER TABLE table_name ADD COLUMN ...')
```

#### CRUD операции
```python
# В db_manager.py методы вида:
def get_crm_cards(self):           # SELECT
def add_crm_card(self, data):      # INSERT
def update_crm_card(self, id, data): # UPDATE
def delete_crm_card(self, id):     # DELETE

# Все возвращают/ожидают Python dict'ы с русскими ключами
```

#### JSON в SQLite
Некоторые колонки хранят JSON (например, этапы согласования):
```python
import json
stages = json.loads(db_data['approval_stages'])  # Десериализация
json_str = json.dumps(stages)  # Сериализация перед сохранением
```

### Паттерны Reports

#### PDF экспорт
```python
from utils.pdf_generator import PDFGenerator
gen = PDFGenerator()
gen.generate_report('output.pdf', title='Отчет', data=rows, headers=['Имя', 'Сумма'])
```
- Автоматическая ориентация: альбомная если колонок > 6
- Регистрирует русский шрифт Arial (Windows)

#### Встроенные отчеты в табах
```python
# Через PyQt5.QtPrintSupport для печати в PDF
printer = QPrinter()
printer.setOutputFormat(QPrinter.PdfFormat)
```

### Build & Distribution

#### PyInstaller specs
```bash
# Сборка exe с включением ресурсов:
pyinstaller InteriorStudio.spec
```
- Копирует `resources/`, `database/migrations.py` в executable
- High DPI scaling включен в main.py (Windows поддержка)
- Проверка путей к иконкам работает как для dev, так и для frozen режима

## Советы по расширению

### Добавление нового таба
1. Создайте `ui/new_tab.py` наследуя `QWidget`
2. **ВАЖНО**: Поддержите оба режима (локальный + API):
   ```python
   from config import MULTI_USER_MODE
   if MULTI_USER_MODE:
       data = self.api_client.get_data()  # Через API
   else:
       data = self.db.get_data()  # Прямая БД
   ```
3. Добавьте класс в `ui/main_window.py` imports и instantiate в `init_ui()`
4. Зарегистрируйте в `config.ROLES` для нужных ролей в `tabs[]`
5. Используйте `self.db = DatabaseManager()` ДА, даже при MULTI_USER_MODE=True (fallback)

### Добавление новой таблицы БД
1. Создайте миграцию в `database/db_manager.py`:
```python
def create_new_table_migration(self):
    conn = self.connect()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS table_name (...)''')
    conn.commit()
    self.close()
```
2. Вызовите в `__init__()` DatabaseManager
3. Создайте CRUD методы в DatabaseManager
4. **Если используется API**: добавьте эндпоинты в `server/server_crm_routes.py`

### Добавление колонки к существующей таблице
```python
def add_new_column_migration(self):
    conn = self.connect()
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(table_name)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'new_column' not in columns:
        cursor.execute('ALTER TABLE table_name ADD COLUMN new_column TYPE DEFAULT value')
        conn.commit()
    self.close()
```

## Известные особенности

- **High DPI на Windows**: Масштабирование включено в main.py (атрибуты Qt.AA_EnableHighDpiScaling)
- **Frameless окна**: Используются везде (main_window, login_window) → CustomTitleBar обязателен
- **Русская локализация**: Все строки в исходном коде на русском, файл использует `# -*- coding: utf-8 -*-`
- **Yandex Disk интеграция**: `utils/yandex_disk.py` для синхронизации отчетов
- **Дублирование кода**: В `database/` есть копия всех файлов UI/utils (тестовая структура?), игнорируйте
- **CRM Kanban сложный**: 5753 строк с логикой переводов между статусами, JSON-сохранением этапов согласования

## Схема базы данных SQLite

### Основные таблицы

#### `employees` — Сотрудники
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT,
    address TEXT,
    birth_date DATE,
    status TEXT DEFAULT 'активный',
    position TEXT NOT NULL,           -- Должность (из config.POSITIONS)
    secondary_position TEXT,           -- Вторая должность
    department TEXT NOT NULL,          -- Отдел (автоопределяется по position)
    login TEXT UNIQUE,                 -- Для входа
    password TEXT,                     -- Парос (хранится открытым!)
    role TEXT,                         -- Роль (из config.ROLES)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `clients` — Клиенты
```sql
CREATE TABLE clients (
    id INTEGER PRIMARY KEY,
    client_type TEXT NOT NULL,        -- 'Физическое лицо' или 'Юридическое лицо'
    full_name TEXT,                   -- Для физлиц
    phone TEXT NOT NULL,
    email TEXT,
    passport_series TEXT,             -- Физлица
    passport_number TEXT,
    registration_address TEXT,
    organization_name TEXT,           -- Юрлица
    inn TEXT,
    ogrn TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `contracts` — Договоры
```sql
CREATE TABLE contracts (
    id INTEGER PRIMARY KEY,
    client_id INTEGER NOT NULL,       -- FK к clients
    project_type TEXT NOT NULL,       -- 'Индивидуальный' или 'Шаблонный'
    agent_type TEXT,                  -- 'ФЕСТИВАЛЬ' или 'ПЕТРОВИЧ'
    city TEXT,                        -- 'СПБ', 'МСК', 'ВН'
    contract_number TEXT UNIQUE NOT NULL,
    contract_date DATE,
    address TEXT,
    area REAL,
    total_amount REAL,
    advance_payment REAL,             -- Первый платеж
    additional_payment REAL,          -- Второй платеж
    third_payment REAL,               -- Третий платеж
    contract_period INTEGER,          -- Дней
    status TEXT DEFAULT 'Новый заказ',
    termination_reason TEXT,          -- Если расторгнут
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `crm_cards` — Проекты в Kanban
```sql
CREATE TABLE crm_cards (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL,     -- FK к contracts
    column_name TEXT NOT NULL,        -- Статус колонки ('Новый заказ', 'Проектирование' и т.д.)
    deadline DATE,
    tags TEXT,                        -- JSON массив тегов
    is_approved BOOLEAN DEFAULT 0,
    approval_stages TEXT,             -- JSON: этапы согласования
    approval_deadline DATE,
    senior_manager_id INTEGER,        -- FK к employees
    sdp_id INTEGER,
    gap_id INTEGER,
    manager_id INTEGER,
    surveyor_id INTEGER,
    order_position INTEGER DEFAULT 0, -- Позиция в колонке
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `supervision_cards` — Карточки авторского надзора
```sql
CREATE TABLE supervision_cards (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER NOT NULL,     -- FK к contracts
    column_name TEXT NOT NULL DEFAULT 'Новый заказ',
    deadline DATE,
    tags TEXT,
    senior_manager_id INTEGER,        -- FK к employees
    dan_id INTEGER,                   -- FK к employees (ДАН)
    dan_completed BOOLEAN DEFAULT 0,
    is_paused BOOLEAN DEFAULT 0,
    pause_reason TEXT,
    paused_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

#### `salaries` — Зарплаты
```sql
CREATE TABLE salaries (
    id INTEGER PRIMARY KEY,
    contract_id INTEGER,              -- FK к contracts
    employee_id INTEGER NOT NULL,     -- FK к employees
    payment_type TEXT NOT NULL,       -- Тип платежа
    stage_name TEXT,                  -- Стадия ( 'Проектирование' и т.д.)
    amount REAL NOT NULL,
    advance_payment REAL,
    report_month TEXT NOT NULL,       -- 'Ноябрь 2025'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Связи между таблицами

```
clients ──┬──→ contracts ──┬──→ crm_cards
          │                ├──→ crm_supervision
          │                └──→ salaries
          │
          └──→ employees (client responsible person)

employees ←──┬── crm_cards (multiple roles: senior_manager, sdp, gap, manager, surveyor)
            ├── contracts (multiple fields)
            ├── salaries
            └── supervision_cards (senior_manager, dan)
```

## Тестирование

Проект **не использует unittest/pytest**. Текущая практика:

### Способ тестирования
1. **Ручное тестирование**: Запуск `python main.py` и проверка GUI
2. **SQL-интеграция**: DatabaseManager инициализирует migrations при старте
3. **Пример встроенного теста** в `utils/pdf_generator.py`:
   ```python
   if __name__ == '__main__':
       gen = PDFGenerator()
       test_data = [['Иван', 'Дизайнер', '50000'], ...]
       gen.generate_report('test_report.pdf', 'Отчет', test_data, ['ФИО', 'Должность', 'Зарплата'])
   ```

### Как добавить автотесты
Если требуется добавить `pytest`:
1. Установить: `pip install pytest pytest-qt`
2. Создать `tests/` папку в корне проекта
3. Писать тесты для DatabaseManager (`test_db.py`):
   ```python
   import pytest
   from database.db_manager import DatabaseManager
   
   @pytest.fixture
   def db():
       return DatabaseManager(':memory:')  # In-memory БД для тестов
   
   def test_add_employee(db):
       emp = {'full_name': 'Тест', 'phone': '+7...', 'position': 'Дизайнер', ...}
       db.add_employee(emp)
       assert db.get_employees() is not None
   ```

## Статусы колонок Kanban

### Индивидуальные проекты (6 колонок)
1. **Новый заказ** — Входящая очередь
2. **В ожидании** — Ожидание информации от клиента
3. **Стадия 1: планировочные решения** — Работа над планировкой
4. **Стадия 2: концепция дизайна** — Разработка концепции (может быть согласование)
5. **Стадия 3: рабочие чертежи** — Создание рабочих чертежей
6. **Выполненный проект** — Завершено

### Шаблонные проекты (5 колонок)
1. **Новый заказ** — Входящая очередь
2. **В ожидании** — Ожидание информации от клиента
3. **Стадия 1: планировочные решения** — Работа над планировкой
4. **Стадия 2: рабочие чертежи** — Создание рабочих чертежей
5. **Выполненный проект** — Завершено

### Логика перемещения карточек
- Перемещение между колонками → изменение `crm_cards.column_name` в БД
- JSON `approval_stages` сохраняет этапы согласования (может быть с дедлайнами)
- `is_approved = 1` → карточка прошла все согласования
- При drag & drop вызывается `on_card_moved()` → обновляется БД и статус

## Часто используемые SQL-запросы и методы

### Получение данных CRM
```python
# Получить все активные карточки по типу проекта
cards = db.get_crm_cards_by_project_type('Индивидуальный')
# Возвращает список dict с полями: contract_number, column_name, senior_manager_name, ...

# Получить архивные карточки (завершённые проекты)
archived = db.get_archived_crm_cards('Индивидуальный')

# Получить историю переходов карточки между стадиями
history = db.get_stage_history(card_id)
```

### Обновление CRM карточки
```python
# Обновить колонку (статус) карточки
db.update_crm_card_column(card_id, 'Стадия 2: концепция дизайна')

# Обновить данные карточки (назначить сотрудников)
updates = {
    'senior_manager_id': 5,
    'sdp_id': 10,
    'gap_id': 15,
    'manager_id': 8
}
db.update_crm_card(card_id, updates)
```

### Работа с контрактами
```python
# Получить ID договора по ID карточки CRM
contract_id = db.get_contract_id_by_crm_card(crm_card_id)

# Получить ID карточки CRM по договору
card_id = db.get_crm_card_id_by_contract(contract_id)
```

### Работа с сотрудниками
```python
# Получить всех сотрудников
employees = db.get_employees()

# Получить сотрудника по позиции
designers = db.get_employees_by_position('Дизайнер')

# Назначить исполнителя на стадию
db.assign_stage_executor(
    card_id=1,
    stage_name='Стадия 2: концепция дизайна',
    executor_id=5,
    assigned_by=10,  # ID сотрудника, который назначает
    deadline='2025-12-31'
)
```

### Работа с историей действий
```python
# Получить историю действий пользователя
history = db.get_action_history(user_id)

# Добавить запись в историю
db.add_action(
    user_id=10,
    action_type='update',
    entity_type='crm_card',
    entity_id=1,
    description='Переместил карточку в Стадия 2'
)
```

### Работа с зарплатами
```python
# Получить зарплаты сотрудника за период
salaries = db.get_salaries_by_employee(employee_id, report_month='Ноябрь 2025')

# Добавить зарплату
db.add_salary({
    'employee_id': 5,
    'payment_type': 'Аванс',
    'stage_name': 'Стадия 2: концепция дизайна',
    'amount': 25000,
    'report_month': 'Ноябрь 2025'
})
```

### SQL запросы прямо в коде
```python
# Если нужен точный контроль, используйте прямые запросы:
conn = self.db.connect()
cursor = conn.cursor()

# Пример: найти все карточки СДП за месяц
cursor.execute('''
    SELECT cc.id, cc.contract_id, c.contract_number, cc.column_name
    FROM crm_cards cc
    JOIN contracts c ON cc.contract_id = c.id
    WHERE cc.sdp_id = ? AND strftime('%Y-%m', cc.updated_at) = ?
    ORDER BY cc.updated_at DESC
''', (sdp_id, '2025-11'))

cards = cursor.fetchall()
self.db.close()
```

## Интеграция с Yandex Disk

### Конфигурация
- **Ссылка**: `config.YANDEX_DISK_LINK` = "https://disk.yandex.ru/d/wxS_YmhYfjl-FQ"
- **Класс**: `utils/yandex_disk.py` → `YandexDiskManager`

### Использование
```python
from utils.yandex_disk import YandexDiskManager

manager = YandexDiskManager(token='<OAUTH_TOKEN>')

# Загрузка отчета на диск
manager.upload_file('report.pdf', '/reports/2025/report.pdf')

# Скачивание
manager.download_file('/reports/2025/report.pdf', 'local_report.pdf')

# Получение публичной ссылки
public_url = manager.get_public_link('/reports/2025/report.pdf')
```

### Как получить OAuth токен
1. Зайти на https://oauth.yandex.ru/
2. Создать приложение с типом "Яндекс.Диск"
3. Получить токен авторизации
4. Сохранить в конфиге или переменной окружения

### Где используется
- **ReportsTab**: Экспорт PDF отчетов на Диск
- **Синхронизация архива**: Регулярная загрузка бэкапов БД

### Важно
- Токен **не должен** храниться в исходном коде
- Использовать переменные окружения: `os.getenv('YANDEX_DISK_TOKEN')`
- При ошибке 401 → токен истек, нужна переавторизация

## Встроенные константы и конфиги

### Роли пользователей (`config.ROLES`)

Каждой роли соответствуют 3 параметра:
- **`tabs`** — доступные табы в главном окне
- **`can_assign`** — кому может назначать задачи (список отделов или `['all']`)
- **`can_edit`** — может ли редактировать данные

**Иерархия ролей:**
```python
# Полный доступ (все табы)
'Руководитель студии' → ['all'] assigned permissions
'Старший менеджер проектов' → ['Проектный отдел', 'Исполнительный отдел']

# Ограниченный доступ
'СДП' / 'ГАП' → СРМ + Статистика + Сотрудники, can_edit=True
'Дизайнер' / 'Чертёжник' / 'Замерщик' → СРМ только, can_edit=False
'ДАН' → СРМ надзора только
```

### Должности и отделы (`config.POSITIONS`)

```python
POSITIONS = [
    'Руководитель студии',      # Административный отдел
    'Старший менеджер проектов', # Административный отдел
    'СДП', 'ГАП',               # Административный отдел
    'Дизайнер', 'Чертёжник',    # Проектный отдел
    'Менеджер', 'ДАН', 'Замерщик' # Исполнительный отдел
]
```

При добавлении сотрудника отдел **автоматически определяется** по должности:
```python
if position in ['Руководитель студии', 'СДП', 'ГАП']:
    department = 'Административный отдел'
elif position in ['Дизайнер', 'Чертёжник']:
    department = 'Проектный отдел'
else:
    department = 'Исполнительный отдел'
```

### Типы проектов и агенты

```python
PROJECT_TYPES = ['Индивидуальный', 'Шаблонный']
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
CITIES = ['СПБ', 'МСК', 'ВН']  # СПБ, МСК, Внеомер
```

### Цветовая схема

```python
COLORS = {
    'primary': '#E8F4F8',      # Светло-голубой
    'secondary': '#F5E6D3',    # Персиковый
    'accent': '#D4E4BC',       # Светло-зеленый
    'background': '#FFFFFF',   # Белый
    'border': '#CCCCCC',       # Серый
    'text': '#333333'          # Темный
}
```

### Типы платежей (для зарплат)

```python
PAYMENT_TYPES = [
    'Аванс',              # Первый платеж
    'Основной платеж',    # Второй платеж
    'Оплата согласования' # Платеж за согласование
]
```

## Соглашение об именах и конвенции кода

### Именование в коде
- **Переменные БД**: `snake_case` (`contract_number`, `senior_manager_id`)
- **Python переменные**: `snake_case`
- **Классы PyQt**: `PascalCase` (`CRMTab`, `DraggableListWidget`)
- **Константы**: `UPPER_CASE` (`DATABASE_PATH`, `PROJECT_TYPES`)

### Паттерны в UI коде
1. **Всегда используйте `# -*- coding: utf-8 -*-`** в начале файла для русского текста
2. **Frameless окна везде**: `self.setWindowFlags(Qt.FramelessWindowHint)`
3. **CustomTitleBar обязателен**: вместо стандартной рамки окна
4. **Все строки на русском**: даже переменные и комментарии

### Паттерны в Database коде
1. **Всегда проверяйте существование колонок перед ALTER TABLE**:
   ```python
   cursor.execute("PRAGMA table_info(table_name)")
   columns = [col[1] for col in cursor.fetchall()]
   if 'new_column' not in columns:
       cursor.execute('ALTER TABLE ...')
   ```

2. **JSON-сохранение для сложных данных**:
   ```python
   import json
   # При сохранении:
   json_str = json.dumps(stages)
   # При загрузке:
   stages = json.loads(db_data['approval_stages'])
   ```

3. **Миграции в `__init__` DatabaseManager**: все миграции должны быть вызваны при инициализации

### Особенности API режима (MULTI_USER_MODE=True)

**SyncManager синхронизирует данные через WebSocket-подобный механизм:**

```python
# utils/sync_manager.py запускает QTimer каждые SYNC_INTERVAL
self.sync_timer = QTimer()
self.sync_timer.timeout.connect(self._sync)
self.sync_timer.start(5000)  # Каждые 5 секунд

# Сигналы, на которые подписываются табы:
online_users_updated.emit(user_count)  # Обновление числа онлайн
connection_status_changed.emit(is_online)  # Статус соединения
```

**Перехват изменений данных:**
- APIClient отправляет PUT/POST запросы к серверу
- Локальный кэш обновляется сразу (optimistic update)
- SyncManager каждые 5 сек синхронизирует с сервером
- При конфликте — данные сервера приоритетнее (CRDT логика)

**Обработка потери интернета:**
```python
# APIClient автоматически retry-ит:
MAX_RETRIES = 3
RETRY_DELAY = 1  # секунда между попытками
DEFAULT_TIMEOUT = 10  # таймаут запроса
```

При отключении сервера местные изменения сохраняются в кэш, синхронизируются при восстановлении.

### Паттерны в PDF/Reports коде
1. **Автоориентация**: альбомная если колонок > 6, иначе книжная
2. **Русский шрифт**: регистрируется при инициализации PDFGenerator
3. **Расширение ориентации на лету**: используйте `landscape()` / `A4`

## Ссылки в коде

- Конфигурация: `config.py` (ROLES, POSITIONS, PROJECT_TYPES, MULTI_USER_MODE, API_BASE_URL)
- Стили: `resources/styles.qss`, `utils/global_styles.py`
- Иконки: `resources/icons/` (SVG файлы)
- База данных: `interior_studio.db` (SQLite, путь в config.DATABASE_PATH)
- Синхронизация: `utils/sync_manager.py` (для API режима)
- API клиент: `utils/api_client.py` (retry/timeout логика)
