"""
Блок сайта «Посмотреть пример проекта»: PDF дизайн-проекта, который листается на сайте как книга.

Страницы PDF один раз превращаются в картинки на сервере — при загрузке файла. Посетителю не нужно
скачивать весь PDF и библиотеку для его чтения: страницы подгружаются по мере листания.
Чертежи в PDF бывают тяжёлыми, поэтому обработка идёт в фоне, а панель показывает прогресс.

Состояние хранится в настройках сайта (видны обоим сервисам — сайта и CRM):
  example_project      — готовый пример: страницы, размер, исходный PDF (его читает сайт);
  example_project_job  — ход обработки нового файла (его читает панель).
Пока новый файл обрабатывается, на сайте остаётся прежний пример.
"""

from datetime import datetime
import json
import logging
import os
import threading
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

PROJECT_KEY = "example_project"
JOB_KEY = "example_project_job"
MAX_PDF_BYTES = 200 * 1024 * 1024
MAX_PAGES = 150
# Длинная сторона страницы-картинки: чертежи читаются, а страница весит 150–400 КБ
PAGE_LONG_SIDE = 1600
JPEG_QUALITY = 82
MEDIA_PREFIX = "/api/v1/site/media/"

_lock = threading.Lock()


class ExampleProjectError(ValueError):
    """Файл не подходит; текст показывается в панели."""


def _get(db, key: str) -> Optional[dict]:
    # База подключается при вызове, а не при импорте: проверку PDF можно тестировать без неё
    from database import SiteSetting

    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    if not row or not row.value:
        return None
    try:
        value = json.loads(row.value)
        return value if isinstance(value, dict) else None
    except ValueError:
        return None


def _put(db, key: str, value: Optional[dict]) -> None:
    from database import SiteSetting

    row = db.query(SiteSetting).filter(SiteSetting.key == key).first()
    text = json.dumps(value, ensure_ascii=False) if value is not None else ""
    if row:
        row.value = text
    else:
        db.add(SiteSetting(key=key, value=text))
    db.commit()


def state(db) -> dict:
    return {"project": _get(db, PROJECT_KEY), "job": _get(db, JOB_KEY)}


def _media_files(project: Optional[dict]) -> list[str]:
    """Имена файлов примера в каталоге загрузок сайта."""
    if not project:
        return []
    urls = [*project.get("pages", []), project.get("pdf", "")]
    return [url[len(MEDIA_PREFIX) :] for url in urls if isinstance(url, str) and url.startswith(MEDIA_PREFIX)]


def _remove_files(uploads_dir: str, names: list[str]) -> None:
    for name in names:
        # Имена создаём сами (uuid), но всё равно не выходим за пределы каталога загрузок
        if "/" in name or "\\" in name or name.startswith("."):
            continue
        try:
            os.remove(os.path.join(uploads_dir, name))
        except FileNotFoundError:
            pass


def check_pdf(content: bytes) -> int:
    """Проверяет файл и возвращает число страниц."""
    if len(content) > MAX_PDF_BYTES:
        raise ExampleProjectError("Файл слишком большой (максимум 200 МБ)")
    if not content.startswith(b"%PDF"):
        raise ExampleProjectError("Это не PDF-файл")
    import pypdfium2 as pdfium

    try:
        document = pdfium.PdfDocument(content)
    except Exception as exc:
        raise ExampleProjectError("Не удалось открыть PDF — возможно, файл повреждён или защищён паролем") from exc
    try:
        pages = len(document)
    finally:
        document.close()
    if pages == 0:
        raise ExampleProjectError("В PDF нет страниц")
    if pages > MAX_PAGES:
        raise ExampleProjectError(f"В PDF {pages} страниц — для показа на сайте возьмите не больше {MAX_PAGES}")
    return pages


def render_pages(pdf_path: str, uploads_dir: str, token: str, on_page=None) -> tuple[list[str], int, int]:
    """Страницы PDF → картинки JPEG. Возвращает адреса картинок и размер первой страницы."""
    import pypdfium2 as pdfium

    document = pdfium.PdfDocument(pdf_path)
    urls: list[str] = []
    size = (0, 0)
    try:
        total = len(document)
        for index in range(total):
            page = document[index]
            width, height = page.get_size()
            scale = PAGE_LONG_SIDE / max(width, height)
            image = page.render(scale=scale).to_pil().convert("RGB")
            page.close()
            if index == 0:
                size = image.size
            name = f"{token}-p{index + 1:03d}.jpg"
            image.save(os.path.join(uploads_dir, name), "JPEG", quality=JPEG_QUALITY, optimize=True, progressive=True)
            urls.append(MEDIA_PREFIX + name)
            if on_page:
                on_page(index + 1, total)
    finally:
        document.close()
    return urls, size[0], size[1]


def _process(pdf_name: str, original_name: str, uploads_dir: str, token: str, pages: int) -> None:
    from database import SessionLocal

    db = SessionLocal()
    try:
        last_saved = [0]

        def progress(done: int, total: int) -> None:
            # Прогресс пишем не чаще раза в несколько страниц — это запись в базу
            if done - last_saved[0] >= 3 or done == total:
                last_saved[0] = done
                _put(db, JOB_KEY, {"status": "processing", "done": done, "total": total, "name": original_name})

        urls, width, height = render_pages(os.path.join(uploads_dir, pdf_name), uploads_dir, token, progress)
        old = _get(db, PROJECT_KEY)
        _put(
            db,
            PROJECT_KEY,
            {
                "pages": urls,
                "width": width,
                "height": height,
                "pdf": MEDIA_PREFIX + pdf_name,
                "name": original_name,
                "uploaded_at": datetime.utcnow().isoformat() + "Z",
            },
        )
        _put(db, JOB_KEY, {"status": "done", "done": pages, "total": pages, "name": original_name})
        # Прежний пример заменён — его файлы больше не нужны
        _remove_files(uploads_dir, _media_files(old))
    except Exception as exc:
        logger.exception("Пример проекта: ошибка обработки PDF")
        db.rollback()
        _put(db, JOB_KEY, {"status": "error", "error": f"Не удалось обработать PDF ({type(exc).__name__})", "name": original_name})
        _remove_files(uploads_dir, [pdf_name] + [f"{token}-p{i:03d}.jpg" for i in range(1, pages + 1)])
    finally:
        db.close()
        _lock.release()


def start_upload(db, content: bytes, original_name: str, uploads_dir: str) -> dict:
    """Сохраняет PDF и запускает обработку в фоне."""
    pages = check_pdf(content)
    if not _lock.acquire(blocking=False):
        raise ExampleProjectError("Предыдущий файл ещё обрабатывается — дождитесь окончания")
    try:
        os.makedirs(uploads_dir, exist_ok=True)
        token = uuid.uuid4().hex
        pdf_name = f"{token}.pdf"
        with open(os.path.join(uploads_dir, pdf_name), "wb") as file:
            file.write(content)
        name = os.path.basename(original_name or "проект.pdf")[:120]
        _put(db, JOB_KEY, {"status": "processing", "done": 0, "total": pages, "name": name})
        threading.Thread(target=_process, args=(pdf_name, name, uploads_dir, token, pages), name="example-project", daemon=True).start()
    except Exception:
        _lock.release()
        raise
    return state(db)


def delete_project(db, uploads_dir: str) -> None:
    """Убирает пример с сайта вместе с файлами."""
    _remove_files(uploads_dir, _media_files(_get(db, PROJECT_KEY)))
    _put(db, PROJECT_KEY, None)
    _put(db, JOB_KEY, None)
