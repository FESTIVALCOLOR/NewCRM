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

    def test_street_level_is_enough_after_quick_fuzzy_calls(self):
        fuzzy_calls = []
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: street(), fuzzy=lambda q, b: fuzzy_calls.append(q) or [])
        assert result.precision == "street"
        # Быстрых запросов не больше двух, сначала самый короткий вариант адреса
        assert fuzzy_calls == ["улица Ленина 5", "улица Ленина 5, Москва"]

    def test_quick_fuzzy_house_match_skips_slow_strict_geocoder(self):
        # Строгий геокодер разрешает только запрос в секунду — если нестрогий нашёл тот же дом, его не спрашиваем
        strict_calls = []
        feature = photon_feature("house", street_name="улица Ленина", housenumber="5")
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: strict_calls.append(q), fuzzy=lambda q, b: [feature])
        assert (result.lat, result.lon, result.precision) == (55.9, 37.5, "house")
        assert strict_calls == []

    def test_quick_fuzzy_answer_is_not_requested_twice(self):
        fuzzy_calls = []

        def fuzzy(query, box):
            fuzzy_calls.append(query)
            return [photon_feature("house", street_name="улица Ленина", housenumber="17")]

        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=fuzzy)
        assert result.precision == "street"
        assert len(fuzzy_calls) == len(set(fuzzy_calls))

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


@pytest.mark.backend
class TestNetworkFailures:
    class _Response:
        def __init__(self, status, data=None):
            self.status_code = status
            self._data = data

        def json(self):
            return self._data

        def raise_for_status(self):
            if self.status_code >= 400:
                error = geo.requests.HTTPError(f"HTTP {self.status_code}")
                error.response = self
                raise error

    @pytest.fixture(autouse=True)
    def _no_sleep(self, monkeypatch):
        monkeypatch.setattr(geo.time, "sleep", lambda seconds: None)

    def test_timeout_is_retried(self, monkeypatch):
        answers = [geo.requests.Timeout("read timeout"), self._Response(200, [house()])]

        def fake_get(*args, **kwargs):
            answer = answers.pop(0)
            if isinstance(answer, Exception):
                raise answer
            return answer

        monkeypatch.setattr(geo.requests, "get", fake_get)
        assert geo.nominatim_search("улица Ленина 5", None)["place_rank"] == 30

    def test_overloaded_service_is_retried_then_gives_up(self, monkeypatch):
        calls = []
        monkeypatch.setattr(geo.requests, "get", lambda *a, **k: calls.append(1) or self._Response(503))
        with pytest.raises(geo.requests.HTTPError):
            geo.photon_search("улица Ленина 5", geo.city_viewbox(*MOSCOW))
        assert len(calls) == geo.RETRY_ATTEMPTS

    def test_client_error_is_not_retried(self, monkeypatch):
        calls = []
        monkeypatch.setattr(geo.requests, "get", lambda *a, **k: calls.append(1) or self._Response(400))
        with pytest.raises(geo.requests.HTTPError):
            geo.nominatim_search("улица Ленина 5", None)
        assert len(calls) == 1


@pytest.mark.backend
class TestPointLabel:
    """Подпись на сайте строится из адреса картографической базы, а не из текста CRM."""

    def test_strict_geocoder_address_parts(self):
        found = {**house(), "address": {"house_number": "18 к3", "road": "Екатерининская улица", "town": "Мурино", "state": "Ленинградская область"}}
        result = geo.geocode_address("Мурино, ул. Екатерининская, 18к3кв447", "СПБ", MOSCOW, strict=lambda q, b: found, fuzzy=None)
        assert (result.place, result.street, result.house) == ("Мурино", "Екатерининская улица", "18 к3")
        assert geo.point_label(result.place, result.street, result.house, "house") == "Мурино, Екатерининская улица, 18 к3"
        assert geo.point_label(result.place, result.street, result.house, "street") == "Мурино, Екатерининская улица"

    def test_street_level_result_has_no_house_number(self):
        found = {**street(), "address": {"road": "улица Ленина", "city": "Москва", "house_number": "7"}}
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: found, fuzzy=None)
        assert result.house == ""
        assert geo.point_label(result.place, result.street, result.house, "house") == "Москва, улица Ленина"

    def test_fuzzy_geocoder_address_parts(self):
        feature = photon_feature("house", street_name="улица Ленина", housenumber="5 к1")
        feature["properties"]["city"] = "Москва"
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=lambda q, b: [feature])
        assert (result.place, result.street, result.house) == ("Москва", "улица Ленина", "5 к1")

    def test_other_house_on_street_gives_street_only(self):
        feature = photon_feature("house", street_name="улица Ленина", housenumber="17")
        result = geo.geocode_address("ул. Ленина 5", "МСК", MOSCOW, strict=lambda q, b: None, fuzzy=lambda q, b: [feature])
        assert (result.street, result.house) == ("улица Ленина", "")

    def test_modes_and_missing_street(self):
        assert geo.point_label("Москва", "улица Ленина", "5", "none") == ""
        assert geo.point_label("Москва", "", "5", "house") == ""
        assert geo.point_label("", "улица Ленина", "5", "house") == "улица Ленина, 5"
        assert geo.point_label("Москва", "улица Ленина", "5", "unknown") == ""


@pytest.mark.backend
class TestGluedApartment:
    """Квартира без пробела после номера дома не должна уходить геокодеру."""

    @pytest.mark.parametrize(
        "address",
        [
            "Мурино,ул. Екатерининская, 18к3кв447,",
            "Белоостровская улица, 10кв447",
            "ул.Бутлерова д.9к.2кв.447",
            "Вазаский пер. 3 кв447",
            "СПБ Энгельса 63.к2.кв447",
            "Дунайский пр. д.53,к2 кв447",
            "Кокколевская 14к1 кв447",
            "Ленсовета, 62к1, кв447,",
        ],
    )
    def test_apartment_is_removed(self, address):
        for query in geo.build_queries(address, "СПБ"):
            assert "447" not in query.text

    @pytest.mark.parametrize(
        "address, full",
        [
            ("Мурино, Петровский бульвар 2 к1, 415", "Мурино, Петровский бульвар 2 к1"),
            ("Коммунарка, ул Эдварда Грига, д 7, 267,", "Коммунарка, улица Эдварда Грига 7"),
            ("Двинская улица, 8 кв.80, 49м2,", "Двинская улица 8"),
            ("Ильменский проезд, 14к3 кв 1403 14 эт", "Ильменский проезд 14 к3"),
            ("Чирикова 5 (Никита), 3", "Чирикова 5"),
        ],
    )
    def test_second_number_after_house_is_dropped(self, address, full):
        # Квартира, этаж или площадь, записанные числом после дома, в поиск не уходят
        assert geo.clean_address(address)[0] == full

    def test_house_and_building_survive(self):
        assert geo.clean_address("Мурино,ул. Екатерининская, 18к3кв447,")[0] == "Мурино, улица Екатерининская 18 к3"
        assert geo.clean_address("Белоостровская улица, 10кв826")[0] == "Белоостровская улица 10"
