"""Сервис кэширования превью файлов из Яндекс.Диска.

Логика:
- Изображения (jpg/png/gif/webp) и PDF → WebP превью 300px, quality 82
- Кэш хранится в /app/previews/ (именованный Docker volume)
- Запись в file_preview_cache таблице (hash, last_accessed_at)
- 90 дней без обращений → удаление файла и перегенерация при следующем запросе
- LRU-вытеснение при достижении 500 МБ (удаляются самые старые по last_accessed_at)
"""

from datetime import datetime, timedelta
import hashlib
from io import BytesIO
import logging
import os
from pathlib import Path

from PIL import Image
import requests as http_requests
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

CACHE_DIR = Path(os.getenv("PREVIEW_CACHE_PATH", "/app/previews"))
MAX_SIZE_BYTES = 500 * 1024 * 1024  # 500 МБ
STALE_DAYS = 90
PREVIEW_MAX_PX = 300
PREVIEW_QUALITY = 82

_SUPPORTED_IMAGE_EXT = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp", ".tiff"}
_SUPPORTED_PDF_EXT = {".pdf"}


def _path_hash(yandex_path: str) -> str:
    return hashlib.md5(yandex_path.encode(), usedforsecurity=False).hexdigest()  # nosec B324


def _preview_filename(path_hash: str) -> str:
    return f"{path_hash}.webp"


def _get_yd_token() -> str:
    token = os.getenv("YANDEX_DISK_TOKEN", "")
    if not token:
        raise RuntimeError("YANDEX_DISK_TOKEN не задан")
    return token


def _download_from_yd(yandex_path: str) -> bytes:
    """Скачать файл с Яндекс.Диска через API (не публичная ссылка)."""
    token = _get_yd_token()
    clean_path = yandex_path if yandex_path.startswith("disk:") else f"disk:{yandex_path}"

    resp = http_requests.get(
        "https://cloud-api.yandex.net/v1/disk/resources/download",
        headers={"Authorization": f"OAuth {token}"},
        params={"path": clean_path},
        timeout=30,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"ЯД API ошибка ({resp.status_code}): {resp.text[:200]}")

    href = resp.json().get("href")
    if not href:
        raise RuntimeError("ЯД вернул пустой href")

    file_resp = http_requests.get(href, timeout=120)
    if file_resp.status_code != 200:
        raise RuntimeError(f"Ошибка скачивания ({file_resp.status_code})")

    return file_resp.content


def _generate_webp_from_image(data: bytes) -> bytes:
    """PIL: открыть изображение → resize → WebP bytes."""
    img = Image.open(BytesIO(data)).convert("RGB")
    img.thumbnail((PREVIEW_MAX_PX, PREVIEW_MAX_PX), Image.LANCZOS)
    out = BytesIO()
    img.save(out, format="WEBP", quality=PREVIEW_QUALITY)
    return out.getvalue()


def _generate_webp_from_pdf(data: bytes) -> bytes:
    """pypdfium2: первая страница PDF → resize → WebP bytes."""
    try:
        import pypdfium2 as pdfium  # noqa: PLC0415
    except ImportError as exc:
        raise RuntimeError("pypdfium2 не установлен") from exc

    pdf = pdfium.PdfDocument(data)
    page = pdf[0]
    # scale=2 → 144 DPI (достаточно для превью 300px)
    bitmap = page.render(scale=2, rotation=0)
    pil_img = bitmap.to_pil().convert("RGB")
    pdf.close()

    pil_img.thumbnail((PREVIEW_MAX_PX, PREVIEW_MAX_PX), Image.LANCZOS)
    out = BytesIO()
    pil_img.save(out, format="WEBP", quality=PREVIEW_QUALITY)
    return out.getvalue()


def _is_image(yandex_path: str) -> bool:
    return Path(yandex_path).suffix.lower() in _SUPPORTED_IMAGE_EXT


def _is_pdf(yandex_path: str) -> bool:
    return Path(yandex_path).suffix.lower() in _SUPPORTED_PDF_EXT


def _build_preview(yandex_path: str) -> bytes:
    data = _download_from_yd(yandex_path)
    if _is_pdf(yandex_path):
        return _generate_webp_from_pdf(data)
    return _generate_webp_from_image(data)


def get_or_create_preview(yandex_path: str, db: Session) -> Path:
    """Вернуть путь к WebP-превью. Генерирует/регенерирует при необходимости."""
    from database import FilePreviewCache  # noqa: PLC0415

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    ph = _path_hash(yandex_path)
    fname = _preview_filename(ph)
    fpath = CACHE_DIR / fname

    now = datetime.utcnow()
    record: FilePreviewCache | None = db.get(FilePreviewCache, ph)

    need_generate = False

    if record is None:
        need_generate = True
    else:
        # 90-дневная протухаемость
        stale_threshold = now - timedelta(days=STALE_DAYS)
        if record.last_accessed_at < stale_threshold:
            logger.info(f"preview stale (>90d): {yandex_path}")
            if fpath.exists():
                fpath.unlink()
            db.delete(record)
            db.commit()
            record = None
            need_generate = True
        elif not fpath.exists():
            # Запись есть, файл пропал (напр. после ручной очистки)
            db.delete(record)
            db.commit()
            record = None
            need_generate = True

    if need_generate:
        webp_bytes = _build_preview(yandex_path)
        fpath.write_bytes(webp_bytes)
        record = FilePreviewCache(
            path_hash=ph,
            yandex_path=yandex_path,
            preview_filename=fname,
            file_size_bytes=len(webp_bytes),
            created_at=now,
            last_accessed_at=now,
        )
        db.add(record)
        db.commit()
        logger.debug(f"preview created: {fname} ({len(webp_bytes) // 1024}KB) for {yandex_path}")
        cleanup_lru(db)
    else:
        record.last_accessed_at = now
        db.commit()

    return fpath


def cleanup_lru(db: Session) -> None:
    """Удалить старейшие записи пока суммарный размер > MAX_SIZE_BYTES."""
    from database import FilePreviewCache  # noqa: PLC0415

    try:
        records = db.query(FilePreviewCache).order_by(FilePreviewCache.last_accessed_at.asc()).all()
        total = sum(r.file_size_bytes or 0 for r in records)

        if total <= MAX_SIZE_BYTES:
            return

        for rec in records:
            if total <= MAX_SIZE_BYTES:
                break
            fpath = CACHE_DIR / rec.preview_filename
            if fpath.exists():
                fpath.unlink()
            total -= rec.file_size_bytes or 0
            db.delete(rec)
            logger.info(f"preview LRU evicted: {rec.preview_filename}")

        db.commit()
    except Exception as exc:
        logger.warning(f"cleanup_lru error: {exc}")


def cleanup_stale_all(db: Session) -> int:
    """Плановая очистка: удалить все записи старше STALE_DAYS без обращений."""
    from database import FilePreviewCache  # noqa: PLC0415

    threshold = datetime.utcnow() - timedelta(days=STALE_DAYS)
    stale = db.query(FilePreviewCache).filter(FilePreviewCache.last_accessed_at < threshold).all()

    count = 0
    for rec in stale:
        fpath = CACHE_DIR / rec.preview_filename
        if fpath.exists():
            fpath.unlink()
        db.delete(rec)
        count += 1

    if count:
        db.commit()
        logger.info(f"cleanup_stale_all: удалено {count} протухших превью")

    return count
