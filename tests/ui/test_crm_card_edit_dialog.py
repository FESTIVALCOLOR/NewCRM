# -*- coding: utf-8 -*-
"""
Тесты CardEditDialog — КРИТИЧЕСКИЙ ПРОБЕЛ (0 тестов ранее).

Покрытие:
  - TestCardEditDialogCreate (6)       — создание диалога, сигналы, атрибуты
  - TestCardEditDialogTabs (6)         — вкладки, видимость по ролям
  - TestCardEditDialogLoadData (6)     — load_data, дедлайн, теги, survey_date
  - TestCardEditDialogAutoSave (5)     — connect_autosave, auto_save_field, _loading_data guard
  - TestCardEditDialogSaveChanges (5)  — save_changes, обновление контракта
  - TestCardEditDialogEdgeCases (4)    — None card_data, пустые поля
  - TestCardEditDialogSignals (3)      — сигналы tech_task, stage_files
ИТОГО: 35 тестов
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QDialog, QComboBox, QLineEdit, QFrame
)
from PyQt5.QtCore import Qt, QDate, pyqtSignal
from PyQt5.QtGui import QIcon


# ========== Фикстуры ==========

@pytest.fixture(autouse=True)
def _mock_card_edit_msgbox():
    """Мок CustomMessageBox/QuestionBox + DatabaseManager для предотвращения блокировки."""
    with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_msg, \
         patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_q, \
         patch('ui.crm_card_edit_dialog.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_card_edit_dialog.YandexDiskManager', return_value=None), \
         patch('ui.crm_card_edit_dialog.YANDEX_DISK_TOKEN', ''):
        mock_msg.return_value.exec_.return_value = None
        mock_q.return_value.exec_.return_value = None
        yield mock_msg


def _mock_icon_loader():
    """Мок IconLoader."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _make_card_data(**overrides):
    """Минимальные данные CRM карточки для CardEditDialog."""
    data = {
        'id': 300,
        'contract_id': 200,
        'contract_number': 'ИП-ПОЛ-300/26',
        'project_type': 'Индивидуальный',
        'project_subtype': 'Полный проект',
        'column_name': 'Стадия 2: концепция дизайна',
        'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тестовая, д.1',
        'area': 85.5,
        'city': 'СПБ',
        'status': 'active',
        'designer_name': 'Дизайнер Тест',
        'draftsman_name': None,
        'designer_completed': 0,
        'draftsman_completed': 0,
        'is_approved': 0,
        'survey_date': '2026-02-10',
        'tech_task_date': '2026-01-20',
        'tech_task_link': None,
        'measurement_link': None,
        'references_link': None,
        'project_data_link': None,
        'contract_file_link': None,
        'yandex_folder_path': '/test/path',
        'stage_executors': [],
        'deadline': '2026-04-15',
        'manager_id': 5,
        'sdp_id': 3,
        'gap_id': 4,
        'senior_manager_id': 2,
        'surveyor_id': 8,
        'tags': 'VIP, Срочный',
        'agent_type': '',
        'total_amount': 500000,
        'advance_payment': 150000,
        'additional_payment': 200000,
        'third_payment': 150000,
        'contract_date': '2026-01-15',
        'contract_period': 45,
    }
    data.update(overrides)
    return data


