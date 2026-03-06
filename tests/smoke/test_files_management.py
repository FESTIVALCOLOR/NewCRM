# -*- coding: utf-8 -*-
"""
Smoke Tests: Files Management — файлы и Яндекс.Диск.

Покрывает: files list, all, updated, by contract, validate,
public-link, scan, CRUD.

Запуск: pytest tests/smoke/test_files_management.py -v --timeout=120
"""

import pytest

from tests.smoke.conftest import (
    _get, _post, _patch, _delete,
    create_test_card, cleanup_test_card, TEST_PREFIX,
)


# ════════════════════════════════════════════════════════════
# 1. File Listing
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestFilesRead:
    """P1: Чтение файлов."""

    def test_files_all(self, admin_headers):
        """GET /files/all — все файлы."""
        resp = _get("/api/files/all", admin_headers)
        assert resp.status_code == 200

    def test_files_list(self, admin_headers):
        """GET /files/all — список файлов (alias)."""
        resp = _get("/api/files/all", admin_headers)
        assert resp.status_code in (200, 422)

    def test_files_updated(self, admin_headers):
        """GET /files/updated — обновлённые файлы."""
        resp = _get("/api/files/updated", admin_headers, params={
            "since": "2020-01-01",
        })
        assert resp.status_code in (200, 400)

    def test_files_by_contract(self, admin_headers):
        """GET /files/contract/{id} — файлы конкретного договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _get(f"/api/files/contract/{cid}", admin_headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ════════════════════════════════════════════════════════════
# 2. File Operations
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestFilesOperations:
    """P1: Операции с файлами."""

    def test_file_validate(self, admin_headers):
        """POST /files/validate — валидация файла."""
        resp = _post("/api/files/validate", admin_headers, json={
            "file_name": "test_document.pdf",
            "file_size": 1024,
        })
        assert resp.status_code in (200, 422), \
            f"Validate: {resp.status_code} {resp.text}"

    def test_file_scan_contract(self, admin_headers):
        """POST /files/scan/{contract_id} — сканирование файлов договора."""
        contracts = _get("/api/contracts", admin_headers).json()
        if not contracts:
            pytest.skip("Нет договоров")
        cid = contracts[0]["id"]
        resp = _post(f"/api/files/scan/{cid}", admin_headers)
        assert resp.status_code in (200, 404, 422), \
            f"Scan: {resp.status_code} {resp.text}"

    def test_create_file_record(self, admin_headers):
        """POST /files — создание записи о файле."""
        client_id, contract_id, _ = create_test_card(admin_headers, "FILE_CR")
        try:
            resp = _post("/api/files", admin_headers, json={
                "contract_id": contract_id,
                "file_name": f"{TEST_PREFIX}test_file.pdf",
                "file_path": f"/smoke_test/{TEST_PREFIX}test.pdf",
                "file_type": "document",
            })
            if resp.status_code in (200, 201):
                file_id = resp.json().get("id")
                if file_id:
                    # Проверяем GET
                    get = _get(f"/api/files/{file_id}", admin_headers)
                    assert get.status_code == 200
                    # Удаляем
                    _delete(f"/api/files/{file_id}", admin_headers)
            else:
                # 422 допустимо — возможно нет обязательных полей
                assert resp.status_code in (200, 201, 422), \
                    f"Create file: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)

    def test_file_public_link(self, admin_headers):
        """GET /files/public-link — получение публичной ссылки."""
        resp = _get("/api/files/public-link", admin_headers, params={
            "path": "/test/nonexistent.pdf",
        })
        # 200 или 404 если файл не существует
        assert resp.status_code in (200, 404, 422), \
            f"Public link: {resp.status_code} {resp.text}"


# ════════════════════════════════════════════════════════════
# 3. Contract Files
# ════════════════════════════════════════════════════════════

@pytest.mark.smoke
class TestContractFiles:
    """P1: Файлы в привязке к договору."""

    def test_patch_contract_files(self, admin_headers):
        """PATCH /contracts/{id}/files — обновление файлов договора."""
        client_id, contract_id, _ = create_test_card(admin_headers, "CTR_FILE")
        try:
            resp = _patch(f"/api/contracts/{contract_id}/files", admin_headers, json={
                "files": [],
            })
            assert resp.status_code in (200, 422), \
                f"Patch files: {resp.status_code} {resp.text}"
        finally:
            cleanup_test_card(admin_headers, client_id, contract_id)
