# 21. Безопасность — Interior Studio CRM

> Дата: 2026-02-16 | Версия: 1.0

---

## Общий уровень безопасности: ~82%

| Категория | Оценка | Вес | Комментарий |
|-----------|--------|-----|-------------|
| Транспорт (SSL/TLS) | 95% | 15% | HTTPS + Let's Encrypt + HSTS + HTTP→HTTPS редирект |
| Аутентификация | 85% | 20% | JWT access+refresh, bcrypt, auto-refresh, валидация паролей |
| Авторизация (RBAC) | 75% | 15% | 9 ролей, IDOR-защита, но нет granular permissions в БД |
| Сетевая безопасность | 90% | 15% | SSH 2222, fail2ban, PostgreSQL закрыт, API только через nginx |
| Защита данных | 80% | 10% | HMAC offline-очередь, пароли bcrypt, секреты в env |
| Инфраструктура | 85% | 10% | Docker non-root, auto-cleanup, бэкапы, мониторинг |
| Заголовки безопасности | 90% | 5% | X-Content-Type, X-Frame, XSS-Protection, HSTS, Referrer, Permissions |
| CORS | 85% | 5% | Конкретные origins, credentials=True, без wildcard |
| Логирование и аудит | 70% | 5% | ActivityLog, auth.log, но нет алертов при инцидентах |

**Итого: ~82% (взвешенная оценка)**

---

## Что внедрено

### 1. SSL/TLS (HTTPS)

| Параметр | Значение |
|----------|----------|
| Домен | `crm.festivalcolor.ru` |
| Сертификат | Let's Encrypt (автообновление) |
| Протоколы | TLSv1.2, TLSv1.3 |
| HSTS | `max-age=31536000; includeSubDomains` |
| HTTP → HTTPS | 301 редирект через nginx |
| Автообновление | certbot timer + deploy hook (копирует в nginx, рестарт) |

**Файлы:**
- `/opt/interior_studio/nginx/nginx.conf` — конфигурация nginx
- `/opt/interior_studio/nginx/ssl/` — сертификаты
- `/etc/letsencrypt/renewal-hooks/deploy/copy-to-nginx.sh` — hook автообновления
- `config.py` — `API_VERIFY_SSL = True`

### 2. JWT аутентификация

| Параметр | Значение |
|----------|----------|
| Алгоритм | HS256 |
| Access token TTL | 60 минут |
| Refresh token TTL | 7 дней |
| Auto-refresh | За 5 мин до истечения (клиент, незаметно для пользователя) |
| SECRET_KEY | Обязательная генерация в production (RuntimeError при дефолтном) |

**Механизм auto-refresh (utils/api_client.py):**
```python
TOKEN_REFRESH_THRESHOLD = 300  # секунд до истечения

def _auto_refresh_if_needed(self):
    """Вызывается перед каждым API запросом"""
    if self._is_token_expiring_soon() and not self._is_refreshing:
        self.refresh_access_token()
```

**Файлы:**
- `server/auth.py` — создание/валидация JWT
- `server/config.py` — настройки TTL, SECRET_KEY
- `utils/api_client.py` — auto-refresh, извлечение exp из JWT

### 3. Хэширование паролей

| Параметр | Значение |
|----------|----------|
| Алгоритм | bcrypt (сервер) / PBKDF2-SHA256 (клиент offline) |
| Итерации PBKDF2 | 100 000 (рекомендация OWASP) |
| Соль | 16 байт (128 бит), уникальная для каждого пароля |
| Plaintext пароли | ЗАПРЕЩЕНЫ — verify_password возвращает False |
| Timing attacks | Защита через `secrets.compare_digest()` |

**Валидация пароля при создании (server/schemas.py):**
- Минимум 6 символов
- Обязательно буквы + цифры

**Файлы:**
- `server/auth.py` — bcrypt 4.2.1 (напрямую, без passlib)
- `utils/password_utils.py` — PBKDF2 для offline

### 4. Сетевая безопасность

