"""
Backend Tests — сайт: регион цены готового дизайна по местоположению посетителя.
База IP подменяется готовыми записями, сеть и файл базы не нужны.
"""

from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "server" / "services"))

import site_visitor_region as vr  # noqa: E402


def record(lat, lon, country="RU", region=""):
    data = {"country": {"iso_code": country}, "location": {"latitude": lat, "longitude": lon}}
    if region:
        data["subdivisions"] = [{"names": {"en": region}}]
    return data


ALL = list(vr.region_centers())


@pytest.mark.backend
class TestPriceRegion:
    @pytest.mark.parametrize(
        "rec, expected",
        [
            (record(55.75, 37.62), {"region": "msk"}),
            (record(55.43, 37.54), {"region": "msk"}),  # Подольск
            (record(56.33, 36.73, region="Moscow Oblast"), {"region": "msk"}),  # Клин — далеко от центра, но в Московской области
            (record(59.94, 30.31), {"region": "spb"}),
            (record(60.0, 30.65, region="Leningrad Oblast"), {"region": "spb"}),
            (record(55.79, 49.12), {"region": "region", "city": "Казань"}),
            (record(58.52, 31.27), {"region": "region", "city": "Великий Новгород"}),
            (record(55.69, 37.89), {"region": "msk"}),  # Люберцы
            (record(56.13, 47.25), {"region": "region", "city": "Чебоксары"}),
        ],
    )
    def test_cities(self, rec, expected):
        assert vr.price_region(rec, ALL) == expected

    def test_far_from_any_center_gives_region_without_city(self):
        # Таймыр: ближайший региональный центр дальше 450 км — город не подставляем
        assert vr.price_region(record(72.0, 100.0), ALL) == {"region": "region", "city": ""}

    @pytest.mark.parametrize("rec", [None, {}, record(45.46, 9.19, country="IT"), {"country": {"iso_code": "RU"}}])
    def test_unknown_or_foreign_visitor_is_not_guessed(self, rec):
        assert vr.price_region(rec, ALL) == {}

    def test_only_cities_from_site_list_are_suggested(self):
        assert vr.price_region(record(55.79, 49.12), ["Уфа", "Самара"]) == {"region": "region", "city": "Самара"}
        assert vr.price_region(record(55.79, 49.12), ["Неизвестноград"]) == {"region": "region"}


@pytest.mark.backend
class TestVisitorRegion:
    def test_custom_city_list_from_settings(self):
        result = vr.visitor_region("1.2.3.4", "Уфа\n\nСамара\n", lookup=lambda ip: record(55.79, 49.12))
        assert result == {"region": "region", "city": "Самара"}

    def test_lookup_failure_is_silent(self):
        def broken(ip):
            raise OSError("база повреждена")

        assert vr.visitor_region("1.2.3.4", "", lookup=broken) == {}

    def test_missing_database_means_no_suggestion(self, monkeypatch):
        monkeypatch.setattr(vr, "GEOIP_DB_PATH", "/nonexistent/db.mmdb")
        monkeypatch.setattr(vr, "_reader", None)
        assert vr.lookup_ip("1.2.3.4") is None
        assert vr.visitor_region("1.2.3.4", "") == {}

    def test_all_centers_are_inside_russia(self):
        assert len(vr.region_centers()) == 81
        for name, (lat, lon) in vr.region_centers().items():
            assert 41 <= lat <= 72 and 19 <= lon <= 180, name
