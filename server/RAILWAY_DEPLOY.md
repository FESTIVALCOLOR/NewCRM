# Инструкция по развертыванию на Railway.app

## Шаг 1: Подготовка

### 1.1. Создайте аккаунт на Railway.app
1. Перейдите на https://railway.app
2. Нажмите "Start a New Project"
3. Войдите через GitHub

### 1.2. Создайте репозиторий на GitHub
```bash
cd "d:\New CRM\interior_studio"
git init
git add server/
git commit -m "Initial server setup"
git remote add origin https://github.com/YOUR_USERNAME/interior-studio-server.git
git push -u origin main
```

## Шаг 2: Создание проекта на Railway

### 2.1. Создать новый проект
1. В Railway нажмите "New Project"
2. Выберите "Deploy from GitHub repo"
3. Выберите ваш репозиторий `interior-studio-server`
4. Railway автоматически обнаружит Dockerfile

### 2.2. Добавить PostgreSQL базу данных
1. В вашем проекте нажмите "New" → "Database" → "Add PostgreSQL"
2. Railway автоматически создаст базу и добавит переменную `DATABASE_URL`

### 2.3. Настроить переменные окружения
В разделе "Variables" добавьте:

```bash
# Секретный ключ для JWT (сгенерировать новый!)
SECRET_KEY=your-very-secret-key-change-this

# Токен Яндекс.Диска
YANDEX_DISK_TOKEN=y0_ваш_токен_яндекс_диска

# Настройки приложения
APP_NAME=Interior Studio CRM API
APP_VERSION=1.0.0
DEBUG=false

# CORS (замените на ваш домен клиента)
ALLOWED_ORIGINS=https://your-client-app.com

# Настройки файлов
MAX_FILE_SIZE_MB=50
FILE_STORAGE_PATH=/app/uploads
PREVIEW_CACHE_PATH=/app/previews
```

## Шаг 3: Генерация секретного ключа

### Локально (Windows):
```powershell
# Установите OpenSSL если нет
# Или используйте Python:
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_hex(32))"
```

Скопируйте результат в `SECRET_KEY`

## Шаг 4: Получение токена Яндекс.Диска

### 4.1. Создайте приложение на Яндекс.OAuth
1. Перейдите на https://oauth.yandex.ru/
2. Нажмите "Зарегистрировать новое приложение"
3. Заполните:
   - Название: "Interior Studio CRM"
   - Платформа: "Веб-сервисы"
   - Права: "Яндекс.Диск: Запись", "Яндекс.Диск: Чтение"
   - Redirect URI: https://oauth.yandex.ru/verification_code

