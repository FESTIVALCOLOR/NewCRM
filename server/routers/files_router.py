"""
Роутер для endpoint'ов файлов проекта (files).
Подключается в main.py через app.include_router(files_router, prefix="/api/files").

ВАЖНО: Статические пути ПЕРЕД динамическими (правило проекта).
"""
import os
import logging
import threading
from datetime import datetime
from fastapi import APIRouter, Body, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List, Optional

from database import get_db, Employee, Contract, ProjectFile
from auth import get_current_user
from schemas import ProjectFileCreate, ProjectFileResponse

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
async def get_all_project_files(
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить все файлы проектов для синхронизации"""
    try:
        files = db.query(ProjectFile).all()

        return [{
            'id': f.id,
            'contract_id': f.contract_id,
            'stage': f.stage,
            'file_type': f.file_type,
            'public_link': f.public_link,
            'yandex_path': f.yandex_path,
            'file_name': f.file_name,
            'preview_cache_path': f.preview_cache_path,
            'file_order': f.file_order,
            'variation': f.variation,
            'upload_date': f.upload_date.isoformat() if f.upload_date else None
        } for f in files]

    except Exception as e:
        logger.exception(f"Ошибка при получении файлов проектов: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/updated")
async def get_updated_files(
    since: str = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить файлы, загруженные после указанного timestamp"""
    if not since:
        raise HTTPException(status_code=400, detail="Parameter 'since' is required")

    try:
        since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid timestamp format")

    files = db.query(ProjectFile).filter(
        ProjectFile.upload_date > since_dt
    ).all()

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
            "variation": f.variation
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
            return {
                "status": "success",
                "public_link": public_link,
                "yandex_path": yandex_path
            }
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

        return {
            "status": "success",
            "folder_path": resolved_path,
            "files": files
        }

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "DiskNotFoundError" in error_str or "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Папка не найдена: {resolved_path}")
        raise HTTPException(status_code=500, detail=f"Error listing files: {error_str}")


