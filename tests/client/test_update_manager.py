# -*- coding: utf-8 -*-
"""
Unit-тесты для utils/update_manager.py
Тестирует сравнение версий, проверку обновлений и логику UpdateManager.
Все сетевые вызовы (requests) и зависимости замокированы.
"""
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from unittest.mock import patch, MagicMock


def make_update_manager():
    """Создаёт экземпляр UpdateManager с замоканным config."""
    mock_config = {
        'APP_VERSION': '1.0.0',
        'UPDATE_CHECK_URL': 'https://cloud-api.yandex.net/v1/disk/public/resources',
        'UPDATE_YANDEX_PUBLIC_KEY': 'test_key',
        'UPDATE_CHECK_ENABLED': True,
        'API_BASE_URL': 'http://localhost:8000',
    }
    with patch.dict('sys.modules', {'config': MagicMock(**mock_config)}):
        # Принудительно перезагрузим модуль чтобы подхватить мок
        import importlib
        if 'utils.update_manager' in sys.modules:
            del sys.modules['utils.update_manager']
        from utils.update_manager import UpdateManager
        return UpdateManager()


# ========== Тесты _compare_versions ==========

class TestCompareVersions:
    """Тесты функции сравнения версий."""

    @pytest.fixture
    def manager(self):
        return make_update_manager()

    def test_greater_version_returns_1(self, manager):
        """v1 > v2 → возвращает 1."""
        assert manager._compare_versions('2.0.0', '1.0.0') == 1

    def test_lesser_version_returns_minus_1(self, manager):
        """v1 < v2 → возвращает -1."""
        assert manager._compare_versions('1.0.0', '2.0.0') == -1

    def test_equal_versions_returns_0(self, manager):
        """v1 == v2 → возвращает 0."""
        assert manager._compare_versions('1.5.3', '1.5.3') == 0

    def test_minor_version_comparison(self, manager):
        """Сравнение по минорной версии."""
        assert manager._compare_versions('1.2.0', '1.1.0') == 1
        assert manager._compare_versions('1.1.0', '1.2.0') == -1

    def test_patch_version_comparison(self, manager):
        """Сравнение по патч-версии."""
        assert manager._compare_versions('1.0.5', '1.0.3') == 1
        assert manager._compare_versions('1.0.1', '1.0.9') == -1

    def test_different_length_versions(self, manager):
        """Версии разной длины дополняются нулями."""
        assert manager._compare_versions('2.0', '1.9.9') == 1
        assert manager._compare_versions('1.0', '1.0.0') == 0

    def test_three_digit_parts(self, manager):
        """Версии с трёхзначными числами сравниваются корректно."""
        assert manager._compare_versions('1.10.0', '1.9.0') == 1
        assert manager._compare_versions('1.9.0', '1.10.0') == -1

    def test_invalid_version_returns_0(self, manager):
        """Некорректная строка версии возвращает 0 без исключения."""
        result = manager._compare_versions('invalid', '1.0.0')
        assert result == 0

    def test_zero_versions_equal(self, manager):
        """'0.0.0' равно '0.0.0'."""
        assert manager._compare_versions('0.0.0', '0.0.0') == 0


# ========== Тесты check_for_updates ==========

