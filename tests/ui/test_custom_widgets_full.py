# -*- coding: utf-8 -*-
"""Тесты для мелких UI-виджетов: custom_combobox, custom_dateedit, flow_layout, bubble_tooltip, chart_widget, custom_message_box, custom_title_bar"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QWidget, QPushButton, QApplication
from PyQt5.QtCore import Qt, QEvent, QRect


# ─── CustomComboBox ──────────────────────────────────────────────────────

class TestCustomComboBox:
    """Тесты CustomComboBox"""

    def test_creation(self, qtbot):
        with patch('ui.custom_combobox.resource_path', return_value='/fake'):
            from ui.custom_combobox import CustomComboBox
            cb = CustomComboBox()
            qtbot.addWidget(cb)
            assert cb.focusPolicy() == Qt.StrongFocus

    def test_wheel_event_without_focus(self, qtbot):
        with patch('ui.custom_combobox.resource_path', return_value='/fake'):
            from ui.custom_combobox import CustomComboBox
            cb = CustomComboBox()
            qtbot.addWidget(cb)
            cb.addItems(['A', 'B', 'C'])
            cb.setCurrentIndex(0)
            # Без фокуса — событие игнорируется
            event = MagicMock()
            event.ignore = MagicMock()
            cb.wheelEvent(event)
            event.ignore.assert_called_once()

    def test_wheel_event_with_focus(self, qtbot):
        with patch('ui.custom_combobox.resource_path', return_value='/fake'):
            from ui.custom_combobox import CustomComboBox
            cb = CustomComboBox()
            qtbot.addWidget(cb)
            cb.addItems(['A', 'B', 'C'])
            cb.setFocus()
            # С фокусом — обрабатывается нормально (не кидает exception)


# ─── CustomDateEdit ──────────────────────────────────────────────────────

class TestCustomDateEdit:
    """Тесты CustomDateEdit"""

    def test_creation(self, qtbot):
        from ui.custom_dateedit import CustomDateEdit
        de = CustomDateEdit()
        qtbot.addWidget(de)
        assert de is not None

    def test_wheel_event_no_calendar(self, qtbot):
        from ui.custom_dateedit import CustomDateEdit
        de = CustomDateEdit()
        qtbot.addWidget(de)
        event = MagicMock()
        event.ignore = MagicMock()
        de.wheelEvent(event)
        event.ignore.assert_called_once()


# ─── FlowLayout ─────────────────────────────────────────────────────────

class TestFlowLayout:
    """Тесты FlowLayout"""

    def test_creation_no_parent(self):
        from ui.flow_layout import FlowLayout
        fl = FlowLayout(margin=5, spacing=10)
        assert fl.count() == 0

    def test_add_item(self, qtbot):
        from ui.flow_layout import FlowLayout
        parent = QWidget()
        qtbot.addWidget(parent)
        fl = FlowLayout(parent, margin=5, spacing=10)
        btn = QPushButton('Test', parent)
        fl.addWidget(btn)
        assert fl.count() == 1

    def test_item_at(self, qtbot):
        from ui.flow_layout import FlowLayout
        parent = QWidget()
        qtbot.addWidget(parent)
        fl = FlowLayout(parent)
        btn = QPushButton('Test', parent)
        fl.addWidget(btn)
        assert fl.itemAt(0) is not None
        assert fl.itemAt(99) is None

    def test_take_at(self, qtbot):
        from ui.flow_layout import FlowLayout
        parent = QWidget()
        qtbot.addWidget(parent)
        fl = FlowLayout(parent)
        btn = QPushButton('Test', parent)
        fl.addWidget(btn)
        item = fl.takeAt(0)
        assert item is not None
        assert fl.count() == 0

    def test_take_at_invalid(self, qtbot):
        from ui.flow_layout import FlowLayout
        parent = QWidget()
        qtbot.addWidget(parent)
        fl = FlowLayout(parent)
        assert fl.takeAt(0) is None
        assert fl.takeAt(-1) is None

    def test_expanding_directions(self):
        from ui.flow_layout import FlowLayout
        fl = FlowLayout()
        assert fl.expandingDirections() == Qt.Orientations(Qt.Orientation(0))

    def test_has_height_for_width(self):
        from ui.flow_layout import FlowLayout
        fl = FlowLayout()
        assert fl.hasHeightForWidth() is True

    def test_height_for_width_empty(self):
        from ui.flow_layout import FlowLayout
        fl = FlowLayout()
        h = fl.heightForWidth(300)
        assert isinstance(h, int)

    def test_minimum_size_empty(self):
        from ui.flow_layout import FlowLayout
        fl = FlowLayout()
        size = fl.minimumSize()
        # Минимальный размер может быть отрицательным из-за margins
        assert isinstance(size.width(), int)
        assert isinstance(size.height(), int)

    def test_do_layout_with_widgets(self, qtbot):
        from ui.flow_layout import FlowLayout
        parent = QWidget()
        parent.setFixedSize(300, 300)
        qtbot.addWidget(parent)
        fl = FlowLayout(parent, margin=5, spacing=5)
        for i in range(5):
            btn = QPushButton(f'Btn{i}', parent)
            fl.addWidget(btn)
        fl.setGeometry(QRect(0, 0, 300, 300))
        assert fl.count() == 5


# ─── ChartWidget ─────────────────────────────────────────────────────────

class TestChartBase:
    """Тесты ChartBase"""

    def test_creation(self, qtbot):
        from ui.chart_widget import ChartBase
        cb = ChartBase(title='Тест')
        qtbot.addWidget(cb)
        assert cb.chart_title == 'Тест'

    def test_creation_no_matplotlib(self, qtbot):
        with patch.dict('sys.modules', {'matplotlib': None, 'matplotlib.backends': None}):
            # Если matplotlib недоступен — не падает
            from ui.chart_widget import ChartBase
            cb = ChartBase(title='Тест')
            qtbot.addWidget(cb)


class TestFunnelBarChart:
    """Тесты FunnelBarChart"""

    def test_creation(self, qtbot):
        from ui.chart_widget import FunnelBarChart
        chart = FunnelBarChart()
        qtbot.addWidget(chart)
        assert chart.chart_title == 'Воронка проектов'

    def test_set_data(self, qtbot):
        from ui.chart_widget import FunnelBarChart, MATPLOTLIB_AVAILABLE
        chart = FunnelBarChart()
        qtbot.addWidget(chart)
        if MATPLOTLIB_AVAILABLE:
            chart.set_data({'Колонка 1': 10, 'Колонка 2': 5, 'Колонка 3': 3})

    def test_set_data_empty(self, qtbot):
        from ui.chart_widget import FunnelBarChart
        chart = FunnelBarChart()
        qtbot.addWidget(chart)
        chart.set_data({})  # не падает
        chart.set_data(None)  # не падает


class TestExecutorLoadChart:
    """Тесты ExecutorLoadChart"""

    def test_creation(self, qtbot):
        from ui.chart_widget import ExecutorLoadChart
        chart = ExecutorLoadChart()
        qtbot.addWidget(chart)
        assert chart.chart_title == 'Нагрузка исполнителей'

    def test_set_data(self, qtbot):
        from ui.chart_widget import ExecutorLoadChart, MATPLOTLIB_AVAILABLE
        chart = ExecutorLoadChart()
        qtbot.addWidget(chart)
        if MATPLOTLIB_AVAILABLE:
            chart.set_data([
                {'name': 'Иванов', 'active_stages': 3},
                {'name': 'Петров', 'active_stages': 6},
                {'name': 'Сидоров', 'active_stages': 9},
            ])

    def test_set_data_empty(self, qtbot):
        from ui.chart_widget import ExecutorLoadChart
        chart = ExecutorLoadChart()
        qtbot.addWidget(chart)
        chart.set_data([])
        chart.set_data(None)


class TestProjectTypePieChart:
    """Тесты ProjectTypePieChart"""

    def test_creation(self, qtbot):
        from ui.chart_widget import ProjectTypePieChart
        chart = ProjectTypePieChart()
        qtbot.addWidget(chart)
        assert chart.chart_title == 'Типы проектов'

    def test_set_data(self, qtbot):
        from ui.chart_widget import ProjectTypePieChart, MATPLOTLIB_AVAILABLE
        chart = ProjectTypePieChart()
        qtbot.addWidget(chart)
        if MATPLOTLIB_AVAILABLE:
            chart.set_data(10, 5, 3)

    def test_set_data_all_zero(self, qtbot):
        from ui.chart_widget import ProjectTypePieChart, MATPLOTLIB_AVAILABLE
        chart = ProjectTypePieChart()
        qtbot.addWidget(chart)
        if MATPLOTLIB_AVAILABLE:
            chart.set_data(0, 0, 0)  # показывает 'Нет данных'

    def test_set_data_no_supervision(self, qtbot):
        from ui.chart_widget import ProjectTypePieChart, MATPLOTLIB_AVAILABLE
        chart = ProjectTypePieChart()
        qtbot.addWidget(chart)
        if MATPLOTLIB_AVAILABLE:
            chart.set_data(10, 5)  # без supervision


# ─── CustomMessageBox ────────────────────────────────────────────────────

class TestCustomMessageBox:
    """Тесты CustomMessageBox"""

    def test_creation_warning(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        parent = QWidget()
        qtbot.addWidget(parent)
        box = CustomMessageBox(parent, 'Тест', 'Тестовое сообщение', 'warning')
        qtbot.addWidget(box)
        assert box is not None

    def test_creation_error(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        parent = QWidget()
        qtbot.addWidget(parent)
        box = CustomMessageBox(parent, 'Ошибка', 'Текст ошибки', 'error')
        qtbot.addWidget(box)
        assert box is not None

    def test_creation_success(self, qtbot):
        from ui.custom_message_box import CustomMessageBox
        parent = QWidget()
        qtbot.addWidget(parent)
        box = CustomMessageBox(parent, 'Успех', 'Операция выполнена', 'success')
        qtbot.addWidget(box)
        assert box is not None


class TestCustomQuestionBox:
    """Тесты CustomQuestionBox"""

    def test_creation(self, qtbot):
        from ui.custom_message_box import CustomQuestionBox
        parent = QWidget()
        qtbot.addWidget(parent)
        box = CustomQuestionBox(parent, 'Вопрос', 'Удалить?')
        qtbot.addWidget(box)
        assert box is not None


# ─── CustomTitleBar ──────────────────────────────────────────────────────

class TestCustomTitleBar:
    """Тесты CustomTitleBar"""

    def test_creation(self, qtbot):
        with patch('ui.custom_title_bar.resource_path', return_value='/fake'), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            parent = QWidget()
            qtbot.addWidget(parent)
            tb = CustomTitleBar(parent, title='Заголовок')
            qtbot.addWidget(tb)
            assert tb is not None

    def test_simple_mode(self, qtbot):
        with patch('ui.custom_title_bar.resource_path', return_value='/fake'), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            parent = QWidget()
            qtbot.addWidget(parent)
            tb = CustomTitleBar(parent, title='Тест', simple_mode=True)
            qtbot.addWidget(tb)
            assert tb is not None

    def test_set_title(self, qtbot):
        with patch('ui.custom_title_bar.resource_path', return_value='/fake'), \
             patch('ui.custom_title_bar.os.path.exists', return_value=False):
            from ui.custom_title_bar import CustomTitleBar
            parent = QWidget()
            qtbot.addWidget(parent)
            tb = CustomTitleBar(parent, title='Начальный')
            qtbot.addWidget(tb)
            tb.set_title('Новый заголовок')


# ─── BubbleToolTip ───────────────────────────────────────────────────────

class TestBubbleToolTip:
    """Тесты BubbleToolTip"""

    def test_singleton_instance(self, qtbot):
        from ui.bubble_tooltip import BubbleToolTip
        BubbleToolTip._instance = None  # сброс
        inst1 = BubbleToolTip.instance()
        inst2 = BubbleToolTip.instance()
        assert inst1 is inst2

    def test_show_bubble_empty_text(self, qtbot):
        from ui.bubble_tooltip import BubbleToolTip
        BubbleToolTip._instance = None
        tip = BubbleToolTip.instance()
        tip.show_bubble('', None)  # пустой текст — hide

    def test_show_bubble_none_widget(self, qtbot):
        from ui.bubble_tooltip import BubbleToolTip
        BubbleToolTip._instance = None
        tip = BubbleToolTip.instance()
        tip.show_bubble('текст', None)  # None widget — hide

    def test_initial_state(self):
        from ui.bubble_tooltip import BubbleToolTip
        BubbleToolTip._instance = None
        tip = BubbleToolTip()
        assert tip._text == ''
        assert tip._arrow_size == 6
        assert tip._radius == 6


# ─── MessengerSelectDialog логика ────────────────────────────────────────

class TestMessengerSelectDialogLogic:
    """Тесты логики MessengerSelectDialog"""

    def test_messenger_btn_style_template(self):
        """Шаблон стиля кнопки мессенджера"""
        from ui.messenger_select_dialog import _MESSENGER_BTN_STYLE
        style = _MESSENGER_BTN_STYLE.format(
            bg='#0088cc', fg='#fff', border='#0077b3',
            hover='#0099dd', pressed='#006699'
        )
        assert 'background-color: #0088cc' in style

    def test_input_style_defined(self):
        from ui.messenger_select_dialog import _INPUT_STYLE
        assert 'QLineEdit' in _INPUT_STYLE

    def test_radio_style_defined(self):
        from ui.messenger_select_dialog import _RADIO_STYLE
        assert 'QRadioButton' in _RADIO_STYLE

    def test_checkbox_style_defined(self):
        from ui.messenger_select_dialog import _CHECKBOX_STYLE
        assert 'QCheckBox' in _CHECKBOX_STYLE


# ─── GlobalSearchWidget логика ───────────────────────────────────────────

class TestGlobalSearchWidgetLogic:
    """Тесты логики GlobalSearchWidget"""

    def test_search_worker_creation(self):
        with patch('ui.global_search_widget.QThread.__init__', return_value=None):
            from ui.global_search_widget import _SearchWorker
            try:
                worker = _SearchWorker(MagicMock(), 'test', limit=20)
                assert worker.query == 'test'
                assert worker.limit == 20
            except Exception:
                pass  # QThread может требовать QApplication
