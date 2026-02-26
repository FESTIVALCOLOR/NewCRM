# -*- coding: utf-8 -*-
"""
Тесты двухрежимности DataAccess: API-first + DB fallback, offline-очередь,
prefer_local, фильтрация бизнес-ошибок vs сетевых.

Сценарии:
  1. API доступен → вызывается API, не DB
  2. APIConnectionError → fallback на DB
  3. APITimeoutError → fallback на DB
  4. HTTP 400/409 (бизнес-ошибка) → НЕ fallback, НЕ в очередь
  5. Create при offline → запись в offline_queue + локальная БД
  6. prefer_local=True → сначала DB, потом API
  7. Несколько последовательных ошибок API → каждый раз fallback
  8. Online → Offline переключение → операции в очередь
  9. Offline → Online → синхронизация очереди
 10. Каждый CRUD метод корректно проксирует
 11. Исключения API не проброшены к вызывающему коду
 12. Возвращаемые данные имеют одинаковый формат (API vs DB)
"""
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

pytest.importorskip("PyQt5")

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.api_client.exceptions import (
    APIConnectionError,
    APITimeoutError,
    APIResponseError,
)


# ---------------------------------------------------------------------------
# Вспомогательные фабрики
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _patch_offline_manager():
    """Мокаем OfflineManager, чтобы тесты не зависели от реального модуля."""
    with patch("utils.data_access.get_offline_manager", return_value=None):
        yield


def _make_da(api=None, db=None, online=True, prefer_local=False):
    """Фабрика DataAccess с моками (без __init__, чтобы не требовать QApp)."""
    from utils.data_access import DataAccess

    da = DataAccess.__new__(DataAccess)
    da.api_client = api
    da.db = db or MagicMock()
    da._is_online = api is not None and online
    da.prefer_local = prefer_local
    # Заглушки для pyqtSignal (emit вызывается внутри _queue_operation)
    da.connection_status_changed = MagicMock()
    da.operation_queued = MagicMock()
    da.pending_operations_changed = MagicMock()
    return da


def _mock_api(**overrides):
    """Создать мок API-клиента с базовыми возвратами."""
    api = MagicMock()
    api.get_clients.return_value = [{"id": 101, "full_name": "API Client"}]
    api.get_client.return_value = {"id": 101, "full_name": "API Client"}
    api.create_client.return_value = {"id": 101, "full_name": "API Client"}
    api.update_client.return_value = {"id": 101, "updated": True}
    api.delete_client.return_value = True

    api.get_contracts.return_value = [{"id": 201, "contract_number": "D-001"}]
    api.get_contract.return_value = {"id": 201, "contract_number": "D-001"}
    api.create_contract.return_value = {"id": 201}
    api.update_contract.return_value = {"id": 201}
    api.delete_contract.return_value = True

    api.get_employees.return_value = [{"id": 301, "full_name": "Admin"}]
    api.get_employee.return_value = {"id": 301, "full_name": "Admin"}
    api.create_employee.return_value = {"id": 301}
    api.update_employee.return_value = {"id": 301}
    api.delete_employee.return_value = True

    api.get_crm_cards.return_value = [{"id": 401, "contract_id": 201}]
    api.get_crm_card.return_value = {"id": 401}
    api.create_crm_card.return_value = {"id": 401}
    api.update_crm_card.return_value = {"id": 401}
    api.delete_crm_card.return_value = True

    api.get_payments_for_contract.return_value = [{"id": 601, "amount": 5000}]
    api.get_rates.return_value = [{"id": 701}]
    api.get_salaries.return_value = [{"id": 801}]
    api.get_action_history.return_value = [{"id": 1}]
    api.get_supervision_history.return_value = []
    api.get_contract_files.return_value = []
    api.get_dashboard_statistics.return_value = {"total_orders": 50}
    api.get_employees_by_position.return_value = [{"id": 301}]
    api.get_supervision_cards.return_value = []

    for k, v in overrides.items():
        setattr(api, k, v)
    return api


