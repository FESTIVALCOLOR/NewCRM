# Interior Studio CRM

**Version:** 1.0.0
**Last updated:** 2026-02-08
**Language:** Python (PyQt5 desktop client + FastAPI server)

---

## Project overview

Interior Studio CRM is a desktop CRM application for an interior design studio. It has two operating modes:
- **Local mode** (`MULTI_USER_MODE = False`): Standalone SQLite-based desktop app
- **Multi-user mode** (`MULTI_USER_MODE = True`): Desktop client communicating with a FastAPI REST API backed by PostgreSQL

The desktop client is built with PyQt5 and packaged into a Windows .exe via PyInstaller.

---

## Directory structure

```
/home/user/NewCRM/
|-- main.py                     # Entry point: QApplication, styles, DB init, login window
|-- config.py                   # All configuration: paths, roles, API settings, FastAPI Settings class
|-- InteriorStudio.spec         # PyInstaller build config
|-- requirements.txt            # Desktop client dependencies (8 packages)
|-- docker-compose.yml          # PostgreSQL + FastAPI + Nginx stack
|-- .env.example                # Environment variable template
|-- deploy_crm.sh / install.sh  # Server deployment scripts
|
|-- database/
|   |-- __init__.py             # REQUIRED - makes this a Python package
|   `-- db_manager.py           # DatabaseManager class (~3900 lines): all SQL, migrations, CRUD
|
|-- ui/                         # PyQt5 UI modules (28 files, ~48000 lines total)
|   |-- __init__.py             # REQUIRED - makes this a Python package
|   |-- login_window.py         # Authentication window
|   |-- main_window.py          # Main tabbed window, role-based tab visibility
|   |-- clients_tab.py          # Client management CRUD
|   |-- contracts_tab.py        # Contract lifecycle management
|   |-- crm_tab.py              # Kanban board for projects (LARGEST file ~18700 lines)
|   |-- crm_supervision_tab.py  # Author supervision workflow (~5500 lines)
|   |-- dashboard_tab.py        # Statistics & KPIs
|   |-- employees_tab.py        # Staff management
|   |-- employee_reports_tab.py # Staff performance reports
|   |-- reports_tab.py          # Statistical reports with PDF export
|   |-- salaries_tab.py         # Payroll management
|   |-- rates_dialog.py         # Rate configuration dialog
|   |-- custom_title_bar.py     # Custom window title bar with logo
|   |-- custom_combobox.py      # ComboBox with scroll fix
|   |-- custom_dateedit.py      # Custom date picker
|   |-- custom_message_box.py   # Branded message dialogs
|   |-- file_gallery_widget.py  # Image gallery widget
|   |-- file_list_widget.py     # File listing widget
|   |-- file_preview_widget.py  # Document preview renderer
|   |-- variation_gallery_widget.py
|   |-- flow_layout.py          # Custom flow layout manager
|   `-- update_dialogs.py       # Auto-update UI dialogs
|
|-- utils/                      # Utility modules (21 files, ~10000 lines)
|   |-- __init__.py             # REQUIRED - makes this a Python package
|   |-- resource_path.py        # CRITICAL: resolves paths for both dev and PyInstaller exe
|   |-- icon_loader.py          # SVG icon loading with caching
|   |-- api_client.py           # REST API client with JWT auth, retry, timeout (~1600 lines)
|   |-- yandex_disk.py          # Yandex Disk cloud storage integration
|   |-- db_security.py          # Password hashing (bcrypt), encryption
|   |-- password_utils.py       # Password hash/verify utilities
|   |-- validators.py           # Email, phone, INN, OGRN, passport validation
|   |-- date_utils.py           # Date formatting, period calculations
|   |-- pdf_generator.py        # PDF generation with ReportLab
|   |-- preview_generator.py    # Image/PDF thumbnail generation
|   |-- logger.py               # Structured logging to file and console
|   |-- update_manager.py       # Version checking via Yandex Disk
|   |-- calendar_styles.py      # QCalendarWidget QSS styling
|   |-- global_styles.py        # Global QSS stylesheet
|   |-- custom_style.py         # Runtime style customization
|   |-- table_settings.py       # Table column width/sort persistence
|   |-- dialog_helpers.py       # Common dialog utilities
|   |-- tooltip_fix.py          # Multi-line tooltip support
|   |-- message_helper.py       # Message box display helpers
|   |-- tab_helpers.py          # Tab switching helpers
|   |-- migrate_passwords.py    # Password hash migration utility
|   |-- add_indexes.py          # Database index creation
|   `-- constants.py            # (empty, reserved)
|
|-- server/                     # FastAPI backend for multi-user mode
|   |-- __init__.py
|   |-- main.py                 # FastAPI app with all routes (~3500 lines)
|   |-- database.py             # SQLAlchemy ORM models (~600 lines)
|   |-- schemas.py              # Pydantic v2 validation schemas (~500 lines)
|   |-- auth.py                 # JWT authentication (~100 lines)
|   |-- config.py               # Server-specific settings
|   |-- yandex_disk_service.py  # Server-side Yandex Disk service
|   |-- Dockerfile              # FastAPI container build
|   |-- requirements.txt        # Server dependencies (12 packages)
|   `-- .env.example
|
|-- resources/                  # Static assets (bundled into exe via PyInstaller)
|   |-- styles.qss              # Main QSS stylesheet
|   |-- logo.png                # Application logo
|   |-- icon.ico                # App icon (main)
|   |-- icon32.ico .. icon256.ico  # Various icon sizes
|   `-- icons/                  # 54 SVG icons for UI buttons
|       |-- add.svg, delete.svg, edit.svg, refresh.svg, save.svg
|       |-- close.svg, minimize.svg, maximize.svg
|       |-- arrow-*.svg, check-*.svg, calendar.svg, etc.
|
|-- nginx/
|   `-- nginx.conf              # Reverse proxy config with SSL
|
`-- Root-level scripts (migration/test utilities, not part of the app):
    |-- add_*.py (12 files)     # DB migration scripts
    |-- fix_*.py (8 files)      # Codebase fix scripts
    |-- test_*.py (8 files)     # Test/check scripts
    |-- check_*.py (5 files)    # Data integrity checks
    |-- migrate_to_server.py    # Migration to multi-user mode
    `-- generate_icons.py       # SVG icon generation
```

