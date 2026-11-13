"""
Готовые дизайны сайта: данные товара (мебель, свет, декор) по ссылке на страницу магазина.

Панель управления присылает ссылку — сервис скачивает страницу и находит в ней название,
фото, артикул, описание, цвет, форму и размеры. Источники в порядке доверия:
разметка JSON-LD (schema.org/Product), микроразметка itemprop, Open Graph,
таблицы и списки характеристик на странице.

Разбор страницы (parse_product_html) — чистая функция без сети, её проверяют тесты.
Скачивание идёт только по публичным адресам: ссылку задаёт человек, а запрос делает сервер,
поэтому адреса внутренней сети, localhost и нестандартные схемы запрещены.
"""

from html.parser import HTMLParser
import ipaddress
import json
import os
import re
import socket
from typing import Optional
from urllib.parse import urljoin, urlparse
import uuid

import requests

MAX_PAGE_BYTES = 3 * 1024 * 1024
MAX_IMAGE_BYTES = 10 * 1024 * 1024
MAX_REDIRECTS = 4
TIMEOUT = 12
# Магазины часто отдают страницу только «браузеру»; название намеренно обезличенное
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
    "Accept-Language": "ru-RU,ru;q=0.9,en;q=0.5",
}
# Фото просим в форматах, которые открываются в любом браузере: иначе сервер картинок может отдать AVIF
IMAGE_ACCEPT = "image/jpeg,image/png,image/webp;q=0.9,image/gif;q=0.8"

FIELD_LIMITS = {"title": 120, "description": 500, "sku": 100, "color": 120, "shape": 120, "size": 200}

# Названия характеристик в таблицах магазинов → поле отметки
_SKU_KEY = re.compile(r"^(?:артикул|код товара|код|sku|арт\.?)(?:\s+(?:товара|производителя))?$", re.IGNORECASE)
_COLOR_KEY = re.compile(r"^(?:основной\s+)?цвет(?:\s+(?:товара|изделия|каркаса|корпуса|обивки|плафона|основания))?$", re.IGNORECASE)
_SHAPE_KEY = re.compile(r"^форма(?:\s+(?:товара|изделия|плафона|столешницы|спинки|сиденья))?$", re.IGNORECASE)
_SIZE_KEY = re.compile(r"^(?:размеры?|габариты|габаритные размеры)(?:\s*\(.*\))?(?:\s+(?:товара|изделия))?(?:,.*)?$", re.IGNORECASE)
# Отдельные измерения: если общих «размеров» нет, строка собирается из них
_DIMENSION_KEY = re.compile(r"^(ширина|высота|глубина|длина|диаметр)(?:\s+(?:товара|изделия|общая))?(?:\s*\(.*\))?(?:,\s*(мм|см|м))?$", re.IGNORECASE)
_DIMENSION_ORDER = ["ширина", "глубина", "длина", "высота", "диаметр"]

_SPACE = re.compile(r"\s+")
_TAGS = re.compile(r"<[^>]+>")


class ProductImportError(ValueError):
    """Страницу не удалось получить или разобрать; текст показывается человеку в панели."""


def _clean(value, limit: Optional[int] = None) -> str:
    if isinstance(value, (list, tuple)):
        value = ", ".join(str(item) for item in value if item)
    text = _SPACE.sub(" ", _TAGS.sub(" ", str(value or ""))).strip(" \t\n:;")
    if limit and len(text) > limit:
        text = text[: limit - 1].rstrip() + "…"
    return text


