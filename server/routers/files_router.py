"""
Роутер для endpoint'ов файлов проекта (files).
Подключается в main.py через app.include_router(files_router, prefix="/api/files").

ВАЖНО: Статические пути ПЕРЕД динамическими (правило проекта).
"""

from datetime import datetime
import logging
import os
import threading
from typing import List, Optional

from auth import get_current_user
from fastapi import APIRouter, Body, Depends, File, HTTPException, UploadFile
from schemas import ProjectFileCreate, ProjectFileResponse
from sqlalchemy.orm import Session

from database import Contract, Employee, ProjectFile, get_db

logger = logging.getLogger(__name__)

# Блокировка для предотвращения параллельных сканирований одного договора
_scanning_contracts_lock = threading.Lock()
_scanning_contracts = set()

# Подключение сервиса Яндекс.Диска
try:
    from yandex_disk_service import get_yandex_disk_service

    yandex_disk_available = True
except ImportError:
    yandex_disk_available = False
    logger.warning("YandexDiskService not available")

router = APIRouter()


# =========================
# СТАТИЧЕСКИЕ ПУТИ (ПЕРЕД ДИНАМИЧЕСКИМИ)
# =========================


@router.get("/all")
async def get_all_project_files(current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить все файлы проектов для синхронизации"""
    try:
        files = db.query(ProjectFile).all()

        return [
            {
                "id": f.id,
                "contract_id": f.contract_id,
                "stage": f.stage,
                "file_type": f.file_type,
                "public_link": f.public_link,
                "yandex_path": f.yandex_path,
                "file_name": f.file_name,
                "preview_cache_path": f.preview_cache_path,
                "file_order": f.file_order,
                "variation": f.variation,
                "upload_date": f.upload_date.isoformat() if f.upload_date else None,
            }
            for f in files
        ]

    except Exception as e:
        logger.exception(f"Ошибка при получении файлов проектов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/updated")
async def get_updated_files(since: str = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить файлы, загруженные после указанного timestamp"""
    if not since:
        raise HTTPException(status_code=400, detail="Parameter 'since' is required")

    try:
        since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    files = db.query(ProjectFile).filter(ProjectFile.upload_date > since_dt).all()

    return [
        {
            "id": f.id,
            "contract_id": f.contract_id,
            "stage": f.stage,
            "file_type": f.file_type,
            "public_link": f.public_link,
            "yandex_path": f.yandex_path,
            "file_name": f.file_name,
            "upload_date": f.upload_date.isoformat() if f.upload_date else None,
            "variation": f.variation,
        }
        for f in files
    ]


@router.get("/public-link")
async def get_public_link(
    yandex_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Получить публичную ссылку на файл"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        public_link = yd_service.get_public_link(yandex_path)

        if public_link:
            return {"status": "success", "public_link": public_link, "yandex_path": yandex_path}
        else:
            raise HTTPException(status_code=404, detail="File not found or cannot create public link")

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "DiskNotFoundError" in error_str or "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Файл не найден: {yandex_path}")
        raise HTTPException(status_code=500, detail=f"Error getting public link: {error_str}")


@router.get("/list")
async def list_yandex_files(
    folder_path: Optional[str] = None,
    path: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
):
    """Получить список файлов в папке Яндекс.Диска"""
    # Принимаем и folder_path и path как алиасы
    resolved_path = folder_path or path
    if not resolved_path:
        raise HTTPException(status_code=422, detail="Необходимо указать folder_path или path")

    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        files = yd_service.list_files(resolved_path)

        return {"status": "success", "folder_path": resolved_path, "files": files}

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "DiskNotFoundError" in error_str or "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Папка не найдена: {resolved_path}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {error_str}")


def _calc_folder_size(yd_service, path: str, max_depth: int = 5, _depth: int = 0) -> int:
    """Рекурсивно суммирует размеры файлов в папке Яндекс.Диска."""
    if _depth > max_depth:
        return 0
    try:
        items = yd_service.list_files(path, limit=1000)
    except Exception:
        return 0
    total = 0
    for item in items:
        if item.get("type") == "file":
            total += item.get("size", 0)
        elif item.get("type") == "dir":
            total += _calc_folder_size(yd_service, item["path"], max_depth, _depth + 1)
    return total


