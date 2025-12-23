# Interior Studio CRM - Документация для Claude

**Версия:** 1.0.0
**Дата обновления:** 22.12.2025
**Python:** 3.14.0
**PyInstaller:** 6.17.0

---

## 🏗️ Структура проекта

```
d:\New CRM\interior_studio\
│
├── main.py                          # ⚡ Точка входа (устанавливает иконку app)
├── config.py                        # Конфигурация (версия, Яндекс.Диск ключ)
├── InteriorStudio.spec              # ⚙️ Конфигурация PyInstaller
│
├── database/
│   ├── __init__.py                  # ⚠️ КРИТИЧНО! Делает database пакетом Python
│   ├── db_manager.py                # Менеджер БД (миграции здесь)
│   └── interior_studio.db           # SQLite база (НЕ включается в exe)
│
├── ui/                              # Модули интерфейса
│   ├── __init__.py                  # ⚠️ КРИТИЧНО! Делает ui пакетом Python
│   ├── login_window.py              # Окно входа (использует resource_path)
│   ├── main_window.py               # Главное окно (использует resource_path)
│   ├── custom_title_bar.py          # Кастомный title bar (использует resource_path)
│   ├── crm_tab.py                   # CRM (использует resource_path)
│   ├── crm_supervision_tab.py       # Супервизия (использует resource_path)
│   ├── reports_tab.py               # Отчеты (использует resource_path)
│   ├── clients_tab.py
│   ├── contracts_tab.py
│   ├── dashboard_tab.py
│   ├── employees_tab.py
│   ├── employee_reports_tab.py
│   ├── salaries_tab.py
│   ├── custom_combobox.py
│   ├── custom_dateedit.py
│   ├── custom_message_box.py
│   ├── file_gallery_widget.py
│   ├── file_list_widget.py
│   ├── file_preview_widget.py
│   ├── variation_gallery_widget.py
│   ├── flow_layout.py
│   ├── rates_dialog.py
│   └── update_dialogs.py
│
├── utils/                           # Утилиты
│   ├── __init__.py                  # ⚠️ КРИТИЧНО! Делает utils пакетом Python
│   ├── resource_path.py             # 🔑 КЛЮЧЕВОЙ МОДУЛЬ для работы exe
│   ├── icon_loader.py               # 🎨 Загрузчик SVG иконок (использует resource_path)
│   ├── calendar_styles.py           # Стили календаря (использует resource_path)
│   ├── logger.py
│   ├── password_utils.py
│   ├── yandex_disk.py
│   ├── global_styles.py
│   ├── db_security.py
│   ├── update_manager.py
│   ├── cache_manager.py
│   ├── constants.py
│   ├── custom_style.py
│   ├── date_utils.py
│   ├── message_helper.py
│   ├── pdf_generator.py
│   ├── preview_generator.py
│   ├── tab_helpers.py
│   ├── tooltip_fix.py
│   └── validators.py
│
├── resources/                       # Ресурсы приложения
│   ├── styles.qss                   # Главный файл стилей
│   ├── logo.png                     # Логотип приложения
│   ├── icon.ico                     # Иконка приложения (используется в spec)
│   ├── icon32.ico                   # Иконка 32x32
│   ├── icon48.ico                   # Иконка 48x48
│   ├── icon64.ico                   # Иконка 64x64
│   └── icons/                       # 📁 Папка с SVG иконками
│       ├── edit.svg
│       ├── delete.svg
│       ├── refresh.svg
│       ├── save.svg
│       ├── add.svg
│       ├── close.svg
│       ├── minimize.svg
│       ├── maximize.svg
│       └── ... (множество SVG)
│
├── dist/                            # Папка с собранным exe
│   ├── InteriorStudio.exe           # Готовый exe файл
│   ├── interior_studio.db           # База данных (копируется вручную)
│   └── logs/                        # Логи работы exe
│
├── build/                           # Временные файлы PyInstaller (удалять при --clean)
├── preview_cache/                   # Кэш превью (не включается в exe)
├── logs/                            # Логи разработки
└── .venv/                           # Виртуальное окружение
```

---

## 🔑 КРИТИЧЕСКИ ВАЖНЫЕ ПРАВИЛА

### 1. Файлы __init__.py

**⚠️ ВСЕ папки с Python модулями ДОЛЖНЫ содержать `__init__.py`:**

```
database/__init__.py   # БЕЗ ЭТОГО PyInstaller НЕ найдет модули
ui/__init__.py         # БЕЗ ЭТОГО PyInstaller НЕ найдет модули
utils/__init__.py      # БЕЗ ЭТОГО PyInstaller НЕ найдет модули
```