class _PageParser(HTMLParser):
    """Собирает со страницы всё, что может описывать товар, за один проход."""

    CELL_TAGS = {"td", "th", "dt", "dd"}
    SKIP_TAGS = {"script", "style", "noscript", "svg", "template"}
    # Характеристика бывает свёрстана без таблицы: <div><span>Размеры: </span><span>80 × 90 см</span></div>
    BLOCK_TAGS = {"div", "p"}
    MAX_BLOCK_TEXT = 200
    MAX_BLOCK_DEPTH = 60

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.json_ld: list[str] = []
        self.meta: dict[str, str] = {}
        self.itemprops: dict[str, str] = {}
        self.pairs: list[tuple[str, str]] = []
        self.title = ""
        self.h1 = ""
        self._ld_buffer: Optional[list[str]] = None
        self._skip_depth = 0
        self._capture: Optional[tuple[str, list[str]]] = None  # (вид, буфер текста)
        self._itemprop: Optional[tuple[str, list[str], str]] = None  # (имя, буфер, тег)
        self._row: Optional[list[str]] = None
        self._cell: Optional[list[str]] = None
        self._cell_tag = ""
        self._term = ""
        self._li: Optional[list[str]] = None
        self._blocks: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        attributes = {name: (value or "") for name, value in attrs}
        if tag == "script" and "ld+json" in attributes.get("type", "").lower():
            self._ld_buffer = []
        elif tag in self.SKIP_TAGS:
            self._skip_depth += 1
        elif tag == "meta":
            self._start_meta(attributes)
        else:
            self._start_itemprop(tag, attributes)
            self._start_structure(tag)

    def _start_meta(self, attributes: dict) -> None:
        key = (attributes.get("property") or attributes.get("name") or "").strip().lower()
        content = attributes.get("content", "").strip()
        prop = attributes.get("itemprop", "").strip().lower()
        if key and content:
            self.meta.setdefault(key, content)
        if prop and content:
            self.itemprops.setdefault(prop, content)

    def _start_itemprop(self, tag: str, attributes: dict) -> None:
        prop = attributes.get("itemprop", "").strip().lower()
        if not prop:
            return
        # Значение бывает в атрибуте (content, src картинки, href ссылки на фото) или в тексте элемента
        direct = attributes.get("content", "")
        if not direct and tag == "img":
            direct = attributes.get("src", "")
        if not direct and prop == "image" and tag in ("link", "a"):
            direct = attributes.get("href", "")
        if direct:
            self.itemprops.setdefault(prop, direct.strip())
        elif self._itemprop is None and tag not in ("img", "link", "br", "input"):
            self._itemprop = (prop, [], tag)

    def _start_structure(self, tag: str) -> None:
        if tag in ("title", "h1"):
            if not getattr(self, tag):
                self._capture = (tag, [])
        elif tag == "tr":
            # Закрывающие теги ячеек и строк в HTML необязательны — новая строка завершает предыдущую
            self._end_row()
            self._row = []
        elif tag in self.CELL_TAGS:
            self._end_cell()
            self._cell = []
            self._cell_tag = tag
        elif tag == "li":
            self._li = []
        elif tag in self.BLOCK_TAGS and len(self._blocks) < self.MAX_BLOCK_DEPTH:
            self._blocks.append([])

    def handle_endtag(self, tag):
        if tag == "script" and self._ld_buffer is not None:
            self.json_ld.append("".join(self._ld_buffer))
            self._ld_buffer = None
            return
        if tag in self.SKIP_TAGS:
            self._skip_depth = max(0, self._skip_depth - 1)
            return
        if self._itemprop and tag == self._itemprop[2]:
            name, buffer, _ = self._itemprop
            text = _clean("".join(buffer))
            if text:
                self.itemprops.setdefault(name, text)
            self._itemprop = None
        if self._capture and tag == self._capture[0]:
            kind, buffer = self._capture
            setattr(self, kind, _clean("".join(buffer)))
            self._capture = None
        elif tag in self.CELL_TAGS:
            self._end_cell()
        elif tag in ("tr", "table", "dl"):
            self._end_row()
        elif tag in self.BLOCK_TAGS and self._blocks:
            text = _clean(" ".join(self._blocks.pop()))
            if ":" in text and len(text) <= self.MAX_BLOCK_TEXT:
                key, _, value = text.partition(":")
                self.pairs.append((key.strip(), value.strip()))
        elif tag == "li" and self._li is not None:
            # «Цвет: белый» одной строкой или двумя соседними элементами внутри пункта списка
            text = _clean(" ".join(part for part in self._li if part.strip()))
            parts = [part.strip() for part in self._li if part.strip()]
            if ":" in text and len(text) <= 200:
                key, _, value = text.partition(":")
                self.pairs.append((key.strip(), value.strip()))
            elif len(parts) == 2 and len(text) <= 200:
                self.pairs.append((_clean(parts[0]), _clean(parts[1])))
            self._li = None

    def _end_cell(self):
        if self._cell is None:
            return
        text = _clean("".join(self._cell))
        tag = self._cell_tag
        self._cell = None
        if tag == "dt":
            self._term = text
        elif tag == "dd":
            if self._term and text:
                self.pairs.append((self._term, text))
            self._term = ""
        elif self._row is not None:
            self._row.append(text)

    def _end_row(self):
        self._end_cell()
        if self._row is None:
            return
        cells = [cell for cell in self._row if cell]
        if len(cells) == 2:
            self.pairs.append((cells[0], cells[1]))
        self._row = None

    def handle_data(self, data):
        if self._ld_buffer is not None:
            self._ld_buffer.append(data)
            return
        if self._skip_depth:
            return
        if self._capture:
            self._capture[1].append(data)
        if self._itemprop:
            self._itemprop[1].append(data)
        if self._cell is not None:
            self._cell.append(data)
        if self._li is not None:
            self._li.append(data)
        for block in self._blocks:
            # Длинный текст характеристикой быть не может — дальше его можно не копить
            if len(block) < 40:
                block.append(data)
            elif len(block) == 40:
                block.append("x" * self.MAX_BLOCK_TEXT)


