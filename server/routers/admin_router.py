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
from sqlalchemy.orm import Session

from database import Employee, get_db

router = APIRouter()
logger = logging.getLogger(__name__)

_backup_state: dict = {"in_progress": False, "last": None}


def _require_admin(current_user: Employee = Depends(get_current_user)):
    """Проверка прав администратора."""
    if current_user.position not in ADMIN_POSITIONS and current_user.role not in ("admin", "director"):
        raise HTTPException(status_code=403, detail="Только администратор")
    return current_user


def _run_backup():
    """Выполнить pg_dump + gzip + загрузить на Яндекс.Диск."""
    global _backup_state
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