| Компонент | Конфигурация |
|-----------|-------------|
| SSH порт | 2222 (вместо стандартного 22) |
| fail2ban | 3 попытки → бан на 1 час, окно 10 мин |
| PostgreSQL | Закрыт снаружи (`expose: 5432`, не `ports`) |
| API (8000) | Закрыт снаружи (`127.0.0.1:8000:8000`) |
| Доступ к API | Только через nginx (443 → 8000) |
| HTTP (80) | Только редирект на HTTPS |

**Файлы:**
- `/etc/ssh/sshd_config` — Port 2222
- `/etc/fail2ban/jail.local` — конфигурация fail2ban
- `docker-compose.yml` — порты контейнеров
- `~/.ssh/config` — SSH-конфиг клиента (Port 2222)

### 5. Security Headers (middleware)

```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
Strict-Transport-Security: max-age=31536000; includeSubDomains (только HTTPS)
```

**Файл:** `server/main.py` — middleware `add_security_headers`

### 6. CORS

| Параметр | Значение |
|----------|----------|
| Origins | `https://crm.festivalcolor.ru`, `http://localhost:3000` |
| Credentials | True |
| Methods | GET, POST, PUT, PATCH, DELETE, OPTIONS |
| Headers | Content-Type, Authorization, X-Requested-With |

Wildcard `*` запрещён при `allow_credentials=True`.

**Файлы:**
- `server/main.py` — CORSMiddleware
- `docker-compose.yml` — `ALLOWED_ORIGINS` env

### 7. IDOR-защита

- Старший менеджер не может изменять Руководителя студии
- Старший менеджер не может назначать защищённые роли
- Проверка принадлежности ресурса текущему пользователю
- Path traversal: отклонение `..` в путях загрузки файлов
- Лимит размера файлов (50 МБ)

**Файл:** `server/main.py` — endpoint-уровневые проверки

### 8. Rate Limiting

| Параметр | Значение |
|----------|----------|
| Лимит входа | 5 попыток за 15 мин на IP |
| Хранение | ActivityLog в PostgreSQL (переживает рестарты) |
| Fallback | In-memory dict (если БД недоступна) |

**Файл:** `server/main.py` — `/api/auth/login`

### 9. Offline безопасность

| Компонент | Защита |
|-----------|--------|
| Offline-очередь | HMAC-SHA256 подпись каждой операции |
| HMAC ключ | Автогенерация в `.offline_hmac_key` (в .gitignore) |
| Race condition | `_is_syncing` проверка под lock до создания потока |
| Невалидные записи | Пропускаются при синхронизации |

**Файлы:**
- `utils/offline_manager.py` — HMAC подписи
- `.gitignore` — `.offline_hmac_key`

### 10. Docker безопасность

| Параметр | Значение |
|----------|----------|
| API контейнер | Запускается от `appuser` (UID 1000), не root |
| PostgreSQL | Доступен только внутри Docker-сети |
| Volumes | uploads, previews, postgres_data — persistent |

**Файлы:**
- `server/Dockerfile` — `USER appuser`
- `docker-compose.yml` — `expose` вместо `ports`

### 11. Бэкап БД

| Параметр | Значение |
|----------|----------|
| Расписание | Ежедневно в 4:00 (cron) |
| Локальное хранение | `/opt/interior_studio/backups/`, 14 дней |
| Удалённое хранение | Яндекс.Диск `CRM/Бэкапы/`, 30 дней |
| Размер бэкапа | ~276 КБ (gzip) |
| Скрипт | `/opt/interior_studio/scripts/backup-db.sh` |

### 12. Автоматическая очистка диска

| Параметр | Значение |
|----------|----------|
| Расписание | Ежедневно в 3:00 (cron) |
| Docker build cache | Полная очистка |
| Pip кэш | Удаление |
| Journald | Ограничение 100 МБ |
| btmp логи | Обнуление |
| Мониторинг | Еженедельно, авто-очистка при >80% |

