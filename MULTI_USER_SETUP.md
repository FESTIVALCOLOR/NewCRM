# Пошаговая инструкция: Настройка многопользовательской CRM

## Обзор архитектуры

```
┌─────────────────────────────┐
│   PyQt5 Клиенты (Windows)   │
│   - Установлен на компьютере│
│   - Локальный кэш           │
│   - Синхронизация каждые 5с │
└──────────┬──────────────────┘
           │ HTTP REST API
           │ JWT токены
           ▼
┌─────────────────────────────┐
│  Railway.app (Сервер)       │
│  - FastAPI приложение       │
│  - PostgreSQL база          │
│  - SSL/HTTPS автоматически  │
└──────────┬──────────────────┘
           │ REST API
           ▼
┌─────────────────────────────┐
│   Яндекс.Диск               │
│  - Хранение файлов          │
│  - Бэкап базы данных        │
└─────────────────────────────┘
```

---

## ЧАСТЬ 1: Настройка сервера на Railway.app

### Шаг 1.1: Регистрация на Railway.app

1. Перейдите на https://railway.app
2. Нажмите "Login" → выберите "Login with GitHub"
3. Авторизуйте Railway доступ к GitHub

**Результат:** Вы попадете в Dashboard Railway

---

### Шаг 1.2: Создание GitHub репозитория

1. Создайте новый репозиторий на GitHub:
   - Название: `interior-studio-server`
   - Private или Public (на ваше усмотрение)
   - НЕ создавайте README

2. Инициализируйте Git в папке сервера:

```powershell
cd "d:\New CRM\interior_studio"

# Инициализация Git
git init

# Добавление серверных файлов
git add server/
git commit -m "Initial server setup"

# Связываем с GitHub (замените YOUR_USERNAME)
git remote add origin https://github.com/YOUR_USERNAME/interior-studio-server.git
git branch -M main
git push -u origin main
```

**Результат:** Код сервера загружен на GitHub

---

### Шаг 1.3: Создание проекта на Railway

1. В Railway нажмите **"New Project"**
2. Выберите **"Deploy from GitHub repo"**
3. Выберите репозиторий `interior-studio-server`
4. Railway автоматически обнаружит `Dockerfile` и начнет сборку

**Результат:** Через 3-5 минут приложение задеплоится

---

### Шаг 1.4: Добавление PostgreSQL базы

1. В вашем проекте нажмите **"New"** → **"Database"** → **"Add PostgreSQL"**
2. Railway автоматически создаст базу данных
3. Переменная `DATABASE_URL` добавится автоматически

**Результат:** База данных PostgreSQL готова

---

### Шаг 1.5: Генерация секретного ключа

Запустите в командной строке:

```powershell
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

**Скопируйте результат** (примерно 64 символа)

---

### Шаг 1.6: Получение токена Яндекс.Диска

#### 1. Создайте приложение на Яндекс.OAuth:

1. Перейдите на https://oauth.yandex.ru/client/new
2. Заполните форму:
   - **Название:** Interior Studio CRM
   - **Платформы:** Веб-сервисы
   - **Redirect URI:** `https://oauth.yandex.ru/verification_code`
   - **Права доступа:**
     - ✅ Яндекс.Диск REST API: Запись
     - ✅ Яндекс.Диск REST API: Чтение
3. Нажмите **"Создать приложение"**
4. **Скопируйте ClientID** (будет выглядеть как: `abc123def456...`)

#### 2. Получите токен доступа:

1. Откройте в браузере (замените YOUR_CLIENT_ID):
```
https://oauth.yandex.ru/authorize?response_type=token&client_id=YOUR_CLIENT_ID
```

2. Нажмите **"Разрешить"**
3. В URL появится токен после `#access_token=`
4. **Скопируйте токен** (начинается с `y0_`)

**Результат:** У вас есть `YANDEX_DISK_TOKEN`

---

### Шаг 1.7: Настройка переменных окружения в Railway

1. В Railway откройте ваш проект
2. Перейдите на вкладку **"Variables"**
3. Добавьте следующие переменные:

| Переменная | Значение | Пример |
|------------|----------|--------|
| `SECRET_KEY` | Сгенерированный ключ из Шага 1.5 | `a1b2c3d4...` |
| `YANDEX_DISK_TOKEN` | Токен из Шага 1.6 | `y0_AgAAAAA...` |
| `APP_NAME` | Interior Studio CRM API | (текст) |
| `APP_VERSION` | 1.0.0 | (текст) |
| `DEBUG` | false | (текст) |
| `MAX_FILE_SIZE_MB` | 50 | (число) |

4. Нажмите **"Add"** после каждой переменной

**Результат:** Переменные окружения настроены

---

### Шаг 1.8: Получение URL сервера

1. В Railway откройте **"Settings"**
2. В разделе **"Domains"** нажмите **"Generate Domain"**
3. **Скопируйте URL** (например: `interior-studio-production.up.railway.app`)

**Результат:** У вас есть публичный URL сервера

