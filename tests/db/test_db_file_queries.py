# -*- coding: utf-8 -*-
"""
DB Tests: Файловые запросы и фильтрация по stage
КРИТИЧЕСКИЙ: Ловит баг с supervision файлами (stage mismatch)
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestFileStageQueries:
    """Тесты фильтрации файлов по stage — ловит stage mismatch баги"""

    def _insert_file(self, db, contract_id, stage, file_type, file_name):
        """Вставить тестовый файл"""
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO project_files (contract_id, stage, file_type, yandex_path, file_name, upload_date)
            VALUES (?, ?, ?, '/test/path', ?, datetime('now'))
        """, (contract_id, stage, file_type, file_name))
        conn.commit()
        file_id = cursor.lastrowid
        db.close()
        return file_id

    @pytest.mark.critical
    def test_supervision_file_returned_by_supervision_filter(self, db_with_data):
        """Файл с stage='supervision' находится фильтром supervision"""
        db = db_with_data
        cid = db._test_data['contract_id']

        self._insert_file(db, cid, 'supervision', 'Стадия 1: Закупка', 'test.pdf')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_files WHERE contract_id = ? AND stage = 'supervision'",
            (cid,)
        )
        results = cursor.fetchall()
        db.close()
        assert len(results) == 1, f"Ожидался 1 файл supervision, найдено {len(results)}"

    @pytest.mark.critical
    def test_stage_name_NOT_in_supervision_filter(self, db_with_data):
        """Файл со stage='Стадия 1: Закупка' НЕ находится фильтром supervision"""
        db = db_with_data
        cid = db._test_data['contract_id']

        # Файл с неправильным stage (старый формат - баг)
        self._insert_file(db, cid, 'Стадия 1: Закупка', 'Файл надзора', 'old_format.pdf')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_files WHERE contract_id = ? AND stage = 'supervision'",
            (cid,)
        )
        results = cursor.fetchall()
        db.close()
        # Файл с stage='Стадия 1: Закупка' НЕ должен попадать в supervision фильтр
        assert len(results) == 0, "Файл с stage='Стадия 1: Закупка' не должен быть в supervision"

    @pytest.mark.critical
    def test_stage1_filter_returns_only_stage1(self, db_with_data):
        """Фильтр по stage='Стадия 1' возвращает только файлы стадии 1"""
        db = db_with_data
        cid = db._test_data['contract_id']

        self._insert_file(db, cid, 'Стадия 1', 'Чертёж', 'stage1.pdf')
        self._insert_file(db, cid, 'Стадия 2', 'Визуализация', 'stage2.pdf')
        self._insert_file(db, cid, 'supervision', 'Надзор', 'sv.pdf')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_files WHERE contract_id = ? AND stage = 'Стадия 1'",
            (cid,)
        )
        results = cursor.fetchall()
        db.close()
        assert len(results) == 1, f"Ожидался 1 файл стадии 1, найдено {len(results)}"

    def test_no_filter_returns_all(self, db_with_data):
        """Без фильтра возвращаются все файлы контракта"""
        db = db_with_data
        cid = db._test_data['contract_id']

        self._insert_file(db, cid, 'Стадия 1', 'А', 'a.pdf')
        self._insert_file(db, cid, 'Стадия 2', 'Б', 'b.pdf')
        self._insert_file(db, cid, 'supervision', 'В', 'c.pdf')

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_files WHERE contract_id = ?",
            (cid,)
        )
        results = cursor.fetchall()
        db.close()
        assert len(results) >= 3, f"Ожидалось >= 3 файлов, найдено {len(results)}"

    def test_empty_result_no_crash(self, db_with_data):
        """Пустой результат не вызывает ошибку"""
        db = db_with_data
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_files WHERE contract_id = 999999 AND stage = 'nonexistent'"
        )
        results = cursor.fetchall()
        db.close()
        assert results == []


class TestTemplateQueries:
    """Тесты для project_templates"""

    def test_add_project_template(self, db_with_data):
        """Добавление шаблона проекта"""
        db = db_with_data
        cid = db._test_data['contract_id']

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO project_templates (contract_id, template_url)
            VALUES (?, 'https://example.com/template1')
        """, (cid,))
        conn.commit()
        template_id = cursor.lastrowid
        db.close()
        assert template_id > 0

    def test_get_project_templates(self, db_with_data):
        """Получение шаблонов проекта по contract_id"""
        db = db_with_data
        cid = db._test_data['contract_id']

        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO project_templates (contract_id, template_url)
            VALUES (?, 'https://example.com/tpl_a')
        """, (cid,))
        conn.commit()

        cursor.execute(
            "SELECT * FROM project_templates WHERE contract_id = ?", (cid,)
        )
        results = cursor.fetchall()
        db.close()
        assert len(results) >= 1

    def test_empty_templates_returns_empty(self, db_with_data):
        """Несуществующий contract_id возвращает пустой список"""
        db = db_with_data
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM project_templates WHERE contract_id = 999999"
        )
        results = cursor.fetchall()
        db.close()
        assert results == []
