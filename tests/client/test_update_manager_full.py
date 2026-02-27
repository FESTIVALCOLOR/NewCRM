# -*- coding: utf-8 -*-
"""
Полное покрытие utils/update_manager.py — 178 строк, покрытие 0% -> 80%+
Тесты: compare_versions, check_for_updates, check_server_version,
       download_update, install_update, upload_update, _fetch_version_json.
~30 тестов.
"""

import pytest
import sys
import os
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture
def um():
    """Создать UpdateManager с мок-конфигом."""
    with patch('utils.update_manager.APP_VERSION', '1.0.0'), \
         patch('utils.update_manager.UPDATE_CHECK_URL', 'http://test/api'), \
         patch('utils.update_manager.UPDATE_YANDEX_PUBLIC_KEY', 'test_key'), \
         patch('utils.update_manager.UPDATE_CHECK_ENABLED', True), \
         patch('utils.update_manager.API_BASE_URL', 'http://api:8000'):
        from utils.update_manager import UpdateManager
        return UpdateManager()


# ==================== _compare_versions ====================

class TestCompareVersions:
    """_compare_versions — сравнение версий X.Y.Z."""

    def test_equal(self, um):
        assert um._compare_versions('1.0.0', '1.0.0') == 0

    def test_v1_greater_major(self, um):
        assert um._compare_versions('2.0.0', '1.0.0') == 1

    def test_v1_less_major(self, um):
        assert um._compare_versions('1.0.0', '2.0.0') == -1

    def test_v1_greater_minor(self, um):
        assert um._compare_versions('1.2.0', '1.1.0') == 1

    def test_v1_less_minor(self, um):
        assert um._compare_versions('1.1.0', '1.2.0') == -1

    def test_v1_greater_patch(self, um):
        assert um._compare_versions('1.0.2', '1.0.1') == 1

    def test_v1_less_patch(self, um):
        assert um._compare_versions('1.0.1', '1.0.2') == -1

    def test_different_lengths_padded_with_zeros(self, um):
        assert um._compare_versions('1.0', '1.0.0') == 0

    def test_longer_v1(self, um):
        assert um._compare_versions('1.0.0.1', '1.0.0') == 1

    def test_invalid_version_returns_0(self, um):
        assert um._compare_versions('abc', '1.0.0') == 0

    def test_empty_string_returns_0(self, um):
        assert um._compare_versions('', '1.0.0') == 0

    def test_large_numbers(self, um):
        assert um._compare_versions('10.20.30', '10.20.29') == 1

    def test_zeros_equal(self, um):
        assert um._compare_versions('0.0.0', '0.0.0') == 0

    def test_v2_greater_major(self, um):
        assert um._compare_versions('1.99.99', '2.0.0') == -1


# ==================== check_for_updates ====================

class TestCheckForUpdates:
    """check_for_updates — проверка наличия обновлений."""

    def test_disabled_returns_not_available(self):
        with patch('utils.update_manager.APP_VERSION', '1.0.0'), \
             patch('utils.update_manager.UPDATE_CHECK_URL', 'http://test'), \
             patch('utils.update_manager.UPDATE_YANDEX_PUBLIC_KEY', 'key'), \
             patch('utils.update_manager.UPDATE_CHECK_ENABLED', False), \
             patch('utils.update_manager.API_BASE_URL', 'http://api'):
            from utils.update_manager import UpdateManager
            um_disabled = UpdateManager()
            result = um_disabled.check_for_updates()
            assert result['available'] is False
            assert result.get('disabled') is True

    def test_no_public_key_returns_error(self):
        with patch('utils.update_manager.APP_VERSION', '1.0.0'), \
             patch('utils.update_manager.UPDATE_CHECK_URL', 'http://test'), \
             patch('utils.update_manager.UPDATE_YANDEX_PUBLIC_KEY', ''), \
             patch('utils.update_manager.UPDATE_CHECK_ENABLED', True), \
             patch('utils.update_manager.API_BASE_URL', 'http://api'):
            from utils.update_manager import UpdateManager
            um_no_key = UpdateManager()
            result = um_no_key.check_for_updates()
            assert result['available'] is False
            assert 'error' in result

    def test_update_available_newer_version(self, um):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {'2.0.0': {'changelog': 'Новое', 'download_url': 'http://dl'}}
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.check_for_updates()
            assert result['available'] is True
            assert result['version'] == '2.0.0'
            assert 'details' in result

    def test_no_update_same_version(self, um):
        version_data = {'latest_version': '1.0.0', 'versions': {}}
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.check_for_updates()
            assert result['available'] is False

    def test_no_update_older_version_on_server(self, um):
        version_data = {'latest_version': '0.9.0', 'versions': {}}
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.check_for_updates()
            assert result['available'] is False

    def test_fetch_returns_none(self, um):
        with patch.object(um, '_fetch_version_json', return_value=None):
            result = um.check_for_updates()
            assert result['available'] is False
            assert 'error' in result

    def test_no_latest_version_key(self, um):
        with patch.object(um, '_fetch_version_json', return_value={'versions': {}}):
            result = um.check_for_updates()
            assert result['available'] is False
            assert 'error' in result

    def test_exception_during_check(self, um):
        with patch.object(um, '_fetch_version_json', side_effect=Exception('Сеть')):
            result = um.check_for_updates()
            assert result['available'] is False
            assert 'error' in result


