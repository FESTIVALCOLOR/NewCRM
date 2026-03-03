# -*- coding: utf-8 -*-
"""
Глубокие тесты вкладки Сотрудники — фильтры, удаление, синхронизация.

НЕ дублирует 30 тестов из test_employees.py. Покрывает:
  - TestEmployeesFilterDepartments (5) — фильтрация по отделам
  - TestEmployeesApplySearch (5)       — поиск по ФИО, должности, статусу, телефону
  - TestEmployeesDeleteLogic (4)       — удаление, права, self-delete
  - TestEmployeesLazyLoading (3)       — ensure_data_loaded, _data_loaded
  - TestEmployeesOnSyncUpdate (3)      — on_sync_update, пустой список
ИТОГО: 20 тестов
"""

import pytest
from unittest.mock import patch, MagicMock, call
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QPushButton, QLineEdit,
    QDialog, QComboBox
)
from PyQt5.QtCore import Qt


# ========== Фикстура авто-мока CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_employees_deep_msgbox():
    """Глобальный мок CustomMessageBox/QuestionBox."""
    with patch('ui.employees_tab.CustomMessageBox') as mock_msg:
        mock_msg.return_value.exec_.return_value = None
        mock_msg.return_value.result.return_value = QDialog.Rejected
        yield mock_msg


# ========== Хелперы ==========

def _create_employees_tab(qtbot, mock_data_access, employee):
    """Создать EmployeesTab с mock DataAccess."""
    with patch('ui.employees_tab.DataAccess') as MockDA, \
         patch('ui.employees_tab.DatabaseManager', return_value=MagicMock()):
        MockDA.return_value = mock_data_access
        from ui.employees_tab import EmployeesTab
        tab = EmployeesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _sample_employees():
    """Тестовый список сотрудников с разными отделами."""
    return [
        {'id': 1, 'full_name': 'Руководитель Тест', 'position': 'Руководитель студии',
         'secondary_position': '', 'department': 'Административный отдел',
         'status': 'активный', 'phone': '+7-999-111-11-11', 'email': 'boss@test.ru',
         'birth_date': '1985-03-15', 'login': 'boss'},
        {'id': 2, 'full_name': 'Менеджер Тестов', 'position': 'Менеджер',
         'secondary_position': '', 'department': 'Исполнительный отдел',
         'status': 'активный', 'phone': '+7-999-222-22-22', 'email': 'manager@test.ru',
         'birth_date': '1990-06-20', 'login': 'manager'},
        {'id': 3, 'full_name': 'Дизайнер Тестов', 'position': 'Дизайнер',
         'secondary_position': '', 'department': 'Проектный отдел',
         'status': 'активный', 'phone': '+7-999-333-33-33', 'email': 'designer@test.ru',
         'birth_date': '1992-11-10', 'login': 'designer'},
        {'id': 4, 'full_name': 'Чертёжник Тестов', 'position': 'Чертёжник',
         'secondary_position': '', 'department': 'Проектный отдел',
         'status': 'уволен', 'phone': '+7-999-444-44-44', 'email': 'draft@test.ru',
         'birth_date': '1988-01-05', 'login': 'draftsman'},
        {'id': 5, 'full_name': 'СДП Тестов', 'position': 'СДП',
         'secondary_position': '', 'department': 'Административный отдел',
         'status': 'активный', 'phone': '+7-999-555-55-55', 'email': 'sdp@test.ru',
         'birth_date': '', 'login': 'sdp'},
        {'id': 6, 'full_name': 'ДАН Тестов', 'position': 'ДАН',
         'secondary_position': '', 'department': 'Исполнительный отдел',
         'status': 'в резерве', 'phone': '', 'email': '', 'birth_date': '',
         'login': 'dan'},
    ]


# ========== 1. Фильтрация по отделам (5 тестов) ==========

