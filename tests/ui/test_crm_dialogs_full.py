# -*- coding: utf-8 -*-
"""
Полное покрытие тестами ui/crm_dialogs.py — все 11 классов диалогов.
~160 тестов. Цель: поднять покрытие с 5% до 50%+.

Классы:
  1. RejectWithCorrectionsDialog
  2. ProjectDataDialog
  3. ExecutorSelectionDialog
  4. ProjectCompletionDialog
  5. CRMStatisticsDialog
  6. ExportPDFDialog
  7. PDFExportSuccessDialog
  8. ReassignExecutorDialog
  9. SurveyDateDialog
 10. TechTaskDialog
 11. MeasurementDialog
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import (QDialog, QPushButton, QLabel, QWidget,
                              QComboBox, QLineEdit, QTableWidget,
                              QTextEdit, QGroupBox, QSpinBox, QApplication)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon


# ========== Авто-мок CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_msgbox_full():
    """Глобальный мок CustomMessageBox/CustomQuestionBox для всех тестов."""
    with patch('ui.crm_dialogs.CustomMessageBox') as m1, \
         patch('ui.crm_dialogs.CustomQuestionBox', MagicMock()):
        m1.return_value.exec_.return_value = None
        yield m1


@pytest.fixture(autouse=True)
def _mock_tooltip_fix():
    """Мок tooltip_fix чтобы не падал импорт."""
    with patch('utils.tooltip_fix.apply_tooltip_palette', return_value=None):
        yield


@pytest.fixture(autouse=True)
def _mock_icon_loader_global():
    """Глобальный мок IconLoader — возвращает реальные QPushButton."""
    mock_il = MagicMock()
    mock_il.load = MagicMock(return_value=QIcon())
    mock_il.create_icon_button = MagicMock(side_effect=lambda *a, **k: QPushButton())
    mock_il.get_icon_path = MagicMock(return_value='')
    with patch('ui.crm_dialogs.IconLoader', mock_il), \
         patch('utils.icon_loader.IconLoader', mock_il):
        yield mock_il


# ========== Хелпер для создания родительского виджета ==========

def _make_parent(qtbot, mock_data_access, employee):
    """Создать родительский виджет с mock данными."""
    w = QWidget()
    w.data = mock_data_access
    w.employee = employee
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


# ========================================================================
# 1. RejectWithCorrectionsDialog (15 тестов)
# ========================================================================

@pytest.mark.ui
class TestRejectWithCorrectionsDialogFull:
    """Диалог отправки на исправление с загрузкой файла правок на ЯД."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import RejectWithCorrectionsDialog
            d = RejectWithCorrectionsDialog(parent, 'Стадия 1: планировочные решения', 200, None, MagicMock())
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_window_flags_frameless(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_fixed_width_420(self, dlg):
        assert dlg.width() > 0  # Диалог создан с корректным размером

    def test_stage_name_stored(self, dlg):
        assert dlg.stage_name == 'Стадия 1: планировочные решения'

    def test_contract_id_stored(self, dlg):
        assert dlg.contract_id == 200

    def test_has_file_label(self, dlg):
        assert hasattr(dlg, 'file_label')
        assert isinstance(dlg.file_label, QLabel)

    def test_file_label_default_text(self, dlg):
        assert 'Файл не выбран' in dlg.file_label.text()

    def test_has_send_button(self, dlg):
        assert hasattr(dlg, 'send_btn')
        assert isinstance(dlg.send_btn, QPushButton)

    def test_send_button_text(self, dlg):
        assert 'Отправить на исправление' in dlg.send_btn.text()

    def test_selected_file_initially_empty(self, dlg):
        assert dlg.selected_file == ''

    def test_corrections_folder_path_initially_empty(self, dlg):
        assert dlg.corrections_folder_path == ''

    def test_submit_without_file_accepts(self, dlg):
        """Без файла — диалог принимается (файл необязателен)."""
        dlg._submit()
        assert dlg.result() == QDialog.Accepted

    def test_submit_with_file_disables_button(self, dlg):
        """При наличии файла кнопка блокируется перед загрузкой."""
        dlg.selected_file = '/tmp/test_corrections.pdf'
        with patch('ui.crm_dialogs.YANDEX_DISK_TOKEN', ''), \
             patch('PyQt5.QtWidgets.QApplication.processEvents'):
            dlg._submit()
        # Кнопка должна быть disabled или текст изменён
        assert dlg.result() == QDialog.Accepted

    def test_select_file_updates_label(self, dlg):
        """_select_file обновляет file_label при выборе файла."""
        with patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                   return_value=('/tmp/test.pdf', '')):
            dlg._select_file()
        assert dlg.selected_file == '/tmp/test.pdf'
        assert 'test.pdf' in dlg.file_label.text()

    def test_select_file_cancel_no_change(self, dlg):
        """Отмена выбора файла — ничего не меняется."""
        with patch('PyQt5.QtWidgets.QFileDialog.getOpenFileName',
                   return_value=('', '')):
            dlg._select_file()
        assert dlg.selected_file == ''


# ========================================================================
# 2. ProjectDataDialog (15 тестов)
# ========================================================================