# ==================== check_server_version ====================

class TestCheckServerVersion:
    """check_server_version — сверка версии клиента с сервером."""

    def test_version_matches(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'version': '1.0.0'}
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um.check_server_version()
            assert result['match'] is True
            assert result['server_version'] == '1.0.0'
            assert result['client_version'] == '1.0.0'

    def test_version_mismatch(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'version': '2.0.0'}
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um.check_server_version()
            assert result['match'] is False

    def test_server_error_status(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um.check_server_version()
            assert 'error' in result

    def test_network_exception(self, um):
        with patch('utils.update_manager.requests.get', side_effect=Exception('timeout')):
            result = um.check_server_version()
            assert 'error' in result

    def test_server_returns_empty_version(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {'version': ''}
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um.check_server_version()
            assert result['match'] is False


# ==================== _fetch_version_json ====================

class TestFetchVersionJson:
    """_fetch_version_json — загрузка version.json из Яндекс.Диска."""

    def test_success_flow(self, um):
        # Мок ответа списка файлов
        list_resp = MagicMock()
        list_resp.status_code = 200
        list_resp.json.return_value = {
            '_embedded': {
                'items': [
                    {'name': 'version.json', 'file': 'http://download/version.json'},
                    {'name': 'other.txt', 'file': 'http://download/other.txt'},
                ]
            }
        }
        # Мок ответа version.json
        version_resp = MagicMock()
        version_resp.status_code = 200
        version_resp.json.return_value = {'latest_version': '2.0.0', 'versions': {}}

        with patch('utils.update_manager.requests.get', side_effect=[list_resp, version_resp]):
            result = um._fetch_version_json()
            assert result is not None
            assert result['latest_version'] == '2.0.0'

    def test_non_200_list_response(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 403
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um._fetch_version_json()
            assert result is None

    def test_no_version_json_in_items(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            '_embedded': {'items': [{'name': 'other.txt'}]}
        }
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um._fetch_version_json()
            assert result is None

    def test_no_file_url_in_version_item(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            '_embedded': {'items': [{'name': 'version.json'}]}  # Нет 'file' ключа
        }
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um._fetch_version_json()
            assert result is None

    def test_version_json_download_fails(self, um):
        list_resp = MagicMock()
        list_resp.status_code = 200
        list_resp.json.return_value = {
            '_embedded': {'items': [{'name': 'version.json', 'file': 'http://dl'}]}
        }
        version_resp = MagicMock()
        version_resp.status_code = 500
        with patch('utils.update_manager.requests.get', side_effect=[list_resp, version_resp]):
            result = um._fetch_version_json()
            assert result is None

    def test_exception_returns_none(self, um):
        with patch('utils.update_manager.requests.get', side_effect=Exception('err')):
            result = um._fetch_version_json()
            assert result is None


# ==================== download_update ====================

class TestDownloadUpdate:
    """download_update — загрузка обновления."""

    def test_successful_download(self, um, tmp_path):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {'2.0.0': {'download_url': 'http://dl/file.exe'}}
        }
        mock_resp = MagicMock()
        mock_resp.headers = {'content-length': '100'}
        mock_resp.iter_content.return_value = [b'x' * 50, b'y' * 50]
        mock_resp.raise_for_status = MagicMock()

        with patch.object(um, '_fetch_version_json', return_value=version_data), \
             patch('utils.update_manager.requests.get', return_value=mock_resp), \
             patch('utils.update_manager.tempfile.gettempdir', return_value=str(tmp_path)):
            result = um.download_update('2.0.0')
            assert result is not None
            assert '2.0.0' in result

    def test_download_calls_progress_callback(self, um, tmp_path):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {'2.0.0': {'download_url': 'http://dl/file.exe'}}
        }
        mock_resp = MagicMock()
        mock_resp.headers = {'content-length': '100'}
        mock_resp.iter_content.return_value = [b'x' * 50, b'y' * 50]
        mock_resp.raise_for_status = MagicMock()

        callback = MagicMock()
        with patch.object(um, '_fetch_version_json', return_value=version_data), \
             patch('utils.update_manager.requests.get', return_value=mock_resp), \
             patch('utils.update_manager.tempfile.gettempdir', return_value=str(tmp_path)):
            um.download_update('2.0.0', progress_callback=callback)
            assert callback.call_count >= 1

    def test_no_version_data_returns_none(self, um):
        with patch.object(um, '_fetch_version_json', return_value=None):
            result = um.download_update('2.0.0')
            assert result is None

    def test_version_not_found_returns_none(self, um):
        version_data = {'latest_version': '2.0.0', 'versions': {}}
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.download_update('3.0.0')
            assert result is None

    def test_no_download_url_returns_none(self, um):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {'2.0.0': {'changelog': 'test'}}  # Нет download_url
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.download_update('2.0.0')
            assert result is None

    def test_exception_returns_none(self, um):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {'2.0.0': {'download_url': 'http://dl/file.exe'}}
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data), \
             patch('utils.update_manager.requests.get', side_effect=Exception('err')):
            result = um.download_update('2.0.0')
            assert result is None


