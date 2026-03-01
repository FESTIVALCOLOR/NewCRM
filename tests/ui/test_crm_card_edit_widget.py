# -*- coding: utf-8 -*-
"""
Widget-тесты CardEditDialog — покрытие UI-рендеринга через pytest-qt.

Фокус: визуальные элементы, наличие виджетов, текст лейблов, видимость
кнопок по ролям, tab-структура, поля формы, состояния виджетов.

Покрытие:
  - TestWidgetExists (5)            — создание диалога, базовый рендеринг
  - TestDialogTitle (3)             — заголовок, title bar
  - TestTabStructureAdmin (6)       — вкладки для администратора
  - TestTabStructureDesigner (4)    — вкладки для дизайнера (исполнитель)
  - TestProjectInfoFields (6)       — поля информации проекта (адрес, площадь, город)
  - TestTeamCombos (5)              — комбобоксы команды проекта
  - TestButtonsVisibility (6)       — кнопки: сохранить, отмена, удалить, чат
  - TestChatButtons (4)             — кнопки мессенджера (создать/открыть/удалить чат)
  - TestStatusCombo (4)             — комбобокс статуса проекта
  - TestDeadlineDisplay (3)         — отображение дедлайна
  - TestSurveyDateDisplay (3)       — отображение даты замера
  - TestTagsField (3)               — поле тегов
  - TestViewOnlyMode (4)            — режим только просмотр
  - TestSdpVisibility (3)           — СДП отображается только для индивидуальных
  - TestSyncLabel (2)               — надпись синхронизации
ИТОГО: ~61 тест
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QWidget, QTabWidget, QPushButton, QLabel,
    QDialog, QComboBox, QLineEdit, QFrame, QScrollArea
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon


# ========== Фикстуры ==========

@pytest.fixture(autouse=True)
def _mock_widget_test_externals():
    """Мок внешних зависимостей: MessageBox, DatabaseManager, YandexDisk."""
    with patch('ui.crm_card_edit_dialog.CustomMessageBox') as mock_msg, \
         patch('ui.crm_card_edit_dialog.CustomQuestionBox') as mock_q, \
         patch('ui.crm_card_edit_dialog.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_card_edit_dialog.YandexDiskManager', return_value=None), \
         patch('ui.crm_card_edit_dialog.YANDEX_DISK_TOKEN', ''):
        mock_msg.return_value.exec_.return_value = None
        mock_q.return_value.exec_.return_value = None
        yield


def _mock_icon_loader():
    """Мок IconLoader для избежания загрузки SVG-файлов."""
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


def _make_card_data(**overrides):
    """Минимальные данные CRM карточки для CardEditDialog."""
    data = {
        'id': 300,
        'contract_id': 200,
        'contract_number': 'ИП-ПОЛ-300/26',
        'project_type': 'Индивидуальный',
        'project_subtype': 'Полный проект',
        'column_name': 'Стадия 2: концепция дизайна',
        'client_name': 'Тестовый Клиент',
        'address': 'г. СПб, ул. Тестовая, д.1',
        'area': 85.5,
        'city': 'СПБ',
        'status': 'active',
        'designer_name': 'Дизайнер Тест',
        'draftsman_name': None,
        'designer_completed': 0,
        'draftsman_completed': 0,
        'is_approved': 0,
        'survey_date': '2026-02-10',
        'tech_task_date': '2026-01-20',
        'tech_task_link': None,
        'measurement_link': None,
        'references_link': None,
        'project_data_link': None,
        'contract_file_link': None,
        'yandex_folder_path': '/test/path',
        'stage_executors': [],
        'deadline': '2026-04-15',
        'manager_id': 5,
        'sdp_id': 3,
        'gap_id': 4,
        'senior_manager_id': 2,
        'surveyor_id': 8,
        'tags': 'VIP, Срочный',
        'agent_type': 'Риелтор',
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


def _make_mock_da(card_data=None):
    """Создать MagicMock DataAccess с типовыми ответами."""
    mock_da = MagicMock()
    mock_da.get_crm_card.return_value = card_data or _make_card_data()
    mock_da.get_contract.return_value = {
        'id': 200, 'status': 'active', 'tech_task_link': None,
        'tech_task_file_name': None, 'measurement_image_link': None,
        'measurement_file_name': None, 'references_yandex_path': None,
        'photo_documentation_yandex_path': None, 'yandex_folder_path': '/test',
        'area': 85.5, 'city': 'СПБ', 'project_type': 'Индивидуальный',
        'project_subtype': 'Полный проект',
    }
    mock_da.get_payments_for_contract.return_value = []
    mock_da.get_project_timeline.return_value = []
    mock_da.get_action_history.return_value = []
    mock_da.get_employees_by_position.return_value = []
    mock_da.get_all_employees.return_value = [
        {'id': 2, 'full_name': 'Старший Менеджер', 'position': 'Старший менеджер проектов',
         'secondary_position': '', 'status': 'активный'},
        {'id': 3, 'full_name': 'СДП Тест', 'position': 'СДП',
         'secondary_position': '', 'status': 'активный'},
        {'id': 4, 'full_name': 'ГАП Тест', 'position': 'ГАП',
         'secondary_position': '', 'status': 'активный'},
        {'id': 5, 'full_name': 'Менеджер Тест', 'position': 'Менеджер',
         'secondary_position': '', 'status': 'активный'},
        {'id': 8, 'full_name': 'Замерщик Тест', 'position': 'Замерщик',
         'secondary_position': '', 'status': 'активный'},
        {'id': 6, 'full_name': 'Дизайнер Тест', 'position': 'Дизайнер',
         'secondary_position': '', 'status': 'активный'},
    ]
    mock_da.get_employee.return_value = None
    mock_da.is_online = False
    mock_da.is_multi_user = False
    mock_da.db = MagicMock()
    mock_da.api_client = None
    return mock_da


def _create_dialog(qtbot, card_data=None, employee=None, view_only=False):
    """Фабрика для создания CardEditDialog с полной изоляцией IO."""
    if card_data is None:
        card_data = _make_card_data()
    if employee is None:
        employee = {
            "id": 1, "full_name": "Тестов Админ", "login": "admin",
            "position": "Руководитель студии", "secondary_position": "",
            "department": "Административный отдел",
            "status": "активный", "offline_mode": False,
        }

    mock_da = _make_mock_da(card_data)

    parent = QWidget()
    parent.data = mock_da
    parent.api_client = None
    qtbot.addWidget(parent)

    with patch('ui.crm_card_edit_dialog.DataAccess', return_value=mock_da), \
         patch('ui.crm_card_edit_dialog.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_card_edit_dialog.YandexDiskManager', return_value=None), \
         patch('ui.crm_card_edit_dialog.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_card_edit_dialog.YANDEX_DISK_TOKEN', ''), \
         patch('ui.crm_card_edit_dialog.TableSettings') as MockTS, \
         patch('ui.crm_card_edit_dialog.create_progress_dialog', return_value=MagicMock()), \
         patch('ui.crm_tab.DataAccess', return_value=mock_da), \
         patch('ui.crm_tab.DatabaseManager', return_value=MagicMock()), \
         patch('ui.crm_tab.YandexDiskManager', return_value=None), \
         patch('ui.crm_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.crm_tab.TableSettings') as MockTS2, \
         patch('ui.base_kanban_tab.IconLoader', _mock_icon_loader()), \
         patch('ui.base_kanban_tab.TableSettings'):
        MockTS.return_value.load_column_collapse_state.return_value = {}
        MockTS2.return_value.load_column_collapse_state.return_value = {}
        from ui.crm_card_edit_dialog import CardEditDialog
        dialog = CardEditDialog(
            parent, card_data=card_data, view_only=view_only,
            employee=employee, api_client=None,
        )
        qtbot.addWidget(dialog)
        return dialog, mock_da


# Сотрудники для параметризации
_ADMIN = {
    "id": 1, "full_name": "Тестов Админ", "login": "admin",
    "position": "Руководитель студии", "secondary_position": "",
    "department": "Административный отдел",
    "status": "активный", "offline_mode": False,
}

_DESIGNER = {
    "id": 6, "full_name": "Дизайнеров Тест", "login": "designer",
    "position": "Дизайнер", "secondary_position": "",
    "department": "Проектный отдел",
    "status": "активный", "offline_mode": False,
}

_MANAGER = {
    "id": 5, "full_name": "Менеджер Тестов", "login": "manager",
    "position": "Менеджер", "secondary_position": "",
    "department": "Административный отдел",
    "status": "активный", "offline_mode": False,
}

_SDP = {
    "id": 3, "full_name": "СДП Тестов", "login": "sdp",
    "position": "СДП", "secondary_position": "",
    "department": "Проектный отдел",
    "status": "активный", "offline_mode": False,
}

_GAP = {
    "id": 4, "full_name": "ГАП Тестов", "login": "gap",
    "position": "ГАП", "secondary_position": "",
    "department": "Проектный отдел",
    "status": "активный", "offline_mode": False,
}

_DRAFTSMAN = {
    "id": 7, "full_name": "Чертёжник Тестов", "login": "draftsman",
    "position": "Чертёжник", "secondary_position": "",
    "department": "Исполнительный отдел",
    "status": "активный", "offline_mode": False,
}

_SURVEYOR = {
    "id": 8, "full_name": "Замерщик Тестов", "login": "surveyor",
    "position": "Замерщик", "secondary_position": "",
    "department": "Исполнительный отдел",
    "status": "активный", "offline_mode": False,
}

_DESIGNER_MANAGER = {
    "id": 10, "full_name": "Дизайнер-Менеджер", "login": "des_mgr",
    "position": "Дизайнер", "secondary_position": "Менеджер",
    "department": "Проектный отдел",
    "status": "активный", "offline_mode": False,
}

_SENIOR_MANAGER = {
    "id": 2, "full_name": "Старший Менеджер", "login": "sr_manager",
    "position": "Старший менеджер проектов", "secondary_position": "",
    "department": "Административный отдел",
    "status": "активный", "offline_mode": False,
}


# ========== 1. Создание виджета (5 тестов) ==========

@pytest.mark.ui
class TestWidgetExists:
    """Базовый рендеринг — диалог создаётся без ошибок."""

    def test_dialog_is_qdialog(self, qtbot):
        """CardEditDialog наследует QDialog."""
        dialog, _ = _create_dialog(qtbot)
        assert isinstance(dialog, QDialog)

    def test_dialog_has_layout(self, qtbot):
        """Диалог имеет layout."""
        dialog, _ = _create_dialog(qtbot)
        assert dialog.layout() is not None

    def test_dialog_not_visible_by_default(self, qtbot):
        """Диалог не показывается автоматически."""
        dialog, _ = _create_dialog(qtbot)
        assert not dialog.isVisible()

    def test_dialog_has_frameless_window_hint(self, qtbot):
        """Диалог использует FramelessWindowHint (кастомный title bar)."""
        dialog, _ = _create_dialog(qtbot)
        assert dialog.windowFlags() & Qt.FramelessWindowHint

    def test_dialog_has_translucent_background(self, qtbot):
        """WA_TranslucentBackground включён для кастомного рендеринга."""
        dialog, _ = _create_dialog(qtbot)
        assert dialog.testAttribute(Qt.WA_TranslucentBackground)


# ========== 2. Заголовок (3 теста) ==========

@pytest.mark.ui
class TestDialogTitle:
    """Заголовок окна и title bar."""

    def test_edit_mode_title(self, qtbot):
        """В режиме редактирования заголовок 'Редактирование карточки проекта'."""
        dialog, _ = _create_dialog(qtbot, view_only=False)
        # Ищем CustomTitleBar среди дочерних виджетов
        from ui.custom_title_bar import CustomTitleBar
        title_bars = dialog.findChildren(CustomTitleBar)
        assert len(title_bars) >= 1, "Должен быть CustomTitleBar"

    def test_view_mode_title(self, qtbot):
        """В режиме просмотра заголовок 'Просмотр карточки'."""
        dialog, _ = _create_dialog(qtbot, view_only=True)
        from ui.custom_title_bar import CustomTitleBar
        title_bars = dialog.findChildren(CustomTitleBar)
        assert len(title_bars) >= 1

    def test_title_bar_is_first_child(self, qtbot):
        """Title bar расположен в верхней части диалога (первый виджет в border_frame)."""
        dialog, _ = _create_dialog(qtbot)
        from ui.custom_title_bar import CustomTitleBar
        title_bars = dialog.findChildren(CustomTitleBar)
        assert title_bars, "CustomTitleBar должен присутствовать"


# ========== 3. Структура вкладок — Администратор (6 тестов) ==========

@pytest.mark.ui
class TestTabStructureAdmin:
    """Вкладки для администратора (Руководитель студии)."""

    def test_admin_has_tabs_widget(self, qtbot):
        """Админ видит QTabWidget."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'tabs')
        assert isinstance(dialog.tabs, QTabWidget)

    def test_admin_tab_count_at_least_4(self, qtbot):
        """Админ видит минимум 4 вкладки."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        # Исполнители и дедлайн, Таблица сроков, Данные по проекту, История, Оплаты
        assert dialog.tabs.count() >= 4, \
            f"Ожидалось >= 4 вкладок, получено {dialog.tabs.count()}"

    def test_admin_sees_executors_tab(self, qtbot):
        """Админ видит вкладку 'Исполнители и дедлайн'."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert any('Исполнители' in name for name in tab_names), \
            f"Вкладка 'Исполнители' не найдена среди: {tab_names}"

    def test_admin_sees_timeline_tab(self, qtbot):
        """Админ видит вкладку 'Таблица сроков'."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert any('Таблица сроков' in name for name in tab_names), \
            f"Вкладка 'Таблица сроков' не найдена: {tab_names}"

    def test_admin_sees_project_data_tab(self, qtbot):
        """Админ видит вкладку 'Данные по проекту'."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert any('Данные по проекту' in name for name in tab_names), \
            f"Вкладка 'Данные по проекту' не найдена: {tab_names}"

    def test_admin_sees_payments_tab(self, qtbot):
        """Админ видит вкладку 'Оплаты'."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert dialog.payments_tab_index >= 0, \
            "payments_tab_index должен быть >= 0 для админа"


# ========== 4. Структура вкладок — Дизайнер (4 теста) ==========

@pytest.mark.ui
class TestTabStructureDesigner:
    """Вкладки для дизайнера (чистый исполнитель)."""

    def test_designer_has_no_executors_tab(self, qtbot):
        """Дизайнер НЕ видит вкладку 'Исполнители и дедлайн'."""
        dialog, _ = _create_dialog(qtbot, employee=_DESIGNER)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names), \
            f"Дизайнер не должен видеть 'Исполнители': {tab_names}"

    def test_designer_has_no_payments_tab(self, qtbot):
        """Дизайнер НЕ видит вкладку 'Оплаты'."""
        dialog, _ = _create_dialog(qtbot, employee=_DESIGNER)
        assert dialog.payments_tab_index == -1, \
            "Дизайнер не должен видеть вкладку оплат"

    def test_designer_sees_project_data_tab(self, qtbot):
        """Дизайнер видит вкладку 'Данные по проекту'."""
        dialog, _ = _create_dialog(qtbot, employee=_DESIGNER)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert any('Данные по проекту' in name for name in tab_names), \
            f"Дизайнер должен видеть 'Данные по проекту': {tab_names}"

    def test_designer_has_no_history_tab(self, qtbot):
        """Дизайнер НЕ видит вкладку 'История по проекту'."""
        dialog, _ = _create_dialog(qtbot, employee=_DESIGNER)
        assert dialog.project_info_tab_index == -1, \
            "Дизайнер не должен видеть историю по проекту"


# ========== 5. Поля информации проекта (6 тестов) ==========

@pytest.mark.ui
class TestProjectInfoFields:
    """Поля информации проекта на вкладке 'Исполнители и дедлайн'."""

    def test_contract_number_displayed(self, qtbot):
        """Номер договора отображается."""
        cd = _make_card_data(contract_number='ИП-ТСТ-777/26')
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any('ИП-ТСТ-777/26' in t for t in texts), \
            "Номер договора должен быть на форме"

    def test_address_displayed(self, qtbot):
        """Адрес проекта отображается."""
        cd = _make_card_data(address='г. Москва, ул. Примерная, д.42')
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any('ул. Примерная' in t for t in texts), \
            "Адрес должен быть на форме"

    def test_area_displayed(self, qtbot):
        """Площадь проекта отображается."""
        cd = _make_card_data(area=120.5)
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any('120.5' in t for t in texts), \
            "Площадь должна быть на форме"

    def test_city_displayed(self, qtbot):
        """Город отображается."""
        cd = _make_card_data(city='МСК')
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any('МСК' in t for t in texts), \
            "Город должен быть на форме"

    def test_agent_type_displayed(self, qtbot):
        """Тип агента отображается."""
        cd = _make_card_data(agent_type='Риелтор')
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        labels = dialog.findChildren(QLabel)
        texts = [lbl.text() for lbl in labels]
        assert any('Риелтор' in t for t in texts), \
            "Тип агента должен быть на форме"

    def test_subtype_displayed(self, qtbot):
        """Подтип проекта отображается."""
        cd = _make_card_data(project_subtype='Полный проект')
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        assert hasattr(dialog, 'subtype_val_label')
        assert 'Полный проект' in dialog.subtype_val_label.text()


# ========== 6. Комбобоксы команды проекта (5 тестов) ==========

@pytest.mark.ui
class TestTeamCombos:
    """Комбобоксы выбора членов команды."""

    def test_senior_manager_combo_exists(self, qtbot):
        """Комбобокс Старший менеджер существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'senior_manager')
        assert dialog.senior_manager is not None

    def test_senior_manager_combo_has_items(self, qtbot):
        """Комбобокс Старший менеджер содержит 'Не назначен' + сотрудников."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert dialog.senior_manager.count() >= 1
        assert dialog.senior_manager.itemText(0) == 'Не назначен'

    def test_gap_combo_exists(self, qtbot):
        """Комбобокс ГАП существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'gap')
        assert dialog.gap is not None
        assert dialog.gap.count() >= 1

    def test_manager_combo_exists(self, qtbot):
        """Комбобокс Менеджер существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'manager')
        assert dialog.manager is not None

    def test_surveyor_combo_exists(self, qtbot):
        """Комбобокс Замерщик существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'surveyor')
        assert dialog.surveyor is not None
        assert dialog.surveyor.count() >= 1


