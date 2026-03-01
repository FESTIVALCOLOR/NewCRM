# -*- coding: utf-8 -*-
"""
Тесты для ui/crm_supervision_tab.py — CRMSupervisionTab.

Покрытие:
- on_card_moved (правила перемещения, guard-условия)
- submit_work (сдача работы ДАН)
- accept_work (принятие работы менеджером)
- pause_card / resume_card (приостановка/возобновление)
- SUPERVISION_STAGE_MAPPING (маппинг стадий)
- init_ui / is_dan_role
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock, call
from PyQt5.QtWidgets import QDialog

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class _FakeIconLoader:
    """Заглушка для IconLoader, не требует реальных SVG."""
    @staticmethod
    def load(name):
        from PyQt5.QtGui import QIcon
        return QIcon()

    @staticmethod
    def create_icon_button(icon_name, text='', tooltip='', icon_size=16):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton(text)
        btn.setToolTip(tooltip)
        return btn

    @staticmethod
    def create_action_button(icon_name, tooltip=''):
        from PyQt5.QtWidgets import QPushButton
        btn = QPushButton()
        btn.setToolTip(tooltip)
        return btn


@pytest.fixture
def employee_manager():
    return {
        'id': 1,
        'full_name': 'Руководитель',
        'position': 'Руководитель студии',
        'secondary_position': '',
    }


@pytest.fixture
def employee_dan():
    return {
        'id': 2,
        'full_name': 'Дизайнер',
        'position': 'ДАН',
        'secondary_position': '',
    }


def _create_supervision_tab(qtbot, employee, mock_patches=None):
    """Фабрика для создания CRMSupervisionTab с моками."""
    with patch('ui.crm_supervision_tab.IconLoader', _FakeIconLoader), \
         patch('ui.crm_supervision_tab.DatabaseManager'), \
         patch('ui.crm_supervision_tab.DataAccess') as MockDA, \
         patch('ui.crm_supervision_tab.YandexDiskManager'), \
         patch('ui.crm_supervision_tab.YANDEX_DISK_TOKEN', 'fake'), \
         patch('ui.crm_supervision_tab.resource_path', side_effect=lambda x: x), \
         patch('ui.crm_supervision_tab.ICONS_PATH', '/fake/icons'), \
         patch('ui.crm_supervision_tab.TableSettings'), \
         patch('ui.crm_supervision_tab.apply_no_focus_delegate'), \
         patch('ui.crm_supervision_tab.ProportionalResizeTable', MagicMock()), \
         patch('ui.crm_supervision_tab._has_perm', side_effect=lambda emp, api, perm: perm != 'supervision.move' or emp.get('position', '') not in ('ДАН', 'Дизайнер', 'Чертёжник', 'Замерщик', 'Менеджер')):

        mock_da = MockDA.return_value
        mock_da.get_supervision_cards.return_value = []
        mock_da.get_archived_supervision_cards.return_value = []
        mock_da.get_supervision_card.return_value = None

        from ui.crm_supervision_tab import CRMSupervisionTab
        tab = CRMSupervisionTab(employee, api_client=MagicMock())
        qtbot.addWidget(tab)
        return tab, mock_da


@pytest.fixture
def manager_tab(qtbot, employee_manager):
    """CRMSupervisionTab для менеджера."""
    tab, mock_da = _create_supervision_tab(qtbot, employee_manager)
    return tab, mock_da


@pytest.fixture
def dan_tab(qtbot, employee_dan):
    """CRMSupervisionTab для ДАН."""
    tab, mock_da = _create_supervision_tab(qtbot, employee_dan)
    return tab, mock_da


# ==================== SUPERVISION_STAGE_MAPPING ====================

class TestSupervisionStageMapping:
    """SUPERVISION_STAGE_MAPPING — маппинг стадий."""

    def test_has_12_stages(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert len(SUPERVISION_STAGE_MAPPING) == 12

    def test_stage1_mapped(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert SUPERVISION_STAGE_MAPPING['Стадия 1: Закупка керамогранита'] == 'STAGE_1_CERAMIC'

    def test_stage12_mapped(self):
        from ui.crm_supervision_tab import SUPERVISION_STAGE_MAPPING
        assert SUPERVISION_STAGE_MAPPING['Стадия 12: Закупка декора'] == 'STAGE_12_DECOR'


# ==================== is_dan_role ====================

class TestIsDanRole:
    """Определение роли ДАН."""

    def test_manager_is_not_dan(self, manager_tab):
        tab, _ = manager_tab
        assert tab.is_dan_role is False

    def test_dan_is_dan(self, dan_tab):
        tab, _ = dan_tab
        assert tab.is_dan_role is True

    def test_secondary_position_dan(self, qtbot):
        """secondary_position='ДАН' → is_dan_role=True."""
        emp = {
            'id': 3, 'full_name': 'Тест', 'position': 'Менеджер',
            'secondary_position': 'ДАН',
        }
        tab, _ = _create_supervision_tab(qtbot, emp)
        assert tab.is_dan_role is True


# ==================== init_ui ====================

class TestInitUI:
    """Структура UI."""

    def test_has_tabs(self, manager_tab):
        tab, _ = manager_tab
        assert tab.tabs is not None

    def test_manager_has_archive_tab(self, manager_tab):
        """Менеджер видит вкладку Архив."""
        tab, _ = manager_tab
        assert tab.tabs.count() >= 2

    def test_dan_no_archive_tab(self, dan_tab):
        """ДАН не видит вкладку Архив."""
        tab, _ = dan_tab
        assert tab.tabs.count() == 1


# ==================== on_card_moved ====================

class TestOnCardMoved:
    """on_card_moved — правила перемещения."""

    def test_block_move_back_to_new_order(self, manager_tab):
        """Нельзя вернуться в 'Новый заказ' из другого столбца."""
        tab, mock_da = manager_tab
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch('ui.crm_supervision_tab.CustomMessageBox') as mock_msg:
            mock_msg.return_value.exec_.return_value = None
            tab.on_card_moved(1, 'Стадия 1: Закупка керамогранита', 'Новый заказ')
            mock_msg.assert_called_once()

    def test_allow_move_from_new_order(self, manager_tab):
        """'Новый заказ' → 'Новый заказ' — не блокируется (no-op)."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'dan_id': 1, 'senior_manager_id': 2, 'dan_completed': 0, 'dan_name': 'ДАН'
        }
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionStageDeadlineDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(1, 'Новый заказ', 'Стадия 1: Закупка керамогранита')
            mock_da.move_supervision_card.assert_called_with(1, 'Стадия 1: Закупка керамогранита')

    def test_block_pending_to_wrong_column(self, manager_tab):
        """Из 'В ожидании' нельзя в столбец, отличный от previous_column."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'previous_column': 'Стадия 3: Закупка оборудования'
        }
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox') as mock_msg:
            mock_msg.return_value.exec_.return_value = None
            tab.on_card_moved(1, 'В ожидании', 'Стадия 1: Закупка керамогранита')
            mock_msg.assert_called_once()

    def test_allow_pending_to_previous_column(self, manager_tab):
        """Из 'В ожидании' можно в previous_column."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'previous_column': 'Стадия 3: Закупка оборудования',
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 0, 'dan_name': 'ДАН'
        }
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionStageDeadlineDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(1, 'В ожидании', 'Стадия 3: Закупка оборудования')
            mock_da.move_supervision_card.assert_called_with(1, 'Стадия 3: Закупка оборудования')

    def test_allow_pending_to_completed(self, manager_tab):
        """Из 'В ожидании' можно в 'Выполненный проект'."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'previous_column': 'Стадия 1: Закупка керамогранита',
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 0, 'dan_name': 'ДАН'
        }
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionCompletionDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(1, 'В ожидании', 'Выполненный проект')
            mock_da.move_supervision_card.assert_called_with(1, 'Выполненный проект')

    def test_block_move_when_dan_submitted(self, manager_tab):
        """Нельзя переместить если ДАН сдал, но не принято (dan_completed=1)."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 1, 'dan_name': 'ДАН'
        }
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox') as mock_msg:
            mock_msg.return_value.exec_.return_value = None
            tab.on_card_moved(
                1, 'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники'
            )
            mock_msg.assert_called_once()

    def test_auto_accept_by_manager(self, manager_tab):
        """Руководитель перемещает при dan_completed=0 → автопринятие."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 0, 'dan_name': 'Тестовый ДАН',
            'contract_id': 10,
        }
        mock_da.execute_raw_query.return_value = [{'contract_id': 10}]
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionStageDeadlineDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(
                1, 'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники'
            )
            mock_da.add_supervision_history.assert_called()

    def test_resets_completion_on_move(self, manager_tab):
        """При перемещении сбрасывает отметку о сдаче."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 0, 'dan_name': 'ДАН'
        }
        mock_da.execute_raw_query.return_value = [{'contract_id': 10}]
        mock_da.execute_raw_update.return_value = 0
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionStageDeadlineDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(
                1, 'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники'
            )
            mock_da.reset_supervision_stage_completion.assert_called_with(1)

    def test_sync_paused_and_resumed(self, manager_tab):
        """Синхронизация приостанавливается и возобновляется при перемещении."""
        tab, mock_da = manager_tab
        mock_sync = MagicMock()
        mock_da.get_supervision_card.return_value = {
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 0, 'dan_name': 'ДАН'
        }
        mock_da.execute_raw_query.return_value = [{'contract_id': 10}]
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=mock_sync), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionStageDeadlineDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(
                1, 'Стадия 1: Закупка керамогранита', 'Стадия 2: Закупка сантехники'
            )
            mock_sync.pause_sync.assert_called_once()
            mock_sync.resume_sync.assert_called_once()

    def test_error_shows_critical_message(self, manager_tab):
        """Ошибка при перемещении — показывает CustomMessageBox с типом 'error'."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.side_effect = Exception('DB error')
        mock_msg = MagicMock()
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=mock_msg) as mock_cls:
            tab.on_card_moved(
                1, 'Новый заказ', 'Стадия 1: Закупка керамогранита'
            )
            mock_cls.assert_called_once()
            call_args = mock_cls.call_args
            assert call_args[0][3] == 'error'  # тип сообщения

    def test_move_to_completed_shows_dialog(self, manager_tab):
        """Перемещение в 'Выполненный проект' открывает SupervisionCompletionDialog."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'dan_id': 1, 'senior_manager_id': 2,
            'dan_completed': 0, 'dan_name': 'ДАН'
        }
        mock_da.execute_raw_query.return_value = [{'contract_id': 10}]
        mock_da.execute_raw_update.return_value = 0
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.SupervisionCompletionDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(
                1, 'Стадия 12: Закупка декора', 'Выполненный проект'
            )
            MockDlg.assert_called_once()

    def test_no_executors_shows_assign_dialog(self, manager_tab):
        """Нет исполнителей → открывает AssignExecutorsDialog."""
        tab, mock_da = manager_tab
        mock_da.get_supervision_card.return_value = {
            'dan_id': None, 'senior_manager_id': None,
            'dan_completed': 0, 'dan_name': None
        }
        with patch.object(tab, 'load_cards_for_current_tab'), \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.AssignExecutorsDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Rejected
            tab.on_card_moved(
                1, 'Новый заказ', 'Стадия 1: Закупка керамогранита'
            )
            MockDlg.assert_called_once()

    def test_dan_cannot_move_still_unassigned(self, manager_tab):
        """После назначения исполнителей всё ещё не назначены → отмена."""
        tab, mock_da = manager_tab
        # Первый вызов — нет исполнителей, второй — всё ещё нет
        mock_da.get_supervision_card.side_effect = [
            {'dan_id': None, 'senior_manager_id': None, 'dan_completed': 0, 'dan_name': None},
            {'dan_id': None, 'senior_manager_id': None},
        ]
        with patch.object(tab, 'load_cards_for_current_tab') as mock_reload, \
             patch.object(tab, '_get_sync_manager', return_value=None), \
             patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox', return_value=MagicMock()), \
             patch('ui.crm_supervision_tab.AssignExecutorsDialog') as MockDlg:
            MockDlg.return_value.exec_.return_value = QDialog.Accepted
            tab.on_card_moved(1, 'Новый заказ', 'Стадия 1: Закупка керамогранита')
            # Карточки перезагружены (отмена перемещения)
            mock_reload.assert_called()
            mock_da.move_supervision_card.assert_not_called()


