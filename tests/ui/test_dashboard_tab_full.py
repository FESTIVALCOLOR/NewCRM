# -*- coding: utf-8 -*-
"""
Тесты для ui/dashboard_tab.py — DashboardTab.

Покрытие:
- calculate_api_statistics (бизнес-логика подсчёта)
- update_card_value (обновление UI)
- load_statistics (интеграция)
- lighter_color (утилита)
- create_stat_card (создание карточки)
"""
import pytest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture
def employee():
    return {
        'id': 1,
        'full_name': 'Иванов Иван',
        'position': 'Руководитель студии',
    }


@pytest.fixture
def mock_api_client():
    return MagicMock()


@pytest.fixture
def dashboard(qtbot, employee, mock_api_client):
    """Создаём DashboardTab с замоканным DataAccess."""
    with patch('ui.dashboard_tab.DatabaseManager'), \
         patch('ui.dashboard_tab.DataAccess') as MockDA, \
         patch('ui.dashboard_tab.resource_path', side_effect=lambda x: x), \
         patch('os.path.exists', return_value=False):

        mock_da = MockDA.return_value
        mock_da.is_multi_user = True
        mock_da.get_all_contracts.return_value = []
        mock_da.get_dashboard_statistics.return_value = {
            'individual_orders': 0, 'template_orders': 0, 'supervision_orders': 0,
            'individual_area': 0.0, 'template_area': 0.0, 'supervision_area': 0.0,
        }

        from ui.dashboard_tab import DashboardTab
        tab = DashboardTab(employee, api_client=mock_api_client)
        qtbot.addWidget(tab)
        return tab


# ==================== calculate_api_statistics ====================

class TestCalculateApiStatistics:
    """calculate_api_statistics — расчёт статистики из контрактов."""

    def test_empty_contracts(self, dashboard):
        """Пустой список контрактов — все нули."""
        dashboard.data_access.get_all_contracts.return_value = []
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 0
        assert stats['template_orders'] == 0
        assert stats['supervision_orders'] == 0
        assert stats['individual_area'] == 0.0
        assert stats['template_area'] == 0.0
        assert stats['supervision_area'] == 0.0

    def test_individual_counted(self, dashboard):
        """Индивидуальный контракт считается правильно."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Индивидуальный', 'area': 120, 'supervision': False},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 1
        assert stats['individual_area'] == 120.0
        assert stats['template_orders'] == 0

    def test_template_counted(self, dashboard):
        """Шаблонный контракт считается правильно."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Шаблонный', 'area': 90, 'supervision': False},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['template_orders'] == 1
        assert stats['template_area'] == 90.0

    def test_supervision_separate_count(self, dashboard):
        """Авторский надзор считается отдельно (supervision=True)."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Индивидуальный', 'area': 150, 'supervision': True},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 1
        assert stats['supervision_orders'] == 1
        assert stats['supervision_area'] == 150.0

    def test_mixed_contracts(self, dashboard):
        """Смешанные контракты — все типы подсчитаны."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Индивидуальный', 'area': 100, 'supervision': False},
            {'project_type': 'Индивидуальный', 'area': 200, 'supervision': True},
            {'project_type': 'Шаблонный', 'area': 90, 'supervision': False},
            {'project_type': 'Шаблонный', 'area': 140, 'supervision': True},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 2
        assert stats['individual_area'] == 300.0
        assert stats['template_orders'] == 2
        assert stats['template_area'] == 230.0
        assert stats['supervision_orders'] == 2
        assert stats['supervision_area'] == 340.0

    def test_null_area_handled(self, dashboard):
        """area=None — не вызывает ошибку, считается как 0."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Индивидуальный', 'area': None, 'supervision': False},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 1
        assert stats['individual_area'] == 0.0

    def test_string_area_handled(self, dashboard):
        """area строкой — конвертируется в float."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Шаблонный', 'area': '95.5', 'supervision': False},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['template_area'] == 95.5

    def test_unknown_project_type_ignored(self, dashboard):
        """Неизвестный project_type — не считается ни в один тип."""
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Неизвестный', 'area': 100, 'supervision': False},
        ]
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 0
        assert stats['template_orders'] == 0

    def test_exception_returns_zeros(self, dashboard):
        """Ошибка при расчёте — возвращает нулевую статистику."""
        dashboard.data_access.get_all_contracts.side_effect = Exception('DB error')
        stats = dashboard.calculate_api_statistics()
        assert stats['individual_orders'] == 0
        assert stats['supervision_area'] == 0.0


