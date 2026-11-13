"""
Карта объектов сайта: разбор адресов и геокодирование.

Модуль без обращений к БД — только чистые функции и вызовы геокодеров,
чтобы логику можно было проверять тестами без сервера.

Адреса в CRM записаны свободным текстом, поэтому перед поиском они приводятся
к виду «город, улица дом»: убираются квартира, индекс, район, пометки в скобках,
раскрываются сокращения. Сначала спрашивается строгий геокодер (Nominatim),
затем терпимый к неточностям (Photon) — оба работают на данных OpenStreetMap,
которые разрешено хранить у себя.
"""

from dataclasses import dataclass
import hashlib
import hmac
import logging
import math
import re
import time
from typing import Callable, Optional

import requests

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
PHOTON_URL = "https://photon.komoot.io/api/"
# Сервисы требуют, чтобы клиент представлялся; название намеренно обезличенное
GEOCODER_HEADERS = {"User-Agent": "site-objects-map/1.0", "Accept-Language": "ru"}
# Nominatim по своим правилам принимает не больше одного запроса в секунду
GEOCODER_PAUSE = 1.1
# Photon жёсткого ограничения не задаёт и просит лишь не перегружать сервис — короткой паузы достаточно
PHOTON_PAUSE = 0.35
# Сбой сети на одном запросе не должен останавливать поиск: запрос повторяется после паузы
RETRY_ATTEMPTS = 3
RETRY_PAUSE = 3.0
# Сколько быстрых запросов к нестрогому геокодеру делается до строгого
QUICK_QUERIES = 2

# Коды городов из справочника CRM: название и центр города
CITIES = {
    "МСК": ("Москва", 55.751, 37.618),
    "СПБ": ("Санкт-Петербург", 59.939, 30.316),
    "ЕКБ": ("Екатеринбург", 56.838, 60.597),
    "ВН": ("Великий Новгород", 58.522, 31.275),
}

# Поиск ограничен областью вокруг города, чтобы одноимённая улица или деревня в другом
# месте не поставила точку за сотни километров. Сначала ищем рядом с городом (около 55 км);
# дальше (около 140 км) — только если в адресе назван населённый пункт вместе с улицей.
NEAR_BOX = (0.5, 0.9)  # градусы широты и долготы в каждую сторону
FAR_BOX = (1.3, 2.2)

# Меняется при изменении правил поиска: входит в отпечаток адреса, поэтому все точки пересчитываются
ALGORITHM_VERSION = "3"

# Ранг результата Nominatim: 30 — дом, 26–27 — улица, меньше — район или город (слишком грубо)
RANK_HOUSE = 28
RANK_STREET = 26

_PAREN_RE = re.compile(r"\([^)]*\)?|[«»\"]")
_POSTCODE_RE = re.compile(r"\b\d{6}\b")
_UNIT_RE = re.compile(
    r"[,;]?\s*\b(?:квартира|кв|офис|оф|помещение|пом|апартаменты|апарт|ап|подъезд|этаж|эт|секция|комната|комн)(?=\.|\s|№|\d|$)(?!-)\.?\s*№?\s*[\w/-]*",
    re.IGNORECASE,
)
# Квартира или офис, приписанные к номеру дома без пробела: «18к3кв447», «10кв826», «д.9к.2кв.660»
_GLUED_UNIT_RE = re.compile(r"(?<=[\d.,)])\s*(?=(?:квартира|кв|офис|оф|пом)\.?\s*№?\s*\d)", re.IGNORECASE)
_FLOOR_RE = re.compile(r"[,;]?\s*\b\d+\s*(?:-?(?:й|ый|ой|ий)\s+)?(?:этаж\w*|эт\b\.?)", re.IGNORECASE)
_LITER_RE = re.compile(r"[,;]?\s*\bлит(?:ера|ер)?\b\.?\s*[А-ЯЁа-яё]?(?![\wа-яё])", re.IGNORECASE)
# Обозначения дома, корпуса и строения бывают написаны слитно с номером: «д9», «корп.2», «ст1»
_HOUSE_WORD_RE = re.compile(r"\b(?:дом|д)\.?\s*(?=\d)", re.IGNORECASE)
_CORPUS_RE = re.compile(r"\b(?:корпус|корп|кор|к)\.?\s*(?=\d)", re.IGNORECASE)
_BUILDING_RE = re.compile(r"\b(?:строение|стр|ст|с)\.?\s*(?=\d)", re.IGNORECASE)
_GLUED_RE = re.compile(r"(\d)\s*([кс])\s*(\d)", re.IGNORECASE)

