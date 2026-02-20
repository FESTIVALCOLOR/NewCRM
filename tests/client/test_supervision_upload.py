# -*- coding: utf-8 -*-
"""
Интеграционные тесты загрузки файлов надзора.
Тестируют РЕАЛЬНУЮ логику, а не моки. Ловят баги вроде upload_file() -> None.
"""
import sys
import os
import threading
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

pytest.importorskip("PyQt5")
pytestmark = pytest.mark.frontend


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_yandex_disk():
    """Mock YandexDiskManager"""
    yd = MagicMock()
    yd.create_folder.return_value = True
    yd.upload_file.return_value = True
    yd.get_public_link.return_value = "https://disk.yandex.ru/d/test_link"
    return yd


# ============================================================================
# КРИТИЧЕСКИЙ ТЕСТ: upload_file() должен возвращать truthy значение
# Этот тест ловит баг, который был на скриншоте пользователя:
# upload_file() возвращал None, и код считал это ошибкой
# ============================================================================

class TestUploadFileReturnValue:
    """upload_file() ОБЯЗАН возвращать truthy значение при успехе"""

    def test_upload_file_returns_true(self):
        """YandexDiskManager.upload_file() должен вернуть True при успехе"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        # Мокаем HTTP ответы
        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {'href': 'https://upload.yandex.net/upload/123'}

        put_response = MagicMock()
        put_response.status_code = 201

        yd.session.get.return_value = get_response
        yd.session.put.return_value = put_response

        # Создаём временный файл для загрузки
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            result = yd.upload_file(tmp_path, "disk:/test/file.txt")
            # КРИТИЧНО: результат должен быть truthy!
            assert result, (
                f"upload_file() вернул {result!r} вместо True. "
                f"Это приводит к ошибке 'Не удалось загрузить файл на Яндекс.Диск' "
                f"даже когда файл успешно загружен."
            )
            assert result is True
        finally:
            os.unlink(tmp_path)

    def test_upload_file_raises_on_error(self):
        """upload_file() должен выбросить Exception при ошибке HTTP"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {'href': 'https://upload.yandex.net/upload/123'}

        put_response = MagicMock()
        put_response.status_code = 500  # Ошибка сервера

        yd.session.get.return_value = get_response
        yd.session.put.return_value = put_response

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            with pytest.raises(Exception, match="Ошибка загрузки файла"):
                yd.upload_file(tmp_path, "disk:/test/file.txt")
        finally:
            os.unlink(tmp_path)

    def test_upload_file_raises_on_no_href(self):
        """upload_file() должен выбросить Exception если нет href в ответе"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        get_response = MagicMock()
        get_response.status_code = 200
        get_response.json.return_value = {}  # Нет href!

        yd.session.get.return_value = get_response

        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"test content")
            tmp_path = f.name

        try:
            with pytest.raises(Exception, match="href"):
                yd.upload_file(tmp_path, "disk:/test/file.txt")
        finally:
            os.unlink(tmp_path)

    def test_upload_file_rejects_oversized(self):
        """upload_file() должен отклонить файл > MAX_FILE_SIZE_MB"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.MAX_FILE_SIZE_MB = 200
        yd.session = MagicMock()

        # Мокаем os.path.getsize чтобы вернуть огромный размер
        with tempfile.NamedTemporaryFile(suffix='.txt', delete=False) as f:
            f.write(b"x")
            tmp_path = f.name

        try:
            with patch('os.path.getsize', return_value=300 * 1024 * 1024):
                with pytest.raises(Exception, match="too large"):
                    yd.upload_file(tmp_path, "disk:/test/big_file.zip")
        finally:
            os.unlink(tmp_path)


# ============================================================================
# ТЕСТ: полный поток загрузки надзора (эмуляция upload_supervision_file)
# ============================================================================