class TestCheckForUpdates:
    """Тесты метода check_for_updates."""

    @pytest.fixture
    def manager(self):
        return make_update_manager()

    def test_returns_disabled_when_check_disabled(self, manager):
        """Когда UPDATE_CHECK_ENABLED=False — возвращает disabled=True."""
        manager_instance = manager
        with patch.object(manager_instance, '_fetch_version_json') as mock_fetch:
            # Мокаем модуль config чтобы UPDATE_CHECK_ENABLED=False
            with patch('utils.update_manager.UPDATE_CHECK_ENABLED', False):
                result = manager_instance.check_for_updates()
                assert result.get('disabled') is True or result.get('available') is False

    def test_returns_error_when_no_public_key(self, manager):
        """Без публичного ключа — возвращает ошибку."""
        manager.public_key = None
        result = manager.check_for_updates()
        assert result['available'] is False
        assert 'error' in result

    def test_returns_available_true_when_newer_version(self, manager):
        """Если на сервере версия новее — available=True."""
        manager.current_version = '1.0.0'
        version_data = {
            'latest_version': '2.0.0',
            'versions': {
                '2.0.0': {
                    'changelog': 'Новые функции',
                    'file_name': 'InteriorStudio_2.0.0.exe'
                }
            }
        }
        with patch.object(manager, '_fetch_version_json', return_value=version_data):
            result = manager.check_for_updates()
            assert result['available'] is True
            assert result['version'] == '2.0.0'

    def test_returns_available_false_when_same_version(self, manager):
        """Если версии совпадают — available=False."""
        manager.current_version = '1.5.0'
        version_data = {
            'latest_version': '1.5.0',
            'versions': {'1.5.0': {}}
        }
        with patch.object(manager, '_fetch_version_json', return_value=version_data):
            result = manager.check_for_updates()
            assert result['available'] is False

    def test_returns_error_when_fetch_fails(self, manager):
        """Если _fetch_version_json вернул None — ошибка."""
        with patch.object(manager, '_fetch_version_json', return_value=None):
            result = manager.check_for_updates()
            assert result['available'] is False
            assert 'error' in result

    def test_returns_error_on_exception(self, manager):
        """При исключении возвращает ошибку без краша."""
        with patch.object(manager, '_fetch_version_json', side_effect=Exception("Сеть недоступна")):
            result = manager.check_for_updates()
            assert result['available'] is False
            assert 'error' in result

    def test_returns_error_when_no_latest_version_in_data(self, manager):
        """Если в version_data нет 'latest_version' — ошибка."""
        version_data = {'versions': {}}  # Нет latest_version
        with patch.object(manager, '_fetch_version_json', return_value=version_data):
            result = manager.check_for_updates()
            assert result['available'] is False
            assert 'error' in result


# ========== Тесты check_server_version ==========

class TestCheckServerVersion:
    """Тесты метода сверки версии с сервером."""

    @pytest.fixture
    def manager(self):
        return make_update_manager()

    def test_returns_match_true_when_versions_equal(self, manager):
        """Версии совпадают — match=True."""
        manager.current_version = '1.2.3'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'version': '1.2.3'}

        with patch('utils.update_manager.requests.get', return_value=mock_response):
            result = manager.check_server_version()
            assert result['match'] is True
            assert result['client_version'] == '1.2.3'
            assert result['server_version'] == '1.2.3'

    def test_returns_match_false_when_versions_differ(self, manager):
        """Версии расходятся — match=False."""
        manager.current_version = '1.0.0'
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'version': '2.0.0'}

        with patch('utils.update_manager.requests.get', return_value=mock_response):
            result = manager.check_server_version()
            assert result['match'] is False

    def test_returns_error_on_non_200_status(self, manager):
        """HTTP ошибка от сервера — возвращает error."""
        mock_response = MagicMock()
        mock_response.status_code = 500

        with patch('utils.update_manager.requests.get', return_value=mock_response):
            result = manager.check_server_version()
            assert 'error' in result

    def test_returns_error_on_network_exception(self, manager):
        """Сетевое исключение — возвращает error без краша."""
        with patch('utils.update_manager.requests.get', side_effect=Exception("timeout")):
            result = manager.check_server_version()
            assert 'error' in result


# ========== Тесты install_update ==========

class TestInstallUpdate:
    """Тесты метода установки обновлений."""

    @pytest.fixture
    def manager(self):
        return make_update_manager()

    def test_install_update_returns_false_when_not_frozen(self, manager):
        """В не-frozen режиме (разработка) install_update возвращает False."""
        with patch('utils.update_manager.sys') as mock_sys:
            mock_sys.frozen = False
            mock_sys.executable = '/fake/path'
            result = manager.install_update('/path/to/update.exe')
            assert result is False
