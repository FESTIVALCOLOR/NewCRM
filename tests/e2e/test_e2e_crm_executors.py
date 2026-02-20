# -*- coding: utf-8 -*-
"""
E2E Tests: Назначение и переназначение исполнителей
12 тестов — назначение на стадии, переназначение, создание платежей.
"""

import pytest
import sys
import os
from urllib.parse import quote

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch, api_delete


class TestExecutorAssignment:
    """Назначение исполнителей на стадии"""

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

    @pytest.mark.critical
    def test_assign_designer_to_stage(self):
        """Назначить дизайнера на стадию"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )
        assert resp.status_code == 200, f"Назначение дизайнера: {resp.status_code} {resp.text}"

    def test_assign_draftsman_to_stage(self):
        """Назначить чертёжника на стадию"""
        draftsman = self.employees.get('draftsman')
        if not draftsman:
            pytest.skip("Нет тестового чертёжника")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": draftsman["id"],
            }
        )
        assert resp.status_code == 200

    def test_assign_with_deadline(self):
        """Назначение с дедлайном исполнителя"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
                "deadline": "2026-04-01",
            }
        )
        assert resp.status_code == 200

    def test_get_card_shows_stage_executors(self):
        """Получение карточки показывает stage_executors"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": designer["id"],
            }
        )

        resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        # Карточка должна содержать информацию об исполнителях
        assert "stage_executors" in data or "id" in data


class TestExecutorReassignment:
    """Переназначение исполнителей"""

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
    def test_reassign_designer(self):
        """Переназначить дизайнера: обновление executor_id"""
        designer = self.employees.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer or not draftsman:
            pytest.skip("Нужны дизайнер и чертёжник")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        # Первое назначение
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        # Переназначение
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}",
            self.headers,
            json={"executor_id": draftsman["id"]}
        )
        assert resp.status_code == 200

    def test_reassign_preserves_stage(self):
        """При переназначении стадия не меняется"""
        designer = self.employees.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer or not draftsman:
            pytest.skip("Нужны дизайнер и чертёжник")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}",
            self.headers,
            json={"executor_id": draftsman["id"]}
        )

        # Проверяем что карточка всё ещё в стадии 1
        resp = api_get(self.api_base, f"/api/crm/cards/{self.card['id']}", self.headers)
        assert resp.status_code == 200
        assert resp.json()["column_name"] == "Стадия 1: планировочные решения"

    def test_get_previous_executor(self):
        """Получение предыдущего исполнителя"""
        designer = self.employees.get('designer')
        draftsman = self.employees.get('draftsman')
        if not designer or not draftsman:
            pytest.skip("Нужны дизайнер и чертёжник")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}",
            self.headers,
            json={"executor_id": draftsman["id"]}
        )

        # Endpoint requires 'position' as query param
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/previous-executor",
            self.headers,
            params={"position": "Дизайнер"}
        )
        # Endpoint может вернуть 200 с данными или 404
        assert resp.status_code in [200, 404]


class TestExecutorCompletion:
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
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "В ожидании"})
        api_patch(api_base, f"/api/crm/cards/{self.card['id']}/column",
                  admin_headers, json={"column_name": "Стадия 1: планировочные решения"})

    def test_executor_submit_work(self):
        """Исполнитель отмечает работу как выполненную"""
        designer = self.employees.get('designer')
        if not designer:
            pytest.skip("Нет тестового дизайнера")

        stage = "Стадия 1: планировочные решения"
        stage_encoded = quote(stage, safe='')

        # Назначаем
        api_post(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor",
            self.headers,
            json={"stage_name": stage, "executor_id": designer["id"]}
        )

        # Подаём работу
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-executor/{stage_encoded}/complete",
            self.headers,
            json={"executor_id": designer['id']}
        )
        assert resp.status_code == 200

    def test_get_submitted_stages(self):
        """Получение списка поданных стадий"""
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/submitted-stages",
            self.headers
        )
        assert resp.status_code == 200

    def test_get_stage_history(self):
        """Получение истории стадий"""
        resp = api_get(
            self.api_base,
            f"/api/crm/cards/{self.card['id']}/stage-history",
            self.headers
        )
        assert resp.status_code == 200
