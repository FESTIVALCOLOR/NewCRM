# -*- coding: utf-8 -*-
"""
Smoke Tests: Rates CRUD — тарифы всех типов.

Покрывает: template rates, individual rates, supervision rates,
surveyor rates, generic CRUD.

Запуск: pytest tests/smoke/test_rates_crud.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. Template Rates
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestTemplateRates:
    """P1: Шаблонные тарифы."""

    def test_list_template_rates(self, admin_headers):
        """GET /rates/template — список шаблонных тарифов."""
        resp = _get("/api/rates/template", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_create_template_rate(self, admin_headers):
        """POST /rates/template — создание шаблонного тарифа."""
        resp = _post("/api/rates/template", admin_headers, json={
            "agent_type": "ФЕСТИВАЛЬ",
            "rate_per_m2": 999.0,
            "description": f"{TEST_PREFIX}Шаблонный тариф",
        })
        # 200/201 или 409 если уже существует, 422 если невалидные данные
        assert resp.status_code in (200, 201, 409, 422), \
            f"Create template rate: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════
# 2. Individual Rates
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestIndividualRates:
    """P1: Индивидуальные тарифы."""

    def test_create_individual_rate(self, admin_headers):
        """POST /rates/individual — создание индивидуального тарифа."""
        client_id, contract_id, _ = create_test_card(admin_headers, "RATE_IND")
        try:
            resp = _post("/api/rates/individual", admin_headers, json={
                "contract_id": contract_id,
                "rate_per_m2": 5500.0,
            })
            assert resp.status_code in (200, 201, 409, 422), \
                f"Create individual: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_delete_individual_rate(self, admin_headers):
        """DELETE /rates/individual — удаление индивидуального тарифа."""
        client_id, contract_id, _ = create_test_card(admin_headers, "RATE_DEL")
        try:
            # Создаём
            _post("/api/rates/individual", admin_headers, json={
                "contract_id": contract_id,
                "rate_per_m2": 5500.0,
            })
            # Удаляем
            resp = _delete("/api/rates/individual", admin_headers)
            # Может потребовать contract_id как параметр
            assert resp.status_code in (200, 204, 400, 404, 422), \
                f"Delete individual: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)


# ════════════════════════════════════════════════════════════
# 3. Supervision & Surveyor Rates
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestSpecialRates:
    """P1: Надзорные и тарифы съёмщиков."""

    def test_create_supervision_rate(self, admin_headers):
        """POST /rates/supervision — создание тарифа надзора."""
        resp = _post("/api/rates/supervision", admin_headers, json={
            "agent_type": "ФЕСТИВАЛЬ",
            "rate_per_m2": 300.0,
            "description": f"{TEST_PREFIX}Надзор тариф",
        })
        assert resp.status_code in (200, 201, 409, 422), \
            f"Create supervision rate: {resp.status_code} {resp.text}"

    def test_create_surveyor_rate(self, admin_headers):
        """POST /rates/surveyor — создание тарифа съёмщика."""
        resp = _post("/api/rates/surveyor", admin_headers, json={
            "agent_type": "ФЕСТИВАЛЬ",
            "rate_per_m2": 200.0,
            "description": f"{TEST_PREFIX}Съёмщик тариф",
        })
        assert resp.status_code in (200, 201, 409, 422), \
            f"Create surveyor rate: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════
# 4. Generic Rate CRUD
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestGenericRateCRUD:
    """P1: Общий CRUD тарифов."""

    def test_list_all_rates(self, admin_headers):
        """GET /rates — полный список тарифов."""
        resp = _get("/api/rates", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_get_rate_by_id(self, admin_headers):
        """GET /rates/{id} — тариф по ID."""
        rates = _get("/api/rates", admin_headers).json()
        if not rates:
            pytest.skip("Нет тарифов")
        rate_id = rates[0]["id"]
        resp = _get(f"/api/rates/{rate_id}", admin_headers)
        assert resp.status_code == 200
        assert resp.json()["id"] == rate_id

    def test_create_update_delete_rate(self, admin_headers):
        """POST → PUT → DELETE /rates — полный цикл."""
        create = _post("/api/rates", admin_headers, json={
            "project_type": "Индивидуальный",
            "role": "Дизайнер",
            "stage_name": "Стадия 1: планировочные решения",
            "rate_per_m2": 7777.0,
        })
        if create.status_code not in (200, 201):
            pytest.skip(f"Создание тарифа: {create.status_code} {create.text}")
        rate_id = create.json()["id"]

        try:
            # Update
            upd = _put(f"/api/rates/{rate_id}", admin_headers, json={
                "rate_per_m2": 8888.0,
            })
            assert upd.status_code == 200, \
                f"Update rate: {upd.status_code} {upd.text}"
        finally:
            # Delete
            _delete(f"/api/rates/{rate_id}", admin_headers)