@router.get("/folder-size")
async def get_folder_size(
    path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Вернуть суммарный размер папки (рекурсивно) в байтах."""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")
    try:
        yd_service = get_yandex_disk_service()
        size = _calc_folder_size(yd_service, path)
        return {"path": path, "size": size}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating folder size: {e}")


@router.get("/public-folder")
async def list_public_folder(
    url: str,
    current_user: Employee = Depends(get_current_user),
):
    """Получить список файлов из публичной ссылки Яндекс.Диска (как десктоп get_public_folder_contents)"""
    import requests as req

    try:
        # ЯД Public API — не требует OAuth для чтения
        resp = req.get("https://cloud-api.yandex.net/v1/disk/public/resources", params={"public_key": url, "limit": 1000}, timeout=15)
        if resp.status_code != 200:
            raise HTTPException(status_code=resp.status_code, detail=f"ЯД API: {resp.text[:200]}")

        data = resp.json()
        items = data.get("_embedded", {}).get("items", [])
        files = []
        for item in items:
            if item.get("type") == "file":
                name = item.get("name", "")
                size = item.get("size", 0)
                # Автоклассификация: замер vs фотофиксация (как десктоп _classify_file)
                name_lower = name.lower()
                dest = "Замер" if any(w in name_lower for w in ["замер", "зам_", "обмер"]) else "Фотофиксация"
                files.append(
                    {
                        "name": name,
                        "path": item.get("path", ""),
                        "size": size,
                        "size_display": f"{size / 1024 / 1024:.1f} МБ" if size >= 1024 * 1024 else f"{size / 1024:.0f} КБ",
                        "mime_type": item.get("mime_type", ""),
                        "destination": dest,
                    }
                )
        return {"status": "success", "files": files, "total": len(files)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/download-public")
async def download_public_to_yd(
    public_url: str,
    file_path: str,
    dest_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Скачать файл из публичной ссылки ЯД и загрузить в свою папку (как десктоп download_public_file + upload)"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")
    import os
    import tempfile

    import requests as req

    try:
        yd_service = get_yandex_disk_service()
        token = yd_service.token

        # 1. Получить ссылку на скачивание из публичной папки
        dl_resp = req.get("https://cloud-api.yandex.net/v1/disk/public/resources/download", params={"public_key": public_url, "path": file_path}, timeout=15)
        if dl_resp.status_code != 200:
            raise HTTPException(status_code=dl_resp.status_code, detail=f"Download URL error: {dl_resp.text[:200]}")

        download_url = dl_resp.json().get("href")
        if not download_url:
            raise HTTPException(status_code=500, detail="Не удалось получить ссылку на скачивание")

        # 2. Скачать во временный файл
        file_name = file_path.split("/")[-1] if "/" in file_path else file_path
        tmp_path = os.path.join(tempfile.gettempdir(), f"crm_upload_{file_name}")
        try:
            with req.get(download_url, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(tmp_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            # 3. Загрузить на свой ЯД
            # Создаём папку если нет
            dest_folder = "/".join(dest_path.replace("disk:", "").split("/")[:-1])
            try:
                yd_service.create_folder(dest_folder)
            except Exception:
                pass

            yd_service.upload_file(tmp_path, dest_path.replace("disk:", ""))

            # 4. Получить публичную ссылку
            public_link = ""
            try:
                public_link = yd_service.get_public_link(dest_folder)
            except Exception:
                pass

            return {"status": "success", "dest_path": dest_path, "public_link": public_link, "file_name": file_name}
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/", response_model=ProjectFileResponse)
async def create_file_record(file_data: ProjectFileCreate, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Создать запись о файле"""
    # Проверяем дубликат по (contract_id, yandex_path) перед вставкой
    data = file_data.model_dump()
    yp = data.get("yandex_path", "")
    if yp:
        existing = db.query(ProjectFile).filter(ProjectFile.contract_id == data.get("contract_id"), ProjectFile.yandex_path == yp).first()
        if existing:
            # Дубликат — возвращаем существующую запись
            return existing

    file_record = ProjectFile(**data)
    db.add(file_record)
    try:
        db.commit()
    except Exception:
        db.rollback()
        # После rollback пробуем найти существующую запись
        if yp:
            existing = db.query(ProjectFile).filter(ProjectFile.contract_id == data.get("contract_id"), ProjectFile.yandex_path == yp).first()
            if existing:
                return existing
        raise HTTPException(status_code=409, detail="Дубликат файла")
    db.refresh(file_record)
    return file_record


@router.get("/upload-url")
async def get_yandex_upload_url(
    yandex_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Получить временный URL для прямой загрузки файла на ЯД из браузера (без проксирования через сервер)"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    if "/../" in yandex_path or yandex_path.endswith("/..") or yandex_path.startswith("../"):
        raise HTTPException(status_code=400, detail="Недопустимый путь файла")

    ext = os.path.splitext(yandex_path)[1].lower()
    ALLOWED_EXTENSIONS_LOCAL = {
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".csv",
        ".rtf",
        ".odt",
        ".ods",
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".heic",
        ".heif",
        ".tif",
        ".tiff",
        ".raw",
        ".cr2",
        ".nef",
        ".arw",
        ".dwg",
        ".dxf",
        ".skp",
        ".3ds",
        ".max",
        ".blend",
        ".ifc",
        ".obj",
        ".fbx",
        ".zip",
        ".rar",
        ".7z",
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
        ".aac",
    }
    if ext and ext not in ALLOWED_EXTENSIONS_LOCAL:
        raise HTTPException(status_code=400, detail=f"Тип файла '{ext}' не разрешён")

    try:
        import requests as _requests

        yd_service = get_yandex_disk_service()
        if not yd_service.token:
            raise HTTPException(status_code=503, detail="Yandex Disk token not configured")

        # Автопереименование при конфликте имён
        actual_path = yandex_path
        try:
            if yd_service.file_exists(actual_path):
                base, ext_part = os.path.splitext(actual_path)
                counter = 1
                while counter <= 99 and yd_service.file_exists(f"{base} ({counter}){ext_part}"):
                    counter += 1
                actual_path = f"{base} ({counter}){ext_part}"
        except Exception:
            pass

        import time as _time

        # Создаём родительскую папку при необходимости
        folder_just_created = False
        parent_dir = "/".join(actual_path.split("/")[:-1])
        if parent_dir and parent_dir != "/":
            # Сначала проверяем существует ли папка (дешевле чем сразу создавать)
            check_r = _requests.get(
                f"{yd_service.base_url}/resources",
                headers=yd_service.headers,
                params={"path": parent_dir},
                timeout=10,
            )
            if check_r.status_code != 200:
                # Папка не существует — создаём рекурсивно
                try:
                    yd_service.create_folder(parent_dir)
                    folder_just_created = True
                except Exception as folder_err:
                    logger.warning(f"Не удалось создать папку {parent_dir}: {folder_err}")

                if folder_just_created:
                    # Ждём пока папка станет реально доступна на YD (до 3 сек)
                    for _ in range(6):
                        _time.sleep(0.5)
                        verify_r = _requests.get(
                            f"{yd_service.base_url}/resources",
                            headers=yd_service.headers,
                            params={"path": parent_dir},
                            timeout=5,
                        )
                        if verify_r.status_code == 200:
                            break
                    else:
                        logger.warning(f"Папка {parent_dir} создана но не стала доступна за 3 сек")

        r = _requests.get(
            f"{yd_service.base_url}/resources/upload",
            headers=yd_service.headers,
            params={"path": actual_path, "overwrite": "true"},
            timeout=30,
        )
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail="Ошибка получения URL загрузки от Яндекс.Диска")

        upload_url = r.json().get("href")
        return {
            "upload_url": upload_url,
            "yandex_path": actual_path,
            "file_name": os.path.basename(actual_path),
            "folder_created": folder_just_created,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при получении upload URL: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/upload")
async def upload_file_to_yandex(
    file: UploadFile = File(...),
    yandex_path: str = None,
    current_user: Employee = Depends(get_current_user),
):
    """Загрузить файл на Яндекс.Диск"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    # Whitelist разрешённых типов файлов
    ALLOWED_EXTENSIONS = {
        # Документы
        ".pdf",
        ".doc",
        ".docx",
        ".xls",
        ".xlsx",
        ".ppt",
        ".pptx",
        ".txt",
        ".csv",
        ".rtf",
        ".odt",
        ".ods",
        # Изображения (включая форматы iPhone/камер)
        ".jpg",
        ".jpeg",
        ".png",
        ".gif",
        ".bmp",
        ".svg",
        ".webp",
        ".heic",
        ".heif",  # iPhone/iPad фото
        ".tif",
        ".tiff",  # сканы, чертежи высокого разрешения
        ".raw",
        ".cr2",
        ".nef",
        ".arw",  # RAW камер
        # CAD / 3D
        ".dwg",
        ".dxf",
        ".skp",
        ".3ds",
        ".max",
        ".blend",
        ".ifc",
        ".obj",
        ".fbx",
        # Архивы
        ".zip",
        ".rar",
        ".7z",
        # Видео (обходы объекта, фотофиксация)
        ".mp4",
        ".mov",
        ".avi",
        ".mkv",
        ".webm",
        # Аудио (голосовые заметки)
        ".mp3",
        ".wav",
        ".ogg",
        ".m4a",
        ".aac",
    }
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f"Тип файла '{ext}' не разрешён для загрузки. Разрешены: фото, PDF, Word, Excel, CAD, архивы, видео")

    try:
        yd_service = get_yandex_disk_service()
        if not yd_service.token:
            raise HTTPException(status_code=503, detail="Yandex Disk token not configured")
        file_bytes = await file.read()

        # Проверка размера файла (по умолчанию 600 МБ — рендеры и видео обходов бывают большими)
        max_size = int(os.environ.get("MAX_FILE_SIZE_MB", 600)) * 1024 * 1024
        if len(file_bytes) > max_size:
            raise HTTPException(status_code=413, detail=f"Размер файла превышает максимально допустимый ({os.environ.get('MAX_FILE_SIZE_MB', 600)} МБ)")

        if not yandex_path:
            # Защита от path traversal в имени файла
            safe_filename = os.path.basename(file.filename or "unnamed")
            yandex_path = f"/CRM/Временные файлы/{safe_filename}"
        else:
            # Защита от path traversal: запрещаем "../" и "/.." (не просто ".." — иначе блокируются файлы типа "дизайн..2.pdf")
            if "/../" in yandex_path or yandex_path.endswith("/..") or yandex_path.startswith("../"):
                raise HTTPException(status_code=400, detail="Недопустимый путь файла")

        # Автопереименование при конфликте имён: file.pdf → file (1).pdf
        try:
            if yd_service.file_exists(yandex_path):
                base, ext = os.path.splitext(yandex_path)
                counter = 1
                while counter <= 99 and yd_service.file_exists(f"{base} ({counter}){ext}"):
                    counter += 1
                yandex_path = f"{base} ({counter}){ext}"
        except Exception:
            pass  # Если проверка не удалась — загружаем с overwrite

        result = yd_service.upload_file_from_bytes(file_bytes, yandex_path)

        if result:
            public_link = yd_service.get_public_link(yandex_path)
            actual_name = os.path.basename(yandex_path)
            return {"status": "success", "yandex_path": yandex_path, "public_link": public_link, "file_name": actual_name}
        else:
            raise HTTPException(status_code=500, detail="Failed to upload file")

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e).lower()
        if "unauthorized" in error_msg or "token" in error_msg or "401" in error_msg:
            raise HTTPException(status_code=503, detail="Yandex Disk not configured or token expired")
        logger.exception(f"Ошибка при загрузке файла: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/folder")
async def create_yandex_folder(
    folder_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Создать папку на Яндекс.Диске"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    # Защита от path traversal
    if ".." in folder_path:
        raise HTTPException(status_code=400, detail="Недопустимый путь папки")

    try:
        yd_service = get_yandex_disk_service()
        result = yd_service.create_folder(folder_path)

        return {"status": "success" if result else "exists", "folder_path": folder_path}

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "DiskNotFoundError" in error_str or "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Путь не найден: {folder_path}")
        raise HTTPException(status_code=500, detail=f"Folder creation error: {error_str}")


@router.post("/move-folder")
async def move_yandex_folder(
    from_path: str,
    to_path: str,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Переименовать/переместить папку на Яндекс.Диске (как десктоп move_folder)"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")
    if ".." in from_path or ".." in to_path:
        raise HTTPException(status_code=400, detail="Недопустимый путь")
    try:
        yd_service = get_yandex_disk_service()
        import requests as req

        token = yd_service.token
        resp = req.post(
            "https://cloud-api.yandex.net/v1/disk/resources/move", params={"from": from_path, "path": to_path, "overwrite": "false"}, headers={"Authorization": f"OAuth {token}"}, timeout=15
        )
        if resp.status_code in [201, 202]:
            # Обновляем пути в project_files и contracts
            try:
                from_clean = from_path.replace("disk:", "")
                to_clean = to_path.replace("disk:", "")
                # Обновляем yandex_path во всех project_files
                affected = db.query(ProjectFile).filter(ProjectFile.yandex_path.like(f"%{from_clean}%")).all()
                for pf in affected:
                    pf.yandex_path = pf.yandex_path.replace(from_clean, to_clean)
                # Обновляем поля contracts (все *_yandex_path)
                contracts = db.query(Contract).filter(Contract.yandex_folder_path.in_([from_path, f"disk:{from_clean}"])).all()
                for c in contracts:
                    # Обновляем все поля с путями
                    for attr in dir(c):
                        if attr.endswith("_yandex_path") and attr != "yandex_folder_path":
                            val = getattr(c, attr, "")
                            if val and from_clean in val:
                                setattr(c, attr, val.replace(from_clean, to_clean))
                    c.yandex_folder_path = to_path
                db.commit()
                logger.info(f"Move: обновлено {len(affected)} файлов, {len(contracts)} контрактов")
            except Exception as update_err:
                logger.warning(f"Move: ошибка обновления путей в БД: {update_err}")
            return {"status": "success", "from": from_path, "to": to_path}
        elif resp.status_code == 409:
            return {"status": "exists", "message": "Целевая папка уже существует"}
        else:
            raise HTTPException(status_code=resp.status_code, detail=resp.text[:200])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)[:200])


@router.post("/validate")
async def validate_files(request: dict, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Пакетная проверка существования файлов на Яндекс.Диске"""
    file_ids = request.get("file_ids", [])
    auto_clean = request.get("auto_clean", False)

    if not file_ids:
        return []

    if len(file_ids) > 50:
        raise HTTPException(status_code=400, detail="Максимум 50 файлов за запрос")

    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    yd = get_yandex_disk_service()
    results = []

    for file_id in file_ids:
        file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
        if not file_record:
            results.append({"file_id": file_id, "exists": False, "reason": "not_in_db"})
            continue

        yandex_path = file_record.yandex_path
        if not yandex_path:
            results.append({"file_id": file_id, "exists": False, "reason": "no_path"})
            if auto_clean:
                db.delete(file_record)
            continue

        try:
            # Нормализация пути: Яндекс API принимает и disk: и без
            check_path = yandex_path
            exists = yd.file_exists(check_path)
            # Если не найден с disk: префиксом — попробуем без
            if not exists and check_path.startswith("disk:"):
                exists = yd.file_exists(check_path[5:])
            # И наоборот
            if not exists and not check_path.startswith("disk:"):
                exists = yd.file_exists("disk:" + check_path)
        except Exception as e:
            logger.warning(f"Ошибка проверки файла {file_id} на YD: {e}")
            results.append({"file_id": file_id, "exists": True, "reason": "check_error"})
            continue

        results.append({"file_id": file_id, "exists": exists})

        if not exists and auto_clean:
            db.delete(file_record)
            logger.info(f"Автоочистка: удалена запись файла {file_id} path={yandex_path} (нет на YD)")

    if auto_clean:
        db.commit()

    return results


@router.delete("/yandex")
async def delete_yandex_file(
    yandex_path: str,
    current_user: Employee = Depends(get_current_user),
):
    """Удалить файл с Яндекс.Диска"""
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    try:
        yd_service = get_yandex_disk_service()
        result = yd_service.delete_file(yandex_path)

        return {"status": "success" if result else "not_found", "yandex_path": yandex_path}

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "DiskNotFoundError" in error_str or "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Файл не найден: {yandex_path}")
        raise HTTPException(status_code=500, detail=f"Error deleting file: {error_str}")


# =========================
# ПУТИ С SUB-PREFIX (contract, scan)
# =========================


@router.get("/contract/{contract_id}", response_model=list[ProjectFileResponse])
async def get_contract_files(contract_id: int, stage: Optional[str] = None, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить файлы договора"""
    query = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id)
    if stage:
        query = query.filter(ProjectFile.stage == stage)
    return query.order_by(ProjectFile.file_order).all()


# Точный маппинг папок ЯД → стадий (используется при сканировании)
_FOLDER_TO_STAGE_EXACT = {
    "Замер": "measurement",
    "Замеры": "measurement",
    "1 стадия - Планировочное решение": "stage1",
    "Планировочное решение": "stage1",
    "Концепция-коллажи": "stage2_concept",
    "Коллажи": "stage2_concept",
    "3D визуализация": "stage2_3d",
    "3D": "stage2_3d",
    "3 стадия - Чертежный проект": "stage3",
    "Чертежный проект": "stage3",
    "Чертежи": "stage3",
    "Референсы": "references",
    "Фотофиксация": "photo_documentation",
    "Фото": "photo_documentation",
    "Анкета": "questionnaire",
    "Анкеты": "questionnaire",
    "Документы": "documents",
    "Акты": "acts",
    "Информационные письма": "info_letters",
    "Доп. соглашения": "supervision",
    "Техническое задание": "tech_task",
    "ТЗ": "tech_task",
    "Авторский надзор": "supervision",
}

# Нечёткий маппинг: ключевые слова → стадия
_FOLDER_KEYWORDS_TO_STAGE = [
    ("замер", "measurement"),
    ("1 стадия", "stage1"),
    ("1стадия", "stage1"),
    ("планировочн", "stage1"),
    ("концепция", "stage2_concept"),
    ("коллаж", "stage2_concept"),
    ("3d", "stage2_3d"),
    ("визуализ", "stage2_3d"),
    ("2 стадия", "stage2_concept"),
    ("2стадия", "stage2_concept"),
    ("3 стадия", "stage3"),
    ("3стадия", "stage3"),
    ("чертеж", "stage3"),
    ("рабочи", "stage3"),
    ("референ", "references"),
    ("фотофикс", "photo_documentation"),
    ("фото", "photo_documentation"),
    ("анкет", "questionnaire"),
    ("документ", "documents"),
    ("техническ", "tech_task"),
    ("надзор", "supervision"),
]


@router.post("/scan/{contract_id}")
async def scan_contract_files_on_yandex(contract_id: int, scope: str = "all", current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Сканирование файлов на Яндекс.Диске для договора.

    Находит файлы, которые есть на ЯД но отсутствуют в БД, и создаёт записи.
    scope: 'all' — вся папка проекта, 'supervision' — только Авторский надзор.
    """
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")

    # Получаем договор для определения папки
    contract = db.query(Contract).filter(Contract.id == contract_id).first()
    if not contract:
        raise HTTPException(status_code=404, detail="Договор не найден")

    folder_path = contract.yandex_folder_path
    if not folder_path:
        raise HTTPException(status_code=404, detail="Папка договора на ЯД не задана")

    # Защита от параллельных сканирований одного договора
    with _scanning_contracts_lock:
        if contract_id in _scanning_contracts:
            return {"status": "already_scanning", "total_on_disk": 0, "already_in_db": 0, "new_files_added": 0, "new_files": []}
        _scanning_contracts.add(contract_id)

    try:
        yd_service = get_yandex_disk_service()

        def match_folder_to_stage(folder_name):
            """Определить стадию по имени папки: сначала точное, потом нечёткое"""
            if folder_name in _FOLDER_TO_STAGE_EXACT:
                return _FOLDER_TO_STAGE_EXACT[folder_name]
            name_lower = folder_name.lower()
            for keyword, stage_id in _FOLDER_KEYWORDS_TO_STAGE:
                if keyword in name_lower:
                    return stage_id
            return None

        def classify_document_by_name(file_name, parent_stage):
            """Определяет точный stage файла по его имени (для актов, писем, соглашений).
            Если не удалось — возвращает parent_stage."""
            name = file_name.lower()
            is_signed = any(w in name for w in ["подпис", "signed", "с подпис"])

            # Акты: используем stage-ID без коллизии с рабочими папками стадий проекта
            if parent_stage in ("acts", "documents"):
                if any(w in name for w in ["планировоч", " пр", "акт_пр", "акт пр", "stage1", "стадия 1", "стадия1"]):
                    return "act_pr_signed" if is_signed else "act_pr"
                if any(w in name for w in ["концепц", "дизайн", " кд", "акт_кд", "акт кд", "stage2", "стадия 2", "стадия2"]):
                    return "act_kd_signed" if is_signed else "act_kd"
                if any(w in name for w in ["чертеж", "чертёж", "рабоч", " рч", "акт_рч", "акт рч", "финал", "stage3", "стадия 3", "стадия3"]):
                    return "act_rch_signed" if is_signed else "act_rch"
                # Общее: если есть слово "акт" но тип не определён → Акт ПР
                if "акт" in name:
                    return "act_pr_signed" if is_signed else "act_pr"

            # Информационные письма
            if parent_stage == "info_letters":
                return "info_letter_signed" if is_signed else "info_letter"

            # Доп. соглашения
            if parent_stage == "supervision":
                return "additional_agreement_signed" if is_signed else "supervision"

            # Договор vs ТЗ в папке Документы
            if parent_stage == "documents":
                if any(w in name for w in ["договор", "contract", "контракт"]):
                    return "documents"
                if any(w in name for w in ["тз", "техническ", "задани", "анкет"]):
                    return "tech_task"
                if any(w in name for w in ["доп", "соглашен", "дополнит"]):
                    return "supervision"
                if any(w in name for w in ["информ", "письм"]):
                    return "info_letter"

            return parent_stage

        def detect_file_type(name):
            ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if ext in ("png", "jpg", "jpeg", "gif", "bmp", "webp", "tiff", "svg"):
                return "image"
            elif ext == "pdf":
                return "pdf"
            elif ext in ("xls", "xlsx", "csv"):
                return "excel"
            elif ext in ("doc", "docx"):
                return "word"
            elif ext in ("dwg", "dxf"):
                return "cad"
            return "other"

        def normalize_path(p):
            """Нормализация пути: убираем 'disk:' префикс для сравнения"""
            if p and p.startswith("disk:"):
                return p[5:]
            return p or ""

        found_files = []

        def scan_folder(path, stage=None, variation=1):
            try:
                items = yd_service.list_files(path)
                for item in items:
                    item_name = item.get("name", "")
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")

                    if item_type == "dir":
                        # Пропускаем папку "правки" — файлы правок отображаются отдельно
                        if item_name.lower() == "правки":
                            continue
                        child_stage = match_folder_to_stage(item_name)
                        child_variation = variation
                        if child_stage is None:
                            child_stage = stage  # наследуем стадию от родителя
                        # Внутри Авторского надзора подпапки "Стадия ..." остаются supervision
                        if stage == "supervision" and item_name.startswith("Стадия"):
                            child_stage = "supervision"
                        # Подпапки "Вариация N" — извлекаем номер вариации
                        if item_name.lower().startswith("вариация"):
                            child_stage = stage
                            import re

                            m = re.search(r"(\d+)", item_name)
                            child_variation = int(m.group(1)) if m else 1
                        # Валидация: пропускаем папки с нераспознанным stage и нестандартными именами
                        # (пользователь мог создать произвольную папку)
                        if child_stage is None and stage is None:
                            logger.info(f"Скан: пропуск нераспознанной папки '{item_name}'")
                            continue
                        scan_folder(item_path, child_stage, child_variation)
                    elif item_type == "file":
                        # Файлы с определённой стадией добавляем
                        # Файлы в корне (stage=None) — пропускаем
                        if stage:
                            # Классифицируем файл по имени (акты, письма, соглашения)
                            classified_stage = classify_document_by_name(item_name, stage)
                            found_files.append(
                                {
                                    "yandex_path": item_path,
                                    "file_name": item_name,
                                    "stage": classified_stage,
                                    "file_type": detect_file_type(item_name),
                                    "variation": variation,
                                }
                            )
            except Exception as e:
                logger.warning(f"Ошибка сканирования {path}: {e}")

        if scope == "supervision":
            # Для надзора сканируем только подпапку "Авторский надзор"
            supervision_path = folder_path.rstrip("/") + "/Авторский надзор"
            logger.info(f"Scan scope=supervision: сканируем только {supervision_path}")
            scan_folder(supervision_path, stage="supervision")
        else:
            scan_folder(folder_path)

        # Получаем существующие записи — нормализуем пути для сравнения
        existing_paths_normalized = set()
        existing_records = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).all()
        for rec in existing_records:
            if rec.yandex_path:
                # Добавляем оба варианта пути (с disk: и без) для надёжного сравнения
                norm = normalize_path(rec.yandex_path)
                existing_paths_normalized.add(norm)
                if not norm.startswith("/"):
                    existing_paths_normalized.add("/" + norm)
                else:
                    existing_paths_normalized.add(norm.lstrip("/"))

        # Создаём записи для новых файлов (сравнение по нормализованному пути)
        new_files = []
        for f in found_files:
            yp = f["yandex_path"]
            yp_normalized = normalize_path(yp)

            if yp_normalized in existing_paths_normalized:
                continue

            # Добавляем в множество чтобы не дублировать внутри одного скана
            existing_paths_normalized.add(yp_normalized)

            # Получаем публичную ссылку
            try:
                public_link = yd_service.get_public_link(yp)
            except Exception:
                public_link = ""

            # Для файлов надзора file_type хранит название стадии
            file_type_val = f["file_type"]
            if f["stage"] == "supervision":
                # Определяем стадию надзора из пути
                parts = yp.split("/")
                for part in parts:
                    if part.startswith("Стадия"):
                        file_type_val = part
                        break

            # Дополнительная проверка: прямой запрос в БД (защита от дубликатов)
            existing_exact = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id, ProjectFile.yandex_path == yp).first()
            if existing_exact:
                logger.info(f"Scan: файл уже есть в БД (exact match), пропускаем: {f['file_name']}")
                continue

            new_record = ProjectFile(
                contract_id=contract_id, stage=f["stage"], file_type=file_type_val, yandex_path=yp, public_link=public_link, file_name=f["file_name"], variation=f.get("variation", 1)
            )
            try:
                # Используем savepoint чтобы rollback не затронул предыдущие записи
                savepoint = db.begin_nested()
                db.add(new_record)
                db.flush()
            except Exception as insert_err:
                savepoint.rollback()
                logger.warning(f"Scan: не удалось добавить файл (дубликат?): {f['file_name']}: {insert_err}")
                continue
            new_files.append(
                {
                    "yandex_path": yp,
                    "file_name": f["file_name"],
                    "stage": f["stage"],
                    "file_type": file_type_val,
                    "public_link": public_link,
                }
            )

        # Синхронизация полей contracts с project_files (для совместимости с десктопом)
        # Десктоп читает файлы из полей contracts, мобиль — из project_files
        all_db_files = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id).all()

        # Полный маппинг stage → поля contracts (link, yandex_path, file_name)
        STAGE_CONTRACT_FIELDS = {
            "documents": ("contract_file_link", "contract_file_yandex_path", "contract_file_name"),
            "tech_task": ("tech_task_link", "tech_task_yandex_path", "tech_task_file_name"),
            "questionnaire": ("tech_task_link", "tech_task_yandex_path", "tech_task_file_name"),
            "measurement": ("measurement_image_link", "measurement_yandex_path", "measurement_file_name"),
            # Новые stage-ID для актов (без коллизии с рабочими папками)
            "act_pr": ("act_planning_link", "act_planning_yandex_path", "act_planning_file_name"),
            "act_kd": ("act_concept_link", "act_concept_yandex_path", "act_concept_file_name"),
            "act_rch": ("act_final_link", "act_final_yandex_path", "act_final_file_name"),
            "act_pr_signed": ("act_planning_signed_link", "act_planning_signed_yandex_path", "act_planning_signed_file_name"),
            "act_kd_signed": ("act_concept_signed_link", "act_concept_signed_yandex_path", "act_concept_signed_file_name"),
            "act_rch_signed": ("act_final_signed_link", "act_final_signed_yandex_path", "act_final_signed_file_name"),
            # Старые stage-ID (совместимость с существующими ProjectFile-записями)
            "stage1": ("act_planning_link", "act_planning_yandex_path", "act_planning_file_name"),
            "stage2_concept": ("act_concept_link", "act_concept_yandex_path", "act_concept_file_name"),
            "stage3": ("act_final_link", "act_final_yandex_path", "act_final_file_name"),
            "stage1_signed": ("act_planning_signed_link", "act_planning_signed_yandex_path", "act_planning_signed_file_name"),
            "stage2_signed": ("act_concept_signed_link", "act_concept_signed_yandex_path", "act_concept_signed_file_name"),
            "stage3_signed": ("act_final_signed_link", "act_final_signed_yandex_path", "act_final_signed_file_name"),
            "supervision": ("additional_agreement_link", "additional_agreement_yandex_path", "additional_agreement_file_name"),
            "acts": ("act_planning_link", "act_planning_yandex_path", "act_planning_file_name"),
            "info_letter": ("info_letter_link", "info_letter_yandex_path", "info_letter_file_name"),
            "info_letters": ("info_letter_link", "info_letter_yandex_path", "info_letter_file_name"),
            "info_letter_signed": ("info_letter_signed_link", "info_letter_signed_yandex_path", "info_letter_signed_file_name"),
            "additional_agreement_signed": ("additional_agreement_signed_link", "additional_agreement_signed_yandex_path", "additional_agreement_signed_file_name"),
        }
        for stage_key, (link_field, path_field, name_field) in STAGE_CONTRACT_FIELDS.items():
            if not getattr(contract, link_field, None):
                pf = next((f for f in all_db_files if f.stage == stage_key), None)
                if pf:
                    setattr(contract, link_field, pf.public_link or "")
                    setattr(contract, path_field, pf.yandex_path or "")
                    setattr(contract, name_field, pf.file_name or "")
                    logger.info(f"Scan: обновлён {link_field} для contract {contract_id}")

        # Обновляем references_yandex_path и photo_documentation_yandex_path
        # Логика: файлы есть → создать ссылку; файлов нет → очистить ссылку
        contract_updated = False

        if scope == "all":
            ref_files = [f for f in found_files if f["stage"] == "references"]
            if ref_files:
                # Файлы есть — создаём ссылку если нет
                if not contract.references_yandex_path:
                    try:
                        first_ref_path = ref_files[0]["yandex_path"]
                        ref_folder = "/".join(first_ref_path.split("/")[:-1])
                        logger.info(f"Scan: публикуем папку референсов: {ref_folder}")
                        ref_link = yd_service.get_public_link(ref_folder)
                        if ref_link:
                            contract.references_yandex_path = ref_link
                            contract_updated = True
                            logger.info(f"Scan: обновлён references_yandex_path: {ref_link}")
                    except Exception as e:
                        logger.warning(f"Scan: не удалось получить ссылку на Референсы: {e}")
            # НЕ очищаем ссылку — она устанавливается клиентом при upload
            # и ведёт на папку, а не на отдельный файл в project_files

            photo_files = [f for f in found_files if f["stage"] == "photo_documentation"]
            if photo_files:
                # Файлы есть — создаём ссылку если нет
                if not contract.photo_documentation_yandex_path:
                    try:
                        first_photo_path = photo_files[0]["yandex_path"]
                        photo_folder = "/".join(first_photo_path.split("/")[:-1])
                        logger.info(f"Scan: публикуем папку фотофиксации: {photo_folder}")
                        photo_link = yd_service.get_public_link(photo_folder)
                        if photo_link:
                            contract.photo_documentation_yandex_path = photo_link
                            contract_updated = True
                            logger.info(f"Scan: обновлён photo_documentation_yandex_path: {photo_link}")
                    except Exception as e:
                        logger.warning(f"Scan: не удалось получить ссылку на Фотофиксацию: {e}")
            # НЕ очищаем ссылку — аналогично референсам

        if new_files or contract_updated:
            db.commit()
            logger.info(f"Scan contract {contract_id}: новых файлов={len(new_files)}, contract_updated={contract_updated}")

        return {
            "status": "success",
            "total_on_disk": len(found_files),
            "already_in_db": len(existing_records),
            "new_files_added": len(new_files),
            "new_files": new_files,
            "contract_updated": contract_updated,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Ошибка при сканировании файлов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
    finally:
        with _scanning_contracts_lock:
            _scanning_contracts.discard(contract_id)


# =========================
# ДИНАМИЧЕСКИЕ ПУТИ (ПОСЛЕ СТАТИЧЕСКИХ)
# =========================

# Кеш превью: 7 дней
_STREAM_CACHE_DIR = "/tmp/interior_stream_cache"
_STREAM_CACHE_TTL = 7 * 24 * 3600  # секунд


def _stream_cache_path(yandex_path: str, ext: str) -> str:
    import hashlib

    key = hashlib.sha256(yandex_path.encode()).hexdigest()
    return os.path.join(_STREAM_CACHE_DIR, f"{key}{ext}")


def _init_stream_cache():
    os.makedirs(_STREAM_CACHE_DIR, exist_ok=True)


def _evict_stream_cache():
    """Удалить из кеша файлы старше TTL (вызывается лениво при каждом промахе)."""
    import time

    now = time.time()
    try:
        for fname in os.listdir(_STREAM_CACHE_DIR):
            fpath = os.path.join(_STREAM_CACHE_DIR, fname)
            try:
                if now - os.path.getmtime(fpath) > _STREAM_CACHE_TTL:
                    os.remove(fpath)
            except OSError:
                pass
    except OSError:
        pass


# ВАЖНО: /stream ПЕРЕД /{file_id} — иначе FastAPI матчит "stream" как file_id
@router.get("/stream")
async def stream_file_from_yandex(
    yandex_path: str,
    token: str = None,
):
    """Стримить файл с Яндекс.Диска для проигрывания в браузере (audio/video/image).
    Принимает JWT token как query param (т.к. <audio src>/<img src> не могут передать Header).
    Кеш на диске 7 дней — повторные запросы не скачивают файл повторно."""
    if not token:
        raise HTTPException(status_code=401, detail="Требуется авторизация")
    from auth import decode_token

    try:
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Невалидный токен")
    except Exception:
        raise HTTPException(status_code=401, detail="Невалидный токен")
    if not yandex_disk_available:
        raise HTTPException(status_code=503, detail="Yandex Disk service not available")
    if ".." in yandex_path:
        raise HTTPException(status_code=400, detail="Недопустимый путь")
    try:
        import time

        from fastapi.responses import FileResponse

        yd_svc = get_yandex_disk_service()
        clean_path = yandex_path.replace("disk:", "").strip()
        if not clean_path.startswith("/"):
            clean_path = "/" + clean_path
        ext = os.path.splitext(clean_path)[1].lower()
        content_types = {
            ".webm": "audio/webm",
            ".ogg": "audio/ogg",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".m4a": "audio/mp4",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".bmp": "image/bmp",
            ".heic": "image/heic",
        }
        ct = content_types.get(ext, "application/octet-stream")

        # Проверяем кеш
        _init_stream_cache()
        cache_file = _stream_cache_path(yandex_path, ext)
        cache_hit = False
        if os.path.exists(cache_file):
            age = time.time() - os.path.getmtime(cache_file)
            if age <= _STREAM_CACHE_TTL:
                cache_hit = True
            else:
                # Файл устарел — удаляем и перекачиваем
                try:
                    os.remove(cache_file)
                except OSError:
                    pass

        if not cache_hit:
            _evict_stream_cache()
            yd_svc.download_file(f"disk:{clean_path}", cache_file)

        return FileResponse(
            cache_file,
            media_type=ct,
            filename=os.path.basename(clean_path),
            headers={"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=604800"},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка стриминга файла: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении файла")


@router.get("/{file_id}")
async def get_file_record(file_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Получить информацию о файле"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")
    return {
        "id": file_record.id,
        "contract_id": file_record.contract_id,
        "stage": file_record.stage,
        "file_type": file_record.file_type,
        "public_link": file_record.public_link,
        "yandex_path": file_record.yandex_path,
        "file_name": file_record.file_name,
        "file_order": file_record.file_order,
        "variation": file_record.variation,
        "uploaded_by": file_record.uploaded_by,
    }


@router.delete("/{file_id}")
async def delete_file_record(file_id: int, current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Удалить запись о файле и файл с Яндекс.Диска"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")

    # Проверка прав: исполнители могут удалять только свои файлы
    manager_positions = {"Руководитель студии", "Старший менеджер проектов", "СДП", "ГАП", "Менеджер"}
    user_position = current_user.position or ""
    is_manager = user_position in manager_positions
    if not is_manager and file_record.uploaded_by != current_user.id:
        raise HTTPException(status_code=403, detail="Вы можете удалять только загруженные вами файлы")

    # Удаляем файл с Яндекс.Диска (до удаления из БД!)
    yandex_path = file_record.yandex_path
    if yandex_path and yandex_disk_available:
        try:
            yd = get_yandex_disk_service()
            yd.delete_file(yandex_path)
            logger.info(f"Файл удалён с Яндекс.Диска: {yandex_path}")
        except Exception as e:
            error_str = str(e)
            if "DiskNotFoundError" not in error_str and "not found" not in error_str.lower():
                logger.warning(f"Не удалось удалить файл с Яндекс.Диска (продолжаем удаление из БД): {e}")
            else:
                logger.info(f"Файл уже удалён с Яндекс.Диска: {yandex_path}")

    db.delete(file_record)
    db.commit()

    return {"status": "success", "message": "Запись о файле удалена"}


@router.patch("/{file_id}/order")
async def update_file_order(file_id: int, file_order: int = Body(embed=True), current_user: Employee = Depends(get_current_user), db: Session = Depends(get_db)):
    """Обновить порядок файла в галерее"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_record.file_order = file_order
    db.commit()

    return {"status": "success", "file_id": file_id, "file_order": file_order}
