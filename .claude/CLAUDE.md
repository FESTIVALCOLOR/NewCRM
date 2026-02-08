# Interior Studio CRM

**Версия:** 1.0.0
**Дата обновления:** 2026-02-08
**Язык:** Python (десктоп-клиент PyQt5 + сервер FastAPI)

---

## Обзор проекта

Interior Studio CRM -- десктопное CRM-приложение для студии дизайна интерьеров. Два режима работы:
- **Локальный режим** (`MULTI_USER_MODE = False`): автономное приложение с SQLite
- **Многопользовательский режим** (`MULTI_USER_MODE = True`): десктоп-клиент взаимодействует с REST API на FastAPI, за которым стоит PostgreSQL

Десктоп-клиент построен на PyQt5 и собирается в Windows .exe через PyInstaller.

---

## Структура каталогов

```
/home/user/NewCRM/
|-- main.py                     # Точка входа: QApplication, стили, инициализация БД, окно логина
|-- config.py                   # Конфигурация: пути, роли, настройки API, класс FastAPI Settings
|-- InteriorStudio.spec         # Конфигурация сборки PyInstaller
|-- requirements.txt            # Зависимости десктоп-клиента (8 пакетов)
|-- docker-compose.yml          # Стек PostgreSQL + FastAPI + Nginx
|-- .env.example                # Шаблон переменных окружения
|-- deploy_crm.sh / install.sh  # Скрипты развертывания сервера
|
|-- database/
|   |-- __init__.py             # ОБЯЗАТЕЛЕН -- делает каталог Python-пакетом
|   `-- db_manager.py           # Класс DatabaseManager (~3900 строк): SQL, миграции, CRUD
|
|-- ui/                         # Модули интерфейса PyQt5 (28 файлов, ~48000 строк)
|   |-- __init__.py             # ОБЯЗАТЕЛЕН -- делает каталог Python-пакетом
|   |-- login_window.py         # Окно аутентификации
|   |-- main_window.py          # Главное окно с вкладками, видимость по ролям
|   |-- clients_tab.py          # Управление клиентами (CRUD)
|   |-- contracts_tab.py        # Управление жизненным циклом договоров
|   |-- crm_tab.py              # Канбан-доска проектов (САМЫЙ БОЛЬШОЙ файл ~18700 строк)
|   |-- crm_supervision_tab.py  # Авторский надзор (~5500 строк)
|   |-- dashboard_tab.py        # Статистика и KPI
|   |-- employees_tab.py        # Управление сотрудниками
|   |-- employee_reports_tab.py # Отчеты по сотрудникам
|   |-- reports_tab.py          # Статистические отчеты с экспортом в PDF
|   |-- salaries_tab.py         # Управление зарплатами
|   |-- rates_dialog.py         # Диалог настройки ставок
|   |-- custom_title_bar.py     # Кастомная панель заголовка с логотипом
|   |-- custom_combobox.py      # ComboBox с исправлением прокрутки
|   |-- custom_dateedit.py      # Кастомный выбор даты
|   |-- custom_message_box.py   # Брендированные диалоги сообщений
|   |-- file_gallery_widget.py  # Виджет галереи изображений
|   |-- file_list_widget.py     # Виджет списка файлов
|   |-- file_preview_widget.py  # Рендерер предпросмотра документов
|   |-- variation_gallery_widget.py
|   |-- flow_layout.py          # Кастомный менеджер потокового лейаута
|   `-- update_dialogs.py       # Диалоги автообновления
|
|-- utils/                      # Утилиты (21 файл, ~10000 строк)
|   |-- __init__.py             # ОБЯЗАТЕЛЕН -- делает каталог Python-пакетом
|   |-- resource_path.py        # КРИТИЧНО: определяет пути для dev и PyInstaller exe
|   |-- icon_loader.py          # Загрузка SVG-иконок с кэшированием
|   |-- api_client.py           # REST API клиент с JWT, retry, timeout (~1600 строк)
|   |-- yandex_disk.py          # Интеграция с Яндекс.Диском
|   |-- db_security.py          # Хеширование паролей (bcrypt), шифрование
|   |-- password_utils.py       # Утилиты хеширования/проверки паролей
|   |-- validators.py           # Валидация email, телефона, ИНН, ОГРН, паспорта
|   |-- date_utils.py           # Форматирование дат, расчет периодов
|   |-- pdf_generator.py        # Генерация PDF через ReportLab
|   |-- preview_generator.py    # Генерация миниатюр изображений/PDF
|   |-- logger.py               # Структурированное логирование в файл и консоль
|   |-- update_manager.py       # Проверка версий через Яндекс.Диск
|   |-- calendar_styles.py      # Стили QCalendarWidget (QSS)
|   |-- global_styles.py        # Глобальные стили (QSS)
|   |-- custom_style.py         # Кастомизация стилей в runtime
|   |-- table_settings.py       # Сохранение ширины столбцов/сортировки
|   |-- dialog_helpers.py       # Вспомогательные утилиты диалогов
|   |-- tooltip_fix.py          # Поддержка многострочных подсказок
|   |-- message_helper.py       # Хелперы отображения сообщений
|   |-- tab_helpers.py          # Хелперы переключения вкладок
|   |-- migrate_passwords.py    # Утилита миграции хешей паролей
|   |-- add_indexes.py          # Создание индексов БД
|   `-- constants.py            # (пустой, зарезервирован)
|
|-- server/                     # Бэкенд FastAPI для многопользовательского режима
|   |-- __init__.py
|   |-- main.py                 # Приложение FastAPI со всеми маршрутами (~3500 строк)
|   |-- database.py             # SQLAlchemy ORM модели (~600 строк)
|   |-- schemas.py              # Схемы валидации Pydantic v2 (~500 строк)
|   |-- auth.py                 # JWT аутентификация (~100 строк)
|   |-- config.py               # Серверные настройки
|   |-- yandex_disk_service.py  # Серверный сервис Яндекс.Диска
|   |-- Dockerfile              # Сборка контейнера FastAPI
|   |-- requirements.txt        # Серверные зависимости (12 пакетов)
|   `-- .env.example
|
|-- resources/                  # Статические ресурсы (встраиваются в exe через PyInstaller)
|   |-- styles.qss              # Главный файл стилей QSS
|   |-- logo.png                # Логотип приложения
|   |-- icon.ico                # Иконка приложения (основная)
|   |-- icon32.ico .. icon256.ico  # Иконки разных размеров
|   `-- icons/                  # 54 SVG-иконки для кнопок интерфейса
|       |-- add.svg, delete.svg, edit.svg, refresh.svg, save.svg
|       |-- close.svg, minimize.svg, maximize.svg
|       |-- arrow-*.svg, check-*.svg, calendar.svg и др.
|
|-- nginx/
|   `-- nginx.conf              # Конфигурация обратного прокси с SSL
|
`-- Скрипты в корне (утилиты миграции/тестирования, не часть приложения):
    |-- add_*.py (12 файлов)    # Скрипты миграции БД
    |-- fix_*.py (8 файлов)     # Скрипты исправлений кодовой базы
    |-- test_*.py (8 файлов)    # Тестовые/проверочные скрипты
    |-- check_*.py (5 файлов)   # Проверка целостности данных
    |-- migrate_to_server.py    # Миграция в многопользовательский режим
    `-- generate_icons.py       # Генерация SVG-иконок
```

