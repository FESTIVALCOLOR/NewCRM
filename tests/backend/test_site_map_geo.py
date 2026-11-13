"""
Backend Tests — карта объектов сайта: разбор адресов, выбор результата геокодера,
сдвиг координат для защиты адресов клиентов. Геокодеры подменяются, сеть не нужна.
"""

import math
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server" / "services"))

import site_map_geo as geo  # noqa: E402

MOSCOW = (55.751, 37.618)


def house(lat=55.76, lon=37.62):
    return {"lat": str(lat), "lon": str(lon), "place_rank": 30}


def street(lat=55.76, lon=37.62):
    return {"lat": str(lat), "lon": str(lon), "place_rank": 26}


def photon_feature(kind, name="", street_name="", housenumber=None, lat=55.9, lon=37.5):
    props = {"type": kind, "name": name, "street": street_name}
    if housenumber:
        props["housenumber"] = housenumber
    return {"properties": props, "geometry": {"coordinates": [lon, lat]}}


@pytest.mark.backend
class TestCleanAddress:
    @pytest.mark.parametrize(
        "address, full, simple, street_only",
        [
            ("ул. Дыбенко д9 корп.2 кв 15", "улица Дыбенко 9 к2", "улица Дыбенко 9", "улица Дыбенко"),
            ("Тверская улица, 99к9, кв. 999", "Тверская улица 99 к9", "Тверская улица 99", "Тверская улица"),
            ("Заречная улица, 1, ст1", "Заречная улица 1 с1", "Заречная улица 1", "Заречная улица"),
            ("Московский проспект 73, к5, с1", "Московский проспект 73 к5 с1", "Московский проспект 73", "Московский проспект"),
            ("Громова, 28 к1 (ванная)", "Громова 28 к1", "Громова 28", "Громова"),
            ("б-р Братьев Весниных, д 2", "бульвар Братьев Весниных 2", "бульвар Братьев Весниных 2", "бульвар Братьев Весниных"),
            ("Санкт-Петербург, пр. Медиков 10/1", "Санкт-Петербург, проспект Медиков 10/1", "Санкт-Петербург, проспект Медиков 10", "Санкт-Петербург, проспект Медиков"),
            ("Каменноостровский, 26, литер З", "Каменноостровский 26", "Каменноостровский 26", "Каменноостровский"),
            (
                "188650, Ленинградская обл, Всеволожский р-н, г Сертолово, мкр Сертолово-1, ул Ларина, 15",
                "Сертолово, улица Ларина 15",
                "Сертолово, улица Ларина 15",
                "Сертолово, улица Ларина",
            ),
        ],
    )
    def test_variants(self, address, full, simple, street_only):
        assert geo.clean_address(address) == (full, simple, street_only)

    @pytest.mark.parametrize("address", ["ул. Ленина 5, кв. 12", "ул. Ленина 5, квартира 12", "ул. Ленина 5 оф 12", "ул. Ленина 5, 12 этаж"])
    def test_apartment_never_reaches_geocoder(self, address):
        for query in geo.build_queries(address, "МСК"):
            assert "12" not in query.text

    def test_only_residential_complex_name_gives_no_queries(self):
        assert geo.build_queries("ЖК «Солнечный» (ванная)", "МСК") == []

    def test_city_added_first_when_address_has_no_town(self):
        queries = [q.text for q in geo.build_queries("ул. Ленина 5", "СПБ")]
        assert queries[0] == "улица Ленина 5, Санкт-Петербург"
        assert "улица Ленина 5" in queries

    def test_city_not_added_when_town_is_explicit(self):
        queries = geo.build_queries("Московская область, г. Красногорск, ул. Ленина, 5", "МСК")
        assert [q.text for q in queries] == ["Красногорск, улица Ленина 5", "Красногорск, улица Ленина"]
        assert [q.with_house for q in queries] == [True, False]
        assert all(q.names_place for q in queries)

    def test_bare_street_does_not_name_a_place(self):
        assert not any(q.names_place for q in geo.build_queries("ул. Ленина 5", "СПБ"))

    def test_house_number_and_street_tokens(self):
        assert geo.house_number("пр-кт Пацаева, 7 к1, кв. 120") == "7"
        assert geo.street_tokens("Долгопрудный, пр-кт Пацаева, 7 к1", "МСК") == ["долго", "пацае"]

    def test_city_words_are_not_street_tokens(self):
        assert geo.street_tokens("Санкт-Петербург, пр. Патриотов, 34", "СПБ") == ["патри"]


