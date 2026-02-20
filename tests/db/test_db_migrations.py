# -*- coding: utf-8 -*-
"""
DB Tests: Миграции и структура таблиц
Проверяет что все таблицы созданы, колонки на месте, индексы созданы.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


# ==============================================================
# ТАБЛИЦЫ
# ==============================================================

class TestTableCreation:
    """Проверка создания всех таблиц"""

    def _table_exists(self, db, table_name):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name=?",
            (table_name,)
        )
        result = cursor.fetchone()
        db.close()
        return result is not None

    def _get_columns(self, db, table_name):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        db.close()
        return columns

    @pytest.mark.critical
    def test_clients_table_exists(self, db):
        """Таблица clients существует"""
        assert self._table_exists(db, 'clients')

    @pytest.mark.critical
    def test_contracts_table_exists(self, db):
        """Таблица contracts существует"""
        assert self._table_exists(db, 'contracts')

    @pytest.mark.critical
    def test_employees_table_exists(self, db):
        """Таблица employees существует"""
        assert self._table_exists(db, 'employees')

    @pytest.mark.critical
    def test_crm_cards_table_exists(self, db):
        """Таблица crm_cards существует"""
        assert self._table_exists(db, 'crm_cards')

    @pytest.mark.critical
    def test_project_files_table_exists(self, db):
        """Таблица project_files существует"""
        assert self._table_exists(db, 'project_files')

    @pytest.mark.critical
    def test_project_templates_table_exists(self, db):
        """Таблица project_templates существует"""
        assert self._table_exists(db, 'project_templates')

    def test_supervision_cards_table_exists(self, db):
        """Таблица supervision_cards существует"""
        assert self._table_exists(db, 'supervision_cards')

    def test_salaries_table_exists(self, db):
        """Таблица salaries существует"""
        assert self._table_exists(db, 'salaries')

    def test_stage_executors_table_exists(self, db):
        """Таблица stage_executors существует"""
        assert self._table_exists(db, 'stage_executors')

    def test_action_history_table_exists(self, db):
        """Таблица action_history существует"""
        assert self._table_exists(db, 'action_history')


# ==============================================================
# КОЛОНКИ И МИГРАЦИИ
# ==============================================================

class TestColumnMigrations:
    """Проверка что все миграции применены корректно"""

    def _get_columns(self, db, table_name):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]
        db.close()
        return columns

    @pytest.mark.critical
    def test_contracts_base_columns(self, db):
        """Договоры имеют базовые колонки"""
        columns = self._get_columns(db, 'contracts')
        base_columns = [
            'id', 'client_id', 'project_type', 'contract_number',
            'contract_date', 'address', 'area', 'total_amount', 'status',
        ]
        for col in base_columns:
            assert col in columns, f"Отсутствует колонка {col} в contracts"

    @pytest.mark.critical
    def test_contracts_file_columns_from_migration(self, db):
        """Договоры имеют файловые колонки из standalone миграции add_contract_file_columns"""
        columns = self._get_columns(db, 'contracts')
        # Эти колонки создаются standalone миграцией add_contract_file_columns
        file_columns = [
            'contract_file_yandex_path',
            'contract_file_name',
            'template_contract_file_yandex_path',
            'template_contract_file_name',
            'references_yandex_path',
            'photo_documentation_yandex_path',
        ]
        for col in file_columns:
            assert col in columns, f"Отсутствует колонка {col} в contracts"

    @pytest.mark.critical
    def test_salaries_stage_name_column(self, db):
        """Зарплаты имеют колонку stage_name"""
        columns = self._get_columns(db, 'salaries')
        assert 'stage_name' in columns, "Отсутствует колонка stage_name в salaries"

    def test_project_files_columns(self, db):
        """project_files имеет все необходимые колонки"""
        columns = self._get_columns(db, 'project_files')
        required = ['id', 'contract_id', 'stage', 'file_type', 'yandex_path',
                     'public_link', 'file_name', 'upload_date']
        for col in required:
            assert col in columns, f"Отсутствует колонка {col} в project_files"

    def test_crm_cards_approval_columns(self, db):
        """CRM карточки имеют базовые колонки согласования"""
        columns = self._get_columns(db, 'crm_cards')
        # is_approved создаётся в initialize_database
        assert 'is_approved' in columns, "Отсутствует колонка is_approved в crm_cards"

    def test_crm_cards_executor_columns(self, db):
        """CRM карточки имеют колонки исполнителей"""
        columns = self._get_columns(db, 'crm_cards')
        executor_cols = ['senior_manager_id', 'sdp_id', 'gap_id',
                         'manager_id', 'surveyor_id']
        for col in executor_cols:
            assert col in columns, f"Отсутствует колонка {col} в crm_cards"

    def test_supervision_cards_columns(self, db):
        """Карточки надзора имеют все необходимые колонки"""
        columns = self._get_columns(db, 'supervision_cards')
        required = ['id', 'contract_id', 'column_name', 'senior_manager_id',
                     'dan_id', 'dan_completed', 'is_paused']
        for col in required:
            assert col in columns, f"Отсутствует колонка {col} в supervision_cards"

    def test_employees_login_column(self, db):
        """Сотрудники имеют колонку login"""
        columns = self._get_columns(db, 'employees')
        assert 'login' in columns, "Отсутствует колонка login в employees"

    def test_contracts_has_contract_number(self, db):
        """Договоры имеют колонку contract_number"""
        columns = self._get_columns(db, 'contracts')
        assert 'contract_number' in columns


class TestIndexes:
    """Проверка создания индексов"""

    def _get_indexes(self, db):
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]
        db.close()
        return indexes

    def test_performance_indexes_created(self, db):
        """Индексы производительности созданы"""
        indexes = self._get_indexes(db)
        # Проверяем что основные индексы есть (создаются standalone миграциями)
        expected_patterns = [
            'idx_project_files_contract',
            'idx_payments_contract_id',
            'idx_supervision_cards_contract_id',
        ]
        for pattern in expected_patterns:
            found = any(pattern in idx for idx in indexes)
            assert found, f"Не найден индекс {pattern}. Имеющиеся: {indexes}"
