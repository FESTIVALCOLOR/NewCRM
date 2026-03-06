# -*- coding: utf-8 -*-
"""
ПРОЦЕССНЫЕ ТЕСТЫ: Жизненный цикл CRM и Supervision карточек.

Проверяют СКВОЗНЫЕ бизнес-процессы:
  1. Контракт → автоматическое создание CRM карточки (safety net)
  2. CRM workflow: submit → accept/reject → client_send → client_ok
  3. Supervision lifecycle: создание → стадии → пауза → возобновление → завершение
  4. move_supervision_card: бизнес-ошибки (422) vs сетевые ошибки
  5. Консистентность: API упал → локальная БД + очередь + данные не потеряны
"""
import pytest
import sys
import os
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== Helpers ====================

def _make_data_access(api_returns=None, api_errors=None):
    """Создать DataAccess с мок API и мок DB.

    api_returns: {method: return_value}
    api_errors: {method: exception}
    """
    mock_api = MagicMock()
    mock_api.is_online = True
    mock_db = MagicMock()

    # Настройка возвратов API
    if api_returns:
        for method, value in api_returns.items():
            getattr(mock_api, method).return_value = value

    # Настройка ошибок API
    if api_errors:
        for method, exc in api_errors.items():
            getattr(mock_api, method).side_effect = exc

    with patch('utils.data_access._global_cache') as mock_cache, \
         patch('utils.data_access.get_offline_manager', return_value=None):
        mock_cache.get.return_value = None
        mock_cache.set = MagicMock()
        mock_cache.invalidate = MagicMock()

        from utils.data_access import DataAccess
        da = DataAccess.__new__(DataAccess)
        da.api_client = mock_api
        da.db = mock_db
        da._is_online = True
        da.prefer_local = False
        da._prev_api_mode = True
        # Мокаем сигналы
        da.connection_status_changed = MagicMock()
        da.operation_queued = MagicMock()
        da.pending_operations_changed = MagicMock()

    return da, mock_api, mock_db


# ==================== Contract → CRM Card auto-creation ====================

