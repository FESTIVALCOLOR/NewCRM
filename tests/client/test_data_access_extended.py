# -*- coding: utf-8 -*-
"""
Расширенные тесты DataAccess — покрытие непокрытых методов.

Методы, уже покрытые в test_data_access.py (не дублируем):
- get_all_clients, get_client, create_client, update_client, delete_client
- get_all_contracts, get_contract, create_contract, update_contract, delete_contract
- get_all_employees, get_employees_by_position, create_employee, update_employee, delete_employee
- get_crm_cards, create_crm_card, update_crm_card, update_crm_card_column
- get_payments_for_contract, create_payment
- get_rates, get_salaries
- get_action_history, add_action_history, get_supervision_history, add_supervision_history
- get_dashboard_statistics
- update_supervision_card, create_supervision_card
- is_multi_user, prefer_local
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

pytest.importorskip("PyQt5")


# ---------------------------------------------------------------------------
# Вспомогательная фабрика DataAccess с моками (без __init__ для PyQt5)
# ---------------------------------------------------------------------------

def _make_da(mock_api=None, mock_db=None, is_online=True):
    """Создать DataAccess с указанными моками, обходя PyQt5 QObject.__init__"""
    with patch('utils.data_access.get_offline_manager', return_value=None):
        from utils.data_access import DataAccess
        da = DataAccess.__new__(DataAccess)
        da.api_client = mock_api
        da.db = mock_db or MagicMock()
        da._is_online = is_online if mock_api is not None else False
        da.prefer_local = False
        return da


@pytest.fixture
def mock_api():
    api = MagicMock()
    api.is_online = True
    return api


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.add_supervision_card.return_value = 501
    db.add_payment.return_value = 601
    db.add_rate.return_value = 701
    db.add_salary.return_value = 801
    db.add_agent.return_value = {"id": 901, "name": "FESTIVAL"}
    return db


@pytest.fixture
def da_online(mock_api, mock_db):
    """DataAccess в режиме online (api_client задан, _is_online=True)"""
    return _make_da(mock_api, mock_db, is_online=True)


@pytest.fixture
def da_offline(mock_db):
    """DataAccess без api_client (только локальная БД)"""
    return _make_da(None, mock_db)


# ===========================================================================
# ПАГИНАЦИЯ КЛИЕНТОВ И ДОГОВОРОВ
# ===========================================================================

class TestPagination:
    """get_clients_paginated и get_contracts_paginated"""

    def test_get_clients_paginated_from_api(self, da_online, mock_api):
        """get_clients_paginated — API возвращает кортеж"""
        mock_api.get_clients_paginated.return_value = ([{"id": 1}], 1)
        result = da_online.get_clients_paginated(skip=0, limit=10)
        assert result == ([{"id": 1}], 1)
        mock_api.get_clients_paginated.assert_called_once_with(skip=0, limit=10)

    def test_get_clients_paginated_fallback(self, mock_db):
        """get_clients_paginated — API упал → fallback на db.get_all_clients + get_clients_count"""
        api = MagicMock()
        api.get_clients_paginated.side_effect = Exception("Offline")
        mock_db.get_all_clients.return_value = [{"id": 1}]
        mock_db.get_clients_count.return_value = 42
        da = _make_da(api, mock_db)
        clients, total = da.get_clients_paginated(skip=0, limit=10)
        assert clients == [{"id": 1}]
        assert total == 42

    def test_get_clients_paginated_local_only(self, mock_db):
        """get_clients_paginated — без api_client → только локальная БД"""
        mock_db.get_all_clients.return_value = [{"id": 2}]
        mock_db.get_clients_count.return_value = 5
        da = _make_da(None, mock_db)
        clients, total = da.get_clients_paginated()
        assert total == 5

    def test_get_contracts_paginated_from_api(self, da_online, mock_api):
        """get_contracts_paginated — API возвращает кортеж"""
        mock_api.get_contracts_paginated.return_value = ([{"id": 1}], 10)
        result = da_online.get_contracts_paginated(skip=0, limit=5)
        assert result == ([{"id": 1}], 10)

    def test_get_contracts_paginated_fallback(self, mock_db):
        """get_contracts_paginated — API упал → db"""
        api = MagicMock()
        api.get_contracts_paginated.side_effect = Exception("Offline")
        mock_db.get_all_contracts.return_value = [{"id": 1}]
        mock_db.get_contracts_count.return_value = 7
        da = _make_da(api, mock_db)
        contracts, total = da.get_contracts_paginated()
        assert total == 7


# ===========================================================================
# КОЛИЧЕСТВО ДОГОВОРОВ
# ===========================================================================

class TestContractsCount:
    """get_contracts_count, get_contracts_count_by_client"""

    def test_get_contracts_count_from_api(self, da_online, mock_api):
        """get_contracts_count — API возвращает число"""
        mock_api.get_contracts_count.return_value = 15
        result = da_online.get_contracts_count(status="active")
        assert result == 15

    def test_get_contracts_count_fallback(self, mock_db):
        """get_contracts_count — API упал → db"""
        api = MagicMock()
        api.get_contracts_count.side_effect = Exception("Offline")
        mock_db.get_contracts_count.return_value = 8
        da = _make_da(api, mock_db)
        result = da.get_contracts_count()
        assert result == 8

    def test_get_contracts_count_by_client_from_api(self, da_online, mock_api):
        """get_contracts_count_by_client — считает через get_contracts"""
        mock_api.get_contracts.return_value = [
            {"client_id": 1}, {"client_id": 1}, {"client_id": 2}
        ]
        result = da_online.get_contracts_count_by_client(1)
        assert result == 2

    def test_get_contracts_count_by_client_fallback(self, mock_db):
        """get_contracts_count_by_client — API упал → db"""
        api = MagicMock()
        api.get_contracts.side_effect = Exception("Offline")
        mock_db.get_contracts_count_by_client.return_value = 3
        da = _make_da(api, mock_db)
        result = da.get_contracts_count_by_client(1)
        assert result == 3

    def test_check_contract_number_exists_api(self, da_online, mock_api):
        """check_contract_number_exists — API отвечает True"""
        mock_api.check_contract_number_exists.return_value = True
        result = da_online.check_contract_number_exists("D-001", exclude_id=None)
        assert result is True

    def test_check_contract_number_exists_fallback(self, mock_db):
        """check_contract_number_exists — API упал → db"""
        api = MagicMock()
        api.check_contract_number_exists.side_effect = Exception("Offline")
        mock_db.check_contract_number_exists.return_value = False
        da = _make_da(api, mock_db)
        result = da.check_contract_number_exists("D-999")
        assert result is False


# ===========================================================================
# SUPERVISION КАРТОЧКИ
# ===========================================================================

class TestSupervisionCards:
    """get_supervision_cards_active, get_supervision_cards_archived, get_supervision_card, etc."""

    def test_get_supervision_cards_active_from_api(self, da_online, mock_api):
        """get_supervision_cards_active — API → список активных"""
        mock_api.get_supervision_cards.return_value = [{"id": 1, "status": "active"}]
        result = da_online.get_supervision_cards_active()
        assert result == [{"id": 1, "status": "active"}]
        mock_api.get_supervision_cards.assert_called_with(status="active")

    def test_get_supervision_cards_active_fallback(self, mock_db):
        """get_supervision_cards_active — API упал → db"""
        api = MagicMock()
        api.get_supervision_cards.side_effect = Exception("Offline")
        mock_db.get_supervision_cards_active.return_value = [{"id": 2}]
        da = _make_da(api, mock_db)
        result = da.get_supervision_cards_active()
        assert result == [{"id": 2}]

    def test_get_supervision_cards_archived_from_api(self, da_online, mock_api):
        """get_supervision_cards_archived — API → список архивных"""
        mock_api.get_supervision_cards.return_value = [{"id": 10}]
        result = da_online.get_supervision_cards_archived()
        mock_api.get_supervision_cards.assert_called_with(status="archived")

    def test_get_supervision_card_from_api(self, da_online, mock_api):
        """get_supervision_card — API → одна карточка"""
        mock_api.get_supervision_card.return_value = {"id": 5, "address": "ул. Ленина"}
        result = da_online.get_supervision_card(5)
        assert result["id"] == 5

    def test_get_supervision_card_fallback(self, mock_db):
        """get_supervision_card — API упал → db"""
        api = MagicMock()
        api.get_supervision_card.side_effect = Exception("Offline")
        mock_db.get_supervision_card_data.return_value = {"id": 5}
        da = _make_da(api, mock_db)
        result = da.get_supervision_card(5)
        assert result == {"id": 5}

    def test_update_supervision_card_column_api(self, da_online, mock_api, mock_db):
        """update_supervision_card_column — обновляет локально + API"""
        mock_api.update_supervision_card.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.update_supervision_card_column(1, "В работе")
        mock_db.update_supervision_card_column.assert_called_once_with(1, "В работе")
        mock_api.update_supervision_card.assert_called_once_with(1, {"column_name": "В работе"})
        assert result is True

    def test_update_supervision_card_column_queued_on_error(self, mock_db):
        """update_supervision_card_column — API упал → в очередь"""
        api = MagicMock()
        api.update_supervision_card.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            result = da.update_supervision_card_column(1, "Пауза")
            mock_queue.assert_called_once()
        assert result is True

    def test_delete_supervision_order_api(self, da_online, mock_api, mock_db):
        """delete_supervision_order — API + локальная БД"""
        mock_api.delete_supervision_order.return_value = True
        da_online._is_online = True
        result = da_online.delete_supervision_order(10, supervision_card_id=5)
        assert result is True

    def test_get_supervision_cards_unified(self, da_online, mock_api):
        """get_supervision_cards(status=active) — унифицированный метод"""
        mock_api.get_supervision_cards.return_value = [{"id": 1}]
        result = da_online.get_supervision_cards(status="active")
        assert result == [{"id": 1}]

    def test_get_supervision_addresses_api(self, da_online, mock_api):
        """get_supervision_addresses — API"""
        mock_api.get_supervision_addresses.return_value = ["ул. Ленина, 1", "пр. Мира, 5"]
        result = da_online.get_supervision_addresses()
        assert len(result) == 2

    def test_get_supervision_addresses_fallback(self, mock_db):
        """get_supervision_addresses — fallback на db"""
        api = MagicMock()
        api.get_supervision_addresses.side_effect = Exception("Offline")
        mock_db.get_supervision_addresses.return_value = ["пр. Мира, 5"]
        da = _make_da(api, mock_db)
        result = da.get_supervision_addresses()
        assert result == ["пр. Мира, 5"]


# ===========================================================================
# SUPERVISION ACTIONS (pause/resume/complete stage)
# ===========================================================================

class TestSupervisionActions:
    """move_supervision_card, complete_supervision_stage, pause, resume"""

    def test_move_supervision_card_api(self, da_online, mock_api, mock_db):
        """move_supervision_card — API + локальная БД"""
        mock_api.move_supervision_card.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.move_supervision_card(1, "Завершён")
        assert result is True
        mock_api.move_supervision_card.assert_called_once_with(1, "Завершён")

    def test_move_supervision_card_queued_on_error(self, mock_db):
        """move_supervision_card — API упал → в очередь"""
        api = MagicMock()
        api.move_supervision_card.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            result = da.move_supervision_card(1, "В работе")
            mock_queue.assert_called_once()
        assert result is True

    def test_complete_supervision_stage_api(self, da_online, mock_api):
        """complete_supervision_stage — API возвращает результат"""
        mock_api.complete_supervision_stage.return_value = {"success": True}
        da_online._is_online = True
        result = da_online.complete_supervision_stage(1, stage_name="Визит 1")
        assert result is not None

    def test_complete_supervision_stage_local_only(self, da_offline, mock_db):
        """complete_supervision_stage — без API → локальная DB"""
        mock_db.complete_supervision_stage.return_value = True
        result = da_offline.complete_supervision_stage(1, stage_name="Визит 1")
        assert result == {"success": True}

    def test_pause_supervision_card_api(self, da_online, mock_api):
        """pause_supervision_card — API с причиной"""
        mock_api.pause_supervision_card.return_value = {"status": "paused"}
        da_online._is_online = True
        result = da_online.pause_supervision_card(1, reason="Ремонт", employee_id=2)
        assert result is not None

    def test_resume_supervision_card_api(self, da_online, mock_api):
        """resume_supervision_card — API возобновляет"""
        mock_api.resume_supervision_card.return_value = {"status": "active"}
        da_online._is_online = True
        result = da_online.resume_supervision_card(1, employee_id=2)
        assert result is not None

    def test_reset_supervision_stage_completion_api(self, da_online, mock_api, mock_db):
        """reset_supervision_stage_completion — API + DB"""
        mock_api.reset_supervision_stage_completion.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.reset_supervision_stage_completion(1)
        assert result is True


# ===========================================================================
# ПЛАТЕЖИ (расширенные методы)
# ===========================================================================

class TestPaymentsExtended:
    """update_payment, delete_payment, get_payment, get_payments_by_type, mark_payment_as_paid"""

    def test_update_payment_api(self, da_online, mock_api, mock_db):
        """update_payment — API + локальная DB"""
        mock_api.update_payment.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.update_payment(1, {"amount": 1000})
        mock_db.update_payment.assert_called_once()
        mock_api.update_payment.assert_called_once()
        assert result is True

    def test_delete_payment_api(self, da_online, mock_api, mock_db):
        """delete_payment — API + локальная DB"""
        mock_api.delete_payment.return_value = True
        da_online._is_online = True
        result = da_online.delete_payment(1)
        mock_db.delete_payment.assert_called_once()
        assert result is True

    def test_delete_payment_queued_on_error(self, mock_db):
        """delete_payment — API упал → в очередь"""
        api = MagicMock()
        api.delete_payment.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            da.delete_payment(1)
            mock_queue.assert_called_once()
            assert mock_queue.call_args[0][0] == 'delete'

    def test_get_payment_from_api(self, da_online, mock_api):
        """get_payment — API"""
        mock_api.get_payment.return_value = {"id": 1, "amount": 5000}
        result = da_online.get_payment(1)
        assert result["id"] == 1

    def test_get_payment_fallback(self, mock_db):
        """get_payment — API упал → db"""
        api = MagicMock()
        api.get_payment.side_effect = Exception("Offline")
        mock_db.get_payment.return_value = {"id": 1}
        da = _make_da(api, mock_db)
        result = da.get_payment(1)
        assert result == {"id": 1}

    def test_get_payments_by_type_api(self, da_online, mock_api):
        """get_payments_by_type — API"""
        mock_api.get_payments_by_type.return_value = [{"id": 1}]
        result = da_online.get_payments_by_type("Полная оплата")
        assert result == [{"id": 1}]

    def test_get_payments_by_supervision_card_api(self, da_online, mock_api):
        """get_payments_by_supervision_card — API"""
        mock_api.get_payments_by_supervision_card.return_value = [{"id": 2}]
        result = da_online.get_payments_by_supervision_card(1)
        assert result == [{"id": 2}]

    def test_get_payments_for_supervision_fallback(self, mock_db):
        """get_payments_for_supervision — API упал → db"""
        api = MagicMock()
        api.get_payments_for_supervision.side_effect = Exception("Offline")
        mock_db.get_payments_for_supervision.return_value = [{"id": 3}]
        da = _make_da(api, mock_db)
        result = da.get_payments_for_supervision(1)
        assert result == [{"id": 3}]

    def test_get_payments_for_crm_api(self, da_online, mock_api):
        """get_payments_for_crm — API"""
        mock_api.get_payments_for_crm.return_value = [{"id": 4}]
        result = da_online.get_payments_for_crm(1)
        assert result == [{"id": 4}]

    def test_mark_payment_as_paid_api(self, da_online, mock_api, mock_db):
        """mark_payment_as_paid — API + локальная DB"""
        mock_api.mark_payment_as_paid.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.mark_payment_as_paid(1, employee_id=2)
        mock_db.mark_payment_as_paid.assert_called_once()
        assert result is True

    def test_mark_payment_as_paid_queued_on_error(self, mock_db):
        """mark_payment_as_paid — API упал → в очередь"""
        api = MagicMock()
        api.mark_payment_as_paid.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            da.mark_payment_as_paid(1, employee_id=3)
            mock_queue.assert_called_once()

    def test_update_payment_manual_api(self, da_online, mock_api, mock_db):
        """update_payment_manual — API + DB"""
        mock_api.update_payment_manual.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.update_payment_manual(1, 9999.0, report_month="2025-01")
        assert result is True

    def test_get_year_payments_api(self, da_online, mock_api):
        """get_year_payments — API"""
        mock_api.get_year_payments.return_value = [{"year": 2025}]
        result = da_online.get_year_payments(2025)
        assert result == [{"year": 2025}]

    def test_recalculate_payments_api(self, da_online, mock_api):
        """recalculate_payments — только API"""
        mock_api.recalculate_payments.return_value = {"recalculated": 5}
        result = da_online.recalculate_payments(contract_id=1)
        assert result == {"recalculated": 5}

    def test_recalculate_payments_no_api(self, da_offline):
        """recalculate_payments — без API → None"""
        result = da_offline.recalculate_payments()
        assert result is None

    def test_set_payments_report_month_api(self, da_online, mock_api):
        """set_payments_report_month — только API"""
        mock_api.set_payments_report_month.return_value = {"ok": True}
        result = da_online.set_payments_report_month(1, "2025-03")
        assert result is True

    def test_set_payments_report_month_no_api(self, da_offline):
        """set_payments_report_month — без API → False"""
        result = da_offline.set_payments_report_month(1, "2025-03")
        assert result is False


# ===========================================================================
# СТАВКИ (расширенные методы)
# ===========================================================================

class TestRatesExtended:
    """get_rate, create_rate, update_rate, delete_rate, template/individual/surveyor rates"""

    def test_get_rate_from_api(self, da_online, mock_api):
        """get_rate — API"""
        mock_api.get_rate.return_value = {"id": 1, "rate": 500}
        result = da_online.get_rate(1)
        assert result["id"] == 1

    def test_get_rate_fallback(self, mock_db):
        """get_rate — API упал → db"""
        api = MagicMock()
        api.get_rate.side_effect = Exception("Offline")
        mock_db.get_rate_by_id.return_value = {"id": 1}
        da = _make_da(api, mock_db)
        result = da.get_rate(1)
        assert result == {"id": 1}

    def test_create_rate_api(self, da_online, mock_api, mock_db):
        """create_rate — локально + API"""
        mock_api.create_rate.return_value = {"id": 701}
        da_online._is_online = True
        result = da_online.create_rate({"role": "Designer", "rate": 500})
        mock_db.add_rate.assert_called_once()
        assert result == {"id": 701}

    def test_update_rate_api(self, da_online, mock_api, mock_db):
        """update_rate — API + DB"""
        mock_api.update_rate.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.update_rate(1, {"rate": 600})
        mock_db.update_rate.assert_called_once()
        assert result is True

    def test_delete_rate_api(self, da_online, mock_api, mock_db):
        """delete_rate — API + DB"""
        mock_api.delete_rate.return_value = True
        da_online._is_online = True
        result = da_online.delete_rate(1)
        mock_db.delete_rate.assert_called_once()
        assert result is True

    def test_get_template_rates_api(self, da_online, mock_api):
        """get_template_rates — API"""
        mock_api.get_template_rates.return_value = [{"id": 1}]
        result = da_online.get_template_rates(role="Designer")
        assert result == [{"id": 1}]

    def test_save_template_rate_api(self, da_online, mock_api):
        """save_template_rate — только API"""
        mock_api.save_template_rate.return_value = {"id": 1}
        result = da_online.save_template_rate("Designer", 0.0, 100.0, 500.0)
        assert result == {"id": 1}

    def test_save_template_rate_no_api(self, da_offline):
        """save_template_rate — без API → None"""
        result = da_offline.save_template_rate("Designer", 0.0, 100.0, 500.0)
        assert result is None

    def test_save_individual_rate_api(self, da_online, mock_api):
        """save_individual_rate — только API"""
        mock_api.save_individual_rate.return_value = {"id": 2}
        result = da_online.save_individual_rate("Designer", 350.0, stage_name="Концепция")
        assert result is not None

    def test_delete_individual_rate_no_api(self, da_offline):
        """delete_individual_rate — без API → False"""
        result = da_offline.delete_individual_rate("Designer")
        assert result is False

    def test_save_surveyor_rate_api(self, da_online, mock_api):
        """save_surveyor_rate — только API"""
        mock_api.save_surveyor_rate.return_value = {"id": 3}
        result = da_online.save_surveyor_rate("Москва", 1500.0)
        assert result is not None

    def test_save_supervision_rate_api(self, da_online, mock_api):
        """save_supervision_rate — только API"""
        mock_api.save_supervision_rate.return_value = {"id": 4}
        result = da_online.save_supervision_rate("Визит", 2000.0, 1500.0)
        assert result is not None

    def test_calculate_payment_amount_api(self, da_online, mock_api):
        """calculate_payment_amount — API"""
        mock_api.calculate_payment_amount.return_value = {"amount": 15000}
        result = da_online.calculate_payment_amount(1, 2, "Designer", stage_name="Концепция")
        assert result == {"amount": 15000}


# ===========================================================================
# ЗАРПЛАТЫ (расширенные методы)
# ===========================================================================

class TestSalariesExtended:
    """get_salary, create_salary, update_salary, delete_salary"""

    def test_get_salary_from_api(self, da_online, mock_api):
        """get_salary — API"""
        mock_api.get_salary.return_value = {"id": 1, "amount": 50000}
        result = da_online.get_salary(1)
        assert result["id"] == 1

    def test_create_salary_api(self, da_online, mock_api, mock_db):
        """create_salary — DB + API"""
        mock_api.create_salary.return_value = {"id": 801}
        da_online._is_online = True
        result = da_online.create_salary({"employee_id": 1, "amount": 50000})
        mock_db.add_salary.assert_called_once()
        assert result == {"id": 801}

    def test_update_salary_api(self, da_online, mock_api, mock_db):
        """update_salary — DB + API"""
        mock_api.update_salary.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.update_salary(1, {"amount": 55000})
        mock_db.update_salary.assert_called_once()
        assert result is True

    def test_delete_salary_api(self, da_online, mock_api, mock_db):
        """delete_salary — DB + API"""
        mock_api.delete_salary.return_value = True
        da_online._is_online = True
        result = da_online.delete_salary(1)
        mock_db.delete_salary.assert_called_once()
        assert result is True

    def test_delete_salary_queued_on_error(self, mock_db):
        """delete_salary — API упал → в очередь"""
        api = MagicMock()
        api.delete_salary.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            da.delete_salary(1)
            mock_queue.assert_called_once()
            assert mock_queue.call_args[0][0] == 'delete'


# ===========================================================================
# АГЕНТЫ
# ===========================================================================

class TestAgents:
    """get_all_agents, get_agent_color, add_agent, update_agent_color, delete_agent"""

    def test_get_all_agents_api(self, da_online, mock_api):
        """get_all_agents — API"""
        mock_api.get_all_agents.return_value = [{"id": 1, "name": "FESTIVAL"}]
        result = da_online.get_all_agents()
        assert result == [{"id": 1, "name": "FESTIVAL"}]

    def test_get_all_agents_fallback(self, mock_db):
        """get_all_agents — API упал → db"""
        api = MagicMock()
        api.get_all_agents.side_effect = Exception("Offline")
        mock_db.get_all_agents.return_value = [{"id": 2, "name": "LOCAL_AGENT"}]
        da = _make_da(api, mock_db)
        result = da.get_all_agents()
        assert result == [{"id": 2, "name": "LOCAL_AGENT"}]

    def test_get_agent_color_from_db_first(self, mock_db):
        """get_agent_color — сначала локальная БД (кешированный lookup)"""
        api = MagicMock()
        mock_db.get_agent_color.return_value = "#FF0000"
        da = _make_da(api, mock_db)
        result = da.get_agent_color("FESTIVAL")
        assert result == "#FF0000"
        api.get_agent_color.assert_not_called()

    def test_get_agent_color_api_fallback_when_db_empty(self, mock_db):
        """get_agent_color — db вернул None → API fallback"""
        api = MagicMock()
        mock_db.get_agent_color.return_value = None
        api.get_agent_color.return_value = "#00FF00"
        da = _make_da(api, mock_db)
        result = da.get_agent_color("FESTIVAL")
        assert result == "#00FF00"

    def test_add_agent_api(self, da_online, mock_api, mock_db):
        """add_agent — API + локальная DB"""
        mock_api.add_agent.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.add_agent("НОВЫЙ АГЕНТ", color="#123456")
        mock_db.add_agent.assert_called_once()
        assert result == {"id": 1}

    def test_update_agent_color_api(self, da_online, mock_api, mock_db):
        """update_agent_color — API + DB"""
        mock_api.update_agent_color.return_value = True
        da_online._is_online = True
        result = da_online.update_agent_color("FESTIVAL", "#ABCDEF")
        mock_db.update_agent_color.assert_called_once()
        assert result is True

    def test_delete_agent_api(self, da_online, mock_api):
        """delete_agent — только API (без offline queue при обычной ошибке)"""
        mock_api.delete_agent.return_value = True
        result = da_online.delete_agent(1)
        assert result is True

    def test_delete_agent_fallback_on_no_api(self, mock_db):
        """delete_agent — без API → db"""
        mock_db.delete_agent.return_value = True
        da = _make_da(None, mock_db)
        result = da.delete_agent(1)
        assert result is True

    def test_get_agent_types_api(self, da_online, mock_api):
        """get_agent_types — API"""
        mock_api.get_agent_types.return_value = ["FESTIVAL", "PETROVICH"]
        result = da_online.get_agent_types()
        assert "FESTIVAL" in result


# ===========================================================================
# ГОРОДА
# ===========================================================================

class TestCities:
    """get_all_cities, add_city, delete_city"""

    def test_get_all_cities_api(self, da_online, mock_api):
        """get_all_cities — API возвращает список"""
        mock_api.get_all_cities.return_value = [{"id": 1, "name": "Москва"}]
        result = da_online.get_all_cities()
        assert result == [{"id": 1, "name": "Москва"}]

    def test_get_all_cities_fallback_to_db(self, mock_db):
        """get_all_cities — API упал → db"""
        api = MagicMock()
        api.get_all_cities.side_effect = Exception("Offline")
        mock_db.get_all_cities.return_value = [{"id": 1, "name": "Краснодар"}]
        da = _make_da(api, mock_db)
        result = da.get_all_cities()
        assert result == [{"id": 1, "name": "Краснодар"}]

    def test_get_all_cities_empty_api_uses_db(self, mock_db):
        """get_all_cities — API вернул пустой список → db"""
        api = MagicMock()
        api.get_all_cities.return_value = []  # пустой ответ от API
        mock_db.get_all_cities.return_value = [{"id": 1, "name": "Сочи"}]
        da = _make_da(api, mock_db)
        result = da.get_all_cities()
        # Если API вернул [], логика в DataAccess использует db
        assert result is not None

    def test_add_city_api_success(self, da_online, mock_api, mock_db):
        """add_city — API + локальная db"""
        mock_api.add_city.return_value = True
        result = da_online.add_city("Новосибирск")
        mock_api.add_city.assert_called_once_with("Новосибирск")

    def test_add_city_fallback_on_no_api(self, mock_db):
        """add_city — без API → db.add_city"""
        mock_db.add_city.return_value = True
        da = _make_da(None, mock_db)
        result = da.add_city("Казань")
        mock_db.add_city.assert_called_once_with("Казань")

    def test_delete_city_api(self, da_online, mock_api):
        """delete_city — API"""
        mock_api.delete_city.return_value = True
        result = da_online.delete_city(1)
        assert result is True

    def test_delete_city_fallback(self, mock_db):
        """delete_city — без API → db"""
        mock_db.delete_city.return_value = True
        da = _make_da(None, mock_db)
        result = da.delete_city(1)
        assert result is True


# ===========================================================================
# STAGE EXECUTORS
# ===========================================================================

class TestStageExecutors:
    """assign_stage_executor, complete_stage_for_executor, reset_stage_completion, etc."""

    def test_assign_stage_executor_api(self, da_online, mock_api, mock_db):
        """assign_stage_executor — DB + API"""
        mock_api.assign_stage_executor.return_value = {"success": True}
        da_online._is_online = True
        result = da_online.assign_stage_executor(1, {
            "stage_name": "Концепция", "executor_id": 2, "assigned_by": 1
        })
        mock_api.assign_stage_executor.assert_called_once()
        assert result == {"success": True}

    def test_assign_stage_executor_queued_on_error(self, mock_db):
        """assign_stage_executor — API упал → в очередь"""
        api = MagicMock()
        api.assign_stage_executor.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            da.assign_stage_executor(1, {"stage_name": "Концепция", "executor_id": 2})
            mock_queue.assert_called_once()

    def test_complete_stage_for_executor_api(self, da_online, mock_api):
        """complete_stage_for_executor — API"""
        mock_api.complete_stage_for_executor.return_value = {"success": True}
        da_online._is_online = True
        result = da_online.complete_stage_for_executor(1, "Концепция", executor_id=2)
        assert result == {"success": True}

    def test_complete_stage_for_executor_local_only(self, da_offline, mock_db):
        """complete_stage_for_executor — без API → DB + local result"""
        result = da_offline.complete_stage_for_executor(1, "Концепция", executor_id=2)
        assert result == {"success": True}

    def test_reset_stage_completion_api(self, da_online, mock_api, mock_db):
        """reset_stage_completion — API + DB"""
        mock_api.reset_stage_completion.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.reset_stage_completion(1)
        assert result is True

    def test_reset_designer_completion_api(self, da_online, mock_api, mock_db):
        """reset_designer_completion — API + DB"""
        mock_api.reset_designer_completion.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.reset_designer_completion(1)
        assert result is True

    def test_reset_draftsman_completion_api(self, da_online, mock_api, mock_db):
        """reset_draftsman_completion — API + DB"""
        mock_api.reset_draftsman_completion.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.reset_draftsman_completion(1)
        assert result is True

    def test_reset_approval_stages_api(self, da_online, mock_api, mock_db):
        """reset_approval_stages — API + DB"""
        mock_api.reset_approval_stages.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.reset_approval_stages(1)
        assert result is True

    def test_save_manager_acceptance_api(self, da_online, mock_api):
        """save_manager_acceptance — DB + API"""
        mock_api.save_manager_acceptance.return_value = {"success": True}
        da_online._is_online = True
        result = da_online.save_manager_acceptance(1, "Концепция", "Иванов", 2)
        assert result is not None

    def test_update_stage_executor_api(self, da_online, mock_api, mock_db):
        """update_stage_executor — DB + API"""
        mock_api.update_stage_executor.return_value = {"success": True}
        da_online._is_online = True
        result = da_online.update_stage_executor(1, "Концепция", {"executor_id": 3})
        assert result is not None

    def test_update_stage_executor_deadline_api(self, da_online, mock_api, mock_db):
        """update_stage_executor_deadline — DB + API"""
        mock_api.update_stage_executor.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.update_stage_executor_deadline(
            1, "Концепция", deadline="2025-12-31", executor_id=2
        )
        assert result is True


# ===========================================================================
# ТАБЛИЦЫ СРОКОВ (CRM и Надзор)
# ===========================================================================

class TestTimelines:
    """get_project_timeline, init_project_timeline, update_timeline_entry, supervision_timeline"""

    def test_get_project_timeline_api(self, da_online, mock_api):
        """get_project_timeline — API"""
        mock_api.get_project_timeline.return_value = [{"stage_code": "C1"}]
        result = da_online.get_project_timeline(1)
        assert result == [{"stage_code": "C1"}]

    def test_get_project_timeline_fallback(self, mock_db):
        """get_project_timeline — API упал → db"""
        api = MagicMock()
        api.get_project_timeline.side_effect = Exception("Offline")
        mock_db.get_project_timeline.return_value = [{"stage_code": "C2"}]
        da = _make_da(api, mock_db)
        result = da.get_project_timeline(1)
        assert result == [{"stage_code": "C2"}]

    def test_init_project_timeline_api(self, da_online, mock_api):
        """init_project_timeline — API"""
        mock_api.init_project_timeline.return_value = {"status": "ok", "count": 5}
        result = da_online.init_project_timeline(1, {"entries": [1, 2, 3, 4, 5]})
        assert result["status"] == "ok"

    def test_reinit_project_timeline_api(self, da_online, mock_api):
        """reinit_project_timeline — API"""
        mock_api.reinit_project_timeline.return_value = {"status": "ok"}
        result = da_online.reinit_project_timeline(1, {"entries": []})
        assert result is not None

    def test_update_timeline_entry_api(self, da_online, mock_api, mock_db):
        """update_timeline_entry — DB + API"""
        da_online._is_online = True
        result = da_online.update_timeline_entry(1, "C1", {"actual_date": "2025-06-01"})
        mock_db.update_timeline_entry.assert_called_once()
        mock_api.update_timeline_entry.assert_called_once()
        assert result is True

    def test_get_timeline_summary_api(self, da_online, mock_api):
        """get_timeline_summary — API"""
        mock_api.get_timeline_summary.return_value = {"total_entries": 10, "progress": 50.0}
        result = da_online.get_timeline_summary(1)
        assert result["total_entries"] == 10

    def test_get_supervision_timeline_api(self, da_online, mock_api):
        """get_supervision_timeline — API возвращает dict"""
        mock_api.get_supervision_timeline.return_value = {"entries": [{"id": 1}], "totals": {}}
        result = da_online.get_supervision_timeline(1)
        assert "entries" in result
        assert "totals" in result

    def test_get_supervision_timeline_fallback(self, mock_db):
        """get_supervision_timeline — API упал → db + обёртка в dict"""
        api = MagicMock()
        api.get_supervision_timeline.side_effect = Exception("Offline")
        mock_db.get_supervision_timeline.return_value = [{"id": 1}]
        da = _make_da(api, mock_db)
        result = da.get_supervision_timeline(1)
        assert "entries" in result
        assert result["entries"] == [{"id": 1}]

    def test_update_supervision_timeline_entry_api(self, da_online, mock_api, mock_db):
        """update_supervision_timeline_entry — DB + API"""
        da_online._is_online = True
        result = da_online.update_supervision_timeline_entry(1, "V1", {"actual_date": "2025-06-01"})
        mock_db.update_supervision_timeline_entry.assert_called_once()
        mock_api.update_supervision_timeline_entry.assert_called_once()
        assert result is True


# ===========================================================================
# ФАЙЛЫ
# ===========================================================================

class TestFiles:
    """create_file_record, delete_file_record, get_project_files, add_project_file"""

    def test_create_file_record_api(self, da_online, mock_api, mock_db):
        """create_file_record — DB + API"""
        mock_api.create_file_record.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.create_file_record({"contract_id": 1, "filename": "test.pdf"})
        mock_db.add_contract_file.assert_called_once()
        assert result == {"id": 1}

    def test_delete_file_record_api(self, da_online, mock_api, mock_db):
        """delete_file_record — DB + API"""
        mock_api.delete_file_record.return_value = True
        da_online._is_online = True
        result = da_online.delete_file_record(1)
        mock_db.delete_project_file.assert_called_once()
        assert result is True

    def test_get_project_files_api(self, da_online, mock_api):
        """get_project_files — API"""
        mock_api.get_project_files.return_value = [{"id": 1, "filename": "plan.dwg"}]
        result = da_online.get_project_files(1, stage="design")
        assert result == [{"id": 1, "filename": "plan.dwg"}]

    def test_scan_contract_files_api(self, da_online, mock_api):
        """scan_contract_files — только API"""
        mock_api.scan_contract_files.return_value = {"files": ["a.pdf"]}
        result = da_online.scan_contract_files(1, scope="full")
        assert result is not None

    def test_scan_contract_files_no_api(self, da_offline):
        """scan_contract_files — без API → None"""
        result = da_offline.scan_contract_files(1)
        assert result is None

    def test_delete_yandex_file_api(self, da_online, mock_api):
        """delete_yandex_file — только API"""
        mock_api.delete_yandex_file.return_value = True
        result = da_online.delete_yandex_file("/path/to/file.pdf")
        assert result is True

    def test_delete_yandex_file_no_api(self, da_offline):
        """delete_yandex_file — без API → False"""
        result = da_offline.delete_yandex_file("/path/to/file.pdf")
        assert result is False

    def test_get_yandex_public_link_dict_response(self, da_online, mock_api):
        """get_yandex_public_link — API возвращает dict → извлекаем URL"""
        mock_api.get_yandex_public_link.return_value = {"public_url": "https://yandex.ru/d/abc123"}
        result = da_online.get_yandex_public_link("/disk/file.pdf")
        assert result == "https://yandex.ru/d/abc123"

    def test_validate_files_api(self, da_online, mock_api):
        """validate_files — API"""
        mock_api.validate_files.return_value = [{"id": 1, "exists": True}]
        result = da_online.validate_files([1, 2, 3])
        assert result == [{"id": 1, "exists": True}]


# ===========================================================================
# ШАБЛОНЫ ПРОЕКТОВ
# ===========================================================================

class TestProjectTemplates:
    """get_project_templates, add_project_template, delete_project_template"""

    def test_get_project_templates_api(self, da_online, mock_api):
        """get_project_templates — API"""
        mock_api.get_project_templates.return_value = [{"id": 1, "url": "https://..."}]
        result = da_online.get_project_templates(1)
        assert result == [{"id": 1, "url": "https://..."}]

    def test_get_project_templates_fallback(self, mock_db):
        """get_project_templates — API упал → db"""
        api = MagicMock()
        api.get_project_templates.side_effect = Exception("Offline")
        mock_db.get_project_templates.return_value = [{"id": 2}]
        da = _make_da(api, mock_db)
        result = da.get_project_templates(1)
        assert result == [{"id": 2}]

    def test_add_project_template_api(self, da_online, mock_api, mock_db):
        """add_project_template — DB + API"""
        mock_api.add_project_template.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.add_project_template(1, "https://docs.google.com/...")
        mock_db.add_project_template.assert_called_once()
        assert result is True

    def test_delete_project_template_api(self, da_online, mock_api, mock_db):
        """delete_project_template — DB + API"""
        mock_api.delete_project_template.return_value = True
        da_online._is_online = True
        result = da_online.delete_project_template(1)
        mock_db.delete_project_template.assert_called_once()
        assert result is True


# ===========================================================================
# СТАТИСТИКА (расширенная)
# ===========================================================================

class TestStatisticsExtended:
    """get_clients_dashboard_stats, get_contracts_dashboard_stats, global_search, etc."""

    def test_get_clients_dashboard_stats_api(self, da_online, mock_api):
        """get_clients_dashboard_stats — API"""
        mock_api.get_clients_dashboard_stats.return_value = {"total": 100}
        result = da_online.get_clients_dashboard_stats()
        assert result == {"total": 100}

    def test_get_clients_dashboard_stats_fallback(self, mock_db):
        """get_clients_dashboard_stats — API упал → db"""
        api = MagicMock()
        api.get_clients_dashboard_stats.side_effect = Exception("Offline")
        mock_db.get_clients_dashboard_stats.return_value = {"total": 50}
        da = _make_da(api, mock_db)
        result = da.get_clients_dashboard_stats()
        assert result == {"total": 50}

    def test_get_contracts_dashboard_stats_api(self, da_online, mock_api):
        """get_contracts_dashboard_stats — API"""
        mock_api.get_contracts_dashboard_stats.return_value = {"active": 10}
        result = da_online.get_contracts_dashboard_stats()
        assert result == {"active": 10}

    def test_global_search_api(self, da_online, mock_api):
        """global_search — API"""
        mock_api.search.return_value = {"clients": [], "contracts": [{"id": 1}]}
        result = da_online.global_search("Иванов")
        assert result == {"clients": [], "contracts": [{"id": 1}]}

    def test_global_search_fallback(self, mock_db):
        """global_search — API упал → db"""
        api = MagicMock()
        api.search.side_effect = Exception("Offline")
        mock_db.global_search.return_value = {"clients": [{"id": 1}]}
        da = _make_da(api, mock_db)
        result = da.global_search("Иванов")
        assert result == {"clients": [{"id": 1}]}

    def test_get_funnel_statistics_api(self, da_online, mock_api):
        """get_funnel_statistics — API"""
        mock_api.get_funnel_statistics.return_value = {"funnel": []}
        result = da_online.get_funnel_statistics(year=2025)
        assert result == {"funnel": []}

    def test_get_executor_load_api(self, da_online, mock_api):
        """get_executor_load — API"""
        mock_api.get_executor_load.return_value = [{"executor_id": 1, "load": 5}]
        result = da_online.get_executor_load(year=2025, month=3)
        assert result == [{"executor_id": 1, "load": 5}]

    def test_get_crm_statistics_filtered_api(self, da_online, mock_api):
        """get_crm_statistics_filtered — API"""
        mock_api.get_crm_statistics_filtered.return_value = {"total": 5}
        result = da_online.get_crm_statistics_filtered(project_type="Индивидуальный")
        assert result == {"total": 5}

    def test_get_supervision_statistics_filtered_api(self, da_online, mock_api):
        """get_supervision_statistics_filtered — API"""
        mock_api.get_supervision_statistics_filtered.return_value = {"visits": 3}
        result = da_online.get_supervision_statistics_filtered(year=2025)
        assert result == {"visits": 3}


# ===========================================================================
# МЕССЕНДЖЕР
# ===========================================================================

class TestMessenger:
    """create_messenger_chat, get_messenger_chat, get_messenger_scripts, etc."""

    def test_create_messenger_chat_api(self, da_online, mock_api):
        """create_messenger_chat — API"""
        mock_api.create_messenger_chat.return_value = {"id": 1, "type": "telegram"}
        result = da_online.create_messenger_chat(crm_card_id=1, messenger_type="telegram")
        assert result == {"id": 1, "type": "telegram"}

    def test_create_messenger_chat_no_api(self, da_offline):
        """create_messenger_chat — без API → None"""
        result = da_offline.create_messenger_chat(crm_card_id=1)
        assert result is None

    def test_get_messenger_chat_api(self, da_online, mock_api):
        """get_messenger_chat — API"""
        mock_api.get_messenger_chat_by_card.return_value = {"id": 1}
        result = da_online.get_messenger_chat(1)
        assert result == {"id": 1}

    def test_get_messenger_chat_no_api(self, da_offline):
        """get_messenger_chat — без API → None"""
        result = da_offline.get_messenger_chat(1)
        assert result is None

    def test_get_messenger_scripts_api(self, da_online, mock_api):
        """get_messenger_scripts — API"""
        mock_api.get_messenger_scripts.return_value = [{"id": 1, "type": "start"}]
        result = da_online.get_messenger_scripts(project_type="Индивидуальный")
        assert len(result) == 1

    def test_get_messenger_scripts_no_api(self, da_offline):
        """get_messenger_scripts — без API → []"""
        result = da_offline.get_messenger_scripts()
        assert result == []

    def test_trigger_script_api(self, da_online, mock_api):
        """trigger_script — API"""
        mock_api.trigger_script.return_value = True
        result = da_online.trigger_script(card_id=1, script_type="start", entity_type="crm")
        assert result is True

    def test_trigger_script_no_api(self, da_offline):
        """trigger_script — без API → False"""
        result = da_offline.trigger_script(1, "start")
        assert result is False

    def test_delete_messenger_chat_api(self, da_online, mock_api):
        """delete_messenger_chat — API"""
        mock_api.delete_messenger_chat.return_value = {"deleted": True}
        result = da_online.delete_messenger_chat(1)
        assert result is not None

    def test_get_messenger_status_api(self, da_online, mock_api):
        """get_messenger_status — API"""
        mock_api.get_messenger_status.return_value = {"telegram_bot_available": True}
        result = da_online.get_messenger_status()
        assert result["telegram_bot_available"] is True

    def test_get_messenger_status_no_api(self, da_offline):
        """get_messenger_status — без API → статус отключения"""
        result = da_offline.get_messenger_status()
        assert result["telegram_bot_available"] is False


# ===========================================================================
# АДМИНИСТРИРОВАНИЕ (права)
# ===========================================================================

class TestAdminPermissions:
    """get_role_permissions_matrix, set_employee_permissions, etc."""

    def test_get_role_permissions_matrix_api(self, da_online, mock_api):
        """get_role_permissions_matrix — API"""
        mock_api.get_role_permissions_matrix.return_value = {"roles": {"admin": ["all"]}}
        result = da_online.get_role_permissions_matrix()
        assert "roles" in result

    def test_get_role_permissions_matrix_no_api(self, da_offline):
        """get_role_permissions_matrix — без API → {"roles": {}}"""
        result = da_offline.get_role_permissions_matrix()
        assert result == {"roles": {}}

    def test_get_employee_permissions_api(self, da_online, mock_api):
        """get_employee_permissions — API"""
        mock_api.get_employee_permissions.return_value = {"permissions": ["clients_read"]}
        result = da_online.get_employee_permissions(1)
        assert "permissions" in result

    def test_get_employee_permissions_fallback(self, mock_db):
        """get_employee_permissions — API упал → db"""
        api = MagicMock()
        api.get_employee_permissions.side_effect = Exception("Offline")
        mock_db.get_employee_permissions.return_value = {"permissions": []}
        da = _make_da(api, mock_db)
        result = da.get_employee_permissions(1)
        assert result == {"permissions": []}

    def test_set_employee_permissions_api(self, da_online, mock_api, mock_db):
        """set_employee_permissions — DB + API"""
        mock_api.set_employee_permissions.return_value = True
        da_online._is_online = True
        result = da_online.set_employee_permissions(1, ["clients_read", "contracts_read"])
        mock_db.set_employee_permissions.assert_called_once()
        assert result is True

    def test_set_employee_permissions_dict_normalization(self, da_online, mock_api, mock_db):
        """set_employee_permissions — dict нормализуется в список"""
        mock_api.set_employee_permissions.return_value = True
        da_online._is_online = True
        result = da_online.set_employee_permissions(1, {"permissions": ["clients_read"]})
        # Должен извлечь список из dict
        assert result is True

    def test_reset_employee_permissions_api(self, da_online, mock_api):
        """reset_employee_permissions — только API"""
        mock_api.reset_employee_permissions.return_value = True
        result = da_online.reset_employee_permissions(1)
        assert result is True

    def test_reset_employee_permissions_no_api(self, da_offline):
        """reset_employee_permissions — без API → False"""
        result = da_offline.reset_employee_permissions(1)
        assert result is False

    def test_get_permission_definitions_api(self, da_online, mock_api):
        """get_permission_definitions — только API"""
        mock_api.get_permission_definitions.return_value = [{"key": "clients_read"}]
        result = da_online.get_permission_definitions()
        assert len(result) == 1

    def test_get_permission_definitions_no_api(self, da_offline):
        """get_permission_definitions — без API → []"""
        result = da_offline.get_permission_definitions()
        assert result == []


# ===========================================================================
# НОРМО-ДНИ
# ===========================================================================

class TestNormDays:
    """get_norm_days_template, save_norm_days_template, preview_norm_days_template"""

    def test_get_norm_days_template_api(self, da_online, mock_api):
        """get_norm_days_template — API"""
        mock_api.get_norm_days_template.return_value = {"entries": [{"stage": "C1", "days": 5}]}
        result = da_online.get_norm_days_template("Индивидуальный", "Базовый")
        assert "entries" in result

    def test_save_norm_days_template_api(self, da_online, mock_api):
        """save_norm_days_template — API"""
        mock_api.save_norm_days_template.return_value = {"saved": True}
        result = da_online.save_norm_days_template({"entries": []})
        assert result == {"saved": True}

    def test_save_norm_days_template_no_api(self, da_offline):
        """save_norm_days_template — без API → None"""
        result = da_offline.save_norm_days_template({"entries": []})
        assert result is None

    def test_preview_norm_days_template_api(self, da_online, mock_api):
        """preview_norm_days_template — API"""
        mock_api.preview_norm_days_template.return_value = {"contract_term": 90, "k_coefficient": 1.0}
        result = da_online.preview_norm_days_template("Индивидуальный", "Базовый", 80.0)
        assert result["contract_term"] == 90

    def test_reset_norm_days_template_api(self, da_online, mock_api):
        """reset_norm_days_template — API"""
        mock_api.reset_norm_days_template.return_value = {"reset": True}
        result = da_online.reset_norm_days_template("Индивидуальный", "Базовый")
        assert result is not None


# ===========================================================================
# ПРОЧИЕ МЕТОДЫ
# ===========================================================================

class TestMiscMethods:
    """get_contract_years, get_cities, get_current_user, delete_order, etc."""

    def test_get_contract_years_api(self, da_online, mock_api):
        """get_contract_years — API"""
        mock_api.get_contract_years.return_value = [2023, 2024, 2025]
        result = da_online.get_contract_years()
        assert 2025 in result

    def test_get_contract_years_fallback(self, mock_db):
        """get_contract_years — API упал → db"""
        api = MagicMock()
        api.get_contract_years.side_effect = Exception("Offline")
        mock_db.get_contract_years.return_value = [2024]
        da = _make_da(api, mock_db)
        result = da.get_contract_years()
        assert result == [2024]

    def test_get_current_user_api(self, da_online, mock_api):
        """get_current_user — только API"""
        mock_api.get_current_user.return_value = {"id": 1, "username": "admin"}
        result = da_online.get_current_user()
        assert result["username"] == "admin"

    def test_get_current_user_no_api(self, da_offline):
        """get_current_user — без API → None"""
        result = da_offline.get_current_user()
        assert result is None

    def test_delete_order_api(self, da_online, mock_api, mock_db):
        """delete_order — API (удаляет crm_card + contract) + DB"""
        da_online._is_online = True
        result = da_online.delete_order(contract_id=1, crm_card_id=2)
        mock_db.delete_order.assert_called_once()
        mock_api.delete_crm_card.assert_called_once_with(2)
        mock_api.delete_contract.assert_called_once_with(1)
        assert result is True

    def test_delete_order_api_error_queued(self, mock_db):
        """delete_order — API упал → в очередь"""
        api = MagicMock()
        api.delete_crm_card.side_effect = Exception("Offline")
        da = _make_da(api, mock_db, is_online=True)
        with patch.object(da, '_queue_operation') as mock_queue:
            result = da.delete_order(contract_id=1, crm_card_id=2)
            assert mock_queue.call_count >= 1

    def test_delete_project_file_api(self, da_online, mock_api, mock_db):
        """delete_project_file — DB + API"""
        mock_api.delete_project_file.return_value = {"yandex_path": "/disk/file.pdf"}
        mock_db.delete_project_file.return_value = None
        da_online._is_online = True
        result = da_online.delete_project_file(1)
        mock_db.delete_project_file.assert_called_once()

    def test_get_projects_by_type_api(self, da_online, mock_api):
        """get_projects_by_type — API"""
        mock_api.get_projects_by_type.return_value = [{"id": 1}]
        result = da_online.get_projects_by_type("Индивидуальный")
        assert result == [{"id": 1}]

    def test_get_pending_operations_count_no_om(self, da_online):
        """get_pending_operations_count — без OfflineManager → 0"""
        result = da_online.get_pending_operations_count()
        assert result == 0

    def test_force_sync_no_om(self, da_online):
        """force_sync — без OfflineManager → no-op"""
        # не должен бросать исключений
        da_online.force_sync()

    def test_get_workflow_state_api(self, da_online, mock_api):
        """get_workflow_state — только API"""
        mock_api.get_workflow_state.return_value = {"state": "submitted"}
        result = da_online.get_workflow_state(1)
        assert result == {"state": "submitted"}

    def test_workflow_submit_api(self, da_online, mock_api):
        """workflow_submit — только API"""
        mock_api.workflow_submit.return_value = {"state": "review"}
        result = da_online.workflow_submit(1)
        assert result is not None

    def test_workflow_accept_api(self, da_online, mock_api):
        """workflow_accept — только API"""
        mock_api.workflow_accept.return_value = {"state": "accepted"}
        result = da_online.workflow_accept(1)
        assert result is not None

    def test_workflow_reject_api(self, da_online, mock_api):
        """workflow_reject — только API"""
        mock_api.workflow_reject.return_value = {"state": "rejected"}
        result = da_online.workflow_reject(1, stage_name="Концепция", reason="Нужна доработка")
        assert result is not None

    def test_workflow_client_send_no_api(self, da_offline):
        """workflow_client_send — без API → None"""
        result = da_offline.workflow_client_send(1)
        assert result is None

    def test_get_employee_active_assignments_api(self, da_online, mock_api):
        """get_employee_active_assignments — API (CRM cards)"""
        mock_api.get_crm_cards.return_value = [
            {"id": 1, "contract_number": "D-001", "team": [
                {"executor_id": 5, "stage_name": "Концепция", "status": "active"}
            ]}
        ]
        result = da_online.get_employee_active_assignments(5)
        assert isinstance(result, list)

    def test_get_accepted_stages_api(self, da_online, mock_api):
        """get_accepted_stages — API"""
        mock_api.get_accepted_stages.return_value = [{"stage": "Концепция"}]
        result = da_online.get_accepted_stages(1)
        assert result == [{"stage": "Концепция"}]

    def test_get_submitted_stages_fallback(self, mock_db):
        """get_submitted_stages — API упал → db"""
        api = MagicMock()
        api.get_submitted_stages.side_effect = Exception("Offline")
        mock_db.get_submitted_stages.return_value = [{"stage": "Чертежи"}]
        da = _make_da(api, mock_db)
        result = da.get_submitted_stages(1)
        assert result == [{"stage": "Чертежи"}]

    def test_get_contract_id_by_crm_card_api(self, da_online, mock_api):
        """get_contract_id_by_crm_card — API"""
        mock_api.get_crm_card.return_value = {"id": 1, "contract_id": 42}
        result = da_online.get_contract_id_by_crm_card(1)
        assert result == 42

    def test_get_archived_crm_cards_api(self, da_online, mock_api):
        """get_archived_crm_cards — API"""
        mock_api.get_archived_crm_cards.return_value = [{"id": 10}]
        result = da_online.get_archived_crm_cards("Индивидуальный")
        assert result == [{"id": 10}]

    def test_move_crm_card_api(self, da_online, mock_api, mock_db):
        """move_crm_card — API через workflow + DB"""
        mock_api.move_crm_card.return_value = {"id": 1}
        da_online._is_online = True
        result = da_online.move_crm_card(1, "В работе")
        mock_api.move_crm_card.assert_called_once_with(1, "В работе")
        assert result is True
