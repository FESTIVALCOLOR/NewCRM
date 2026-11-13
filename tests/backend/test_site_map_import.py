"""
Backend Tests — карта объектов сайта: загрузка объектов из файла Excel.
Файлы собираются в памяти, сервер и сеть не нужны.
"""

import io
from pathlib import Path
import sys

import pytest

openpyxl = pytest.importorskip("openpyxl")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server"))

from services import site_map_geo as geo  # noqa: E402
from services import site_map_import as imp  # noqa: E402


def xlsx(rows) -> bytes:
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    for row in rows:
        sheet.append(row)
    buffer = io.BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()


@pytest.mark.backend
class TestParseObjectsXlsx:
    def test_reads_city_and_address(self):
        parsed = imp.parse_objects_xlsx(xlsx([["Город", "Адрес"], ["Москва", "ул. Тверская, 12"], ["Казань", "ул. Баумана, 5"]]))
        assert parsed.rows == [("Москва", "ул. Тверская, 12"), ("Казань", "ул. Баумана, 5")]
        assert parsed.skipped == [] and parsed.duplicates == 0

    def test_columns_found_by_name_in_any_order_below_a_title(self):
        rows = [["Наши объекты"], [], ["№", "Адрес объекта", "Площадь", "ГОРОД"], [1, "Невский проспект, 10", 80, "спб"]]
        assert imp.parse_objects_xlsx(xlsx(rows)).rows == [("Санкт-Петербург", "Невский проспект, 10")]

    def test_city_spelling_is_unified(self):
        rows = [["Город", "Адрес"], ["г. москва", "ул. Ленина, 1"], ["МСК", "ул. Ленина, 2"], ["Питер", "ул. Ленина, 3"], ["нижний Новгород", "ул. Ленина, 4"]]
        cities = [city for city, _ in imp.parse_objects_xlsx(xlsx(rows)).rows]
        assert cities == ["Москва", "Москва", "Санкт-Петербург", "Нижний Новгород"]

    def test_rows_without_city_or_address_are_reported(self):
        rows = [["Город", "Адрес"], ["Москва", None], [None, "ул. Ленина, 5"], [None, None], ["Москва", "ул. Ленина, 5"]]
        parsed = imp.parse_objects_xlsx(xlsx(rows))
        assert parsed.rows == [("Москва", "ул. Ленина, 5")]
        assert parsed.skipped == ["строка 2: не указан адрес", "строка 3: не указан город"]

    def test_same_house_written_differently_is_one_object(self):
        rows = [["Город", "Адрес"], ["Москва", "ул. Ленина, д. 5, кв. 12"], ["МСК", "улица Ленина 5"], ["Москва", "ул. Ленина, 7"]]
        parsed = imp.parse_objects_xlsx(xlsx(rows))
        assert len(parsed.rows) == 2
        assert parsed.duplicates == 1

    def test_numeric_house_cell_is_not_a_float(self):
        parsed = imp.parse_objects_xlsx(xlsx([["Город", "Адрес"], ["Москва", 12.0]]))
        assert parsed.rows == [("Москва", "12")]

    def test_missing_columns_explained(self):
        with pytest.raises(imp.ImportFileError, match="Город"):
            imp.parse_objects_xlsx(xlsx([["Название", "Улица"], ["Москва", "ул. Ленина, 5"]]))

    def test_not_an_excel_file(self):
        with pytest.raises(imp.ImportFileError, match="xlsx"):
            imp.parse_objects_xlsx(b"city;address\n")

    def test_too_big_file_rejected_before_parsing(self):
        with pytest.raises(imp.ImportFileError, match="большой"):
            imp.parse_objects_xlsx(b"x" * (imp.MAX_FILE_SIZE + 1))

    def test_template_can_be_loaded_back(self):
        parsed = imp.parse_objects_xlsx(imp.build_template_xlsx())
        assert [city for city, _ in parsed.rows] == ["Москва", "Санкт-Петербург"]


@pytest.mark.backend
class TestCityFromFile:
    def test_full_name_uses_known_center_without_geocoder(self):
        calls = []
        assert geo.resolve_city_center("Москва", search=lambda q, b: calls.append(q)) == (55.751, 37.618)
        assert geo.resolve_city_center("г. Санкт-Петербург", search=lambda q, b: calls.append(q)) == (59.939, 30.316)
        assert calls == []

    def test_address_key_ignores_apartment_and_city_spelling(self):
        assert geo.address_key("ул. Ленина, д. 5, кв. 12", "МСК") == geo.address_key("улица Ленина 5", "Москва")
        assert geo.address_key("ул. Ленина 5", "МСК") != geo.address_key("ул. Ленина 5", "СПБ")
        assert geo.address_key("ул. Ленина 5", "МСК") != geo.address_key("ул. Ленина 6", "МСК")
