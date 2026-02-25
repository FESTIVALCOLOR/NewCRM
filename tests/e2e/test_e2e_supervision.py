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


# ==============================================================
# КЛЮЧИ КАРТОЧКИ НАДЗОРА
# ==============================================================

@pytest.mark.e2e
class TestSupervisionCardKeys:
    """Проверка структуры ключей карточки надзора"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_card_list_keys(self):
        """GET /api/supervision/cards — проверка ключей карточки в списке"""
        resp = api_get(self.api_base, "/api/supervision/cards", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        if data:
            for item in data[:5]:
                assert "id" in item, "Карточка надзора должна содержать поле 'id'"
                assert "contract_id" in item, "Карточка надзора должна содержать поле 'contract_id'"
                assert "column_name" in item, "Карточка надзора должна содержать поле 'column_name'"
                assert "is_paused" in item, "Карточка надзора должна содержать поле 'is_paused'"
                assert "total_pause_days" in item, "Карточка надзора должна содержать поле 'total_pause_days'"
                assert "address" in item, "Карточка надзора в списке должна содержать поле 'address'"
                assert "contract_number" in item, "Карточка надзора должна содержать поле 'contract_number'"

    def test_card_detail_keys(self):
        """GET /api/supervision/cards/{id} — проверка ключей одной карточки"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()

        required_keys = [
            "id", "contract_id", "column_name", "deadline", "tags",
            "senior_manager_id", "dan_id", "dan_completed",
            "is_paused", "pause_reason", "paused_at", "total_pause_days",
            "created_at", "updated_at"
        ]
        for key in required_keys:
            assert key in data, f"Карточка надзора должна содержать ключ '{key}'"

    def test_card_created_with_default_values(self):
        """Карточка надзора создаётся с корректными значениями по умолчанию"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        assert card["is_paused"] is False, "Новая карточка не должна быть на паузе"
        assert card["dan_completed"] is False, "Новая карточка: dan_completed = False"
        assert card["total_pause_days"] == 0, "Новая карточка: total_pause_days = 0"
        assert card["column_name"] == "Новый заказ", "Новая карточка в колонке 'Новый заказ'"


# ==============================================================
# ФИЛЬТРАЦИЯ НАДЗОРА ПО СТАТУСУ
# ==============================================================

@pytest.mark.e2e
class TestSupervisionFiltering:
    """Тесты фильтрации карточек надзора"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers):
        self.api_base = api_base
        self.headers = admin_headers

    def test_filter_active_cards(self):
        """GET /api/supervision/cards?status=active — только активные карточки"""
        resp = api_get(
            self.api_base,
            "/api/supervision/cards",
            self.headers,
            params={"status": "active"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        # Активные карточки должны иметь contract_status = 'АВТОРСКИЙ НАДЗОР'
        for item in data[:5]:
            if "contract_status" in item:
                assert item["contract_status"] == "АВТОРСКИЙ НАДЗОР", (
                    f"Активная карточка должна иметь contract_status='АВТОРСКИЙ НАДЗОР', "
                    f"получили '{item['contract_status']}'"
                )

    def test_filter_archived_cards(self):
        """GET /api/supervision/cards?status=archived — только архивные карточки"""
        resp = api_get(
            self.api_base,
            "/api/supervision/cards",
            self.headers,
            params={"status": "archived"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        archived_statuses = {"СДАН", "РАСТОРГНУТ"}
        for item in data[:5]:
            if "contract_status" in item and item["contract_status"]:
                assert item["contract_status"] in archived_statuses, (
                    f"Архивная карточка должна иметь статус из {archived_statuses}, "
                    f"получили '{item['contract_status']}'"
                )

    def test_filter_by_city(self, module_factory):
        """GET /api/supervision/cards?city=... — фильтрация по городу"""
        # Создаём карточку с конкретным городом (дефолт в conftest — "СПБ")
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"], city="СПБ")
        module_factory.create_supervision_card(contract["id"])

        resp = api_get(
            self.api_base,
            "/api/supervision/cards",
            self.headers,
            params={"city": "СПБ"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for item in data[:10]:
            assert item.get("city") == "СПБ", (
                f"Фильтр по городу вернул карточку с city='{item.get('city')}'"
            )

    def test_filter_with_pagination(self):
        """GET /api/supervision/cards?skip=0&limit=5 — пагинация"""
        resp = api_get(
            self.api_base,
            "/api/supervision/cards",
            self.headers,
            params={"skip": 0, "limit": 5}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) <= 5, "Лимит пагинации не соблюдён"


# ==============================================================
# ИСТОРИЯ НАДЗОРА — КЛЮЧИ И ИНВАРИАНТЫ
# ==============================================================

@pytest.mark.e2e
class TestSupervisionHistoryKeys:
    """Проверка структуры истории надзора"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_history_entry_keys(self):
        """Запись истории содержит все обязательные ключи"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        # Добавляем запись
        post_resp = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers,
            json={"entry_type": "note", "message": f"{TEST_PREFIX} тестовая запись"}
        )
        assert post_resp.status_code == 200
        entry = post_resp.json()

        required_keys = ["id", "supervision_card_id", "entry_type", "message", "created_at"]
        for key in required_keys:
            assert key in entry, f"Запись истории должна содержать ключ '{key}'"

        assert entry["supervision_card_id"] == card["id"]
        assert entry["entry_type"] == "note"

    def test_history_records_pause_event(self):
        """Пауза карточки создаёт запись в истории типа 'pause'"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        # Ставим на паузу
        api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/pause",
            self.headers,
            json={"pause_reason": "Тест истории паузы"}
        )

        # Получаем историю
        resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        pause_entries = [e for e in data if e.get("entry_type") == "pause"]
        assert len(pause_entries) >= 1, "В истории должна быть запись о паузе"

    def test_history_records_column_move(self):
        """Перемещение колонки записывается в историю"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        # Перемещаем карточку
        api_patch(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/column",
            self.headers,
            json={"column_name": "В ожидании"}
        )

        # Получаем историю
        resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/history",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        move_entries = [e for e in data if e.get("entry_type") == "card_moved"]
        assert len(move_entries) >= 1, "В истории должна быть запись о перемещении"


# ==============================================================
# ДОПОЛНИТЕЛЬНЫЕ ENDPOINT'Ы НАДЗОРА
# ==============================================================

@pytest.mark.e2e
class TestSupervisionAdditionalEndpoints:
    """Дополнительные эндпоинты надзора"""

    @pytest.fixture(autouse=True)
    def setup(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory

    def test_get_nonexistent_card_returns_404(self):
        """GET /api/supervision/cards/999999 — несуществующая карточка возвращает 404"""
        resp = api_get(
            self.api_base,
            "/api/supervision/cards/999999",
            self.headers
        )
        assert resp.status_code == 404

    def test_addresses_list_is_strings(self):
        """GET /api/supervision/addresses — список строк-адресов"""
        resp = api_get(self.api_base, "/api/supervision/addresses", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        for addr in data[:10]:
            assert isinstance(addr, str), f"Адрес должен быть строкой, получили: {type(addr)}"

    def test_complete_stage_sets_dan_completed(self):
        """POST /api/supervision/cards/{id}/complete-stage — устанавливает dan_completed=True"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/complete-stage",
            self.headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data
        assert data["status"] == "success"

        # Проверяем что dan_completed изменился
        get_resp = api_get(
            self.api_base,
            f"/api/supervision/cards/{card['id']}",
            self.headers
        )
        assert get_resp.status_code == 200
        assert get_resp.json()["dan_completed"] is True

    def test_invalid_column_move_returns_422(self):
        """PATCH /api/supervision/cards/{id}/column — недопустимая колонка возвращает 422"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        resp = api_patch(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/column",
            self.headers,
            json={"column_name": "Несуществующая колонка"}
        )
        assert resp.status_code == 422

    def test_pause_already_paused_card_returns_422(self):
        """POST /api/supervision/cards/{id}/pause дважды — второй раз возвращает 422"""
        client = self.factory.create_client()
        contract = self.factory.create_contract(client["id"])
        card = self.factory.create_supervision_card(contract["id"])

        # Первая пауза
        resp1 = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/pause",
            self.headers,
            json={"pause_reason": "Первая пауза"}
        )
        assert resp1.status_code == 200

        # Вторая пауза — должна вернуть 422
        resp2 = api_post(
            self.api_base,
            f"/api/supervision/cards/{card['id']}/pause",
            self.headers,
            json={"pause_reason": "Повторная пауза"}
        )
        assert resp2.status_code == 422
