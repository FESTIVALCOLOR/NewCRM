# -*- coding: utf-8 -*-
"""
Углублённые тесты CRM-диалогов — RejectWithCorrectionsDialog, ProjectDataDialog,
CRMStatisticsDialog, ExportPDFDialog, ReassignExecutorDialog, SurveyDateDialog,
TechTaskDialog, MeasurementDialog.
~25 тестов. НЕ дублирует test_crm.py (82 теста на CRMTab/CRMCard).
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QWidget
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


# ========== Авто-мок CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_crm_deep_msgbox():
    with patch('ui.crm_dialogs.CustomMessageBox') as m1, \
         patch('ui.crm_dialogs.CustomQuestionBox', MagicMock()):
        m1.return_value.exec_.return_value = None
        yield m1


# ========== Хелпер IconLoader ==========

def _mock_icon_loader():
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(side_effect=lambda *a, **k: QPushButton())
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _make_parent(qtbot, mock_data_access, employee):
    w = QWidget()
    w.data = mock_data_access
    w.employee = employee
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


# ========================================================================
# 1. RejectWithCorrectionsDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestRejectWithCorrectionsDialog:
    """Диалог отправки на исправление."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.YandexDiskManager', return_value=None):
            from ui.crm_dialogs import RejectWithCorrectionsDialog
            d = RejectWithCorrectionsDialog(parent, 'Стадия 1', 200, None, MagicMock())
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_as_dialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_has_file_label(self, dlg):
        assert hasattr(dlg, 'file_label')

    def test_submit_without_file(self, dlg):
        dlg._submit()
        assert dlg.result() == QDialog.Accepted