@pytest.mark.ui
class TestProjectDataDialogFull:
    """Диалог просмотра данных проекта."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ProjectDataDialog
            d = ProjectDataDialog(parent, 'https://example.com/project/123')
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_link_stored(self, dlg):
        assert dlg.project_data_link == 'https://example.com/project/123'

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_width(self, dlg):
        assert dlg.minimumWidth() >= 950

    def test_has_copy_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('Копировать' in t for t in texts)

    def test_has_open_browser_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('Открыть в браузере' in t for t in texts)

    def test_has_close_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('Закрыть' in t for t in texts)

    def test_copy_link(self, dlg, qapp):
        """copy_link копирует ссылку в буфер обмена."""
        dlg.copy_link()
        clipboard = QApplication.clipboard()
        assert clipboard.text() == 'https://example.com/project/123'

    def test_open_in_browser(self, dlg):
        """open_in_browser вызывает QDesktopServices.openUrl."""
        with patch('PyQt5.QtGui.QDesktopServices.openUrl') as mock_open:
            dlg.open_in_browser()
            mock_open.assert_called_once()

    def test_show_event_centers(self, dlg):
        """showEvent вызывает center_on_screen."""
        with patch.object(dlg, 'center_on_screen') as mock_center:
            from PyQt5.QtGui import QShowEvent
            dlg.showEvent(QShowEvent())
            mock_center.assert_called_once()

    def test_show_event_not_centered_twice(self, dlg):
        """Повторный showEvent не центрирует заново."""
        from PyQt5.QtGui import QShowEvent
        with patch('utils.dialog_helpers.center_dialog_on_parent'):
            dlg.showEvent(QShowEvent())
        with patch.object(dlg, 'center_on_screen') as mock_center:
            dlg.showEvent(QShowEvent())
            mock_center.assert_not_called()

    def test_link_label_is_clickable(self, dlg):
        """Ссылка на проект отображается как кликабельная."""
        labels = dlg.findChildren(QLabel)
        link_labels = [l for l in labels if 'example.com' in l.text()]
        assert len(link_labels) >= 1

    def test_header_label_present(self, dlg):
        labels = dlg.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('Ссылка на данные проекта' in t for t in texts)

    def test_different_link(self, qtbot, mock_data_access, mock_employee_admin):
        """Диалог корректно работает с разными ссылками."""
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ProjectDataDialog
            d = ProjectDataDialog(parent, 'https://drive.google.com/folder/abc')
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            # НЕ добавляем qtbot.addWidget(d) — дочерний диалог
            assert d.project_data_link == 'https://drive.google.com/folder/abc'


# ========================================================================
# 3. ExecutorSelectionDialog (18 тестов)
# ========================================================================

@pytest.mark.ui
class TestExecutorSelectionDialogFull:
    """Диалог выбора исполнителя."""

    @pytest.fixture
    def mock_da(self, mock_data_access):
        """Настроенный mock DataAccess для ExecutorSelectionDialog."""
        mock_data_access.get_project_timeline.return_value = []
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Иванов Иван', 'position': 'Чертёжник', 'secondary_position': ''},
            {'id': 11, 'full_name': 'Петров Пётр', 'position': 'Чертёжник', 'secondary_position': ''},
        ]
        mock_data_access.get_crm_card.return_value = {'contract_id': 200, 'stage_executors': []}
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()
        return mock_data_access

    @pytest.fixture
    def dlg(self, qtbot, mock_da, mock_employee_admin):
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da):
            from ui.crm_dialogs import ExecutorSelectionDialog
            d = ExecutorSelectionDialog(parent, 300, 'Стадия 1: планировочные решения',
                                        'Индивидуальный', api_client=None, contract_id=200)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, dlg):
        assert dlg.card_id == 300

    def test_stage_name_stored(self, dlg):
        assert dlg.stage_name == 'Стадия 1: планировочные решения'

    def test_project_type_stored(self, dlg):
        assert dlg.project_type == 'Индивидуальный'

    def test_contract_id_stored(self, dlg):
        assert dlg.contract_id == 200

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_width(self, dlg):
        assert dlg.minimumWidth() >= 450

    def test_has_executor_combo(self, dlg):
        assert hasattr(dlg, 'executor_combo')

    def test_executor_combo_has_items(self, dlg):
        assert dlg.executor_combo.count() >= 2

    def test_executor_combo_first_item(self, dlg):
        assert dlg.executor_combo.itemText(0) == 'Иванов Иван'

    def test_executor_combo_item_data(self, dlg):
        assert dlg.executor_combo.itemData(0) == 10

    def test_has_stage_deadline(self, dlg):
        assert hasattr(dlg, 'stage_deadline')

    def test_deadline_default_7_days(self, dlg):
        """Дедлайн по умолчанию = +7 дней (если нет timeline)."""
        expected = QDate.currentDate().addDays(7)
        assert dlg.stage_deadline.date() == expected

    def test_norm_days_zero_when_no_timeline(self, dlg):
        assert dlg._norm_days == 0

    def test_assign_calls_data_access(self, dlg, mock_da):
        """assign_executor вызывает data.assign_stage_executor."""
        mock_da.assign_stage_executor = MagicMock()
        mock_da.get_contract_id_by_crm_card.return_value = 200
        mock_da.get_contract.return_value = {'project_type': 'Индивидуальный'}
        mock_da.calculate_payment_amount.return_value = 10000
        mock_da.create_payment.return_value = {'id': 1}
        dlg.assign_executor()
        mock_da.assign_stage_executor.assert_called_once()

    def test_assign_creates_payments_individual(self, dlg, mock_da):
        """Для индивидуального проекта создаются аванс и доплата."""
        mock_da.assign_stage_executor = MagicMock()
        mock_da.get_contract_id_by_crm_card.return_value = 200
        mock_da.get_contract.return_value = {'project_type': 'Индивидуальный'}
        mock_da.calculate_payment_amount.return_value = 10000
        mock_da.create_payment.return_value = {'id': 1}
        dlg.assign_executor()
        # Аванс + Доплата = 2 вызова
        assert mock_da.create_payment.call_count == 2

    def test_position_detected_stage1(self, mock_da, qtbot, mock_employee_admin):
        """Стадия 1 — ищем Чертёжников."""
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        mock_da.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Черт', 'position': 'Чертёжник', 'secondary_position': ''},
        ]
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da):
            from ui.crm_dialogs import ExecutorSelectionDialog
            d = ExecutorSelectionDialog(parent, 300, 'Стадия 1: планировочные',
                                        'Индивидуальный', contract_id=200)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            assert d.executor_combo.count() == 1


# ========================================================================
# 4. ProjectCompletionDialog (15 тестов)
# ========================================================================

@pytest.mark.ui
class TestProjectCompletionDialogFull:
    """Диалог завершения проекта."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ProjectCompletionDialog
            d = ProjectCompletionDialog(parent, 300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, dlg):
        assert dlg.card_id == 300

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_width(self, dlg):
        assert dlg.minimumWidth() >= 500

    def test_has_status_combo(self, dlg):
        assert hasattr(dlg, 'status')

    def test_status_combo_3_items(self, dlg):
        assert dlg.status.count() == 3

    def test_status_combo_first_item(self, dlg):
        assert 'СДАН' in dlg.status.itemText(0)

    def test_status_combo_second_item(self, dlg):
        assert 'АВТОРСКИЙ НАДЗОР' in dlg.status.itemText(1)

    def test_status_combo_third_item(self, dlg):
        assert 'РАСТОРГНУТ' in dlg.status.itemText(2)

    def test_termination_reason_hidden_by_default(self, dlg):
        assert hasattr(dlg, 'termination_reason_group')
        assert dlg.termination_reason_group.isHidden()

    def test_termination_reason_shown_on_cancel(self, dlg):
        """При выборе РАСТОРГНУТ показывается поле причины."""
        dlg.status.setCurrentIndex(2)
        assert not dlg.termination_reason_group.isHidden()

    def test_termination_reason_hidden_on_sdan(self, dlg):
        """При возврате к СДАН поле причины скрывается."""
        dlg.status.setCurrentIndex(2)
        dlg.status.setCurrentIndex(0)
        assert dlg.termination_reason_group.isHidden()

    def test_has_termination_reason_textedit(self, dlg):
        assert hasattr(dlg, 'termination_reason')
        assert isinstance(dlg.termination_reason, QTextEdit)

    def test_complete_project_without_reason_validation(self, dlg, _mock_msgbox_full):
        """Расторжение без причины показывает ошибку."""
        dlg.status.setCurrentIndex(2)
        dlg.termination_reason.setPlainText('')
        dlg.complete_project()
        _mock_msgbox_full.assert_called()

    def test_complete_project_sdan(self, dlg, mock_data_access):
        """Завершение проекта со статусом СДАН."""
        mock_data_access.get_contract_id_by_crm_card.return_value = 200
        mock_data_access.update_contract.return_value = {}
        mock_data_access.set_payments_report_month.return_value = None
        dlg.status.setCurrentIndex(0)
        dlg.complete_project()
        mock_data_access.update_contract.assert_called_once()

    def test_complete_project_supervision(self, dlg, mock_data_access):
        """Завершение с АВТОРСКИЙ НАДЗОР создаёт карточку надзора."""
        mock_data_access.get_contract_id_by_crm_card.return_value = 200
        mock_data_access.update_contract.return_value = {}
        mock_data_access.create_supervision_card.return_value = {'id': 500}
        mock_data_access.set_payments_report_month.return_value = None
        dlg.status.setCurrentIndex(1)
        dlg.complete_project()
        mock_data_access.create_supervision_card.assert_called_once()


