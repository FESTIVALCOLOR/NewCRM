# -*- coding: utf-8 -*-
"""
E2E Tests: Дедлайны карточек и исполнителей
8 тестов — дедлайны на уровне карточки, исполнителя, согласования.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch


class TestCardDeadline:
    """Дедлайны на уровне CRM карточки"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(contract["id"])

    def test_set_card_deadline(self):
        """Установка дедлайна карточки"""
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"deadline": "2026-06-15"}
        )
        assert resp.status_code == 200
        assert resp.json()["deadline"] == "2026-06-15"

    def test_update_card_deadline(self):
        """Обновление дедлайна карточки"""
        api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"deadline": "2026-06-15"}
        )
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"deadline": "2026-07-01"}
        )
        assert resp.status_code == 200
        assert resp.json()["deadline"] == "2026-07-01"

    def test_card_deadline_can_be_cleared(self):
        """Дедлайн можно очистить"""
        api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"deadline": "2026-06-15"}
        )
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"deadline": None}
        )
        assert resp.status_code == 200


class TestExecutorDeadline:
    """Дедлайны на уровне исполнителя"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def test_set_executor_deadline(self):
        """Установка дедлайна исполнителя при назначении"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
                "deadline": "2026-05-01",
            }
        )
        assert resp.status_code == 200

    def test_update_executor_deadline(self):
        """Обновление дедлайна исполнителя"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        stage = "Стадия 1: планировочные решения"
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"], "deadline": "2026-05-01"}
        )

        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor-deadline",
            self.headers,
            json={"stage_name": stage, "deadline": "2026-06-01"}
        )
        assert resp.status_code == 200

    def test_executor_deadline_independent_from_card(self):
        """Дедлайн исполнителя независим от дедлайна карточки"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        # Ставим дедлайн карточки
        api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"deadline": "2026-12-31"}
        )

        # Ставим другой дедлайн исполнителю
        stage = "Стадия 1: планировочные решения"
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"], "deadline": "2026-05-01"}
        )

        # Проверяем что дедлайн карточки не изменился
        resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert resp.status_code == 200
        assert resp.json()["deadline"] == "2026-12-31"


class TestApprovalDeadline:
    """Дедлайны согласования"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(contract["id"])

    def test_set_approval_deadline(self):
        """Установка дедлайна согласования"""
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}",
            self.headers,
            json={"approval_deadline": "2026-08-01"}
        )
        assert resp.status_code == 200

    def test_get_approval_deadlines(self):
        """Получение дедлайнов согласования"""
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/approval-deadlines",
            self.headers
        )
        assert resp.status_code == 200
