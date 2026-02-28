# -*- coding: utf-8 -*-
"""
Полные тесты для utils/yandex_disk.py

Покрытие:
- YandexDiskManager: singleton (get_instance), конструктор
- build_contract_folder_path — чистая функция, различные параметры
- get_stage_folder_path — все стадии, вариации, префикс disk:
- _check_response: 200 OK, 401 → YandexDiskTokenError, 403, 429 → RateLimitError
- create_folder, file_exists, folder_exists — мок requests
- get_public_link — retry логика
- delete_folder, delete_file, copy_file, move_folder
- Edge cases: пустой токен, специальные символы

НЕ делаем реальных HTTP запросов — всё через mock/patch.
"""
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock

import pytest

# Корень проекта
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.yandex_disk import (
    YandexDiskManager,
    YandexDiskError,
    YandexDiskTokenError,
    YandexDiskRateLimitError,
    YandexDiskNetworkError,
)


# ============================================================================
# Фикстуры
# ============================================================================


@pytest.fixture(autouse=True)
def clear_singleton():
    """Очищаем кэш синглтонов перед каждым тестом."""
    YandexDiskManager._instances.clear()
    yield
    YandexDiskManager._instances.clear()


@pytest.fixture
def manager():
    """Создаёт экземпляр YandexDiskManager с тестовым токеном.

    Используем __new__ чтобы обойти __init__, который импортирует config.
    Все атрибуты задаём вручную.
    """
    mgr = YandexDiskManager.__new__(YandexDiskManager)
    mgr.token = 'test-token-12345'
    mgr.base_url = 'https://cloud-api.yandex.net/v1/disk'
    mgr.archive_root = '/test_root'
    mgr.session = MagicMock()
    return mgr


@pytest.fixture
def mock_response():
    """Фабрика фиктивных HTTP-ответов."""
    def _make(status_code=200, json_data=None):
        resp = MagicMock()
        resp.status_code = status_code
        resp.json.return_value = json_data or {}
        resp.text = ''
        return resp
    return _make


# ============================================================================
# Исключения — иерархия
# ============================================================================


class TestExceptionHierarchy:
    """Тесты иерархии исключений Яндекс.Диска."""

    def test_token_error_inherits_base(self):
        """YandexDiskTokenError наследует YandexDiskError."""
        assert issubclass(YandexDiskTokenError, YandexDiskError)

    def test_rate_limit_error_inherits_base(self):
        """YandexDiskRateLimitError наследует YandexDiskError."""
        assert issubclass(YandexDiskRateLimitError, YandexDiskError)

    def test_network_error_inherits_base(self):
        """YandexDiskNetworkError наследует YandexDiskError."""
        assert issubclass(YandexDiskNetworkError, YandexDiskError)

    def test_base_error_inherits_exception(self):
        """YandexDiskError наследует стандартный Exception."""
        assert issubclass(YandexDiskError, Exception)


# ============================================================================
# _check_response — обработка HTTP ответов
# ============================================================================


class TestCheckResponse:
    """Тесты внутреннего метода _check_response."""

    def test_200_ok(self, manager, mock_response):
        """200 — нет исключения, ответ возвращается."""
        resp = mock_response(200)
        result = manager._check_response(resp, "test_op")
        assert result is resp

    def test_401_raises_token_error(self, manager, mock_response):
        """401 — выбрасывается YandexDiskTokenError."""
        resp = mock_response(401)
        with pytest.raises(YandexDiskTokenError, match="token expired"):
            manager._check_response(resp, "test_op")

    def test_403_raises_token_error(self, manager, mock_response):
        """403 — выбрасывается YandexDiskTokenError (access forbidden)."""
        resp = mock_response(403)
        with pytest.raises(YandexDiskTokenError, match="access forbidden"):
            manager._check_response(resp, "test_op")

    def test_429_raises_rate_limit_error(self, manager, mock_response):
        """429 — выбрасывается YandexDiskRateLimitError."""
        resp = mock_response(429)
        with pytest.raises(YandexDiskRateLimitError, match="rate limit"):
            manager._check_response(resp, "test_op")

    def test_500_passes_through(self, manager, mock_response):
        """500 — не вызывает исключения в _check_response (обработка выше)."""
        resp = mock_response(500)
        result = manager._check_response(resp, "test_op")
        assert result.status_code == 500