---

### Шаг 1.9: Проверка работы сервера

Откройте в браузере:
```
https://ваш-домен.railway.app
```

Должны увидеть:
```json
{
  "app": "Interior Studio CRM API",
  "version": "1.0.0",
  "status": "running"
}
```

**Результат:** Сервер работает!

---

### Шаг 1.10: Создание администратора

#### Вариант А: Через Railway CLI (рекомендуется)

1. Установите Railway CLI:
```powershell
npm install -g @railway/cli
```

2. Войдите:
```powershell
railway login
```

3. Свяжите с проектом:
```powershell
cd "d:\New CRM\interior_studio\server"
railway link
```

4. Создайте файл `create_admin.py` в `server/`:

```python
from database import SessionLocal, Employee
from auth import get_password_hash
from datetime import datetime

db = SessionLocal()

# ВАЖНО: Замените данные на свои!
admin = Employee(
    full_name="Ваше Имя",
    phone="+7 999 000-00-00",
    email="your@email.com",
    login="admin",
    password_hash=get_password_hash("YourStrongPassword123!"),
    position="Руководитель студии",
    department="Управление",
    role="Руководитель студии",
    status="активный",
    created_at=datetime.utcnow(),
    updated_at=datetime.utcnow()
)

db.add(admin)
db.commit()

print(f"✓ Администратор создан: {admin.full_name} (ID: {admin.id})")
db.close()
```

5. Запустите через Railway:
```powershell
railway run python create_admin.py
```

#### Вариант Б: Через SQL в DBeaver

1. В Railway откройте PostgreSQL сервис
2. Скопируйте строку подключения из "Connect"
3. Подключитесь через DBeaver
4. Выполните SQL:

```sql
INSERT INTO employees (
    full_name, phone, email, login, password_hash,
    position, department, role, status, created_at, updated_at
) VALUES (
    'Ваше Имя',
    '+7 999 000-00-00',
    'your@email.com',
    'admin',
    -- Хэш для "admin123" - ОБЯЗАТЕЛЬНО ЗАМЕНИТЕ!
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oDgbHQJO9EGu',
    'Руководитель студии',
    'Управление',
    'Руководитель студии',
    'активный',
    NOW(),
    NOW()
);
```

**Результат:** Администратор создан

---

## ЧАСТЬ 2: Настройка PyQt5 клиента

### Шаг 2.1: Обновление config.py

Откройте `d:\New CRM\interior_studio\config.py` и добавьте:

```python
# =========================
# МНОГОПОЛЬЗОВАТЕЛЬСКИЙ РЕЖИМ
# =========================

# Включить многопользовательский режим
MULTI_USER_MODE = True

# URL сервера (замените на ваш Railway URL)
API_BASE_URL = "https://ваш-домен.railway.app"

# Интервал синхронизации (секунды)
SYNC_INTERVAL = 5

# Локальный кэш
CACHE_ENABLED = True
CACHE_PATH = "cache/"
```

---

### Шаг 2.2: Создание менеджера синхронизации

Создайте файл `utils/sync_manager.py`:

```python
"""
Менеджер синхронизации с сервером
Обновляет данные каждые 5 секунд
"""
from PyQt5.QtCore import QTimer, QObject, pyqtSignal
from datetime import datetime
from utils.api_client import APIClient
from config import API_BASE_URL, SYNC_INTERVAL


class SyncManager(QObject):
    """Автоматическая синхронизация с сервером"""

    # Сигналы для обновления UI
    clients_updated = pyqtSignal(list)
    contracts_updated = pyqtSignal(list)
    employees_updated = pyqtSignal(list)
    notifications_received = pyqtSignal(list)

    def __init__(self, api_client: APIClient):
        super().__init__()
        self.api_client = api_client
        self.last_sync = datetime.utcnow()
        self.timer = QTimer()
        self.timer.timeout.connect(self.sync)

    def start(self):
        """Запустить автоматическую синхронизацию"""
        self.timer.start(SYNC_INTERVAL * 1000)
        print(f"[SYNC] Синхронизация запущена (каждые {SYNC_INTERVAL}с)")

    def stop(self):
        """Остановить синхронизацию"""
        self.timer.stop()
        print("[SYNC] Синхронизация остановлена")

    def sync(self):
        """Синхронизация с сервером"""
        try:
            # Запрашиваем обновления
            response = self.api_client.sync(
                last_sync_timestamp=self.last_sync,
                entity_types=['clients', 'contracts', 'employees']
            )

            # Отправляем сигналы если есть обновления
            if response.get('clients'):
                self.clients_updated.emit(response['clients'])

            if response.get('contracts'):
                self.contracts_updated.emit(response['contracts'])

            if response.get('employees'):
                self.employees_updated.emit(response['employees'])

            if response.get('notifications'):
                self.notifications_received.emit(response['notifications'])

            # Обновляем время последней синхронизации
            self.last_sync = datetime.fromisoformat(response['timestamp'])

        except Exception as e:
            print(f"[ERROR] Ошибка синхронизации: {e}")
```

