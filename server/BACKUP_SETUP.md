# Настройка автоматических бэкапов PostgreSQL

## Установка на Timeweb (production)

### 1. Скопировать скрипт и дать права

```bash
ssh timeweb
chmod +x /opt/interior_studio/server/backup_postgres.sh
mkdir -p /opt/interior_studio/backups/postgres
```

### 2. Тест запуска

```bash
/opt/interior_studio/server/backup_postgres.sh
```

Ожидаемый вывод:
```
[2026-02-27 03:00:00] Начало бэкапа PostgreSQL...
[OK] Бэкап создан: /opt/interior_studio/backups/postgres/crm_postgres_20260227_030000.sql.gz (X.XX MB)
[...] Загрузка на Яндекс.Диск: disk:/CRM/Бэкапы/PostgreSQL/crm_postgres_20260227_030000.sql.gz
[OK] Загружено на Яндекс.Диск
[...] Удаление бэкапов старше 14 дней...
[OK] Удалено старых бэкапов: 0
[2026-02-27 03:00:05] Бэкап PostgreSQL завершён успешно.
```

### 3. Добавить в cron (ежедневно в 3:00)

```bash
crontab -e
```

Добавить строку:
```
0 3 * * * /opt/interior_studio/server/backup_postgres.sh >> /opt/interior_studio/backups/postgres/cron.log 2>&1
```

### 4. Настройка

| Переменная | По умолчанию | Описание |
|------------|-------------|----------|
| `KEEP_DAYS` | 14 | Сколько дней хранить локальные бэкапы |
| `UPLOAD_TO_YADISK` | true | Загружать на Яндекс.Диск |
| `YADISK_BACKUP_PATH` | disk:/CRM/Бэкапы/PostgreSQL | Путь на Яндекс.Диске |

### 5. Отключение выгрузки на Яндекс.Диск

```bash
UPLOAD_TO_YADISK=false /opt/interior_studio/server/backup_postgres.sh
```

## Восстановление из бэкапа

### Из локального файла
```bash
# Остановить API
docker-compose down api

# Восстановить
gunzip -c /opt/interior_studio/backups/postgres/crm_postgres_YYYYMMDD_HHMMSS.sql.gz | \
  docker exec -i crm_postgres psql -U crm_user -d interior_studio_crm

# Запустить API
docker-compose up -d api
```

### Из Яндекс.Диска
```bash
# Скачать через API контейнер
docker exec crm_api python3 -c "
from yandex_disk_service import get_yandex_disk_service
yd = get_yandex_disk_service()
yd.download_file('disk:/CRM/Бэкапы/PostgreSQL/crm_postgres_XXXXXXXX_XXXXXX.sql.gz', '/tmp/restore.sql.gz')
"
docker cp crm_api:/tmp/restore.sql.gz /tmp/restore.sql.gz
gunzip -c /tmp/restore.sql.gz | docker exec -i crm_postgres psql -U crm_user -d interior_studio_crm
```
