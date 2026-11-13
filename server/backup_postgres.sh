#!/bin/bash
# =============================================================================
# Автоматический бэкап PostgreSQL (Interior Studio CRM)
# Запуск через cron: 0 3 * * * /opt/interior_studio/server/backup_postgres.sh
# =============================================================================

set -euo pipefail

# === Настройки ===
BACKUP_DIR="/opt/interior_studio/backups/postgres"
CONTAINER_NAME="crm_postgres"
DB_NAME="interior_studio_crm"
DB_USER="crm_user"
KEEP_DAYS=14  # Хранить бэкапы за последние 14 дней

# Яндекс.Диск (загрузка через API контейнер)
UPLOAD_TO_YADISK="${UPLOAD_TO_YADISK:-true}"
API_CONTAINER="crm_api"
YADISK_BACKUP_PATH="disk:/CRM/Бэкапы/PostgreSQL"

# === Подготовка ===
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="crm_postgres_${TIMESTAMP}.sql.gz"
BACKUP_PATH="${BACKUP_DIR}/${BACKUP_FILE}"

mkdir -p "${BACKUP_DIR}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Начало бэкапа PostgreSQL..."

# === Создание дампа ===
# pg_dump внутри контейнера → gzip на хосте
if ! docker exec "${CONTAINER_NAME}" pg_dump -U "${DB_USER}" -d "${DB_NAME}" --no-owner --no-acl 2>/dev/null | gzip > "${BACKUP_PATH}"; then
    echo "[ERROR] pg_dump failed!"
    rm -f "${BACKUP_PATH}"
    exit 1
fi

# Проверка что файл не пустой
FILESIZE=$(stat -c%s "${BACKUP_PATH}" 2>/dev/null || stat -f%z "${BACKUP_PATH}" 2>/dev/null || echo "0")
if [ "${FILESIZE}" -lt 100 ]; then
    echo "[ERROR] Бэкап слишком маленький (${FILESIZE} bytes), возможно ошибка!"
    rm -f "${BACKUP_PATH}"
    exit 1
fi

FILESIZE_MB=$(echo "scale=2; ${FILESIZE}/1024/1024" | bc 2>/dev/null || echo "?")
echo "[OK] Бэкап создан: ${BACKUP_PATH} (${FILESIZE_MB} MB)"

# === Загрузка на Яндекс.Диск ===
if [ "${UPLOAD_TO_YADISK}" = "true" ]; then
    echo "[...] Загрузка на Яндекс.Диск: ${YADISK_BACKUP_PATH}/${BACKUP_FILE}"

    # Копируем бэкап в контейнер API
    docker cp "${BACKUP_PATH}" "${API_CONTAINER}:/tmp/${BACKUP_FILE}"

    # Загружаем через Python-скрипт внутри API контейнера
    UPLOAD_RESULT=$(docker exec "${API_CONTAINER}" python3 -c "
import sys
try:
    from yandex_disk_service import get_yandex_disk_service
    yd = get_yandex_disk_service()
    # Создаём папку если не существует
    yd.create_folder('disk:/CRM/Бэкапы')
    yd.create_folder('${YADISK_BACKUP_PATH}')
    result = yd.upload_file('/tmp/${BACKUP_FILE}', '${YADISK_BACKUP_PATH}/${BACKUP_FILE}')
    print('OK')
except Exception as e:
    print(f'ERROR: {e}', file=sys.stderr)
    print('FAIL')
" 2>&1)

    # Удаляем временный файл из контейнера
    docker exec "${API_CONTAINER}" rm -f "/tmp/${BACKUP_FILE}" 2>/dev/null || true

    if echo "${UPLOAD_RESULT}" | grep -q "OK"; then
        echo "[OK] Загружено на Яндекс.Диск"

        # Ротация старых бэкапов на Яндекс.Диске (старше KEEP_DAYS)
        echo "[...] Ротация бэкапов на Яндекс.Диске (старше ${KEEP_DAYS} дней)..."
        CUTOFF_DATE=$(date -d "-${KEEP_DAYS} days" +%Y%m%d 2>/dev/null || date -v-${KEEP_DAYS}d +%Y%m%d 2>/dev/null || echo "")
        if [ -n "${CUTOFF_DATE}" ]; then
            YD_CLEANUP=$(docker exec "${API_CONTAINER}" python3 -c "
import sys
try:
    from yandex_disk_service import get_yandex_disk_service
    yd = get_yandex_disk_service()
    items = yd.list_files('${YADISK_BACKUP_PATH}')
    deleted = 0
    for item in items:
        name = item.get('name', '')
        if not name.startswith('crm_postgres_') or not name.endswith('.sql.gz'):
            continue
        # crm_postgres_YYYYMMDD_HHMMSS.sql.gz
        date_part = name.split('_')[2]  # YYYYMMDD
        if date_part < '${CUTOFF_DATE}':
            path = '${YADISK_BACKUP_PATH}/' + name
            yd.delete_file(path)
            deleted += 1
    print(f'OK:{deleted}')
except Exception as e:
    print(f'FAIL:{e}', file=sys.stderr)
    print('FAIL')
" 2>&1)
            if echo "${YD_CLEANUP}" | grep -q "OK:"; then
                YD_DEL_COUNT=$(echo "${YD_CLEANUP}" | grep -oP 'OK:\K[0-9]+')
                echo "[OK] Удалено старых бэкапов с Яндекс.Диска: ${YD_DEL_COUNT}"
            else
                echo "[WARN] Ротация на Яндекс.Диске: ${YD_CLEANUP}"
            fi
        fi
    else
        echo "[WARN] Не удалось загрузить на Яндекс.Диск: ${UPLOAD_RESULT}"
    fi
fi

# === Ротация старых бэкапов ===
echo "[...] Удаление бэкапов старше ${KEEP_DAYS} дней..."
DELETED=$(find "${BACKUP_DIR}" -name "crm_postgres_*.sql.gz" -mtime +${KEEP_DAYS} -delete -print | wc -l)
echo "[OK] Удалено старых бэкапов: ${DELETED}"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Бэкап PostgreSQL завершён успешно."
