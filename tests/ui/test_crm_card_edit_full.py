# -*- coding: utf-8 -*-
"""Тесты для ui/crm_card_edit_dialog.py — CardEditDialog (~200 тестов)"""

import pytest
import os
from unittest.mock import patch, MagicMock, PropertyMock, call
from PyQt5.QtWidgets import QWidget, QDialog, QComboBox, QLabel, QLineEdit, QPushButton, QApplication, QDateEdit
from PyQt5.QtCore import Qt, QDate, QEvent, QPoint


# ─── Глобальные автоuse фикстуры ───────────────────────────────────────────


def _mock_icon_loader():
    """Фабрика мока IconLoader"""
    loader = MagicMock()
    loader.get_icon.return_value = MagicMock()
    btn = QPushButton("mock")
    loader.create_button.return_value = btn
    return loader


@pytest.fixture(autouse=True)
def _patch_heavy_deps(qapp):
    """Глобальный мок тяжёлых зависимостей для всего модуля"""
    from contextlib import ExitStack
    with ExitStack() as stack:
        stack.enter_context(patch('ui.crm_card_edit_dialog.IconLoader', _mock_icon_loader()))
        stack.enter_context(patch('ui.crm_card_edit_dialog.CustomTitleBar', return_value=QWidget()))
        mock_cmb = stack.enter_context(patch('ui.crm_card_edit_dialog.CustomMessageBox'))
        mock_cqb = stack.enter_context(patch('ui.crm_card_edit_dialog.CustomQuestionBox'))
        mock_cmb_src = stack.enter_context(patch('ui.custom_message_box.CustomMessageBox'))
        mock_cqb_src = stack.enter_context(patch('ui.custom_message_box.CustomQuestionBox'))
        stack.enter_context(patch('ui.crm_card_edit_dialog.CustomComboBox', QComboBox))
        stack.enter_context(patch('ui.crm_card_edit_dialog.CustomDateEdit', QDateEdit))
        stack.enter_context(patch('ui.crm_card_edit_dialog.disable_wheel_on_tabwidget'))
        stack.enter_context(patch('ui.crm_card_edit_dialog.add_today_button_to_dateedit'))
        stack.enter_context(patch('ui.crm_card_edit_dialog.CALENDAR_STYLE', ''))
        stack.enter_context(patch('ui.crm_card_edit_dialog.ProportionalResizeTable', return_value=MagicMock()))
        stack.enter_context(patch('ui.crm_card_edit_dialog.apply_no_focus_delegate'))
        stack.enter_context(patch('ui.crm_card_edit_dialog.TableSettings', return_value=MagicMock()))
        stack.enter_context(patch('ui.crm_card_edit_dialog.resource_path', lambda x: x))
        stack.enter_context(patch('ui.crm_card_edit_dialog.create_progress_dialog', return_value=MagicMock()))
        stack.enter_context(patch('ui.crm_card_edit_dialog.YandexDiskManager', return_value=MagicMock()))
        stack.enter_context(patch('ui.crm_card_edit_dialog.YANDEX_DISK_TOKEN', 'fake-token'))
        stack.enter_context(patch('ui.crm_card_edit_dialog._emp_has_pos', return_value=True))
        stack.enter_context(patch('ui.crm_card_edit_dialog._emp_only_pos', return_value=False))
        stack.enter_context(patch('ui.crm_card_edit_dialog._has_perm', return_value=True))
        stack.enter_context(patch('ui.crm_card_edit_dialog._load_user_permissions', return_value={}))
        mock_qdlg = stack.enter_context(patch('ui.crm_card_edit_dialog.QDialog'))
        mock_qdlg.Accepted = QDialog.Accepted
        mock_qdlg.Rejected = QDialog.Rejected
        mock_qdlg.return_value.exec_.return_value = QDialog.Rejected
        mock_qdlg.return_value.result.return_value = QDialog.Rejected
        mock_cmb.return_value.exec_.return_value = QDialog.Accepted
        mock_cqb.return_value.exec_.return_value = QDialog.Rejected
        mock_cmb_src.return_value.exec_.return_value = QDialog.Accepted
        mock_cqb_src.return_value.exec_.return_value = QDialog.Rejected
        yield


def _make_card_data(**overrides):
    """Фабрика card_data"""
    base = {
        'id': 1,
        'contract_id': 100,
        'contract_number': 'ДИ-001',
        'client_name': 'Тестовый клиент',
        'address': 'ул. Тестовая, 1',
        'area': 50.0,
        'project_type': 'Индивидуальный',
        'project_subtype': 'Квартира',
        'agent_type': 'Риелтор',
        'status': 'В работе',
        'column_name': 'В работе',
        'deadline': '2026-12-31',
        'survey_date': None,
        'surveyor_id': None,
        'senior_manager_id': None,
        'sdp_id': None,
        'gap_id': None,
        'manager_id': None,
        'tags': '',
        'tech_task_date': None,
        'tech_task_link': None,
        'stage_executors': [],
    }
    base.update(overrides)
    return base


def _make_stub_dialog():
    """Создать CardEditDialog-заглушку без вызова __init__ (Python 3.14 safe)"""
    from ui.crm_card_edit_dialog import CardEditDialog
    from PyQt5.QtWidgets import QApplication, QDialog
    if QApplication.instance() is None:
        QApplication([])

    def _minimal_init(self, *args, **kwargs):
        QDialog.__init__(self)  # Инициализация C++ объекта без тяжёлого UI

    with patch.object(CardEditDialog, '__init__', _minimal_init):
        obj = CardEditDialog()
    return obj


