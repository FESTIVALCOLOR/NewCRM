# -*- coding: utf-8 -*-
"""
DB Tests: CRUD операции DatabaseManager
Проверяет основные операции чтения/записи через db_manager.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


class TestClientsCRUD:
    """CRUD клиентов"""

    def test_create_client(self, db):
        """Создание клиента"""
        client_data = {
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Клиент CRUD',
            'phone': '+79991111111',
            'email': 'crud_test@test.com',
        }
        client_id = db.add_client(client_data)
        assert client_id is not None
        assert client_id > 0

    def test_read_client(self, db):
        """Чтение клиента"""
        client_data = {
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Клиент Read',
            'phone': '+79992222222',
        }
        client_id = db.add_client(client_data)
        client = db.get_client_by_id(client_id)
        assert client is not None
        assert client['full_name'] == '__TEST__Клиент Read'

    def test_update_client(self, db):
        """Обновление клиента"""
        client_data = {
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__До Обновления',
            'phone': '+79993333333',
        }
        client_id = db.add_client(client_data)
        db.update_client(client_id, {'full_name': '__TEST__После Обновления'})
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == '__TEST__После Обновления'

    def test_delete_client(self, db):
        """Удаление клиента"""
        client_data = {
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Удаляемый',
            'phone': '+79994444444',
        }
        client_id = db.add_client(client_data)
        db.delete_client(client_id)
        client = db.get_client_by_id(client_id)
        assert client is None

    def test_get_all_clients(self, db):
        """Получение списка клиентов"""
        db.add_client({
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Список1',
            'phone': '+79995555555',
        })
        clients = db.get_all_clients()
        assert isinstance(clients, list)
        assert len(clients) >= 1


class TestContractsCRUD:
    """CRUD договоров"""

    def _create_client(self, db):
        return db.add_client({
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Клиент Для Договора',
            'phone': '+79996666666',
        })

    def test_create_contract(self, db):
        """Создание договора"""
        client_id = self._create_client(db)
        contract_data = {
            'client_id': client_id,
            'project_type': 'Индивидуальный',
            'agent_type': 'ФЕСТИВАЛЬ',
            'city': 'СПБ',
            'contract_number': '__TEST__CONTRACT_001',
            'address': 'Тестовый адрес',
            'area': 75.0,
            'total_amount': 300000,
            'status': 'Новый заказ',
        }
        contract_id = db.add_contract(contract_data)
        assert contract_id is not None
        assert contract_id > 0

    def test_read_contract(self, db):
        """Чтение договора"""
        client_id = self._create_client(db)
        contract_id = db.add_contract({
            'client_id': client_id,
            'project_type': 'Шаблонный',
            'contract_number': '__TEST__CONTRACT_002',
            'area': 50.0,
            'status': 'Новый заказ',
        })
        contract = db.get_contract_by_id(contract_id)
        assert contract is not None
        assert contract['contract_number'] == '__TEST__CONTRACT_002'

    def test_update_contract(self, db):
        """Обновление договора"""
        client_id = self._create_client(db)
        contract_id = db.add_contract({
            'client_id': client_id,
            'project_type': 'Индивидуальный',
            'contract_number': '__TEST__CONTRACT_003',
            'status': 'Новый заказ',
        })
        db.update_contract(contract_id, {'status': 'СДАН'})
        contract = db.get_contract_by_id(contract_id)
        assert contract['status'] == 'СДАН'


class TestFilesCRUD:
    """CRUD файлов проекта"""

    def _create_contract(self, db):
        client_id = db.add_client({
            'client_type': 'Физическое лицо',
            'full_name': '__TEST__Клиент Для Файлов',
            'phone': '+79997777777',
        })
        return db.add_contract({
            'client_id': client_id,
            'project_type': 'Индивидуальный',
            'contract_number': '__TEST__FILES_001',
            'status': 'Новый заказ',
        })

    def test_add_project_file(self, db):
        """Добавление файла проекта"""
        contract_id = self._create_contract(db)
        file_id = db.add_project_file(
            contract_id=contract_id,
            stage='Стадия 1',
            file_type='Чертёж',
            public_link='',
            yandex_path='/test/path/file.pdf',
            file_name='test_file.pdf',
        )
        assert file_id is not None
        assert file_id > 0

    def test_get_project_files(self, db):
        """Получение файлов проекта"""
        contract_id = self._create_contract(db)
        db.add_project_file(
            contract_id=contract_id, stage='Стадия 1', file_type='Чертёж',
            public_link='', yandex_path='/test/path/a.pdf', file_name='a.pdf',
        )
        db.add_project_file(
            contract_id=contract_id, stage='Стадия 2', file_type='Визуализация',
            public_link='', yandex_path='/test/path/b.pdf', file_name='b.pdf',
        )
        files = db.get_project_files(contract_id)
        assert isinstance(files, list)
        assert len(files) >= 2

    def test_get_project_files_with_stage_filter(self, db):
        """Получение файлов с фильтром по stage"""
        contract_id = self._create_contract(db)
        db.add_project_file(
            contract_id=contract_id, stage='Стадия 1', file_type='Чертёж',
            public_link='', yandex_path='/test/s1.pdf', file_name='s1.pdf',
        )
        db.add_project_file(
            contract_id=contract_id, stage='supervision', file_type='Надзор',
            public_link='', yandex_path='/test/sv.pdf', file_name='sv.pdf',
        )
        stage1_files = db.get_project_files(contract_id, stage='Стадия 1')
        assert all(f.get('stage') == 'Стадия 1' for f in stage1_files)

    def test_delete_project_file(self, db):
        """Удаление файла проекта"""
        contract_id = self._create_contract(db)
        file_id = db.add_project_file(
            contract_id=contract_id, stage='Стадия 1', file_type='Тест',
            public_link='', yandex_path='/test/del.pdf', file_name='del.pdf',
        )
        db.delete_project_file(file_id)
        files = db.get_project_files(contract_id)
        file_ids = [f.get('id') for f in files]
        assert file_id not in file_ids
