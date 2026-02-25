# -*- coding: utf-8 -*-
"""
Тесты для AgentsCitiesWidget — виджет управления агентами и городами.
"""
import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import QApplication, QTableWidget, QPushButton, QLabel
from unittest.mock import patch, MagicMock


@pytest.fixture(scope="module")
def qapp():
    """QApplication для модуля тестов."""
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance() or QApplication(sys.argv)
    yield app


def _make_mock_data_access(agents=None, cities=None):
    """Создать MagicMock DataAccess с готовыми данными агентов и городов."""
    mock_da = MagicMock()
    mock_da.get_all_agents.return_value = agents or []
    mock_da.get_all_cities.return_value = cities or []
    return mock_da


class TestAgentsCitiesWidget:

    def test_create_widget(self, qapp):
        """Виджет AgentsCitiesWidget создаётся без ошибок."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access()
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget is not None
            widget.close()

    def test_widget_has_two_tables(self, qapp):
        """Виджет содержит две таблицы: агентов и городов."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access()
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert hasattr(widget, '_agents_table')
            assert hasattr(widget, '_cities_table')
            assert isinstance(widget._agents_table, QTableWidget)
            assert isinstance(widget._cities_table, QTableWidget)
            widget.close()

    def test_agents_table_columns(self, qapp):
        """Таблица агентов имеет 4 столбца: Название, Цвет, Статус, действие."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access()
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget._agents_table.columnCount() == 4
            widget.close()

    def test_cities_table_columns(self, qapp):
        """Таблица городов имеет 3 столбца: Название, Статус, действие."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access()
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget._cities_table.columnCount() == 3
            widget.close()

    def test_load_agents_populates_table(self, qapp):
        """_load_agents заполняет таблицу агентов из данных DataAccess."""
        agents_data = [
            {'id': 1, 'name': 'ПЕТРОВИЧ', 'color': '#FF0000', 'status': 'активный'},
            {'id': 2, 'name': 'РОМАШКА', 'color': '#00FF00', 'status': 'активный'},
        ]
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access(agents=agents_data)
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget._agents_table.rowCount() == 2
            assert widget._agents_table.item(0, 0).text() == 'ПЕТРОВИЧ'
            assert widget._agents_table.item(1, 0).text() == 'РОМАШКА'
            widget.close()

    def test_load_cities_populates_table(self, qapp):
        """_load_cities заполняет таблицу городов из данных DataAccess."""
        cities_data = [
            {'id': 1, 'name': 'НСК', 'status': 'активный'},
            {'id': 2, 'name': 'МСК', 'status': 'активный'},
            {'id': 3, 'name': 'СПБ', 'status': 'активный'},
        ]
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access(cities=cities_data)
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget._cities_table.rowCount() == 3
            assert widget._cities_table.item(0, 0).text() == 'НСК'
            widget.close()

    def test_empty_agents_table(self, qapp):
        """При пустом списке агентов таблица имеет 0 строк."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access(agents=[])
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget._agents_table.rowCount() == 0
            widget.close()

    def test_empty_cities_table(self, qapp):
        """При пустом списке городов таблица имеет 0 строк."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access(cities=[])
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            assert widget._cities_table.rowCount() == 0
            widget.close()

    def test_widget_has_add_buttons(self, qapp):
        """Виджет содержит кнопки 'Добавить' для агентов и городов."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access()
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            buttons = widget.findChildren(QPushButton)
            btn_texts = [b.text() for b in buttons]
            # Должно быть как минимум 2 кнопки "Добавить"
            assert btn_texts.count('Добавить') >= 2
            widget.close()

    def test_data_access_initialized(self, qapp):
        """Атрибут data инициализируется из переданного data_access."""
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access()
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            # data должен быть установлен
            assert widget.data is mock_da
            widget.close()

    def test_agent_status_in_table(self, qapp):
        """Статус агента отображается в таблице."""
        agents_data = [
            {'id': 1, 'name': 'ТЕСТ', 'color': '#FFFFFF', 'status': 'активный'},
        ]
        with patch('ui.agents_cities_widget.DataAccess', return_value=_make_mock_data_access()), \
             patch('ui.agents_cities_widget.IconLoader'):
            from ui.agents_cities_widget import AgentsCitiesWidget
            mock_da = _make_mock_data_access(agents=agents_data)
            widget = AgentsCitiesWidget(parent=None, data_access=mock_da)
            # Столбец 2 — статус
            item = widget._agents_table.item(0, 2)
            assert item is not None
            assert item.text() == 'активный'
            widget.close()