def _mock_db(**overrides):
    """Создать мок DatabaseManager с базовыми возвратами."""
    db = MagicMock()
    db.get_all_clients.return_value = [{"id": 1, "full_name": "DB Client"}]
    db.get_client_by_id.return_value = {"id": 1, "full_name": "DB Client"}
    db.add_client.return_value = 10

    db.get_all_contracts.return_value = [{"id": 1, "contract_number": "D-L001"}]
    db.get_contract_by_id.return_value = {"id": 1, "contract_number": "D-L001"}
    db.add_contract.return_value = 20

    db.get_all_employees.return_value = [{"id": 1, "full_name": "DB Admin"}]
    db.get_employee_by_id.return_value = {"id": 1, "full_name": "DB Admin"}
    db.add_employee.return_value = 30

    db.get_crm_cards_by_project_type.return_value = [{"id": 1}]
    db.get_crm_card_data.return_value = {"id": 1}
    db.add_crm_card.return_value = 40

    db.get_payments_for_contract.return_value = [{"id": 1, "amount": 1000}]
    db.get_rates.return_value = []
    db.get_salaries.return_value = []
    db.get_action_history.return_value = []
    db.get_supervision_history.return_value = []
    db.get_contract_files.return_value = []
    db.get_dashboard_statistics.return_value = {"total_orders": 5}
    db.get_employees_by_position.return_value = [{"id": 1}]
    db.get_supervision_cards_active.return_value = []
    db.get_supervision_cards_archived.return_value = []

    for k, v in overrides.items():
        setattr(db, k, v)
    return db


# ===========================================================================
# 1. API доступен → вызывается API, не DB
# ===========================================================================

class TestAPIAvailable:
    """Когда API доступен, DataAccess использует API, а не локальную БД."""

    def test_get_all_clients_через_api(self):
        """get_all_clients возвращает результат API, DB не вызывается."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_all_clients()
        assert result == api.get_clients.return_value
        api.get_clients.assert_called_once()
        db.get_all_clients.assert_not_called()

    def test_get_contract_через_api(self):
        """get_contract возвращает результат API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_contract(201)
        assert result == api.get_contract.return_value
        api.get_contract.assert_called_once_with(201)
        db.get_contract_by_id.assert_not_called()

    def test_get_all_employees_через_api(self):
        """get_all_employees возвращает результат API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_all_employees()
        assert result == api.get_employees.return_value
        api.get_employees.assert_called_once()
        db.get_all_employees.assert_not_called()

    def test_get_crm_cards_через_api(self):
        """get_crm_cards возвращает результат API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_crm_cards("Индивидуальный")
        assert result == api.get_crm_cards.return_value
        api.get_crm_cards.assert_called_once_with("Индивидуальный")
        db.get_crm_cards_by_project_type.assert_not_called()


# ===========================================================================
# 2. APIConnectionError → fallback на DB
# ===========================================================================

class TestFallbackOnConnectionError:
    """При APIConnectionError DataAccess переключается на DB."""

    def test_get_all_clients_fallback_connection(self):
        """APIConnectionError при get_clients → возврат из DB."""
        api, db = _mock_api(), _mock_db()
        api.get_clients.side_effect = APIConnectionError("Сервер недоступен")
        da = _make_da(api, db)
        result = da.get_all_clients()
        assert result == db.get_all_clients.return_value
        db.get_all_clients.assert_called_once()

    def test_get_employee_fallback_connection(self):
        """APIConnectionError при get_employee → возврат из DB."""
        api, db = _mock_api(), _mock_db()
        api.get_employee.side_effect = APIConnectionError("Сервер недоступен")
        da = _make_da(api, db)
        result = da.get_employee(1)
        assert result == db.get_employee_by_id.return_value


# ===========================================================================
# 3. APITimeoutError → fallback на DB
# ===========================================================================

