# -*- coding: utf-8 -*-
"""
Тесты окна авторизации — LoginWindow.
14 тестов.
"""

import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QWidget, QLineEdit, QPushButton
from PyQt5.QtCore import Qt


def _create_login_window(qtbot, tmp_path):
    """Создать LoginWindow с мок-БД и без API."""
    db_path = str(tmp_path / "login_test.db")
    with patch('ui.login_window.DatabaseManager') as MockDB, \
         patch('ui.login_window.MULTI_USER_MODE', False):
        mock_db = MagicMock()
        MockDB.return_value = mock_db
        from ui.login_window import LoginWindow
        w = LoginWindow()
        qtbot.addWidget(w)
        return w, mock_db


@pytest.mark.ui
class TestLoginWindowRendering:
    """Проверка рендеринга окна входа."""

    def test_login_window_renders(self, qtbot, tmp_path):
        """Окно создаётся как QWidget."""
        w, _ = _create_login_window(qtbot, tmp_path)
        assert isinstance(w, QWidget)

    def test_login_input_present(self, qtbot, tmp_path):
        """Поле логина существует и является QLineEdit."""
        w, _ = _create_login_window(qtbot, tmp_path)
        assert hasattr(w, 'login_input')
        assert isinstance(w.login_input, QLineEdit)

    def test_password_input_masked(self, qtbot, tmp_path):
        """Пароль маскирован (EchoMode.Password)."""
        w, _ = _create_login_window(qtbot, tmp_path)
        assert w.password_input.echoMode() == QLineEdit.Password

    def test_login_button_present(self, qtbot, tmp_path):
        """Кнопка 'ВОЙТИ' существует."""
        w, _ = _create_login_window(qtbot, tmp_path)
        buttons = w.findChildren(QPushButton)
        login_btns = [b for b in buttons if 'ВОЙТИ' in b.text().upper()]
        assert len(login_btns) >= 1

    def test_frameless_window(self, qtbot, tmp_path):
        """Окно без стандартной рамки."""
        w, _ = _create_login_window(qtbot, tmp_path)
        assert w.windowFlags() & Qt.FramelessWindowHint

    def test_translucent_background(self, qtbot, tmp_path):
        """Прозрачный фон для border-radius."""
        w, _ = _create_login_window(qtbot, tmp_path)
        assert w.testAttribute(Qt.WA_TranslucentBackground)

    def test_title_bar_present(self, qtbot, tmp_path):
        """CustomTitleBar существует."""
        w, _ = _create_login_window(qtbot, tmp_path)
        from ui.custom_title_bar import CustomTitleBar
        title_bars = w.findChildren(CustomTitleBar)
        assert len(title_bars) >= 1

    def test_fixed_size(self, qtbot, tmp_path):
        """Фиксированный размер 400x580."""
        w, _ = _create_login_window(qtbot, tmp_path)
        assert w.width() == 400
        assert w.height() == 580


@pytest.mark.ui
class TestLoginWindowValidation:
    """Проверка валидации ввода."""

    def test_empty_login_rejected(self, qtbot, tmp_path):
        """Пустой логин — main_window не создан."""
        w, mock_db = _create_login_window(qtbot, tmp_path)
        w.login_input.setText('')
        w.password_input.setText('password')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None

    def test_empty_password_rejected(self, qtbot, tmp_path):
        """Пустой пароль — main_window не создан."""
        w, mock_db = _create_login_window(qtbot, tmp_path)
        w.login_input.setText('admin')
        w.password_input.setText('')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None

    def test_wrong_credentials_offline(self, qtbot, tmp_path):
        """Неверные данные — ошибка (offline режим)."""
        w, mock_db = _create_login_window(qtbot, tmp_path)
        # БД возвращает None (пользователь не найден)
        mock_db.get_employee_by_login.return_value = None
        w.login_input.setText('wrong_user')
        w.password_input.setText('wrong_pass')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None

    def test_correct_login_offline(self, qtbot, tmp_path):
        """Верный логин (offline) — main_window создан."""
        w, mock_db = _create_login_window(qtbot, tmp_path)
        employee_data = {
            "id": 1, "full_name": "Тестов Админ", "login": "admin",
            "position": "Руководитель студии", "secondary_position": "",
            "department": "Административный отдел",
            "status": "активный"
        }
        mock_db.get_employee_by_login.return_value = employee_data
        w.login_input.setText('admin')
        w.password_input.setText('admin123')
        with patch('ui.login_window.MainWindow') as MockMW:
            mock_mw = MagicMock()
            MockMW.return_value = mock_mw
            w.login()
            # MainWindow создан с данными employee
            MockMW.assert_called_once_with(employee_data)
            assert w.main_window is not None

    def test_inactive_user_rejected(self, qtbot, tmp_path):
        """Неактивный пользователь — main_window не создан (get_employee_by_login вернёт None)."""
        w, mock_db = _create_login_window(qtbot, tmp_path)
        # БД не найдёт пользователя (пароль не совпадёт или статус проверяется внутри)
        mock_db.get_employee_by_login.return_value = None
        w.login_input.setText('fired')
        w.password_input.setText('pass123')
        with patch('ui.login_window.CustomMessageBox') as MockMsg:
            MockMsg.return_value.exec_.return_value = None
            w.login()
        assert w.main_window is None


@pytest.mark.ui
class TestLoginWindowInteraction:
    """Проверка взаимодействия."""

    def test_enter_submits(self, qtbot, tmp_path):
        """Enter в поле пароля подключён к login()."""
        w, _ = _create_login_window(qtbot, tmp_path)
        # Проверяем что returnPressed подключён к login
        # (не вызываем emit, т.к. login() покажет диалог)
        receivers = w.password_input.receivers(w.password_input.returnPressed)
        assert receivers > 0