_ABBREVIATIONS = [
    (re.compile(r"\bпр-к?т\b\.?|\bпросп\b\.?", re.IGNORECASE), "проспект"),
    (re.compile(r"\bпр-д\b\.?", re.IGNORECASE), "проезд"),
    (re.compile(r"\bб-р\b\.?|\bбул\b\.?", re.IGNORECASE), "бульвар"),
    (re.compile(r"\bнаб\b\.?", re.IGNORECASE), "набережная"),
    (re.compile(r"\bш-се\b\.?|\bш\b\.", re.IGNORECASE), "шоссе"),
    (re.compile(r"\bпер\b\.?", re.IGNORECASE), "переулок"),
    (re.compile(r"\bпл\b\.?", re.IGNORECASE), "площадь"),
    (re.compile(r"\bул\b\.?", re.IGNORECASE), "улица"),
    (re.compile(r"\bпр\b\.", re.IGNORECASE), "проспект"),
]
_STREET_TYPES = {"улица", "проспект", "проезд", "бульвар", "набережная", "шоссе", "переулок", "площадь", "аллея", "линия", "тупик"}

# Части адреса, которые геокодеру только мешают: область, район, поселение, микрорайон, название ЖК
_NOISE_PART_RE = re.compile(r"\bобл\b|область|р-н\b|\bрайон\b|с/п|\bокруг\b|\bмкр\b|микрорайон|\bкв-л\b|\bквартал\b", re.IGNORECASE)
_NOISE_CODE_RE = re.compile(r"\b(?:МО|ЛО|ЖК|КП|СНТ)\b")
_TOWN_MARK_RE = re.compile(r"\b(?:город|гор|г|пгт|пос[её]лок|пос|деревня|дер)\b\.?\s*", re.IGNORECASE)
_EXPLICIT_TOWN_RE = re.compile(r"(?:^|[\s,])(?:г|пгт|пос|дер)\.?\s+[А-ЯЁ]|[А-ЯЁ][а-яё]+\s+дер\b")

_HOUSE_PART_RE = re.compile(r"^\d+[\w/-]*(?:\s+[кс]\d+\w*)*$", re.IGNORECASE)
# Служебное слово, оставшееся без номера после очистки («дом» от «дом 2 этажа»)
_ORPHAN_WORD_RE = re.compile(r"^(?:дом|д|корпус|корп|к|строение|стр|с|владение|вл)\.?$", re.IGNORECASE)
_CORPUS_PART_RE = re.compile(r"^[кс]\d+\w*$", re.IGNORECASE)
# Часть адреса уже заканчивается номером дома (с корпусом или строением)
_ENDS_WITH_HOUSE_RE = re.compile(r"\s\d[\w/-]*(?:\s+[кс]\d+\w*)*$", re.IGNORECASE)
_TRAILING_CORPUS_RE = re.compile(r"(\d[\w/-]*?)(?:\s+[кс]\d+\w*)+", re.IGNORECASE)
_FRACTION_RE = re.compile(r"\b(\d+[а-яё]?)/\d+\w*", re.IGNORECASE)
_TRAILING_HOUSE_RE = re.compile(r"\s+\d+[\w/-]*(?:\s+[кс]\d+\w*)*\s*$", re.IGNORECASE)


@dataclass
class GeoResult:
    lat: float
    lon: float
    precision: str  # 'house' или 'street'
    # Адрес найденного места по данным картографической базы — из него строится подпись на сайте
    place: str = ""
    street: str = ""
    house: str = ""  # только если найден именно этот дом


@dataclass(frozen=True)
class Query:
    text: str
    with_house: bool  # в запросе есть номер дома
    names_place: bool  # кроме улицы назван населённый пункт: такой запрос можно искать и вдали от города


