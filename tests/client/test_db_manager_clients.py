# -*- coding: utf-8 -*-
"""
Покрытие database/db_manager.py — CRUD клиентов, сотрудников, базовые методы.
~40 тестов. Все тесты используют реальную SQLite через tmp_path, без моков.
"""

import pytest
import sys
import os
import sqlite3

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


@pytest.fixture
def db(tmp_path):
    """Создать DatabaseManager с временной SQLite БД.

    Порядок инициализации:
    1. Сбрасываем глобальный флаг _migrations_completed
    2. Создаём DatabaseManager (конструктор вызывает run_migrations,
       но на пустой БД ALTER TABLE нет таблиц — все ошибки ловятся try/except)
    3. Вызываем initialize_database() для создания основных таблиц
    4. Повторно вызываем миграции, чтобы добавить колонки (address, birth_date,
       secondary_position и т.д.), которых нет в initialize_database()
    5. Удаляем seed-данные (admin), чтобы тесты начинали с чистой БД
    """
    import database.db_manager as dbm_module
    dbm_module._migrations_completed = False

    db_path = str(tmp_path / 'test.db')
    from database.db_manager import DatabaseManager
    manager = DatabaseManager(db_path=db_path)

    # Создаём основные таблицы
    manager.initialize_database()

    # Повторно запускаем миграции — теперь таблицы есть и ALTER TABLE сработает
    dbm_module._migrations_completed = False
    manager.run_migrations()

    # Удаляем seed-данные (admin), чтобы тесты начинали с чистой таблицы
    conn = manager.connect()
    conn.execute('DELETE FROM employees')
    conn.commit()
    manager.close()

    manager.connect()
    return manager


# ==================== Данные для тестов ====================

SAMPLE_CLIENT = {
    'client_type': 'Физическое лицо',
    'full_name': 'Иванов Иван Иванович',
    'phone': '+79001234567',
    'email': 'ivanov@test.ru',
}

SAMPLE_CLIENT_LEGAL = {
    'client_type': 'Юридическое лицо',
    'full_name': 'ООО Рога и Копыта',
    'phone': '+79009876543',
    'email': 'office@roga.ru',
    'organization_name': 'ООО Рога и Копыта',
    'inn': '7712345678',
    'ogrn': '1177746000000',
}

SAMPLE_EMPLOYEE = {
    'full_name': 'Петров Пётр',
    'login': 'petrov',
    'password': 'test123',
    'position': 'Дизайнер',
}

SAMPLE_EMPLOYEE_MANAGER = {
    'full_name': 'Сидорова Анна',
    'login': 'sidorova',
    'password': 'pass456',
    'position': 'Менеджер',
}


# ==================== _validate_table ====================

