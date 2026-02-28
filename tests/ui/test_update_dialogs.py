# -*- coding: utf-8 -*-
"""
Тесты диалогов обновлений — VersionDialog, UpdateDialog.
~10 тестов.
"""

import re
import pytest
from unittest.mock import patch, MagicMock
from PyQt5.QtWidgets import QDialog, QPushButton, QLabel, QLineEdit, QProgressBar, QMessageBox


# ========== Авто-мок QMessageBox ==========

@pytest.fixture(autouse=True)
def _mock_update_msgbox():
    """Мок QMessageBox чтобы диалоги не блокировали тесты."""
    with patch('ui.update_dialogs.QMessageBox') as m:
        m.warning = MagicMock()
        m.information = MagicMock()
        m.critical = MagicMock()
        yield m


# ========================================================================
# 1. VersionDialog (7 тестов)
# ========================================================================

@pytest.mark.ui
class TestVersionDialog:
    """Диалог управления версиями и обновлениями."""

    @pytest.fixture
    def dlg(self, qtbot):
        from ui.update_dialogs import VersionDialog
        d = VersionDialog()
        qtbot.addWidget(d)
        return d

    def test_creates_as_dialog(self, dlg):
        """VersionDialog создаётся как QDialog."""
        assert isinstance(dlg, QDialog)

    def test_has_version_input(self, dlg):
        """Поле ввода версии существует."""
        assert hasattr(dlg, 'version_input')
        assert isinstance(dlg.version_input, QLineEdit)

    def test_has_server_info_label(self, dlg):
        """Лейбл информации о сервере существует."""
        assert hasattr(dlg, 'server_info_label')

    def test_has_upload_progress(self, dlg):
        """Прогресс-бар загрузки существует и скрыт."""
        assert hasattr(dlg, 'upload_progress')
        assert isinstance(dlg.upload_progress, QProgressBar)
        assert not dlg.upload_progress.isVisible()

    def test_upload_btn_disabled_initially(self, dlg):
        """Кнопка загрузки отключена без выбранного файла."""
        assert hasattr(dlg, 'upload_btn')
        assert not dlg.upload_btn.isEnabled()

    def test_save_version_invalid_format(self, dlg, _mock_update_msgbox):
        """Невалидный формат версии вызывает предупреждение."""
        dlg.version_input.setText('abc')
        dlg.save_version()
        _mock_update_msgbox.warning.assert_called_once()

    def test_save_version_valid_format(self, dlg, _mock_update_msgbox):
        """Валидный формат X.Y.Z обрабатывается без warning (но может вызвать ошибку файла)."""
        # Мокаем файловые операции чтобы не трогать реальный config.py
        with patch('builtins.open', MagicMock()):
            with patch('ui.update_dialogs.re.sub', return_value='APP_VERSION = "2.0.0"'):
                dlg.version_input.setText('2.0.0')
                dlg.save_version()
                # Не должен быть вызван warning (формат валидный)
                _mock_update_msgbox.warning.assert_not_called()

    def test_choose_exe_file_updates_label(self, dlg):
        """Выбор exe обновляет лейбл и включает кнопку загрузки."""
        import os
        with patch('ui.update_dialogs.QFileDialog.getOpenFileName', return_value=('/tmp/test.exe', '')), \
             patch('os.path.getsize', return_value=50 * 1024 * 1024):
            dlg.choose_exe_file()
            assert dlg.selected_exe_path == '/tmp/test.exe'
            assert dlg.upload_btn.isEnabled()

    def test_check_server_version_error(self, dlg):
        """Проверка версии сервера с ошибкой обновляет лейбл."""
        with patch('utils.update_manager.UpdateManager') as MockUM:
            MockUM.return_value.check_server_version.return_value = {'error': 'Connection refused'}
            dlg.check_server_version()
            assert 'ошибка' in dlg.server_info_label.text().lower() or 'error' in dlg.server_info_label.text().lower()


# ========================================================================
# 2. UpdateDialog (3 теста)
# ========================================================================

@pytest.mark.ui
class TestUpdateDialog:
    """Диалог обновления программы."""

    @pytest.fixture
    def update_info(self):
        return {
            'version': '2.1.0',
            'details': {
                'release_date': '2026-02-26',
                'size_mb': 85.5,
                'changelog': 'Новые функции и исправления'
            }
        }

    @pytest.fixture
    def dlg(self, qtbot, update_info):
        from ui.update_dialogs import UpdateDialog
        d = UpdateDialog(update_info)
        qtbot.addWidget(d)
        return d

    def test_creates_with_update_info(self, dlg):
        """Диалог создаётся с данными обновления."""
        assert dlg.update_info['version'] == '2.1.0'

    def test_has_progress_bar(self, dlg):
        """Прогресс-бар существует и скрыт."""
        assert hasattr(dlg, 'progress_bar')
        assert not dlg.progress_bar.isVisible()

    def test_displays_version(self, dlg):
        """Версия отображается в диалоге."""
        labels = dlg.findChildren(QLabel)
        version_found = any('2.1.0' in lbl.text() for lbl in labels)
        assert version_found, "Версия 2.1.0 не найдена в лейблах диалога"