# ==================== install_update ====================

class TestInstallUpdate:
    """install_update — установка обновления."""

    def test_not_frozen_returns_false(self, um):
        with patch('utils.update_manager.sys') as mock_sys:
            mock_sys.frozen = False
            type(mock_sys).frozen = property(lambda s: False)
            delattr(mock_sys, 'frozen')
            result = um.install_update('/path/to/update.exe')
            assert result is False

    def test_exception_returns_false(self, um):
        with patch('utils.update_manager.getattr', side_effect=Exception('err')):
            result = um.install_update('/path/to/update.exe')
            assert result is False


# ==================== _download_version_json_from_disk ====================

class TestDownloadVersionJsonFromDisk:
    """_download_version_json_from_disk — загрузка через OAuth."""

    def test_successful_download(self, um, tmp_path):
        yd_mock = MagicMock()
        version_data = {'latest_version': '2.0.0', 'versions': {}}

        def fake_download(yandex_path, local_path):
            with open(local_path, 'w') as f:
                json.dump(version_data, f)

        yd_mock.download_file.side_effect = fake_download
        with patch('utils.update_manager.tempfile.gettempdir', return_value=str(tmp_path)):
            result = um._download_version_json_from_disk(yd_mock, '/disk/version.json')
            assert result is not None
            assert result['latest_version'] == '2.0.0'

    def test_exception_returns_none(self, um):
        yd_mock = MagicMock()
        yd_mock.download_file.side_effect = Exception("Ошибка")
        result = um._download_version_json_from_disk(yd_mock, '/disk/version.json')
        assert result is None


# ==================== Конструктор ====================

class TestUpdateManagerInit:
    """Тесты инициализации UpdateManager."""

    def test_current_version_set(self, um):
        assert um.current_version == '1.0.0'

    def test_update_url_set(self, um):
        assert um.update_url == 'http://test/api'

    def test_public_key_set(self, um):
        assert um.public_key == 'test_key'