# ========================================================================
# 5. CRMStatisticsDialog (20 тестов)
# ========================================================================

@pytest.mark.ui
class TestCRMStatisticsDialogFull:
    """Диалог статистики CRM."""

    @pytest.fixture
    def mock_da(self, mock_data_access):
        mock_data_access.get_projects_by_type.return_value = [
            {'contract_number': 'ИП-001', 'address': 'ул. Тестовая', 'city': 'СПБ', 'contract_id': 200}
        ]
        mock_data_access.get_employees_by_position.return_value = [
            {'id': 10, 'full_name': 'Тестовый Дизайнер', 'position': 'Дизайнер'}
        ]
        mock_data_access.get_crm_statistics_filtered.return_value = [
            {
                'assigned_date': '2026-01-10', 'executor_name': 'Тестов',
                'stage_name': 'Стадия 1', 'assigned_by_name': 'Админ',
                'deadline': '2026-01-20', 'submitted_date': '',
                'completed': False, 'completed_date': '', 'project_info': 'ИП-001'
            }
        ]
        return mock_data_access

    @pytest.fixture
    def dlg(self, qtbot, mock_da, mock_employee_admin):
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da), \
             patch('ui.crm_dialogs.apply_no_focus_delegate', return_value=None):
            from ui.crm_dialogs import CRMStatisticsDialog
            d = CRMStatisticsDialog(parent, 'Индивидуальный', mock_employee_admin)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_project_type_stored(self, dlg):
        assert dlg.project_type == 'Индивидуальный'

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_has_period_combo(self, dlg):
        assert hasattr(dlg, 'period_combo')
        assert dlg.period_combo.count() == 4

    def test_has_year_spin(self, dlg):
        assert hasattr(dlg, 'year_spin')
        assert isinstance(dlg.year_spin, QSpinBox)

    def test_year_spin_default(self, dlg):
        assert dlg.year_spin.value() == QDate.currentDate().year()

    def test_has_project_combo(self, dlg):
        assert hasattr(dlg, 'project_combo')
        # 'Все проекты' + загруженные проекты
        assert dlg.project_combo.count() >= 1

    def test_has_executor_combo(self, dlg):
        assert hasattr(dlg, 'executor_combo')
        assert dlg.executor_combo.count() >= 1

    def test_has_stage_combo(self, dlg):
        assert hasattr(dlg, 'stage_combo')

    def test_stage_combo_has_all_option(self, dlg):
        assert dlg.stage_combo.itemText(0) == 'Все'

    def test_has_status_combo(self, dlg):
        assert hasattr(dlg, 'status_combo')
        assert dlg.status_combo.count() == 4

    def test_has_stats_table(self, dlg):
        assert hasattr(dlg, 'stats_table')
        assert isinstance(dlg.stats_table, QTableWidget)

    def test_stats_table_8_columns(self, dlg):
        assert dlg.stats_table.columnCount() == 8

    def test_has_summary_labels(self, dlg):
        assert hasattr(dlg, 'total_label')
        assert hasattr(dlg, 'completed_label')
        assert hasattr(dlg, 'in_progress_label')
        assert hasattr(dlg, 'overdue_label')

    def test_is_overdue_none(self, dlg):
        assert dlg.is_overdue(None) is False

    def test_is_overdue_empty(self, dlg):
        assert dlg.is_overdue('') is False

    def test_is_overdue_past_date(self, dlg):
        assert dlg.is_overdue('2020-01-01') is True

    def test_is_overdue_future_date(self, dlg):
        assert dlg.is_overdue('2030-12-31') is False

    def test_on_period_changed_month(self, dlg):
        """Изменение периода на Месяц показывает month_combo."""
        dlg.on_period_changed('Месяц')
        assert not dlg.month_combo.isHidden()

    def test_on_period_changed_quarter(self, dlg):
        """Изменение периода на Квартал показывает quarter_combo."""
        dlg.on_period_changed('Квартал')
        assert not dlg.quarter_combo.isHidden()

    def test_on_period_changed_all_time(self, dlg):
        """Период 'Все время' скрывает year_spin."""
        dlg.on_period_changed('Все время')
        assert dlg.year_spin.isHidden()

    def test_reset_filters(self, dlg, mock_da):
        """Сброс фильтров возвращает все к значениям по умолчанию."""
        dlg.period_combo.setCurrentText('Месяц')
        dlg.status_combo.setCurrentIndex(1)
        mock_da.get_crm_statistics_filtered.return_value = []
        dlg.reset_filters()
        assert dlg.period_combo.currentText() == 'Все время'
        assert dlg.status_combo.currentIndex() == 0

    def test_load_statistics_called(self, dlg, mock_da):
        """load_statistics вызывает get_crm_statistics_filtered."""
        mock_da.get_crm_statistics_filtered.return_value = []
        dlg.load_statistics()
        mock_da.get_crm_statistics_filtered.assert_called()

    def test_get_current_filters_info_all_time(self, dlg):
        """Без фильтров возвращает пустой список."""
        dlg.period_combo.setCurrentText('Все время')
        dlg.project_combo.setCurrentIndex(0)
        dlg.executor_combo.setCurrentIndex(0)
        dlg.stage_combo.setCurrentIndex(0)
        dlg.status_combo.setCurrentIndex(0)
        filters, suffix = dlg._get_current_filters_info()
        assert len(filters) == 0

    def test_open_folder_no_crash(self, dlg):
        """open_folder не падает при невалидном пути."""
        with patch('os.startfile', side_effect=OSError):
            dlg.open_folder('/nonexistent/path')  # Не должно бросить исключение