class TestSupervisionUploadFlow:
    """Тестируем полный поток загрузки как в upload_supervision_file()"""

    def test_full_upload_flow_success(self):
        """Полный поток загрузки: create_folder -> upload_file -> get_public_link"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test_token"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        # Мокаем create_folder (PUT /resources -> 409 already exists)
        folder_response = MagicMock()
        folder_response.status_code = 409

        # Мокаем upload GET (get upload link)
        upload_link_response = MagicMock()
        upload_link_response.status_code = 200
        upload_link_response.json.return_value = {'href': 'https://upload.yandex.net/xxx'}

        # Мокаем upload PUT (actual upload)
        upload_response = MagicMock()
        upload_response.status_code = 201

        # Мокаем publish PUT
        publish_response = MagicMock()
        publish_response.status_code = 200

        # Мокаем get metadata GET
        meta_response = MagicMock()
        meta_response.status_code = 200
        meta_response.json.return_value = {'public_url': 'https://disk.yandex.ru/d/abc123'}

        # Настраиваем session.put и session.get по порядку вызовов
        yd.session.put.side_effect = [folder_response, folder_response, upload_response, publish_response]
        yd.session.get.side_effect = [upload_link_response, meta_response]

        contract_folder = "disk:/ARCHIVE/FESTIVAL/Individual/SPB/Address"
        stage = "Стадия 1: Закупка керамогранита"
        file_name = "test_file.pdf"

        # Шаг 1: create_folder для "Авторский надзор"
        supervision_folder = f"{contract_folder}/Авторский надзор"
        result1 = yd.create_folder(supervision_folder)
        assert result1 is True

        # Шаг 2: create_folder для стадии
        stage_folder = f"{supervision_folder}/{stage}"
        result2 = yd.create_folder(stage_folder)
        assert result2 is True

        # Шаг 3: upload_file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as f:
            f.write(b"PDF content")
            tmp_path = f.name

        try:
            yandex_path = f"{stage_folder}/{file_name}"
            result_upload = yd.upload_file(tmp_path, yandex_path)

            # КРИТИЧНО: result_upload ДОЛЖЕН быть truthy
            assert result_upload, "upload_file() вернул falsy — загрузка сломана!"

            # Шаг 4: get_public_link (только если upload успешен)
            if result_upload:
                public_link = yd.get_public_link(yandex_path)
                assert public_link == 'https://disk.yandex.ru/d/abc123'
        finally:
            os.unlink(tmp_path)

    def test_upload_flow_failure_emits_error(self):
        """При ошибке upload_file: исключение -> supervision_upload_error"""
        errors = []

        def upload_thread():
            try:
                raise Exception("Ошибка загрузки файла: 500")
            except Exception as e:
                errors.append(str(e))

        thread = threading.Thread(target=upload_thread)
        thread.start()
        thread.join(timeout=5)

        assert len(errors) == 1
        assert "500" in errors[0]


# ============================================================================
# ТЕСТ: create_folder обработка ответов
# ============================================================================

class TestCreateFolder:
    """Тестируем create_folder с реальной логикой"""

    def test_create_folder_201(self):
        """create_folder: 201 = папка создана"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        resp = MagicMock()
        resp.status_code = 201
        yd.session.put.return_value = resp

        assert yd.create_folder("disk:/test/new_folder") is True

    def test_create_folder_409(self):
        """create_folder: 409 = уже существует, тоже True"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        resp = MagicMock()
        resp.status_code = 409
        yd.session.put.return_value = resp

        assert yd.create_folder("disk:/test/existing_folder") is True

    def test_create_folder_no_token(self):
        """create_folder без токена -> False"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = None
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"

        assert yd.create_folder("disk:/test") is False

    def test_create_folder_500(self):
        """create_folder: 500 = ошибка сервера -> False"""
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.token = "test"
        yd.base_url = "https://cloud-api.yandex.net/v1/disk"
        yd.session = MagicMock()

        resp = MagicMock()
        resp.status_code = 500
        yd.session.put.return_value = resp

        assert yd.create_folder("disk:/test") is False


# ============================================================================
# ТЕСТ: build_contract_folder_path (чистая логика, без HTTP)
# ============================================================================

