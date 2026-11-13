"""
Готовые (шаблонные) дизайны сайта: каталог галерей с отметками мебели на фото.

Публичная часть:  GET /site/ready-designs — видимые дизайны с фото и отметками.
Панель управления: /site/admin/ready-designs/… — только для руководителя студии.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from routers.site_admin_router import ReorderItem, require_site_admin
from sqlalchemy.orm import Session

from database import Employee, ReadyDesign, ReadyDesignImage, SiteSection, get_db

MAX_MARKERS_PER_IMAGE = 30
DIRECTIONS_SECTION_KEY = "directions"

public_router = APIRouter(prefix="/site", tags=["site-public"])
admin_router = APIRouter(prefix="/site/admin/ready-designs", tags=["site-admin"])


# ──────────────────────────────────────────────
# СХЕМЫ
# ──────────────────────────────────────────────


class Marker(BaseModel):
    """Отметка предмета на фото; x и y — проценты от ширины и высоты фото."""

    x: float = Field(ge=0, le=100)
    y: float = Field(ge=0, le=100)
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)
    url: str = Field(default="", max_length=500)
    # Данные товара: фото и характеристики (вводятся вручную или подставляются по ссылке на магазин)
    image_url: str = Field(default="", max_length=1000)
    sku: str = Field(default="", max_length=100)
    color: str = Field(default="", max_length=120)
    shape: str = Field(default="", max_length=120)
    size: str = Field(default="", max_length=200)

    @field_validator("title", "description", "url", "image_url", "sku", "color", "shape", "size")
    @classmethod
    def _strip(cls, value: str) -> str:
        return value.strip()

    @field_validator("image_url")
    @classmethod
    def _only_image_links(cls, value: str) -> str:
        # Адрес попадает в src на публичном сайте: только наши загрузки или обычная веб-ссылка
        if value and not value.startswith("/api/v1/site/media/") and not value.lower().startswith(("http://", "https://")):
            raise ValueError("Фото должно быть загружено в панель или задано ссылкой http(s)://")
        return value

    @field_validator("title")
    @classmethod
    def _title_not_blank(cls, value: str) -> str:
        # Ограничение длины проверяется до обрезки пробелов, поэтому «   » нужно отсечь отдельно
        if not value:
            raise ValueError("У отметки должно быть название")
        return value

    @field_validator("url")
    @classmethod
    def _only_web_links(cls, value: str) -> str:
        # Ссылка попадает в href на публичном сайте: javascript: и подобные схемы недопустимы
        if value and not value.lower().startswith(("http://", "https://")):
            raise ValueError("Ссылка должна начинаться с http:// или https://")
        return value


class ProductLink(BaseModel):
    url: str = Field(min_length=1, max_length=1000)


class ImageCreate(BaseModel):
    url: str = Field(min_length=1, max_length=1000)
    alt: str = Field(default="", max_length=300)


class ImageUpdate(BaseModel):
    alt: Optional[str] = Field(default=None, max_length=300)
    markers: Optional[list[Marker]] = Field(default=None, max_length=MAX_MARKERS_PER_IMAGE)


class ImageResponse(BaseModel):
    id: int
    url: str
    alt: str = ""
    sort_order: int = 0
    markers: list[Marker] = []

    class Config:
        from_attributes = True


class DesignCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    tagline: str = Field(default="", max_length=300)
    description: str = Field(default="", max_length=5000)
    cover_url: Optional[str] = Field(default=None, max_length=1000)
    is_visible: bool = True


class DesignUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    tagline: Optional[str] = Field(default=None, max_length=300)
    description: Optional[str] = Field(default=None, max_length=5000)
    cover_url: Optional[str] = Field(default=None, max_length=1000)
    is_visible: Optional[bool] = None


class DesignResponse(BaseModel):
    id: int
    title: str
    tagline: Optional[str] = ""
    description: Optional[str] = ""
    cover_url: Optional[str] = None
    is_visible: bool = True
    sort_order: int = 0
    images: list[ImageResponse] = []

    class Config:
        from_attributes = True


# ──────────────────────────────────────────────
# СЕКЦИЯ «НАПРАВЛЕНИЯ» НА ГЛАВНОЙ
# ──────────────────────────────────────────────


def ensure_directions_section(db: Session) -> None:
    """Добавляет на главную секцию с выбором направления — на место, где раньше стояло портфолио."""
    if db.query(SiteSection).filter(SiteSection.key == DIRECTIONS_SECTION_KEY).first():
        return
    sections = db.query(SiteSection).order_by(SiteSection.sort_order, SiteSection.id).all()
    position = next((i for i, section in enumerate(sections) if section.key == "portfolio"), len(sections))
    sections.insert(position, SiteSection(key=DIRECTIONS_SECTION_KEY, label="Направления: индивидуальный и готовый дизайн", is_visible=True))
    for index, section in enumerate(sections):
        section.sort_order = index
    db.add(sections[position])
    db.commit()


# ──────────────────────────────────────────────
# ПУБЛИЧНАЯ ВЫДАЧА
# ──────────────────────────────────────────────


@public_router.get("/ready-designs", response_model=list[DesignResponse])
def list_public_designs(db: Session = Depends(get_db)):
    return db.query(ReadyDesign).filter(ReadyDesign.is_visible.is_(True)).order_by(ReadyDesign.sort_order, ReadyDesign.id).all()


# ──────────────────────────────────────────────
# ПАНЕЛЬ УПРАВЛЕНИЯ
# ──────────────────────────────────────────────
# Статические пути (/reorder, /images/…) объявлены ДО динамических /{design_id}


def _design_or_404(db: Session, design_id: int) -> ReadyDesign:
    design = db.query(ReadyDesign).filter(ReadyDesign.id == design_id).first()
    if design is None:
        raise HTTPException(404, "Дизайн не найден")
    return design


def _image_or_404(db: Session, image_id: int) -> ReadyDesignImage:
    image = db.query(ReadyDesignImage).filter(ReadyDesignImage.id == image_id).first()
    if image is None:
        raise HTTPException(404, "Фото не найдено")
    return image


@admin_router.get("", response_model=list[DesignResponse])
def list_designs(db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    return db.query(ReadyDesign).order_by(ReadyDesign.sort_order, ReadyDesign.id).all()


@admin_router.post("", response_model=DesignResponse)
def create_design(data: DesignCreate, db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    design = ReadyDesign(**data.model_dump(), sort_order=db.query(ReadyDesign).count())
    db.add(design)
    db.commit()
    db.refresh(design)
    return design


@admin_router.post("/product-preview")
def preview_product(data: ProductLink, _: Employee = Depends(require_site_admin)):
    """Данные товара по ссылке на страницу магазина — для заполнения отметки на фото."""
    from routers.site_admin_router import UPLOADS_DIR
    from services.site_product_import import ProductImportError, fetch_product

    try:
        return fetch_product(data.url, UPLOADS_DIR)
    except ProductImportError as exc:
        raise HTTPException(400, str(exc))


@admin_router.put("/reorder")
def reorder_designs(items: list[ReorderItem], db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    for item in items:
        design = db.query(ReadyDesign).filter(ReadyDesign.id == item.id).first()
        if design:
            design.sort_order = item.sort_order
    db.commit()
    return {"ok": True}


@admin_router.put("/images/reorder")
def reorder_images(items: list[ReorderItem], db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    for item in items:
        image = db.query(ReadyDesignImage).filter(ReadyDesignImage.id == item.id).first()
        if image:
            image.sort_order = item.sort_order
    db.commit()
    return {"ok": True}


@admin_router.put("/images/{image_id}", response_model=ImageResponse)
def update_image(image_id: int, data: ImageUpdate, db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    image = _image_or_404(db, image_id)
    if data.alt is not None:
        image.alt = data.alt
    if data.markers is not None:
        image.markers = [marker.model_dump() for marker in data.markers]
    db.commit()
    db.refresh(image)
    return image


@admin_router.delete("/images/{image_id}")
def delete_image(image_id: int, db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    db.delete(_image_or_404(db, image_id))
    db.commit()
    return {"ok": True}


@admin_router.put("/{design_id}", response_model=DesignResponse)
def update_design(design_id: int, data: DesignUpdate, db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    design = _design_or_404(db, design_id)
    changes = data.model_dump(exclude_unset=True)
    for key, value in changes.items():
        # Обложку можно сбросить (None), остальные поля пустым значением не затираются
        if value is not None or key == "cover_url":
            setattr(design, key, value)
    db.commit()
    db.refresh(design)
    return design


@admin_router.delete("/{design_id}")
def delete_design(design_id: int, db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    db.delete(_design_or_404(db, design_id))
    db.commit()
    return {"ok": True}


@admin_router.post("/{design_id}/images", response_model=ImageResponse)
def add_image(design_id: int, data: ImageCreate, db: Session = Depends(get_db), _: Employee = Depends(require_site_admin)):
    design = _design_or_404(db, design_id)
    image = ReadyDesignImage(design_id=design.id, url=data.url, alt=data.alt, sort_order=len(design.images), markers=[])
    db.add(image)
    db.commit()
    db.refresh(image)
    return image
