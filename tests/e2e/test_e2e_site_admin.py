# -*- coding: utf-8 -*-
"""
E2E Tests: CMS сайта (site admin)
Регрессионные тесты на дефекты админки сайта:
  - PUT /site/admin/<list>/reorder отдавал 422 (маршрут перехватывался /<list>/{id})
  - частичное обновление ({is_visible}) отдавало 422 или затирало остальные поля
  - сохранение тарифа стирало подпункты (subitems)
  - доступ к CMS должен быть только у руководителя студии
"""

import os
import sys

import pytest
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_delete, api_get, api_post, api_put

BASE = "/api/v1/site/admin"


@pytest.fixture
def stat(api_base, admin_headers):
    resp = api_post(api_base, f"{BASE}/stats", admin_headers, json={"value": "42", "label": f"{TEST_PREFIX}цифра", "sort_order": 7})
    assert resp.status_code == 200, resp.text
    item = resp.json()
    yield item
    api_delete(api_base, f"{BASE}/stats/{item['id']}", admin_headers)


@pytest.fixture
def plan(api_base, admin_headers):
    payload = {
        "title": f"{TEST_PREFIX}тариф",
        "price_label": "1 руб",
        "sort_order": 5,
        "items": [{"text": "Пункт", "sort_order": 0, "subitems": ["подпункт 1", "подпункт 2"]}],
    }
    resp = api_post(api_base, f"{BASE}/pricing", admin_headers, json=payload)
    assert resp.status_code == 200, resp.text
    item = resp.json()
    yield item
    api_delete(api_base, f"{BASE}/pricing/{item['id']}", admin_headers)


@pytest.mark.e2e
class TestSiteAdminReorder:
    @pytest.mark.parametrize("name", ["services", "reviews", "portfolio", "stats", "pricing", "team"])
    def test_reorder_route_not_shadowed_by_id_route(self, api_base, admin_headers, name):
        resp = api_put(api_base, f"{BASE}/{name}/reorder", admin_headers, json=[])
        assert resp.status_code == 200, f"{name}: {resp.status_code} {resp.text}"

    def test_sections_reorder(self, api_base, admin_headers):
        sections = api_get(api_base, f"{BASE}/sections", admin_headers).json()
        same_order = [{"key": s["key"], "sort_order": s["sort_order"]} for s in sections]
        resp = api_put(api_base, f"{BASE}/sections/reorder", admin_headers, json=same_order)
        assert resp.status_code == 200, resp.text

    def test_reorder_changes_sort_order(self, api_base, admin_headers, stat):
        resp = api_put(api_base, f"{BASE}/stats/reorder", admin_headers, json=[{"id": stat["id"], "sort_order": 99}])
        assert resp.status_code == 200, resp.text
        stats = api_get(api_base, f"{BASE}/stats", admin_headers).json()
        assert next(s for s in stats if s["id"] == stat["id"])["sort_order"] == 99


@pytest.mark.e2e
class TestSiteAdminPartialUpdate:
    def test_partial_update_keeps_other_fields(self, api_base, admin_headers, stat):
        resp = api_put(api_base, f"{BASE}/stats/{stat['id']}", admin_headers, json={"value": "43"})
        assert resp.status_code == 200, resp.text
        updated = resp.json()
        assert updated["value"] == "43"
        assert updated["label"] == stat["label"]
        assert updated["sort_order"] == 7

    def test_visibility_toggle_keeps_plan_items_and_subitems(self, api_base, admin_headers, plan):
        resp = api_put(api_base, f"{BASE}/pricing/{plan['id']}", admin_headers, json={"is_visible": False})
        assert resp.status_code == 200, resp.text
        updated = resp.json()
        assert updated["is_visible"] is False
        assert updated["title"] == plan["title"]
        assert updated["sort_order"] == 5
        assert updated["items"][0]["subitems"] == ["подпункт 1", "подпункт 2"]

    def test_plan_items_replace_saves_subitems(self, api_base, admin_headers, plan):
        items = [{"text": "Новый пункт", "sort_order": 0, "subitems": ["а", "б"]}, {"text": "Без подпунктов", "sort_order": 1}]
        resp = api_put(api_base, f"{BASE}/pricing/{plan['id']}", admin_headers, json={"items": items})
        assert resp.status_code == 200, resp.text
        saved = resp.json()["items"]
        assert [i["text"] for i in saved] == ["Новый пункт", "Без подпунктов"]
        assert saved[0]["subitems"] == ["а", "б"]
        assert not saved[1]["subitems"]


