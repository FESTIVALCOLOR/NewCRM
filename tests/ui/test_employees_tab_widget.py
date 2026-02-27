# -*- coding: utf-8 -*-
"""
Тесты для EmployeesTab — вкладка управления сотрудниками.

Проверяется создание виджета, наличие элементов UI (таблица, кнопки, фильтры),
заполнение таблицы данными, фильтрация по отделу, права доступа.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import (QApplication, QTableWidget, QPushButton,
                              QLabel, QHeaderView)
from PyQt5.QtCore import Qt
from unittest.mock import patch, MagicMock


# ========== Вспомогательные функции ==========

def _make_mock_data_access(employees=None):
    """Создать MagicMock DataAccess для EmployeesTab."""
    mock_da = MagicMock()
    mock_da.get_all_employees.return_value = employees or []
    mock_da.get_all_clients.return_value = []
    mock_da.get_all_contracts.return_value = []
    mock_da.db = MagicMock()
    mock_da.is_online = False
    return mock_da


def _create_employees_tab(qtbot, employee, employees_data=None):
    """Создать EmployeesTab с замоканными зависимостями."""
    mock_da = _make_mock_data_access(employees=employees_data)
    with patch('ui.employees_tab.DataAccess', return_value=mock_da), \
         patch('ui.employees_tab.IconLoader') as mock_icon:
        mock_icon.load.return_value = MagicMock()
        mock_icon.create_action_button.return_value = QPushButton()
        mock_icon.create_icon_button.return_value = QPushButton()
        from ui.employees_tab import EmployeesTab
        tab = EmployeesTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab, mock_da


# ========== Тестовые данные ==========

SAMPLE_EMPLOYEES = [
    {
        'id': 1, 'full_name': 'Иванов Иван Иванович',
        'position': 'Руководитель студии', 'secondary_position': '',
        'phone': '+7 (999) 111-11-11', 'email': 'ivanov@test.ru',
        'birth_date': '1990-05-15', 'status': 'активный',
        'department': 'Административный отдел'
    },
    {
        'id': 2, 'full_name': 'Петров Пётр Петрович',
        'position': 'Дизайнер', 'secondary_position': 'Менеджер',
        'phone': '+7 (999) 222-22-22', 'email': 'petrov@test.ru',
        'birth_date': '1985-10-20', 'status': 'активный',
        'department': 'Проектный отдел'
    },
    {
        'id': 3, 'full_name': 'Сидоров Сергей Сергеевич',
        'position': 'Менеджер', 'secondary_position': '',
        'phone': '+7 (999) 333-33-33', 'email': 'sidorov@test.ru',
        'birth_date': '', 'status': 'уволен',
        'department': 'Исполнительный отдел'
    },
    {
        'id': 4, 'full_name': 'Козлов Алексей Александрович',
        'position': 'Чертёжник', 'secondary_position': '',
        'phone': '+7 (999) 444-44-44', 'email': 'kozlov@test.ru',
        'birth_date': '1995-03-12', 'status': 'активный',
        'department': 'Проектный отдел'
    },
    {
        'id': 5, 'full_name': 'Волкова Мария Андреевна',
        'position': 'ГАП', 'secondary_position': '',
        'phone': '+7 (999) 555-55-55', 'email': 'volkova@test.ru',
        'birth_date': '1988-12-01', 'status': 'активный',
        'department': 'Административный отдел'
    },
]


class TestEmployeesTabCreation:
    """Тесты создания и инициализации EmployeesTab."""

    def test_create_widget(self, qtbot, mock_employee_admin):
        """EmployeesTab создаётся без ошибок."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab is not None

    def test_widget_is_visible(self, qtbot, mock_employee_admin):
        """EmployeesTab видим после show()."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        tab.show()
        assert tab.isVisible()

    def test_employee_stored(self, qtbot, mock_employee_admin):
        """Атрибут employee сохраняет данные текущего пользователя."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.employee == mock_employee_admin

    def test_data_access_initialized(self, qtbot, mock_employee_admin):
        """DataAccess инициализирован."""
        tab, mock_da = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.data is mock_da


class TestEmployeesTabPermissions:
    """Тесты прав доступа в зависимости от роли."""

    def test_admin_can_edit(self, qtbot, mock_employee_admin):
        """Руководитель студии имеет право редактирования."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.can_edit is True

    def test_admin_can_delete(self, qtbot, mock_employee_admin):
        """Руководитель студии имеет право удаления."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.can_delete is True

    def test_designer_cannot_edit(self, qtbot, mock_employee_designer):
        """Дизайнер не имеет права редактирования."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_designer)
        assert tab.can_edit is False

    def test_designer_cannot_delete(self, qtbot, mock_employee_designer):
        """Дизайнер не имеет права удаления."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_designer)
        assert tab.can_delete is False

    def test_senior_manager_can_edit(self, qtbot, mock_employee_senior_manager):
        """Старший менеджер имеет право редактирования."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_senior_manager)
        assert tab.can_edit is True

    def test_senior_manager_cannot_delete(self, qtbot, mock_employee_senior_manager):
        """Старший менеджер НЕ имеет права удаления (только Руководитель)."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_senior_manager)
        assert tab.can_delete is False