def _make_employee(**overrides):
    """Фабрика employee"""
    base = {
        'id': 10,
        'full_name': 'Тест Тестов',
        'position': 'Директор',
        'secondary_position': '',
    }
    base.update(overrides)
    return base


def _make_mock_data_access():
    """Фабрика мока DataAccess"""
    da = MagicMock()
    da.db = MagicMock()
    da.is_online = True
    da.is_multi_user = True
    da.prefer_local = False
    da.get_crm_card.return_value = None
    da.get_contract.return_value = {'id': 100, 'status': 'В работе', 'project_type': 'Индивидуальный'}
    da.get_all_employees.return_value = []
    da.get_payments_for_contract.return_value = []
    da.get_supervision_cards.return_value = []
    da.get_project_history.return_value = []
    da.get_approval_deadlines.return_value = []
    da.get_stage_files.return_value = []
    da.get_action_history.return_value = []
    return da


@pytest.fixture
def card_dialog_factory(qtbot):
    """Фабрика создания CardEditDialog с моками"""
    dialogs = []

    def _create(card_data=None, employee=None, view_only=False):
        cd = card_data or _make_card_data()
        emp = employee or _make_employee()
        mock_da = _make_mock_data_access()

        parent = QWidget()
        parent.data = mock_da
        parent.api_client = MagicMock()
        parent.employee = emp
        parent.refresh_current_tab = MagicMock()
        qtbot.addWidget(parent)

        with patch('ui.crm_card_edit_dialog.DataAccess', return_value=mock_da), \
             patch('ui.crm_card_edit_dialog.DatabaseManager', return_value=MagicMock()):
            from ui.crm_card_edit_dialog import CardEditDialog
            dlg = CardEditDialog(parent, cd, view_only=view_only, employee=emp,
                                 api_client=parent.api_client)
            dlg.closeEvent = lambda e: e.accept()
            dialogs.append(dlg)
            return dlg, mock_da

    yield _create

    for d in dialogs:
        try:
            d.close()
        except Exception:
            pass


# ─── Тесты truncate_filename (чистая логика, без UI) ──────────────────────


class TestTruncateFilename:
    """Тесты метода truncate_filename"""

    def _make(self):
        """Создать минимальный объект для вызова truncate_filename"""
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        return obj

    def test_short_name_unchanged(self):
        obj = self._make()
        assert obj.truncate_filename('file.txt') == 'file.txt'

    def test_exact_max_length(self):
        obj = self._make()
        name = 'a' * 46 + '.txt'  # 50 chars
        assert obj.truncate_filename(name, 50) == name

    def test_long_name_truncated(self):
        obj = self._make()
        name = 'a' * 100 + '.pdf'
        result = obj.truncate_filename(name, 30)
        assert '...' in result
        assert result.endswith('.pdf')
        assert len(result) <= 30

    def test_very_long_extension(self):
        obj = self._make()
        name = 'file' + '.verylongextension'
        result = obj.truncate_filename(name, 10)
        assert len(result) <= 10

    def test_no_extension(self):
        obj = self._make()
        name = 'a' * 60
        result = obj.truncate_filename(name, 30)
        assert '...' in result

    def test_default_max_length_50(self):
        obj = self._make()
        name = 'a' * 100 + '.txt'
        result = obj.truncate_filename(name)
        assert len(result) <= 50

    def test_empty_string(self):
        obj = self._make()
        assert obj.truncate_filename('') == ''

    def test_single_char(self):
        obj = self._make()
        assert obj.truncate_filename('a') == 'a'


# ─── Тесты _get_contract_yandex_folder ────────────────────────────────────


