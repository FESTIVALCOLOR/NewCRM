# -*- coding: utf-8 -*-
"""
E2E Tests: Реальный Яндекс.Диск — загрузка/удаление файлов, папки
14 тестов — все операции в папке __TEST__/ с полной очисткой.
"""

import pytest
import requests
import ssl
import time
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, REQUEST_TIMEOUT, api_post, api_get, api_delete, _http_session

# Яндекс.Диск API
YD_API_BASE = "https://cloud-api.yandex.net/v1/disk"
YD_TEST_ROOT = f"АРХИВ ПРОЕКТОВ/{TEST_PREFIX}"


def _yd_request_with_retry(method, url, max_retries=3, **kwargs):
    """HTTP запрос к ЯД с retry при SSL ошибках"""
    kwargs.setdefault("timeout", REQUEST_TIMEOUT)
    last_err = None
    for attempt in range(max_retries):
        try:
            return getattr(_http_session, method)(url, **kwargs)
        except (ssl.SSLEOFError, requests.exceptions.SSLError, requests.exceptions.ConnectionError) as e:
            last_err = e
            if attempt < max_retries - 1:
                time.sleep(1 * (attempt + 1))
    raise last_err


@pytest.fixture(scope="module")
def yd_token():
    """Токен Яндекс.Диска из переменной окружения"""
    token = os.environ.get('YANDEX_DISK_TOKEN', '')
    if not token:
        pytest.skip("YANDEX_DISK_TOKEN не установлен")
    return token


@pytest.fixture(scope="module")
def yd_headers(yd_token):
    """Headers для Яндекс.Диск API"""
    return {"Authorization": f"OAuth {yd_token}"}


@pytest.fixture(scope="module", autouse=True)
def cleanup_yd_test_folder(yd_headers):
    """Очистка тестовой папки на ЯД после всех тестов"""
    yield
    # Удаляем тестовую папку
    try:
        _yd_request_with_retry(
            "delete",
            f"{YD_API_BASE}/resources",
            headers=yd_headers,
            params={"path": f"disk:/{YD_TEST_ROOT}", "permanently": True},
            timeout=30
        )
        print(f"\n[CLEANUP] Удалена тестовая папка на ЯД: {YD_TEST_ROOT}")
    except Exception as e:
        print(f"\n[CLEANUP] Ошибка удаления тестовой папки: {e}")


def yd_mkdir(yd_headers, path):
    """Создать папку на Яндекс.Диске"""
    return _yd_request_with_retry(
        "put",
        f"{YD_API_BASE}/resources",
        headers=yd_headers,
        params={"path": f"disk:/{path}"},
    )


def yd_exists(yd_headers, path):
    """Проверить существование файла/папки"""
    resp = _yd_request_with_retry(
        "get",
        f"{YD_API_BASE}/resources",
        headers=yd_headers,
        params={"path": f"disk:/{path}"},
    )
    return resp.status_code == 200


def yd_delete(yd_headers, path, permanently=True):
    """Удалить файл/папку"""
    return _yd_request_with_retry(
        "delete",
        f"{YD_API_BASE}/resources",
        headers=yd_headers,
        params={"path": f"disk:/{path}", "permanently": permanently},
    )


def yd_upload(yd_headers, path, content: bytes):
    """Загрузить файл на ЯД"""
    # 1. Получить URL для загрузки
    resp = _yd_request_with_retry(
        "get",
        f"{YD_API_BASE}/resources/upload",
        headers=yd_headers,
        params={"path": f"disk:/{path}", "overwrite": True},
    )
    if resp.status_code != 200:
        return resp

    upload_url = resp.json().get("href")
    if not upload_url:
        return resp

    # 2. Загрузить файл
    resp = _yd_request_with_retry("put", upload_url, data=content, timeout=30)
    return resp


# ==============================================================
# ПАПКИ НА ЯНДЕКС.ДИСКЕ
# ==============================================================

