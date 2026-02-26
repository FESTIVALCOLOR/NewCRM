# -*- coding: utf-8 -*-
"""
Покрытие utils/update_manager.py — UpdateManager.
~25 тестов.
"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.fixture
def um():
    """Создать UpdateManager с мок-конфигом."""
    with patch('utils.update_manager.APP_VERSION', '1.0.0'), \
         patch('utils.update_manager.UPDATE_CHECK_URL', 'http://test'), \
         patch('utils.update_manager.UPDATE_YANDEX_PUBLIC_KEY', 'test_key'), \
         patch('utils.update_manager.UPDATE_CHECK_ENABLED', True), \
         patch('utils.update_manager.API_BASE_URL', 'http://api'):
        from utils.update_manager import UpdateManager
        return UpdateManager()


# ==================== _compare_versions ====================

class TestCompareVersions:
    def test_equal_versions(self, um):
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

    def test_different_lengths(self, um):
        assert um._compare_versions('1.0', '1.0.0') == 0

    def test_longer_v1(self, um):
        assert um._compare_versions('1.0.0.1', '1.0.0') == 1

    def test_invalid_version_returns_zero(self, um):
        assert um._compare_versions('abc', '1.0.0') == 0

    def test_large_numbers(self, um):
        assert um._compare_versions('10.20.30', '10.20.29') == 1


# ==================== check_for_updates ====================

class TestCheckForUpdates:
    def test_disabled_returns_not_available(self):
        with patch('utils.update_manager.APP_VERSION', '1.0.0'), \
             patch('utils.update_manager.UPDATE_CHECK_URL', 'http://test'), \
             patch('utils.update_manager.UPDATE_YANDEX_PUBLIC_KEY', 'test_key'), \
             patch('utils.update_manager.UPDATE_CHECK_ENABLED', False), \
             patch('utils.update_manager.API_BASE_URL', 'http://api'):
            from utils.update_manager import UpdateManager
            um_disabled = UpdateManager()
            result = um_disabled.check_for_updates()
            assert result['available'] is False
            assert result.get('disabled') is True

    def test_no_public_key(self):
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

    def test_update_available(self, um):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {
                '2.0.0': {'changelog': 'Новая версия', 'download_url': 'http://dl'}
            }
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.check_for_updates()
            assert result['available'] is True
            assert result['version'] == '2.0.0'

    def test_no_update_same_version(self, um):
        version_data = {
            'latest_version': '1.0.0',
            'versions': {}
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.check_for_updates()
            assert result['available'] is False

    def test_no_update_older_version(self, um):
        version_data = {
            'latest_version': '0.9.0',
            'versions': {}
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.check_for_updates()
            assert result['available'] is False

    def test_fetch_returns_none(self, um):
        with patch.object(um, '_fetch_version_json', return_value=None):
            result = um.check_for_updates()
            assert result['available'] is False
            assert 'error' in result

    def test_no_latest_version_key(self, um):
        with patch.object(um, '_fetch_version_json', return_value={}):
            result = um.check_for_updates()
            assert result['available'] is False

    def test_exception_during_check(self, um):
        with patch.object(um, '_fetch_version_json', side_effect=Exception('network error')):
            result = um.check_for_updates()
            assert result['available'] is False
            assert 'error' in result


# ==================== check_server_version ====================

class TestCheckServerVersion:
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
            assert result['server_version'] == '2.0.0'

    def test_server_error(self, um):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch('utils.update_manager.requests.get', return_value=mock_resp):
            result = um.check_server_version()
            assert 'error' in result

    def test_network_error(self, um):
        with patch('utils.update_manager.requests.get', side_effect=Exception('timeout')):
            result = um.check_server_version()
            assert 'error' in result


# ==================== download_update ====================

class TestDownloadUpdate:
    def test_download_success(self, um, tmp_path):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {
                '2.0.0': {'download_url': 'http://dl/file.exe'}
            }
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

    def test_download_no_version_data(self, um):
        with patch.object(um, '_fetch_version_json', return_value=None):
            result = um.download_update('2.0.0')
            assert result is None

    def test_download_version_not_found(self, um):
        version_data = {
            'latest_version': '2.0.0',
            'versions': {}
        }
        with patch.object(um, '_fetch_version_json', return_value=version_data):
            result = um.download_update('3.0.0')
            assert result is None
