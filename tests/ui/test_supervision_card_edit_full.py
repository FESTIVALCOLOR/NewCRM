# -*- coding: utf-8 -*-
"""
Тесты для ui/supervision_card_edit_dialog.py — диалог редактирования карточки надзора.

Покрытие:
- Конструктор, init_ui, вкладки
- load_data, save_changes, auto_save_field
- Кнопки чата, скриптов
- Файлы надзора, комментарии
- Статусы (пауза/возобновление)
- Расчёты стоимости, оплаты
- Resize, mouse events
- Создание history widget
- delete_order
- on_employee_changed
- reassign_dan
- Различные роли (менеджер, ДАН, руководитель)
"""

import pytest
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
pytest.importorskip("PyQt5")

from PyQt5.QtWidgets import (QApplication, QTabWidget, QLabel, QPushButton,
                              QLineEdit, QDialog, QFrame, QComboBox, QTableWidget)
from PyQt5.QtCore import Qt, QDate, QPoint, QSize
from PyQt5.QtGui import QIcon
from unittest.mock import patch, MagicMock, PropertyMock, call


# ========== Вспомогательные функции ==========

class _FakeIconLoader:
    """Fake IconLoader — возвращает реальные Qt-объекты, без MagicMock."""
    @staticmethod
    def load(*args, **kwargs):
        return QIcon()
    @staticmethod
    def load_colored(*args, **kwargs):
        return QIcon()
    @staticmethod
    def create_action_button(*args, **kwargs):
        return QPushButton()
    @staticmethod
    def create_icon_button(*args, **kwargs):
        return QPushButton()
    @staticmethod
    def get_icon(*args, **kwargs):
        return QIcon()
    @staticmethod
    def get_icon_path(*args, **kwargs):
        return ''


def _make_mock_data_access():
    """Создать MagicMock DataAccess для SupervisionCardEditDialog."""
    mock_da = MagicMock()
    mock_da.get_employees_by_position.return_value = [
        {'id': 10, 'full_name': 'СМП Тестов'},
        {'id': 11, 'full_name': 'СМП Другой'},
    ]
    mock_da.get_supervision_history.return_value = []
    mock_da.get_supervision_timeline.return_value = []
    mock_da.get_payments_for_supervision.return_value = []
    mock_da.get_submitted_stages.return_value = []
    mock_da.get_stage_history.return_value = []
    mock_da.get_payment.return_value = None
    mock_da.get_contract.return_value = {'yandex_folder_path': '/test/path'}
    mock_da.get_supervision_chat.return_value = None
    mock_da.get_payments_by_supervision_card.return_value = []
    mock_da.calculate_payment_amount.return_value = 5000
    mock_da.execute_raw_query.return_value = []
    mock_da.db = MagicMock()
    mock_da.is_online = False
    mock_da.is_multi_user = False
    mock_da.api_client = None
    mock_da.prefer_local = False
    return mock_da


SAMPLE_CARD_DATA = {
    'id': 1, 'contract_id': 100,
    'contract_number': 'АН-12345/26',
    'client_name': 'Иванов И.И.',
    'address': 'ул. Тестовая, д.1',
    'city': 'СПБ', 'area': 85.5,
    'column_name': 'Новый заказ',
    'dan_id': 9, 'dan_name': 'ДАН Тестов',
    'senior_manager_id': 10, 'senior_manager_name': 'СМП Тестов',
    'agent_type': '', 'status': 'active',
    'start_date': '2026-01-15',
    'deadline': '2026-03-15',
    'tags': 'VIP',
    'is_paused': False,
    'pause_reason': None,
    'paused_at': None,
    'created_at': '2026-01-15',
    'yandex_folder_path': '/test/path',
}

SAMPLE_CARD_PAUSED = {
    **SAMPLE_CARD_DATA,
    'is_paused': True,
    'pause_reason': 'Ждём материалы',
    'paused_at': '2026-02-01',
}


