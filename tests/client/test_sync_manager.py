# -*- coding: utf-8 -*-
"""
Тесты для utils/sync_manager.py — SyncManager, EditLockContext.

Этап 9: Мелкие модули и gaps.
PyQt5 замокан — тесты запускаются в CI без GUI.
"""
import sys
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock, call
from datetime import datetime
from types import SimpleNamespace

import pytest

# Мокаем PyQt5 ДО импорта sync_manager
# Создаём стабильные моки без side_effect проблем
_mock_pyqt5 = MagicMock()
_mock_qtcore = MagicMock()
_mock_qtwidgets = MagicMock()
_mock_qtgui = MagicMock()

# Делаем pyqtSignal возвращающим MagicMock (дескриптор)
_mock_qtcore.pyqtSignal = MagicMock(return_value=MagicMock())

# QObject.__init__ не должен делать ничего
_mock_qtcore.QObject = type('MockQObject', (), {'__init__': lambda self, *a, **kw: None})

# QTimer — мок, который ведёт себя как объект с нужными методами
class MockQTimer:
    def __init__(self, *args, **kwargs):
        self.timeout = MagicMock()
        self.timeout.connect = MagicMock()
        self._interval = 0
    def start(self, interval=0):
        self._interval = interval
    def stop(self):
        pass
    @staticmethod
    def singleShot(ms, callback):
        pass

_mock_qtcore.QTimer = MockQTimer

sys.modules['PyQt5'] = _mock_pyqt5
sys.modules['PyQt5.QtCore'] = _mock_qtcore
sys.modules['PyQt5.QtWidgets'] = _mock_qtwidgets
sys.modules['PyQt5.QtGui'] = _mock_qtgui

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Импортируем ПОСЛЕ мокирования PyQt5
from utils.sync_manager import SyncManager, EditLockContext


# ============================================================================
# ХЕЛПЕРЫ
# ============================================================================

def _make_response(status_code=200, json_data=None):
    """Создать mock Response"""
    resp = MagicMock()
    resp.status_code = status_code
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


@pytest.fixture
def mock_api():
    """Mock API клиент"""
    api = MagicMock()
    api.is_online = True
    api.base_url = "http://test-server:8000"
    return api


@pytest.fixture
def sync_manager(mock_api):
    """SyncManager с замоканным API клиентом"""
    sm = SyncManager(api_client=mock_api, employee_id=1)
    return sm


# ============================================================================
# ИНИЦИАЛИЗАЦИЯ
# ============================================================================

class TestSyncManagerInit:
    """Инициализация SyncManager"""

    def test_init_default_state(self, sync_manager, mock_api):
        """Начальное состояние после создания."""
        assert sync_manager.api_client is mock_api
        assert sync_manager.employee_id == 1
        assert sync_manager.is_running is False
        assert sync_manager.is_connected is False
        assert sync_manager._sync_paused is False
        assert sync_manager._sync_in_progress is False

    def test_init_locked_records_empty(self, sync_manager):
        """Кеш блокировок — пустой словарь."""
        assert sync_manager._locked_records == {}

    def test_init_online_users_empty(self, sync_manager):
        """Кеш онлайн-пользователей — пустой список."""
        assert sync_manager._online_users == []

    def test_init_update_handlers(self, sync_manager):
        """Обработчики обновлений — все ключи присутствуют."""
        expected_keys = ['clients', 'contracts', 'employees', 'crm_cards',
                         'supervision_cards', 'payments']
        for key in expected_keys:
            assert key in sync_manager._update_handlers

    def test_constants(self, sync_manager):
        """Константы — корректные значения."""
        assert sync_manager.DEFAULT_SYNC_INTERVAL == 30000
        assert sync_manager.HEARTBEAT_INTERVAL == 60000
        assert sync_manager.LOCK_TIMEOUT == 120


# ============================================================================
# START / STOP
# ============================================================================