# ============================================================================
# build_contract_folder_path — формирование пути папки
# ============================================================================


class TestBuildContractFolderPath:
    """Тесты формирования пути к папке договора."""

    def test_individual_project(self, manager):
        """Индивидуальный проект — папка 'Индивидуальные'."""
        path = manager.build_contract_folder_path(
            'ФЕСТИВАЛЬ', 'Индивидуальный', 'СПБ', 'Невский 1', 100
        )
        assert '/ФЕСТИВАЛЬ/Индивидуальные/СПБ/СПБ-Невский 1-100м2' in path

    def test_template_project(self, manager):
        """Шаблонный проект — папка 'Шаблонные'."""
        path = manager.build_contract_folder_path(
            'ПЕТРОВИЧ', 'Шаблонный', 'МСК', 'Тверская 5', 50
        )
        assert '/ПЕТРОВИЧ/Шаблонные/МСК/МСК-Тверская 5-50м2' in path

    def test_supervision_status(self, manager):
        """Статус 'АВТОРСКИЙ НАДЗОР' — папка 'Авторские надзоры'."""
        path = manager.build_contract_folder_path(
            'ФЕСТИВАЛЬ', 'Индивидуальный', 'ВН', 'Ленина 10', 75,
            status='АВТОРСКИЙ НАДЗОР'
        )
        assert 'Авторские надзоры' in path

    def test_unknown_project_type(self, manager):
        """Неизвестный тип проекта — используется как есть."""
        path = manager.build_contract_folder_path(
            'ФЕСТИВАЛЬ', 'Особый', 'СПБ', 'Невский 1', 100
        )
        assert '/Особый/' in path

    def test_address_with_slashes(self, manager):
        """Слеши в адресе заменяются на дефисы."""
        path = manager.build_contract_folder_path(
            'ФЕСТИВАЛЬ', 'Индивидуальный', 'СПБ', 'к1/к2\\к3', 80
        )
        assert 'к1-к2-к3' in path
        assert '/' not in path.split('/')[-1].replace('м2', '')  # В имени папки нет слешей

    def test_path_starts_with_archive_root(self, manager):
        """Путь начинается с archive_root."""
        path = manager.build_contract_folder_path(
            'ФЕСТИВАЛЬ', 'Индивидуальный', 'СПБ', 'Адрес', 100
        )
        assert path.startswith('/test_root/')


# ============================================================================
# get_stage_folder_path — путь к папке стадии
# ============================================================================


class TestGetStageFolderPath:
    """Тесты получения пути к папке стадии."""

    def test_measurement(self, manager):
        """Стадия 'measurement' — подпапка 'Замер'."""
        path = manager.get_stage_folder_path('/root/contract', 'measurement')
        assert path == '/root/contract/Замер'

    def test_stage1(self, manager):
        """Стадия 'stage1' — '1 стадия - Планировочное решение'."""
        path = manager.get_stage_folder_path('/root/contract', 'stage1')
        assert path == '/root/contract/1 стадия - Планировочное решение'

    def test_stage2_concept(self, manager):
        """Стадия 'stage2_concept' — вложенная папка."""
        path = manager.get_stage_folder_path('/root/contract', 'stage2_concept')
        assert path == '/root/contract/2 стадия - Концепция дизайна/Концепция-коллажи'

    def test_stage2_3d(self, manager):
        """Стадия 'stage2_3d' — '3D визуализация'."""
        path = manager.get_stage_folder_path('/root/contract', 'stage2_3d')
        assert path == '/root/contract/2 стадия - Концепция дизайна/3D визуализация'

    def test_stage3(self, manager):
        """Стадия 'stage3' — '3 стадия - Чертежный проект'."""
        path = manager.get_stage_folder_path('/root/contract', 'stage3')
        assert path == '/root/contract/3 стадия - Чертежный проект'

    def test_unknown_stage_returns_none(self, manager):
        """Неизвестная стадия — возвращает None."""
        result = manager.get_stage_folder_path('/root/contract', 'unknown_stage')
        assert result is None

    def test_variation_added(self, manager):
        """С вариацией добавляется подпапка 'Вариация N'."""
        path = manager.get_stage_folder_path('/root/contract', 'stage2_concept', variation=2)
        assert path.endswith('/Вариация 2')

    def test_variation_ignored_for_non_stage2(self, manager):
        """Вариация игнорируется для не-stage2 стадий."""
        path = manager.get_stage_folder_path('/root/contract', 'stage1', variation=3)
        assert 'Вариация' not in path

    def test_disk_prefix_stripped(self, manager):
        """Префикс 'disk:' удаляется из пути."""
        path = manager.get_stage_folder_path('disk:/root/contract', 'measurement')
        assert path == '/root/contract/Замер'
        assert not path.startswith('disk:')

    def test_references_stage(self, manager):
        """Стадия 'references' — подпапка 'Референсы'."""
        path = manager.get_stage_folder_path('/root/contract', 'references')
        assert path == '/root/contract/Референсы'

    def test_photo_documentation_stage(self, manager):
        """Стадия 'photo_documentation' — подпапка 'Фотофиксация'."""
        path = manager.get_stage_folder_path('/root/contract', 'photo_documentation')
        assert path == '/root/contract/Фотофиксация'