def _create_dialog(qtbot, employee, card_data=None, mock_da=None):
    """Создать SupervisionCardEditDialog с замоканными зависимостями."""
    if card_data is None:
        card_data = dict(SAMPLE_CARD_DATA)
    if mock_da is None:
        mock_da = _make_mock_data_access()

    parent_widget = MagicMock()
    parent_widget.data = mock_da

    with patch('ui.supervision_card_edit_dialog.DataAccess', return_value=mock_da), \
         patch('ui.supervision_card_edit_dialog.IconLoader', _FakeIconLoader), \
         patch('ui.supervision_card_edit_dialog.YandexDiskManager'), \
         patch('ui.supervision_card_edit_dialog.YANDEX_DISK_TOKEN', 'fake_token'), \
         patch('ui.supervision_card_edit_dialog.CustomTitleBar', return_value=QLabel('Title')), \
         patch('ui.supervision_card_edit_dialog.CustomComboBox', QComboBox), \
         patch('ui.supervision_card_edit_dialog.CustomDateEdit') as MockDateEdit, \
         patch('ui.supervision_card_edit_dialog._has_perm', side_effect=lambda emp, api, perm: perm != 'supervision.move' or emp.get('position', '') not in ('ДАН', 'Дизайнер', 'Чертёжник', 'Замерщик', 'Менеджер')), \
         patch('ui.supervision_card_edit_dialog.add_today_button_to_dateedit'), \
         patch('ui.supervision_card_edit_dialog.create_progress_dialog', return_value=MagicMock()):

        # CustomDateEdit -> реальный QDateEdit для тестирования
        from PyQt5.QtWidgets import QDateEdit
        MockDateEdit.side_effect = lambda *a, **k: QDateEdit()

        from ui.supervision_card_edit_dialog import SupervisionCardEditDialog
        dialog = SupervisionCardEditDialog(
            parent=None,
            card_data=card_data,
            employee=employee,
            api_client=None
        )
        qtbot.addWidget(dialog)
        return dialog, mock_da


# ========== Тестовые классы ==========


class TestSupervisionCardEditDialogCreation:
    """Тесты создания и инициализации диалога."""

    def test_create_dialog_admin(self, qtbot, mock_employee_admin):
        """Диалог создаётся для администратора."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog is not None

    def test_create_dialog_senior_manager(self, qtbot, mock_employee_senior_manager):
        """Диалог создаётся для старшего менеджера."""
        dialog, _ = _create_dialog(qtbot, mock_employee_senior_manager)
        assert dialog is not None

    def test_create_dialog_dan(self, qtbot, mock_employee_dan):
        """Диалог создаётся для ДАН (read-only)."""
        dialog, _ = _create_dialog(qtbot, mock_employee_dan)
        assert dialog is not None

    def test_card_data_stored(self, qtbot, mock_employee_admin):
        """card_data сохраняется."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.card_data['id'] == 1
        assert dialog.card_data['contract_number'] == 'АН-12345/26'

    def test_employee_stored(self, qtbot, mock_employee_admin):
        """employee сохраняется."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.employee == mock_employee_admin

    def test_is_dan_role_false_for_admin(self, qtbot, mock_employee_admin):
        """Администратор не является ДАН."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.is_dan_role is False

    def test_is_dan_role_true(self, qtbot, mock_employee_dan):
        """ДАН определяется корректно."""
        dialog, _ = _create_dialog(qtbot, mock_employee_dan)
        assert dialog.is_dan_role is True

    def test_is_dan_role_secondary(self, qtbot):
        """ДАН как вторичная должность определяется."""
        employee = {
            'id': 20, 'full_name': 'Тест',
            'position': 'Дизайнер', 'secondary_position': 'ДАН',
            'login': 'test', 'status': 'активный'
        }
        dialog, _ = _create_dialog(qtbot, employee)
        assert dialog.is_dan_role is True

    def test_frameless_window(self, qtbot, mock_employee_admin):
        """Окно без рамки."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.windowFlags() & Qt.FramelessWindowHint

    def test_resize_initial_state(self, qtbot, mock_employee_admin):
        """Начальное состояние resize."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.resizing is False
        assert dialog.resize_edge is None