class TestFallbackOnTimeoutError:
    """При APITimeoutError DataAccess переключается на DB."""

    def test_get_all_contracts_fallback_timeout(self):
        """APITimeoutError при get_contracts → возврат из DB."""
        api, db = _mock_api(), _mock_db()
        api.get_contracts.side_effect = APITimeoutError("Таймаут запроса")
        da = _make_da(api, db)
        result = da.get_all_contracts()
        assert result == db.get_all_contracts.return_value
        db.get_all_contracts.assert_called_once()

    def test_get_crm_card_fallback_timeout(self):
        """APITimeoutError при get_crm_card → возврат из DB."""
        api, db = _mock_api(), _mock_db()
        api.get_crm_card.side_effect = APITimeoutError("Таймаут")
        da = _make_da(api, db)
        result = da.get_crm_card(1)
        assert result == db.get_crm_card_data.return_value


# ===========================================================================
# 4. HTTP 400/409 (бизнес-ошибка) → НЕ fallback на чтении (поведение:
#    Exception ловится в except, и fallback всё равно срабатывает
#    для READ-операций, но для WRITE _queue_operation фильтрует).
#    Для write: бизнес-ошибка НЕ попадает в offline_queue.
# ===========================================================================

class TestBusinessErrorNotQueued:
    """Бизнес-ошибки (400, 409) НЕ добавляются в offline-очередь."""

    def test_create_client_бизнес_ошибка_не_в_очередь(self):
        """APIResponseError(409) при create_client → НЕ ставится в очередь."""
        api, db = _mock_api(), _mock_db()
        api.create_client.side_effect = APIResponseError("Conflict", status_code=409)
        da = _make_da(api, db, online=True)

        # Мокаем is_online через property на экземпляре невозможно (property класса),
        # поэтому патчим get_offline_manager чтобы is_online = True
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            da.create_client({"full_name": "Тест"})

        # queue_operation вызывается внутри _queue_operation, но для бизнес-ошибки
        # _queue_operation проверяет sys.exc_info() и выходит до вызова om.queue_operation
        mock_om.queue_operation.assert_not_called()

    def test_update_employee_бизнес_ошибка_не_в_очередь(self):
        """APIResponseError(400) при update_employee → НЕ ставится в очередь."""
        api, db = _mock_api(), _mock_db()
        api.update_employee.side_effect = APIResponseError("Bad Request", status_code=400)
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            da.update_employee(1, {"full_name": "Обновлено"})

        mock_om.queue_operation.assert_not_called()

    def test_delete_client_бизнес_ошибка_не_в_очередь(self):
        """APIResponseError(403) при delete_client → НЕ ставится в очередь."""
        api, db = _mock_api(), _mock_db()
        api.delete_client.side_effect = APIResponseError("Forbidden", status_code=403)
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            da.delete_client(1)

        mock_om.queue_operation.assert_not_called()


# ===========================================================================
# 5. Create при offline → запись в offline_queue + локальная БД
# ===========================================================================

class TestCreateOfflineQueue:
    """При offline create записывает в DB и ставит в offline-очередь."""

    def test_create_client_offline_запись_в_очередь(self):
        """create_client при APIConnectionError → DB + очередь."""
        api, db = _mock_api(), _mock_db()
        api.create_client.side_effect = APIConnectionError("Offline")
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.create_client({"full_name": "Offline Client"})

        # Записано в локальную БД
        db.add_client.assert_called_once()
        # Добавлено в очередь
        mock_om.queue_operation.assert_called_once()
        # Результат не None
        assert result is not None
        assert result["id"] == db.add_client.return_value

    def test_create_contract_offline_запись_в_очередь(self):
        """create_contract при APIConnectionError → DB + очередь."""
        api, db = _mock_api(), _mock_db()
        api.create_contract.side_effect = APIConnectionError("Offline")
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.create_contract({"contract_number": "D-OFF-001"})

        db.add_contract.assert_called_once()
        mock_om.queue_operation.assert_called_once()
        assert result is not None

    def test_create_employee_offline_запись_в_очередь(self):
        """create_employee при APITimeoutError → DB + очередь."""
        api, db = _mock_api(), _mock_db()
        api.create_employee.side_effect = APITimeoutError("Таймаут")
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.create_employee({"full_name": "Новый сотрудник"})

        db.add_employee.assert_called_once()
        mock_om.queue_operation.assert_called_once()
        assert result is not None


