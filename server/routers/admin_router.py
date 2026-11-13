"""Административный роутер: бекап БД, системные задачи."""

from datetime import datetime
import gzip
import logging
import os
import re
import subprocess
import tempfile

from auth import get_current_user
from constants import ADMIN_POSITIONS
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
import requests as http_requests
from sqlalchemy.orm import Session

from database import Employee, get_db

router = APIRouter()
logger = logging.getLogger(__name__)

_backup_state: dict = {"in_progress": False, "last": None}
_restore_state: dict = {"in_progress": False, "last": None}


def _require_admin(current_user: Employee = Depends(get_current_user)):
    """Проверка прав администратора."""
    if current_user.position not in ADMIN_POSITIONS and current_user.role not in ("admin", "director"):
        raise HTTPException(status_code=403, detail="Только администратор")
    return current_user


def _run_backup():
    """Выполнить pg_dump + gzip + загрузить на Яндекс.Диск."""
    _backup_state["in_progress"] = True
    try:
        database_url = os.getenv("DATABASE_URL", "")
        if not database_url.startswith("postgresql"):
            raise RuntimeError("Бекап доступен только для PostgreSQL")

        # Парсим postgresql://user:pass@host:port/dbname
        m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)", database_url)
        if not m:
            raise RuntimeError(f"Не удалось распарсить DATABASE_URL")
        user, password, host, port, dbname = m.groups()
        port = port or "5432"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"crm_postgres_{timestamp}.sql.gz"

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        proc = subprocess.run(
            ["pg_dump", "-U", user, "-h", host, "-p", port, "-d", dbname, "--no-owner", "--no-acl"],
            capture_output=True,
            env=env,
            timeout=300,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"pg_dump завершился с ошибкой: {proc.stderr.decode('utf-8', errors='replace')[:500]}")

        compressed = gzip.compress(proc.stdout)
        if len(compressed) < 200:
            raise RuntimeError("Бекап слишком маленький — вероятно ошибка pg_dump")

        size_mb = round(len(compressed) / 1024 / 1024, 2)

        # Загрузка на Яндекс.Диск
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise RuntimeError("Яндекс.Диск не настроен (нет токена)")

        yd_path = f"disk:/CRM/Бэкапы/PostgreSQL/{filename}"
        yd.upload_file_from_bytes(compressed, yd_path)

        result = {"status": "success", "filename": filename, "size_mb": size_mb, "yd_path": yd_path, "timestamp": timestamp}
        _backup_state["last"] = result
        logger.info(f"Бекап завершён: {filename} ({size_mb} MB)")

    except Exception as e:
        err_msg = str(e)
        _backup_state["last"] = {"status": "error", "error": err_msg}
        logger.error(f"Ошибка бекапа PostgreSQL: {err_msg}")
    finally:
        _backup_state["in_progress"] = False


async def scheduled_backup_loop():
    """Ежедневный автоматический бекап PostgreSQL в 03:00 UTC."""
    import asyncio

    logger.info("Scheduled backup loop: запущен (ежедневно в 03:00 UTC)")
    while True:
        try:
            now = datetime.utcnow()
            # Следующий 03:00 UTC
            next_run = now.replace(hour=3, minute=0, second=0, microsecond=0)
            if now >= next_run:
                next_run = (
                    next_run.replace(day=next_run.day + 1)
                    if next_run.day < 28
                    else next_run.replace(
                        year=next_run.year + (1 if next_run.month == 12 else 0),
                        month=(next_run.month % 12) + 1 if next_run.month == 12 else next_run.month + 1,
                        day=1,
                    )
                )
            sleep_secs = (next_run - now).total_seconds()
            logger.info(f"Scheduled backup: следующий запуск через {sleep_secs / 3600:.1f}ч")
            await asyncio.sleep(sleep_secs)
            if not _backup_state["in_progress"]:
                logger.info("Scheduled backup: запускаю автоматический бекап...")
                _run_backup()
            else:
                logger.warning("Scheduled backup: пропускаю — уже идёт бекап")
        except Exception as e:
            logger.error(f"Scheduled backup loop error: {e}")
            await asyncio.sleep(3600)


@router.post("/backup/postgres")
async def trigger_postgres_backup(
    background_tasks: BackgroundTasks,
    current_user: Employee = Depends(_require_admin),
):
    """Запустить резервное копирование PostgreSQL → Яндекс.Диск."""
    if _backup_state["in_progress"]:
        raise HTTPException(status_code=409, detail="Бекап уже выполняется")

    database_url = os.getenv("DATABASE_URL", "")
    if not database_url.startswith("postgresql"):
        raise HTTPException(status_code=422, detail="Бекап доступен только для PostgreSQL (production)")

    background_tasks.add_task(_run_backup)
    return {"status": "started", "message": "Бекап запущен в фоне"}


@router.get("/backup/status")
async def get_backup_status(current_user: Employee = Depends(_require_admin)):
    """Статус последнего бекапа."""
    return {
        "in_progress": _backup_state["in_progress"],
        "last": _backup_state["last"],
    }