@pytest.mark.backend
class TestGeocodeAddress:
    def test_house_found_by_strict_geocoder(self):
        calls = []

        def strict(query, box):
            calls.append(query)
            return house()

        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=strict, fuzzy=None)
        assert (result.lat, result.lon, result.precision) == (55.76, 37.62, "house")
        assert calls == ["улица Ленина 5, Москва"]

    def test_search_is_bounded_to_city_region(self):
        boxes = []

        def strict(query, box):
            boxes.append(box)
            return house()

        geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=strict, fuzzy=None)
        west, south, east, north = boxes[0]
        assert west < MOSCOW[1] < east and south < MOSCOW[0] < north

    def test_bare_name_is_never_searched_far_from_city(self):
        # Регрессия: «деревня Рязаново, 28А» нашлась в одноимённой деревне за 155 км от Москвы
        boxes = []

        def strict(query, box):
            boxes.append(box)
            return None

        def fuzzy(query, box):
            boxes.append(box)
            return []

        result = geo.geocode_address("Рязаново дер., д.28А, Щербинка р-н, дом 2 этажа", "МСК", MOSCOW, strict=strict, fuzzy=fuzzy)
        assert result is None
        assert set(boxes) == {geo.city_viewbox(*MOSCOW, geo.NEAR_BOX)}

    def test_address_with_town_falls_back_to_wide_region(self):
        far = geo.city_viewbox(*MOSCOW, geo.FAR_BOX)
        result = geo.geocode_address("г. Клин, ул. Ленина, 5", "МСК", MOSCOW, strict=lambda q, box: house() if box == far else None, fuzzy=None)
        assert result is not None and result.precision == "house"

    def test_too_coarse_result_is_rejected(self):
        # Геокодер узнал только город — такую точку показывать нельзя
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: {"lat": "55.7", "lon": "37.6", "place_rank": 16}, fuzzy=None)
        assert result is None

    def test_street_level_is_enough_without_fuzzy_call(self):
        fuzzy_calls = []
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: street(), fuzzy=lambda q, b: fuzzy_calls.append(q) or [])
        assert result.precision == "street"
        assert fuzzy_calls == []

    def test_fuzzy_used_when_strict_finds_nothing(self):
        feature = photon_feature("house", street_name="улица Ленина", housenumber="5 к1")
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=lambda q, b: [feature])
        assert (result.lat, result.lon, result.precision) == (55.9, 37.5, "house")

    def test_fuzzy_other_house_on_same_street_is_street_precision(self):
        feature = photon_feature("house", street_name="улица Ленина", housenumber="17")
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=lambda q, b: [feature])
        assert result.precision == "street"

    def test_fuzzy_result_on_another_street_is_rejected(self):
        # Нестрогий геокодер любит подставлять похожее — чужая улица не должна стать точкой
        feature = photon_feature("house", street_name="улица Гагарина", housenumber="5")
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=lambda q, b: [feature])
        assert result is None

    def test_fuzzy_city_or_district_is_rejected(self):
        feature = photon_feature("city", name="Ленинский")
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=lambda q, b: [feature])
        assert result is None

    def test_unknown_city_means_not_found_without_requests(self):
        calls = []
        result = geo.geocode_address("ул. Ленина 5", "XX", None, strict=lambda q, b: calls.append(q), fuzzy=None)
        assert result is None
        assert calls == []


@pytest.mark.backend
class TestCityCenter:
    def test_known_code(self):
        assert geo.resolve_city_center("спб") == (59.939, 30.316)
        assert geo.city_name("ЕКБ") == "Екатеринбург"

    def test_unknown_short_code_is_not_geocoded(self):
        calls = []
        assert geo.resolve_city_center("КЗН", search=lambda q, b: calls.append(q)) is None
        assert calls == []

    def test_full_city_name_is_resolved_by_geocoder(self):
        found = {"lat": "55.79", "lon": "49.12", "place_rank": 16}
        assert geo.resolve_city_center("Казань", search=lambda q, b: found) == (55.79, 49.12)
        assert geo.city_name("Казань") == "Казань"


@pytest.mark.backend
class TestPrivacy:
    @staticmethod
    def _distance_m(a, b):
        d_lat = (a[0] - b[0]) * 111_320
        d_lon = (a[1] - b[1]) * 111_320 * math.cos(math.radians(a[0]))
        return math.hypot(d_lat, d_lon)

    @pytest.mark.parametrize("contract_id", range(1, 60))
    def test_point_is_shifted_60_to_150_meters(self, contract_id):
        original = (59.93863, 30.31413)
        shifted = geo.privacy_offset(contract_id, *original, secret="s3cret")
        assert 58 <= self._distance_m(original, shifted) <= 152

    def test_shift_is_stable_and_depends_on_secret(self):
        first = geo.privacy_offset(7, 55.75, 37.61, secret="one")
        assert first == geo.privacy_offset(7, 55.75, 37.61, secret="one")
        assert first != geo.privacy_offset(7, 55.75, 37.61, secret="two")
        assert first != geo.privacy_offset(8, 55.75, 37.61, secret="one")

    def test_address_hash_tracks_address_and_city(self):
        base = geo.address_hash("ул. Ленина 5", "МСК")
        assert base == geo.address_hash("  УЛ. ЛЕНИНА 5 ", "мск")
        assert base != geo.address_hash("ул. Ленина 6", "МСК")
        assert base != geo.address_hash("ул. Ленина 5", "СПБ")

    def test_address_hash_changes_with_algorithm_version(self, monkeypatch):
        # Смена правил поиска должна заставить пересчитать все точки
        base = geo.address_hash("ул. Ленина 5", "МСК")
        monkeypatch.setattr(geo, "ALGORITHM_VERSION", "next")
        assert base != geo.address_hash("ул. Ленина 5", "МСК")