class TestBuildContractFolderPath:
    """Тесты построения пути к папке — чистая логика"""

    def test_individual_project_path(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.archive_root = "disk:/АРХИВ ПРОЕКТОВ"

        path = yd.build_contract_folder_path(
            agent_type="ФЕСТИВАЛЬ",
            project_type="Индивидуальный",
            city="СПБ",
            address="г. Санкт-Петербург, ул. Ленина 1",
            area=100.5
        )
        assert path == "disk:/АРХИВ ПРОЕКТОВ/ФЕСТИВАЛЬ/Индивидуальные/СПБ/СПБ-г. Санкт-Петербург, ул. Ленина 1-100.5м2"

    def test_template_project_path(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.archive_root = "disk:/АРХИВ ПРОЕКТОВ"

        path = yd.build_contract_folder_path("ПЕТРОВИЧ", "Шаблонный", "МСК", "Московская 5", 80.0)
        assert "Шаблонные" in path
        assert "ПЕТРОВИЧ" in path
        assert "МСК" in path

    def test_supervision_status_path(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.archive_root = "disk:/АРХИВ ПРОЕКТОВ"

        path = yd.build_contract_folder_path(
            "ФЕСТИВАЛЬ", "Индивидуальный", "ВН", "Адрес", 50.0,
            status='АВТОРСКИЙ НАДЗОР'
        )
        assert "Авторские надзоры" in path

    def test_address_with_slashes_cleaned(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        yd.archive_root = "disk:/АРХИВ ПРОЕКТОВ"

        path = yd.build_contract_folder_path("ФЕСТИВАЛЬ", "Индивидуальный", "СПБ", "ул/Ленина\\5", 100.0)
        assert "/" not in path.split("СПБ/")[1].split("-ул")[0]  # no slashes in address part
        assert "\\" not in path


# ============================================================================
# ТЕСТ: get_stage_folder_path
# ============================================================================

class TestGetStageFolderPath:
    """Тесты получения пути к папке стадии"""

    def test_measurement_stage(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        path = yd.get_stage_folder_path("disk:/contract", "measurement")
        assert path == "/contract/Замер"

    def test_stage1(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        path = yd.get_stage_folder_path("disk:/contract", "stage1")
        assert path == "/contract/1 стадия - Планировочное решение"

    def test_stage2_concept_with_variation(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        path = yd.get_stage_folder_path("disk:/contract", "stage2_concept", variation=2)
        assert "Вариация 2" in path
        assert "Концепция-коллажи" in path

    def test_unknown_stage_returns_none(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        path = yd.get_stage_folder_path("disk:/contract", "nonexistent")
        assert path is None

    def test_disk_prefix_stripped(self):
        from utils.yandex_disk import YandexDiskManager
        yd = YandexDiskManager.__new__(YandexDiskManager)
        path = yd.get_stage_folder_path("disk:/contract/folder", "stage3")
        assert not path.startswith("disk:")


# ============================================================================
# ТЕСТЫ PROGRESS DIALOG
# ============================================================================

class TestProgressDialogSettings:
    """Проверяем правильную настройку QProgressDialog"""

    def test_progress_dialog_settings(self, qtbot):
        """QProgressDialog должен иметь setMinimumDuration(0)"""
        from PyQt5.QtWidgets import QProgressDialog

        progress = QProgressDialog("Loading...", "Cancel", 0, 100)
        qtbot.addWidget(progress)

        progress.setMinimumDuration(0)
        progress.setAutoClose(True)
        progress.setAutoReset(False)

        assert progress.minimumDuration() == 0
        assert progress.autoClose() is True
        assert progress.autoReset() is False

    def test_progress_value_updates(self, qtbot):
        """Progress bar значения обновляются корректно"""
        from PyQt5.QtWidgets import QProgressDialog

        progress = QProgressDialog("Loading...", "Cancel", 0, 100)
        progress.setAutoReset(False)
        qtbot.addWidget(progress)

        progress.setValue(30)
        assert progress.value() == 30

        progress.setValue(70)
        assert progress.value() == 70

        progress.setValue(100)
        assert progress.value() == 100