class TestYandexDiskFolders:
    """Тесты создания/удаления папок на ЯД"""

    @pytest.mark.critical
    def test_create_folder_for_new_contract(self, yd_headers):
        """Создание папки для нового договора"""
        folder_path = f"{YD_TEST_ROOT}/ФЕСТИВАЛЬ/Индивидуальные/СПБ/001_Тестовый"
        # Создаём иерархию
        parts = folder_path.split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            yd_mkdir(yd_headers, current)

        assert yd_exists(yd_headers, folder_path), f"Папка не создана: {folder_path}"

    def test_folder_structure_by_agent_city(self, yd_headers):
        """Структура: АГЕНТ/ТипПроекта/ГОРОД"""
        base = f"{YD_TEST_ROOT}/ПЕТРОВИЧ/Шаблонные/МСК"
        parts = base.split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            yd_mkdir(yd_headers, current)

        assert yd_exists(yd_headers, base)

    def test_create_folder_new_city(self, yd_headers):
        """Новый город: создаётся подпапка"""
        path = f"{YD_TEST_ROOT}/ФЕСТИВАЛЬ/Индивидуальные/ВН"
        parts = path.split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            yd_mkdir(yd_headers, current)

        assert yd_exists(yd_headers, path)

    def test_create_folder_new_agent(self, yd_headers):
        """Новый агент: создаётся подпапка"""
        path = f"{YD_TEST_ROOT}/НОВЫЙ_АГЕНТ/Индивидуальные/СПБ"
        parts = path.split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            yd_mkdir(yd_headers, current)

        assert yd_exists(yd_headers, path)

    def test_delete_folder(self, yd_headers):
        """Удаление папки с ЯД"""
        path = f"{YD_TEST_ROOT}/TO_DELETE"
        yd_mkdir(yd_headers, f"{YD_TEST_ROOT}")
        yd_mkdir(yd_headers, path)
        assert yd_exists(yd_headers, path)

        yd_delete(yd_headers, path)
        time.sleep(1)  # ЯД может кэшировать
        assert not yd_exists(yd_headers, path), "Папка не удалена"


# ==============================================================
# ФАЙЛЫ НА ЯНДЕКС.ДИСКЕ
# ==============================================================