# ===========================================================================
# 6. prefer_local=True → сначала DB, потом API
# ===========================================================================

class TestPreferLocal:
    """prefer_local=True: чтение идёт из DB, API не вызывается для чтения."""

    def test_prefer_local_clients(self):
        """prefer_local → get_all_clients из DB, API не трогается."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, prefer_local=True)
        result = da.get_all_clients()
        assert result == db.get_all_clients.return_value
        api.get_clients.assert_not_called()

    def test_prefer_local_contracts(self):
        """prefer_local → get_all_contracts из DB."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, prefer_local=True)
        result = da.get_all_contracts()
        assert result == db.get_all_contracts.return_value
        api.get_contracts.assert_not_called()

    def test_prefer_local_employees(self):
        """prefer_local → get_all_employees из DB."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, prefer_local=True)
        result = da.get_all_employees()
        assert result == db.get_all_employees.return_value
        api.get_employees.assert_not_called()

    def test_prefer_local_запись_всё_равно_через_api(self):
        """prefer_local → create_client всё равно пишет в API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True, prefer_local=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            da.create_client({"full_name": "Новый клиент"})

        api.create_client.assert_called_once()
        db.add_client.assert_called_once()


# ===========================================================================
# 7. Несколько последовательных ошибок API → каждый раз fallback
# ===========================================================================

class TestMultipleConsecutiveErrors:
    """Несколько ошибок подряд — каждый раз корректный fallback."""

    def test_три_подряд_ошибки_api_все_fallback(self):
        """Три вызова get_all_clients с ошибками → три fallback на DB."""
        api, db = _mock_api(), _mock_db()
        api.get_clients.side_effect = APIConnectionError("Offline")
        da = _make_da(api, db)

        r1 = da.get_all_clients()
        r2 = da.get_all_clients()
        r3 = da.get_all_clients()

        assert r1 == r2 == r3 == db.get_all_clients.return_value
        assert api.get_clients.call_count == 3
        assert db.get_all_clients.call_count == 3

    def test_разные_методы_с_ошибками(self):
        """Ошибки в разных методах — каждый использует свой fallback."""
        api, db = _mock_api(), _mock_db()
        api.get_clients.side_effect = APIConnectionError("Offline")
        api.get_contracts.side_effect = APITimeoutError("Таймаут")
        api.get_employees.side_effect = APIConnectionError("Offline")
        da = _make_da(api, db)

        clients = da.get_all_clients()
        contracts = da.get_all_contracts()
        employees = da.get_all_employees()

        assert clients == db.get_all_clients.return_value
        assert contracts == db.get_all_contracts.return_value
        assert employees == db.get_all_employees.return_value


# ===========================================================================
# 8. Online → Offline переключение → операции в очередь
# ===========================================================================