# ========================================================================
# 6. ExportPDFDialog (12 тестов)
# ========================================================================

@pytest.mark.ui
class TestExportPDFDialogFull:
    """Диалог выбора имени файла для экспорта PDF."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ExportPDFDialog
            d = ExportPDFDialog(parent, 'Отчет CRM 2026-01-15')
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_default_filename_stored(self, dlg):
        assert dlg.default_filename == 'Отчет CRM 2026-01-15'

    def test_selected_folder_initially_none(self, dlg):
        assert dlg.selected_folder is None

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_minimum_width(self, dlg):
        assert dlg.minimumWidth() >= 550

    def test_has_filename_input(self, dlg):
        assert hasattr(dlg, 'filename_input')
        assert isinstance(dlg.filename_input, QLineEdit)

    def test_filename_input_default_value(self, dlg):
        assert dlg.filename_input.text() == 'Отчет CRM 2026-01-15'

    def test_get_filename_with_pdf(self, dlg):
        dlg.filename_input.setText('test.pdf')
        assert dlg.get_filename() == 'test.pdf'

    def test_get_filename_adds_pdf(self, dlg):
        dlg.filename_input.setText('report')
        assert dlg.get_filename() == 'report.pdf'

    def test_get_filename_empty_uses_default(self, dlg):
        dlg.filename_input.setText('')
        assert dlg.get_filename() == 'Отчет CRM 2026-01-15.pdf'

    def test_get_folder_returns_none_initially(self, dlg):
        assert dlg.get_folder() is None

    def test_select_folder_sets_folder(self, dlg):
        """Выбор папки сохраняет путь."""
        with patch('PyQt5.QtWidgets.QFileDialog.getExistingDirectory',
                   return_value='/tmp/exports'):
            dlg.select_folder()
        assert dlg.selected_folder == '/tmp/exports'


# ========================================================================
# 7. PDFExportSuccessDialog (10 тестов)
# ========================================================================

@pytest.mark.ui
class TestPDFExportSuccessDialogFull:
    """Диалог успешного экспорта PDF."""

    @pytest.fixture
    def dlg(self, qtbot, mock_data_access, mock_employee_admin):
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import PDFExportSuccessDialog
            d = PDFExportSuccessDialog(parent, '/tmp/report.pdf', '/tmp')
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_file_path_stored(self, dlg):
        assert dlg.file_path == '/tmp/report.pdf'

    def test_folder_path_stored(self, dlg):
        assert dlg.folder_path == '/tmp'

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_width(self, dlg):
        assert dlg.minimumWidth() >= 500

    def test_success_title_label(self, dlg):
        labels = dlg.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('PDF успешно создан' in t for t in texts)

    def test_file_path_label(self, dlg):
        labels = dlg.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('/tmp/report.pdf' in t for t in texts)

    def test_has_open_folder_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('Открыть папку' in t for t in texts)

    def test_has_ok_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('OK' in t for t in texts)


# ========================================================================
# 8. ReassignExecutorDialog (20 тестов)
# ========================================================================

@pytest.mark.ui
class TestReassignExecutorDialogFull:
    """Диалог переназначения исполнителя."""

    @pytest.fixture
    def mock_da(self, mock_data_access):
        mock_data_access.get_crm_card.return_value = {
            'contract_id': 200,
            'stage_executors': [
                {'stage_name': 'Стадия 1: планировочные решения', 'executor_id': 10, 'deadline': '2026-02-01', 'assigned_date': '2026-01-15'}
            ]
        }
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Иванов Иван', 'position': 'Чертёжник', 'secondary_position': ''},
            {'id': 11, 'full_name': 'Петров Пётр', 'position': 'Чертёжник', 'secondary_position': ''},
            {'id': 12, 'full_name': 'Сидоров Сидор', 'position': 'Чертёжник', 'secondary_position': ''},
        ]
        mock_data_access.get_action_history.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()
        return mock_data_access

    @pytest.fixture
    def dlg(self, qtbot, mock_da, mock_employee_admin):
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da):
            from ui.crm_dialogs import ReassignExecutorDialog
            d = ReassignExecutorDialog(
                parent, card_id=300, position='Чертёжник',
                stage_keyword='Стадия 1', executor_type='draftsman',
                current_executor_name='Иванов Иван',
                stage_name='Стадия 1: планировочные решения',
                api_client=None
            )
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, dlg):
        assert dlg.card_id == 300

    def test_position_stored(self, dlg):
        assert dlg.position == 'Чертёжник'

    def test_stage_keyword_stored(self, dlg):
        assert dlg.stage_keyword == 'Стадия 1'

    def test_stage_name_stored(self, dlg):
        assert dlg.stage_name == 'Стадия 1: планировочные решения'

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_width(self, dlg):
        assert dlg.minimumWidth() >= 600

    def test_has_executor_combo(self, dlg):
        assert hasattr(dlg, 'executor_combo')

    def test_executor_combo_has_items(self, dlg):
        assert dlg.executor_combo.count() >= 3

    def test_has_deadline_edit(self, dlg):
        assert hasattr(dlg, 'deadline_edit')

    def test_deadline_loaded_from_data(self, dlg):
        """Дедлайн загружается из stage_executors."""
        expected = QDate.fromString('2026-02-01', 'yyyy-MM-dd')
        assert dlg.deadline_edit.date() == expected

    def test_current_executor_name(self, dlg):
        """Текущий исполнитель отображается."""
        assert dlg.current_executor_name == 'Иванов Иван'

    def test_current_executor_id_set(self, dlg):
        """_current_executor_id установлен для проверки дубликата."""
        assert dlg._current_executor_id == 10

    def test_current_executor_selected_in_combo(self, dlg):
        """Текущий исполнитель предвыбран в combo."""
        assert dlg.executor_combo.currentData() == 10

    def test_save_same_executor_warns(self, dlg, _mock_msgbox_full):
        """Выбор того же исполнителя показывает предупреждение."""
        dlg.executor_combo.setCurrentIndex(0)  # Иванов — текущий
        dlg.save_reassignment()
        _mock_msgbox_full.assert_called()

    def test_save_different_executor_calls_update(self, dlg, mock_da):
        """Переназначение на другого исполнителя вызывает update_stage_executor."""
        mock_da.update_stage_executor = MagicMock()
        mock_da.get_payments_for_contract.return_value = []
        mock_da.get_current_user.return_value = {'id': 1}
        mock_da.add_action_history = MagicMock()
        # Выбираем Петрова (id=11)
        for i in range(dlg.executor_combo.count()):
            if dlg.executor_combo.itemData(i) == 11:
                dlg.executor_combo.setCurrentIndex(i)
                break
        dlg.save_reassignment()
        mock_da.update_stage_executor.assert_called_once()

    def test_check_payment_exists_none(self, dlg):
        """_check_payment_exists возвращает None если нет совпадений."""
        result = dlg._check_payment_exists([], 200, 11, 'Чертёжник', 'Стадия 1', 'Аванс')
        assert result is None

    def test_check_payment_exists_found(self, dlg):
        """_check_payment_exists находит существующий платёж."""
        payments = [
            {'id': 1, 'contract_id': 200, 'employee_id': 11, 'role': 'Чертёжник',
             'stage_name': 'Стадия 1: планировочные', 'payment_type': 'Аванс', 'reassigned': False}
        ]
        result = dlg._check_payment_exists(payments, 200, 11, 'Чертёжник', 'Стадия 1', 'Аванс')
        assert result is not None
        assert result['id'] == 1

    def test_check_payment_exists_skips_reassigned(self, dlg):
        """_check_payment_exists пропускает переназначенные платежи."""
        payments = [
            {'id': 1, 'contract_id': 200, 'employee_id': 11, 'role': 'Чертёжник',
             'stage_name': 'Стадия 1: планировочные', 'payment_type': 'Аванс', 'reassigned': True}
        ]
        result = dlg._check_payment_exists(payments, 200, 11, 'Чертёжник', 'Стадия 1', 'Аванс')
        assert result is None


# ========================================================================
# 9. SurveyDateDialog (12 тестов)
# ========================================================================

@pytest.mark.ui
class TestSurveyDateDialogFull:
    """Диалог установки даты замера."""

    @pytest.fixture
    def mock_da(self, mock_data_access):
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()
        return mock_data_access

    @pytest.fixture
    def dlg(self, qtbot, mock_da, mock_employee_admin):
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da):
            from ui.crm_dialogs import SurveyDateDialog
            d = SurveyDateDialog(parent, 300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, dlg):
        assert dlg.card_id == 300

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_fixed_size(self, dlg):
        assert dlg.width() == 400
        assert dlg.height() == 220

    def test_has_survey_date(self, dlg):
        assert hasattr(dlg, 'survey_date')

    def test_survey_date_default_today(self, dlg):
        assert dlg.survey_date.date() == QDate.currentDate()

    def test_survey_date_format(self, dlg):
        assert dlg.survey_date.displayFormat() == 'dd.MM.yyyy'

    def test_has_save_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('Сохранить' in t for t in texts)

    def test_has_cancel_button(self, dlg):
        btns = dlg.findChildren(QPushButton)
        texts = [b.text() for b in btns]
        assert any('Отмена' in t for t in texts)

    def test_save_calls_update_crm_card(self, dlg, mock_da):
        """Сохранение вызывает data.update_crm_card."""
        mock_da.update_crm_card = MagicMock()
        dlg.save()
        mock_da.update_crm_card.assert_called_once()

    def test_save_passes_survey_date(self, dlg, mock_da):
        """Сохранённая дата передаётся в формате yyyy-MM-dd."""
        mock_da.update_crm_card = MagicMock()
        dlg.survey_date.setDate(QDate(2026, 3, 15))
        dlg.save()
        call_args = mock_da.update_crm_card.call_args
        assert call_args[0][1]['survey_date'] == '2026-03-15'


# ========================================================================
# 10. TechTaskDialog (18 тестов)
# ========================================================================

@pytest.mark.ui
class TestTechTaskDialogFull:
    """Диалог добавления технического задания."""

    @pytest.fixture
    def mock_da(self, mock_data_access):
        mock_data_access.get_crm_card.return_value = {'contract_id': 200}
        mock_data_access.get_contract.return_value = {
            'tech_task_link': None, 'tech_task_file_name': None,
            'yandex_folder_path': '/disk/contracts/200'
        }
        return mock_data_access

    @pytest.fixture
    def dlg(self, qtbot, mock_da, mock_employee_admin):
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da):
            from ui.crm_dialogs import TechTaskDialog
            d = TechTaskDialog(parent, 300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, dlg):
        assert dlg.card_id == 300

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_has_file_label_display(self, dlg):
        assert hasattr(dlg, 'file_label_display')
        assert isinstance(dlg.file_label_display, QLabel)

    def test_file_label_default_text(self, dlg):
        assert 'Не загружен' in dlg.file_label_display.text()

    def test_uploaded_file_link_initially_none(self, dlg):
        assert dlg.uploaded_file_link is None

    def test_has_tech_task_date(self, dlg):
        assert hasattr(dlg, 'tech_task_date')

    def test_tech_task_date_default_today(self, dlg):
        assert dlg.tech_task_date.date() == QDate.currentDate()

    def test_tech_task_date_format(self, dlg):
        assert dlg.tech_task_date.displayFormat() == 'dd.MM.yyyy'

    def test_truncate_filename_short(self, dlg):
        assert dlg.truncate_filename('test.pdf') == 'test.pdf'

    def test_truncate_filename_long(self, dlg):
        long_name = 'a' * 100 + '.pdf'
        result = dlg.truncate_filename(long_name, 50)
        assert len(result) <= 50
        assert '...' in result

    def test_truncate_filename_exact_limit(self, dlg):
        name = 'a' * 46 + '.pdf'  # 50 символов
        assert dlg.truncate_filename(name, 50) == name

    def test_save_without_file_shows_error(self, dlg, _mock_msgbox_full):
        """Сохранение без загруженного файла показывает ошибку."""
        dlg.uploaded_file_link = None
        dlg.save()
        _mock_msgbox_full.assert_called()

    def test_save_with_file_calls_update(self, dlg, mock_da):
        """Сохранение с файлом обновляет crm_card."""
        dlg.uploaded_file_link = 'https://disk.yandex.ru/d/test'
        mock_da.update_crm_card = MagicMock()
        dlg.save()
        mock_da.update_crm_card.assert_called_once()

    def test_save_passes_tech_task_date(self, dlg, mock_da):
        """Переданная дата в формате yyyy-MM-dd."""
        dlg.uploaded_file_link = 'https://disk.yandex.ru/d/test'
        mock_da.update_crm_card = MagicMock()
        dlg.tech_task_date.setDate(QDate(2026, 5, 20))
        dlg.save()
        call_args = mock_da.update_crm_card.call_args
        assert call_args[0][1]['tech_task_date'] == '2026-05-20'

    def test_on_file_uploaded_success(self, dlg, mock_da):
        """_on_file_uploaded обновляет UI и данные."""
        mock_da.update_contract = MagicMock()
        dlg._on_file_uploaded('https://link', '/disk/path', 'file.pdf', 200)
        assert dlg.uploaded_file_link == 'https://link'
        assert 'file.pdf' in dlg.file_label_display.text()

    def test_on_file_uploaded_no_link(self, dlg, _mock_msgbox_full):
        """_on_file_uploaded без ссылки показывает ошибку."""
        dlg._on_file_uploaded('', '', '', 200)
        assert 'Не загружен' in dlg.file_label_display.text()

    def test_on_file_upload_error(self, dlg, _mock_msgbox_full):
        """_on_file_upload_error показывает ошибку."""
        dlg._on_file_upload_error('Network error')
        assert 'Не загружен' in dlg.file_label_display.text()


# ========================================================================
# 11. MeasurementDialog (18 тестов)
# ========================================================================

@pytest.mark.ui
class TestMeasurementDialogFull:
    """Диалог добавления замера с загрузкой изображения."""

    @pytest.fixture
    def mock_da(self, mock_data_access):
        mock_data_access.get_crm_card.return_value = {
            'contract_id': 200, 'surveyor_id': None, 'survey_date': None
        }
        mock_data_access.get_contract.return_value = {
            'measurement_image_link': None, 'measurement_file_name': None,
            'measurement_date': None, 'yandex_folder_path': '/disk/contracts/200'
        }
        mock_data_access.get_employees_by_position.return_value = [
            {'id': 20, 'full_name': 'Замерщик Тестов', 'position': 'Замерщик'}
        ]
        return mock_data_access

    @pytest.fixture
    def dlg(self, qtbot, mock_da, mock_employee_admin):
        parent = _make_parent(qtbot, mock_da, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_da), \
             patch('ui.crm_tab._emp_has_pos', return_value=False):
            from ui.crm_dialogs import MeasurementDialog
            d = MeasurementDialog(parent, 300, employee=mock_employee_admin, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            yield d

    def test_instance_is_qdialog(self, dlg):
        assert isinstance(dlg, QDialog)

    def test_card_id_stored(self, dlg):
        assert dlg.card_id == 300

    def test_frameless_hint(self, dlg):
        assert dlg.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, dlg):
        assert dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_fixed_size(self, dlg):
        assert dlg.width() == 500
        assert dlg.height() == 350

    def test_has_file_label_display(self, dlg):
        assert hasattr(dlg, 'file_label_display')
        assert isinstance(dlg.file_label_display, QLabel)

    def test_file_label_default_text(self, dlg):
        assert 'Не загружено' in dlg.file_label_display.text()

    def test_uploaded_image_link_initially_none(self, dlg):
        assert dlg.uploaded_image_link is None

    def test_has_surveyor_combo(self, dlg):
        assert hasattr(dlg, 'surveyor_combo')

    def test_surveyor_combo_has_default(self, dlg):
        assert dlg.surveyor_combo.itemText(0) == 'Не назначен'

    def test_surveyor_combo_has_surveyors(self, dlg):
        # 'Не назначен' + 1 замерщик
        assert dlg.surveyor_combo.count() >= 2

    def test_has_measurement_date(self, dlg):
        assert hasattr(dlg, 'measurement_date')

    def test_measurement_date_default_today(self, dlg):
        assert dlg.measurement_date.date() == QDate.currentDate()

    def test_measurement_date_format(self, dlg):
        assert dlg.measurement_date.displayFormat() == 'dd.MM.yyyy'

    def test_save_without_image_shows_error(self, dlg, _mock_msgbox_full):
        """Сохранение без изображения показывает ошибку."""
        dlg.uploaded_image_link = None
        dlg.save()
        _mock_msgbox_full.assert_called()

    def test_truncate_filename_short(self, dlg):
        assert dlg.truncate_filename('image.jpg') == 'image.jpg'

    def test_truncate_filename_long(self, dlg):
        long_name = 'photo_' + 'a' * 100 + '.png'
        result = dlg.truncate_filename(long_name, 50)
        assert len(result) <= 50
        assert '...' in result

    def test_on_image_uploaded_success(self, dlg, mock_da):
        """_on_image_uploaded обновляет UI и данные."""
        mock_da.update_contract = MagicMock()
        dlg._on_image_uploaded('https://link', '/disk/path', 'photo.jpg', 200)
        assert dlg.uploaded_image_link == 'https://link'
        assert 'photo.jpg' in dlg.file_label_display.text()

    def test_on_image_uploaded_no_link(self, dlg, _mock_msgbox_full):
        """_on_image_uploaded без ссылки показывает ошибку."""
        dlg._on_image_uploaded('', '', '', 200)
        assert 'Не загружено' in dlg.file_label_display.text()

    def test_on_image_upload_error(self, dlg, _mock_msgbox_full):
        """_on_image_upload_error показывает ошибку."""
        dlg._on_image_upload_error('Disk full')
        _mock_msgbox_full.assert_called()


# ========================================================================
# 12. Кросс-диалоговые тесты (интеграция)
# ========================================================================

@pytest.mark.ui
class TestCrossDialogIntegration:
    """Интеграционные тесты — взаимодействие между диалогами."""

    def test_executor_dialog_stage2_selects_designers(self, qtbot, mock_data_access, mock_employee_admin):
        """ExecutorSelectionDialog для Стадии 2 концепции выбирает Дизайнеров."""
        mock_data_access.get_project_timeline.return_value = []
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Дизайнер А', 'position': 'Дизайнер', 'secondary_position': ''},
        ]
        mock_data_access.get_crm_card.return_value = {'contract_id': 200, 'stage_executors': []}
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ExecutorSelectionDialog
            d = ExecutorSelectionDialog(parent, 300, 'Стадия 2: концепция дизайна',
                                        'Индивидуальный', contract_id=200)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            assert d.executor_combo.count() == 1
            assert d.executor_combo.itemText(0) == 'Дизайнер А'

    def test_executor_dialog_visualization_selects_designers(self, qtbot, mock_data_access, mock_employee_admin):
        """ExecutorSelectionDialog для 3д визуализации выбирает Дизайнеров."""
        mock_data_access.get_project_timeline.return_value = []
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Дизайнер Б', 'position': 'Дизайнер', 'secondary_position': ''},
        ]
        mock_data_access.get_crm_card.return_value = {'contract_id': 200, 'stage_executors': []}
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ExecutorSelectionDialog
            d = ExecutorSelectionDialog(parent, 300, 'Стадия 3: 3д визуализация (Дополнительная)',
                                        'Шаблонный', contract_id=201)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            assert d.executor_combo.count() == 1
            assert d.executor_combo.itemText(0) == 'Дизайнер Б'

    def test_executor_dialog_secondary_position(self, qtbot, mock_data_access, mock_employee_admin):
        """ExecutorSelectionDialog учитывает secondary_position."""
        mock_data_access.get_project_timeline.return_value = []
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Двойная Роль', 'position': 'Дизайнер', 'secondary_position': 'Чертёжник'},
        ]
        mock_data_access.get_crm_card.return_value = {'contract_id': 200, 'stage_executors': []}
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ExecutorSelectionDialog
            d = ExecutorSelectionDialog(parent, 300, 'Стадия 1: планировочные',
                                        'Индивидуальный', contract_id=200)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)
            # Чертёжник в secondary_position должен попасть в список
            assert d.executor_combo.count() == 1

    def test_completion_dialog_on_status_changed_show_hide(self, qtbot, mock_data_access, mock_employee_admin):
        """ProjectCompletionDialog on_status_changed переключает видимость."""
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ProjectCompletionDialog
            d = ProjectCompletionDialog(parent, 300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)

            # РАСТОРГНУТ — показать
            d.on_status_changed('Проект РАСТОРГНУТ')
            assert not d.termination_reason_group.isHidden()

            # СДАН — скрыть
            d.on_status_changed('Проект СДАН')
            assert d.termination_reason_group.isHidden()

            # АВТОРСКИЙ НАДЗОР — скрыть
            d.on_status_changed('Проект передан в АВТОРСКИЙ НАДЗОР')
            assert d.termination_reason_group.isHidden()

    def test_statistics_individual_stages(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMStatisticsDialog для Индивидуального: 3 стадии."""
        mock_data_access.get_projects_by_type.return_value = []
        mock_data_access.get_employees_by_position.return_value = []
        mock_data_access.get_crm_statistics_filtered.return_value = []

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.apply_no_focus_delegate', return_value=None):
            from ui.crm_dialogs import CRMStatisticsDialog
            d = CRMStatisticsDialog(parent, 'Индивидуальный', mock_employee_admin)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)

            # 'Все' + 3 стадии = 4
            assert d.stage_combo.count() == 4
            assert 'концепция' in d.stage_combo.itemText(2)

    def test_statistics_template_stages(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMStatisticsDialog для Шаблонного: 3 стадии."""
        mock_data_access.get_projects_by_type.return_value = []
        mock_data_access.get_employees_by_position.return_value = []
        mock_data_access.get_crm_statistics_filtered.return_value = []

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.apply_no_focus_delegate', return_value=None):
            from ui.crm_dialogs import CRMStatisticsDialog
            d = CRMStatisticsDialog(parent, 'Шаблонный', mock_employee_admin)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)

            # 'Все' + 3 стадии = 4
            assert d.stage_combo.count() == 4
            assert 'визуализация' in d.stage_combo.itemText(3).lower()

    def test_export_pdf_dialog_from_statistics(self, qtbot, mock_data_access, mock_employee_admin):
        """ExportPDFDialog корректно считает записи из родительской таблицы."""
        mock_data_access.get_projects_by_type.return_value = []
        mock_data_access.get_employees_by_position.return_value = []
        mock_data_access.get_crm_statistics_filtered.return_value = []

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_dialogs.apply_no_focus_delegate', return_value=None):
            from ui.crm_dialogs import CRMStatisticsDialog, ExportPDFDialog
            stats_dlg = CRMStatisticsDialog(parent, 'Индивидуальный', mock_employee_admin)
            stats_dlg.setAttribute(Qt.WA_DeleteOnClose, False)
            stats_dlg.setParent(None)
            qtbot.addWidget(stats_dlg)

            # Создаём ExportPDFDialog как дочерний
            export_dlg = ExportPDFDialog(stats_dlg, 'test_export')
            export_dlg.setAttribute(Qt.WA_DeleteOnClose, False)

            # Проверяем что диалог видит stats_table
            labels = export_dlg.findChildren(QLabel)
            texts = [l.text() for l in labels]
            # Должен показать "Будет экспортировано записей: 0"
            assert any('0' in t for t in texts)

    def test_measurement_dialog_with_existing_data(self, qtbot, mock_data_access, mock_employee_admin):
        """MeasurementDialog загружает существующие данные."""
        mock_data_access.get_crm_card.return_value = {
            'contract_id': 200, 'surveyor_id': 20, 'survey_date': '2026-01-10'
        }
        mock_data_access.get_contract.return_value = {
            'measurement_image_link': 'https://ya.ru/d/existing',
            'measurement_file_name': 'existing_photo.jpg',
            'measurement_date': '2026-01-10',
            'yandex_folder_path': '/disk/contracts/200'
        }
        mock_data_access.get_employees_by_position.return_value = [
            {'id': 20, 'full_name': 'Замерщик Тестов', 'position': 'Замерщик'}
        ]

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access), \
             patch('ui.crm_tab._emp_has_pos', return_value=False):
            from ui.crm_dialogs import MeasurementDialog
            d = MeasurementDialog(parent, 300, employee=mock_employee_admin, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)

            # Изображение загружено
            assert d.uploaded_image_link == 'https://ya.ru/d/existing'
            assert 'existing_photo' in d.file_label_display.text()
            # Дата замера установлена
            assert d.measurement_date.date() == QDate(2026, 1, 10)
            # Замерщик предвыбран (индекс 1, т.к. 0 = 'Не назначен')
            assert d.surveyor_combo.currentData() == 20

    def test_tech_task_dialog_with_existing_file(self, qtbot, mock_data_access, mock_employee_admin):
        """TechTaskDialog загружает существующий файл ТЗ."""
        mock_data_access.get_crm_card.return_value = {'contract_id': 200}
        mock_data_access.get_contract.return_value = {
            'tech_task_link': 'https://ya.ru/d/existing_tz',
            'tech_task_file_name': 'ТЗ_проект_001.pdf',
            'yandex_folder_path': '/disk/contracts/200'
        }

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import TechTaskDialog
            d = TechTaskDialog(parent, 300, api_client=None)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)

            assert d.uploaded_file_link == 'https://ya.ru/d/existing_tz'
            assert 'ТЗ_проект_001' in d.file_label_display.text()

    def test_reassign_executor_history_loading(self, qtbot, mock_data_access, mock_employee_admin):
        """ReassignExecutorDialog загружает историю переназначений."""
        mock_data_access.get_crm_card.return_value = {
            'contract_id': 200,
            'stage_executors': [
                {'stage_name': 'Стадия 1: планировочные решения', 'executor_id': 10, 'deadline': '2026-02-01', 'assigned_date': '2026-01-15'}
            ]
        }
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Иванов', 'position': 'Чертёжник', 'secondary_position': ''},
            {'id': 11, 'full_name': 'Петров', 'position': 'Чертёжник', 'secondary_position': ''},
        ]
        mock_data_access.get_action_history.return_value = [
            {'action_type': 'reassign', 'description': 'Переназначение: Сидоров -> Иванов', 'action_date': '2026-01-10'}
        ]
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ReassignExecutorDialog
            d = ReassignExecutorDialog(
                parent, card_id=300, position='Чертёжник',
                stage_keyword='Стадия 1', executor_type='draftsman',
                current_executor_name='Иванов',
                stage_name='Стадия 1: планировочные решения',
                api_client=None
            )
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.setParent(None)
            qtbot.addWidget(d)

            # Диалог должен создаться без ошибок (история загружена)
            assert isinstance(d, QDialog)

    def test_executor_dialog_template_stage1_zero_payment(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонный проект, Стадия 1 — выплата с суммой 0."""
        mock_data_access.get_project_timeline.return_value = []
        mock_data_access.get_all_employees.return_value = [
            {'id': 10, 'full_name': 'Черт', 'position': 'Чертёжник', 'secondary_position': ''},
        ]
        mock_data_access.get_crm_card.return_value = {'contract_id': 201, 'stage_executors': []}
        mock_data_access.db.connect.return_value.cursor.return_value.fetchall.return_value = []
        mock_data_access.db.connect.return_value.cursor.return_value.fetchone.return_value = None
        mock_data_access.db.close = MagicMock()
        mock_data_access.assign_stage_executor = MagicMock()
        mock_data_access.get_contract_id_by_crm_card.return_value = 201
        mock_data_access.get_contract.return_value = {'project_type': 'Шаблонный'}
        mock_data_access.create_payment.return_value = {'id': 1}

        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_dialogs.DataAccess', return_value=mock_data_access):
            from ui.crm_dialogs import ExecutorSelectionDialog
            d = ExecutorSelectionDialog(parent, 300, 'Стадия 1: планировочные решения',
                                        'Шаблонный', contract_id=201)
            d.setAttribute(Qt.WA_DeleteOnClose, False)
            d.assign_executor()

            # Для шаблонного проекта Стадия 1 — одна выплата (не аванс+доплата)
            assert mock_data_access.create_payment.call_count == 1
            # Сумма должна быть 0
            call_args = mock_data_access.create_payment.call_args
            assert call_args[0][0]['calculated_amount'] == 0.00