### 4.2. Получите токен
1. После создания приложения скопируйте Client ID
2. Перейдите по ссылке:
```
https://oauth.yandex.ru/authorize?response_type=token&client_id=ВАШ_CLIENT_ID
```
3. Разрешите доступ
4. Скопируйте токен из URL (после #access_token=)
5. Добавьте в Railway Variables как `YANDEX_DISK_TOKEN`

## Шаг 5: Деплой

### 5.1. Автоматический деплой
Railway автоматически задеплоит после коммита в GitHub:
```bash
cd "d:\New CRM\interior_studio"
git add server/
git commit -m "Add server configuration"
git push
```

### 5.2. Проверка деплоя
1. В Railway откройте вкладку "Deployments"
2. Дождитесь статуса "Success" (3-5 минут)
3. Нажмите "View Logs" чтобы увидеть логи

### 5.3. Получить URL сервера
1. В Railway откройте вкладку "Settings"
2. В разделе "Domains" нажмите "Generate Domain"
3. Скопируйте URL (например: `interior-studio-production.up.railway.app`)

## Шаг 6: Тестирование API

### 6.1. Проверка health check
```bash
curl https://ваш-домен.railway.app/health
```

Должно вернуть:
```json
{"status": "healthy"}
```

### 6.2. Тестовый запрос (Postman или curl)
```bash
curl https://ваш-домен.railway.app/
```

Должно вернуть:
```json
{
  "app": "Interior Studio CRM API",
  "version": "1.0.0",
  "status": "running"
}
```

## Шаг 7: Создание первого пользователя

### 7.1. Подключитесь к PostgreSQL
1. В Railway откройте PostgreSQL сервис
2. Нажмите "Connect" → скопируйте строку подключения
3. Используйте psql или DBeaver для подключения

### 7.2. Создайте администратора
```sql
INSERT INTO employees (
    full_name,
    phone,
    login,
    password_hash,
    position,
    department,
    role,
    status
) VALUES (
    'Администратор',
    '+7 999 000-00-00',
    'admin',
    -- Хэш для пароля "admin123" (ЗАМЕНИТЕ В ПРОДАКШЕНЕ!)
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewY5oDgbHQJO9EGu',
    'Руководитель студии',
    'Управление',
    'Руководитель студии',
    'активный'
);
```

### 7.3. Или через скрипт миграции
Создайте файл `server/create_admin.py`:

```python
from database import SessionLocal, Employee
from auth import get_password_hash

db = SessionLocal()

admin = Employee(
    full_name="Администратор",
    phone="+7 999 000-00-00",
    login="admin",
    password_hash=get_password_hash("admin123"),  # ЗАМЕНИТЕ!
    position="Руководитель студии",
    department="Управление",
    role="Руководитель студии",
    status="активный"
)

db.add(admin)
db.commit()
print("Администратор создан")
```

Запустите в Railway CLI:
```bash
railway run python create_admin.py
```

## Шаг 8: Обновление клиента (PyQt5)

Измените `config.py` в клиенте:

```python
# config.py
API_BASE_URL = "https://ваш-домен.railway.app"
```

## Шаг 9: Мониторинг и логи

### 9.1. Просмотр логов в реальном времени
В Railway:
1. Откройте "Deployments"
2. Нажмите "View Logs"

### 9.2. Метрики
Railway показывает:
- CPU usage
- Memory usage
- Network traffic
- Request count

## Шаг 10: Обновление приложения

### Автоматическое обновление:
```bash
cd "d:\New CRM\interior_studio"
# Внесите изменения в server/
git add server/
git commit -m "Update server"
git push
```

Railway автоматически пересоберет и задеплоит новую версию.

## Стоимость

### Railway.app тарифы:
- **Hobby Plan** (бесплатно):
  - $5 кредитов/месяц (~500 часов работы)
  - 512 MB RAM
  - 1 GB диск
  - PostgreSQL база
  - Достаточно для 5-10 пользователей

- **Developer Plan** ($5/месяц):
  - $5 фиксированная плата + дополнительные ресурсы
  - 8 GB RAM
  - 100 GB диск
  - Приоритетная поддержка

### Рекомендации:
1. Начните с Hobby Plan
2. Мониторьте использование в разделе "Usage"
3. При превышении лимитов перейдите на Developer Plan

## Резервное копирование

### Автоматический бэкап PostgreSQL:
Railway делает snapshot базы каждые 24 часа (хранится 7 дней).

### Ручной бэкап:
```bash
# Скачать дамп базы
railway pg:dump > backup.sql

# Восстановить из дампа
railway pg:restore < backup.sql
```

## Безопасность

1. **ОБЯЗАТЕЛЬНО** смените пароль администратора после первого входа
2. **ОБЯЗАТЕЛЬНО** сгенерируйте новый SECRET_KEY (не используйте дефолтный!)
3. Настройте CORS только для ваших доменов
4. Включите HTTPS (Railway предоставляет автоматически)
5. Регулярно обновляйте зависимости:
   ```bash
   pip list --outdated
   ```

## Проблемы и решения

### Приложение не запускается
- Проверьте логи: "Deployments" → "View Logs"
- Убедитесь что все переменные окружения заданы
- Проверьте что DATABASE_URL правильный

### Ошибка подключения к БД
- Railway автоматически создает DATABASE_URL
- Убедитесь что PostgreSQL сервис запущен

### Файлы не сохраняются
- Railway использует эфемерный диск (файлы удаляются при рестарте)
- Используйте Яндекс.Диск для постоянного хранения

## Поддержка

- Документация Railway: https://docs.railway.app
- Discord Railway: https://discord.gg/railway
- GitHub Issues: создайте issue в вашем репозитории