class TestStartStop:
    """start() / stop() менеджера синхронизации"""

    def test_start_sets_running(self, sync_manager):
        """start() — устанавливает is_running=True."""
        sync_manager.start()
        assert sync_manager.is_running is True
        assert sync_manager.last_sync_timestamp is not None

    def test_start_idempotent(self, sync_manager):
        """Повторный start() — ничего не делает."""
        sync_manager.start()
        ts1 = sync_manager.last_sync_timestamp
        sync_manager.start()  # повторный вызов
        # timestamp не должен измениться
        assert sync_manager.last_sync_timestamp == ts1

    def test_stop_sets_not_running(self, sync_manager):
        """stop() — устанавливает is_running=False."""
        sync_manager.start()
        sync_manager.stop()
        assert sync_manager.is_running is False

    def test_stop_idempotent(self, sync_manager):
        """Повторный stop() — ничего не делает."""
        sync_manager.stop()  # уже не запущен
        assert sync_manager.is_running is False

    def test_stop_releases_locks(self, sync_manager, mock_api):
        """stop() — освобождает все блокировки."""
        sync_manager.start()
        sync_manager._locked_records = {
            'client': {1: '1', 2: '1'},
            'contract': {10: '1'}
        }
        sync_manager.stop()
        assert sync_manager._locked_records == {}

    def test_start_with_custom_interval(self, sync_manager):
        """start(sync_interval=5000) — принимает кастомный интервал."""
        sync_manager.start(sync_interval=5000)
        assert sync_manager.is_running is True


# ============================================================================
# PAUSE / RESUME
# ============================================================================

class TestPauseResume:
    """pause_sync() / resume_sync()"""

    def test_pause_sync(self, sync_manager):
        """pause_sync() устанавливает _sync_paused=True."""
        sync_manager.pause_sync()
        assert sync_manager._sync_paused is True

    def test_resume_sync(self, sync_manager):
        """resume_sync() устанавливает _sync_paused=False."""
        sync_manager.pause_sync()
        sync_manager.resume_sync()
        assert sync_manager._sync_paused is False


# ============================================================================
# _sync_data GUARDS
# ============================================================================

class TestSyncDataGuards:
    """_sync_data — проверки перед синхронизацией"""

    def test_sync_data_no_api_client(self, sync_manager):
        """_sync_data — без api_client ничего не делает."""
        sync_manager.api_client = None
        sync_manager.last_sync_timestamp = datetime.utcnow()
        sync_manager._sync_data()  # не должно упасть

    def test_sync_data_no_timestamp(self, sync_manager):
        """_sync_data — без last_sync_timestamp ничего не делает."""
        sync_manager.last_sync_timestamp = None
        sync_manager._sync_data()  # не должно упасть

    def test_sync_data_offline_skipped(self, sync_manager, mock_api):
        """_sync_data — при offline пропускается."""
        mock_api.is_online = False
        sync_manager.last_sync_timestamp = datetime.utcnow()
        sync_manager._sync_data()
        assert sync_manager._sync_in_progress is False

    def test_sync_data_paused_skipped(self, sync_manager):
        """_sync_data — при паузе пропускается."""
        sync_manager.last_sync_timestamp = datetime.utcnow()
        sync_manager._sync_paused = True
        sync_manager._sync_data()
        assert sync_manager._sync_in_progress is False


# ============================================================================
# LOCK / UNLOCK RECORDS
# ============================================================================

class TestLockUnlock:
    """lock_record / unlock_record / is_record_locked"""

    def test_lock_record_success(self, sync_manager, mock_api):
        """lock_record — успешная блокировка."""
        mock_api._request.return_value = _make_response(200)
        result = sync_manager.lock_record('client', 1)
        assert result is True
        assert sync_manager._locked_records.get('client', {}).get(1) == '1'

    def test_lock_record_conflict(self, sync_manager, mock_api):
        """lock_record — 409 конфликт → False."""
        mock_api._request.return_value = _make_response(409, {
            "locked_by": "Другой пользователь"
        })
        result = sync_manager.lock_record('client', 1)
        assert result is False

    def test_lock_record_no_api_client(self, sync_manager):
        """lock_record без api_client — True (оффлайн режим)."""
        sync_manager.api_client = None
        result = sync_manager.lock_record('client', 1)
        assert result is True

    def test_lock_record_exception(self, sync_manager, mock_api):
        """lock_record — исключение → True (оптимистичный подход)."""
        mock_api._request.side_effect = Exception("Network error")
        result = sync_manager.lock_record('client', 1)
        assert result is True

    def test_unlock_record(self, sync_manager, mock_api):
        """unlock_record — разблокировка."""
        sync_manager._locked_records = {'client': {1: '1'}}
        mock_api._request.return_value = _make_response(200)
        sync_manager.unlock_record('client', 1)
        assert 1 not in sync_manager._locked_records.get('client', {})

    def test_unlock_record_no_api_client(self, sync_manager):
        """unlock_record без api_client — ничего не делает."""
        sync_manager.api_client = None
        sync_manager.unlock_record('client', 1)  # не должно упасть

    def test_is_record_locked_api(self, sync_manager, mock_api):
        """is_record_locked — проверка через API."""
        mock_api._request.return_value = _make_response(200, {
            "is_locked": True, "locked_by": "Admin"
        })
        is_locked, locked_by = sync_manager.is_record_locked('client', 1)
        assert is_locked is True
        assert locked_by == "Admin"

    def test_is_record_locked_no_api(self, sync_manager):
        """is_record_locked без api_client — (False, None)."""
        sync_manager.api_client = None
        result = sync_manager.is_record_locked('client', 1)
        assert result == (False, None)