class TestSupervisionCardEditDialogTabs:
    """Тесты вкладок диалога."""

    def test_has_tabs_widget(self, qtbot, mock_employee_admin):
        """Диалог содержит QTabWidget."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert hasattr(dialog, 'tabs')
        assert isinstance(dialog.tabs, QTabWidget)

    def test_admin_has_edit_tab(self, qtbot, mock_employee_admin):
        """Администратор видит вкладку Редактирование."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        tab_texts = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert 'Редактирование' in tab_texts

    def test_dan_no_edit_tab(self, qtbot, mock_employee_dan):
        """ДАН не видит вкладку Редактирование."""
        dialog, _ = _create_dialog(qtbot, mock_employee_dan)
        tab_texts = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert 'Редактирование' not in tab_texts

    def test_timeline_tab_present(self, qtbot, mock_employee_admin):
        """Вкладка 'Таблица сроков' присутствует."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        tab_texts = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert 'Таблица сроков' in tab_texts

    def test_payments_tab_present(self, qtbot, mock_employee_admin):
        """Вкладка 'Оплаты надзора' присутствует."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        tab_texts = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert 'Оплаты надзора' in tab_texts

    def test_project_info_tab_present(self, qtbot, mock_employee_admin):
        """Вкладка 'Информация о проекте' присутствует."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        tab_texts = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert 'Информация о проекте' in tab_texts

    def test_visits_tab_present(self, qtbot, mock_employee_admin):
        """Вкладка 'Таблица выездов и дефектов' присутствует."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        tab_texts = [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())]
        assert 'Таблица выездов и дефектов' in tab_texts

    def test_admin_tab_count(self, qtbot, mock_employee_admin):
        """Администратор видит 5 вкладок (Редактирование + 4 отложенных)."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.tabs.count() == 5

    def test_dan_tab_count(self, qtbot, mock_employee_dan):
        """ДАН видит 4 вкладки (без Редактирования)."""
        dialog, _ = _create_dialog(qtbot, mock_employee_dan)
        assert dialog.tabs.count() == 4


class TestSupervisionCardEditLoadData:
    """Тесты загрузки данных."""

    def test_load_data_sets_tags(self, qtbot, mock_employee_admin):
        """load_data устанавливает теги."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.tags.text() == 'VIP'

    def test_load_data_skip_for_dan(self, qtbot, mock_employee_dan):
        """load_data пропускается для ДАН."""
        dialog, _ = _create_dialog(qtbot, mock_employee_dan)
        # Для ДАН нет вкладки редактирования и полей
        assert dialog.is_dan_role is True

    def test_load_data_sets_start_date(self, qtbot, mock_employee_admin):
        """load_data устанавливает дату начала."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        date = dialog.start_date_edit.date()
        assert date.toString('yyyy-MM-dd') == '2026-01-15'

    def test_load_data_sets_deadline_label(self, qtbot, mock_employee_admin):
        """load_data устанавливает текст дедлайна."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.deadline_label.text() == '15.03.2026'

    def test_load_data_no_deadline(self, qtbot, mock_employee_admin):
        """load_data без дедлайна показывает 'Не установлен'."""
        card = dict(SAMPLE_CARD_DATA)
        card['deadline'] = None
        dialog, _ = _create_dialog(qtbot, mock_employee_admin, card_data=card)
        assert dialog.deadline_label.text() == 'Не установлен'

    def test_load_data_handles_datetime_format(self, qtbot, mock_employee_admin):
        """load_data обрабатывает формат с T-разделителем."""
        card = dict(SAMPLE_CARD_DATA)
        card['start_date'] = '2026-01-15T10:30:00'
        dialog, _ = _create_dialog(qtbot, mock_employee_admin, card_data=card)
        date = dialog.start_date_edit.date()
        assert date.toString('yyyy-MM-dd') == '2026-01-15'

    def test_loading_data_flag(self, qtbot, mock_employee_admin):
        """Флаг _loading_data сбрасывается после загрузки."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog._loading_data is False


class TestSupervisionCardEditSaveChanges:
    """Тесты сохранения данных."""

    def test_save_changes_calls_update(self, qtbot, mock_employee_admin):
        """save_changes вызывает data.update_supervision_card."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        with patch.object(dialog, 'accept'), \
             patch.object(dialog, 'refresh_payments_tab'), \
             patch.object(dialog, 'refresh_project_info_tab'), \
             patch('ui.supervision_card_edit_dialog.CRMSupervisionTab', create=True):
            dialog.save_changes()
            mock_da.update_supervision_card.assert_called_once()

    def test_save_changes_skip_for_dan(self, qtbot, mock_employee_dan):
        """save_changes ничего не делает для ДАН."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_dan)
        dialog.save_changes()
        mock_da.update_supervision_card.assert_not_called()

    def test_save_changes_passes_correct_data(self, qtbot, mock_employee_admin):
        """save_changes передаёт правильные поля."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        dialog.tags.setText('Новый тег')
        with patch.object(dialog, 'accept'), \
             patch.object(dialog, 'refresh_payments_tab'), \
             patch.object(dialog, 'refresh_project_info_tab'), \
             patch('ui.supervision_card_edit_dialog.CRMSupervisionTab', create=True):
            dialog.save_changes()
            args = mock_da.update_supervision_card.call_args
            assert args[0][0] == 1  # card id
            updates = args[0][1]
            assert updates['tags'] == 'Новый тег'