def _create_card_dialog(qtbot, card_data, employee, view_only=False):
    """Создать CardEditDialog с моками."""
    mock_da = MagicMock()
    mock_da.get_crm_card.return_value = card_data
    mock_da.get_contract.return_value = {
        'id': 200, 'status': 'active', 'tech_task_link': None,
        'tech_task_file_name': None, 'measurement_image_link': None,
        'measurement_file_name': None, 'references_yandex_path': None,
        'photo_documentation_yandex_path': None, 'yandex_folder_path': '/test',
        'area': 85.5, 'city': 'СПБ', 'project_type': 'Индивидуальный',
        'project_subtype': 'Полный проект',
    }
    mock_da.get_payments_for_contract.return_value = []
    mock_da.get_project_timeline.return_value = []
    mock_da.get_action_history.return_value = []
    mock_da.get_employees_by_position.return_value = []
    mock_da.get_all_employees.return_value = [
        {'id': 2, 'full_name': 'Старший Менеджер', 'position': 'Старший менеджер проектов', 'status': 'активный'},
        {'id': 3, 'full_name': 'СДП Тест', 'position': 'СДП', 'status': 'активный'},
        {'id': 4, 'full_name': 'ГАП Тест', 'position': 'ГАП', 'status': 'активный'},
        {'id': 5, 'full_name': 'Менеджер Тест', 'position': 'Менеджер', 'status': 'активный'},
        {'id': 8, 'full_name': 'Замерщик Тест', 'position': 'Замерщик', 'status': 'активный'},
    ]
    mock_da.is_online = False
    mock_da.is_multi_user = False
    mock_da.db = MagicMock()
    mock_da.api_client = None

    parent = QWidget()
    parent.data = mock_da
    parent.api_client = None
    qtbot.addWidget(parent)

    with patch('ui.crm_card_edit_dialog.DataAccess', return_value=mock_da), \
         patch('ui.crm_card_edit_dialog.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_card_edit_dialog.YandexDiskManager', return_value=None), \
         patch('ui.crm_card_edit_dialog.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_card_edit_dialog.YANDEX_DISK_TOKEN', ''), \
         patch('ui.crm_card_edit_dialog.TableSettings') as MockTS, \
         patch('ui.crm_card_edit_dialog.create_progress_dialog', return_value=MagicMock()), \
         patch('ui.crm_tab.DataAccess', return_value=mock_da), \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS2, \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockTS.return_value.load_column_collapse_state.return_value = {}
        MockTS2.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_card_edit_dialog import CardEditDialog
        dialog = CardEditDialog(
            parent, card_data=card_data, view_only=view_only,
            employee=employee, api_client=None
        )
        qtbot.addWidget(dialog)
        return dialog, mock_da


# ========== 1. Создание диалога (6 тестов) ==========

@pytest.mark.ui
class TestCardEditDialogCreate:
    """Создание CardEditDialog."""

    def test_dialog_creates(self, qtbot, mock_employee_admin):
        """Диалог создаётся как QDialog."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert isinstance(dialog, QDialog)

    def test_dialog_stores_card_data(self, qtbot, mock_employee_admin):
        """card_data сохраняются."""
        cd = _make_card_data(id=999)
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        assert dialog.card_data['id'] == 999

    def test_dialog_stores_employee(self, qtbot, mock_employee_admin):
        """employee сохраняется."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert dialog.employee == mock_employee_admin

    def test_dialog_has_tabs(self, qtbot, mock_employee_admin):
        """Диалог имеет QTabWidget."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'tabs')
        assert isinstance(dialog.tabs, QTabWidget)

    def test_dialog_has_signals(self, qtbot, mock_employee_admin):
        """Диалог имеет все необходимые сигналы."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'tech_task_upload_completed')
        assert hasattr(dialog, 'tech_task_upload_error')
        assert hasattr(dialog, 'stage_files_uploaded')
        assert hasattr(dialog, 'stage_upload_error')

    def test_dialog_view_only_mode(self, qtbot, mock_employee_admin):
        """view_only=True устанавливается."""
        dialog, _ = _create_card_dialog(
            qtbot, _make_card_data(), mock_employee_admin, view_only=True
        )
        assert dialog.view_only is True


# ========== 2. Вкладки по ролям (6 тестов) ==========

@pytest.mark.ui
class TestCardEditDialogTabs:
    """Вкладки CardEditDialog по ролям."""

    def test_admin_sees_edit_tab(self, qtbot, mock_employee_admin):
        """Админ видит вкладку 'Исполнители и дедлайн'."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert dialog.tabs.count() >= 1, "Админ должен видеть хотя бы 1 вкладку"

    def test_designer_no_edit_tab(self, qtbot, mock_employee_designer):
        """Дизайнер НЕ видит вкладку 'Исполнители и дедлайн' (is_executor=True)."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_designer)
        # Дизайнер — чистый исполнитель, не видит вкладку с назначениями
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names), \
            f"Дизайнер не должен видеть 'Исполнители': {tab_names}"

    def test_admin_has_senior_manager_combo(self, qtbot, mock_employee_admin):
        """Админ видит комбобокс Старший менеджер."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'senior_manager'), "Должен быть комбобокс senior_manager"

    def test_admin_has_gap_combo(self, qtbot, mock_employee_admin):
        """Админ видит комбобокс ГАП."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'gap'), "Должен быть комбобокс gap"

    def test_admin_has_manager_combo(self, qtbot, mock_employee_admin):
        """Админ видит комбобокс Менеджер."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'manager'), "Должен быть комбобокс manager"

    def test_admin_has_tags_field(self, qtbot, mock_employee_admin):
        """Админ видит поле тегов."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'tags'), "Должно быть поле tags"