# ============================================================================
# ONLINE USERS
# ============================================================================

class TestOnlineUsers:
    """get_online_users / get_online_users_count"""

    def test_get_online_users_returns_copy(self, sync_manager):
        """get_online_users — возвращает копию."""
        sync_manager._online_users = [{"id": 1, "name": "Admin"}]
        users = sync_manager.get_online_users()
        assert users == [{"id": 1, "name": "Admin"}]
        # Модификация не влияет на оригинал
        users.append({"id": 2})
        assert len(sync_manager._online_users) == 1

    def test_get_online_users_count(self, sync_manager):
        """get_online_users_count — количество."""
        sync_manager._online_users = [{"id": 1}, {"id": 2}]
        assert sync_manager.get_online_users_count() == 2

    def test_get_online_users_count_empty(self, sync_manager):
        """get_online_users_count — 0 при пустом списке."""
        assert sync_manager.get_online_users_count() == 0


# ============================================================================
# SUBSCRIPTION API
# ============================================================================

class TestSubscription:
    """subscribe / unsubscribe / set_sync_entity_types"""

    def test_subscribe(self, sync_manager):
        """subscribe — добавляет handler."""
        handler = MagicMock()
        sync_manager.subscribe('clients', handler)
        assert handler in sync_manager._update_handlers['clients']

    def test_subscribe_unknown_type(self, sync_manager):
        """subscribe — неизвестный entity_type не падает."""
        handler = MagicMock()
        sync_manager.subscribe('unknown_type', handler)
        # Просто не добавляет (ключа нет)
        assert 'unknown_type' not in sync_manager._update_handlers

    def test_unsubscribe(self, sync_manager):
        """unsubscribe — удаляет handler."""
        handler = MagicMock()
        sync_manager._update_handlers['clients'] = [handler]
        sync_manager.unsubscribe('clients', handler)
        assert handler not in sync_manager._update_handlers['clients']

    def test_unsubscribe_missing_handler(self, sync_manager):
        """unsubscribe — несуществующий handler не падает."""
        handler = MagicMock()
        sync_manager.unsubscribe('clients', handler)  # не должно быть ошибки

    def test_set_sync_entity_types(self, sync_manager):
        """set_sync_entity_types — меняет список типов."""
        sync_manager.set_sync_entity_types(['clients'])
        assert sync_manager._sync_entity_types == ['clients']


# ============================================================================
# SET SYNC INTERVAL / FORCE SYNC
# ============================================================================

class TestSyncControls:
    """set_sync_interval / force_sync"""

    def test_set_sync_interval_when_running(self, sync_manager):
        """set_sync_interval — при запущенном менеджере."""
        sync_manager.is_running = True
        sync_manager.set_sync_interval(10000)
        # Не должно упасть (QTimer замокан)

    def test_set_sync_interval_when_not_running(self, sync_manager):
        """set_sync_interval — при незапущенном менеджере — ничего не делает."""
        sync_manager.is_running = False
        sync_manager.set_sync_interval(10000)
        # _sync_timer.stop/start не вызываются

    def test_force_sync(self, sync_manager, mock_api):
        """force_sync — вызывает _sync_data."""
        sync_manager.last_sync_timestamp = datetime.utcnow()
        # Не должно упасть даже если sync_data не делает ничего
        sync_manager.force_sync()


# ============================================================================
# _process_sync_result
# ============================================================================