def _json_ld_products(blocks: list[str]) -> list[dict]:
    """Все объекты типа Product из блоков JSON-LD, включая вложенные в @graph."""
    found: list[dict] = []

    def walk(node, depth=0):
        if depth > 6:
            return
        if isinstance(node, list):
            for item in node:
                walk(item, depth + 1)
        elif isinstance(node, dict):
            kinds = node.get("@type")
            kinds = kinds if isinstance(kinds, list) else [kinds]
            if any(str(kind).lower() in ("product", "productgroup") for kind in kinds):
                found.append(node)
            for key in ("@graph", "mainEntity", "hasVariant"):
                if key in node:
                    walk(node[key], depth + 1)

    for block in blocks:
        try:
            walk(json.loads(block.strip()))
        except (ValueError, RecursionError):
            continue
    return found


def _first_image(value) -> str:
    if isinstance(value, list):
        value = value[0] if value else ""
    if isinstance(value, dict):
        value = value.get("url") or value.get("contentUrl") or ""
    return str(value or "").strip()


def _dimension_text(value) -> str:
    """Значение размера из JSON-LD: число, строка или QuantitativeValue."""
    if isinstance(value, dict):
        amount = value.get("value")
        unit = value.get("unitText") or {"CMT": "см", "MMT": "мм", "MTR": "м"}.get(str(value.get("unitCode", "")).upper(), "")
        return _clean(f"{amount} {unit}") if amount not in (None, "") else ""
    return _clean(value)


def _apply_pair(result: dict, dimensions: dict, key: str, value: str) -> None:
    key = _clean(key).rstrip(".")
    value = _clean(value)
    if not key or not value or len(key) > 60:
        return
    if not result["sku"] and _SKU_KEY.match(key):
        result["sku"] = value
    elif not result["color"] and _COLOR_KEY.match(key):
        result["color"] = value
    elif not result["shape"] and _SHAPE_KEY.match(key):
        result["shape"] = value
    elif not result["size"] and _SIZE_KEY.match(key):
        result["size"] = value
    else:
        match = _DIMENSION_KEY.match(key)
        if match:
            name = match.group(1).lower()
            unit = match.group(2)
            # Единица измерения бывает в названии («Ширина, см») — тогда она дописывается к числу
            if unit and re.fullmatch(r"[\d.,\s]+", value):
                value = f"{value} {unit}"
            dimensions.setdefault(name, value)