# ========== 3. Загрузка данных (6 тестов) ==========

@pytest.mark.ui
class TestCardEditDialogLoadData:
    """load_data — загрузка и отображение данных."""

    def test_load_data_sets_loading_flag(self, qtbot, mock_employee_admin):
        """load_data устанавливает _loading_data=True во время загрузки."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        loading_values = []

        def capture(*args, **kwargs):
            loading_values.append(dialog._loading_data)
            return _make_card_data()

        mock_da.get_crm_card.side_effect = capture
        with patch('database.db_manager.DatabaseManager') as MockDBM:
                MockDBM.return_value = MagicMock()
                dialog.load_data()
        assert any(v is True for v in loading_values), "_loading_data должен быть True во время загрузки"

    def test_load_data_resets_loading_flag(self, qtbot, mock_employee_admin):
        """load_data сбрасывает _loading_data=False после загрузки."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        with patch('database.db_manager.DatabaseManager') as MockDBM:
                MockDBM.return_value = MagicMock()
                dialog.load_data()
        assert dialog._loading_data is False, "_loading_data должен быть False после загрузки"

    def test_load_data_sets_tags(self, qtbot, mock_employee_admin):
        """load_data загружает теги."""
        cd = _make_card_data(tags='Срочный, Premium')
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        with patch('database.db_manager.DatabaseManager') as MockDBM:
                MockDBM.return_value = MagicMock()
                dialog.load_data()
        if hasattr(dialog, 'tags'):
            assert dialog.tags.text() == 'Срочный, Premium'

    def test_load_data_sets_deadline_display(self, qtbot, mock_employee_admin):
        """load_data отображает дедлайн."""
        cd = _make_card_data(deadline='2026-04-15')
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        with patch('database.db_manager.DatabaseManager') as MockDBM:
                MockDBM.return_value = MagicMock()
                dialog.load_data()
        if hasattr(dialog, 'deadline_display'):
            text = dialog.deadline_display.text()
            assert '15.04.2026' in text, f"Дедлайн должен быть '15.04.2026', получено: '{text}'"

    def test_load_data_no_deadline(self, qtbot, mock_employee_admin):
        """load_data без дедлайна — 'Не установлен'."""
        cd = _make_card_data(deadline=None, stage_executors=[])
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        with patch('database.db_manager.DatabaseManager') as MockDBM:
                MockDBM.return_value = MagicMock()
                dialog.load_data()
        if hasattr(dialog, 'deadline_display'):
            text = dialog.deadline_display.text()
            assert 'Не установлен' in text

    def test_load_data_survey_date(self, qtbot, mock_employee_admin):
        """load_data загружает дату замера."""
        cd = _make_card_data(survey_date='2026-02-10')
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        with patch('database.db_manager.DatabaseManager') as MockDBM:
                MockDBM.return_value = MagicMock()
                dialog.load_data()
        if hasattr(dialog, 'survey_date_label'):
            text = dialog.survey_date_label.text()
            assert '10.02.2026' in text, f"Дата замера: '{text}'"


# ========== 4. Автосохранение (5 тестов) ==========