_CITY_PREFIX_RE = re.compile(r"^(?:город|гор\.?|г\.?)\s+", re.IGNORECASE)
_CITY_ALIASES = {"спб": "СПБ", "питер": "СПБ", "петербург": "СПБ", "с-петербург": "СПБ", "мск": "МСК", "екб": "ЕКБ"}


def _known_city(value: Optional[str]) -> Optional[tuple[str, float, float]]:
    """Город из справочника по коду CRM, названию или привычному сокращению."""
    text = _CITY_PREFIX_RE.sub("", (value or "").strip()).strip(" .").lower().replace("ё", "е")
    if not text:
        return None
    for code, entry in CITIES.items():
        if text in (code.lower(), entry[0].lower()):
            return entry
    alias = _CITY_ALIASES.get(text)
    return CITIES[alias] if alias else None


def city_name(code: Optional[str]) -> str:
    """Название города по коду CRM; незнакомое значение считается самим названием."""
    known = _known_city(code)
    return known[0] if known else (code or "").strip()


def normalize_city(value: Optional[str]) -> str:
    """Город из файла в едином написании: «г. москва», «МСК» и «Москва» — один город."""
    known = _known_city(value)
    if known:
        return known[0]
    text = re.sub(r"\s+", " ", _CITY_PREFIX_RE.sub("", (value or "").strip())).strip(" .,")
    return text[:1].upper() + text[1:] if text else ""


def address_key(address: Optional[str], city: Optional[str]) -> str:
    """Ключ для поиска повторов: один и тот же дом, записанный по-разному, даёт один ключ."""
    full = clean_address(address or "")[0] or (address or "")
    return f"{city_name(city).lower()}|{re.sub(r'[^0-9a-zа-яё]+', ' ', full.lower()).strip()}"


def _normalize_parts(address: str) -> list[str]:
    """Адрес по частям: без квартиры, индекса, района и пометок, с раскрытыми сокращениями."""
    text = _PAREN_RE.sub(" ", address or "")
    text = _POSTCODE_RE.sub(" ", text)
    # «12 этаж» убирается раньше общего правила, иначе от него останется число
    text = _FLOOR_RE.sub("", text)
    text = _GLUED_UNIT_RE.sub(" ", text)
    text = _UNIT_RE.sub("", text)
    text = _LITER_RE.sub("", text)
    text = _HOUSE_WORD_RE.sub("", text)
    text = _CORPUS_RE.sub("к", text)
    text = _BUILDING_RE.sub("с", text)
    text = _GLUED_RE.sub(lambda m: f"{m.group(1)} {m.group(2).lower()}{m.group(3)}", text)
    for pattern, full in _ABBREVIATIONS:
        text = pattern.sub(full + " ", text)

    parts: list[str] = []
    for raw in re.split(r"[,;]", text):
        part = re.sub(r"\s+", " ", raw).strip(" .")
        if not part or _ORPHAN_WORD_RE.match(part) or _NOISE_PART_RE.search(part) or _NOISE_CODE_RE.search(part):
            continue
        part = _TOWN_MARK_RE.sub("", part).strip(" .")
        if not part:
            continue
        # Номер дома и корпус, записанные через запятую, приклеиваются к улице: «улица Ларина 5 к2»
        if parts and (_HOUSE_PART_RE.match(part) or _CORPUS_PART_RE.match(part)):
            # Второе число после номера дома — квартира («2 к1, 415») или площадь («49м2»), не дом: в поиск не идёт
            if _HOUSE_PART_RE.match(part) and _ENDS_WITH_HOUSE_RE.search(parts[-1]):
                continue
            parts[-1] = f"{parts[-1]} {part}"
        else:
            parts.append(part)
    return parts


def clean_address(address: str) -> tuple[str, str, str]:
    """Три варианта адреса: с корпусом, только с номером дома и только до улицы."""
    parts = _normalize_parts(address)
    full = ", ".join(parts)
    simple = ", ".join(_FRACTION_RE.sub(r"\1", _TRAILING_CORPUS_RE.sub(r"\1", p)) for p in parts)
    street = ", ".join(filter(None, (_TRAILING_HOUSE_RE.sub("", p).strip() for p in parts if not _HOUSE_PART_RE.match(p))))
    return full, simple, street