---

## Критические правила для ИИ-ассистентов

### 1. Файлы `__init__.py` ОБЯЗАТЕЛЬНЫ

Каждый каталог Python-пакета (`database/`, `ui/`, `utils/`, `server/`) ДОЛЖЕН содержать файл `__init__.py`. Без них PyInstaller не найдет модули. Файлы могут быть пустыми, но должны существовать.

### 2. Запрет emoji в UI-коде

НИКОГДА не используйте символы emoji в строках пользовательского интерфейса. Используйте обычный текст ("ВНИМАНИЕ", "УСПЕХ", "ОШИБКА") или SVG-иконки через `IconLoader`. Emoji допустимы ТОЛЬКО в `print()` для отладки.

```python
# НЕПРАВИЛЬНО
label = QLabel('ВНИМАНИЕ')
button = QPushButton('Готово')

# ПРАВИЛЬНО -- обычный текст
label = QLabel('ВНИМАНИЕ')
button = QPushButton('Готово')

# ПРАВИЛЬНО -- SVG-иконка
from utils.icon_loader import IconLoader
button = IconLoader.create_icon_button('check', 'Готово', icon_size=14)
```

### 3. Всегда использовать `resource_path()` для статических ресурсов

Все пути к файлам в `resources/` ДОЛЖНЫ проходить через `resource_path()`. Прямые пути вроде `'resources/logo.png'` ломаются в PyInstaller exe.

```python
from utils.resource_path import resource_path

# Правильно
logo = QPixmap(resource_path('resources/logo.png'))
icon = QIcon(resource_path('resources/icons/edit.svg'))
with open(resource_path('resources/styles.qss'), 'r') as f: ...

# Неправильно -- не работает в exe
logo = QPixmap('resources/logo.png')
```

