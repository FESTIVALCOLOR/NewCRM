# -*- coding: utf-8 -*-
"""
DB Tests: Offline авторизация и CRUD сотрудников
Проверяет cache_employee_password, get_employee_for_offline_login,
add_employee, get_employee_by_login, get_employees_by_department,
get_employees_by_position, check_login_exists.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from utils.password_utils import hash_password, verify_password


# ============================================================
# Тесты CRUD сотрудников
# ============================================================

class TestEmployeeCRUD:
    """CRUD операции с сотрудниками."""

    def test_add_employee_designer(self, db):
        """Создание сотрудника-дизайнера."""
        emp_id = db.add_employee({
            'full_name': '__TEST__Дизайнер Offline',
            'phone': '+79991111001',
            'position': 'Дизайнер',
            'login': '__test_offline_des',
            'password': 'secret123',
        })
        assert emp_id is not None
        assert emp_id > 0

    def test_add_employee_department_auto(self, db):
        """Отдел определяется автоматически по должности."""
        # Дизайнер → Проектный отдел
        emp_id = db.add_employee({
            'full_name': '__TEST__Дизайнер Dept',
            'phone': '+79991111002',
            'position': 'Дизайнер',
            'login': '__test_dept_des',
            'password': 'pass',
        })
        emp = db.get_employee_by_id(emp_id)
        assert emp['department'] == 'Проектный отдел'

        # Менеджер → Исполнительный отдел
        mgr_id = db.add_employee({
            'full_name': '__TEST__Менеджер Dept',
            'phone': '+79991111003',
            'position': 'Менеджер',
            'login': '__test_dept_mgr',
            'password': 'pass',
        })
        mgr = db.get_employee_by_id(mgr_id)
        assert mgr['department'] == 'Исполнительный отдел'

        # Руководитель → Административный отдел
        head_id = db.add_employee({
            'full_name': '__TEST__Руководитель Dept',
            'phone': '+79991111004',
            'position': 'Руководитель студии',
            'login': '__test_dept_head',
            'password': 'pass',
        })
        head = db.get_employee_by_id(head_id)
        assert head['department'] == 'Административный отдел'

    def test_add_employee_password_hashed(self, db):
        """Пароль сохраняется в хэшированном виде."""
        emp_id = db.add_employee({
            'full_name': '__TEST__Hash Сотрудник',
            'phone': '+79991111005',
            'position': 'Дизайнер',
            'login': '__test_hash_emp',
            'password': 'my_secret_pass',
        })

        # Получаем напрямую из БД
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM employees WHERE id = ?', (emp_id,))
        row = cursor.fetchone()
        db.close()

        stored_hash = row['password']
        # Пароль НЕ хранится в открытом виде
        assert stored_hash != 'my_secret_pass'
        # Верификация через password_utils
        assert verify_password('my_secret_pass', stored_hash)

    def test_get_employee_by_login_correct_password(self, db):
        """Вход с правильным паролем."""
        db.add_employee({
            'full_name': '__TEST__Login Сотрудник',
            'phone': '+79991111006',
            'position': 'Дизайнер',
            'login': '__test_login_ok',
            'password': 'correct_pass',
        })

        emp = db.get_employee_by_login('__test_login_ok', 'correct_pass')
        assert emp is not None
        assert emp['full_name'] == '__TEST__Login Сотрудник'

    def test_get_employee_by_login_wrong_password(self, db):
        """Вход с неправильным паролем."""
        db.add_employee({
            'full_name': '__TEST__Login Wrong',
            'phone': '+79991111007',
            'position': 'Дизайнер',
            'login': '__test_login_wrong',
            'password': 'correct_pass',
        })

        emp = db.get_employee_by_login('__test_login_wrong', 'wrong_pass')
        assert emp is None

    def test_get_employee_by_login_nonexistent(self, db):
        """Вход с несуществующим логином."""
        emp = db.get_employee_by_login('__nonexistent_login__', 'any_pass')
        assert emp is None

    def test_get_employees_by_department(self, db):
        """Получение сотрудников по отделу."""
        db.add_employee({
            'full_name': '__TEST__Dept Дизайнер1',
            'phone': '+79991111008',
            'position': 'Дизайнер',
            'login': '__test_dept1',
            'password': 'pass',
        })
        db.add_employee({
            'full_name': '__TEST__Dept Чертёжник1',
            'phone': '+79991111009',
            'position': 'Чертёжник',
            'login': '__test_dept2',
            'password': 'pass',
        })

        employees = db.get_employees_by_department('Проектный отдел')
        assert isinstance(employees, list)
        assert len(employees) >= 2
        # Все из проектного отдела
        for emp in employees:
            assert emp['department'] == 'Проектный отдел'

    def test_get_employees_by_position(self, db):
        """Получение сотрудников по должности."""
        db.add_employee({
            'full_name': '__TEST__Pos Дизайнер1',
            'phone': '+79991111010',
            'position': 'Дизайнер',
            'login': '__test_pos1',
            'password': 'pass',
        })

        employees = db.get_employees_by_position('Дизайнер')
        assert isinstance(employees, list)
        assert len(employees) >= 1
        # Все с должностью Дизайнер (primary или secondary)
        for emp in employees:
            assert emp['position'] == 'Дизайнер' or emp.get('secondary_position') == 'Дизайнер'

    def test_get_employees_by_position_secondary(self, db):
        """Получение сотрудников по ВТОРИЧНОЙ должности."""
        db.add_employee({
            'full_name': '__TEST__SecPos Сотрудник',
            'phone': '+79991111011',
            'position': 'Менеджер',
            'secondary_position': 'Замерщик',
            'login': '__test_secpos',
            'password': 'pass',
        })

        employees = db.get_employees_by_position('Замерщик')
        assert isinstance(employees, list)
        found = any(e['full_name'] == '__TEST__SecPos Сотрудник' for e in employees)
        assert found, "Сотрудник с вторичной должностью 'Замерщик' должен быть найден"


class TestLoginExists:
    """Проверка уникальности логина."""

    def test_check_login_exists_true(self, db):
        """Логин существует."""
        db.add_employee({
            'full_name': '__TEST__Exists Сотрудник',
            'phone': '+79991111012',
            'position': 'Дизайнер',
            'login': '__test_exists',
            'password': 'pass',
        })

        assert db.check_login_exists('__test_exists') is True

    def test_check_login_exists_false(self, db):
        """Логин не существует."""
        assert db.check_login_exists('__nonexistent_login_xyz__') is False

    def test_check_login_exists_admin(self, db):
        """Логин 'admin' всегда существует (создаётся при initialize_database)."""
        assert db.check_login_exists('admin') is True


class TestOfflineAuth:
    """Offline авторизация: кэширование и вход."""

    def test_cache_employee_password(self, db):
        """Кэширование пароля для offline-аутентификации."""
        emp_id = db.add_employee({
            'full_name': '__TEST__Cache Сотрудник',
            'phone': '+79991111013',
            'position': 'Дизайнер',
            'login': '__test_cache',
            'password': 'old_pass',
        })

        result = db.cache_employee_password(emp_id, 'new_cached_pass')
        assert result is True

        # Проверяем что новый пароль сохранён корректно
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute('SELECT password FROM employees WHERE id = ?', (emp_id,))
        row = cursor.fetchone()
        db.close()

        assert verify_password('new_cached_pass', row['password'])

    def test_get_employee_for_offline_login_exists(self, db):
        """Получение сотрудника для offline-входа (с кэшированным паролем)."""
        emp_id = db.add_employee({
            'full_name': '__TEST__Offline Login',
            'phone': '+79991111014',
            'position': 'Дизайнер',
            'login': '__test_offline_login',
            'password': 'offline_pass',
        })

        emp = db.get_employee_for_offline_login('__test_offline_login')
        assert emp is not None
        assert emp['full_name'] == '__TEST__Offline Login'
        assert emp['login'] == '__test_offline_login'

    def test_get_employee_for_offline_login_no_password(self, db):
        """Offline-вход невозможен без кэшированного пароля."""
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO employees (full_name, phone, position, department, login, password, status)
            VALUES ('__TEST__NoPass', '+79991111015', 'Дизайнер', 'Проектный', '__test_nopass', '', 'активный')
        """)
        conn.commit()
        db.close()

        emp = db.get_employee_for_offline_login('__test_nopass')
        assert emp is None

    def test_get_employee_for_offline_login_inactive(self, db):
        """Offline-вход невозможен для неактивного сотрудника."""
        conn = db.connect()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO employees (full_name, phone, position, department, login, password, status)
            VALUES ('__TEST__Inactive', '+79991111016', 'Дизайнер', 'Проектный', '__test_inactive', 'somehash', 'уволен')
        """)
        conn.commit()
        db.close()

        emp = db.get_employee_for_offline_login('__test_inactive')
        assert emp is None

    def test_get_employee_for_offline_login_nonexistent(self, db):
        """Offline-вход для несуществующего логина."""
        emp = db.get_employee_for_offline_login('__absolutely_nonexistent__')
        assert emp is None

    def test_cache_then_offline_login(self, db):
        """Полный сценарий: создание → кэширование → offline-вход."""
        emp_id = db.add_employee({
            'full_name': '__TEST__Full Flow',
            'phone': '+79991111017',
            'position': 'Менеджер',
            'login': '__test_full_flow',
            'password': 'initial_pass',
        })

        # Кэшируем новый пароль (как после API-входа)
        db.cache_employee_password(emp_id, 'api_pass_123')

        # Получаем для offline
        emp = db.get_employee_for_offline_login('__test_full_flow')
        assert emp is not None

        # Проверяем offline-пароль
        assert verify_password('api_pass_123', emp['password'])