def build_queries(address: str, city_code: Optional[str]) -> list[Query]:
    """Варианты запроса от точного к грубому, без повторов."""
    full, simple, street = clean_address(address)
    name = city_name(city_code)
    source = address or ""
    # Если в адресе уже назван город («г. Химки»), название города договора может только помешать
    has_town = bool(_EXPLICIT_TOWN_RE.search(source)) or (bool(name) and name.lower() in source.lower())
    queries: dict[str, Query] = {}
    for base, has_number in ((full, True), (simple, True), (street, False)):
        if not base:
            continue
        with_house = has_number and base != street
        names_place = ", " in base
        if name and not has_town:
            text = f"{base}, {name}"
            queries.setdefault(text, Query(text, with_house, names_place))
        queries.setdefault(base, Query(base, with_house, names_place))
    return list(queries.values())


def _word_stems(text: str) -> list[str]:
    return [w[:5] for w in re.findall(r"[а-яё]{4,}", text.lower().replace("ё", "е"))]


def street_tokens(address: str, city_code: Optional[str] = None) -> list[str]:
    """Значимые слова названия улицы и посёлка — по ним проверяется ответ нестрогого геокодера.

    Слова из названий городов не учитываются: «Санкт-Петербург» в адресе не должен
    засчитать совпадением, например, Петергофское шоссе.
    """
    _, _, street = clean_address(address)
    city_stems = set(_word_stems(" ".join(name for name, _, _ in CITIES.values()) + " " + city_name(city_code)))
    type_stems = {t[:5] for t in _STREET_TYPES}
    return [stem for stem in _word_stems(street) if stem not in city_stems and stem not in type_stems]


def house_number(address: str) -> Optional[str]:
    """Номер дома без корпуса и дроби — для сверки с ответом геокодера."""
    _, simple, _ = clean_address(address)
    for part in reversed(simple.split(", ")):
        match = re.search(r"(?:^|\s)(\d+)[\w-]*\s*$", part)
        if match:
            return match.group(1)
    return None


def city_viewbox(lat: float, lon: float, size: tuple[float, float] = NEAR_BOX) -> tuple[float, float, float, float]:
    """Область поиска вокруг города: запад, юг, восток, север."""
    d_lat, d_lon = size
    return lon - d_lon, lat - d_lat, lon + d_lon, lat + d_lat


def _get_json(url: str, params: dict, pause: float):
    """Запрос к геокодеру с повтором при сбое сети или перегрузке сервиса. После запроса — пауза по правилам сервиса."""
    for attempt in range(1, RETRY_ATTEMPTS + 1):
        try:
            response = requests.get(url, params=params, headers=GEOCODER_HEADERS, timeout=15)
            # 429 и 5xx — сервис временно перегружен, адрес тут ни при чём
            if response.status_code == 429 or response.status_code >= 500:
                response.raise_for_status()
            response.raise_for_status()
            return response.json()
        except (requests.ConnectionError, requests.Timeout, requests.HTTPError) as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            retryable = status is None or status == 429 or status >= 500
            if not retryable or attempt == RETRY_ATTEMPTS:
                raise
            logger.info("Геокодер: повтор запроса после сбоя (%s), попытка %s", type(exc).__name__, attempt + 1)
            time.sleep(RETRY_PAUSE * attempt)
        finally:
            time.sleep(pause)
    return None


def nominatim_search(query: str, box: Optional[tuple[float, float, float, float]] = None) -> Optional[dict]:
    """Строгий геокодер: находит адрес, только если распознал каждое слово запроса."""
    params: dict = {"q": query, "format": "jsonv2", "limit": 1, "countrycodes": "ru", "addressdetails": 1}
    if box:
        west, south, east, north = box
        params["viewbox"] = f"{west},{north},{east},{south}"
        params["bounded"] = 1
    results = _get_json(NOMINATIM_URL, params, GEOCODER_PAUSE)
    return results[0] if results else None