class TestValidateTable:
    """Тесты метода _validate_table."""

    def test_valid_table_clients(self, db):
        """Таблица 'clients' проходит валидацию без ошибок."""
        db._validate_table('clients')  # не должно бросить исключение

    def test_valid_table_employees(self, db):
        """Таблица 'employees' проходит валидацию."""
        db._validate_table('employees')

    def test_valid_table_contracts(self, db):
        """Таблица 'contracts' проходит валидацию."""
        db._validate_table('contracts')

    def test_invalid_table_raises_error(self, db):
        """Несуществующая таблица вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя таблицы"):
            db._validate_table('nonexistent_table')

    def test_sql_injection_table_raises_error(self, db):
        """SQL-инъекция в имени таблицы вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя таблицы"):
            db._validate_table("clients; DROP TABLE employees")

    def test_empty_table_name_raises_error(self, db):
        """Пустое имя таблицы вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя таблицы"):
            db._validate_table('')


# ==================== _validate_columns ====================

class TestValidateColumns:
    """Тесты staticmethod _validate_columns."""

    def test_valid_snake_case_columns(self, db):
        """snake_case колонки проходят валидацию."""
        db._validate_columns(['full_name', 'phone', 'email'])

    def test_valid_single_word_column(self, db):
        """Колонка из одного слова проходит валидацию."""
        db._validate_columns(['phone'])

    def test_column_with_numbers(self, db):
        """Колонка с цифрами проходит валидацию."""
        db._validate_columns(['field1', 'payment_2'])

    def test_column_starting_with_underscore(self, db):
        """Колонка начинающаяся с _ проходит валидацию."""
        db._validate_columns(['_internal_field'])

    def test_column_with_uppercase_raises_error(self, db):
        """Колонка с заглавными буквами вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._validate_columns(['FullName'])

    def test_column_with_dash_raises_error(self, db):
        """Колонка с дефисом вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._validate_columns(['full-name'])

    def test_column_with_space_raises_error(self, db):
        """Колонка с пробелом вызывает ValueError (SQL injection attempt)."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._validate_columns(['full name'])

    def test_column_with_sql_injection_raises_error(self, db):
        """Колонка с SQL-инъекцией вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._validate_columns(['name; DROP TABLE clients--'])

    def test_column_starting_with_digit_raises_error(self, db):
        """Колонка начинающаяся с цифры вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._validate_columns(['1field'])

    def test_empty_column_name_raises_error(self, db):
        """Пустое имя колонки вызывает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._validate_columns([''])


# ==================== _build_set_clause ====================

class TestBuildSetClause:
    """Тесты метода _build_set_clause."""

    def test_single_field(self, db):
        """Одно поле — корректный SET clause."""
        clause, values = db._build_set_clause({'full_name': 'Тест'})
        assert clause == 'full_name = ?'
        assert values == ['Тест']

    def test_multiple_fields(self, db):
        """Несколько полей — clause с запятыми."""
        data = {'full_name': 'Тест', 'phone': '123', 'email': 'a@b.ru'}
        clause, values = db._build_set_clause(data)
        # Проверяем что все поля присутствуют
        assert 'full_name = ?' in clause
        assert 'phone = ?' in clause
        assert 'email = ?' in clause
        assert len(values) == 3

    def test_values_preserve_order(self, db):
        """Значения соответствуют порядку ключей."""
        from collections import OrderedDict
        data = OrderedDict([('full_name', 'Иванов'), ('phone', '123')])
        clause, values = db._build_set_clause(data)
        assert values == ['Иванов', '123']

    def test_invalid_column_in_build(self, db):
        """Невалидная колонка в _build_set_clause бросает ValueError."""
        with pytest.raises(ValueError, match="Недопустимое имя колонки"):
            db._build_set_clause({'INVALID COLUMN': 'value'})


# ==================== add_client ====================

class TestAddClient:
    """Тесты метода add_client."""

    def test_add_client_returns_id(self, db):
        """add_client возвращает числовой ID нового клиента."""
        client_id = db.add_client(SAMPLE_CLIENT)
        assert isinstance(client_id, int)
        assert client_id > 0

    def test_add_client_persists_data(self, db):
        """Данные клиента сохраняются в БД."""
        client_id = db.add_client(SAMPLE_CLIENT)
        client = db.get_client_by_id(client_id)
        assert client is not None
        assert client['full_name'] == 'Иванов Иван Иванович'
        assert client['phone'] == '+79001234567'
        assert client['email'] == 'ivanov@test.ru'
        assert client['client_type'] == 'Физическое лицо'

    def test_add_legal_client(self, db):
        """Юридическое лицо сохраняется со всеми полями."""
        client_id = db.add_client(SAMPLE_CLIENT_LEGAL)
        client = db.get_client_by_id(client_id)
        assert client['client_type'] == 'Юридическое лицо'
        assert client['organization_name'] == 'ООО Рога и Копыта'
        assert client['inn'] == '7712345678'

    def test_add_client_minimal_data(self, db):
        """Клиент с минимальными данными (обязательные поля)."""
        minimal = {'client_type': 'Физическое лицо', 'phone': '+70001111111'}
        client_id = db.add_client(minimal)
        assert client_id > 0
        client = db.get_client_by_id(client_id)
        assert client['phone'] == '+70001111111'
        # Необязательные поля — пустые строки
        assert client['full_name'] == ''

    def test_add_multiple_clients_unique_ids(self, db):
        """Каждый новый клиент получает уникальный ID."""
        id1 = db.add_client(SAMPLE_CLIENT)
        id2 = db.add_client({**SAMPLE_CLIENT, 'phone': '+79002222222'})
        id3 = db.add_client({**SAMPLE_CLIENT, 'phone': '+79003333333'})
        assert len({id1, id2, id3}) == 3  # все уникальные


# ==================== get_client_by_id ====================

class TestGetClientById:
    """Тесты метода get_client_by_id."""

    def test_get_existing_client(self, db):
        """Получение существующего клиента по ID — возвращает dict."""
        client_id = db.add_client(SAMPLE_CLIENT)
        client = db.get_client_by_id(client_id)
        assert isinstance(client, dict)
        assert client['id'] == client_id

    def test_get_nonexistent_client_returns_none(self, db):
        """Несуществующий ID — возвращает None."""
        result = db.get_client_by_id(99999)
        assert result is None

    def test_get_client_after_delete_returns_none(self, db):
        """После удаления клиент не находится."""
        client_id = db.add_client(SAMPLE_CLIENT)
        db.delete_client(client_id)
        result = db.get_client_by_id(client_id)
        assert result is None


# ==================== get_all_clients ====================

class TestGetAllClients:
    """Тесты метода get_all_clients."""

    def test_empty_db_returns_empty_list(self, db):
        """Пустая БД — пустой список."""
        clients = db.get_all_clients()
        assert clients == []

    def test_returns_all_added_clients(self, db):
        """Возвращает всех добавленных клиентов."""
        db.add_client(SAMPLE_CLIENT)
        db.add_client({**SAMPLE_CLIENT, 'phone': '+79005555555'})
        clients = db.get_all_clients()
        assert len(clients) == 2

    def test_returns_list_of_dicts(self, db):
        """Каждый элемент — словарь."""
        db.add_client(SAMPLE_CLIENT)
        clients = db.get_all_clients()
        assert isinstance(clients[0], dict)

    def test_pagination_skip(self, db):
        """Параметр skip пропускает записи."""
        for i in range(5):
            db.add_client({**SAMPLE_CLIENT, 'phone': f'+7900{i:07d}'})
        # skip=2 — пропустить 2 самых новых (ORDER BY id DESC)
        clients = db.get_all_clients(skip=2)
        assert len(clients) == 3

    def test_pagination_limit(self, db):
        """Параметр limit ограничивает количество записей."""
        for i in range(5):
            db.add_client({**SAMPLE_CLIENT, 'phone': f'+7900{i:07d}'})
        clients = db.get_all_clients(limit=3)
        assert len(clients) == 3

    def test_pagination_skip_and_limit(self, db):
        """Комбинация skip + limit."""
        for i in range(10):
            db.add_client({**SAMPLE_CLIENT, 'phone': f'+7900{i:07d}'})
        clients = db.get_all_clients(skip=3, limit=2)
        assert len(clients) == 2


# ==================== get_clients_count ====================

class TestGetClientsCount:
    """Тесты метода get_clients_count."""

    def test_empty_db_count_zero(self, db):
        """Пустая БД — count = 0."""
        assert db.get_clients_count() == 0

    def test_count_after_add(self, db):
        """count увеличивается после добавления."""
        db.add_client(SAMPLE_CLIENT)
        assert db.get_clients_count() == 1
        db.add_client({**SAMPLE_CLIENT, 'phone': '+79006666666'})
        assert db.get_clients_count() == 2

    def test_count_after_delete(self, db):
        """count уменьшается после удаления."""
        client_id = db.add_client(SAMPLE_CLIENT)
        assert db.get_clients_count() == 1
        db.delete_client(client_id)
        assert db.get_clients_count() == 0


# ==================== update_client ====================

class TestUpdateClient:
    """Тесты метода update_client."""

    def test_update_full_name(self, db):
        """Обновление имени клиента."""
        client_id = db.add_client(SAMPLE_CLIENT)
        db.update_client(client_id, {'full_name': 'Сидоров Сидор'})
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == 'Сидоров Сидор'

    def test_update_multiple_fields(self, db):
        """Обновление нескольких полей одновременно."""
        client_id = db.add_client(SAMPLE_CLIENT)
        db.update_client(client_id, {
            'full_name': 'Новое Имя',
            'phone': '+79001111111',
            'email': 'new@test.ru',
        })
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == 'Новое Имя'
        assert client['phone'] == '+79001111111'
        assert client['email'] == 'new@test.ru'

    def test_update_does_not_affect_other_fields(self, db):
        """Обновление одного поля не затрагивает другие."""
        client_id = db.add_client(SAMPLE_CLIENT)
        db.update_client(client_id, {'full_name': 'Другое Имя'})
        client = db.get_client_by_id(client_id)
        # Телефон не изменился
        assert client['phone'] == '+79001234567'

    def test_update_with_disallowed_field_is_ignored(self, db):
        """Поля не из whitelist игнорируются."""
        client_id = db.add_client(SAMPLE_CLIENT)
        # 'source' НЕ в ALLOWED_FIELDS update_client
        db.update_client(client_id, {'source': 'Реклама', 'full_name': 'OK'})
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == 'OK'

    def test_update_with_empty_data_does_nothing(self, db):
        """Пустой словарь — ничего не обновляется (без ошибки)."""
        client_id = db.add_client(SAMPLE_CLIENT)
        # Пустой словарь → validated_data пуст → ранний return
        db.update_client(client_id, {})
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == SAMPLE_CLIENT['full_name']

    def test_update_with_only_disallowed_fields_does_nothing(self, db):
        """Только неразрешённые поля — ничего не обновляется."""
        client_id = db.add_client(SAMPLE_CLIENT)
        db.update_client(client_id, {'nonexistent_field': 'value'})
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == SAMPLE_CLIENT['full_name']


# ==================== delete_client ====================

class TestDeleteClient:
    """Тесты метода delete_client."""

    def test_delete_existing_client(self, db):
        """Удаление существующего клиента."""
        client_id = db.add_client(SAMPLE_CLIENT)
        db.delete_client(client_id)
        assert db.get_client_by_id(client_id) is None

    def test_delete_nonexistent_client_no_error(self, db):
        """Удаление несуществующего клиента не вызывает ошибку."""
        db.delete_client(99999)  # не должно бросить исключение

    def test_delete_does_not_affect_other_clients(self, db):
        """Удаление одного клиента не затрагивает других."""
        id1 = db.add_client(SAMPLE_CLIENT)
        id2 = db.add_client({**SAMPLE_CLIENT, 'phone': '+79007777777'})
        db.delete_client(id1)
        assert db.get_client_by_id(id2) is not None
        assert db.get_clients_count() == 1


# ==================== CRUD полный цикл ====================

class TestClientCRUDCycle:
    """Полный цикл: create → read → update → delete."""

    def test_full_crud_cycle(self, db):
        """Полный цикл CRUD клиента."""
        # Create
        client_id = db.add_client(SAMPLE_CLIENT)
        assert client_id > 0

        # Read
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == 'Иванов Иван Иванович'

        # Update
        db.update_client(client_id, {'full_name': 'Обновлённое Имя'})
        client = db.get_client_by_id(client_id)
        assert client['full_name'] == 'Обновлённое Имя'

        # Delete
        db.delete_client(client_id)
        assert db.get_client_by_id(client_id) is None
        assert db.get_clients_count() == 0


# ==================== add_employee ====================

class TestAddEmployee:
    """Тесты метода add_employee."""

    def test_add_employee_returns_id(self, db):
        """add_employee возвращает числовой ID."""
        emp_id = db.add_employee(SAMPLE_EMPLOYEE)
        assert isinstance(emp_id, int)
        assert emp_id > 0

    def test_employee_password_is_hashed(self, db):
        """Пароль хешируется — в БД не хранится открытый текст."""
        emp_id = db.add_employee(SAMPLE_EMPLOYEE)
        emp = db.get_employee_by_id(emp_id)
        # Пароль в БД НЕ совпадает с открытым текстом
        assert emp['password'] != 'test123'
        # Пароль — непустая строка (хеш)
        assert len(emp['password']) > 0

    def test_department_auto_assigned_designer(self, db):
        """Должность 'Дизайнер' → отдел 'Проектный отдел'."""
        emp_id = db.add_employee(SAMPLE_EMPLOYEE)
        emp = db.get_employee_by_id(emp_id)
        assert emp['department'] == 'Проектный отдел'

    def test_department_auto_assigned_manager(self, db):
        """Должность 'Менеджер' → отдел 'Исполнительный отдел'."""
        emp_id = db.add_employee(SAMPLE_EMPLOYEE_MANAGER)
        emp = db.get_employee_by_id(emp_id)
        assert emp['department'] == 'Исполнительный отдел'

    def test_department_auto_assigned_admin(self, db):
        """Должность 'Руководитель студии' → 'Административный отдел'."""
        emp_data = {**SAMPLE_EMPLOYEE, 'login': 'boss', 'position': 'Руководитель студии'}
        emp_id = db.add_employee(emp_data)
        emp = db.get_employee_by_id(emp_id)
        assert emp['department'] == 'Административный отдел'

    def test_department_unknown_position(self, db):
        """Неизвестная должность → отдел 'Другое'."""
        emp_data = {**SAMPLE_EMPLOYEE, 'login': 'unknown', 'position': 'Стажёр'}
        emp_id = db.add_employee(emp_data)
        emp = db.get_employee_by_id(emp_id)
        assert emp['department'] == 'Другое'


# ==================== get_employee_by_login ====================

class TestGetEmployeeByLogin:
    """Тесты метода get_employee_by_login."""

    def test_correct_credentials_returns_dict(self, db):
        """Верный логин/пароль — возвращает словарь сотрудника."""
        db.add_employee(SAMPLE_EMPLOYEE)
        result = db.get_employee_by_login('petrov', 'test123')
        assert isinstance(result, dict)
        assert result['full_name'] == 'Петров Пётр'

    def test_wrong_password_returns_none(self, db):
        """Неверный пароль — возвращает None."""
        db.add_employee(SAMPLE_EMPLOYEE)
        result = db.get_employee_by_login('petrov', 'wrongpass')
        assert result is None

    def test_nonexistent_login_returns_none(self, db):
        """Несуществующий логин — возвращает None."""
        result = db.get_employee_by_login('nonexistent', 'any')
        assert result is None


# ==================== get_all_employees ====================

class TestGetAllEmployees:
    """Тесты метода get_all_employees."""

    def test_empty_db(self, db):
        """Пустая БД — пустой список."""
        assert db.get_all_employees() == []

    def test_returns_all_employees(self, db):
        """Возвращает всех добавленных сотрудников."""
        db.add_employee(SAMPLE_EMPLOYEE)
        db.add_employee(SAMPLE_EMPLOYEE_MANAGER)
        employees = db.get_all_employees()
        assert len(employees) == 2


# ==================== get_employee_by_id ====================

class TestGetEmployeeById:
    """Тесты метода get_employee_by_id."""

    def test_existing_employee(self, db):
        """Получение существующего сотрудника по ID."""
        emp_id = db.add_employee(SAMPLE_EMPLOYEE)
        emp = db.get_employee_by_id(emp_id)
        assert emp is not None
        assert emp['login'] == 'petrov'

    def test_nonexistent_id_returns_none(self, db):
        """Несуществующий ID — возвращает None."""
        assert db.get_employee_by_id(99999) is None


# ==================== check_login_exists ====================

class TestCheckLoginExists:
    """Тесты метода check_login_exists."""

    def test_existing_login_returns_true(self, db):
        """Существующий логин — True."""
        db.add_employee(SAMPLE_EMPLOYEE)
        assert db.check_login_exists('petrov') is True

    def test_nonexistent_login_returns_false(self, db):
        """Несуществующий логин — False."""
        assert db.check_login_exists('nobody') is False

    def test_after_adding_two_employees(self, db):
        """Проверка двух разных логинов."""
        db.add_employee(SAMPLE_EMPLOYEE)
        db.add_employee(SAMPLE_EMPLOYEE_MANAGER)
        assert db.check_login_exists('petrov') is True
        assert db.check_login_exists('sidorova') is True
        assert db.check_login_exists('unknown') is False
