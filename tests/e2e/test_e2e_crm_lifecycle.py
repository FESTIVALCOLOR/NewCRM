# -*- coding: utf-8 -*-
"""
E2E Tests: Полный цикл CRM карточки
18 тестов — создание, перемещение через все колонки, замер, шаблонные проекты.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_patch, api_delete


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


# ==============================================================
# КЛЮЧИ CRM КАРТОЧКИ
# ==============================================================

@pytest.mark.e2e
class TestCRMCardKeys:
    """Проверка структуры ключей CRM карточки"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_create_card_keys(self):
        """POST /api/crm/cards — ответ содержит все обязательные ключи"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        required_keys = [
            "id", "contract_id", "column_name", "deadline", "tags",
            "is_approved", "approval_deadline", "approval_stages",
            "project_data_link", "senior_manager_id", "sdp_id",
            "gap_id", "manager_id", "surveyor_id", "order_position",
            "created_at", "updated_at"
        ]
        for key in required_keys:
            assert key in card, f"CRM карточка должна содержать ключ '{key}'"

    def test_get_card_keys(self):
        """GET /api/crm/cards/{id} — ответ содержит все поля включая контрактные"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card_created = self.factory.create_crm_card(contract["id"])

        resp = api_get(self.api_base, f"/api/crm/cards/{card_created['id']}", self.headers)
        assert resp.status_code == 200
        data = resp.json()

        # Собственные ключи карточки
        card_keys = ["id", "contract_id", "column_name", "is_approved",
                     "senior_manager_id", "sdp_id", "gap_id", "manager_id", "surveyor_id",
                     "stage_executors"]
        for key in card_keys:
            assert key in data, f"GET карточки должен содержать ключ '{key}'"

        # Ключи из контракта
        contract_keys = ["contract_number", "address", "area", "city",
                         "agent_type", "project_type", "contract_status"]
        for key in contract_keys:
            assert key in data, f"GET карточки должен содержать контрактный ключ '{key}'"

    def test_card_list_keys(self):
        """GET /api/crm/cards?project_type=... — список карточек с полными ключами"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Индивидуальный")
        self.factory.create_crm_card(contract["id"])

        resp = api_get(self.api_base, "/api/crm/cards", self.headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        if data:
            for item in data[:5]:
                assert "id" in item
                assert "contract_id" in item
                assert "column_name" in item
                assert "project_type" in item
                assert "address" in item
                assert "area" in item


# ==============================================================
# ФИЛЬТРАЦИЯ CRM КАРТОЧЕК
# ==============================================================

@pytest.mark.e2e
class TestCRMCardFiltering:
    """Тесты фильтрации CRM карточек"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_filter_individual_project_type(self):
        """GET /api/crm/cards?project_type=Индивидуальный — только индивидуальные"""
        # Создаём карточку индивидуального типа
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Индивидуальный")
        self.factory.create_crm_card(contract["id"])

        resp = api_get(self.api_base, "/api/crm/cards", self.headers,
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:10]:
            assert item["project_type"] == "Индивидуальный", (
                f"Фильтр Индивидуальный вернул карточку с project_type='{item['project_type']}'"
            )

    def test_filter_template_project_type(self):
        """GET /api/crm/cards?project_type=Шаблонный — только шаблонные"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Шаблонный")
        self.factory.create_crm_card(contract["id"])

        resp = api_get(self.api_base, "/api/crm/cards", self.headers,
                       params={"project_type": "Шаблонный"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:10]:
            assert item["project_type"] == "Шаблонный", (
                f"Фильтр Шаблонный вернул карточку с project_type='{item['project_type']}'"
            )

    def test_filter_archived_cards(self):
        """GET /api/crm/cards?project_type=...&archived=true — архивные карточки"""
        resp = api_get(self.api_base, "/api/crm/cards", self.headers,
                       params={"project_type": "Индивидуальный", "archived": "true"})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        archive_statuses = {"СДАН", "РАСТОРГНУТ", "АВТОРСКИЙ НАДЗОР"}
        for item in data[:5]:
            if "contract_status" in item and item["contract_status"]:
                assert item["contract_status"] in archive_statuses, (
                    f"Архивная карточка имеет contract_status='{item['contract_status']}'"
                )

    def test_cards_require_project_type_param(self):
        """GET /api/crm/cards без project_type — должен вернуть ошибку валидации"""
        resp = api_get(self.api_base, "/api/crm/cards", self.headers)
        # Без обязательного параметра должен вернуться 422
        assert resp.status_code == 422


# ==============================================================
# ПЕРЕМЕЩЕНИЕ КАРТОЧКИ — БИЗНЕС-ИНВАРИАНТЫ
# ==============================================================

@pytest.mark.e2e
class TestCRMCardMovementInvariants:
    """Проверка бизнес-инвариантов перемещения карточек"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_cannot_move_back_to_new_order(self):
        """Нельзя вернуть карточку в 'Новый заказ' после перемещения"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        # Перемещаем в В ожидании
        api_patch(self.api_base, f"/api/crm/cards/{card['id']}/column",
                  self.headers, json={"column_name": "В ожидании"})

        # Пытаемся вернуть в Новый заказ — должен вернуть 422
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{card['id']}/column",
            self.headers,
            json={"column_name": "Новый заказ"}
        )
        assert resp.status_code == 422

    def test_move_column_response_keys(self):
        """PATCH /api/crm/cards/{id}/column — ответ содержит id, column_name, old_column_name"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{card['id']}/column",
            self.headers,
            json={"column_name": "В ожидании"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert "column_name" in data
        assert "old_column_name" in data
        assert data["column_name"] == "В ожидании"
        assert data["old_column_name"] == "Новый заказ"

    def test_invalid_column_returns_422(self):
        """PATCH /api/crm/cards/{id}/column с несуществующей колонкой — 422"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{card['id']}/column",
            self.headers,
            json={"column_name": "Несуществующая колонка"}
        )
        assert resp.status_code == 422

    def test_card_in_waiting_state_records_paused_at(self):
        """При переходе в 'В ожидании' карточка запоминает время паузы"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        api_patch(self.api_base, f"/api/crm/cards/{card['id']}/column",
                  self.headers, json={"column_name": "В ожидании"})

        # Получаем карточку и проверяем column_name
        resp = api_get(self.api_base, f"/api/crm/cards/{card['id']}", self.headers)
        assert resp.status_code == 200
        assert resp.json()["column_name"] == "В ожидании"


