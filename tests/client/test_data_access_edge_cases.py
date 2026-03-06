# -*- coding: utf-8 -*-
"""
Тесты edge cases для DataAccess:
- API→SQLite fallback при ошибках
- Offline-очередь: сетевые ошибки vs бизнес-ошибки
- Кеширование (_DataCache TTL, инвалидация)
- prefer_local mode
- Переключение online↔offline
- create_client/update_client/delete_client с offline-очередью

HIGH criticality — покрывает разрывы логики между API и локальной БД.
"""
import pytest
import sys
import os
import time as _time_module
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== _DataCache ====================

class TestDataCache:
    """_DataCache — кеш с TTL для DataAccess."""

    def _make_cache(self):
        from utils.data_access import _DataCache
        return _DataCache()

    def test_set_and_get(self):
        cache = self._make_cache()
        cache.set("key1", [1, 2, 3])
        assert cache.get("key1") == [1, 2, 3]

    def test_get_missing_key(self):
        cache = self._make_cache()
        assert cache.get("nonexistent") is None

    def test_ttl_expiry(self):
        cache = self._make_cache()
        cache.set("key1", "data")
        # Подменяем timestamp на прошлое
        ts, data = cache._store["key1"]
        cache._store["key1"] = (ts - 100, data)  # 100 сек назад
        assert cache.get("key1") is None

    def test_ttl_custom_value(self):
        cache = self._make_cache()
        cache.set("key1", "data")
        # С кастомным TTL=0.001 — данные ещё не истекли (только что записали)
        result = cache.get("key1", ttl=60)
        assert result == "data"

    def test_ttl_custom_expired(self):
        cache = self._make_cache()
        cache.set("key1", "data")
        ts, data = cache._store["key1"]
        cache._store["key1"] = (ts - 10, data)
        # TTL=5 — уже истекло
        assert cache.get("key1", ttl=5) is None

    def test_invalidate_all(self):
        cache = self._make_cache()
        cache.set("a:1", "data1")
        cache.set("b:2", "data2")
        cache.invalidate()
        assert cache.get("a:1") is None
        assert cache.get("b:2") is None

    def test_invalidate_prefix(self):
        cache = self._make_cache()
        cache.set("clients:0:100", "cl")
        cache.set("clients:100:200", "cl2")
        cache.set("contracts:0:100", "co")
        cache.invalidate("clients")
        assert cache.get("clients:0:100") is None
        assert cache.get("clients:100:200") is None
        assert cache.get("contracts:0:100") == "co"

    def test_invalidate_prefix_no_match(self):
        cache = self._make_cache()
        cache.set("key1", "data")
        cache.invalidate("nonexistent_prefix")
        assert cache.get("key1") == "data"

    def test_default_ttl(self):
        from utils.data_access import _DataCache
        assert _DataCache.DEFAULT_TTL == 30

    def test_overwrite_key(self):
        cache = self._make_cache()
        cache.set("key1", "old")
        cache.set("key1", "new")
        assert cache.get("key1") == "new"


# ==================== DataAccess — инициализация ====================

class TestDataAccessInit:
    """DataAccess — инициализация и базовые свойства."""

    def _make_da(self, api_client=None, db=None):
        from utils.data_access import DataAccess
        mock_db = db or MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=api_client, db=mock_db)
        return da

    def test_init_with_api(self):
        da = self._make_da(api_client=MagicMock())
        assert da.is_multi_user is True

    def test_init_without_api(self):
        da = self._make_da()
        assert da.is_multi_user is False

    def test_prefer_local_default_false(self):
        da = self._make_da()
        assert da.prefer_local is False

    def test_should_use_api_with_client(self):
        da = self._make_da(api_client=MagicMock())
        assert da._should_use_api() is True

    def test_should_use_api_prefer_local(self):
        da = self._make_da(api_client=MagicMock())
        da.prefer_local = True
        assert da._should_use_api() is False

    def test_should_use_api_no_client(self):
        da = self._make_da()
        assert da._should_use_api() is False

    def test_is_online_with_offline_manager(self):
        mock_om = MagicMock()
        mock_om.is_online.return_value = True
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da = self._make_da(api_client=MagicMock())
            assert da.is_online is True

    def test_is_online_offline_manager_says_no(self):
        mock_om = MagicMock()
        mock_om.is_online.return_value = False
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da = self._make_da(api_client=MagicMock())
            assert da.is_online is False

    def test_is_online_no_offline_manager(self):
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = self._make_da(api_client=MagicMock())
            assert da.is_online is True

    def test_is_online_no_api_client(self):
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = self._make_da()
            assert da.is_online is False