def _first(*values) -> str:
    """Первое непустое значение, очищенное от разметки и лишних пробелов."""
    for value in values:
        text = _clean(value)
        if text:
            return text
    return ""


def _fill(result: dict, field: str, *values) -> None:
    """Заполняет поле, если оно ещё пустое: источники перебираются от надёжного к грубому."""
    if not result[field]:
        result[field] = _first(*values)


def _from_json_ld(parser: _PageParser, result: dict, dimensions: dict) -> None:
    for product in _json_ld_products(parser.json_ld):
        _fill(result, "title", product.get("name"))
        _fill(result, "description", product.get("description"))
        _fill(result, "image_url", _first_image(product.get("image")))
        _fill(result, "sku", product.get("sku"), product.get("mpn"), product.get("productID"))
        _fill(result, "color", product.get("color"))
        for name, key in (("ширина", "width"), ("высота", "height"), ("глубина", "depth")):
            if product.get(key):
                dimensions.setdefault(name, _dimension_text(product[key]))
        properties = product.get("additionalProperty") or []
        for prop in properties if isinstance(properties, list) else [properties]:
            if isinstance(prop, dict):
                _apply_pair(result, dimensions, str(prop.get("name", "")), _dimension_text(prop.get("value")))


def _from_markup(parser: _PageParser, result: dict, dimensions: dict) -> None:
    props = parser.itemprops
    meta = parser.meta
    _fill(result, "title", props.get("name"), meta.get("og:title"), parser.h1, parser.title)
    _fill(result, "description", props.get("description"), meta.get("og:description"), meta.get("description"))
    _fill(result, "image_url", props.get("image"), meta.get("og:image"), meta.get("twitter:image"))
    _fill(result, "sku", props.get("sku"), props.get("mpn"), meta.get("product:retailer_item_id"))
    _fill(result, "color", props.get("color"), meta.get("product:color"))
    for key, value in parser.pairs:
        _apply_pair(result, dimensions, key, value)


def _web_image(url: str, base_url: str) -> str:
    """Адрес фото в абсолютном виде; всё, кроме http(s), отбрасывается."""
    if not url:
        return ""
    absolute = urljoin(base_url, url) if base_url else url
    return absolute if absolute.lower().startswith(("http://", "https://")) else ""


def parse_product_html(html: str, base_url: str = "") -> dict:
    """Данные товара со страницы магазина. Ненайденные поля остаются пустыми строками."""
    parser = _PageParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        # Битая разметка: используем то, что успели прочитать
        pass

    result = {"title": "", "description": "", "image_url": "", "sku": "", "color": "", "shape": "", "size": ""}
    dimensions: dict[str, str] = {}
    _from_json_ld(parser, result, dimensions)
    _from_markup(parser, result, dimensions)

    if not result["size"] and dimensions:
        result["size"] = ", ".join(f"{name} {dimensions[name]}" for name in _DIMENSION_ORDER if name in dimensions)
    result["image_url"] = _web_image(result["image_url"], base_url)
    for field, limit in FIELD_LIMITS.items():
        result[field] = _clean(result[field], limit)
    return result


# ──────────────────────────────────────────────
# СКАЧИВАНИЕ
# ──────────────────────────────────────────────


def _check_public_url(url: str) -> None:
    """Запрещает всё, кроме http(s)-адресов публичного интернета."""
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.hostname:
        raise ProductImportError("Ссылка должна начинаться с http:// или https://")
    if parsed.username or parsed.password:
        raise ProductImportError("Ссылка с логином и паролем не поддерживается")
    try:
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        addresses = {info[4][0] for info in socket.getaddrinfo(parsed.hostname, port, proto=socket.IPPROTO_TCP)}
    except (socket.gaierror, ValueError) as exc:
        raise ProductImportError("Сайт по этой ссылке не найден — проверьте адрес") from exc
    for address in addresses:
        if not ipaddress.ip_address(address.split("%")[0]).is_global:
            raise ProductImportError("Ссылка ведёт не на публичный сайт")


