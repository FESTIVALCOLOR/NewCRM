# -*- coding: utf-8 -*-
"""
Тесты utils/yandex_disk.py — работа с Яндекс.Диском через REST API.

Покрытие:
  - TestYandexDiskInit (3) — инициализация менеджера
  - TestCheckResponse (4) — обработка кодов ответа API
  - TestCreateFolder (4) — создание папок
  - TestUploadFile (4) — загрузка файлов
  - TestDownloadFile (2) — скачивание файлов
  - TestDeleteOperations (3) — удаление файлов/папок
  - TestFileExists (3) — проверка существования
  - TestBuildContractFolderPath (4) — формирование путей
  - TestGetStageFolderPath (3) — пути к стадиям проекта
ИТОГО: 30 тестов
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture
def yd_manager():
    """Создаёт YandexDiskManager с мокнутыми зависимостями."""
    with patch('utils.yandex_disk.requests.Session') as mock_session_cls:
        mock_session = MagicMock()
        mock_session_cls.return_value = mock_session
        with patch.dict('sys.modules', {'config': MagicMock(
            YANDEX_DISK_TOKEN='test_token',
            YANDEX_DISK_PROJECTS='/Проекты'
        )}):
            from utils.yandex_disk import YandexDiskManager
            # Очищаем кеш singleton
            YandexDiskManager._instances.clear()
            manager = YandexDiskManager(token='test_oauth_token')
            manager.archive_root = '/Проекты'
            # Подменяем сессию
            manager.session = mock_session
            yield manager
            YandexDiskManager._instances.clear()


def _make_response(status_code, json_data=None, text=''):
    """Создаёт мок HTTP-ответа."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    return resp


class TestYandexDiskInit:
    """Тесты инициализации YandexDiskManager."""

    def test_token_stored(self, yd_manager):
        """Токен сохраняется в атрибуте."""
        assert yd_manager.token == 'test_oauth_token'

    def test_base_url_set(self, yd_manager):
        """Базовый URL API установлен."""
        assert yd_manager.base_url == 'https://cloud-api.yandex.net/v1/disk'

    def test_max_file_size_defined(self, yd_manager):
        """Лимит размера файла определён."""
        assert yd_manager.MAX_FILE_SIZE_MB == 200


class TestCheckResponse:
    """Тесты обработки кодов ответа API."""

    def test_401_raises_token_error(self, yd_manager):
        """401 — YandexDiskTokenError."""
        from utils.yandex_disk import YandexDiskTokenError
        resp = _make_response(401)
        with pytest.raises(YandexDiskTokenError):
            yd_manager._check_response(resp, "test")

    def test_403_raises_token_error(self, yd_manager):
        """403 — YandexDiskTokenError (доступ запрещён)."""
        from utils.yandex_disk import YandexDiskTokenError
        resp = _make_response(403)
        with pytest.raises(YandexDiskTokenError):
            yd_manager._check_response(resp, "test")

    def test_429_raises_rate_limit_error(self, yd_manager):
        """429 — YandexDiskRateLimitError."""
        from utils.yandex_disk import YandexDiskRateLimitError
        resp = _make_response(429)
        with pytest.raises(YandexDiskRateLimitError):
            yd_manager._check_response(resp, "test")

    def test_200_no_error(self, yd_manager):
        """200 — нет ошибки, возвращает response."""
        resp = _make_response(200)
        result = yd_manager._check_response(resp, "test")
        assert result is resp


class TestCreateFolder:
    """Тесты создания папок на Яндекс.Диске."""

    def test_create_folder_success(self, yd_manager):
        """Успешное создание папки (201)."""
        yd_manager.session.put.return_value = _make_response(201)
        result = yd_manager.create_folder('/test/folder')
        assert result is True

    def test_create_folder_already_exists(self, yd_manager):
        """Папка уже существует (409) — возвращает True."""
        yd_manager.session.put.return_value = _make_response(409)
        result = yd_manager.create_folder('/existing/folder')
        assert result is True

    def test_create_folder_error(self, yd_manager):
        """Ошибка сервера (500) — возвращает False."""
        yd_manager.session.put.return_value = _make_response(500)
        result = yd_manager.create_folder('/error/folder')
        assert result is False

    def test_create_folder_no_token(self, yd_manager):
        """Без токена — возвращает False."""
        yd_manager.token = None
        result = yd_manager.create_folder('/test/folder')
        assert result is False


class TestUploadFile:
    """Тесты загрузки файлов на Яндекс.Диск."""

    def test_upload_file_success(self, yd_manager, tmp_path):
        """Успешная загрузка файла."""
        # Создаём временный файл
        test_file = tmp_path / 'test.txt'
        test_file.write_text('тестовое содержимое')

        # Мокаем получение ссылки загрузки
        yd_manager.session.get.return_value = _make_response(200, {'href': 'https://upload.example.com/file'})
        # Мокаем саму загрузку
        yd_manager.session.put.return_value = _make_response(201)

        result = yd_manager.upload_file(str(test_file), '/remote/test.txt')
        assert result is True

    def test_upload_file_too_large(self, yd_manager, tmp_path):
        """Файл больше лимита — Exception."""
        test_file = tmp_path / 'large.bin'
        # Создаём файл — мокаем его размер через os.path.getsize
        test_file.write_bytes(b'x')

        with patch('os.path.getsize', return_value=250 * 1024 * 1024):
            with pytest.raises(Exception, match="File too large"):
                yd_manager.upload_file(str(test_file), '/remote/large.bin')

    def test_upload_get_link_error(self, yd_manager, tmp_path):
        """Ошибка получения ссылки загрузки."""
        test_file = tmp_path / 'test.txt'
        test_file.write_text('content')

        yd_manager.session.get.return_value = _make_response(500, text='Server Error')

        with pytest.raises(Exception, match="Ошибка получения ссылки"):
            yd_manager.upload_file(str(test_file), '/remote/test.txt')

    def test_upload_missing_href(self, yd_manager, tmp_path):
        """В ответе нет поля href — Exception."""
        test_file = tmp_path / 'test.txt'
        test_file.write_text('content')

        yd_manager.session.get.return_value = _make_response(200, {'no_href': 'value'})

        with pytest.raises(Exception, match="href"):
            yd_manager.upload_file(str(test_file), '/remote/test.txt')