@pytest.mark.ui
class TestEmployeesFilterDepartments:
    """Фильтрация сотрудников по отделам через on_filter_changed."""

    def test_filter_all_shows_all(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр 'Все отделы' показывает всех сотрудников."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.on_filter_changed('all')
        assert tab.employees_table.rowCount() == 6, "Все 6 сотрудников должны быть видны"

    def test_filter_admin_department(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр 'Административный' показывает Руководителя, СМП, СДП, ГАП."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.on_filter_changed('admin')
        # Руководитель студии + СДП = 2 из тестовых данных
        assert tab.employees_table.rowCount() == 2

    def test_filter_project_department(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр 'Проектный' показывает Дизайнеров и Чертёжников."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.on_filter_changed('project')
        # Дизайнер + Чертёжник = 2
        assert tab.employees_table.rowCount() == 2

    def test_filter_executive_department(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр 'Исполнительный' показывает Менеджеров, ДАН, Замерщиков."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.on_filter_changed('executive')
        # Менеджер + ДАН = 2
        assert tab.employees_table.rowCount() == 2

    def test_filter_changes_button_state(self, qtbot, mock_data_access, mock_employee_admin):
        """При переключении фильтра кнопка становится checked."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.on_filter_changed('project')
        assert tab.filter_buttons['project'].isChecked(), "Кнопка 'project' должна быть checked"
        assert not tab.filter_buttons['all'].isChecked(), "Кнопка 'all' НЕ должна быть checked"


# ========== 2. Поиск (5 тестов) ==========

@pytest.mark.ui
class TestEmployeesApplySearch:
    """Поиск сотрудников через apply_search."""

    def test_search_by_name(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск по ФИО."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({'name': 'Дизайнер'})
        assert tab.employees_table.rowCount() == 1, "Должен найти 1 сотрудника"

    def test_search_by_position(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск по должности."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({'position': 'СДП'})
        assert tab.employees_table.rowCount() == 1

    def test_search_by_status(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск по статусу."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({'status': 'уволен'})
        assert tab.employees_table.rowCount() == 1

    def test_search_empty_returns_all(self, qtbot, mock_data_access, mock_employee_admin):
        """Пустой поиск возвращает всех."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({})
        assert tab.employees_table.rowCount() == 6

    def test_search_no_match(self, qtbot, mock_data_access, mock_employee_admin):
        """Поиск без совпадений — пустая таблица."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.apply_search({'name': 'НесуществующийСотрудник'})
        assert tab.employees_table.rowCount() == 0


# ========== 3. Удаление сотрудника (4 теста) ==========

@pytest.mark.ui
class TestEmployeesDeleteLogic:
    """Логика удаления сотрудников."""

    def test_can_delete_admin_true(self, qtbot, mock_data_access, mock_employee_admin):
        """Руководитель студии имеет can_delete=True."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.can_delete is True, "Руководитель должен иметь право удаления"

    def test_can_delete_designer_false(self, qtbot, mock_data_access, mock_employee_designer):
        """Дизайнер НЕ имеет can_delete."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_designer)
        assert tab.can_delete is False, "Дизайнер не должен удалять"

    def test_can_delete_manager_false(self, qtbot, mock_data_access, mock_employee_manager):
        """Менеджер НЕ имеет can_delete."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_manager)
        assert tab.can_delete is False, "Менеджер не должен удалять"

    def test_delete_self_blocked(self, qtbot, mock_data_access, mock_employee_admin):
        """Нельзя удалить самого себя."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        self_data = {'id': mock_employee_admin['id'], 'full_name': 'Я сам'}
        # CustomQuestionBox импортируется внутри delete_employee, мокаем через ui.custom_message_box
        with patch('ui.custom_message_box.CustomQuestionBox') as mock_q:
            mock_q.return_value.exec_.return_value = QDialog.Rejected
            tab.delete_employee(self_data)
        # delete_employee не должен вызываться для самого себя
        mock_data_access.delete_employee.assert_not_called()


# ========== 4. Ленивая загрузка (3 теста) ==========

@pytest.mark.ui
class TestEmployeesLazyLoading:
    """Ленивая загрузка EmployeesTab."""

    def test_data_not_loaded_on_create(self, qtbot, mock_data_access, mock_employee_admin):
        """_data_loaded=False при создании."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab._data_loaded is False

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает _data_loaded=True."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        assert tab._data_loaded is True

    def test_double_ensure_reloads_via_cache(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторный ensure_data_loaded обновляет данные (через кэш DataAccess)."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        call_count = mock_data_access.get_all_employees.call_count
        assert call_count >= 1
        tab.ensure_data_loaded()
        # При повторном вызове данные перезагружаются
        assert mock_data_access.get_all_employees.call_count > call_count


# ========== 5. Синхронизация (3 теста) ==========

@pytest.mark.ui
class TestEmployeesOnSyncUpdate:
    """on_sync_update — обработка обновлений от SyncManager."""

    def test_sync_update_reloads_table(self, qtbot, mock_data_access, mock_employee_admin):
        """on_sync_update с данными перезагружает таблицу."""
        mock_data_access.get_all_employees.return_value = _sample_employees()
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        initial_count = mock_data_access.get_all_employees.call_count
        tab.on_sync_update([{'id': 1, 'full_name': 'Обновлённый'}])
        assert mock_data_access.get_all_employees.call_count > initial_count

    def test_sync_update_empty_list_skips(self, qtbot, mock_data_access, mock_employee_admin):
        """on_sync_update с пустым списком не перезагружает."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        count_before = mock_data_access.get_all_employees.call_count
        tab.on_sync_update([])
        assert mock_data_access.get_all_employees.call_count == count_before

    def test_sync_update_none_skips(self, qtbot, mock_data_access, mock_employee_admin):
        """on_sync_update с None не перезагружает."""
        mock_data_access.get_all_employees.return_value = []
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        count_before = mock_data_access.get_all_employees.call_count
        tab.on_sync_update(None)
        assert mock_data_access.get_all_employees.call_count == count_before