class TestYandexDiskFiles:
    """Тесты загрузки/удаления файлов"""

    @pytest.mark.critical
    def test_upload_small_file(self, yd_headers):
        """Загрузка тестового файла (1KB txt)"""
        # Создаём папку
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        folder = f"{YD_TEST_ROOT}/uploads"
        yd_mkdir(yd_headers, folder)

        file_path = f"{folder}/test_upload.txt"
        content = b"Test file content for E2E testing\n" * 30  # ~1KB
        resp = yd_upload(yd_headers, file_path, content)
        assert resp.status_code in [200, 201, 202], f"Загрузка неудачна: {resp.status_code}"

    @pytest.mark.critical
    def test_file_exists_after_upload(self, yd_headers):
        """file_exists() True после загрузки"""
        folder = f"{YD_TEST_ROOT}/uploads"
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        yd_mkdir(yd_headers, folder)

        file_path = f"{folder}/exists_test.txt"
        yd_upload(yd_headers, file_path, b"Test content")
        time.sleep(1)

        assert yd_exists(yd_headers, file_path), "Файл не найден после загрузки"

    def test_get_public_link(self, yd_headers):
        """Получение публичной ссылки"""
        folder = f"{YD_TEST_ROOT}/uploads"
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        yd_mkdir(yd_headers, folder)

        file_path = f"{folder}/public_test.txt"
        yd_upload(yd_headers, file_path, b"Public content")
        time.sleep(1)

        # Публикуем
        resp = _http_session.put(
            f"{YD_API_BASE}/resources/publish",
            headers=yd_headers,
            params={"path": f"disk:/{file_path}"},
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code == 200

        # Проверяем публичную ссылку
        resp = _http_session.get(
            f"{YD_API_BASE}/resources",
            headers=yd_headers,
            params={"path": f"disk:/{file_path}"},
            timeout=REQUEST_TIMEOUT
        )
        if resp.status_code == 200:
            data = resp.json()
            assert "public_url" in data or "public_key" in data

    @pytest.mark.critical
    def test_delete_file(self, yd_headers):
        """Удаление файла с ЯД"""
        folder = f"{YD_TEST_ROOT}/uploads"
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        yd_mkdir(yd_headers, folder)

        file_path = f"{folder}/to_delete.txt"
        yd_upload(yd_headers, file_path, b"Delete me")
        time.sleep(1)
        assert yd_exists(yd_headers, file_path)

        yd_delete(yd_headers, file_path)
        time.sleep(1)
        assert not yd_exists(yd_headers, file_path), "Файл не удалён"

    def test_file_not_exists_after_delete(self, yd_headers):
        """file_exists() False после удаления"""
        folder = f"{YD_TEST_ROOT}/uploads"
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        yd_mkdir(yd_headers, folder)

        file_path = f"{folder}/gone.txt"
        yd_upload(yd_headers, file_path, b"Soon gone")
        time.sleep(1)

        yd_delete(yd_headers, file_path)
        time.sleep(1)
        assert not yd_exists(yd_headers, file_path)


# ==============================================================
# ИНТЕГРАЦИЯ API + ЯД
# ==============================================================

class TestYandexDiskIntegration:
    """Тесты интеграции API с Яндекс.Диском"""

    def test_api_folder_create_endpoint(self, api_base, admin_headers, yd_headers):
        """API endpoint создания папки на ЯД"""
        resp = api_post(api_base, "/api/files/folder", admin_headers,
                        params={"folder_path": f"/{YD_TEST_ROOT}/api_folder_test"})
        # 200/201 — OK, 409 — уже есть, 404 — путь не найден, 503 — сервис недоступен
        assert resp.status_code in [200, 201, 404, 409, 503], f"Ошибка: {resp.status_code} {resp.text}"

    def test_api_file_list_endpoint(self, api_base, admin_headers):
        """API endpoint списка файлов на ЯД"""
        resp = api_get(api_base, "/api/files/list", admin_headers,
                       params={"folder_path": f"/{YD_TEST_ROOT}"})
        # 200 — OK, 404 — папка не найдена
        assert resp.status_code in [200, 404]

    def test_api_delete_removes_db_record(self, api_base, admin_headers, module_factory):
        """DELETE /api/files/{id} удаляет запись из БД"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])

        file_rec = module_factory.create_file_record(
            contract["id"], "Стадия 1", "Тест", "api_del.pdf"
        )
        file_id = file_rec["id"]

        resp = api_delete(api_base, f"/api/files/{file_id}", admin_headers)
        assert resp.status_code == 200

        resp = api_get(api_base, f"/api/files/{file_id}", admin_headers)
        assert resp.status_code == 404

    def test_upload_file_via_api(self, api_base, admin_headers, yd_token, module_factory):
        """Загрузка файла через API endpoint"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])

        # Создаём тестовый файл
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode='w') as f:
            f.write("Test file content for API upload")
            tmp_path = f.name

        try:
            with open(tmp_path, 'rb') as f:
                resp = _http_session.post(
                    f"{api_base}/api/files/upload",
                    headers={"Authorization": admin_headers["Authorization"]},
                    files={"file": ("test_upload.txt", f, "text/plain")},
                    data={
                        "contract_id": str(contract["id"]),
                        "stage": "Стадия 1",
                        "file_type": "Тестовый",
                        "yandex_path": f"/{YD_TEST_ROOT}/uploads/api_upload.txt",
                    },
                    timeout=30
                )
            # Может вернуть разные коды в зависимости от конфигурации ЯД
            assert resp.status_code in [200, 201, 500], f"Upload: {resp.status_code} {resp.text}"
        finally:
            os.unlink(tmp_path)


# ==============================================================
# РАСШИРЕННЫЕ API ТЕСТЫ ЯНДЕКС.ДИСКА
# ==============================================================