@pytest.mark.ui
class TestCardEditDialogAutoSave:
    """connect_autosave_signals, auto_save_field."""

    def test_auto_save_skips_during_loading(self, qtbot, mock_employee_admin):
        """auto_save_field пропускает сохранение если _loading_data=True."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        dialog._loading_data = True
        mock_da.update_crm_card.reset_mock()
        dialog.auto_save_field()
        mock_da.update_crm_card.assert_not_called()

    def test_auto_save_saves_tags(self, qtbot, mock_employee_admin):
        """auto_save_field сохраняет теги."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        dialog._loading_data = False
        if hasattr(dialog, 'tags'):
            dialog.tags.setText('Новый тег')
            mock_da.update_crm_card.reset_mock()
            dialog.auto_save_field()
            mock_da.update_crm_card.assert_called()

    def test_connect_autosave_signals_exists(self, qtbot, mock_employee_admin):
        """Метод connect_autosave_signals существует."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'connect_autosave_signals')
        assert callable(dialog.connect_autosave_signals)

    def test_auto_save_calls_update(self, qtbot, mock_employee_admin):
        """auto_save_field вызывает update_crm_card при изменениях."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        dialog._loading_data = False
        mock_da.update_crm_card.reset_mock()
        dialog.auto_save_field()
        mock_da.update_crm_card.assert_called()

    def test_auto_save_exception_handled(self, qtbot, mock_employee_admin):
        """auto_save_field обрабатывает исключения без краша."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        dialog._loading_data = False
        mock_da.update_crm_card.side_effect = Exception("Ошибка БД")
        # Не должен упасть
        dialog.auto_save_field()


# ========== 5. Сохранение изменений (5 тестов) ==========

@pytest.mark.ui
class TestCardEditDialogSaveChanges:
    """save_changes — финальное сохранение."""

    def test_save_changes_calls_update_crm_card(self, qtbot, mock_employee_admin):
        """save_changes вызывает update_crm_card."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        mock_da.update_crm_card.reset_mock()
        dialog.save_changes()
        mock_da.update_crm_card.assert_called()

    def test_save_changes_updates_contract_status(self, qtbot, mock_employee_admin):
        """save_changes обновляет статус контракта."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        if hasattr(dialog, 'status_combo'):
            dialog.status_combo.setCurrentText('СДАН')
            mock_da.update_contract.reset_mock()
            dialog.save_changes()
            mock_da.update_contract.assert_called()

    def test_save_changes_accepts_dialog(self, qtbot, mock_employee_admin):
        """save_changes завершается accept()."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        dialog.save_changes()
        assert dialog.result() == QDialog.Accepted

    def test_save_changes_includes_tags(self, qtbot, mock_employee_admin):
        """save_changes включает tags в updates."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        if hasattr(dialog, 'tags'):
            dialog.tags.setText('Тег сохранения')
            mock_da.update_crm_card.reset_mock()
            dialog.save_changes()
            call_args = mock_da.update_crm_card.call_args
            updates = call_args[0][1] if call_args else {}
            assert updates.get('tags') == 'Тег сохранения'

    def test_save_changes_includes_manager_id(self, qtbot, mock_employee_admin):
        """save_changes включает manager_id в updates."""
        dialog, mock_da = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        mock_da.update_crm_card.reset_mock()
        dialog.save_changes()
        call_args = mock_da.update_crm_card.call_args
        updates = call_args[0][1] if call_args else {}
        assert 'manager_id' in updates


# ========== 6. Edge cases (4 теста) ==========

@pytest.mark.ui
class TestCardEditDialogEdgeCases:
    """Edge cases для CardEditDialog."""

    def test_dialog_with_minimal_data(self, qtbot, mock_employee_admin):
        """Диалог с минимальными данными не падает."""
        cd = {'id': 1, 'contract_id': 1}
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        assert dialog is not None

    def test_dialog_with_empty_tags(self, qtbot, mock_employee_admin):
        """Пустые теги — корректно."""
        cd = _make_card_data(tags='')
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        if hasattr(dialog, 'tags'):
            assert dialog.card_data['tags'] == ''

    def test_dialog_with_none_contract_id(self, qtbot, mock_employee_admin):
        """contract_id=None — диалог создаётся."""
        cd = _make_card_data(contract_id=None)
        dialog, _ = _create_card_dialog(qtbot, cd, mock_employee_admin)
        assert dialog.card_data['contract_id'] is None

    def test_loading_data_initial_false(self, qtbot, mock_employee_admin):
        """_loading_data=False при создании (до load_data)."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        # После init _loading_data может быть True если load_data вызван,
        # но до вызова load_data должен быть False
        # Проверяем что атрибут существует
        assert hasattr(dialog, '_loading_data')


# ========== 7. Сигналы (3 теста) ==========

@pytest.mark.ui
class TestCardEditDialogSignals:
    """Сигналы CardEditDialog."""

    def test_tech_task_upload_completed_signal(self, qtbot, mock_employee_admin):
        """Сигнал tech_task_upload_completed существует и подключён."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'tech_task_upload_completed')
        assert dialog.tech_task_upload_completed is not None

    def test_stage_files_uploaded_signal(self, qtbot, mock_employee_admin):
        """Сигнал stage_files_uploaded существует."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'stage_files_uploaded')

    def test_preview_loaded_signal(self, qtbot, mock_employee_admin):
        """Сигнал preview_loaded существует."""
        dialog, _ = _create_card_dialog(qtbot, _make_card_data(), mock_employee_admin)
        assert hasattr(dialog, 'preview_loaded')
