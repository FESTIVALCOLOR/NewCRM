# -*- coding: utf-8 -*-
"""
Тесты диалогов авторского надзора — PauseDialog, SupervisionStatisticsDialog,
SupervisionCompletionDialog, AddProjectNoteDialog, SupervisionStageDeadlineDialog,
SupervisionReassignDANDialog, AssignExecutorsDialog, SupervisionFileUploadDialog.
~20 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QDialog, QPushButton, QWidget, QTextEdit, QMessageBox
from PyQt5.QtCore import Qt, QDate


# ========== Авто-мок CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_supervision_dlg_msgbox():
    """Мок CustomMessageBox / CustomQuestionBox / QMessageBox."""
    with patch('ui.supervision_dialogs.CustomMessageBox') as m1, \
         patch('ui.supervision_dialogs.CustomQuestionBox', MagicMock()):
        m1.return_value.exec_.return_value = None
        yield m1


# ========== Хелперы ==========

def _make_parent(qtbot, mock_data_access, employee):
    w = QWidget()
    w.data = mock_data_access
    w.employee = employee
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


# ========================================================================
# 1. PauseDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestPauseDialog:
    """Диалог приостановки проекта."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.supervision_dialogs.DataAccess') as MockDA:
            MockDA.return_value = mock_data_access
            from ui.supervision_dialogs import PauseDialog
            d = PauseDialog(parent, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_as_dialog(self, dlg):
        """PauseDialog создаётся как QDialog."""
        assert isinstance(dlg, QDialog)

    def test_has_reason_text(self, dlg):
        """Поле причины приостановки существует."""
        assert hasattr(dlg, 'reason_text')
        assert isinstance(dlg.reason_text, QTextEdit)

    def test_accept_closes(self, dlg):
        """Нажатие «Приостановить» закрывает диалог (accept)."""
        dlg.accept()
        assert dlg.result() == QDialog.Accepted


# ========================================================================
# 2. SupervisionStatisticsDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestSupervisionStatisticsDialog:
    """Диалог статистики надзора."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_supervision_cards_active.return_value = []
        mock_data_access.get_supervision_cards_archived.return_value = []
        mock_data_access.get_all_employees.return_value = []
        with patch('ui.supervision_dialogs.DataAccess') as MockDA, \
             patch('ui.supervision_dialogs.IconLoader') as MockIcon:
            MockDA.return_value = mock_data_access
            MockIcon.load = MagicMock(return_value=None)
            MockIcon.create_icon_button = MagicMock(side_effect=lambda *a, **k: QPushButton())
            from ui.supervision_dialogs import SupervisionStatisticsDialog
            d = SupervisionStatisticsDialog(parent, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_as_dialog(self, dlg):
        """Диалог создаётся."""
        assert isinstance(dlg, QDialog)

    def test_has_stats_table(self, dlg):
        """Таблица статистики существует."""
        assert hasattr(dlg, 'stats_table')

    def test_has_period_combo(self, dlg):
        """Комбобокс периода существует."""
        assert hasattr(dlg, 'period_combo')


# ========================================================================
# 3. SupervisionCompletionDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestSupervisionCompletionDialog:
    """Диалог завершения проекта надзора."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.supervision_dialogs.DataAccess') as MockDA:
            MockDA.return_value = mock_data_access
            from ui.supervision_dialogs import SupervisionCompletionDialog
            d = SupervisionCompletionDialog(parent, card_id=500, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 500

    def test_on_status_changed_shows_reason(self, dlg):
        """Выбор «РАСТОРГНУТ» показывает поле причины."""
        dlg.on_status_changed('Проект РАСТОРГНУТ')
        assert not dlg.termination_reason_group.isHidden()

    def test_on_status_changed_hides_reason(self, dlg):
        """Выбор «СДАН» скрывает поле причины."""
        dlg.on_status_changed('Проект РАСТОРГНУТ')
        dlg.on_status_changed('Проект СДАН')
        assert dlg.termination_reason_group.isHidden()


# ========================================================================
# 4. AddProjectNoteDialog (2 теста)
# ========================================================================

@pytest.mark.ui
class TestAddProjectNoteDialog:
    """Диалог добавления записи в историю проекта."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.supervision_dialogs.DataAccess') as MockDA:
            MockDA.return_value = mock_data_access
            from ui.supervision_dialogs import AddProjectNoteDialog
            d = AddProjectNoteDialog(parent, card_id=500, employee=mock_employee_admin, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 500

    def test_has_note_text(self, dlg):
        """Поле текста записи существует."""
        assert hasattr(dlg, 'note_text')


# ========================================================================
# 5. SupervisionReassignDANDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestSupervisionReassignDANDialog:
    """Диалог переназначения ДАН."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_employees_by_position.return_value = [
            {'id': 9, 'full_name': 'ДАН Тестов', 'position': 'ДАН', 'status': 'активный'},
            {'id': 10, 'full_name': 'ДАН Второй', 'position': 'ДАН', 'status': 'активный'},
        ]
        mock_data_access.get_supervision_card.return_value = {
            'id': 500, 'dan_id': 9, 'contract_id': 200
        }
        with patch('ui.supervision_dialogs.DataAccess') as MockDA:
            MockDA.return_value = mock_data_access
            from ui.supervision_dialogs import SupervisionReassignDANDialog
            d = SupervisionReassignDANDialog(parent, card_id=500, current_dan_name='ДАН Тестов', api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 500

    def test_has_dan_combo(self, dlg):
        """Комбобокс ДАН существует."""
        assert hasattr(dlg, 'dan_combo')
        assert dlg.dan_combo.count() >= 2

    def test_save_calls_update(self, dlg):
        """Сохранение вызывает update_supervision_card."""
        dlg.data.update_supervision_card = MagicMock()
        dlg.data.get_supervision_card.return_value = {
            'id': 500, 'dan_id': 9, 'contract_id': 200
        }
        dlg.data.get_payments_for_contract.return_value = []
        dlg.dan_combo.setCurrentIndex(1)  # Второй ДАН
        dlg.save_reassignment()
        dlg.data.update_supervision_card.assert_called_once()


# ========================================================================
# 6. AssignExecutorsDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestAssignExecutorsDialog:
    """Диалог назначения исполнителей (ДАН + СМП) при перемещении на рабочую стадию."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_employees_by_position.return_value = [
            {'id': 2, 'full_name': 'СМП Тест', 'position': 'Старший менеджер проектов', 'status': 'активный'},
        ]
        with patch('ui.supervision_dialogs.DataAccess') as MockDA:
            MockDA.return_value = mock_data_access
            from ui.supervision_dialogs import AssignExecutorsDialog
            d = AssignExecutorsDialog(parent, card_id=500, stage_name='Рабочая стадия', api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_stage_name(self, dlg):
        assert dlg.stage_name == 'Рабочая стадия'

    def test_has_smp_combo(self, dlg):
        """Комбобокс Старшего менеджера существует."""
        assert hasattr(dlg, 'smp_combo')

    def test_has_dan_combo(self, dlg):
        """Комбобокс ДАН существует."""
        assert hasattr(dlg, 'dan_combo')


# ========================================================================
# 7. SupervisionFileUploadDialog (4 теста)
# ========================================================================

@pytest.mark.ui
class TestSupervisionFileUploadDialog:
    """Диалог загрузки файла для надзора."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        card_data = {'id': 500, 'address': 'ул. Тестовая, д.1', 'contract_number': 'ТСТ-001'}
        stages = ['Стадия 1', 'Стадия 2', 'Стадия 3']
        with patch('ui.supervision_dialogs.DataAccess') as MockDA:
            MockDA.return_value = mock_data_access
            from ui.supervision_dialogs import SupervisionFileUploadDialog
            d = SupervisionFileUploadDialog(parent, card_data=card_data, stages=stages, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_stages(self, dlg):
        """Диалог создаётся с переданными стадиями."""
        assert len(dlg.stages) == 3

    def test_upload_button_disabled_initially(self, dlg):
        """Кнопка загрузки отключена при инициализации."""
        assert not dlg.upload_btn.isEnabled()

    def test_get_result_initially_none(self, dlg):
        """get_result возвращает None при инициализации."""
        assert dlg.get_result() is None

    def test_browse_file_updates_label(self, dlg):
        """browse_file обновляет лейбл файла (мокаем QFileDialog)."""
        with patch('ui.supervision_dialogs.QFileDialog.getOpenFileName', return_value=('/tmp/test.pdf', 'All files (*.*)')):
            dlg.browse_file()
            assert dlg.selected_file_path == '/tmp/test.pdf'
            assert 'test.pdf' in dlg.file_label.text()
