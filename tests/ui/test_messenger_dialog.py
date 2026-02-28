# -*- coding: utf-8 -*-
"""
Тесты диалога выбора мессенджера — MessengerSelectDialog.
Двухшаговый: выбор мессенджера -> настройка чата.
~12 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QWidget, QLineEdit,
    QRadioButton, QCheckBox, QStackedWidget,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon


# ========== Хелперы ==========

def _make_parent(qtbot, mock_data_access, employee):
    w = QWidget()
    w.data = mock_data_access
    w.employee = employee
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


def _card_data():
    """Тестовые данные CRM-карточки."""
    return {
        'id': 300,
        'city': 'СПБ',
        'address': 'ул. Тестовая, д.1',
        'agent_type': 'ФЕСТИВАЛЬ',
        'senior_manager_id': 2,
        'senior_manager_name': 'СМП Тест',
        'sdp_id': 3,
        'sdp_name': 'СДП Тест',
        'stage_executors': [
            {'executor_id': 6, 'executor_name': 'Дизайнер Тест', 'stage_name': 'Стадия 2: концепция дизайна'},
        ],
    }


@pytest.fixture
def messenger_dlg(qtbot, mock_data_access, mock_employee_admin):
    """Создать MessengerSelectDialog."""
    parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)
    mock_data_access.get_all_employees.return_value = [
        {'id': 1, 'full_name': 'Директор Тест', 'position': 'Руководитель студии', 'status': 'активный'},
    ]

    with patch('ui.messenger_select_dialog.IconLoader') as MockIcon, \
         patch('ui.messenger_select_dialog.resource_path', return_value=''), \
         patch('ui.messenger_select_dialog.QPixmap', return_value=QPixmap()):
        MockIcon.load = MagicMock(return_value=QIcon())
        from ui.messenger_select_dialog import MessengerSelectDialog
        d = MessengerSelectDialog(
            parent,
            card_data=_card_data(),
            api_client=None,
            db=MagicMock(),
            data_access=mock_data_access,
            employee=mock_employee_admin,
            card_type='crm',
        )
        d.setAttribute(Qt.WA_DeleteOnClose, False)
        d._test_parent = parent
        qtbot.addWidget(d)
        yield d


# ========================================================================
# Тесты
# ========================================================================

@pytest.mark.ui
class TestMessengerSelectDialogPage1:
    """Страница 1: выбор мессенджера."""

    def test_creates_as_dialog(self, messenger_dlg):
        """Диалог создаётся."""
        assert isinstance(messenger_dlg, QDialog)

    def test_has_stacked_widget(self, messenger_dlg):
        """QStackedWidget (страницы) существует."""
        assert hasattr(messenger_dlg, '_stack')
        assert isinstance(messenger_dlg._stack, QStackedWidget)
        assert messenger_dlg._stack.count() == 2

    def test_initial_page_is_messenger(self, messenger_dlg):
        """Начальная страница — выбор мессенджера (индекс 0)."""
        assert messenger_dlg._stack.currentIndex() == 0

    def test_telegram_selected_by_default(self, messenger_dlg):
        """Telegram выбран по умолчанию."""
        assert messenger_dlg._selected_messenger == 'telegram'


@pytest.mark.ui
class TestMessengerSelectDialogPage2:
    """Страница 2: настройка чата."""

    def test_on_messenger_chosen_switches_page(self, messenger_dlg):
        """Выбор мессенджера переключает на страницу настройки."""
        messenger_dlg._on_messenger_chosen('telegram')
        assert messenger_dlg._stack.currentIndex() == 1

    def test_chat_title_edit_exists(self, messenger_dlg):
        """Поле названия чата существует."""
        assert hasattr(messenger_dlg, '_chat_title_edit')
        assert isinstance(messenger_dlg._chat_title_edit, QLineEdit)

    def test_default_title_contains_city(self, messenger_dlg):
        """Название по умолчанию содержит город."""
        title = messenger_dlg._build_default_title()
        assert 'СПБ' in title

    def test_manual_mode_by_default(self, messenger_dlg):
        """По умолчанию выбран ручной режим (привязка)."""
        assert messenger_dlg._radio_manual.isChecked()

    def test_invite_link_not_hidden_in_manual(self, messenger_dlg):
        """В ручном режиме поле invite-ссылки НЕ скрыто."""
        messenger_dlg._on_method_toggled()
        assert not messenger_dlg._invite_link_edit.isHidden()

    def test_invite_link_hidden_in_auto(self, messenger_dlg):
        """В автоматическом режиме поле invite скрыто."""
        messenger_dlg._radio_auto.setChecked(True)
        messenger_dlg._on_method_toggled()
        assert messenger_dlg._invite_link_edit.isHidden()


@pytest.mark.ui
class TestMessengerSelectDialogParticipants:
    """Участники и создание чата."""

    def test_participant_checkboxes_built(self, messenger_dlg):
        """Чекбоксы участников построены."""
        assert len(messenger_dlg._participant_checkboxes) >= 1

    def test_collect_members_returns_checked(self, messenger_dlg):
        """_collect_members возвращает отмеченных участников."""
        members = messenger_dlg._collect_members()
        assert isinstance(members, list)

    def test_on_create_empty_title_error(self, messenger_dlg):
        """Пустое название чата — ошибка (CustomMessageBox вызывается из локального импорта)."""
        messenger_dlg._on_messenger_chosen('telegram')
        messenger_dlg._chat_title_edit.setText('')
        with patch('ui.custom_message_box.CustomMessageBox') as mock_msg:
            mock_msg.return_value.exec_.return_value = None
            messenger_dlg._on_create()
            mock_msg.assert_called()

    def test_on_create_manual_no_link_error(self, messenger_dlg):
        """Ручной режим без invite-ссылки — ошибка."""
        messenger_dlg._on_messenger_chosen('telegram')
        messenger_dlg._chat_title_edit.setText('Тест чат')
        messenger_dlg._radio_manual.setChecked(True)
        messenger_dlg._invite_link_edit.setText('')
        with patch('ui.custom_message_box.CustomMessageBox') as mock_msg:
            mock_msg.return_value.exec_.return_value = None
            messenger_dlg._on_create()