Файлы, которые ДОЛЖНЫ импортировать `resource_path`:
- `main.py`, `ui/login_window.py`, `ui/custom_title_bar.py`
- `ui/crm_tab.py`, `ui/crm_supervision_tab.py`, `ui/reports_tab.py`
- `utils/icon_loader.py`, `utils/calendar_styles.py`

### 4. Новые модули нужно регистрировать в PyInstaller spec

При добавлении нового Python-модуля его нужно добавить в `hiddenimports` в `InteriorStudio.spec`:

```python
hiddenimports=[
    ...
    'ui.new_module',      # Новые UI-модули добавлять сюда
    'utils.new_utility',  # Новые утилиты добавлять сюда
    ...
]
```

### 5. База данных НЕ встраивается в exe

SQLite база данных (`interior_studio.db`) находится рядом с exe, не внутри него. Только `resources/` встраивается в exe через `datas` в spec-файле.

### 6. Осведомленность о многопользовательском режиме

Приложение имеет двойную архитектуру. Когда `MULTI_USER_MODE = True` в `config.py`, клиент использует `utils/api_client.py` для связи с сервером FastAPI. Когда `False` -- использует `database/db_manager.py` напрямую с SQLite. Многие модули вкладок проверяют этот флаг для выбора источника данных.

---

## Технологический стек

| Уровень | Технология | Версия |
|---------|-----------|--------|
| Десктоп GUI | PyQt5 | 5.15.9 |
| Локальная БД | SQLite | (stdlib) |
| Серверный фреймворк | FastAPI | 0.115.0 |
| Серверная БД | PostgreSQL | 15-alpine |
| ORM | SQLAlchemy | 2.0.36 |
| Валидация | Pydantic | 2.10.3 |
| Аутентификация | JWT (python-jose, HS256) | 3.3.0 |
| Облачное хранилище | Яндекс.Диск API | собственный клиент |
| Генерация PDF | ReportLab | 4.0.7 |
| Анализ данных | Pandas | 2.1.4 |
| Графики | Matplotlib | 3.8.2 |
| HTTP-клиент | Requests | 2.31.0 |
| Сборка exe | PyInstaller | 6.3.0 |
| Чтение PDF | PyMuPDF | 1.23.8 |
| Контейнеризация | Docker Compose | 3.8 |
| Обратный прокси | Nginx | alpine |

---

## Архитектура

### Поток приложения

```
main.py
  -> Инициализация QApplication (High DPI, стиль Fusion, глобальные стили)
  -> DatabaseManager.initialize_database() (запуск миграций)
  -> LoginWindow
     -> Аутентификация через db_manager (локально) или api_client (многопользовательский)
     -> MainWindow
        -> Загрузка вкладок в зависимости от роли пользователя
        -> Каждая вкладка использует db_manager или api_client
        -> Иконки через IconLoader
        -> Все ресурсы через resource_path()
```

### Двухрежимный доступ к данным

```
config.MULTI_USER_MODE = True:
  Клиент (PyQt5) --HTTPS--> FastAPI (server/main.py) --SQLAlchemy--> PostgreSQL
  Аутентификация: JWT токены, срок действия 30 мин (сервер), 24 часа (локальные Settings)
  Повтор: 3 попытки с задержкой 1 сек, таймаут 10 сек

config.MULTI_USER_MODE = False:
  Клиент (PyQt5) --напрямую--> SQLite (database/db_manager.py)
  Аутентификация: локальная проверка хеша пароля
```

### Стек развертывания сервера

```
docker-compose.yml:
  postgres (порт 5432) -> crm_user / interior_studio_crm
  api (порт 8000) -> FastAPI с uvicorn
  nginx (порты 80, 443) -> SSL-терминация, обратный прокси к api
```

Текущий сервер: `https://147.45.154.193` (Timeweb Cloud VPS)

---

## Ролевая модель доступа

9 ролей определены в `config.py` с гранулярным доступом к вкладкам:

| Роль | Вкладки | Редактирование | Назначение |
|------|---------|----------------|-----------|
| Руководитель студии | Все | Да | Все |
| Старший менеджер проектов | Все | Да | Проектный/Исполнительный отделы |
| СДП | СРМ, Отчеты, Сотрудники | Да | Нет |
| ГАП | СРМ, Отчеты, Сотрудники | Да | Нет |
| Менеджер | СРМ, Сотрудники | Да | Нет |
| Дизайнер | СРМ | Да (свои проекты) | Нет |
| Чертёжник | СРМ | Да (свои проекты) | Нет |
| ДАН | СРМ надзора | Да (свои проекты) | Нет |
| Замерщик | СРМ | Только чтение | Нет |

---

## Схема базы данных (17 локальных таблиц)

