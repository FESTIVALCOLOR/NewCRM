# -*- coding: utf-8 -*-
"""
E2E Tests: Согласование, подача и принятие работы
10 тестов — подача работы дизайнером/чертёжником, принятие менеджером.
"""

import pytest
import sys
import os
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch


class TestWorkSubmission:
    """Подача работы исполнителями"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        # Перемещаем в стадию 1
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def test_designer_submits_work(self):
        """Дизайнер отмечает работу как выполненную"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        stage = "Стадия 1: планировочные решения"
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        encoded_stage = quote(stage, safe='')
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{encoded_stage}/complete",
            self.headers,
            json={"executor_id": designer["id"]}
        )
        assert resp.status_code == 200

    def test_draftsman_submits_work(self):
        """Чертёжник отмечает работу"""
        draftsman = self.employees.get('draftsman')
        if not draftsman:
            pytest.skip("Нет чертёжника")

        stage = "Стадия 1: планировочные решения"
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": draftsman["id"]}
        )

        encoded_stage = quote(stage, safe='')
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{encoded_stage}/complete",
            self.headers,
            json={"executor_id": draftsman["id"]}
        )
        assert resp.status_code == 200

    def test_complete_approval_stage(self):
        """Завершение этапа согласования"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/complete-approval-stage",
            self.headers,
            json={"stage_name": "Стадия 1: планировочные решения"}
        )
        assert resp.status_code == 200


class TestManagerAcceptance:
    """Принятие работы менеджером"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(self.contract["id"])
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    @pytest.mark.critical
    def test_manager_accepts_work(self):
        """Менеджер принимает работу"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/manager-acceptance",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_name": designer["full_name"],
                "manager_id": 1,
            }
        )
        assert resp.status_code == 200

    def test_get_accepted_stages(self):
        """Получение списка принятых стадий"""
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/accepted-stages",
            self.headers
        )
        assert resp.status_code == 200


class TestApprovalReset:
    """Сброс согласования"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])
        self.card = module_factory.create_crm_card(contract["id"])

    def test_reset_approval_stages(self):
        """Сброс этапов согласования"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-approval",
            self.headers
        )
        assert resp.status_code == 200

    def test_reset_stages(self):
        """Сброс стадий карточки"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-stages",
            self.headers
        )
        assert resp.status_code == 200

    def test_reset_designer_completion(self):
        """Сброс отметки дизайнера"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-designer",
            self.headers
        )
        assert resp.status_code == 200

    def test_reset_draftsman_completion(self):
        """Сброс отметки чертёжника"""
        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/reset-draftsman",
            self.headers
        )
        assert resp.status_code == 200