**Скрипты:**
- `/opt/interior_studio/scripts/docker-cleanup.sh`
- `/opt/interior_studio/scripts/disk-monitor.sh`

---

## Cron-расписание сервера

```
0 3 * * *  /opt/interior_studio/scripts/docker-cleanup.sh    # Очистка диска
0 4 * * *  /opt/interior_studio/scripts/backup-db.sh          # Бэкап БД
0 9 * * 1  /opt/interior_studio/scripts/disk-monitor.sh       # Мониторинг (пн)
```

---

## Что ещё можно улучшить (оставшиеся ~18%)

### Высокий приоритет

| # | Мера | Эффект | Сложность |
|---|------|--------|-----------|
| 1 | **Сменить пароль admin/admin123** | Защита от несанкционированного доступа | 5 мин |
| 2 | **SSH по ключам only** (отключить пароли) | Исключает брутфорс полностью | 10 мин |
| 3 | **Granular permissions в БД** | Точные права вместо ролевых проверок в коде | 2-4 часа |

### Средний приоритет

| # | Мера | Эффект | Сложность |
|---|------|--------|-----------|
| 4 | WAF (fail2ban для nginx) | Защита от SQL-injection/XSS на уровне запросов | 30 мин |
| 5 | Алерты при инцидентах (Telegram бот) | Оперативное уведомление при атаках | 1-2 часа |
| 6 | Content-Security-Policy header | Защита от XSS через inline-скрипты | 15 мин |
| 7 | Автоматический бан после N неудач по API login | Rate limit уже есть, но бан IP — нет | 30 мин |

### Низкий приоритет (nice-to-have)

| # | Мера | Эффект | Сложность |
|---|------|--------|-----------|
| 8 | Аудит-лог всех действий пользователей | Отслеживание кто что менял | 2-4 часа |
| 9 | Двухфакторная аутентификация (2FA/TOTP) | Дополнительный уровень защиты входа | 4-8 часов |
| 10 | Шифрование бэкапов (GPG) | Защита данных при утечке бэкапа | 30 мин |
| 11 | VPN для SSH (WireGuard) | SSH недоступен из интернета | 1-2 часа |

---

## Конфигурация окружения

### Клиент (.env)
```env
API_BASE_URL=https://crm.festivalcolor.ru
API_VERIFY_SSL=true
```

### Сервер (docker-compose.yml env)
```env
SECRET_KEY=<сгенерированный openssl rand -hex 32>
POSTGRES_PASSWORD=<сгенерированный openssl rand -base64 24>
ALLOWED_ORIGINS=https://crm.festivalcolor.ru,http://localhost:3000
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### SSH
```
Host timeweb
    HostName 147.45.154.193
    Port 2222
    User root
    IdentityFile ~/.ssh/id_ed25519
```

---

## Инфраструктура сервера

```
┌─────────────────────────────────────────────┐
│            147.45.154.193                    │
│            crm.festivalcolor.ru              │
├─────────────────────────────────────────────┤
│                                              │
│  Интернет ──► :443 (nginx)                  │
│               │ SSL termination              │
│               │ HSTS, Security Headers       │
│               ▼                              │
│           :8000 (FastAPI) ◄── только локально│
│               │ JWT, CORS, Rate Limit        │
│               ▼                              │
│           :5432 (PostgreSQL) ◄── только Docker│
│                                              │
│  SSH: :2222 ◄── fail2ban (3 попытки / 1 час)│
│  :80 ──► 301 redirect → :443                │
│  :8000 ──► закрыт снаружи                   │
│  :5432 ──► закрыт снаружи                   │
│  :22   ──► закрыт                            │
│                                              │
│  Cron: 3:00 cleanup, 4:00 backup            │
│  Certbot: автообновление SSL                │
│  Fail2ban: блокировка брутфорса             │
├─────────────────────────────────────────────┤
│  Бэкапы: локально 14д + Яндекс.Диск 30д    │
└─────────────────────────────────────────────┘
```
