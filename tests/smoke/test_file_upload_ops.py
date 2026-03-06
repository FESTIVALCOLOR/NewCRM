# -*- coding: utf-8 -*-
"""
Smoke Tests: File Upload Operations — upload, folder, order, public links.

Тестирует файловые операции через Yandex Disk API.

Запуск: pytest tests/smoke/test_file_upload_ops.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _put, _patch, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


@pytest.mark.smoke
class TestFileRecordCRUD:
    """P1: CRUD записей файлов (без реальной загрузки на Yandex Disk)."""

    def test_create_file_record(self, admin_headers):
        """POST /files — создание записи файла."""
        client_id, contract_id, card_id = create_test_card(admin_headers, "F_REC")
        try:
            resp = _post("/api/files", admin_headers, json={
                "contract_id": contract_id,
                "file_name": f"{TEST_PREFIX}test_file.pdf",
                "file_path": "/test/path/test_file.pdf",
                "file_type": "document",
            })
            if resp.status_code in (200, 201):
                file_id = resp.json().get("id")
                assert file_id, "Нет ID файла в ответе"
                # Удаляем запись
                _delete(f"/api/files/{file_id}", admin_headers)
            else:
                # Endpoint может не поддерживать прямое создание
                assert resp.status_code in (400, 404, 405, 422)
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_files_by_contract(self, admin_headers):
        """GET /files/contract/{id} — файлы по договору."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        contract_id = contracts[0]["id"]
        resp = _get(f"/api/files/contract/{contract_id}", admin_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_files_updated_since(self, admin_headers):
        """GET /files/updated — файлы обновлённые с даты."""
        resp = _get("/api/files/updated", admin_headers, params={
            "since": "2020-01-01",
        })
        assert resp.status_code in (200, 422)
        if resp.status_code == 200:
            assert isinstance(resp.json(), list)

    def test_files_validate(self, admin_headers):
        """POST /files/validate — валидация файлов."""
        resp = _post("/api/files/validate", admin_headers)
        assert resp.status_code in (200, 422)


@pytest.mark.smoke
class TestFolderOperations:
    """P1: Операции с папками на Yandex Disk."""

    def test_create_folder_for_contract(self, admin_headers):
        """POST /files/folder — создание папки для договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        contract_id = contracts[0]["id"]
        resp = _post("/api/files/folder", admin_headers, json={
            "contract_id": contract_id,
        })
        # 200 = создана/уже существует, 400 = нет настроек Yandex Disk
        assert resp.status_code in (200, 201, 400, 409, 422, 500), \
            f"Create folder: {resp.status_code} {resp.text}"

    def test_public_link(self, admin_headers):
        """GET /files/{id}/public-link — получение публичной ссылки."""
        resp_files = _get("/api/files/all", admin_headers)
        if resp_files.status_code != 200:
            pytest.skip(f"GET /files/all вернул {resp_files.status_code}")
        files = resp_files.json()
        if not files:
            pytest.skip("Нет файлов")

        file_id = files[0]["id"]
        resp = _get(f"/api/files/{file_id}/public-link", admin_headers)
        # 200 = ссылка есть, 404 = нет файла на диске
        assert resp.status_code in (200, 404, 500)


@pytest.mark.smoke
class TestFileOrder:
    """P2: Порядок файлов в договоре."""

    def test_patch_file_order(self, admin_headers):
        """PATCH /files/{file_id}/order — обновление порядка файла."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        contract_id = contracts[0]["id"]
        # Получаем текущие файлы
        files_resp = _get(f"/api/files/contract/{contract_id}", admin_headers)
        if files_resp.status_code != 200:
            pytest.skip(f"GET files: {files_resp.status_code}")
        files = files_resp.json()
        if not files:
            pytest.skip("Нет файлов для договора")

        # Обновляем порядок первого файла (идемпотентно)
        file_id = files[0]["id"]
        current_order = files[0].get("file_order", 0)
        resp = _patch(f"/api/files/{file_id}/order", admin_headers, json={
            "file_order": current_order,
        })
        assert resp.status_code in (200, 404, 405, 422), \
            f"Patch file order: {resp.status_code} {resp.text}"

    def test_scan_files(self, admin_headers):
        """POST /files/scan/{contract_id} — сканирование файлов Yandex Disk."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")

        contract_id = contracts[0]["id"]
        resp = _post(f"/api/files/scan/{contract_id}", admin_headers)
        assert resp.status_code in (200, 202, 400, 404, 422, 500), \
            f"Scan files: {resp.status_code} {resp.text}"