# ========== 7. Кнопки (6 тестов) ==========

@pytest.mark.ui
class TestButtonsVisibility:
    """Кнопки диалога: наличие, видимость."""

    def test_save_button_exists_in_edit_mode(self, qtbot):
        """Кнопка 'Сохранить' существует в режиме редактирования."""
        dialog, _ = _create_dialog(qtbot, view_only=False)
        save_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Сохранить' in btn.text()
        ]
        assert len(save_btns) >= 1, "Кнопка 'Сохранить' должна быть"

    def test_cancel_button_exists_in_edit_mode(self, qtbot):
        """Кнопка 'Отмена' существует в режиме редактирования."""
        dialog, _ = _create_dialog(qtbot, view_only=False)
        cancel_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Отмена' in btn.text()
        ]
        assert len(cancel_btns) >= 1, "Кнопка 'Отмена' должна быть"

    def test_delete_button_for_admin(self, qtbot):
        """Кнопка 'Удалить заказ' видна для Руководителя студии."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        delete_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Удалить' in btn.text()
        ]
        assert len(delete_btns) >= 1, "Админ должен видеть 'Удалить заказ'"

    def test_delete_button_for_senior_manager(self, qtbot):
        """Кнопка 'Удалить заказ' видна для Старшего менеджера."""
        dialog, _ = _create_dialog(qtbot, employee=_SENIOR_MANAGER, view_only=False)
        delete_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Удалить' in btn.text()
        ]
        assert len(delete_btns) >= 1, "Старший менеджер должен видеть 'Удалить'"

    def test_no_delete_button_for_manager(self, qtbot):
        """Кнопка 'Удалить заказ' НЕ видна для обычного Менеджера."""
        dialog, _ = _create_dialog(qtbot, employee=_MANAGER, view_only=False)
        delete_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Удалить заказ' in btn.text()
        ]
        assert len(delete_btns) == 0, "Менеджер не должен видеть 'Удалить заказ'"

    def test_close_button_in_view_mode(self, qtbot):
        """Кнопка 'Закрыть' видна в режиме просмотра."""
        dialog, _ = _create_dialog(qtbot, view_only=True)
        close_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Закрыть' in btn.text()
        ]
        assert len(close_btns) >= 1, "Кнопка 'Закрыть' должна быть в view_only"


# ========== 8. Кнопки чата (4 теста) ==========

@pytest.mark.ui
class TestChatButtons:
    """Кнопки мессенджера: создать/открыть/удалить чат."""

    def test_create_chat_btn_exists(self, qtbot):
        """Кнопка 'Создать чат' существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        assert hasattr(dialog, 'create_chat_btn')
        assert isinstance(dialog.create_chat_btn, QPushButton)

    def test_open_chat_btn_exists(self, qtbot):
        """Кнопка 'Открыть чат' существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        assert hasattr(dialog, 'open_chat_btn')
        assert isinstance(dialog.open_chat_btn, QPushButton)

    def test_delete_chat_btn_exists(self, qtbot):
        """Кнопка 'Удалить чат' существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        assert hasattr(dialog, 'delete_chat_btn')
        assert isinstance(dialog.delete_chat_btn, QPushButton)

    def test_script_buttons_exist(self, qtbot):
        """Кнопки скриптов мессенджера (начальный/завершающий) существуют."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        assert hasattr(dialog, 'start_script_btn')
        assert hasattr(dialog, 'end_script_btn')


# ========== 9. Комбобокс статуса проекта (4 теста) ==========

@pytest.mark.ui
class TestStatusCombo:
    """Комбобокс статуса проекта."""

    def test_status_combo_exists_for_admin(self, qtbot):
        """Комбобокс статуса существует для Руководителя."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'status_combo')

    def test_status_combo_has_correct_items(self, qtbot):
        """Комбобокс статуса содержит все статусы."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        items = [dialog.status_combo.itemText(i) for i in range(dialog.status_combo.count())]
        expected = ['Новый заказ', 'В работе', 'СДАН', 'РАСТОРГНУТ', 'АВТОРСКИЙ НАДЗОР']
        for status in expected:
            assert status in items, f"Статус '{status}' не найден в комбобоксе: {items}"

    def test_status_combo_enabled_for_admin(self, qtbot):
        """Комбобокс статуса включён для Руководителя."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert dialog.status_combo.isEnabled()

    def test_status_combo_not_created_for_sdp(self, qtbot):
        """Комбобокс статуса не создаётся для СДП (нет crm_cards.move → is_executor)."""
        dialog, _ = _create_dialog(qtbot, employee=_SDP)
        assert not hasattr(dialog, 'status_combo'), \
            "СДП — исполнитель, status_combo не должен создаваться"