class TestSupervisionCardEditAutoSave:
    """Тесты автосохранения."""

    def test_auto_save_skips_during_loading(self, qtbot, mock_employee_admin):
        """auto_save_field не сохраняет во время загрузки."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        dialog._loading_data = True
        mock_da.reset_mock()
        dialog.auto_save_field()
        mock_da.update_supervision_card.assert_not_called()

    def test_auto_save_calls_update(self, qtbot, mock_employee_admin):
        """auto_save_field вызывает update_supervision_card."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        dialog._loading_data = False
        mock_da.reset_mock()
        dialog.auto_save_field()
        mock_da.update_supervision_card.assert_called_once()


class TestSupervisionCardEditChatButtons:
    """Тесты кнопок чата."""

    def test_chat_buttons_exist(self, qtbot, mock_employee_admin):
        """Кнопки чата существуют."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert hasattr(dialog, 'sv_create_chat_btn')
        assert hasattr(dialog, 'sv_open_chat_btn')
        assert hasattr(dialog, 'sv_delete_chat_btn')

    def test_script_buttons_exist(self, qtbot, mock_employee_admin):
        """Кнопки скриптов существуют."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert hasattr(dialog, 'sv_start_script_btn')
        assert hasattr(dialog, 'sv_end_script_btn')

    def test_chat_buttons_initial_state_offline(self, qtbot, mock_employee_admin):
        """Кнопки чата отключены в offline режиме."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog._update_supervision_chat_buttons()
        assert not dialog.sv_create_chat_btn.isEnabled()

    def test_update_chat_buttons_with_chat(self, qtbot, mock_employee_admin):
        """При наличии чата: открыть/удалить включены, создать отключён."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.data.is_multi_user = True
        dialog._sv_chat_data = {'chat': {'is_active': True, 'id': 1}}
        dialog._update_supervision_chat_buttons()
        assert not dialog.sv_create_chat_btn.isEnabled()
        assert dialog.sv_open_chat_btn.isEnabled()
        assert dialog.sv_delete_chat_btn.isEnabled()

    def test_update_chat_buttons_no_chat_online(self, qtbot, mock_employee_admin):
        """Без чата онлайн: создать включён, остальные отключены."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.data.is_multi_user = True
        dialog._sv_chat_data = None
        dialog._update_supervision_chat_buttons()
        assert dialog.sv_create_chat_btn.isEnabled()
        assert not dialog.sv_open_chat_btn.isEnabled()
        assert not dialog.sv_delete_chat_btn.isEnabled()


class TestSupervisionCardEditOpenChat:
    """Тесты открытия чата."""

    def test_open_chat_no_data(self, qtbot, mock_employee_admin):
        """Открытие чата без данных — ничего не происходит."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog._sv_chat_data = None
        dialog._on_open_supervision_chat()  # не падает

    def test_open_chat_no_link(self, qtbot, mock_employee_admin):
        """Открытие чата без ссылки — предупреждение."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog._sv_chat_data = {'chat': {'invite_link': ''}}
        with patch('ui.supervision_card_edit_dialog.CustomMessageBox') as MockMsgBox:
            mock_instance = MagicMock()
            MockMsgBox.return_value = mock_instance
            dialog._on_open_supervision_chat()
            MockMsgBox.assert_called_once()


class TestSupervisionCardEditScripts:
    """Тесты отправки скриптов."""

    def test_send_start_script_no_id(self, qtbot, mock_employee_admin):
        """Отправка начального скрипта без ID — ничего не происходит."""
        card = dict(SAMPLE_CARD_DATA)
        card['id'] = None
        dialog, _ = _create_dialog(qtbot, mock_employee_admin, card_data=card)
        dialog._on_send_supervision_start_script()  # не падает

    def test_send_end_script_no_id(self, qtbot, mock_employee_admin):
        """Отправка завершающего скрипта без ID — ничего не происходит."""
        card = dict(SAMPLE_CARD_DATA)
        card['id'] = None
        dialog, _ = _create_dialog(qtbot, mock_employee_admin, card_data=card)
        dialog._on_send_supervision_end_script()  # не падает

    def test_send_start_script_success(self, qtbot, mock_employee_admin):
        """Отправка начального скрипта — успех."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.trigger_script.return_value = True
        with patch('ui.supervision_card_edit_dialog.CustomMessageBox') as MockMsgBox:
            mock_instance = MagicMock()
            MockMsgBox.return_value = mock_instance
            dialog._on_send_supervision_start_script()
            mock_da.trigger_script.assert_called_once_with(1, 'supervision_start', entity_type='supervision')