class TestDownloadFile:
    """Тесты скачивания файлов."""

    def test_download_file_success(self, yd_manager, tmp_path):
        """Успешное скачивание файла."""
        download_path = str(tmp_path / 'downloaded.txt')

        # Мок получения ссылки
        yd_manager.session.get.side_effect = [
            _make_response(200, {'href': 'https://download.example.com/file'}),
            MagicMock(status_code=200, iter_content=lambda chunk_size: [b'data']),
        ]

        yd_manager.download_file('/remote/file.txt', download_path)
        assert os.path.exists(download_path)

    def test_download_link_error(self, yd_manager, tmp_path):
        """Ошибка получения ссылки для скачивания."""
        yd_manager.session.get.return_value = _make_response(404)

        with pytest.raises(Exception, match="download link"):
            yd_manager.download_file('/nonexistent.txt', str(tmp_path / 'out.txt'))


class TestDeleteOperations:
    """Тесты удаления файлов и папок."""

    def test_delete_folder_success(self, yd_manager):
        """Успешное удаление папки (204)."""
        yd_manager.session.delete.return_value = _make_response(204)
        result = yd_manager.delete_folder('/old/folder')
        assert result is True

    def test_delete_folder_not_found(self, yd_manager):
        """Папка не найдена (404) — True (уже удалена)."""
        yd_manager.session.delete.return_value = _make_response(404)
        result = yd_manager.delete_folder('/missing/folder')
        assert result is True

    def test_delete_file_no_token(self, yd_manager):
        """Удаление без токена — False."""
        yd_manager.token = None
        result = yd_manager.delete_file('/some/file.txt')
        assert result is False


class TestFileExists:
    """Тесты проверки существования файлов."""

    def test_file_exists_true(self, yd_manager):
        """Файл существует (200)."""
        yd_manager.session.get.return_value = _make_response(200)
        assert yd_manager.file_exists('/existing/file.txt') is True

    def test_file_not_exists(self, yd_manager):
        """Файл не существует (404)."""
        yd_manager.session.get.return_value = _make_response(404)
        assert yd_manager.file_exists('/missing/file.txt') is False

    def test_file_exists_no_token(self, yd_manager):
        """Без токена — False."""
        yd_manager.token = None
        assert yd_manager.file_exists('/any/file.txt') is False


class TestBuildContractFolderPath:
    """Тесты формирования пути к папке договора."""

    def test_individual_project(self, yd_manager):
        """Индивидуальный проект — правильный путь."""
        path = yd_manager.build_contract_folder_path(
            agent_type='ФЕСТИВАЛЬ',
            project_type='Индивидуальный',
            city='СПБ',
            address='Невский 10',
            area='85'
        )
        assert '/Проекты/ФЕСТИВАЛЬ/Индивидуальные/СПБ/СПБ-Невский 10-85м2' == path

    def test_template_project(self, yd_manager):
        """Шаблонный проект — правильный путь."""
        path = yd_manager.build_contract_folder_path(
            agent_type='ПЕТРОВИЧ',
            project_type='Шаблонный',
            city='МСК',
            address='Тверская 5',
            area='60'
        )
        assert '/Проекты/ПЕТРОВИЧ/Шаблонные/МСК/МСК-Тверская 5-60м2' == path

    def test_supervision_status(self, yd_manager):
        """Статус АВТОРСКИЙ НАДЗОР — папка 'Авторские надзоры'."""
        path = yd_manager.build_contract_folder_path(
            agent_type='ФЕСТИВАЛЬ',
            project_type='Индивидуальный',
            city='ВН',
            address='Ленина 1',
            area='120',
            status='АВТОРСКИЙ НАДЗОР'
        )
        assert 'Авторские надзоры' in path

    def test_address_with_slashes_cleaned(self, yd_manager):
        """Слэши в адресе заменяются на дефисы."""
        path = yd_manager.build_contract_folder_path(
            agent_type='ФЕСТИВАЛЬ',
            project_type='Индивидуальный',
            city='СПБ',
            address='ул/Мира/д.5',
            area='70'
        )
        assert '/' not in path.split('СПБ-')[1].split('-70м2')[0].replace('/', '')
        assert 'ул-Мира-д.5' in path


class TestGetStageFolderPath:
    """Тесты получения пути к папке стадии."""

    def test_measurement_stage(self, yd_manager):
        """Стадия замера."""
        path = yd_manager.get_stage_folder_path('/contract/folder', 'measurement')
        assert path == '/contract/folder/Замер'

    def test_stage2_with_variation(self, yd_manager):
        """Стадия 2 с вариацией."""
        path = yd_manager.get_stage_folder_path('/contract/folder', 'stage2_concept', variation=2)
        assert path == '/contract/folder/2 стадия - Концепция дизайна/Концепция-коллажи/Вариация 2'

    def test_unknown_stage_returns_none(self, yd_manager):
        """Неизвестная стадия — None."""
        path = yd_manager.get_stage_folder_path('/contract/folder', 'unknown_stage')
        assert path is None