class TestContractCRMCardCreation:
    """Создание контракта автоматически создаёт CRM карточку."""

    def test_create_contract_checks_crm_card_exists(self):
        """После create_contract вызывается _ensure_crm_card_exists."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.add_contract.return_value = 1
        mock_api.create_contract.return_value = {'id': 100, 'project_type': 'Дизайн'}
        mock_api.get_crm_cards.return_value = [{'contract_id': 100}]

        with patch('utils.data_access.get_offline_manager', return_value=None), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            da.create_contract({'project_type': 'Дизайн', 'client_id': 1})

        # Проверяем что get_crm_cards был вызван для проверки
        mock_api.get_crm_cards.assert_called()

    def test_create_contract_creates_missing_crm_card(self):
        """Если CRM карточка не создана сервером → DataAccess создаёт её."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.add_contract.return_value = 1
        mock_api.create_contract.return_value = {'id': 100, 'project_type': 'Дизайн'}
        # Нет CRM карточки для этого контракта
        mock_api.get_crm_cards.return_value = []
        mock_api.create_crm_card.return_value = {'id': 200}

        with patch('utils.data_access.get_offline_manager', return_value=None), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            da.create_contract({'project_type': 'Дизайн', 'client_id': 1})

        # CRM карточка создана через API
        mock_api.create_crm_card.assert_called_once_with({
            'contract_id': 100,
            'column_name': 'Новый заказ'
        })

    def test_create_contract_supervision_no_crm_card(self):
        """Контракт Авторского надзора → CRM карточка НЕ создаётся."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.add_contract.return_value = 1
        mock_api.create_contract.return_value = {'id': 100, 'project_type': 'Авторский надзор'}

        with patch('utils.data_access.get_offline_manager', return_value=None), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            da.create_contract({'project_type': 'Авторский надзор'})

        # create_crm_card НЕ вызван для надзора
        mock_api.create_crm_card.assert_not_called()

    def test_create_contract_api_error_queues(self):
        """Ошибка API при создании контракта → операция в очереди."""
        from utils.api_client.exceptions import APIConnectionError

        da, mock_api, mock_db = _make_data_access()
        mock_db.add_contract.return_value = 1
        mock_api.create_contract.side_effect = APIConnectionError("down")

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            result = da.create_contract({'project_type': 'Дизайн'})

        # Данные сохранены локально
        mock_db.add_contract.assert_called_once()
        # Операция в очереди
        mock_om.queue_operation.assert_called_once()
        # Результат содержит локальный ID
        assert result is not None
        assert result.get('id') == 1


# ==================== CRM Workflow process ====================

class TestCRMWorkflowProcess:
    """Полный цикл workflow: submit → accept/reject → client → ok."""

    def test_workflow_full_cycle_submit_accept(self):
        """submit → accept: дизайнер сдаёт, менеджер принимает."""
        da, mock_api, _ = _make_data_access()

        # Шаг 1: Дизайнер сдаёт работу
        mock_api.workflow_submit.return_value = {'status': 'submitted', 'card_id': 1}
        result = da.workflow_submit(1)
        assert result is not None
        assert result['status'] == 'submitted'
        mock_api.workflow_submit.assert_called_once_with(1)

        # Шаг 2: Менеджер принимает
        mock_api.workflow_accept.return_value = {'status': 'accepted', 'card_id': 1}
        result = da.workflow_accept(1)
        assert result is not None
        assert result['status'] == 'accepted'
        mock_api.workflow_accept.assert_called_once_with(1)

    def test_workflow_reject_includes_corrections_path(self):
        """reject с corrections_path → путь к правкам передаётся на сервер."""
        da, mock_api, _ = _make_data_access()

        mock_api.workflow_reject.return_value = {'status': 'rejected'}
        path = '/disk/projects/001/corrections/'

        result = da.workflow_reject(1, corrections_path=path)

        assert result is not None
        mock_api.workflow_reject.assert_called_once_with(1, corrections_path=path)

    def test_workflow_reject_then_resubmit(self):
        """reject → повторный submit: полный цикл итерации."""
        da, mock_api, _ = _make_data_access()

        # Менеджер отклоняет
        mock_api.workflow_reject.return_value = {'status': 'rejected'}
        reject_result = da.workflow_reject(1, corrections_path='/disk/corrections/')
        assert reject_result['status'] == 'rejected'

        # Дизайнер исправляет и пересдаёт
        mock_api.workflow_submit.return_value = {'status': 'submitted'}
        submit_result = da.workflow_submit(1)
        assert submit_result['status'] == 'submitted'

        # Менеджер принимает
        mock_api.workflow_accept.return_value = {'status': 'accepted'}
        accept_result = da.workflow_accept(1)
        assert accept_result['status'] == 'accepted'

    def test_workflow_client_cycle(self):
        """client_send → client_ok: согласование с клиентом."""
        da, mock_api, _ = _make_data_access()

        mock_api.workflow_client_send.return_value = {'status': 'sent_to_client'}
        result = da.workflow_client_send(1)
        assert result['status'] == 'sent_to_client'

        mock_api.workflow_client_ok.return_value = {'status': 'client_approved'}
        result = da.workflow_client_ok(1)
        assert result['status'] == 'client_approved'

    def test_workflow_no_api_returns_none(self):
        """Без API все workflow-операции → None."""
        da, _, _ = _make_data_access()
        da.api_client = None

        assert da.workflow_submit(1) is None
        assert da.workflow_accept(1) is None
        assert da.workflow_reject(1) is None
        assert da.workflow_client_send(1) is None
        assert da.workflow_client_ok(1) is None
        assert da.get_workflow_state(1) is None

    def test_workflow_api_error_returns_none(self):
        """Ошибка API при workflow → None (не исключение)."""
        da, mock_api, _ = _make_data_access()
        mock_api.workflow_submit.side_effect = Exception("Server error")

        result = da.workflow_submit(1)
        assert result is None

    def test_get_workflow_state_returns_current_state(self):
        """get_workflow_state возвращает текущее состояние."""
        da, mock_api, _ = _make_data_access()
        mock_api.get_workflow_state.return_value = {
            'current_stage': 'Стадия 1',
            'is_submitted': True,
            'is_accepted': False,
            'submitted_at': '2026-01-15T10:00:00'
        }

        state = da.get_workflow_state(1)
        assert state is not None
        assert state['is_submitted'] is True
        assert state['is_accepted'] is False


# ==================== CRM Card movement process ====================

class TestCRMCardMovement:
    """Перемещение CRM карточки по колонкам через DataAccess."""

    def test_move_crm_card_updates_local_and_api(self):
        """move_crm_card → обновляет и локальную БД, и API."""
        da, mock_api, mock_db = _make_data_access()
        mock_api.move_crm_card.return_value = {'id': 1, 'column_name': 'Стадия 1'}

        with patch('utils.data_access._global_cache') as mc:
            result = da.move_crm_card(1, 'Стадия 1')

        assert result is True
        mock_db.update_crm_card_column.assert_called_once_with(1, 'Стадия 1')
        mock_api.move_crm_card.assert_called_once_with(1, 'Стадия 1')

    def test_move_crm_card_api_error_queues(self):
        """API ошибка при move → обновляется локально + операция в очереди."""
        from utils.api_client.exceptions import APIConnectionError

        da, mock_api, mock_db = _make_data_access()
        mock_api.move_crm_card.side_effect = APIConnectionError("down")

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om), \
             patch('utils.data_access._global_cache') as mc:
            result = da.move_crm_card(1, 'Стадия 2')

        assert result is True
        mock_db.update_crm_card_column.assert_called_once_with(1, 'Стадия 2')
        mock_om.queue_operation.assert_called_once()

    def test_update_crm_card_column_full_chain(self):
        """update_crm_card_column → local + API + cache invalidation."""
        da, mock_api, mock_db = _make_data_access()
        mock_api.update_crm_card.return_value = {'id': 1}

        with patch('utils.data_access._global_cache') as mc:
            result = da.update_crm_card_column(1, 'В ожидании')

        assert result is True
        mock_db.update_crm_card_column.assert_called_once_with(1, 'В ожидании')
        mock_api.update_crm_card.assert_called_once_with(1, {'column_name': 'В ожидании'})
        mc.invalidate.assert_called_with("crm_cards")


# ==================== Supervision lifecycle process ====================

class TestSupervisionLifecycleProcess:
    """Жизненный цикл карточки авторского надзора."""

    def test_create_supervision_card_with_dict(self):
        """Создание карточки надзора с полным dict."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.add_supervision_card.return_value = 1
        mock_api.create_supervision_card.return_value = {'id': 100}

        with patch('utils.data_access.get_offline_manager', return_value=None), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            result = da.create_supervision_card({
                'contract_id': 5,
                'column_name': 'Новый заказ'
            })

        assert result is not None
        assert result.get('id') == 100

    def test_create_supervision_card_with_int(self):
        """Создание карточки надзора с int (contract_id) → автоматически формирует dict."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.add_supervision_card.return_value = 1
        mock_api.create_supervision_card.return_value = {'id': 200}

        with patch('utils.data_access.get_offline_manager', return_value=None), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            result = da.create_supervision_card(5)

        # Должен вызвать API с правильным dict
        mock_api.create_supervision_card.assert_called_once_with({
            'contract_id': 5,
            'column_name': 'Новый заказ'
        })

    def test_supervision_pause_resume_cycle(self):
        """Пауза → Возобновление: полный цикл."""
        da, mock_api, mock_db = _make_data_access()

        # Пауза
        mock_api.pause_supervision_card.return_value = {'is_paused': True}
        with patch('utils.data_access.get_offline_manager', return_value=None):
            result = da.pause_supervision_card(1, reason='Ожидание материалов')
        assert result is not None
        mock_db.pause_supervision_card.assert_called_once_with(1, 'Ожидание материалов', 0)
        mock_api.pause_supervision_card.assert_called_once_with(1, 'Ожидание материалов')

        # Возобновление
        mock_api.resume_supervision_card.return_value = {'is_paused': False}
        with patch('utils.data_access.get_offline_manager', return_value=None):
            result = da.resume_supervision_card(1, employee_id=5)
        assert result is not None
        mock_db.resume_supervision_card.assert_called_once_with(1, 5)
        mock_api.resume_supervision_card.assert_called_once_with(1, 5)

    def test_supervision_complete_stage(self):
        """Завершение стадии надзора → local + API."""
        da, mock_api, mock_db = _make_data_access()

        mock_api.complete_supervision_stage.return_value = {'completed': True}

        with patch('utils.data_access.get_offline_manager', return_value=None):
            result = da.complete_supervision_stage(1, stage_name='Монтаж')

        mock_db.complete_supervision_stage.assert_called_once_with(1, stage_name='Монтаж')
        mock_api.complete_supervision_stage.assert_called_once_with(1, stage_name='Монтаж')

    def test_supervision_complete_stage_api_error_queues(self):
        """Ошибка API при complete_stage → операция в очереди."""
        from utils.api_client.exceptions import APIConnectionError

        da, mock_api, mock_db = _make_data_access()
        mock_api.complete_supervision_stage.side_effect = APIConnectionError("down")

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.complete_supervision_stage(1, stage_name='Монтаж')

        # Локально стадия всё равно завершена
        mock_db.complete_supervision_stage.assert_called_once()
        # Операция в очереди
        mock_om.queue_operation.assert_called_once()

    def test_supervision_reset_stage_completion(self):
        """Сброс стадии → local + API."""
        da, mock_api, mock_db = _make_data_access()
        mock_api.reset_supervision_stage_completion.return_value = {'reset': True}

        with patch('utils.data_access.get_offline_manager', return_value=None):
            result = da.reset_supervision_stage_completion(1)

        assert result is True
        mock_db.reset_supervision_stage_completion.assert_called_once_with(1)
        mock_api.reset_supervision_stage_completion.assert_called_once_with(1)


# ==================== move_supervision_card — бизнес vs сетевые ошибки ====================

class TestMoveSupervisionCardProcess:
    """move_supervision_card: обработка бизнес-ошибок (422/400) vs сетевых ошибок."""

    def test_move_success_updates_local(self):
        """Успешное перемещение → обновляет локальную БД."""
        da, mock_api, mock_db = _make_data_access()
        mock_api.move_supervision_card.return_value = {'id': 1, 'column_name': 'Стадия 2'}

        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=MagicMock(return_value=True))):
            result = da.move_supervision_card(1, 'Стадия 2')

        assert result is True
        mock_db.update_supervision_card_column.assert_called_with(1, 'Стадия 2')

    def test_move_422_raises_not_queued(self):
        """422 Unprocessable Entity → исключение пробрасывается наверх, НЕ в очередь."""
        from utils.api_client.exceptions import APIResponseError

        da, mock_api, mock_db = _make_data_access()
        mock_api.move_supervision_card.side_effect = APIResponseError(
            "Нельзя переместить обратно", status_code=422
        )

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            with pytest.raises(APIResponseError) as exc_info:
                da.move_supervision_card(1, 'Новый заказ')

        assert exc_info.value.status_code == 422
        # Очередь НЕ должна быть вызвана
        mock_om.queue_operation.assert_not_called()
        # Локальная БД НЕ обновлена (бизнес-ошибка)
        mock_db.update_supervision_card_column.assert_not_called()

    def test_move_400_raises_not_queued(self):
        """400 Bad Request → исключение пробрасывается наверх."""
        from utils.api_client.exceptions import APIResponseError

        da, mock_api, mock_db = _make_data_access()
        mock_api.move_supervision_card.side_effect = APIResponseError("Bad Request", status_code=400)

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            with pytest.raises(APIResponseError):
                da.move_supervision_card(1, 'Invalid Column')

        mock_om.queue_operation.assert_not_called()

    def test_move_network_error_queues_and_updates_local(self):
        """Сетевая ошибка → обновляет локально + ставит в очередь."""
        from utils.api_client.exceptions import APIConnectionError

        da, mock_api, mock_db = _make_data_access()
        mock_api.move_supervision_card.side_effect = APIConnectionError("Connection refused")

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.move_supervision_card(1, 'Стадия 2')

        assert result is True
        mock_db.update_supervision_card_column.assert_called_with(1, 'Стадия 2')
        mock_om.queue_operation.assert_called_once()

    def test_move_timeout_queues_and_updates_local(self):
        """Таймаут → обновляет локально + ставит в очередь."""
        from utils.api_client.exceptions import APITimeoutError

        da, mock_api, mock_db = _make_data_access()
        mock_api.move_supervision_card.side_effect = APITimeoutError("Timed out")

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.move_supervision_card(1, 'Стадия 3')

        assert result is True
        mock_db.update_supervision_card_column.assert_called_with(1, 'Стадия 3')
        mock_om.queue_operation.assert_called_once()

    def test_move_offline_updates_local_and_queues(self):
        """Offline режим → обновляет локально + ставит в очередь."""
        da, mock_api, mock_db = _make_data_access()

        mock_om = MagicMock()
        mock_om.is_online.return_value = False

        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.move_supervision_card(1, 'Стадия 1')

        assert result is True
        mock_db.update_supervision_card_column.assert_called_with(1, 'Стадия 1')
        mock_om.queue_operation.assert_called_once()


# ==================== Data consistency rules ====================

class TestDataConsistency:
    """Консистентность данных: локальная БД + API + кеш."""

    def test_create_contract_invalidates_contracts_and_crm_cards(self):
        """create_contract инвалидирует оба кеша: contracts и crm_cards."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.add_contract.return_value = 1
        mock_api.create_contract.return_value = {'id': 100, 'project_type': 'Дизайн'}
        mock_api.get_crm_cards.return_value = [{'contract_id': 100}]

        invalidated = []
        with patch('utils.data_access._global_cache') as mc, \
             patch('utils.data_access.get_offline_manager', return_value=None):
            mc.get.return_value = None
            mc.invalidate.side_effect = lambda p: invalidated.append(p)
            da.create_contract({'project_type': 'Дизайн'})

        assert 'contracts' in invalidated
        assert 'crm_cards' in invalidated

    def test_delete_contract_deletes_crm_card_locally(self):
        """Удаление контракта → удаляется связанная CRM карточка в локальной БД."""
        da, mock_api, mock_db = _make_data_access()
        mock_api.delete_contract.return_value = True
        mock_db.get_crm_card_id_by_contract.return_value = 10
        mock_db.delete_order.return_value = True

        with patch('utils.data_access.get_offline_manager', return_value=MagicMock(is_online=MagicMock(return_value=True))):
            result = da.delete_contract(5)

        assert result is True
        mock_db.get_crm_card_id_by_contract.assert_called_once_with(5)
        mock_db.delete_order.assert_called_once_with(5, 10)

    def test_delete_contract_offline_queues_and_deletes_locally(self):
        """Удаление контракта в offline → локально удалить + в очередь."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.get_crm_card_id_by_contract.return_value = 10
        mock_db.delete_order.return_value = True

        mock_om = MagicMock()
        mock_om.is_online.return_value = False

        with patch('utils.data_access.get_offline_manager', return_value=mock_om):
            result = da.delete_contract(5)

        assert result is True
        mock_db.delete_order.assert_called_once()
        mock_om.queue_operation.assert_called_once()

    def test_api_error_on_create_preserves_local_data(self):
        """API ошибка при создании → данные сохранены локально."""
        from utils.api_client.exceptions import APIConnectionError

        da, mock_api, mock_db = _make_data_access()
        mock_db.add_client.return_value = 42
        mock_api.create_client.side_effect = APIConnectionError("down")

        mock_om = MagicMock()
        with patch('utils.data_access.get_offline_manager', return_value=mock_om), \
             patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            result = da.create_client({'full_name': 'Important Client'})

        # Данные сохранены локально
        mock_db.add_client.assert_called_once_with({'full_name': 'Important Client'})
        # Результат содержит локальные данные
        assert result is not None
        assert result['id'] == 42
        assert result['full_name'] == 'Important Client'
        # Операция в очереди для синхронизации позже
        mock_om.queue_operation.assert_called_once()

    def test_supervision_db_error_doesnt_block_api(self):
        """Ошибка локальной БД при supervision → API всё равно вызывается."""
        da, mock_api, mock_db = _make_data_access()
        mock_db.complete_supervision_stage.side_effect = Exception("DB locked")
        mock_api.complete_supervision_stage.return_value = {'completed': True}

        with patch('utils.data_access.get_offline_manager', return_value=None):
            result = da.complete_supervision_stage(1, stage_name='Монтаж')

        # API вызван несмотря на ошибку DB
        mock_api.complete_supervision_stage.assert_called_once()

    def test_fallback_chain_api_fails_then_db(self):
        """Чтение: API упал → читаем из локальной БД."""
        da, mock_api, mock_db = _make_data_access()
        mock_api.get_crm_card.side_effect = Exception("API down")
        mock_db.get_crm_card_data.return_value = {
            'id': 1, 'contract_id': 5, 'column_name': 'Стадия 1'
        }

        with patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            result = da.get_crm_card(1)

        assert result is not None
        assert result['column_name'] == 'Стадия 1'
        mock_db.get_crm_card_data.assert_called_once_with(1)

    def test_prefer_local_reads_from_db(self):
        """prefer_local=True → читаем из DB, не из API."""
        da, mock_api, mock_db = _make_data_access()
        da.prefer_local = True
        mock_db.get_all_clients.return_value = [{'id': 1, 'full_name': 'Local Client'}]

        with patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            result = da.get_all_clients()

        # API НЕ вызван
        mock_api.get_clients.assert_not_called()
        # Данные из БД
        assert len(result) == 1
        assert result[0]['full_name'] == 'Local Client'

    def test_cache_mode_switch_invalidates(self):
        """Переключение API/local → кеш инвалидируется."""
        da, mock_api, mock_db = _make_data_access()
        da._prev_api_mode = True
        da.prefer_local = True  # Теперь _should_use_api() = False

        with patch('utils.data_access._global_cache') as mc:
            mc.get.return_value = None
            mock_db.get_all_clients.return_value = []
            da.get_all_clients()

        # Кеш должен быть очищен при смене режима
        mc.invalidate.assert_called()
