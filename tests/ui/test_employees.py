# -*- coding: utf-8 -*-
"""
Тесты вкладки Сотрудники — EmployeesTab, EmployeeDialog, EmployeeSearchDialog.
30 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QWidget, QTableWidget, QPushButton, QLineEdit,
    QDialog, QComboBox
)
from PyQt5.QtCore import Qt


# ========== Фикстура авто-мока CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_employees_msgbox():
    """Глобальный мок CustomMessageBox чтобы диалоги не блокировали тесты."""
    with patch('ui.employees_tab.CustomMessageBox') as mock_msg:
        mock_msg.return_value.exec_.return_value = None
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


def _create_employee_dialog(qtbot, parent_widget, employee_data=None, view_only=False):
    """Создать EmployeeDialog с parent_widget."""
    with patch('ui.employees_tab.DataAccess') as MockDA, \
         patch('ui.employees_tab.DatabaseManager', return_value=MagicMock()):
        MockDA.return_value = parent_widget.data
        from ui.employees_tab import EmployeeDialog
        dlg = EmployeeDialog(parent_widget, employee_data=employee_data, view_only=view_only)
        qtbot.addWidget(dlg)
        return dlg


def _create_employee_search_dialog(parent_widget):
    """Создать EmployeeSearchDialog."""
    from ui.employees_tab import EmployeeSearchDialog
    dlg = EmployeeSearchDialog(parent_widget)
    return dlg


# ========== 1. Рендеринг вкладки (6 тестов) ==========

@pytest.mark.ui
class TestEmployeesTabRendering:
    """Проверка рендеринга вкладки Сотрудники."""

    def test_tab_creates(self, qtbot, mock_data_access, mock_employee_admin):
        """Вкладка создаётся как QWidget."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_table_present(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица сотрудников существует."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'employees_table')
        assert isinstance(tab.employees_table, QTableWidget)

    def test_table_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Таблица имеет 8 колонок."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.employees_table.columnCount() == 8

    def test_can_edit_admin(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ имеет can_edit = True."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.can_edit is True

    def test_can_edit_designer_false(self, qtbot, mock_data_access, mock_employee_designer):
        """Дизайнер не может редактировать (can_edit = False)."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_designer)
        assert tab.can_edit is False

    def test_data_access_set(self, qtbot, mock_data_access, mock_employee_admin):
        """DataAccess назначен."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None


# ========== 2. Рендеринг диалога (8 тестов) ==========

@pytest.mark.ui
class TestEmployeeDialogRendering:
    """Проверка рендеринга диалога сотрудника."""

    def test_dialog_creates(self, qtbot, parent_widget):
        """Диалог создаётся."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert isinstance(dlg, QDialog)

    def test_full_name_field(self, qtbot, parent_widget):
        """Поле ФИО существует."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'full_name')
        assert isinstance(dlg.full_name, QLineEdit)

    def test_login_field(self, qtbot, parent_widget):
        """Поле логина существует."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'login')
        assert isinstance(dlg.login, QLineEdit)

    def test_password_masked(self, qtbot, parent_widget):
        """Пароль маскирован."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert dlg.password.echoMode() == QLineEdit.Password

    def test_position_combo(self, qtbot, parent_widget):
        """Комбобокс должности с 9 элементами."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'position')
        # Для Руководителя студии — 9 позиций
        assert dlg.position.count() == 9

    def test_secondary_position_combo(self, qtbot, parent_widget):
        """Комбобокс доп.должности существует."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'secondary_position')
        # "Нет" + 9 позиций
        assert dlg.secondary_position.count() >= 1

    def test_status_combo(self, qtbot, parent_widget):
        """Комбобокс статуса с 3 вариантами."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        assert hasattr(dlg, 'status')
        assert dlg.status.count() == 3  # активный, уволен, в резерве

    def test_edit_prefills_data(self, qtbot, parent_widget, sample_employee):
        """Редактирование — поля заполнены."""
        dlg = _create_employee_dialog(qtbot, parent_widget, employee_data=sample_employee)
        assert dlg.full_name.text() == sample_employee['full_name']


# ========== 3. Валидация (8 тестов) ==========

@pytest.mark.ui
class TestEmployeeValidation:
    """Валидация обязательных полей."""

    def test_empty_name_rejected(self, qtbot, parent_widget):
        """Пустое ФИО — ошибка."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('')
        dlg.login.setText('test_login')
        dlg.password.setText('pass1234')
        dlg.password_confirm.setText('pass1234')
        dlg.save_employee()
        assert dlg.result() != QDialog.Accepted

    def test_empty_login_rejected(self, qtbot, parent_widget):
        """Пустой логин — ошибка."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Тестов Тест')
        dlg.login.setText('')
        dlg.password.setText('pass1234')
        dlg.password_confirm.setText('pass1234')
        dlg.save_employee()
        assert dlg.result() != QDialog.Accepted

    def test_empty_password_on_create_rejected(self, qtbot, parent_widget):
        """Пустой пароль при создании — ошибка."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Тестов Тест')
        dlg.login.setText('test_login')
        dlg.password.setText('')
        dlg.save_employee()
        assert dlg.result() != QDialog.Accepted

    def test_short_password_rejected(self, qtbot, parent_widget):
        """Пароль < 4 символов — ошибка."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Тестов Тест')
        dlg.login.setText('test_login')
        dlg.password.setText('123')
        dlg.password_confirm.setText('123')
        dlg.save_employee()
        assert dlg.result() != QDialog.Accepted

    def test_password_mismatch_rejected(self, qtbot, parent_widget):
        """Пароли не совпадают — ошибка."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Тестов Тест')
        dlg.login.setText('test_login')
        dlg.password.setText('password1')
        dlg.password_confirm.setText('password2')
        dlg.save_employee()
        assert dlg.result() != QDialog.Accepted

    def test_valid_employee_accepted(self, qtbot, parent_widget):
        """Валидные данные — сохранение."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Новый Сотрудник')
        dlg.login.setText('new_emp')
        dlg.password.setText('test1234')
        dlg.password_confirm.setText('test1234')
        dlg.save_employee()
        assert dlg.result() == QDialog.Accepted

    def test_edit_empty_password_ok(self, qtbot, parent_widget, sample_employee):
        """Редактирование без пароля — допустимо (пароль не меняется)."""
        dlg = _create_employee_dialog(qtbot, parent_widget, employee_data=sample_employee)
        dlg.full_name.setText('Обновлённое ФИО')
        dlg.password.setText('')
        dlg.password_confirm.setText('')
        dlg.save_employee()
        assert dlg.result() == QDialog.Accepted

    def test_view_only_no_save(self, qtbot, parent_widget, sample_employee):
        """В режиме просмотра нет кнопки сохранить."""
        dlg = _create_employee_dialog(qtbot, parent_widget,
                                       employee_data=sample_employee, view_only=True)
        save_btns = [b for b in dlg.findChildren(QPushButton)
                     if 'сохранить' in b.text().lower()]
        assert len(save_btns) == 0


# ========== 4. CRUD операции (4 теста) ==========

@pytest.mark.ui
class TestEmployeeCRUD:
    """Создание, обновление сотрудников."""

    def test_create_calls_data(self, qtbot, parent_widget):
        """Создание вызывает create_employee."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Новый Сотрудник')
        dlg.login.setText('new_emp')
        dlg.password.setText('test1234')
        dlg.password_confirm.setText('test1234')
        dlg.save_employee()
        parent_widget.data.create_employee.assert_called()

    def test_update_calls_data(self, qtbot, parent_widget, sample_employee):
        """Обновление вызывает update_employee."""
        dlg = _create_employee_dialog(qtbot, parent_widget, employee_data=sample_employee)
        dlg.full_name.setText('Обновлённое ФИО')
        dlg.save_employee()
        parent_widget.data.update_employee.assert_called()

    def test_position_in_data(self, qtbot, parent_widget):
        """Должность передаётся в данных."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Тест Должность')
        dlg.login.setText('test_pos')
        dlg.password.setText('test1234')
        dlg.password_confirm.setText('test1234')
        dlg.position.setCurrentText('Дизайнер')
        dlg.save_employee()
        call_args = parent_widget.data.create_employee.call_args[0][0]
        assert call_args['position'] == 'Дизайнер'

    def test_department_auto_determined(self, qtbot, parent_widget):
        """Отдел определяется автоматически по должности."""
        dlg = _create_employee_dialog(qtbot, parent_widget)
        dlg.full_name.setText('Тест Отдел')
        dlg.login.setText('test_dept')
        dlg.password.setText('test1234')
        dlg.password_confirm.setText('test1234')
        dlg.position.setCurrentText('Дизайнер')
        dlg.save_employee()
        call_args = parent_widget.data.create_employee.call_args[0][0]
        assert call_args['department'] == 'Проектный отдел'


# ========== 5. Поиск (4 теста) ==========

@pytest.mark.ui
class TestEmployeeSearch:
    """Поиск сотрудников."""

    def test_search_dialog_creates(self, qtbot, mock_data_access, mock_employee_admin):
        """Диалог поиска создаётся."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_employee_search_dialog(tab)
        assert isinstance(dlg, QDialog)

    def test_search_has_name_input(self, qtbot, mock_data_access, mock_employee_admin):
        """Поле поиска по ФИО существует."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_employee_search_dialog(tab)
        assert hasattr(dlg, 'name_input')

    def test_search_has_position_combo(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр по должности существует."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_employee_search_dialog(tab)
        assert hasattr(dlg, 'position_combo')

    def test_search_has_status_combo(self, qtbot, mock_data_access, mock_employee_admin):
        """Фильтр по статусу существует."""
        tab = _create_employees_tab(qtbot, mock_data_access, mock_employee_admin)
        dlg = _create_employee_search_dialog(tab)
        assert hasattr(dlg, 'status_combo')
