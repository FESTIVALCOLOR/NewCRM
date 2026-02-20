# -*- coding: utf-8 -*-
"""
E2E Tests: Файлы (CRUD + фильтрация по stage)
12 тестов — КРИТИЧЕСКИЙ: ловит stage mismatch баг supervision.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from tests.e2e.conftest import TEST_PREFIX, api_get, api_post, api_delete, api_patch


# ==============================================================
# ФИЛЬТРАЦИЯ ПО STAGE — КРИТИЧЕСКИЕ ТЕСТЫ
# ==============================================================

class TestFileStageFiltering:
    """Фильтрация файлов по stage через API"""

    @pytest.fixture(autouse=True)
    def setup_contract(self, api_base, admin_headers, module_factory):
        """Создаём клиента и договор для каждого теста"""
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.contract_id = self.contract["id"]

    @pytest.mark.critical
    def test_supervision_file_returned_by_supervision_filter(self):
        """Файл с stage='supervision' находится фильтром supervision"""
        self.factory.create_file_record(
            self.contract_id,
            stage="supervision",
            file_type="Стадия 1: Закупка",
            file_name=f"{TEST_PREFIX}sv_file.pdf"
        )
        resp = api_get(self.api_base, f"/api/files/contract/{self.contract_id}",
                       self.headers, params={"stage": "supervision"})
        assert resp.status_code == 200
        files = resp.json()
        sv_files = [f for f in files if f.get('stage') == 'supervision']
        assert len(sv_files) >= 1, f"Не найден файл supervision. Все файлы: {files}"

    @pytest.mark.critical
    def test_stage_name_NOT_in_supervision_filter(self):
        """Файл с stage='Стадия 1: Закупка' НЕ попадает в фильтр supervision"""
        # Создаём файл с неправильным stage (симулируем старый баг)
        self.factory.create_file_record(
            self.contract_id,
            stage="Стадия 1: Закупка керамогранита",
            file_type="Файл надзора",
            file_name=f"{TEST_PREFIX}wrong_stage.pdf"
        )
        resp = api_get(self.api_base, f"/api/files/contract/{self.contract_id}",
                       self.headers, params={"stage": "supervision"})
        assert resp.status_code == 200
        files = resp.json()
        wrong_files = [f for f in files
                       if f.get('stage') == 'Стадия 1: Закупка керамогранита']
        assert len(wrong_files) == 0, "Файл с неправильным stage попал в фильтр supervision"

    @pytest.mark.critical
    def test_stage1_filter_returns_only_stage1(self):
        """Фильтр stage='Стадия 1' возвращает только файлы стадии 1"""
        self.factory.create_file_record(self.contract_id, "Стадия 1", "Чертёж", "s1.pdf")
        self.factory.create_file_record(self.contract_id, "Стадия 2", "Визуал", "s2.pdf")
        self.factory.create_file_record(self.contract_id, "supervision", "Надзор", "sv.pdf")

        resp = api_get(self.api_base, f"/api/files/contract/{self.contract_id}",
                       self.headers, params={"stage": "Стадия 1"})
        assert resp.status_code == 200
        files = resp.json()
        for f in files:
            assert f['stage'] == 'Стадия 1', f"Файл не стадии 1: {f}"

    def test_no_filter_returns_all(self):
        """Без фильтра stage возвращаются все файлы"""
        self.factory.create_file_record(self.contract_id, "Стадия 1", "А", "a.pdf")
        self.factory.create_file_record(self.contract_id, "Стадия 2", "Б", "b.pdf")
        self.factory.create_file_record(self.contract_id, "supervision", "В", "c.pdf")

        resp = api_get(self.api_base, f"/api/files/contract/{self.contract_id}",
                       self.headers)
        assert resp.status_code == 200
        files = resp.json()
        assert len(files) >= 3


# ==============================================================
# CRUD ФАЙЛОВ
# ==============================================================

class TestFileCRUD:
    """CRUD операции с файлами через API"""

    @pytest.fixture(autouse=True)
    def setup_contract(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.contract_id = self.contract["id"]

    def test_create_file_record(self):
        """Создание записи файла"""
        file_rec = self.factory.create_file_record(
            self.contract_id, "Стадия 1", "Чертёж", "test_create.pdf"
        )
        assert file_rec["id"] > 0
        assert file_rec["stage"] == "Стадия 1"
        assert file_rec["file_type"] == "Чертёж"

    def test_get_file_by_id(self):
        """Получение файла по ID"""
        file_rec = self.factory.create_file_record(
            self.contract_id, "Стадия 1", "Чертёж", "test_get.pdf"
        )
        resp = api_get(self.api_base, f"/api/files/{file_rec['id']}", self.headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == file_rec["id"]

    def test_get_files_by_contract(self):
        """Получение файлов по ID договора"""
        self.factory.create_file_record(self.contract_id, "Стадия 1", "А", "a.pdf")
        self.factory.create_file_record(self.contract_id, "Стадия 2", "Б", "b.pdf")

        resp = api_get(self.api_base, f"/api/files/contract/{self.contract_id}",
                       self.headers)
        assert resp.status_code == 200
        files = resp.json()
        assert len(files) >= 2

    def test_update_file_order(self):
        """Обновление порядка файла"""
        file_rec = self.factory.create_file_record(
            self.contract_id, "Стадия 1", "Чертёж", "test_order.pdf"
        )
        # file_order — query parameter, не JSON body
        resp = api_patch(self.api_base,
                         f"/api/files/{file_rec['id']}/order?file_order=5",
                         self.headers)
        assert resp.status_code == 200

    def test_delete_file_record(self):
        """Удаление записи файла"""
        file_rec = self.factory.create_file_record(
            self.contract_id, "Стадия 1", "Удаляемый", "to_delete.pdf"
        )
        file_id = file_rec["id"]

        resp = api_delete(self.api_base, f"/api/files/{file_id}", self.headers)
        assert resp.status_code == 200

        resp = api_get(self.api_base, f"/api/files/{file_id}", self.headers)
        assert resp.status_code == 404


# ==============================================================
# ВАЛИДАЦИЯ ФАЙЛОВ
# ==============================================================

class TestFileValidation:
    """Проверка валидации файлов"""

    @pytest.fixture(autouse=True)
    def setup_contract(self, api_base, admin_headers, module_factory):
        self.api_base = api_base
        self.headers = admin_headers
        self.factory = module_factory
        client = module_factory.create_client()
        self.contract = module_factory.create_contract(client["id"])
        self.contract_id = self.contract["id"]

    def test_validate_existing_file(self):
        """Валидация существующего файла"""
        file_rec = self.factory.create_file_record(
            self.contract_id, "Стадия 1", "Чертёж", "valid.pdf",
            yandex_path="/some/real/path.pdf"
        )
        resp = api_post(self.api_base, "/api/files/validate", self.headers,
                        json={"file_ids": [file_rec["id"]]})
        assert resp.status_code == 200

    def test_validate_nonexistent_file(self):
        """Валидация несуществующего файла"""
        resp = api_post(self.api_base, "/api/files/validate", self.headers,
                        json={"file_ids": [999999]})
        assert resp.status_code == 200

    def test_validate_batch(self):
        """Батч-валидация нескольких файлов"""
        f1 = self.factory.create_file_record(
            self.contract_id, "Стадия 1", "А", "batch1.pdf",
            yandex_path="/batch/1.pdf"
        )
        f2 = self.factory.create_file_record(
            self.contract_id, "Стадия 2", "Б", "batch2.pdf",
            yandex_path="/batch/2.pdf"
        )
        resp = api_post(self.api_base, "/api/files/validate", self.headers,
                        json={"file_ids": [f1["id"], f2["id"]]})
        assert resp.status_code == 200
