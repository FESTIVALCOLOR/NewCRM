# -*- coding: utf-8 -*-
"""
Глубокие тесты CRM вкладки — edge cases, взаимодействия, фильтрация.

НЕ дублирует 82 теста из test_crm.py. Покрывает:
  - TestCRMLoadCardsForType (8)    — загрузка карточек по типу, фильтрация, пустые данные
  - TestCRMOnTabChanged (5)        — переключение вкладок, loading_guard, prefer_local
  - TestCRMRefresh (5)             — обновление, счётчики, dashboard
  - TestCRMCardRendering (8)       — отображение данных карточки, стили, прогресс
  - TestCRMCardEdgeCases (5)       — пустые данные, None значения, кириллица
  - TestCRMColumnInteraction (5)   — DraggableListWidget, card_moved, bulk mode
  - TestCRMPermissions (5)         — _has_perm, _load_user_permissions, кэш
ИТОГО: 41 тест
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QDialog, QComboBox, QFrame, QListWidget
)
from PyQt5.QtCore import Qt, QDate
from PyQt5.QtGui import QIcon


# ========== Фикстура авто-мока CustomMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_crm_deep_msgbox():
    """Глобальный мок CustomMessageBox чтобы диалоги не блокировали тесты."""
    with patch('ui.crm_tab.CustomMessageBox') as mock_msg, \
         patch('ui.crm_tab.CustomQuestionBox') as mock_q:
        mock_msg.return_value.exec_.return_value = None
        mock_q.return_value.exec_.return_value = None
        yield mock_msg


# ========== Хелперы ==========

def _mock_icon_loader():
    """Настроить IconLoader."""
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
    """Создать CRMTab с mock DataAccess."""
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


def _make_card_data(card_id=300, column='Новый заказ', project_type='Индивидуальный',
                    project_subtype='Полный проект', **overrides):
    """Сгенерировать минимальные данные CRM карточки."""
    data = {
        'id': card_id,
        'contract_id': 200,
        'contract_number': f'ИП-ПОЛ-{card_id}/26',
        'project_type': project_type,
        'project_subtype': project_subtype,
        'column_name': column,
        'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тест',
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
        'measurement_link': None,
        'references_link': None,
        'project_data_link': None,
        'contract_file_link': None,
        'yandex_folder_path': None,
        'stage_executors': [],
        'deadline': None,
        'manager_id': None,
        'sdp_id': None,
        'gap_id': None,
        'tags': '',
        'agent_type': '',
        'total_amount': 500000,
        'advance_payment': 150000,
        'additional_payment': 200000,
        'third_payment': 150000,
        'contract_date': '2026-01-15',
        'contract_period': 45,
    }
    data.update(overrides)
    return data


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


# ========== 1. Загрузка карточек по типу (8 тестов) ==========

@pytest.mark.ui
class TestCRMLoadCardsForType:
    """Загрузка карточек load_cards_for_type — edge cases и фильтрация."""

    def test_load_individual_cards_places_in_correct_columns(self, qtbot, mock_data_access, mock_employee_admin):
        """Карточки размещаются в колонках по column_name."""
        cards = [
            _make_card_data(card_id=1, column='Новый заказ'),
            _make_card_data(card_id=2, column='В ожидании'),
            _make_card_data(card_id=3, column='Стадия 1: планировочные решения'),
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        # Каждая колонка должна содержать соответствующую карточку
        assert tab.individual_widget.columns['Новый заказ'].cards_list.count() == 1, \
            "Колонка 'Новый заказ' должна содержать 1 карточку"
        assert tab.individual_widget.columns['В ожидании'].cards_list.count() == 1
        assert tab.individual_widget.columns['Стадия 1: планировочные решения'].cards_list.count() == 1

    def test_load_cards_empty_list(self, qtbot, mock_data_access, mock_employee_admin):
        """Пустой список карточек — колонки пустые, без ошибок."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        for col in tab.individual_widget.columns.values():
            assert col.cards_list.count() == 0, "Все колонки должны быть пустыми"

    def test_load_cards_none_response(self, qtbot, mock_data_access, mock_employee_admin):
        """get_crm_cards возвращает None — обработка без ошибок."""
        mock_data_access.get_crm_cards.return_value = None
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        # Не должен упасть
        tab.load_cards_for_type('Индивидуальный')

    def test_load_cards_with_unknown_column(self, qtbot, mock_data_access, mock_employee_admin):
        """Карточка с неизвестным column_name — игнорируется без ошибок."""
        cards = [_make_card_data(card_id=1, column='Несуществующая колонка')]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        total = sum(col.cards_list.count() for col in tab.individual_widget.columns.values())
        assert total == 0, "Карточка с неизвестной колонкой не должна добавляться"

    def test_load_cards_template_type(self, qtbot, mock_data_access, mock_employee_admin):
        """Загрузка карточек для шаблонных проектов."""
        cards = [
            _make_card_data(card_id=1, column='Новый заказ', project_type='Шаблонный'),
            _make_card_data(card_id=2, column='Стадия 2: рабочие чертежи', project_type='Шаблонный'),
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Шаблонный')
        assert tab.template_widget.columns['Новый заказ'].cards_list.count() == 1
        assert tab.template_widget.columns['Стадия 2: рабочие чертежи'].cards_list.count() == 1

    def test_load_cards_updates_counters(self, qtbot, mock_data_access, mock_employee_admin):
        """После загрузки карточек обновляются счётчики вкладок."""
        cards = [
            _make_card_data(card_id=i, column='Новый заказ') for i in range(5)
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        tab_text = tab.project_tabs.tabText(0)
        assert '5' in tab_text, f"Счётчик должен содержать '5', получено: '{tab_text}'"

    def test_load_cards_clears_old_cards(self, qtbot, mock_data_access, mock_employee_admin):
        """Повторная загрузка очищает старые карточки."""
        cards = [_make_card_data(card_id=1, column='Новый заказ')]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        assert tab.individual_widget.columns['Новый заказ'].cards_list.count() == 1
        # Повторная загрузка с пустым списком
        mock_data_access.get_crm_cards.return_value = []
        tab.load_cards_for_type('Индивидуальный')
        assert tab.individual_widget.columns['Новый заказ'].cards_list.count() == 0

    def test_load_cards_exception_handled(self, qtbot, mock_data_access, mock_employee_admin):
        """Исключение в get_crm_cards — обработка без краша UI."""
        mock_data_access.get_crm_cards.side_effect = Exception("Тестовая ошибка сети")
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        # Не должен упасть
        tab.load_cards_for_type('Индивидуальный')


# ========== 2. Переключение вкладок (5 тестов) ==========

@pytest.mark.ui
class TestCRMOnTabChanged:
    """Переключение между вкладками проектов."""

    def test_tab_changed_loads_individual(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение на index=0 загружает индивидуальные карточки."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.reset_mock()
        tab.on_tab_changed(0)
        mock_data_access.get_crm_cards.assert_called_with('Индивидуальный')

    def test_tab_changed_loads_template(self, qtbot, mock_data_access, mock_employee_admin):
        """Переключение на index=1 загружает шаблонные карточки."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.reset_mock()
        tab.on_tab_changed(1)
        mock_data_access.get_crm_cards.assert_called_with('Шаблонный')

    def test_loading_guard_prevents_on_tab_changed(self, qtbot, mock_data_access, mock_employee_admin):
        """_loading_guard=True предотвращает повторную загрузку при переключении."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        mock_data_access.get_crm_cards.reset_mock()
        tab._loading_guard = True
        tab.on_tab_changed(0)
        # Не должно быть вызовов get_crm_cards
        mock_data_access.get_crm_cards.assert_not_called()

    def test_tab_changed_uses_prefer_local(self, qtbot, mock_data_access, mock_employee_admin):
        """on_tab_changed устанавливает prefer_local=True перед загрузкой."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        # Проверяем через side_effect, что prefer_local устанавливается
        prefer_local_during_call = []

        def capture_prefer_local(*args, **kwargs):
            prefer_local_during_call.append(tab.data.prefer_local)
            return []

        mock_data_access.get_crm_cards.side_effect = capture_prefer_local
        tab.on_tab_changed(0)
        assert len(prefer_local_during_call) > 0, "get_crm_cards должен быть вызван"
        assert prefer_local_during_call[0] is True, "prefer_local должен быть True во время загрузки"

    def test_tab_changed_restores_prefer_local(self, qtbot, mock_data_access, mock_employee_admin):
        """После on_tab_changed prefer_local возвращается в False."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.on_tab_changed(0)
        assert tab.data.prefer_local is False, "prefer_local должен вернуться в False"


# ========== 3. Обновление и счётчики (5 тестов) ==========

@pytest.mark.ui
class TestCRMRefresh:
    """refresh_current_tab и update_project_tab_counters."""

    def test_refresh_current_tab_index_0(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab при index=0 загружает индивидуальные."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.project_tabs.setCurrentIndex(0)
        mock_data_access.get_crm_cards.reset_mock()
        tab.refresh_current_tab()
        mock_data_access.get_crm_cards.assert_called()

    def test_refresh_current_tab_index_1(self, qtbot, mock_data_access, mock_employee_admin):
        """refresh_current_tab при index=1 загружает шаблонные."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.project_tabs.setCurrentIndex(1)
        mock_data_access.get_crm_cards.reset_mock()
        tab.refresh_current_tab()
        mock_data_access.get_crm_cards.assert_called_with('Шаблонный')

    def test_update_counters_zero_cards(self, qtbot, mock_data_access, mock_employee_admin):
        """Счётчики = 0 когда карточек нет."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        tab.update_project_tab_counters()
        tab_text = tab.project_tabs.tabText(0)
        assert '0' in tab_text, f"Должен быть счётчик 0, получено: '{tab_text}'"

    def test_update_counters_multiple_cards(self, qtbot, mock_data_access, mock_employee_admin):
        """Счётчики корректно считают карточки в разных колонках."""
        cards = [
            _make_card_data(card_id=1, column='Новый заказ'),
            _make_card_data(card_id=2, column='Новый заказ'),
            _make_card_data(card_id=3, column='В ожидании'),
        ]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        tab.update_project_tab_counters()
        tab_text = tab.project_tabs.tabText(0)
        assert '3' in tab_text, f"Должен быть счётчик 3, получено: '{tab_text}'"

    def test_update_counters_no_crash_without_template(self, qtbot, mock_data_access, mock_employee_sdp):
        """СДП без template_widget — update_project_tab_counters не падает."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_sdp)
        # Не должен упасть
        tab.update_project_tab_counters()


# ========== 4. CRMCard рендеринг данных (8 тестов) ==========

@pytest.mark.ui
class TestCRMCardRendering:
    """Отображение данных в CRMCard: адрес, город, агент, прогресс."""

    def test_card_displays_address(self, qtbot, mock_employee_admin):
        """Карточка отображает адрес в labels."""
        data = _make_card_data(address='г. Москва, ул. Ленина, д.10')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        address_found = any('Ленина' in lbl.text() for lbl in labels if lbl.text())
        assert address_found, "Адрес 'Ленина' должен отображаться на карточке"

    def test_card_displays_city(self, qtbot, mock_employee_admin):
        """Карточка отображает город."""
        data = _make_card_data(city='МСК')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        city_found = any('МСК' in lbl.text() for lbl in labels if lbl.text())
        assert city_found, "Город 'МСК' должен отображаться на карточке"

    def test_card_displays_area(self, qtbot, mock_employee_admin):
        """Карточка отображает площадь."""
        data = _make_card_data(area=120.5)
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        area_found = any('120' in lbl.text() for lbl in labels if lbl.text())
        assert area_found, "Площадь '120' должна отображаться на карточке"

    def test_card_displays_contract_number(self, qtbot, mock_employee_admin):
        """Карточка отображает номер договора."""
        data = _make_card_data(contract_number='ШП-СТДЗ-99999/26')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        found = any('99999' in lbl.text() for lbl in labels if lbl.text())
        assert found, "Номер договора должен отображаться на карточке"

    def test_card_with_designer_shows_name(self, qtbot, mock_employee_admin):
        """Карточка с дизайнером показывает имя."""
        data = _make_card_data(
            designer_name='Иванова А.А.',
            column='Стадия 2: концепция дизайна'
        )
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        found = any('Иванова' in lbl.text() for lbl in labels if lbl.text())
        assert found, "Имя дизайнера должно отображаться"

    def test_card_with_draftsman_shows_name(self, qtbot, mock_employee_admin):
        """Карточка с чертёжником показывает имя."""
        data = _make_card_data(
            draftsman_name='Петров Б.Б.',
            column='Стадия 1: планировочные решения'
        )
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        labels = card.findChildren(QLabel)
        found = any('Петров' in lbl.text() for lbl in labels if lbl.text())
        assert found, "Имя чертёжника должно отображаться"

    def test_card_is_qframe(self, qtbot, mock_employee_admin):
        """CRMCard наследует QFrame."""
        data = _make_card_data()
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert isinstance(card, QFrame), "CRMCard должен быть QFrame"

    def test_card_with_agent_type(self, qtbot, mock_employee_admin):
        """Карточка с типом агента отображает его."""
        data = _make_card_data(agent_type='Фестиваль')
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        # Агентский тип может отображаться как текст или иконка
        assert card.card_data['agent_type'] == 'Фестиваль'


# ========== 5. CRMCard edge cases (5 тестов) ==========

@pytest.mark.ui
class TestCRMCardEdgeCases:
    """Edge cases для CRMCard."""

    def test_card_with_none_values(self, qtbot, mock_employee_admin):
        """Карточка с None в ключевых полях не падает."""
        data = _make_card_data(
            client_name=None,
            address=None,
            city=None,
            designer_name=None,
            deadline=None,
        )
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card is not None, "Карточка должна создаться даже с None"

    def test_card_with_empty_strings(self, qtbot, mock_employee_admin):
        """Карточка с пустыми строками не падает."""
        data = _make_card_data(
            client_name='',
            address='',
            city='',
            tags='',
        )
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card is not None

    def test_card_with_long_address(self, qtbot, mock_employee_admin):
        """Карточка с очень длинным адресом не падает."""
        long_addr = 'г. Санкт-Петербург, ул. Очень Длинное Название Улицы, д.12345, корп.6, кв.789'
        data = _make_card_data(address=long_addr)
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['address'] == long_addr

    def test_card_with_zero_area(self, qtbot, mock_employee_admin):
        """Карточка с площадью 0 не падает."""
        data = _make_card_data(area=0)
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert card.card_data['area'] == 0

    def test_card_with_stage_executors_list(self, qtbot, mock_employee_admin):
        """Карточка с несколькими исполнителями."""
        executors = [
            {'stage_name': 'Стадия 1', 'executor_id': 7, 'executor_name': 'Чертёжник А'},
            {'stage_name': 'Стадия 2', 'executor_id': 6, 'executor_name': 'Дизайнер Б'},
            {'stage_name': 'Стадия 3', 'executor_id': 8, 'executor_name': 'Чертёжник В'},
        ]
        data = _make_card_data(stage_executors=executors)
        card = _create_crm_card(qtbot, data, mock_employee_admin)
        assert len(card.card_data['stage_executors']) == 3


# ========== 6. CRMColumn взаимодействие (5 тестов) ==========

@pytest.mark.ui
class TestCRMColumnInteraction:
    """CRMColumn: DraggableListWidget, card_moved, bulk mode."""

    def test_column_clear_cards(self, qtbot, mock_data_access, mock_employee_admin):
        """clear_cards очищает список карточек."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        col = tab.individual_widget.columns['Новый заказ']
        col.clear_cards()
        assert col.cards_list.count() == 0, "После clear_cards список должен быть пустым"

    def test_column_update_header_count(self, qtbot, mock_data_access, mock_employee_admin):
        """update_header_count обновляет счётчик в заголовке."""
        cards = [_make_card_data(card_id=i, column='Новый заказ') for i in range(3)]
        mock_data_access.get_crm_cards.return_value = cards
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        tab.load_cards_for_type('Индивидуальный')
        col = tab.individual_widget.columns['Новый заказ']
        header_text = col.header_label.text()
        assert '3' in header_text, f"Заголовок должен содержать '3', получено: '{header_text}'"

    def test_column_has_project_type(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка хранит project_type."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        col = tab.individual_widget.columns['Новый заказ']
        assert col.project_type == 'Индивидуальный'

    def test_column_has_column_name(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка хранит column_name."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        col = tab.individual_widget.columns['В ожидании']
        assert col.column_name == 'В ожидании'

    def test_column_has_employee(self, qtbot, mock_data_access, mock_employee_admin):
        """Колонка хранит ссылку на employee."""
        mock_data_access.get_crm_cards.return_value = []
        tab = _create_crm_tab(qtbot, mock_data_access, mock_employee_admin)
        col = tab.individual_widget.columns['Новый заказ']
        assert col.employee == mock_employee_admin


# ========== 7. Permissions (5 тестов) ==========

@pytest.mark.ui
class TestCRMPermissions:
    """Кэш permissions и функции _has_perm."""

    def test_load_user_permissions_caches(self):
        """_load_user_permissions кэширует результат."""
        from ui.crm_tab import _load_user_permissions, _user_permissions_cache
        # Очищаем кэш перед тестом
        _user_permissions_cache.clear()
        emp = {'id': 999, 'position': 'Дизайнер', 'role': ''}
        perms = _load_user_permissions(emp, None)
        assert isinstance(perms, set), "Должен вернуть set"
        # Второй вызов использует кэш
        perms2 = _load_user_permissions(emp, None)
        assert perms2 is perms or perms2 == perms
        # Очистка
        _user_permissions_cache.pop(999, None)

    def test_has_perm_admin_always_true(self):
        """Суперюзер имеет все права (_has_perm всегда True)."""
        from ui.crm_tab import _has_perm, _user_permissions_cache
        _user_permissions_cache.clear()
        emp = {'id': 998, 'position': 'Руководитель', 'role': 'admin'}
        result = _has_perm(emp, None, 'crm_cards.update')
        assert result is True
        _user_permissions_cache.pop(998, None)

    def test_has_perm_director_always_true(self):
        """Директор имеет все права."""
        from ui.crm_tab import _has_perm, _user_permissions_cache
        _user_permissions_cache.clear()
        emp = {'id': 997, 'position': 'Руководитель', 'role': 'director'}
        result = _has_perm(emp, None, 'some.permission')
        assert result is True
        _user_permissions_cache.pop(997, None)

    def test_has_perm_empty_permissions(self):
        """Пользователь без permissions — _has_perm False."""
        from ui.crm_tab import _has_perm, _user_permissions_cache
        _user_permissions_cache.clear()
        emp = {'id': 996, 'position': 'Дизайнер', 'role': ''}
        result = _has_perm(emp, None, 'crm_cards.update')
        assert result is False
        _user_permissions_cache.pop(996, None)

    def test_load_user_permissions_none_employee(self):
        """_load_user_permissions с None employee — пустой set."""
        from ui.crm_tab import _load_user_permissions
        result = _load_user_permissions(None, None)
        assert result == set()