@pytest.mark.e2e
class TestSiteAdminAccess:
    def test_requires_auth(self, api_base):
        assert api_get(api_base, f"{BASE}/settings", {}).status_code == 401

    def test_forbidden_for_non_director(self, api_base, role_tokens):
        headers = role_tokens.get("designer")
        if not headers:
            pytest.skip("нет токена дизайнера")
        resp = api_get(api_base, f"{BASE}/settings", headers)
        assert resp.status_code == 403
        assert "Руководителю студии" in resp.json()["detail"]

    def test_setting_upsert(self, api_base, admin_headers):
        key = f"{TEST_PREFIX}key"
        resp = api_put(api_base, f"{BASE}/settings/{key}", admin_headers, json={"value": "79991234567"})
        assert resp.status_code == 200, resp.text
        assert resp.json()["value"] == "79991234567"


@pytest.mark.e2e
class TestSiteObjectsMap:
    """Карта объектов: публичная выдача не должна содержать адресов и номеров договоров."""

    def test_public_points_have_no_private_fields(self, api_base):
        resp = api_get(api_base, "/api/v1/site/map-points", {})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert set(data) == {"points", "cities", "total"}
        assert data["total"] == len(data["points"])
        for point in data["points"]:
            # Подпись (адрес без квартиры) — по настройке; номера договоров и имена не передаются никогда
            assert {"lat", "lon", "kind", "city"} <= set(point) <= {"lat", "lon", "kind", "city", "label"}
            assert point["kind"] in {"done", "work", "supervision"}
            assert "кв" not in point.get("label", "").lower().split()

    def test_status_requires_site_admin(self, api_base, admin_headers, role_tokens):
        assert api_get(api_base, f"{BASE}/map/status", {}).status_code == 401
        designer = role_tokens.get("designer")
        if designer:
            assert api_get(api_base, f"{BASE}/map/status", designer).status_code == 403
        resp = api_get(api_base, f"{BASE}/map/status", admin_headers)
        assert resp.status_code == 200, resp.text
        status = resp.json()
        everything = status["total"] + status["extra_total"]
        assert everything == len(status["objects"])
        assert everything == status["shown"] + status["hidden"] + status["not_found"] + status["pending"]
        assert {obj["source"] for obj in status["objects"]} <= {"crm", "file"}

    def test_hiding_unknown_point_returns_404(self, api_base, admin_headers):
        resp = api_put(api_base, f"{BASE}/map/points/999999999", admin_headers, json={"hidden": True})
        assert resp.status_code == 404

    def test_import_requires_site_admin(self, api_base):
        files = {"file": ("objects.xlsx", b"x", "application/octet-stream")}
        assert requests.post(f"{api_base}{BASE}/map/import", files=files, timeout=30).status_code == 401
        assert api_delete(api_base, f"{BASE}/map/extra", {}).status_code == 401

    def test_import_of_non_excel_file_is_rejected(self, api_base, admin_headers):
        # Отказ должен случиться до записи в базу: объектов из файла не прибавляется
        before = api_get(api_base, f"{BASE}/map/status", admin_headers).json()["extra_total"]
        files = {"file": ("objects.xlsx", "Город;Адрес".encode("utf-8"), "application/octet-stream")}
        resp = requests.post(f"{api_base}{BASE}/map/import", headers=admin_headers, files=files, timeout=30)
        assert resp.status_code == 400, resp.text
        assert "xlsx" in resp.json()["detail"]
        assert api_get(api_base, f"{BASE}/map/status", admin_headers).json()["extra_total"] == before

    def test_import_template_is_an_excel_file(self, api_base, admin_headers):
        resp = api_get(api_base, f"{BASE}/map/import-template", admin_headers)
        assert resp.status_code == 200
        assert resp.content[:2] == b"PK"

    def test_unknown_extra_object_returns_404(self, api_base, admin_headers):
        assert api_put(api_base, f"{BASE}/map/extra/999999999", admin_headers, json={"hidden": True}).status_code == 404
        assert api_delete(api_base, f"{BASE}/map/extra/999999999", admin_headers).status_code == 404


