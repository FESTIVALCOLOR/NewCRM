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
from services.site_map_geo import ADDRESS_MODES, FuzzyGuard, address_hash, address_key, city_name, geocode_address, point_label, privacy_offset, resolve_city_center
from sqlalchemy import func
from sqlalchemy.orm import Session

from config import get_settings
from database import Contract, SessionLocal, SiteMapExtraObject, SiteMapPoint, SiteSection, SiteSetting

logger = logging.getLogger(__name__)

MAP_SECTION_KEY = "objects_map"
# Ненайденный адрес проверяется заново раз в неделю: данные геокодера пополняются
RETRY_NOT_FOUND_AFTER = timedelta(days=7)
# Подряд столько адресов не удалось проверить из-за сети — геокодер, видимо, недоступен: прекращаем до следующего запуска
MAX_NETWORK_FAILURES = 5

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


def _needs_geocoding(point, current_hash: str, now: datetime) -> bool:
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

        # Сначала объекты договоров, затем загруженные из файла
        jobs = [(contract.id, None, contract.address, contract.city) for contract in contracts]
        jobs += [(None, extra, extra.address, extra.city) for extra in db.query(SiteMapExtraObject).order_by(SiteMapExtraObject.id).all()]
        centers: dict = {}
        failures = 0
        fuzzy = FuzzyGuard()
        postponed = 0
        for contract_id, extra, address, raw_city in jobs:
            now = datetime.utcnow()
            current_hash = address_hash(address, raw_city)
            point = extra if extra is not None else points.get(contract_id)
            if not _needs_geocoding(point, current_hash, now):
                continue
            try:
                city = (raw_city or "").strip()
                if city not in centers:
                    centers[city] = resolve_city_center(city)
                found = geocode_address(address, city, centers[city], fuzzy=fuzzy)
            except Exception as exc:
                # Сбой сети — не «адрес не найден»: точку не трогаем, адрес проверим при следующем запуске.
                # Один сбой не останавливает обновление — остальные адреса ищутся дальше
                failures += 1
                logger.warning("Карта объектов: сбой геокодера (%s подряд): %s", failures, type(exc).__name__)
                if failures >= MAX_NETWORK_FAILURES:
                    _state["last_error"] = f"Геокодер недоступен ({type(exc).__name__}) — поиск продолжится автоматически через несколько минут"
                    break
                continue
            failures = 0
            if found is None and fuzzy.down:
                # Без нестрогого геокодера поиск неполный: «не найден» ставить нельзя — адрес остаётся в очереди
                postponed += 1
                continue
            if point is None:
                point = SiteMapPoint(contract_id=contract_id)
                db.add(point)
            point.address_hash = current_hash
            point.geocoded_at = now
            if found:
                point.lat, point.lon, point.precision, point.status = found.lat, found.lon, found.precision, "ok"
                point.place, point.street, point.house = found.place, found.street, found.house
            else:
                point.lat, point.lon, point.precision, point.status = None, None, None, "not_found"
                point.place, point.street, point.house = None, None, None
            db.commit()
        if postponed and not _state["last_error"]:
            _state["last_error"] = f"Быстрый геокодер временно недоступен — {postponed} адресов ждут его возвращения, поиск повторится автоматически"
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
    # Признак выставляется сразу, а не в потоке: панель по нему понимает, что нужно следить за ходом поиска
    _state["running"] = True
    threading.Thread(target=sync_map_points, name="site-map-sync", daemon=True).start()
    return True


ADDRESS_MODE_KEY = "map_address_mode"


def address_mode(db: Session) -> str:
    """Что показывать при наведении на точку; по умолчанию — улицу и дом."""
    row = db.query(SiteSetting).filter(SiteSetting.key == ADDRESS_MODE_KEY).first()
    value = (row.value or "").strip() if row else ""
    return value if value in ADDRESS_MODES else "house"