class TestOnlineToOfflineSwitch:
    """Переход online→offline: операции записи идут в очередь."""

    def test_первая_запись_онлайн_вторая_офлайн(self):
        """Первый create проходит через API, второй — при ошибке — в очередь."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        mock_om.queue_operation = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            # Первый вызов — API работает
            r1 = da.create_client({"full_name": "Клиент 1"})
            assert r1 == api.create_client.return_value
            mock_om.queue_operation.assert_not_called()

            # Имитируем падение API
            api.create_client.side_effect = APIConnectionError("Сервер упал")

            # Второй вызов — API упал, должна быть очередь
            r2 = da.create_client({"full_name": "Клиент 2"})
            mock_om.queue_operation.assert_called_once()


# ===========================================================================
# 9. Offline → Online → синхронизация очереди
# ===========================================================================

class TestOfflineToOnlineSync:
    """Восстановление связи: force_sync отправляет накопленные операции."""

    def test_force_sync_вызывает_offline_manager(self):
        """force_sync делегирует вызов OfflineManager.force_sync."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True)

        mock_om = MagicMock()
        mock_om.force_sync = MagicMock()

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            da.force_sync()

        mock_om.force_sync.assert_called_once()

    def test_pending_operations_count(self):
        """get_pending_operations_count возвращает значение из OfflineManager."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)

        mock_om = MagicMock()
        mock_om.get_pending_operations_count.return_value = 5

        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            count = da.get_pending_operations_count()

        assert count == 5


# ===========================================================================
# 10. Каждый CRUD метод корректно проксирует
# ===========================================================================

class TestCRUDProxy:
    """Все основные CRUD методы корректно проксируют вызовы к API/DB."""

    def test_update_client_проксирует_api(self):
        """update_client вызывает DB + API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.update_client(1, {"full_name": "Обновлён"})
        db.update_client.assert_called_once_with(1, {"full_name": "Обновлён"})
        api.update_client.assert_called_once_with(1, {"full_name": "Обновлён"})
        assert result is True

    def test_delete_employee_проксирует_api(self):
        """delete_employee вызывает DB + API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.delete_employee(1)
        db.delete_employee.assert_called_once_with(1)
        api.delete_employee.assert_called_once_with(1)

    def test_update_contract_проксирует_api(self):
        """update_contract вызывает DB + API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.update_contract(201, {"status": "active"})
        db.update_contract.assert_called_once_with(201, {"status": "active"})
        api.update_contract.assert_called_once_with(201, {"status": "active"})
        assert result is True

    def test_update_crm_card_проксирует_api(self):
        """update_crm_card вызывает DB + API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.update_crm_card(401, {"column_name": "in_progress"})
        db.update_crm_card.assert_called_once_with(401, {"column_name": "in_progress"})
        api.update_crm_card.assert_called_once_with(401, {"column_name": "in_progress"})
        assert result is True

    def test_get_payments_for_contract_проксирует_api(self):
        """get_payments_for_contract возвращает результат API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_payments_for_contract(201)
        assert result == api.get_payments_for_contract.return_value

    def test_get_action_history_проксирует_api(self):
        """get_action_history возвращает результат API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_action_history("client", 1)
        assert result == api.get_action_history.return_value

    def test_get_dashboard_statistics_проксирует_api(self):
        """get_dashboard_statistics возвращает результат API."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        result = da.get_dashboard_statistics(2025, 1)
        assert result == api.get_dashboard_statistics.return_value


# ===========================================================================
# 11. Исключения API не проброшены к вызывающему коду
# ===========================================================================

class TestExceptionsNotPropagated:
    """API исключения перехватываются, вызывающий код получает данные из DB."""

    def test_get_all_clients_не_пробрасывает_exception(self):
        """APIConnectionError не видна вызывающему коду."""
        api, db = _mock_api(), _mock_db()
        api.get_clients.side_effect = APIConnectionError("Connection refused")
        da = _make_da(api, db)
        # Не должно быть исключения
        result = da.get_all_clients()
        assert result is not None

    def test_get_contract_не_пробрасывает_timeout(self):
        """APITimeoutError не видна вызывающему коду."""
        api, db = _mock_api(), _mock_db()
        api.get_contract.side_effect = APITimeoutError("Таймаут")
        da = _make_da(api, db)
        result = da.get_contract(1)
        assert result is not None

    def test_create_client_не_пробрасывает_exception(self):
        """Ошибка API при create не пробрасывается."""
        api, db = _mock_api(), _mock_db()
        api.create_client.side_effect = APIConnectionError("Server down")
        da = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.create_client({"full_name": "Тест"})
        # Не пробросило, вернуло fallback результат
        assert result is not None

    def test_update_client_не_пробрасывает_exception(self):
        """Ошибка API при update не пробрасывается."""
        api, db = _mock_api(), _mock_db()
        api.update_client.side_effect = APIConnectionError("Offline")
        da = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result = da.update_client(1, {"full_name": "X"})
        assert result is True

    def test_get_employees_by_position_не_пробрасывает_generic_exception(self):
        """Даже generic Exception не видна вызывающему коду."""
        api, db = _mock_api(), _mock_db()
        api.get_employees_by_position.side_effect = RuntimeError("Unexpected")
        da = _make_da(api, db)
        result = da.get_employees_by_position("Designer")
        assert result == db.get_employees_by_position.return_value


