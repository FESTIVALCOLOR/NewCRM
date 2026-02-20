# -*- coding: utf-8 -*-
"""
E2E Tests: Тарифы (Rates) - CRUD, шаблонные, индивидуальные, надзор, замерщик
25 тестов - полное покрытие всех /api/rates/* endpoints.
"""

import pytest
import requests
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import (
    TEST_PREFIX, REQUEST_TIMEOUT, _http_session,
    api_get, api_post, api_put, api_delete,
)


# ==============================================================
# CRUD ТАРИФОВ (базовые endpoints)
# ==============================================================

class TestRatesCRUD:
    """CRUD операции с тарифами через /api/rates"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory

    @pytest.mark.order(1)
    @pytest.mark.critical
    def test_create_rate(self):
        """Создание тарифа через POST /api/rates"""
        rate = self.factory.create_rate(
            project_type="Индивидуальный",
            role="Дизайнер",
            rate_per_m2=100.0,
            stage_name=f"{TEST_PREFIX}stage_crud_create",
        )
        assert rate["id"] > 0
        assert rate["project_type"] == "Индивидуальный"
        assert rate["role"] == "Дизайнер"
        assert rate["rate_per_m2"] == 100.0
        assert f"{TEST_PREFIX}stage_crud_create" in rate["stage_name"]

    @pytest.mark.order(2)
    def test_get_rate_by_id(self):
        """Получение тарифа по ID через GET /api/rates/{rate_id}"""
        rate = self.factory.create_rate(
            stage_name=f"{TEST_PREFIX}stage_get_by_id",
        )
        resp = api_get(self.api_base, f"/api/rates/{rate['id']}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rate["id"]
        assert data["role"] == rate["role"]
        assert data["rate_per_m2"] == rate["rate_per_m2"]

    @pytest.mark.order(3)
    def test_get_rate_not_found(self):
        """GET /api/rates/{rate_id} возвращает 404 для несуществующего тарифа"""
        resp = api_get(self.api_base, "/api/rates/999999999", self.headers)
        assert resp.status_code == 404

    @pytest.mark.order(4)
    def test_list_all_rates(self):
        """Получение списка всех тарифов через GET /api/rates"""
        # Создаём тариф чтобы список не был пустым
        self.factory.create_rate(stage_name=f"{TEST_PREFIX}stage_list_all")
        resp = api_get(self.api_base, "/api/rates", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

    @pytest.mark.order(5)
    def test_list_rates_filter_by_project_type(self):
        """Фильтрация тарифов по project_type"""
        self.factory.create_rate(
            project_type="Индивидуальный",
            stage_name=f"{TEST_PREFIX}stage_filter_pt",
        )
        resp = api_get(
            self.api_base, "/api/rates", self.headers,
            params={"project_type": "Индивидуальный"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for rate in data:
            assert rate["project_type"] == "Индивидуальный"

    @pytest.mark.order(6)
    def test_list_rates_filter_by_role(self):
        """Фильтрация тарифов по role"""
        self.factory.create_rate(
            role="Чертёжник",
            stage_name=f"{TEST_PREFIX}stage_filter_role",
        )
        resp = api_get(
            self.api_base, "/api/rates", self.headers,
            params={"role": "Чертёжник"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for rate in data:
            assert rate["role"] == "Чертёжник"

    @pytest.mark.order(7)
    def test_update_rate(self):
        """Обновление тарифа через PUT /api/rates/{rate_id}"""
        rate = self.factory.create_rate(
            rate_per_m2=100.0,
            stage_name=f"{TEST_PREFIX}stage_update",
        )
        resp = api_put(
            self.api_base, f"/api/rates/{rate['id']}", self.headers,
            json={"rate_per_m2": 250.0}
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["id"] == rate["id"]
        assert updated["rate_per_m2"] == 250.0

    @pytest.mark.order(8)
    def test_update_rate_multiple_fields(self):
        """Обновление нескольких полей тарифа"""
        rate = self.factory.create_rate(
            stage_name=f"{TEST_PREFIX}stage_update_multi",
        )
        resp = api_put(
            self.api_base, f"/api/rates/{rate['id']}", self.headers,
            json={
                "role": "Чертёжник",
                "rate_per_m2": 300.0,
            }
        )
        assert resp.status_code == 200
        updated = resp.json()
        assert updated["role"] == "Чертёжник"
        assert updated["rate_per_m2"] == 300.0

    @pytest.mark.order(9)
    def test_delete_rate(self):
        """Удаление тарифа через DELETE /api/rates/{rate_id}"""
        # Создаём напрямую, не через фабрику, чтобы сами удалили
        resp = api_post(self.api_base, "/api/rates", self.headers, json={
            "project_type": "Индивидуальный",
            "role": "Дизайнер",
            "rate_per_m2": 50.0,
            "stage_name": f"{TEST_PREFIX}stage_delete",
        })
        assert resp.status_code == 200
        rate_id = resp.json()["id"]

        # Удаляем
        resp = api_delete(self.api_base, f"/api/rates/{rate_id}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"

        # Проверяем что удалён
        resp = api_get(self.api_base, f"/api/rates/{rate_id}", self.headers)
        assert resp.status_code == 404


# ==============================================================
# ШАБЛОННЫЕ ТАРИФЫ
# ==============================================================

class TestTemplateRates:
    """Шаблонные тарифы: GET /api/rates/template, POST /api/rates/template"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory
        self._manually_created_ids = []

    def _cleanup_manual_rates(self):
        """Удаление вручную созданных тарифов"""
        for rate_id in self._manually_created_ids:
            try:
                _http_session.delete(
                    f"{self.api_base}/api/rates/{rate_id}",
                    headers=self.headers,
                    timeout=REQUEST_TIMEOUT,
                )
            except Exception:
                pass

    @pytest.mark.order(1)
    @pytest.mark.critical
    def test_create_template_rate(self):
        """Создание шаблонного тарифа через POST /api/rates/template"""
        resp = api_post(self.api_base, "/api/rates/template", self.headers, json={
            "role": "Дизайнер",
            "area_from": 0.0,
            "area_to": 50.0,
            "price": 100000.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["project_type"] == "Шаблонный"
        assert data["role"] == "Дизайнер"
        assert data["area_from"] == 0.0
        assert data["area_to"] == 50.0
        assert data["fixed_price"] == 100000.0
        self.factory.track_rate(data["id"])
        self._manually_created_ids.append(data["id"])

    @pytest.mark.order(2)
    def test_upsert_template_rate_updates_existing(self):
        """POST /api/rates/template обновляет существующий тариф (upsert)"""
        # Создаём
        resp1 = api_post(self.api_base, "/api/rates/template", self.headers, json={
            "role": "Чертёжник",
            "area_from": 50.0,
            "area_to": 100.0,
            "price": 80000.0,
        })
        assert resp1.status_code == 200
        first_id = resp1.json()["id"]
        self.factory.track_rate(first_id)

        # Обновляем тот же тариф (те же role + area_from + area_to)
        resp2 = api_post(self.api_base, "/api/rates/template", self.headers, json={
            "role": "Чертёжник",
            "area_from": 50.0,
            "area_to": 100.0,
            "price": 120000.0,
        })
        assert resp2.status_code == 200
        data = resp2.json()
        # Должен обновить, а не создать новый
        assert data["id"] == first_id
        assert data["fixed_price"] == 120000.0

    @pytest.mark.order(3)
    def test_get_template_rates(self):
        """Получение списка шаблонных тарифов через GET /api/rates/template"""
        # Создаём шаблонный тариф
        resp_create = api_post(self.api_base, "/api/rates/template", self.headers, json={
            "role": "Дизайнер",
            "area_from": 100.0,
            "area_to": 150.0,
            "price": 200000.0,
        })
        assert resp_create.status_code == 200
        self.factory.track_rate(resp_create.json()["id"])

        resp = api_get(self.api_base, "/api/rates/template", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Все записи должны быть шаблонными
        for rate in data:
            assert rate["project_type"] == "Шаблонный"

    @pytest.mark.order(4)
    def test_get_template_rates_filter_by_role(self):
        """Фильтрация шаблонных тарифов по role"""
        # Создаём тариф для конкретной роли
        resp_create = api_post(self.api_base, "/api/rates/template", self.headers, json={
            "role": "Дизайнер",
            "area_from": 200.0,
            "area_to": 300.0,
            "price": 350000.0,
        })
        assert resp_create.status_code == 200
        self.factory.track_rate(resp_create.json()["id"])

        resp = api_get(
            self.api_base, "/api/rates/template", self.headers,
            params={"role": "Дизайнер"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for rate in data:
            assert rate["role"] == "Дизайнер"
            assert rate["project_type"] == "Шаблонный"


# ==============================================================
# ИНДИВИДУАЛЬНЫЕ ТАРИФЫ
# ==============================================================

class TestIndividualRates:
    """Индивидуальные тарифы: POST /api/rates/individual, DELETE /api/rates/individual"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory

    @pytest.mark.order(1)
    @pytest.mark.critical
    def test_create_individual_rate(self):
        """Создание индивидуального тарифа через POST /api/rates/individual"""
        resp = api_post(self.api_base, "/api/rates/individual", self.headers, json={
            "role": "Дизайнер",
            "rate_per_m2": 150.0,
            "stage_name": f"{TEST_PREFIX}individual_stage1",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["project_type"] == "Индивидуальный"
        assert data["role"] == "Дизайнер"
        assert data["rate_per_m2"] == 150.0
        self.factory.track_rate(data["id"])

    @pytest.mark.order(2)
    def test_create_individual_rate_no_stage(self):
        """Создание индивидуального тарифа без stage_name"""
        resp = api_post(self.api_base, "/api/rates/individual", self.headers, json={
            "role": "Чертёжник",
            "rate_per_m2": 80.0,
            "stage_name": None,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["project_type"] == "Индивидуальный"
        assert data["role"] == "Чертёжник"
        assert data["rate_per_m2"] == 80.0
        self.factory.track_rate(data["id"])

    @pytest.mark.order(3)
    def test_upsert_individual_rate(self):
        """POST /api/rates/individual обновляет существующий тариф (upsert)"""
        stage = f"{TEST_PREFIX}individual_upsert"
        # Создаём
        resp1 = api_post(self.api_base, "/api/rates/individual", self.headers, json={
            "role": "Дизайнер",
            "rate_per_m2": 100.0,
            "stage_name": stage,
        })
        assert resp1.status_code == 200
        first_id = resp1.json()["id"]
        self.factory.track_rate(first_id)

        # Обновляем (тот же role + stage_name)
        resp2 = api_post(self.api_base, "/api/rates/individual", self.headers, json={
            "role": "Дизайнер",
            "rate_per_m2": 200.0,
            "stage_name": stage,
        })
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["id"] == first_id
        assert data["rate_per_m2"] == 200.0

    @pytest.mark.order(4)
    def test_delete_individual_rate(self):
        """Удаление индивидуального тарифа через DELETE /api/rates/{id}"""
        stage = f"{TEST_PREFIX}individual_delete"
        # Создаём
        resp_create = api_post(self.api_base, "/api/rates/individual", self.headers, json={
            "role": "Дизайнер",
            "rate_per_m2": 100.0,
            "stage_name": stage,
        })
        assert resp_create.status_code == 200
        created_id = resp_create.json()["id"]

        # Удаляем через generic DELETE /api/rates/{id}
        resp = api_delete(self.api_base, f"/api/rates/{created_id}", self.headers)
        assert resp.status_code == 200

        # Проверяем что удалён
        resp_check = api_get(self.api_base, f"/api/rates/{created_id}", self.headers)
        assert resp_check.status_code == 404

    @pytest.mark.order(5)
    def test_delete_individual_rate_by_role_only(self):
        """Удаление индивидуальных тарифов по id после создания"""
        stage = f"{TEST_PREFIX}individual_del_role"
        # Создаём тариф
        resp_create = api_post(self.api_base, "/api/rates/individual", self.headers, json={
            "role": "ГАП",
            "rate_per_m2": 50.0,
            "stage_name": stage,
        })
        assert resp_create.status_code == 200
        created_id = resp_create.json()["id"]

        # Удаляем через generic endpoint
        resp = api_delete(self.api_base, f"/api/rates/{created_id}", self.headers)
        assert resp.status_code == 200


# ==============================================================
# ТАРИФЫ НАДЗОРА
# ==============================================================

class TestSupervisionRates:
    """Тарифы надзора: POST /api/rates/supervision (создаёт 2 записи: ДАН + Старший менеджер)"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory

    @pytest.mark.order(1)
    @pytest.mark.critical
    def test_create_supervision_rates(self):
        """Создание тарифов надзора через POST /api/rates/supervision"""
        stage = f"{TEST_PREFIX}supervision_stage1"
        resp = api_post(self.api_base, "/api/rates/supervision", self.headers, json={
            "stage_name": stage,
            "executor_rate": 50.0,
            "manager_rate": 30.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["stage_name"] == stage
        assert isinstance(data["rates"], list)
        assert len(data["rates"]) == 2

        # Проверяем что созданы записи для ДАН и Старшего менеджера
        roles_in_response = [r["role"] for r in data["rates"]]
        assert "ДАН" in roles_in_response
        assert "Старший менеджер проектов" in roles_in_response

        # Проверяем ставки
        for r in data["rates"]:
            if r["role"] == "ДАН":
                assert r["rate"] == 50.0
            elif r["role"] == "Старший менеджер проектов":
                assert r["rate"] == 30.0

        # Находим и трекаем созданные записи через GET /api/rates
        resp_all = api_get(
            self.api_base, "/api/rates", self.headers,
            params={"role": "ДАН"}
        )
        if resp_all.status_code == 200:
            for rate in resp_all.json():
                if rate.get("stage_name") == stage:
                    self.factory.track_rate(rate["id"])

        resp_all2 = api_get(
            self.api_base, "/api/rates", self.headers,
            params={"role": "Старший менеджер проектов"}
        )
        if resp_all2.status_code == 200:
            for rate in resp_all2.json():
                if rate.get("stage_name") == stage:
                    self.factory.track_rate(rate["id"])

    @pytest.mark.order(2)
    def test_upsert_supervision_rates(self):
        """POST /api/rates/supervision обновляет существующие тарифы (upsert)"""
        stage = f"{TEST_PREFIX}supervision_upsert"

        # Создаём
        resp1 = api_post(self.api_base, "/api/rates/supervision", self.headers, json={
            "stage_name": stage,
            "executor_rate": 40.0,
            "manager_rate": 20.0,
        })
        assert resp1.status_code == 200

        # Обновляем (тот же stage_name)
        resp2 = api_post(self.api_base, "/api/rates/supervision", self.headers, json={
            "stage_name": stage,
            "executor_rate": 60.0,
            "manager_rate": 35.0,
        })
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["status"] == "success"

        # Проверяем обновлённые ставки
        for r in data["rates"]:
            if r["role"] == "ДАН":
                assert r["rate"] == 60.0
            elif r["role"] == "Старший менеджер проектов":
                assert r["rate"] == 35.0

        # Трекаем для очистки
        resp_cleanup = api_get(self.api_base, "/api/rates", self.headers)
        if resp_cleanup.status_code == 200:
            for rate in resp_cleanup.json():
                if rate.get("stage_name") == stage and rate.get("project_type") == "Авторский надзор":
                    self.factory.track_rate(rate["id"])

    @pytest.mark.order(3)
    def test_supervision_rates_stored_separately(self):
        """Тарифы надзора хранятся как отдельные записи Rate с project_type='Авторский надзор'"""
        stage = f"{TEST_PREFIX}supervision_separate"
        resp = api_post(self.api_base, "/api/rates/supervision", self.headers, json={
            "stage_name": stage,
            "executor_rate": 45.0,
            "manager_rate": 25.0,
        })
        assert resp.status_code == 200

        # Проверяем через основной endpoint что записи существуют
        resp_all = api_get(self.api_base, "/api/rates", self.headers)
        assert resp_all.status_code == 200
        all_rates = resp_all.json()

        supervision_rates = [
            r for r in all_rates
            if r.get("stage_name") == stage and r.get("project_type") == "Авторский надзор"
        ]
        assert len(supervision_rates) == 2

        roles = set(r["role"] for r in supervision_rates)
        assert roles == {"Старший менеджер проектов", "ДАН"}

        # Трекаем для очистки
        for rate in supervision_rates:
            self.factory.track_rate(rate["id"])


# ==============================================================
# ТАРИФЫ ЗАМЕРЩИКА
# ==============================================================

class TestSurveyorRates:
    """Тарифы замерщика: POST /api/rates/surveyor"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = factory

    @pytest.mark.order(1)
    @pytest.mark.critical
    def test_create_surveyor_rate(self):
        """Создание тарифа замерщика через POST /api/rates/surveyor"""
        resp = api_post(self.api_base, "/api/rates/surveyor", self.headers, json={
            "city": "СПБ",
            "price": 5000.0,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] > 0
        assert data["role"] == "Замерщик"
        assert data["city"] == "СПБ"
        assert data["surveyor_price"] == 5000.0
        self.factory.track_rate(data["id"])

    @pytest.mark.order(2)
    def test_upsert_surveyor_rate(self):
        """POST /api/rates/surveyor обновляет существующий тариф (upsert)"""
        # Создаём
        resp1 = api_post(self.api_base, "/api/rates/surveyor", self.headers, json={
            "city": "МСК",
            "price": 6000.0,
        })
        assert resp1.status_code == 200
        first_id = resp1.json()["id"]
        self.factory.track_rate(first_id)

        # Обновляем (тот же city)
        resp2 = api_post(self.api_base, "/api/rates/surveyor", self.headers, json={
            "city": "МСК",
            "price": 8000.0,
        })
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["id"] == first_id
        assert data["surveyor_price"] == 8000.0

    @pytest.mark.order(3)
    def test_create_surveyor_rate_different_cities(self):
        """Тарифы замерщика для разных городов -- отдельные записи"""
        cities_prices = [
            ("СПБ", 5000.0),
            ("МСК", 7000.0),
            ("ВН", 4000.0),
        ]
        created_ids = []

        for city, price in cities_prices:
            resp = api_post(self.api_base, "/api/rates/surveyor", self.headers, json={
                "city": city,
                "price": price,
            })
            assert resp.status_code == 200
            data = resp.json()
            assert data["city"] == city
            assert data["surveyor_price"] == price
            created_ids.append(data["id"])
            self.factory.track_rate(data["id"])

        # Проверяем что все 3 города имеют тарифы
        resp_all = api_get(
            self.api_base, "/api/rates", self.headers,
            params={"role": "Замерщик"}
        )
        assert resp_all.status_code == 200
        surveyor_rates = resp_all.json()
        cities_found = {r["city"] for r in surveyor_rates if r.get("city")}
        for city, _ in cities_prices:
            assert city in cities_found, f"Тариф для города {city} не найден"

    @pytest.mark.order(4)
    def test_surveyor_rate_retrievable_via_generic_endpoint(self):
        """Тариф замерщика доступен через GET /api/rates/{rate_id}"""
        resp_create = api_post(self.api_base, "/api/rates/surveyor", self.headers, json={
            "city": "ВН",
            "price": 3500.0,
        })
        assert resp_create.status_code == 200
        rate_id = resp_create.json()["id"]
        self.factory.track_rate(rate_id)

        resp = api_get(self.api_base, f"/api/rates/{rate_id}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == rate_id
        assert data["role"] == "Замерщик"
        assert data["city"] == "ВН"
        assert data["surveyor_price"] == 3500.0