class TestProcessSyncResult:
    """_process_sync_result — обработка данных от сервера"""

    def test_process_sync_result_with_data(self, sync_manager):
        """_process_sync_result — обрабатывает клиентов, договоры, сотрудников."""
        sync_manager._sync_in_progress = True
        result = {
            'timestamp': '2025-01-01T00:00:00Z',
            'clients': [{'id': 1}],
            'contracts': [{'id': 2}],
            'employees': [{'id': 3}]
        }
        sync_manager._process_sync_result(result)
        assert sync_manager._sync_in_progress is False
        assert sync_manager.is_connected is True

    def test_process_sync_result_empty(self, sync_manager):
        """_process_sync_result — пустой результат не падает."""
        sync_manager._sync_in_progress = True
        result = {}
        sync_manager._process_sync_result(result)
        assert sync_manager._sync_in_progress is False

    def test_process_sync_result_paused_ignored(self, sync_manager):
        """_process_sync_result — при паузе результат игнорируется."""
        sync_manager._sync_in_progress = True
        sync_manager._sync_paused = True
        result = {'clients': [{'id': 1}]}
        sync_manager._process_sync_result(result)
        assert sync_manager._sync_in_progress is False


# ============================================================================
# _on_sync_error
# ============================================================================

class TestOnSyncError:
    """_on_sync_error — обработка ошибки синхронизации"""

    def test_on_sync_error_disconnects(self, sync_manager):
        """_on_sync_error — при is_connected=True переключает на False."""
        sync_manager._sync_in_progress = True
        sync_manager.is_connected = True
        sync_manager._on_sync_error()
        assert sync_manager._sync_in_progress is False
        assert sync_manager.is_connected is False

    def test_on_sync_error_already_disconnected(self, sync_manager):
        """_on_sync_error — при is_connected=False ничего не меняет."""
        sync_manager._sync_in_progress = True
        sync_manager.is_connected = False
        sync_manager._on_sync_error()
        assert sync_manager.is_connected is False


# ============================================================================
# _send_heartbeat GUARDS
# ============================================================================

class TestSendHeartbeat:
    """_send_heartbeat — проверки перед отправкой"""

    def test_heartbeat_no_api_client(self, sync_manager):
        """_send_heartbeat — без api_client ничего не делает."""
        sync_manager.api_client = None
        sync_manager._send_heartbeat()  # не падает

    def test_heartbeat_offline_skipped(self, sync_manager, mock_api):
        """_send_heartbeat — при offline пропускается."""
        mock_api.is_online = False
        sync_manager._send_heartbeat()
        mock_api._request.assert_not_called()


# ============================================================================
# EditLockContext
# ============================================================================

class TestEditLockContext:
    """EditLockContext — контекстный менеджер блокировки"""

    def test_context_acquired(self, sync_manager, mock_api):
        """Успешная блокировка — acquired=True."""
        mock_api._request.return_value = _make_response(200)
        with EditLockContext(sync_manager, 'client', 1) as lock:
            assert lock.acquired is True

    def test_context_not_acquired(self, sync_manager, mock_api):
        """Конфликт — acquired=False, locked_by заполнен."""
        mock_api._request.side_effect = [
            _make_response(409, {"locked_by": "Admin"}),  # lock_record → 409
            _make_response(200, {"is_locked": True, "locked_by": "Admin"})  # is_record_locked
        ]
        with EditLockContext(sync_manager, 'client', 1) as lock:
            assert lock.acquired is False
            assert lock.locked_by == "Admin"

    def test_context_unlock_on_exit(self, sync_manager, mock_api):
        """При выходе из контекста — разблокировка."""
        mock_api._request.return_value = _make_response(200)
        with EditLockContext(sync_manager, 'client', 1):
            pass
        # unlock_record вызван (DELETE запрос)
        calls = mock_api._request.call_args_list
        # Последний вызов — DELETE для unlock
        assert any(c[0][0] == 'DELETE' for c in calls)

    def test_context_no_sync_manager(self):
        """Без sync_manager — acquired=True, unlock не вызывается."""
        with EditLockContext(None, 'client', 1) as lock:
            assert lock.acquired is True

    def test_context_not_acquired_no_unlock(self, sync_manager, mock_api):
        """При неуспешной блокировке — unlock НЕ вызывается."""
        mock_api._request.side_effect = [
            _make_response(409, {"locked_by": "Other"}),  # lock_record → 409
            _make_response(200, {"is_locked": True, "locked_by": "Other"})  # is_record_locked
        ]
        with EditLockContext(sync_manager, 'client', 1) as lock:
            pass
        # Не должно быть DELETE вызова (unlock не нужен)
        calls = mock_api._request.call_args_list
        delete_calls = [c for c in calls if c[0][0] == 'DELETE']
        assert len(delete_calls) == 0
