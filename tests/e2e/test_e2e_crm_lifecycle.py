# -*- coding: utf-8 -*-
"""
E2E Tests: Полный цикл CRM карточки
18 тестов — создание, перемещение через все колонки, замер, шаблонные проекты.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch


# ==============================================================
# СОЗДАНИЕ CRM КАРТОЧЕК
# ==============================================================

class TestCRMCardCreation:
    """Создание CRM карточек"""

    @pytest.mark.critical
    def test_create_card_for_individual_project(self, api_base, admin_headers, module_factory):
        """Создание карточки для индивидуального проекта"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"], project_type="Индивидуальный")
        card = module_factory.create_crm_card(contract["id"])
        assert card["id"] > 0
        assert card["contract_id"] == contract["id"]

    @pytest.mark.critical
    def test_create_card_for_template_project(self, api_base, admin_headers, module_factory):
        """Создание карточки для шаблонного проекта"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"], project_type="Шаблонный")
        card = module_factory.create_crm_card(contract["id"])
        assert card["id"] > 0

    def test_card_default_column_new_order(self, api_base, admin_headers, module_factory):
        """Карточка по умолчанию в колонке 'Новый заказ'"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        card = module_factory.create_crm_card(contract["id"])
        assert card["column_name"] == "Новый заказ"

    def test_card_links_to_contract(self, api_base, admin_headers, module_factory):
        """Карточка привязана к договору"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        card = module_factory.create_crm_card(contract["id"])

        resp = api_get(api_base, f"/api/crm/cards/{card['id']}", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["contract_id"] == contract["id"]


# ==============================================================
# ПЕРЕМЕЩЕНИЕ КАРТОЧЕК
# ==============================================================

class TestCRMCardMovement:
    """Перемещение карточек через все колонки"""

    @pytest.fixture(autouse=True)
    def setup_card(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(
            client["id"], project_type="Индивидуальный"
        )
        self.card = module_factory.create_crm_card(self.contract["id"])

    def _move_card(self, column_name):
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/column",
            self.headers,
            json={"column_name": column_name}
        )
        return resp

    @pytest.mark.critical
    def test_move_new_order_to_waiting(self):
        """Новый заказ -> В ожидании"""
        resp = self._move_card("В ожидании")
        assert resp.status_code == 200
        data = resp.json()
        assert data["column_name"] == "В ожидании"

    @pytest.mark.critical
    def test_move_waiting_to_stage1(self):
        """В ожидании -> Стадия 1"""
        self._move_card("В ожидании")
        resp = self._move_card("Стадия 1: планировочные решения")
        assert resp.status_code == 200

    def test_move_stage1_to_stage2_concept(self):
        """Стадия 1 -> Стадия 2: концепция (только индивидуальные)"""
        self._move_card("В ожидании")
        self._move_card("Стадия 1: планировочные решения")
        resp = self._move_card("Стадия 2: концепция дизайна")
        assert resp.status_code == 200

    def test_move_to_stage3(self):
        """-> Стадия 3: рабочие чертежи"""
        self._move_card("В ожидании")
        self._move_card("Стадия 1: планировочные решения")
        self._move_card("Стадия 2: концепция дизайна")
        resp = self._move_card("Стадия 3: рабочие чертежи")
        assert resp.status_code == 200

    def test_move_to_completed(self):
        """-> Выполненный проект"""
        self._move_card("В ожидании")
        self._move_card("Стадия 1: планировочные решения")
        self._move_card("Стадия 2: концепция дизайна")
        self._move_card("Стадия 3: рабочие чертежи")
        resp = self._move_card("Выполненный проект")
        assert resp.status_code == 200

    def test_template_project_skips_stage2_concept(self):
        """Шаблонный проект: стадии отличаются от индивидуального"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Шаблонный")
        card = self.factory.create_crm_card(contract["id"])

        # Перемещаем через стадии шаблонного проекта
        api_patch(self.api_base, f"/api/crm/cards/{card['id']}/column",
                  self.headers, json={"column_name": "В ожидании"})
        api_patch(self.api_base, f"/api/crm/cards/{card['id']}/column",
                  self.headers, json={"column_name": "Стадия 1: планировочные решения"})
        # Шаблонный — Стадия 2: рабочие чертежи (без Стадии 2: концепция дизайна)
        resp = api_patch(self.api_base, f"/api/crm/cards/{card['id']}/column",
                         self.headers, json={"column_name": "Стадия 2: рабочие чертежи"})
        assert resp.status_code == 200

    def test_get_card_after_movement(self):
        """Получение карточки отражает текущую колонку"""
        self._move_card("В ожидании")
        resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert resp.status_code == 200
        assert resp.json()["column_name"] == "В ожидании"

    def test_get_cards_by_project_type(self):
        """Получение карточек с фильтром по типу проекта"""
        resp = api_get(self.api_base, "/api/crm/cards", self.headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)


# ==============================================================
# ЭТАП ЗАМЕРА
# ==============================================================

class TestMeasurement:
    """Тесты этапа замера"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])

    def test_set_measurement_date(self):
        """Установка даты замера"""
        resp = api_patch(
            self.api_base,
            f"/api/contracts/{self.contract['id']}/files",
            self.headers,
            json={"measurement_date": "2026-03-15"}
        )
        assert resp.status_code == 200

    def test_assign_surveyor(self):
        """Назначение замерщика"""
        surveyor = self.employees.get('surveyor')
        if not surveyor:
            pytest.skip("Нет тестового замерщика")
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"surveyor_id": surveyor["id"]}
        )
        assert resp.status_code == 200
        # PATCH response doesn't include employee FK fields, verify via GET
        get_resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["surveyor_id"] == surveyor["id"]

    def test_assign_sdp(self):
        """Назначение СДП на карточку"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет тестового СДП")
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"sdp_id": sdp["id"]}
        )
        assert resp.status_code == 200
        # PATCH response doesn't include employee FK fields, verify via GET
        get_resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["sdp_id"] == sdp["id"]

    def test_assign_gap(self):
        """Назначение ГАП на карточку"""
        gap = self.employees.get('gap')
        if not gap:
            pytest.skip("Нет тестового ГАП")
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"gap_id": gap["id"]}
        )
        assert resp.status_code == 200
        # PATCH response doesn't include employee FK fields, verify via GET
        get_resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["gap_id"] == gap["id"]

    def test_assign_manager(self):
        """Назначение менеджера на карточку"""
        manager = self.employees.get('manager')
        if not manager:
            pytest.skip("Нет тестового менеджера")
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"manager_id": manager["id"]}
        )
        assert resp.status_code == 200
        # PATCH response doesn't include employee FK fields, verify via GET
        get_resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["manager_id"] == manager["id"]

    def test_assign_senior_manager(self):
        """Назначение старшего менеджера на карточку"""
        sm = self.employees.get('senior_manager')
        if not sm:
            pytest.skip("Нет тестового старшего менеджера")
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"senior_manager_id": sm["id"]}
        )
        assert resp.status_code == 200
        # PATCH response doesn't include employee FK fields, verify via GET
        get_resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["senior_manager_id"] == sm["id"]
