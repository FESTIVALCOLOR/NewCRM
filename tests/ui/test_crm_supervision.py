# -*- coding: utf-8 -*-
"""
Тесты CRM Надзора — CRMSupervisionTab, SupervisionColumn, SupervisionCard, диалоги.
40 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QDialog, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


# ========== Фикстура авто-мока ==========

@pytest.fixture(autouse=True)
def _mock_supervision_msgbox():
    """Глобальный мок CustomMessageBox."""
    with patch('ui.crm_supervision_tab.CustomMessageBox') as mock_msg, \
         patch('ui.crm_supervision_tab.CustomQuestionBox', MagicMock()):
        mock_msg.return_value.exec_.return_value = None
        yield mock_msg


# ========== Хелперы ==========

def _mock_icon_loader():
    """IconLoader с реальным QIcon."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else ''))
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_supervision_tab(qtbot, mock_data_access, employee):
    """Создать CRMSupervisionTab с mock DataAccess."""
    with patch('ui.crm_supervision_tab.DataAccess') as MockDA, \
         patch('ui.crm_supervision_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_supervision_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_supervision_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_supervision_tab.TableSettings') as MockTS, \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = mock_data_access
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_supervision_tab import CRMSupervisionTab
        tab = CRMSupervisionTab(employee=employee, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _make_supervision_card_data(card_id=400, column='Новый заказ', **overrides):
    """Сгенерировать данные карточки надзора."""
    data = {
        'id': card_id,
        'contract_id': 200,
        'contract_number': f'НДЗ-{card_id}/26',
        'column_name': column,
        'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тест',
        'area': 100,
        'city': 'СПБ',
        'status': 'active',
        'agent_type': '',
        'dan_name': None,
        'senior_manager_name': None,
        'dan_completed': 0,
        'is_paused': 0,
        'deadline': None,
        'tags': '',
        'stage_executors': [],
        'yandex_folder_path': None,
    }
    data.update(overrides)
    return data


# ========== 1. Рендеринг (6 тестов) ==========

@pytest.mark.ui
class TestSupervisionRendering:
    """Проверка рендеринга вкладки CRM Надзора."""

    def test_tab_creates(self, qtbot, mock_data_access, mock_employee_admin):
        """Вкладка создаётся как QWidget."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget)

    def test_tabs_widget_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """QTabWidget существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'tabs')
        assert isinstance(tab.tabs, QTabWidget)

    def test_active_widget_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Доска активных проектов существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'active_widget')

    def test_data_access_set(self, qtbot, mock_data_access, mock_employee_admin):
        """DataAccess назначен."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None

    def test_15_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Доска имеет 15 колонок."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert len(tab.active_widget.columns) == 15

    def test_column_names_include_stages(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонки включают стадии закупок."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        col_names = list(tab.active_widget.columns.keys())
        assert 'Новый заказ' in col_names
        assert 'Выполненный проект' in col_names
        # Проверяем наличие стадий закупок
        stage_cols = [c for c in col_names if 'Стадия' in c]
        assert len(stage_cols) == 12


# ========== 2. Видимость по ролям (8 тестов) ==========

@pytest.mark.ui
class TestSupervisionRoles:
    """Видимость элементов по ролям."""

    def test_admin_sees_archive(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит архив (2 подвкладки)."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.tabs.count() >= 2

    def test_manager_sees_archive(self, qtbot, mock_data_access, mock_employee_manager):
        """Менеджер видит архив."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_manager)
        assert tab.tabs.count() >= 2

    def test_dan_no_archive(self, qtbot, mock_data_access, mock_employee_dan):
        """ДАН не видит архив (1 подвкладка)."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_dan)
        assert tab.tabs.count() == 1

    def test_dan_is_dan_role_true(self, qtbot, mock_data_access, mock_employee_dan):
        """ДАН имеет is_dan_role = True."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_dan)
        assert tab.is_dan_role is True

    def test_admin_is_dan_role_false(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ имеет is_dan_role = False."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.is_dan_role is False

    def test_stats_visible_admin(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит кнопку статистики."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        btns = tab.findChildren(QPushButton)
        stat_btns = [b for b in btns if 'статистик' in b.text().lower()]
        assert len(stat_btns) >= 1

    def test_stats_hidden_dan(self, qtbot, mock_data_access, mock_employee_dan):
        """ДАН не видит кнопку статистики."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_dan)
        btns = tab.findChildren(QPushButton)
        stat_btns = [b for b in btns if 'статистик' in b.text().lower()]
        assert len(stat_btns) == 0

    def test_sr_manager_sees_archive(self, qtbot, mock_data_access, mock_employee_senior_manager):
        """Старший менеджер видит архив."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_senior_manager)
        assert tab.tabs.count() >= 2


# ========== 3. Колонки (6 тестов) ==========

@pytest.mark.ui
class TestSupervisionColumns:
    """Проверка колонок доски надзора."""

    def test_column_is_frame(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка — QFrame."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.active_widget.columns.values():
            assert isinstance(col, QFrame)
            break

    def test_column_has_cards_list(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка имеет cards_list."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.active_widget.columns.values():
            assert hasattr(col, 'cards_list')
            break

    def test_column_has_header(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка имеет header_label."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.active_widget.columns.values():
            assert hasattr(col, 'header_label')
            break

    def test_column_has_collapse_btn(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка имеет кнопку сворачивания."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.active_widget.columns.values():
            assert hasattr(col, 'collapse_btn')
            break

    def test_first_column_new_order(self, qtbot, mock_data_access, mock_employee_admin):
        """Первая колонка — Новый заказ."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        first = list(tab.active_widget.columns.keys())[0]
        assert first == 'Новый заказ'

    def test_last_column_completed(self, qtbot, mock_data_access, mock_employee_admin):
        """Последняя колонка — Выполненный проект."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        last = list(tab.active_widget.columns.keys())[-1]
        assert last == 'Выполненный проект'


# ========== 4. Ленивая загрузка (4 теста) ==========

@pytest.mark.ui
class TestSupervisionLazyLoading:
    """Ленивая загрузка данных."""

    def test_data_not_loaded_on_create(self, qtbot, mock_data_access, mock_employee_admin):
        """Данные не загружены при создании."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab._data_loaded is False

    def test_ensure_data_loaded_sets_flag(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded устанавливает флаг."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        assert tab._data_loaded is True

    def test_ensure_data_loaded_calls_api(self, qtbot, mock_data_access, mock_employee_admin):
        """ensure_data_loaded загружает данные."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        mock_data_access.get_supervision_cards_active.assert_called()

    def test_double_ensure_no_reload(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторный ensure не перезагружает."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.ensure_data_loaded()
        cnt = mock_data_access.get_supervision_cards_active.call_count
        tab.ensure_data_loaded()
        assert mock_data_access.get_supervision_cards_active.call_count == cnt


# ========== 5. Стадии и маппинг (6 тестов) ==========

@pytest.mark.ui
class TestSupervisionStages:
    """Стадии и маппинг надзора."""

    def test_stage_1_ceramic(self, qtbot, mock_data_access, mock_employee_admin):
        """Стадия 1 — Закупка керамогранита."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        cols = list(tab.active_widget.columns.keys())
        ceramic_stages = [c for c in cols if 'керамогранит' in c.lower()]
        assert len(ceramic_stages) == 1

    def test_stage_12_decor(self, qtbot, mock_data_access, mock_employee_admin):
        """Стадия 12 — Закупка декора."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        cols = list(tab.active_widget.columns.keys())
        decor_purchase = [c for c in cols if 'закупка' in c.lower() and 'декор' in c.lower()]
        assert len(decor_purchase) == 1

    def test_12_working_stages(self, qtbot, mock_data_access, mock_employee_admin):
        """12 рабочих стадий (без Новый заказ, В ожидании, Выполненный)."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        cols = list(tab.active_widget.columns.keys())
        working = [c for c in cols if 'Стадия' in c]
        assert len(working) == 12

    def test_stage_order(self, qtbot, mock_data_access, mock_employee_admin):
        """Стадии идут в правильном порядке."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        cols = list(tab.active_widget.columns.keys())
        stage_indices = [i for i, c in enumerate(cols) if 'Стадия' in c]
        assert stage_indices == sorted(stage_indices)

    def test_has_waiting_column(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка 'В ожидании' существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert 'В ожидании' in tab.active_widget.columns

    def test_on_card_moved_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Метод on_card_moved существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'on_card_moved')
        assert callable(tab.on_card_moved)


# ========== 6. Навигация и прочее (10 тестов) ==========

@pytest.mark.ui
class TestSupervisionNavigation:
    """Навигация и общие элементы."""

    def test_first_tab_active(self, qtbot, mock_data_access, mock_employee_admin):
        """При создании активна первая вкладка."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.tabs.currentIndex() == 0

    def test_on_tab_changed_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Метод on_tab_changed существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'on_tab_changed')

    def test_refresh_method_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Метод refresh_current_tab существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'refresh_current_tab')
        assert callable(tab.refresh_current_tab)

    def test_employee_stored(self, qtbot, mock_data_access, mock_employee_admin):
        """employee сохранён."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.employee == mock_employee_admin

    def test_refresh_btn_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """Кнопка обновления существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        btns = tab.findChildren(QPushButton)
        refresh_btns = [b for b in btns if 'обновить' in b.text().lower()]
        assert len(refresh_btns) >= 1

    def test_card_moved_signal_on_column(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонки имеют сигнал card_moved."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.active_widget.columns.values():
            assert hasattr(col, 'card_moved')
            break

    def test_column_has_is_collapsed(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка имеет атрибут _is_collapsed."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        for col in tab.active_widget.columns.values():
            assert hasattr(col, '_is_collapsed')
            break

    def test_yandex_disk_attr(self, qtbot, mock_data_access, mock_employee_admin):
        """Атрибут yandex_disk существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'yandex_disk')

    def test_db_attr(self, qtbot, mock_data_access, mock_employee_admin):
        """Атрибут db существует."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.db is not None

    def test_api_client_none(self, qtbot, mock_data_access, mock_employee_admin):
        """api_client = None (offline)."""
        tab = _create_supervision_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.api_client is None