---

## Critical rules for AI assistants

### 1. `__init__.py` files are REQUIRED

Every Python package directory (`database/`, `ui/`, `utils/`, `server/`) MUST have an `__init__.py` file. Without these, PyInstaller will not find the modules. They can be empty but must exist.

### 2. No emoji in UI code

NEVER use emoji characters in user-facing UI strings. Use plain text ("ВНИМАНИЕ", "УСПЕХ", "ОШИБКА") or SVG icons via `IconLoader`. Emoji are only acceptable in `print()` debug statements.

```python
# WRONG
label = QLabel('ВНИМАНИЕ')
button = QPushButton('Готово')

# RIGHT - plain text
label = QLabel('ВНИМАНИЕ')
button = QPushButton('Готово')

# RIGHT - SVG icon
from utils.icon_loader import IconLoader
button = IconLoader.create_icon_button('check', 'Готово', icon_size=14)
```

### 3. Always use `resource_path()` for static assets

All paths to files in `resources/` MUST go through `resource_path()`. Direct paths like `'resources/logo.png'` break in the PyInstaller exe.

```python
from utils.resource_path import resource_path

# Correct
logo = QPixmap(resource_path('resources/logo.png'))
icon = QIcon(resource_path('resources/icons/edit.svg'))
with open(resource_path('resources/styles.qss'), 'r') as f: ...

# Incorrect - breaks in exe
logo = QPixmap('resources/logo.png')
```

Files that MUST import `resource_path`:
- `main.py`, `ui/login_window.py`, `ui/custom_title_bar.py`
- `ui/crm_tab.py`, `ui/crm_supervision_tab.py`, `ui/reports_tab.py`
- `utils/icon_loader.py`, `utils/calendar_styles.py`

### 4. New modules must be registered in PyInstaller spec

When adding a new Python module, add it to `hiddenimports` in `InteriorStudio.spec`:

```python
hiddenimports=[
    ...
    'ui.new_module',      # Add new UI modules here
    'utils.new_utility',  # Add new utility modules here
    ...
]
```

### 5. Database is NOT bundled with the exe

The SQLite database (`interior_studio.db`) lives beside the exe, not inside it. Only `resources/` goes into the exe via `datas` in the spec file.

### 6. Multi-user mode awareness

The app has dual architecture. When `MULTI_USER_MODE = True` in `config.py`, the client uses `utils/api_client.py` to talk to the FastAPI server. When `False`, it uses `database/db_manager.py` directly with SQLite. Many tab modules check this flag to decide which data source to use.

---

## Technology stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Desktop GUI | PyQt5 | 5.15.9 |
| Local database | SQLite | (stdlib) |
| Server framework | FastAPI | 0.115.0 |
| Server database | PostgreSQL | 15-alpine |
| ORM | SQLAlchemy | 2.0.36 |
| Validation | Pydantic | 2.10.3 |
| Authentication | JWT (python-jose, HS256) | 3.3.0 |
| Cloud storage | Yandex Disk API | custom client |
| PDF generation | ReportLab | 4.0.7 |
| Data analysis | Pandas | 2.1.4 |
| Charts | Matplotlib | 3.8.2 |
| HTTP client | Requests | 2.31.0 |
| Packaging | PyInstaller | 6.3.0 |
| PDF reading | PyMuPDF | 1.23.8 |
| Containerization | Docker Compose | 3.8 |
| Reverse proxy | Nginx | alpine |

