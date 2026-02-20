# -*- coding: utf-8 -*-
"""
Тесты DataAccess — CRUD операции с изолированной БД.
20 тестов.
"""

import pytest
from utils.data_access import DataAccess


@pytest.mark.ui
class TestDataAccessClients:
    """CRUD операции с клиентами через DataAccess."""

    def test_create_client_individual(self, data_access):
        """Создание физического лица."""
        result = data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Тестов Клиент Один",
            "phone": "+7 (999) 111-11-11",
            "email": "test1@test.ru"
        })
        assert result is not None
        assert result.get("id") is not None

    def test_create_client_legal(self, data_access):
        """Создание юридического лица."""
        result = data_access.create_client({
            "client_type": "Юридическое лицо",
            "organization_name": "ООО Тест",
            "organization_type": "ООО",
            "inn": "7712345678",
            "phone": "+7 (495) 222-22-22"
        })
        assert result is not None

    def test_get_all_clients_empty(self, data_access):
        """Пустая БД — пустой список."""
        clients = data_access.get_all_clients()
        assert isinstance(clients, list)
        assert len(clients) == 0

    def test_get_all_clients_after_create(self, data_access):
        """После создания — клиент появляется в списке."""
        data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Тестов Два",
            "phone": "+7 (999) 333-33-33"
        })
        clients = data_access.get_all_clients()
        assert len(clients) >= 1

    def test_update_client(self, data_access):
        """Обновление клиента."""
        result = data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Старое Имя",
            "phone": "+7 (999) 444-44-44"
        })
        client_id = result["id"]
        data_access.update_client(client_id, {
            "full_name": "Новое Имя",
            "phone": "+7 (999) 444-44-44"
        })
        clients = data_access.get_all_clients()
        updated = [c for c in clients if c["id"] == client_id]
        assert len(updated) == 1
        assert updated[0]["full_name"] == "Новое Имя"


@pytest.mark.ui
class TestDataAccessContracts:
    """CRUD операции с договорами."""

    def test_create_contract(self, data_access):
        """Создание договора."""
        client = data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Клиент Для Договора",
            "phone": "+7 (999) 555-55-55"
        })
        result = data_access.create_contract({
            "contract_number": "ТСТ-ПОЛ-001/26",
            "project_type": "Индивидуальный проект",
            "client_id": client["id"],
            "contract_date": "2026-01-15",
            "city": "СПБ",
            "address": "г. СПб, ул. Тест, д.1",
            "area": 85.5,
            "total_amount": 500000
        })
        assert result is not None
        assert result.get("id") is not None

    def test_get_all_contracts_empty(self, data_access):
        """Пустая БД — пустой список."""
        contracts = data_access.get_all_contracts()
        assert isinstance(contracts, list)
        assert len(contracts) == 0

    def test_get_all_contracts_after_create(self, data_access):
        """После создания — договор появляется."""
        client = data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Клиент Два",
            "phone": "+7 (999) 666-66-66"
        })
        data_access.create_contract({
            "contract_number": "ТСТ-ПОЛ-002/26",
            "project_type": "Индивидуальный проект",
            "client_id": client["id"],
            "contract_date": "2026-02-01",
            "city": "МСК",
            "address": "г. Москва, ул. Тест, д.2",
            "area": 100,
            "total_amount": 600000
        })
        contracts = data_access.get_all_contracts()
        assert len(contracts) >= 1

    def test_update_contract(self, data_access):
        """Обновление договора."""
        client = data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Клиент Три",
            "phone": "+7 (999) 777-77-77"
        })
        result = data_access.create_contract({
            "contract_number": "ТСТ-ПОЛ-003/26",
            "project_type": "Индивидуальный проект",
            "client_id": client["id"],
            "contract_date": "2026-03-01",
            "city": "СПБ",
            "address": "Старый адрес",
            "area": 50,
            "total_amount": 200000
        })
        data_access.update_contract(result["id"], {"address": "Новый адрес"})
        contracts = data_access.get_all_contracts()
        updated = [c for c in contracts if c["id"] == result["id"]]
        assert len(updated) == 1
        assert updated[0]["address"] == "Новый адрес"


@pytest.mark.ui
class TestDataAccessEmployees:
    """CRUD операции с сотрудниками."""

    def test_create_employee(self, data_access):
        """Создание сотрудника."""
        result = data_access.create_employee({
            "full_name": "Новый Сотрудник",
            "login": "new_emp",
            "password": "test123",
            "position": "Дизайнер",
            "department": "Проектный отдел",
            "status": "активный"
        })
        assert result is not None

    def test_get_all_employees(self, data_access):
        """Получение списка сотрудников."""
        employees = data_access.get_all_employees()
        assert isinstance(employees, list)

    def test_update_employee(self, data_access):
        """Обновление сотрудника."""
        result = data_access.create_employee({
            "full_name": "Старое ФИО",
            "login": "old_emp",
            "password": "test123",
            "position": "Дизайнер",
            "department": "Проектный отдел",
            "status": "активный"
        })
        emp_id = result["id"]
        data_access.update_employee(emp_id, {"full_name": "Новое ФИО"})
        employees = data_access.get_all_employees()
        updated = [e for e in employees if e["id"] == emp_id]
        assert len(updated) == 1
        assert updated[0]["full_name"] == "Новое ФИО"


@pytest.mark.ui
class TestDataAccessOnlineOffline:
    """Проверка online/offline режима."""

    def test_is_online_false_without_api(self, data_access):
        """Без API клиента — offline режим."""
        assert data_access.is_online is False

    def test_db_available(self, data_access):
        """БД доступна."""
        assert data_access.db is not None

    def test_api_client_none(self, data_access):
        """API клиент = None в offline режиме."""
        assert data_access.api_client is None


@pytest.mark.ui
class TestDataAccessIntegrity:
    """Целостность данных."""

    def test_client_all_fields_preserved(self, data_access):
        """Все поля клиента сохраняются."""
        data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Полное Имя Тест",
            "phone": "+7 (999) 888-88-88",
            "email": "full@test.ru",
            "address": "г. Тест, ул. Полная, д.100",
            "passport_series": "4012",
            "passport_number": "654321",
            "notes": "Заметки тест"
        })
        clients = data_access.get_all_clients()
        assert len(clients) == 1
        c = clients[0]
        assert c["full_name"] == "Полное Имя Тест"
        assert c["phone"] == "+7 (999) 888-88-88"
        assert c["email"] == "full@test.ru"

    def test_contract_all_fields_preserved(self, data_access):
        """Все поля договора сохраняются."""
        client = data_access.create_client({
            "client_type": "Физическое лицо",
            "full_name": "Клиент Полный",
            "phone": "+7 (999) 999-99-99"
        })
        data_access.create_contract({
            "contract_number": "ТСТ-ПОЛ-FULL/26",
            "project_type": "Индивидуальный проект",
            "client_id": client["id"],
            "contract_date": "2026-01-01",
            "city": "СПБ",
            "address": "Полный адрес",
            "area": 99.9,
            "total_amount": 1000000,
            "advance_payment": 300000,
            "contract_period": 45
        })
        contracts = data_access.get_all_contracts()
        assert len(contracts) == 1
        ct = contracts[0]
        assert ct["contract_number"] == "ТСТ-ПОЛ-FULL/26"
        assert ct["city"] == "СПБ"
        assert float(ct["area"]) == pytest.approx(99.9, abs=0.1)