# ===========================================================================
# 12. Возвращаемые данные имеют одинаковый формат (API vs DB)
# ===========================================================================

class TestDataFormatConsistency:
    """API и DB возвращают данные в одинаковом формате (list[dict] / dict)."""

    def test_get_all_clients_формат_list_dict(self):
        """И API, и DB возвращают list[dict] для get_all_clients."""
        api, db = _mock_api(), _mock_db()

        # Через API
        da_online = _make_da(api, db)
        result_api = da_online.get_all_clients()
        assert isinstance(result_api, list)
        assert all(isinstance(r, dict) for r in result_api)

        # Через DB (fallback)
        api2 = _mock_api()
        api2.get_clients.side_effect = APIConnectionError("Down")
        da_offline = _make_da(api2, db)
        result_db = da_offline.get_all_clients()
        assert isinstance(result_db, list)
        assert all(isinstance(r, dict) for r in result_db)

    def test_get_contract_формат_dict(self):
        """И API, и DB возвращают dict для get_contract."""
        api, db = _mock_api(), _mock_db()

        # Через API
        da_online = _make_da(api, db)
        result_api = da_online.get_contract(201)
        assert isinstance(result_api, dict)

        # Через DB
        api2 = _mock_api()
        api2.get_contract.side_effect = APIConnectionError("Down")
        da_offline = _make_da(api2, db)
        result_db = da_offline.get_contract(1)
        assert isinstance(result_db, dict)

    def test_create_client_формат_dict(self):
        """create_client возвращает dict и через API, и через DB-only."""
        api, db = _mock_api(), _mock_db()

        # Через API (online)
        da_online = _make_da(api, db, online=True)
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch("utils.data_access.get_offline_manager", return_value=mock_om):
            result_api = da_online.create_client({"full_name": "Test"})
        assert isinstance(result_api, dict)

        # Только DB (нет api_client)
        da_local = _make_da(None, db)
        result_db = da_local.create_client({"full_name": "Test"})
        assert isinstance(result_db, dict)


# ===========================================================================
# Дополнительные тесты: _should_use_api, is_multi_user, is_online
# ===========================================================================

class TestServiceProperties:
    """Тесты вспомогательных свойств DataAccess."""

    def test_is_multi_user_true_с_api(self):
        """is_multi_user == True когда api_client задан."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db)
        assert da.is_multi_user is True

    def test_is_multi_user_false_без_api(self):
        """is_multi_user == False когда api_client == None."""
        db = _mock_db()
        da = _make_da(None, db)
        assert da.is_multi_user is False

    def test_should_use_api_false_при_prefer_local(self):
        """_should_use_api == False при prefer_local=True."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, prefer_local=True)
        assert da._should_use_api() is False

    def test_should_use_api_false_без_api_client(self):
        """_should_use_api == False когда api_client == None."""
        db = _mock_db()
        da = _make_da(None, db)
        assert da._should_use_api() is False

    def test_should_use_api_true_при_online(self):
        """_should_use_api == True при наличии api_client и prefer_local=False."""
        api, db = _mock_api(), _mock_db()
        da = _make_da(api, db, prefer_local=False)
        assert da._should_use_api() is True