Файлы могут быть пустыми, но ДОЛЖНЫ существовать!

### 2. Запрет Emoji в UI

**⚠️ НИКОГДА не используйте emoji в пользовательском интерфейсе:**

- Вместо emoji используйте **текст** (например, "ВНИМАНИЕ", "УСПЕХ", "ОШИБКА")
- Для иконок используйте **SVG файлы** из `resources/icons/`
- Emoji допустимы **ТОЛЬКО** в `print()` для отладки в консоли

**Примеры:**

❌ **НЕПРАВИЛЬНО:**
```python
# В UI элементах
label = QLabel('⚠️ ВНИМАНИЕ')
button = QPushButton('✓ Готово')
message = '📝 Запись добавлена'
```

✅ **ПРАВИЛЬНО:**
```python
# Текст без emoji
label = QLabel('ВНИМАНИЕ')
button = QPushButton('Готово')
message = 'Запись добавлена'

# Или SVG иконка через IconLoader
from utils.icon_loader import IconLoader
button = IconLoader.create_icon_button('check', 'Готово', icon_size=14)

# Допустимо в консоли для отладки
print("✓ Миграция выполнена успешно")
```

### 3. resource_path() - ОБЯЗАТЕЛЕН для всех ресурсов

**utils/resource_path.py:**
```python
import sys
import os

def resource_path(relative_path):
    """Определяет правильный путь к ресурсам в exe и dev"""
    try:
        base_path = sys._MEIPASS  # PyInstaller временная папка
    except Exception:
        base_path = os.path.abspath(".")  # Режим разработки
    return os.path.join(base_path, relative_path)
```

**КАК ИСПОЛЬЗОВАТЬ:**

✅ **ПРАВИЛЬНО:**
```python
from utils.resource_path import resource_path

# Загрузка изображений
logo = QPixmap(resource_path('resources/logo.png'))
icon = QIcon(resource_path('resources/icons/edit.svg'))

# Загрузка файлов
with open(resource_path('resources/styles.qss'), 'r') as f:
    styles = f.read()

# В IconLoader
icon_path = resource_path(os.path.join('resources/icons', icon_name))
```

❌ **НЕПРАВИЛЬНО:**
```python
# НЕ РАБОТАЕТ в exe!
logo = QPixmap('resources/logo.png')
icon = QIcon('resources/icons/edit.svg')
with open('resources/styles.qss', 'r') as f:
```

### 3. Импорты - строгий порядок

**Файлы, которые ДОЛЖНЫ импортировать resource_path:**
- `main.py` - для styles.qss и иконки приложения
- `ui/login_window.py` - для logo.png
- `ui/custom_title_bar.py` - для logo.png и иконок
- `ui/crm_tab.py` - для logo.png в PDF
- `ui/crm_supervision_tab.py` - для logo.png в PDF
- `ui/reports_tab.py` - для logo.png в отчетах
- `utils/icon_loader.py` - для всех SVG иконок
- `utils/calendar_styles.py` - для ICONS_PATH

**Правильный импорт:**
```python
from utils.resource_path import resource_path
```

**Размещение:** После всех импортов PyQt5/database/ui, перед комментариями

---

## ⚙️ InteriorStudio.spec - Конфигурация PyInstaller

### Структура spec файла:

```python
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],                     # Точка входа
    pathex=[],
    binaries=[],

    # РЕСУРСЫ: Только resources - остальное автоматически
    datas=[
        ('resources', 'resources'),  # Включает ВСЮ папку resources
    ],

    # МОДУЛИ: Все UI, database, utils модули
    hiddenimports=[
        # PyQt5
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt5.QtSvg',              # Для SVG иконок

        # Стандартные библиотеки
        'requests',
        'sqlite3',

        # UI модули (ВСЕ)
        'ui',
        'ui.login_window',
        'ui.main_window',
        'ui.clients_tab',
        'ui.contracts_tab',
        'ui.crm_tab',
        'ui.crm_supervision_tab',
        'ui.dashboard_tab',
        'ui.employees_tab',
        'ui.employee_reports_tab',
        'ui.reports_tab',
        'ui.salaries_tab',
        'ui.custom_title_bar',
        'ui.custom_combobox',
        'ui.custom_dateedit',
        'ui.custom_message_box',
        'ui.file_gallery_widget',
        'ui.file_list_widget',
        'ui.file_preview_widget',
        'ui.variation_gallery_widget',
        'ui.flow_layout',
        'ui.rates_dialog',
        'ui.update_dialogs',

        # Database модули
        'database',
        'database.db_manager',

        # Utils модули (ВСЕ используемые)
        'utils',
        'utils.logger',
        'utils.password_utils',
        'utils.yandex_disk',
        'utils.resource_path',      # ⚠️ КРИТИЧНО!
        'utils.calendar_styles',
        'utils.global_styles',
        'utils.db_security',
        'utils.update_manager',
        'utils.icon_loader',         # ⚠️ КРИТИЧНО для иконок!
    ],

    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='InteriorStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,                   # Без консоли для GUI
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='resources/icon.ico',       # Иконка exe файла
)
```