def image_extension(body: bytes) -> str:
    """Расширение по содержимому файла: заголовку ответа доверять нельзя. Пусто — формат не подходит."""
    if body[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if body[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if body[:6] in (b"GIF87a", b"GIF89a"):
        return ".gif"
    if body[:4] == b"RIFF" and body[8:12] == b"WEBP":
        return ".webp"
    return ""


def _download(url: str, max_bytes: int, accept: Optional[str] = None) -> tuple[bytes, str, str, str]:
    """Скачивает адрес с проверкой каждого шага переадресации. Возвращает тело, тип, кодировку и итоговый адрес."""
    current = url
    for _ in range(MAX_REDIRECTS + 1):
        _check_public_url(current)
        try:
            headers = {**HEADERS, "Accept": accept} if accept else HEADERS
            response = requests.get(current, headers=headers, timeout=TIMEOUT, stream=True, allow_redirects=False)
        except requests.RequestException as exc:
            raise ProductImportError("Сайт не ответил — попробуйте позже или заполните поля вручную") from exc
        try:
            if response.is_redirect or response.is_permanent_redirect:
                location = response.headers.get("Location", "")
                if not location:
                    raise ProductImportError("Сайт вернул переадресацию без адреса")
                current = urljoin(current, location)
                continue
            if response.status_code in (404, 410):
                raise ProductImportError("Страница по этой ссылке не найдена — проверьте адрес")
            if response.status_code != 200:
                raise ProductImportError(f"Сайт не отдал страницу (код {response.status_code}) — возможно, он закрыт от автоматических запросов. Заполните поля вручную")
            body = b""
            for chunk in response.iter_content(64 * 1024):
                body += chunk
                if len(body) > max_bytes:
                    raise ProductImportError("Страница слишком большая")
            encoding = response.encoding if response.encoding and response.encoding.lower() != "iso-8859-1" else None
            return body, response.headers.get("Content-Type", "").split(";")[0].strip().lower(), encoding or "", current
        finally:
            response.close()
    raise ProductImportError("Слишком много переадресаций")


def _decode(body: bytes, declared: str) -> str:
    head = body[:4096].decode("ascii", "ignore")
    in_page = re.search(r"charset=[\"']?([\w-]+)", head, re.IGNORECASE)
    for encoding in filter(None, [declared, in_page.group(1) if in_page else "", "utf-8", "cp1251"]):
        try:
            return body.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            continue
    return body.decode("utf-8", "replace")


def save_remote_image(url: str, uploads_dir: str) -> str:
    """Копирует фото товара к нам: чужая ссылка может перестать работать. Пустая строка — если не вышло."""
    try:
        body, _, _, _ = _download(url, MAX_IMAGE_BYTES, accept=IMAGE_ACCEPT)
    except ProductImportError:
        return ""
    extension = image_extension(body)
    if not extension:
        return ""
    os.makedirs(uploads_dir, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{extension}"
    with open(os.path.join(uploads_dir, filename), "wb") as file:
        file.write(body)
    return f"/api/v1/site/media/{filename}"


def fetch_product(url: str, uploads_dir: str) -> dict:
    """Данные товара по ссылке; фото сохраняется в загрузки сайта."""
    url = (url or "").strip()
    body, content_type, declared, final_url = _download(url, MAX_PAGE_BYTES)
    if content_type and "html" not in content_type:
        raise ProductImportError("По ссылке не страница товара, а файл другого типа")
    # Относительные адреса картинок считаются от адреса, на который привела переадресация
    product = parse_product_html(_decode(body, declared), final_url)
    found = [field for field in ("title", "description", "image_url", "sku", "color", "shape", "size") if product[field]]
    if not found or found == ["title"]:
        raise ProductImportError("На странице не нашлось данных о товаре — возможно, сайт показывает их только в браузере. Заполните поля вручную")
    if product["image_url"]:
        product["image_url"] = save_remote_image(product["image_url"], uploads_dir)
    product["url"] = url
    return product