# ============================================================================
# create_folder — создание папки (мок requests)
# ============================================================================


class TestCreateFolder:
    """Тесты создания папки на Яндекс.Диске."""

    def test_create_folder_success(self, manager, mock_response):
        """Код 201 — папка создана, возвращает True."""
        manager.session.put.return_value = mock_response(201)
        result = manager.create_folder('/test/folder')
        assert result is True

    def test_create_folder_already_exists(self, manager, mock_response):
        """Код 409 — папка уже существует, возвращает True."""
        manager.session.put.return_value = mock_response(409)
        result = manager.create_folder('/test/folder')
        assert result is True

    def test_create_folder_error(self, manager, mock_response):
        """Код 500 — ошибка сервера, возвращает False."""
        manager.session.put.return_value = mock_response(500)
        result = manager.create_folder('/test/folder')
        assert result is False

    def test_create_folder_no_token(self, manager):
        """Без токена — возвращает False без HTTP запроса."""
        manager.token = None
        result = manager.create_folder('/test/folder')
        assert result is False
        manager.session.put.assert_not_called()

    def test_create_folder_401_raises_token_error(self, manager, mock_response):
        """Код 401 — _check_response выбрасывает YandexDiskTokenError, метод возвращает False."""
        manager.session.put.return_value = mock_response(401)
        # create_folder ловит все исключения
        result = manager.create_folder('/test/folder')
        assert result is False


# ============================================================================
# file_exists / folder_exists — проверка существования
# ============================================================================


class TestExistenceChecks:
    """Тесты проверки существования файлов и папок."""

    def test_file_exists_true(self, manager, mock_response):
        """Файл существует (200)."""
        manager.session.get.return_value = mock_response(200)
        assert manager.file_exists('/path/file.pdf') is True

    def test_file_exists_false(self, manager, mock_response):
        """Файл не найден (404)."""
        manager.session.get.return_value = mock_response(404)
        assert manager.file_exists('/path/file.pdf') is False

    def test_file_exists_no_token(self, manager):
        """Без токена — False без HTTP запроса."""
        manager.token = None
        assert manager.file_exists('/path/file.pdf') is False

    def test_folder_exists_true(self, manager, mock_response):
        """Папка существует (200)."""
        manager.session.get.return_value = mock_response(200)
        assert manager.folder_exists('/path/folder') is True

    def test_folder_exists_false(self, manager, mock_response):
        """Папка не найдена (404)."""
        manager.session.get.return_value = mock_response(404)
        assert manager.folder_exists('/path/folder') is False

    def test_folder_exists_no_token(self, manager):
        """Без токена — False."""
        manager.token = None
        assert manager.folder_exists('/path/folder') is False


# ============================================================================
# delete_folder / delete_file — удаление
# ============================================================================


class TestDeletion:
    """Тесты удаления файлов и папок."""

    def test_delete_folder_success(self, manager, mock_response):
        """Успешное удаление папки (204)."""
        manager.session.delete.return_value = mock_response(204)
        assert manager.delete_folder('/path/folder') is True

    def test_delete_folder_not_found(self, manager, mock_response):
        """Папка не найдена при удалении (404) — считается успехом."""
        manager.session.delete.return_value = mock_response(404)
        assert manager.delete_folder('/path/folder') is True

    def test_delete_folder_no_token(self, manager):
        """Удаление без токена — False."""
        manager.token = None
        assert manager.delete_folder('/path/folder') is False

    def test_delete_file_success(self, manager, mock_response):
        """Успешное удаление файла (202)."""
        manager.session.delete.return_value = mock_response(202)
        assert manager.delete_file('/path/file.pdf') is True

    def test_delete_file_not_found(self, manager, mock_response):
        """Файл не найден при удалении (404) — считается успехом."""
        manager.session.delete.return_value = mock_response(404)
        assert manager.delete_file('/path/file.pdf') is True


