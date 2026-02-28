# -*- coding: utf-8 -*-
"""
Глубокие тесты диалогов мессенджера:
  - MessengerAdminDialog  (ui/messenger_admin_dialog.py, 1526 строк)
  - MessengerSelectDialog (ui/messenger_select_dialog.py, 654 строки)
  - MessengerSettingsWidget (встраиваемый виджет)

~40 тестов: создание, стили, вкладки, валидация, MTProto, скрипты, SMTP, навигация.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from PyQt5.QtWidgets import (
    QDialog, QPushButton, QWidget, QLineEdit, QTabWidget,
    QRadioButton, QCheckBox, QStackedWidget, QListWidget,
    QTextEdit, QComboBox, QLabel, QSpinBox,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QIcon, QColor


# =====================================================================
# Хелперы
# =====================================================================

def _card_data_crm():
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
        'gap_id': 4,
        'gap_name': 'ГАП Тест',
        'manager_id': 5,
        'manager_name': 'Менеджер Тест',
        'stage_executors': [
            {'executor_id': 6, 'executor_name': 'Дизайнер Тест', 'stage_name': 'Стадия 2: концепция дизайна'},
            {'executor_id': 7, 'executor_name': 'Чертёжник Тест', 'stage_name': 'Стадия 3: рабочие чертежи'},
        ],
    }


def _card_data_supervision():
    """Тестовые данные карточки надзора."""
    return {
        'id': 400,
        'city': 'МСК',
        'address': 'пр. Надзорный, д.5',
        'agent_type': 'Петрович',
        'senior_manager_id': 2,
        'senior_manager_name': 'СМП Надзор',
        'dan_id': 9,
        'dan_name': 'ДАН Тест',
    }


def _make_parent(qtbot, mock_data_access, employee):
    """Создать родительский виджет с моковыми зависимостями."""
    w = QWidget()
    w.data = mock_data_access
    w.employee = employee
    w.db = mock_data_access.db
    w.api_client = None
    qtbot.addWidget(w)
    return w


# Общие патчи для MessengerAdminDialog
_ADMIN_PATCHES = {
    'icon_loader': 'ui.messenger_admin_dialog.IconLoader',
    'resource_path': 'ui.messenger_admin_dialog.resource_path',
    'custom_title_bar': 'ui.custom_title_bar.CustomTitleBar',
}

# Общие патчи для MessengerSelectDialog
_SELECT_PATCHES = {
    'icon_loader': 'ui.messenger_select_dialog.IconLoader',
    'resource_path': 'ui.messenger_select_dialog.resource_path',
    'qpixmap': 'ui.messenger_select_dialog.QPixmap',
}


# =====================================================================
# Фикстуры — MessengerAdminDialog
# =====================================================================

@pytest.fixture
def admin_dlg(qtbot, mock_data_access, mock_employee_admin):
    """Создать MessengerAdminDialog с полными моками."""
    mock_data_access.get_messenger_settings.return_value = [
        {'setting_key': 'telegram_bot_token', 'setting_value': 'test-token-123'},
        {'setting_key': 'telegram_api_id', 'setting_value': '12345678'},
        {'setting_key': 'telegram_api_hash', 'setting_value': 'abc123hash'},
        {'setting_key': 'telegram_phone', 'setting_value': '+79001234567'},
        {'setting_key': 'smtp_host', 'setting_value': 'smtp.test.ru'},
        {'setting_key': 'smtp_port', 'setting_value': '587'},
        {'setting_key': 'smtp_username', 'setting_value': 'user@test.ru'},
        {'setting_key': 'smtp_password', 'setting_value': 'secret123'},
        {'setting_key': 'smtp_use_tls', 'setting_value': 'true'},
        {'setting_key': 'smtp_from_name', 'setting_value': 'CRM Test'},
    ]
    mock_data_access.get_messenger_scripts.return_value = [
        {
            'id': 1, 'script_type': 'project_start',
            'message_template': 'Привет, {client_name}!',
            'is_enabled': True, 'use_auto_deadline': False,
            'stage_name': '', 'memo_file_path': None,
        },
        {
            'id': 2, 'script_type': 'stage_complete',
            'message_template': 'Этап {stage_name} завершён.',
            'is_enabled': False, 'use_auto_deadline': True,
            'stage_name': 'Стадия 1: планировочные решения',
            'memo_file_path': '/CRM/memo/memo.pdf',
        },
    ]
    mock_data_access.get_messenger_status.return_value = {
        'telegram_bot_available': True,
        'telegram_mtproto_available': False,
        'email_available': True,
    }
    mock_data_access.mtproto_session_status.return_value = {'valid': False}

    parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)

    with patch(_ADMIN_PATCHES['icon_loader']) as MockIcon, \
         patch(_ADMIN_PATCHES['resource_path'], return_value='/fake/path'):
        MockIcon.load = MagicMock(return_value=QIcon())
        from ui.messenger_admin_dialog import MessengerAdminDialog
        dlg = MessengerAdminDialog(
            parent,
            api_client=None,
            data_access=mock_data_access,
            employee=mock_employee_admin,
        )
        dlg.setAttribute(Qt.WA_DeleteOnClose, False)
        qtbot.addWidget(dlg)
        yield dlg


# =====================================================================
# Фикстуры — MessengerSelectDialog
# =====================================================================

@pytest.fixture
def select_dlg_crm(qtbot, mock_data_access, mock_employee_admin):
    """Создать MessengerSelectDialog для CRM-карточки."""
    mock_data_access.get_all_employees.return_value = [
        {'id': 1, 'full_name': 'Директор Тест', 'position': 'Руководитель студии', 'status': 'активный'},
    ]

    parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)

    with patch(_SELECT_PATCHES['icon_loader']) as MockIcon, \
         patch(_SELECT_PATCHES['resource_path'], return_value=''), \
         patch(_SELECT_PATCHES['qpixmap'], return_value=QPixmap()):
        MockIcon.load = MagicMock(return_value=QIcon())
        from ui.messenger_select_dialog import MessengerSelectDialog
        dlg = MessengerSelectDialog(
            parent,
            card_data=_card_data_crm(),
            api_client=None,
            db=MagicMock(),
            data_access=mock_data_access,
            employee=mock_employee_admin,
            card_type='crm',
        )
        dlg.setAttribute(Qt.WA_DeleteOnClose, False)
        qtbot.addWidget(dlg)
        yield dlg


@pytest.fixture
def select_dlg_supervision(qtbot, mock_data_access, mock_employee_admin):
    """Создать MessengerSelectDialog для карточки надзора."""
    mock_data_access.get_all_employees.return_value = [
        {'id': 1, 'full_name': 'Директор Надзор', 'position': 'Директор', 'status': 'активный'},
    ]

    parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)

    with patch(_SELECT_PATCHES['icon_loader']) as MockIcon, \
         patch(_SELECT_PATCHES['resource_path'], return_value=''), \
         patch(_SELECT_PATCHES['qpixmap'], return_value=QPixmap()):
        MockIcon.load = MagicMock(return_value=QIcon())
        from ui.messenger_select_dialog import MessengerSelectDialog
        dlg = MessengerSelectDialog(
            parent,
            card_data=_card_data_supervision(),
            api_client=None,
            db=MagicMock(),
            data_access=mock_data_access,
            employee=mock_employee_admin,
            card_type='supervision',
        )
        dlg.setAttribute(Qt.WA_DeleteOnClose, False)
        qtbot.addWidget(dlg)
        yield dlg


# =====================================================================
# Тесты: MessengerAdminDialog — создание и базовая структура
# =====================================================================

@pytest.mark.ui
class TestAdminDialogCreation:
    """Тесты создания и базовой структуры MessengerAdminDialog."""

    def test_creates_as_dialog(self, admin_dlg):
        """Диалог создаётся как QDialog."""
        assert isinstance(admin_dlg, QDialog)

    def test_has_frameless_window(self, admin_dlg):
        """Диалог использует FramelessWindowHint."""
        assert admin_dlg.windowFlags() & Qt.FramelessWindowHint

    def test_has_translucent_background(self, admin_dlg):
        """Диалог использует полупрозрачный фон."""
        assert admin_dlg.testAttribute(Qt.WA_TranslucentBackground)

    def test_minimum_size(self, admin_dlg):
        """Минимальный размер 680x560."""
        assert admin_dlg.minimumWidth() == 680
        assert admin_dlg.minimumHeight() == 560

    def test_maximum_size(self, admin_dlg):
        """Максимальный размер 780x700."""
        assert admin_dlg.maximumWidth() == 780
        assert admin_dlg.maximumHeight() == 700

    def test_has_tab_widget(self, admin_dlg):
        """QTabWidget с 3 вкладками."""
        assert hasattr(admin_dlg, '_tabs')
        assert isinstance(admin_dlg._tabs, QTabWidget)
        assert admin_dlg._tabs.count() == 3

    def test_tab_names(self, admin_dlg):
        """Названия вкладок: Telegram, Email (SMTP), Скрипты."""
        assert admin_dlg._tabs.tabText(0) == "Telegram"
        assert admin_dlg._tabs.tabText(1) == "Email (SMTP)"
        assert admin_dlg._tabs.tabText(2) == "Скрипты"


# =====================================================================
# Тесты: Вкладка Telegram
# =====================================================================

@pytest.mark.ui
class TestAdminTelegramTab:
    """Тесты вкладки Telegram."""

    def test_telegram_fields_exist(self, admin_dlg):
        """Поля Bot Token, API ID, API Hash, Телефон существуют."""
        assert hasattr(admin_dlg, '_tg_bot_token')
        assert hasattr(admin_dlg, '_tg_api_id')
        assert hasattr(admin_dlg, '_tg_api_hash')
        assert hasattr(admin_dlg, '_tg_phone')

    def test_telegram_settings_loaded(self, admin_dlg):
        """Настройки Telegram загружены из data_access."""
        assert admin_dlg._tg_bot_token.text() == 'test-token-123'
        assert admin_dlg._tg_api_id.text() == '12345678'
        assert admin_dlg._tg_api_hash.text() == 'abc123hash'
        assert admin_dlg._tg_phone.text() == '+79001234567'

    def test_bot_token_is_password_mode(self, admin_dlg):
        """Bot Token по умолчанию в режиме пароля (скрыт)."""
        assert admin_dlg._tg_bot_token.echoMode() == QLineEdit.Password

    def test_api_hash_is_password_mode(self, admin_dlg):
        """API Hash по умолчанию в режиме пароля (скрыт)."""
        assert admin_dlg._tg_api_hash.echoMode() == QLineEdit.Password

    def test_telegram_status_label(self, admin_dlg):
        """Статус Telegram отображается."""
        assert hasattr(admin_dlg, '_tg_status')
        text = admin_dlg._tg_status.text()
        assert 'Bot API' in text
        assert 'подключен' in text

    def test_mtproto_send_button_exists(self, admin_dlg):
        """Кнопка 'Запросить код' для MTProto существует."""
        assert hasattr(admin_dlg, '_mtproto_send_btn')
        assert isinstance(admin_dlg._mtproto_send_btn, QPushButton)
        assert admin_dlg._mtproto_send_btn.isEnabled()

    def test_mtproto_code_input_hidden_initially(self, admin_dlg):
        """Поле ввода кода MTProto скрыто по умолчанию."""
        assert not admin_dlg._mtproto_code_input.isVisible()

    def test_mtproto_verify_button_hidden_initially(self, admin_dlg):
        """Кнопка 'Подтвердить' скрыта по умолчанию."""
        assert not admin_dlg._mtproto_verify_btn.isVisible()


# =====================================================================
# Тесты: MTProto авторизация
# =====================================================================

@pytest.mark.ui
class TestAdminMTProto:
    """Тесты MTProto авторизации."""

    def test_send_code_success(self, admin_dlg):
        """Успешная отправка кода — показываются поля ввода."""
        admin_dlg.data_access.mtproto_send_code.return_value = {
            'status': 'code_sent', 'phone': '+79001234567',
        }
        admin_dlg._on_mtproto_send_code()
        # Поле ввода кода должно стать видимым (в offscreen — not isHidden)
        assert not admin_dlg._mtproto_code_input.isHidden()
        assert not admin_dlg._mtproto_verify_btn.isHidden()
        assert not admin_dlg._mtproto_sms_btn.isHidden()

    def test_send_code_error(self, admin_dlg):
        """Ошибка отправки кода — отображается сообщение об ошибке."""
        admin_dlg.data_access.mtproto_send_code.return_value = {
            'status': 'error', 'detail': 'Телефон не найден',
        }
        admin_dlg._on_mtproto_send_code()
        assert 'Телефон не найден' in admin_dlg._mtproto_session_label.text()
        assert admin_dlg._mtproto_send_btn.isEnabled()

    def test_send_code_exception(self, admin_dlg):
        """Исключение при отправке кода — обработка ошибки."""
        admin_dlg.data_access.mtproto_send_code.side_effect = Exception("Нет связи")
        admin_dlg._on_mtproto_send_code()
        assert 'Нет связи' in admin_dlg._mtproto_session_label.text()
        assert admin_dlg._mtproto_send_btn.isEnabled()

    def test_verify_code_empty(self, admin_dlg):
        """Верификация пустого кода — сообщение об ошибке."""
        admin_dlg._mtproto_code_input.setText("")
        admin_dlg._on_mtproto_verify_code()
        assert 'Введите код' in admin_dlg._mtproto_session_label.text()

    def test_verify_code_success(self, admin_dlg):
        """Успешная верификация кода — скрываются поля, обновляется статус."""
        admin_dlg._mtproto_code_input.setText("12345")
        admin_dlg._mtproto_code_input.setVisible(True)
        admin_dlg._mtproto_verify_btn.setVisible(True)
        admin_dlg._mtproto_sms_btn.setVisible(True)

        admin_dlg.data_access.mtproto_verify_code.return_value = {
            'status': 'success',
            'user': {'first_name': 'Иван', 'username': 'ivan_test'},
        }
        # Перезагрузка статуса после верификации
        admin_dlg.data_access.mtproto_session_status.return_value = {
            'valid': True, 'first_name': 'Иван', 'username': 'ivan_test',
        }

        admin_dlg._on_mtproto_verify_code()

        # После verify_code вызывается _load_status(), который обновляет label
        label_text = admin_dlg._mtproto_session_label.text()
        assert 'Сессия активна' in label_text or 'MTProto' in label_text
        assert admin_dlg._mtproto_code_input.isHidden()
        assert admin_dlg._mtproto_verify_btn.isHidden()

    def test_resend_sms_success(self, admin_dlg):
        """Успешная переотправка по SMS."""
        admin_dlg.data_access.mtproto_resend_sms.return_value = {
            'status': 'sms_sent', 'phone': '+79001234567',
        }
        admin_dlg._on_mtproto_resend_sms()
        assert 'SMS' in admin_dlg._mtproto_session_label.text()
        assert admin_dlg._mtproto_sms_btn.isEnabled()


# =====================================================================
# Тесты: Вкладка Email (SMTP)
# =====================================================================

@pytest.mark.ui
class TestAdminEmailTab:
    """Тесты вкладки Email (SMTP)."""

    def test_smtp_fields_exist(self, admin_dlg):
        """Поля SMTP существуют."""
        assert hasattr(admin_dlg, '_smtp_host')
        assert hasattr(admin_dlg, '_smtp_port')
        assert hasattr(admin_dlg, '_smtp_username')
        assert hasattr(admin_dlg, '_smtp_password')
        assert hasattr(admin_dlg, '_smtp_tls')
        assert hasattr(admin_dlg, '_smtp_from_name')

    def test_smtp_settings_loaded(self, admin_dlg):
        """Настройки SMTP загружены."""
        assert admin_dlg._smtp_host.text() == 'smtp.test.ru'
        assert admin_dlg._smtp_port.text() == '587'
        assert admin_dlg._smtp_username.text() == 'user@test.ru'
        assert admin_dlg._smtp_password.text() == 'secret123'
        assert admin_dlg._smtp_tls.isChecked() is True
        assert admin_dlg._smtp_from_name.text() == 'CRM Test'

    def test_smtp_password_is_password_mode(self, admin_dlg):
        """Пароль SMTP скрыт по умолчанию."""
        assert admin_dlg._smtp_password.echoMode() == QLineEdit.Password

    def test_email_status_label(self, admin_dlg):
        """Статус Email отображается."""
        text = admin_dlg._email_status.text()
        assert 'подключен' in text


# =====================================================================
# Тесты: Вкладка Скрипты
# =====================================================================

@pytest.mark.ui
class TestAdminScriptsTab:
    """Тесты вкладки Скрипты."""

    def test_script_list_exists(self, admin_dlg):
        """Список скриптов существует и содержит загруженные скрипты."""
        assert hasattr(admin_dlg, '_script_list')
        assert isinstance(admin_dlg._script_list, QListWidget)
        assert admin_dlg._script_list.count() == 2

    def test_script_list_displays_types(self, admin_dlg):
        """Скрипты отображаются с правильными типами."""
        item0 = admin_dlg._script_list.item(0).text()
        item1 = admin_dlg._script_list.item(1).text()
        # Первый скрипт — "Начало проекта"
        assert 'Начало проекта' in item0
        # Второй — "Завершение стадии" + выключен
        assert 'Завершение стадии' in item1
        assert 'ВЫКЛ' in item1

    def test_script_editor_stack_initial(self, admin_dlg):
        """Редактор скриптов — начальное состояние: пустая страница."""
        assert admin_dlg._script_editor_stack.currentIndex() == 0

    def test_select_script_shows_editor(self, admin_dlg):
        """Выбор скрипта переключает на редактор."""
        admin_dlg._script_list.setCurrentRow(0)
        assert admin_dlg._script_editor_stack.currentIndex() == 1
        assert admin_dlg._current_script_id == 1

    def test_script_text_loaded(self, admin_dlg):
        """Текст шаблона загружается при выборе скрипта."""
        admin_dlg._script_list.setCurrentRow(0)
        assert admin_dlg._script_text.toPlainText() == 'Привет, {client_name}!'

    def test_script_type_combo(self, admin_dlg):
        """ComboBox типов скриптов содержит все 5 типов."""
        combo = admin_dlg._script_type_combo
        assert combo.count() == 5
        # Проверяем ключи
        keys = [combo.itemData(i) for i in range(combo.count())]
        assert 'project_start' in keys
        assert 'stage_complete' in keys
        assert 'custom' in keys

    def test_insert_placeholder(self, admin_dlg):
        """Вставка плейсхолдера в текст скрипта."""
        admin_dlg._script_list.setCurrentRow(0)
        admin_dlg._script_text.setPlainText("")
        admin_dlg._insert_placeholder("{client_name}")
        assert '{client_name}' in admin_dlg._script_text.toPlainText()

    def test_script_enabled_checkbox(self, admin_dlg):
        """Чекбокс 'Включен' отражает состояние скрипта."""
        admin_dlg._script_list.setCurrentRow(0)
        assert admin_dlg._script_enabled_cb.isChecked() is True

        admin_dlg._script_list.setCurrentRow(1)
        assert admin_dlg._script_enabled_cb.isChecked() is False

    def test_script_auto_deadline_checkbox(self, admin_dlg):
        """Чекбокс 'Подставлять дедлайн' отражает состояние скрипта."""
        admin_dlg._script_list.setCurrentRow(0)
        assert admin_dlg._script_auto_deadline_cb.isChecked() is False

        admin_dlg._script_list.setCurrentRow(1)
        assert admin_dlg._script_auto_deadline_cb.isChecked() is True

    def test_memo_file_loaded(self, admin_dlg):
        """PDF-памятка отображается для скрипта с файлом."""
        admin_dlg._script_list.setCurrentRow(1)
        assert admin_dlg._memo_file_label.text() == 'memo.pdf'

    def test_memo_clear(self, admin_dlg):
        """Кнопка 'Убрать' очищает путь к PDF-памятке."""
        admin_dlg._script_list.setCurrentRow(1)
        admin_dlg._on_clear_memo()
        assert admin_dlg._memo_file_path is None
        assert admin_dlg._memo_file_label.text() == 'Не загружена'

    def test_deselect_script_returns_to_empty(self, admin_dlg):
        """Снятие выделения возвращает на пустую страницу."""
        admin_dlg._script_list.setCurrentRow(0)
        assert admin_dlg._script_editor_stack.currentIndex() == 1
        # Вызываем с row=-1 (снятие выделения)
        admin_dlg._on_script_selected(-1)
        assert admin_dlg._script_editor_stack.currentIndex() == 0
        assert admin_dlg._current_script_id is None

    def test_stage_combo_populated(self, admin_dlg):
        """Комбобокс стадий заполнен данными из CRM_STAGE_GROUPS."""
        combo = admin_dlg._script_stage_combo
        assert combo.count() > 10  # Много стадий + группы
        # Первый элемент — "(все стадии)"
        assert combo.itemText(0) == '(все стадии)'
        assert combo.itemData(0) == ''


# =====================================================================
# Тесты: Сохранение настроек
# =====================================================================

@pytest.mark.ui
class TestAdminSaveSettings:
    """Тесты сохранения настроек."""

    def test_on_save_collects_all_settings(self, admin_dlg):
        """Сохранение собирает все 10 настроек."""
        admin_dlg._tg_bot_token.setText('new-token')
        admin_dlg._smtp_host.setText('smtp.new.ru')

        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            admin_dlg.data_access.update_messenger_settings.return_value = True
            admin_dlg._on_save()

        call_args = admin_dlg.data_access.update_messenger_settings.call_args[0][0]
        keys = [s['setting_key'] for s in call_args]
        assert 'telegram_bot_token' in keys
        assert 'smtp_host' in keys
        assert len(call_args) == 10

    def test_on_save_error_handling(self, admin_dlg):
        """Ошибка сохранения — показ сообщения об ошибке."""
        admin_dlg.data_access.update_messenger_settings.side_effect = Exception("Ошибка сети")

        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            admin_dlg._on_save()
            # CustomMessageBox вызван с типом "error"
            assert MockMB.called
            call_args = MockMB.call_args
            assert 'Ошибка' in str(call_args)


# =====================================================================
# Тесты: Сохранение/удаление скриптов
# =====================================================================

@pytest.mark.ui
class TestAdminScriptActions:
    """Тесты действий со скриптами (сохранение, удаление)."""

    def test_save_script_success(self, admin_dlg):
        """Успешное сохранение скрипта."""
        admin_dlg._script_list.setCurrentRow(0)
        admin_dlg._script_text.setPlainText("Новый текст шаблона")

        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            admin_dlg._on_save_script()

        admin_dlg.data_access.update_messenger_script.assert_called_once()
        call_args = admin_dlg.data_access.update_messenger_script.call_args
        assert call_args[0][0] == 1  # script_id
        assert call_args[0][1]['message_template'] == "Новый текст шаблона"

    def test_save_script_empty_text(self, admin_dlg):
        """Сохранение пустого скрипта — показ предупреждения."""
        admin_dlg._script_list.setCurrentRow(0)
        admin_dlg._script_text.setPlainText("")

        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            admin_dlg._on_save_script()

        # update_messenger_script НЕ вызван
        admin_dlg.data_access.update_messenger_script.assert_not_called()

    def test_delete_script_confirmed(self, admin_dlg):
        """Удаление скрипта после подтверждения."""
        admin_dlg._script_list.setCurrentRow(0)

        with patch('ui.custom_message_box.CustomQuestionBox') as MockQB, \
             patch('ui.custom_message_box.CustomMessageBox'):
            MockQB.return_value.exec_.return_value = QDialog.Accepted
            admin_dlg._on_delete_script()

        admin_dlg.data_access.delete_messenger_script.assert_called_once_with(1)


# =====================================================================
# Тесты: Стили и константы модуля
# =====================================================================

@pytest.mark.ui
class TestAdminStyles:
    """Тесты стилей и констант."""

    def test_script_placeholders_dict(self):
        """SCRIPT_PLACEHOLDERS содержит все 10 плейсхолдеров."""
        from ui.messenger_admin_dialog import SCRIPT_PLACEHOLDERS
        assert len(SCRIPT_PLACEHOLDERS) == 10
        assert '{client_name}' in SCRIPT_PLACEHOLDERS
        assert '{deadline}' in SCRIPT_PLACEHOLDERS

    def test_script_types_dict(self):
        """SCRIPT_TYPES содержит все 5 типов."""
        from ui.messenger_admin_dialog import SCRIPT_TYPES
        assert len(SCRIPT_TYPES) == 5
        assert 'project_start' in SCRIPT_TYPES
        assert 'custom' in SCRIPT_TYPES

    def test_crm_stage_groups(self):
        """CRM_STAGE_GROUPS содержит 3 группы: Индивидуальный, Шаблонный, Надзор."""
        from ui.messenger_admin_dialog import CRM_STAGE_GROUPS
        assert len(CRM_STAGE_GROUPS) == 3
        assert 'Индивидуальный проект' in CRM_STAGE_GROUPS
        assert 'Шаблонный проект' in CRM_STAGE_GROUPS
        assert 'Надзор' in CRM_STAGE_GROUPS

    def test_tab_style_constant(self):
        """_TAB_STYLE содержит стили QTabWidget."""
        from ui.messenger_admin_dialog import _TAB_STYLE
        assert 'QTabWidget' in _TAB_STYLE
        assert 'QTabBar' in _TAB_STYLE

    def test_input_style_constant(self):
        """_INPUT_STYLE содержит стили QLineEdit."""
        from ui.messenger_admin_dialog import _INPUT_STYLE
        assert 'QLineEdit' in _INPUT_STYLE
        assert 'border' in _INPUT_STYLE


# =====================================================================
# Тесты: MessengerSelectDialog — создание и навигация
# =====================================================================

@pytest.mark.ui
class TestSelectDialogCreation:
    """Тесты создания MessengerSelectDialog."""

    def test_creates_as_dialog(self, select_dlg_crm):
        """Диалог создаётся как QDialog."""
        assert isinstance(select_dlg_crm, QDialog)

    def test_has_stacked_widget(self, select_dlg_crm):
        """QStackedWidget с 2 страницами."""
        assert hasattr(select_dlg_crm, '_stack')
        assert isinstance(select_dlg_crm._stack, QStackedWidget)
        assert select_dlg_crm._stack.count() == 2

    def test_initial_page_is_messenger(self, select_dlg_crm):
        """Начальная страница — выбор мессенджера (индекс 0)."""
        assert select_dlg_crm._stack.currentIndex() == 0

    def test_telegram_selected_by_default(self, select_dlg_crm):
        """Telegram выбран по умолчанию."""
        assert select_dlg_crm._selected_messenger == 'telegram'

    def test_min_max_width(self, select_dlg_crm):
        """Минимальная ширина 500, максимальная 560."""
        assert select_dlg_crm.minimumWidth() == 500
        assert select_dlg_crm.maximumWidth() == 560


# =====================================================================
# Тесты: MessengerSelectDialog — навигация между страницами
# =====================================================================

@pytest.mark.ui
class TestSelectDialogNavigation:
    """Тесты навигации между страницами."""

    def test_on_messenger_chosen_switches_to_config(self, select_dlg_crm):
        """Выбор мессенджера переключает на страницу настройки."""
        select_dlg_crm._on_messenger_chosen('telegram')
        assert select_dlg_crm._stack.currentIndex() == 1
        assert select_dlg_crm._selected_messenger == 'telegram'

    def test_go_back_returns_to_messenger_page(self, select_dlg_crm):
        """Кнопка 'Назад' возвращает на выбор мессенджера."""
        select_dlg_crm._on_messenger_chosen('telegram')
        assert select_dlg_crm._stack.currentIndex() == 1
        select_dlg_crm._go_back()
        assert select_dlg_crm._stack.currentIndex() == 0


# =====================================================================
# Тесты: MessengerSelectDialog — настройка чата (страница 2)
# =====================================================================

@pytest.mark.ui
class TestSelectDialogConfigPage:
    """Тесты страницы настройки чата."""

    def test_chat_title_prefilled(self, select_dlg_crm):
        """Название чата предзаполнено из card_data."""
        title = select_dlg_crm._chat_title_edit.text()
        assert title  # Не пустое
        assert 'ИН' in title  # Префикс для CRM-карточки

    def test_manual_method_default(self, select_dlg_crm):
        """Ручная привязка выбрана по умолчанию."""
        assert select_dlg_crm._radio_manual.isChecked()
        assert not select_dlg_crm._radio_auto.isChecked()

    def test_invite_link_visible_for_manual(self, select_dlg_crm):
        """Поле invite-ссылки видимо при ручном режиме."""
        assert not select_dlg_crm._invite_link_edit.isHidden()

    def test_invite_link_hidden_for_auto(self, select_dlg_crm):
        """Поле invite-ссылки скрыто при автоматическом режиме."""
        select_dlg_crm._radio_auto.setChecked(True)
        assert select_dlg_crm._invite_link_edit.isHidden()

    def test_create_btn_text_changes_with_method(self, select_dlg_crm):
        """Текст кнопки меняется при переключении метода."""
        # Переключаем на авто — 'Создать чат'
        select_dlg_crm._radio_auto.setChecked(True)
        select_dlg_crm._update_create_btn_text()
        assert select_dlg_crm._create_btn.text() == 'Создать чат'

        # Переключаем на ручной — 'Привязать чат'
        select_dlg_crm._radio_manual.setChecked(True)
        select_dlg_crm._update_create_btn_text()
        assert select_dlg_crm._create_btn.text() == 'Привязать чат'

    def test_back_button_exists(self, select_dlg_crm):
        """Кнопка 'Назад' существует."""
        assert hasattr(select_dlg_crm, '_back_btn')
        assert isinstance(select_dlg_crm._back_btn, QPushButton)


# =====================================================================
# Тесты: MessengerSelectDialog — участники
# =====================================================================

@pytest.mark.ui
class TestSelectDialogParticipants:
    """Тесты участников чата."""

    def test_crm_participants_built(self, select_dlg_crm):
        """Для CRM-карточки создаются участники из card_data."""
        assert len(select_dlg_crm._participant_checkboxes) > 0

    def test_crm_has_senior_manager(self, select_dlg_crm):
        """Старший менеджер в списке участников (обязательный)."""
        roles = [p['role'] for p in select_dlg_crm._participant_checkboxes]
        assert 'Старший менеджер' in roles
        sm = next(p for p in select_dlg_crm._participant_checkboxes
                  if p['role'] == 'Старший менеджер')
        assert sm['mandatory'] is True

    def test_crm_has_designer(self, select_dlg_crm):
        """Дизайнер в списке участников (необязательный)."""
        roles = [p['role'] for p in select_dlg_crm._participant_checkboxes]
        assert 'Дизайнер' in roles
        des = next(p for p in select_dlg_crm._participant_checkboxes
                   if p['role'] == 'Дизайнер')
        assert des['mandatory'] is False

    def test_supervision_has_dan(self, select_dlg_supervision):
        """Для надзора ДАН в списке участников (обязательный)."""
        roles = [p['role'] for p in select_dlg_supervision._participant_checkboxes]
        assert 'ДАН' in roles
        dan = next(p for p in select_dlg_supervision._participant_checkboxes
                   if p['role'] == 'ДАН')
        assert dan['mandatory'] is True

    def test_collect_members_returns_checked(self, select_dlg_crm):
        """_collect_members() возвращает только отмеченных участников."""
        members = select_dlg_crm._collect_members()
        assert len(members) > 0
        for m in members:
            assert 'member_id' in m
            assert 'role_in_project' in m


# =====================================================================
# Тесты: MessengerSelectDialog — _build_default_title
# =====================================================================

@pytest.mark.ui
class TestSelectDialogDefaultTitle:
    """Тесты формирования названия чата по умолчанию."""

    def test_crm_title_prefix(self, select_dlg_crm):
        """CRM-карточка: префикс ИН."""
        title = select_dlg_crm._build_default_title()
        assert title.startswith('ИН')

    def test_supervision_title_prefix(self, select_dlg_supervision):
        """Карточка надзора: префикс АН."""
        title = select_dlg_supervision._build_default_title()
        assert title.startswith('АН')

    def test_title_contains_city(self, select_dlg_crm):
        """Название содержит город."""
        title = select_dlg_crm._build_default_title()
        assert 'СПБ' in title

    def test_title_replaces_underscores(self, qtbot, mock_data_access, mock_employee_admin):
        """Подчёркивания в городе заменяются на дефисы."""
        mock_data_access.get_all_employees.return_value = []
        parent = _make_parent(qtbot, mock_data_access, mock_employee_admin)

        card = {'id': 500, 'city': 'Санкт_Петербург', 'address': 'ул. Тест'}

        with patch(_SELECT_PATCHES['icon_loader']) as MockIcon, \
             patch(_SELECT_PATCHES['resource_path'], return_value=''), \
             patch(_SELECT_PATCHES['qpixmap'], return_value=QPixmap()):
            MockIcon.load = MagicMock(return_value=QIcon())
            from ui.messenger_select_dialog import MessengerSelectDialog
            dlg = MessengerSelectDialog(
                parent, card_data=card, api_client=None,
                db=MagicMock(), data_access=mock_data_access,
                employee=mock_employee_admin, card_type='crm',
            )
            dlg.setAttribute(Qt.WA_DeleteOnClose, False)
            title = dlg._build_default_title()
            # Не должно быть подчёркиваний
            assert '_' not in title


# =====================================================================
# Тесты: MessengerSelectDialog — валидация при создании
# =====================================================================

@pytest.mark.ui
class TestSelectDialogValidation:
    """Тесты валидации при создании/привязке чата."""

    def test_empty_title_shows_warning(self, select_dlg_crm):
        """Пустое название чата — показ предупреждения."""
        select_dlg_crm._chat_title_edit.setText("")
        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            select_dlg_crm._on_create()
            assert MockMB.called

    def test_manual_empty_link_shows_warning(self, select_dlg_crm):
        """Пустая invite-ссылка при ручной привязке — показ предупреждения."""
        select_dlg_crm._chat_title_edit.setText("Тестовый чат")
        select_dlg_crm._radio_manual.setChecked(True)
        select_dlg_crm._invite_link_edit.setText("")
        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            select_dlg_crm._on_create()
            assert MockMB.called

    def test_successful_bind_calls_data_access(self, select_dlg_crm):
        """Успешная привязка вызывает data_access.bind_messenger_chat."""
        select_dlg_crm._chat_title_edit.setText("Тестовый чат")
        select_dlg_crm._radio_manual.setChecked(True)
        select_dlg_crm._invite_link_edit.setText("https://t.me/+ABC123")

        select_dlg_crm.data_access.bind_messenger_chat.return_value = {
            'id': 10, 'chat_id': '12345',
        }

        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            select_dlg_crm._on_create()

        select_dlg_crm.data_access.bind_messenger_chat.assert_called_once()

    def test_create_btn_reenabled_after_error(self, select_dlg_crm):
        """Кнопка 'Создать' включается обратно после ошибки."""
        select_dlg_crm._chat_title_edit.setText("Тестовый чат")
        select_dlg_crm._radio_manual.setChecked(True)
        select_dlg_crm._invite_link_edit.setText("https://t.me/+ABC123")

        select_dlg_crm.data_access.bind_messenger_chat.side_effect = Exception("Ошибка")

        with patch('ui.custom_message_box.CustomMessageBox') as MockMB:
            MockMB.return_value.exec_ = MagicMock()
            select_dlg_crm._on_create()

        assert select_dlg_crm._create_btn.isEnabled()


# =====================================================================
# Тесты: MessengerSelectDialog — стили
# =====================================================================

@pytest.mark.ui
class TestSelectDialogStyles:
    """Тесты стилей MessengerSelectDialog."""

    def test_messenger_btn_style_constant(self):
        """_MESSENGER_BTN_STYLE содержит стили QPushButton."""
        from ui.messenger_select_dialog import _MESSENGER_BTN_STYLE
        assert 'QPushButton' in _MESSENGER_BTN_STYLE

    def test_radio_style_constant(self):
        """_RADIO_STYLE содержит стили QRadioButton."""
        from ui.messenger_select_dialog import _RADIO_STYLE
        assert 'QRadioButton' in _RADIO_STYLE

    def test_checkbox_style_constant(self):
        """_CHECKBOX_STYLE содержит стили QCheckBox с disabled состоянием."""
        from ui.messenger_select_dialog import _CHECKBOX_STYLE
        assert 'QCheckBox' in _CHECKBOX_STYLE
        assert 'disabled' in _CHECKBOX_STYLE
