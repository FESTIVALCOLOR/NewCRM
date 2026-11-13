"""
Backend Tests — готовые дизайны сайта: данные товара со страницы магазина.
Страницы заданы прямо в тестах, сеть не нужна; проверка адресов подменяет DNS.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server" / "services"))

import site_product_import as imp  # noqa: E402

JSON_LD_PAGE = """
<html><head><title>Купить диван — Магазин</title>
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "BreadcrumbList", "itemListElement": []},
  {"@type": "Product", "name": "Диван «Осло» трёхместный", "sku": "OSL-3-GR",
   "description": "Мягкий <b>диван</b> с   высокой спинкой.",
   "image": ["/img/oslo-1.jpg", "/img/oslo-2.jpg"], "color": "серый",
   "width": {"@type": "QuantitativeValue", "value": 220, "unitCode": "CMT"},
   "height": {"@type": "QuantitativeValue", "value": 85, "unitCode": "CMT"},
   "depth": "95 см",
   "additionalProperty": [{"@type": "PropertyValue", "name": "Форма", "value": "прямой"}]}
]}
</script></head><body><h1>Диван Осло</h1></body></html>
"""

TABLE_PAGE = """
<html><head>
<meta property="og:title" content="Торшер Arc — купить">
<meta property="og:image" content="https://cdn.shop.example/arc.webp">
<meta name="description" content="Напольный светильник с дугой.">
</head><body>
<h1>Торшер Arc</h1>
<script>var price = "<tr><td>Цвет</td><td>красный</td></tr>";</script>
<table>
  <tr><th>Артикул</th><td> ARC-001 </td></tr>
  <tr><td>Цвет плафона</td><td>белый</td></tr>
  <tr><td>Форма плафона</td><td>шар</td></tr>
  <tr><td>Высота, см</td><td>190</td></tr>
  <tr><td>Диаметр, см</td><td>35</td></tr>
  <tr><td>Страна</td><td>Италия</td></tr>
  <tr><td colspan="2">Доставка</td></tr>
</table></body></html>
"""

LIST_PAGE = """
<html><body><h1>Кресло Lounge</h1>
<dl><dt>Размеры (ШхГхВ):</dt><dd>80 × 85 × 100 см</dd><dt>Вес</dt><dd>12 кг</dd></dl>
<ul>
  <li>Цвет: <span>горчичный</span></li>
  <li><span>Код товара</span><span>100500</span></li>
  <li>Просто пункт списка без характеристики</li>
