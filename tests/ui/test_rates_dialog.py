# -*- coding: utf-8 -*-
"""
Тесты диалога тарифов — RatesDialog.
4 вкладки: Индивидуальные, Шаблонные, Авторский надзор, Замерщик.
~10 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QWidget, QTabWidget,
    QTableWidget, QDoubleSpinBox,
)
from PyQt5.QtCore import Qt


# ========== Авто-мок QMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_rates_msgbox():
    with patch('ui.rates_dialog.QMessageBox', MagicMock()):
        yield


# ========== Хелперы ==========

def _make_parent(qtbot, mock_data_access, employee):
    w = QWidget()
    w.data = mock_data_access
    w.employee = employee
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


@pytest.fixture
def rates_dlg(qtbot, mock_data_access, mock_employee_admin):
    """Создать RatesDialog с моками. Патчи активны на время теста."""
    parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
    mock_data_access.get_rates.return_value = []
    mock_data_access.get_all_cities.return_value = [
        {'name': 'СПБ'}, {'name': 'МСК'}, {'name': 'ВН'}
    ]
    mock_data_access.save_rate.return_value = True
    mock_data_access.get_rates_for_role.return_value = []
    mock_data_access.db.connect.return_value = MagicMock()
    cursor_mock = MagicMock()
    cursor_mock.fetchone.return_value = None
    cursor_mock.fetchall.return_value = []
    mock_data_access.db.connect.return_value.cursor.return_value = cursor_mock
    mock_data_access.db.close.return_value = None

    with patch('ui.rates_dialog.DataAccess') as MockDA, \
         patch('ui.rates_dialog.DatabaseManager', return_value=mock_data_access.db), \
         patch('ui.rates_dialog.apply_no_focus_delegate', lambda t: None):
        MockDA.return_value = mock_data_access
        from ui.rates_dialog import RatesDialog
        d = RatesDialog(parent, api_client=None)
        d.setAttribute(Qt.WA_DeleteOnClose, False)
        d._test_parent = parent  # prevent GC
        qtbot.addWidget(d)
        yield d


# ========================================================================
# Тесты
# ========================================================================

@pytest.mark.ui
class TestRatesDialogInit:
    """Инициализация диалога тарифов."""

    def test_creates_as_dialog(self, rates_dlg):
        """Диалог создаётся."""
        assert isinstance(rates_dlg, QDialog)

    def test_has_tab_widget(self, rates_dlg):
        """QTabWidget с 4 вкладками."""
        tabs = rates_dlg.findChildren(QTabWidget)
        assert len(tabs) >= 1
        # 4 вкладки: Индивидуальные, Шаблонные, АН, Замерщик
        assert tabs[0].count() == 4


@pytest.mark.ui
class TestRatesDialogIndividual:
    """Вкладка «Индивидуальные тарифы»."""

    def test_individual_table_exists(self, rates_dlg):
        """Таблица индивидуальных тарифов существует."""
        table = rates_dlg.findChild(QTableWidget, 'individual_rates_table')
        assert table is not None

    def test_individual_table_has_rows(self, rates_dlg):
        """Таблица содержит строки (роли/стадии)."""
        table = rates_dlg.findChild(QTableWidget, 'individual_rates_table')
        assert table.rowCount() >= 5  # Дизайнер, 2 Чертёжника, СДП, ГАП, СМП, Менеджер

    def test_individual_table_has_spinboxes(self, rates_dlg):
        """Ячейки содержат QDoubleSpinBox для цен."""
        table = rates_dlg.findChild(QTableWidget, 'individual_rates_table')
        spin = table.cellWidget(0, 2)
        assert isinstance(spin, QDoubleSpinBox)

    def test_spinbox_min_zero(self, rates_dlg):
        """Цена >= 0."""
        table = rates_dlg.findChild(QTableWidget, 'individual_rates_table')
        spin = table.cellWidget(0, 2)
        assert spin.minimum() == 0


@pytest.mark.ui
class TestRatesDialogSupervision:
    """Вкладка «Авторский надзор»."""

    def test_supervision_table_exists(self, rates_dlg):
        """Таблица тарифов АН существует."""
        table = rates_dlg.findChild(QTableWidget, 'supervision_rates_table')
        assert table is not None

    def test_supervision_table_12_stages(self, rates_dlg):
        """12 стадий АН."""
        table = rates_dlg.findChild(QTableWidget, 'supervision_rates_table')
        assert table.rowCount() == 12


@pytest.mark.ui
class TestRatesDialogSurveyor:
    """Вкладка «Замерщик»."""

    def test_surveyor_table_exists(self, rates_dlg):
        """Таблица тарифов замерщика существует."""
        table = rates_dlg.findChild(QTableWidget, 'surveyor_rates_table')
        assert table is not None

    def test_surveyor_table_city_count(self, rates_dlg):
        """Количество строк соответствует числу городов."""
        table = rates_dlg.findChild(QTableWidget, 'surveyor_rates_table')
        # Мы замокали 3 города
        assert table.rowCount() >= 3
