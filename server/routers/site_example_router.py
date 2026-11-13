"""
Блок сайта «Посмотреть пример проекта»: загрузка PDF в панели управления.
Готовый пример попадает на сайт через общие настройки (/site/public → settings.example_project).
"""

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from routers.site_admin_router import UPLOADS_DIR, require_site_admin
from sqlalchemy.orm import Session

from database import Employee, SiteSection, get_db

EXAMPLE_SECTION_KEY = "project_example"

admin_router = APIRouter(prefix="/site/admin/example-project", tags=["site-admin"])


def ensure_example_section(db: Session) -> None:
    """Добавляет на главную секцию примера проекта — сразу после «Услуг»."""
    if db.query(SiteSection).filter(SiteSection.key == EXAMPLE_SECTION_KEY).first():
        return
    sections = db.query(SiteSection).order_by(SiteSection.sort_order, SiteSection.id).all()
    after = next((i for i, section in enumerate(sections) if section.key == "services"), len(sections) - 1)
    new = SiteSection(key=EXAMPLE_SECTION_KEY, label="Пример проекта (книга PDF)", is_visible=True)
    sections.insert(after + 1, new)
    for index, section in enumerate(sections):
        section.sort_order = index
    db.add(new)
    db.commit()


@admin_router.get("")
def get_example_project(db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    from services.site_example_project import state

    return state(db)


@admin_router.post("")
async def upload_example_project(file: UploadFile = File(...), db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    """Загружает PDF проекта; страницы готовятся в фоне, ход виден в ответе GET."""
    from services.site_example_project import MAX_PDF_BYTES, ExampleProjectError, start_upload

    # Читаем не больше лимита плюс один байт: по нему видно превышение, а огромный файл в память не попадёт
    content = await file.read(MAX_PDF_BYTES + 1)
    try:
        return start_upload(db, content, file.filename or "", UPLOADS_DIR)
    except ExampleProjectError as exc:
        raise HTTPException(400, str(exc))


@admin_router.delete("")
def delete_example_project(db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    from services.site_example_project import delete_project

    delete_project(db, UPLOADS_DIR)
    return {"ok": True}