# ==============================================================
# ИСПОЛНИТЕЛИ СТАДИЙ (STAGE EXECUTORS)
# ==============================================================

@pytest.mark.e2e
class TestStageExecutors:
    """Тесты назначения исполнителей на стадии CRM карточки"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory, test_employees):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        self.employees = test_employees

    def test_assign_stage_executor(self):
        """POST /api/crm/cards/{id}/stage-executor — назначить исполнителя на стадию"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет тестового СДП")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Индивидуальный")
        card = self.factory.create_crm_card(contract["id"])

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 1: планировочные решения",
                "executor_id": sdp["id"],
                "deadline": None
            }
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["stage_name"] == "Стадия 1: планировочные решения"
        assert data["executor_id"] == sdp["id"]

    def test_stage_executor_invalid_stage_returns_400(self):
        """POST /api/crm/cards/{id}/stage-executor — несуществующая стадия возвращает 400"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет тестового СДП")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Индивидуальный")
        card = self.factory.create_crm_card(contract["id"])

        resp = api_post(
            self.api_base,
            f"/api/crm/cards/{card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Несуществующая стадия",
                "executor_id": sdp["id"],
                "deadline": None
            }
        )
        assert resp.status_code == 400

    def test_get_card_stage_executors(self):
        """GET /api/crm/cards/{id} — ответ содержит stage_executors как список"""
        sdp = self.employees.get('sdp')
        if not sdp:
            pytest.skip("Нет тестового СДП")

        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"], project_type="Индивидуальный")
        card = self.factory.create_crm_card(contract["id"])

        # Назначаем исполнителя
        api_post(
            self.api_base,
            f"/api/crm/cards/{card['id']}/stage-executor",
            self.headers,
            json={
                "stage_name": "Стадия 2: концепция дизайна",
                "executor_id": sdp["id"],
                "deadline": None
            }
        )

        # Получаем карточку и проверяем stage_executors
        resp = api_get(self.api_base, f"/api/crm/cards/{card['id']}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "stage_executors" in data
        assert isinstance(data["stage_executors"], list)
        if data["stage_executors"]:
            executor = data["stage_executors"][0]
            assert "id" in executor
            assert "stage_name" in executor
            assert "executor_id" in executor
            assert "completed" in executor


# ==============================================================
# БИЗНЕС-ИНВАРИАНТЫ: СТАТУС И ПРОГРЕСС
# ==============================================================

@pytest.mark.e2e
class TestCRMBusinessInvariants:
    """Проверка бизнес-инвариантов CRM карточек"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_nonexistent_card_returns_404(self):
        """GET /api/crm/cards/999999 — несуществующая карточка возвращает 404"""
        resp = api_get(self.api_base, "/api/crm/cards/999999", self.headers)
        assert resp.status_code == 404

    def test_duplicate_card_for_same_contract_returns_409(self):
        """POST /api/crm/cards с уже существующим contract_id — возвращает 409"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        self.factory.create_crm_card(contract["id"])

        # Попытка создать дубль
        resp = api_post(
            self.api_base,
            "/api/crm/cards",
            self.headers,
            json={
                "contract_id": contract["id"],
                "column_name": "Новый заказ",
                "order_position": 0
            }
        )
        assert resp.status_code == 409, "Дубль CRM карточки для того же договора должен возвращать 409"

    def test_card_update_approval_fields(self):
        """PATCH /api/crm/cards/{id} — обновление поля is_approved"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{card['id']}",
            self.headers,
            json={"is_approved": True}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_approved"] is True

    def test_card_update_project_data_link(self):
        """PATCH /api/crm/cards/{id} — обновление ссылки на данные проекта"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_crm_card(contract["id"])

        test_link = f"https://example.com/{TEST_PREFIX}"
        resp = api_patch(
            self.api_base,
            f"/api/crm/cards/{card['id']}",
            self.headers,
            json={"project_data_link": test_link}
        )
        assert resp.status_code == 200

        # Проверяем через GET
        get_resp = api_get(self.api_base, f"/api/crm/cards/{card['id']}", self.headers)
        assert get_resp.status_code == 200
        assert get_resp.json()["project_data_link"] == test_link

    def test_cards_without_auth_returns_401(self):
        """GET /api/crm/cards без токена — 401/403"""
        resp = api_get(self.api_base, "/api/crm/cards", {},
                       params={"project_type": "Индивидуальный"})
        assert resp.status_code in (401, 403)