### Правила для spec файла:

1. **datas** - только статические ресурсы (resources)
2. **hiddenimports** - ВСЕ Python модули (ui, database, utils)
3. **icon** - путь к .ico файлу (НЕ нужен resource_path здесь)
4. **console=False** - для GUI приложения
5. **НЕ добавлять** в datas: database/, ui/, utils/ (они Python модули, не данные)

### Добавление нового UI модуля:

```python
# 1. Создать файл
ui/new_module.py

# 2. Добавить импорт resource_path (если нужен)
from utils.resource_path import resource_path

# 3. Добавить в hiddenimports в spec:
hiddenimports=[
    ...
    'ui.new_module',  # ← ДОБАВИТЬ
    ...
]

# 4. Пересобрать
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm
```

---

## 🔧 Команды для работы

### Разработка:

```bash
# Запуск через Python
.venv\Scripts\python.exe main.py

# Применение миграций БД
.venv\Scripts\python.exe -c "from database.db_manager import DatabaseManager; db = DatabaseManager(); print('OK')"

# Проверка импорта модуля
.venv\Scripts\python.exe -c "from ui.login_window import LoginWindow; print('OK')"

# Проверка загрузки иконки
.venv\Scripts\python.exe -c "from utils.icon_loader import IconLoader; icon = IconLoader.load('edit'); print('Icon:', not icon.isNull())"
```

### Сборка exe:

```bash
# Полная пересборка (рекомендуется)
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm

# Быстрая пересборка (без очистки)
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --noconfirm

# После сборки - копирование БД
cp interior_studio.db dist/interior_studio.db
```

### Очистка:

```bash
# Удалить временные файлы
rm -rf build/
rm -rf dist/
rm -rf __pycache__/
find . -name "*.pyc" -delete
```

---

## 🐛 Типичные проблемы и решения

### 1. "No module named 'ui.login_window'"

**Причина:** Отсутствует `database/__init__.py` или `ui/__init__.py`

**Решение:**
```bash
echo "" > database/__init__.py
echo "" > ui/__init__.py
```

### 2. "no such column: cc.approval_deadline"

**Причина:** База данных в dist/ не обновлена миграциями

**Решение:**
```bash
# Запустить программу через Python для миграций
.venv\Scripts\python.exe main.py
# Скопировать обновленную БД
cp interior_studio.db dist/interior_studio.db
```

### 3. Ресурсы не загружаются в exe

**Причина:** НЕ используется `resource_path()`

**Решение:**
```python
# Было
logo = QPixmap('resources/logo.png')

# Стало
from utils.resource_path import resource_path
logo = QPixmap(resource_path('resources/logo.png'))
```

### 4. Иконки не отображаются

**Причина:** `IconLoader` или `calendar_styles.py` используют прямые пути

**Решение:**
```python
# utils/icon_loader.py
icon_path = resource_path(os.path.join(IconLoader.ICONS_DIR, icon_name))

# utils/calendar_styles.py
ICONS_PATH = resource_path('resources/icons')
```

### 5. Иконка не в панели задач Windows

**Причина:** Не установлена иконка приложения в main.py

**Решение:**
```python
# main.py
from PyQt5.QtGui import QIcon
from utils.resource_path import resource_path

app = QApplication(sys.argv)
app_icon = QIcon(resource_path('resources/icon.ico'))
app.setWindowIcon(app_icon)
```

### 6. "Permission denied" при сборке

**Причина:** exe файл запущен

**Решение:**
```bash
# Закрыть InteriorStudio.exe
taskkill /F /IM InteriorStudio.exe
# Или удалить вручную
rm dist/InteriorStudio.exe
```

---

## 📦 База данных

### Важно:

- База данных **НЕ включается** в exe файл
- Хранится рядом с exe: `dist/interior_studio.db`
- При обновлении exe база **сохраняется**
- Миграции выполняются при первом запуске

### Расположение БД:

```
Разработка:  d:\New CRM\interior_studio\interior_studio.db
Exe:         d:\New CRM\interior_studio\dist\interior_studio.db
```

### Синхронизация БД после изменений:

```bash
# 1. Запустить Python для миграций
.venv\Scripts\python.exe main.py

# 2. Скопировать обновленную БД в dist
cp interior_studio.db dist/interior_studio.db
```

---

## 🎨 Иконки и ресурсы

### Форматы:

- **SVG** - для кнопок интерфейса (`resources/icons/*.svg`)
- **PNG** - для логотипа (`resources/logo.png`)
- **ICO** - для иконки приложения (`resources/icon.ico`)
- **QSS** - для стилей (`resources/styles.qss`)

### Загрузка иконок:

```python
# Через IconLoader (рекомендуется)
from utils.icon_loader import IconLoader
icon = IconLoader.load('edit')  # .svg добавляется автоматически
btn.setIcon(icon)

# Напрямую (если нужен контроль)
from PyQt5.QtGui import QIcon
from utils.resource_path import resource_path
icon = QIcon(resource_path('resources/icons/edit.svg'))
```

### Загрузка изображений:

```python
from PyQt5.QtGui import QPixmap
from utils.resource_path import resource_path

logo = QPixmap(resource_path('resources/logo.png'))
if not logo.isNull():
    label.setPixmap(logo)
```

---

## 🔄 Система обновлений

### Файлы:

- `config.py` - настройки (APP_VERSION, UPDATE_YANDEX_PUBLIC_KEY)
- `utils/update_manager.py` - менеджер обновлений
- `ui/update_dialogs.py` - диалоги обновлений

### Версионирование:

```python
# config.py
APP_VERSION = "1.0.0"  # Изменить при обновлении
APP_NAME = "Interior Studio CRM"
UPDATE_CHECK_ENABLED = True
UPDATE_YANDEX_PUBLIC_KEY = "SmxiWfUUEt8oEA"
```

### Процесс обновления:

1. Изменить версию в `config.py`
2. Собрать exe
3. Загрузить на Яндекс.Диск
4. Создать/обновить `version.json`
5. Пользователи получат уведомление об обновлении

---

## 🏗️ Архитектура приложения

### Основные компоненты:

1. **main.py** - точка входа, инициализация QApplication
2. **login_window.py** - аутентификация
3. **main_window.py** - главное окно с вкладками
4. **Tabs** - функциональные модули (CRM, клиенты, договора и т.д.)
5. **db_manager.py** - работа с SQLite БД
6. **IconLoader** - централизованная загрузка иконок
7. **resource_path** - правильные пути для exe

### Поток работы:

```
main.py
  → LoginWindow
    → аутентификация через db_manager
    → MainWindow
      → загрузка вкладок (tabs)
      → каждая вкладка использует db_manager
      → иконки через IconLoader
      → все ресурсы через resource_path()
```

---

## 📝 Чеклист перед сборкой exe

- [ ] Все __init__.py на месте (database, ui, utils)
- [ ] Все ресурсы используют resource_path()
- [ ] IconLoader использует resource_path()
- [ ] calendar_styles.py использует resource_path()
- [ ] main.py устанавливает иконку приложения
- [ ] Все новые модули добавлены в hiddenimports
- [ ] Версия обновлена в config.py (если нужно)
- [ ] База данных обновлена миграциями
- [ ] Python версия запускается без ошибок

---

## 🚀 Быстрый старт для новой сессии

```bash
# 1. Проверка структуры
ls database/__init__.py ui/__init__.py utils/__init__.py

# 2. Проверка Python версии
.venv\Scripts\python.exe main.py

# 3. Сборка exe
.venv\Scripts\pyinstaller.exe InteriorStudio.spec --clean --noconfirm

# 4. Копирование БД
cp interior_studio.db dist/interior_studio.db

# 5. Тест exe
dist\InteriorStudio.exe
```

---

## 📚 Дополнительная документация

- `СТРУКТУРА_ПРОЕКТА.md` - подробная структура
- `ФИНАЛЬНЫЙ_ОТЧЕТ.md` - история исправлений
- `ГОТОВО_ФИНАЛЬНАЯ_ВЕРСИЯ.md` - последний статус
- `ИСПРАВЛЕНИЕ_ПУТЕЙ_К_РЕСУРСАМ.md` - техническая документация

---

**Обновлено:** 22.12.2025, 00:00
**Статус:** Проект работает, exe собирается корректно
**Следующие шаги:** Настройка системы обновлений, разработка API сервера для синхронизации