# ========================================================================
# 2. ProjectDataDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestProjectDataDialog:
    """Диалог просмотра данных проекта."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ProjectDataDialog
            d = ProjectDataDialog(parent, 'https://example.com/project/123')
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_link(self, dlg):
        assert dlg.project_data_link == 'https://example.com/project/123'

    def test_has_copy_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        copy_btns = [b for b in btns if 'копировать' in b.text().lower()]
        assert len(copy_btns) >= 1

    def test_has_open_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        open_btns = [b for b in btns if 'открыть' in b.text().lower() or 'браузер' in b.text().lower()]
        assert len(open_btns) >= 1


# ========================================================================
# 3. CRMStatisticsDialog (4 теста)
# ========================================================================

@pytest.mark.ui
class TestCRMStatisticsDialog:

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.return_value = []
        mock_data_access.get_all_employees.return_value = []
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.IconLoader', _mock_icon_loader()):
            from ui.crm_dialogs import CRMStatisticsDialog
            d = CRMStatisticsDialog(parent, 'Индивидуальный', mock_employee_admin)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_project_type(self, dlg):
        assert dlg.project_type == 'Индивидуальный'

    def test_has_stats_table(self, dlg):
        assert hasattr(dlg, 'stats_table')

    def test_has_action_buttons(self, dlg):
        btns = dlg.findChildren(QPushButton)
        assert len(btns) >= 1, "Диалог статистики должен содержать кнопки"

    def test_has_period_filter(self, dlg):
        assert hasattr(dlg, 'period_combo')


# ========================================================================
# 4. ExportPDFDialog (4 теста)
# ========================================================================

@pytest.mark.ui
class TestExportPDFDialog:

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ExportPDFDialog
            d = ExportPDFDialog(parent, 'статистика_2026')
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_default_filename(self, dlg):
        assert dlg.filename_input.text() == 'статистика_2026'

    def test_get_filename_adds_pdf(self, dlg):
        dlg.filename_input.setText('отчёт')
        assert dlg.get_filename() == 'отчёт.pdf'

    def test_get_filename_preserves_pdf(self, dlg):
        dlg.filename_input.setText('отчёт.pdf')
        assert dlg.get_filename() == 'отчёт.pdf'

    def test_get_folder_initially_none(self, dlg):
        assert dlg.get_folder() is None


# ========================================================================
# 5. SurveyDateDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestSurveyDateDialog:

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.db.connect.return_value = MagicMock()
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close.return_value = None
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import SurveyDateDialog
            d = SurveyDateDialog(parent, card_id=300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 300

    def test_has_survey_date_field(self, dlg):
        assert hasattr(dlg, 'survey_date')

    def test_save_calls_update(self, dlg):
        dlg.data.update_crm_card = MagicMock()
        dlg.save()
        dlg.data.update_crm_card.assert_called_once()
        call_args = dlg.data.update_crm_card.call_args
        assert call_args[0][0] == 300
        assert 'survey_date' in call_args[0][1]


# ========================================================================
# 6. TechTaskDialog (4 теста)
# ========================================================================

@pytest.mark.ui
class TestTechTaskDialog:

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = None
        mock_data_access.db.connect.return_value = MagicMock()
        mock_data_access.db.connect.return_value.cursor.return_value = cursor_mock
        mock_data_access.db.close.return_value = None
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.YandexDiskManager', return_value=None):
            from ui.crm_dialogs import TechTaskDialog
            d = TechTaskDialog(parent, card_id=300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 300

    def test_has_upload_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        upload_btns = [b for b in btns if 'загрузить' in b.text().lower()]
        assert len(upload_btns) >= 1

    def test_truncate_filename_short(self, dlg):
        assert dlg.truncate_filename('test.pdf') == 'test.pdf'

    def test_truncate_filename_long(self, dlg):
        long_name = 'a' * 100 + '.pdf'
        result = dlg.truncate_filename(long_name, max_length=50)
        assert len(result) <= 50
        assert '...' in result


# ========================================================================
# 7. MeasurementDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestMeasurementDialog:

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        cursor_mock = MagicMock()
        cursor_mock.fetchone.return_value = None
        cursor_mock.fetchall.return_value = []
        mock_data_access.db.connect.return_value = MagicMock()
        mock_data_access.db.connect.return_value.cursor.return_value = cursor_mock
        mock_data_access.db.close.return_value = None
        mock_data_access.get_all_employees.return_value = [
            {'id': 8, 'full_name': 'Замерщик Тест', 'position': 'Замерщик', 'status': 'активный'}
        ]
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.YandexDiskManager', return_value=None):
            from ui.crm_dialogs import MeasurementDialog
            d = MeasurementDialog(parent, card_id=300, employee=mock_employee_admin, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 300

    def test_truncate_filename(self, dlg):
        assert dlg.truncate_filename('file.png') == 'file.png'
        long = dlg.truncate_filename('a' * 60 + '.jpg', max_length=30)
        assert len(long) <= 30 and '...' in long

    def test_has_upload_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        upload_btns = [b for b in btns if 'загрузить' in b.text().lower()]
        assert len(upload_btns) >= 1


# ========================================================================
# 8. ReassignExecutorDialog (2 теста)
# ========================================================================

@pytest.mark.ui
class TestReassignExecutorDialog:

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_card.return_value = {
            'id': 300, 'stage_executors': [], 'contract_id': 200
        }
        mock_data_access.get_all_employees.return_value = [
            {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
        ]
        mock_data_access.get_employees_by_position.return_value = [
            {'id': 7, 'full_name': 'Чертёжник Тест', 'position': 'Чертёжник', 'status': 'активный'},
        ]
        mock_data_access.get_action_history.return_value = []
        mock_data_access.db.connect.return_value = MagicMock()
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close.return_value = None

        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.IconLoader', _mock_icon_loader()):
            from ui.crm_dialogs import ReassignExecutorDialog
            d = ReassignExecutorDialog(
                parent, card_id=300, position='Чертёжник',
                stage_keyword='планировочные', executor_type='Чертёжник',
                current_executor_name='Старый Чертёжник',
                stage_name='Стадия 1: планировочные решения',
                api_client=None,
            )
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d._test_parent = parent
            qtbot.addWidget(d)
            yield d

    def test_creates_with_card_id(self, dlg):
        assert dlg.card_id == 300

    def test_has_executor_combo(self, dlg):
        assert hasattr(dlg, 'executor_combo')
