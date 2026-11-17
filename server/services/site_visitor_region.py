"""
Регион посетителя сайта для калькулятора готового дизайна: Москва, Санкт-Петербург или ближайший
региональный центр — чтобы цена сразу показывалась для его города.

Город определяется по IP-адресу через локальную базу DB-IP (бесплатная версия «IP to City Lite»,
лицензия CC BY 4.0, на сайте нужна ссылка на DB-IP). Адрес никуда не отправляется и не сохраняется:
поиск идёт в файле на нашем сервере, в ответе — только регион цены и название города.
"""

import json
import logging
import math
import os
from pathlib import Path
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)

GEOIP_DB_PATH = os.environ.get("SITE_GEOIP_DB", "/app/geoip/dbip-city-lite.mmdb")
CENTERS_PATH = Path(__file__).with_name("region_centers.json")

MOSCOW = (55.751, 37.618)
SAINT_PETERSBURG = (59.939, 30.316)
# Москва и Петербург с ближайшими пригородами — цена этих городов
CAPITAL_RADIUS_KM = 120
# Дальше этого от любого регионального центра город не подставляем: определение по IP неточное
REGION_RADIUS_KM = 450

# Регионы по базе DB-IP (английские названия), которые относятся к цене Москвы и Петербурга
_MOSCOW_REGIONS = {"moscow", "moscow oblast"}
_SPB_REGIONS = {"st. petersburg", "st.-petersburg", "saint petersburg", "st petersburg", "leningrad oblast", "leningradskaya oblast'"}

_reader = None
_reader_lock = threading.Lock()
_centers: Optional[dict] = None


def distance_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1, lat2, lon2 = map(math.radians, (*a, *b))
    h = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(h))


def region_centers() -> dict:
    """Региональные центры из списка калькулятора и их координаты."""
    global _centers
    if _centers is None:
        _centers = {name: tuple(coords) for name, coords in json.loads(CENTERS_PATH.read_text(encoding="utf-8")).items()}
    return _centers


def _open_reader():
    global _reader
    with _reader_lock:
        if _reader is None and os.path.isfile(GEOIP_DB_PATH):
            import maxminddb

            _reader = maxminddb.open_database(GEOIP_DB_PATH)
    return _reader


def lookup_ip(ip: str) -> Optional[dict]:
    """Запись базы DB-IP для адреса: страна, регион, координаты. None — адреса нет в базе или база не установлена."""
    reader = _open_reader()
    if reader is None or not ip:
        return None
    try:
        return reader.get(ip)
    except ValueError:
        return None


def price_region(record: Optional[dict], candidates: list[str]) -> dict:
    """Регион цены по записи базы: {"region": "msk"|"spb"|"region", "city": "…"} или {} — не определили."""
    if not record or (record.get("country") or {}).get("iso_code") != "RU":
        return {}
    location = record.get("location") or {}
    if location.get("latitude") is None or location.get("longitude") is None:
        return {}
    point = (float(location["latitude"]), float(location["longitude"]))
    regions = {str((sub.get("names") or {}).get("en", "")).lower() for sub in record.get("subdivisions") or []}
    if regions & _MOSCOW_REGIONS or distance_km(point, MOSCOW) <= CAPITAL_RADIUS_KM:
        return {"region": "msk"}
    if regions & _SPB_REGIONS or distance_km(point, SAINT_PETERSBURG) <= CAPITAL_RADIUS_KM:
        return {"region": "spb"}
    centers = region_centers()
    known = [(name, centers[name]) for name in candidates if name in centers]
    if not known:
        return {"region": "region"}
    name, coords = min(known, key=lambda item: distance_km(point, item[1]))
    return {"region": "region", "city": name if distance_km(point, coords) <= REGION_RADIUS_KM else ""}


def visitor_region(ip: str, custom_cities: Optional[str], lookup: Callable[[str], Optional[dict]] = lookup_ip) -> dict:
    """Регион цены для посетителя. Список городов — свой из настроек сайта или стандартный."""
    candidates = [line.strip() for line in (custom_cities or "").splitlines() if line.strip()] or list(region_centers())
    try:
        return price_region(lookup(ip), candidates)
    except Exception as exc:
        # Определение города — удобство, а не обязательная часть страницы: при сбое просто не подставляем
        logger.warning("Регион посетителя не определён: %s", type(exc).__name__)
        return {}