READY = f"{BASE}/ready-designs"


@pytest.fixture
def ready_design(api_base, admin_headers):
    resp = api_post(api_base, READY, admin_headers, json={"title": f"{TEST_PREFIX}готовый дизайн", "tagline": "подпись", "description": "описание"})
    assert resp.status_code == 200, resp.text
    design = resp.json()
    yield design
    api_delete(api_base, f"{READY}/{design['id']}", admin_headers)


def _public_design(api_base, design_id):
    resp = api_get(api_base, "/api/v1/site/ready-designs", {})
    assert resp.status_code == 200, resp.text
    return next((item for item in resp.json() if item["id"] == design_id), None)


class TestSiteReadyDesigns:
    """Каталог готовых дизайнов: галерея, отметки мебели на фото, публичная выдача."""

    def test_requires_site_admin(self, api_base, role_tokens):
        assert api_get(api_base, READY, {}).status_code == 401
        assert api_post(api_base, READY, {}, json={"title": "x"}).status_code == 401
        designer = role_tokens.get("designer")
        if designer:
            assert api_get(api_base, READY, designer).status_code == 403

    def test_public_list_needs_no_auth(self, api_base):
        resp = api_get(api_base, "/api/v1/site/ready-designs", {})
        assert resp.status_code == 200, resp.text
        assert isinstance(resp.json(), list)

    def test_gallery_and_markers_reach_public_site(self, api_base, admin_headers, ready_design):
        design_id = ready_design["id"]
        image = api_post(api_base, f"{READY}/{design_id}/images", admin_headers, json={"url": "/api/v1/site/media/test.jpg"}).json()
        assert image["markers"] == []

        product = {"image_url": "/api/v1/site/media/sofa.jpg", "sku": "SF-1", "color": "серый", "shape": "угловой", "size": "240 × 160 см"}
        markers = [
            {"x": 12.5, "y": 80, "title": " Диван ", "description": "угловой", "url": "https://example.com/sofa", **product},
            {"x": 100, "y": 0, "title": "Торшер"},
        ]
        resp = api_put(api_base, f"{READY}/images/{image['id']}", admin_headers, json={"markers": markers})
        assert resp.status_code == 200, resp.text
        assert [m["title"] for m in resp.json()["markers"]] == ["Диван", "Торшер"]

        public = _public_design(api_base, design_id)
        assert public is not None
        assert public["title"] == ready_design["title"]
        assert len(public["images"]) == 1
        assert public["images"][0]["markers"][0] == {"x": 12.5, "y": 80.0, "title": "Диван", "description": "угловой", "url": "https://example.com/sofa", **product}
        # Отметка без данных товара остаётся допустимой: поля просто пустые
        assert public["images"][0]["markers"][1]["image_url"] == "" and public["images"][0]["markers"][1]["sku"] == ""

    @pytest.mark.parametrize(
        "marker",
        [
            {"x": 10, "y": 10, "title": "Диван", "url": "javascript:alert(1)"},
            {"x": 101, "y": 10, "title": "Диван"},
            {"x": 10, "y": -1, "title": "Диван"},
            {"x": 10, "y": 10, "title": "   "},
            {"x": 10, "y": 10, "title": "Диван", "image_url": "javascript:alert(1)"},
            {"x": 10, "y": 10, "title": "Диван", "sku": "x" * 101},
        ],
    )
    def test_bad_marker_is_rejected_and_nothing_saved(self, api_base, admin_headers, ready_design, marker):
        image = api_post(api_base, f"{READY}/{ready_design['id']}/images", admin_headers, json={"url": "/api/v1/site/media/test.jpg"}).json()
        resp = api_put(api_base, f"{READY}/images/{image['id']}", admin_headers, json={"markers": [marker]})
        assert resp.status_code == 422, resp.text
        assert _public_design(api_base, ready_design["id"])["images"][0]["markers"] == []

    def test_hidden_design_is_not_public(self, api_base, admin_headers, ready_design):
        resp = api_put(api_base, f"{READY}/{ready_design['id']}", admin_headers, json={"is_visible": False})
        assert resp.status_code == 200, resp.text
        # Частичное обновление не затирает остальные поля
        assert resp.json()["title"] == ready_design["title"]
        assert resp.json()["description"] == "описание"
        assert _public_design(api_base, ready_design["id"]) is None

    def test_cover_can_be_set_and_cleared(self, api_base, admin_headers, ready_design):
        url = f"{READY}/{ready_design['id']}"
        assert api_put(api_base, url, admin_headers, json={"cover_url": "/api/v1/site/media/cover.jpg"}).json()["cover_url"] == "/api/v1/site/media/cover.jpg"
        assert api_put(api_base, url, admin_headers, json={"cover_url": None}).json()["cover_url"] is None

    def test_reorder_routes_not_shadowed_by_id_routes(self, api_base, admin_headers, ready_design):
        resp = api_put(api_base, f"{READY}/reorder", admin_headers, json=[{"id": ready_design["id"], "sort_order": 3}])
        assert resp.status_code == 200, resp.text
        image = api_post(api_base, f"{READY}/{ready_design['id']}/images", admin_headers, json={"url": "/api/v1/site/media/test.jpg"}).json()
        resp = api_put(api_base, f"{READY}/images/reorder", admin_headers, json=[{"id": image["id"], "sort_order": 5}])
        assert resp.status_code == 200, resp.text
        saved = next(item for item in api_get(api_base, READY, admin_headers).json() if item["id"] == ready_design["id"])
        assert saved["sort_order"] == 3
        assert saved["images"][0]["sort_order"] == 5

    def test_deleting_design_removes_its_images(self, api_base, admin_headers, ready_design):
        image = api_post(api_base, f"{READY}/{ready_design['id']}/images", admin_headers, json={"url": "/api/v1/site/media/test.jpg"}).json()
        assert api_delete(api_base, f"{READY}/{ready_design['id']}", admin_headers).status_code == 200
        assert api_put(api_base, f"{READY}/images/{image['id']}", admin_headers, json={"alt": "x"}).status_code == 404
        assert api_delete(api_base, f"{READY}/{ready_design['id']}", admin_headers).status_code == 404

    def test_product_preview_requires_site_admin(self, api_base):
        assert api_post(api_base, f"{READY}/product-preview", {}, json={"url": "https://example.com/"}).status_code == 401

    @pytest.mark.parametrize("url", ["http://127.0.0.1:8000/health", "http://localhost/admin", "ftp://example.com/a", "file:///etc/passwd", "http://169.254.169.254/latest/meta-data/"])
    def test_product_preview_refuses_non_public_links(self, api_base, admin_headers, url):
        # Запрос по ссылке делает сервер, поэтому внутренние адреса должны отсекаться
        resp = api_post(api_base, f"{READY}/product-preview", admin_headers, json={"url": url})
        assert resp.status_code == 400, resp.text