# ============================================================================
# move_folder / copy_file
# ============================================================================


class TestMoveAndCopy:
    """Тесты перемещения папок и копирования файлов."""

    def test_move_folder_success(self, manager, mock_response):
        """Успешное перемещение папки (201)."""
        manager.session.post.return_value = mock_response(201)
        assert manager.move_folder('/from', '/to') is True

    def test_move_folder_no_token(self, manager):
        """Перемещение без токена — False."""
        manager.token = None
        assert manager.move_folder('/from', '/to') is False

    def test_copy_file_success(self, manager, mock_response):
        """Успешное копирование файла (201)."""
        manager.session.post.return_value = mock_response(201)
        assert manager.copy_file('/from/file', '/to/file') is True

    def test_copy_file_error(self, manager, mock_response):
        """Ошибка при копировании (500) — False."""
        manager.session.post.return_value = mock_response(500)
        assert manager.copy_file('/from/file', '/to/file') is False

    def test_copy_file_no_token(self, manager):
        """Копирование без токена — False."""
        manager.token = None
        assert manager.copy_file('/from/file', '/to/file') is False


# ============================================================================
# get_public_link — retry логика
# ============================================================================


class TestGetPublicLink:
    """Тесты получения публичной ссылки с retry."""

    @patch('utils.yandex_disk.time')
    def test_success_first_attempt(self, mock_time, manager, mock_response):
        """Успешное получение ссылки с первой попытки."""
        # publish — 200, meta — 200 с public_url
        publish_resp = mock_response(200)
        meta_resp = mock_response(200, json_data={'public_url': 'https://disk.yandex.ru/i/abc123'})

        manager.session.put.return_value = publish_resp
        manager.session.get.return_value = meta_resp

        result = manager.get_public_link('/path/file.pdf')
        assert result == 'https://disk.yandex.ru/i/abc123'

    @patch('utils.yandex_disk.time')
    def test_fallback_to_public_key(self, mock_time, manager, mock_response):
        """Если public_url нет, формируется из public_key."""
        publish_resp = mock_response(200)
        meta_resp = mock_response(200, json_data={'public_key': 'xyz789'})

        manager.session.put.return_value = publish_resp
        manager.session.get.return_value = meta_resp

        result = manager.get_public_link('/path/file.pdf')
        assert 'xyz789' in result

    @patch('utils.yandex_disk.time')
    def test_returns_empty_after_all_retries(self, mock_time, manager, mock_response):
        """После исчерпания попыток — пустая строка."""
        # publish OK, но meta не содержит public_url/public_key
        publish_resp = mock_response(200)
        meta_resp = mock_response(200, json_data={})

        manager.session.put.return_value = publish_resp
        manager.session.get.return_value = meta_resp

        result = manager.get_public_link('/path/file.pdf', max_retries=2)
        assert result == ''

    @patch('utils.yandex_disk.time')
    def test_retry_on_publish_failure(self, mock_time, manager, mock_response):
        """Retry при неуспешном publish (500)."""
        fail_resp = mock_response(500)
        manager.session.put.return_value = fail_resp

        result = manager.get_public_link('/path/file.pdf', max_retries=2)
        assert result == ''
        # put вызывается max_retries раз
        assert manager.session.put.call_count == 2


# ============================================================================
# MAX_FILE_SIZE_MB — константа
# ============================================================================


class TestConstants:
    """Тесты констант модуля."""

    def test_max_file_size_mb(self):
        """MAX_FILE_SIZE_MB = 200."""
        assert YandexDiskManager.MAX_FILE_SIZE_MB == 200

    def test_max_file_size_is_int(self):
        """MAX_FILE_SIZE_MB — целое число."""
        assert isinstance(YandexDiskManager.MAX_FILE_SIZE_MB, int)