---

## Architecture

### Application flow

```
main.py
  -> QApplication init (High DPI, Fusion style, global styles)
  -> DatabaseManager.initialize_database() (runs migrations)
  -> LoginWindow
     -> auth via db_manager (local) or api_client (multi-user)
     -> MainWindow
        -> Tab loading based on user role
        -> Each tab uses db_manager or api_client
        -> Icons via IconLoader
        -> All resources via resource_path()
```

### Dual-mode data access

```
config.MULTI_USER_MODE = True:
  Client (PyQt5) --HTTPS--> FastAPI (server/main.py) --SQLAlchemy--> PostgreSQL
  Auth: JWT tokens, 30-min expiry (server), 24-hour (local Settings)
  Retry: 3 attempts with 1s delay, 10s timeout

config.MULTI_USER_MODE = False:
  Client (PyQt5) --direct--> SQLite (database/db_manager.py)
  Auth: local password hash verification
```

### Server deployment stack

```
docker-compose.yml:
  postgres (port 5432) -> crm_user / interior_studio_crm
  api (port 8000) -> FastAPI with uvicorn
  nginx (ports 80, 443) -> SSL termination, reverse proxy to api
```

Current server: `https://147.45.154.193` (Timeweb Cloud VPS)

---

## Role-based access control

9 roles defined in `config.py` with granular tab access:

| Role | Tabs | Can Edit | Can Assign |
|------|------|----------|-----------|
| Руководитель студии | All | Yes | All |
| Старший менеджер проектов | All | Yes | Project/Executive depts |
| СДП | CRM, Reports, Employees | Yes | No |
| ГАП | CRM, Reports, Employees | Yes | No |
| Менеджер | CRM, Employees | Yes | No |
| Дизайнер | CRM | Yes (own projects) | No |
| Чертёжник | CRM | Yes (own projects) | No |
| ДАН | CRM Supervision | Yes (own projects) | No |
| Замерщик | CRM | Read-only | No |

---

## Database schema (17 local tables)

Key tables in `database/db_manager.py`:

- **employees** - Users/staff with auth, roles, positions, status
- **clients** - Client records (individuals and organizations)
- **contracts** - Contract lifecycle (amounts, dates, files, status)
- **crm_cards** - Kanban cards for project management workflow
- **stage_executors** - Per-stage executor assignments for CRM cards
- **crm_supervision** / **supervision_cards** - Author supervision workflow
- **salaries** - Payroll records per contract/employee/stage
- **payments** - Payment tracking system
- **rates** - Rate configuration per position/stage/payment type
- **project_files** - File metadata (Yandex Disk integration)
- **action_history** - Audit trail of user actions
- **agents** - Agent reference table (ФЕСТИВАЛЬ, ПЕТРОВИЧ)
- **approval_stage_deadlines** - Approval workflow timing
- **manager_stage_acceptance** - Manager sign-off tracking
- **surveys** - Survey/measurement records

Server adds multi-user tables in `server/database.py`:
- **UserSession** - Token and activity tracking
- **UserPermission** - Granular access control
- **ActivityLog** - Server-side audit trail
- **ConcurrentEdit** - Optimistic locking for multi-user edits
- **Notification** - System notifications

Migrations run automatically in `DatabaseManager.initialize_database()`.

---

## API integration status

| Module | API Integration | Notes |
|--------|----------------|-------|
| Dashboard | 100% | Statistics endpoints |
| Clients | 100% | Full CRUD |
| Employees | 100% | Full CRUD |
| Contracts | ~70% | Missing file upload integration |
| CRM | 0% (prepared) | Routes exist, client not wired |
| CRM Supervision | 0% (prepared) | Routes exist, client not wired |
| Reports | 0% | Not started |
| Salaries | 0% | Not started |
| Employee Reports | 0% | Not started |

`utils/api_client.py` (`APIClient` class) handles all REST communication with JWT auth, retry logic (3 attempts), and 10-second timeouts.

---

## Key modules reference

### `database/db_manager.py` (~3900 lines)
Central database access layer. Contains:
- `DatabaseManager` class with all CRUD operations
- `initialize_database()` - creates tables and runs migrations
- All SQL queries for every entity type
- Migration methods that add columns/tables as needed

### `ui/crm_tab.py` (~18700 lines)
Largest file. Implements the Kanban-style CRM board with:
- Drag-and-drop card movement between columns
- Stage executor assignment
- Approval workflows
- File attachments (Yandex Disk)
- PDF generation for contracts