Основные таблицы в `database/db_manager.py`:

- **employees** -- Пользователи/сотрудники: аутентификация, роли, должности, статус
- **clients** -- Записи клиентов (физические лица и организации)
- **contracts** -- Жизненный цикл договоров (суммы, даты, файлы, статус)
- **crm_cards** -- Канбан-карточки для управления проектами
- **stage_executors** -- Назначение исполнителей по этапам для CRM-карточек
- **crm_supervision** / **supervision_cards** -- Авторский надзор
- **salaries** -- Записи зарплат по договору/сотруднику/этапу
- **payments** -- Система учета платежей
- **rates** -- Конфигурация ставок по должности/этапу/типу оплаты
- **project_files** -- Метаданные файлов (интеграция с Яндекс.Диском)
- **action_history** -- Аудит-журнал действий пользователей
- **agents** -- Справочная таблица агентов (ФЕСТИВАЛЬ, ПЕТРОВИЧ)
- **approval_stage_deadlines** -- Тайминг процесса согласования
- **manager_stage_acceptance** -- Подтверждение приемки менеджером
- **surveys** -- Записи замеров/обследований

Сервер добавляет многопользовательские таблицы в `server/database.py`:
- **UserSession** -- Отслеживание токенов и активности
- **UserPermission** -- Гранулярный контроль доступа
- **ActivityLog** -- Серверный аудит-журнал
- **ConcurrentEdit** -- Оптимистичная блокировка для многопользовательских правок
- **Notification** -- Системные уведомления

Миграции запускаются автоматически в `DatabaseManager.initialize_database()`.

---

## Статус интеграции с API

| Модуль | Интеграция с API | Примечания |
|--------|-----------------|-----------|
| Дашборд | 100% | Эндпоинты статистики |
| Клиенты | 100% | Полный CRUD |
| Сотрудники | 100% | Полный CRUD |
| Договора | ~70% | Не хватает интеграции загрузки файлов |
| СРМ | 0% (подготовлено) | Маршруты есть, клиент не подключен |
| СРМ надзора | 0% (подготовлено) | Маршруты есть, клиент не подключен |
| Отчеты | 0% | Не начато |
| Зарплаты | 0% | Не начато |
| Отчеты по сотрудникам | 0% | Не начато |

`utils/api_client.py` (класс `APIClient`) обеспечивает всю REST-коммуникацию с JWT-аутентификацией, логикой повторных попыток (3 попытки) и таймаутом 10 секунд.

---

## Справочник ключевых модулей

### `database/db_manager.py` (~3900 строк)
Центральный слой доступа к данным. Содержит:
- Класс `DatabaseManager` со всеми CRUD-операциями
- `initialize_database()` -- создание таблиц и запуск миграций
- Все SQL-запросы для каждого типа сущностей
- Методы миграций для добавления столбцов/таблиц

### `ui/crm_tab.py` (~18700 строк)
Самый большой файл. Реализует CRM-доску в стиле канбан:
- Перетаскивание карточек между колонками (drag-and-drop)
- Назначение исполнителей по этапам
- Процессы согласования
- Вложение файлов (Яндекс.Диск)
- Генерация PDF для договоров

### `utils/api_client.py` (~1600 строк)
REST-клиент с методами для каждого API-эндпоинта:
- `login()`, `get_employees()`, `create_client()` и др.
- Управление JWT-токенами (автообновление)
- Иерархия исключений: `APIError`, `APITimeoutError`, `APIConnectionError`, `APIAuthError`, `APIResponseError`

### `server/main.py` (~3500 строк)
Приложение FastAPI с 50+ эндпоинтами для всех типов сущностей. Использует SQLAlchemy ORM модели из `server/database.py` и Pydantic-схемы из `server/schemas.py`.

---

## Конфигурация (`config.py`)

Основные настройки:

```python
# Пути
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'interior_studio.db')

# Версионирование
APP_VERSION = "1.0.0"
APP_NAME = "Interior Studio CRM"

# Многопользовательский режим
MULTI_USER_MODE = True
API_BASE_URL = "https://147.45.154.193"
SYNC_INTERVAL = 5  # секунды

# Обновления
UPDATE_CHECK_ENABLED = True
UPDATE_YANDEX_PUBLIC_KEY = "SmxiWfUUEt8oEA"

# Доменные константы
PROJECT_TYPES = ['Индивидуальный', 'Шаблонный']
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
CITIES = ['СПБ', 'МСК', 'ВН']
PROJECT_STATUSES = ['СДАН', 'АВТОРСКИЙ НАДЗОР', 'РАСТОРГНУТ']

# Класс FastAPI Settings (используется сервером)
# secret_key, algorithm (HS256), access_token_expire_minutes (1440)
```