def _run_restore(filename: str):
    """Скачать бекап с ЯД, удалить все таблицы и восстановить через psql."""
    _restore_state["in_progress"] = True
    tmp_sql = None
    try:
        # Валидация имени файла
        if not re.match(r"^crm_postgres_[\w.]+\.sql\.gz$", filename):
            raise RuntimeError(f"Недопустимое имя файла: {filename}")

        database_url = os.getenv("DATABASE_URL", "")
        if not database_url.startswith("postgresql"):
            raise RuntimeError("Восстановление доступно только для PostgreSQL")

        m = re.match(r"postgresql(?:\+\w+)?://([^:]+):([^@]+)@([^:/]+):?(\d+)?/(.+)", database_url)
        if not m:
            raise RuntimeError("Не удалось распарсить DATABASE_URL")
        user, password, host, port, dbname = m.groups()
        port = port or "5432"

        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise RuntimeError("Яндекс.Диск не настроен (нет токена)")

        yd_path = f"disk:/CRM/Бэкапы/PostgreSQL/{filename}"

        # Получаем ссылку для скачивания
        dl_resp = http_requests.get(
            f"{yd.base_url}/resources/download",
            headers=yd.headers,
            params={"path": yd_path},
            timeout=30,
        )
        if dl_resp.status_code != 200:
            raise RuntimeError(f"Ошибка получения ссылки скачивания: {dl_resp.text[:300]}")

        download_url = dl_resp.json().get("href")
        if not download_url:
            raise RuntimeError("Пустая ссылка скачивания от Яндекс.Диска")

        # Скачиваем файл
        file_resp = http_requests.get(download_url, timeout=300, stream=True)
        if file_resp.status_code != 200:
            raise RuntimeError(f"Ошибка скачивания файла: {file_resp.status_code}")

        compressed = file_resp.content
        if len(compressed) < 100:
            raise RuntimeError("Скачанный файл слишком мал — вероятно ошибка")

        # Распаковываем
        sql_bytes = gzip.decompress(compressed)
        logger.info(f"Файл скачан и распакован: {len(sql_bytes)} байт SQL")

        # Записываем во временный файл
        with tempfile.NamedTemporaryFile(suffix=".sql", delete=False) as tf:
            tf.write(sql_bytes)
            tmp_sql = tf.name

        env = os.environ.copy()
        env["PGPASSWORD"] = password

        # Удаляем все таблицы (CASCADE)
        drop_sql = (
            "DO $$ DECLARE r RECORD; BEGIN "
            "FOR r IN (SELECT tablename FROM pg_tables WHERE schemaname='public') LOOP "
            "EXECUTE 'DROP TABLE IF EXISTS ' || quote_ident(r.tablename) || ' CASCADE'; "
            "END LOOP; END $$;"
        )
        drop_proc = subprocess.run(
            ["psql", "-U", user, "-h", host, "-p", port, "-d", dbname, "-c", drop_sql],
            capture_output=True,
            env=env,
            timeout=120,
        )
        if drop_proc.returncode != 0:
            raise RuntimeError(f"Ошибка удаления таблиц: {drop_proc.stderr.decode('utf-8', errors='replace')[:500]}")

        # Восстанавливаем
        restore_proc = subprocess.run(
            ["psql", "-U", user, "-h", host, "-p", port, "-d", dbname, "-f", tmp_sql],
            capture_output=True,
            env=env,
            timeout=600,
        )
        if restore_proc.returncode != 0:
            raise RuntimeError(f"Ошибка восстановления: {restore_proc.stderr.decode('utf-8', errors='replace')[:500]}")

        result = {"status": "success", "filename": filename, "timestamp": datetime.now().isoformat()}
        _restore_state["last"] = result
        logger.info(f"Восстановление из бекапа завершено: {filename}")

    except Exception as e:
        err_msg = str(e)
        _restore_state["last"] = {"status": "error", "error": err_msg}
        logger.error(f"Ошибка восстановления из бекапа: {err_msg}")
    finally:
        _restore_state["in_progress"] = False
        if tmp_sql and os.path.exists(tmp_sql):
            os.unlink(tmp_sql)


@router.post("/backup/restore")
async def restore_postgres_backup(
    filename: str,
    background_tasks: BackgroundTasks,
    current_user: Employee = Depends(_require_admin),
):
    """Восстановить БД из бекапа на Яндекс.Диске."""
    if _restore_state["in_progress"]:
        raise HTTPException(status_code=409, detail="Восстановление уже выполняется")
    if _backup_state["in_progress"]:
        raise HTTPException(status_code=409, detail="Сейчас выполняется бекап — подождите")

    if not re.match(r"^crm_postgres_[\w.]+\.sql\.gz$", filename):
        raise HTTPException(status_code=400, detail="Недопустимое имя файла")

    _restore_state["in_progress"] = True
    _restore_state["last"] = None
    background_tasks.add_task(_run_restore, filename)
    return {"status": "started", "message": f"Восстановление из {filename} запущено"}


@router.get("/backup/restore/status")
async def get_restore_status(current_user: Employee = Depends(_require_admin)):
    """Статус последнего восстановления из бекапа."""
    return {
        "in_progress": _restore_state["in_progress"],
        "last": _restore_state["last"],
    }


@router.get("/backup/list")
async def list_backups(current_user: Employee = Depends(_require_admin)):
    """Список файлов бекапов на Яндекс.Диске."""
    try:
        from yandex_disk_service import get_yandex_disk_service

        yd = get_yandex_disk_service()
        if not yd or not yd.token:
            raise HTTPException(status_code=503, detail="Яндекс.Диск не настроен")

        items = yd.list_files("disk:/CRM/Бэкапы/PostgreSQL", limit=50)
        backups = [
            {
                "name": it.get("name"),
                "size": it.get("size", 0),
                "created": it.get("created", ""),
                "modified": it.get("modified", ""),
            }
            for it in items
            if it.get("type") == "file" and it.get("name", "").endswith(".sql.gz")
        ]
        # Сортируем по имени (дата в имени)
        backups.sort(key=lambda x: x["name"], reverse=True)
        return {"backups": backups}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка получения списка: {e}")