# ==================== DataAccess — API→DB fallback ====================

class TestDataAccessFallback:
    """DataAccess — fallback на локальную БД при ошибках API."""

    def _make_da(self, api_client=None, db=None):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()  # Очистить кеш перед каждым тестом
        mock_db = db or MagicMock()
        mock_api = api_client or MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)
        return da

    def test_get_all_clients_api_success(self):
        """API работает — возвращаются данные с API."""
        da = self._make_da()
        da.api_client.get_clients.return_value = [{"id": 1}]
        result = da.get_all_clients()
        assert result == [{"id": 1}]
        da.api_client.get_clients.assert_called_once()

    def test_get_all_clients_api_fails_fallback_db(self):
        """API падает — fallback на локальную БД."""
        da = self._make_da()
        da.api_client.get_clients.side_effect = Exception("Connection refused")
        da.db.get_all_clients.return_value = [{"id": 2, "source": "local"}]
        result = da.get_all_clients()
        assert result == [{"id": 2, "source": "local"}]
        da.db.get_all_clients.assert_called_once()

    def test_get_all_clients_prefer_local_skips_api(self):
        """prefer_local=True — API не вызывается, сразу локальная БД."""
        da = self._make_da()
        da.prefer_local = True
        da.db.get_all_clients.return_value = [{"id": 3}]
        result = da.get_all_clients()
        assert result == [{"id": 3}]
        da.api_client.get_clients.assert_not_called()

    def test_get_contract_api_success(self):
        da = self._make_da()
        da.api_client.get_contract.return_value = {"id": 10, "number": "DP-001"}
        result = da.get_contract(10)
        assert result == {"id": 10, "number": "DP-001"}

    def test_get_contract_api_fails_fallback(self):
        da = self._make_da()
        da.api_client.get_contract.side_effect = ConnectionError("timeout")
        da.db.get_contract_by_id.return_value = {"id": 10, "number": "DP-001", "source": "local"}
        result = da.get_contract(10)
        assert result["source"] == "local"

    def test_get_all_contracts_api_success(self):
        from utils.data_access import _global_cache
        _global_cache.invalidate()
        da = self._make_da()
        da.api_client.get_contracts.return_value = [{"id": 1}]
        result = da.get_all_contracts()
        assert result == [{"id": 1}]

    def test_get_all_contracts_api_fails_fallback(self):
        from utils.data_access import _global_cache
        _global_cache.invalidate()
        da = self._make_da()
        da.api_client.get_contracts.side_effect = Exception("err")
        da.db.get_all_contracts.return_value = [{"id": 2}]
        result = da.get_all_contracts()
        assert result == [{"id": 2}]

    def test_get_all_employees_api_fails_fallback(self):
        from utils.data_access import _global_cache
        _global_cache.invalidate()
        da = self._make_da()
        da.api_client.get_employees.side_effect = TimeoutError("timeout")
        da.db.get_all_employees.return_value = [{"id": 1, "name": "Тест"}]
        result = da.get_all_employees()
        assert result == [{"id": 1, "name": "Тест"}]

    def test_get_client_no_api(self):
        """Без api_client — только локальная БД."""
        from utils.data_access import DataAccess
        mock_db = MagicMock()
        mock_db.get_client_by_id.return_value = {"id": 5}
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=None, db=mock_db)
        result = da.get_client(5)
        assert result == {"id": 5}


# ==================== DataAccess — кеширование при переключении ====================

class TestDataAccessCacheModeSwitch:
    """Инвалидация кеша при смене online↔offline."""

    def test_cache_invalidated_on_mode_change(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)

        # Заполняем кеш
        _global_cache.set("clients:0:10000", [{"cached": True}])

        # Переключаем в prefer_local
        da.prefer_local = True
        # _check_cache_on_mode_change сбросит кеш при вызове
        da._check_cache_on_mode_change()
        assert _global_cache.get("clients:0:10000") is None

    def test_cache_not_invalidated_same_mode(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)

        _global_cache.set("clients:0:10000", [{"cached": True}])
        # Тот же режим — кеш остаётся
        da._check_cache_on_mode_change()
        assert _global_cache.get("clients:0:10000") == [{"cached": True}]


