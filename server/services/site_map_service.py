"""
Карта объектов сайта: синхронизация точек с договорами CRM и выдача данных.

Публичная выдача не содержит адресов, номеров договоров и имён клиентов —
только сдвинутые координаты, состояние объекта и город.
"""

from datetime import datetime, timedelta
import logging
import threading
from typing import Optional

from constants import STATUS_COMPLETED, STATUS_SUPERVISION, STATUS_TERMINATED
from services.site_map_geo import address_hash, city_name, geocode_address, privacy_offset, resolve_city_center
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import get_settings
from database import Contract, SessionLocal, SiteMapPoint, SiteSection

logger = logging.getLogger(__name__)

MAP_SECTION_KEY = "objects_map"
# Ненайденный адрес проверяется заново раз в неделю: данные геокодера пополняются
RETRY_NOT_FOUND_AFTER = timedelta(days=7)

_sync_lock = threading.Lock()
_state: dict = {"running": False, "last_sync": None, "last_error": None}


def ensure_map_section(db: Session) -> None:
    """Добавляет секцию карты в список секций сайта (последней), если её ещё нет."""
    if db.query(SiteSection).filter(SiteSection.key == MAP_SECTION_KEY).first():
        return
    last = db.query(func.max(SiteSection.sort_order)).scalar()
    db.add(SiteSection(key=MAP_SECTION_KEY, label="Карта объектов", is_visible=True, sort_order=(last if last is not None else -1) + 1))
    db.commit()


def _eligible_contracts(db: Session):
    """Договоры, объекты которых показываются на карте: с адресом и не расторгнутые."""
    return db.query(Contract).filter(Contract.address.isnot(None), func.trim(Contract.address) != "").filter(func.coalesce(Contract.status, "") != STATUS_TERMINATED)


def point_kind(contract_status: Optional[str]) -> str:
    if contract_status == STATUS_COMPLETED:
        return "done"
    if contract_status == STATUS_SUPERVISION:
        return "supervision"
    return "work"


def _needs_geocoding(point: Optional[SiteMapPoint], current_hash: str, now: datetime) -> bool:
    if point is None or point.address_hash != current_hash:
        return True
    if point.status == "not_found":
        return not point.geocoded_at or now - point.geocoded_at > RETRY_NOT_FOUND_AFTER
    return False


def sync_map_points() -> bool:
    """Находит координаты для новых и изменённых адресов. False — если синхронизация уже идёт."""
    if not _sync_lock.acquire(blocking=False):
        return False
    _state.update(running=True, last_error=None)
    db = SessionLocal()
    try:
        contracts = _eligible_contracts(db).all()
        points = {p.contract_id: p for p in db.query(SiteMapPoint).all()}

        eligible_ids = {c.id for c in contracts}
        for contract_id, point in points.items():
            if contract_id not in eligible_ids:
                db.delete(point)
        db.commit()

        centers: dict = {}
        for contract in contracts:
            now = datetime.utcnow()
            current_hash = address_hash(contract.address, contract.city)
            point = points.get(contract.id)
            if not _needs_geocoding(point, current_hash, now):
                continue
            try:
                city = (contract.city or "").strip()
                if city not in centers:
                    centers[city] = resolve_city_center(city)
                found = geocode_address(contract.address, city, centers[city])
            except Exception as exc:
                # Сбой сети — не «адрес не найден»: точку не трогаем, попробуем при следующем запуске
                _state["last_error"] = f"Геокодер недоступен: {type(exc).__name__}"
                logger.warning("Карта объектов: сбой геокодера: %s", type(exc).__name__)
                break
            if point is None:
                point = SiteMapPoint(contract_id=contract.id)
                db.add(point)
            point.address_hash = current_hash
            point.geocoded_at = now
            if found:
                point.lat, point.lon, point.precision, point.status = found.lat, found.lon, found.precision, "ok"
            else:
                point.lat, point.lon, point.precision, point.status = None, None, None, "not_found"
            db.commit()
        _state["last_sync"] = datetime.utcnow()
        return True
    except Exception as exc:
        db.rollback()
        _state["last_error"] = f"Ошибка синхронизации: {type(exc).__name__}"
        logger.exception("Карта объектов: ошибка синхронизации")
        return True
    finally:
        db.close()
        _state["running"] = False
        _sync_lock.release()


def start_sync_in_background() -> bool:
    """Запускает синхронизацию в отдельном потоке. False — если она уже идёт."""
    if _state["running"]:
        return False
    threading.Thread(target=sync_map_points, name="site-map-sync", daemon=True).start()
    return True


def public_points(db: Session) -> dict:
    """Точки для публичной карты: без адресов, со сдвигом координат."""
    secret = get_settings().secret_key
    rows = (
        db.query(SiteMapPoint, Contract.status, Contract.city)
        .join(Contract, Contract.id == SiteMapPoint.contract_id)
        .filter(SiteMapPoint.status == "ok", SiteMapPoint.lat.isnot(None), SiteMapPoint.lon.isnot(None))
        .filter(SiteMapPoint.hidden.is_(False))
        .filter(func.coalesce(Contract.status, "") != STATUS_TERMINATED)
        .all()
    )
    points = []
    city_counts: dict = {}
    for point, contract_status, city in rows:
        lat, lon = privacy_offset(point.contract_id, point.lat, point.lon, secret)
        name = city_name(city) or "Другие города"
        points.append({"lat": lat, "lon": lon, "kind": point_kind(contract_status), "city": name})
        city_counts[name] = city_counts.get(name, 0) + 1
    cities = [{"name": name, "count": count} for name, count in sorted(city_counts.items(), key=lambda item: -item[1])]
    return {"points": points, "cities": cities, "total": len(points)}


def map_status(db: Session) -> dict:
    """Состояние карты для панели управления (только для администратора сайта)."""
    contracts = _eligible_contracts(db).order_by(Contract.id.desc()).all()
    points = {p.contract_id: p for p in db.query(SiteMapPoint).all()}
    counts = {"shown": 0, "approximate": 0, "not_found": 0, "pending": 0, "hidden": 0}
    objects = []
    for contract in contracts:
        point = points.get(contract.id)
        if point is None or point.address_hash != address_hash(contract.address, contract.city):
            state = "pending"
        elif point.status == "not_found":
            state = "not_found"
        elif point.hidden:
            state = "hidden"
        else:
            state = "shown"
            if point.precision == "street":
                counts["approximate"] += 1
        counts[state] += 1
        objects.append(
            {
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "city": city_name(contract.city),
                "address": contract.address,
                "state": state,
                # Скрыть можно только объект, для которого уже есть запись с координатами
                "can_toggle": point is not None and state in ("shown", "hidden"),
            }
        )
    return {
        "total": len(contracts),
        **counts,
        "running": _state["running"],
        "last_sync": _state["last_sync"].isoformat() + "Z" if _state["last_sync"] else None,
        "last_error": _state["last_error"],
        "objects": objects,
    }


def set_point_hidden(db: Session, contract_id: int, hidden: bool) -> bool:
    """Скрывает объект с карты или возвращает его. False — если для договора ещё нет точки."""
    point = db.query(SiteMapPoint).filter(SiteMapPoint.contract_id == contract_id).first()
    if point is None:
        return False
    point.hidden = hidden
    db.commit()
    return True
