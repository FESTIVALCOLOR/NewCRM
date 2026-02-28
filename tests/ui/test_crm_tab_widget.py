# -*- coding: utf-8 -*-
"""
Widget-тесты CRM вкладки — реальные QWidget через pytest-qt.

Покрывает UI-рендеринг ui/crm_tab.py:
  - TestCRMTabCreation (5)          — создание виджета, видимость, тип
  - TestCRMTabUIElements (6)        — наличие ключевых UI элементов
  - TestCRMTabProjectTypes (5)      — переключение Инд/Шаблонные, колонки
  - TestCRMColumnRendering (5)      — пустые колонки, заголовки, счётчики
  - TestCRMColumnWithCards (4)      — рендеринг с карточками
  - TestCRMCardWidget (5)           — создание карточки, данные, стили
  - TestCRMTabRoleVisibility (4)    — видимость элементов по ролям
  - TestCRMColumnCollapse (4)       — свёрнутые/развёрнутые колонки
  - TestCRMTabRefreshButton (2)     — кнопка обновления
  - TestCRMCardFormatting (4)       — форматирование текста карточки
ИТОГО: 44 теста
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QFrame, QListWidget, QScrollArea, QGroupBox
)
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon


# ========== Фикстура авто-мока CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_crm_widget_msgbox():
    """Глобальный мок CustomMessageBox/CustomQuestionBox чтобы диалоги не блокировали тесты."""
    with patch('ui.crm_tab.CustomMessageBox') as mock_msg, \
         patch('ui.crm_tab.CustomQuestionBox') as mock_q:
        mock_msg.return_value.exec_.return_value = None
        mock_q.return_value.exec_.return_value = None
        yield


# ========== Хелперы ==========

def _mock_icon_loader():
    """Настроить IconLoader: load() -> QIcon, create_icon_button -> QPushButton."""
    mock = MagicMock()
    mock.load = MagicMock(return_value=QIcon())
    mock.create_icon_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.create_action_button = MagicMock(
        side_effect=lambda *a, **k: QPushButton(a[1] if len(a) > 1 else '')
    )
    mock.get_icon_path = MagicMock(return_value='')
    return mock


def _create_crm_tab(qtbot, mock_data_access, employee, can_edit=True):
    """Создать CRMTab с mock DataAccess и полностью замоканными зависимостями."""
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS, \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = mock_data_access
        MockTS.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_tab import CRMTab
        tab = CRMTab(employee=employee, can_edit=can_edit, api_client=None)
        qtbot.addWidget(tab)
        return tab


def _create_crm_column(qtbot, column_name, project_type, employee, can_edit=True):
    """Создать отдельную CRMColumn с моками."""
    mock_db = MagicMock()
    mock_ts_instance = MagicMock()
    mock_ts_instance.get_column_collapsed_state.return_value = None
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings', return_value=mock_ts_instance), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings', return_value=mock_ts_instance):
        MockDA.return_value = MagicMock()
        from ui.crm_tab import CRMColumn
        column = CRMColumn(column_name, project_type, employee, can_edit, mock_db, api_client=None)
        qtbot.addWidget(column)
        return column


def _create_crm_card(qtbot, card_data, employee, can_edit=True):
    """Создать CRMCard с mock данными."""
    mock_db = MagicMock()
    with patch('ui.crm_tab.DataAccess') as MockDA, \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockDA.return_value = MagicMock()
        from ui.crm_tab import CRMCard
        card = CRMCard(card_data, can_edit, mock_db, employee=employee, api_client=None)
        qtbot.addWidget(card)
        return card


def _make_card_data(card_id=300, column='Новый заказ', project_type='Индивидуальный',
                    **overrides):
    """Сгенерировать минимальные данные CRM карточки."""
    data = {
        'id': card_id,
        'contract_id': 200,
        'contract_number': f'ИП-ПОЛ-{card_id}/26',
        'project_type': project_type,
        'project_subtype': 'Полный проект',
        'column_name': column,
        'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тестовая, д.1',
        'area': 85.5,
        'city': 'СПБ',
        'status': 'active',
        'designer_name': None,
        'draftsman_name': None,
        'designer_completed': 0,
        'draftsman_completed': 0,
        'is_approved': 0,
        'survey_date': None,
        'tech_task_date': None,
        'tech_task_link': None,
        'tech_task_file': None,
        'measurement_image_link': None,
        'measurement_link': None,
        'references_link': None,
        'project_data_link': None,
        'contract_file_link': None,
        'yandex_folder_path': None,
        'stage_executors': [],
        'deadline': None,
        'designer_deadline': None,
        'draftsman_deadline': None,
        'manager_id': None,
        'sdp_id': None,
        'gap_id': None,
        'senior_manager_name': None,
        'sdp_name': None,
        'gap_name': None,
        'manager_name': None,
        'surveyor_name': None,
        'surveyor_id': None,
        'designer_name': None,
        'draftsman_name': None,
        'tags': '',
        'agent_type': '',
        'agent_name': '',
        'total_amount': 500000,
        'advance_payment': 150000,
        'additional_payment': 200000,
        'third_payment': 150000,
        'contract_date': '2026-01-15',
        'contract_period': 45,
    }
    data.update(overrides)
    return data


# ========== 1. Создание CRMTab (5 тестов) ==========

@pytest.mark.ui
class TestCRMTabCreation:
    """Базовое создание и инициализация CRMTab."""

    def test_crm_tab_is_qwidget(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab является экземпляром QWidget."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert isinstance(tab, QWidget), "CRMTab должен наследоваться от QWidget"

    def test_crm_tab_has_layout(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab имеет установленный layout."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.layout() is not None, "CRMTab должен иметь layout"

    def test_crm_tab_stores_employee(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab сохраняет ссылку на сотрудника."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.employee == mock_employee_admin, "CRMTab должен хранить employee"

    def test_crm_tab_stores_can_edit(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab сохраняет флаг can_edit."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin, can_edit=False)
        assert tab.can_edit is False, "can_edit=False должен сохраняться"

    def test_crm_tab_has_data_access(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab создаёт DataAccess."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.data is not None, "CRMTab должен иметь DataAccess"


# ========== 2. Наличие ключевых UI элементов (6 тестов) ==========

@pytest.mark.ui
class TestCRMTabUIElements:
    """Наличие ключевых UI элементов на вкладке CRM."""

    def test_has_project_tabs(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab содержит QTabWidget для типов проектов."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'project_tabs'), "Должен быть атрибут project_tabs"
        assert isinstance(tab.project_tabs, QTabWidget), "project_tabs должен быть QTabWidget"

    def test_project_tabs_has_individual_tab(self, qtbot, mock_data_access, mock_employee_admin):
        """Есть вкладка 'Индивидуальные проекты'."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab_texts = [tab.project_tabs.tabText(i) for i in range(tab.project_tabs.count())]
        has_individual = any('Индивидуальные' in t for t in tab_texts)
        assert has_individual, f"Должна быть вкладка 'Индивидуальные проекты', найдено: {tab_texts}"

    def test_project_tabs_has_template_tab_for_admin(self, qtbot, mock_data_access, mock_employee_admin):
        """Для администратора есть вкладка 'Шаблонные проекты'."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab_texts = [tab.project_tabs.tabText(i) for i in range(tab.project_tabs.count())]
        has_template = any('Шаблонные' in t for t in tab_texts)
        assert has_template, f"Должна быть вкладка 'Шаблонные проекты' для admin, найдено: {tab_texts}"

    def test_has_individual_widget(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab имеет individual_widget (доска для индивидуальных проектов)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'individual_widget'), "Должен быть individual_widget"
        assert hasattr(tab.individual_widget, 'columns'), "individual_widget должен иметь columns"

    def test_has_template_widget(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab имеет template_widget (доска для шаблонных проектов) для admin."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'template_widget'), "Должен быть template_widget для admin"
        assert hasattr(tab.template_widget, 'columns'), "template_widget должен иметь columns"

    def test_header_label_exists(self, qtbot, mock_data_access, mock_employee_admin):
        """CRMTab содержит заголовок 'CRM - Управление проектами'."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        labels = tab.findChildren(QLabel)
        header_texts = [lbl.text() for lbl in labels]
        has_header = any('CRM' in t and 'проект' in t.lower() for t in header_texts)
        assert has_header, f"Должен быть заголовок CRM, найдено: {header_texts[:5]}"