# ==================== DataAccess — offline queue ====================

class TestDataAccessOfflineQueue:
    """DataAccess._queue_operation — разделение сетевых и бизнес-ошибок."""

    def _make_da(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)
        return da

    def test_queue_network_error(self):
        """APIConnectionError — ставится в offline-очередь."""
        from utils.api_client.exceptions import APIConnectionError
        da = self._make_da()
        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            try:
                raise APIConnectionError("Connection refused")
            except APIConnectionError:
                da._queue_operation('create', 'client', 1, {"name": "Тест"})
        mock_om.queue_operation.assert_called_once()

    def test_queue_timeout_error(self):
        """APITimeoutError — ставится в offline-очередь."""
        from utils.api_client.exceptions import APITimeoutError
        da = self._make_da()
        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            try:
                raise APITimeoutError("Timeout")
            except APITimeoutError:
                da._queue_operation('update', 'contract', 5, {"status": "active"})
        mock_om.queue_operation.assert_called_once()

    def test_queue_business_error_rejected(self):
        """APIResponseError (400/409) — НЕ ставится в очередь."""
        from utils.api_client.exceptions import APIResponseError
        da = self._make_da()
        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            try:
                raise APIResponseError("Conflict: duplicate", status_code=409)
            except APIResponseError:
                da._queue_operation('create', 'client', 1, {"name": "dup"})
        mock_om.queue_operation.assert_not_called()

    def test_queue_auth_error_rejected(self):
        """APIAuthError — НЕ ставится в очередь (бизнес-ошибка)."""
        from utils.api_client.exceptions import APIAuthError
        da = self._make_da()
        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            try:
                raise APIAuthError("Unauthorized")
            except APIAuthError:
                da._queue_operation('update', 'client', 1, {})
        mock_om.queue_operation.assert_not_called()

    def test_queue_generic_exception_rejected(self):
        """Обычное Exception — НЕ ставится в очередь."""
        da = self._make_da()
        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            try:
                raise ValueError("bad data")
            except ValueError:
                da._queue_operation('update', 'client', 1, {})
        mock_om.queue_operation.assert_not_called()

    def test_queue_outside_except_block(self):
        """Вызов вне except-блока (exc_info() = None) — ставится в очередь."""
        da = self._make_da()
        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da._queue_operation('create', 'client', 1, {"name": "Тест"})
        mock_om.queue_operation.assert_called_once()

    def test_queue_no_offline_manager(self):
        """Без OfflineManager — ничего не падает."""
        da = self._make_da()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da._queue_operation('create', 'client', 1, {})
        # Не упало — OK

    def test_pending_operations_count(self):
        da = self._make_da()
        mock_om = MagicMock()
        mock_om.get_pending_operations_count.return_value = 5
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            assert da.get_pending_operations_count() == 5

    def test_pending_operations_count_no_om(self):
        da = self._make_da()
        with patch('utils.data_access.get_offline_manager', return_value=None):
            assert da.get_pending_operations_count() == 0


# ==================== DataAccess — create/update/delete с очередью ====================

