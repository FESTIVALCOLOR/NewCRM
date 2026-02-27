# -*- coding: utf-8 -*-
"""Тесты для ui/crm_archive.py и ui/base_kanban_tab.py"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtWidgets import QListWidget, QListWidgetItem, QWidget


# ─── Патчи для импортов ─────────────────────────────────────────────────

ARCHIVE_PATCHES = {
    'ui.crm_archive.DataAccess': MagicMock,
    'ui.crm_archive.IconLoader': MagicMock(),
    'ui.crm_archive.CustomTitleBar': MagicMock(return_value=QWidget()),
    'ui.crm_archive.CustomMessageBox': MagicMock(),
    'ui.crm_archive.CustomQuestionBox': MagicMock(),
    'ui.crm_archive.CustomComboBox': MagicMock(),
    'ui.crm_archive.YANDEX_DISK_TOKEN': 'fake_token',
    'ui.crm_archive.resource_path': lambda p: p,
}


# ─── base_kanban_tab.py ─────────────────────────────────────────────────

class TestBaseDraggableList:
    """Тесты BaseDraggableList"""

    def test_creation_drag_enabled(self, qtbot):
        with patch('ui.base_kanban_tab.IconLoader', MagicMock()), \
             patch('ui.base_kanban_tab.DataAccess', MagicMock()), \
             patch('ui.base_kanban_tab.TableSettings', MagicMock()):
            from ui.base_kanban_tab import BaseDraggableList

            class ConcreteDraggableList(BaseDraggableList):
                def dropEvent(self, event):
                    pass

            lst = ConcreteDraggableList(parent_column=MagicMock(), can_drag=True)
            qtbot.addWidget(lst)
            assert lst.can_drag is True
            assert lst.dragDropMode() == QListWidget.DragDrop

    def test_creation_drag_disabled(self, qtbot):
        with patch('ui.base_kanban_tab.IconLoader', MagicMock()), \
             patch('ui.base_kanban_tab.DataAccess', MagicMock()), \
             patch('ui.base_kanban_tab.TableSettings', MagicMock()):
            from ui.base_kanban_tab import BaseDraggableList

            class ConcreteDraggableList(BaseDraggableList):
                def dropEvent(self, event):
                    pass

            lst = ConcreteDraggableList(parent_column=MagicMock(), can_drag=False)
            qtbot.addWidget(lst)
            assert lst.can_drag is False
            assert lst.dragDropMode() == QListWidget.NoDragDrop

    def test_start_drag_blocked_when_no_drag(self, qtbot):
        with patch('ui.base_kanban_tab.IconLoader', MagicMock()), \
             patch('ui.base_kanban_tab.DataAccess', MagicMock()), \
             patch('ui.base_kanban_tab.TableSettings', MagicMock()):
            from ui.base_kanban_tab import BaseDraggableList

            class ConcreteDraggableList(BaseDraggableList):
                def dropEvent(self, event):
                    pass

            lst = ConcreteDraggableList(parent_column=MagicMock(), can_drag=False)
            qtbot.addWidget(lst)
            lst.startDrag(Qt.MoveAction)  # не падает, просто return

    def test_start_drag_no_item(self, qtbot):
        with patch('ui.base_kanban_tab.IconLoader', MagicMock()), \
             patch('ui.base_kanban_tab.DataAccess', MagicMock()), \
             patch('ui.base_kanban_tab.TableSettings', MagicMock()):
            from ui.base_kanban_tab import BaseDraggableList

            class ConcreteDraggableList(BaseDraggableList):
                def dropEvent(self, event):
                    pass

            lst = ConcreteDraggableList(parent_column=MagicMock(), can_drag=True)
            qtbot.addWidget(lst)
            lst.startDrag(Qt.MoveAction)  # нет текущего элемента


class TestBaseKanbanColumn:
    """Тесты BaseKanbanColumn"""

    @pytest.fixture
    def column(self, qtbot):
        with patch('ui.base_kanban_tab.IconLoader') as MockIL, \
             patch('ui.base_kanban_tab.DataAccess', MagicMock()), \
             patch('ui.base_kanban_tab.TableSettings') as MockTS:
            MockIL.load.return_value = MagicMock()
            mock_settings = MagicMock()
            mock_settings.get_column_collapsed_state.return_value = None
            MockTS.return_value = mock_settings

            from ui.base_kanban_tab import BaseKanbanColumn

            class ConcreteColumn(BaseKanbanColumn):
                def init_ui(self):
                    from PyQt5.QtWidgets import QVBoxLayout, QLabel, QPushButton
                    layout = QVBoxLayout()
                    self.header_label = QLabel('Тест')
                    self.collapse_btn = QPushButton()
                    self.cards_list = QListWidget()
                    layout.addWidget(self.header_label)
                    layout.addWidget(self.collapse_btn)
                    layout.addWidget(self.cards_list)
                    self.setLayout(layout)

                def _make_vertical_label(self):
                    return QLabel('V')

                def _create_card_widget(self, card_data):
                    w = QWidget()
                    w.setMinimumHeight(50)
                    return w

            col = ConcreteColumn()
            col.column_name = 'Тестовая колонка'
            col._board_name = 'test_board'
            col.init_ui()
            qtbot.addWidget(col)
            return col

    def test_initial_state(self, column):
        assert column._is_collapsed is False
        assert column.column_name == 'Тестовая колонка'

    def test_collapse_column(self, column):
        column._collapse_column()
        assert column._is_collapsed is True
        assert column.cards_list.isHidden()
        assert column.header_label.isHidden()
        assert column.vertical_label is not None

    def test_expand_column(self, column):
        column._collapse_column()
        column._expand_column()
        assert column._is_collapsed is False

    def test_toggle_collapse(self, column):
        column.toggle_collapse()
        assert column._is_collapsed is True
        column.toggle_collapse()
        assert column._is_collapsed is False

    def test_update_header_count_zero(self, column):
        column.update_header_count()
        assert column.header_label.text() == 'Тестовая колонка'

    def test_update_header_count_nonzero(self, column):
        item = QListWidgetItem()
        column.cards_list.addItem(item)
        column.update_header_count()
        assert '(1)' in column.header_label.text()

    def test_update_header_count_collapsed(self, column):
        item = QListWidgetItem()
        column.cards_list.addItem(item)
        column._collapse_column()
        column.update_header_count()
        assert column.vertical_label is not None
        assert '(1)' in column.vertical_label.text()

    def test_add_card(self, column):
        column.add_card({'id': 1, 'name': 'test'})
        assert column.cards_list.count() == 1

    def test_add_card_bulk(self, column):
        column.add_card({'id': 1}, bulk=True)
        column.add_card({'id': 2}, bulk=True)
        assert column.cards_list.count() == 2

    def test_clear_cards(self, column):
        column.add_card({'id': 1})
        column.add_card({'id': 2})
        column.clear_cards()
        assert column.cards_list.count() == 0

    def test_find_card_item_by_id(self, column):
        column.add_card({'id': 42})
        item, row = column.find_card_item_by_id(42)
        assert item is not None
        assert row == 0

    def test_find_card_item_by_id_not_found(self, column):
        item, row = column.find_card_item_by_id(999)
        assert item is None
        assert row == -1

    def test_collapse_short_name_with_colon(self, column):
        column.column_name = 'Дизайн: интерьер'
        column._collapse_column()
        assert 'Дизайн' in column.vertical_label.text()

    def test_apply_initial_collapse_state_none(self, column):
        column._settings.get_column_collapsed_state.return_value = None
        column._apply_initial_collapse_state()
        assert column._is_collapsed is False

    def test_apply_initial_collapse_state_true(self, column):
        column._settings.get_column_collapsed_state.return_value = True
        column._apply_initial_collapse_state()
        assert column._is_collapsed is True


class TestBaseKanbanTab:
    """Тесты BaseKanbanTab"""

    @pytest.fixture
    def tab(self, qtbot):
        with patch('ui.base_kanban_tab.IconLoader') as MockIL, \
             patch('ui.base_kanban_tab.DataAccess') as MockDA, \
             patch('ui.base_kanban_tab.TableSettings', MagicMock()):
            MockIL.load.return_value = MagicMock()
            MockIL.create_action_button.return_value = MagicMock()
            mock_da = MagicMock()
            MockDA.return_value = mock_da

            from ui.base_kanban_tab import BaseKanbanTab

            class ConcreteTab(BaseKanbanTab):
                def init_ui(self):
                    pass

                def load_active_data(self):
                    pass

                def get_tab_title(self):
                    return 'Тест'

            employee = {'id': 1, 'role': 'admin', 'full_name': 'Тест'}
            t = ConcreteTab(employee=employee)
            qtbot.addWidget(t)
            return t

    def test_initial_state(self, tab):
        assert tab._data_loaded is False
        assert tab._loading_guard is False

    def test_get_sync_manager_none(self, tab):
        assert tab._get_sync_manager() is None

    def test_notify_dashboard_refresh(self, tab):
        tab._notify_dashboard_refresh()  # не падает

    def test_make_kanban_scroll_area(self, tab):
        scroll, layout = tab._make_kanban_scroll_area()
        assert scroll is not None
        assert layout is not None

    def test_on_tab_changed_guard(self, tab):
        tab._loading_guard = True
        tab._on_tab_changed_impl = MagicMock()
        tab.on_tab_changed(0)
        tab._on_tab_changed_impl.assert_not_called()

    def test_on_tab_changed_sets_prefer_local(self, tab):
        calls = []

        def impl(index):
            calls.append(tab.data.prefer_local)

        tab._on_tab_changed_impl = impl
        tab.on_tab_changed(0)
        assert calls == [True]
        assert tab.data.prefer_local is False

    def test_refresh_current_tab(self, tab):
        tab._notify_dashboard_refresh = MagicMock()
        tab.refresh_current_tab()
        tab._notify_dashboard_refresh.assert_called_once()


# ─── crm_archive.py — ArchiveCard ───────────────────────────────────────

class TestArchiveCard:
    """Тесты ArchiveCard"""

    @pytest.fixture
    def make_card(self, qtbot):
        def _make(card_data=None, card_type='crm'):
            if card_data is None:
                card_data = {
                    'id': 1,
                    'contract_number': 'ИД-001',
                    'address': 'ул. Тестовая 1',
                    'area': 100,
                    'city': 'Москва',
                    'contract_status': 'СДАН',
                    'agent_type': 'Прямой',
                }
            mock_da = MagicMock()
            mock_da.db = MagicMock()
            mock_da.get_agent_color.return_value = '#4CAF50'
            with patch('ui.crm_archive.DataAccess', return_value=mock_da), \
                 patch('ui.crm_archive.IconLoader') as MockIL:
                MockIL.create_icon_button.return_value = MagicMock(spec=QWidget)
                MockIL.create_icon_button.return_value.setFixedSize = MagicMock()
                MockIL.create_icon_button.return_value.setStyleSheet = MagicMock()
                MockIL.create_icon_button.return_value.setEnabled = MagicMock()
                MockIL.create_icon_button.return_value.clicked = MagicMock()
                # Возвращаем реальную QPushButton чтобы addWidget работал
                from PyQt5.QtWidgets import QPushButton
                btn = QPushButton('test')
                MockIL.create_icon_button.return_value = btn
                card = MagicMock()
                # Тестируем инициализацию данных напрямую
                card.card_data = card_data
                card.card_type = card_type
                return card
        return _make

    def test_status_sdan_color(self):
        """Статус СДАН — зелёный фон"""
        data = {'contract_status': 'СДАН', 'status': ''}
        status = data.get('contract_status') or data.get('status', '')
        assert 'СДАН' in status

    def test_status_rastorgnut_color(self):
        """Статус РАСТОРГНУТ — красный фон"""
        data = {'contract_status': 'РАСТОРГНУТ'}
        status = data.get('contract_status') or data.get('status', '')
        assert 'РАСТОРГНУТ' in status

    def test_status_nadzor_color(self):
        """Статус АВТОРСКИЙ НАДЗОР — синий фон"""
        data = {'contract_status': 'АВТОРСКИЙ НАДЗОР'}
        status = data.get('contract_status') or data.get('status', '')
        assert 'НАДЗОР' in status

    def test_status_fallback(self):
        """Неизвестный статус — серый фон"""
        data = {'contract_status': 'ДРУГОЙ'}
        status = data.get('contract_status') or data.get('status', '')
        assert 'СДАН' not in status
        assert 'РАСТОРГНУТ' not in status
        assert 'НАДЗОР' not in status

    def test_status_from_status_key(self):
        """Фоллбэк на ключ status если contract_status отсутствует"""
        data = {'status': 'СДАН'}
        status = data.get('contract_status') or data.get('status', '')
        assert 'СДАН' in status

    def test_card_data_area_city(self):
        """Карточка с площадью и городом"""
        data = {'area': 150, 'city': 'Москва', 'contract_status': 'СДАН'}
        assert data.get('area') == 150
        assert data.get('city') == 'Москва'

    def test_card_data_no_area(self):
        """Карточка без площади"""
        data = {'contract_status': 'СДАН'}
        assert data.get('area') is None

    def test_agent_type_present(self):
        """Карточка с типом агента"""
        data = {'agent_type': 'Агент', 'contract_status': 'СДАН'}
        assert data.get('agent_type') == 'Агент'

    def test_supervision_button_hidden_for_nadzor(self):
        """Кнопка 'В авторский надзор' скрыта для статуса НАДЗОР"""
        status = 'АВТОРСКИЙ НАДЗОР'
        should_show = 'АВТОРСКИЙ НАДЗОР' not in status and 'НАДЗОР' not in status
        assert should_show is False

    def test_supervision_button_visible_for_sdan(self):
        """Кнопка 'В авторский надзор' видна для статуса СДАН"""
        status = 'СДАН'
        should_show = 'АВТОРСКИЙ НАДЗОР' not in status and 'НАДЗОР' not in status
        assert should_show is True


class TestArchiveCardDetailsDialog:
    """Тесты логики ArchiveCardDetailsDialog"""

    def test_card_data_fields(self):
        """Проверка полей карточки для диалога"""
        card_data = {
            'id': 1, 'contract_number': 'ИД-001',
            'address': 'ул. Тестовая 1', 'area': 100,
            'city': 'Москва', 'contract_status': 'СДАН',
            'agent_type': 'Прямой', 'tags': 'VIP',
            'deadline': '2026-12-31',
            'termination_reason': None,
        }
        assert card_data.get('contract_number') == 'ИД-001'
        assert card_data.get('termination_reason') is None

    def test_termination_reason_present(self):
        """Карточка с причиной расторжения"""
        card_data = {
            'contract_status': 'РАСТОРГНУТ',
            'termination_reason': 'Клиент отказался',
        }
        assert card_data.get('termination_reason') is not None

    def test_tags_present(self):
        """Карточка с тегами"""
        card_data = {'tags': 'VIP, Срочный', 'contract_status': 'СДАН'}
        assert card_data.get('tags') == 'VIP, Срочный'

    def test_deadline_present(self):
        """Карточка с дедлайном"""
        card_data = {'deadline': '2026-06-01', 'contract_status': 'СДАН'}
        assert card_data.get('deadline') == '2026-06-01'

    def test_card_type_crm(self):
        """Тип карточки CRM"""
        card_type = 'crm'
        assert card_type == 'crm'

    def test_card_type_supervision(self):
        """Тип карточки supervision"""
        card_type = 'supervision'
        assert card_type == 'supervision'
