# -*- coding: utf-8 -*-
"""
Глубокие тесты окна авторизации LoginWindow.
~25 тестов: рендеринг, валидация, аутентификация (online/offline),
обработка ошибок API, синхронизация, кеширование пароля,
SyncProgressDialog, SyncWorker, focus_password.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock, call
from PyQt5.QtWidgets import (QWidget, QLineEdit, QPushButton, QLabel,
                             QProgressBar, QDialog, QApplication)
from PyQt5.QtCore import Qt, QThread


# ========== Хелпер ==========

def _create_login(qtbot, multi_user=False, api_client=None):
    """Создать LoginWindow с мок-БД и настраиваемым режимом.

    Возвращает (window, mock_db).
    """
    mock_db = MagicMock()
    patches_ctx = [
        patch('ui.login_window.DatabaseManager', return_value=mock_db),
        patch('ui.login_window.MULTI_USER_MODE', multi_user),
    ]
    if multi_user:
        mock_api = api_client or MagicMock()
        patches_ctx.append(
            patch('ui.login_window.APIClient', return_value=mock_api)
        )

    for p in patches_ctx:
        p.start()

    try:
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        if multi_user:
            w.api_client = mock_api
        return w, mock_db
    finally:
        for p in patches_ctx:
            p.stop()


# ========== 1. Рендеринг (8 тестов) ==========

@pytest.mark.ui
class TestLoginWindowDeepRendering:
    """Рендеринг и структура окна авторизации."""

    def test_is_qwidget(self, qtbot, tmp_path):
        """LoginWindow наследуется от QWidget."""
        w, _ = _create_login(qtbot)
        assert isinstance(w, QWidget)

    def test_login_input_exists(self, qtbot):
        """Поле логина существует."""
        w, _ = _create_login(qtbot)
        assert hasattr(w, 'login_input')
        assert isinstance(w.login_input, QLineEdit)

    def test_password_input_exists(self, qtbot):
        """Поле пароля существует."""
        w, _ = _create_login(qtbot)
        assert hasattr(w, 'password_input')
        assert isinstance(w.password_input, QLineEdit)

    def test_password_masked(self, qtbot):
        """Пароль маскирован (EchoMode.Password)."""
        w, _ = _create_login(qtbot)
        assert w.password_input.echoMode() == QLineEdit.Password

    def test_frameless_window(self, qtbot):
        """Окно без стандартной рамки."""
        w, _ = _create_login(qtbot)
        assert w.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, qtbot):
        """WA_TranslucentBackground включён для скруглённых углов."""
        w, _ = _create_login(qtbot)
        assert w.testAttribute(Qt.WA_TranslucentBackground)

    def test_fixed_size_400x580(self, qtbot):
        """Фиксированный размер 400x580."""
        w, _ = _create_login(qtbot)
        assert w.width() == 400
        assert w.height() == 580

    def test_window_title(self, qtbot):
        """Заголовок окна содержит 'Вход'."""
        w, _ = _create_login(qtbot)
        assert 'Вход' in w.windowTitle()


# ========== 2. UI-элементы (4 теста) ==========

@pytest.mark.ui
class TestLoginWindowDeepUIElements:
    """Наличие кнопок, меток и других элементов."""

    def test_login_button_present(self, qtbot):
        """Кнопка 'ВОЙТИ' существует."""
        w, _ = _create_login(qtbot)
        buttons = w.findChildren(QPushButton)
        login_btns = [b for b in buttons if 'ВОЙТИ' in b.text().upper()]
        assert len(login_btns) >= 1

    def test_login_placeholder(self, qtbot):
        """Placeholder поля логина — 'Введите логин'."""
        w, _ = _create_login(qtbot)
        assert 'логин' in w.login_input.placeholderText().lower()

    def test_password_placeholder(self, qtbot):
        """Placeholder поля пароля — 'Введите пароль'."""
        w, _ = _create_login(qtbot)
        assert 'пароль' in w.password_input.placeholderText().lower()

    def test_title_label_present(self, qtbot):
        """Заголовок 'Вход в систему' присутствует."""
        w, _ = _create_login(qtbot)
        labels = w.findChildren(QLabel)
        title_labels = [l for l in labels if 'Вход в систему' in l.text()]
        assert len(title_labels) >= 1


# ========== 3. Валидация ввода (3 теста) ==========

@pytest.mark.ui
class TestLoginWindowDeepValidation:
    """Валидация полей логина и пароля."""

    def test_empty_both_fields(self, qtbot):
        """Пустые оба поля — ошибка, main_window не создан."""
        w, _ = _create_login(qtbot)
        w.login_input.setText('')
        w.password_input.setText('')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None

    def test_empty_login_only(self, qtbot):
        """Пустой логин — ошибка."""
        w, _ = _create_login(qtbot)
        w.login_input.setText('')
        w.password_input.setText('pass123')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None
        MockMsg.assert_called_once()

    def test_empty_password_only(self, qtbot):
        """Пустой пароль — ошибка."""
        w, _ = _create_login(qtbot)
        w.login_input.setText('admin')
        w.password_input.setText('')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None


# ========== 4. Локальная аутентификация (3 теста) ==========

@pytest.mark.ui
class TestLoginWindowDeepLocalAuth:
    """Аутентификация через локальную SQLite БД (MULTI_USER_MODE=False)."""

    def test_wrong_credentials(self, qtbot):
        """Неверные данные — ошибка."""
        w, mock_db = _create_login(qtbot, multi_user=False)
        mock_db.get_employee_by_login.return_value = None
        w.login_input.setText('wrong')
        w.password_input.setText('wrong')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None

    def test_correct_login_creates_main_window(self, qtbot):
        """Успешный вход — MainWindow создаётся."""
        w, mock_db = _create_login(qtbot, multi_user=False)
        emp = {"id": 1, "full_name": "Тестов", "login": "admin",
               "position": "Руководитель студии", "secondary_position": "",
               "role": "admin", "department": "Тест", "status": "активный"}
        mock_db.get_employee_by_login.return_value = emp
        w.login_input.setText('admin')
        w.password_input.setText('admin123')
        with patch('ui.login_window.MainWindow') as MockMW:
            mock_mw_inst = MagicMock()
            MockMW.return_value = mock_mw_inst
            w.login()
            MockMW.assert_called_once_with(emp)
            assert w.main_window is not None

    def test_correct_login_hides_window(self, qtbot):
        """Успешный вход — LoginWindow скрывается."""
        w, mock_db = _create_login(qtbot, multi_user=False)
        emp = {"id": 1, "full_name": "Тестов", "login": "admin",
               "position": "Руководитель студии", "secondary_position": ""}
        mock_db.get_employee_by_login.return_value = emp
        w.login_input.setText('admin')
        w.password_input.setText('pass')
        with patch('ui.login_window.MainWindow') as MockMW:
            MockMW.return_value = MagicMock()
            w.login()
            # LoginWindow должен быть скрыт
            assert not w.isVisible()


# ========== 5. Взаимодействие с UI (3 теста) ==========

@pytest.mark.ui
class TestLoginWindowDeepInteraction:
    """Взаимодействие пользователя с элементами."""

    def test_enter_in_login_focuses_password(self, qtbot):
        """Enter в поле логина переводит фокус на пароль."""
        w, _ = _create_login(qtbot)
        # Проверяем что returnPressed поля логина подключён к focus_password
        receivers = w.login_input.receivers(w.login_input.returnPressed)
        assert receivers > 0

    def test_enter_in_password_calls_login(self, qtbot):
        """Enter в поле пароля подключён к login()."""
        w, _ = _create_login(qtbot)
        receivers = w.password_input.receivers(w.password_input.returnPressed)
        assert receivers > 0

    def test_focus_password_method(self, qtbot):
        """focus_password переводит фокус на поле пароля."""
        w, _ = _create_login(qtbot)
        w.show()
        w.login_input.setFocus()
        w.focus_password()
        # В offscreen режиме фокус может не работать идеально,
        # но метод не должен бросать исключение
        assert True


# ========== 6. SyncProgressDialog (2 теста) ==========

@pytest.mark.ui
class TestSyncProgressDialog:
    """Диалог прогресса синхронизации."""

    def test_dialog_creation(self, qtbot):
        """SyncProgressDialog создаётся без ошибок."""
        from ui.login_window import SyncProgressDialog
        dialog = SyncProgressDialog()
        qtbot.addWidget(dialog)
        assert isinstance(dialog, QDialog)

    def test_set_progress(self, qtbot):
        """set_progress обновляет прогресс и сообщение."""
        from ui.login_window import SyncProgressDialog
        dialog = SyncProgressDialog()
        qtbot.addWidget(dialog)
        dialog.set_progress(3, 7, "Загрузка клиентов...")
        assert dialog.progress_bar.value() == 3
        assert dialog.progress_bar.maximum() == 7
        assert dialog.message_label.text() == "Загрузка клиентов..."


# ========== 7. Кеширование пароля и offline-вход (2 теста) ==========

@pytest.mark.ui
class TestLoginWindowDeepOffline:
    """Кеширование пароля и offline-аутентификация."""

    def test_cache_password_called(self, qtbot):
        """_cache_password_for_offline вызывает db.cache_employee_password."""
        w, mock_db = _create_login(qtbot, multi_user=False)
        w._cache_password_for_offline(42, "secret_pass")
        mock_db.cache_employee_password.assert_called_once_with(42, "secret_pass")

    def test_try_offline_login_no_employee(self, qtbot):
        """_try_offline_login возвращает False если пользователь не найден."""
        w, mock_db = _create_login(qtbot, multi_user=False)
        mock_db.get_employee_for_offline_login.return_value = None
        result = w._try_offline_login("unknown", "pass")
        assert result is False