def public_points(db: Session) -> dict:
    """Точки для публичной карты.

    Номера договоров, имена и квартиры на сайт не попадают никогда: подпись строится из адреса,
    который вернула картографическая база, а не из текста CRM. Подпись — по настройке:
    улица и дом (тогда точка стоит точно на доме — сдвиг потерял бы смысл), только улица или ничего
    (тогда точка сдвинута на 60–150 м, чтобы по ней нельзя было найти дом).
    """
    secret = get_settings().secret_key
    mode = address_mode(db)

    def place(key, lat, lon):
        return (round(lat, 5), round(lon, 5)) if mode == "house" else privacy_offset(key, lat, lon, secret)

    def item(lat, lon, kind, name, found):
        point = {"lat": lat, "lon": lon, "kind": kind, "city": name}
        label = point_label(found.place, found.street, found.house, mode)
        if label:
            point["label"] = label
        return point

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
        lat, lon = place(point.contract_id, point.lat, point.lon)
        name = city_name(city) or "Другие города"
        points.append(item(lat, lon, point_kind(contract_status), name, point))
        city_counts[name] = city_counts.get(name, 0) + 1
    extras = (
        db.query(SiteMapExtraObject)
        .filter(SiteMapExtraObject.status == "ok", SiteMapExtraObject.lat.isnot(None), SiteMapExtraObject.lon.isnot(None))
        .filter(SiteMapExtraObject.hidden.is_(False))
        .all()
    )
    for extra in extras:
        # Объекты из файла — выполненные проекты прошлых лет; правила те же, что у объектов договоров
        lat, lon = place(f"extra-{extra.id}", extra.lat, extra.lon)
        name = city_name(extra.city) or "Другие города"
        points.append(item(lat, lon, "done", name, extra))
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
                "key": f"crm-{contract.id}",
                "source": "crm",
                "extra_id": None,
                "contract_id": contract.id,
                "contract_number": contract.contract_number,
                "city": city_name(contract.city),
                "address": contract.address,
                "state": state,
                # Скрыть можно только объект, для которого уже есть запись с координатами
                "can_toggle": point is not None and state in ("shown", "hidden"),
            }
        )
    extras = db.query(SiteMapExtraObject).order_by(SiteMapExtraObject.id.desc()).all()
    for extra in extras:
        if extra.address_hash != address_hash(extra.address, extra.city):
            state = "pending"
        elif extra.status == "not_found":
            state = "not_found"
        elif extra.hidden:
            state = "hidden"
        else:
            state = "shown"
            if extra.precision == "street":
                counts["approximate"] += 1
        counts[state] += 1
        objects.append(
            {
                "key": f"file-{extra.id}",
                "source": "file",
                "extra_id": extra.id,
                "contract_id": None,
                "contract_number": "из файла",
                "city": city_name(extra.city),
                "address": extra.address,
                "state": state,
                "can_toggle": state in ("shown", "hidden"),
            }
        )
    return {
        "total": len(contracts),
        "extra_total": len(extras),
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


def set_extra_hidden(db: Session, extra_id: int, hidden: bool) -> bool:
    """Скрывает с карты объект из файла или возвращает его. False — если такого объекта нет."""
    extra = db.query(SiteMapExtraObject).filter(SiteMapExtraObject.id == extra_id).first()
    if extra is None:
        return False
    extra.hidden = hidden
    db.commit()
    return True


def delete_extra(db: Session, extra_id: Optional[int] = None) -> int:
    """Удаляет один объект из файла или, без номера, все загруженные. Возвращает число удалённых."""
    query = db.query(SiteMapExtraObject)
    if extra_id is not None:
        query = query.filter(SiteMapExtraObject.id == extra_id)
    deleted = query.delete(synchronize_session=False)
    db.commit()
    return deleted


def import_extra_objects(db: Session, rows: list) -> dict:
    """Добавляет объекты из файла; уже известные адреса (в CRM или загруженные раньше) пропускает."""
    known = {address_key(c.address, c.city) for c in _eligible_contracts(db).all()}
    known |= {address_key(e.address, e.city) for e in db.query(SiteMapExtraObject).all()}
    added = duplicates = 0
    for city, address in rows:
        key = address_key(address, city)
        if key in known:
            duplicates += 1
            continue
        known.add(key)
        db.add(SiteMapExtraObject(city=city, address=address, address_hash="", status="pending"))
        added += 1
    db.commit()
    return {"added": added, "duplicates": duplicates}
