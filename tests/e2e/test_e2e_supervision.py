# -*- coding: utf-8 -*-
"""
E2E Tests: Жизненный цикл авторского надзора
12 тестов — создание, назначение, пауза, возобновление, история.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch, api_delete


class TestSupervisionLifecycle:
    """Жизненный цикл карточки надзора"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    @pytest.mark.critical
    def test_create_supervision_card(self):
        """Создание карточки надзора"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])
        assert card["id"] > 0
        assert card["contract_id"] == contract["id"]
        assert card["column_name"] == "Новый заказ"

    def test_assign_dan(self):
        """Назначение ДАН на карточку надзора"""
        dan = self.employees.get('dan')
        if not dan:
            pytest.skip("Нет тестового ДАН")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/supervision/cards/{card['id']}",
            self.headers,
            json={"dan_id": dan["id"]}
        )
        assert resp.status_code == 200
        assert resp.json()["dan_id"] == dan["id"]

    def test_assign_senior_manager(self):
        """Назначение старшего менеджера на надзор"""
        sm = self.employees.get('senior_manager')
        if not sm:
            pytest.skip("Нет тестового старшего менеджера")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/supervision/cards/{card['id']}",
            self.headers,
            json={"senior_manager_id": sm["id"]}
        )
        assert resp.status_code == 200
        assert resp.json()["senior_manager_id"] == sm["id"]

    @pytest.mark.critical
    def test_move_between_columns(self):
        """Перемещение карточки надзора между колонками"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/column",
            self.headers,
            json={"column_name": "В ожидании"}
        )
        assert resp.status_code == 200
        assert resp.json()["column_name"] == "В ожидании"

    def test_pause_supervision(self):
        """Приостановка надзора"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/pause",
            self.headers,
            json={"pause_reason": "Ожидание материалов"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_paused"] == True

    def test_resume_supervision(self):
        """Возобновление надзора"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        # Ставим на паузу
        api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/pause",
            self.headers,
            json={"pause_reason": "Пауза"}
        )

        # Возобновляем
        resp = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/resume",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_paused"] == False

    def test_complete_stage(self):
        """Завершение стадии надзора"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/complete-stage",
            self.headers
        )
        assert resp.status_code == 200

    def test_add_history_entry(self):
        """Добавление записи истории"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers,
            json={
                "entry_type": "note",
                "message": "Тестовая заметка",
            }
        )
        assert resp.status_code == 200

    def test_get_history(self):
        """Получение истории надзора"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        # Добавляем запись
        api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers,
            json={"entry_type": "note", "message": "Запись для проверки"}
        )

        resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1


class TestSupervisionFromCRM:
    """Связь надзора с CRM"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_supervision_linked_to_same_contract(self):
        """Надзор привязан к тому же договору что и CRM"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])

        # Создаём CRM карточку
        crm_card = self.factory.create_crm_card(contract["id"])

        # Создаём карточку надзора для того же договора
        sv_card = self.factory.create_supervision_card(contract["id"])

        assert sv_card["contract_id"] == crm_card["contract_id"]
        assert sv_card["contract_id"] == contract["id"]

    def test_get_supervision_contract(self):
        """Получение информации о договоре из надзора"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/contract",
            self.headers
        )
        assert resp.status_code == 200

    def test_get_supervision_addresses(self):
        """Получение списка адресов надзора"""
        resp = api_get(
            self.api_base,
            "/api/supervision/addresses",
            self.headers
        )
        assert resp.status_code == 200