class TestDataAccessCRUDWithQueue:
    """DataAccess CRUD — API-first с fallback и offline-очередь."""

    def _make_da(self, online=True):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        mock_om = MagicMock()
        mock_om.is_online.return_value = online
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            da = DataAccess(api_client=mock_api, db=mock_db)
        da._om = mock_om
        return da

    def test_create_client_online_success(self):
        da = self._make_da(online=True)
        da.api_client.create_client.return_value = {"id": 100, "name": "Новый"}
        da.db.add_client.return_value = 1
        result = da.create_client({"name": "Новый"})
        assert result is not None
        assert result["id"] == 100

    def test_create_client_api_fails_queues(self):
        """API падает с сетевой ошибкой — запись сохранена локально + в очередь."""
        from utils.api_client.exceptions import APIConnectionError
        da = self._make_da(online=True)
        da.api_client.create_client.side_effect = APIConnectionError("timeout")
        da.db.add_client.return_value = 5
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.create_client({"name": "Offline"})
        assert result is not None
        assert result["id"] == 5

    def test_update_client_online_success(self):
        da = self._make_da(online=True)
        da.api_client.update_client.return_value = {"id": 1}
        result = da.update_client(1, {"name": "Updated"})
        assert result is True
        da.db.update_client.assert_called_once()

    def test_update_client_api_fails_queues(self):
        from utils.api_client.exceptions import APITimeoutError
        da = self._make_da(online=True)
        da.api_client.update_client.side_effect = APITimeoutError("timeout")
        with patch('utils.data_access.get_offline_manager', return_value=da._om):
            result = da.update_client(1, {"name": "Updated"})
        assert result is True  # Локально обновлено
        da.db.update_client.assert_called_once()

    def test_delete_client_online_success(self):
        da = self._make_da(online=True)
        da.api_client.delete_client.return_value = True
        result = da.delete_client(1)
        assert result is True

    def test_create_client_api_returns_list(self):
        """API возвращает list вместо dict — защита от неожиданного формата."""
        da = self._make_da(online=True)
        da.api_client.create_client.return_value = [{"id": 200, "name": "Тест"}]
        da.db.add_client.return_value = 1
        result = da.create_client({"name": "Тест"})
        assert result is not None
        # Должен извлечь dict из list
        assert result["id"] == 200

    def test_update_local_id_same_id(self):
        """_update_local_id с одинаковыми ID — ничего не делает."""
        da = self._make_da()
        da._update_local_id('clients', 5, 5)
        da.db.connect.assert_not_called()

    def test_contracts_count_api_fallback(self):
        """get_contracts_count — fallback на DB при ошибке API."""
        from utils.data_access import _global_cache
        _global_cache.invalidate()
        da = self._make_da()
        da.api_client.get_contracts_count.side_effect = Exception("err")
        da.db.get_contracts_count.return_value = 42
        result = da.get_contracts_count()
        assert result == 42

    def test_contracts_count_no_db_method(self):
        """get_contracts_count — нет метода в DB → 0."""
        from utils.data_access import _global_cache
        _global_cache.invalidate()
        da = self._make_da()
        da.api_client.get_contracts_count.side_effect = Exception("err")
        # Удаляем метод из мока
        del da.db.get_contracts_count
        result = da.get_contracts_count()
        assert result == 0


# ==================== DataAccess — кеш при чтении ====================

class TestDataAccessCaching:
    """DataAccess — кеширование данных при чтении."""

    def test_cached_data_returned_without_api_call(self):
        """При повторном вызове — данные из кеша, API не вызывается."""
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        mock_api.get_clients.return_value = [{"id": 1}]
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)

        # Первый вызов — из API
        result1 = da.get_all_clients()
        assert mock_api.get_clients.call_count == 1

        # Второй вызов — из кеша
        result2 = da.get_all_clients()
        assert mock_api.get_clients.call_count == 1  # Не вырос
        assert result1 == result2

    def test_cache_invalidated_on_write(self):
        """create_client — инвалидирует кеш клиентов."""
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_db = MagicMock()
        mock_api.get_clients.return_value = [{"id": 1}]
        mock_api.create_client.return_value = {"id": 2}
        mock_db.add_client.return_value = 2
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)

        da.get_all_clients()
        assert mock_api.get_clients.call_count == 1

        # Запись — инвалидация
        da.create_client({"name": "New"})

        # Следующий read — снова из API
        da.get_all_clients()
        assert mock_api.get_clients.call_count == 2


# ==================== DataAccess — check_contract_number_exists ====================

class TestDataAccessContractNumber:
    """check_contract_number_exists — API-first с fallback."""

    def test_api_success(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_api.check_contract_number_exists.return_value = True
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=MagicMock())
        assert da.check_contract_number_exists("DP-001") is True

    def test_api_fails_fallback_db(self):
        from utils.data_access import DataAccess, _global_cache
        _global_cache.invalidate()
        mock_api = MagicMock()
        mock_api.check_contract_number_exists.side_effect = Exception("err")
        mock_db = MagicMock()
        mock_db.check_contract_number_exists.return_value = False
        with patch('utils.data_access.get_offline_manager', return_value=None):
            da = DataAccess(api_client=mock_api, db=mock_db)
        assert da.check_contract_number_exists("DP-999") is False