---

### Шаг 2.3: Модификация login_window.py

Измените аутентификацию для работы с API:

```python
# В ui/login_window.py

from utils.api_client import APIClient
from config import API_BASE_URL, MULTI_USER_MODE

class LoginWindow(QDialog):
    def __init__(self):
        super().__init__()
        # ...
        # Инициализация API клиента
        if MULTI_USER_MODE:
            self.api_client = APIClient(API_BASE_URL)

    def check_login(self):
        login = self.login_input.text().strip()
        password = self.password_input.text()

        if MULTI_USER_MODE:
            # Аутентификация через API
            try:
                result = self.api_client.login(login, password)
                self.employee_id = result['employee_id']
                self.employee_role = result['role']
                self.employee_name = result['full_name']
                self.accept()
            except Exception as e:
                CustomMessageBox.critical(
                    self,
                    "Ошибка входа",
                    f"Не удалось войти: {str(e)}"
                )
        else:
            # Старая логика (локальная база)
            # ...
```

---

### Шаг 2.4: Модификация main_window.py

Добавьте синхронизацию в главное окно:

```python
# В ui/main_window.py

from utils.sync_manager import SyncManager
from config import MULTI_USER_MODE

class MainWindow(QMainWindow):
    def __init__(self, employee_id, employee_role, employee_name):
        super().__init__()
        # ...

        if MULTI_USER_MODE:
            # Инициализация синхронизации
            self.sync_manager = SyncManager(self.api_client)
            self.sync_manager.clients_updated.connect(self.on_clients_updated)
            self.sync_manager.contracts_updated.connect(self.on_contracts_updated)
            self.sync_manager.start()

    def on_clients_updated(self, clients):
        """Обработка обновления клиентов"""
        # Обновить таблицу клиентов
        if hasattr(self, 'clients_tab'):
            self.clients_tab.refresh_data()

    def on_contracts_updated(self, contracts):
        """Обработка обновления договоров"""
        # Обновить таблицу договоров
        if hasattr(self, 'contracts_tab'):
            self.contracts_tab.refresh_data()

    def closeEvent(self, event):
        """При закрытии окна"""
        if MULTI_USER_MODE:
            self.sync_manager.stop()
            self.api_client.logout()
        super().closeEvent(event)
```

---

## ЧАСТЬ 3: Тестирование

### Шаг 3.1: Проверка подключения

1. Запустите клиент:
```powershell
.venv\Scripts\python.exe main.py
```

2. Войдите с логином/паролем администратора
3. Проверьте логи в консоли:
```
[SYNC] Синхронизация запущена (каждые 5с)
[INFO] Подключено к серверу: https://...
```

---

### Шаг 3.2: Проверка создания клиента

1. Создайте нового клиента через интерфейс
2. Откройте Railway → "Deployments" → "View Logs"
3. Должны увидеть в логах:
```
INFO: POST /api/clients 200 OK
```

---

### Шаг 3.3: Проверка многопользовательской работы

1. Установите клиент на 2 компьютера
2. Войдите на обоих
3. Создайте клиента на компьютере №1
4. Через 5 секунд он появится на компьютере №2

**Результат:** Многопользовательский режим работает!

---

## ЧАСТЬ 4: Мониторинг и обслуживание

### Просмотр логов сервера

Railway → ваш проект → "Deployments" → "View Logs"

### Просмотр метрик

Railway → ваш проект → "Metrics"
- CPU usage
- Memory usage
- Request count

### Резервное копирование базы

```powershell
# Установка Railway CLI
npm install -g @railway/cli

# Вход
railway login

# Бэкап
railway pg:dump > backup-$(date +%Y%m%d).sql
```

### Обновление сервера

```powershell
cd "d:\New CRM\interior_studio"
git add server/
git commit -m "Update server"
git push
```

Railway автоматически задеплоит новую версию.

---

## Стоимость

### Railway.app Hobby Plan (бесплатно):
- $5 кредитов/месяц
- ~500 часов работы
- PostgreSQL 1GB
- Достаточно для 5-10 пользователей

### При превышении лимита:
- Developer Plan: $5/мес фиксировано + по использованию
- Или оптимизировать: уменьшить SYNC_INTERVAL до 10-15 секунд

---

## Поддержка

**Документация:**
- Railway: https://docs.railway.app
- FastAPI: https://fastapi.tiangolo.com
- Яндекс.Диск API: https://yandex.ru/dev/disk/

**Проблемы:**
- Railway Discord: https://discord.gg/railway
- GitHub Issues: создайте issue в репозитории

---

## Что дальше?

1. **Добавьте всех сотрудников** через интерфейс администратора
2. **Настройте права доступа** для каждой роли
3. **Мигрируйте данные** из локальной SQLite в PostgreSQL
4. **Настройте Яндекс.Диск** для хранения файлов проектов
5. **Обучите сотрудников** работе с новой системой

Удачи!