class TestEmployeesTabTable:
    """Тесты таблицы сотрудников."""

    def test_has_employees_table(self, qtbot, mock_employee_admin):
        """Наличие таблицы сотрудников."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'employees_table')

    def test_table_column_count(self, qtbot, mock_employee_admin):
        """Таблица имеет 8 столбцов (включая скрытый ID)."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.employees_table.columnCount() == 8

    def test_table_headers(self, qtbot, mock_employee_admin):
        """Проверка заголовков столбцов таблицы."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        expected_headers = [
            'ID', 'ФИО', 'Должность', 'Телефон', 'Email',
            'Дата рождения', 'Статус', 'Действия'
        ]
        for i, header_text in enumerate(expected_headers):
            item = tab.employees_table.horizontalHeaderItem(i)
            assert item is not None, f"Столбец {i} не имеет заголовка"
            # Заголовки могут содержать пробелы по краям
            assert header_text in item.text().strip(), \
                f"Столбец {i}: ожидалось '{header_text}', получено '{item.text().strip()}'"

    def test_id_column_hidden(self, qtbot, mock_employee_admin):
        """Столбец ID скрыт."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.employees_table.isColumnHidden(0) is True

    def test_empty_table_on_empty_data(self, qtbot, mock_employee_admin):
        """При пустом списке сотрудников таблица имеет 0 строк."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=[])
        assert tab.employees_table.rowCount() == 0

    def test_table_populated_with_data(self, qtbot, mock_employee_admin):
        """Таблица заполняется данными сотрудников."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        assert tab.employees_table.rowCount() == len(SAMPLE_EMPLOYEES)

    def test_employee_name_in_table(self, qtbot, mock_employee_admin):
        """ФИО сотрудника отображается в таблице."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        # Столбец 1 — ФИО
        item = tab.employees_table.item(0, 1)
        assert item is not None
        assert item.text() == 'Иванов Иван Иванович'

    def test_secondary_position_displayed(self, qtbot, mock_employee_admin):
        """Двойная должность отображается через слэш."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        # Столбец 2 — Должность; Петров (index 1) имеет двойную должность
        item = tab.employees_table.item(1, 2)
        assert item is not None
        assert 'Дизайнер/Менеджер' == item.text()

    def test_sorting_enabled(self, qtbot, mock_employee_admin):
        """Сортировка включена."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.employees_table.isSortingEnabled() is True

    def test_no_edit_triggers(self, qtbot, mock_employee_admin):
        """Редактирование ячеек отключено."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.employees_table.editTriggers() == QTableWidget.NoEditTriggers


class TestEmployeesTabFilters:
    """Тесты кнопок-фильтров по отделам."""

    def test_has_filter_buttons(self, qtbot, mock_employee_admin):
        """Наличие словаря кнопок-фильтров."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert hasattr(tab, 'filter_buttons')
        assert isinstance(tab.filter_buttons, dict)

    def test_four_filter_buttons(self, qtbot, mock_employee_admin):
        """Должно быть 4 кнопки-фильтра: all, admin, project, executive."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        expected_keys = {'all', 'admin', 'project', 'executive'}
        assert set(tab.filter_buttons.keys()) == expected_keys

    def test_default_filter_is_all(self, qtbot, mock_employee_admin):
        """По умолчанию кнопка 'Все отделы' нажата."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.filter_buttons['all'].isChecked() is True

    def test_filter_button_text(self, qtbot, mock_employee_admin):
        """Проверка текста кнопок-фильтров."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        assert tab.filter_buttons['all'].text() == 'Все отделы'
        assert tab.filter_buttons['admin'].text() == 'Административный отдел'
        assert tab.filter_buttons['project'].text() == 'Проектный отдел'
        assert tab.filter_buttons['executive'].text() == 'Исполнительный отдел'

    def test_filter_admin_department(self, qtbot, mock_employee_admin):
        """Фильтр 'Административный отдел' показывает только администрацию."""
        tab, mock_da = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        # Переключаем фильтр на 'admin'
        tab.on_filter_changed('admin')
        # После фильтрации должны остаться: Руководитель студии (Иванов) + ГАП (Волкова)
        assert tab.employees_table.rowCount() == 2

    def test_filter_project_department(self, qtbot, mock_employee_admin):
        """Фильтр 'Проектный отдел' показывает только дизайнеров и чертёжников."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        tab.on_filter_changed('project')
        # Дизайнер (Петров) + Чертёжник (Козлов)
        assert tab.employees_table.rowCount() == 2

    def test_filter_executive_department(self, qtbot, mock_employee_admin):
        """Фильтр 'Исполнительный отдел' показывает менеджеров, ДАН, замерщиков."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        tab.on_filter_changed('executive')
        # Менеджер (Сидоров)
        assert tab.employees_table.rowCount() == 1

    def test_filter_all_resets(self, qtbot, mock_employee_admin):
        """Фильтр 'Все отделы' показывает всех."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin, employees_data=SAMPLE_EMPLOYEES)
        tab.on_filter_changed('admin')
        tab.on_filter_changed('all')
        assert tab.employees_table.rowCount() == len(SAMPLE_EMPLOYEES)

    def test_filter_button_checked_state(self, qtbot, mock_employee_admin):
        """При выборе фильтра соответствующая кнопка становится нажатой."""
        tab, _ = _create_employees_tab(qtbot, mock_employee_admin)
        tab.on_filter_changed('project')
        assert tab.filter_buttons['project'].isChecked() is True
        assert tab.filter_buttons['all'].isChecked() is False