### `utils/api_client.py` (~1600 lines)
REST client with methods for every API endpoint:
- `login()`, `get_employees()`, `create_client()`, etc.
- JWT token management (auto-refresh)
- Custom exception hierarchy: `APIError`, `APITimeoutError`, `APIConnectionError`, `APIAuthError`, `APIResponseError`

### `server/main.py` (~3500 lines)
FastAPI application with 50+ endpoints covering all entity types. Uses SQLAlchemy ORM models from `server/database.py` and Pydantic schemas from `server/schemas.py`.

---

## Configuration (`config.py`)

Key settings:

```python
# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(BASE_DIR, 'interior_studio.db')

# Versioning
APP_VERSION = "1.0.0"
APP_NAME = "Interior Studio CRM"

# Multi-user
MULTI_USER_MODE = True
API_BASE_URL = "https://147.45.154.193"
SYNC_INTERVAL = 5  # seconds

# Updates
UPDATE_CHECK_ENABLED = True
UPDATE_YANDEX_PUBLIC_KEY = "SmxiWfUUEt8oEA"

# Domain constants
PROJECT_TYPES = ['Индивидуальный', 'Шаблонный']
AGENTS = ['ФЕСТИВАЛЬ', 'ПЕТРОВИЧ']
CITIES = ['СПБ', 'МСК', 'ВН']
PROJECT_STATUSES = ['СДАН', 'АВТОРСКИЙ НАДЗОР', 'РАСТОРГНУТ']

# FastAPI Settings class (used by server)
# secret_key, algorithm (HS256), access_token_expire_minutes (1440)
```

---

## Development commands

```bash
# Run desktop app (development)
python main.py

# Run database migrations
python -c "from database.db_manager import DatabaseManager; db = DatabaseManager(); db.initialize_database(); print('OK')"

# Verify module imports
python -c "from ui.login_window import LoginWindow; print('OK')"
python -c "from utils.icon_loader import IconLoader; print('OK')"

# Start FastAPI server locally
cd server && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Build Windows exe (on Windows)
pyinstaller InteriorStudio.spec --clean --noconfirm
cp interior_studio.db dist/interior_studio.db

# Docker deployment
docker-compose up -d --build

# Check server health
curl -k https://147.45.154.193/health
```

---

## PyInstaller spec rules

The `InteriorStudio.spec` file controls exe building:

- **datas**: Only `('resources', 'resources')` -- static assets only
- **hiddenimports**: All Python modules from `ui/`, `database/`, `utils/`
- **console=False**: GUI application, no console window
- **icon**: `resources/icon.ico`
- Do NOT add `database/`, `ui/`, `utils/` to `datas` -- they are Python modules, not data files

---

## Common issues and solutions

| Problem | Cause | Fix |
|---------|-------|-----|
| `No module named 'ui.xxx'` | Missing `__init__.py` | Create empty `__init__.py` in the package dir |
| `no such column: cc.xxx` | Outdated DB in dist/ | Run app via Python to trigger migrations, copy DB |
| Resources missing in exe | Not using `resource_path()` | Wrap all resource paths with `resource_path()` |
| Icons not showing | Direct paths in IconLoader | Use `resource_path()` in icon loading code |
| App icon missing from taskbar | Not set in `main.py` | `app.setWindowIcon(QIcon(resource_path('resources/icon.ico')))` |
| `Permission denied` during build | exe is running | Kill `InteriorStudio.exe` process first |
| API connection errors | Server unreachable or SSL | Check `API_BASE_URL`, SSL cert, server status |
| Pydantic import errors | v1 vs v2 | Use `pydantic-settings` for `BaseSettings` (v2) |

---

## Pre-build checklist

- [ ] All `__init__.py` files exist (database, ui, utils, server)
- [ ] All resource paths use `resource_path()`
- [ ] New modules added to `hiddenimports` in spec
- [ ] Version updated in `config.py` if releasing
- [ ] Database migrations run without errors
- [ ] App launches successfully via `python main.py`

---

## Dependencies

### Desktop client (`requirements.txt`)
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

### Server (`server/requirements.txt`)
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

## Update system

Files: `config.py` (version constants), `utils/update_manager.py`, `ui/update_dialogs.py`

Process: bump `APP_VERSION` in `config.py` -> build exe -> upload to Yandex Disk -> update `version.json` -> clients auto-detect update.

---

## File storage (Yandex Disk)

Cloud file storage is handled by `utils/yandex_disk.py` (client-side) and `server/yandex_disk_service.py` (server-side). Used for:
- Contract PDF uploads
- Technical task documents
- Survey data
- Database backups

Token is configured in `config.py` as `YANDEX_DISK_TOKEN`.

---

**Status:** Desktop app works, exe builds correctly, server deployed on Timeweb Cloud. API integration ~40% complete (Dashboard, Clients, Employees done; Contracts partial; CRM/Reports/Salaries pending).