@router.post("/", response_model=ProjectFileResponse)
async def create_file_record(
    file_data: ProjectFileCreate,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Создать запись о файле"""
    # Проверяем дубликат по (contract_id, yandex_path) перед вставкой
    data = file_data.model_dump()
    yp = data.get('yandex_path', '')
    if yp:
        existing = db.query(ProjectFile).filter(
            ProjectFile.contract_id == data.get('contract_id'),
            ProjectFile.yandex_path == yp
        ).first()
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
            existing = db.query(ProjectFile).filter(
                ProjectFile.contract_id == data.get('contract_id'),
                ProjectFile.yandex_path == yp
            ).first()
            if existing:
                return existing
        raise HTTPException(status_code=409, detail="Дубликат файла")
    db.refresh(file_record)
    return file_record


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
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp',
        '.dwg', '.dxf', '.skp', '.3ds', '.max', '.blend',
        '.zip', '.rar', '.7z',
        '.txt', '.csv', '.rtf',
    }
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext and ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail=f"Тип файла '{ext}' не разрешён для загрузки"
            )

    try:
        yd_service = get_yandex_disk_service()
        if not yd_service.token:
            raise HTTPException(status_code=503, detail="Yandex Disk token not configured")
        file_bytes = await file.read()

        # Проверка размера файла
        max_size = int(os.environ.get("MAX_FILE_SIZE_MB", 50)) * 1024 * 1024
        if len(file_bytes) > max_size:
            raise HTTPException(
                status_code=413,
                detail=f"Размер файла превышает максимально допустимый ({os.environ.get('MAX_FILE_SIZE_MB', 50)} МБ)"
            )

        if not yandex_path:
            # Защита от path traversal в имени файла
            safe_filename = os.path.basename(file.filename or "unnamed")
            yandex_path = f"/CRM/Временные файлы/{safe_filename}"
        else:
            # Защита от path traversal: запрещаем ".." в пути
            if ".." in yandex_path:
                raise HTTPException(status_code=400, detail="Недопустимый путь файла")

        result = yd_service.upload_file_from_bytes(file_bytes, yandex_path)

        if result:
            public_link = yd_service.get_public_link(yandex_path)
            return {
                "status": "success",
                "yandex_path": yandex_path,
                "public_link": public_link,
                "file_name": file.filename
            }
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

        return {
            "status": "success" if result else "exists",
            "folder_path": folder_path
        }

    except HTTPException:
        raise
    except Exception as e:
        error_str = str(e)
        if "DiskNotFoundError" in error_str or "not found" in error_str.lower():
            raise HTTPException(status_code=404, detail=f"Путь не найден: {folder_path}")
        raise HTTPException(status_code=500, detail=f"Folder creation error: {error_str}")


@router.post("/validate")
async def validate_files(
    request: dict,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
            if not exists and check_path.startswith('disk:'):
                exists = yd.file_exists(check_path[5:])
            # И наоборот
            if not exists and not check_path.startswith('disk:'):
                exists = yd.file_exists('disk:' + check_path)
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

        return {
            "status": "success" if result else "not_found",
            "yandex_path": yandex_path
        }

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

@router.get("/contract/{contract_id}", response_model=List[ProjectFileResponse])
async def get_contract_files(
    contract_id: int,
    stage: Optional[str] = None,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить файлы договора"""
    query = db.query(ProjectFile).filter(ProjectFile.contract_id == contract_id)
    if stage:
        query = query.filter(ProjectFile.stage == stage)
    return query.order_by(ProjectFile.file_order).all()


@router.post("/scan/{contract_id}")
async def scan_contract_files_on_yandex(
    contract_id: int,
    scope: str = "all",
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
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
            return {
                "status": "already_scanning",
                "total_on_disk": 0,
                "already_in_db": 0,
                "new_files_added": 0,
                "new_files": []
            }
        _scanning_contracts.add(contract_id)

    try:
        yd_service = get_yandex_disk_service()

        # Точный маппинг папок → стадий
        folder_to_stage_exact = {
            'Замер': 'measurement',
            'Замеры': 'measurement',
            '1 стадия - Планировочное решение': 'stage1',
            'Планировочное решение': 'stage1',
            'Концепция-коллажи': 'stage2_concept',
            'Коллажи': 'stage2_concept',
            '3D визуализация': 'stage2_3d',
            '3D': 'stage2_3d',
            '3 стадия - Чертежный проект': 'stage3',
            'Чертежный проект': 'stage3',
            'Чертежи': 'stage3',
            'Референсы': 'references',
            'Фотофиксация': 'photo_documentation',
            'Фото': 'photo_documentation',
            'Анкета': 'questionnaire',
            'Анкеты': 'questionnaire',
            'Документы': 'documents',
            'Техническое задание': 'tech_task',
            'ТЗ': 'tech_task',
            'Авторский надзор': 'supervision',
        }

        # Нечёткий маппинг: ключевые слова → стадия (для папок с нестандартными именами)
        folder_keywords_to_stage = [
            ('замер', 'measurement'),
            ('1 стадия', 'stage1'),
            ('1стадия', 'stage1'),
            ('планировочн', 'stage1'),
            ('концепция', 'stage2_concept'),
            ('коллаж', 'stage2_concept'),
            ('3d', 'stage2_3d'),
            ('визуализ', 'stage2_3d'),
            ('2 стадия', 'stage2_concept'),
            ('2стадия', 'stage2_concept'),
            ('3 стадия', 'stage3'),
            ('3стадия', 'stage3'),
            ('чертеж', 'stage3'),
            ('рабочи', 'stage3'),
            ('референ', 'references'),
            ('фотофикс', 'photo_documentation'),
            ('фото', 'photo_documentation'),
            ('анкет', 'questionnaire'),
            ('документ', 'documents'),
            ('техническ', 'tech_task'),
            ('надзор', 'supervision'),
        ]

        def match_folder_to_stage(folder_name):
            """Определить стадию по имени папки: сначала точное, потом нечёткое"""
            # Точное совпадение
            if folder_name in folder_to_stage_exact:
                return folder_to_stage_exact[folder_name]
            # Нечёткое: ищем ключевое слово в нижнем регистре
            name_lower = folder_name.lower()
            for keyword, stage_id in folder_keywords_to_stage:
                if keyword in name_lower:
                    return stage_id
            return None

        def detect_file_type(name):
            ext = name.rsplit('.', 1)[-1].lower() if '.' in name else ''
            if ext in ('png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'svg'):
                return 'image'
            elif ext == 'pdf':
                return 'pdf'
            elif ext in ('xls', 'xlsx', 'csv'):
                return 'excel'
            elif ext in ('doc', 'docx'):
                return 'word'
            elif ext in ('dwg', 'dxf'):
                return 'cad'
            return 'other'

        def normalize_path(p):
            """Нормализация пути: убираем 'disk:' префикс для сравнения"""
            if p and p.startswith('disk:'):
                return p[5:]
            return p or ''

        found_files = []

        def scan_folder(path, stage=None):
            try:
                items = yd_service.list_files(path)
                for item in items:
                    item_name = item.get('name', '')
                    item_path = item.get('path', '')
                    item_type = item.get('type', '')

                    if item_type == 'dir':
                        # Пропускаем папку "правки" — файлы правок отображаются отдельно
                        if item_name.lower() == 'правки':
                            continue
                        child_stage = match_folder_to_stage(item_name)
                        if child_stage is None:
                            child_stage = stage  # наследуем стадию от родителя
                        # Внутри Авторского надзора подпапки "Стадия ..." остаются supervision
                        if stage == 'supervision' and item_name.startswith('Стадия'):
                            child_stage = 'supervision'
                        # Подпапки "Вариация N" наследуют стадию от родителя
                        if item_name.startswith('Вариация') or item_name.startswith('вариация'):
                            child_stage = stage
                        scan_folder(item_path, child_stage)
                    elif item_type == 'file':
                        # Файлы с определённой стадией добавляем
                        # Файлы в корне (stage=None) — пропускаем
                        if stage:
                            found_files.append({
                                'yandex_path': item_path,
                                'file_name': item_name,
                                'stage': stage,
                                'file_type': detect_file_type(item_name),
                            })
            except Exception as e:
                logger.warning(f"Ошибка сканирования {path}: {e}")

        if scope == 'supervision':
            # Для надзора сканируем только подпапку "Авторский надзор"
            supervision_path = folder_path.rstrip('/') + '/Авторский надзор'
            logger.info(f"Scan scope=supervision: сканируем только {supervision_path}")
            scan_folder(supervision_path, stage='supervision')
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
                if not norm.startswith('/'):
                    existing_paths_normalized.add('/' + norm)
                else:
                    existing_paths_normalized.add(norm.lstrip('/'))

        # Создаём записи для новых файлов (сравнение по нормализованному пути)
        new_files = []
        for f in found_files:
            yp = f['yandex_path']
            yp_normalized = normalize_path(yp)

            if yp_normalized in existing_paths_normalized:
                continue

            # Добавляем в множество чтобы не дублировать внутри одного скана
            existing_paths_normalized.add(yp_normalized)

            # Получаем публичную ссылку
            try:
                public_link = yd_service.get_public_link(yp)
            except Exception:
                public_link = ''

            # Для файлов надзора file_type хранит название стадии
            file_type_val = f['file_type']
            if f['stage'] == 'supervision':
                # Определяем стадию надзора из пути
                parts = yp.split('/')
                for part in parts:
                    if part.startswith('Стадия'):
                        file_type_val = part
                        break

            # Дополнительная проверка: прямой запрос в БД (защита от дубликатов)
            existing_exact = db.query(ProjectFile).filter(
                ProjectFile.contract_id == contract_id,
                ProjectFile.yandex_path == yp
            ).first()
            if existing_exact:
                logger.info(f"Scan: файл уже есть в БД (exact match), пропускаем: {f['file_name']}")
                continue

            new_record = ProjectFile(
                contract_id=contract_id,
                stage=f['stage'],
                file_type=file_type_val,
                yandex_path=yp,
                public_link=public_link,
                file_name=f['file_name']
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
            new_files.append({
                'yandex_path': yp,
                'file_name': f['file_name'],
                'stage': f['stage'],
                'file_type': file_type_val,
                'public_link': public_link,
            })

        # Для файлов из "Анкета" (questionnaire/tech_task): обновляем contract.tech_task_link
        tech_task_files = [f for f in new_files if f['stage'] in ('questionnaire', 'tech_task')]
        if tech_task_files and not contract.tech_task_link:
            first_tt = tech_task_files[0]
            contract.tech_task_link = first_tt.get('public_link', '')
            contract.tech_task_yandex_path = first_tt.get('yandex_path', '')
            contract.tech_task_file_name = first_tt.get('file_name', '')
            logger.info(f"Scan: обновлён tech_task_link для contract {contract_id}")

        # Обновляем references_yandex_path и photo_documentation_yandex_path
        # Логика: файлы есть → создать ссылку; файлов нет → очистить ссылку
        contract_updated = False

        if scope == 'all':
            ref_files = [f for f in found_files if f['stage'] == 'references']
            if ref_files:
                # Файлы есть — создаём ссылку если нет
                if not contract.references_yandex_path:
                    try:
                        first_ref_path = ref_files[0]['yandex_path']
                        ref_folder = '/'.join(first_ref_path.split('/')[:-1])
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

            photo_files = [f for f in found_files if f['stage'] == 'photo_documentation']
            if photo_files:
                # Файлы есть — создаём ссылку если нет
                if not contract.photo_documentation_yandex_path:
                    try:
                        first_photo_path = photo_files[0]['yandex_path']
                        photo_folder = '/'.join(first_photo_path.split('/')[:-1])
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
            "contract_updated": contract_updated
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

@router.get("/{file_id}")
async def get_file_record(
    file_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Получить информацию о файле"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")
    return {
        'id': file_record.id,
        'contract_id': file_record.contract_id,
        'stage': file_record.stage,
        'file_type': file_record.file_type,
        'public_link': file_record.public_link,
        'yandex_path': file_record.yandex_path,
        'file_name': file_record.file_name,
        'file_order': file_record.file_order,
        'variation': file_record.variation
    }


@router.delete("/{file_id}")
async def delete_file_record(
    file_id: int,
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Удалить запись о файле и файл с Яндекс.Диска"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")

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
async def update_file_order(
    file_id: int,
    file_order: int = Body(embed=True),
    current_user: Employee = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Обновить порядок файла в галерее"""
    file_record = db.query(ProjectFile).filter(ProjectFile.id == file_id).first()
    if not file_record:
        raise HTTPException(status_code=404, detail="Файл не найден")

    file_record.file_order = file_order
    db.commit()

    return {"status": "success", "file_id": file_id, "file_order": file_order}