def photon_search(query: str, box: tuple[float, float, float, float]) -> list[dict]:
    """Нестрогий геокодер: возвращает похожие адреса, даже если часть слов не совпала."""
    west, south, east, north = box
    params = {"q": query, "limit": 5, "bbox": f"{west},{south},{east},{north}", "lat": (south + north) / 2, "lon": (west + east) / 2}
    data = _get_json(PHOTON_URL, params, PHOTON_PAUSE)
    return (data or {}).get("features", [])


StrictSearch = Callable[[str, Optional[tuple[float, float, float, float]]], Optional[dict]]
FuzzySearch = Callable[[str, tuple[float, float, float, float]], list[dict]]


def resolve_city_center(city_code: Optional[str], search: StrictSearch = nominatim_search) -> Optional[tuple[float, float]]:
    """Центр города: из справочника или, для незнакомого названия, от геокодера."""
    code = (city_code or "").strip()
    known = _known_city(code)
    if known:
        return known[1], known[2]
    if len(code) < 4:
        # Короткое незнакомое значение — это неизвестный код, а не название города
        return None
    found = search(code, None)
    if found and int(found.get("place_rank", 0)) <= 16:
        return float(found["lat"]), float(found["lon"])
    return None


def _clip(value, limit: int) -> str:
    return str(value or "").strip()[:limit]


def _strict_result(found: dict, precision: str) -> GeoResult:
    address = found.get("address") or {}
    place = next((address[key] for key in _PLACE_KEYS if address.get(key)), "")
    street = next((address[key] for key in _STREET_KEYS if address.get(key)), "")
    house = address.get("house_number", "") if precision == "house" else ""
    return GeoResult(float(found["lat"]), float(found["lon"]), precision, _clip(place, 120), _clip(street, 200), _clip(house, 30))


def _pick_fuzzy(features: list[dict], tokens: list[str], house: Optional[str]) -> Optional[GeoResult]:
    """Из ответа нестрогого геокодера берётся только дом или улица с совпадающим названием."""
    for feature in features:
        props = feature.get("properties", {})
        kind = props.get("type")
        if kind not in ("house", "street"):
            continue
        haystack = f"{props.get('name', '')} {props.get('street', '')}".lower().replace("ё", "е")
        if not any(token in haystack for token in tokens):
            continue
        lon, lat = feature["geometry"]["coordinates"][:2]
        # Дом засчитывается, только если совпал номер; иначе это просто точка на нужной улице
        found_number = re.match(r"\d+", str(props.get("housenumber") or ""))
        same_house = kind == "house" and house is not None and found_number is not None and found_number.group(0) == house
        street = props.get("street") if kind == "house" else props.get("name")
        return GeoResult(
            float(lat),
            float(lon),
            "house" if same_house else "street",
            _clip(props.get("city") or props.get("town") or props.get("village") or props.get("locality"), 120),
            _clip(street, 200),
            _clip(props.get("housenumber"), 30) if same_house else "",
        )
    return None


def geocode_address(
    address: str,
    city_code: Optional[str],
    center: Optional[tuple[float, float]],
    strict: StrictSearch = nominatim_search,
    fuzzy: Optional[FuzzySearch] = photon_search,
) -> Optional[GeoResult]:
    """Координаты адреса с точностью до дома или улицы; None — если найти не удалось.

    Без центра города поиск не ограничить областью, а значит точке нельзя доверять —
    такие адреса считаются ненайденными.
    """
    if not center:
        return None
    queries = build_queries(address, city_code)
    if not queries:
        return None
    tokens = street_tokens(address, city_code)
    house = house_number(address)

    near = _search(queries, city_viewbox(*center, NEAR_BOX), strict, fuzzy, tokens, house)
    if near:
        return near
    # Одиночное название («Заречная 5», «Рязаново 28А») вдали от города почти наверняка совпадёт
    # с чужой улицей или деревней, поэтому дальний поиск — только для адресов с населённым пунктом
    far_queries = [q for q in queries if q.names_place]
    if not far_queries:
        return None
    return _search(far_queries, city_viewbox(*center, FAR_BOX), strict, fuzzy, tokens, house)


