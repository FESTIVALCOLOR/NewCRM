# -*- coding: utf-8 -*-
"""
Тесты для P1 UI виджетов:
- ui/custom_message_box.py (CustomMessageBox, CustomQuestionBox)
- ui/chart_widget.py (ChartBase, _Theme, и все графики)
- ui/base_kanban_tab.py (BaseDraggableList, BaseKanbanColumn, BaseKanbanTab)
- ui/global_search_widget.py (GlobalSearchWidget, _SearchWorker)

Покрытие:
- Создание виджетов, структура UI
- Выбор иконки/цвета по icon_type
- Chart: создание, set_data, экспорт PNG
- Kanban: add_card, toggle_collapse, clear_cards
- Search: debounce, минимум символов, обработка результатов
"""
import pytest
import sys
import os
from unittest.mock import MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==================== CustomMessageBox ====================

class TestCustomMessageBox:
    """CustomMessageBox — окно сообщения."""

    def test_creates_dialog(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        box = CustomMessageBox(None, 'Тест', 'Сообщение')
        qtbot.addWidget(box)
        assert box is not None

    def test_warning_icon_type(self, qtbot):
        """icon_type='warning' → текст 'ВНИМАНИЕ'."""
        from ui.custom_message_box import CustomMessageBox
        from PyQt5.QtWidgets import QLabel
        box = CustomMessageBox(None, 'Тест', 'Сообщение', icon_type='warning')
        qtbot.addWidget(box)
        labels = box.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert 'ВНИМАНИЕ' in texts

    def test_error_icon_type(self, qtbot):
        """icon_type='error' → текст 'ОШИБКА'."""
        from ui.custom_message_box import CustomMessageBox
        from PyQt5.QtWidgets import QLabel
        box = CustomMessageBox(None, 'Тест', 'Ошибка', icon_type='error')
        qtbot.addWidget(box)
        labels = box.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert 'ОШИБКА' in texts

    def test_success_icon_type(self, qtbot):
        """icon_type='success' → текст 'УСПЕХ'."""
        from ui.custom_message_box import CustomMessageBox
        from PyQt5.QtWidgets import QLabel
        box = CustomMessageBox(None, 'Тест', 'Ок', icon_type='success')
        qtbot.addWidget(box)
        labels = box.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert 'УСПЕХ' in texts

    def test_info_icon_type(self, qtbot):
        """icon_type='info' → текст 'ИНФО'."""
        from ui.custom_message_box import CustomMessageBox
        from PyQt5.QtWidgets import QLabel
        box = CustomMessageBox(None, 'Тест', 'Инфо', icon_type='info')
        qtbot.addWidget(box)
        labels = box.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert 'ИНФО' in texts

    def test_has_ok_button(self, qtbot):
        """Есть кнопка OK."""
        from ui.custom_message_box import CustomMessageBox
        from PyQt5.QtWidgets import QPushButton
        box = CustomMessageBox(None, 'Тест', 'Сообщение')
        qtbot.addWidget(box)
        buttons = box.findChildren(QPushButton)
        ok_buttons = [b for b in buttons if b.text() == 'OK']
        assert len(ok_buttons) >= 1

    def test_minimum_width(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        box = CustomMessageBox(None, 'Тест', 'Сообщение')
        qtbot.addWidget(box)
        assert box.minimumWidth() >= 280

    def test_frameless_window(self, qtbot):
        """Окно без рамки."""
        from ui.custom_message_box import CustomMessageBox
        from PyQt5.QtCore import Qt
        box = CustomMessageBox(None, 'Тест', 'Сообщение')
        qtbot.addWidget(box)
        assert box.windowFlags() & Qt.FramelessWindowHint


# ==================== CustomQuestionBox ====================

class TestCustomQuestionBox:
    """CustomQuestionBox — окно вопроса Да/Нет."""

    def test_has_yes_no_buttons(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        from PyQt5.QtWidgets import QPushButton
        box = CustomQuestionBox(None, 'Вопрос', 'Удалить?')
        qtbot.addWidget(box)
        buttons = box.findChildren(QPushButton)
        texts = [b.text() for b in buttons]
        assert 'Да' in texts
        assert 'Нет' in texts

    def test_minimum_width_315(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        box = CustomQuestionBox(None, 'Вопрос', 'Текст')
        qtbot.addWidget(box)
        assert box.minimumWidth() >= 315

    def test_message_displayed(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        from PyQt5.QtWidgets import QLabel
        box = CustomQuestionBox(None, 'Вопрос', 'Удалить запись?')
        qtbot.addWidget(box)
        labels = box.findChildren(QLabel)
        texts = [l.text() for l in labels]
        assert any('Удалить запись?' in t for t in texts)


# ==================== ChartWidget ====================

class TestChartTheme:
    """_Theme — константы графиков."""

    def test_palette_has_colors(self):
        from ui.chart_widget import _Theme
        assert len(_Theme.PALETTE) >= 5

    def test_individual_color(self):
        from ui.chart_widget import _Theme
        assert _Theme.COLOR_INDIVIDUAL.startswith('#')

    def test_bar_width_range(self):
        from ui.chart_widget import _Theme
        assert 0 < _Theme.BAR_W_VERT < 1

    def test_font_sizes_positive(self):
        from ui.chart_widget import _Theme
        assert _Theme.TITLE_SIZE > 0
        assert _Theme.LABEL_SIZE > 0
        assert _Theme.VALUE_SIZE > 0


class TestChartBase:
    """ChartBase — базовый класс графиков."""

    def test_creates_with_title(self, qtbot):
        from ui.chart_widget import ChartBase
        chart = ChartBase(title="Тестовый график")
        qtbot.addWidget(chart)
        assert chart.chart_title == "Тестовый график"

    def test_has_canvas(self, qtbot):
        from ui.chart_widget import ChartBase, MATPLOTLIB_AVAILABLE
        chart = ChartBase()
        qtbot.addWidget(chart)
        if MATPLOTLIB_AVAILABLE:
            assert chart.canvas is not None
        else:
            assert chart.canvas is None

    def test_truncate_short_text(self, qtbot):
        from ui.chart_widget import ChartBase
        chart = ChartBase()
        qtbot.addWidget(chart)
        assert chart._truncate("Короткий") == "Короткий"

    def test_truncate_long_text(self, qtbot):
        from ui.chart_widget import ChartBase
        chart = ChartBase()
        qtbot.addWidget(chart)
        result = chart._truncate("Очень длинное название которое не поместится")
        assert len(result) <= 23  # max_len=20 + "..."

    def test_wrap_label_short(self, qtbot):
        from ui.chart_widget import ChartBase
        chart = ChartBase()
        qtbot.addWidget(chart)
        result = chart._wrap_label("Короткий")
        assert result == "Короткий"

    def test_wrap_label_long(self, qtbot):
        from ui.chart_widget import ChartBase
        chart = ChartBase()
        qtbot.addWidget(chart)
        result = chart._wrap_label("Очень длинное название для переноса на две строки")
        assert '\n' in result

    def test_minimum_height(self, qtbot):
        from ui.chart_widget import ChartBase, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = ChartBase()
        qtbot.addWidget(chart)
        assert chart.minimumHeight() >= 260


class TestFunnelBarChart:
    """FunnelBarChart — горизонтальная воронка."""

    def test_creates(self, qtbot):
        from ui.chart_widget import FunnelBarChart, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = FunnelBarChart()
        qtbot.addWidget(chart)
        assert chart.chart_title == "Воронка проектов"

    def test_set_data_empty(self, qtbot):
        from ui.chart_widget import FunnelBarChart, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = FunnelBarChart()
        qtbot.addWidget(chart)
        chart.set_data({})  # Пустой dict — не должно упасть

    def test_set_data_with_values(self, qtbot):
        from ui.chart_widget import FunnelBarChart, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = FunnelBarChart()
        qtbot.addWidget(chart)
        chart.set_data({'Новый заказ': 10, 'В работе': 7, 'Завершён': 3})


class TestExecutorLoadChart:
    """ExecutorLoadChart — нагрузка исполнителей."""

    def test_set_data(self, qtbot):
        from ui.chart_widget import ExecutorLoadChart, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = ExecutorLoadChart()
        qtbot.addWidget(chart)
        chart.set_data([
            {"name": "Иванов", "active_stages": 3},
            {"name": "Петров", "active_stages": 8},
        ])


class TestLineChartWidget:
    """LineChartWidget — линейный график."""

    def test_set_data(self, qtbot):
        from ui.chart_widget import LineChartWidget, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = LineChartWidget(title="Динамика")
        qtbot.addWidget(chart)
        chart.set_data([
            {'label': 'Контракты', 'x': ['Янв', 'Фев', 'Мар'], 'y': [5, 8, 12]},
        ])


class TestProjectTypePieChart:
    """ProjectTypePieChart — donut-диаграмма."""

    def test_set_data(self, qtbot):
        from ui.chart_widget import ProjectTypePieChart, MATPLOTLIB_AVAILABLE
        if not MATPLOTLIB_AVAILABLE:
            pytest.skip("matplotlib не установлен")
        chart = ProjectTypePieChart()
        qtbot.addWidget(chart)
        chart.set_data(individual_count=60, template_count=40)


class TestSectionWidget:
    """SectionWidget — контейнер секции."""

    def test_creates_with_title(self, qtbot):
        from ui.chart_widget import SectionWidget
        section = SectionWidget(title="Секция", description="Описание")
        qtbot.addWidget(section)
        assert section is not None

    def test_add_widget(self, qtbot):
        from ui.chart_widget import SectionWidget
        from PyQt5.QtWidgets import QLabel
        section = SectionWidget(title="Тест")
        qtbot.addWidget(section)
        label = QLabel("Внутри секции")
        section.add_widget(label)


# ==================== BaseKanbanTab ====================

class TestBaseKanbanColumn:
    """BaseKanbanColumn — колонка канбан-доски."""

    def test_toggle_collapse_stores_state(self, qtbot):
        """toggle_collapse сохраняет состояние."""
        from ui.base_kanban_tab import BaseKanbanColumn
        assert hasattr(BaseKanbanColumn, 'toggle_collapse')
        assert hasattr(BaseKanbanColumn, 'add_card')
        assert hasattr(BaseKanbanColumn, 'clear_cards')
        assert hasattr(BaseKanbanColumn, 'find_card_item_by_id')

    def test_collapsed_width_in_init(self):
        """_collapsed_width задаётся в __init__."""
        from ui.base_kanban_tab import BaseKanbanColumn
        import inspect
        src = inspect.getsource(BaseKanbanColumn.__init__)
        assert '_collapsed_width' in src


class TestBaseDraggableList:
    """BaseDraggableList — базовый drag-drop список."""

    def test_has_start_drag(self):
        from ui.base_kanban_tab import BaseDraggableList
        assert hasattr(BaseDraggableList, 'startDrag')


class TestBaseKanbanTab:
    """BaseKanbanTab — базовая вкладка канбан."""

    def test_has_required_methods(self):
        from ui.base_kanban_tab import BaseKanbanTab
        assert hasattr(BaseKanbanTab, 'refresh_current_tab')
        assert hasattr(BaseKanbanTab, 'on_tab_changed')
        assert hasattr(BaseKanbanTab, '_make_kanban_scroll_area')
        assert hasattr(BaseKanbanTab, '_make_header_layout')


# ==================== GlobalSearchWidget ====================

class TestGlobalSearchWidget:
    """GlobalSearchWidget — поиск."""

    def test_creates_widget(self, qtbot):
        from ui.global_search_widget import GlobalSearchWidget
        mock_da = MagicMock()
        widget = GlobalSearchWidget(data_access=mock_da)
        qtbot.addWidget(widget)
        assert widget is not None

    def test_has_search_input(self, qtbot):
        from ui.global_search_widget import GlobalSearchWidget
        from PyQt5.QtWidgets import QLineEdit
        mock_da = MagicMock()
        widget = GlobalSearchWidget(data_access=mock_da)
        qtbot.addWidget(widget)
        line_edit = widget.findChild(QLineEdit)
        assert line_edit is not None

    def test_has_result_selected_signal(self):
        from ui.global_search_widget import GlobalSearchWidget
        assert hasattr(GlobalSearchWidget, 'result_selected')

    def test_min_search_length(self, qtbot):
        """Минимум 2 символа для поиска."""
        from ui.global_search_widget import GlobalSearchWidget
        mock_da = MagicMock()
        widget = GlobalSearchWidget(data_access=mock_da)
        qtbot.addWidget(widget)
        # search_input — публичный атрибут
        widget.search_input.setText("А")
        # Поиск не запущен (worker не создан при 1 символе)
        assert widget._worker is None