# ========== 3. Переключение между типами проектов (5 тестов) ==========

@pytest.mark.ui
class TestCRMTabProjectTypes:
    """Переключение между индивидуальными и шаблонными проектами."""

    def test_individual_columns_count(self, qtbot, mock_data_access, mock_employee_admin):
        """Индивидуальная доска содержит 6 колонок."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        columns = tab.individual_widget.columns
        assert len(columns) == 6, f"Ожидалось 6 колонок, получено {len(columns)}"

    def test_individual_columns_names(self, qtbot, mock_data_access, mock_employee_admin):
        """Индивидуальная доска содержит правильные названия колонок."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        columns = tab.individual_widget.columns
        expected = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: планировочные решения',
            'Стадия 2: концепция дизайна',
            'Стадия 3: рабочие чертежи',
            'Выполненный проект'
        ]
        for name in expected:
            assert name in columns, f"Колонка '{name}' должна присутствовать"

    def test_template_columns_count(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонная доска содержит 6 колонок."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        columns = tab.template_widget.columns
        assert len(columns) == 6, f"Ожидалось 6 колонок, получено {len(columns)}"

    def test_template_columns_names(self, qtbot, mock_data_access, mock_employee_admin):
        """Шаблонная доска содержит правильные названия колонок."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        columns = tab.template_widget.columns
        expected = [
            'Новый заказ', 'В ожидании',
            'Стадия 1: планировочные решения',
            'Стадия 2: рабочие чертежи',
            'Стадия 3: 3д визуализация (Дополнительная)',
            'Выполненный проект'
        ]
        for name in expected:
            assert name in columns, f"Колонка '{name}' должна присутствовать в шаблонных"

    def test_switch_project_tabs(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение вкладок меняет currentIndex."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.project_tabs.setCurrentIndex(1)
        assert tab.project_tabs.currentIndex() == 1, "Должна быть активна вкладка шаблонных"
        tab.project_tabs.setCurrentIndex(0)
        assert tab.project_tabs.currentIndex() == 0, "Должна быть активна вкладка индивидуальных"


# ========== 4. Рендеринг пустых колонок (5 тестов) ==========

@pytest.mark.ui
class TestCRMColumnRendering:
    """Рендеринг пустых колонок CRMColumn."""

    def test_column_is_qframe(self, qtbot, mock_employee_admin):
        """CRMColumn является экземпляром QFrame."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        assert isinstance(column, QFrame), "CRMColumn должна быть QFrame"

    def test_column_has_header_label(self, qtbot, mock_employee_admin):
        """CRMColumn содержит заголовок с именем колонки."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        assert hasattr(column, 'header_label'), "Должен быть header_label"
        assert isinstance(column.header_label, QLabel), "header_label должен быть QLabel"
        assert 'Новый заказ' in column.header_label.text(), \
            f"Заголовок должен содержать имя колонки, получено: '{column.header_label.text()}'"

    def test_column_has_cards_list(self, qtbot, mock_employee_admin):
        """CRMColumn содержит QListWidget для карточек."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        assert hasattr(column, 'cards_list'), "Должен быть cards_list"
        assert isinstance(column.cards_list, QListWidget), "cards_list должен быть QListWidget"

    def test_empty_column_count_is_zero(self, qtbot, mock_employee_admin):
        """Пустая колонка содержит 0 карточек."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        assert column.cards_list.count() == 0, "Пустая колонка должна содержать 0 элементов"

    def test_column_has_collapse_button(self, qtbot, mock_employee_admin):
        """CRMColumn содержит кнопку сворачивания."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        assert hasattr(column, 'collapse_btn'), "Должна быть кнопка сворачивания collapse_btn"
        assert isinstance(column.collapse_btn, QPushButton), "collapse_btn должна быть QPushButton"


# ========== 5. Рендеринг колонки с карточками (4 теста) ==========

@pytest.mark.ui
class TestCRMColumnWithCards:
    """Рендеринг колонки с добавленными карточками."""

    def test_add_card_increases_count(self, qtbot, mock_employee_admin):
        """Добавление карточки увеличивает счётчик."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        card_data = _make_card_data(card_id=1, column='Новый заказ')
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = MagicMock()
            column.add_card(card_data)
        assert column.cards_list.count() == 1, "После add_card должна быть 1 карточка"

    def test_add_multiple_cards(self, qtbot, mock_employee_admin):
        """Добавление нескольких карточек."""
        column = _create_crm_column(qtbot, 'В ожидании', 'Индивидуальный', mock_employee_admin)
        for i in range(3):
            card_data = _make_card_data(card_id=i + 1, column='В ожидании')
            with patch('ui.crm_tab.DataAccess') as MockDA, \
                 patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
                 patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
                MockDA.return_value = MagicMock()
                column.add_card(card_data, bulk=True)
        column.update_header_count()
        assert column.cards_list.count() == 3, "Должно быть 3 карточки"
        assert '3' in column.header_label.text(), \
            f"Заголовок должен содержать '3', получено: '{column.header_label.text()}'"

    def test_clear_cards_removes_all(self, qtbot, mock_employee_admin):
        """clear_cards очищает все карточки."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        card_data = _make_card_data(card_id=1, column='Новый заказ')
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = MagicMock()
            column.add_card(card_data)
        assert column.cards_list.count() == 1
        column.clear_cards()
        assert column.cards_list.count() == 0, "После clear_cards должно быть 0 карточек"

    def test_header_count_after_add_and_clear(self, qtbot, mock_employee_admin):
        """Заголовок обновляется после добавления и очистки."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        # Пустая колонка — без счётчика
        assert 'Новый заказ' in column.header_label.text()
        # Добавляем карточку
        card_data = _make_card_data(card_id=1, column='Новый заказ')
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = MagicMock()
            column.add_card(card_data)
        assert '1' in column.header_label.text(), "Заголовок должен показать (1)"
        # Очищаем
        column.clear_cards()
        # После очистки — без счётчика
        assert 'Новый заказ' == column.header_label.text().strip(), \
            f"После очистки заголовок: '{column.header_label.text()}'"


# ========== 6. CRMCard виджет (5 тестов) ==========

@pytest.mark.ui
class TestCRMCardWidget:
    """Создание и рендеринг CRMCard."""

    def test_card_is_qframe(self, qtbot, mock_employee_admin):
        """CRMCard является QFrame."""
        card_data = _make_card_data()
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        assert isinstance(card, QFrame), "CRMCard должна быть QFrame"

    def test_card_stores_card_data(self, qtbot, mock_employee_admin):
        """CRMCard хранит card_data."""
        card_data = _make_card_data(address='г. Москва, Тверская 1')
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        assert card.card_data['address'] == 'г. Москва, Тверская 1'

    def test_card_has_layout(self, qtbot, mock_employee_admin):
        """CRMCard имеет layout."""
        card_data = _make_card_data()
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        assert card.layout() is not None, "CRMCard должна иметь layout"

    def test_card_displays_contract_number(self, qtbot, mock_employee_admin):
        """CRMCard отображает номер договора."""
        card_data = _make_card_data(contract_number='ИП-ПОЛ-99999/26')
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        has_contract = any('99999' in t for t in texts)
        assert has_contract, f"Карточка должна содержать номер договора, найдено: {texts}"

    def test_card_displays_address(self, qtbot, mock_employee_admin):
        """CRMCard отображает адрес."""
        card_data = _make_card_data(address='пр. Невский, д. 100')
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        has_address = any('Невский' in t for t in texts)
        assert has_address, f"Карточка должна содержать адрес, найдено: {texts}"


# ========== 7. Видимость элементов по ролям (4 теста) ==========

@pytest.mark.ui
class TestCRMTabRoleVisibility:
    """Видимость UI-элементов в зависимости от роли сотрудника."""

    def test_admin_sees_two_tabs(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит обе вкладки: Индивидуальные и Шаблонные."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert tab.project_tabs.count() == 2, \
            f"Админ должен видеть 2 вкладки, видит {tab.project_tabs.count()}"

    def test_sdp_sees_only_individual_tab(self, qtbot, mock_data_access, mock_employee_sdp):
        """СДП видит только индивидуальные проекты (нет шаблонных)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_sdp)
        assert tab.project_tabs.count() == 1, \
            f"СДП должен видеть 1 вкладку, видит {tab.project_tabs.count()}"

    def test_designer_sees_two_tabs(self, qtbot, mock_data_access, mock_employee_designer):
        """Дизайнер видит обе вкладки (шаблонные не скрыты для дизайнера)."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_designer)
        # Дизайнер — не чистый СДП, поэтому шаблонные видны
        assert tab.project_tabs.count() == 2, \
            f"Дизайнер должен видеть 2 вкладки, видит {tab.project_tabs.count()}"

    def test_admin_has_archive_subtabs(self, qtbot, mock_data_access, mock_employee_admin):
        """Админ видит подвкладки Архив в индивидуальных проектах."""
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        assert hasattr(tab, 'individual_subtabs'), "Должны быть individual_subtabs"
        # Админ должен видеть подвкладку архива
        assert tab.individual_subtabs.count() >= 2, \
            f"Должно быть >= 2 подвкладок (Активные + Архив), найдено: {tab.individual_subtabs.count()}"


# ========== 8. Свёрнутые/развёрнутые колонки (4 теста) ==========

@pytest.mark.ui
class TestCRMColumnCollapse:
    """Тестирование сворачивания/разворачивания колонок."""

    def test_column_initially_expanded(self, qtbot, mock_employee_admin):
        """Обычная колонка начинает развёрнутой."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        assert column._is_collapsed is False, "Колонка должна начинаться развёрнутой"
        # isHidden() проверяет явный hide(), а не видимость в иерархии (offscreen)
        assert not column.cards_list.isHidden(), "cards_list не должен быть скрыт"

    def test_toggle_collapse_hides_cards(self, qtbot, mock_employee_admin):
        """toggle_collapse скрывает список карточек."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        with patch.object(column._settings, 'save_column_collapsed_state'):
            column.toggle_collapse()
        assert column._is_collapsed is True, "Колонка должна быть свёрнута"
        assert column.cards_list.isHidden(), "cards_list должен быть скрыт"

    def test_toggle_collapse_twice_restores(self, qtbot, mock_employee_admin):
        """Двойной toggle возвращает колонку в развёрнутое состояние."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        with patch.object(column._settings, 'save_column_collapsed_state'):
            column.toggle_collapse()
            column.toggle_collapse()
        assert column._is_collapsed is False, "После двойного toggle колонка должна быть развёрнута"
        assert not column.cards_list.isHidden(), "cards_list не должен быть скрыт"

    def test_collapsed_column_width_is_narrow(self, qtbot, mock_employee_admin):
        """Свёрнутая колонка имеет узкую ширину."""
        column = _create_crm_column(qtbot, 'Новый заказ', 'Индивидуальный', mock_employee_admin)
        with patch.object(column._settings, 'save_column_collapsed_state'):
            column.toggle_collapse()
        assert column.maximumWidth() == column._collapsed_width, \
            f"Ширина свёрнутой колонки должна быть {column._collapsed_width}, получено {column.maximumWidth()}"