class TestSupervisionCardEditDeleteOrder:
    """Тесты удаления заказа."""

    def test_delete_order_requires_confirmation(self, qtbot, mock_employee_admin):
        """delete_order показывает диалог подтверждения."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        with patch('ui.supervision_card_edit_dialog.CustomQuestionBox') as MockQBox:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            MockQBox.return_value = mock_instance
            dialog.delete_order()
            MockQBox.assert_called_once()


class TestSupervisionCardEditPauseResume:
    """Тесты приостановки и возобновления."""

    def test_pause_button_text_active(self, qtbot, mock_employee_admin):
        """Для активной карточки — кнопка 'Приостановить'."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.pause_btn.text() == 'Приостановить'

    def test_pause_button_text_paused(self, qtbot, mock_employee_admin):
        """Для приостановленной карточки — кнопка 'Возобновить'."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin, card_data=dict(SAMPLE_CARD_PAUSED))
        assert dialog.pause_btn.text() == 'Возобновить'


class TestSupervisionCardEditHistory:
    """Тесты создания виджета истории."""

    def test_create_history_widget_empty(self, qtbot, mock_employee_admin):
        """create_history_widget при пустой истории показывает сообщение."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_supervision_history.return_value = []
        widget = dialog.create_history_widget()
        assert widget is not None

    def test_create_history_widget_with_entries(self, qtbot, mock_employee_admin):
        """create_history_widget с записями создаёт виджеты."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_supervision_history.return_value = [
            {'id': 1, 'entry_type': 'note', 'created_at': '2026-01-15',
             'created_by_name': 'Тест', 'message': 'Тестовая запись'},
        ]
        widget = dialog.create_history_widget()
        assert widget is not None

    def test_create_history_entry_widget_note(self, qtbot, mock_employee_admin):
        """create_history_entry_widget для типа note."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        entry = {'entry_type': 'note', 'created_at': '2026-01-15',
                 'created_by_name': 'Тест', 'message': 'Тестовая запись'}
        widget = dialog.create_history_entry_widget(entry)
        assert isinstance(widget, QFrame)

    def test_create_history_entry_widget_pause(self, qtbot, mock_employee_admin):
        """create_history_entry_widget для типа pause (жёлтый фон)."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        entry = {'entry_type': 'pause', 'created_at': '2026-02-01',
                 'created_by_name': 'Тест', 'message': 'Пауза'}
        widget = dialog.create_history_entry_widget(entry)
        assert isinstance(widget, QFrame)

    def test_create_history_entry_widget_resume(self, qtbot, mock_employee_admin):
        """create_history_entry_widget для типа resume."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        entry = {'entry_type': 'resume', 'created_at': '2026-02-10',
                 'created_by_name': 'Тест', 'message': 'Возобновление'}
        widget = dialog.create_history_entry_widget(entry)
        assert isinstance(widget, QFrame)

    def test_create_history_entry_widget_submitted(self, qtbot, mock_employee_admin):
        """create_history_entry_widget для типа submitted."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        entry = {'entry_type': 'submitted', 'created_at': '2026-02-05',
                 'created_by_name': 'Тест', 'message': 'Стадия сдана'}
        widget = dialog.create_history_entry_widget(entry)
        assert isinstance(widget, QFrame)

    def test_create_history_entry_widget_accepted(self, qtbot, mock_employee_admin):
        """create_history_entry_widget для типа accepted."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        entry = {'entry_type': 'accepted', 'created_at': '2026-02-06',
                 'created_by_name': 'Тест', 'message': 'Стадия принята'}
        widget = dialog.create_history_entry_widget(entry)
        assert isinstance(widget, QFrame)

    def test_reload_history_empty(self, qtbot, mock_employee_admin):
        """reload_history при пустой истории — метод существует."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        assert hasattr(dialog, 'reload_history')


class TestSupervisionCardEditPayments:
    """Тесты виджета оплат."""

    def test_create_payments_widget_empty(self, qtbot, mock_employee_admin):
        """create_payments_widget без оплат."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_payments_for_supervision.return_value = []
        widget = dialog.create_payments_widget()
        assert widget is not None

    def test_create_payments_widget_with_data(self, qtbot, mock_employee_admin):
        """create_payments_widget с оплатами."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_payments_for_supervision.return_value = [
            {'id': 1, 'role': 'Старший менеджер проектов', 'employee_name': 'СМП Тестов',
             'stage_name': '', 'payment_type': 'Полная оплата',
             'final_amount': 5000, 'report_month': '2026-02',
             'payment_status': 'to_pay', 'reassigned': False},
        ]
        widget = dialog.create_payments_widget()
        assert widget is not None

    def test_create_payments_widget_with_reassigned(self, qtbot, mock_employee_admin):
        """create_payments_widget с переназначенными оплатами."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_payments_for_supervision.return_value = [
            {'id': 1, 'role': 'ДАН', 'employee_name': 'ДАН Тестов',
             'stage_name': '', 'payment_type': 'Полная оплата',
             'final_amount': 3000, 'report_month': '2026-01',
             'payment_status': 'paid', 'reassigned': True,
             'old_employee_id': 99},
        ]
        mock_da.get_employee.return_value = {'full_name': 'Старый ДАН'}
        widget = dialog.create_payments_widget()
        assert widget is not None

    def test_refresh_payment_tab(self, qtbot, mock_employee_admin):
        """refresh_payment_tab не падает."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_payments_for_supervision.return_value = []
        dialog.refresh_payment_tab()


class TestSupervisionCardEditProjectInfo:
    """Тесты виджета информации о проекте."""

    def test_create_project_info_widget_empty(self, qtbot, mock_employee_admin):
        """create_project_info_widget без данных."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_submitted_stages.return_value = []
        mock_da.get_stage_history.return_value = []
        mock_da.execute_raw_query.return_value = []
        widget = dialog.create_project_info_widget()
        assert widget is not None

    def test_create_project_info_widget_with_stages(self, qtbot, mock_employee_admin):
        """create_project_info_widget с стадиями."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_submitted_stages.return_value = [
            {'stage_name': 'Стадия 1', 'executor_name': 'Тест', 'submitted_date': '2026-02-01'},
        ]
        mock_da.get_stage_history.return_value = [
            {'stage_name': 'Стадия 1', 'executor_name': 'Тест', 'assigned_date': '2026-01-20',
             'deadline': '2026-02-20', 'completed': False, 'submitted_date': '2026-02-01'},
        ]
        mock_da.execute_raw_query.return_value = []
        widget = dialog.create_project_info_widget()
        assert widget is not None

    def test_create_stage_info_widget_completed(self, qtbot, mock_employee_admin):
        """create_stage_info_widget для завершённой стадии."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        stage = {
            'stage_name': 'Стадия 1', 'executor_name': 'Тест',
            'assigned_date': '2026-01-20', 'deadline': '2026-02-20',
            'completed': True, 'submitted_date': '2026-02-01',
        }
        widget = dialog.create_stage_info_widget(stage)
        assert isinstance(widget, QFrame)

    def test_create_stage_info_widget_pending(self, qtbot, mock_employee_admin):
        """create_stage_info_widget для незавершённой стадии."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        stage = {
            'stage_name': 'Стадия 2', 'executor_name': 'Другой',
            'assigned_date': '2026-02-01', 'deadline': '2026-03-01',
            'completed': False,
        }
        widget = dialog.create_stage_info_widget(stage)
        assert isinstance(widget, QFrame)


class TestSupervisionCardEditResize:
    """Тесты изменения размера окна."""

    def test_get_resize_edge_left(self, qtbot, mock_employee_admin):
        """Определение левого края."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.resize(1200, 800)
        pos = QPoint(3, 400)
        assert dialog.get_resize_edge(pos) == 'left'

    def test_get_resize_edge_right(self, qtbot, mock_employee_admin):
        """Определение правого края."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.resize(1200, 800)
        pos = QPoint(1197, 400)
        assert dialog.get_resize_edge(pos) == 'right'

    def test_get_resize_edge_center(self, qtbot, mock_employee_admin):
        """Центр — нет края."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.resize(1200, 800)
        pos = QPoint(600, 400)
        assert dialog.get_resize_edge(pos) is None

    def test_set_cursor_shape_horizontal(self, qtbot, mock_employee_admin):
        """Курсор горизонтального изменения."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.set_cursor_shape('left')
        assert dialog.cursor().shape() == Qt.SizeHorCursor

    def test_set_cursor_shape_arrow(self, qtbot, mock_employee_admin):
        """Курсор-стрелка по умолчанию."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        dialog.set_cursor_shape(None)
        assert dialog.cursor().shape() == Qt.ArrowCursor