def _search(
    queries: list[Query],
    box: tuple[float, float, float, float],
    strict: StrictSearch,
    fuzzy: Optional[FuzzySearch],
    tokens: list[str],
    house: Optional[str],
) -> Optional[GeoResult]:
    """Поиск в одной области.

    Сначала один быстрый запрос к нестрогому геокодеру: если он нашёл именно этот дом на этой улице,
    ответ проверен и дальше искать незачем. Иначе — строгий геокодер (не чаще раза в секунду),
    и только потом остальные запросы к нестрогому.
    """
    answers: dict[str, list[dict]] = {}

    def ask_fuzzy(query: Query) -> Optional[GeoResult]:
        if query.text not in answers:
            answers[query.text] = fuzzy(query.text, box)
        return _pick_fuzzy(answers[query.text], tokens, house if query.with_house else None)

    can_fuzzy = fuzzy is not None and bool(tokens)
    if can_fuzzy and house:
        # Сначала вариант без корпуса: «13к1» нестрогий геокодер часто не узнаёт, а номер дома сверяется и так
        for query in sorted((q for q in queries if q.with_house), key=lambda q: len(q.text))[:QUICK_QUERIES]:
            quick = ask_fuzzy(query)
            if quick and quick.precision == "house":
                return quick

    street_level: Optional[GeoResult] = None
    for query in queries:
        found = strict(query.text, box)
        if not found:
            continue
        rank = int(found.get("place_rank", 0))
        if rank >= RANK_HOUSE:
            return _strict_result(found, "house")
        if rank >= RANK_STREET and street_level is None:
            street_level = _strict_result(found, "street")
    # Точки на карте всё равно сдвигаются на десятки метров, поэтому улицы достаточно.
    # Без названия улицы ответ нестрогого геокодера нечем проверить — его не спрашиваем.
    if street_level is not None or not can_fuzzy:
        return street_level
    for query in queries:
        picked = ask_fuzzy(query)
        if picked:
            return picked
    return None


# Подпись точки на публичной карте: «house» — улица и дом, «street» — только улица, «none» — без подписи
ADDRESS_MODES = ("house", "street", "none")
_PLACE_KEYS = ("city", "town", "village", "hamlet", "municipality")
_STREET_KEYS = ("road", "pedestrian", "residential", "square", "footway")


def point_label(place: Optional[str], street: Optional[str], house: Optional[str], mode: str = "house") -> str:
    """Подпись точки на сайте из адреса, который вернула картографическая база.

    Подпись не собирается из текста CRM: там бывают квартиры, записанные слитно («18к3кв447»),
    имена и пометки. В базе OpenStreetMap квартир и имён нет — только населённый пункт, улица и дом.
    """
    if mode not in ("house", "street") or not street:
        return ""
    street_part = f"{street}, {house}" if mode == "house" and house else street
    return f"{place}, {street_part}" if place else street_part


def address_hash(address: Optional[str], city: Optional[str]) -> str:
    """Отпечаток адреса: по нему видно, что адрес в договоре изменили и точку нужно искать заново."""
    normalized = f"v{ALGORITHM_VERSION}|{(city or '').strip().lower()}|{(address or '').strip().lower()}"
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:40]


def privacy_offset(contract_id: "int | str", lat: float, lon: float, secret: str) -> tuple[float, float]:
    """Сдвигает точку на 60–150 м в постоянную для договора (или объекта из файла) сторону.

    Объекты — жильё клиентов, поэтому точный дом на публичной карте не показывается.
    Сдвиг зависит от секретного ключа сервера: зная номер договора, его не вычислить обратно.
    """
    digest = hmac.new(secret.encode("utf-8"), f"site-map:{contract_id}".encode(), hashlib.sha256).digest()
    angle = int.from_bytes(digest[0:2], "big") / 65535 * 2 * math.pi
    distance = 60 + int.from_bytes(digest[2:4], "big") / 65535 * 90
    d_lat = distance * math.cos(angle) / 111_320
    d_lon = distance * math.sin(angle) / (111_320 * max(math.cos(math.radians(lat)), 0.1))
    return round(lat + d_lat, 5), round(lon + d_lon, 5)