# ==================== save_termination_reason ====================

class TestSaveTerminationReason:
    """save_termination_reason — сохранение причины расторжения."""

    def test_empty_reason_shows_warning(self, manager_tab):
        """Пустая причина → предупреждение."""
        tab, mock_da = manager_tab
        mock_dialog = MagicMock()
        with patch('ui.crm_supervision_tab.QMessageBox'), \
             patch('ui.crm_supervision_tab.CustomMessageBox') as mock_msg:
            mock_msg.return_value.exec_.return_value = None
            tab.save_termination_reason(1, '   ', mock_dialog)
            mock_msg.assert_called_once()
            mock_dialog.accept.assert_not_called()

    def test_valid_reason_saves(self, manager_tab):
        """Валидная причина → сохранение и закрытие диалога."""
        tab, mock_da = manager_tab
        mock_dialog = MagicMock()
        tab.save_termination_reason(1, 'Клиент отказался', mock_dialog)
        mock_da.update_contract.assert_called_once_with(1, {'termination_reason': 'Клиент отказался'})
        mock_dialog.accept.assert_called_once()


# ==================== refresh_current_tab ====================

class TestRefreshCurrentTab:
    """refresh_current_tab — обновление вкладки."""

    def test_calls_load_for_active(self, manager_tab):
        """При активной вкладке вызывает load_active_cards."""
        tab, _ = manager_tab
        tab.tabs.setCurrentIndex(0)
        with patch.object(tab, 'load_active_cards') as mock_load:
            tab.refresh_current_tab()
            mock_load.assert_called()


# ==================== SupervisionDraggableList ====================

class TestSupervisionDraggableList:
    """SupervisionDraggableList — базовые проверки."""

    def test_import(self):
        from ui.crm_supervision_tab import SupervisionDraggableList
        assert SupervisionDraggableList is not None

    def test_is_subclass_of_base(self):
        from ui.crm_supervision_tab import SupervisionDraggableList
        from ui.base_kanban_tab import BaseDraggableList
        assert issubclass(SupervisionDraggableList, BaseDraggableList)