# ========== 9. Кнопка обновления (2 теста) ==========

@pytest.mark.ui
class TestCRMTabRefreshButton:
    """Кнопка обновления данных."""

    def test_refresh_calls_load_cards(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab вызывает load_cards_for_type."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.reset_mock()
        tab.project_tabs.setCurrentIndex(0)
        tab.refresh_current_tab()
        mock_data_access.get_crm_cards.assert_called(), \
            "refresh_current_tab должен вызывать get_crm_cards"

    def test_refresh_updates_counters(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab обновляет счётчики вкладок."""
        cards = [_make_card_data(card_id=i, column='Новый заказ') for i in range(3)]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.project_tabs.setCurrentIndex(0)
        tab.refresh_current_tab()
        tab_text = tab.project_tabs.tabText(0)
        assert '3' in tab_text, f"Счётчик должен содержать '3', получено: '{tab_text}'"


# ========== 10. Форматирование текста карточки (4 теста) ==========

@pytest.mark.ui
class TestCRMCardFormatting:
    """Форматирование данных в карточке."""

    def test_card_shows_area_in_sq_meters(self, qtbot, mock_employee_admin):
        """Площадь отображается в м2."""
        card_data = _make_card_data(area=120.5)
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        has_area = any('120.5' in t and 'м' in t for t in texts)
        assert has_area, f"Карточка должна содержать '120.5 м²', найдено: {texts}"

    def test_card_shows_city(self, qtbot, mock_employee_admin):
        """Город отображается на карточке."""
        card_data = _make_card_data(city='МСК')
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        has_city = any('МСК' in t for t in texts)
        assert has_city, f"Карточка должна содержать 'МСК', найдено: {texts}"

    def test_card_shows_agent_type(self, qtbot, mock_employee_admin):
        """Тип агента отображается если указан."""
        card_data = _make_card_data(agent_type='Авито')
        mock_da = MagicMock()
        mock_da.get_agent_color.return_value = '#FF0000'
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
             patch('ui.crm_tab.YandexDiskManager', return_value=None), \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.TableSettings'):
            MockDA.return_value = mock_da
            from ui.crm_tab import CRMCard
            card = CRMCard(card_data, True, MagicMock(), employee=mock_employee_admin, api_client=None)
            qtbot.addWidget(card)
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        has_agent = any('Авито' in t for t in texts)
        assert has_agent, f"Карточка должна содержать тип агента 'Авито', найдено: {texts}"

    def test_card_shows_tags_if_present(self, qtbot, mock_employee_admin):
        """Теги отображаются если указаны."""
        card_data = _make_card_data(tags='VIP')
        card = _create_crm_card(qtbot, card_data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        has_tags = any('VIP' in t for t in texts)
        assert has_tags, f"Карточка должна содержать тег 'VIP', найдено: {texts}"


# ========== 11. Дополнительные widget-тесты ==========

@pytest.mark.ui
class TestCRMTabLoadCardsWidget:
    """Загрузка карточек в реальные виджеты."""

    def test_load_populates_individual_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """load_cards_for_type('Индивидуальный') заполняет колонки."""
        cards = [
            _make_card_data(card_id=1, column='Новый заказ'),
            _make_card_data(card_id=2, column='Новый заказ'),
            _make_card_data(card_id=3, column='Выполненный проект'),
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = mock_data_access
            tab.load_cards_for_type('Индивидуальный')
        assert tab.individual_widget.columns['Новый заказ'].cards_list.count() == 2
        assert tab.individual_widget.columns['Выполненный проект'].cards_list.count() == 1

    def test_load_template_populates_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """load_cards_for_type('Шаблонный') заполняет шаблонные колонки."""
        cards = [
            _make_card_data(card_id=1, column='Новый заказ', project_type='Шаблонный'),
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = mock_data_access
            tab.load_cards_for_type('Шаблонный')
        assert tab.template_widget.columns['Новый заказ'].cards_list.count() == 1

    def test_reload_clears_and_refills(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторная загрузка очищает старые и заполняет новые карточки."""
        # Первая загрузка — 2 карточки
        cards = [
            _make_card_data(card_id=1, column='В ожидании'),
            _make_card_data(card_id=2, column='В ожидании'),
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = mock_data_access
            tab.load_cards_for_type('Индивидуальный')
        assert tab.individual_widget.columns['В ожидании'].cards_list.count() == 2
        # Вторая загрузка — 1 карточка
        mock_data_access.get_crm_cards.return_value = [
            _make_card_data(card_id=3, column='В ожидании'),
        ]
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = mock_data_access
            tab.load_cards_for_type('Индивидуальный')
        assert tab.individual_widget.columns['В ожидании'].cards_list.count() == 1

    def test_card_data_stored_in_item(self, qtbot, mock_data_access, mock_employee_admin):
        """card_id сохраняется в UserRole данных QListWidgetItem."""
        cards = [_make_card_data(card_id=42, column='Новый заказ')]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        with patch('ui.crm_tab.DataAccess') as MockDA, \
             patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
             patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()):
            MockDA.return_value = mock_data_access
            tab.load_cards_for_type('Индивидуальный')
        col = tab.individual_widget.columns['Новый заказ']
        item = col.cards_list.item(0)
        assert item is not None, "Должен быть элемент в колонке"
        assert item.data(Qt.UserRole) == 42, f"card_id должен быть 42, получено: {item.data(Qt.UserRole)}"
