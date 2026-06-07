"""Роутер превью файлов. GET /api/v1/files/preview?yandex_path=...&token=...

JWT принимается как query-параметр ?token= (img src не может передавать заголовки).
Возвращает WebP-превью с Cache-Control: public, max-age=604800 (7 дней).
"""

import logging

from auth import decode_token
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from services.preview_service import CACHE_DIR, _is_image, _is_pdf, get_or_create_preview
from sqlalchemy.orm import Session

from database import get_db

router = APIRouter()
logger = logging.getLogger(__name__)


def _get_employee_from_token(token: str | None = Query(default=None)):
    """Проверить JWT из query-параметра ?token=."""
    if not token:
        raise HTTPException(status_code=401, detail="Токен не передан")
    return decode_token(token)  # бросает HTTPException при невалидном токене


@router.get("/preview")
async def get_file_preview(
    yandex_path: str = Query(..., description="Путь на Яндекс.Диске (disk:/CRM/...)"),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    _auth=Depends(_get_employee_from_token),
    db: Session = Depends(get_db),
):
    """Вернуть WebP-превью файла. Генерируется при первом обращении, затем из кэша."""
    if not yandex_path:
        raise HTTPException(status_code=400, detail="yandex_path обязателен")

    # Нормализуем путь
    if not yandex_path.startswith("disk:"):
        yandex_path = f"disk:{yandex_path}"

    suffix = yandex_path.lower().split("?")[0]  # убираем query string если есть
    if not (_is_image(suffix) or _is_pdf(suffix)):
        raise HTTPException(status_code=415, detail="Формат файла не поддерживается для превью")

    try:
        preview_path = get_or_create_preview(yandex_path, db)
    except Exception as exc:
        logger.error(f"Ошибка генерации превью для {yandex_path}: {exc}")
        raise HTTPException(status_code=502, detail=f"Не удалось создать превью: {exc}") from exc

    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Превью не найдено")

    return FileResponse(
        path=str(preview_path),
        media_type="image/webp",
        headers={
            "Cache-Control": "public, max-age=604800, immutable",
            "X-Preview-Cache": "hit" if True else "miss",
        },
    )