---

## Команды для разработки

```bash
# Запуск десктоп-приложения (разработка)
python main.py

# Запуск миграций БД
python -c "from database.db_manager import DatabaseManager; db = DatabaseManager(); db.initialize_database(); print('OK')"

# Проверка импорта модулей
python -c "from ui.login_window import LoginWindow; print('OK')"
python -c "from utils.icon_loader import IconLoader; print('OK')"

# Запуск сервера FastAPI локально
cd server && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Сборка Windows exe (на Windows)
pyinstaller InteriorStudio.spec --clean --noconfirm
cp interior_studio.db dist/interior_studio.db

# Развертывание через Docker
docker-compose up -d --build

# Проверка здоровья сервера
curl -k https://147.45.154.193/health
```

---

## Правила PyInstaller spec

Файл `InteriorStudio.spec` управляет сборкой exe:

- **datas**: Только `('resources', 'resources')` -- только статические ресурсы
- **hiddenimports**: Все Python-модули из `ui/`, `database/`, `utils/`
- **console=False**: GUI-приложение, без окна консоли
- **icon**: `resources/icon.ico`
- НЕ добавлять `database/`, `ui/`, `utils/` в `datas` -- это Python-модули, а не данные

---

## Типичные проблемы и решения

| Проблема | Причина | Решение |
|----------|---------|---------|
| `No module named 'ui.xxx'` | Отсутствует `__init__.py` | Создать пустой `__init__.py` в каталоге пакета |
| `no such column: cc.xxx` | Устаревшая БД в dist/ | Запустить приложение через Python для миграций, скопировать БД |
| Ресурсы не загружаются в exe | Не используется `resource_path()` | Обернуть все пути к ресурсам в `resource_path()` |
| Иконки не отображаются | Прямые пути в IconLoader | Использовать `resource_path()` в коде загрузки иконок |
| Иконка не в панели задач | Не установлена в `main.py` | `app.setWindowIcon(QIcon(resource_path('resources/icon.ico')))` |
| `Permission denied` при сборке | exe-файл запущен | Завершить процесс `InteriorStudio.exe` |
| Ошибки подключения к API | Сервер недоступен или SSL | Проверить `API_BASE_URL`, SSL-сертификат, статус сервера |
| Ошибки импорта Pydantic | v1 vs v2 | Использовать `pydantic-settings` для `BaseSettings` (v2) |

---

## Чеклист перед сборкой

- [ ] Все файлы `__init__.py` на месте (database, ui, utils, server)
- [ ] Все пути к ресурсам используют `resource_path()`
- [ ] Новые модули добавлены в `hiddenimports` в spec-файле
- [ ] Версия обновлена в `config.py` (при выпуске релиза)
- [ ] Миграции БД выполняются без ошибок
- [ ] Приложение запускается через `python main.py`

---

## Зависимости

### Десктоп-клиент (`requirements.txt`)
```
PyQt5==5.15.9
PyQt5-tools==5.15.9.3.3
reportlab==4.0.7
matplotlib==3.8.2
pandas==2.1.4
requests==2.31.0
pyinstaller==6.3.0
PyMuPDF==1.23.8
```

### Сервер (`server/requirements.txt`)
```
fastapi==0.115.0
uvicorn[standard]==0.32.0
sqlalchemy==2.0.36
psycopg2-binary==2.9.10
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.18
python-dotenv==1.0.1
requests==2.32.3
pydantic==2.10.3
pydantic-settings==2.6.1
alembic==1.14.0
```

---

## Система обновлений

Файлы: `config.py` (константы версий), `utils/update_manager.py`, `ui/update_dialogs.py`

Процесс: обновить `APP_VERSION` в `config.py` -> собрать exe -> загрузить на Яндекс.Диск -> обновить `version.json` -> клиенты автоматически обнаружат обновление.

---

## Файловое хранилище (Яндекс.Диск)

Облачное хранение файлов обеспечивается модулями `utils/yandex_disk.py` (клиентская сторона) и `server/yandex_disk_service.py` (серверная сторона). Используется для:
- Загрузки PDF договоров
- Документов технических заданий
- Данных замеров
- Резервных копий базы данных

Токен настраивается в `config.py` как `YANDEX_DISK_TOKEN`.

---

**Статус:** Десктоп-приложение работает, exe собирается корректно, сервер развернут на Timeweb Cloud. Интеграция с API ~40% завершена (Дашборд, Клиенты, Сотрудники готовы; Договора частично; СРМ/Отчеты/Зарплаты в ожидании).