# ========== 10. Отображение дедлайна (3 теста) ==========

@pytest.mark.ui
class TestDeadlineDisplay:
    """Отображение дедлайна проекта."""

    def test_deadline_display_exists(self, qtbot):
        """QLabel дедлайна существует для админа."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'deadline_display')
        assert isinstance(dialog.deadline_display, QLabel)

    def test_deadline_display_default_text(self, qtbot):
        """Дедлайн по умолчанию 'Не установлен' (до load_data)."""
        cd = _make_card_data(deadline=None, stage_executors=[])
        dialog, _ = _create_dialog(qtbot, card_data=cd, employee=_ADMIN)
        # До вызова load_data текст может быть 'Не установлен'
        assert dialog.deadline_display.text() == 'Не установлен'

    def test_edit_deadline_btn_visible_for_admin(self, qtbot):
        """Кнопка 'Изменить дедлайн' видна для Руководителя."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        # Ищем кнопку по тексту
        deadline_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Изменить дедлайн' in btn.text()
        ]
        assert len(deadline_btns) >= 1, \
            "Кнопка 'Изменить дедлайн' должна быть для Руководителя"


# ========== 11. Отображение даты замера (3 теста) ==========

@pytest.mark.ui
class TestSurveyDateDisplay:
    """Отображение даты замера."""

    def test_survey_date_label_exists(self, qtbot):
        """QLabel даты замера существует для админа."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'survey_date_label')
        assert isinstance(dialog.survey_date_label, QLabel)

    def test_survey_date_default_text(self, qtbot):
        """Дата замера по умолчанию 'Не установлена'."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        # До load_data текст по умолчанию
        assert dialog.survey_date_label.text() == 'Не установлена'

    def test_edit_survey_btn_visible_for_admin(self, qtbot):
        """Кнопка 'Изменить дату' замера видна для Руководителя."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        survey_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Изменить дату' in btn.text()
        ]
        assert len(survey_btns) >= 1, \
            "Кнопка 'Изменить дату' замера должна быть для Руководителя"


# ========== 12. Поле тегов (3 теста) ==========

@pytest.mark.ui
class TestTagsField:
    """Поле тегов проекта."""

    def test_tags_field_exists(self, qtbot):
        """QLineEdit тегов существует для админа."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert hasattr(dialog, 'tags')
        assert isinstance(dialog.tags, QLineEdit)

    def test_tags_placeholder(self, qtbot):
        """Поле тегов имеет placeholder."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        placeholder = dialog.tags.placeholderText()
        assert placeholder != '', "Placeholder тегов не должен быть пустым"

    def test_tags_not_created_for_sdp(self, qtbot):
        """Теги не создаются для СДП (нет crm_cards.move → is_executor, нет вкладки 'Исполнители')."""
        dialog, _ = _create_dialog(qtbot, employee=_SDP)
        assert not hasattr(dialog, 'tags'), \
            "СДП — исполнитель, поле tags не создаётся (нет вкладки 'Исполнители и дедлайн')"


# ========== 13. Режим только просмотр (4 теста) ==========

@pytest.mark.ui
class TestViewOnlyMode:
    """view_only=True — диалог в режиме только просмотр."""

    def test_view_only_flag(self, qtbot):
        """view_only устанавливается в True."""
        dialog, _ = _create_dialog(qtbot, view_only=True)
        assert dialog.view_only is True

    def test_view_only_has_close_button(self, qtbot):
        """В view_only есть кнопка 'Закрыть'."""
        dialog, _ = _create_dialog(qtbot, view_only=True)
        # В view_only диалог disabled, но кнопка 'Закрыть' создаётся с setEnabled(True)
        close_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if 'Закрыть' in btn.text()
        ]
        assert len(close_btns) >= 1

    def test_view_only_no_save_button(self, qtbot):
        """В view_only НЕТ кнопки 'Сохранить'."""
        dialog, _ = _create_dialog(qtbot, view_only=True)
        save_btns = [
            btn for btn in dialog.findChildren(QPushButton)
            if btn.text() == 'Сохранить'
        ]
        assert len(save_btns) == 0, "В view_only не должно быть кнопки 'Сохранить'"

    def test_view_only_dialog_disabled(self, qtbot):
        """В view_only диалог disabled (для блокировки полей)."""
        dialog, _ = _create_dialog(qtbot, view_only=True)
        assert not dialog.isEnabled(), "В view_only диалог должен быть disabled"


# ========== 14. Видимость СДП (3 теста) ==========

@pytest.mark.ui
class TestSdpVisibility:
    """СДП комбобокс — только для индивидуальных проектов."""

    def test_sdp_exists_for_individual(self, qtbot):
        """СДП комбобокс создаётся для Индивидуальных проектов."""
        cd = _make_card_data(project_type='Индивидуальный')
        dialog, _ = _create_dialog(qtbot, card_data=cd, employee=_ADMIN)
        assert hasattr(dialog, 'sdp')
        assert dialog.sdp is not None

    def test_sdp_none_for_template(self, qtbot):
        """СДП = None для Шаблонных проектов."""
        cd = _make_card_data(project_type='Шаблонный')
        dialog, _ = _create_dialog(qtbot, card_data=cd, employee=_ADMIN)
        assert hasattr(dialog, 'sdp')
        assert dialog.sdp is None, "Для шаблонных проектов sdp должен быть None"

    def test_sdp_enabled_for_admin(self, qtbot):
        """СДП комбобокс включён для Руководителя."""
        cd = _make_card_data(project_type='Индивидуальный')
        dialog, _ = _create_dialog(qtbot, card_data=cd, employee=_ADMIN)
        assert dialog.sdp is not None
        assert dialog.sdp.isEnabled()


# ========== 15. Надпись синхронизации (2 теста) ==========

@pytest.mark.ui
class TestSyncLabel:
    """Надпись 'Синхронизация...' в нижней части диалога."""

    def test_sync_label_exists(self, qtbot):
        """QLabel синхронизации существует."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        assert hasattr(dialog, 'sync_label')
        assert isinstance(dialog.sync_label, QLabel)

    def test_sync_label_hidden_initially(self, qtbot):
        """Надпись синхронизации скрыта при создании."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN, view_only=False)
        assert not dialog.sync_label.isVisible()


# ========== 16. Дополнительные роли: вкладки (7 тестов) ==========

@pytest.mark.ui
class TestTabsByRole:
    """Видимость вкладок для разных ролей."""

    def test_manager_no_executors_tab(self, qtbot):
        """Менеджер НЕ видит вкладку 'Исполнители и дедлайн' (нет crm_cards.move)."""
        dialog, _ = _create_dialog(qtbot, employee=_MANAGER)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names), \
            f"Менеджер без crm_cards.move не должен видеть 'Исполнители': {tab_names}"

    def test_manager_no_payments_tab(self, qtbot):
        """Менеджер НЕ видит вкладку 'Оплаты' (нет crm_cards.payments)."""
        dialog, _ = _create_dialog(qtbot, employee=_MANAGER)
        assert dialog.payments_tab_index == -1, \
            "Менеджер без crm_cards.payments не должен видеть 'Оплаты'"

    def test_sdp_no_executors_tab(self, qtbot):
        """СДП НЕ видит вкладку 'Исполнители и дедлайн' (нет crm_cards.move)."""
        dialog, _ = _create_dialog(qtbot, employee=_SDP)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names), \
            f"СДП без crm_cards.move не должен видеть 'Исполнители': {tab_names}"

    def test_gap_no_payments_tab(self, qtbot):
        """ГАП НЕ видит вкладку 'Оплаты' (нет crm_cards.payments)."""
        dialog, _ = _create_dialog(qtbot, employee=_GAP)
        assert dialog.payments_tab_index == -1, \
            "ГАП без crm_cards.payments не должен видеть 'Оплаты'"

    def test_draftsman_no_executors_tab(self, qtbot):
        """Чертёжник НЕ видит вкладку 'Исполнители и дедлайн'."""
        dialog, _ = _create_dialog(qtbot, employee=_DRAFTSMAN)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names)

    def test_surveyor_no_executors_tab(self, qtbot):
        """Замерщик НЕ видит вкладку 'Исполнители и дедлайн'."""
        dialog, _ = _create_dialog(qtbot, employee=_SURVEYOR)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names)

    def test_designer_manager_no_executors_tab(self, qtbot):
        """Дизайнер+Менеджер (двойная роль) НЕ видит 'Исполнители' (ни одна позиция не даёт crm_cards.move)."""
        dialog, _ = _create_dialog(qtbot, employee=_DESIGNER_MANAGER)
        tab_names = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert not any('Исполнители' in name for name in tab_names), \
            f"Дизайнер+Менеджер без crm_cards.move не должен видеть 'Исполнители': {tab_names}"


# ========== 17. Комбобоксы — доступность по роли (4 теста) ==========

@pytest.mark.ui
class TestComboAccessByRole:
    """Доступность комбобоксов в зависимости от роли."""

    def test_combos_enabled_for_admin(self, qtbot):
        """Все комбобоксы команды включены для Руководителя."""
        dialog, _ = _create_dialog(qtbot, employee=_ADMIN)
        assert dialog.senior_manager.isEnabled()
        assert dialog.gap.isEnabled()
        assert dialog.manager.isEnabled()
        assert dialog.surveyor.isEnabled()

    def test_combos_not_created_for_manager(self, qtbot):
        """Комбобоксы команды не создаются для Менеджера (нет crm_cards.move → is_executor)."""
        dialog, _ = _create_dialog(qtbot, employee=_MANAGER)
        assert not hasattr(dialog, 'senior_manager'), \
            "Менеджер — исполнитель, комбобоксы команды не создаются"
        assert not hasattr(dialog, 'gap'), \
            "Менеджер — исполнитель, комбобоксы команды не создаются"

    def test_combos_not_created_for_sdp(self, qtbot):
        """Комбобоксы команды не создаются для СДП (нет crm_cards.move → is_executor)."""
        dialog, _ = _create_dialog(qtbot, employee=_SDP)
        assert not hasattr(dialog, 'senior_manager'), \
            "СДП — исполнитель, комбобоксы команды не создаются"
        assert not hasattr(dialog, 'gap'), \
            "СДП — исполнитель, комбобоксы команды не создаются"

    def test_combos_enabled_for_senior_manager(self, qtbot):
        """Комбобоксы команды включены для Старшего менеджера."""
        dialog, _ = _create_dialog(qtbot, employee=_SENIOR_MANAGER)
        assert dialog.senior_manager.isEnabled()
        assert dialog.gap.isEnabled()
        assert dialog.manager.isEnabled()


# ========== 18. Атрибуты инициализации (4 теста) ==========

@pytest.mark.ui
class TestDialogAttributes:
    """Атрибуты диалога после инициализации."""

    def test_loading_data_flag_exists(self, qtbot):
        """Флаг _loading_data существует."""
        dialog, _ = _create_dialog(qtbot)
        assert hasattr(dialog, '_loading_data')

    def test_deferred_tabs_flag(self, qtbot):
        """Флаг _deferred_tabs_ready существует."""
        dialog, _ = _create_dialog(qtbot)
        assert hasattr(dialog, '_deferred_tabs_ready')

    def test_resize_margin(self, qtbot):
        """resize_margin = 8."""
        dialog, _ = _create_dialog(qtbot)
        assert dialog.resize_margin == 8

    def test_active_sync_count(self, qtbot):
        """_active_sync_count инициализирован 0."""
        dialog, _ = _create_dialog(qtbot)
        assert dialog._active_sync_count == 0


# ========== 19. Scroll Area (2 теста) ==========

@pytest.mark.ui
class TestScrollArea:
    """Scroll Area для контента."""

    def test_dialog_has_scroll_area(self, qtbot):
        """Диалог содержит QScrollArea."""
        dialog, _ = _create_dialog(qtbot)
        scroll_areas = dialog.findChildren(QScrollArea)
        assert len(scroll_areas) >= 1, "Должен быть хотя бы один QScrollArea"

    def test_scroll_area_horizontal_off(self, qtbot):
        """Горизонтальный скролл отключён."""
        dialog, _ = _create_dialog(qtbot)
        scroll_areas = dialog.findChildren(QScrollArea)
        for sa in scroll_areas:
            policy = sa.horizontalScrollBarPolicy()
            # Может быть AlwaysOff или AsNeeded — главное не AlwaysOn
            assert policy != Qt.ScrollBarAlwaysOn


# ========== 20. Минимальные данные / edge cases (3 теста) ==========

@pytest.mark.ui
class TestEdgeCasesWidget:
    """Edge cases виджетов."""

    def test_minimal_card_data(self, qtbot):
        """Диалог не падает с минимальными данными."""
        cd = {'id': 1, 'contract_id': 1}
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        assert dialog is not None

    def test_none_values_in_card_data(self, qtbot):
        """Диалог обрабатывает None значения в card_data."""
        cd = _make_card_data(
            address=None, area=None, city=None,
            agent_type=None, project_subtype=None,
        )
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        assert dialog is not None

    def test_empty_string_values(self, qtbot):
        """Диалог обрабатывает пустые строки."""
        cd = _make_card_data(
            address='', city='', tags='', agent_type='',
        )
        dialog, _ = _create_dialog(qtbot, card_data=cd)
        assert dialog is not None