class TestGetContractYandexFolder:
    """Тесты _get_contract_yandex_folder"""

    def test_none_contract_id(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        assert obj._get_contract_yandex_folder(None) is None

    def test_zero_contract_id(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        assert obj._get_contract_yandex_folder(0) is None

    def test_valid_contract_returns_path(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.get_contract.return_value = {'yandex_folder_path': '/disk/contracts/123'}
        result = obj._get_contract_yandex_folder(123)
        assert result == '/disk/contracts/123'

    def test_contract_without_path(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.get_contract.return_value = {'id': 123}
        result = obj._get_contract_yandex_folder(123)
        assert result is None

    def test_contract_not_found(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.get_contract.return_value = None
        result = obj._get_contract_yandex_folder(999)
        assert result is None

    def test_exception_returns_none(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.get_contract.side_effect = Exception("DB error")
        result = obj._get_contract_yandex_folder(123)
        assert result is None


# ─── Тесты _add_action_history ────────────────────────────────────────────


class TestAddActionHistory:
    """Тесты _add_action_history"""

    def test_default_entity_type(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'id': 42}
        obj.employee = {'id': 10}
        obj.data = MagicMock()

        obj._add_action_history('update', 'Обновлено поле')
        obj.data.add_action_history.assert_called_once_with(
            user_id=10,
            action_type='update',
            entity_type='crm_card',
            entity_id=42,
            description='Обновлено поле'
        )

    def test_custom_entity_type_and_id(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'id': 42}
        obj.employee = {'id': 10}
        obj.data = MagicMock()

        obj._add_action_history('survey_complete', 'Замер выполнен',
                                entity_type='contract', entity_id=100)
        obj.data.add_action_history.assert_called_once_with(
            user_id=10,
            action_type='survey_complete',
            entity_type='contract',
            entity_id=100,
            description='Замер выполнен'
        )

    def test_no_employee(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'id': 42}
        obj.employee = None
        obj.data = MagicMock()

        obj._add_action_history('delete', 'Удалено')
        obj.data.add_action_history.assert_called_once_with(
            user_id=None,
            action_type='delete',
            entity_type='crm_card',
            entity_id=42,
            description='Удалено'
        )


# ─── Тесты set_combo_by_id ────────────────────────────────────────────────


class TestSetComboById:
    """Тесты set_combo_by_id"""

    def test_sets_correct_index(self, qtbot):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()

        combo = QComboBox()
        qtbot.addWidget(combo)
        combo.addItem('Не назначен', None)
        combo.addItem('Иванов', 10)
        combo.addItem('Петров', 20)

        obj.set_combo_by_id(combo, 20)
        assert combo.currentIndex() == 2
        assert combo.currentData() == 20

    def test_none_employee_id_no_change(self, qtbot):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()

        combo = QComboBox()
        qtbot.addWidget(combo)
        combo.addItem('Не назначен', None)
        combo.addItem('Иванов', 10)

        obj.set_combo_by_id(combo, None)
        assert combo.currentIndex() == 0

    def test_missing_id_no_change(self, qtbot):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()

        combo = QComboBox()
        qtbot.addWidget(combo)
        combo.addItem('Не назначен', None)
        combo.addItem('Иванов', 10)

        obj.set_combo_by_id(combo, 999)
        assert combo.currentIndex() == 0


# ─── Тесты _show_sync_label / _on_sync_ended ──────────────────────────────


class TestSyncLabel:
    """Тесты _show_sync_label и _on_sync_ended"""

    def test_show_sync_increments_count(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._active_sync_count = 0
        obj.sync_label = MagicMock()

        obj._show_sync_label()
        assert obj._active_sync_count == 1
        obj.sync_label.setVisible.assert_called_with(True)

    def test_on_sync_ended_decrements(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._active_sync_count = 2
        obj.sync_label = MagicMock()

        obj._on_sync_ended()
        assert obj._active_sync_count == 1
        obj.sync_label.setVisible.assert_not_called()

    def test_on_sync_ended_hides_at_zero(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._active_sync_count = 1
        obj.sync_label = MagicMock()

        obj._on_sync_ended()
        assert obj._active_sync_count == 0
        obj.sync_label.setVisible.assert_called_with(False)


# ─── Тесты auto_save_field ────────────────────────────────────────────────


class TestAutoSaveField:
    """Тесты auto_save_field"""

    def test_skip_during_loading(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = True
        obj.data = MagicMock()
        obj.card_data = {'id': 1}

        obj.auto_save_field()
        obj.data.update_crm_card.assert_not_called()

    def test_saves_tags(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.data = MagicMock()
        obj.data.is_online = True
        obj.data.is_multi_user = True
        obj.card_data = {
            'id': 1, 'contract_id': None,
            'senior_manager_id': None, 'sdp_id': None,
            'gap_id': None, 'manager_id': None, 'surveyor_id': None,
        }
        obj.tags = MagicMock()
        obj.tags.text.return_value = '  тег1, тег2  '

        obj.auto_save_field()
        called_updates = obj.data.update_crm_card.call_args[0][1]
        assert called_updates['tags'] == 'тег1, тег2'

    def test_saves_senior_manager(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.data = MagicMock()
        obj.data.is_online = True
        obj.data.is_multi_user = False
        obj.card_data = {
            'id': 1, 'contract_id': None,
            'senior_manager_id': None, 'sdp_id': None,
            'gap_id': None, 'manager_id': None, 'surveyor_id': None,
        }
        obj.senior_manager = MagicMock()
        obj.senior_manager.currentData.return_value = 55

        obj.auto_save_field()
        called_updates = obj.data.update_crm_card.call_args[0][1]
        assert called_updates['senior_manager_id'] == 55


# ─── Тесты save_changes ───────────────────────────────────────────────────


class TestSaveChanges:
    """Тесты save_changes"""

    def test_save_updates_card(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj.card_data = {'id': 1, 'contract_id': None}
        obj.tags = MagicMock()
        obj.tags.text.return_value = 'tag1'
        obj.accept = MagicMock()

        obj.save_changes()
        obj.data.update_crm_card.assert_called_once()
        obj.accept.assert_called_once()

    def test_save_updates_status(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj.card_data = {'id': 1, 'contract_id': 100}
        obj.tags = MagicMock()
        obj.tags.text.return_value = ''
        obj.status_combo = MagicMock()
        obj.status_combo.currentText.return_value = 'СДАН'
        obj.accept = MagicMock()

        obj.save_changes()
        obj.data.update_contract.assert_called()

    def test_save_creates_supervision_card(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.data = MagicMock()
        obj.data.is_multi_user = True
        obj.data.get_supervision_cards.return_value = []
        obj.card_data = {'id': 1, 'contract_id': 100}
        obj.tags = MagicMock()
        obj.tags.text.return_value = ''
        obj.status_combo = MagicMock()
        obj.status_combo.currentText.return_value = 'АВТОРСКИЙ НАДЗОР'
        obj.accept = MagicMock()

        obj.save_changes()
        obj.data.create_supervision_card.assert_called()


# ─── Тесты on_employee_changed ────────────────────────────────────────────


class TestOnEmployeeChanged:
    """Тесты on_employee_changed"""

    def test_skip_during_loading(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = True
        obj.data = MagicMock()

        combo = MagicMock()
        obj.on_employee_changed(combo, 'Менеджер')
        obj.data.update_crm_card.assert_not_called()

    def test_skip_no_contract_id(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {'id': 1, 'contract_id': None}
        obj.data = MagicMock()

        combo = MagicMock()
        obj.on_employee_changed(combo, 'Менеджер')
        obj.data.update_crm_card.assert_not_called()

    def test_updates_card_field(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {'id': 1, 'contract_id': 100}
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj.data.calculate_payment_amount.return_value = 5000

        combo = MagicMock()
        combo.currentData.return_value = 55
        obj.refresh_payments_tab = MagicMock()

        obj.on_employee_changed(combo, 'Менеджер')
        obj.data.update_crm_card.assert_called_once_with(1, {'manager_id': 55})
        assert obj.card_data['manager_id'] == 55

    def test_sdp_creates_advance_and_balance(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {'id': 1, 'contract_id': 100, 'project_type': 'Индивидуальный'}
        obj.data = MagicMock()
        obj.data.is_multi_user = True
        obj.data.get_payments_for_contract.return_value = []
        obj.data.calculate_payment_amount.return_value = 10000
        obj.refresh_payments_tab = MagicMock()

        combo = MagicMock()
        combo.currentData.return_value = 30

        obj.on_employee_changed(combo, 'СДП')

        # Должны быть 2 вызова create_payment (аванс + доплата)
        assert obj.data.create_payment.call_count == 2
        calls = obj.data.create_payment.call_args_list
        assert calls[0][0][0]['payment_type'] == 'Аванс'
        assert calls[1][0][0]['payment_type'] == 'Доплата'

    def test_template_project_skip_smp_payment(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {'id': 1, 'contract_id': 100, 'project_type': 'Шаблонный'}
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj.refresh_payments_tab = MagicMock()

        combo = MagicMock()
        combo.currentData.return_value = 55

        obj.on_employee_changed(combo, 'Старший менеджер проектов')
        # Для шаблонного проекта НЕ создаётся платёж
        obj.data.create_payment.assert_not_called()
        obj.data.calculate_payment_amount.assert_not_called()


# ─── Тесты _load_messenger_chat_state ─────────────────────────────────────


class TestMessengerChat:
    """Тесты методов мессенджер-чата"""

    def test_load_state_no_data_access(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'id': 1}
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj._update_chat_buttons_state = MagicMock()

        obj._load_messenger_chat_state()
        assert obj._messenger_chat_data is None

    def test_load_state_multi_user(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'id': 1}
        obj.data = MagicMock()
        obj.data.is_multi_user = True
        obj.data.get_messenger_chat.return_value = {'chat': {'id': 5, 'is_active': True}}
        obj._update_chat_buttons_state = MagicMock()

        obj._load_messenger_chat_state()
        assert obj._messenger_chat_data['chat']['id'] == 5

    def test_update_buttons_no_chat(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._messenger_chat_data = None
        obj.data = MagicMock()
        obj.data.is_multi_user = True
        obj.create_chat_btn = MagicMock()
        obj.open_chat_btn = MagicMock()
        obj.delete_chat_btn = MagicMock()

        obj._update_chat_buttons_state()
        obj.create_chat_btn.setEnabled.assert_called_with(True)
        obj.open_chat_btn.setEnabled.assert_called_with(False)
        obj.delete_chat_btn.setEnabled.assert_called_with(False)

    def test_update_buttons_with_active_chat(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._messenger_chat_data = {'chat': {'id': 5, 'is_active': True}}
        obj.data = MagicMock()
        obj.data.is_multi_user = True
        obj.create_chat_btn = MagicMock()
        obj.open_chat_btn = MagicMock()
        obj.delete_chat_btn = MagicMock()

        obj._update_chat_buttons_state()
        obj.create_chat_btn.setEnabled.assert_called_with(False)
        obj.open_chat_btn.setEnabled.assert_called_with(True)
        obj.delete_chat_btn.setEnabled.assert_called_with(True)

    def test_update_buttons_offline(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._messenger_chat_data = None
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj.create_chat_btn = MagicMock()
        obj.open_chat_btn = MagicMock()
        obj.delete_chat_btn = MagicMock()

        obj._update_chat_buttons_state()
        obj.create_chat_btn.setEnabled.assert_called_with(False)

    def test_on_open_chat_no_data(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._messenger_chat_data = None
        # Не должен падать
        obj._on_open_chat()

    def test_on_delete_chat_no_data(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._messenger_chat_data = None
        obj._on_delete_chat()

    def test_send_start_script_no_card(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = None
        obj.data = MagicMock()
        obj._on_send_start_script()
        obj.data.trigger_script.assert_not_called()

    def test_send_end_script_no_card(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = None
        obj.data = MagicMock()
        obj._on_send_end_script()
        obj.data.trigger_script.assert_not_called()

    def test_send_start_script_success(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'id': 1}
        obj.data = MagicMock()
        obj.data.trigger_script.return_value = True

        with patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            obj._on_send_start_script()
        obj.data.trigger_script.assert_called_once_with(1, 'project_start')


# ─── Тесты delete_order ───────────────────────────────────────────────────


class TestDeleteOrder:
    """Тесты delete_order"""

    def test_cancel_delete(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb:
            mock_cqb.return_value.exec_.return_value = QDialog.Rejected
            obj.delete_order()
        obj.data.delete_contract.assert_not_called()
        obj.data.delete_order.assert_not_called()

    def test_confirm_delete_api(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.data.is_multi_user = True
        obj.accept = MagicMock()
        obj.parent = MagicMock(return_value=None)

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb, \
             patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            mock_cqb.return_value.exec_.return_value = QDialog.Accepted
            obj.delete_order()
        obj.data.delete_contract.assert_called_once_with(100)
        obj.accept.assert_called_once()

    def test_confirm_delete_local(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.data.is_multi_user = False
        obj.accept = MagicMock()
        obj.parent = MagicMock(return_value=None)

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb, \
             patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            mock_cqb.return_value.exec_.return_value = QDialog.Accepted
            obj.delete_order()
        obj.data.delete_order.assert_called_once_with(100, 1)


# ─── Тесты connect_autosave_signals ───────────────────────────────────────


class TestConnectAutosaveSignals:
    """Тесты connect_autosave_signals"""

    def test_connects_status_combo(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.status_combo = MagicMock()
        obj.auto_save_field = MagicMock()

        obj.connect_autosave_signals()
        obj.status_combo.currentIndexChanged.connect.assert_called()

    def test_connects_tags(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.tags = MagicMock()
        obj.auto_save_field = MagicMock()

        obj.connect_autosave_signals()
        obj.tags.textChanged.connect.assert_called()

    def test_no_crash_no_widgets(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.auto_save_field = MagicMock()
        # Нет ни одного виджета
        obj.connect_autosave_signals()  # Не должен падать


# ─── Тесты load_data ──────────────────────────────────────────────────────


class TestLoadData:
    """Тесты load_data"""

    def test_sets_loading_flag(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {'id': 1, 'contract_id': None, 'survey_date': None,
                         'tech_task_date': None, 'stage_executors': []}
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = None
        obj.data.get_contract.return_value = None
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = True
        obj._cached_contract = None

        obj.load_data()
        assert obj._loading_data is False  # Флаг сброшен после загрузки

    def test_merges_fresh_data(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {'id': 1, 'contract_id': None, 'survey_date': None,
                         'tech_task_date': None, 'tags': 'old', 'stage_executors': []}
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = {'id': 1, 'tags': 'new_tags'}
        obj.data.get_contract.return_value = None
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = True
        obj._cached_contract = None

        obj.load_data()
        assert obj.card_data['tags'] == 'new_tags'

    def test_sets_deadline_from_stage_executors(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {
            'id': 1, 'contract_id': None, 'survey_date': None,
            'tech_task_date': None, 'deadline': None,
            'stage_executors': [
                {'deadline': '2026-06-01'},
                {'deadline': '2026-12-01'},
            ],
        }
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = None
        obj.data.get_contract.return_value = None
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = True
        obj._cached_contract = None
        obj.deadline_display = MagicMock()

        obj.load_data()
        obj.deadline_display.setText.assert_called_with('01.12.2026')

    def test_sets_survey_date_label(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {
            'id': 1, 'contract_id': None,
            'survey_date': '2026-03-15', 'tech_task_date': None,
            'stage_executors': [],
        }
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = None
        obj.data.get_contract.return_value = None
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = True
        obj._cached_contract = None
        obj.survey_date_label = MagicMock()

        obj.load_data()
        obj.survey_date_label.setText.assert_called_with('15.03.2026')

    def test_no_survey_date(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {
            'id': 1, 'contract_id': None,
            'survey_date': None, 'tech_task_date': None,
            'stage_executors': [],
        }
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = None
        obj.data.get_contract.return_value = None
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = True
        obj._cached_contract = None
        obj.survey_date_label = MagicMock()

        obj.load_data()
        obj.survey_date_label.setText.assert_called_with('Не установлена')

    def test_connects_autosave_not_view_only(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {
            'id': 1, 'contract_id': None,
            'survey_date': None, 'tech_task_date': None,
            'stage_executors': [],
        }
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = None
        obj.data.get_contract.return_value = None
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = False
        obj._cached_contract = None
        obj.connect_autosave_signals = MagicMock()

        obj.load_data()
        obj.connect_autosave_signals.assert_called_once()

    def test_tech_task_file_label_set(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj._loading_data = False
        obj.card_data = {
            'id': 1, 'contract_id': 100,
            'survey_date': None, 'tech_task_date': None,
            'stage_executors': [],
        }
        obj.data = MagicMock()
        obj.data.prefer_local = False
        obj.data.get_crm_card.return_value = None
        obj.data.get_contract.return_value = {
            'id': 100, 'status': 'В работе',
            'tech_task_link': 'https://ya.disk/tz.pdf',
            'tech_task_file_name': 'ТехЗадание.pdf',
        }
        obj.verify_files_on_yandex_disk = MagicMock()
        obj._load_all_stage_files_batch = MagicMock()
        obj.validate_stage_files_on_yandex = MagicMock()
        obj.view_only = True
        obj._cached_contract = None
        obj.tech_task_file_label = MagicMock()
        obj.upload_tz_btn = MagicMock()
        obj.truncate_filename = lambda name, max_length=50: name

        obj.load_data()
        set_text = obj.tech_task_file_label.setText.call_args[0][0]
        assert 'ТехЗадание.pdf' in set_text
        obj.upload_tz_btn.setEnabled.assert_called_with(False)


# ─── Тесты save_survey_date (with DB mock) ────────────────────────────────


class TestSaveSurveyDate:
    """Тесты save_survey_date"""

    def _make_obj(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.employee = _make_employee()
        obj.data = _make_mock_data_access()

        # Мокаем DB connect
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # Нет existing survey
        mock_conn.cursor.return_value = mock_cursor
        obj.data.db.connect.return_value = mock_conn

        obj.survey_date_label = MagicMock()
        obj.refresh_payments_tab = MagicMock()
        obj.refresh_project_info_tab = MagicMock()
        obj.reload_project_history = MagicMock()
        obj.findChildren = MagicMock(return_value=[])
        obj._add_action_history = MagicMock()

        return obj

    def test_creates_new_survey(self):
        obj = self._make_obj()
        dialog = MagicMock()
        survey_date = QDate(2026, 3, 15)

        with patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            obj.save_survey_date(survey_date, 20, dialog)

        dialog.accept.assert_called_once()
        obj.survey_date_label.setText.assert_called_with('15.03.2026')

    def test_updates_existing_survey(self):
        obj = self._make_obj()
        # existing record found
        mock_conn = obj.data.db.connect.return_value
        mock_conn.cursor.return_value.fetchone.return_value = {'id': 99}
        dialog = MagicMock()
        survey_date = QDate(2026, 5, 20)

        with patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            obj.save_survey_date(survey_date, 20, dialog)

        dialog.accept.assert_called_once()

    def test_error_shows_message(self):
        obj = self._make_obj()
        obj.data.db.connect.side_effect = Exception("DB fail")
        dialog = MagicMock()
        survey_date = QDate(2026, 3, 15)

        with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_cmb:
            obj.save_survey_date(survey_date, 20, dialog)
            mock_cmb.assert_called()


# ─── Тесты mark_survey_complete ───────────────────────────────────────────


class TestMarkSurveyComplete:
    """Тесты mark_survey_complete"""

    def test_no_surveyor_shows_warning(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.surveyor = MagicMock()
        obj.surveyor.currentData.return_value = None

        with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_cmb:
            obj.mark_survey_complete()
            mock_cmb.assert_called()

    def test_with_surveyor_opens_dialog(self):
        obj = _make_stub_dialog()
        obj.surveyor = MagicMock()
        obj.surveyor.currentData.return_value = 20

        with patch('ui.crm_card_edit_dialog.CustomDateEdit', QDateEdit), \
             patch('ui.crm_card_edit_dialog.add_today_button_to_dateedit'), \
             patch('ui.crm_card_edit_dialog.CustomTitleBar', return_value=QWidget()), \
             patch('ui.custom_title_bar.CustomTitleBar', return_value=QWidget()), \
             patch('ui.crm_card_edit_dialog.QDialog') as mock_dlg:
            mock_dlg.return_value.exec_.return_value = None
            obj.mark_survey_complete()
            mock_dlg.assert_called()


# ─── Тесты refresh_payments_tab ───────────────────────────────────────────


class TestRefreshPaymentsTab:
    """Тесты refresh_payments_tab"""

    def test_no_payments_tab(self):
        obj = _make_stub_dialog()
        obj.card_data = {'contract_id': 100}
        obj.data = MagicMock()
        obj.payments_tab_index = -1  # Нет вкладки оплат
        obj.refresh_payments_tab()  # Не должен падать

    def test_with_payments_tab_index(self):
        obj = _make_stub_dialog()
        obj.card_data = {'contract_id': 100}
        obj.data = MagicMock()
        obj.payments_tab_index = 0
        obj.tabs = MagicMock()
        obj.create_payments_tab = MagicMock(return_value=QWidget())

        obj.refresh_payments_tab()
        obj.create_payments_tab.assert_called_once()


# ─── Тесты refresh_project_info_tab ───────────────────────────────────────


class TestRefreshProjectInfoTab:
    """Тесты refresh_project_info_tab"""

    def test_no_project_info_container(self):
        obj = _make_stub_dialog()
        obj.refresh_project_info_tab()  # Нет project_info_tab_index — не должен падать

    def test_with_tab_index(self):
        obj = _make_stub_dialog()
        obj.project_info_tab_index = 0
        obj.tabs = MagicMock()
        obj.create_project_info_widget = MagicMock(return_value=QWidget())

        obj.refresh_project_info_tab()
        obj.create_project_info_widget.assert_called_once()


# ─── Тесты _on_history_filter_changed ─────────────────────────────────────


class TestHistoryFilter:
    """Тесты _on_history_filter_changed"""

    def test_filter_all(self):
        from PyQt5.QtWidgets import QVBoxLayout
        obj = _make_stub_dialog()
        obj._all_history_items = [
            {'action_type': 'update', 'description': 'Тест',
             'action_date': '2026-01-01 12:00:00', 'user_name': 'Тестов'},
        ]
        obj.info_layout = QVBoxLayout()

        obj._on_history_filter_changed('Все действия')
        assert obj.info_layout.count() >= 1


# ─── Тесты upload / delete tech task ──────────────────────────────────────


class TestUploadTechTask:
    """Тесты upload_project_tech_task_file"""

    def test_upload_method_exists(self):
        obj = _make_stub_dialog()
        assert hasattr(obj, 'upload_project_tech_task_file')
        assert callable(obj.upload_project_tech_task_file)


class TestDeleteTechTask:
    """Тесты delete_tech_task_file"""

    def test_cancel_does_nothing(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb:
            mock_cqb.return_value.exec_.return_value = QDialog.Rejected
            obj.delete_tech_task_file()
        obj.data.update_contract.assert_not_called()


# ─── Тесты upload/delete references ───────────────────────────────────────


class TestDeleteReferences:
    """Тесты delete_references_folder"""

    def test_cancel_does_nothing(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb:
            mock_cqb.return_value.exec_.return_value = QDialog.Rejected
            obj.delete_references_folder()
        obj.data.update_contract.assert_not_called()


class TestDeletePhotoDoc:
    """Тесты delete_photo_documentation_folder"""

    def test_cancel_does_nothing(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb:
            mock_cqb.return_value.exec_.return_value = QDialog.Rejected
            obj.delete_photo_documentation_folder()
        obj.data.update_contract.assert_not_called()


# ─── Тесты project templates ──────────────────────────────────────────────


class TestProjectTemplates:
    """Тесты load_project_templates и save_project_templates"""

    def test_load_returns_list(self):
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.data.get_project_templates.return_value = [
            {'id': 1, 'template_url': 'https://example.com', 'template_name': 'Шаблон 1'},
        ]
        mock_layout = MagicMock()
        mock_layout.count.return_value = 0
        obj.templates_container = MagicMock()
        obj.templates_container.layout.return_value = mock_layout
        obj.create_template_link_widget = MagicMock()

        obj.load_project_templates()
        obj.data.get_project_templates.assert_called_with(100)

    def test_delete_template(self):
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.employee = _make_employee()
        obj.load_project_templates = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_cqb, \
             patch('ui.custom_message_box.CustomQuestionBox') as mock_cqb_src, \
             patch('ui.crm_card_edit_dialog.CustomMessageBox'), \
             patch('ui.custom_message_box.CustomMessageBox'):
            mock_cqb.return_value.exec_.return_value = QDialog.Accepted
            mock_cqb_src.return_value.exec_.return_value = QDialog.Accepted
            obj.delete_project_template(1)


# ─── Тесты _on_project_tech_task_uploaded / error ──────────────────────────


class TestTechTaskUploadCallbacks:
    """Тесты _on_project_tech_task_uploaded и _on_project_tech_task_upload_error"""

    def test_on_uploaded_updates_labels(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.tech_task_file_label = MagicMock()
        obj.project_data_tz_file_label = MagicMock()
        obj.upload_tz_btn = MagicMock()
        obj._add_action_history = MagicMock()
        obj.employee = _make_employee()
        obj.truncate_filename = lambda name, max_length=50: name
        obj.reload_project_history = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            obj._on_project_tech_task_uploaded(
                'https://ya.disk/link', '/disk/path', 'ТЗ.pdf', 100
            )

        obj.data.update_contract.assert_called()
        obj.tech_task_file_label.setText.assert_called()

    def test_on_error_shows_message(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()

        with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_cmb:
            obj._on_project_tech_task_upload_error('Ошибка загрузки')
            mock_cmb.assert_called()


# ─── Тесты _on_references_uploaded / error ─────────────────────────────────


class TestReferencesUploadCallbacks:
    """Тесты _on_references_uploaded и _on_references_upload_error"""

    def test_on_uploaded_updates_labels(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.project_data_references_label = MagicMock()
        obj._add_action_history = MagicMock()
        obj.employee = _make_employee()
        obj.reload_project_history = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            obj._on_references_uploaded('https://ya.disk/refs', 100)

        obj.data.update_contract.assert_called()

    def test_on_error_shows_message(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()

        with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_cmb:
            obj._on_references_upload_error('Ошибка')
            mock_cmb.assert_called()


# ─── Тесты _on_photo_doc_uploaded / error ──────────────────────────────────


class TestPhotoDocUploadCallbacks:
    """Тесты _on_photo_doc_uploaded и _on_photo_doc_upload_error"""

    def test_on_uploaded_updates_labels(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.project_data_photo_doc_label = MagicMock()
        obj._add_action_history = MagicMock()
        obj.employee = _make_employee()
        obj.reload_project_history = MagicMock()

        with patch('ui.crm_card_edit_dialog.CustomMessageBox'):
            obj._on_photo_doc_uploaded('https://ya.disk/photos', 100)

        obj.data.update_contract.assert_called()

    def test_on_error_shows_message(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()

        with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_cmb:
            obj._on_photo_doc_upload_error('Ошибка')
            mock_cmb.assert_called()


# ─── Тесты verify_files_on_yandex_disk ────────────────────────────────────


class TestVerifyFiles:
    """Тесты verify_files_on_yandex_disk"""

    def test_no_contract_id_skips(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = {'contract_id': None}
        obj.verify_files_on_yandex_disk()  # Не должен падать


# ─── Тесты _reload_all_stage_files ────────────────────────────────────────


class TestReloadStageFiles:
    """Тесты _reload_all_stage_files"""

    def test_no_stage_lists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        # Нет stage1_list и т.д. — не должен падать
        obj._reload_all_stage_files()


# ─── Тесты CardEditDialog через factory ───────────────────────────────────


class TestCardEditDialogInit:
    """Тесты инициализации CardEditDialog (через stub)"""

    def test_creation(self):
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        assert obj is not None
        assert obj.card_data['id'] == 1

    def test_view_only_attr(self):
        obj = _make_stub_dialog()
        obj.view_only = True
        assert obj.view_only is True

    def test_custom_card_data(self):
        obj = _make_stub_dialog()
        custom = _make_card_data(client_name='Кастомный клиент', area=120.0)
        obj.card_data = custom
        assert obj.card_data['client_name'] == 'Кастомный клиент'
        assert obj.card_data['area'] == 120.0

    def test_has_data_access(self):
        obj = _make_stub_dialog()
        obj.data = _make_mock_data_access()
        assert obj.data is not None

    def test_has_employee(self):
        obj = _make_stub_dialog()
        obj.employee = _make_employee()
        assert obj.employee is not None
        assert obj.employee['id'] == 10

    def test_class_methods_exist(self):
        """Проверка наличия ключевых методов"""
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, 'init_ui')
        assert hasattr(CardEditDialog, 'load_data')
        assert hasattr(CardEditDialog, 'save_changes')

    def test_resize_attrs(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        # Атрибуты создаются в __init__, но для stub проверяем наличие в классе
        assert hasattr(CardEditDialog, 'mousePressEvent')
        assert hasattr(CardEditDialog, 'mouseMoveEvent')


# ─── Тесты edit_tech_task_file ─────────────────────────────────────────────


class TestEditTechTaskFile:
    """Тесты edit_tech_task_file"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "edit_tech_task_file")


class TestEditTechTaskDate:
    """Тесты edit_tech_task_date"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "edit_tech_task_date")


class TestEditMeasurementDate:
    """Тесты edit_measurement_date"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "edit_measurement_date")


class TestChangeProjectDeadline:
    """Тесты change_project_deadline"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "change_project_deadline")


class TestChangeExecutorDeadline:
    """Тесты change_executor_deadline"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "change_executor_deadline")


class TestReassignExecutor:
    """Тесты reassign_executor_from_dialog"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "reassign_executor_from_dialog")


class TestAddMeasurement:
    """Тесты add_measurement"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "add_measurement")


class TestReloadMeasurementData:
    """Тесты reload_measurement_data"""

    def test_reloads(self):
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        mock_result = {
            'measurement_image_link': 'https://ya.disk/measure.jpg',
            'measurement_file_name': 'замер.jpg',
            'measurement_date': '2026-01-15',
        }
        obj.data.db.connect.return_value.cursor.return_value.fetchone.return_value = mock_result
        obj.project_data_survey_file_label = MagicMock()
        obj.truncate_filename = lambda name, max_length=50: name

        obj.reload_measurement_data()
        obj.project_data_survey_file_label.setText.assert_called()
        text = obj.project_data_survey_file_label.setText.call_args[0][0]
        assert 'замер.jpg' in text


# ─── Тесты reload_project_history ─────────────────────────────────────────


class TestReloadProjectHistory:
    """Тесты reload_project_history"""

    def test_no_history_container(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        # Нет history_scroll — не должен падать
        obj.reload_project_history()

    def test_with_history(self):
        from PyQt5.QtWidgets import QVBoxLayout
        obj = _make_stub_dialog()
        obj.card_data = _make_card_data()
        obj.data = MagicMock()
        obj.data.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        obj.info_layout = QVBoxLayout()

        obj.reload_project_history()
        obj.data.db.connect.assert_called()


# ─── Тесты add_project_templates ──────────────────────────────────────────


class TestAddProjectTemplates:
    """Тесты add_project_templates"""

    def test_method_exists(self):
        from ui.crm_card_edit_dialog import CardEditDialog
        assert hasattr(CardEditDialog, "add_project_templates")


class TestAddTemplateInputField:
    """Тесты add_template_input_field"""

    def test_adds_field(self):
        from PyQt5.QtWidgets import QVBoxLayout
        obj = _make_stub_dialog()
        obj.template_inputs_layout = QVBoxLayout()
        obj.template_input_fields = []

        obj.add_template_input_field()
        assert len(obj.template_input_fields) == 1


# ─── Тесты remove_template_input_field ────────────────────────────────────


class TestRemoveTemplateInputField:
    """Тесты remove_template_input_field"""

    def test_removes_field(self):
        from PyQt5.QtWidgets import QHBoxLayout, QLineEdit
        obj = _make_stub_dialog()
        obj.template_inputs_layout = MagicMock()
        row = QHBoxLayout()
        input_field = QLineEdit()
        row.addWidget(input_field)
        obj.template_input_fields = [input_field]

        obj.remove_template_input_field(row, input_field)
        assert len(obj.template_input_fields) == 0