class TestSupervisionCardEditOnEmployeeChanged:
    """Тесты обработчика изменения сотрудника."""

    def test_skip_during_loading(self, qtbot, mock_employee_admin):
        """on_employee_changed не срабатывает во время загрузки."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        dialog._loading_data = True
        mock_da.reset_mock()
        combo = MagicMock()
        dialog.on_employee_changed(combo, 'ДАН')
        mock_da.update_supervision_card.assert_not_called()

    def test_skip_without_contract_id(self, qtbot, mock_employee_admin):
        """on_employee_changed без contract_id — ничего не делает."""
        card = dict(SAMPLE_CARD_DATA)
        card['contract_id'] = None
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin, card_data=card)
        dialog._loading_data = False
        mock_da.reset_mock()
        combo = MagicMock()
        combo.currentData.return_value = 10
        dialog.on_employee_changed(combo, 'ДАН')
        mock_da.update_supervision_card.assert_not_called()


class TestSupervisionCardEditSaveManualAmount:
    """Тесты save_manual_amount."""

    def test_save_manual_amount(self, qtbot, mock_employee_admin):
        """save_manual_amount обновляет платёж."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_dialog = MagicMock()
        mock_da.get_payments_for_supervision.return_value = []
        dialog.save_manual_amount(1, 15000.0, 2, 2026, mock_dialog)
        mock_da.update_payment.assert_called_once()
        args = mock_da.update_payment.call_args
        assert args[0][0] == 1
        update_data = args[0][1]
        assert update_data['manual_amount'] == 15000.0
        assert update_data['report_month'] == '2026-02'

    def test_save_manual_amount_closes_dialog(self, qtbot, mock_employee_admin):
        """save_manual_amount закрывает диалог."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_dialog = MagicMock()
        mock_da.get_payments_for_supervision.return_value = []
        dialog.save_manual_amount(1, 5000.0, 1, 2026, mock_dialog)
        mock_dialog.accept.assert_called_once()


class TestSupervisionCardEditDeletePayment:
    """Тесты удаления оплаты."""

    def test_delete_payment_calls_confirmation(self, qtbot, mock_employee_admin):
        """delete_payment показывает подтверждение."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        with patch('ui.supervision_card_edit_dialog.CustomQuestionBox') as MockQBox:
            mock_instance = MagicMock()
            mock_instance.exec_.return_value = QDialog.Rejected
            MockQBox.return_value = mock_instance
            dialog.delete_payment(1, 'ДАН', 'ДАН Тестов')
            MockQBox.assert_called_once()