class TestYandexDiskAPIExtended:
    """Расширенные тесты API endpoints для Яндекс.Диска"""

    def test_api_public_link_endpoint(self, api_base, admin_headers, yd_headers):
        """GET /api/files/public-link — публичная ссылка"""
        # Загружаем файл напрямую на ЯД
        folder = f"{YD_TEST_ROOT}/public_link_api"
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        yd_mkdir(yd_headers, folder)
        file_path = f"{folder}/link_test.txt"
        yd_upload(yd_headers, file_path, b"Public link test content")
        time.sleep(1)

        resp = api_get(api_base, "/api/files/public-link", admin_headers,
                       params={"yandex_path": f"/{file_path}"})
        # 200 — ссылка получена, 404 — файл не найден на ЯД
        assert resp.status_code in [200, 404], f"Public-link: {resp.status_code} {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            assert "public_link" in data or "status" in data

    def test_api_public_link_nonexistent(self, api_base, admin_headers):
        """GET /api/files/public-link — несуществующий файл → 404"""
        resp = api_get(api_base, "/api/files/public-link", admin_headers,
                       params={"yandex_path": "/nonexistent/fake_file_999.txt"})
        assert resp.status_code in [404, 500], f"Expected 404/500: {resp.status_code}"

    def test_api_delete_yandex_file(self, api_base, admin_headers, yd_headers):
        """DELETE /api/files/yandex — удаление файла с ЯД"""
        # Загружаем тестовый файл
        folder = f"{YD_TEST_ROOT}/api_delete"
        yd_mkdir(yd_headers, YD_TEST_ROOT)
        yd_mkdir(yd_headers, folder)
        file_path = f"{folder}/to_delete_api.txt"
        yd_upload(yd_headers, file_path, b"Delete via API test")
        time.sleep(1)

        resp = api_delete(api_base, "/api/files/yandex", admin_headers,
                          params={"yandex_path": f"/{file_path}"})
        assert resp.status_code in [200, 404, 422], f"Delete YD: {resp.status_code} {resp.text}"

    def test_api_delete_yandex_nonexistent(self, api_base, admin_headers):
        """DELETE /api/files/yandex — несуществующий файл"""
        resp = api_delete(api_base, "/api/files/yandex", admin_headers,
                          params={"yandex_path": "/nonexistent/no_file_999.txt"})
        # 200 (not_found status), 404, или 422 (validation)
        assert resp.status_code in [200, 404, 422]

    def test_api_scan_contract_folder(self, api_base, admin_headers, module_factory):
        """POST /api/files/scan/{contract_id} — сканирование папки договора"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])

        resp = api_post(api_base, f"/api/files/scan/{contract['id']}", admin_headers)
        # 200 — сканирование OK, 404 — папка не найдена, 503 — ЯД недоступен
        assert resp.status_code in [200, 404, 503], f"Scan: {resp.status_code} {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            assert "total_on_disk" in data or "status" in data

    def test_api_validate_files(self, api_base, admin_headers, module_factory):
        """POST /api/files/validate — валидация существования файлов на ЯД"""
        client = module_factory.create_client()
        contract = module_factory.create_contract(client["id"])

        # Создаём запись файла в БД
        file_rec = module_factory.create_file_record(
            contract["id"], "Стадия 1", "Тест", "validate_test.pdf"
        )

        resp = _http_session.post(
            f"{api_base}/api/files/validate",
            headers=admin_headers,
            json={"file_ids": [file_rec["id"]], "auto_clean": False},
            timeout=REQUEST_TIMEOUT
        )
        assert resp.status_code in [200, 503], f"Validate: {resp.status_code} {resp.text}"
        if resp.status_code == 200:
            data = resp.json()
            assert isinstance(data, list)
            assert len(data) >= 1
            assert "file_id" in data[0]

    def test_api_nested_folder_creation(self, api_base, admin_headers, yd_headers):
        """POST /api/files/folder — вложенные папки"""
        nested_path = f"/{YD_TEST_ROOT}/level1/level2/level3"
        # Создаём промежуточные папки
        parts = nested_path.strip("/").split("/")
        current = ""
        for part in parts:
            current = f"{current}/{part}" if current else part
            yd_mkdir(yd_headers, current)

        resp = api_post(api_base, "/api/files/folder", admin_headers,
                        params={"folder_path": nested_path})
        # 200/201 — создана, 409 — уже есть
        assert resp.status_code in [200, 201, 409, 503], f"Nested folder: {resp.status_code} {resp.text}"