</ul>
<span itemprop="sku">не должен победить список? должен: микроразметка надёжнее</span>
</body></html>
"""


@pytest.mark.backend
class TestParseProductHtml:
    def test_json_ld_product(self):
        product = imp.parse_product_html(JSON_LD_PAGE, "https://shop.example/catalog/oslo")
        assert product == {
            "title": "Диван «Осло» трёхместный",
            "description": "Мягкий диван с высокой спинкой.",
            "image_url": "https://shop.example/img/oslo-1.jpg",
            "sku": "OSL-3-GR",
            "color": "серый",
            "shape": "прямой",
            "size": "ширина 220 см, глубина 95 см, высота 85 см",
        }

    def test_characteristics_table_and_open_graph(self):
        product = imp.parse_product_html(TABLE_PAGE, "https://shop.example/arc")
        assert product["title"] == "Торшер Arc — купить"
        assert product["description"] == "Напольный светильник с дугой."
        assert product["image_url"] == "https://cdn.shop.example/arc.webp"
        assert product["sku"] == "ARC-001"
        # Строка таблицы внутри <script> — не характеристика товара
        assert product["color"] == "белый"
        assert product["shape"] == "шар"
        assert product["size"] == "высота 190 см, диаметр 35 см"

    def test_definition_list_and_bullet_list(self):
        product = imp.parse_product_html(LIST_PAGE)
        assert product["title"] == "Кресло Lounge"
        assert product["size"] == "80 × 85 × 100 см"
        assert product["color"] == "горчичный"
        # Микроразметка надёжнее списка характеристик
        assert product["sku"].startswith("не должен победить")

    def test_page_without_product_gives_empty_fields(self):
        product = imp.parse_product_html("<html><head><title>Вход</title></head><body><p>Подтвердите, что вы не робот</p></body></html>")
        assert product["title"] == "Вход"
        assert all(product[field] == "" for field in ("description", "image_url", "sku", "color", "shape", "size"))

    def test_broken_markup_and_json_do_not_crash(self):
        html = '<html><script type="application/ld+json">{"@type": "Product", </script><table><tr><td>Цвет<td>синий</table><h1>Стол'
        assert imp.parse_product_html(html)["color"] == "синий"

    def test_long_values_are_trimmed_to_field_limits(self):
        html = f"<h1>{'А' * 300}</h1><table><tr><td>Цвет</td><td>{'б' * 300}</td></tr></table>"
        product = imp.parse_product_html(html)
        assert len(product["title"]) == imp.FIELD_LIMITS["title"]
        assert len(product["color"]) == imp.FIELD_LIMITS["color"]

    @pytest.mark.parametrize("image", ["javascript:alert(1)", "data:image/png;base64,AAAA"])
    def test_only_web_image_links_survive(self, image):
        html = f'<meta property="og:image" content="{image}"><h1>Стол</h1>'
        assert imp.parse_product_html(html, "https://shop.example/")["image_url"] == ""

    @pytest.mark.parametrize(
        "key, field",
        [("Артикул", "sku"), ("Код товара", "sku"), ("Основной цвет", "color"), ("Цвет обивки", "color"), ("Форма столешницы", "shape"), ("Габариты", "size"), ("Размер", "size")],
    )
    def test_characteristic_names(self, key, field):
        product = imp.parse_product_html(f"<table><tr><td>{key}</td><td>значение</td></tr></table>")
        assert product[field] == "значение"

    @pytest.mark.parametrize("key", ["Цветовая температура", "Формат упаковки", "Размер скидки на второй товар в корзине при покупке комплекта мебели"])
    def test_similar_names_are_not_mistaken_for_characteristics(self, key):
        product = imp.parse_product_html(f"<table><tr><td>{key}</td><td>значение</td></tr></table>")
        assert all(product[field] == "" for field in ("sku", "color", "shape", "size"))


@pytest.mark.backend
class TestOnlyPublicAddresses:
    """Запрос делает сервер, поэтому адреса внутренней сети должны отсекаться до запроса."""

    @staticmethod
    def _resolve_to(monkeypatch, address):
        monkeypatch.setattr(imp.socket, "getaddrinfo", lambda *args, **kwargs: [(2, 1, 6, "", (address, 443))])

    @pytest.mark.parametrize("url", ["ftp://shop.example/a", "file:///etc/passwd", "javascript:alert(1)", "//shop.example/a", "https://", ""])
    def test_only_http_links(self, url):
        with pytest.raises(imp.ProductImportError):
            imp._check_public_url(url)

    @pytest.mark.parametrize("address", ["127.0.0.1", "10.0.0.5", "172.18.0.2", "192.168.1.1", "169.254.169.254", "::1", "0.0.0.0"])
    def test_internal_addresses_are_rejected(self, monkeypatch, address):
        self._resolve_to(monkeypatch, address)
        with pytest.raises(imp.ProductImportError, match="публичный"):
            imp._check_public_url("https://shop.example/product")

    def test_public_address_is_allowed(self, monkeypatch):
        self._resolve_to(monkeypatch, "93.184.215.14")
        imp._check_public_url("https://shop.example/product")

    def test_credentials_in_link_are_rejected(self, monkeypatch):
        self._resolve_to(monkeypatch, "93.184.215.14")
        with pytest.raises(imp.ProductImportError):
            imp._check_public_url("https://user:pass@shop.example/product")

    def test_redirect_to_internal_address_is_not_followed(self, monkeypatch):
        calls = []

        class Redirect:
            is_redirect = True
            is_permanent_redirect = False
            status_code = 302
            headers = {"Location": "http://internal.example/admin"}

            def close(self):
                pass

        def fake_get(url, **kwargs):
            calls.append(url)
            return Redirect()

        monkeypatch.setattr(imp.requests, "get", fake_get)
        monkeypatch.setattr(imp.socket, "getaddrinfo", lambda host, *a, **k: [(2, 1, 6, "", ("10.0.0.5" if host == "internal.example" else "93.184.215.14", 80))])
        with pytest.raises(imp.ProductImportError, match="публичный"):
            imp._download("https://shop.example/product", 1000)
        assert calls == ["https://shop.example/product"]


@pytest.mark.backend
class TestProductImage:
    @pytest.mark.parametrize(
        "body, extension",
        [
            (b"\xff\xd8\xff\xe0" + b"0" * 20, ".jpg"),
            (b"\x89PNG\r\n\x1a\n" + b"0" * 20, ".png"),
            (b"GIF89a" + b"0" * 20, ".gif"),
            (b"RIFF\x00\x00\x00\x00WEBPVP8 ", ".webp"),
            # AVIF открывается не везде, HTML и SVG под видом картинки недопустимы
            (b"\x00\x00\x00\x1cftypavif", ""),
            (b"<html><body>captcha</body></html>", ""),
            (b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", ""),
            (b"", ""),
        ],
    )
    def test_format_is_taken_from_file_content(self, body, extension):
        assert imp.image_extension(body) == extension

    def test_image_is_saved_only_in_supported_format(self, monkeypatch, tmp_path):
        seen = {}

        def fake_download(url, max_bytes, accept=None):
            seen["accept"] = accept
            return fake_download.body, "image/jpeg", "", url

        monkeypatch.setattr(imp, "_download", fake_download)
        fake_download.body = b"\x89PNG\r\n\x1a\n" + b"0" * 20
        saved = imp.save_remote_image("https://cdn.shop.example/a.jpg", str(tmp_path))
        assert saved.startswith("/api/v1/site/media/") and saved.endswith(".png")
        assert (tmp_path / saved.rsplit("/", 1)[1]).read_bytes() == fake_download.body
        # Формат AVIF не запрашивается: его открывают не все браузеры
        assert "avif" not in seen["accept"]

        fake_download.body = b"<html>not an image</html>"
        assert imp.save_remote_image("https://cdn.shop.example/a.jpg", str(tmp_path)) == ""
        assert len(list(tmp_path.iterdir())) == 1

    def test_avif_is_kept_when_it_cannot_be_converted(self, monkeypatch, tmp_path):
        # Заголовок AVIF без настоящих данных: пересохранить нельзя, но и отбрасывать фото не нужно
        body = b"\x00\x00\x00\x1cftypavif" + b"0" * 20
        assert imp.browser_image(body) == (body, ".avif")
        monkeypatch.setattr(imp, "_download", lambda url, max_bytes, accept=None: (body, "image/avif", "", url))
        assert imp.save_remote_image("https://cdn.shop.example/a.jpg", str(tmp_path)).endswith(".avif")

    def test_avif_is_converted_to_jpeg_when_possible(self):
        image_module = pytest.importorskip("PIL.Image")
        features = pytest.importorskip("PIL.features")
        if not features.check("avif"):
            pytest.skip("Pillow собран без поддержки AVIF")
        import io

        source = io.BytesIO()
        image_module.new("RGBA", (8, 8), (255, 0, 0, 0)).save(source, "AVIF")
        body, extension = imp.browser_image(source.getvalue())
        assert extension == ".jpg" and imp.image_extension(body) == ".jpg"
        # Прозрачный фон становится белым, а не чёрным
        assert image_module.open(io.BytesIO(body)).getpixel((4, 4))[0] > 240

    @pytest.mark.parametrize("body", [b"<html>ftyp</html>", b"\x00\x00\x00\x18ftypmp42" + b"0" * 20, b""])
    def test_other_files_are_not_images(self, body):
        assert imp.browser_image(body) == (b"", "")