class TestSupervisionCardEditDeferredTabs:
    """Тесты отложенной инициализации вкладок."""

    def test_deferred_tabs_not_ready_initially(self, qtbot, mock_employee_admin):
        """Отложенные вкладки не готовы при создании."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog._deferred_tabs_ready is False

    def test_sv_timeline_widget_initially_none(self, qtbot, mock_employee_admin):
        """sv_timeline_widget изначально None."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert dialog.sv_timeline_widget is None

    def test_sync_label_hidden(self, qtbot, mock_employee_admin):
        """Надпись синхронизации скрыта по умолчанию."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        assert not dialog.sync_label.isVisible()


class TestSupervisionCardEditContractFolder:
    """Тесты получения папки договора."""

    def test_get_contract_yandex_folder_no_id(self, qtbot, mock_employee_admin):
        """Без contract_id возвращает None."""
        dialog, _ = _create_dialog(qtbot, mock_employee_admin)
        result = dialog._get_contract_yandex_folder(None)
        assert result is None

    def test_get_contract_yandex_folder_with_id(self, qtbot, mock_employee_admin):
        """С contract_id возвращает путь."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_contract.return_value = {'yandex_folder_path': '/disk/test'}
        result = dialog._get_contract_yandex_folder(100)
        assert result == '/disk/test'

    def test_get_contract_yandex_folder_no_contract(self, qtbot, mock_employee_admin):
        """Если договор не найден — None."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_contract.return_value = None
        result = dialog._get_contract_yandex_folder(999)
        assert result is None

    def test_get_contract_yandex_folder_exception(self, qtbot, mock_employee_admin):
        """При исключении — None."""
        dialog, mock_da = _create_dialog(qtbot, mock_employee_admin)
        mock_da.get_contract.side_effect = Exception('Test error')
        result = dialog._get_contract_yandex_folder(100)
        assert result is None