# ==================== update_card_value ====================

class TestUpdateCardValue:
    """update_card_value — обновление текста карточки."""

    def test_updates_existing_card(self, dashboard):
        """Обновляет значение существующей карточки."""
        dashboard.update_card_value('individual_orders', '42')
        from PyQt5.QtWidgets import QGroupBox, QLabel
        card = dashboard.findChild(QGroupBox, 'individual_orders')
        assert card is not None
        value_label = card.findChild(QLabel, 'value_label')
        assert value_label.text() == '42'

    def test_nonexistent_card_no_error(self, dashboard):
        """Несуществующая карточка — не падает."""
        dashboard.update_card_value('nonexistent_card', '99')

    def test_update_area_card(self, dashboard):
        """Обновление карточки площади."""
        dashboard.update_card_value('individual_area', '1,500 м²')
        from PyQt5.QtWidgets import QGroupBox, QLabel
        card = dashboard.findChild(QGroupBox, 'individual_area')
        value_label = card.findChild(QLabel, 'value_label')
        assert value_label.text() == '1,500 м²'


# ==================== lighter_color ====================

class TestLighterColor:
    """lighter_color — утилита цвета."""

    def test_returns_same_color(self, dashboard):
        """Возвращает тот же цвет (текущая реализация)."""
        assert dashboard.lighter_color('#fff4d9') == '#fff4d9'


# ==================== load_statistics ====================

class TestLoadStatistics:
    """load_statistics — интеграционная загрузка."""

    def test_multi_user_calls_api_statistics(self, dashboard):
        """В многопользовательском режиме вызывает calculate_api_statistics."""
        dashboard.data_access.is_multi_user = True
        dashboard.data_access.get_all_contracts.return_value = [
            {'project_type': 'Индивидуальный', 'area': 100, 'supervision': False},
        ]
        dashboard.load_statistics()
        from PyQt5.QtWidgets import QGroupBox, QLabel
        card = dashboard.findChild(QGroupBox, 'individual_orders')
        value_label = card.findChild(QLabel, 'value_label')
        assert value_label.text() == '1'

    def test_local_mode_calls_dashboard_statistics(self, dashboard):
        """В локальном режиме вызывает get_dashboard_statistics."""
        dashboard.data_access.is_multi_user = False
        dashboard.data_access.get_dashboard_statistics.return_value = {
            'individual_orders': 5, 'template_orders': 3, 'supervision_orders': 1,
            'individual_area': 500.0, 'template_area': 300.0, 'supervision_area': 100.0,
        }
        dashboard.load_statistics()
        dashboard.data_access.get_dashboard_statistics.assert_called()

    def test_exception_does_not_crash(self, dashboard):
        """Ошибка при загрузке — не падает."""
        dashboard.data_access.is_multi_user = True
        dashboard.data_access.get_all_contracts.side_effect = Exception('Connection error')
        dashboard.data_access.get_dashboard_statistics.side_effect = Exception('DB error')
        dashboard.load_statistics()  # Не должно упасть


# ==================== create_stat_card ====================

class TestCreateStatCard:
    """create_stat_card — создание карточки."""

    def test_card_is_groupbox(self, dashboard):
        """Карточка — QGroupBox."""
        from PyQt5.QtWidgets import QGroupBox
        card = dashboard.create_stat_card('test', 'Тест', '0', 'icon.svg', '#fff', '#000')
        assert isinstance(card, QGroupBox)

    def test_card_has_object_name(self, dashboard):
        card = dashboard.create_stat_card('my_card', 'Заголовок', '99', 'icon.svg', '#fff', '#000')
        assert card.objectName() == 'my_card'

    def test_card_has_value_label(self, dashboard):
        from PyQt5.QtWidgets import QLabel
        card = dashboard.create_stat_card('card1', 'Заголовок', '42', 'icon.svg', '#eee', '#333')
        value_label = card.findChild(QLabel, 'value_label')
        assert value_label is not None
        assert value_label.text() == '42'
