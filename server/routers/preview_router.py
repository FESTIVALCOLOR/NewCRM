"""Роутер превью файлов. GET /api/v1/files/preview?yandex_path=...&token=...

JWT принимается как query-параметр ?token= (img src не может передавать заголовки).
Возвращает WebP-превью с Cache-Control: public, max-age=604800 (7 дней).
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from services.preview_service import CACHE_DIR, _is_image, _is_pdf, get_or_create_preview
from sqlalchemy.orm import Session

from database import SessionLocal

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("")
async def get_file_preview(
    yandex_path: str,
    token: str = None,
):
    """Вернуть WebP-превью файла. Генерируется при первом обращении, затем из кэша.
    JWT принимается как ?token= (аналогично /stream — <img src> не передаёт заголовки).
    """
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

    if not yandex_path:
        raise HTTPException(status_code=400, detail="yandex_path обязателен")

    if ".." in yandex_path:
        raise HTTPException(status_code=400, detail="Недопустимый путь")

    if not yandex_path.startswith("disk:"):
        yandex_path = f"disk:{yandex_path}"

    suffix = yandex_path.lower().split("?")[0]
    if not (_is_image(suffix) or _is_pdf(suffix)):
        raise HTTPException(status_code=415, detail="Формат файла не поддерживается для превью")

    db: Session = SessionLocal()
    try:
        preview_path = get_or_create_preview(yandex_path, db)
    except Exception as exc:
        logger.error(f"Ошибка генерации превью для {yandex_path}: {exc}")
        raise HTTPException(status_code=502, detail=f"Не удалось создать превью: {exc}") from exc
    finally:
        db.close()

    if not preview_path.exists():
        raise HTTPException(status_code=404, detail="Превью не найдено")

    return FileResponse(
        path=str(preview_path),
        media_type="image/webp",
        headers={"Cache-Control": "public, max-age=604800, immutable"},
    )
